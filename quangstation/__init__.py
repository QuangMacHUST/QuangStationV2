#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
QuangStation V2 - Hệ thống Lập kế hoạch Xạ trị Mã nguồn Mở
===========================================================

Phát triển bởi Mạc Đăng Quang

Đây là hệ thống lập kế hoạch xạ trị hoàn chỉnh với các chức năng:
- Nhập khẩu và quản lý dữ liệu bệnh nhân
- Xử lý hình ảnh và phân đoạn cấu trúc
- Lập kế hoạch xạ trị
- Tính toán phân bố liều
- Tối ưu hóa kế hoạch
- Đánh giá kế hoạch
- Đảm bảo chất lượng
- Báo cáo

Phiên bản: 2.0.0
"""

import os
import importlib
import json
from datetime import datetime
import logging

# Import Resource Utils
from quangstation.core.utils.resource_utils import get_resources_path as _get_resources_path

# Biến phiên bản
__version__ = "2.0.0"
__author__ = "Mạc Đăng Quang"
__email__ = "quangmacdang@gmail.com"
__license__ = "GPL-3.0"
__copyright__ = "Copyright 2023, Mạc Đăng Quang"

# Cấu hình mặc định
DEFAULT_CONFIG = {
    "language": "vi",
    "theme": "default",
    "data_directory": None,
    "log_level": "INFO",
    "use_gpu": True,
    "use_cpp_extensions": True,
}

# Biến toàn cục
_config = dict(DEFAULT_CONFIG)
_language = "vi"
_logger = None
_integration_manager = None
_session_manager = None

# Thiết lập logging
def setup_logging(log_level=None, log_to_file=True):
    """
    Thiết lập logging cho hệ thống QuangStation V2
    
    Args:
        log_level: Mức độ log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Có ghi log vào file hay không
    """
    from quangstation.core.utils.logging import setup_logging, get_logger, setup_exception_logging
    
    # Thiết lập log level từ cấu hình nếu không được cung cấp
    if log_level is None:
        log_level = _config.get("log_level", "INFO")
    
    # Tạo thư mục log nếu chưa tồn tại
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # Tên file log dựa trên thời gian hiện tại
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f"quangstation_{timestamp}.log") if log_to_file else None
    
    # Thiết lập logging
    setup_logging(log_level=log_level, log_file=log_file)
    
    # Lấy logger cho module chính
    global _logger
    _logger = get_logger("QuangStation")
    
    # Thiết lập xử lý ngoại lệ toàn cục
    setup_exception_logging()
    
    # Ghi log thông tin hệ thống
    log_system_info()
    
    _logger.info(f"QuangStation V2 (phiên bản {__version__}) được khởi tạo")
    
    return _logger

def log_system_info():
    """Ghi log thông tin hệ thống để trợ giúp debug"""
    try:
        import platform
        import sys
        
        if _logger is None:
            return
            
        _logger.info("=== Thông tin hệ thống ===")
        _logger.info(f"Hệ điều hành: {platform.system()} {platform.version()}")
        _logger.info(f"Python: {platform.python_version()} ({platform.python_implementation()})")
        _logger.info(f"Kiến trúc: {platform.machine()}")
        
        # Thông tin bộ nhớ
        try:
            import psutil
            memory = psutil.virtual_memory()
            memory_gb = memory.total / (1024 ** 3)
            _logger.info(f"Bộ nhớ RAM: {memory_gb:.2f} GB (Khả dụng: {memory.available / (1024 ** 3):.2f} GB)")
            
            # Thông tin CPU
            _logger.info(f"CPU: {psutil.cpu_count(logical=False)} lõi vật lý, {psutil.cpu_count(logical=True)} luồng")
        except ImportError:
            _logger.info("Không thể lấy thông tin phần cứng (psutil không được cài đặt)")
        
        # Thông tin GPU
        try:
            import torch
            _logger.info(f"CUDA khả dụng: {torch.cuda.is_available()}")
            if torch.cuda.is_available():
                _logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
                _logger.info(f"Số lượng GPU: {torch.cuda.device_count()}")
                _logger.info(f"Bộ nhớ GPU: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB")
        except ImportError:
            _logger.info("Không thể lấy thông tin GPU (torch không được cài đặt)")
            
        # Thư mục làm việc
        _logger.info(f"Thư mục làm việc: {os.getcwd()}")
        _logger.info(f"Thư mục cài đặt: {os.path.dirname(os.path.dirname(__file__))}")
        
        # Module đã cài đặt
        _logger.info("=== Kiểm tra module phụ thuộc ===")
        is_complete, missing = check_dependencies(show_warnings=False)
        if is_complete:
            _logger.info("Tất cả module phụ thuộc đã được cài đặt")
        else:
            _logger.warning(f"Thiếu module phụ thuộc: {', '.join(missing)}")
            
        _logger.info("=== Kết thúc kiểm tra hệ thống ===")
    except Exception as error:
        if _logger:
            _logger.error(f"Lỗi khi ghi log thông tin hệ thống: {str(error)}")

# Quản lý ngôn ngữ
def set_language(language_code):
    """
    Thiết lập ngôn ngữ cho ứng dụng
    
    Args:
        language_code: Mã ngôn ngữ (vi, en)
    """
    global _language
    
    # Kiểm tra ngôn ngữ được hỗ trợ
    supported_languages = ["vi", "en"]
    if language_code not in supported_languages:
        if _logger:
            _logger.warning(f"Ngôn ngữ không được hỗ trợ: {language_code}. Sử dụng ngôn ngữ mặc định: vi")
        return False
    
    # Lưu ngôn ngữ mới
    _language = language_code
    _config["language"] = language_code
    
    if _logger:
        _logger.info(f"Đã chuyển sang ngôn ngữ: {language_code}")
        
    # Tải file ngôn ngữ
    load_translations(language_code)
    
    return True

def get_language():
    """
    Lấy ngôn ngữ hiện tại của ứng dụng
    
    Returns:
        str: Mã ngôn ngữ hiện tại
    """
    return _language

def load_translations(language_code=None):
    """
    Tải các chuỗi dịch từ file ngôn ngữ
    
    Args:
        language_code: Mã ngôn ngữ cần tải (nếu None sẽ sử dụng ngôn ngữ hiện tại)
        
    Returns:
        dict: Từ điển các chuỗi dịch
    """
    global _translations
    
    # Sử dụng ngôn ngữ hiện tại nếu không được chỉ định
    if language_code is None:
        language_code = _language
    
    # Tạo đường dẫn đến file ngôn ngữ
    lang_file = os.path.join(get_resources_path(), "lang", f"{language_code}.json")
    
    try:
        # Kiểm tra xem file có tồn tại không
        if not os.path.exists(lang_file):
            if _logger:
                _logger.warning(f"Không tìm thấy file ngôn ngữ: {lang_file}")
            
            # Nếu là Tiếng Anh, tự tạo dịch cơ bản
            if language_code == "en":
                _translations = create_default_english_translations()
            else:
                # Nếu không có file ngôn ngữ, sử dụng chuỗi gốc (Tiếng Việt)
                _translations = {}
            
            # Lưu file ngôn ngữ mới
            save_translations(language_code)
            
            return _translations
        
        # Đọc file ngôn ngữ
        with open(lang_file, 'r', encoding='utf-8') as f:
            _translations = json.load(f)
            
        if _logger:
            _logger.info(f"Đã tải {len(_translations)} chuỗi dịch từ {lang_file}")
            
        return _translations
    except Exception as error:
        if _logger:
            _logger.error(f"Lỗi khi tải file ngôn ngữ: {str(error)}")
        
        # Nếu có lỗi, sử dụng chuỗi gốc
        _translations = {}
        return _translations

def save_translations(language_code=None):
    """
    Lưu các chuỗi dịch vào file ngôn ngữ
    
    Args:
        language_code: Mã ngôn ngữ cần lưu (nếu None sẽ sử dụng ngôn ngữ hiện tại)
        
    Returns:
        bool: True nếu lưu thành công, False nếu không
    """
    global _translations
    
    # Sử dụng ngôn ngữ hiện tại nếu không được chỉ định
    if language_code is None:
        language_code = _language
    
    # Tạo thư mục lang nếu chưa tồn tại
    lang_dir = os.path.join(get_resources_path(), "lang")
    os.makedirs(lang_dir, exist_ok=True)
    
    # Tạo đường dẫn đến file ngôn ngữ
    lang_file = os.path.join(lang_dir, f"{language_code}.json")
    
    try:
        # Lưu file ngôn ngữ
        with open(lang_file, 'w', encoding='utf-8') as f:
            json.dump(_translations, f, indent=4, ensure_ascii=False)
            
        if _logger:
            _logger.info(f"Đã lưu {len(_translations)} chuỗi dịch vào {lang_file}")
            
        return True
    except Exception as error:
        if _logger:
            _logger.error(f"Lỗi khi lưu file ngôn ngữ: {str(error)}")
        
        return False

def create_default_english_translations():
    """
    Tạo các chuỗi dịch tiếng Anh mặc định
    
    Returns:
        dict: Từ điển các chuỗi dịch tiếng Anh
    """
    return {
        # Chuỗi giao diện chung
        "app_title": "QuangStation V2 - Radiotherapy Treatment Planning System",
        "file": "File",
        "edit": "Edit",
        "view": "View",
        "help": "Help",
        "tools": "Tools",
        "report": "Report",
        "language": "Language",
        
        # Menu File
        "new_patient": "New Patient",
        "open_patient": "Open Patient",
        "import_dicom": "Import DICOM",
        "export_plan": "Export Plan",
        "exit": "Exit",
        
        # Menu Plan
        "new_plan": "New Plan",
        "copy_plan": "Copy Plan",
        "delete_plan": "Delete Plan",
        
        # Menu Tools
        "auto_contour": "Auto Contour",
        "dose_calculation": "Dose Calculation",
        "optimize_plan": "Optimize Plan",
        "show_dvh": "Show DVH",
        "plan_qa": "Plan QA",
        "settings": "Settings",
        
        # Các nút chức năng
        "save": "Save",
        "cancel": "Cancel",
        "close": "Close",
        "apply": "Apply",
        "calculate": "Calculate",
        "optimize": "Optimize",
        
        # Thông báo lỗi
        "error": "Error",
        "warning": "Warning",
        "info": "Information",
        "confirm": "Confirmation",
        
        # Thông báo thành công
        "success": "Success",
        "operation_completed": "Operation completed successfully",
        
        # Các chuỗi khác
        "loading": "Loading...",
        "processing": "Processing...",
        "please_wait": "Please wait..."
    }

def translate(key, default=None):
    """
    Dịch một chuỗi theo ngôn ngữ hiện tại
    
    Args:
        key: Khóa chuỗi cần dịch
        default: Chuỗi mặc định nếu không tìm thấy khóa
        
    Returns:
        str: Chuỗi đã dịch
    """
    global _translations
    
    # Nếu chưa có translations, tải file ngôn ngữ
    if '_translations' not in globals() or _translations is None:
        _translations = load_translations()
    
    # Nếu ngôn ngữ là tiếng Việt, trả về key hoặc default
    if _language == "vi":
        return default if default is not None else key
    
    # Tìm chuỗi dịch
    if key in _translations:
        return _translations[key]
    
    # Nếu không tìm thấy, trả về chuỗi mặc định hoặc khóa
    return default if default is not None else key

# Biến lưu trữ các chuỗi dịch
_translations = None

# Khởi tạo với ngôn ngữ mặc định
load_translations()

# Kiểm tra phụ thuộc
def check_dependencies(show_warnings=True):
    """
    Kiểm tra các thư viện phụ thuộc
    
    Args:
        show_warnings: Hiển thị cảnh báo nếu thiếu thư viện
        
    Returns:
        tuple: (is_complete, missing_packages)
    """
    logger = logging.getLogger(__name__)
    
    required_packages = {
        "numpy": "1.19.0",
        "matplotlib": "3.3.0",
        "pydicom": "2.1.0",
        "scikit-image": "0.17.0",
        "scikit-learn": "0.23.0",
        "scipy": "1.5.0",
        "SimpleITK": "2.0.0",
        "vtk": "9.0.0",
        "pandas": "1.1.0",
        "openpyxl": "3.0.0",
        "reportlab": "3.5.0",
        "PyPDF2": "1.26.0",
        "PIL": "8.0.0",  # Pillow
    }
    
    optional_packages = {
        "torch": "1.7.0",
        "tensorflow": "2.4.0",
        "keras": "2.4.0",
        "cupy": "8.0.0",
        "opencv-python": "4.5.0",
    }
    
    missing_packages = []
    
    # Kiểm tra các thư viện bắt buộc
    for package, min_version in required_packages.items():
        try:
            # Sử dụng importlib để kiểm tra thư viện
            # thay vì import trực tiếp để tránh lỗi
            pkg = importlib.import_module(package)
            # Một số thư viện có thể không có phiên bản hoặc tên khác
            if hasattr(pkg, "__version__"):
                if pkg.__version__ < min_version:
                    missing_packages.append(f"{package} (>={min_version})")
                    if show_warnings:
                        logger.warning("Phiên bản thư viện %s (%s) thấp hơn yêu cầu (%s)", 
                                      package, pkg.__version__, min_version)
        except ImportError:
            missing_packages.append(f"{package} (>={min_version})")
            if show_warnings:
                logger.warning("Không tìm thấy thư viện bắt buộc: %s", package)
    
    # Kiểm tra các thư viện tùy chọn nhưng chỉ hiển thị thông báo
    for package, min_version in optional_packages.items():
        try:
            importlib.import_module(package)
        except ImportError:
            if show_warnings:
                logger.info("Thư viện tùy chọn không được cài đặt: %s", package)
    
    return (len(missing_packages) == 0, missing_packages)

# Quản lý cấu hình
def load_config(config_path=None):
    """
    Tải cấu hình từ file
    
    Args:
        config_path: Đường dẫn đến file cấu hình json
        
    Returns:
        dict: Cấu hình đã tải
    """
    global _config
    
    if config_path is None:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "settings.json")
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                _config.update(loaded_config)
                
            if _logger:
                _logger.info(f"Đã tải cấu hình từ {config_path}")
            
            # Cập nhật ngôn ngữ nếu có trong cấu hình
            if "language" in loaded_config:
                set_language(loaded_config["language"])
                
            # Cập nhật các cấu hình khác nếu cần
            from quangstation.utils.config import GlobalConfig
            GlobalConfig.update_from_dict(_config)
            
            return _config
        else:
            if _logger:
                _logger.warning(f"Không tìm thấy file cấu hình: {config_path}, sử dụng cấu hình mặc định")
    except Exception as error:
        if _logger:
            _logger.error(f"Lỗi khi tải cấu hình: {str(error)}")
    
    return _config

def save_config(config_path=None):
    """
    Lưu cấu hình vào file
    
    Args:
        config_path: Đường dẫn đến file cấu hình json
        
    Returns:
        bool: True nếu lưu thành công, False nếu không
    """
    if config_path is None:
        config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "settings.json")
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(_config, f, indent=4, ensure_ascii=False)
        
        if _logger:
            _logger.info(f"Đã lưu cấu hình vào {config_path}")
        
        return True
    except Exception as error:
        if _logger:
            _logger.error(f"Lỗi khi lưu cấu hình: {str(error)}")
        
        return False

def set_data_directory(directory):
    """
    Thiết lập thư mục dữ liệu
    
    Args:
        directory: Đường dẫn đến thư mục lưu trữ dữ liệu
    
    Returns:
        bool: True nếu thành công, False nếu không
    """
    if os.path.exists(directory) and os.path.isdir(directory):
        _config["data_directory"] = directory
        if _logger:
            _logger.info(f"Đã thiết lập thư mục dữ liệu: {directory}")
        return True
    else:
        if _logger:
            _logger.warning(f"Thư mục không tồn tại: {directory}")
        return False

def get_data_directory():
    """
    Lấy thư mục dữ liệu hiện tại
    
    Returns:
        str: Đường dẫn đến thư mục dữ liệu
    """
    data_dir = _config.get("data_directory")
    if data_dir is None:
        # Sử dụng thư mục mặc định
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        os.makedirs(data_dir, exist_ok=True)
        _config["data_directory"] = data_dir
    
    return data_dir

def get_resources_path():
    """
    Trả về đường dẫn đến thư mục resources
    
    Returns:
        str: Đường dẫn đến thư mục resources
    """
    return _get_resources_path()

# Hàm hiển thị thông tin phiên bản
def show_version():
    """
    Hiển thị thông tin phiên bản của QuangStation V2
    
    Returns:
        dict: Thông tin phiên bản
    """
    version_info = {
        "name": "QuangStation V2",
        "version": __version__,
        "author": __author__,
        "email": __email__,
        "license": __license__,
        "copyright": __copyright__,
        "description": "Hệ thống Lập kế hoạch Xạ trị Mã nguồn Mở"
    }
    
    for key, value in version_info.items():
        print(f"{key}: {value}")
    
    return version_info

# Hàm khởi chạy ứng dụng
def run_application():
    """
    Khởi chạy ứng dụng QuangStation V2
    """
    # Thiết lập kết nối với cơ sở dữ liệu và tạo session
    global _integration_manager, _session_manager
    
    # Tạo thể hiện của integration manager nếu chưa có
    if _integration_manager is None:
        from quangstation.integration import IntegrationManager
        data_dir = get_data_directory()
        db_path = os.path.join(data_dir, "patients.db")
        _integration_manager = IntegrationManager(db_path=db_path)
        
        if _logger:
            _logger.info(f"Đã khởi tạo Integration Manager với database: {db_path}")
    
    # Tạo thể hiện của session manager nếu chưa có
    if _session_manager is None:
        from quangstation.data_management.session_management import SessionManager
        workspace_dir = os.path.join(get_data_directory(), "workspace")
        _session_manager = SessionManager(workspace_dir=workspace_dir)
        
        if _logger:
            _logger.info(f"Đã khởi tạo Session Manager với workspace: {workspace_dir}")
    
    # Kiểm tra xem tkinter có sẵn sàng hay không
    try:
        import tkinter
    except ImportError:
        if _logger:
            _logger.error("Không thể khởi động giao diện: thiếu thư viện tkinter")
        print("Lỗi: Không thể khởi động giao diện vì thiếu thư viện tkinter")
        print("Hãy cài đặt tkinter để sử dụng giao diện đồ họa.")
        return False
    
    # Chạy ứng dụng chính
    try:
        from quangstation.main import main
        main()
        return True
    except Exception as error:
        if _logger:
            _logger.error(f"Lỗi khi khởi động ứng dụng: {str(error)}")
            import traceback
            _logger.error(traceback.format_exc())
        print(f"Lỗi khi khởi động ứng dụng: {str(error)}")
        return False

# Các module được export
__all__ = [
    # Core
    'setup_logging', 'show_version', 'run_application',
    'set_language', 'get_language', 'load_config', 'save_config',
    'set_data_directory', 'get_data_directory', 'get_resources_path',
    'check_dependencies', 'log_system_info',
    
    # Đa ngôn ngữ
    'load_translations', 'save_translations', 'translate',
    
    # Các module từ utils
    'get_logger', 'get_config', 'GlobalConfig',
    
    # Quản lý dữ liệu
    'PatientDatabase', 'DICOMParser', 'SessionManager',
    
    # Xử lý hình ảnh
    'ImageLoader', 'Segmentation',
    
    # Phân đoạn cấu trúc
    'ContourTools',
    
    # Lập kế hoạch
    'PlanConfig', 'BeamManager', 'create_technique',
    
    # Tính liều
    'DoseCalculator',
    
    # Đánh giá kế hoạch
    'DVHCalculator', 'DVHPlotter', 'BiologicalMetrics',
    
    # Tối ưu hóa
    'PlanOptimizer',
    
    # Đảm bảo chất lượng
    'QAToolkit',
    
    # Báo cáo
    'ReportGenerator',
    
    # Workflow tích hợp
    'RTWorkflow', 'IntegrationManager', 'create_workflow', 'load_workflow'
]

# Thiết lập mặc định
# Chỉ cần import module là sẽ tự động thiết lập logging
setup_logging()

# Tải cấu hình mặc định
try:
    load_config()
except:
    if _logger:
        _logger.warning("Không thể tải cấu hình mặc định, sử dụng cấu hình cơ bản")

# Import các module cần thiết (lười)
def _lazy_import():
    global PatientDatabase, DICOMParser, SessionManager
    global ImageLoader, Segmentation
    global ContourTools
    global PlanConfig, BeamManager, create_technique
    global DoseCalculator
    global DVHCalculator, DVHPlotter, BiologicalMetrics
    global PlanOptimizer
    global QAToolkit
    global ReportGenerator
    global RTWorkflow, IntegrationManager, create_workflow, load_workflow
    global get_logger, get_config, GlobalConfig
    
    # Các import tối thiểu
    from quangstation.core.utils.logging import get_logger
    from quangstation.core.utils.config import get_config, GlobalConfig
    
    # Import đầy đủ khi cần
    try:
        # Quản lý dữ liệu
        from quangstation.clinical.data_management.patient_db import PatientDatabase
        from quangstation.core.io.dicom_parser import DICOMParser
        from quangstation.clinical.data_management.session_management import SessionManager

        # Xử lý hình ảnh
        from quangstation.services.image_processing.image_loader import ImageLoader
        from quangstation.services.image_processing.segmentation import Segmentation

        # Phân đoạn cấu trúc
        from quangstation.clinical.contouring.contour_tools import ContourTools

        # Lập kế hoạch
        from quangstation.clinical.planning.plan_config import PlanConfig
        from quangstation.clinical.planning.beam_management import BeamManager
        from quangstation.clinical.planning.techniques import create_technique

        # Tính liều
        from quangstation.clinical.dose_calculation.dose_engine_wrapper import DoseCalculator

        # Đánh giá kế hoạch
        from quangstation.clinical.plan_evaluation.dvh import DVHCalculator, DVHPlotter
        from quangstation.clinical.plan_evaluation.biological_metrics import BiologicalCalculator as BiologicalMetrics

        # Tối ưu hóa
        from quangstation.clinical.optimization.optimizer_wrapper import PlanOptimizer

        # Đảm bảo chất lượng
        from quangstation.quality.quality_assurance.qa_tools import PlanQA as QAToolkit

        # Báo cáo
        from quangstation.quality.reporting.report_gen import TreatmentReport as ReportGenerator

        # Workflow tích hợp
        from quangstation.services.intergration.integration import RTWorkflow, IntegrationManager, create_workflow, load_workflow
    except ImportError as e:
        if _logger:
            _logger.warning(f"Không thể import một số module: {str(e)}")

# Chỉ import khi cần
if __name__ != "__main__":
    try:
        # Kiểm tra nếu tkinter khả dụng
        import importlib.util
        if importlib.util.find_spec("tkinter"):
            # Nếu có, import các module GUI cụ thể thay vì import *
            from quangstation.gui import main_window, splash_screen
    except ImportError as ex:
        logger = logging.getLogger(__name__)
        logger.warning("Không thể import các module GUI: %s", str(ex))
