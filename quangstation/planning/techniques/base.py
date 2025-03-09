#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module cung cấp lớp cơ sở cho các kỹ thuật xạ trị trong QuangStation V2.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import os
import json
import math
import copy
from quangstation.utils.logging import get_logger

logger = get_logger(__name__)

class RTTechnique:
    """Lớp cơ sở cho các kỹ thuật xạ trị"""
    
    def __init__(self, name: str):
        self.name = name
        self.description = ""
        self.beams = []
        self.isocenter = [0, 0, 0]  # mm
        self.prescription_dose = 0.0  # Gy
        self.fractions = 0
        self.metadata = {}
        
    def get_beam_setup(self) -> List[Dict]:
        """Trả về thiết lập chùm tia cho kỹ thuật này"""
        return getattr(self, "beams", {})
        
    def create_plan(self, structures: Dict[str, np.ndarray]) -> Dict:
        """Tạo kế hoạch xạ trị dựa trên các cấu trúc"""
        raise NotImplementedError("Subclasses must implement this method")

    def set_isocenter(self, position: List[float]):
        """
        Thiết lập tâm xạ trị.
        
        Args:
            position: Tọa độ tâm [x, y, z] (mm)
        """
        self.isocenter = position
        logger.info(f"Đã thiết lập tâm xạ trị tại {position}")
        
    def set_prescription(self, dose: float, fractions: int):
        """
        Thiết lập liều kê toa.
        
        Args:
            dose: Liều kê toa (Gy)
            fractions: Số phân liều
        """
        self.prescription_dose = dose
        self.fractions = fractions
        logger.info(f"Đã thiết lập liều kê toa: {dose} Gy trong {fractions} phân liều")
        
    def set_metadata(self, key: str, value: Any):
        """
        Thiết lập metadata.
        
        Args:
            key: Khóa
            value: Giá trị
        """
        self.metadata[key] = value
        
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Lấy metadata.
        
        Args:
            key: Khóa
            default: Giá trị mặc định nếu không tìm thấy
            
        Returns:
            Giá trị metadata
        """
        return self.metadata.get(key, default)
        
    def save_to_file(self, file_path: str):
        """
        Lưu kế hoạch xạ trị ra file.
        
        Args:
            file_path: Đường dẫn file
        """
        # Tạo dữ liệu cần lưu
        data = {
            'name': self.name,
            'beams': getattr(self, "beams", {}),
            'isocenter': self.isocenter,
            'prescription_dose': self.prescription_dose,
            'fractions': self.fractions,
            'metadata': self.metadata
        }
        
        # Lưu ra file JSON
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            logger.info(f"Đã lưu kế hoạch xạ trị vào {file_path}")
        except Exception as error:
            logger.error(f"Lỗi khi lưu kế hoạch xạ trị: {str(error)}")

    def load_from_file(self, file_path: str):
        """
        Tải kế hoạch xạ trị từ file.
        
        Args:
            file_path: Đường dẫn file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            self.name = data.get('name', self.name)
            self.beams = data.get('beams', [])
            self.isocenter = data.get('isocenter', [0, 0, 0])
            self.prescription_dose = data.get('prescription_dose', 0.0)
            self.fractions = data.get('fractions', 0)
            self.metadata = data.get('metadata', {})
            
            logger.info(f"Đã tải kế hoạch xạ trị từ {file_path}")
        except Exception as error:
            logger.error(f"Lỗi khi tải kế hoạch xạ trị: {str(error)}")

    def set_beam_angles(self, angles: List[float]):
        """
        Thiết lập góc gantry cho các chùm tia.
        
        Args:
            angles: Danh sách các góc (độ)
        """
        # Thêm mới hoặc cập nhật các chùm tia
        if not getattr(self, "beams", {}):
            # Tạo chùm tia mới
            for angle in angles:
                beam = {
                    'gantry_angle': angle,
                    'collimator_angle': 0.0,
                    'couch_angle': 0.0,
                    'energy': 6.0,  # MV
                    'weight': 1.0,
                    'isocenter': copy.deepcopy(self.isocenter),
                    'field_size': [10.0, 10.0],  # cm
                    'mlc': None,
                    'wedge': None,
                    'bolus': None
                }
                getattr(self, "beams", {}).append(beam)
        else:
            # Cập nhật góc gantry cho các chùm tia sẵn có
            for i, angle in enumerate(angles):
                if i < len(getattr(self, "beams", {})):
                    self.beams[i]['gantry_angle'] = angle
                else:
                    # Tạo thêm chùm tia mới nếu cần
                    beam = {
                        'gantry_angle': angle,
                        'collimator_angle': 0.0,
                        'couch_angle': 0.0,
                        'energy': 6.0,  # MV
                        'weight': 1.0,
                        'isocenter': copy.deepcopy(self.isocenter),
                        'field_size': [10.0, 10.0],  # cm
                        'mlc': None,
                        'wedge': None,
                        'bolus': None
                    }
                    getattr(self, "beams", {}).append(beam)
        
        logger.info(f"Đã thiết lập góc gantry: {angles}")
        
    def set_beam_energies(self, energies: List[float]):
        """
        Thiết lập năng lượng cho các chùm tia.
        
        Args:
            energies: Danh sách năng lượng (MV)
        """
        if not getattr(self, "beams", {}):
            logger.warning("Không có chùm tia nào để thiết lập năng lượng")
            return
            
        # Cập nhật năng lượng cho các chùm tia
        for i, energy in enumerate(energies):
            if i < len(getattr(self, "beams", {})):
                self.beams[i]['energy'] = energy
            else:
                break
                
        logger.info(f"Đã thiết lập năng lượng chùm tia: {energies}")
    
    def set_field_sizes(self, field_sizes: List[Tuple[float, float]]):
        """
        Thiết lập kích thước trường cho các chùm tia.
        
        Args:
            field_sizes: Danh sách kích thước trường (cm x cm)
        """
        if not getattr(self, "beams", {}):
            logger.warning("Không có chùm tia nào để thiết lập kích thước trường")
            return
            
        # Cập nhật kích thước trường cho các chùm tia
        for i, field_size in enumerate(field_sizes):
            if i < len(getattr(self, "beams", {})):
                self.beams[i]['field_size'] = list(field_size)
            else:
                break
                
        logger.info(f"Đã thiết lập kích thước trường: {field_sizes}")
    
    def add_beam(self, beam_data: Dict[str, Any]):
        """
        Thêm một chùm tia mới.
        
        Args:
            beam_data: Dữ liệu chùm tia
        """
        # Đảm bảo có các trường cần thiết
        default_beam = {
            'gantry_angle': 0.0,
            'collimator_angle': 0.0,
            'couch_angle': 0.0,
            'energy': 6.0,
            'weight': 1.0,
            'isocenter': copy.deepcopy(self.isocenter),
            'field_size': [10.0, 10.0],
            'mlc': None,
            'wedge': None,
            'bolus': None
        }
        
        # Cập nhật với dữ liệu được cung cấp
        for key, value in beam_data.items():
            default_beam[key] = value
            
        # Thêm vào danh sách
        getattr(self, "beams", {}).append(default_beam)
        logger.info(f"Đã thêm chùm tia mới: góc gantry {default_beam['gantry_angle']}, năng lượng {default_beam['energy']} MV")
    
    def remove_beam(self, index: int):
        """
        Xóa một chùm tia.
        
        Args:
            index: Chỉ số chùm tia cần xóa
        """
        if 0 <= index < len(self.beams):
            removed_beam = self.beams.pop(index)
            logger.info(f"Đã xóa chùm tia tại góc gantry {removed_beam['gantry_angle']}")
        else:
            logger.warning(f"Chỉ số chùm tia không hợp lệ: {index}")
    
    def update_beam(self, index: int, properties: Dict[str, Any]):
        """
        Cập nhật thuộc tính của một chùm tia.
        
        Args:
            index: Chỉ số chùm tia
            properties: Các thuộc tính cần cập nhật
        """
        if 0 <= index < len(self.beams):
            beam = self.beams[index]
            for key, value in properties.items():
                beam[key] = value
            logger.info(f"Đã cập nhật chùm tia {index}")
        else:
            logger.warning(f"Chỉ số chùm tia không hợp lệ: {index}")
    
    def get_beams(self) -> List[Dict[str, Any]]:
        """
        Lấy danh sách tất cả các chùm tia.
        
        Returns:
            List[Dict]: Danh sách các chùm tia
        """
        return copy.deepcopy(getattr(self, "beams", {})) 