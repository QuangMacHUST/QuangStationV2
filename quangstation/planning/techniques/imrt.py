#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module cung cấp kỹ thuật xạ trị điều biến cường độ (IMRT) cho QuangStation V2.
"""

import numpy as np
import random
import math
from typing import Dict, List, Tuple, Optional, Any
from quangstation.planning.techniques.base import RTTechnique
from quangstation.utils.logging import get_logger

logger = get_logger(__name__)

class IMRT(RTTechnique):
    """Kỹ thuật xạ trị điều biến cường độ (IMRT)"""
    
    def __init__(self):
        super().__init__("IMRT")
        self.description = "Xạ trị điều biến cường độ sử dụng nhiều phân đoạn tĩnh"
        
        # Thông số mặc định
        self.beam_energy = 6.0  # MV
        self.beam_angles = [0, 50, 100, 150, 210, 260, 310]  # degrees
        self.collimator_angles = [0, 0, 0, 0, 0, 0, 0]  # degrees
        self.couch_angles = [0, 0, 0, 0, 0, 0, 0]  # degrees
        self.num_segments = 10  # Số phân đoạn cho mỗi trường
        self.min_segment_area = 5.0  # cm²
        self.min_segment_mu = 5.0  # MU
        
    def create_plan(self, structures: Dict[str, np.ndarray]) -> Dict:
        """
        Tạo kế hoạch IMRT
        
        Args:
            structures: Dictionary chứa các cấu trúc (key: tên cấu trúc, value: mảng numpy)
            
        Returns:
            Dictionary chứa thông tin kế hoạch
        """
        self.beams = []
        
        # Tạo các trường IMRT
        for i, angle in enumerate(self.beam_angles):
            beam_id = f"Field_{i+1}"
            
            # Xác định góc collimator và couch
            collimator_angle = self.collimator_angles[i] if i < len(self.collimator_angles) else 0
            couch_angle = self.couch_angles[i] if i < len(self.couch_angles) else 0
            
            # Tạo các control point (phân đoạn) cho trường này
            control_points = self._create_imrt_control_points(self.num_segments)
            
            # Tạo beam
            beam = {
                "id": beam_id,
                "gantry_angle": angle,
                "collimator_angle": collimator_angle,
                "couch_angle": couch_angle,
                "energy": self.beam_energy,
                "technique": "STATIC",
                "weight": 1.0,
                "control_points": control_points,
                "jaw_positions": {"X1": -10, "X2": 10, "Y1": -10, "Y2": 10}  # Kích thước mặc định
            }
            
            getattr(self, "beams", {}).append(beam)
        
        # Nếu có cấu trúc PTV, tự động điều chỉnh kích thước trường
        if "PTV" in structures or "ptv" in structures:
            ptv_key = "PTV" if "PTV" in structures else "ptv"
            ptv = structures[ptv_key]
            
            # Tính toán kích thước trường dựa trên PTV
            # Đây chỉ là logic đơn giản, cần cải thiện trong ứng dụng thực tế
            logger.info("Đang điều chỉnh kích thước trường dựa trên PTV")
            field_margin = 10  # mm
            
            # Mô phỏng việc tính margin - trong thực tế sẽ phức tạp hơn
            field_size_x = 100  # mm
            field_size_y = 100  # mm
            
            # Cập nhật kích thước trường cho tất cả các beam
            for beam in getattr(self, "beams", {}):
                beam["jaw_positions"] = {
                    "X1": -field_size_x/2,
                    "X2": field_size_x/2,
                    "Y1": -field_size_y/2,
                    "Y2": field_size_y/2
                }
        
        return {
            "technique": self.name,
            "beams": getattr(self, "beams", {}),
            "prescription": {"dose": self.prescription_dose, "fractions": self.fractions},
            "isocenter": self.isocenter
        }
    
    def _create_imrt_control_points(self, num_segments: int) -> List[Dict]:
        """
        Tạo các control point cho IMRT
        
        Args:
            num_segments: Số phân đoạn
            
        Returns:
            Danh sách các control point
        """
        control_points = []
        
        # Tổng MU cho tất cả các phân đoạn
        total_mu = 100.0
        
        # Phân bổ MU ngẫu nhiên nhưng có tính đến min_segment_mu
        mus = []
        remaining_mu = total_mu
        for i in range(num_segments - 1):
            # Tính toán MU tối đa có thể cho phân đoạn này
            max_mu = remaining_mu - self.min_segment_mu * (num_segments - i - 1)
            if max_mu < self.min_segment_mu:
                segment_mu = self.min_segment_mu
            else:
                segment_mu = random.uniform(self.min_segment_mu, max_mu)
            
            mus.append(segment_mu)
            remaining_mu -= segment_mu
        
        # Phân đoạn cuối cùng nhận phần MU còn lại
        mus.append(remaining_mu)
        
        # Tạo các control point với MU đã phân bổ
        for i in range(num_segments):
            control_point = {
                "index": i,
                "mu": mus[i],
                "mlc": self._create_random_mlc_pattern()
            }
            control_points.append(control_point)
            
        return control_points
    
    def _create_random_mlc_pattern(self) -> List[List[float]]:
        """
        Tạo mẫu MLC ngẫu nhiên cho IMRT
        
        Returns:
            Danh sách vị trí MLC
        """
        # Mô phỏng mẫu MLC với 80 lá (40 cặp)
        mlc_positions = []
        
        # Số lá MLC (thường là 40 cặp = 80 lá)
        num_leaves = 40
        
        # Mô phỏng các vị trí MLC ngẫu nhiên (trong thực tế sẽ dựa trên tối ưu hóa)
        for i in range(num_leaves):
            # Tạo vị trí ngẫu nhiên cho cặp lá, đảm bảo lá trên (X1) < lá dưới (X2)
            left_pos = random.uniform(-10.0, 0.0)  # cm
            right_pos = random.uniform(left_pos + 0.5, 10.0)  # cm
            
            # Đảm bảo độ mở tối thiểu
            min_opening = 0.5  # cm
            if right_pos - left_pos < min_opening:
                right_pos = left_pos + min_opening
            
            mlc_positions.append([left_pos, right_pos])
            
        return mlc_positions
    
    def set_beam_angles(self, angles: List[float]):
        """
        Thiết lập các góc chùm tia
        
        Args:
            angles: Danh sách các góc chùm tia (độ)
        """
        self.beam_angles = angles
        logger.info(f"Đã thiết lập các góc chùm tia: {angles}")
    
    def set_num_segments(self, num: int):
        """
        Thiết lập số lượng phân đoạn cho mỗi trường
        
        Args:
            num: Số lượng phân đoạn
        """
        if num < 3:
            num = 3  # IMRT cần ít nhất 3 phân đoạn
        self.num_segments = num
        logger.info(f"Đã thiết lập số lượng phân đoạn cho mỗi trường: {num}")
    
    def set_min_segment_area(self, area: float):
        """
        Thiết lập diện tích tối thiểu cho mỗi phân đoạn
        
        Args:
            area: Diện tích tối thiểu (cm²)
        """
        if area < 1.0:
            area = 1.0
        self.min_segment_area = area
        logger.info(f"Đã thiết lập diện tích tối thiểu cho mỗi phân đoạn: {area} cm²")
    
    def set_min_segment_mu(self, mu: float):
        """
        Thiết lập MU tối thiểu cho mỗi phân đoạn
        
        Args:
            mu: MU tối thiểu
        """
        if mu < 1.0:
            mu = 1.0
        self.min_segment_mu = mu
        logger.info(f"Đã thiết lập MU tối thiểu cho mỗi phân đoạn: {mu}") 