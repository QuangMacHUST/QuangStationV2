#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module định nghĩa cấu trúc dữ liệu cho kế hoạch xạ trị.
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum, auto
from datetime import datetime

class TechniqueType(Enum):
    """Loại kỹ thuật xạ trị."""
    STATIC = auto()  # 3D-CRT
    IMRT = auto()    # Intensity Modulated RT
    VMAT = auto()    # Volumetric Modulated Arc Therapy
    SRS = auto()     # Stereotactic Radiosurgery
    SBRT = auto()    # Stereotactic Body RT
    ELECTRON = auto() # Electron
    PROTON = auto()  # Proton Therapy

class RadiationType(Enum):
    """Loại bức xạ."""
    PHOTON = auto()
    ELECTRON = auto()
    PROTON = auto()

@dataclass
class BeamConfig:
    """
    Class chứa thông tin một chùm tia.
    """
    
    # Thông tin cơ bản
    name: str
    number: int
    type: TechniqueType
    radiation_type: RadiationType
    
    # Thông tin máy
    machine_name: str
    energy: str  # 6MV, 15MV, 6MeV, etc.
    
    # Thông tin hình học
    isocenter: Tuple[float, float, float]  # mm
    gantry_angle: float  # độ
    collimator_angle: float  # độ
    couch_angle: float  # độ
    
    # Thông tin field
    field_x: Tuple[float, float]  # mm, (X1, X2)
    field_y: Tuple[float, float]  # mm, (Y1, Y2)
    sad: float = 1000.0  # mm
    
    # Thông tin MLC
    mlc_type: str = 'MLCX'  # MLCX, MLCY
    mlc_segments: List[List[float]] = None  # Vị trí các lá MLC (mm)
    
    # Thông tin liều
    monitor_units: float = 100.0  # MU
    dose_rate: float = 600.0  # MU/min
    
    # Thông tin VMAT
    arc_direction: str = None  # CW, CC
    arc_start_angle: float = None  # độ
    arc_stop_angle: float = None  # độ
    
    # Thông tin bổ sung
    metadata: Dict[str, Any] = None
    
    @property
    def field_size(self) -> Tuple[float, float]:
        """Kích thước field (mm)."""
        return (
            abs(self.field_x[1] - self.field_x[0]),
            abs(self.field_y[1] - self.field_y[0])
        )
    
    @property
    def is_arc(self) -> bool:
        """Kiểm tra xem có phải là arc không."""
        return self.type == TechniqueType.VMAT
    
    @property
    def arc_length(self) -> float:
        """Độ dài cung (độ)."""
        if not self.is_arc:
            return 0.0
            
        if self.arc_direction == 'CW':
            if self.arc_stop_angle > self.arc_start_angle:
                return self.arc_stop_angle - self.arc_start_angle
            else:
                return 360.0 - (self.arc_start_angle - self.arc_stop_angle)
        else:  # CC
            if self.arc_stop_angle < self.arc_start_angle:
                return self.arc_start_angle - self.arc_stop_angle
            else:
                return 360.0 - (self.arc_stop_angle - self.arc_start_angle)

@dataclass
class PrescriptionConfig:
    """
    Class chứa thông tin kê đơn.
    """
    
    # Thông tin liều
    total_dose: float  # Gy
    fraction_count: int
    fraction_dose: float  # Gy
    
    # Thông tin target
    target_name: str
    target_type: str  # PTV, CTV, GTV
    target_coverage: float = 0.95  # % thể tích nhận đủ liều
    
    # Thông tin ràng buộc
    min_dose: float = None  # Gy
    max_dose: float = None  # Gy
    mean_dose: float = None  # Gy
    
    # Thông tin bổ sung
    metadata: Dict[str, Any] = None

@dataclass
class PlanConfig:
    """
    Class chứa thông tin kế hoạch xạ trị.
    """
    
    # Thông tin cơ bản
    plan_id: str
    plan_name: str
    technique: TechniqueType
    radiation_type: RadiationType
    
    # Thông tin máy
    machine_name: str
    energy: str  # 6MV, 15MV, 6MeV, etc.
    
    # Thông tin bệnh nhân
    patient_id: str
    patient_name: str
    patient_position: str  # HFS, HFP, FFS, FFP
    
    # Thông tin kê đơn
    prescription: PrescriptionConfig
    
    # Danh sách chùm tia
    beams: List[BeamConfig]
    
    # Thông tin tối ưu
    objectives: List[Dict[str, Any]] = None  # Danh sách mục tiêu tối ưu
    constraints: List[Dict[str, Any]] = None  # Danh sách ràng buộc
    
    # Thông tin thời gian
    created_time: datetime = None
    modified_time: datetime = None
    approved_time: datetime = None
    
    # Thông tin trạng thái
    is_approved: bool = False
    approved_by: str = None
    
    # Thông tin bổ sung
    metadata: Dict[str, Any] = None
    
    @property
    def num_beams(self) -> int:
        """Số lượng chùm tia."""
        return len(self.beams)
    
    @property
    def total_mu(self) -> float:
        """Tổng số MU."""
        return sum(beam.monitor_units for beam in self.beams)
    
    @property
    def is_approved(self) -> bool:
        """Kiểm tra xem kế hoạch đã được duyệt chưa."""
        return self.approved_time is not None and self.approved_by is not None
    
    def add_beam(self, beam: BeamConfig):
        """Thêm một chùm tia mới."""
        if any(b.name == beam.name for b in self.beams):
            raise ValueError(f"Chùm tia {beam.name} đã tồn tại")
        self.beams.append(beam)
    
    def remove_beam(self, beam_name: str):
        """Xóa một chùm tia."""
        self.beams = [b for b in self.beams if b.name != beam_name]
    
    def get_beam(self, beam_name: str) -> Optional[BeamConfig]:
        """Lấy thông tin một chùm tia."""
        for beam in self.beams:
            if beam.name == beam_name:
                return beam
        return None
    
    def approve(self, approver: str):
        """Duyệt kế hoạch."""
        self.approved_time = datetime.now()
        self.approved_by = approver
    
    def unapprove(self):
        """Hủy duyệt kế hoạch."""
        self.approved_time = None
        self.approved_by = None
    
    def copy(self, new_plan_id: str, new_plan_name: str) -> 'PlanConfig':
        """
        Tạo bản sao của kế hoạch.
        
        Args:
            new_plan_id: ID kế hoạch mới
            new_plan_name: Tên kế hoạch mới
            
        Returns:
            PlanConfig: Kế hoạch mới
        """
        import copy
        new_plan = copy.deepcopy(self)
        new_plan.plan_id = new_plan_id
        new_plan.plan_name = new_plan_name
        new_plan.created_time = datetime.now()
        new_plan.modified_time = datetime.now()
        new_plan.approved_time = None
        new_plan.approved_by = None
        return new_plan 