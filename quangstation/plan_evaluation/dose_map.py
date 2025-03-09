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
        # Giá trị mặc định để tránh lỗi "biến chưa được khởi tạo"
        dose_slice = np.zeros_like(self.volume[0])
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
                     colormap: str = 'jet', alpha: float = 0.7,
                     show_structures: bool = True, structure_names: List[str] = None,
                     show_isodose: bool = True, isodose_levels: List[float] = None,
                     figsize: Tuple[int, int] = (10, 8), use_relative_dose: bool = False,
                     add_colorbar: bool = True) -> plt.Figure:
        """
        Hiển thị bản đồ liều trên lát cắt CT.
        
        Args:
            axis: Trục hiển thị ('axial', 'coronal', 'sagittal')
            slice_index: Chỉ số lát cắt
            colormap: Tên colormap cho phân bố liều
            alpha: Độ trong suốt của overlay liều
            show_structures: Hiển thị contour cấu trúc
            structure_names: Danh sách tên cấu trúc cần hiển thị (None = tất cả)
            show_isodose: Hiển thị các đường isodose
            isodose_levels: Danh sách mức liều hiển thị (%)
            figsize: Kích thước figure
            use_relative_dose: Sử dụng liều tương đối (%) thay vì liều tuyệt đối (Gy)
            add_colorbar: Hiển thị thanh màu bên cạnh hình
            
        Returns:
            Figure: Đối tượng matplotlib Figure
        """
        if self.dose_data is None or self.ct_data is None:
            logger.error("Không có dữ liệu liều hoặc CT")
            return None
            
        # Kiểm tra slice_index
        if slice_index is None:
            if axis == 'axial':
                slice_index = self.dose_data.shape[0] // 2
            elif axis == 'coronal':
                slice_index = self.dose_data.shape[1] // 2
            elif axis == 'sagittal':
                slice_index = self.dose_data.shape[2] // 2
        
        # Tạo figure và axes
        fig, ax = plt.subplots(figsize=figsize)
        
        # Lấy lát cắt CT
        if axis == 'axial':
            ct_slice = self.ct_data[slice_index, :, :]
            dose_slice = self.dose_data[slice_index, :, :]
        elif axis == 'coronal':
            ct_slice = self.ct_data[:, slice_index, :]
            dose_slice = self.dose_data[:, slice_index, :]
        elif axis == 'sagittal':
            ct_slice = self.ct_data[:, :, slice_index]
            dose_slice = self.dose_data[:, :, slice_index]
        else:
            logger.error(f"Trục không hợp lệ: {axis}")
            return None
            
        # Chuyển đổi CT sang ảnh xám bằng cửa sổ CT mặc định
        window_center = self.window_center or 40  # Mặc định cho soft tissue
        window_width = self.window_width or 400
        
        # Chuyển đổi CT sang ảnh có giá trị 0-1
        ct_min = window_center - window_width/2
        ct_max = window_center + window_width/2
        ct_display = np.clip((ct_slice - ct_min) / (ct_max - ct_min), 0, 1)
        
        # Hiển thị CT
        ax.imshow(ct_display, cmap='gray', aspect='equal')
        
        # Chuẩn hóa liều nếu cần
        if use_relative_dose and self.prescription_dose:
            # Sử dụng liều tương đối (%)
            dose_display = dose_slice * self.dose_grid_scaling / self.prescription_dose * 100
            dose_unit = '%'
            # Mặc định isodose levels cho liều tương đối
            default_isodose_levels = [10, 30, 50, 70, 80, 90, 95, 100, 105, 110]
        else:
            # Sử dụng liều tuyệt đối (Gy)
            dose_display = dose_slice * self.dose_grid_scaling
            dose_unit = 'Gy'
            # Mặc định isodose levels cho liều tuyệt đối (tính từ liều kê toa nếu có)
            if self.prescription_dose:
                dose_ref = self.prescription_dose
                default_isodose_levels = [
                    dose_ref * p / 100 for p in [10, 30, 50, 70, 80, 90, 95, 100, 105, 110]
                ]
            else:
                default_isodose_levels = [0.5, 1, 2, 5, 10, 15, 20, 30, 40, 50]
        
        # Hiển thị dose color wash nếu có liều
        if np.max(dose_display) > 0:
            # Tạo mask cho liều
            dose_mask = dose_display > 0
            
            # Hiển thị color wash liều
            im = ax.imshow(np.ma.masked_where(~dose_mask, dose_display), 
                          cmap=colormap, alpha=alpha, vmin=0, interpolation='bilinear')
            
            # Thêm color bar
            if add_colorbar:
                cbar = fig.colorbar(im, ax=ax, shrink=0.8)
                cbar.set_label(f'Dose ({dose_unit})', rotation=270, labelpad=15)
            
            # Hiển thị isodose lines
            if show_isodose:
                isodose_levels = isodose_levels or default_isodose_levels
                
                # Tạo giá trị liều tương đối từ liều tuyệt đối nếu cần
                if not use_relative_dose and self.prescription_dose:
                    isodose_display_vals = [f"{level:.1f} Gy" for level in isodose_levels]
                else:
                    isodose_display_vals = [f"{level:.1f} {dose_unit}" for level in isodose_levels]
                
                # Lấy biến thể colormap để có màu tương ứng
                cmap = plt.get_cmap(colormap)
                
                # Lấy các mức dose tối đa và tối thiểu
                dose_max = np.max(dose_display)
                
                for i, level in enumerate(isodose_levels):
                    if level > 0 and level <= dose_max * 1.1:
                        # Lấy màu từ colormap theo tỷ lệ với dose_max
                        if use_relative_dose:
                            color_val = level / 120  # chuẩn hóa màu (120% là max)
                        else:
                            color_val = level / (dose_max * 1.1)
                        color = cmap(min(color_val, 1.0))
                        
                        # Vẽ contour
                        contours = ax.contour(dose_display, levels=[level], colors=[color], linewidths=1.5)
                        
                        # Thêm nhãn
                        fmt = {level: isodose_display_vals[i]}
                        ax.clabel(contours, inline=True, fmt=fmt, fontsize=8)
        
        # Hiển thị cấu trúc
        if show_structures and self.structures:
            structures_to_show = structure_names or list(self.structures.keys())
            
            for name in structures_to_show:
                if name in self.structures:
                    # Lấy mask của cấu trúc
                    struct_mask = self.structures[name]["mask"]
                    struct_color = self.structures[name]["color"]
                    
                    # Lấy contour của cấu trúc trên lát cắt
                    if axis == 'axial':
                        struct_slice = struct_mask[slice_index, :, :]
                    elif axis == 'coronal':
                        struct_slice = struct_mask[:, slice_index, :]
                    elif axis == 'sagittal':
                        struct_slice = struct_mask[:, :, slice_index]
                    
                    # Vẽ contour cấu trúc
                    if np.any(struct_slice):
                        contours = ax.contour(struct_slice, levels=[0.5], colors=[struct_color], linewidths=2)
                        ax.clabel(contours, inline=True, fmt={0.5: name}, fontsize=9)
        
        # Thiết lập trục
        ax.set_aspect('equal')
        ax.set_axis_off()
        
        # Thêm tiêu đề
        if axis == 'axial':
            title = f'Axial Slice {slice_index}'
        elif axis == 'coronal':
            title = f'Coronal Slice {slice_index}'
        elif axis == 'sagittal':
            title = f'Sagittal Slice {slice_index}'
            
        ax.set_title(title)
        
        # Thêm thông tin dose
        if self.prescription_dose:
            dose_info = f"Prescription: {self.prescription_dose:.1f} Gy"
            if hasattr(self, 'fractions') and self.fractions:
                dose_info += f" in {self.fractions} fractions"
            fig.text(0.01, 0.01, dose_info, transform=ax.transAxes)
        
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
