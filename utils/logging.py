"""
Module logging.py
----------------
Module này cung cấp các công cụ ghi log cho hệ thống QuangStation V2.
Hỗ trợ ghi log vào file và hiển thị trên console.
"""

import os
import logging
import datetime
from logging.handlers import RotatingFileHandler
import traceback
import sys

class QuangLogger:
    """
    Lớp quản lý ghi log cho hệ thống QuangStation V2.
    Cung cấp các mức độ log khác nhau và hỗ trợ ghi log vào file.
    """
    
    # Các mức độ log
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL
    
    # Định dạng log mặc định
    DEFAULT_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    def __init__(self, logger_name="QuangStation", log_level=logging.INFO, 
                 log_to_file=True, log_directory="logs", max_file_size=10*1024*1024,
                 backup_count=5, log_format=None):
        """
        Khởi tạo logger.
        
        Args:
            logger_name (str): Tên của logger
            log_level (int): Mức độ log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_to_file (bool): Có ghi log vào file hay không
            log_directory (str): Thư mục chứa file log
            max_file_size (int): Kích thước tối đa của file log (bytes)
            backup_count (int): Số lượng file log backup
            log_format (str): Định dạng log
        """
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(log_level)
        
        # Xóa tất cả handlers hiện tại (nếu có)
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # Định dạng log
        if log_format is None:
            log_format = self.DEFAULT_FORMAT
        formatter = logging.Formatter(log_format)
        
        # Handler cho console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Handler cho file nếu được yêu cầu
        if log_to_file:
            try:
                # Tạo thư mục log nếu chưa tồn tại
                if not os.path.exists(log_directory):
                    os.makedirs(log_directory)
                
                # Tạo tên file log với timestamp
                timestamp = datetime.datetime.now().strftime("%Y%m%d")
                log_file = os.path.join(log_directory, f"{logger_name}_{timestamp}.log")
                
                # Tạo file handler với rotating
                file_handler = RotatingFileHandler(
                    log_file, 
                    maxBytes=max_file_size, 
                    backupCount=backup_count
                )
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
                
                self.log_info(f"Đã khởi tạo log tại: {log_file}")
            except Exception as e:
                self.log_error(f"Không thể tạo file log: {str(e)}")
    
    def log_debug(self, message):
        """Ghi log ở mức DEBUG"""
        self.logger.debug(message)
    
    def log_info(self, message):
        """Ghi log ở mức INFO"""
        self.logger.info(message)
    
    def log_warning(self, message):
        """Ghi log ở mức WARNING"""
        self.logger.warning(message)
    
    def log_error(self, message, include_traceback=False):
        """
        Ghi log ở mức ERROR.
        
        Args:
            message (str): Thông báo lỗi
            include_traceback (bool): Có ghi thêm traceback không
        """
        if include_traceback:
            message = f"{message}\nTraceback: {traceback.format_exc()}"
        self.logger.error(message)
    
    def log_critical(self, message, include_traceback=True):
        """
        Ghi log ở mức CRITICAL.
        
        Args:
            message (str): Thông báo lỗi nghiêm trọng
            include_traceback (bool): Có ghi thêm traceback không
        """
        if include_traceback:
            message = f"{message}\nTraceback: {traceback.format_exc()}"
        self.logger.critical(message)
    
    def log_exception(self, message="Có ngoại lệ xảy ra:"):
        """
        Ghi log ngoại lệ hiện tại trong chương trình.
        
        Args:
            message (str): Thông báo đi kèm ngoại lệ
        """
        self.logger.exception(message)
    
    def log_operation(self, operation, status, details=None):
        """
        Ghi log một thao tác trong hệ thống.
        
        Args:
            operation (str): Tên thao tác
            status (str): Trạng thái (thành công/thất bại)
            details (str, optional): Chi tiết bổ sung
        """
        message = f"Operation: {operation} - Status: {status}"
        if details:
            message += f" - Details: {details}"
        self.log_info(message)
    
    def log_user_action(self, user, action, target=None, result=None):
        """
        Ghi log thao tác của người dùng.
        
        Args:
            user (str): Tên người dùng
            action (str): Thao tác
            target (str, optional): Đối tượng tác động
            result (str, optional): Kết quả
        """
        message = f"User: {user} - Action: {action}"
        if target:
            message += f" - Target: {target}"
        if result:
            message += f" - Result: {result}"
        self.log_info(message)
    
    def get_logger(self):
        """Lấy đối tượng logger gốc"""
        return self.logger

# Tạo logger mặc định cho toàn bộ hệ thống
default_logger = QuangLogger(logger_name="QuangStation")

def get_logger(module_name=None):
    """
    Lấy logger cho một module cụ thể.
    
    Args:
        module_name (str, optional): Tên module
        
    Returns:
        QuangLogger: Logger cho module
    """
    if module_name:
        return QuangLogger(logger_name=f"QuangStation.{module_name}")
    return default_logger

def log_system_info():
    """Ghi log thông tin hệ thống"""
    try:
        import platform
        import psutil
        
        logger = get_logger("SystemInfo")
        logger.log_info(f"Hệ điều hành: {platform.system()} {platform.release()}")
        logger.log_info(f"Python version: {platform.python_version()}")
        logger.log_info(f"CPU: {platform.processor()}")
        
        # Thông tin bộ nhớ
        memory = psutil.virtual_memory()
        logger.log_info(f"RAM: Tổng = {memory.total/1024/1024/1024:.2f} GB, "
                       f"Khả dụng = {memory.available/1024/1024/1024:.2f} GB")
        
        # Thông tin ổ đĩa
        disk = psutil.disk_usage('/')
        logger.log_info(f"Ổ đĩa: Tổng = {disk.total/1024/1024/1024:.2f} GB, "
                      f"Còn trống = {disk.free/1024/1024/1024:.2f} GB")
        
    except ImportError:
        default_logger.log_warning("Không thể import thư viện platform hoặc psutil")
    except Exception as e:
        default_logger.log_error(f"Lỗi khi thu thập thông tin hệ thống: {str(e)}")

def setup_exception_logging():
    """Cài đặt bắt ngoại lệ toàn cục để ghi log"""
    def exception_handler(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Trả về hành vi mặc định cho KeyboardInterrupt
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # Ghi log ngoại lệ
        logger = get_logger("ExceptionHandler")
        logger.log_critical(f"Ngoại lệ không được xử lý: {exc_value}")
    
    # Thiết lập handler cho ngoại lệ không được xử lý
    sys.excepthook = exception_handler
