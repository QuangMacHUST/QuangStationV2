#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Công cụ tự động cập nhật các import sau khi tái cấu trúc thư mục
"""

import os
import re
import argparse
from pathlib import Path

# Ánh xạ từ cấu trúc cũ sang cấu trúc mới
IMPORT_MAPPING = {
    # Core modules
    r'from quangstation\.data_models': r'from quangstation.core.data_models',
    r'from quangstation\.io': r'from quangstation.core.io',
    r'from quangstation\.utils': r'from quangstation.core.utils',
    
    # Clinical modules
    r'from quangstation\.data_management': r'from quangstation.clinical.data_management',
    r'from quangstation\.contouring': r'from quangstation.clinical.contouring',
    r'from quangstation\.planning': r'from quangstation.clinical.planning',
    r'from quangstation\.dose_calculation': r'from quangstation.clinical.dose_calculation',
    r'from quangstation\.optimization': r'from quangstation.clinical.optimization',
    r'from quangstation\.plan_evaluation': r'from quangstation.clinical.plan_evaluation',
    
    # Service modules
    r'from quangstation\.image_processing': r'from quangstation.services.image_processing',
    r'from quangstation\.integration': r'from quangstation.services.integration',
    
    # Quality modules
    r'from quangstation\.quality_assurance': r'from quangstation.quality.quality_assurance',
    r'from quangstation\.reporting': r'from quangstation.quality.reporting',
    
    # Import statements without 'from'
    r'import quangstation\.data_models': r'import quangstation.core.data_models',
    r'import quangstation\.io': r'import quangstation.core.io',
    r'import quangstation\.utils': r'import quangstation.core.utils',
    r'import quangstation\.data_management': r'import quangstation.clinical.data_management',
    r'import quangstation\.contouring': r'import quangstation.clinical.contouring',
    r'import quangstation\.planning': r'import quangstation.clinical.planning',
    r'import quangstation\.dose_calculation': r'import quangstation.clinical.dose_calculation',
    r'import quangstation\.optimization': r'import quangstation.clinical.optimization',
    r'import quangstation\.plan_evaluation': r'import quangstation.clinical.plan_evaluation',
    r'import quangstation\.image_processing': r'import quangstation.services.image_processing',
    r'import quangstation\.quality_assurance': r'import quangstation.quality.quality_assurance',
    r'import quangstation\.reporting': r'import quangstation.quality.reporting',
}

def update_imports_in_file(filepath):
    """Cập nhật các import trong một file"""
    print(f"Đang xử lý: {filepath}")
    
    # Đọc nội dung file
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Tạo bản sao nội dung gốc để kiểm tra thay đổi
    original_content = content
    
    # Áp dụng các quy tắc thay thế
    for old_pattern, new_pattern in IMPORT_MAPPING.items():
        content = re.sub(old_pattern, new_pattern, content)
    
    # Nếu nội dung đã thay đổi, ghi lại file
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    
    return False

def process_directory(directory):
    """Xử lý tất cả file Python trong thư mục"""
    modified_count = 0
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                if update_imports_in_file(filepath):
                    modified_count += 1
    
    return modified_count

def parse_arguments():
    parser = argparse.ArgumentParser(description='Cập nhật đường dẫn import cho tái cấu trúc QuangStation')
    parser.add_argument('--dir', default='quangstation', help='Thư mục gốc để xử lý')
    return parser.parse_args()

def main():
    args = parse_arguments()
    directory = args.dir
    
    if not os.path.isdir(directory):
        print(f"Lỗi: {directory} không phải là thư mục hợp lệ")
        return
    
    print(f"Bắt đầu cập nhật import trong thư mục: {directory}")
    modified_count = process_directory(directory)
    print(f"Hoàn thành! Đã cập nhật {modified_count} file")

if __name__ == "__main__":
    main() 