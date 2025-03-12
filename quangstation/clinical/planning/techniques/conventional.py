#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module cung cấp các kỹ thuật xạ trị 3D thông thường trong QuangStation V2.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from quangstation.clinical.planning.techniques.base import RTTechnique
from quangstation.core.utils.logging import get_logger

logger = get_logger(__name__)

class Conventional3DCRT(RTTechnique):
    """Kỹ thuật xạ trị 3D thông thường"""
    
    def __init__(self):
        super().__init__("3DCRT")
        self.description = "Xạ trị 3D thông thường với các trường hình dạng cố định"
        
        # Thông số mặc định
        self.beam_energy = 6.0  # MV
        self.beam_angles = [0, 90, 180, 270]  # degrees
        self.collimator_angles = [0, 0, 0, 0]  # degrees
        self.couch_angles = [0, 0, 0, 0]  # degrees
        self.use_wedges = False
        self.wedge_angles = [0, 0, 0, 0]  # degrees
        
    def create_plan(self, structures: Dict[str, np.ndarray]) -> Dict:
        """
        Tạo kế hoạch 3DCRT với 4 trường tiêu chuẩn
        
        Args:
            structures: Dictionary chứa các cấu trúc (key: tên cấu trúc, value: mảng numpy)
            
        Returns:
            Dictionary chứa thông tin kế hoạch
        """
        self.beams = [
            {
                "id": "AP",
                "gantry_angle": 0,
                "collimator_angle": 0,
                "couch_angle": 0,
                "energy": 6,
                "technique": "STATIC",
                "weight": 1.0,
                "mlc": None,
                "jaw_positions": {"X1": -10, "X2": 10, "Y1": -10, "Y2": 10}
            },
            {
                "id": "PA",
                "gantry_angle": 180,
                "collimator_angle": 0,
                "couch_angle": 0,
                "energy": 6,
                "technique": "STATIC",
                "weight": 1.0,
                "mlc": None,
                "jaw_positions": {"X1": -10, "X2": 10, "Y1": -10, "Y2": 10}
            },
            {
                "id": "RLAT",
                "gantry_angle": 270,
                "collimator_angle": 0,
                "couch_angle": 0,
                "energy": 6,
                "technique": "STATIC",
                "weight": 1.0,
                "mlc": None,
                "jaw_positions": {"X1": -10, "X2": 10, "Y1": -10, "Y2": 10}
            },
            {
                "id": "LLAT",
                "gantry_angle": 90,
                "collimator_angle": 0,
                "couch_angle": 0,
                "energy": 6,
                "technique": "STATIC",
                "weight": 1.0,
                "mlc": None,
                "jaw_positions": {"X1": -10, "X2": 10, "Y1": -10, "Y2": 10}
            }
        ]
        
        # Cập nhật các thông số chùm tia từ các thuộc tính của lớp
        for i, beam in enumerate(getattr(self, "beams", {})):
            if i < len(self.beam_angles):
                beam["gantry_angle"] = self.beam_angles[i]
            if i < len(self.collimator_angles):
                beam["collimator_angle"] = self.collimator_angles[i]
            if i < len(self.couch_angles):
                beam["couch_angle"] = self.couch_angles[i]
            
            beam["energy"] = self.beam_energy
            
            # Cài đặt thông số wedge nếu cần
            if self.use_wedges and i < len(self.wedge_angles) and self.wedge_angles[i] > 0:
                beam["wedge"] = {
                    "angle": self.wedge_angles[i],
                    "orientation": 0,  # Mặc định theo hướng Y
                    "type": "physical"
                }
        
        # Nếu có cấu trúc PTV, tự động điều chỉnh kích thước trường
        if "PTV" in structures or "ptv" in structures:
            ptv_key = "PTV" if "PTV" in structures else "ptv"
            ptv = structures[ptv_key]
            
            # Tính toán kích thước trường dựa trên PTV
            # Đây chỉ là logic đơn giản, cần cải thiện trong ứng dụng thực tế
            logger.info("Đang điều chỉnh kích thước trường dựa trên PTV")
            field_margin = 10  # mm
            
            # Mô phỏng việc tính margin - trong thực tế sẽ phức tạp hơn
            field_size_x = 40  # mm
            field_size_y = 40  # mm
            
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
    
    def set_beam_angles(self, angles: List[float]):
        """
        Thiết lập các góc chùm tia
        
        Args:
            angles: Danh sách các góc chùm tia (độ)
        """
        self.beam_angles = angles
        logger.info(f"Đã thiết lập các góc chùm tia: {angles}")
    
    def set_beam_energy(self, energy: float):
        """
        Thiết lập năng lượng chùm tia
        
        Args:
            energy: Năng lượng chùm tia (MV)
        """
        self.beam_energy = energy
        logger.info(f"Đã thiết lập năng lượng chùm tia: {energy} MV")
    
    def enable_wedges(self, wedge_angles: List[float]):
        """
        Bật sử dụng wedge với các góc cho trước
        
        Args:
            wedge_angles: Danh sách các góc wedge cho từng chùm tia (độ)
        """
        self.use_wedges = True
        self.wedge_angles = wedge_angles
        logger.info(f"Đã bật sử dụng wedge với các góc: {wedge_angles}")
    
    def disable_wedges(self):
        """Tắt sử dụng wedge"""
        self.use_wedges = False
        logger.info("Đã tắt sử dụng wedge") 