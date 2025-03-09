#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module quản lý Bolus cho QuangStation V2.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import matplotlib.pyplot as plt
from scipy import ndimage

class BolusModel:
    """Lớp mô phỏng và quản lý bolus trong xạ trị"""
    
    def __init__(self, name: str, density: float = 1.0, thickness_mm: float = 10.0):
        """
        Khởi tạo mô hình bolus
        
        Args:
            name: Tên bolus
            density: Mật độ của bolus (g/cm³)
            thickness_mm: Độ dày của bolus (mm)
        """
        self.name = name
        self.density = density
        self.thickness_mm = thickness_mm
        self.material = "tissue_equivalent"
        self.hu_value = 0  # HU value tương ứng với mật độ nước
        self.mask = None  # Mask 3D xác định vị trí bolus
        
    def create_rectangular_bolus(self, center_x: float, center_y: float, 
                               width: float, height: float, 
                               image_shape: Tuple[int, int, int], 
                               pixel_spacing: List[float]) -> np.ndarray:
        """
        Tạo bolus hình chữ nhật
        
        Args:
            center_x, center_y: Tọa độ tâm bolus (mm)
            width, height: Kích thước bolus (mm)
            image_shape: Kích thước ảnh (z, y, x)
            pixel_spacing: Khoảng cách pixel (mm) [z, y, x]
            
        Returns:
            Mask 3D chỉ ra vị trí bolus
        """
        # Tạo mask 2D
        z_dim, y_dim, x_dim = image_shape
        mask_2d = np.zeros((y_dim, x_dim), dtype=np.uint8)
        
        # Chuyển tọa độ mm sang chỉ số pixel
        center_x_pixel = int(center_x / pixel_spacing[2])
        center_y_pixel = int(center_y / pixel_spacing[1])
        half_width_pixel = int(width / 2 / pixel_spacing[2])
        half_height_pixel = int(height / 2 / pixel_spacing[1])
        
        # Xác định ranh giới bolus
        x_min = max(0, center_x_pixel - half_width_pixel)
        x_max = min(x_dim, center_x_pixel + half_width_pixel)
        y_min = max(0, center_y_pixel - half_height_pixel)
        y_max = min(y_dim, center_y_pixel + half_height_pixel)
        
        # Tạo mask hình chữ nhật
        mask_2d[y_min:y_max, x_min:x_max] = 1
        
        # Tìm lát cắt trên cùng của bệnh nhân
        patient_mask = self._find_patient_surface(image_shape, pixel_spacing)
        
        # Đặt bolus lên bề mặt bệnh nhân (chỉ trên một số lát cắt)
        thickness_slices = int(self.thickness_mm / pixel_spacing[0])
        mask_3d = np.zeros(image_shape, dtype=np.uint8)
        
        for z in range(z_dim):
            if np.any(patient_mask[z, :, :]):
                # Tìm vị trí đặt bolus: trên bề mặt bệnh nhân
                for y in range(y_dim):
                    for x in range(x_dim):
                        if mask_2d[y, x] == 1 and patient_mask[z, y, x] == 1:
                            # Đặt bolus ở đây và các lát cắt phía trên
                            for t in range(thickness_slices):
                                if z-t >= 0:
                                    mask_3d[z-t, y, x] = 1
                                    
        self.mask = mask_3d
        return mask_3d
    
    def create_contour_bolus(self, structure_mask: np.ndarray, 
                           margin_mm: float,
                           image_shape: Tuple[int, int, int],
                           pixel_spacing: List[float]) -> np.ndarray:
        """
        Tạo bolus bao quanh một cấu trúc
        
        Args:
            structure_mask: Mask 3D xác định cấu trúc
            margin_mm: Lề xung quanh cấu trúc (mm)
            image_shape: Kích thước ảnh (z, y, x)
            pixel_spacing: Khoảng cách pixel (mm) [z, y, x]
            
        Returns:
            Mask 3D chỉ ra vị trí bolus
        """
        # Chuyển margin từ mm sang pixel
        margin_pixel_y = int(margin_mm / pixel_spacing[1])
        margin_pixel_x = int(margin_mm / pixel_spacing[2])
        
        # Mở rộng cấu trúc
        structure_dilated = ndimage.binary_dilation(
            structure_mask, 
            iterations=max(margin_pixel_y, margin_pixel_x)
        ).astype(np.uint8)
        
        # Tìm lát cắt trên cùng của bệnh nhân
        patient_mask = self._find_patient_surface(image_shape, pixel_spacing)
        
        # Tìm bề mặt bệnh nhân
        surface_mask = self._extract_surface(patient_mask)
        
        # Đặt bolus trên bề mặt bệnh nhân, chỉ trong phần mở rộng cấu trúc
        thickness_slices = int(self.thickness_mm / pixel_spacing[0])
        mask_3d = np.zeros(image_shape, dtype=np.uint8)
        
        z_dim, y_dim, x_dim = image_shape
        for z in range(z_dim):
            for y in range(y_dim):
                for x in range(x_dim):
                    if structure_dilated[z, y, x] == 1 and surface_mask[z, y, x] == 1:
                        # Đặt bolus ở đây và các lát cắt phía trên
                        for t in range(thickness_slices):
                            if z-t >= 0:
                                mask_3d[z-t, y, x] = 1
                                    
        self.mask = mask_3d
        return mask_3d
    
    def _find_patient_surface(self, image_shape: Tuple[int, int, int], 
                            pixel_spacing: List[float]) -> np.ndarray:
        """
        Tạo mask giả lập bề mặt bệnh nhân
        
        Chú ý: Trong thực tế, cần khảo sát ảnh CT thực để tìm bề mặt
        
        Args:
            image_shape: Kích thước ảnh (z, y, x)
            pixel_spacing: Khoảng cách pixel (mm) [z, y, x]
            
        Returns:
            Mask 3D biểu diễn bề mặt bệnh nhân
        """
        # Giả lập một hình trụ làm bề mặt bệnh nhân
        z_dim, y_dim, x_dim = image_shape
        center_y, center_x = y_dim // 2, x_dim // 2
        radius_pixel = min(y_dim, x_dim) // 3
        
        mask = np.zeros(image_shape, dtype=np.uint8)
        
        for z in range(z_dim):
            for y in range(y_dim):
                for x in range(x_dim):
                    dist = np.sqrt((y - center_y)**2 + (x - center_x)**2)
                    if dist <= radius_pixel:
                        mask[z, y, x] = 1
                        
        return mask
    
    def _extract_surface(self, volume: np.ndarray) -> np.ndarray:
        """
        Trích xuất bề mặt từ một thể tích
        
        Args:
            volume: Ma trận 3D
            
        Returns:
            Ma trận 3D chỉ chứa bề mặt
        """
        # Dùng phép trừ để tìm bề mặt
        eroded = ndimage.binary_erosion(volume).astype(np.uint8)
        surface = volume - eroded
        
        return surface
    
    def apply_bolus_to_image(self, image_data: np.ndarray) -> np.ndarray:
        """
        Áp dụng bolus vào ảnh CT
        
        Args:
            image_data: Ma trận 3D chứa dữ liệu HU
            
        Returns:
            Ma trận 3D đã thêm bolus
        """
        if self.mask is None:
            raise ValueError("Bolus mask chưa được tạo")
            
        # Tạo bản sao của ảnh
        modified_image = image_data.copy()
        
        # Đặt giá trị HU tương ứng với bolus
        modified_image[self.mask == 1] = self.hu_value
        
        return modified_image
    
    def visualize_bolus(self, image_data: np.ndarray, slice_index: int, axis: str = 'axial'):
        """
        Hiển thị bolus trên ảnh CT
        
        Args:
            image_data: Ma trận 3D chứa dữ liệu HU
            slice_index: Chỉ số lát cắt cần hiển thị
            axis: Trục hiển thị ('axial', 'coronal', 'sagittal')
        """
        if self.mask is None:
            raise ValueError("Bolus mask chưa được tạo")
            
        # Lấy lát cắt tương ứng
        if axis == 'axial':
            image_slice = image_data[slice_index, :, :]
            bolus_slice = self.mask[slice_index, :, :]
        elif axis == 'coronal':
            image_slice = image_data[:, slice_index, :]
            bolus_slice = self.mask[:, slice_index, :]
        elif axis == 'sagittal':
            image_slice = image_data[:, :, slice_index]
            bolus_slice = self.mask[:, :, slice_index]
        else:
            raise ValueError(f"Trục không hợp lệ: {axis}")
            
        # Hiển thị
        fig, ax = plt.subplots(figsize=(10, 10))
        
        # Hiển thị ảnh CT với window/level
        ax.imshow(image_slice, cmap='gray', vmin=-1000, vmax=1000)
        
        # Hiển thị bolus với màu đỏ
        bolus_overlay = np.zeros((*bolus_slice.shape, 4), dtype=np.uint8)
        bolus_overlay[bolus_slice == 1] = [255, 0, 0, 128]  # RGBA với alpha=128
        ax.imshow(bolus_overlay)
        
        ax.set_title(f'Bolus trên lát cắt {slice_index} ({axis})')
        plt.tight_layout()
        plt.show()


class BolusManager:
    """Quản lý các bolus trong kế hoạch xạ trị"""
    
    def __init__(self):
        """Khởi tạo bolus manager"""
        self.bolus_list = {}
        self.material_density = {
            "tissue_equivalent": 1.0,
            "super_flab": 1.02,
            "aquaplast": 1.1,
            "paraffin_wax": 0.9,
            "brass": 8.5,
            "custom": 1.0
        }
        
    def add_bolus(self, name: str, material: str = "tissue_equivalent", 
                thickness_mm: float = 10.0) -> BolusModel:
        """
        Thêm bolus mới
        
        Args:
            name: Tên bolus
            material: Vật liệu bolus
            thickness_mm: Độ dày bolus (mm)
            
        Returns:
            BolusModel instance
        """
        density = self.material_density.get(material, 1.0)
        bolus = BolusModel(name, density, thickness_mm)
        bolus.material = material
        
        # Tính giá trị HU từ mật độ
        # HU = 1000 * (density - 1)
        bolus.hu_value = int(1000 * (density - 1))
        
        self.bolus_list[name] = bolus
        return bolus
    
    def get_bolus(self, name: str) -> Optional[BolusModel]:
        """Lấy bolus theo tên"""
        return self.bolus_list.get(name)
    
    def remove_bolus(self, name: str) -> bool:
        """Xóa bolus theo tên"""
        if name in self.bolus_list:
            del self.bolus_list[name]
            return True
        return False
    
    def get_available_materials(self) -> Dict[str, float]:
        """Trả về danh sách vật liệu bolus có sẵn"""
        return self.material_density.copy()
    
    def apply_all_bolus_to_image(self, image_data: np.ndarray) -> np.ndarray:
        """
        Áp dụng tất cả bolus vào ảnh CT
        
        Args:
            image_data: Ma trận 3D chứa dữ liệu HU
            
        Returns:
            Ma trận 3D đã thêm bolus
        """
        if not self.bolus_list:
            raise ValueError("Không có bolus để áp dụng")
            
        modified_image = image_data.copy()
        
        for bolus in self.bolus_list.values():
            modified_image = bolus.apply_bolus_to_image(modified_image)
            
        return modified_image 