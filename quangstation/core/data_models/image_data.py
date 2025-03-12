#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module định nghĩa cấu trúc dữ liệu cho hình ảnh y tế.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

@dataclass
class ImageData:
    """
    Class chứa dữ liệu hình ảnh y tế (CT, MRI, PET, SPECT).
    """
    
    # Dữ liệu pixel 3D
    pixel_array: np.ndarray
    
    # Thông tin không gian
    spacing: Tuple[float, float, float]  # mm, (x, y, z)
    origin: Tuple[float, float, float]  # mm, (x, y, z)
    direction: Tuple[float, float, float, float, float, float, float, float, float]  # Ma trận hướng 3x3
    
    # Metadata
    modality: str  # CT, MR, PT, NM
    patient_position: str  # HFS, HFP, FFS, FFP
    study_uid: str
    series_uid: str
    frame_of_reference_uid: str
    
    # Thông tin window/level
    window_center: float = 40  # HU
    window_width: float = 400  # HU
    
    # Thông tin rescale (cho CT)
    rescale_slope: float = 1.0
    rescale_intercept: float = -1024.0
    
    # Thông tin bổ sung
    metadata: Dict[str, Any] = None
    
    @property
    def shape(self) -> Tuple[int, int, int]:
        """Trả về kích thước dữ liệu (depth, height, width)."""
        return self.pixel_array.shape
    
    @property
    def num_slices(self) -> int:
        """Trả về số lượng slice."""
        return self.shape[0]
    
    @property
    def slice_positions(self) -> List[float]:
        """Tính vị trí các slice theo trục z."""
        return [self.origin[2] + i * self.spacing[2] for i in range(self.num_slices)]
    
    def get_slice(self, index: int, apply_window: bool = True) -> np.ndarray:
        """
        Lấy một slice từ thể tích dữ liệu.
        
        Args:
            index: Chỉ số slice
            apply_window: Áp dụng window/level
            
        Returns:
            np.ndarray: Slice 2D
        """
        if not 0 <= index < self.num_slices:
            raise IndexError(f"Chỉ số slice {index} nằm ngoài phạm vi [0, {self.num_slices-1}]")
            
        slice_data = self.pixel_array[index]
        
        if apply_window and self.modality == 'CT':
            # Chuyển về HU
            hu_data = slice_data * self.rescale_slope + self.rescale_intercept
            
            # Áp dụng window/level
            min_value = self.window_center - self.window_width / 2
            max_value = self.window_center + self.window_width / 2
            windowed = np.clip(hu_data, min_value, max_value)
            
            # Chuẩn hóa về [0, 255]
            normalized = ((windowed - min_value) / (max_value - min_value) * 255).astype(np.uint8)
            return normalized
            
        return slice_data
    
    def get_physical_coordinates(self, i: int, j: int, k: int) -> Tuple[float, float, float]:
        """
        Chuyển từ tọa độ voxel sang tọa độ vật lý (mm).
        
        Args:
            i, j, k: Tọa độ voxel
            
        Returns:
            Tuple[float, float, float]: Tọa độ vật lý (x, y, z) mm
        """
        x = self.origin[0] + i * self.spacing[0]
        y = self.origin[1] + j * self.spacing[1]
        z = self.origin[2] + k * self.spacing[2]
        return (x, y, z)
    
    def get_voxel_coordinates(self, x: float, y: float, z: float) -> Tuple[int, int, int]:
        """
        Chuyển từ tọa độ vật lý (mm) sang tọa độ voxel.
        
        Args:
            x, y, z: Tọa độ vật lý (mm)
            
        Returns:
            Tuple[int, int, int]: Tọa độ voxel (i, j, k)
        """
        i = int(round((x - self.origin[0]) / self.spacing[0]))
        j = int(round((y - self.origin[1]) / self.spacing[1]))
        k = int(round((z - self.origin[2]) / self.spacing[2]))
        return (i, j, k)
    
    def resample(self, new_spacing: Tuple[float, float, float]) -> 'ImageData':
        """
        Tạo bản sao của dữ liệu với spacing mới.
        
        Args:
            new_spacing: Spacing mới (mm)
            
        Returns:
            ImageData: Dữ liệu đã được resample
        """
        from scipy.ndimage import zoom
        
        # Tính tỷ lệ scaling
        scale = (
            self.spacing[0] / new_spacing[0],
            self.spacing[1] / new_spacing[1],
            self.spacing[2] / new_spacing[2]
        )
        
        # Resample dữ liệu
        resampled = zoom(self.pixel_array, scale, order=1)
        
        # Tạo bản sao với dữ liệu mới
        return ImageData(
            pixel_array=resampled,
            spacing=new_spacing,
            origin=self.origin,
            direction=self.direction,
            modality=self.modality,
            patient_position=self.patient_position,
            study_uid=self.study_uid,
            series_uid=self.series_uid,
            frame_of_reference_uid=self.frame_of_reference_uid,
            window_center=self.window_center,
            window_width=self.window_width,
            rescale_slope=self.rescale_slope,
            rescale_intercept=self.rescale_intercept,
            metadata=self.metadata
        ) 