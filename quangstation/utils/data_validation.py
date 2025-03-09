#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module data_validation.py
-------------------------
Module này cung cấp các hàm và tiện ích để xác thực tính toàn vẹn dữ liệu
giữa các module trong hệ thống QuangStation.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any, Callable
import os
import json
from dataclasses import dataclass
from enum import Enum
import re

from quangstation.utils.logging import get_logger

# Khởi tạo logger
logger = get_logger("DataValidation")

class DataType(Enum):
    """Các kiểu dữ liệu chính trong hệ thống"""
    CT_IMAGE = "ct_image"
    MR_IMAGE = "mr_image"
    PET_IMAGE = "pet_image"
    STRUCTURE_MASK = "structure_mask"
    DOSE_MATRIX = "dose_matrix"
    BEAM_CONFIG = "beam_config"
    PLAN_CONFIG = "plan_config"
    DVH_DATA = "dvh_data"
    PATIENT_INFO = "patient_info"
    DICOM_METADATA = "dicom_metadata"
    OPTIMIZATION_CONSTRAINTS = "optimization_constraints"
    QA_RESULTS = "qa_results"

@dataclass
class ValidationResult:
    """Kết quả xác thực dữ liệu"""
    valid: bool
    message: str
    data_type: DataType
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
    
    def __bool__(self):
        return self.valid

def validate_ct_image(image_data: np.ndarray, metadata: Dict[str, Any] = None) -> ValidationResult:
    """
    Xác thực dữ liệu hình ảnh CT.
    
    Args:
        image_data: Mảng NumPy 3D chứa dữ liệu CT
        metadata: Siêu dữ liệu đi kèm với ảnh CT
    
    Returns:
        ValidationResult: Kết quả xác thực
    """
    warnings = []
    
    # Kiểm tra dữ liệu là mảng NumPy 3D
    if not isinstance(image_data, np.ndarray):
        return ValidationResult(
            valid=False,
            message="Dữ liệu CT không phải là mảng NumPy",
            data_type=DataType.CT_IMAGE
        )
    
    # Kiểm tra số chiều
    if image_data.ndim != 3:
        return ValidationResult(
            valid=False, 
            message=f"Dữ liệu CT phải là mảng 3D, nhận được mảng {image_data.ndim}D",
            data_type=DataType.CT_IMAGE
        )
    
    # Kiểm tra kích thước hợp lý
    if image_data.shape[0] < 5:
        warnings.append(f"Số lát cắt CT ít ({image_data.shape[0]}), có thể gây vấn đề cho phân tích")
    
    if image_data.shape[1] < 100 or image_data.shape[2] < 100:
        warnings.append(f"Kích thước CT nhỏ ({image_data.shape}), có thể ảnh hưởng đến độ chính xác")
    
    # Kiểm tra giá trị trong phạm vi Hounsfield Unit
    min_val, max_val = np.min(image_data), np.max(image_data)
    if min_val < -2000 or max_val > 3000:
        warnings.append(f"Giá trị HU nằm ngoài phạm vi thông thường: [{min_val}, {max_val}]")
    
    # Kiểm tra siêu dữ liệu
    if metadata is not None:
        # Kiểm tra thông tin khoảng cách voxel
        if 'PixelSpacing' not in metadata or len(metadata['PixelSpacing']) != 2:
            warnings.append("Thiếu thông tin PixelSpacing trong metadata hoặc không đúng định dạng")
        
        if 'SliceThickness' not in metadata:
            warnings.append("Thiếu thông tin SliceThickness trong metadata")
    
    return ValidationResult(
        valid=True,
        message="Dữ liệu CT hợp lệ",
        data_type=DataType.CT_IMAGE,
        warnings=warnings
    )

def validate_structure_mask(mask: np.ndarray, image_data: np.ndarray = None) -> ValidationResult:
    """
    Xác thực mặt nạ cấu trúc.
    
    Args:
        mask: Mảng NumPy chứa mặt nạ cấu trúc (mỗi phần tử là 0 hoặc 1)
        image_data: Dữ liệu hình ảnh tương ứng (để kiểm tra kích thước)
    
    Returns:
        ValidationResult: Kết quả xác thực
    """
    warnings = []
    
    # Kiểm tra dữ liệu là mảng NumPy
    if not isinstance(mask, np.ndarray):
        return ValidationResult(
            valid=False,
            message="Mặt nạ cấu trúc không phải là mảng NumPy",
            data_type=DataType.STRUCTURE_MASK
        )
    
    # Kiểm tra số chiều
    if mask.ndim != 3:
        return ValidationResult(
            valid=False,
            message=f"Mặt nạ cấu trúc phải là mảng 3D, nhận được mảng {mask.ndim}D",
            data_type=DataType.STRUCTURE_MASK
        )
    
    # Kiểm tra kiểu dữ liệu
    if mask.dtype != np.bool_ and not np.issubdtype(mask.dtype, np.integer):
        warnings.append(f"Kiểu dữ liệu của mặt nạ nên là boolean hoặc integer, nhận được {mask.dtype}")
    
    # Kiểm tra giá trị (phải bao gồm 0 và 1, không được chứa các giá trị khác)
    unique_values = np.unique(mask)
    if not np.all(np.isin(unique_values, [0, 1])):
        return ValidationResult(
            valid=False,
            message=f"Mặt nạ cấu trúc chỉ được chứa giá trị 0 và 1, nhận được {unique_values}",
            data_type=DataType.STRUCTURE_MASK
        )
    
    # Kiểm tra kích thước so với ảnh
    if image_data is not None:
        if mask.shape != image_data.shape:
            return ValidationResult(
                valid=False,
                message=f"Kích thước mặt nạ ({mask.shape}) khác với kích thước ảnh ({image_data.shape})",
                data_type=DataType.STRUCTURE_MASK
            )
    
    # Kiểm tra mặt nạ có chứa vùng kích hoạt
    if np.sum(mask) == 0:
        warnings.append("Mặt nạ cấu trúc không chứa vùng kích hoạt (toàn bộ là 0)")
    
    return ValidationResult(
        valid=True,
        message="Mặt nạ cấu trúc hợp lệ",
        data_type=DataType.STRUCTURE_MASK,
        warnings=warnings
    )

def validate_dose_matrix(dose_data: np.ndarray, image_data: np.ndarray = None) -> ValidationResult:
    """
    Xác thực ma trận liều.
    
    Args:
        dose_data: Mảng NumPy 3D chứa dữ liệu liều
        image_data: Dữ liệu hình ảnh tương ứng (để kiểm tra kích thước)
    
    Returns:
        ValidationResult: Kết quả xác thực
    """
    warnings = []
    
    # Kiểm tra dữ liệu là mảng NumPy
    if not isinstance(dose_data, np.ndarray):
        return ValidationResult(
            valid=False,
            message="Dữ liệu liều không phải là mảng NumPy",
            data_type=DataType.DOSE_MATRIX
        )
    
    # Kiểm tra số chiều
    if dose_data.ndim != 3:
        return ValidationResult(
            valid=False,
            message=f"Dữ liệu liều phải là mảng 3D, nhận được mảng {dose_data.ndim}D",
            data_type=DataType.DOSE_MATRIX
        )
    
    # Kiểm tra kiểu dữ liệu
    if not np.issubdtype(dose_data.dtype, np.number):
        warnings.append(f"Kiểu dữ liệu của ma trận liều nên là số, nhận được {dose_data.dtype}")
    
    # Kiểm tra giá trị
    min_val, max_val = np.min(dose_data), np.max(dose_data)
    if min_val < 0:
        warnings.append(f"Ma trận liều chứa giá trị âm: {min_val}")
    
    if max_val > 1000:
        warnings.append(f"Ma trận liều chứa giá trị quá lớn: {max_val}, có thể là lỗi đơn vị")
    
    # Kiểm tra kích thước so với ảnh
    if image_data is not None:
        if dose_data.shape != image_data.shape:
            warnings.append(f"Kích thước ma trận liều ({dose_data.shape}) khác với kích thước ảnh ({image_data.shape})")
    
    return ValidationResult(
        valid=True,
        message="Ma trận liều hợp lệ",
        data_type=DataType.DOSE_MATRIX,
        warnings=warnings
    )

def validate_plan_config(plan_config: Dict[str, Any]) -> ValidationResult:
    """
    Xác thực cấu hình kế hoạch.
    
    Args:
        plan_config: Dictionary chứa thông tin cấu hình kế hoạch
    
    Returns:
        ValidationResult: Kết quả xác thực
    """
    warnings = []
    required_fields = ['plan_name', 'total_dose', 'fraction_count', 'technique']
    
    # Kiểm tra các trường bắt buộc
    missing_fields = [field for field in required_fields if field not in plan_config]
    if missing_fields:
        return ValidationResult(
            valid=False,
            message=f"Thiếu các trường bắt buộc trong cấu hình kế hoạch: {', '.join(missing_fields)}",
            data_type=DataType.PLAN_CONFIG
        )
    
    # Kiểm tra giá trị
    if plan_config['total_dose'] <= 0:
        return ValidationResult(
            valid=False,
            message=f"Liều tổng không hợp lệ: {plan_config['total_dose']}",
            data_type=DataType.PLAN_CONFIG
        )
    
    if plan_config['fraction_count'] <= 0:
        return ValidationResult(
            valid=False,
            message=f"Số buổi không hợp lệ: {plan_config['fraction_count']}",
            data_type=DataType.PLAN_CONFIG
        )
    
    # Kiểm tra kỹ thuật
    valid_techniques = ['3DCRT', 'IMRT', 'VMAT', 'SRS', 'SBRT']
    if plan_config['technique'] not in valid_techniques:
        warnings.append(f"Kỹ thuật '{plan_config['technique']}' không nằm trong danh sách kỹ thuật phổ biến: {', '.join(valid_techniques)}")
    
    # Kiểm tra isocenter
    if 'isocenter' not in plan_config:
        warnings.append("Thiếu thông tin isocenter trong cấu hình kế hoạch")
    elif not isinstance(plan_config['isocenter'], list) or len(plan_config['isocenter']) != 3:
        warnings.append(f"Tọa độ isocenter không hợp lệ: {plan_config['isocenter']}")
    
    # Kiểm tra danh sách beam
    if 'beams' not in plan_config or not plan_config['beams']:
        warnings.append("Kế hoạch không có beam nào")
    
    return ValidationResult(
        valid=True,
        message="Cấu hình kế hoạch hợp lệ",
        data_type=DataType.PLAN_CONFIG,
        warnings=warnings
    )

def validate_dvh_data(dvh_data: Dict[str, Any]) -> ValidationResult:
    """
    Xác thực dữ liệu DVH.
    
    Args:
        dvh_data: Dictionary chứa dữ liệu DVH
    
    Returns:
        ValidationResult: Kết quả xác thực
    """
    warnings = []
    
    # Kiểm tra cấu trúc dữ liệu
    for structure_name, dvh_info in dvh_data.items():
        required_keys = ['dose_bins', 'volume_bins', 'cumulative_volume', 'differential_volume', 'metrics']
        missing_keys = [key for key in required_keys if key not in dvh_info]
        
        if missing_keys:
            warnings.append(f"Cấu trúc '{structure_name}' thiếu các trường DVH: {', '.join(missing_keys)}")
        
        # Kiểm tra kích thước mảng
        if 'dose_bins' in dvh_info and 'cumulative_volume' in dvh_info:
            if len(dvh_info['dose_bins']) != len(dvh_info['cumulative_volume']):
                return ValidationResult(
                    valid=False,
                    message=f"Kích thước mảng liều và mảng thể tích tích lũy không khớp cho cấu trúc '{structure_name}'",
                    data_type=DataType.DVH_DATA
                )
        
        # Kiểm tra metrics
        if 'metrics' in dvh_info:
            if not isinstance(dvh_info['metrics'], dict):
                warnings.append(f"Metrics của cấu trúc '{structure_name}' không phải là dictionary")
            else:
                expected_metrics = ['min_dose', 'max_dose', 'mean_dose', 'median_dose', 'D95', 'V20']
                missing_metrics = [metric for metric in expected_metrics if metric not in dvh_info['metrics']]
                if missing_metrics:
                    warnings.append(f"Cấu trúc '{structure_name}' thiếu các metrics: {', '.join(missing_metrics)}")
    
    return ValidationResult(
        valid=True,
        message="Dữ liệu DVH hợp lệ",
        data_type=DataType.DVH_DATA,
        warnings=warnings
    )

def validate_patient_info(patient_info: Dict[str, Any]) -> ValidationResult:
    """
    Xác thực thông tin bệnh nhân.
    
    Args:
        patient_info: Dictionary chứa thông tin bệnh nhân
    
    Returns:
        ValidationResult: Kết quả xác thực
    """
    warnings = []
    required_fields = ['PatientID', 'PatientName']
    
    # Kiểm tra các trường bắt buộc
    missing_fields = [field for field in required_fields if field not in patient_info]
    if missing_fields:
        return ValidationResult(
            valid=False,
            message=f"Thiếu các trường bắt buộc trong thông tin bệnh nhân: {', '.join(missing_fields)}",
            data_type=DataType.PATIENT_INFO
        )
    
    # Kiểm tra mã bệnh nhân
    if not patient_info['PatientID'] or not isinstance(patient_info['PatientID'], str):
        return ValidationResult(
            valid=False,
            message="Mã bệnh nhân không hợp lệ",
            data_type=DataType.PATIENT_INFO
        )
    
    # Kiểm tra tên bệnh nhân
    if not patient_info['PatientName'] or not isinstance(patient_info['PatientName'], str):
        return ValidationResult(
            valid=False,
            message="Tên bệnh nhân không hợp lệ",
            data_type=DataType.PATIENT_INFO
        )
    
    # Kiểm tra các trường khác
    if 'PatientBirthDate' in patient_info:
        date_pattern = re.compile(r'^\d{8}$')  # YYYYMMDD
        if not date_pattern.match(str(patient_info['PatientBirthDate'])):
            warnings.append(f"Định dạng ngày sinh không hợp lệ: {patient_info['PatientBirthDate']}")
    
    return ValidationResult(
        valid=True,
        message="Thông tin bệnh nhân hợp lệ",
        data_type=DataType.PATIENT_INFO,
        warnings=warnings
    )

def validate_data_flow(source_data: Any, target_module: str, expected_type: DataType) -> ValidationResult:
    """
    Kiểm tra tính hợp lệ của dữ liệu chuyển từ module này sang module khác.
    
    Args:
        source_data: Dữ liệu nguồn cần kiểm tra
        target_module: Tên module đích sẽ nhận dữ liệu
        expected_type: Loại dữ liệu mong đợi
    
    Returns:
        ValidationResult: Kết quả xác thực
    """
    # Xác định hàm kiểm tra dựa trên loại dữ liệu
    validation_functions = {
        DataType.CT_IMAGE: validate_ct_image,
        DataType.STRUCTURE_MASK: validate_structure_mask,
        DataType.DOSE_MATRIX: validate_dose_matrix,
        DataType.PLAN_CONFIG: validate_plan_config,
        DataType.DVH_DATA: validate_dvh_data,
        DataType.PATIENT_INFO: validate_patient_info
    }
    
    if expected_type not in validation_functions:
        return ValidationResult(
            valid=False,
            message=f"Không có hàm xác thực cho loại dữ liệu {expected_type.value}",
            data_type=expected_type
        )
    
    # Thực hiện xác thực
    result = validation_functions[expected_type](source_data)
    
    # Ghi log
    if result.valid:
        log_message = f"Dữ liệu {expected_type.value} hợp lệ cho module {target_module}"
        if result.warnings:
            log_message += f" với {len(result.warnings)} cảnh báo"
            for warning in result.warnings:
                log_message += f"\n  - {warning}"
        logger.info(log_message)
    else:
        logger.error(f"Dữ liệu {expected_type.value} không hợp lệ cho module {target_module}: {result.message}")
    
    return result

def check_data_compatibility(data_provider: Any, data_receiver: Any) -> bool:
    """
    Kiểm tra tính tương thích của dữ liệu giữa bên cung cấp và bên nhận.
    
    Args:
        data_provider: Đối tượng cung cấp dữ liệu
        data_receiver: Đối tượng nhận dữ liệu
    
    Returns:
        bool: True nếu dữ liệu tương thích, False nếu không
    """
    # Thực hiện trong future
    return True 