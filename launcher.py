#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Launcher cho QuangStation V2 - Hệ thống Lập kế hoạch Xạ trị Mã nguồn Mở
Phát triển bởi Mạc Đăng Quang

File này giúp khởi chạy QuangStation V2 từ thư mục gốc của dự án.
"""

import os
import sys
import argparse
import importlib
import logging
import tkinter as tk
from tkinter import messagebox
from threading import Thread
from datetime import datetime
import traceback

# Set up UTF-8 encoding for console output
if sys.platform == 'win32':
    # Force UTF-8 encoding on Windows
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Thiết lập logging cơ bản
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(stream=sys.stdout)
    ]
)

logger = logging.getLogger("Launcher")

# Danh sách các thư viện bắt buộc
REQUIRED_PACKAGES = [
    'numpy', 'matplotlib', 'pydicom', 'pillow', 'vtk', 'scipy', 
    'pandas', 'reportlab', 'tk', 'docx', 'torch'
]

def check_dependencies():
    """
    Kiểm tra các thư viện phụ thuộc
    
    Returns:
        bool: True nếu tất cả thư viện tồn tại, False nếu không
    """
    logger.info("Đang kiểm tra các thư viện phụ thuộc...")
    missing_packages = []
    
    for package in REQUIRED_PACKAGES:
        try:
            importlib.import_module(package)
            logger.debug(f"- {package}: OK")
        except ImportError:
            missing_packages.append(package)
            logger.error(f"- {package}: THIẾU")
    
    if missing_packages:
        logger.error(f"Thiếu các thư viện: {', '.join(missing_packages)}")
        logger.info("Vui lòng cài đặt các thư viện thiếu bằng lệnh:")
        logger.info(f"pip install {' '.join(missing_packages)}")
        return False
    
    logger.info("Tất cả thư viện phụ thuộc đã được cài đặt.")
    return True

def check_system_config():
    """
    Kiểm tra cấu hình hệ thống
    
    Returns:
        bool: True nếu hệ thống đáp ứng yêu cầu, False nếu không
    """
    import platform
    
    logger.info("Đang kiểm tra cấu hình hệ thống...")
    
    # Kiểm tra hệ điều hành
    os_name = platform.system()
    os_version = platform.version()
    logger.info(f"Hệ điều hành: {os_name} {os_version}")
    
    # Kiểm tra Python
    python_version = platform.python_version()
    logger.info(f"Phiên bản Python: {python_version}")
    
    if sys.version_info < (3, 8):
        logger.warning("Phiên bản Python khuyến nghị là 3.8 trở lên")
    
    # Kiểm tra bộ nhớ
    try:
        import psutil
        memory = psutil.virtual_memory()
        memory_gb = memory.total / (1024 ** 3)
        logger.info(f"Bộ nhớ RAM: {memory_gb:.2f} GB")
        
        if memory_gb < 8:
            logger.warning("Khuyến nghị: Bộ nhớ RAM ít nhất 8GB")
    except ImportError:
        logger.info("Không thể kiểm tra thông tin bộ nhớ RAM (psutil không được cài đặt)")
    
    # Kiểm tra GPU (nếu có)
    try:
        import torch
        gpu_available = torch.cuda.is_available()
        if gpu_available:
            gpu_count = torch.cuda.device_count()
            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f"GPU: {gpu_name} (x{gpu_count})")
        else:
            logger.info("GPU: Không có")
    except:
        logger.info("Không thể kiểm tra thông tin GPU (PyTorch không được cài đặt hoặc không hoạt động)")
    
    return True

def setup_logging(args):
    """
    Thiết lập hệ thống logging
    
    Args:
        args: Tham số dòng lệnh đã phân tích
    """
    # Xác định cấp độ logging
    if args.debug:
        log_level = logging.DEBUG
    elif args.quiet:
        log_level = logging.ERROR
    else:
        log_level = logging.INFO
    
    # Thiết lập lại cấp độ cho logger gốc
    logger.setLevel(log_level)
    
    # Tạo thư mục logs nếu chưa tồn tại
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Tạo tên file log dựa trên thời gian
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f'quangstation_{timestamp}.log')
    
    # Tạo file handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(log_level)
    
    # Định dạng log
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # Thêm handler vào logger
    logger.addHandler(file_handler)
    
    # Ghi thông tin phiên
    logger.info("=" * 50)
    logger.info("Khoi dong QuangStation V2")
    logger.info(f"Thoi gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Duong dan: {os.path.dirname(os.path.abspath(__file__))}")
    logger.info("=" * 50)
    
    logger.info(f"Da thiet lap log tai: {log_file}")

def parse_arguments():
    """
    Phân tích các tham số dòng lệnh
    
    Returns:
        argparse.Namespace: Các tham số đã phân tích
    """
    parser = argparse.ArgumentParser(description='QuangStation V2 - Hệ thống Lập kế hoạch Xạ trị Mã nguồn Mở')
    
    # Các tham số chung
    parser.add_argument('--version', action='store_true', help='Hiển thị phiên bản và thoát')
    parser.add_argument('--debug', action='store_true', help='Chạy ở chế độ debug (chi tiết)')
    parser.add_argument('--quiet', action='store_true', help='Chạy ở chế độ yên lặng (chỉ hiện lỗi)')
    parser.add_argument('--no-splash', action='store_true', help='Không hiển thị màn hình splash')
    
    # Các tham số chức năng
    parser.add_argument('--skip-checks', action='store_true', help='Bỏ qua kiểm tra thư viện và hệ thống')
    parser.add_argument('--data-dir', type=str, help='Thư mục lưu trữ dữ liệu')
    parser.add_argument('--config', type=str, help='Đường dẫn đến file cấu hình')
    parser.add_argument('--lang', type=str, choices=['vi', 'en'], default='vi', help='Ngôn ngữ (vi hoặc en)')
    
    return parser.parse_args()

def run_checks_thread(args):
    """
    Chạy các kiểm tra hệ thống trên luồng riêng
    
    Args:
        args: Tham số dòng lệnh đã phân tích
    """
    # Kiểm tra thư viện và hệ thống
    if not args.skip_checks:
        check_dependencies()
        check_system_config()

def get_resources_path(subdir=None):
    """
    Get the path to the resources directory
    
    Args:
        subdir: Optional subdirectory within resources
        
    Returns:
        str: Absolute path to the resources directory or subdirectory
    """
    base_path = os.path.dirname(os.path.abspath(__file__))
    resources_path = os.path.join(base_path, 'resources')
    
    if subdir:
        return os.path.join(resources_path, subdir)
    return resources_path

def run_application(root, args):
    """
    Khởi chạy ứng dụng chính
    
    Args:
        root: Cửa sổ Tkinter gốc
        args: Tham số dòng lệnh đã phân tích
    """
    try:
        logger.info("Đang khởi động QuangStation V2...")
        
        # Add the project root to Python path
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Nạp module chính
        import quangstation
        
        # Hiện thông tin phiên bản
        if hasattr(quangstation, 'show_version'):
            quangstation.show_version()
        else:
            logger.info("QuangStation V2 - Version 2.0.0")
        
        # Thiết lập ngôn ngữ từ tham số dòng lệnh
        if hasattr(quangstation, 'set_language'):
            quangstation.set_language(args.lang)
        
        # Thiết lập thư mục dữ liệu nếu được chỉ định
        if args.data_dir and hasattr(quangstation, 'set_data_directory'):
            quangstation.set_data_directory(args.data_dir)
        
        # Nạp cấu hình nếu được chỉ định
        if args.config and hasattr(quangstation, 'load_config'):
            quangstation.load_config(args.config)
        
        # Khởi chạy ứng dụng
        logger.info("Đang khởi chạy giao diện người dùng...")
        # Set the root window to be visible
        root.deiconify()
        
        if hasattr(quangstation, 'run_application'):
            quangstation.run_application(root)
        else:
            # Fallback to directly importing and running the main app
            from quangstation.__main__ import MainApp
            MainApp(root)
            root.mainloop()
        
    except Exception as error:
        logger.error(f"Lỗi khi khởi động: {str(error)}")
        if args.debug:
            traceback.print_exc()
        messagebox.showerror("Lỗi khởi động", 
                             f"Không thể khởi động QuangStation V2:\n{str(error)}\n\nVui lòng kiểm tra file log để biết thêm chi tiết.")

def main():
    """
    Hàm chính để khởi chạy ứng dụng
    """
    try:
        # Phân tích tham số dòng lệnh
        args = parse_arguments()

        # Hiển thị phiên bản nếu được yêu cầu
        if args.version:
            print("QuangStation V2 - Version 2.0.0")
            print("Author: Mac Dang Quang")
            print("License: MIT")
            return 0

        # Thiết lập logging
        setup_logging(args)

        # Hiển thị ASCII art nếu không tắt splash
        if not args.no_splash:
            print("=" * 80)
            print("               ____                             _____ _        _   _             ")
            print("              / __ \\                           / ____| |      | | (_)            ")
            print("             | |  | |_   _  __ _ _ __   __ _  | (___ | |_ __ _| |_ _  ___  _ __  ")
            print("             | |  | | | | |/ _` | '_ \\ / _` |  \\___ \\| __/ _` | __| |/ _ \\| '_ \\ ")
            print("             | |__| | |_| | (_| | | | | (_| |  ____) | || (_| | |_| | (_) | | | |")
            print("              \\___\\_\\\\__,_|\\__,_|_| |_|\\__, | |_____/ \\__\\__,_|\\__|_|\\___/|_| |_|")
            print("                                        __/ |                                    ")
            print("                                       |___/                                     ")
            print("=" * 80)
            print("                    QuangStation V2 - Lap ke hoach Xa tri")
            print("=" * 80)

        # Tạo cửa sổ gốc
        root = tk.Tk()
        root.withdraw()  # Ẩn cửa sổ chính cho đến khi kiểm tra xong

        # Chạy các kiểm tra trong luồng riêng
        checks_thread = Thread(target=run_checks_thread, args=(args,))
        checks_thread.daemon = True
        checks_thread.start()

        # Chạy ứng dụng chính
        run_application(root, args)
    except Exception as e:
        logger.error(f"Lỗi khi khởi động: {str(e)}")
        if args.debug:
            traceback.print_exc()

if __name__ == "__main__":
    main()