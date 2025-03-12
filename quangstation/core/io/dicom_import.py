#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module cung cấp chức năng nhập kế hoạch xạ trị từ định dạng DICOM.
"""

from typing import Dict, Any
# Sử dụng module external_integration để quản lý thư viện bên ngoài một cách nhất quán
from quangstation.core.utils.external_integration import get_module
from quangstation.core.utils.logging import get_logger
from quangstation.core.io.dicom_parser import DICOMParser

logger = get_logger(__name__)

# Lấy module pydicom từ external_integration
pydicom = get_module("pydicom")
if not pydicom:
    logger.error("Không thể import pydicom. Chức năng nhập DICOM sẽ không hoạt động.")

def import_plan_from_dicom(dicom_dir: str, modality_filters: Dict[str, bool] = None) -> Dict[str, Any]:
    """
    Nhập kế hoạch xạ trị từ định dạng DICOM (RT Plan, RT Dose, RT Struct)
    
    Args:
        dicom_dir: Thư mục chứa file DICOM
        modality_filters: Bộ lọc các loại dữ liệu cần nhập, ví dụ: {'CT': True, 'MR': False}
        
    Returns:
        Dict[str, Any]: Dữ liệu kế hoạch xạ trị
    """
    if not pydicom:
        logger.error("Không thể nhập DICOM vì thiếu thư viện pydicom")
        return {}
        
    logger.info(f"Đang nhập kế hoạch từ DICOM trong thư mục {dicom_dir}")
    
    # Xử lý bộ lọc modality
    if modality_filters is None:
        modality_filters = {
            'CT': True,
            'MR': True,
            'RTSTRUCT': True,
            'RTPLAN': True,
            'RTDOSE': True
        }
    
    # Ghi log các loại dữ liệu được chọn
    logger.info("Các loại dữ liệu được chọn để nhập: %s", 
               ', '.join([k for k, v in modality_filters.items() if v]))
    
    # Tạo parser để phân tích dữ liệu DICOM
    parser = DICOMParser(dicom_dir)
    
    # Trích xuất thông tin bệnh nhân
    patient_info = parser.extract_patient_info()
    
    # Trích xuất dữ liệu hình ảnh
    image_data = None
    image_metadata = {}
    
    if modality_filters.get('CT', True) and parser.ct_files:
        image_data, image_metadata = parser.extract_image_volume(modality='CT')
        logger.info("Đã nhập dữ liệu CT")
    elif modality_filters.get('MR', True) and parser.mri_files:
        image_data, image_metadata = parser.extract_image_volume(modality='MR')
        logger.info("Đã nhập dữ liệu MR")
    
    # Trích xuất dữ liệu cấu trúc
    structures = {}
    if modality_filters.get('RTSTRUCT', True) and parser.rt_struct:
        structures = parser.extract_rt_structure()
        logger.info("Đã nhập dữ liệu cấu trúc RT")
    
    # Trích xuất dữ liệu kế hoạch
    plan_data = {}
    if modality_filters.get('RTPLAN', True) and parser.rt_plan:
        plan_data = parser.extract_rt_plan()
        logger.info("Đã nhập dữ liệu kế hoạch xạ trị")
    
    # Trích xuất dữ liệu liều
    dose_data = None
    dose_metadata = {}
    if modality_filters.get('RTDOSE', True) and parser.rt_dose:
        dose_data, dose_metadata = parser.extract_rt_dose()
        logger.info("Đã nhập dữ liệu liều xạ")
    
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
    
    logger.info("Nhập kế hoạch DICOM thành công.")
    
    return result