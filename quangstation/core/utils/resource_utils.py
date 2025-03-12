#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Các hàm tiện ích để xử lý tài nguyên (resources) trong QuangStation V2
"""

import os
import logging

logger = logging.getLogger(__name__)

def get_resources_path(subdir=None):
    """
    Trả về đường dẫn đến thư mục resources
    
    Args:
        subdir (str, optional): Thư mục con trong resources (nếu có)
        
    Returns:
        str: Đường dẫn đến thư mục resources hoặc thư mục con của nó
    """
    # Đường dẫn tới thư mục gốc của dự án
    project_root = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))))
    
    # Thư mục resources nằm trong thư mục gốc
    resources_dir = os.path.join(project_root, "resources")
    
    # Tạo thư mục nếu chưa tồn tại
    if not os.path.exists(resources_dir):
        logger.info("Tạo thư mục resources: %s", resources_dir)
        os.makedirs(resources_dir, exist_ok=True)
        
        # Tạo thư mục con cho ngôn ngữ
        lang_dir = os.path.join(resources_dir, "lang")
        if not os.path.exists(lang_dir):
            os.makedirs(lang_dir, exist_ok=True)
    
    # Trả về thư mục con nếu được chỉ định
    if subdir:
        subdir_path = os.path.join(resources_dir, subdir)
        # Tạo thư mục con nếu chưa tồn tại
        if not os.path.exists(subdir_path):
            logger.info("Tạo thư mục con: %s", subdir_path)
            os.makedirs(subdir_path, exist_ok=True)
        return subdir_path
    
    return resources_dir

def get_icons_path():
    """
    Trả về đường dẫn đến thư mục chứa biểu tượng
    
    Returns:
        str: Đường dẫn đến thư mục icons
    """
    return get_resources_path("icons")

def get_templates_path():
    """
    Trả về đường dẫn đến thư mục chứa các mẫu báo cáo
    
    Returns:
        str: Đường dẫn đến thư mục templates
    """
    return get_resources_path("templates")

def get_models_path():
    """
    Trả về đường dẫn đến thư mục chứa các mô hình AI
    
    Returns:
        str: Đường dẫn đến thư mục models
    """
    return get_resources_path("models")

def get_lang_path():
    """
    Trả về đường dẫn đến thư mục chứa các file ngôn ngữ
    
    Returns:
        str: Đường dẫn đến thư mục lang
    """
    return get_resources_path("lang")

def get_data_path():
    """
    Trả về đường dẫn đến thư mục chứa dữ liệu tham chiếu
    
    Returns:
        str: Đường dẫn đến thư mục data
    """
    return get_resources_path("data")

def get_file_path(resource_type, filename):
    """
    Trả về đường dẫn đến một file dựa trên loại tài nguyên và tên file
    
    Args:
        resource_type (str): Loại tài nguyên (icons, templates, models, lang, data)
        filename (str): Tên file
        
    Returns:
        str: Đường dẫn đến file
    """
    resource_dirs = {
        "icons": get_icons_path(),
        "templates": get_templates_path(),
        "models": get_models_path(),
        "lang": get_lang_path(),
        "data": get_data_path()
    }
    
    if resource_type not in resource_dirs:
        logger.warning("Loại tài nguyên không hợp lệ: %s", resource_type)
        return None
    
    return os.path.join(resource_dirs[resource_type], filename)
