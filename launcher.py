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
import time
from datetime import datetime

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
        logger.info(f"CUDA khả dụng: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
            logger.info(f"Số lượng GPU: {torch.cuda.device_count()}")
    except ImportError:
        logger.info("Không thể kiểm tra thông tin GPU (torch không được cài đặt)")
    
    return True

def setup_logging(args):
    """
    Thiết lập logging dựa trên các tham số dòng lệnh
    
    Args:
        args: Các tham số dòng lệnh
    """
    log_level = logging.INFO
    
    if args.debug:
        log_level = logging.DEBUG
    elif args.quiet:
        log_level = logging.WARNING
    
    # Tạo thư mục log nếu không tồn tại
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Tên file log dựa trên thời gian hiện tại
    log_file = os.path.join(log_dir, f"quangstation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    # Thiết lập lại logging
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Xóa tất cả handlers hiện tại
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Thêm handlers mới
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(file_handler)
    
    # Chỉ thêm console handler nếu không ở chế độ yên lặng
    if not args.quiet:
        console_handler = logging.StreamHandler(stream=sys.stdout)
        console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        root_logger.addHandler(console_handler)
    
    logger.info(f"Đã thiết lập log tại: {log_file}")

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
    
    # Các tham số chức năng
    parser.add_argument('--skip-checks', action='store_true', help='Bỏ qua kiểm tra thư viện và hệ thống')
    parser.add_argument('--data-dir', type=str, help='Thư mục lưu trữ dữ liệu')
    parser.add_argument('--config', type=str, help='Đường dẫn đến file cấu hình')
    parser.add_argument('--lang', type=str, choices=['vi', 'en'], default='vi', help='Ngôn ngữ (vi hoặc en)')
    
    return parser.parse_args()

def main():
    """
    Hàm chính để khởi chạy ứng dụng
    """
    # Thêm thư mục gốc vào đường dẫn Python
    root_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, root_dir)
    
    # Phân tích tham số dòng lệnh
    args = parse_arguments()
    
    # Thiết lập logging
    setup_logging(args)
    
    # Hiển thị phiên bản và thoát nếu được yêu cầu
    if args.version:
        try:
            import quangstation
            quangstation.show_version()
        except:
            logger.info("QuangStation V2 - Phiên bản 2.0.0")
        return
    
    # Bắt đầu đo thời gian khởi động
    start_time = time.time()
    
    # Hiển thị banner
    print("=" * 80)
    print("                    QuangStation V2 - Lập kế hoạch Xạ trị")
    print("                       Mã nguồn mở - Phát triển tại Việt Nam")
    print("=" * 80)
    
    # Kiểm tra thư viện và hệ thống
    if not args.skip_checks:
        if not check_dependencies():
            logger.error("Không thể khởi động do thiếu thư viện phụ thuộc")
            return
        
        check_system_config()
    
    # Cố gắng nạp và khởi chạy ứng dụng
    try:
        logger.info("Đang khởi động QuangStation V2...")
        
        # Nạp module chính
        import quangstation
        
        # Hiện thông tin phiên bản
        quangstation.show_version()
        
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
        quangstation.run_application()
        
    except Exception as error:
        logger.error(f"Lỗi khi khởi động: {str(error)}")
        if args.debug:
            import traceback
            traceback.print_exc()
    
    # Hiển thị thời gian khởi động
    elapsed_time = time.time() - start_time
    logger.info(f"Thời gian khởi động: {elapsed_time:.2f} giây")

if __name__ == "__main__":
    main() 