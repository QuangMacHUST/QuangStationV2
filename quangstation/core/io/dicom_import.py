#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module cung cấp chức năng nhập kế hoạch xạ trị từ định dạng DICOM.

Hỗ trợ nhập các loại dữ liệu:
- CT/MRI/PET: Dữ liệu hình ảnh 3D
- RT Structure: Dữ liệu contour của các cấu trúc giải phẫu
- RT Plan: Dữ liệu kế hoạch xạ trị
- RT Dose: Dữ liệu phân bố liều xạ trị

Module này cung cấp các hàm:
- import_plan_from_dicom: Nhập toàn bộ kế hoạch xạ trị từ thư mục DICOM
- verify_dicom_compatibility: Kiểm tra tính tương thích của dữ liệu DICOM
"""

import os
import time
import traceback
from typing import Dict, Any, Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor

# Sử dụng module external_integration để quản lý thư viện bên ngoài một cách nhất quán
from quangstation.core.utils.external_integration import get_module
from quangstation.core.utils.logging import get_logger
from quangstation.core.utils.dicom_error_handler import handle_dicom_error, DICOMError, DICOMErrorCodes, validate_dicom_directory
from quangstation.core.io.dicom_parser import DICOMParser
from quangstation.core.data_models.image_data import ImageData
from quangstation.core.data_models.structure_data import StructureSet
from quangstation.core.data_models.plan_data import PlanConfig
from quangstation.core.data_models.dose_data import DoseData

logger = get_logger(__name__)

# Lấy module pydicom từ external_integration
pydicom = get_module("pydicom")
if not pydicom:
    logger.error("Không thể import pydicom. Chức năng nhập DICOM sẽ không hoạt động.")

@handle_dicom_error
def import_plan_from_dicom(dicom_dir: str, modality_filters: Dict[str, bool] = None, 
                          progress_callback = None) -> Dict[str, Any]:
    """
    Nhập kế hoạch xạ trị từ định dạng DICOM (RT Plan, RT Dose, RT Struct)
    
    Hàm này sẽ quét thư mục DICOM, phân loại các file theo loại dữ liệu,
    và nhập tất cả dữ liệu liên quan đến kế hoạch xạ trị.
    
    Args:
        dicom_dir: Thư mục chứa file DICOM
        modality_filters: Bộ lọc các loại dữ liệu cần nhập, ví dụ: {'CT': True, 'MR': False}
        progress_callback: Hàm callback để cập nhật tiến trình (nhận giá trị từ 0-100 và thông báo)
        
    Returns:
        Dict[str, Any]: Dữ liệu kế hoạch xạ trị với các khóa:
            - 'patient': Thông tin bệnh nhân
            - 'image': Dữ liệu hình ảnh (data và metadata)
            - 'structures': Dữ liệu cấu trúc
            - 'plan': Dữ liệu kế hoạch
            - 'dose': Dữ liệu liều (data và metadata)
    
    Raises:
        DICOMError: Khi có lỗi xảy ra trong quá trình nhập dữ liệu DICOM
    """
    if not pydicom:
        raise DICOMError(
            "Không thể nhập DICOM vì thiếu thư viện pydicom",
            DICOMErrorCodes.PARSING_ERROR
        )
    
    # Xác thực thư mục DICOM
    valid, errors = validate_dicom_directory(dicom_dir)
    if not valid:
        error_message = "\n".join(errors)
        raise DICOMError(
            f"Thư mục DICOM không hợp lệ: {error_message}",
            DICOMErrorCodes.INVALID_DIRECTORY
        )
        
    logger.info(f"Đang nhập kế hoạch từ DICOM trong thư mục {dicom_dir}")
    
    # Cập nhật tiến trình
    if progress_callback:
        progress_callback(5, "Đang chuẩn bị quét dữ liệu DICOM...")
    
    # Xử lý bộ lọc modality
    if modality_filters is None:
        modality_filters = {
            'ct': True,
            'mr': True,
            'pt': True,
            'rtplan': True,
            'rtdose': True,
            'rtstruct': True
        }
    
    # Chuẩn hóa khóa bộ lọc (viết thường)
    modality_filters = {k.lower(): v for k, v in modality_filters.items()}
    
    # Ghi log các loại dữ liệu được chọn
    logger.info("Các loại dữ liệu được chọn để nhập: %s", 
               ', '.join([k for k, v in modality_filters.items() if v]))
    
    # Cập nhật tiến trình
    if progress_callback:
        progress_callback(10, "Đang quét và phân tích dữ liệu DICOM...")
    
    # Tạo parser để phân tích dữ liệu DICOM
    try:
        parser = DICOMParser(dicom_dir)
    except Exception as error:
        logger.error(f"Lỗi khi tạo DICOMParser: {str(error)}")
        traceback.print_exc()
        raise DICOMError(
            f"Không thể phân tích dữ liệu DICOM: {str(error)}",
            DICOMErrorCodes.PARSING_ERROR,
            {"traceback": traceback.format_exc()}
        )
    
    # Cập nhật tiến trình
    if progress_callback:
        progress_callback(20, "Đang trích xuất thông tin bệnh nhân...")
    
    # Trích xuất thông tin bệnh nhân
    try:
        patient_info = parser.extract_patient_info()
        logger.info(f"Đã trích xuất thông tin bệnh nhân: {patient_info.get('patient_name', 'Unknown')}")
    except Exception as error:
        logger.error(f"Lỗi khi trích xuất thông tin bệnh nhân: {str(error)}")
        patient_info = {"patient_id": "Unknown", "patient_name": "Unknown"}
    
    # Khởi tạo biến kết quả
    result = {
        'patient': patient_info,
        'image': {
            'data': None,
            'metadata': {}
        },
        'structures': {},
        'plan': {},
        'dose': {
            'data': None,
            'metadata': {}
        }
    }
    
    # Sử dụng ThreadPoolExecutor để tải các dữ liệu song song
    import_tasks = []
    
    # Cập nhật tiến trình
    if progress_callback:
        progress_callback(30, "Đang tải dữ liệu hình ảnh...")
    
    # Trích xuất dữ liệu hình ảnh
    if modality_filters.get('ct', True) and parser.ct_files:
        try:
            image_data, image_metadata = parser.extract_image_volume(modality='CT')
            result['image']['data'] = image_data
            result['image']['metadata'] = image_metadata
            logger.info("Đã nhập dữ liệu CT")
        except Exception as error:
            logger.error(f"Lỗi khi trích xuất dữ liệu CT: {str(error)}")
            if progress_callback:
                progress_callback(35, f"Cảnh báo: Không thể trích xuất dữ liệu CT - {str(error)}")
    elif modality_filters.get('mr', True) and parser.mri_files:
        try:
            image_data, image_metadata = parser.extract_image_volume(modality='MR')
            result['image']['data'] = image_data
            result['image']['metadata'] = image_metadata
            logger.info("Đã nhập dữ liệu MR")
        except Exception as error:
            logger.error(f"Lỗi khi trích xuất dữ liệu MR: {str(error)}")
            if progress_callback:
                progress_callback(35, f"Cảnh báo: Không thể trích xuất dữ liệu MR - {str(error)}")
    elif modality_filters.get('pt', True) and parser.pet_files:
        try:
            image_data, image_metadata = parser.extract_image_volume(modality='PT')
            result['image']['data'] = image_data
            result['image']['metadata'] = image_metadata
            logger.info("Đã nhập dữ liệu PET")
        except Exception as error:
            logger.error(f"Lỗi khi trích xuất dữ liệu PET: {str(error)}")
            if progress_callback:
                progress_callback(35, f"Cảnh báo: Không thể trích xuất dữ liệu PET - {str(error)}")
    
    # Cập nhật tiến trình
    if progress_callback:
        progress_callback(50, "Đang tải dữ liệu cấu trúc...")
    
    # Trích xuất dữ liệu cấu trúc
    if modality_filters.get('rtstruct', True) and parser.rt_struct:
        try:
            structures = parser.extract_rt_structure()
            result['structures'] = structures
            logger.info(f"Đã nhập dữ liệu cấu trúc RT ({len(structures)} cấu trúc)")
        except Exception as error:
            logger.error(f"Lỗi khi trích xuất dữ liệu cấu trúc RT: {str(error)}")
            if progress_callback:
                progress_callback(55, f"Cảnh báo: Không thể trích xuất dữ liệu cấu trúc RT - {str(error)}")
    
    # Cập nhật tiến trình
    if progress_callback:
        progress_callback(70, "Đang tải dữ liệu kế hoạch xạ trị...")
    
    # Trích xuất dữ liệu kế hoạch
    if modality_filters.get('rtplan', True) and parser.rt_plan:
        try:
            plan_data = parser.extract_rt_plan()
            result['plan'] = plan_data
            logger.info("Đã nhập dữ liệu kế hoạch xạ trị")
        except Exception as error:
            logger.error(f"Lỗi khi trích xuất dữ liệu kế hoạch RT: {str(error)}")
            if progress_callback:
                progress_callback(75, f"Cảnh báo: Không thể trích xuất dữ liệu kế hoạch RT - {str(error)}")
    
    # Cập nhật tiến trình
    if progress_callback:
        progress_callback(80, "Đang tải dữ liệu liều...")
    
    # Trích xuất dữ liệu liều
    if modality_filters.get('rtdose', True) and parser.rt_dose:
        try:
            dose_data, dose_metadata = parser.extract_rt_dose()
            result['dose']['data'] = dose_data
            result['dose']['metadata'] = dose_metadata
            logger.info("Đã nhập dữ liệu liều xạ")
        except Exception as error:
            # Ghi log chi tiết hơn với traceback
            logger.error(f"Lỗi khi trích xuất dữ liệu liều RT: {str(error)}")
            logger.debug(f"Chi tiết lỗi: {traceback.format_exc()}")
            if progress_callback:
                progress_callback(85, f"Cảnh báo: Không thể trích xuất dữ liệu liều RT - {str(error)}")
    
    # Cập nhật tiến trình
    if progress_callback:
        progress_callback(95, "Đang hoàn thành nhập dữ liệu...")
    
    # Kiểm tra xem có dữ liệu nào được nhập không
    has_data = (
        result['image']['data'] is not None or 
        result['structures'] or 
        result['plan'] or 
        result['dose']['data'] is not None
    )
    
    if not has_data:
        raise DICOMError(
            "Không tìm thấy dữ liệu hợp lệ trong thư mục DICOM",
            DICOMErrorCodes.INSUFFICIENT_DATA
        )
    
    logger.info("Nhập kế hoạch DICOM thành công.")
    
    # Cập nhật tiến trình
    if progress_callback:
        progress_callback(100, "Đã hoàn thành nhập dữ liệu DICOM!")
    
    return result

@handle_dicom_error
def verify_dicom_compatibility(dicom_dir: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Kiểm tra tính tương thích của dữ liệu DICOM
    
    Hàm này kiểm tra xem dữ liệu DICOM có phù hợp để nhập vào hệ thống không,
    mà không thực sự nhập dữ liệu. Hàm này hữu ích để xác minh trước khi nhập
    dữ liệu đầy đủ.
    
    Args:
        dicom_dir: Thư mục chứa file DICOM
        
    Returns:
        Tuple[bool, Dict[str, Any]]: (có tương thích không, thông tin chi tiết)
            - Thông tin chi tiết bao gồm:
                - patient_info: Thông tin bệnh nhân
                - has_image: Có dữ liệu hình ảnh không
                - has_structure: Có dữ liệu cấu trúc không
                - has_plan: Có dữ liệu kế hoạch không
                - has_dose: Có dữ liệu liều không
                - image_count: Số lượng hình ảnh
                - structure_count: Số lượng cấu trúc
                - compatibility_issues: Danh sách các vấn đề về tính tương thích
    
    Raises:
        DICOMError: Khi có lỗi xảy ra trong quá trình kiểm tra
    """
    if not pydicom:
        raise DICOMError(
            "Không thể kiểm tra DICOM vì thiếu thư viện pydicom",
            DICOMErrorCodes.PARSING_ERROR
        )
    
    # Kiểm tra thư mục
    valid, errors = validate_dicom_directory(dicom_dir)
    if not valid:
        error_message = "\n".join(errors)
        raise DICOMError(
            f"Thư mục DICOM không hợp lệ: {error_message}",
            DICOMErrorCodes.INVALID_DIRECTORY
        )
    
    try:
        # Tạo parser
        parser = DICOMParser(dicom_dir)
        
        # Trích xuất thông tin
        patient_info = parser.extract_patient_info()
        
        # Kiểm tra các file đã được phân loại đúng
        has_image = len(parser.ct_files) > 0 or len(parser.mri_files) > 0 or len(parser.pet_files) > 0
        has_structure = parser.rt_struct is not None
        has_plan = parser.rt_plan is not None
        has_dose = parser.rt_dose is not None
        
        # Tạo kết quả
        result = {
            'patient_info': patient_info,
            'has_image': has_image,
            'has_structure': has_structure,
            'has_plan': has_plan,
            'has_dose': has_dose,
            'image_count': len(parser.ct_files) + len(parser.mri_files) + len(parser.pet_files),
            'structure_count': 0,
            'compatibility_issues': []
        }
        
        # Kiểm tra số lượng cấu trúc
        if has_structure:
            try:
                structures = parser.extract_rt_structure()
                result['structure_count'] = len(structures)
            except Exception as error:
                result['compatibility_issues'].append(f"Lỗi khi đọc cấu trúc: {str(error)}")
        
        # Kiểm tra tính tương thích
        is_compatible = True
        
        # Kiểm tra xem có ít nhất một loại dữ liệu
        if not (has_image or has_structure or has_plan or has_dose):
            result['compatibility_issues'].append("Không tìm thấy dữ liệu DICOM hợp lệ")
            is_compatible = False
        
        # Trả về kết quả
        return is_compatible, result
        
    except Exception as error:
        logger.error(f"Lỗi khi kiểm tra tính tương thích DICOM: {str(error)}")
        raise DICOMError(
            f"Không thể kiểm tra tính tương thích DICOM: {str(error)}",
            DICOMErrorCodes.PARSING_ERROR,
            {"traceback": traceback.format_exc()}
        )