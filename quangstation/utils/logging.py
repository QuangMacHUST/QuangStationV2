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
import json
import platform
import sqlite3
import threading
import queue
from typing import Dict, Any, Optional, List, Union

from quangstation.utils.config import get_config

class DatabaseLogHandler(logging.Handler):
    """Handler ghi log vào cơ sở dữ liệu SQLite"""
    
    def __init__(self, db_path: str):
        super().__init__()
        self.db_path = db_path
        self.queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()
        self._create_table()
    
    def _create_table(self):
        """Tạo bảng log nếu chưa tồn tại"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    level TEXT,
                    logger TEXT,
                    message TEXT,
                    module TEXT,
                    function TEXT,
                    line INTEGER,
                    traceback TEXT,
                    user TEXT,
                    session_id TEXT
                )
            ''')
            conn.commit()
            conn.close()
        except Exception as e:
            sys.stderr.write(f"Lỗi khi tạo bảng log: {str(e)}\n")
    
    def emit(self, record):
        """Thêm bản ghi vào hàng đợi"""
        self.queue.put(record)
    
    def _process_queue(self):
        """Xử lý hàng đợi và ghi vào cơ sở dữ liệu"""
        while True:
            try:
                record = self.queue.get()
                self._write_to_db(record)
                self.queue.task_done()
            except Exception as e:
                sys.stderr.write(f"Lỗi khi xử lý hàng đợi log: {str(e)}\n")
    
    def _write_to_db(self, record):
        """Ghi bản ghi vào cơ sở dữ liệu"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Chuẩn bị dữ liệu
            timestamp = datetime.datetime.fromtimestamp(record.created).isoformat()
            level = record.levelname
            logger_name = record.name
            message = self.format(record)
            module = record.module
            function = record.funcName
            line = record.lineno
            
            # Lấy traceback nếu có
            if hasattr(record, 'exc_info') and record.exc_info:
                tb = ''.join(traceback.format_exception(*record.exc_info))
            else:
                tb = None
            
            # Lấy thông tin người dùng và phiên làm việc nếu có
            user = getattr(record, 'user', None)
            session_id = getattr(record, 'session_id', None)
            
            # Thêm vào cơ sở dữ liệu
            cursor.execute('''
                INSERT INTO system_logs 
                (timestamp, level, logger, message, module, function, line, traceback, user, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, level, logger_name, message, module, function, line, tb, user, session_id))
            
            conn.commit()
            conn.close()
        except Exception as e:
            sys.stderr.write(f"Lỗi khi ghi log vào cơ sở dữ liệu: {str(e)}\n")
    
    def close(self):
        """Đóng handler"""
        try:
            self.queue.join()  # Đợi tất cả các bản ghi được xử lý
        except Exception:
            pass
        super().close()

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
    
    # Từ điển lưu trữ các logger đã tạo
    _loggers = {}
    
    # Lock để đảm bảo thread-safety
    _lock = threading.RLock()
    
    @classmethod
    def get_instance(cls, logger_name: str = "QuangStation") -> 'QuangLogger':
        """
        Lấy instance của logger theo tên
        
        Args:
            logger_name: Tên của logger
            
        Returns:
            Instance của QuangLogger
        """
        with cls._lock:
            if logger_name not in cls._loggers:
                cls._loggers[logger_name] = cls(logger_name)
            return cls._loggers[logger_name]
    
    def __init__(self, logger_name: str = "QuangStation", log_level: int = None, 
                 log_to_file: bool = None, log_directory: str = None, 
                 max_file_size: int = None, backup_count: int = None, 
                 log_format: str = None, log_to_db: bool = None,
                 db_path: str = None):
        """
        Khởi tạo logger
        
        Args:
            logger_name: Tên của logger
            log_level: Mức độ log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_to_file: Có ghi log vào file hay không
            log_directory: Thư mục chứa file log
            max_file_size: Kích thước tối đa của file log (bytes)
            backup_count: Số lượng file log backup tối đa
            log_format: Định dạng log
            log_to_db: Có ghi log vào cơ sở dữ liệu hay không
            db_path: Đường dẫn đến file cơ sở dữ liệu
        """
        self.logger_name = logger_name
        
        # Lấy cấu hình từ GlobalConfig nếu không được chỉ định
        if log_level is None:
            log_level_str = get_config("logging.level", "INFO")
            log_level = getattr(logging, log_level_str.upper(), logging.INFO)
        
        if log_to_file is None:
            log_to_file = get_config("logging.file_logging", True)
        
        if log_directory is None:
            log_directory = get_config("logging.log_dir", os.path.join(os.path.expanduser("~"), "QuangStation_Data", "logs"))
        
        if max_file_size is None:
            max_file_size = get_config("logging.max_file_size_mb", 10) * 1024 * 1024
        
        if backup_count is None:
            backup_count = get_config("logging.backup_count", 5)
        
        if log_format is None:
            log_format = self.DEFAULT_FORMAT
        
        if log_to_db is None:
            log_to_db = get_config("logging.log_to_db", False)
        
        if db_path is None:
            db_path = get_config("logging.db_path", os.path.join(os.path.expanduser("~"), "QuangStation_Data", "logs.db"))
        
        # Tạo logger
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(log_level)
        
        # Xóa tất cả các handler hiện có
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Tạo formatter
        formatter = logging.Formatter(log_format)
        
        # Thêm console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Thêm file handler nếu cần
        if log_to_file:
            # Tạo thư mục log nếu chưa tồn tại
            os.makedirs(log_directory, exist_ok=True)
            
            # Tạo file handler
            log_file = os.path.join(log_directory, f"{logger_name}.log")
            file_handler = RotatingFileHandler(
                log_file, 
                maxBytes=max_file_size, 
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        
        # Thêm database handler nếu cần
        if log_to_db:
            # Tạo thư mục chứa database nếu chưa tồn tại
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            # Tạo database handler
            db_handler = DatabaseLogHandler(db_path)
            db_handler.setFormatter(formatter)
            self.logger.addHandler(db_handler)
    
    def log_debug(self, message: str, **kwargs):
        """Ghi log mức DEBUG"""
        self.logger.debug(message, **kwargs)
    
    def log_info(self, message: str, **kwargs):
        """Ghi log mức INFO"""
        self.logger.info(message, **kwargs)
    
    def log_warning(self, message: str, **kwargs):
        """Ghi log mức WARNING"""
        self.logger.warning(message, **kwargs)
    
    def log_error(self, message: str, include_traceback: bool = False, **kwargs):
        """
        Ghi log mức ERROR
        
        Args:
            message: Thông điệp lỗi
            include_traceback: Có bao gồm traceback hay không
        """
        if include_traceback:
            self.logger.error(message, exc_info=True, **kwargs)
        else:
            self.logger.error(message, **kwargs)
    
    def log_critical(self, message: str, include_traceback: bool = True, **kwargs):
        """
        Ghi log mức CRITICAL
        
        Args:
            message: Thông điệp lỗi nghiêm trọng
            include_traceback: Có bao gồm traceback hay không
        """
        if include_traceback:
            self.logger.critical(message, exc_info=True, **kwargs)
        else:
            self.logger.critical(message, **kwargs)
    
    def log_exception(self, message: str = "Có ngoại lệ xảy ra:", **kwargs):
        """
        Ghi log ngoại lệ hiện tại
        
        Args:
            message: Thông điệp kèm theo ngoại lệ
        """
        self.logger.exception(message, **kwargs)
    
    def log_operation(self, operation: str, status: str, details: Any = None, **kwargs):
        """
        Ghi log một thao tác
        
        Args:
            operation: Tên thao tác
            status: Trạng thái (success, failed, etc.)
            details: Chi tiết bổ sung
        """
        message = f"Thao tác: {operation}, Trạng thái: {status}"
        if details:
            if isinstance(details, dict):
                details_str = json.dumps(details, ensure_ascii=False)
            else:
                details_str = str(details)
            message += f", Chi tiết: {details_str}"
        
        if status.lower() in ["success", "thành công", "ok"]:
            self.log_info(message, **kwargs)
        else:
            self.log_error(message, **kwargs)
    
    def log_user_action(self, user: str, action: str, target: str = None, result: str = None, **kwargs):
        """
        Ghi log hành động của người dùng
        
        Args:
            user: Tên người dùng
            action: Hành động
            target: Đối tượng tác động
            result: Kết quả
        """
        message = f"Người dùng: {user}, Hành động: {action}"
        if target:
            message += f", Đối tượng: {target}"
        if result:
            message += f", Kết quả: {result}"
        
        self.log_info(message, user=user, **kwargs)
    
    def get_logger(self):
        """Lấy đối tượng logger gốc"""
        return self.logger
    
    def set_session_id(self, session_id: str):
        """
        Đặt ID phiên làm việc cho logger
        
        Args:
            session_id: ID phiên làm việc
        """
        # Thêm filter để bổ sung session_id vào tất cả các bản ghi
        class SessionFilter(logging.Filter):
            def __init__(self, session_id):
                super().__init__()
                self.session_id = session_id
            
            def filter(self, record):
                record.session_id = self.session_id
                return True
        
        # Xóa tất cả các filter hiện có
        for filter in self.logger.filters[:]:
            self.logger.removeFilter(filter)
        
        # Thêm filter mới
        self.logger.addFilter(SessionFilter(session_id))
    
    def query_logs(self, level: str = None, start_time: str = None, 
                  end_time: str = None, user: str = None, 
                  session_id: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Truy vấn log từ cơ sở dữ liệu
        
        Args:
            level: Mức độ log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            start_time: Thời gian bắt đầu (ISO format)
            end_time: Thời gian kết thúc (ISO format)
            user: Tên người dùng
            session_id: ID phiên làm việc
            limit: Số lượng bản ghi tối đa
            
        Returns:
            Danh sách các bản ghi log
        """
        db_path = get_config("logging.db_path", os.path.join(os.path.expanduser("~"), "QuangStation_Data", "logs.db"))
        
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Xây dựng truy vấn
            query = "SELECT * FROM system_logs WHERE 1=1"
            params = []
            
            if level:
                query += " AND level = ?"
                params.append(level)
            
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time)
            
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time)
            
            if user:
                query += " AND user = ?"
                params.append(user)
            
            if session_id:
                query += " AND session_id = ?"
                params.append(session_id)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            # Thực hiện truy vấn
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Chuyển đổi kết quả thành danh sách từ điển
            result = []
            for row in rows:
                result.append(dict(row))
            
            conn.close()
            return result
        except Exception as e:
            sys.stderr.write(f"Lỗi khi truy vấn log: {str(e)}\n")
            return []

def get_logger(module_name: str = None) -> QuangLogger:
    """
    Lấy logger cho module
    
    Args:
        module_name: Tên module
        
    Returns:
        Instance của QuangLogger
    """
    if module_name is None:
        # Lấy tên module gọi hàm này
        frame = sys._getframe(1)
        module_name = frame.f_globals.get('__name__', 'unknown')
    
    return QuangLogger.get_instance(module_name)

def log_system_info():
    """Ghi log thông tin hệ thống"""
    logger = get_logger("SystemInfo")
    
    try:
        # Thông tin hệ điều hành
        os_info = {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor()
        }
        
        # Thông tin Python
        python_info = {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "compiler": platform.python_compiler()
        }
        
        # Thông tin thời gian
        time_info = {
            "start_time": datetime.datetime.now().isoformat(),
            "timezone": datetime.datetime.now().astimezone().tzinfo.tzname(None)
        }
        
        # Ghi log
        logger.log_info(f"Hệ điều hành: {json.dumps(os_info, ensure_ascii=False)}")
        logger.log_info(f"Python: {json.dumps(python_info, ensure_ascii=False)}")
        logger.log_info(f"Thời gian: {json.dumps(time_info, ensure_ascii=False)}")
        
        return True
    except Exception as e:
        logger.log_error(f"Lỗi khi ghi log thông tin hệ thống: {str(e)}", include_traceback=True)
        return False

def setup_exception_logging():
    """Thiết lập xử lý ngoại lệ không bắt được"""
    logger = get_logger("UncaughtException")
    
    def exception_handler(exc_type, exc_value, exc_traceback):
        """Xử lý ngoại lệ không bắt được"""
        if issubclass(exc_type, KeyboardInterrupt):
            # Không ghi log cho KeyboardInterrupt
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # Ghi log ngoại lệ
        logger.log_critical("Ngoại lệ không bắt được:", include_traceback=False)
        logger.log_critical(f"Loại: {exc_type.__name__}", include_traceback=False)
        logger.log_critical(f"Giá trị: {exc_value}", include_traceback=False)
        
        # Ghi traceback
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        for line in tb_lines:
            logger.log_critical(line.rstrip(), include_traceback=False)
    
    # Đặt exception handler
    sys.excepthook = exception_handler
