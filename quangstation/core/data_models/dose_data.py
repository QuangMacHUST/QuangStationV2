#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module định nghĩa cấu trúc dữ liệu cho phân bố liều.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum, auto

class DoseType(Enum):
    """Loại liều."""
    PHYSICAL = auto()  # Liều vật lý (Gy)
    EFFECTIVE = auto()  # Liều hiệu dụng (Gy)
    EQUIVALENT = auto()  # Liều tương đương (Sv)
    RELATIVE = auto()   # Liều tương đối (%)

@dataclass
class DoseData:
    """
    Class chứa dữ liệu phân bố liều.
    """
    
    # Dữ liệu liều 3D
    dose_matrix: np.ndarray  # Gy
    
    # Thông tin không gian
    spacing: Tuple[float, float, float]  # mm, (x, y, z)
    origin: Tuple[float, float, float]  # mm, (x, y, z)
    direction: Tuple[float, float, float, float, float, float, float, float, float]  # Ma trận hướng 3x3
    
    # Thông tin liều
    dose_type: DoseType
    dose_unit: str  # GY, CGY, %
    dose_summation_type: str  # PLAN, BEAM, FRACTION, BRACHY
    
    # Thông tin tham chiếu
    referenced_plan_uid: str = None
    referenced_beam_number: int = None
    referenced_fraction_number: int = None
    
    # Thông tin bổ sung
    metadata: Dict[str, Any] = None
    
    @property
    def shape(self) -> Tuple[int, int, int]:
        """Kích thước của phân bố liều."""
        return self.dose_matrix.shape
    
    @property
    def min_dose(self) -> float:
        """Liều nhỏ nhất (Gy)."""
        return float(np.min(self.dose_matrix))
    
    @property
    def max_dose(self) -> float:
        """Liều lớn nhất (Gy)."""
        return float(np.max(self.dose_matrix))
    
    @property
    def mean_dose(self) -> float:
        """Liều trung bình (Gy)."""
        return float(np.mean(self.dose_matrix))
    
    def get_slice(self, index: int) -> np.ndarray:
        """
        Lấy một slice từ phân bố liều.
        
        Args:
            index: Chỉ số slice
            
        Returns:
            np.ndarray: Slice 2D
        """
        if not 0 <= index < self.shape[0]:
            raise IndexError(f"Chỉ số slice {index} nằm ngoài phạm vi [0, {self.shape[0]-1}]")
        return self.dose_matrix[index]
    
    def get_dose_at_point(self, x: float, y: float, z: float) -> float:
        """
        Lấy giá trị liều tại một điểm trong không gian.
        
        Args:
            x, y, z: Tọa độ điểm (mm)
            
        Returns:
            float: Giá trị liều (Gy)
        """
        # Chuyển từ tọa độ vật lý sang chỉ số voxel
        i = int(round((x - self.origin[0]) / self.spacing[0]))
        j = int(round((y - self.origin[1]) / self.spacing[1]))
        k = int(round((z - self.origin[2]) / self.spacing[2]))
        
        # Kiểm tra chỉ số có hợp lệ không
        if not (0 <= i < self.shape[2] and 0 <= j < self.shape[1] and 0 <= k < self.shape[0]):
            return 0.0
            
        return float(self.dose_matrix[k, j, i])
    
    def get_dose_profile(self, start_point: Tuple[float, float, float],
                        end_point: Tuple[float, float, float],
                        num_points: int = 100) -> Tuple[List[float], List[float]]:
        """
        Lấy profile liều theo một đường thẳng.
        
        Args:
            start_point: Điểm đầu (mm)
            end_point: Điểm cuối (mm)
            num_points: Số điểm lấy mẫu
            
        Returns:
            Tuple[List[float], List[float]]: (distances, doses)
                distances: Khoảng cách từ điểm đầu (mm)
                doses: Giá trị liều tại các điểm (Gy)
        """
        # Tính vector hướng
        direction = np.array(end_point) - np.array(start_point)
        length = np.linalg.norm(direction)
        direction = direction / length
        
        # Tạo các điểm lấy mẫu
        distances = np.linspace(0, length, num_points)
        points = np.array(start_point) + direction.reshape(3, 1) * distances.reshape(1, -1)
        
        # Lấy giá trị liều tại các điểm
        doses = [self.get_dose_at_point(x, y, z) for x, y, z in points.T]
        
        return list(distances), doses
    
    def get_isodose_contours(self, dose_level: float, slice_index: int) -> List[np.ndarray]:
        """
        Lấy các đường đồng liều trên một slice.
        
        Args:
            dose_level: Mức liều (Gy)
            slice_index: Chỉ số slice
            
        Returns:
            List[np.ndarray]: Danh sách các contour, mỗi contour là mảng Nx2
        """
        import cv2
        
        # Lấy slice
        if not 0 <= slice_index < self.shape[0]:
            return []
            
        slice_data = self.dose_matrix[slice_index]
        
        # Tạo mask cho mức liều
        mask = (slice_data >= dose_level).astype(np.uint8)
        
        # Tìm contour bằng OpenCV
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        
        # Chuyển về dạng numpy array
        return [contour.squeeze() for contour in contours if len(contour) > 2]
    
    def resample(self, new_spacing: Tuple[float, float, float]) -> 'DoseData':
        """
        Tạo bản sao của dữ liệu với spacing mới.
        
        Args:
            new_spacing: Spacing mới (mm)
            
        Returns:
            DoseData: Dữ liệu đã được resample
        """
        from scipy.ndimage import zoom
        
        # Tính tỷ lệ scaling
        scale = (
            self.spacing[0] / new_spacing[0],
            self.spacing[1] / new_spacing[1],
            self.spacing[2] / new_spacing[2]
        )
        
        # Resample dữ liệu
        resampled = zoom(self.dose_matrix, scale, order=1)
        
        # Tạo bản sao với dữ liệu mới
        return DoseData(
            dose_matrix=resampled,
            spacing=new_spacing,
            origin=self.origin,
            direction=self.direction,
            dose_type=self.dose_type,
            dose_unit=self.dose_unit,
            dose_summation_type=self.dose_summation_type,
            referenced_plan_uid=self.referenced_plan_uid,
            referenced_beam_number=self.referenced_beam_number,
            referenced_fraction_number=self.referenced_fraction_number,
            metadata=self.metadata
        )
    
    def normalize(self, normalization_value: float) -> 'DoseData':
        """
        Chuẩn hóa phân bố liều theo một giá trị.
        
        Args:
            normalization_value: Giá trị chuẩn hóa (Gy)
            
        Returns:
            DoseData: Phân bố liều đã chuẩn hóa
        """
        if normalization_value <= 0:
            raise ValueError("Giá trị chuẩn hóa phải dương")
            
        # Tạo bản sao
        normalized = DoseData(
            dose_matrix=self.dose_matrix * (100.0 / normalization_value),
            spacing=self.spacing,
            origin=self.origin,
            direction=self.direction,
            dose_type=DoseType.RELATIVE,
            dose_unit='%',
            dose_summation_type=self.dose_summation_type,
            referenced_plan_uid=self.referenced_plan_uid,
            referenced_beam_number=self.referenced_beam_number,
            referenced_fraction_number=self.referenced_fraction_number,
            metadata=self.metadata
        )
        
        return normalized 