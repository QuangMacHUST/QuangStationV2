#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module vẽ đường viền (contouring) cho QuangStation V2.
Cung cấp các công cụ vẽ đường viền, phân đoạn tự động và quản lý thư viện cơ quan.
"""

from quangstation.contouring.contour_tools import ContourTools
from quangstation.contouring.auto_segmentation import AutoSegmentation, SegmentationModel, UNetModel
from quangstation.contouring.organ_library import OrganLibrary, OrganProperties, get_organ_library

__all__ = [
    'ContourTools',         # Công cụ vẽ đường viền
    'AutoSegmentation',     # Phân đoạn tự động
    'SegmentationModel',    # Lớp cơ sở cho mô hình phân đoạn
    'UNetModel',            # Mô hình UNet
    'OrganLibrary',         # Thư viện cơ quan
    'OrganProperties',      # Thuộc tính cơ quan
    'get_organ_library'     # Hàm helper để lấy instance của thư viện cơ quan
]

def get_auto_segmentation():
    """
    Tạo và trả về một instance của AutoSegmentation.
    
    Returns:
        AutoSegmentation: Instance của lớp AutoSegmentation
    """
    return AutoSegmentation()

def create_contour_tools(image_data, spacing=(1.0, 1.0, 1.0), origin=(0.0, 0.0, 0.0), direction=(1,0,0,0,1,0,0,0,1)):
    """
    Tạo và trả về một instance của ContourTools.
    
    Args:
        image_data: Dữ liệu ảnh 3D (numpy array)
        spacing: Khoảng cách giữa các pixel (mm)
        origin: Điểm gốc của ảnh (mm)
        direction: Ma trận hướng
        
    Returns:
        ContourTools: Instance của lớp ContourTools
    """
    return ContourTools(image_data, spacing, origin, direction)

# Thêm hàm helper vào danh sách export
__all__.extend(['get_auto_segmentation', 'create_contour_tools'])
