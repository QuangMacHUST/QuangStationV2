#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module xử lý hình ảnh y tế cho QuangStation V2.
Cung cấp các lớp và hàm để tải, xử lý và hiển thị ảnh CT/MRI/PET/SPECT.
"""

from quangstation.image_processing.image_loader import ImageLoader
from quangstation.image_processing.segmentation import (
    auto_segment, 
    threshold_segmentation, 
    edge_based_segmentation,
    region_growing,
    watershed_segmentation,
    create_mask_from_contours,
    contours_from_mask
)

__all__ = [
    # Lớp tải ảnh
    "ImageLoader",
    
    # Các hàm phân vùng ảnh
    "auto_segment",
    "threshold_segmentation",
    "edge_based_segmentation",
    "region_growing",
    "watershed_segmentation",
    "create_mask_from_contours",
    "contours_from_mask"
]
