#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module cung cấp chức năng nhập kế hoạch xạ trị từ định dạng DICOM.
"""

import os
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

# Sử dụng module external_integration để quản lý thư viện bên ngoài một cách nhất quán
from quangstation.utils.external_integration import get_module
from quangstation.utils.logging import get_logger
from quangstation.io.dicom_parser import DICOMParser

logger = get_logger(__name__)

# Lấy module pydicom từ external_integration
pydicom = get_module("pydicom")
if not pydicom:
    logger.error("Không thể import pydicom. Chức năng nhập DICOM sẽ không hoạt động.")

def import_plan_from_dicom(dicom_dir: str) -> Dict[str, Any]:
    """
    Nhập kế hoạch xạ trị từ định dạng DICOM (RT Plan, RT Dose, RT Struct)
    
    Args:
        dicom_dir: Thư mục chứa file DICOM
        
    Returns:
        Dict[str, Any]: Dữ liệu kế hoạch xạ trị
    """
    if not pydicom:
        logger.error("Không thể nhập DICOM vì thiếu thư viện pydicom")
        return {}
        
    logger.info(f"Đang nhập kế hoạch từ DICOM trong thư mục {dicom_dir}")
    
    # Tạo parser để phân tích dữ liệu DICOM
    parser = DICOMParser(dicom_dir)
    
    # Trích xuất thông tin bệnh nhân
    patient_info = parser.extract_patient_info()
    
    # Trích xuất dữ liệu hình ảnh
    image_data = None
    image_metadata = {}
    if parser.ct_files:
        image_data, image_metadata = parser.extract_image_volume(modality='CT')
    elif parser.mri_files:
        image_data, image_metadata = parser.extract_image_volume(modality='MR')
    
    # Trích xuất dữ liệu cấu trúc
    structures = {}
    if parser.rt_struct:
        structures = parser.extract_rt_struct()
    
    # Trích xuất dữ liệu kế hoạch
    plan_data = {}
    if parser.rt_plan:
        plan_data = parser.extract_rt_plan()
    
    # Trích xuất dữ liệu liều
    dose_data = None
    dose_metadata = {}
    if parser.rt_dose:
        dose_data, dose_metadata = parser.extract_rt_dose()
    
    # Tổng hợp dữ liệu
    result = {
        'patient': patient_info,
        'image': {
            'data': image_data,
            'metadata': image_metadata
        },
        'structures': structures,
        'plan': plan_data,
        'dose': {
            'data': dose_data,
            'metadata': dose_metadata
        }
    }
    
    logger.info(f"Nhập kế hoạch DICOM thành công.")
    
    return result 