#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module quản lý giao diện nhập dữ liệu DICOM vào hệ thống QuangStation V2.

Module này đóng vai trò kết nối giữa các thành phần:
- Module nhập dữ liệu DICOM core/io/dicom_import.py
- Cơ sở dữ liệu bệnh nhân PatientDatabase
- Quản lý phiên làm việc SessionManager

Cung cấp các lớp và hàm:
- DataImportInterface: Giao diện nhập dữ liệu DICOM chính
- import_dicom_to_patient: Nhập dữ liệu DICOM vào hồ sơ bệnh nhân
"""

import os
import sys
import time
import datetime
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Callable
import traceback

from quangstation.clinical.data_management.patient_db import PatientDatabase, Patient
from quangstation.core.io.dicom_import import import_plan_from_dicom, verify_dicom_compatibility
from quangstation.core.utils.logging import get_logger
from quangstation.core.utils.dicom_error_handler import DICOMError, DICOMErrorCodes, handle_dicom_error
from quangstation.core.data_models.image_data import ImageData
from quangstation.core.data_models.structure_data import Structure, StructureSet, StructureType
from quangstation.core.data_models.plan_data import PlanConfig
from quangstation.core.data_models.dose_data import DoseData, DoseType

logger = get_logger(__name__)

class DataImportInterface:
    """
    Giao diện nhập dữ liệu DICOM vào hệ thống.
    
    Lớp này cung cấp các phương thức để nhập dữ liệu DICOM vào cơ sở dữ liệu bệnh nhân
    và quản lý quá trình nhập dữ liệu. Nó cũng cung cấp phương thức để kiểm tra tính
    tương thích của dữ liệu DICOM trước khi nhập.
    """
    
    def __init__(self):
        """Khởi tạo giao diện nhập dữ liệu DICOM."""
        self.db = PatientDatabase()
        self.last_error = None
        self.last_import_result = None
        logger.info("DataImportInterface đã được khởi tạo")
    
    @handle_dicom_error
    def check_dicom_compatibility(self, dicom_dir: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Kiểm tra tính tương thích của dữ liệu DICOM trước khi nhập.
        
        Args:
            dicom_dir: Đường dẫn đến thư mục chứa dữ liệu DICOM
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (có tương thích không, thông tin chi tiết)
        """
        logger.info(f"Đang kiểm tra tính tương thích của dữ liệu DICOM trong thư mục: {dicom_dir}")
        return verify_dicom_compatibility(dicom_dir)
    
    @handle_dicom_error
    def import_dicom_data(self, dicom_dir: str, patient_id: Optional[str] = None, 
                         modality_filters: Optional[Dict[str, bool]] = None,
                         progress_callback: Optional[Callable[[int, str], None]] = None) -> Dict[str, Any]:
        """
        Nhập dữ liệu DICOM vào hệ thống và thêm vào cơ sở dữ liệu bệnh nhân.
        
        Args:
            dicom_dir: Đường dẫn đến thư mục chứa dữ liệu DICOM
            patient_id: ID của bệnh nhân (nếu không cung cấp, sẽ tạo bệnh nhân mới từ thông tin DICOM)
            modality_filters: Bộ lọc các loại dữ liệu cần nhập
            progress_callback: Hàm callback để cập nhật tiến trình (nhận giá trị từ 0-100 và thông báo)
            
        Returns:
            Dict[str, Any]: Thông tin kết quả nhập dữ liệu:
                - patient_id: ID của bệnh nhân
                - has_image: Có dữ liệu hình ảnh không
                - has_structure: Có dữ liệu cấu trúc không
                - has_plan: Có dữ liệu kế hoạch không
                - has_dose: Có dữ liệu liều không
                - message: Thông báo kết quả
        """
        logger.info(f"Đang nhập dữ liệu DICOM từ thư mục: {dicom_dir}")
        
        try:
            # Tạo hàm callback để cập nhật tiến trình
            def _progress_update(progress: int, message: str):
                if progress_callback:
                    progress_callback(progress, message)
                logger.debug(f"Tiến trình nhập dữ liệu: {progress}% - {message}")
            
            # Nhập dữ liệu DICOM
            import_result = import_plan_from_dicom(dicom_dir, modality_filters, _progress_update)
            self.last_import_result = import_result
            
            # Lấy thông tin bệnh nhân
            patient_info = import_result['patient']
            
            # Nếu không có patient_id, tạo hoặc lấy bệnh nhân từ thông tin DICOM
            if not patient_id:
                # Kiểm tra xem bệnh nhân đã tồn tại trong cơ sở dữ liệu chưa
                if 'patient_id' in patient_info and self.db.patient_exists(patient_info['patient_id']):
                    patient_id = patient_info['patient_id']
                    logger.info(f"Bệnh nhân với ID {patient_id} đã tồn tại trong cơ sở dữ liệu")
                    
                    # Lấy thông tin bệnh nhân từ cơ sở dữ liệu
                    patient = self.db.get_patient(patient_id)
                else:
                    # Tạo bệnh nhân mới
                    _progress_update(45, "Đang tạo bệnh nhân mới từ thông tin DICOM...")
                    patient = Patient(
                        patient_id=patient_info.get('patient_id'),
                        name=patient_info.get('patient_name', ''),
                        birth_date=patient_info.get('birth_date', ''),
                        gender=patient_info.get('gender', ''),
                    )
                    
                    # Thêm bệnh nhân vào cơ sở dữ liệu
                    patient_id = self.db.add_patient(patient)
                    logger.info(f"Đã tạo bệnh nhân mới với ID: {patient_id}")
            else:
                # Kiểm tra xem bệnh nhân có tồn tại không
                if not self.db.patient_exists(patient_id):
                    raise DICOMError(
                        f"Bệnh nhân với ID {patient_id} không tồn tại trong cơ sở dữ liệu",
                        DICOMErrorCodes.NO_PATIENT_INFO
                    )
                
                # Lấy thông tin bệnh nhân từ cơ sở dữ liệu
                patient = self.db.get_patient(patient_id)
            
            # Nhập dữ liệu hình ảnh (nếu có)
            if import_result['image']['data'] is not None:
                _progress_update(60, "Đang lưu dữ liệu hình ảnh...")
                image_data = import_result['image']['data']
                image_metadata = import_result['image']['metadata']
                modality = image_metadata.get('modality', 'CT')
                
                # Lưu vào cơ sở dữ liệu
                volume_id = self.db.insert_volume(patient_id, modality, image_data, image_metadata)
                logger.info(f"Đã lưu dữ liệu hình ảnh {modality} với ID: {volume_id}")
            
            # Nhập dữ liệu cấu trúc (nếu có)
            if import_result['structures']:
                _progress_update(70, "Đang lưu dữ liệu cấu trúc...")
                
                # Lưu vào cơ sở dữ liệu
                struct_id = self.db.insert_rt_struct(patient_id, import_result['structures'])
                logger.info(f"Đã lưu dữ liệu cấu trúc với ID: {struct_id}")
            
            # Nhập dữ liệu kế hoạch (nếu có)
            if import_result['plan']:
                _progress_update(80, "Đang lưu dữ liệu kế hoạch xạ trị...")
                
                # Lưu vào cơ sở dữ liệu
                plan_id = self.db.insert_rt_plan(patient_id, import_result['plan'])
                logger.info(f"Đã lưu dữ liệu kế hoạch xạ trị với ID: {plan_id}")
            
            # Nhập dữ liệu liều (nếu có)
            if import_result['dose']['data'] is not None:
                _progress_update(90, "Đang lưu dữ liệu liều xạ trị...")
                dose_data = import_result['dose']['data']
                dose_metadata = import_result['dose']['metadata']
                
                # Lưu vào cơ sở dữ liệu
                dose_id = self.db.insert_rt_dose(patient_id, dose_data, dose_metadata)
                logger.info(f"Đã lưu dữ liệu liều xạ trị với ID: {dose_id}")
            
            # Cập nhật tiến trình
            _progress_update(100, "Đã hoàn thành nhập dữ liệu DICOM!")
            
            # Tạo kết quả trả về
            result = {
                'patient_id': patient_id,
                'has_image': import_result['image']['data'] is not None,
                'has_structure': bool(import_result['structures']),
                'has_plan': bool(import_result['plan']),
                'has_dose': import_result['dose']['data'] is not None,
                'message': "Đã nhập dữ liệu DICOM thành công"
            }
            
            return result
        
        except DICOMError as error:
            # Ghi lại lỗi cuối cùng
            self.last_error = error
            logger.error(f"Lỗi khi nhập dữ liệu DICOM: {str(error)}")
            
            # Tạo kết quả lỗi
            result = {
                'patient_id': patient_id,
                'has_image': False,
                'has_structure': False,
                'has_plan': False,
                'has_dose': False,
                'message': f"Lỗi: {str(error)}",
                'error': str(error)
            }
            
            # Chuyển tiếp lỗi
            raise
    
    def get_last_error(self) -> Optional[str]:
        """
        Lấy thông tin lỗi cuối cùng khi nhập dữ liệu.
        
        Returns:
            Optional[str]: Thông tin lỗi (None nếu không có lỗi)
        """
        if self.last_error:
            return str(self.last_error)
        return None

@handle_dicom_error
def import_dicom_to_patient(dicom_dir: str, patient_id: Optional[str] = None, 
                          progress_callback: Optional[Callable[[int, str], None]] = None) -> Dict[str, Any]:
    """
    Hàm tiện ích để nhập dữ liệu DICOM vào hồ sơ bệnh nhân.
    
    Args:
        dicom_dir: Đường dẫn đến thư mục chứa dữ liệu DICOM
        patient_id: ID của bệnh nhân (nếu không cung cấp, sẽ tạo bệnh nhân mới từ thông tin DICOM)
        progress_callback: Hàm callback để cập nhật tiến trình (nhận giá trị từ 0-100 và thông báo)
        
    Returns:
        Dict[str, Any]: Thông tin kết quả nhập dữ liệu
    """
    importer = DataImportInterface()
    return importer.import_dicom_data(dicom_dir, patient_id, None, progress_callback) 