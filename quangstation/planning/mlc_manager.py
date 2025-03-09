#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module quản lý MLC (Multi-Leaf Collimator) cho QuangStation V2.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import matplotlib.pyplot as plt

class MLCModel:
    """Lớp cơ sở cho các mô hình MLC khác nhau"""
    
    def __init__(self, name: str, leaf_count: int = 60, leaf_width: float = 5.0):
        # Giá trị mặc định để tránh lỗi "biến chưa được khởi tạo"
        structure_mask = np.zeros_like(self.volume)
        """
        Khởi tạo mô hình MLC
        
        Args:
            name: Tên mô hình MLC
            leaf_count: Số lá MLC (cho mỗi bank)
            leaf_width: Độ rộng của lá MLC (mm)
        """
        self.name = name
        self.leaf_count = leaf_count
        self.leaf_width = leaf_width
        self.max_field_size = 40.0  # cm
        self.min_gap = 0.5  # Khoảng cách tối thiểu giữa các lá đối diện (mm)
        self.max_travel = 20.0  # Khoảng di chuyển tối đa từ tâm (cm)
        self.transmission = 0.015  # Độ truyền qua lá (1.5%)
        self.leakage = 0.002  # Độ rò qua khe hở giữa các lá (0.2%)
        self.leaf_ends = "rounded"  # Kiểu đầu lá: "rounded" hoặc "focused"
        
    def get_leaf_positions_bounds(self) -> Tuple[float, float]:
        """Trả về giới hạn vị trí của lá MLC"""
        return (-self.max_travel, self.max_travel)
    
    def validate_leaf_positions(self, bank_a: List[float], bank_b: List[float]) -> bool:
        """
        Kiểm tra tính hợp lệ của vị trí lá MLC
        
        Args:
            bank_a: Danh sách vị trí lá bank A (cm)
            bank_b: Danh sách vị trí lá bank B (cm)
            
        Returns:
            True nếu hợp lệ, False nếu không
        """
        if len(bank_a) != self.leaf_count or len(bank_b) != self.leaf_count:
            return False
            
        min_pos, max_pos = self.get_leaf_positions_bounds()
        
        for i in range(self.leaf_count):
            # Kiểm tra giới hạn vị trí
            if bank_a[i] < min_pos or bank_a[i] > 0:
                return False
            if bank_b[i] > max_pos or bank_b[i] < 0:
                return False
                
            # Kiểm tra khoảng cách tối thiểu
            if (bank_b[i] - bank_a[i]) < self.min_gap / 10.0:  # Chuyển từ mm sang cm
                return False
                
        return True
    
    def fit_mlc_to_contour(self, contour: np.ndarray, margin_cm: float = 0.5) -> Tuple[List[float], List[float]]:
        """
        Tự động điều chỉnh vị trí lá MLC để vừa với hình dạng contour
        
        Args:
            contour: Ma trận 2D đánh dấu contour (1 = trong, 0 = ngoài)
            margin_cm: Lề cần thêm vào xung quanh contour (cm)
            
        Returns:
            Tuple (bank_a, bank_b) chứa vị trí các lá (cm)
        """
        # Kích thước pixel (giả sử 1mm/pixel)
        pixel_size = 0.1  # cm/pixel
        
        # Chuyển đổi margin từ cm sang pixels
        margin_pixels = int(margin_cm / pixel_size)
        
        # Mở rộng contour bằng margin
        if margin_pixels > 0:
            from scipy import ndimage
            contour_expanded = ndimage.binary_dilation(contour, 
                                                      iterations=margin_pixels).astype(np.int32)
        else:
            contour_expanded = contour.copy()
        
        # Tính toán kích thước field
        rows, cols = contour_expanded.shape
        pixel_per_leaf = self.leaf_width / 10.0 / pixel_size  # leaf width từ mm sang cm, rồi sang pixel
        
        bank_a = []
        bank_b = []
        
        # Tính toán vị trí lá cho từng lá
        for i in range(self.leaf_count):
            # Vị trí tâm của lá (pixel)
            leaf_center = int((i + 0.5) * pixel_per_leaf)
            
            if leaf_center < 0 or leaf_center >= rows:
                # Lá nằm ngoài phạm vi contour
                bank_a.append(-self.max_travel)
                bank_b.append(self.max_travel)
                continue
            
            # Tìm vị trí xa nhất bên trái và bên phải của contour trên hàng này
            row = contour_expanded[leaf_center, :]
            left_indices = np.where(row > 0)[0]
            
            if len(left_indices) == 0:
                # Không có contour trên hàng này
                bank_a.append(-self.max_travel)
                bank_b.append(self.max_travel)
                continue
                
            # Vị trí trái nhất và phải nhất
            left_most = left_indices.min()
            right_most = left_indices.max()
            
            # Chuyển từ pixel sang cm (giả sử tâm field ở giữa ảnh)
            center_col = cols / 2
            pos_a = (left_most - center_col) * pixel_size
            pos_b = (right_most - center_col) * pixel_size
            
            # Giới hạn trong phạm vi cho phép
            pos_a = max(-self.max_travel, min(0, pos_a))
            pos_b = max(0, min(self.max_travel, pos_b))
            
            bank_a.append(pos_a)
            bank_b.append(pos_b)
            
        return (bank_a, bank_b)
    
    def create_rectangular_mlc(self, field_size_x: float, field_size_y: float) -> Tuple[List[float], List[float]]:
        """
        Tạo mẫu MLC hình chữ nhật
        
        Args:
            field_size_x: Kích thước trường theo X (cm)
            field_size_y: Kích thước trường theo Y (cm)
            
        Returns:
            Tuple (bank_a, bank_b) chứa vị trí các lá (cm)
        """
        # Giới hạn kích thước trường
        field_size_x = min(field_size_x, self.max_field_size)
        field_size_y = min(field_size_y, self.max_field_size)
        
        half_x = field_size_x / 2.0
        half_y = field_size_y / 2.0
        
        bank_a = []
        bank_b = []
        
        # Tính số lá cần mở cho field_size_y
        leaf_width_cm = self.leaf_width / 10.0  # mm sang cm
        leaves_to_open = int(np.ceil(field_size_y / leaf_width_cm))
        start_leaf = max(0, (self.leaf_count - leaves_to_open) // 2)
        end_leaf = min(self.leaf_count, start_leaf + leaves_to_open)
        
        for i in range(self.leaf_count):
            if start_leaf <= i < end_leaf:
                # Lá nằm trong field
                bank_a.append(-half_x)
                bank_b.append(half_x)
            else:
                # Lá nằm ngoài field
                bank_a.append(0)
                bank_b.append(0)
                
        return (bank_a, bank_b)
    
    def create_circular_mlc(self, radius_cm: float) -> Tuple[List[float], List[float]]:
        """
        Tạo mẫu MLC hình tròn
        
        Args:
            radius_cm: Bán kính hình tròn (cm)
            
        Returns:
            Tuple (bank_a, bank_b) chứa vị trí các lá (cm)
        """
        # Giới hạn bán kính
        radius_cm = min(radius_cm, self.max_field_size / 2.0)
        
        bank_a = []
        bank_b = []
        
        leaf_width_cm = self.leaf_width / 10.0  # mm sang cm
        
        for i in range(self.leaf_count):
            # Vị trí tâm của lá (cm) từ tâm trường
            y_pos = (i - self.leaf_count/2 + 0.5) * leaf_width_cm
            
            # Tính x_pos dựa trên phương trình hình tròn: x^2 + y^2 = r^2
            if abs(y_pos) > radius_cm:
                # Ngoài hình tròn
                bank_a.append(0)
                bank_b.append(0)
            else:
                # Trong hình tròn
                x_pos = np.sqrt(radius_cm**2 - y_pos**2)
                bank_a.append(-x_pos)
                bank_b.append(x_pos)
                
        return (bank_a, bank_b)
    
    def visualize_mlc(self, bank_a: List[float], bank_b: List[float], ax=None, 
                     contour: np.ndarray = None, pixel_size: float = 0.1):
        """
        Hiển thị MLC
        
        Args:
            bank_a: Vị trí lá bank A (cm)
            bank_b: Vị trí lá bank B (cm)
            ax: Matplotlib axes để vẽ
            contour: Ma trận contour để hiển thị cùng (tùy chọn)
            pixel_size: Kích thước pixel của contour (cm/pixel)
        """
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 10))
            
        # Vẽ contour nếu có
        if contour is not None:
            rows, cols = contour.shape
            # Tính toán extent của contour
            half_width = cols * pixel_size / 2
            half_height = rows * pixel_size / 2
            ax.imshow(contour.T, cmap='gray', alpha=0.3, 
                     extent=[-half_width, half_width, -half_height, half_height])
            
        # Vẽ lá MLC
        leaf_width_cm = self.leaf_width / 10.0  # mm sang cm
        
        for i in range(self.leaf_count):
            # Vị trí Y của lá
            y_top = (i + 0.5) * leaf_width_cm
            y_bottom = (i - 0.5) * leaf_width_cm
            
            # Vẽ lá bank A (bên trái)
            rect_a = plt.Rectangle(
                (bank_a[i], y_bottom),
                -bank_a[i],  # Chiều rộng
                leaf_width_cm,  # Chiều cao
                color='blue', alpha=0.5
            )
            ax.add_patch(rect_a)
            
            # Vẽ lá bank B (bên phải)
            rect_b = plt.Rectangle(
                (0, y_bottom),
                bank_b[i],  # Chiều rộng
                leaf_width_cm,  # Chiều cao
                color='red', alpha=0.5
            )
            ax.add_patch(rect_b)
            
        # Cấu hình trục
        max_pos = max(abs(min(bank_a)), max(bank_b))
        ax.set_xlim(-max_pos*1.2, max_pos*1.2)
        ax.set_ylim(-self.leaf_count * leaf_width_cm / 2 * 1.2, 
                    self.leaf_count * leaf_width_cm / 2 * 1.2)
        ax.set_xlabel('X (cm)')
        ax.set_ylabel('Y (cm)')
        ax.set_title(f'MLC Pattern - {self.name}')
        ax.grid(True)
        
        return ax


class VarianMLC120(MLCModel):
    """Mô hình MLC Varian HD120 MLC"""
    
    def __init__(self):
        super().__init__("Varian HD120 MLC", leaf_count=120, leaf_width=2.5)
        # Cấu hình đặc thù của HD120
        self.min_gap = 0.3  # mm
        self.transmission = 0.01  # 1%
        self.max_speed = 2.5  # cm/s
        self.inner_leaf_width = 2.5  # mm (40 lá trung tâm)
        self.outer_leaf_width = 5.0  # mm (80 lá ngoài)
        
        # Tạo mảng độ rộng lá
        self.leaf_widths = np.ones(self.leaf_count) * self.outer_leaf_width
        center_start = (self.leaf_count - 40) // 2
        self.leaf_widths[center_start:center_start+40] = self.inner_leaf_width


class ElektaAgility(MLCModel):
    """Mô hình MLC Elekta Agility"""
    
    def __init__(self):
        super().__init__("Elekta Agility", leaf_count=160, leaf_width=5.0)
        # Cấu hình đặc thù của Agility
        self.min_gap = 0.5  # mm
        self.transmission = 0.005  # 0.5%
        self.max_speed = 3.5  # cm/s
        self.interdigitation = True  # Cho phép răng lược


class SiemensMLC(MLCModel):
    """Mô hình MLC Siemens 160 MLC"""
    
    def __init__(self):
        super().__init__("Siemens 160 MLC", leaf_count=160, leaf_width=5.0)
        # Cấu hình đặc thù
        self.min_gap = 0.5  # mm
        self.transmission = 0.012  # 1.2%
        self.max_speed = 3.0  # cm/s


class MLCManager:
    """Quản lý MLC cho kế hoạch xạ trị"""
    
    def __init__(self):
        """Khởi tạo các model MLC có sẵn"""
        self.mlc_models = {
            "varian_hd120": VarianMLC120(),
            "elekta_agility": ElektaAgility(),
            "siemens_160": SiemensMLC(),
            "standard": MLCModel("Standard MLC", leaf_count=60, leaf_width=5.0)
        }
        self.active_model = self.mlc_models["standard"]
        
    def set_active_model(self, model_name: str):
        """Thiết lập model MLC hiện tại"""
        if model_name in self.mlc_models:
            self.active_model = self.mlc_models[model_name]
            return True
        return False
        
    def get_available_models(self) -> List[str]:
        """Trả về danh sách các model MLC có sẵn"""
        return list(self.mlc_models.keys())
        
    def fit_mlc_to_structure(self, structure_mask: np.ndarray, beam_angle: float, 
                            margin_cm: float = 0.5) -> Tuple[List[float], List[float]]:
        """
        Tự động điều chỉnh MLC để vừa với hình dạng cấu trúc từ một góc chiếu
        
        Args:
            structure_mask: Ma trận 3D đánh dấu cấu trúc 
            beam_angle: Góc chùm tia (độ)
            margin_cm: Lề xung quanh cấu trúc (cm)
            
        Returns:
            Tuple (bank_a, bank_b) chứa vị trí các lá
        """
        # Chuyển đổi cấu trúc 3D thành hình chiếu 2D từ góc beam_angle
        projection = self._create_beam_eye_view(structure_mask, beam_angle)
        
        # Điều chỉnh MLC
        return self.active_model.fit_mlc_to_contour(projection, margin_cm)
        
    def _create_beam_eye_view(self, structure_mask: np.ndarray, beam_angle: float) -> np.ndarray:
        """
        Tạo hình chiếu Beam's Eye View từ góc chùm tia
        
        Args:
            structure_mask: Ma trận 3D đánh dấu cấu trúc
            beam_angle: Góc chùm tia (độ)
            
        Returns:
            Ma trận 2D biểu diễn hình chiếu BEV
        """
        # Trong thực tế, đây là một thuật toán phức tạp
        # Đơn giản hóa bằng cách dùng phép chiếu max/mean
        
        # Xoay cấu trúc theo góc beam
        angle_rad = np.radians(beam_angle)
        
        # Giả lập xoay bằng cách lấy phép chiếu theo trục Z
        if abs(np.sin(angle_rad)) < 0.7071:  # Gần 0 hoặc 180 độ
            # Dùng phép chiếu theo Z
            projection = np.max(structure_mask, axis=0)
        else:
            # Dùng phép chiếu theo X hoặc Y tùy góc
            if abs(np.cos(angle_rad)) > 0:
                projection = np.max(structure_mask, axis=1)
            else:
                projection = np.max(structure_mask, axis=2)
                
        return projection
    
    def save_mlc_pattern(self, bank_a: List[float], bank_b: List[float], file_path: str) -> bool:
        """
        Lưu mẫu MLC vào file
        
        Args:
            bank_a: Vị trí lá bank A (cm)
            bank_b: Vị trí lá bank B (cm)
            file_path: Đường dẫn lưu file
            
        Returns:
            True nếu thành công, False nếu thất bại
        """
        try:
            import json
            with open(file_path, 'w') as f:
                json.dump({
                    "model": self.active_model.name,
                    "leaf_count": self.active_model.leaf_count,
                    "leaf_width": self.active_model.leaf_width,
                    "bank_a": bank_a,
                    "bank_b": bank_b
                }, f, indent=2)
            return True
        except Exception as error:
            print(f"Lỗi khi lưu mẫu MLC: {error}")
            return False
            
    def load_mlc_pattern(self, file_path: str) -> Tuple[List[float], List[float]]:
        """
        Tải mẫu MLC từ file
        
        Args:
            file_path: Đường dẫn file
            
        Returns:
            Tuple (bank_a, bank_b) chứa vị trí các lá
        """
        try:
            import json
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            # Kiểm tra model
            model_name = data.get("model", "standard")
            if model_name in self.mlc_models:
                self.set_active_model(model_name)
                
            return data["bank_a"], data["bank_b"]
        except Exception as error:
            print(f"Lỗi khi tải mẫu MLC: {error}")
            return [], [] 