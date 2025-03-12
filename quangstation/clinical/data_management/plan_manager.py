#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module quản lý kế hoạch xạ trị cho QuangStation V2.
"""

import os
import json
import uuid
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import shutil
import pickle
from pathlib import Path

from quangstation.core.utils.logging import get_logger
from quangstation.core.utils.config import get_config
from quangstation.core.io import export_plan_to_dicom

logger = get_logger(__name__)

class RTPlan:
    """Lớp đại diện cho kế hoạch xạ trị"""
    
    def __init__(self, plan_id: str = None, patient_id: str = None, **kwargs):
        """
        Khởi tạo đối tượng kế hoạch xạ trị
        
        Args:
            plan_id: ID kế hoạch (nếu không cung cấp sẽ tạo tự động)
            patient_id: ID bệnh nhân
            **kwargs: Thông tin khác về kế hoạch
        """
        self.plan_id = plan_id or str(uuid.uuid4())
        self.patient_id = patient_id
        self.name = kwargs.get('name', 'Kế hoạch mới')
        self.description = kwargs.get('description', '')
        self.created_date = kwargs.get('created_date', datetime.now().isoformat())
        self.modified_date = kwargs.get('modified_date', datetime.now().isoformat())
        self.status = kwargs.get('status', 'draft')  # draft, submitted, approved, delivered
        
        # Thông tin kỹ thuật
        self.technique = kwargs.get('technique', '3DCRT')  # 3DCRT, IMRT, VMAT, SRS, etc.
        self.modality = kwargs.get('modality', 'PHOTON')  # PHOTON, ELECTRON, PROTON
        self.energy = kwargs.get('energy', '6MV')  # 6MV, 10MV, etc.
        
        # Thông tin liều
        self.prescribed_dose = kwargs.get('prescribed_dose', 0.0)  # Gy
        self.fraction_count = kwargs.get('fraction_count', 0)
        self.fraction_dose = kwargs.get('fraction_dose', 0.0)  # Gy
        
        # Cấu trúc mục tiêu
        self.target_volumes = kwargs.get('target_volumes', {})  # Dict[name: {type, dose, priority}]
        
        # Cấu trúc nguy cấp (OAR)
        self.oars = kwargs.get('oars', {})  # Dict[name: {constraints}]
        
        # Thông tin chùm tia
        self.beams = kwargs.get('beams', [])  # List[beam_dict]
        
        # Dữ liệu liều
        self.dose_data = kwargs.get('dose_data', None)  # 3D numpy array
        self.dose_grid = kwargs.get('dose_grid', None)  # {size, resolution, origin}
        
        # DVH và các chỉ số đánh giá
        self.dvh_data = kwargs.get('dvh_data', {})
        self.plan_metrics = kwargs.get('plan_metrics', {})
        
        # Tải thêm thông tin từ kwargs
        for key, value in kwargs.items():
            if key not in ['plan_id', 'patient_id', 'name', 'description', 'created_date', 
                          'modified_date', 'status', 'technique', 'modality', 'energy',
                          'prescribed_dose', 'fraction_count', 'fraction_dose',
                          'target_volumes', 'oars', 'beams', 'dose_data', 
                          'dose_grid', 'dvh_data', 'plan_metrics']:
                setattr(self, key, value)
    
    def to_dict(self, include_large_data=False) -> Dict[str, Any]:
        """
        Chuyển đổi thông tin kế hoạch thành dictionary
        
        Args:
            include_large_data: Nếu True, bao gồm cả dữ liệu lớn như dose_data
            
        Returns:
            Dict thông tin kế hoạch
        """
        result = {
            'plan_id': self.plan_id,
            'patient_id': self.patient_id,
            'name': self.name,
            'description': self.description,
            'created_date': self.created_date,
            'modified_date': self.modified_date,
            'status': self.status,
            'technique': self.technique,
            'modality': self.modality,
            'energy': self.energy,
            'prescribed_dose': self.prescribed_dose,
            'fraction_count': self.fraction_count,
            'fraction_dose': self.fraction_dose,
            'target_volumes': self.target_volumes,
            'oars': self.oars,
            'beams': self.beams,
            'dose_grid': self.dose_grid,
            'plan_metrics': self.plan_metrics
        }
        
        if include_large_data:
            # Đối với dữ liệu lớn, chuyển đổi thành dạng phù hợp để serialize
            if self.dose_data is not None:
                # Lưu ý: Không serialize trực tiếp numpy array vào dict
                # Thay vào đó, ghi vào file riêng nếu cần
                result['has_dose_data'] = True
            else:
                result['has_dose_data'] = False
            
            if self.dvh_data:
                result['dvh_data'] = self.dvh_data
        
        return result
    
    def update(self, **kwargs) -> None:
        """
        Cập nhật thông tin kế hoạch
        
        Args:
            **kwargs: Thông tin cần cập nhật
        """
        # Cập nhật các thuộc tính cơ bản
        for key in ['name', 'description', 'status', 'technique', 'modality', 'energy',
                   'prescribed_dose', 'fraction_count', 'fraction_dose']:
            if key in kwargs:
                setattr(self, key, kwargs[key])
        
        # Cập nhật target_volumes nếu có
        if 'target_volumes' in kwargs:
            self.target_volumes = kwargs['target_volumes']
        
        # Cập nhật oars nếu có
        if 'oars' in kwargs:
            self.oars = kwargs['oars']
        
        # Cập nhật beams nếu có
        if 'beams' in kwargs:
            self.beams = kwargs['beams']
        
        # Cập nhật dose_data nếu có
        if 'dose_data' in kwargs and kwargs['dose_data'] is not None:
            self.dose_data = kwargs['dose_data']
        
        # Cập nhật dose_grid nếu có
        if 'dose_grid' in kwargs:
            self.dose_grid = kwargs['dose_grid']
        
        # Cập nhật các thuộc tính khác
        for key, value in kwargs.items():
            if key not in ['plan_id', 'patient_id', 'created_date']:
                setattr(self, key, value)
        
        # Cập nhật ngày sửa đổi
        self.modified_date = datetime.now().isoformat()
    
    def add_beam(self, beam_data: Dict[str, Any]) -> str:
        """
        Thêm chùm tia vào kế hoạch
        
        Args:
            beam_data: Thông tin chùm tia
            
        Returns:
            beam_id: ID của chùm tia
        """
        beam_id = beam_data.get('beam_id', str(uuid.uuid4()))
        beam_data['beam_id'] = beam_id
        
        # Kiểm tra xem beam_id đã tồn tại chưa
        for i, beam in enumerate(self.beams):
            if beam.get('beam_id') == beam_id:
                # Nếu đã tồn tại, cập nhật
                self.beams[i] = beam_data
                self.modified_date = datetime.now().isoformat()
                return beam_id
        
        # Nếu chưa tồn tại, thêm mới
        self.beams.append(beam_data)
        self.modified_date = datetime.now().isoformat()
        return beam_id
    
    def remove_beam(self, beam_id: str) -> bool:
        """
        Xóa chùm tia khỏi kế hoạch
        
        Args:
            beam_id: ID của chùm tia cần xóa
            
        Returns:
            bool: True nếu xóa thành công, False nếu không tìm thấy
        """
        for i, beam in enumerate(self.beams):
            if beam.get('beam_id') == beam_id:
                del self.beams[i]
                self.modified_date = datetime.now().isoformat()
                return True
        return False
    
    def add_target(self, name: str, target_type: str, prescribed_dose: float, priority: int = 1) -> None:
        """
        Thêm cấu trúc mục tiêu vào kế hoạch
        
        Args:
            name: Tên cấu trúc mục tiêu
            target_type: Loại mục tiêu (PTV, CTV, GTV)
            prescribed_dose: Liều kê toa (Gy)
            priority: Độ ưu tiên (số càng lớn càng ưu tiên)
        """
        self.target_volumes[name] = {
            'type': target_type,
            'dose': prescribed_dose,
            'priority': priority
        }
        self.modified_date = datetime.now().isoformat()
    
    def remove_target(self, name: str) -> bool:
        """
        Xóa cấu trúc mục tiêu khỏi kế hoạch
        
        Args:
            name: Tên cấu trúc mục tiêu cần xóa
            
        Returns:
            bool: True nếu xóa thành công, False nếu không tìm thấy
        """
        if name in self.target_volumes:
            del self.target_volumes[name]
            self.modified_date = datetime.now().isoformat()
            return True
        return False
    
    def add_oar(self, name: str, constraints: Dict[str, Any]) -> None:
        """
        Thêm cơ quan nguy cấp (OAR) vào kế hoạch
        
        Args:
            name: Tên cơ quan
            constraints: Ràng buộc liều (Dict với các khóa như 'max_dose', 'mean_dose', 'V20Gy', ...)
        """
        self.oars[name] = constraints
        self.modified_date = datetime.now().isoformat()
    
    def remove_oar(self, name: str) -> bool:
        """
        Xóa cơ quan nguy cấp (OAR) khỏi kế hoạch
        
        Args:
            name: Tên cơ quan cần xóa
            
        Returns:
            bool: True nếu xóa thành công, False nếu không tìm thấy
        """
        if name in self.oars:
            del self.oars[name]
            self.modified_date = datetime.now().isoformat()
            return True
        return False
    
    def set_dose_data(self, dose_data: np.ndarray, grid_info: Dict[str, Any] = None) -> None:
        """
        Thiết lập dữ liệu liều
        
        Args:
            dose_data: Dữ liệu liều 3D
            grid_info: Thông tin về lưới liều (kích thước, độ phân giải, gốc tọa độ)
        """
        self.dose_data = dose_data
        
        if grid_info:
            self.dose_grid = grid_info
        elif self.dose_grid is None:
            # Thiết lập thông tin lưới mặc định nếu không cung cấp
            self.dose_grid = {
                'size': dose_data.shape,
                'resolution': [2.5, 2.5, 2.5],  # mm
                'origin': [0, 0, 0]  # mm
            }
        
        self.modified_date = datetime.now().isoformat()
    
    def set_dvh_data(self, dvh_data: Dict[str, Any]) -> None:
        """
        Thiết lập dữ liệu DVH
        
        Args:
            dvh_data: Dữ liệu DVH
        """
        self.dvh_data = dvh_data
        self.modified_date = datetime.now().isoformat()
    
    def set_plan_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Thiết lập các chỉ số đánh giá kế hoạch
        
        Args:
            metrics: Các chỉ số đánh giá
        """
        self.plan_metrics = metrics
        self.modified_date = datetime.now().isoformat()
    
    def __str__(self) -> str:
        """Biểu diễn chuỗi của đối tượng kế hoạch"""
        return f"Plan: {self.name} (ID: {self.plan_id}, Patient: {self.patient_id})"


class PlanManager:
    """Lớp quản lý kế hoạch xạ trị"""
    
    def __init__(self, data_dir: str = None):
        """
        Khởi tạo quản lý kế hoạch
        
        Args:
            data_dir: Thư mục lưu trữ dữ liệu (nếu không cung cấp sẽ sử dụng mặc định)
        """
        # Xác định đường dẫn lưu trữ dữ liệu
        self.data_dir = data_dir or os.path.join(
            get_config('workspace.root_dir', os.path.expanduser('~/QuangStation_Data')),
            'plans'
        )
        
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Dữ liệu các kế hoạch đã tải
        self.loaded_plans = {}
        
        logger.info(f"Khởi tạo PlanManager tại {self.data_dir}")
    
    def create_plan(self, patient_id: str, name: str = None, **kwargs) -> RTPlan:
        """
        Tạo kế hoạch mới
        
        Args:
            patient_id: ID bệnh nhân
            name: Tên kế hoạch
            **kwargs: Thông tin khác về kế hoạch
            
        Returns:
            RTWPlan: Đối tượng kế hoạch mới
        """
        plan_id = kwargs.get('plan_id', str(uuid.uuid4()))
        name = name or f"Kế hoạch {datetime.now().strftime('%d/%m/%Y')}"
        
        # Tạo kế hoạch mới
        plan = RTPlan(
            plan_id=plan_id,
            patient_id=patient_id,
            name=name,
            **kwargs
        )
        
        # Lưu kế hoạch
        self.save_plan(plan)
        
        # Thêm vào danh sách đã tải
        self.loaded_plans[plan_id] = plan
        
        logger.info(f"Đã tạo kế hoạch mới: {plan}")
        return plan
    
    def get_plan(self, plan_id: str) -> Optional[RTPlan]:
        """
        Lấy thông tin kế hoạch
        
        Args:
            plan_id: ID của kế hoạch cần lấy
            
        Returns:
            RTWPlan: Đối tượng kế hoạch, hoặc None nếu không tìm thấy
        """
        # Kiểm tra đã tải chưa
        if plan_id in self.loaded_plans:
            return self.loaded_plans[plan_id]
        
        # Tải từ đĩa
        plan_dir = os.path.join(self.data_dir, plan_id)
        
        if not os.path.exists(plan_dir):
            logger.warning(f"Không tìm thấy thư mục dữ liệu của kế hoạch: {plan_id}")
            return None
        
        try:
            # Tải thông tin cơ bản
            plan_info_file = os.path.join(plan_dir, 'plan_info.json')
            with open(plan_info_file, 'r') as f:
                plan_info = json.load(f)
            
            # Tạo đối tượng RTWPlan
            plan = RTPlan(**plan_info)
            
            # Tải dữ liệu liều (nếu có)
            dose_file = os.path.join(plan_dir, 'dose_data.npy')
            if os.path.exists(dose_file):
                plan.dose_data = np.load(dose_file)
            
            # Tải dữ liệu DVH (nếu có)
            dvh_file = os.path.join(plan_dir, 'dvh_data.json')
            if os.path.exists(dvh_file):
                with open(dvh_file, 'r') as f:
                    plan.dvh_data = json.load(f)
            
            # Lưu vào danh sách đã tải
            self.loaded_plans[plan_id] = plan
            
            return plan
            
        except Exception as e:
            logger.error(f"Lỗi khi tải kế hoạch {plan_id}: {str(e)}")
            return None
    
    def save_plan(self, plan: RTPlan) -> bool:
        """
        Lưu kế hoạch vào đĩa
        
        Args:
            plan: Đối tượng kế hoạch cần lưu
            
        Returns:
            bool: True nếu lưu thành công, False nếu thất bại
        """
        # Tạo thư mục cho kế hoạch
        plan_dir = os.path.join(self.data_dir, plan.plan_id)
        os.makedirs(plan_dir, exist_ok=True)
        
        try:
            # Lưu thông tin cơ bản
            plan_info = plan.to_dict(include_large_data=False)
            plan_info_file = os.path.join(plan_dir, 'plan_info.json')
            with open(plan_info_file, 'w') as f:
                json.dump(plan_info, f, indent=2)
            
            # Lưu dữ liệu liều (nếu có)
            if plan.dose_data is not None:
                dose_file = os.path.join(plan_dir, 'dose_data.npy')
                np.save(dose_file, plan.dose_data)
            
            # Lưu dữ liệu DVH (nếu có)
            if plan.dvh_data:
                dvh_file = os.path.join(plan_dir, 'dvh_data.json')
                with open(dvh_file, 'w') as f:
                    json.dump(plan.dvh_data, f, indent=2)
            
            # Lưu vào danh sách đã tải
            self.loaded_plans[plan.plan_id] = plan
            
            logger.info(f"Đã lưu kế hoạch: {plan}")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu kế hoạch {plan.plan_id}: {str(e)}")
            return False
    
    def delete_plan(self, plan_id: str) -> bool:
        """
        Xóa kế hoạch
        
        Args:
            plan_id: ID của kế hoạch cần xóa
            
        Returns:
            bool: True nếu xóa thành công, False nếu không tìm thấy
        """
        plan_dir = os.path.join(self.data_dir, plan_id)
        
        if not os.path.exists(plan_dir):
            logger.warning(f"Không tìm thấy thư mục dữ liệu của kế hoạch: {plan_id}")
            return False
        
        try:
            # Xóa thư mục dữ liệu
            shutil.rmtree(plan_dir)
            
            # Xóa khỏi danh sách đã tải
            if plan_id in self.loaded_plans:
                del self.loaded_plans[plan_id]
            
            logger.info(f"Đã xóa kế hoạch: {plan_id}")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi xóa kế hoạch {plan_id}: {str(e)}")
            return False
    
    def get_patient_plans(self, patient_id: str) -> List[Dict[str, Any]]:
        """
        Lấy danh sách kế hoạch của bệnh nhân
        
        Args:
            patient_id: ID bệnh nhân
            
        Returns:
            List[Dict]: Danh sách thông tin cơ bản của các kế hoạch
        """
        plans = []
        
        # Duyệt qua tất cả thư mục kế hoạch
        for plan_id in os.listdir(self.data_dir):
            plan_dir = os.path.join(self.data_dir, plan_id)
            
            if os.path.isdir(plan_dir):
                plan_info_file = os.path.join(plan_dir, 'plan_info.json')
                
                if os.path.exists(plan_info_file):
                    try:
                        with open(plan_info_file, 'r') as f:
                            plan_info = json.load(f)
                            
                            # Kiểm tra xem kế hoạch có phải của bệnh nhân này không
                            if plan_info.get('patient_id') == patient_id:
                                # Chỉ lấy thông tin cơ bản
                                basic_info = {
                                    'plan_id': plan_info.get('plan_id'),
                                    'name': plan_info.get('name'),
                                    'description': plan_info.get('description', ''),
                                    'status': plan_info.get('status', 'draft'),
                                    'technique': plan_info.get('technique', ''),
                                    'created_date': plan_info.get('created_date', ''),
                                    'modified_date': plan_info.get('modified_date', '')
                                }
                                plans.append(basic_info)
                                
                    except Exception as e:
                        logger.error(f"Lỗi khi đọc thông tin kế hoạch {plan_id}: {str(e)}")
        
        # Sắp xếp theo ngày sửa đổi (mới nhất lên đầu)
        plans.sort(key=lambda x: x.get('modified_date', ''), reverse=True)
        
        return plans
    
    def copy_plan(self, plan_id: str, new_name: str = None) -> Optional[RTPlan]:
        """
        Sao chép kế hoạch
        
        Args:
            plan_id: ID kế hoạch cần sao chép
            new_name: Tên mới cho kế hoạch sao chép
            
        Returns:
            RTWPlan: Kế hoạch sao chép, hoặc None nếu không thành công
        """
        # Tải kế hoạch gốc
        original_plan = self.get_plan(plan_id)
        if not original_plan:
            logger.error(f"Không tìm thấy kế hoạch gốc: {plan_id}")
            return None
        
        # Tạo tên mới nếu không được chỉ định
        if not new_name:
            new_name = f"Copy of {original_plan.name}"
        
        # Tạo kế hoạch mới
        new_plan = RTPlan(
            patient_id=original_plan.patient_id,
            name=new_name,
            description=original_plan.description,
            technique=original_plan.technique,
            modality=original_plan.modality,
            energy=original_plan.energy,
            prescribed_dose=original_plan.prescribed_dose,
            fraction_count=original_plan.fraction_count,
            fraction_dose=original_plan.fraction_dose,
            target_volumes=original_plan.target_volumes.copy(),
            oars=original_plan.oars.copy(),
            beams=[beam.copy() for beam in original_plan.beams],
            dose_grid=original_plan.dose_grid.copy() if original_plan.dose_grid else None
        )
        
        # Sao chép dữ liệu liều (nếu có)
        if original_plan.dose_data is not None:
            new_plan.dose_data = original_plan.dose_data.copy()
        
        # Sao chép dữ liệu DVH (nếu có)
        if original_plan.dvh_data:
            new_plan.dvh_data = original_plan.dvh_data.copy()
        
        # Lưu kế hoạch mới
        self.save_plan(new_plan)
        
        logger.info(f"Đã sao chép kế hoạch: {original_plan} -> {new_plan}")
        return new_plan
    
    def export_plan_to_dicom(self, plan_id: str, output_dir: str) -> Dict[str, str]:
        """
        Xuất kế hoạch sang định dạng DICOM
        
        Args:
            plan_id: ID kế hoạch cần xuất
            output_dir: Thư mục đầu ra
            
        Returns:
            Dict[str, str]: Thông tin về các file đã xuất
        """
        # Tải kế hoạch
        plan = self.get_plan(plan_id)
        if not plan:
            logger.error(f"Không tìm thấy kế hoạch: {plan_id}")
            raise ValueError(f"Không tìm thấy kế hoạch: {plan_id}")
        
        # Tạo thư mục đầu ra nếu chưa tồn tại
        os.makedirs(output_dir, exist_ok=True)
        
        # Xuất kế hoạch sang DICOM
        result = export_plan_to_dicom(plan, output_dir)
        
        logger.info(f"Đã xuất kế hoạch {plan_id} sang DICOM tại {output_dir}")
        return result
    
    def import_plan_from_dicom(self, dicom_dir: str, patient_id: str) -> Optional[RTPlan]:
        """
        Nhập kế hoạch từ file DICOM
        
        Args:
            dicom_dir: Thư mục chứa file DICOM
            patient_id: ID bệnh nhân
            
        Returns:
            RTWPlan: Kế hoạch đã nhập, hoặc None nếu không thành công
        """
        from quangstation.core.io import dicom_import
        
        try:
            # Nhập dữ liệu từ DICOM
            dicom_data = dicom_import.import_plan_from_dicom(dicom_dir)
            
            if not dicom_data:
                logger.error("Không thể nhập dữ liệu từ DICOM")
                return None
            
            # Tạo kế hoạch mới
            plan_id = str(uuid.uuid4())
            plan_name = dicom_data.get('plan', {}).get('name', f"Kế hoạch nhập từ DICOM {datetime.datetime.now().strftime('%Y-%m-%d')}")
            
            plan = RTPlan(plan_id=plan_id, patient_id=patient_id, name=plan_name)
            
            # Cập nhật thông tin kế hoạch từ dữ liệu DICOM
            plan_info = dicom_data.get('plan', {})
            plan.update(**plan_info)
            
            # Cập nhật cấu trúc
            structures = dicom_data.get('structures', {})
            for name, struct_data in structures.items():
                if 'type' in struct_data:
                    if struct_data['type'] == 'TARGET':
                        plan.add_target(name, struct_data.get('target_type', 'PTV'), 
                                       struct_data.get('prescribed_dose', 0.0),
                                       struct_data.get('priority', 1))
                    else:
                        plan.add_oar(name, struct_data.get('constraints', {}))
            
            # Cập nhật dữ liệu liều nếu có
            dose_data = dicom_data.get('dose', {}).get('data')
            dose_metadata = dicom_data.get('dose', {}).get('metadata', {})
            if dose_data is not None:
                plan.set_dose_data(dose_data, dose_metadata)
            
            # Lưu kế hoạch
            self.save_plan(plan)
            
            logger.info(f"Đã nhập kế hoạch từ DICOM thành công: {plan_id}")
            return plan
            
        except Exception as e:
            logger.error(f"Lỗi khi nhập kế hoạch từ DICOM: {str(e)}")
            return None

# Tạo instance mặc định
plan_manager = PlanManager()
