#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module tích hợp kết nối các thành phần của hệ thống QuangStation.

Module này cung cấp các lớp và hàm để tích hợp giữa các thành phần:
- DICOM: Nhập/xuất dữ liệu DICOM, quản lý ảnh
- Contouring: Vẽ và quản lý cấu trúc
- Planning: Lập kế hoạch xạ trị, quản lý chùm tia
- Dose Calculation: Tính toán phân bố liều
"""

import os
import sys
import numpy as np
import pydicom
from typing import Dict, List, Tuple, Optional, Union, Any, Protocol, runtime_checkable
from pathlib import Path
import uuid
from datetime import datetime
import abc
import logging
import json

# Import các module hệ thống
from quangstation.utils.logging import get_logger
from quangstation.utils.config import get_config
from quangstation.io.dicom_parser import DICOMParser
from quangstation.image_processing.image_loader import ImageLoader
from quangstation.contouring.contour_tools import ContourTools
from quangstation.image_processing.segmentation import Segmentation
from quangstation.planning.techniques import RTTechnique, create_technique
from quangstation.dose_calculation.dose_engine_wrapper import DoseCalculator
from quangstation.plan_evaluation.dvh import DVHCalculator
from quangstation.data_management.session_management import SessionManager
from quangstation.data_management.patient_db import PatientDatabase
from quangstation.planning.plan_config import PlanConfig
from quangstation.io.dicom_export_rt import export_dicom_data as export_dicom_rt

# Module log
logger = get_logger("Integration")

@runtime_checkable
class DataProvider(Protocol):
    """Protocol định nghĩa interface cho các lớp cung cấp dữ liệu"""
    
    def get_image_data(self) -> Optional[np.ndarray]:
        """Trả về dữ liệu hình ảnh CT"""
        ...
    
    def get_structures(self) -> Dict[str, np.ndarray]:
        """Trả về từ điển các cấu trúc"""
        ...
    
    def get_plan_config(self) -> Optional[PlanConfig]:
        """Trả về cấu hình kế hoạch"""
        ...
    
    def get_dose_data(self) -> Optional[np.ndarray]:
        """Trả về dữ liệu phân bố liều"""
        ...

@runtime_checkable
class DataReceiver(Protocol):
    """Protocol định nghĩa interface cho các lớp nhận dữ liệu"""
    
    def set_image_data(self, image_data: np.ndarray, spacing: List[float], origin: List[float]) -> bool:
        """Thiết lập dữ liệu hình ảnh CT"""
        ...
    
    def set_structure(self, name: str, mask: np.ndarray, color: Optional[Tuple[float, float, float]] = None) -> bool:
        """Thiết lập cấu trúc"""
        ...
    
    def set_plan_config(self, plan_config: PlanConfig) -> bool:
        """Thiết lập cấu hình kế hoạch"""
        ...
    
    def set_dose_data(self, dose_data: np.ndarray, dose_grid_scaling: float) -> bool:
        """Thiết lập dữ liệu phân bố liều"""
        ...

class RTWorkflow:
    """
    Lớp quản lý quy trình xạ trị.
    
    Lớp này quản lý toàn bộ quy trình từ nhập dữ liệu đến lập kế hoạch và tính toán liều.
    """
    
    def __init__(self, session_id: Optional[str] = None):
        """
        Khởi tạo một quy trình xạ trị.
        
        Args:
            session_id: ID phiên làm việc, None để tạo ID mới
        """
        # Khởi tạo logger
        self.logger = get_logger("RTWorkflow")
        
        # Tạo ID phiên nếu không được cung cấp
        self.session_id = session_id or str(uuid.uuid4())
        self.logger.info(f"Khởi tạo quy trình xạ trị với ID: {self.session_id}")
        
        # Khởi tạo các thành phần
        self.dicom_parser = DICOMParser()
        self.image_loader = ImageLoader()
        self.contour_tools = ContourTools()
        self.segmentation = Segmentation()
        self.dose_calculator = DoseCalculator()
        self.dvh_calculator = DVHCalculator()
        self.session_manager = SessionManager()
        
        # Khởi tạo dữ liệu
        self.volume = None  # Dữ liệu hình ảnh CT
        self.structures = {}  # Cấu trúc
        self.plan = None  # Kế hoạch xạ trị
        self.dose = None  # Phân bố liều
        self.dvh = None  # Biểu đồ DVH
        
        # Thông tin bệnh nhân
        self.patient_id = None
        self.patient_name = None
        self.study_uid = None
        self.series_uid = None
        
        # Thông tin kỹ thuật
        self.technique = None
        self.beam_config = None
        
        # Thông tin phiên làm việc
        self.session_data = {}
        
    def load_session(self, session_id: str) -> bool:
        """
        Tải dữ liệu từ một phiên làm việc đã lưu.
        
        Args:
            session_id: ID phiên làm việc cần tải
            
        Returns:
            bool: True nếu tải thành công, False nếu không
        """
        try:
            session_data = self.session_manager.load_session(session_id)
            if not session_data:
                self.logger.error(f"Không tìm thấy phiên làm việc với ID: {session_id}")
                return False
                
            # Cập nhật dữ liệu từ phiên
            self.session_id = session_id
            self.session_data = session_data
            
            # Tải các thành phần từ phiên
            if 'patient_id' in session_data:
                self.patient_id = session_data['patient_id']
            if 'patient_name' in session_data:
                self.patient_name = session_data['patient_name']
            if 'study_uid' in session_data:
                self.study_uid = session_data['study_uid']
            if 'series_uid' in session_data:
                self.series_uid = session_data['series_uid']
                
            # Tải dữ liệu hình ảnh nếu có
            if 'image_path' in session_data and os.path.exists(session_data['image_path']):
                self.volume = self.image_loader.load_volume(session_data['image_path'])
                
            # Tải cấu trúc nếu có
            if 'structures_path' in session_data and os.path.exists(session_data['structures_path']):
                self.structures = self.contour_tools.load_structures(session_data['structures_path'])
                
            # Tải kế hoạch nếu có
            if 'plan_path' in session_data and os.path.exists(session_data['plan_path']):
                with open(session_data['plan_path'], 'r') as f:
                    self.plan = json.load(f)
                    
            # Tải liều nếu có
            if 'dose_path' in session_data and os.path.exists(session_data['dose_path']):
                self.dose = np.load(session_data['dose_path'])
                
            self.logger.info(f"Đã tải phiên làm việc: {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Lỗi khi tải phiên làm việc: {str(e)}")
            return False

    def load_dicom_data(self, directory: str) -> bool:
        """
        Tải dữ liệu DICOM từ thư mục
        
        Args:
            directory: Đường dẫn đến thư mục chứa dữ liệu DICOM
            
        Returns:
            bool: True nếu tải thành công, False nếu có lỗi
        """
        try:
            self.logger.info(f"Đang tải dữ liệu DICOM từ {directory}")
            
            # Parse và tải dữ liệu DICOM
            self.dicom_parser.parse_directory(directory)
            patient_info = self.dicom_parser.get_patient_info()
            
            # Cập nhật metadata bệnh nhân
            self.patient_id = patient_info.get('PatientID', str(uuid.uuid4()))
            self.patient_name = patient_info.get('PatientName', 'Unknown')
            self.patient_metadata = patient_info
            
            # Tải dữ liệu hình ảnh nếu có CT series
            ct_series = self.dicom_parser.get_series_by_modality('CT')
            if ct_series:
                series_id = ct_series[0]  # Lấy CT series đầu tiên
                image_data, metadata = self.dicom_parser.load_series_data(series_id)
                
                if image_data is not None:
                    self.volume = image_data
                    self.image_spacing = metadata.get('PixelSpacing', [1.0, 1.0]) + [metadata.get('SliceThickness', 1.0)]
                    self.image_origin = metadata.get('ImagePositionPatient', [0.0, 0.0, 0.0])
                    self.image_orientation = metadata.get('ImageOrientationPatient', [1, 0, 0, 0, 1, 0])
                    self.logger.info(f"Đã tải dữ liệu CT: shape={image_data.shape}, spacing={self.image_spacing}")
                
            # Tải dữ liệu cấu trúc nếu có RTSTRUCT
            rt_struct_series = self.dicom_parser.get_series_by_modality('RTSTRUCT')
            if rt_struct_series and self.volume is not None:
                series_id = rt_struct_series[0]  # Lấy RTSTRUCT đầu tiên
                structure_set = self.dicom_parser.load_rt_struct(series_id)
                
                if structure_set:
                    for name, mask, color in structure_set:
                        self.structures[name] = mask
                        getattr(self, "structure_colors", {})[name] = color
                    
                    self.logger.info(f"Đã tải {len(self.structures)} cấu trúc từ RTSTRUCT")
            
            # Tải dữ liệu kế hoạch nếu có RTPLAN
            rt_plan_series = self.dicom_parser.get_series_by_modality('RTPLAN')
            if rt_plan_series:
                series_id = rt_plan_series[0]  # Lấy RTPLAN đầu tiên
                plan_data = self.dicom_parser.load_rt_plan(series_id)
                
                if plan_data:
                    self.plan = plan_data
                    self.logger.info(f"Đã tải kế hoạch xạ trị: {self.plan.get('plan_name', 'Unnamed Plan')}")
            
            # Tải dữ liệu liều nếu có RTDOSE
            rt_dose_series = self.dicom_parser.get_series_by_modality('RTDOSE')
            if rt_dose_series:
                series_id = rt_dose_series[0]  # Lấy RTDOSE đầu tiên
                dose_data, dose_metadata = self.dicom_parser.load_rt_dose(series_id)
                
                if dose_data is not None:
                    self.dose = dose_data
                    self.logger.info(f"Đã tải dữ liệu phân bố liều: shape={dose_data.shape}")
            
            return True
        
        except Exception as error:
            self.logger.error(f"Lỗi khi tải dữ liệu DICOM: {str(error)}")
            return False

# ... Implement other methods with careful attention to data integrity ...

# Functions tiện ích toàn cục

def create_workflow():
    """
    Hàm tiện ích để tạo một quy trình mới.
    
    Returns:
        RTWorkflow: Quy trình xạ trị mới
    """
    return RTWorkflow()

def load_workflow(session_id):
    """
    Hàm tiện ích để tải một quy trình đã lưu.
    
    Args:
        session_id: ID của phiên làm việc
        
    Returns:
        RTWorkflow: Quy trình xạ trị
    """
    workflow = RTWorkflow(session_id)
    success = workflow.load_session(session_id)
    
    if not success:
        logger.error(f"Không thể tải quy trình với session_id={session_id}")
        return None
        
    return workflow

def load_dicom_directory(directory):
    """
    Hàm tiện ích để tạo quy trình và tải dữ liệu DICOM.
    
    Args:
        directory: Đường dẫn đến thư mục chứa dữ liệu DICOM
        
    Returns:
        RTWorkflow: Quy trình xạ trị
    """
    workflow = RTWorkflow()
    success = workflow.load_dicom_data(directory)
    
    if not success:
        logger.error(f"Không thể tải dữ liệu DICOM từ {directory}")
        return None
        
    return workflow

class IntegrationManager:
    """
    Lớp quản lý tích hợp giữa các thành phần của hệ thống QuangStation.
    
    Lớp này đóng vai trò trung gian giữa các module, giúp dễ dàng 
    truyền dữ liệu giữa các thành phần khác nhau mà không phụ thuộc trực tiếp.
    """
    
    def __init__(self, db_path: str = None):
        """
        Khởi tạo Integration Manager.
        
        Args:
            db_path: Đường dẫn đến cơ sở dữ liệu bệnh nhân (nếu có).
        """
        self.patient_db = PatientDatabase(db_path) if db_path else PatientDatabase()
        self.dicom_parser = DICOMParser()
        self.contour_tools = None
        self.dose_calculator = DoseCalculator()
        self.image_loader = ImageLoader()
        self.dvh_calculator = DVHCalculator()
        
        # Biến lưu trữ trạng thái hiện tại
        self.current_patient_id = None
        self.current_image_data = None
        self.current_structures = {}
        self.current_plan_config = None
        self.current_dose_data = None
        
        logger.info("Đã khởi tạo Integration Manager")
    
    def load_patient_data(self, patient_id: str) -> bool:
        """
        Tải dữ liệu bệnh nhân từ cơ sở dữ liệu.
        
        Args:
            patient_id: ID của bệnh nhân cần tải.
            
        Returns:
            True nếu tải thành công, False nếu không.
        """
        try:
            # Kiểm tra xem bệnh nhân có tồn tại không
            if not self.patient_db.patient_exists(patient_id):
                logger.error(f"Bệnh nhân {patient_id} không tồn tại trong cơ sở dữ liệu")
                return False
            
            # Thiết lập ID bệnh nhân hiện tại
            self.current_patient_id = patient_id
            
            # Tải dữ liệu bệnh nhân
            patient_data = self.patient_db.get_patient_data(patient_id)
            if not patient_data:
                logger.error(f"Không thể tải dữ liệu cho bệnh nhân {patient_id}")
                return False
            
            # Tải dữ liệu hình ảnh
            image_path = patient_data.get('image_data_path')
            if image_path and os.path.exists(image_path):
                self.current_image_data = self.image_loader.load_series(image_path)
                logger.info(f"Đã tải dữ liệu hình ảnh cho bệnh nhân {patient_id}")
            else:
                logger.warning(f"Không tìm thấy dữ liệu hình ảnh cho bệnh nhân {patient_id}")
            
            # Tải dữ liệu cấu trúc nếu có
            structure_path = patient_data.get('structure_data_path')
            if structure_path and os.path.exists(structure_path):
                # Khởi tạo ContourTools với dữ liệu hình ảnh hiện tại
                if self.current_image_data:
                    self.contour_tools = ContourTools(self.current_image_data)
                    self.contour_tools.load_structures(structure_path)
                    self.current_structures = self.contour_tools.get_all_structures()
                    logger.info(f"Đã tải {len(self.current_structures)} cấu trúc cho bệnh nhân {patient_id}")
                else:
                    logger.error("Không thể tải cấu trúc: dữ liệu hình ảnh chưa được tải")
            
            return True
        except Exception as error:
            logger.error(f"Lỗi khi tải dữ liệu bệnh nhân {patient_id}: {str(error)}")
            return False
    
    def import_dicom_data(self, dicom_folder: str, patient_info: Dict[str, Any] = None) -> Optional[str]:
        """
        Nhập dữ liệu DICOM từ thư mục.
        
        Args:
            dicom_folder: Đường dẫn đến thư mục chứa file DICOM.
            patient_info: Thông tin bệnh nhân bổ sung (nếu có).
            
        Returns:
            ID của bệnh nhân nếu nhập thành công, None nếu thất bại.
        """
        try:
            # Sử dụng DICOM Parser để đọc dữ liệu
            parsed_data = self.dicom_parser.parse_folder(dicom_folder)
            if not parsed_data:
                logger.error(f"Không thể đọc dữ liệu DICOM từ thư mục {dicom_folder}")
                return None
            
            # Tạo thông tin bệnh nhân nếu chưa có
            if not patient_info:
                # Lấy thông tin từ header DICOM
                patient_info = {
                    'name': parsed_data.get('patient_name', 'Unknown'),
                    'id': parsed_data.get('patient_id', f"PT{np.random.randint(10000, 99999)}"),
                    'birth_date': parsed_data.get('birth_date', 'Unknown'),
                    'sex': parsed_data.get('sex', 'Unknown')
                }
            
            # Tạo bệnh nhân mới trong cơ sở dữ liệu
            patient_id = self.patient_db.add_patient(patient_info)
            
            # Lưu dữ liệu hình ảnh
            if 'image_data' in parsed_data:
                image_path = os.path.join(self.patient_db.get_patient_folder(patient_id), 'image_data')
                os.makedirs(image_path, exist_ok=True)
                
                # Lưu dữ liệu và cập nhật thông tin bệnh nhân
                self.image_loader.save_to_disk(parsed_data['image_data'], image_path)
                self.patient_db.update_patient(patient_id, {'image_data_path': image_path})
                
                # Cập nhật dữ liệu hiện tại
                self.current_patient_id = patient_id
                self.current_image_data = parsed_data['image_data']
                
                # Khởi tạo ContourTools
                self.contour_tools = ContourTools(self.current_image_data)
            
            # Cập nhật thông tin cho RT-STRUCT nếu có
            if 'structure_data' in parsed_data:
                # Lưu dữ liệu cấu trúc
                structure_path = os.path.join(self.patient_db.get_patient_folder(patient_id), 'structures.rtss')
                self.dicom_parser.save_rt_struct(parsed_data['structure_data'], structure_path)
                self.patient_db.update_patient(patient_id, {'structure_data_path': structure_path})
                
                # Tải cấu trúc vào contour_tools
                if self.contour_tools:
                    self.contour_tools.load_structures(structure_path)
                    self.current_structures = self.contour_tools.get_all_structures()
            
            # Cập nhật thông tin cho RT-PLAN nếu có
            if 'plan_data' in parsed_data:
                # Lưu dữ liệu kế hoạch
                plan_path = os.path.join(self.patient_db.get_patient_folder(patient_id), 'plan.rtplan')
                self.dicom_parser.save_rt_plan(parsed_data['plan_data'], plan_path)
                self.patient_db.update_patient(patient_id, {'plan_data_path': plan_path})
                
                # Tạo PlanConfig từ dữ liệu RT-PLAN
                self.current_plan_config = PlanConfig()
                self._create_plan_config_from_rtplan(parsed_data['plan_data'])
            
            # Cập nhật thông tin cho RT-DOSE nếu có
            if 'dose_data' in parsed_data:
                # Lưu dữ liệu liều
                dose_path = os.path.join(self.patient_db.get_patient_folder(patient_id), 'dose.rtdose')
                self.dicom_parser.save_rt_dose(parsed_data['dose_data'], dose_path)
                self.patient_db.update_patient(patient_id, {'dose_data_path': dose_path})
                
                # Cập nhật dữ liệu liều hiện tại
                self.current_dose_data = parsed_data['dose_data']
            
            logger.info(f"Đã nhập thành công dữ liệu DICOM cho bệnh nhân {patient_id}")
            return patient_id
        except Exception as error:
            logger.error(f"Lỗi khi nhập dữ liệu DICOM: {str(error)}")
            return None
    
    def create_structure(self, name: str, mask: np.ndarray, color: str = None) -> bool:
        """
        Tạo cấu trúc mới.
        
        Args:
            name: Tên cấu trúc.
            mask: Mảng 3D đánh dấu cấu trúc (binary mask).
            color: Màu hiển thị (mã hex).
            
        Returns:
            True nếu tạo thành công, False nếu không.
        """
        if not self.contour_tools:
            if self.current_image_data:
                self.contour_tools = ContourTools(self.current_image_data)
            else:
                logger.error("Không thể tạo cấu trúc: chưa tải dữ liệu hình ảnh")
                return False
        
        try:
            # Thêm cấu trúc mới
            self.contour_tools.add_structure(name, mask)
            
            # Đặt màu nếu được cung cấp
            if color:
                self.contour_tools.set_structure_color(name, color)
            
            # Cập nhật danh sách cấu trúc hiện tại
            self.current_structures = self.contour_tools.get_all_structures()
            
            # Lưu cấu trúc nếu đã có bệnh nhân
            if self.current_patient_id:
                structure_path = os.path.join(
                    self.patient_db.get_patient_folder(self.current_patient_id), 
                    'structures.rtss'
                )
                self.contour_tools.save_to_dicom(structure_path)
                self.patient_db.update_patient(
                    self.current_patient_id, 
                    {'structure_data_path': structure_path}
                )
            
            logger.info(f"Đã tạo cấu trúc {name}")
            return True
        except Exception as error:
            logger.error(f"Lỗi khi tạo cấu trúc {name}: {str(error)}")
            return False
    
    def create_plan(self, plan_config: PlanConfig) -> bool:
        """
        Tạo kế hoạch xạ trị mới.
        
        Args:
            plan_config: Đối tượng cấu hình kế hoạch.
            
        Returns:
            True nếu tạo thành công, False nếu không.
        """
        if not self.current_patient_id:
            logger.error("Không thể tạo kế hoạch: chưa chọn bệnh nhân")
            return False
        
        try:
            # Lưu cấu hình kế hoạch
            self.current_plan_config = plan_config
            
            # Lưu kế hoạch vào cơ sở dữ liệu
            plan_folder = os.path.join(
                self.patient_db.get_patient_folder(self.current_patient_id),
                'plans'
            )
            os.makedirs(plan_folder, exist_ok=True)
            
            plan_path = os.path.join(plan_folder, f"{plan_config.plan_id}.json")
            with open(plan_path, 'w') as f:
                import json
                json.dump(plan_config.to_dict(), f, indent=2)
            
            # Cập nhật thông tin bệnh nhân
            current_plans = self.patient_db.get_patient_data(self.current_patient_id).get('plans', [])
            current_plans.append({
                'plan_id': plan_config.plan_id,
                'plan_name': plan_config.plan_name,
                'created_at': plan_config.created_at,
                'path': plan_path
            })
            
            self.patient_db.update_patient(self.current_patient_id, {'plans': current_plans})
            
            logger.info(f"Đã tạo kế hoạch {plan_config.plan_name}")
            return True
        except Exception as error:
            logger.error(f"Lỗi khi tạo kế hoạch: {str(error)}")
            return False
    
    def calculate_dose(self, algorithm: str = 'CCC', **kwargs) -> Optional[np.ndarray]:
        """
        Tính toán phân bố liều.
        
        Args:
            algorithm: Thuật toán tính liều ('CCC', 'MC', 'AAA', v.v).
            **kwargs: Các tham số bổ sung cho thuật toán.
            
        Returns:
            Mảng 3D chứa phân bố liều nếu tính toán thành công, None nếu thất bại.
        """
        if not self.current_plan_config:
            logger.error("Không thể tính liều: chưa có kế hoạch")
            return None
        
        if not self.current_image_data:
            logger.error("Không thể tính liều: chưa có dữ liệu hình ảnh")
            return None
        
        try:
            # Tính toán liều dựa trên thuật toán
            self.current_dose_data = self.dose_calculator.calculate(
                patient_id=self.current_patient_id,
                image_data=self.current_image_data,
                structures=self.current_structures,
                plan_config=self.current_plan_config,
                algorithm=algorithm,
                **kwargs
            )
            
            # Lưu dữ liệu liều nếu tính toán thành công
            if self.current_dose_data is not None and self.current_patient_id:
                dose_path = os.path.join(
                    self.patient_db.get_patient_folder(self.current_patient_id),
                    'plans',
                    f"{self.current_plan_config.plan_id}_dose.npy"
                )
                
                np.save(dose_path, self.current_dose_data)
                
                # Cập nhật thông tin kế hoạch
                current_plans = self.patient_db.get_patient_data(self.current_patient_id).get('plans', [])
                for plan in current_plans:
                    if plan['plan_id'] == self.current_plan_config.plan_id:
                        plan['dose_path'] = dose_path
                        break
                
                self.patient_db.update_patient(self.current_patient_id, {'plans': current_plans})
                
                logger.info(f"Đã tính toán phân bố liều cho kế hoạch {self.current_plan_config.plan_name}")
            
            return self.current_dose_data
        except Exception as error:
            logger.error(f"Lỗi khi tính toán liều: {str(error)}")
            return None
    
    def calculate_dvh(self, structures: List[str] = None) -> Optional[Dict[str, Dict[str, np.ndarray]]]:
        """
        Tính toán Dose-Volume Histogram (DVH).
        
        Args:
            structures: Danh sách các cấu trúc cần tính DVH. Nếu None, tính cho tất cả.
            
        Returns:
            Dictionary chứa dữ liệu DVH nếu tính toán thành công, None nếu thất bại.
        """
        if not self.current_dose_data:
            logger.error("Không thể tính DVH: chưa có dữ liệu liều")
            return None
        
        if not self.current_structures:
            logger.error("Không thể tính DVH: chưa có cấu trúc")
            return None
        
        try:
            # Xác định danh sách cấu trúc cần tính
            if structures is None:
                structures = list(self.current_structures.keys())
            
            # Tính DVH cho mỗi cấu trúc
            dvh_data = {}
            for name in structures:
                if name in self.current_structures:
                    structure_mask = self.current_structures[name]
                    dvh_result = self.dvh_calculator.calculate(
                        structure_mask=structure_mask,
                        dose_matrix=self.current_dose_data,
                        name=name
                    )
                    dvh_data[name] = dvh_result
            
            # Lưu dữ liệu DVH nếu tính toán thành công
            if dvh_data and self.current_patient_id and self.current_plan_config:
                dvh_path = os.path.join(
                    self.patient_db.get_patient_folder(self.current_patient_id),
                    'plans',
                    f"{self.current_plan_config.plan_id}_dvh.npz"
                )
                
                # Lưu mảng dữ liệu DVH
                np.savez(dvh_path, **{name: data for name, data in dvh_data.items()})
                
                # Cập nhật thông tin kế hoạch
                current_plans = self.patient_db.get_patient_data(self.current_patient_id).get('plans', [])
                for plan in current_plans:
                    if plan['plan_id'] == self.current_plan_config.plan_id:
                        plan['dvh_path'] = dvh_path
                        break
                
                self.patient_db.update_patient(self.current_patient_id, {'plans': current_plans})
                
                logger.info(f"Đã tính toán DVH cho {len(dvh_data)} cấu trúc")
            
            return dvh_data
        except Exception as error:
            logger.error(f"Lỗi khi tính toán DVH: {str(error)}")
            return None
    
    def export_dicom_data(self, export_folder: str, items: List[str] = None) -> bool:
        """
        Xuất dữ liệu sang định dạng DICOM.
        
        Args:
            export_folder: Thư mục đích.
            items: Danh sách các loại dữ liệu cần xuất ('image', 'structure', 'plan', 'dose').
                Nếu None, xuất tất cả.
                
        Returns:
            True nếu xuất thành công, False nếu không.
        """
        if not self.current_patient_id:
            logger.error("Không thể xuất dữ liệu: chưa chọn bệnh nhân")
            return False
        
        # Mặc định xuất tất cả
        if items is None:
            items = ['image', 'structure', 'plan', 'dose']
        
        try:
            # Lấy thông tin bệnh nhân
            patient_info = self.get_patient_info()
            
            # Chuẩn bị dữ liệu để xuất
            export_data = {
                'image_data': self.current_image_data if 'image' in items else None,
                'structures': self.current_structures if 'structure' in items else None,
                'plan_config': self.current_plan_config if 'plan' in items else None,
                'dose_data': self.current_dose_data if 'dose' in items else None,
                'patient_info': patient_info,
                'dose_spacing': getattr(self, 'dose_spacing', None),
                'dose_origin': getattr(self, 'dose_origin', None),
                'dose_positions': getattr(self, 'dose_positions', None),
                'structure_uid': getattr(self, 'structure_uid', None),
                'rtplan_uid': getattr(self, 'rtplan_uid', None)
            }
            
            # Gọi hàm xuất DICOM từ module io
            result = export_dicom_rt(export_folder, **export_data)
            
            if result:
                logger.info(f"Đã xuất dữ liệu DICOM thành công vào thư mục {export_folder}")
                return True
            else:
                logger.error("Xuất dữ liệu DICOM thất bại")
                return False
            
        except Exception as error:
            logger.error(f"Lỗi khi xuất dữ liệu DICOM: {str(error)}")
            return False
    
    def get_patient_info(self) -> Optional[Dict[str, Any]]:
        """Lấy thông tin bệnh nhân hiện tại."""
        if not self.current_patient_id:
            return None
        
        return self.patient_db.get_patient_data(self.current_patient_id)
    
    def get_image_data(self) -> Optional[np.ndarray]:
        """Lấy dữ liệu hình ảnh hiện tại."""
        return self.current_image_data
    
    def get_structures(self) -> Dict[str, np.ndarray]:
        """Lấy dữ liệu cấu trúc hiện tại."""
        return self.current_structures
    
    def get_plan_config(self) -> Optional[PlanConfig]:
        """Lấy cấu hình kế hoạch hiện tại."""
        return self.current_plan_config
    
    def get_dose_data(self) -> Optional[np.ndarray]:
        """Lấy dữ liệu liều hiện tại."""
        return self.current_dose_data

    def _create_plan_config_from_rtplan(self, plan_data):
        """
        Tạo đối tượng PlanConfig từ dữ liệu DICOM RT-PLAN.
        
        Args:
            plan_data: Dữ liệu DICOM RT-PLAN (có thể là Dataset từ pydicom hoặc dữ liệu đã được parse)
            
        Returns:
            None (cập nhật self.current_plan_config)
        """
        try:
            if plan_data is None:
                logger.warning("Không có dữ liệu RT-PLAN để tạo PlanConfig")
                return
                
            # Xử lý nếu plan_data là đối tượng pydicom Dataset
            if hasattr(plan_data, 'SOPClassUID'):
                dicom_dataset = plan_data
            elif isinstance(plan_data, dict) and 'dataset' in plan_data:
                dicom_dataset = plan_data['dataset']
            else:
                logger.warning("Định dạng dữ liệu RT-PLAN không được hỗ trợ")
                return
                
            # Thiết lập thông tin cơ bản
            plan_name = getattr(dicom_dataset, 'RTPlanLabel', "Unnamed Plan")
            self.current_plan_config.plan_name = plan_name
            
            # Thiết lập machine name và radiation type
            beam_sequence = getattr(dicom_dataset, 'BeamSequence', None)
            if beam_sequence and len(beam_sequence) > 0:
                first_beam = beam_sequence[0]
                # Machine name
                machine_name = getattr(first_beam, 'TreatmentMachineName', "")
                self.current_plan_config.machine_name = machine_name
                
                # Radiation type
                radiation_type = getattr(first_beam, 'RadiationType', "PHOTON").lower()
                if radiation_type in ['photon', 'electron', 'proton']:
                    self.current_plan_config.radiation_type = radiation_type
                
                # Năng lượng
                control_point_seq = getattr(first_beam, 'ControlPointSequence', None)
                if control_point_seq and len(control_point_seq) > 0:
                    energy = getattr(control_point_seq[0], 'NominalBeamEnergy', "")
                    if energy:
                        if radiation_type == 'photon':
                            self.current_plan_config.energy = f"{energy}MV"
                        elif radiation_type == 'electron':
                            self.current_plan_config.energy = f"{energy}MeV"
                        else:
                            self.current_plan_config.energy = str(energy)
            
            # Thiết lập thông tin liều
            fraction_group_seq = getattr(dicom_dataset, 'FractionGroupSequence', None)
            if fraction_group_seq and len(fraction_group_seq) > 0:
                first_group = fraction_group_seq[0]
                fraction_count = getattr(first_group, 'NumberOfFractionsPlanned', 0)
                self.current_plan_config.fraction_count = int(fraction_count)
                
                # Tính tổng liều
                total_dose = 0.0
                ref_beam_seq = getattr(first_group, 'ReferencedBeamSequence', [])
                for ref_beam in ref_beam_seq:
                    beam_meterset = getattr(ref_beam, 'BeamMeterset', 0.0)
                    total_dose += float(beam_meterset)
                
                # Giả định: 1 MU = 0.01 Gy (cần điều chỉnh theo thiết bị thực tế)
                total_dose = total_dose * 0.01
                
                self.current_plan_config.total_dose = total_dose
                if self.current_plan_config.fraction_count > 0:
                    self.current_plan_config.fraction_dose = total_dose / self.current_plan_config.fraction_count
            
            # Thiết lập kỹ thuật xạ trị dựa trên loại beam
            technique = "3DCRT"  # Mặc định
            if beam_sequence:
                # Kiểm tra có IMRT hoặc VMAT không
                has_mlc = False
                has_dynamic = False
                
                for beam in beam_sequence:
                    beam_type = getattr(beam, 'BeamType', "STATIC")
                    if beam_type == "DYNAMIC":
                        has_dynamic = True
                    
                    # Kiểm tra có MLC không
                    cp_seq = getattr(beam, 'ControlPointSequence', [])
                    for cp in cp_seq:
                        device_seq = getattr(cp, 'BeamLimitingDevicePositionSequence', [])
                        for device in device_seq:
                            if getattr(device, 'RTBeamLimitingDeviceType', "") in ['MLCX', 'MLCY']:
                                has_mlc = True
                                break
                
                if has_dynamic and has_mlc:
                    technique = "VMAT"
                elif has_mlc:
                    technique = "IMRT"
                
                self.current_plan_config.technique = technique
            
            # Thiết lập tư thế bệnh nhân
            patient_position = getattr(dicom_dataset, 'PatientPosition', "HFS")
            valid_positions = ["HFS", "HFP", "FFS", "FFP"]
            if patient_position in valid_positions:
                self.current_plan_config.patient_position = patient_position
            
            # Thiết lập isocenter
            isocenter = [0.0, 0.0, 0.0]  # Mặc định
            if beam_sequence and len(beam_sequence) > 0:
                cp_seq = getattr(beam_sequence[0], 'ControlPointSequence', [])
                if cp_seq and len(cp_seq) > 0:
                    isocenter_pos = getattr(cp_seq[0], 'IsocenterPosition', None)
                    if isocenter_pos:
                        isocenter = [float(isocenter_pos[0]), float(isocenter_pos[1]), float(isocenter_pos[2])]
            
            self.current_plan_config.isocenter = isocenter
            
            # Thiết lập thông tin chùm tia
            self.current_plan_config.beams = []
            
            if beam_sequence:
                for i, beam in enumerate(beam_sequence):
                    beam_info = {
                        "id": f"beam_{i+1}",
                        "name": getattr(beam, 'BeamName', f"Beam {i+1}"),
                        "weight": 1.0,  # Mặc định
                        "gantry_angle": 0.0,
                        "collimator_angle": 0.0,
                        "couch_angle": 0.0,
                    }
                    
                    # Lấy thông tin góc chiếu
                    cp_seq = getattr(beam, 'ControlPointSequence', [])
                    if cp_seq and len(cp_seq) > 0:
                        cp = cp_seq[0]
                        beam_info["gantry_angle"] = float(getattr(cp, 'GantryAngle', 0.0))
                        beam_info["collimator_angle"] = float(getattr(cp, 'BeamLimitingDeviceAngle', 0.0))
                        beam_info["couch_angle"] = float(getattr(cp, 'PatientSupportAngle', 0.0))
                        
                        # Lấy thông tin trường chiếu (jaw, MLC)
                        device_seq = getattr(cp, 'BeamLimitingDevicePositionSequence', [])
                        for device in device_seq:
                            device_type = getattr(device, 'RTBeamLimitingDeviceType', "")
                            positions = getattr(device, 'LeafJawPositions', [])
                            
                            if device_type == 'X':
                                beam_info["field_x"] = positions
                            elif device_type == 'Y':
                                beam_info["field_y"] = positions
                            elif device_type in ['MLCX', 'MLCY']:
                                beam_info["mlc_segments"] = [positions]
                    
                    # Xử lý thông tin VMAT
                    beam_type = getattr(beam, 'BeamType', "STATIC")
                    if beam_type == "DYNAMIC" and len(cp_seq) > 1:
                        arc_segments = []
                        start_angle = float(getattr(cp_seq[0], 'GantryAngle', 0.0))
                        stop_angle = float(getattr(cp_seq[-1], 'GantryAngle', 0.0))
                        
                        arc_segment = {
                            "start_angle": start_angle,
                            "stop_angle": stop_angle,
                            "control_points": len(cp_seq)
                        }
                        
                        arc_segments.append(arc_segment)
                        beam_info["arc_segments"] = arc_segments
                    
                    # Lấy thông tin Monitor Units
                    if fraction_group_seq and len(fraction_group_seq) > 0:
                        ref_beam_seq = getattr(fraction_group_seq[0], 'ReferencedBeamSequence', [])
                        for ref_beam in ref_beam_seq:
                            if getattr(ref_beam, 'ReferencedBeamNumber', None) == i + 1:
                                beam_info["monitor_units"] = float(getattr(ref_beam, 'BeamMeterset', 100.0))
                                break
                    
                    # Thêm beam vào danh sách
                    self.current_plan_config.beams.append(beam_info)
            
            logger.info(f"Đã tạo PlanConfig từ dữ liệu DICOM RT-PLAN: {plan_name}")
            
        except Exception as error:
            logger.error(f"Lỗi khi tạo PlanConfig từ dữ liệu DICOM: {str(error)}", include_traceback=True) 