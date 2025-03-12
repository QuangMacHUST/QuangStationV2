#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module định nghĩa cấu trúc dữ liệu cho thông tin chùm tia xạ trị.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum, auto
import numpy as np

class RadiationType(Enum):
    """Loại bức xạ."""
    PHOTON = "photon"
    ELECTRON = "electron"
    PROTON = "proton"
    NEUTRON = "neutron"
    CARBON = "carbon"
    COBALT = "cobalt"
    
class CollimatorType(Enum):
    """Loại collimator."""
    SYMMETRIC = "symmetric"
    ASYMMETRIC = "asymmetric"
    MLC = "mlc"
    MLCX = "mlcx"
    CIRCULAR = "circular"
    
class MLCType(Enum):
    """Kiểu Multi-Leaf Collimator."""
    STATIC = "static"
    DYNAMIC = "dynamic"
    STEP_AND_SHOOT = "step_and_shoot"
    
class BeamType(Enum):
    """Loại chùm tia."""
    STATIC = "static"
    ARC = "arc"
    VMAT = "vmat"
    CONFORMAL_ARC = "conformal_arc"
    ELECTRON = "electron"
    PROTON = "proton"
    SETUP = "setup"
    
@dataclass
class MLCPosition:
    """Vị trí của Multi-Leaf Collimator."""
    bank_a: List[float]  # Vị trí lá MLC bank A (mm)
    bank_b: List[float]  # Vị trí lá MLC bank B (mm)
    
    @property
    def num_leaves(self) -> int:
        """Số lượng lá MLC."""
        return len(self.bank_a)
    
    def get_aperture(self) -> List[float]:
        """Trả về độ mở của từng cặp lá (mm)."""
        return [abs(self.bank_b[i] - self.bank_a[i]) for i in range(self.num_leaves)]
    
    def get_center(self) -> List[float]:
        """Trả về tâm của từng cặp lá (mm)."""
        return [(self.bank_b[i] + self.bank_a[i]) / 2 for i in range(self.num_leaves)]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MLCPosition':
        """Tạo đối tượng MLCPosition từ dict."""
        return cls(
            bank_a=data.get('bank_a', []),
            bank_b=data.get('bank_b', [])
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi sang dict."""
        return {
            'bank_a': self.bank_a,
            'bank_b': self.bank_b
        }

@dataclass
class MLCSequence:
    """Chuỗi vị trí MLC cho điều biến cường độ."""
    positions: List[MLCPosition] = field(default_factory=list)  # Danh sách các vị trí MLC
    control_points: List[float] = field(default_factory=list)  # Các điểm kiểm soát (0-1)
    cumulative_meterset: List[float] = field(default_factory=list)  # Meterset tích lũy
    
    def add_position(self, position: MLCPosition, control_point: float, meterset: float):
        """Thêm một vị trí MLC vào chuỗi."""
        self.positions.append(position)
        self.control_points.append(control_point)
        self.cumulative_meterset.append(meterset)
    
    @property
    def num_control_points(self) -> int:
        """Số lượng điểm kiểm soát."""
        return len(self.positions)
    
    def get_position_at(self, control_point: float) -> MLCPosition:
        """
        Lấy vị trí MLC tại điểm kiểm soát cụ thể.
        
        Args:
            control_point: Điểm kiểm soát (0-1)
            
        Returns:
            MLCPosition: Vị trí MLC nội suy
        """
        if not self.positions:
            raise ValueError("Không có vị trí MLC nào")
            
        if control_point <= self.control_points[0]:
            return self.positions[0]
            
        if control_point >= self.control_points[-1]:
            return self.positions[-1]
            
        # Tìm đoạn chứa control_point
        for i in range(len(self.control_points) - 1):
            if self.control_points[i] <= control_point <= self.control_points[i+1]:
                # Nội suy tuyến tính
                t = (control_point - self.control_points[i]) / (self.control_points[i+1] - self.control_points[i])
                
                pos_a = self.positions[i]
                pos_b = self.positions[i+1]
                
                # Nội suy bank A
                bank_a = [pos_a.bank_a[j] + t * (pos_b.bank_a[j] - pos_a.bank_a[j]) 
                          for j in range(pos_a.num_leaves)]
                
                # Nội suy bank B
                bank_b = [pos_a.bank_b[j] + t * (pos_b.bank_b[j] - pos_a.bank_b[j]) 
                          for j in range(pos_a.num_leaves)]
                
                return MLCPosition(bank_a=bank_a, bank_b=bank_b)
                
        # Không tìm thấy đoạn phù hợp (không nên xảy ra)
        return self.positions[0]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MLCSequence':
        """Tạo đối tượng MLCSequence từ dict."""
        seq = cls()
        
        positions_data = data.get('positions', [])
        control_points = data.get('control_points', [])
        meterset = data.get('cumulative_meterset', [])
        
        for i in range(len(positions_data)):
            pos = MLCPosition.from_dict(positions_data[i])
            cp = control_points[i] if i < len(control_points) else 0
            ms = meterset[i] if i < len(meterset) else 0
            seq.add_position(pos, cp, ms)
            
        return seq
    
    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi sang dict."""
        return {
            'positions': [pos.to_dict() for pos in self.positions],
            'control_points': self.control_points,
            'cumulative_meterset': self.cumulative_meterset
        }

@dataclass
class BeamData:
    """
    Class chứa thông tin về chùm tia xạ trị.
    """
    
    # Thông tin cơ bản
    beam_id: str  # ID chùm tia (B1, B2, ...)
    beam_name: str  # Tên chùm tia
    beam_type: BeamType  # Loại chùm tia
    radiation_type: RadiationType  # Loại bức xạ
    
    # Thông tin hình học
    isocenter: Tuple[float, float, float]  # Vị trí tâm iso (mm)
    gantry_angle: float  # Góc gantry (độ)
    collimator_angle: float  # Góc collimator (độ)
    couch_angle: float  # Góc bàn (độ)
    
    # Thông tin năng lượng
    energy: float  # Năng lượng (MV hoặc MeV)
    dose_rate: float  # Tốc độ liều (MU/phút)
    
    # Thông tin MU
    monitor_units: float  # Số lượng Monitor Units
    
    # Thông tin kích thước trường
    field_size: Tuple[float, float] = (100.0, 100.0)  # Kích thước trường (mm)
    sad: float = 1000.0  # Source-Axis Distance (mm)
    
    # Thông tin thêm cho chùm tia arc
    arc_start_angle: Optional[float] = None  # Góc bắt đầu arc (độ)
    arc_stop_angle: Optional[float] = None  # Góc kết thúc arc (độ)
    arc_direction: Optional[str] = None  # Chiều quay (CW/CCW)
    
    # Thông tin colimator
    collimator_type: CollimatorType = CollimatorType.ASYMMETRIC
    
    # Thông tin MLC
    mlc_type: Optional[MLCType] = None
    mlc_positions: Optional[Union[MLCPosition, MLCSequence]] = None
    
    # Thông tin bổ sung
    bolus: bool = False  # Có sử dụng bolus không
    bolus_material: Optional[str] = None  # Vật liệu bolus
    bolus_thickness: Optional[float] = None  # Độ dày bolus (mm)
    
    # Thông tin tính toán
    source_to_surface_distance: Optional[float] = None  # SSD (mm)
    effective_depth: Optional[float] = None  # Độ sâu hiệu dụng (mm)
    wedge_factor: Optional[float] = None  # Hệ số wedge
    
    # Thông tin phụ
    description: Optional[str] = None  # Mô tả chùm tia
    setup_notes: Optional[str] = None  # Ghi chú thiết lập
    contribution: Optional[float] = None  # Đóng góp vào tổng liều (%)
    
    # Thông tin khác
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_field_borders(self) -> Tuple[float, float, float, float]:
        """
        Lấy ranh giới trường tại mặt phẳng isocenter.
        
        Returns:
            Tuple[float, float, float, float]: X1, X2, Y1, Y2 (mm)
        """
        width, height = self.field_size
        x1 = -width / 2
        x2 = width / 2
        y1 = -height / 2
        y2 = height / 2
        return (x1, x2, y1, y2)
    
    def set_field_borders(self, x1: float, x2: float, y1: float, y2: float):
        """
        Thiết lập ranh giới trường.
        
        Args:
            x1, x2, y1, y2: Ranh giới trường (mm)
        """
        width = abs(x2 - x1)
        height = abs(y2 - y1)
        self.field_size = (width, height)
    
    def calculate_ssd(self, skin_surface_distance: float) -> float:
        """
        Tính Source-to-Surface Distance.
        
        Args:
            skin_surface_distance: Khoảng cách từ isocenter đến bề mặt da (mm)
            
        Returns:
            float: SSD (mm)
        """
        return self.sad - skin_surface_distance
    
    def is_modulated(self) -> bool:
        """
        Kiểm tra xem chùm tia có điều biến không.
        
        Returns:
            bool: True nếu chùm tia được điều biến cường độ
        """
        modulated_types = [BeamType.VMAT, BeamType.CONFORMAL_ARC]
        if self.beam_type in modulated_types:
            return True
            
        if self.mlc_type in [MLCType.DYNAMIC, MLCType.STEP_AND_SHOOT]:
            return True
            
        if isinstance(self.mlc_positions, MLCSequence) and self.mlc_positions.num_control_points > 1:
            return True
            
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Chuyển đổi thành dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary chứa thông tin chùm tia
        """
        result = {
            "beam_id": self.beam_id,
            "beam_name": self.beam_name,
            "beam_type": self.beam_type.value,
            "radiation_type": self.radiation_type.value,
            "isocenter": list(self.isocenter),
            "gantry_angle": self.gantry_angle,
            "collimator_angle": self.collimator_angle,
            "couch_angle": self.couch_angle,
            "energy": self.energy,
            "dose_rate": self.dose_rate,
            "monitor_units": self.monitor_units,
            "field_size": list(self.field_size),
            "sad": self.sad,
            "collimator_type": self.collimator_type.value,
            "bolus": self.bolus
        }
        
        # Thêm các trường tùy chọn
        if self.mlc_type:
            result["mlc_type"] = self.mlc_type.value
            
        if self.mlc_positions:
            if isinstance(self.mlc_positions, MLCPosition):
                result["mlc_positions"] = self.mlc_positions.to_dict()
                result["mlc_sequence"] = False
            elif isinstance(self.mlc_positions, MLCSequence):
                result["mlc_positions"] = self.mlc_positions.to_dict()
                result["mlc_sequence"] = True
                
        if self.arc_start_angle is not None:
            result["arc_start_angle"] = self.arc_start_angle
            result["arc_stop_angle"] = self.arc_stop_angle
            result["arc_direction"] = self.arc_direction
            
        # Thêm metadata
        result["metadata"] = self.metadata
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BeamData':
        """
        Tạo đối tượng BeamData từ dictionary.
        
        Args:
            data: Dictionary chứa thông tin chùm tia
            
        Returns:
            BeamData: Đối tượng chùm tia
        """
        # Chuyển đổi enum
        beam_type = BeamType(data.get("beam_type", "static"))
        radiation_type = RadiationType(data.get("radiation_type", "photon"))
        collimator_type = CollimatorType(data.get("collimator_type", "asymmetric"))
        
        # Chuyển đổi MLCType nếu có
        mlc_type = None
        if "mlc_type" in data:
            mlc_type = MLCType(data.get("mlc_type"))
            
        # Chuyển đổi MLC positions
        mlc_positions = None
        if "mlc_positions" in data:
            if data.get("mlc_sequence", False):
                mlc_positions = MLCSequence.from_dict(data.get("mlc_positions"))
            else:
                mlc_positions = MLCPosition.from_dict(data.get("mlc_positions"))
                
        # Chuyển đổi field size
        field_size = tuple(data.get("field_size", (100.0, 100.0)))
        
        # Tạo đối tượng
        return cls(
            beam_id=data.get("beam_id", ""),
            beam_name=data.get("beam_name", ""),
            beam_type=beam_type,
            radiation_type=radiation_type,
            isocenter=tuple(data.get("isocenter", (0, 0, 0))),
            gantry_angle=data.get("gantry_angle", 0),
            collimator_angle=data.get("collimator_angle", 0),
            couch_angle=data.get("couch_angle", 0),
            energy=data.get("energy", 6),
            dose_rate=data.get("dose_rate", 600),
            monitor_units=data.get("monitor_units", 100),
            field_size=field_size,
            sad=data.get("sad", 1000.0),
            arc_start_angle=data.get("arc_start_angle"),
            arc_stop_angle=data.get("arc_stop_angle"),
            arc_direction=data.get("arc_direction"),
            collimator_type=collimator_type,
            mlc_type=mlc_type,
            mlc_positions=mlc_positions,
            bolus=data.get("bolus", False),
            bolus_material=data.get("bolus_material"),
            bolus_thickness=data.get("bolus_thickness"),
            source_to_surface_distance=data.get("source_to_surface_distance"),
            effective_depth=data.get("effective_depth"),
            wedge_factor=data.get("wedge_factor"),
            description=data.get("description"),
            setup_notes=data.get("setup_notes"),
            contribution=data.get("contribution"),
            metadata=data.get("metadata", {})
        )
