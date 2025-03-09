#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module cung cấp các kỹ thuật xạ trị khác nhau cho QuangStation V2.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any

class RTTechnique:
    """Lớp cơ sở cho các kỹ thuật xạ trị"""
    
    def __init__(self, name: str):
        self.name = name
        self.description = ""
        self.beams = []
        
    def get_beam_setup(self) -> List[Dict]:
        """Trả về thiết lập chùm tia cho kỹ thuật này"""
        return self.beams
        
    def create_plan(self, structures: Dict[str, np.ndarray]) -> Dict:
        """Tạo kế hoạch xạ trị dựa trên các cấu trúc"""
        raise NotImplementedError("Subclasses must implement this method")

class Conventional3DCRT(RTTechnique):
    """Kỹ thuật xạ trị 3D thông thường"""
    
    def __init__(self):
        super().__init__("3DCRT")
        self.description = "Xạ trị 3D thông thường với các trường hình dạng cố định"
        
    def create_plan(self, structures: Dict[str, np.ndarray]) -> Dict:
        """Tạo kế hoạch 3DCRT với 4 trường tiêu chuẩn"""
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
        
        return {
            "technique": self.name,
            "beams": self.beams,
            "prescription": {"dose": 50.0, "fractions": 25}
        }

class FieldInField(RTTechnique):
    """Kỹ thuật Field-in-Field (FIF)"""
    
    def __init__(self):
        super().__init__("FIF")
        self.description = "Kỹ thuật Field-in-Field (trường trong trường) để tối ưu phân bố liều"
        
    def create_plan(self, structures: Dict[str, np.ndarray]) -> Dict:
        """Tạo kế hoạch Field-in-Field (FIF) cơ bản"""
        
        # Trường chính
        main_fields = [
            {
                "id": "AP_Main",
                "gantry_angle": 0,
                "collimator_angle": 0,
                "couch_angle": 0,
                "energy": 6,
                "technique": "STATIC",
                "weight": 0.7,
                "mlc": None,
                "jaw_positions": {"X1": -10, "X2": 10, "Y1": -10, "Y2": 10}
            },
            {
                "id": "PA_Main",
                "gantry_angle": 180,
                "collimator_angle": 0,
                "couch_angle": 0,
                "energy": 6,
                "technique": "STATIC",
                "weight": 0.7,
                "mlc": None,
                "jaw_positions": {"X1": -10, "X2": 10, "Y1": -10, "Y2": 10}
            }
        ]
        
        # Trường trong (sub-fields)
        sub_fields = [
            {
                "id": "AP_Sub1",
                "gantry_angle": 0,
                "collimator_angle": 0,
                "couch_angle": 0,
                "energy": 6,
                "technique": "STATIC",
                "weight": 0.15,
                "mlc": self._create_blocking_mlc(True),  # Block hot spots
                "jaw_positions": {"X1": -10, "X2": 10, "Y1": -10, "Y2": 10}
            },
            {
                "id": "AP_Sub2",
                "gantry_angle": 0,
                "collimator_angle": 0,
                "couch_angle": 0,
                "energy": 6,
                "technique": "STATIC",
                "weight": 0.15,
                "mlc": self._create_blocking_mlc(False),  # Different blocking pattern
                "jaw_positions": {"X1": -10, "X2": 10, "Y1": -10, "Y2": 10}
            },
            {
                "id": "PA_Sub1",
                "gantry_angle": 180,
                "collimator_angle": 0,
                "couch_angle": 0,
                "energy": 6,
                "technique": "STATIC",
                "weight": 0.15,
                "mlc": self._create_blocking_mlc(True),  # Block hot spots
                "jaw_positions": {"X1": -10, "X2": 10, "Y1": -10, "Y2": 10}
            },
            {
                "id": "PA_Sub2",
                "gantry_angle": 180,
                "collimator_angle": 0,
                "couch_angle": 0,
                "energy": 6,
                "technique": "STATIC",
                "weight": 0.15,
                "mlc": self._create_blocking_mlc(False),  # Different blocking pattern
                "jaw_positions": {"X1": -10, "X2": 10, "Y1": -10, "Y2": 10}
            }
        ]
        
        self.beams = main_fields + sub_fields
        
        return {
            "technique": self.name,
            "beams": self.beams,
            "prescription": {"dose": 50.0, "fractions": 25}
        }
        
    def _create_blocking_mlc(self, pattern: bool) -> List[List[float]]:
        """
        Tạo mẫu MLC cho kỹ thuật FIF
        
        Args:
            pattern: Mẫu chặn - True hoặc False để tạo các mẫu khác nhau
            
        Returns:
            Danh sách vị trí MLC [[bank A positions], [bank B positions]]
        """
        # Tạo mẫu MLC - đây chỉ là ví dụ
        bank_a = []
        bank_b = []
        
        # Trong thực tế, mẫu này sẽ phức tạp hơn và phụ thuộc vào phân phối liều
        num_leaves = 60  # Giả sử máy có 60 cặp lá MLC
        
        for i in range(num_leaves):
            if pattern:
                # Mẫu 1
                if 20 <= i < 40:
                    bank_a.append(-5.0)  # Chặn vùng giữa
                    bank_b.append(5.0)
                else:
                    bank_a.append(-10.0)  # Mở rộng
                    bank_b.append(10.0)
            else:
                # Mẫu 2
                if 10 <= i < 25 or 35 <= i < 50:
                    bank_a.append(-6.0)  # Chặn hai vùng khác
                    bank_b.append(6.0)
                else:
                    bank_a.append(-10.0)  # Mở rộng
                    bank_b.append(10.0)
        
        return [bank_a, bank_b]

class IMRT(RTTechnique):
    """Kỹ thuật Xạ trị điều biến cường độ (IMRT)"""
    
    def __init__(self):
        super().__init__("IMRT")
        self.description = "Xạ trị điều biến cường độ với nhiều segment trên mỗi góc"
        
    def create_plan(self, structures: Dict[str, np.ndarray]) -> Dict:
        """Tạo kế hoạch IMRT cơ bản với các góc tiêu chuẩn"""
        
        # IMRT thường dùng 5-9 trường
        imrt_angles = [0, 72, 144, 216, 288]  # 5 trường cách đều nhau
        
        self.beams = []
        
        for i, angle in enumerate(imrt_angles):
            # Mỗi trường IMRT có nhiều segment (control points)
            beam = {
                "id": f"IMRT_{i+1}",
                "gantry_angle": angle,
                "collimator_angle": 0,
                "couch_angle": 0,
                "energy": 6,
                "technique": "STATIC",
                "weight": 1.0,
                "control_points": self._create_imrt_control_points(10),  # 10 control points
                "jaw_positions": {"X1": -10, "X2": 10, "Y1": -10, "Y2": 10}
            }
            
            self.beams.append(beam)
        
        return {
            "technique": self.name,
            "beams": self.beams,
            "prescription": {"dose": 70.0, "fractions": 35}
        }
        
    def _create_imrt_control_points(self, num_segments: int) -> List[Dict]:
        """
        Tạo các control points cho IMRT
        
        Args:
            num_segments: Số segment cho trường IMRT
            
        Returns:
            Danh sách các control points
        """
        control_points = []
        
        # Tạo các segment với các mẫu MLC khác nhau
        for i in range(num_segments):
            # Trọng số của segment (tổng = 1)
            segment_weight = 1.0 / num_segments
            
            # Tạo mẫu MLC ngẫu nhiên
            # Trong thực tế, các mẫu này sẽ được tính bởi thuật toán tối ưu
            mlc_pattern = self._create_random_mlc_pattern()
            
            control_point = {
                "index": i,
                "weight": segment_weight,
                "mlc": mlc_pattern,
                "jaw_positions": {"X1": -10, "X2": 10, "Y1": -10, "Y2": 10}
            }
            
            control_points.append(control_point)
            
        return control_points
        
    def _create_random_mlc_pattern(self) -> List[List[float]]:
        """
        Tạo mẫu MLC ngẫu nhiên cho IMRT
        
        Returns:
            Danh sách vị trí MLC [[bank A positions], [bank B positions]]
        """
        num_leaves = 60
        bank_a = []
        bank_b = []
        
        np.random.seed(123)  # Đặt seed cố định cho khả năng tái tạo
        
        for i in range(num_leaves):
            # Tạo vị trí ngẫu nhiên giữa -10 và 0 cho bank A
            pos_a = max(-10.0, min(0.0, -10.0 + np.random.random() * 10.0))
            # Tạo vị trí ngẫu nhiên giữa 0 và 10 cho bank B
            pos_b = max(0.0, min(10.0, np.random.random() * 10.0))
            
            bank_a.append(pos_a)
            bank_b.append(pos_b)
            
        return [bank_a, bank_b]

class VMAT(RTTechnique):
    """Kỹ thuật Xạ trị điều biến thể tích hồ quang (VMAT)"""
    
    def __init__(self):
        super().__init__("VMAT")
        self.description = "Xạ trị điều biến thể tích hồ quang với chùm tia quay liên tục"
        
    def create_plan(self, structures: Dict[str, np.ndarray]) -> Dict:
        """Tạo kế hoạch VMAT cơ bản với các cung tiêu chuẩn"""
        
        # VMAT thường dùng 1-3 cung
        vmat_arcs = [
            {"start_angle": 181, "stop_angle": 179, "direction": 1},  # CW
            {"start_angle": 179, "stop_angle": 181, "direction": -1}  # CCW
        ]
        
        self.beams = []
        
        for i, arc in enumerate(vmat_arcs):
            # Mỗi cung VMAT có nhiều control points
            beam = {
                "id": f"VMAT_Arc{i+1}",
                "technique": "ARC",
                "energy": 6,
                "weight": 1.0,
                "is_arc": True,
                "arc_start_angle": arc["start_angle"],
                "arc_stop_angle": arc["stop_angle"],
                "arc_direction": arc["direction"],
                "collimator_angle": 30 if i%2==0 else 330,  # Xoay collimator để giảm lỗi khung
                "couch_angle": 0,
                "control_points": self._create_vmat_control_points(arc["start_angle"], 
                                                                 arc["stop_angle"], 
                                                                 arc["direction"],
                                                                 72),  # 72 control points (5 độ/point)
                "jaw_positions": {"X1": -10, "X2": 10, "Y1": -10, "Y2": 10}
            }
            
            self.beams.append(beam)
        
        return {
            "technique": self.name,
            "beams": self.beams,
            "prescription": {"dose": 70.0, "fractions": 28}
        }
        
    def _create_vmat_control_points(self, start_angle: float, stop_angle: float, 
                                  direction: int, num_points: int) -> List[Dict]:
        """
        Tạo các control points cho VMAT
        
        Args:
            start_angle: Góc bắt đầu cung (độ)
            stop_angle: Góc kết thúc cung (độ)
            direction: Hướng quay (1=CW, -1=CCW)
            num_points: Số control point
            
        Returns:
            Danh sách các control points
        """
        control_points = []
        
        # Tính toán các góc gantry cho từng control point
        # Xử lý đặc biệt khi cung đi qua 0/360 độ
        if direction > 0:  # CW
            if stop_angle < start_angle:
                stop_angle += 360
            angle_step = (stop_angle - start_angle) / (num_points - 1)
            angles = [start_angle + i * angle_step for i in range(num_points)]
            # Chuẩn hóa về [0, 360)
            angles = [angle % 360 for angle in angles]
        else:  # CCW
            if start_angle < stop_angle:
                start_angle += 360
            angle_step = (start_angle - stop_angle) / (num_points - 1)
            angles = [start_angle - i * angle_step for i in range(num_points)]
            # Chuẩn hóa về [0, 360)
            angles = [angle % 360 for angle in angles]
            
        for i, angle in enumerate(angles):
            # Trọng số của control point (không đồng đều trong VMAT)
            cp_weight = 1.0 / num_points
            if i == 0 or i == num_points - 1:
                cp_weight *= 0.5  # Trọng số giảm ở đầu và cuối cung
                
            # Tạo mẫu MLC tương ứng với góc gantry
            # Trong thực tế, mẫu này được tính bởi thuật toán tối ưu
            mlc_pattern = self._create_mlc_pattern_for_angle(angle)
            
            control_point = {
                "index": i,
                "gantry_angle": angle,
                "weight": cp_weight,
                "mlc": mlc_pattern,
                "jaw_positions": {"X1": -10, "X2": 10, "Y1": -10, "Y2": 10},
                "dose_rate": 500  # MU/min
            }
            
            control_points.append(control_point)
            
        return control_points
        
    def _create_mlc_pattern_for_angle(self, angle: float) -> List[List[float]]:
        """
        Tạo mẫu MLC cho một góc gantry cụ thể trong VMAT
        
        Args:
            angle: Góc gantry (độ)
            
        Returns:
            Danh sách vị trí MLC [[bank A positions], [bank B positions]]
        """
        num_leaves = 60
        bank_a = []
        bank_b = []
        
        # Tạo mẫu MLC dựa trên góc gantry
        # Đây chỉ là ví dụ mẫu, trong thực tế sẽ phức tạp hơn nhiều
        for i in range(num_leaves):
            # Tạo hình dạng MLC phụ thuộc vào góc (hình sin)
            modifier = np.sin(np.radians(angle) + i * 0.1) * 5.0
            
            pos_a = max(-10.0, min(0.0, -5.0 + modifier))
            pos_b = max(0.0, min(10.0, 5.0 + modifier))
            
            bank_a.append(pos_a)
            bank_b.append(pos_b)
            
        return [bank_a, bank_b]

class SRS(RTTechnique):
    """Kỹ thuật Phẫu thuật xạ trị định vị (SRS)"""
    
    def __init__(self):
        super().__init__("SRS")
        self.description = "Phẫu thuật xạ trị định vị cho các tổn thương nhỏ, liều cao"
        
    def create_plan(self, structures: Dict[str, np.ndarray]) -> Dict:
        """Tạo kế hoạch SRS cơ bản với nhiều cung nhỏ"""
        
        # SRS thường dùng nhiều cung nhỏ (non-coplanar)
        self.beams = []
        
        # Cung đồng phẳng (coplanar arcs)
        coplanar_arcs = [
            {"start": 181, "stop": 20, "couch": 0, "collimator": 45},
            {"start": 340, "stop": 179, "couch": 0, "collimator": 315},
        ]
        
        # Cung không đồng phẳng (non-coplanar arcs)
        noncoplanar_arcs = [
            {"start": 181, "stop": 20, "couch": 45, "collimator": 45},
            {"start": 340, "stop": 179, "couch": 315, "collimator": 45},
            {"start": 181, "stop": 20, "couch": 90, "collimator": 0},
        ]
        
        # Thêm cung đồng phẳng
        for i, arc in enumerate(coplanar_arcs):
            beam = {
                "id": f"SRS_Cop_Arc{i+1}",
                "technique": "ARC",
                "energy": 6,  # Có thể dùng FFF (Flattening Filter Free)
                "weight": 1.0,
                "is_arc": True,
                "arc_start_angle": arc["start"],
                "arc_stop_angle": arc["stop"],
                "arc_direction": 1,  # CW
                "collimator_angle": arc["collimator"],
                "couch_angle": arc["couch"],
                "control_points": self._create_srs_control_points(arc["start"], arc["stop"], 36),
                "jaw_positions": {"X1": -3, "X2": 3, "Y1": -3, "Y2": 3}  # Trường nhỏ
            }
            
            self.beams.append(beam)
            
        # Thêm cung không đồng phẳng
        for i, arc in enumerate(noncoplanar_arcs):
            beam = {
                "id": f"SRS_NonCop_Arc{i+1}",
                "technique": "ARC",
                "energy": 6,  # Có thể dùng FFF (Flattening Filter Free)
                "weight": 1.0,
                "is_arc": True,
                "arc_start_angle": arc["start"],
                "arc_stop_angle": arc["stop"],
                "arc_direction": 1,  # CW
                "collimator_angle": arc["collimator"],
                "couch_angle": arc["couch"],
                "control_points": self._create_srs_control_points(arc["start"], arc["stop"], 36),
                "jaw_positions": {"X1": -3, "X2": 3, "Y1": -3, "Y2": 3}  # Trường nhỏ
            }
            
            self.beams.append(beam)
        
        return {
            "technique": self.name,
            "beams": self.beams,
            "prescription": {"dose": 24.0, "fractions": 3}  # Liều cao, ít phân đoạn
        }
        
    def _create_srs_control_points(self, start_angle: float, stop_angle: float, 
                                 num_points: int) -> List[Dict]:
        """
        Tạo các control points cho SRS
        
        Args:
            start_angle: Góc bắt đầu cung (độ)
            stop_angle: Góc kết thúc cung (độ)
            num_points: Số control point
            
        Returns:
            Danh sách các control points
        """
        control_points = []
        
        # Tính toán các góc gantry
        if stop_angle < start_angle:
            stop_angle += 360
        angle_step = (stop_angle - start_angle) / (num_points - 1)
        
        for i in range(num_points):
            angle = (start_angle + i * angle_step) % 360
            
            # Tạo mẫu MLC tròn cho SRS
            mlc_pattern = self._create_circular_mlc_pattern(2.5)  # Bán kính 2.5cm
            
            control_point = {
                "index": i,
                "gantry_angle": angle,
                "weight": 1.0 / num_points,
                "mlc": mlc_pattern,
                "jaw_positions": {"X1": -3, "X2": 3, "Y1": -3, "Y2": 3},
                "dose_rate": 1400  # FFF có thể có dose rate cao
            }
            
            control_points.append(control_point)
            
        return control_points
        
    def _create_circular_mlc_pattern(self, radius_cm: float) -> List[List[float]]:
        """
        Tạo mẫu MLC hình tròn cho SRS
        
        Args:
            radius_cm: Bán kính hình tròn (cm)
            
        Returns:
            Danh sách vị trí MLC [[bank A positions], [bank B positions]]
        """
        num_leaves = 60
        leaf_width_cm = 0.5  # Giả sử leaf width là 5mm
        bank_a = []
        bank_b = []
        
        # Tạo hình tròn với MLC
        for i in range(num_leaves):
            # Vị trí tâm của leaf (cm) từ tâm trường
            y_pos = (i - num_leaves/2 + 0.5) * leaf_width_cm
            
            # Tính x_pos dựa trên phương trình hình tròn: x^2 + y^2 = r^2
            if abs(y_pos) > radius_cm:
                # Ngoài hình tròn
                x_pos = 0
            else:
                # Trong hình tròn
                x_pos = np.sqrt(radius_cm**2 - y_pos**2)
                
            bank_a.append(-x_pos)
            bank_b.append(x_pos)
            
        return [bank_a, bank_b]

class SBRT(RTTechnique):
    """Kỹ thuật Xạ trị thân định vị (SBRT)"""
    
    def __init__(self):
        super().__init__("SBRT")
        self.description = "Xạ trị thân định vị cho các tổn thương ở thân, liều cao"
        
    def create_plan(self, structures: Dict[str, np.ndarray]) -> Dict:
        """Tạo kế hoạch SBRT cơ bản"""
        
        # SBRT thường dùng VMAT hoặc nhiều trường IMRT
        self.beams = []
        
        # Tạo 2 cung VMAT cho SBRT
        sbrt_arcs = [
            {"start": 181, "stop": 179, "collimator": 30, "direction": 1},  # CW
            {"start": 179, "stop": 181, "collimator": 330, "direction": -1}  # CCW
        ]
        
        for i, arc in enumerate(sbrt_arcs):
            beam = {
                "id": f"SBRT_Arc{i+1}",
                "technique": "ARC",
                "energy": 10,  # Năng lượng cao hơn để penetration tốt hơn
                "weight": 1.0,
                "is_arc": True,
                "arc_start_angle": arc["start"],
                "arc_stop_angle": arc["stop"],
                "arc_direction": arc["direction"],
                "collimator_angle": arc["collimator"],
                "couch_angle": 0,
                "control_points": self._create_sbrt_control_points(arc["start"], 
                                                                arc["stop"], 
                                                                arc["direction"],
                                                                72),
                "jaw_positions": {"X1": -5, "X2": 5, "Y1": -5, "Y2": 5}
            }
            
            self.beams.append(beam)
        
        return {
            "technique": self.name,
            "beams": self.beams
        }
        
    def _create_sbrt_control_points(self, start_angle: float, stop_angle: float, 
                                 direction: int, num_points: int) -> List[Dict]:
        """
        Tạo các control points cho SBRT
        
        Args:
            start_angle: Góc bắt đầu cung (độ)
            stop_angle: Góc kết thúc cung (độ)
            direction: Hướng quay (1=CW, -1=CCW)
            num_points: Số control point
            
        Returns:
            Danh sách các control points
        """
        control_points = []
        
        # Tính toán các góc gantry
        if stop_angle < start_angle:
            stop_angle += 360
        angle_step = (stop_angle - start_angle) / (num_points - 1)
        
        for i in range(num_points):
            angle = (start_angle + i * angle_step) % 360
            
            # Tạo mẫu MLC tròn cho SBRT
            mlc_pattern = self._create_circular_mlc_pattern(5.0)  # Bán kính 5cm
            
            control_point = {
                "index": i,
                "gantry_angle": angle,
                "weight": 1.0 / num_points,
                "mlc": mlc_pattern,
                "jaw_positions": {"X1": -5, "X2": 5, "Y1": -5, "Y2": 5},
                "dose_rate": 1400  # FFF có thể có dose rate cao
            }
            
            control_points.append(control_point)
            
        return control_points
        
    def _create_circular_mlc_pattern(self, radius_cm: float) -> List[List[float]]:
        """
        Tạo mẫu MLC hình tròn cho SBRT
        
        Args:
            radius_cm: Bán kính hình tròn (cm)
            
        Returns:
            Danh sách vị trí MLC [[bank A positions], [bank B positions]]
        """
        num_leaves = 60
        leaf_width_cm = 0.5  # Giả sử leaf width là 5mm
        bank_a = []
        bank_b = []
        
        # Tạo hình tròn với MLC
        for i in range(num_leaves):
            # Vị trí tâm của leaf (cm) từ tâm trường
            y_pos = (i - num_leaves/2 + 0.5) * leaf_width_cm
            
            # Tính x_pos dựa trên phương trình hình tròn: x^2 + y^2 = r^2
            if abs(y_pos) > radius_cm:
                # Ngoài hình tròn
                x_pos = 0
            else:
                # Trong hình tròn
                x_pos = np.sqrt(radius_cm**2 - y_pos**2)
                
            bank_a.append(-x_pos)
            bank_b.append(x_pos)
            
        return [bank_a, bank_b] 