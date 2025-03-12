#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module định nghĩa cấu trúc dữ liệu cho cấu trúc giải phẫu.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum, auto

class StructureType(Enum):
    """Loại cấu trúc."""
    TARGET = auto()  # PTV, CTV, GTV
    OAR = auto()    # Cơ quan nguy cấp
    EXTERNAL = auto()  # Body
    SUPPORT = auto()  # Bàn điều trị, mask
    OTHER = auto()   # Khác

@dataclass
class Structure:
    """
    Class chứa thông tin một cấu trúc.
    """
    
    # Thông tin cơ bản
    name: str
    type: StructureType
    number: int
    
    # Dữ liệu mask 3D
    mask: np.ndarray
    
    # Thông tin hiển thị
    color: Tuple[float, float, float]  # RGB [0, 1]
    opacity: float = 0.5
    visible: bool = True
    
    # Thông tin bổ sung
    metadata: Dict[str, Any] = None
    
    @property
    def volume(self) -> float:
        """Tính thể tích cấu trúc (mm3)."""
        return float(np.sum(self.mask))
    
    @property
    def center_of_mass(self) -> Tuple[float, float, float]:
        """Tính tâm khối của cấu trúc."""
        if not np.any(self.mask):
            return (0.0, 0.0, 0.0)
            
        indices = np.where(self.mask)
        center = np.mean(indices, axis=1)
        return tuple(float(x) for x in center)
    
    def get_bounding_box(self) -> Tuple[slice, slice, slice]:
        """
        Lấy hộp bao quanh cấu trúc.
        
        Returns:
            Tuple[slice, slice, slice]: Các slice để cắt ra vùng chứa cấu trúc
        """
        if not np.any(self.mask):
            return (slice(0, 0), slice(0, 0), slice(0, 0))
            
        indices = np.where(self.mask)
        starts = [int(np.min(idx)) for idx in indices]
        ends = [int(np.max(idx)) + 1 for idx in indices]
        return tuple(slice(start, end) for start, end in zip(starts, ends))
    
    def get_contours(self, slice_index: int) -> List[np.ndarray]:
        """
        Lấy các contour trên một slice.
        
        Args:
            slice_index: Chỉ số slice
            
        Returns:
            List[np.ndarray]: Danh sách các contour, mỗi contour là mảng Nx2
        """
        import cv2
        
        # Lấy slice mask
        if not 0 <= slice_index < self.mask.shape[0]:
            return []
            
        slice_mask = self.mask[slice_index].astype(np.uint8)
        
        # Tìm contour bằng OpenCV
        contours, _ = cv2.findContours(slice_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        
        # Chuyển về dạng numpy array
        return [contour.squeeze() for contour in contours if len(contour) > 2]
    
    def create_margin(self, margin_mm: float, spacing: Tuple[float, float, float]) -> 'Structure':
        """
        Tạo cấu trúc mới bằng cách thêm/bớt margin.
        
        Args:
            margin_mm: Độ rộng margin (mm), dương để mở rộng, âm để thu nhỏ
            spacing: Khoảng cách giữa các voxel (mm)
            
        Returns:
            Structure: Cấu trúc mới với margin
        """
        from scipy.ndimage import binary_dilation, binary_erosion
        
        # Chuyển margin từ mm sang voxel
        margin_voxels = [int(round(abs(margin_mm) / s)) for s in spacing]
        
        # Tạo kernel hình cầu
        from scipy.ndimage import generate_binary_structure
        kernel = generate_binary_structure(3, 1)
        
        # Áp dụng margin
        if margin_mm >= 0:
            new_mask = binary_dilation(self.mask, kernel, iterations=max(margin_voxels))
        else:
            new_mask = binary_erosion(self.mask, kernel, iterations=max(margin_voxels))
            
        # Tạo cấu trúc mới
        return Structure(
            name=f"{self.name}_margin{margin_mm:+.1f}mm",
            type=self.type,
            number=self.number,
            mask=new_mask,
            color=self.color,
            opacity=self.opacity,
            visible=self.visible,
            metadata=self.metadata
        )

@dataclass
class StructureSet:
    """
    Class quản lý tập hợp các cấu trúc.
    """
    
    # Dict chứa các cấu trúc, key là tên cấu trúc
    structures: Dict[str, Structure]
    
    # Thông tin không gian
    spacing: Tuple[float, float, float]  # mm, (x, y, z)
    origin: Tuple[float, float, float]  # mm, (x, y, z)
    direction: Tuple[float, float, float, float, float, float, float, float, float]  # Ma trận hướng 3x3
    
    # Metadata
    study_uid: str
    series_uid: str
    frame_of_reference_uid: str
    structure_set_uid: str
    
    # Thông tin bổ sung
    metadata: Dict[str, Any] = None
    
    def __getitem__(self, key: str) -> Structure:
        """Lấy cấu trúc theo tên."""
        return self.structures[key]
    
    def __iter__(self):
        """Duyệt qua các cấu trúc."""
        return iter(self.structures.values())
    
    def __len__(self) -> int:
        """Số lượng cấu trúc."""
        return len(self.structures)
    
    @property
    def shape(self) -> Tuple[int, int, int]:
        """Kích thước của mask."""
        if not self.structures:
            return (0, 0, 0)
        return next(iter(self.structures.values())).mask.shape
    
    def get_targets(self) -> List[Structure]:
        """Lấy danh sách các cấu trúc target."""
        return [s for s in self if s.type == StructureType.TARGET]
    
    def get_oars(self) -> List[Structure]:
        """Lấy danh sách các cơ quan nguy cấp."""
        return [s for s in self if s.type == StructureType.OAR]
    
    def get_external(self) -> Optional[Structure]:
        """Lấy cấu trúc external (body)."""
        for s in self:
            if s.type == StructureType.EXTERNAL:
                return s
        return None
    
    def add_structure(self, structure: Structure):
        """Thêm một cấu trúc mới."""
        if structure.name in self.structures:
            raise ValueError(f"Cấu trúc {structure.name} đã tồn tại")
        self.structures[structure.name] = structure
    
    def remove_structure(self, name: str):
        """Xóa một cấu trúc."""
        if name in self.structures:
            del self.structures[name]
    
    def rename_structure(self, old_name: str, new_name: str):
        """Đổi tên một cấu trúc."""
        if old_name not in self.structures:
            raise ValueError(f"Không tìm thấy cấu trúc {old_name}")
        if new_name in self.structures:
            raise ValueError(f"Cấu trúc {new_name} đã tồn tại")
            
        structure = self.structures.pop(old_name)
        structure.name = new_name
        self.structures[new_name] = structure
    
    def create_union(self, names: List[str], new_name: str) -> Structure:
        """
        Tạo cấu trúc mới bằng phép hợp các cấu trúc.
        
        Args:
            names: Danh sách tên các cấu trúc
            new_name: Tên cấu trúc mới
            
        Returns:
            Structure: Cấu trúc mới
        """
        if not names:
            raise ValueError("Danh sách cấu trúc trống")
            
        # Lấy các cấu trúc
        structures = [self[name] for name in names]
        
        # Tính union mask
        union_mask = np.zeros_like(structures[0].mask)
        for structure in structures:
            union_mask = np.logical_or(union_mask, structure.mask)
            
        # Tạo cấu trúc mới
        union = Structure(
            name=new_name,
            type=structures[0].type,
            number=max(s.number for s in structures) + 1,
            mask=union_mask,
            color=(1.0, 0.0, 0.0),  # Đỏ
            opacity=0.5,
            visible=True
        )
        
        # Thêm vào structure set
        self.add_structure(union)
        return union
    
    def create_intersection(self, names: List[str], new_name: str) -> Structure:
        """
        Tạo cấu trúc mới bằng phép giao các cấu trúc.
        
        Args:
            names: Danh sách tên các cấu trúc
            new_name: Tên cấu trúc mới
            
        Returns:
            Structure: Cấu trúc mới
        """
        if not names:
            raise ValueError("Danh sách cấu trúc trống")
            
        # Lấy các cấu trúc
        structures = [self[name] for name in names]
        
        # Tính intersection mask
        intersection_mask = np.ones_like(structures[0].mask)
        for structure in structures:
            intersection_mask = np.logical_and(intersection_mask, structure.mask)
            
        # Tạo cấu trúc mới
        intersection = Structure(
            name=new_name,
            type=structures[0].type,
            number=max(s.number for s in structures) + 1,
            mask=intersection_mask,
            color=(0.0, 1.0, 0.0),  # Xanh lá
            opacity=0.5,
            visible=True
        )
        
        # Thêm vào structure set
        self.add_structure(intersection)
        return intersection
    
    def create_subtraction(self, name1: str, name2: str, new_name: str) -> Structure:
        """
        Tạo cấu trúc mới bằng phép trừ hai cấu trúc.
        
        Args:
            name1: Tên cấu trúc bị trừ
            name2: Tên cấu trúc trừ đi
            new_name: Tên cấu trúc mới
            
        Returns:
            Structure: Cấu trúc mới
        """
        # Lấy các cấu trúc
        structure1 = self[name1]
        structure2 = self[name2]
        
        # Tính subtraction mask
        subtraction_mask = np.logical_and(structure1.mask, np.logical_not(structure2.mask))
        
        # Tạo cấu trúc mới
        subtraction = Structure(
            name=new_name,
            type=structure1.type,
            number=max(structure1.number, structure2.number) + 1,
            mask=subtraction_mask,
            color=(0.0, 0.0, 1.0),  # Xanh dương
            opacity=0.5,
            visible=True
        )
        
        # Thêm vào structure set
        self.add_structure(subtraction)
        return subtraction 