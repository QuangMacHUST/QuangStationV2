#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Wrapper Python cho module tính toán liều C++.
"""

import os
import numpy as np
from typing import Dict, List, Tuple, Optional, Any

try:
    from quangstation.dose_calculation.dose_engine import CollapsedConeConvolution, PencilBeam
    HAS_CPP_MODULE = True
except ImportError:
    HAS_CPP_MODULE = False
    from quangstation.utils.logging import get_logger
    logger = get_logger("DoseCalculation")
    logger.log_warning("Không thể import module C++ _dose_engine. Sử dụng phiên bản Python thuần túy.")

class DoseCalculator:
    """
    Lớp wrapper cho các thuật toán tính toán liều.
    Hỗ trợ cả triển khai C++ và Python thuần túy.
    """
    
    ALGO_COLLAPSED_CONE = "collapsed_cone"
    ALGO_PENCIL_BEAM = "pencil_beam"
    
    def __init__(self, algorithm: str = ALGO_COLLAPSED_CONE, resolution_mm: float = 3.0):
        """
        Khởi tạo bộ tính toán liều
        
        Args:
            algorithm: Thuật toán tính toán liều ('collapsed_cone' hoặc 'pencil_beam')
            resolution_mm: Độ phân giải lưới liều (mm)
        """
        self.algorithm = algorithm
        self.resolution_mm = resolution_mm
        self.beam_data = []
        self.structures = {}
        self.patient_data = None
        
        # Nếu có module C++, sử dụng nó
        if HAS_CPP_MODULE:
            if algorithm == self.ALGO_COLLAPSED_CONE:
                self._algo = CollapsedConeConvolution(resolution=resolution_mm)
            elif algorithm == self.ALGO_PENCIL_BEAM:
                self._algo = PencilBeam(resolution=resolution_mm)
            else:
                raise ValueError(f"Thuật toán không hợp lệ: {algorithm}")
        else:
            self._algo = None  # Sẽ sử dụng triển khai Python thuần túy
    
    def set_patient_data(self, image_data: np.ndarray, spacing: List[float]):
        """
        Đặt dữ liệu hình ảnh bệnh nhân
        
        Args:
            image_data: Ma trận 3D chứa dữ liệu HU
            spacing: Khoảng cách voxel [x, y, z] (mm)
        """
        self.patient_data = {
            "image_data": image_data,
            "spacing": spacing
        }
        
        if HAS_CPP_MODULE and self.hu_to_density_file:
            self._algo.set_hu_to_ed_conversion_file(self.hu_to_density_file)
    
    def set_hu_to_density_file(self, file_path: str):
        """
        Đặt file chuyển đổi giá trị HU sang mật độ electron tương đối
        
        Args:
            file_path: Đường dẫn đến file chuyển đổi
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Không tìm thấy file chuyển đổi HU: {file_path}")
        
        self.hu_to_density_file = file_path
        
        if HAS_CPP_MODULE and hasattr(self, '_algo'):
            self._algo.set_hu_to_ed_conversion_file(file_path)
    
    def add_beam(self, beam_data: Dict[str, Any]):
        """
        Thêm chùm tia
        
        Args:
            beam_data: Thông tin chùm tia (góc, năng lượng, trọng số, v.v.)
        """
        self.beam_data.append(beam_data)
    
    def add_structure(self, name: str, mask: np.ndarray):
        """
        Thêm cấu trúc
        
        Args:
            name: Tên cấu trúc
            mask: Ma trận mask của cấu trúc (0 hoặc 1)
        """
        self.structures[name] = mask
    
    def calculate_dose(self) -> np.ndarray:
        """
        Tính toán liều
        
        Returns:
            Ma trận 3D chứa dữ liệu liều
        """
        if not self.patient_data:
            raise ValueError("Chưa đặt dữ liệu bệnh nhân")
        
        if not self.beam_data:
            raise ValueError("Chưa thêm chùm tia")
        
        # Nếu có module C++, sử dụng nó
        if HAS_CPP_MODULE and self._algo:
            return self._calculate_dose_cpp()
        else:
            return self._calculate_dose_python()
    
    def _calculate_dose_cpp(self) -> np.ndarray:
        """
        Tính toán liều sử dụng module C++
        
        Returns:
            Ma trận 3D chứa dữ liệu liều
        """
        # Chuẩn bị dữ liệu đầu vào cho module C++
        image_data = self.patient_data["image_data"]
        spacing = self.patient_data["spacing"]
        
        # Chuyển đổi beam_data thành định dạng phù hợp với module C++
        beams = []
        for beam in self.beam_data:
            # TODO: Chuyển đổi từ định dạng Python sang C++
            beams.append(beam)
        
        # Chuyển đổi structures thành định dạng phù hợp với module C++
        structures_cpp = {}
        for name, mask in self.structures.items():
            structures_cpp[name] = mask
        
        # Gọi hàm tính toán liều C++
        dose_matrix = self._algo.calculateDose(
            image_data,
            spacing,
            beams,
            structures_cpp
        )
        
        return dose_matrix
    
    def _calculate_dose_python(self) -> np.ndarray:
        """
        Tính toán liều sử dụng triển khai Python thuần túy
        
        Returns:
            Ma trận 3D chứa dữ liệu liều
        """
        # Triển khai thuật toán tính toán liều đơn giản bằng Python
        # Đây chỉ là phiên bản giả để minh họa và dự phòng
        
        from quangstation.utils.logging import get_logger
        logger = get_logger("DoseCalculation")
        logger.log_warning("Sử dụng triển khai Python thuần túy cho tính toán liều. Hiệu suất sẽ thấp hơn.")
        
        image_data = self.patient_data["image_data"]
        shape = image_data.shape
        
        # Tạo ma trận liều với các giá trị 0
        dose_matrix = np.zeros(shape, dtype=np.float32)
        
        # Đối với mỗi chùm tia, tính liều đóng góp
        for beam in self.beam_data:
            # Lấy thông tin chùm tia
            gantry_angle = beam.get("gantry_angle", 0)
            energy = beam.get("energy", 6)
            weight = beam.get("weight", 1.0)
            
            # Tính toán đường đi của tia
            # (Đây chỉ là một mô phỏng đơn giản)
            
            # Áp dụng suy giảm theo độ sâu
            # (Đây chỉ là một mô phỏng đơn giản)
            
            # Cộng dồn vào ma trận liều
            
        # Chuẩn hóa ma trận liều
        if np.max(dose_matrix) > 0:
            dose_matrix = dose_matrix * (100.0 / np.max(dose_matrix))
        
        return dose_matrix
    
    def save_dose_matrix(self, file_path: str):
        """
        Lưu ma trận liều vào file
        
        Args:
            file_path: Đường dẫn file
        """
        # TODO: Implement save dose matrix
        pass
    
    def load_dose_matrix(self, file_path: str) -> np.ndarray:
        """
        Tải ma trận liều từ file
        
        Args:
            file_path: Đường dẫn file
            
        Returns:
            Ma trận liều
        """
        # TODO: Implement load dose matrix
        pass

# Tạo instance mặc định
default_calculator = DoseCalculator()
