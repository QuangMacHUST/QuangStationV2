#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module cung cấp kỹ thuật xạ trị cung tròn điều biến cường độ (VMAT) cho QuangStation V2.
"""

import numpy as np
import random
import math
from typing import Dict, List, Tuple, Optional, Any
from quangstation.planning.techniques.base import RTTechnique
from quangstation.utils.logging import get_logger

logger = get_logger(__name__)

class VMAT(RTTechnique):
    """Kỹ thuật xạ trị cung tròn điều biến cường độ (VMAT)"""
    
    def __init__(self):
        super().__init__("VMAT")
        self.description = "Xạ trị cung tròn điều biến cường độ (VMAT)"
        
        # Thông số mặc định
        self.beam_energy = 6.0  # MV
        self.arc_angles = [(179, 181)]  # (start, stop) degrees
        self.arc_directions = [1]  # 1: CW, -1: CCW
        self.collimator_angles = [45]  # degrees
        self.couch_angles = [0]  # degrees
        self.control_points_per_arc = 90  # Số control point cho mỗi cung
        
    def create_plan(self, structures: Dict[str, np.ndarray]) -> Dict:
        """
        Tạo kế hoạch VMAT
        
        Args:
            structures: Dictionary chứa các cấu trúc (key: tên cấu trúc, value: mảng numpy)
            
        Returns:
            Dictionary chứa thông tin kế hoạch
        """
        self.beams = []
        
        # Tạo các cung VMAT
        for i, arc in enumerate(self.arc_angles):
            start_angle, stop_angle = arc
            
            # Xác định góc collimator và couch
            collimator_angle = self.collimator_angles[i] if i < len(self.collimator_angles) else 45
            couch_angle = self.couch_angles[i] if i < len(self.couch_angles) else 0
            
            # Xác định hướng cung
            direction = self.arc_directions[i] if i < len(self.arc_directions) else 1
            
            # Tạo các control point cho cung này
            control_points = self._create_vmat_control_points(
                start_angle, stop_angle, direction, self.control_points_per_arc
            )
            
            # Phân tích tên cung
            arc_id = f"Arc_{i+1}"
            if abs(stop_angle - start_angle) >= 350:
                arc_id = "FullArc"
            elif direction == 1:
                arc_id = f"CW_Arc_{i+1}"
            else:
                arc_id = f"CCW_Arc_{i+1}"
            
            # Tìm PTV để tạo aperture
            ptv_mask = None
            if "PTV" in structures:
                ptv_mask = structures["PTV"]
            elif "ptv" in structures:
                ptv_mask = structures["ptv"]
            
            # Tạo beam
            beam = {
                "id": arc_id,
                "gantry_angle": start_angle,  # Góc bắt đầu
                "collimator_angle": collimator_angle,
                "couch_angle": couch_angle,
                "energy": self.beam_energy,
                "technique": "ARC",
                "weight": 1.0,
                "control_points": control_points,
                "arc_direction": "CW" if direction == 1 else "CCW",
                "arc_start_angle": start_angle,
                "arc_stop_angle": stop_angle,
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
                
                # Cập nhật MLC dựa trên PTV cho mỗi control point
                if "control_points" in beam:
                    for cp in beam["control_points"]:
                        gantry_angle = cp.get("gantry_angle", beam["gantry_angle"])
                        # Trong ứng dụng thực tế, chúng ta sẽ tạo aperture phù hợp cho mỗi góc
                        # Ở đây chỉ sử dụng một hàm tạo mẫu
                        cp["mlc"] = self._create_mlc_pattern_for_angle(gantry_angle)
        
        return {
            "technique": self.name,
            "beams": getattr(self, "beams", {}),
            "prescription": {"dose": self.prescription_dose, "fractions": self.fractions},
            "isocenter": self.isocenter
        }
    
    def _create_aperture_from_ptv(self, ptv_mask: np.ndarray, gantry_angle: float) -> Dict:
        """
        Tạo aperture từ PTV cho một góc chụp cụ thể
        
        Args:
            ptv_mask: Mặt nạ PTV
            gantry_angle: Góc gantry (độ)
            
        Returns:
            Dictionary chứa thông tin aperture
        """
        # Đây là hàm mô phỏng, trong thực tế cần phân tích hình chiếu của PTV theo góc
        # Và tính toán vị trí lá MLC phù hợp
        
        # Tạo một aperture giả định
        aperture = {
            "mlc": self._create_mlc_pattern_for_angle(gantry_angle),
            "jaw_positions": {"X1": -10, "X2": 10, "Y1": -10, "Y2": 10}
        }
        
        return aperture
    
    def _create_vmat_control_points(self, start_angle: float, stop_angle: float, 
                              direction: int, num_points: int) -> List[Dict]:
        """
        Tạo các control point cho VMAT
        
        Args:
            start_angle: Góc bắt đầu (độ)
            stop_angle: Góc kết thúc (độ)
            direction: Hướng cung (1: CW, -1: CCW)
            num_points: Số control point
            
        Returns:
            Danh sách các control point
        """
        control_points = []
        
        # Tính toán góc giữa các điểm
        if direction == 1:  # CW
            if stop_angle < start_angle:
                stop_angle += 360
            angle_step = (stop_angle - start_angle) / (num_points - 1)
        else:  # CCW
            if start_angle < stop_angle:
                start_angle += 360
            angle_step = (start_angle - stop_angle) / (num_points - 1)
        
        # Tổng MU cho tất cả các control point
        total_mu = 100.0
        mu_per_point = total_mu / (num_points - 1)  # Điểm đầu tiên có MU=0
        
        # Tạo các control point với góc và MU
        for i in range(num_points):
            if direction == 1:  # CW
                angle = (start_angle + i * angle_step) % 360
            else:  # CCW
                angle = (start_angle - i * angle_step) % 360
            
            # Điểm đầu tiên có MU=0, điểm cuối cùng có MU=total_mu
            mu = mu_per_point * i
            
            control_point = {
                "index": i,
                "gantry_angle": angle,
                "mu": mu,
                "mlc": self._create_mlc_pattern_for_angle(angle),
                "cumulative_meterset_weight": mu / total_mu
            }
            
            control_points.append(control_point)
        
        return control_points
    
    def _create_mlc_pattern_for_angle(self, angle: float) -> List[List[float]]:
        """
        Tạo mẫu MLC cho một góc gantry cụ thể
        
        Args:
            angle: Góc gantry (độ)
            
        Returns:
            Danh sách vị trí MLC
        """
        # Mô phỏng mẫu MLC với 80 lá (40 cặp)
        mlc_positions = []
        
        # Số lá MLC (thường là 40 cặp = 80 lá)
        num_leaves = 40
        
        # Mô phỏng các vị trí MLC thay đổi theo góc (trong thực tế sẽ phức tạp hơn)
        # Ở đây tạo một mẫu hình sin đơn giản thay đổi theo góc
        for i in range(num_leaves):
            # Tính phase dựa trên số thứ tự lá và góc
            phase = (i / num_leaves * 2 * math.pi + angle / 180 * math.pi) % (2 * math.pi)
            
            # Tạo hình dạng sin, biên độ thay đổi từ trung tâm ra ngoài
            amplitude = 3.0 * math.sin(math.pi * i / num_leaves)  # cm
            offset = amplitude * math.sin(phase)
            
            # Vị trí cơ bản
            base_left = -5.0  # cm
            base_right = 5.0  # cm
            
            # Vị trí cuối cùng
            left_pos = base_left + offset
            right_pos = base_right + offset
            
            # Đảm bảo left_pos < right_pos và nằm trong phạm vi hợp lệ
            left_pos = max(-10.0, min(left_pos, 9.0))
            right_pos = max(left_pos + 1.0, min(right_pos, 10.0))
            
            mlc_positions.append([left_pos, right_pos])
        
        return mlc_positions
    
    def set_arc_setup(self, arc_angles: List[Tuple[float, float]], directions: List[int] = None):
        """
        Thiết lập các cung
        
        Args:
            arc_angles: Danh sách các cặp góc (start, stop) (độ)
            directions: Danh sách hướng cung (1: CW, -1: CCW)
        """
        self.arc_angles = arc_angles
        
        if directions is not None:
            # Đảm bảo có đủ giá trị hướng cho tất cả các cung
            if len(directions) < len(arc_angles):
                # Nếu thiếu, điền thêm giá trị mặc định (1: CW)
                self.arc_directions = directions + [1] * (len(arc_angles) - len(directions))
            else:
                self.arc_directions = directions[:len(arc_angles)]
        
        logger.info(f"Đã thiết lập {len(arc_angles)} cung với các góc: {arc_angles}")
        if directions:
            logger.info(f"Hướng cung: {self.arc_directions}")
    
    def set_control_points_per_arc(self, num: int):
        """
        Thiết lập số lượng control point cho mỗi cung
        
        Args:
            num: Số lượng control point
        """
        if num < 10:
            num = 10  # VMAT cần ít nhất 10 control point
        
        self.control_points_per_arc = num
        logger.info(f"Đã thiết lập số lượng control point cho mỗi cung: {num}") 