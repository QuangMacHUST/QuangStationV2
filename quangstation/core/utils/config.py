"""
Quản lý cấu hình toàn cục cho hệ thống QuangStation V2
"""

import os
import json
import platform
from typing import Dict, Any, Optional, List
import logging
from pathlib import Path

class GlobalConfig:
    """Lớp quản lý cấu hình toàn cục"""
    
    _instance = None
    _config_path = os.path.join(os.path.expanduser("~"), ".quangstation", "config.json")
    _default_config = {
        "workspace": {
            "root_dir": os.path.join(os.path.expanduser("~"), "QuangStation_Data"),
            "temp_dir": os.path.join(os.path.expanduser("~"), "QuangStation_Data", "temp"),
            "backup_dir": os.path.join(os.path.expanduser("~"), "QuangStation_Data", "backups"),
            "auto_backup": True,
            "backup_interval_hours": 24
        },
        "database": {
            "path": os.path.join(os.path.expanduser("~"), "QuangStation_Data", "patients.db"),
            "backup_count": 5,
            "auto_vacuum": True
        },
        "logging": {
            "level": "INFO",
            "file_logging": True,
            "log_dir": os.path.join(os.path.expanduser("~"), "QuangStation_Data", "logs"),
            "max_file_size_mb": 10,
            "backup_count": 5
        },
        "display": {
            "default_window": 400,
            "default_level": 40,
            "colormap": "viridis",
            "show_annotations": True,
            "show_coordinates": True,
            "show_scale": True,
            "default_structure_colors": {
                "PTV": "#FF0000",
                "CTV": "#00FF00",
                "GTV": "#0000FF",
                "BODY": "#FFFF00",
                "LUNG": "#00FFFF",
                "HEART": "#FF00FF",
                "SPINAL_CORD": "#FF8000"
            }
        },
        "dose_calculation": {
            "algorithm": "collapsed_cone",
            "resolution_mm": 3.0,
            "threads": 4,
            "use_gpu": False,
            "hu_to_density_table": "default"
        },
        "optimization": {
            "algorithm": "gradient",
            "max_iterations": 100,
            "convergence_threshold": 0.001,
            "use_gpu": False
        },
        "ui": {
            "theme": "light",
            "font_size": 10,
            "window_size": [1280, 800],
            "maximize_on_startup": False,
            "confirm_on_exit": True,
            "language": "vi_VN"
        },
        "dicom": {
            "auto_anonymize": False,
            "institution_name": "QuangStation",
            "default_modalities": ["CT", "RTSTRUCT", "RTPLAN", "RTDOSE"]
        }
    }
    
    def __new__(cls):
        """Singleton pattern"""
        if not cls._instance:
            cls._instance = super(GlobalConfig, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Khởi tạo cấu hình"""
        self.config = self._load_config()
        self._ensure_directories()
        
    def _load_config(self) -> Dict[str, Any]:
        """Tải cấu hình từ file"""
        try:
            # Tạo thư mục cấu hình nếu chưa tồn tại
            os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
            
            # Kiểm tra xem file cấu hình đã tồn tại chưa
            if os.path.exists(self._config_path):
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                
                # Hợp nhất cấu hình người dùng với cấu hình mặc định
                config = self._merge_configs(self._default_config, user_config)
            else:
                # Nếu không có file cấu hình, sử dụng cấu hình mặc định
                config = self._default_config.copy()
                
                # Lưu cấu hình mặc định
                with open(self._config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
            
            return config
        except Exception as error:
            logging.error(f"Lỗi khi tải cấu hình: {str(error)}")
            return self._default_config.copy()
    
    def _merge_configs(self, default_config: Dict, user_config: Dict) -> Dict:
        """Hợp nhất cấu hình người dùng với cấu hình mặc định"""
        result = default_config.copy()
        
        for key, value in user_config.items():
            if key in result and isinstance(value, dict) and isinstance(result[key], dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _ensure_directories(self):
        """Đảm bảo các thư mục cần thiết tồn tại"""
        directories = [
            self.config["workspace"]["root_dir"],
            self.config["workspace"]["temp_dir"],
            self.config["workspace"]["backup_dir"],
            self.config["logging"]["log_dir"],
            os.path.dirname(self.config["database"]["path"])
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def get(self, key_path: str, default=None) -> Any:
        """
        Lấy giá trị cấu hình theo đường dẫn khóa
        
        Args:
            key_path: Đường dẫn khóa, phân tách bằng dấu chấm (ví dụ: "display.colormap")
            default: Giá trị mặc định nếu không tìm thấy khóa
            
        Returns:
            Giá trị cấu hình
        """
        try:
            parts = key_path.split('.')
            value = self.config
            
            for part in parts:
                value = value[part]
                
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any) -> bool:
        """
        Đặt giá trị cấu hình theo đường dẫn khóa
        
        Args:
            key_path: Đường dẫn khóa, phân tách bằng dấu chấm (ví dụ: "display.colormap")
            value: Giá trị cần đặt
            
        Returns:
            True nếu thành công, False nếu thất bại
        """
        try:
            parts = key_path.split('.')
            config = self.config
            
            # Điều hướng đến phần tử cuối cùng
            for part in parts[:-1]:
                if part not in config:
                    config[part] = {}
                config = config[part]
            
            # Đặt giá trị
            config[parts[-1]] = value
            
            # Lưu cấu hình
            self.save()
            
            return True
        except Exception as error:
            logging.error(f"Lỗi khi đặt cấu hình {key_path}: {str(error)}")
            return False
    
    def save(self) -> bool:
        """
        Lưu cấu hình hiện tại vào file
        
        Returns:
            True nếu thành công, False nếu thất bại
        """
        try:
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as error:
            logging.error(f"Lỗi khi lưu cấu hình: {str(error)}")
            return False
    
    def reset_to_default(self) -> bool:
        """
        Đặt lại cấu hình về mặc định
        
        Returns:
            True nếu thành công, False nếu thất bại
        """
        try:
            self.config = self._default_config.copy()
            self.save()
            self._ensure_directories()
            return True
        except Exception as error:
            logging.error(f"Lỗi khi đặt lại cấu hình: {str(error)}")
            return False
    
    def validate_config(self) -> List[str]:
        """
        Xác thực cấu hình hiện tại
        
        Returns:
            Danh sách các lỗi, rỗng nếu không có lỗi
        """
        errors = []
        
        # Kiểm tra các thư mục
        for path_key in ["workspace.root_dir", "workspace.temp_dir", "workspace.backup_dir", "logging.log_dir"]:
            path = self.get(path_key)
            if not path or not isinstance(path, str):
                errors.append(f"Đường dẫn không hợp lệ cho {path_key}: {path}")
        
        # Kiểm tra các giá trị số
        for num_key in ["logging.max_file_size_mb", "logging.backup_count", "dose_calculation.resolution_mm"]:
            value = self.get(num_key)
            if not isinstance(value, (int, float)) or value <= 0:
                errors.append(f"Giá trị không hợp lệ cho {num_key}: {value}")
        
        # Kiểm tra các giá trị boolean
        for bool_key in ["workspace.auto_backup", "database.auto_vacuum", "logging.file_logging"]:
            value = self.get(bool_key)
            if not isinstance(value, bool):
                errors.append(f"Giá trị không hợp lệ cho {bool_key}: {value}")
        
        return errors
    
    def export_config(self, file_path: str) -> bool:
        """
        Xuất cấu hình hiện tại ra file
        
        Args:
            file_path: Đường dẫn file xuất
            
        Returns:
            True nếu thành công, False nếu thất bại
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as error:
            logging.error(f"Lỗi khi xuất cấu hình: {str(error)}")
            return False
    
    def import_config(self, file_path: str) -> bool:
        """
        Nhập cấu hình từ file
        
        Args:
            file_path: Đường dẫn file nhập
            
        Returns:
            True nếu thành công, False nếu thất bại
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
            
            # Hợp nhất cấu hình
            self.config = self._merge_configs(self._default_config, user_config)
            
            # Lưu cấu hình
            self.save()
            
            # Đảm bảo các thư mục tồn tại
            self._ensure_directories()
            
            return True
        except Exception as error:
            logging.error(f"Lỗi khi nhập cấu hình: {str(error)}")
            return False

# Tạo instance toàn cục
config = GlobalConfig()

# Hàm tiện ích
def get_config(key: str, default=None):
    """Lấy giá trị cấu hình"""
    return config.get(key, default)

def set_config(key: str, value: Any):
    """Đặt giá trị cấu hình"""
    config.set(key, value)

def reset_config():
    """Đặt lại cấu hình về mặc định"""
    config.reset_to_default()

def validate_config():
    """Xác thực cấu hình hiện tại"""
    return config.validate_config()

def export_config(file_path: str):
    """Xuất cấu hình hiện tại ra file"""
    config.export_config(file_path)

def import_config(file_path: str):
    """Nhập cấu hình từ file"""
    config.import_config(file_path) 