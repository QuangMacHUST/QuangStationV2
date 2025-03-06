"""
Module bản đồ liều xạ trị cho hệ thống QuangStation V2
Cung cấp các công cụ để hiển thị, phân tích và đánh giá phân bố liều
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.figure import Figure
from typing import Dict, List, Tuple, Optional, Union
import os
import json
from datetime import datetime

from utils.logging import get_logger
from utils.config import get_config

logger = get_logger("DoseMap")

class DoseMap:
    """Lớp quản lý và hiển thị bản đồ liều xạ trị"""
    
    def __init__(self, dose_data: np.ndarray = None, dose_grid_scaling: float = 1.0, 
                 voxel_size: List[float] = None):
        """
        Khởi tạo đối tượng bản đồ liều
        
        Args:
            dose_data (np.ndarray): Dữ liệu liều 3D
            dose_grid_scaling (float): Hệ số tỷ lệ liều (Gy/giá trị)
            voxel_size (List[float]): Kích thước voxel [x, y, z] (mm)
        """
        self.dose_data = dose_data
        self.dose_grid_scaling = dose_grid_scaling
        self.voxel_size = voxel_size if voxel_size else [1.0, 1.0, 1.0]
        self.structures = {}  # Từ điển lưu trữ các cấu trúc (masks)
        self.isocenter = None  # Tọa độ tâm xạ trị
        self.prescription_dose = None  # Liều kê toa (Gy)
        
        # Cấu hình màu sắc mặc định
        self.colormap = plt.cm.jet
        self.alpha = 0.7  # Độ trong suốt mặc định
        
        logger.info("Khởi tạo đối tượng DoseMap")
    
    def set_dose_data(self, dose_data: np.ndarray, dose_grid_scaling: float = None, 
                     voxel_size: List[float] = None):
        """
        Cập nhật dữ liệu liều
        
        Args:
            dose_data (np.ndarray): Dữ liệu liều 3D
            dose_grid_scaling (float): Hệ số tỷ lệ liều (Gy/giá trị)
            voxel_size (List[float]): Kích thước voxel [x, y, z] (mm)
        """
        self.dose_data = dose_data
        if dose_grid_scaling:
            self.dose_grid_scaling = dose_grid_scaling
        if voxel_size:
            self.voxel_size = voxel_size
        
        logger.info(f"Cập nhật dữ liệu liều: shape={dose_data.shape}, scaling={self.dose_grid_scaling}")
    
    def add_structure(self, name: str, mask: np.ndarray, color: str = None):
        """
        Thêm cấu trúc (mask) vào bản đồ liều
        
        Args:
            name (str): Tên cấu trúc
            mask (np.ndarray): Mặt nạ nhị phân 3D của cấu trúc
            color (str): Mã màu cho cấu trúc (hex hoặc tên màu)
        """
        if mask.shape != self.dose_data.shape:
            logger.warning(f"Kích thước mask ({mask.shape}) không khớp với dữ liệu liều ({self.dose_data.shape})")
            return False
        
        # Gán màu ngẫu nhiên nếu không được chỉ định
        if not color:
            import random
            r = random.randint(0, 255)
            g = random.randint(0, 255)
            b = random.randint(0, 255)
            color = f"#{r:02x}{g:02x}{b:02x}"
        
        self.structures[name] = {
            "mask": mask,
            "color": color
        }
        
        logger.info(f"Đã thêm cấu trúc: {name}, color={color}")
        return True
    
    def remove_structure(self, name: str):
        """
        Xóa cấu trúc khỏi bản đồ liều
        
        Args:
            name (str): Tên cấu trúc cần xóa
        """
        if name in self.structures:
            del self.structures[name]
            logger.info(f"Đã xóa cấu trúc: {name}")
            return True
        return False
    
    def set_isocenter(self, position: List[float]):
        """
        Thiết lập tọa độ tâm xạ trị
        
        Args:
            position (List[float]): Tọa độ [x, y, z] (mm)
        """
        self.isocenter = position
        logger.info(f"Đã thiết lập tâm xạ trị: {position}")
    
    def set_prescription_dose(self, dose: float):
        """
        Thiết lập liều kê toa
        
        Args:
            dose (float): Liều kê toa (Gy)
        """
        self.prescription_dose = dose
        logger.info(f"Đã thiết lập liều kê toa: {dose} Gy")
    
    def get_dose_slice(self, axis: str = 'axial', slice_index: int = None) -> np.ndarray:
        """
        Lấy lát cắt liều theo trục chỉ định
        
        Args:
            axis (str): Trục cắt ('axial', 'coronal', 'sagittal')
            slice_index (int): Chỉ số lát cắt
        
        Returns:
            np.ndarray: Mảng 2D chứa dữ liệu liều của lát cắt
        """
        if self.dose_data is None:
            logger.error("Không có dữ liệu liều")
            return None
        
        # Lấy lát cắt giữa nếu không chỉ định
        if slice_index is None:
            if axis == 'axial':
                slice_index = self.dose_data.shape[2] // 2
            elif axis == 'coronal':
                slice_index = self.dose_data.shape[1] // 2
            elif axis == 'sagittal':
                slice_index = self.dose_data.shape[0] // 2
        
        # Lấy lát cắt theo trục
        try:
            if axis == 'axial':
                return self.dose_data[:, :, slice_index] * self.dose_grid_scaling
            elif axis == 'coronal':
                return self.dose_data[:, slice_index, :] * self.dose_grid_scaling
            elif axis == 'sagittal':
                return self.dose_data[slice_index, :, :] * self.dose_grid_scaling
            else:
                logger.error(f"Trục không hợp lệ: {axis}")
                return None
        except IndexError:
            logger.error(f"Chỉ số lát cắt ngoài phạm vi: {slice_index}")
            return None
    
    def get_structure_slice(self, name: str, axis: str = 'axial', slice_index: int = None) -> np.ndarray:
        """
        Lấy lát cắt cấu trúc theo trục chỉ định
        
        Args:
            name (str): Tên cấu trúc
            axis (str): Trục cắt ('axial', 'coronal', 'sagittal')
            slice_index (int): Chỉ số lát cắt
        
        Returns:
            np.ndarray: Mảng 2D chứa dữ liệu mask của lát cắt
        """
        if name not in self.structures:
            logger.error(f"Không tìm thấy cấu trúc: {name}")
            return None
        
        # Lấy lát cắt giữa nếu không chỉ định
        if slice_index is None:
            if axis == 'axial':
                slice_index = self.dose_data.shape[2] // 2
            elif axis == 'coronal':
                slice_index = self.dose_data.shape[1] // 2
            elif axis == 'sagittal':
                slice_index = self.dose_data.shape[0] // 2
        
        # Lấy lát cắt theo trục
        try:
            if axis == 'axial':
                return self.structures[name]["mask"][:, :, slice_index]
            elif axis == 'coronal':
                return self.structures[name]["mask"][:, slice_index, :]
            elif axis == 'sagittal':
                return self.structures[name]["mask"][slice_index, :, :]
            else:
                logger.error(f"Trục không hợp lệ: {axis}")
                return None
        except IndexError:
            logger.error(f"Chỉ số lát cắt ngoài phạm vi: {slice_index}")
            return None
    
    def plot_dose_map(self, axis: str = 'axial', slice_index: int = None, 
                     show_structures: bool = True, show_isocenter: bool = True,
                     show_colorbar: bool = True, figsize: Tuple[int, int] = (10, 8),
                     dose_range: Tuple[float, float] = None) -> Figure:
        """
        Vẽ bản đồ liều cho lát cắt chỉ định
        
        Args:
            axis (str): Trục cắt ('axial', 'coronal', 'sagittal')
            slice_index (int): Chỉ số lát cắt
            show_structures (bool): Hiển thị các cấu trúc
            show_isocenter (bool): Hiển thị tâm xạ trị
            show_colorbar (bool): Hiển thị thanh màu
            figsize (Tuple[int, int]): Kích thước hình (inch)
            dose_range (Tuple[float, float]): Phạm vi liều hiển thị (min, max) Gy
        
        Returns:
            Figure: Đối tượng Figure của matplotlib
        """
        # Lấy dữ liệu lát cắt
        dose_slice = self.get_dose_slice(axis, slice_index)
        if dose_slice is None:
            return None
        
        # Tạo figure
        fig, ax = plt.subplots(figsize=figsize)
        
        # Thiết lập phạm vi liều
        if dose_range is None:
            vmin = 0
            vmax = self.prescription_dose if self.prescription_dose else dose_slice.max()
        else:
            vmin, vmax = dose_range
        
        # Vẽ bản đồ liều
        im = ax.imshow(dose_slice.T, cmap=self.colormap, alpha=self.alpha, 
                      vmin=vmin, vmax=vmax, origin='lower')
        
        # Hiển thị các cấu trúc
        if show_structures and self.structures:
            for name, struct_data in self.structures.items():
                struct_slice = self.get_structure_slice(name, axis, slice_index)
                if struct_slice is not None:
                    # Vẽ đường viền cấu trúc
                    from scipy import ndimage
                    contours = ndimage.find_objects(ndimage.label(struct_slice)[0])
                    for contour in contours:
                        ax.contour(struct_slice.T, levels=[0.5], colors=[struct_data["color"]], 
                                  linewidths=2, origin='lower')
        
        # Hiển thị tâm xạ trị
        if show_isocenter and self.isocenter:
            # Chuyển đổi tọa độ tâm sang chỉ số pixel
            iso_pixel = self._convert_position_to_pixel(self.isocenter, axis)
            if iso_pixel:
                ax.plot(iso_pixel[0], iso_pixel[1], 'r+', markersize=10, markeredgewidth=2)
        
        # Hiển thị thanh màu
        if show_colorbar:
            cbar = fig.colorbar(im, ax=ax)
            cbar.set_label('Liều (Gy)')
        
        # Thiết lập tiêu đề và nhãn
        ax.set_title(f'Bản đồ liều - {axis.capitalize()} - Slice {slice_index}')
        
        if axis == 'axial':
            ax.set_xlabel('X (pixel)')
            ax.set_ylabel('Y (pixel)')
        elif axis == 'coronal':
            ax.set_xlabel('X (pixel)')
            ax.set_ylabel('Z (pixel)')
        elif axis == 'sagittal':
            ax.set_xlabel('Y (pixel)')
            ax.set_ylabel('Z (pixel)')
        
        plt.tight_layout()
        return fig
    
    def _convert_position_to_pixel(self, position: List[float], axis: str) -> Tuple[int, int]:
        """
        Chuyển đổi tọa độ vật lý (mm) sang chỉ số pixel
        
        Args:
            position (List[float]): Tọa độ [x, y, z] (mm)
            axis (str): Trục cắt ('axial', 'coronal', 'sagittal')
        
        Returns:
            Tuple[int, int]: Tọa độ pixel (x, y)
        """
        try:
            x_idx = int(position[0] / self.voxel_size[0])
            y_idx = int(position[1] / self.voxel_size[1])
            z_idx = int(position[2] / self.voxel_size[2])
            
            if axis == 'axial':
                return (x_idx, y_idx)
            elif axis == 'coronal':
                return (x_idx, z_idx)
            elif axis == 'sagittal':
                return (y_idx, z_idx)
        except:
            logger.error("Không thể chuyển đổi tọa độ sang pixel")
            return None
    
    def calculate_dose_statistics(self, structure_name: str = None) -> Dict:
        """
        Tính toán các thông số thống kê liều cho cấu trúc
        
        Args:
            structure_name (str): Tên cấu trúc (None để tính toàn bộ)
        
        Returns:
            Dict: Từ điển chứa các thông số thống kê
        """
        if self.dose_data is None:
            logger.error("Không có dữ liệu liều")
            return None
        
        # Tính toán cho cấu trúc cụ thể
        if structure_name:
            if structure_name not in self.structures:
                logger.error(f"Không tìm thấy cấu trúc: {structure_name}")
                return None
            
            mask = self.structures[structure_name]["mask"]
            dose_values = self.dose_data[mask > 0] * self.dose_grid_scaling
        else:
            # Tính toán cho toàn bộ dữ liệu liều
            dose_values = self.dose_data.flatten() * self.dose_grid_scaling
        
        # Tính các thông số thống kê
        stats = {
            "min": float(np.min(dose_values)),
            "max": float(np.max(dose_values)),
            "mean": float(np.mean(dose_values)),
            "median": float(np.median(dose_values)),
            "std": float(np.std(dose_values)),
            "volume_cc": float(np.sum(mask if structure_name else 1) * np.prod(self.voxel_size) / 1000) if structure_name else None
        }
        
        # Tính các phân vị
        for p in [5, 10, 25, 50, 75, 90, 95, 98, 99]:
            stats[f"D{p}"] = float(np.percentile(dose_values, p))
        
        return stats
    
    def calculate_conformity_index(self, target_name: str, prescription_dose: float = None) -> float:
        """
        Tính chỉ số tương thích (Conformity Index)
        CI = (V_prescription / V_target) * (V_prescription / V_body)
        
        Args:
            target_name (str): Tên cấu trúc đích
            prescription_dose (float): Liều kê toa (Gy), mặc định lấy từ thuộc tính
        
        Returns:
            float: Chỉ số tương thích
        """
        if target_name not in self.structures:
            logger.error(f"Không tìm thấy cấu trúc đích: {target_name}")
            return None
        
        if prescription_dose is None:
            prescription_dose = self.prescription_dose
            
        if prescription_dose is None:
            logger.error("Chưa thiết lập liều kê toa")
            return None
        
        # Tính thể tích nhận liều kê toa
        dose_mask = self.dose_data * self.dose_grid_scaling >= prescription_dose
        v_prescription = np.sum(dose_mask) * np.prod(self.voxel_size) / 1000  # cc
        
        # Thể tích cấu trúc đích
        target_mask = self.structures[target_name]["mask"]
        v_target = np.sum(target_mask) * np.prod(self.voxel_size) / 1000  # cc
        
        # Thể tích cơ thể (toàn bộ)
        v_body = np.prod(self.dose_data.shape) * np.prod(self.voxel_size) / 1000  # cc
        
        # Tính chỉ số tương thích
        ci = (v_prescription / v_target) * (v_prescription / v_body)
        
        return float(ci)
    
    def calculate_homogeneity_index(self, target_name: str) -> float:
        """
        Tính chỉ số đồng nhất (Homogeneity Index)
        HI = (D2% - D98%) / D50%
        
        Args:
            target_name (str): Tên cấu trúc đích
        
        Returns:
            float: Chỉ số đồng nhất
        """
        if target_name not in self.structures:
            logger.error(f"Không tìm thấy cấu trúc đích: {target_name}")
            return None
        
        # Lấy giá trị liều trong cấu trúc đích
        target_mask = self.structures[target_name]["mask"]
        dose_values = self.dose_data[target_mask > 0] * self.dose_grid_scaling
        
        # Tính các phân vị liều
        d2 = float(np.percentile(dose_values, 2))
        d50 = float(np.percentile(dose_values, 50))
        d98 = float(np.percentile(dose_values, 98))
        
        # Tính chỉ số đồng nhất
        hi = (d2 - d98) / d50
        
        return float(hi)
    
    def save_dose_map(self, filename: str, axis: str = 'axial', slice_index: int = None,
                     dpi: int = 300, **kwargs):
        """
        Lưu bản đồ liều ra file
        
        Args:
            filename (str): Đường dẫn file
            axis (str): Trục cắt ('axial', 'coronal', 'sagittal')
            slice_index (int): Chỉ số lát cắt
            dpi (int): Độ phân giải (DPI)
            **kwargs: Các tham số khác cho plot_dose_map
        """
        fig = self.plot_dose_map(axis, slice_index, **kwargs)
        if fig:
            fig.savefig(filename, dpi=dpi, bbox_inches='tight')
            plt.close(fig)
            logger.info(f"Đã lưu bản đồ liều: {filename}")
            return True
        return False
    
    def export_dose_data(self, filename: str, include_structures: bool = True):
        """
        Xuất dữ liệu liều ra file
        
        Args:
            filename (str): Đường dẫn file
            include_structures (bool): Bao gồm dữ liệu cấu trúc
        """
        data = {
            "dose_shape": list(self.dose_data.shape),
            "dose_grid_scaling": self.dose_grid_scaling,
            "voxel_size": self.voxel_size,
            "prescription_dose": self.prescription_dose,
            "isocenter": self.isocenter,
            "timestamp": datetime.now().isoformat()
        }
        
        # Thêm thông tin cấu trúc (không bao gồm dữ liệu mask)
        if include_structures:
            structures_info = {}
            for name, struct_data in self.structures.items():
                structures_info[name] = {
                    "color": struct_data["color"],
                    "stats": self.calculate_dose_statistics(name)
                }
            data["structures"] = structures_info
        
        # Lưu file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Đã xuất dữ liệu liều: {filename}")
        return True

# Hàm tiện ích để tạo và hiển thị bản đồ liều
def create_dose_map(dose_data: np.ndarray, structures: Dict[str, np.ndarray] = None,
                   dose_grid_scaling: float = 1.0, voxel_size: List[float] = None,
                   prescription_dose: float = None) -> DoseMap:
    """
    Tạo đối tượng bản đồ liều từ dữ liệu
    
    Args:
        dose_data (np.ndarray): Dữ liệu liều 3D
        structures (Dict[str, np.ndarray]): Từ điển cấu trúc {tên: mask}
        dose_grid_scaling (float): Hệ số tỷ lệ liều (Gy/giá trị)
        voxel_size (List[float]): Kích thước voxel [x, y, z] (mm)
        prescription_dose (float): Liều kê toa (Gy)
    
    Returns:
        DoseMap: Đối tượng bản đồ liều
    """
    dose_map = DoseMap(dose_data, dose_grid_scaling, voxel_size)
    
    if prescription_dose:
        dose_map.set_prescription_dose(prescription_dose)
    
    if structures:
        for name, mask in structures.items():
            dose_map.add_structure(name, mask)
    
    return dose_map
