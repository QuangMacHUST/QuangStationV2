"""
Quản lý cấu hình toàn cục cho hệ thống QuangStation V2
"""

import os
import json
import platform
from typing import Dict, Any

class GlobalConfig:
    """Lớp quản lý cấu hình toàn cục"""
    
    _instance = None
    _config_path = os.path.join(os.path.expanduser("~"), ".quangstation", "config.json")
    
    def __new__(cls):
        """Singleton pattern"""
        if not cls._instance:
            cls._instance = super(GlobalConfig, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Khởi tạo cấu hình"""
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Tải cấu hình từ file"""
        # Tạo thư mục cấu hình nếu chưa tồn tại
        os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
        
        # Cấu hình mặc định
        default_config = {
            "version": "2.0.0",
            "system": {
                "os": platform.system(),
                "os_version": platform.version(),
                "python_version": platform.python_version()
            },
            "paths": {
                "workspace": os.path.join(os.path.expanduser("~"), "QuangStation"),
                "dicom_import": os.path.join(os.path.expanduser("~"), "QuangStation", "dicom_import"),
                "export": os.path.join(os.path.expanduser("~"), "QuangStation", "export")
            },
            "logging": {
                "level": "INFO",
                "max_file_size": 10 * 1024 * 1024,  # 10 MB
                "backup_count": 5
            },
            "dose_calculation": {
                "default_algorithm": "CCC",
                "grid_resolution": 2.5  # mm
            },
            "ui": {
                "theme": "default",
                "language": "vi"
            }
        }
        
        # Nếu file cấu hình chưa tồn tại, tạo mới
        if not os.path.exists(self._config_path):
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
            return default_config
        
        # Đọc file cấu hình
        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                
            # Merge cấu hình người dùng với cấu hình mặc định
            return {**default_config, **user_config}
        except json.JSONDecodeError:
            return default_config
    
    def get(self, key: str, default=None):
        """Lấy giá trị cấu hình"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """Đặt giá trị cấu hình"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        
        # Lưu lại file cấu hình
        with open(self._config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)
    
    def reset_to_default(self):
        """Đặt lại cấu hình về mặc định"""
        default_config = {
            "version": "2.0.0",
            "system": {
                "os": platform.system(),
                "os_version": platform.version(),
                "python_version": platform.python_version()
            },
            "paths": {
                "workspace": os.path.join(os.path.expanduser("~"), "QuangStation"),
                "dicom_import": os.path.join(os.path.expanduser("~"), "QuangStation", "dicom_import"),
                "export": os.path.join(os.path.expanduser("~"), "QuangStation", "export")
            },
            "logging": {
                "level": "INFO",
                "max_file_size": 10 * 1024 * 1024,
                "backup_count": 5
            },
            "dose_calculation": {
                "default_algorithm": "CCC",
                "grid_resolution": 2.5
            },
            "ui": {
                "theme": "default",
                "language": "vi"
            }
        }
        
        self.config = default_config
        
        with open(self._config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)

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