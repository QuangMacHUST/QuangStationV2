#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module cung cấp kỹ thuật xạ trị Field-in-Field (FIF) cho QuangStation V2.
"""

import numpy as np
import random
from typing import Dict, List, Tuple, Optional, Any
from quangstation.clinical.planning.techniques.base import RTTechnique
from quangstation.core.utils.logging import get_logger

logger = get_logger(__name__)

class FieldInField(RTTechnique):
    """Kỹ thuật Field-in-Field (FIF)"""
    
    def __init__(self):
        super().__init__("FIF")
        self.description = "Kỹ thuật Field-in-Field (trường trong trường) để tối ưu phân bố liều"
        
        # Thông số mặc định
        self.beam_energy = 6.0  # MV
        self.main_beam_angles = [0, 180]  # degrees - thường là các trường đối diện
        self.num_subfields = 2  # Số trường con cho mỗi trường chính
        self.collimator_angles = [0, 0]  # degrees
        self.couch_angles = [0, 0]  # degrees
        self.subfield_weight_reduction = 0.3  # Mức giảm trọng số cho mỗi trường con
        
    def create_plan(self, structures: Dict[str, np.ndarray]) -> Dict:
        """
        Tạo kế hoạch Field-in-Field
        
        Args:
            structures: Dictionary chứa các cấu trúc (key: tên cấu trúc, value: mảng numpy)
            
        Returns:
            Dictionary chứa thông tin kế hoạch
        """
        self.beams = []
        
        # Tạo các trường chính
        for i, angle in enumerate(self.main_beam_angles):
            beam_id = f"Main_{i+1}"
            if angle == 0:
                beam_id = "AP"
            elif angle == 180:
                beam_id = "PA"
            elif angle == 90:
                beam_id = "LLAT"
            elif angle == 270:
                beam_id = "RLAT"
            
            # Trường chính có trọng số là 1.0
            main_beam = {
                "id": beam_id,
                "gantry_angle": angle,
                "collimator_angle": self.collimator_angles[i] if i < len(self.collimator_angles) else 0,
                "couch_angle": self.couch_angles[i] if i < len(self.couch_angles) else 0,
                "energy": self.beam_energy,
                "technique": "STATIC",
                "weight": 1.0,
                "mlc": None,  # Sẽ được cập nhật sau dựa trên PTV
                "jaw_positions": {"X1": -10, "X2": 10, "Y1": -10, "Y2": 10}  # Kích thước mặc định
            }
            
            getattr(self, "beams", {}).append(main_beam)
            
            # Tạo các trường con cho mỗi trường chính
            for j in range(self.num_subfields):
                subfield_weight = 1.0 - (j + 1) * self.subfield_weight_reduction
                if subfield_weight < 0.1:
                    subfield_weight = 0.1  # Đảm bảo trọng số tối thiểu
                
                subfield = {
                    "id": f"{beam_id}_Sub_{j+1}",
                    "gantry_angle": angle,
                    "collimator_angle": self.collimator_angles[i] if i < len(self.collimator_angles) else 0,
                    "couch_angle": self.couch_angles[i] if i < len(self.couch_angles) else 0,
                    "energy": self.beam_energy,
                    "technique": "STATIC",
                    "weight": subfield_weight,
                    "mlc": self._create_blocking_mlc(True),  # MLC chặn một phần của trường
                    "jaw_positions": {"X1": -10, "X2": 10, "Y1": -10, "Y2": 10}  # Kích thước mặc định
                }
                
                getattr(self, "beams", {}).append(subfield)
        
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
    
    def _create_blocking_mlc(self, pattern: bool) -> List[List[float]]:
        """
        Tạo mẫu MLC để chặn các vùng có liều cao
        
        Args:
            pattern: Mẫu chặn
            
        Returns:
            Danh sách vị trí MLC
        """
        # Mô phỏng mẫu MLC với 80 lá (40 cặp)
        mlc_positions = []
        
        # Số lá MLC (thường là 40 cặp = 80 lá)
        num_leaves = 40
        
        # Mô phỏng các vị trí MLC ngẫu nhiên (trong thực tế sẽ dựa trên phân bố liều)
        for i in range(num_leaves):
            # Mỗi cặp lá có một vị trí mở
            if pattern:
                # Tạo một mẫu chặn ngẫu nhiên với độ mở khác nhau
                open_width = random.uniform(0.5, 2.0)  # cm
                position_x = random.uniform(-5.0, 5.0 - open_width)  # cm
                
                # Lá trên và lá dưới tương ứng
                leaf_pair = [position_x, position_x + open_width]
            else:
                # Mặc định mở hoàn toàn (-10cm đến 10cm)
                leaf_pair = [-10.0, 10.0]
                
            mlc_positions.append(leaf_pair)
            
        return mlc_positions
    
    def set_main_beam_angles(self, angles: List[float]):
        """
        Thiết lập các góc cho các trường chính
        
        Args:
            angles: Danh sách các góc chùm tia (độ)
        """
        self.main_beam_angles = angles
        logger.info(f"Đã thiết lập các góc trường chính: {angles}")
    
    def set_num_subfields(self, num: int):
        """
        Thiết lập số lượng trường con cho mỗi trường chính
        
        Args:
            num: Số lượng trường con
        """
        if num < 1:
            num = 1
        self.num_subfields = num
        logger.info(f"Đã thiết lập số lượng trường con: {num}")
    
    def set_beam_energy(self, energy: float):
        """
        Thiết lập năng lượng chùm tia
        
        Args:
            energy: Năng lượng chùm tia (MV)
        """
        self.beam_energy = energy
        logger.info(f"Đã thiết lập năng lượng chùm tia: {energy} MV")
    
    def set_subfield_weight_reduction(self, reduction: float):
        """
        Thiết lập mức giảm trọng số cho các trường con
        
        Args:
            reduction: Mức giảm trọng số (0-1)
        """
        if reduction < 0:
            reduction = 0
        elif reduction > 0.5:
            reduction = 0.5
            
        self.subfield_weight_reduction = reduction
        logger.info(f"Đã thiết lập mức giảm trọng số trường con: {reduction}") 