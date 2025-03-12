#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module quản lý chùm tia và bộ collimator đa lá (MLC) cho QuangStation V2.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any
import copy
import math
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from quangstation.core.utils.logging import get_logger

logger = get_logger(__name__)

class MLCModel:
    """Lớp cơ sở cho các mô hình MLC khác nhau"""
    
    def __init__(self, name: str, num_leaf_pairs: int, leaf_width_mm: float, 
                max_field_size_mm: Tuple[float, float], max_leaf_spread_mm: float):
        """
        Khởi tạo mô hình MLC
        
        Args:
            name: Tên mô hình MLC
            num_leaf_pairs: Số cặp lá
            leaf_width_mm: Độ rộng của mỗi lá (mm)
            max_field_size_mm: Kích thước trường tối đa (mm x mm)
            max_leaf_spread_mm: Khoảng cách tối đa giữa hai lá đối diện (mm)
        """
        self.name = name
        self.num_leaf_pairs = num_leaf_pairs
        self.leaf_width_mm = leaf_width_mm
        self.max_field_size_mm = max_field_size_mm
        self.max_leaf_spread_mm = max_leaf_spread_mm
        
        # Vị trí mặc định của lá (đóng hoàn toàn)
        self.leaf_positions = np.zeros((num_leaf_pairs, 2))  # [lá A, lá B] cho mỗi cặp
        
    def validate_positions(self, positions: np.ndarray) -> bool:
        """
        Kiểm tra tính hợp lệ của vị trí lá
        
        Args:
            positions: Mảng numpy (num_leaf_pairs, 2) chứa vị trí lá [lá A, lá B]
            
        Returns:
            bool: True nếu hợp lệ, False nếu không
        """
        if positions.shape != (self.num_leaf_pairs, 2):
            logger.log_error(f"Kích thước mảng vị trí không hợp lệ: {positions.shape}, cần ({self.num_leaf_pairs}, 2)")
            return False
            
        # Kiểm tra lá A luôn nằm bên trái lá B
        if np.any(positions[:, 0] > positions[:, 1]):
            logger.log_error("Lá A không thể nằm bên phải lá B")
            return False
            
        # Kiểm tra khoảng cách giữa hai lá
        leaf_spreads = positions[:, 1] - positions[:, 0]
        if np.any(leaf_spreads > self.max_leaf_spread_mm):
            logger.log_error(f"Khoảng cách giữa hai lá vượt quá giới hạn {self.max_leaf_spread_mm} mm")
            return False
            
        # Kiểm tra vị trí lá không vượt quá giới hạn trường
        half_width = self.max_field_size_mm[0] / 2
        if np.any(positions[:, 0] < -half_width) or np.any(positions[:, 1] > half_width):
            logger.log_error(f"Vị trí lá vượt quá giới hạn trường ±{half_width} mm")
            return False
            
        return True
        
    def set_positions(self, positions: np.ndarray) -> bool:
        """
        Thiết lập vị trí lá
        
        Args:
            positions: Mảng numpy (num_leaf_pairs, 2) chứa vị trí lá [lá A, lá B]
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        if self.validate_positions(positions):
            self.leaf_positions = positions.copy()
            return True
        return False
        
    def get_positions(self) -> np.ndarray:
        """
        Lấy vị trí hiện tại của lá
        
        Returns:
            np.ndarray: Mảng numpy (num_leaf_pairs, 2) chứa vị trí lá [lá A, lá B]
        """
        return self.leaf_positions.copy()
        
    def fit_to_contour(self, contour_mask: np.ndarray, iso_center: Tuple[float, float, float],
                     gantry_angle: float, pixel_spacing: Tuple[float, float, float]) -> bool:
        """
        Tự động điều chỉnh vị trí lá để phù hợp với contour
        
        Args:
            contour_mask: Mảng 3D mask của contour
            iso_center: Tọa độ tâm iso (mm)
            gantry_angle: Góc gantry (độ)
            pixel_spacing: Khoảng cách pixel (mm)
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            import scipy.ndimage as ndimage
            from skimage.measure import find_contours
            import matplotlib.pyplot as plt
            
            # Kiểm tra dữ liệu đầu vào
            if contour_mask is None or contour_mask.ndim != 3:
                logger.log_error("Contour mask không hợp lệ")
                return False
                
            # 1. Chuẩn bị dữ liệu
            # Chuyển đổi tọa độ isocenter từ mm sang pixel
            iso_pixel_x = int(iso_center[0] / pixel_spacing[0])
            iso_pixel_y = int(iso_center[1] / pixel_spacing[1])
            iso_pixel_z = int(iso_center[2] / pixel_spacing[2])
            
            # Đảm bảo isocenter nằm trong phạm vi của mask
            if (iso_pixel_x < 0 or iso_pixel_x >= contour_mask.shape[2] or
                iso_pixel_y < 0 or iso_pixel_y >= contour_mask.shape[1] or
                iso_pixel_z < 0 or iso_pixel_z >= contour_mask.shape[0]):
                logger.log_error("Isocenter nằm ngoài phạm vi của contour mask")
                return False
            
            # 2. Tạo beam's eye view (BEV) bằng cách chiếu contour theo góc gantry
            # Chuyển đổi góc gantry sang radian
            gantry_rad = np.radians(gantry_angle)
            
            # Tạo mảng 2D để lưu BEV
            bev_size = max(contour_mask.shape)
            bev = np.zeros((bev_size, bev_size), dtype=np.float32)
            
            # Tính toán ma trận xoay
            cos_theta = np.cos(gantry_rad)
            sin_theta = np.sin(gantry_rad)
            
            # Chiếu contour lên BEV
            for z in range(contour_mask.shape[0]):
                # Tính khoảng cách từ lát cắt đến isocenter theo trục Z
                z_dist = (z - iso_pixel_z) * pixel_spacing[2]
                
                # Xoay và chiếu mỗi lát cắt
                for y in range(contour_mask.shape[1]):
                    for x in range(contour_mask.shape[2]):
                        if contour_mask[z, y, x] > 0:
                            # Tính tọa độ tương đối so với isocenter (mm)
                            rel_x = (x - iso_pixel_x) * pixel_spacing[0]
                            rel_y = (y - iso_pixel_y) * pixel_spacing[1]
                            
                            # Xoay tọa độ theo góc gantry
                            rot_x = rel_x * cos_theta - z_dist * sin_theta
                            rot_y = rel_y
                            
                            # Chuyển về tọa độ pixel trong BEV
                            bev_x = int(rot_x / pixel_spacing[0] + bev_size // 2)
                            bev_y = int(rot_y / pixel_spacing[1] + bev_size // 2)
                            
                            # Đảm bảo tọa độ nằm trong phạm vi của BEV
                            if 0 <= bev_x < bev_size and 0 <= bev_y < bev_size:
                                bev[bev_y, bev_x] = 1.0
            
            # Làm mịn BEV để lấp đầy các lỗ hổng
            bev = ndimage.binary_dilation(bev, iterations=2)
            bev = ndimage.binary_erosion(bev, iterations=1)
            bev = ndimage.binary_fill_holes(bev)
            
            # 3. Xác định biên giới contour cho mỗi lá MLC
            # Tính toán vị trí trung tâm của BEV
            center_x = bev_size // 2
            center_y = bev_size // 2
            
            # Tính toán kích thước của mỗi lá MLC theo pixel
            leaf_width_pixel = self.leaf_width_mm / pixel_spacing[1]
            
            # Tính toán số lượng lá cần thiết để bao phủ contour
            num_leaves = min(self.num_leaf_pairs, int(bev.shape[0] / leaf_width_pixel))
            
            # Tính toán vị trí bắt đầu của lá đầu tiên
            start_y = center_y - (num_leaves * leaf_width_pixel) / 2
            
            # Khởi tạo mảng vị trí lá
            leaf_positions = np.zeros((self.num_leaf_pairs, 2))
            
            # Tìm biên giới contour cho mỗi lá
            for i in range(num_leaves):
                # Tính toán vị trí của lá hiện tại
                leaf_start = int(start_y + i * leaf_width_pixel)
                leaf_end = int(start_y + (i + 1) * leaf_width_pixel)
                
                # Đảm bảo vị trí nằm trong phạm vi của BEV
                leaf_start = max(0, min(leaf_start, bev.shape[0] - 1))
                leaf_end = max(0, min(leaf_end, bev.shape[0] - 1))
                
                # Lấy dải pixel tương ứng với lá MLC
                leaf_strip = bev[leaf_start:leaf_end, :]
                
                # Tìm vị trí xa nhất bên trái và bên phải của contour
                if np.any(leaf_strip):
                    # Tìm các cột có pixel thuộc contour
                    cols_with_contour = np.where(np.any(leaf_strip, axis=0))[0]
                    
                    if len(cols_with_contour) > 0:
                        left_edge = cols_with_contour[0]
                        right_edge = cols_with_contour[-1]
                        
                        # Chuyển đổi từ pixel sang mm, tương đối so với tâm
                        left_pos = (left_edge - center_x) * pixel_spacing[0]
                        right_pos = (right_edge - center_x) * pixel_spacing[0]
                        
                        # Thêm lề an toàn (5mm)
                        left_pos -= 5.0
                        right_pos += 5.0
                        
                        # Giới hạn trong phạm vi cho phép của MLC
                        left_pos = max(-self.max_leaf_spread_mm / 2, min(left_pos, 0))
                        right_pos = min(self.max_leaf_spread_mm / 2, max(right_pos, 0))
                        
                        # Lưu vị trí lá
                        if i < self.num_leaf_pairs:
                            leaf_positions[i, 0] = left_pos
                            leaf_positions[i, 1] = right_pos
            
            # Đặt vị trí cho các lá không được sử dụng
            for i in range(num_leaves, self.num_leaf_pairs):
                leaf_positions[i, 0] = 0
                leaf_positions[i, 1] = 0
            
            # Cập nhật vị trí lá MLC
            success = self.set_positions(leaf_positions)
            
            if success:
                logger.log_info(f"Đã điều chỉnh MLC để phù hợp với contour, góc gantry {gantry_angle}°")
            else:
                logger.log_warning("Không thể đặt vị trí MLC")
                
            return success
            
        except Exception as e:
            logger.log_error(f"Lỗi khi điều chỉnh MLC: {str(e)}")
            import traceback
            logger.log_error(traceback.format_exc())
            return False
        
    def create_rectangular_field(self, field_size_mm: Tuple[float, float],
                               center_offset_mm: Tuple[float, float] = (0, 0)) -> bool:
        """
        Tạo trường hình chữ nhật
        
        Args:
            field_size_mm: Kích thước trường (width, height) (mm)
            center_offset_mm: Độ lệch tâm (x, y) (mm)
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        width, height = field_size_mm
        x_offset, y_offset = center_offset_mm
        
        # Kiểm tra kích thước trường
        if width > self.max_field_size_mm[0] or height > self.max_field_size_mm[1]:
            logger.log_error(f"Kích thước trường ({width}x{height}) vượt quá giới hạn")
            return False
            
        # Tính vị trí lá
        half_width = width / 2
        half_height = height / 2
        
        # Tính số lá cần mở
        leaves_to_open = int(height / self.leaf_width_mm)
        if leaves_to_open > self.num_leaf_pairs:
            leaves_to_open = self.num_leaf_pairs
            
        # Tính vị trí bắt đầu lá
        start_leaf = (self.num_leaf_pairs - leaves_to_open) // 2
        
        # Tạo vị trí lá mới (mặc định là đóng)
        new_positions = np.zeros((self.num_leaf_pairs, 2))
        
        # Mở các lá cần thiết
        for i in range(start_leaf, start_leaf + leaves_to_open):
            if i < self.num_leaf_pairs:
                new_positions[i, 0] = x_offset - half_width  # Lá A (bên trái)
                new_positions[i, 1] = x_offset + half_width  # Lá B (bên phải)
        
        # Thiết lập vị trí lá mới
        return self.set_positions(new_positions)
    
    def create_circular_field(self, diameter_mm: float, center_offset_mm: Tuple[float, float] = (0, 0)) -> bool:
        """
        Tạo trường hình tròn
        
        Args:
            diameter_mm: Đường kính trường (mm)
            center_offset_mm: Độ lệch tâm (x, y) (mm)
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        x_offset, y_offset = center_offset_mm
        
        # Kiểm tra kích thước trường
        if diameter_mm > min(self.max_field_size_mm):
            logger.log_error(f"Đường kính trường ({diameter_mm}) vượt quá giới hạn")
            return False
            
        radius = diameter_mm / 2
        
        # Tạo vị trí lá mới (mặc định là đóng)
        new_positions = np.zeros((self.num_leaf_pairs, 2))
        
        # Tính vị trí trung tâm của mỗi lá
        leaf_centers = np.linspace(-self.max_field_size_mm[1]/2 + self.leaf_width_mm/2, 
                                self.max_field_size_mm[1]/2 - self.leaf_width_mm/2, 
                                self.num_leaf_pairs)
        
        # Tính vị trí lá để tạo hình tròn
        for i in range(self.num_leaf_pairs):
            y = leaf_centers[i] - y_offset
            # Nếu lá nằm trong hình tròn
            if abs(y) <= radius:
                # Tính chiều rộng của hình tròn tại vị trí y
                half_width = np.sqrt(radius**2 - y**2)
                new_positions[i, 0] = x_offset - half_width  # Lá A (bên trái)
                new_positions[i, 1] = x_offset + half_width  # Lá B (bên phải)
        
        # Thiết lập vị trí lá mới
        return self.set_positions(new_positions)
    
    def visualize(self, ax=None, show=True):
        """
        Hiển thị hình ảnh MLC
        
        Args:
            ax: Matplotlib axes. Nếu None, sẽ tạo axes mới
            show: Hiển thị hình ảnh nếu True
            
        Returns:
            matplotlib.axes.Axes: Axes đã vẽ MLC
        """
        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 8))
            
        # Vẽ khung trường
        field_width, field_height = self.max_field_size_mm
        rect = Rectangle((-field_width/2, -field_height/2), field_width, field_height, 
                       fill=False, edgecolor='black', linestyle='--')
        ax.add_patch(rect)
        
        # Vẽ các lá MLC
        leaf_centers = np.linspace(-field_height/2 + self.leaf_width_mm/2, 
                                field_height/2 - self.leaf_width_mm/2, 
                                self.num_leaf_pairs)
        
        for i in range(self.num_leaf_pairs):
            y_center = leaf_centers[i]
            
            # Lá bên trái (A)
            left_pos = self.leaf_positions[i, 0]
            left_width = left_pos + field_width/2
            left_rect = Rectangle((-field_width/2, y_center - self.leaf_width_mm/2),
                               left_width, self.leaf_width_mm,
                               fill=True, edgecolor='blue', facecolor='lightblue')
            ax.add_patch(left_rect)
            
            # Lá bên phải (B)
            right_pos = self.leaf_positions[i, 1]
            right_width = field_width/2 - right_pos
            right_rect = Rectangle((right_pos, y_center - self.leaf_width_mm/2),
                                right_width, self.leaf_width_mm,
                                fill=True, edgecolor='blue', facecolor='lightblue')
            ax.add_patch(right_rect)
        
        # Cấu hình trục
        ax.set_xlim(-field_width/2 - 10, field_width/2 + 10)
        ax.set_ylim(-field_height/2 - 10, field_height/2 + 10)
        ax.set_xlabel('X (mm)')
        ax.set_ylabel('Y (mm)')
        ax.set_title(f'MLC Model: {self.name}')
        ax.grid(True)
        ax.set_aspect('equal')
        
        if show:
            plt.show()
            
        return ax


# Các lớp con MLC cụ thể
class VarianMLC120(MLCModel):
    """Mô hình MLC Varian 120 lá"""
    
    def __init__(self):
        super().__init__(
            name="Varian MLC 120",
            num_leaf_pairs=60,
            leaf_width_mm=5.0,
            max_field_size_mm=(400.0, 400.0),
            max_leaf_spread_mm=150.0
        )
        
class ElektaMLC160(MLCModel):
    """Mô hình MLC Elekta 160 lá"""
    
    def __init__(self):
        super().__init__(
            name="Elekta MLC 160",
            num_leaf_pairs=80,
            leaf_width_mm=5.0,
            max_field_size_mm=(400.0, 400.0),
            max_leaf_spread_mm=200.0
        )

class SiemensMLC160(MLCModel):
    """Mô hình MLC Siemens 160 lá"""
    
    def __init__(self):
        super().__init__(
            name="Siemens MLC 160",
            num_leaf_pairs=80,
            leaf_width_mm=5.0,
            max_field_size_mm=(400.0, 400.0),
            max_leaf_spread_mm=200.0
        )


class Beam:
    """Lớp quản lý thông tin chùm tia"""
    
    def __init__(self, beam_id: str, beam_type: str = "photon", energy: float = 6.0):
        """
        Khởi tạo chùm tia
        
        Args:
            beam_id: ID của chùm tia
            beam_type: Loại chùm tia ("photon", "electron", "proton")
            energy: Năng lượng chùm tia (MV hoặc MeV)
        """
        self.id = beam_id
        self.type = beam_type
        self.energy = energy
        
        # Thông số hình học
        self.gantry_angle = 0.0  # Góc gantry (độ)
        self.collimator_angle = 0.0  # Góc collimator (độ)
        self.couch_angle = 0.0  # Góc cáng (độ)
        self.ssd = 1000.0  # Source-Surface Distance (mm)
        self.isocenter = (0.0, 0.0, 0.0)  # Tọa độ tâm (mm)
        
        # Thông số trường
        self.field_type = "rectangular"  # rectangular, circular, irregular
        self.field_size = (100.0, 100.0)  # Kích thước trường (mm x mm) cho rectangular
        self.field_diameter = 100.0  # Đường kính (mm) cho circular
        self.center_offset = (0.0, 0.0)  # Độ lệch tâm (mm)
        
        # Thông số MLC
        self.mlc_model = None  # Model MLC
        self.mlc_positions = None  # Vị trí các lá MLC
        
        # Thông số lệch
        self.has_wedge = False
        self.wedge_type = None  # physical, dynamic, enhanced
        self.wedge_angle = 0.0  # Góc (độ)
        self.wedge_orientation = 0.0  # Hướng (độ)
        
        # Thông số VMAT
        self.is_arc = False
        self.arc_start_angle = 0.0
        self.arc_stop_angle = 0.0
        self.arc_direction = 1  # 1: CW, -1: CCW
        
        # Thông số liều
        self.weight = 1.0
        self.monitor_units = 100.0
        
        # Control points (cho IMRT, VMAT)
        self.control_points = []
        
    def set_gantry_angle(self, angle: float) -> None:
        """Đặt góc gantry"""
        self.gantry_angle = angle % 360.0
        
    def set_collimator_angle(self, angle: float) -> None:
        """Đặt góc collimator"""
        self.collimator_angle = angle % 360.0
        
    def set_couch_angle(self, angle: float) -> None:
        """Đặt góc cáng"""
        self.couch_angle = angle % 360.0
        
    def set_isocenter(self, position: Tuple[float, float, float]) -> None:
        """Đặt vị trí tâm"""
        self.isocenter = position
        
    def set_rectangular_field(self, width: float, height: float, center_offset: Tuple[float, float] = (0, 0)) -> None:
        """Đặt trường hình chữ nhật"""
        self.field_type = "rectangular"
        self.field_size = (width, height)
        self.center_offset = center_offset
        
        # Cập nhật MLC nếu có
        if self.mlc_model is not None:
            self.mlc_model.create_rectangular_field((width, height), center_offset)
            self.mlc_positions = self.mlc_model.get_positions()
        
    def set_circular_field(self, diameter: float, center_offset: Tuple[float, float] = (0, 0)) -> None:
        """Đặt trường hình tròn"""
        self.field_type = "circular"
        self.field_diameter = diameter
        self.center_offset = center_offset
        
        # Cập nhật MLC nếu có
        if self.mlc_model is not None:
            self.mlc_model.create_circular_field(diameter, center_offset)
            self.mlc_positions = self.mlc_model.get_positions()
    
    def set_mlc_model(self, mlc_model: MLCModel) -> None:
        """Đặt model MLC"""
        self.mlc_model = mlc_model
        
        # Cập nhật lại trường dựa trên thông số hiện tại
        if self.field_type == "rectangular":
            self.mlc_model.create_rectangular_field(self.field_size, self.center_offset)
        elif self.field_type == "circular":
            self.mlc_model.create_circular_field(self.field_diameter, self.center_offset)
            
        self.mlc_positions = self.mlc_model.get_positions()
    
    def set_mlc_positions(self, positions: np.ndarray) -> bool:
        """Đặt vị trí các lá MLC"""
        if self.mlc_model is None:
            logger.log_error("Chưa thiết lập model MLC")
            return False
            
        if self.mlc_model.set_positions(positions):
            self.mlc_positions = self.mlc_model.get_positions()
            self.field_type = "irregular"
            return True
        return False
    
    def fit_mlc_to_contour(self, contour_mask: np.ndarray, pixel_spacing: Tuple[float, float, float]) -> bool:
        """Điều chỉnh MLC phù hợp với contour"""
        if self.mlc_model is None:
            logger.log_error("Chưa thiết lập model MLC")
            return False
            
        if self.mlc_model.fit_to_contour(contour_mask, self.isocenter, self.gantry_angle, pixel_spacing):
            self.mlc_positions = self.mlc_model.get_positions()
            self.field_type = "irregular"
            return True
        return False
    
    def set_wedge(self, has_wedge: bool, wedge_type: str = None, wedge_angle: float = 0.0, 
                wedge_orientation: float = 0.0) -> None:
        """Cấu hình lêch"""
        self.has_wedge = has_wedge
        
        if has_wedge:
            self.wedge_type = wedge_type
            self.wedge_angle = wedge_angle
            self.wedge_orientation = wedge_orientation
    
    def set_arc(self, is_arc: bool, start_angle: float = 0.0, stop_angle: float = 0.0, 
              direction: int = 1) -> None:
        """Cấu hình chùm tia arc (cho VMAT)"""
        self.is_arc = is_arc
        
        if is_arc:
            self.arc_start_angle = start_angle % 360.0
            self.arc_stop_angle = stop_angle % 360.0
            self.arc_direction = direction
    
    def add_control_point(self, gantry_angle: float, mlc_positions: np.ndarray, 
                        dose_weight: float) -> None:
        """Thêm control point (cho IMRT, VMAT)"""
        control_point = {
            "gantry_angle": gantry_angle % 360.0,
            "mlc_positions": mlc_positions.copy() if mlc_positions is not None else None,
            "dose_weight": dose_weight
        }
        self.control_points.append(control_point)
    
    def to_dict(self) -> Dict:
        """Chuyển đổi thành dictionary để lưu trữ"""
        beam_dict = {
            "id": self.id,
            "type": self.type,
            "energy": self.energy,
            "gantry_angle": self.gantry_angle,
            "collimator_angle": self.collimator_angle,
            "couch_angle": self.couch_angle,
            "ssd": self.ssd,
            "isocenter": self.isocenter,
            "field_type": self.field_type,
            "field_size": self.field_size,
            "field_diameter": self.field_diameter,
            "center_offset": self.center_offset,
            "has_wedge": self.has_wedge,
            "wedge_type": self.wedge_type,
            "wedge_angle": self.wedge_angle,
            "wedge_orientation": self.wedge_orientation,
            "is_arc": self.is_arc,
            "arc_start_angle": self.arc_start_angle,
            "arc_stop_angle": self.arc_stop_angle,
            "arc_direction": self.arc_direction,
            "weight": self.weight,
            "monitor_units": self.monitor_units,
        }
        
        # Thêm thông tin MLC nếu có
        if self.mlc_model is not None:
            beam_dict["mlc_model"] = self.mlc_model.name
            beam_dict["mlc_positions"] = self.mlc_positions.tolist()
            
        # Thêm control points nếu có
        if self.control_points:
            beam_dict["control_points"] = []
            for cp in self.control_points:
                cp_dict = {
                    "gantry_angle": cp["gantry_angle"],
                    "dose_weight": cp["dose_weight"]
                }
                if cp["mlc_positions"] is not None:
                    cp_dict["mlc_positions"] = cp["mlc_positions"].tolist()
                beam_dict["control_points"].append(cp_dict)
                
        return beam_dict
    
    @classmethod
    def from_dict(cls, beam_dict: Dict) -> 'Beam':
        """Tạo đối tượng từ dictionary"""
        beam = cls(
            beam_id=beam_dict["id"],
            beam_type=beam_dict["type"],
            energy=beam_dict["energy"]
        )
        
        # Cấu hình các thông số cơ bản
        beam.gantry_angle = beam_dict["gantry_angle"]
        beam.collimator_angle = beam_dict["collimator_angle"]
        beam.couch_angle = beam_dict["couch_angle"]
        beam.ssd = beam_dict["ssd"]
        beam.isocenter = beam_dict["isocenter"]
        beam.field_type = beam_dict["field_type"]
        beam.field_size = beam_dict["field_size"]
        beam.field_diameter = beam_dict["field_diameter"]
        beam.center_offset = beam_dict["center_offset"]
        beam.has_wedge = beam_dict["has_wedge"]
        beam.wedge_type = beam_dict["wedge_type"]
        beam.wedge_angle = beam_dict["wedge_angle"]
        beam.wedge_orientation = beam_dict["wedge_orientation"]
        beam.is_arc = beam_dict["is_arc"]
        beam.arc_start_angle = beam_dict["arc_start_angle"]
        beam.arc_stop_angle = beam_dict["arc_stop_angle"]
        beam.arc_direction = beam_dict["arc_direction"]
        beam.weight = beam_dict["weight"]
        beam.monitor_units = beam_dict["monitor_units"]
        
        # Cấu hình MLC nếu có
        if "mlc_model" in beam_dict:
            # Tạo model MLC dựa vào tên
            if beam_dict["mlc_model"] == "Varian MLC 120":
                beam.mlc_model = VarianMLC120()
            elif beam_dict["mlc_model"] == "Elekta MLC 160":
                beam.mlc_model = ElektaMLC160()
            elif beam_dict["mlc_model"] == "Siemens MLC 160":
                beam.mlc_model = SiemensMLC160()
                
            # Đặt vị trí lá
            if "mlc_positions" in beam_dict:
                mlc_positions = np.array(beam_dict["mlc_positions"])
                beam.mlc_model.set_positions(mlc_positions)
                beam.mlc_positions = beam.mlc_model.get_positions()
                
        # Cấu hình control points nếu có
        if "control_points" in beam_dict:
            for cp_dict in beam_dict["control_points"]:
                mlc_positions = None
                if "mlc_positions" in cp_dict:
                    mlc_positions = np.array(cp_dict["mlc_positions"])
                    
                beam.add_control_point(
                    gantry_angle=cp_dict["gantry_angle"],
                    mlc_positions=mlc_positions,
                    dose_weight=cp_dict["dose_weight"]
                )
                
        return beam
    
    def visualize(self, ax=None, show=True):
        """Hiển thị thông tin chùm tia"""
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 8))
            
        # Vẽ MLC nếu có
        if self.mlc_model is not None:
            self.mlc_model.visualize(ax, show=False)
            
        # Hiển thị thông tin chùm tia
        info_text = [
            f"Beam ID: {self.id}",
            f"Type: {self.type}",
            f"Energy: {self.energy} {'MV' if self.type == 'photon' else 'MeV'}",
            f"Gantry: {self.gantry_angle}°",
            f"Collimator: {self.collimator_angle}°",
            f"Couch: {self.couch_angle}°"
        ]
        
        if self.field_type == "rectangular":
            info_text.append(f"Field size: {self.field_size[0]}×{self.field_size[1]} mm²")
        elif self.field_type == "circular":
            info_text.append(f"Field diameter: {self.field_diameter} mm")
            
        if self.center_offset != (0, 0):
            info_text.append(f"Center offset: ({self.center_offset[0]}, {self.center_offset[1]}) mm")
            
        if self.has_wedge:
            info_text.append(f"Wedge: {self.wedge_type}, {self.wedge_angle}°, {self.wedge_orientation}°")
            
        if self.is_arc:
            info_text.append(f"Arc: {self.arc_start_angle}° → {self.arc_stop_angle}° ({'CW' if self.arc_direction == 1 else 'CCW'})")
            
        info_text.append(f"Weight: {self.weight}")
        info_text.append(f"MU: {self.monitor_units}")
        
        # Vẽ thông tin ở góc phải trên
        plt.annotate('\n'.join(info_text), xy=(0.95, 0.95), xycoords='axes fraction', 
                  horizontalalignment='right', verticalalignment='top',
                  bbox=dict(boxstyle="round,pad=0.5", fc="white", alpha=0.8))
        
        if show:
            plt.show()
            
        return ax


class Plan:
    """Lớp quản lý kế hoạch xạ trị"""
    
    def __init__(self, plan_id: str, patient_id: str, technique: str = "3DCRT"):
        """
        Khởi tạo kế hoạch
        
        Args:
            plan_id: ID của kế hoạch
            patient_id: ID của bệnh nhân
            technique: Kỹ thuật xạ trị (3DCRT, IMRT, VMAT, SRS, SBRT)
        """
        self.id = plan_id
        self.patient_id = patient_id
        self.technique = technique
        self.description = ""
        
        # Thông số kê toa
        self.prescribed_dose = 0.0  # Liều kê toa (Gy)
        self.fractions = 0  # Số phân liều
        self.prescription_type = "isocenter"  # isocenter, mean, min, max, d95
        self.target_name = ""  # Tên cấu trúc mục tiêu
        
        # Thông tin tham chiếu
        self.isocenter = (0.0, 0.0, 0.0)  # Tọa độ tâm (mm)
        
        # Danh sách chùm tia
        self.beams = []
        
        # Thông tin liều
        self.dose_matrix = None  # Ma trận liều
        self.dose_grid_spacing = (3.0, 3.0, 3.0)  # Độ phân giải liều (mm)
        
        # Thông tin đánh giá
        self.dvh_data = {}  # Dữ liệu DVH cho các cấu trúc
        self.evaluation_metrics = {}  # Các chỉ số đánh giá kế hoạch
        
        # Thông tin quy trình
        self.creation_date = None
        self.approval_status = "Draft"  # Draft, Reviewed, Approved
        self.approved_by = ""
        self.approval_date = None
        
    def add_beam(self, beam: Beam) -> None:
        """Thêm chùm tia vào kế hoạch"""
        getattr(self, "beams", {}).append(beam)
        
    def remove_beam(self, beam_id: str) -> bool:
        """Xóa chùm tia khỏi kế hoạch"""
        for i, beam in enumerate(getattr(self, "beams", {})):
            if beam.id == beam_id:
                getattr(self, "beams", {}).pop(i)
                return True
        return False
    
    def set_prescription(self, dose: float, fractions: int, 
                       prescription_type: str = "isocenter",
                       target_name: str = "") -> None:
        """Đặt thông tin kê toa"""
        self.prescribed_dose = dose
        self.fractions = fractions
        self.prescription_type = prescription_type
        self.target_name = target_name
        
    def set_isocenter(self, position: Tuple[float, float, float]) -> None:
        """Đặt vị trí tâm của kế hoạch"""
        self.isocenter = position
        
        # Cập nhật tâm cho tất cả các chùm tia
        for beam in getattr(self, "beams", {}):
            beam.set_isocenter(position)
            
    def normalize_to_prescription(self) -> None:
        """Chuẩn hóa liều theo kê toa."""
        import numpy as np
        from quangstation.utils.logging import get_logger
        logger = get_logger(__name__)
        
        # Kiểm tra xem đã có dose matrix chưa
        if not hasattr(self, "dose_matrix") or self.dose_matrix is None:
            logger.warning("Chưa có ma trận liều để chuẩn hóa")
            return
            
        # Kiểm tra xem đã có prescribed_dose chưa
        if not hasattr(self, "prescribed_dose") or self.prescribed_dose <= 0:
            logger.warning("Chưa đặt liều kê toa")
            return
            
        try:
            # Lấy reference_point hoặc target dựa trên prescription_type
            if hasattr(self, "prescription_type"):
                if self.prescription_type == "isocenter":
                    # Lấy giá trị liều tại tâm điều trị
                    if hasattr(self, "isocenter") and self.isocenter is not None:
                        # Tính chỉ số của tâm điều trị trong ma trận liều
                        iso_idx = [int(x) for x in self.isocenter]
                        current_dose = self.dose_matrix[iso_idx[0], iso_idx[1], iso_idx[2]]
                    else:
                        # Nếu không có tâm điều trị, dùng điểm có liều lớn nhất
                        current_dose = np.max(self.dose_matrix)
                
                elif self.prescription_type == "max_dose":
                    # Dùng liều lớn nhất làm reference
                    current_dose = np.max(self.dose_matrix)
                
                elif self.prescription_type == "mean_ptv":
                    # Dùng liều trung bình trong PTV
                    if hasattr(self, "target_name") and hasattr(self, "structure_masks"):
                        # Lấy mask của target
                        if self.target_name in self.structure_masks:
                            target_mask = self.structure_masks[self.target_name]
                            # Tính liều trung bình trong target
                            masked_dose = self.dose_matrix[target_mask > 0]
                            if len(masked_dose) > 0:
                                current_dose = np.mean(masked_dose)
                            else:
                                current_dose = np.max(self.dose_matrix)
                        else:
                            logger.warning(f"Target {self.target_name} không tồn tại trong cấu trúc")
                            current_dose = np.max(self.dose_matrix)
                    else:
                        logger.warning("Không tìm thấy target hoặc structure_masks")
                        current_dose = np.max(self.dose_matrix)
                
                elif self.prescription_type == "dX":
                    # Liều tại X% thể tích của PTV (ví dụ: D95, D90)
                    if hasattr(self, "target_name") and hasattr(self, "structure_masks") and hasattr(self, "prescription_volume_pct"):
                        if self.target_name in self.structure_masks:
                            target_mask = self.structure_masks[self.target_name]
                            masked_dose = self.dose_matrix[target_mask > 0]
                            
                            if len(masked_dose) > 0:
                                # Sắp xếp giá trị liều
                                sorted_dose = np.sort(masked_dose)
                                # Lấy vị trí tương ứng với X%
                                idx = int(len(sorted_dose) * (100 - self.prescription_volume_pct) / 100)
                                current_dose = sorted_dose[idx]
                            else:
                                current_dose = np.max(self.dose_matrix)
                        else:
                            logger.warning(f"Target {self.target_name} không tồn tại trong cấu trúc")
                            current_dose = np.max(self.dose_matrix)
                    else:
                        logger.warning("Không đủ thông tin để chuẩn hóa theo DX")
                        current_dose = np.max(self.dose_matrix)
                else:
                    # Mặc định dùng liều lớn nhất
                    current_dose = np.max(self.dose_matrix)
            else:
                # Mặc định dùng liều lớn nhất
                current_dose = np.max(self.dose_matrix)
                
            # Tránh chia cho 0
            if current_dose <= 0:
                logger.warning("Liều hiện tại là 0 hoặc âm, không thể chuẩn hóa")
                return
                
            # Tính hệ số chuẩn hóa
            normalization_factor = self.prescribed_dose / current_dose
            
            # Chuẩn hóa ma trận liều
            self.dose_matrix *= normalization_factor
            
            # Chuẩn hóa trọng số của tất cả các chùm tia
            for beam in getattr(self, "beams", []):
                if hasattr(beam, "weight"):
                    beam.weight *= normalization_factor
                
            logger.info(f"Đã chuẩn hóa liều với hệ số {normalization_factor:.4f}")
            
            # Đánh dấu đã chuẩn hóa
            self.is_normalized = True
            
        except Exception as e:
            logger.error(f"Lỗi khi chuẩn hóa liều: {str(e)}")
    
    def to_dict(self) -> Dict:
        """Chuyển đổi thành dictionary để lưu trữ"""
        plan_dict = {
            "id": self.id,
            "patient_id": self.patient_id,
            "technique": self.technique,
            "description": self.description,
            "prescribed_dose": self.prescribed_dose,
            "fractions": self.fractions,
            "prescription_type": self.prescription_type,
            "target_name": self.target_name,
            "isocenter": self.isocenter,
            "beams": [beam.to_dict() for beam in getattr(self, "beams", {})],
            "dose_grid_spacing": self.dose_grid_spacing,
            "approval_status": self.approval_status,
            "approved_by": self.approved_by,
        }
        
        # Thêm ngày tháng nếu có
        if self.creation_date:
            plan_dict["creation_date"] = self.creation_date.isoformat()
        if self.approval_date:
            plan_dict["approval_date"] = self.approval_date.isoformat()
            
        return plan_dict
    
    @classmethod
    def from_dict(cls, plan_dict: Dict) -> 'Plan':
        """Tạo đối tượng từ dictionary"""
        plan = cls(
            plan_id=plan_dict["id"],
            patient_id=plan_dict["patient_id"],
            technique=plan_dict["technique"]
        )
        
        # Cấu hình các thông số cơ bản
        plan.description = plan_dict["description"]
        plan.prescribed_dose = plan_dict["prescribed_dose"]
        plan.fractions = plan_dict["fractions"]
        plan.prescription_type = plan_dict["prescription_type"]
        plan.target_name = plan_dict["target_name"]
        plan.isocenter = plan_dict["isocenter"]
        plan.dose_grid_spacing = plan_dict["dose_grid_spacing"]
        plan.approval_status = plan_dict["approval_status"]
        plan.approved_by = plan_dict["approved_by"]
        
        # Tạo các chùm tia
        for beam_dict in plan_dict["beams"]:
            beam = Beam.from_dict(beam_dict)
            plan.add_beam(beam)
            
        # Xử lý ngày tháng nếu có
        if "creation_date" in plan_dict:
            from datetime import datetime
            plan.creation_date = datetime.fromisoformat(plan_dict["creation_date"])
        if "approval_date" in plan_dict:
            from datetime import datetime
            plan.approval_date = datetime.fromisoformat(plan_dict["approval_date"])
            
        return plan
    
    def summary(self) -> Dict:
        """Tạo bảng tóm tắt kế hoạch"""
        summary = {
            "plan_id": self.id,
            "patient_id": self.patient_id,
            "technique": self.technique,
            "prescription": f"{self.prescribed_dose} Gy in {self.fractions} fractions",
            "num_beams": len(getattr(self, "beams", {})),
            "status": self.approval_status
        }
        
        # Thêm thông tin chùm tia
        beams_summary = []
        for beam in getattr(self, "beams", {}):
            beam_info = {
                "id": beam.id,
                "type": beam.type,
                "energy": beam.energy,
                "gantry": beam.gantry_angle,
                "field_size": beam.field_size if beam.field_type == "rectangular" else beam.field_diameter,
                "mu": beam.monitor_units
            }
            beams_summary.append(beam_info)
            
        summary["beams"] = beams_summary
        
        return summary 