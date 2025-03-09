#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
QuangStation V2 - Hệ thống Lập kế hoạch Xạ trị Mã nguồn Mở
"""

__version__ = "2.0.0"
__author__ = "Mạc Đăng Quang"
__email__ = "quangmacdang@gmail.com"

# Kiểm tra các dependency cần thiết
import importlib.util
import sys

required_packages = [
    "numpy",
    "matplotlib",
    "pydicom",
    "scipy",
    "vtk",
    "opencv-python",
]

for package in required_packages:
    # Đổi opencv-python thành opencv để kiểm tra
    pkg_name = package if package != "opencv-python" else "cv2"
    
    if importlib.util.find_spec(pkg_name) is None:
        print(f"Cảnh báo: Không tìm thấy package {package}. Vui lòng cài đặt bằng cách chạy: pip install {package}")

# Kiểm tra tkinter riêng vì là module tích hợp
try:
    import tkinter
except ImportError:
    print("Cảnh báo: Không tìm thấy module tkinter. Vui lòng cài đặt Python với tùy chọn tkinter.")

# Import các module chính
from quangstation.utils.logging import setup_exception_logging

# Thiết lập xử lý ngoại lệ toàn cục
setup_exception_logging()

# Thông tin về phiên bản
def show_version():
    """Hiển thị thông tin phiên bản của QuangStation V2"""
    version_info = {
        "name": "QuangStation V2",
        "version": __version__,
        "author": __author__,
        "email": __email__,
        "description": "Hệ thống Lập kế hoạch Xạ trị Mã nguồn Mở"
    }
    
    for key, value in version_info.items():
        print(f"{key}: {value}")
    
    return version_info
