#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module quản lý danh sách cơ quan và cấu trúc cơ thể cho QuangStation V2.
"""

import json
import os
import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any
from pathlib import Path

from quangstation.utils.logging import get_logger
logger = get_logger("OrganLibrary")

class OrganProperties:
    """Lớp chứa thuộc tính của cơ quan"""
    
    def __init__(self, name: str, color: str = "#FF0000", hu_range: Tuple[int, int] = None, 
                density: float = None, alpha_beta: float = None, priority: int = 0,
                category: str = "Other"):
        """
        Khởi tạo thuộc tính của cơ quan
        
        Args:
            name: Tên cơ quan
            color: Mã màu hiển thị (hex code)
            hu_range: Phạm vi HU thường gặp của mô (min, max)
            density: Mật độ tương đối của mô
            alpha_beta: Tỷ số alpha/beta cho mô (Gy)
            priority: Độ ưu tiên (0-100)
            category: Phân loại (Target, OAR, Normal, Other)
        """
        self.name = name
        self.display_name = name
        self.color = color
        self.hu_range = hu_range if hu_range else (-100, 100)
        self.density = density if density else 1.0
        self.alpha_beta = alpha_beta if alpha_beta else 10.0
        self.priority = priority
        self.category = category
        self.dose_constraints = []
        self.visible = True
        self.custom = False
        
    def to_dict(self) -> Dict:
        """Chuyển đổi thành dictionary để lưu trữ"""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "color": self.color,
            "hu_range": self.hu_range,
            "density": self.density,
            "alpha_beta": self.alpha_beta,
            "priority": self.priority,
            "category": self.category,
            "dose_constraints": self.dose_constraints,
            "visible": self.visible,
            "custom": self.custom
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'OrganProperties':
        """Tạo đối tượng từ dictionary"""
        organ = cls(
            name=data.get("name", "Unknown"),
            color=data.get("color", "#FF0000"),
            hu_range=data.get("hu_range", (-100, 100)),
            density=data.get("density", 1.0),
            alpha_beta=data.get("alpha_beta", 10.0),
            priority=data.get("priority", 0),
            category=data.get("category", "Other")
        )
        organ.display_name = data.get("display_name", organ.name)
        organ.dose_constraints = data.get("dose_constraints", [])
        organ.visible = data.get("visible", True)
        organ.custom = data.get("custom", False)
        return organ
        
    def add_dose_constraint(self, constraint_type: str, dose: float, volume: float = None, 
                         priority: int = 1, protocol: str = "General"):
        """
        Thêm ràng buộc liều
        
        Args:
            constraint_type: Loại ràng buộc (max, min, mean, d_xx, v_xx)
            dose: Giá trị liều (Gy)
            volume: Giá trị thể tích (%) cho ràng buộc D/V
            priority: Độ ưu tiên (1-5)
            protocol: Protocol liên quan
        """
        self.dose_constraints.append({
            "type": constraint_type,
            "dose": dose,
            "volume": volume,
            "priority": priority,
            "protocol": protocol
        })

class OrganLibrary:
    """Quản lý thư viện cơ quan và cấu trúc cơ thể"""
    
    def __init__(self, config_file: str = None):
        """
        Khởi tạo thư viện cơ quan
        
        Args:
            config_file: Đường dẫn đến file cấu hình (nếu None, sử dụng mặc định)
        """
        self.organs = {}  # Dictionary chứa tất cả cơ quan {name: OrganProperties}
        self.categories = {
            "Target": {"priority": 100, "description": "Vùng mục tiêu (PTV, CTV, GTV)"},
            "OAR": {"priority": 80, "description": "Cơ quan nguy cấp (Organs At Risk)"},
            "Normal": {"priority": 50, "description": "Mô bình thường"},
            "Reference": {"priority": 30, "description": "Cấu trúc tham chiếu"},
            "External": {"priority": 20, "description": "Body outline"},
            "Other": {"priority": 0, "description": "Cấu trúc khác"}
        }
        
        # Tải cấu hình
        if config_file is None:
            # Sử dụng file cấu hình mặc định trong thư mục resources
            config_dir = Path(__file__).parent.parent.parent / "resources" / "config"
            config_file = config_dir / "organ_library.json"
            if not config_file.exists():
                # Tạo thư mục nếu chưa tồn tại
                config_dir.mkdir(parents=True, exist_ok=True)
                # Tạo file cấu hình mặc định
                self._create_default_config(str(config_file))
        
        # Tải cấu hình từ file
        self.load_config(config_file)
        
    def _create_default_config(self, config_file: str):
        """Tạo file cấu hình mặc định với danh sách cơ quan cơ bản"""
        default_organs = self._generate_default_organs()
        
        # Lưu vào file
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump({
                "categories": self.categories,
                "organs": {name: organ.to_dict() for name, organ in default_organs.items()}
            }, f, indent=4, ensure_ascii=False)
            
        logger.info(f"Đã tạo file cấu hình mặc định: {config_file}")
        
    def _generate_default_organs(self) -> Dict[str, OrganProperties]:
        """Tạo danh sách cơ quan mặc định"""
        default_organs = {}
        
        # PTV, CTV, GTV
        default_organs["PTV"] = OrganProperties("PTV", "#FF0000", (-100, 100), 1.0, 10.0, 100, "Target")
        default_organs["PTV"].display_name = "PTV (Planning Target Volume)"
        default_organs["PTV"].add_dose_constraint("min", 95.0, 95.0, 5, "General")  # 95% thể tích nhận ít nhất 95% liều
        
        default_organs["CTV"] = OrganProperties("CTV", "#FFA500", (-100, 100), 1.0, 10.0, 95, "Target")
        default_organs["CTV"].display_name = "CTV (Clinical Target Volume)"
        
        default_organs["GTV"] = OrganProperties("GTV", "#FF4500", (-100, 100), 1.0, 10.0, 90, "Target")
        default_organs["GTV"].display_name = "GTV (Gross Tumor Volume)"
        default_organs["GTV"].add_dose_constraint("min", 100.0, 98.0, 5, "General")  # 98% thể tích nhận 100% liều
        
        # Cơ quan nguy cấp
        default_organs["Brain"] = OrganProperties("Brain", "#A9A9A9", (0, 100), 1.04, 2.1, 80, "OAR")
        default_organs["Brain"].add_dose_constraint("max", 60.0, None, 3, "General")
        
        default_organs["BrainStem"] = OrganProperties("BrainStem", "#8B008B", (0, 100), 1.04, 2.0, 85, "OAR")
        default_organs["BrainStem"].display_name = "Thân não"
        default_organs["BrainStem"].add_dose_constraint("max", 54.0, None, 4, "General")
        
        default_organs["SpinalCord"] = OrganProperties("SpinalCord", "#FFFF00", (0, 100), 1.04, 2.0, 85, "OAR")
        default_organs["SpinalCord"].display_name = "Tủy sống"
        default_organs["SpinalCord"].add_dose_constraint("max", 45.0, None, 5, "General")
        default_organs["SpinalCord"].add_dose_constraint("max", 50.0, 0.03, 4, "General")  # 0.03cc < 50Gy
        
        default_organs["Lung_Left"] = OrganProperties("Lung_Left", "#ADD8E6", (-800, -500), 0.25, 4.0, 75, "OAR")
        default_organs["Lung_Left"].display_name = "Phổi trái"
        default_organs["Lung_Left"].add_dose_constraint("mean", 20.0, None, 3, "General")
        default_organs["Lung_Left"].add_dose_constraint("max", 30.0, 30.0, 2, "General")  # V30 < 30%
        
        default_organs["Lung_Right"] = OrganProperties("Lung_Right", "#87CEFA", (-800, -500), 0.25, 4.0, 75, "OAR")
        default_organs["Lung_Right"].display_name = "Phổi phải"
        default_organs["Lung_Right"].add_dose_constraint("mean", 20.0, None, 3, "General")
        default_organs["Lung_Right"].add_dose_constraint("max", 30.0, 30.0, 2, "General")  # V30 < 30%
        
        default_organs["Heart"] = OrganProperties("Heart", "#FF69B4", (0, 100), 1.05, 2.5, 80, "OAR")
        default_organs["Heart"].display_name = "Tim"
        default_organs["Heart"].add_dose_constraint("mean", 26.0, None, 3, "General")
        default_organs["Heart"].add_dose_constraint("max", 40.0, 50.0, 2, "General")  # V40 < 50%
        
        default_organs["Esophagus"] = OrganProperties("Esophagus", "#FFA07A", (-100, 100), 1.03, 3.0, 70, "OAR")
        default_organs["Esophagus"].display_name = "Thực quản"
        default_organs["Esophagus"].add_dose_constraint("mean", 34.0, None, 2, "General")
        
        default_organs["Liver"] = OrganProperties("Liver", "#8B4513", (50, 100), 1.05, 3.0, 75, "OAR")
        default_organs["Liver"].display_name = "Gan"
        default_organs["Liver"].add_dose_constraint("mean", 30.0, None, 3, "General")
        default_organs["Liver"].add_dose_constraint("max", 40.0, 30.0, 2, "General")  # V40 < 30%
        
        default_organs["Kidney_Left"] = OrganProperties("Kidney_Left", "#800080", (0, 100), 1.05, 2.5, 75, "OAR")
        default_organs["Kidney_Left"].display_name = "Thận trái"
        default_organs["Kidney_Left"].add_dose_constraint("mean", 18.0, None, 3, "General")
        
        default_organs["Kidney_Right"] = OrganProperties("Kidney_Right", "#9932CC", (0, 100), 1.05, 2.5, 75, "OAR")
        default_organs["Kidney_Right"].display_name = "Thận phải"
        default_organs["Kidney_Right"].add_dose_constraint("mean", 18.0, None, 3, "General")
        
        default_organs["Bladder"] = OrganProperties("Bladder", "#00FFFF", (-100, 100), 1.03, 5.0, 70, "OAR")
        default_organs["Bladder"].display_name = "Bàng quang"
        default_organs["Bladder"].add_dose_constraint("max", 65.0, 50.0, 2, "General")  # V65 < 50%
        
        default_organs["Rectum"] = OrganProperties("Rectum", "#FF8C00", (-100, 100), 1.03, 3.0, 75, "OAR")
        default_organs["Rectum"].display_name = "Trực tràng"
        default_organs["Rectum"].add_dose_constraint("max", 75.0, 15.0, 3, "General")  # V75 < 15%
        default_organs["Rectum"].add_dose_constraint("max", 70.0, 20.0, 3, "General")  # V70 < 20%
        default_organs["Rectum"].add_dose_constraint("max", 50.0, 50.0, 2, "General")  # V50 < 50%
        
        default_organs["Parotid_Left"] = OrganProperties("Parotid_Left", "#98FB98", (-100, 100), 1.03, 3.0, 70, "OAR")
        default_organs["Parotid_Left"].display_name = "Tuyến mang tai trái"
        default_organs["Parotid_Left"].add_dose_constraint("mean", 26.0, None, 2, "General")
        
        default_organs["Parotid_Right"] = OrganProperties("Parotid_Right", "#90EE90", (-100, 100), 1.03, 3.0, 70, "OAR")
        default_organs["Parotid_Right"].display_name = "Tuyến mang tai phải"
        default_organs["Parotid_Right"].add_dose_constraint("mean", 26.0, None, 2, "General")
        
        # Cấu trúc tham chiếu và bên ngoài
        default_organs["Body"] = OrganProperties("Body", "#00FF00", (-1000, 3000), 1.0, 3.0, 20, "External")
        default_organs["Body"].display_name = "Body Outline"
        
        default_organs["Ring"] = OrganProperties("Ring", "#808080", (-1000, 3000), 1.0, 3.0, 40, "Reference")
        default_organs["Ring"].display_name = "Ring Structure"
        
        return default_organs
        
    def load_config(self, config_file: str):
        """Tải cấu hình từ file"""
        if not os.path.exists(config_file):
            logger.warning(f"Không tìm thấy file cấu hình: {config_file}, sử dụng cấu hình mặc định")
            self.organs = self._generate_default_organs()
            return
            
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            # Tải danh mục
            if "categories" in config:
                self.categories = config["categories"]
                
            # Tải cơ quan
            if "organs" in config:
                self.organs = {}
                for name, organ_data in config["organs"].items():
                    self.organs[name] = OrganProperties.from_dict(organ_data)
                    
            logger.info(f"Đã tải cấu hình từ file: {config_file}")
        except Exception as error:
            logger.error(f"Lỗi khi tải cấu hình: {str(error)}")
            # Sử dụng cấu hình mặc định
            self.organs = self._generate_default_organs()
            
    def save_config(self, config_file: str):
        """Lưu cấu hình vào file"""
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "categories": self.categories,
                    "organs": {name: organ.to_dict() for name, organ in self.organs.items()}
                }, f, indent=4, ensure_ascii=False)
                
            logger.info(f"Đã lưu cấu hình vào file: {config_file}")
            return True
        except Exception as error:
            logger.error(f"Lỗi khi lưu cấu hình: {str(error)}")
            return False
            
    def get_organ(self, name: str) -> Optional[OrganProperties]:
        """Lấy thông tin cơ quan theo tên"""
        return self.organs.get(name)
        
    def get_organs_by_category(self, category: str) -> List[OrganProperties]:
        """Lấy danh sách cơ quan theo danh mục"""
        return [organ for organ in self.organs.values() if organ.category == category]
        
    def get_all_organs(self) -> List[OrganProperties]:
        """Lấy danh sách tất cả cơ quan"""
        return list(self.organs.values())
        
    def add_organ(self, organ: OrganProperties) -> bool:
        """Thêm cơ quan mới vào thư viện"""
        if organ.name in self.organs:
            logger.warning(f"Cơ quan {organ.name} đã tồn tại")
            return False
            
        self.organs[organ.name] = organ
        logger.info(f"Đã thêm cơ quan: {organ.name}")
        return True
        
    def update_organ(self, organ: OrganProperties) -> bool:
        """Cập nhật thông tin cơ quan"""
        if organ.name not in self.organs:
            logger.warning(f"Không tìm thấy cơ quan: {organ.name}")
            return False
            
        self.organs[organ.name] = organ
        logger.info(f"Đã cập nhật cơ quan: {organ.name}")
        return True
        
    def delete_organ(self, name: str) -> bool:
        """Xóa cơ quan khỏi thư viện"""
        if name not in self.organs:
            logger.warning(f"Không tìm thấy cơ quan: {name}")
            return False
            
        # Kiểm tra xem có phải cơ quan mặc định không
        if not self.organs[name].custom:
            logger.warning(f"Không thể xóa cơ quan mặc định: {name}")
            return False
            
        del self.organs[name]
        logger.info(f"Đã xóa cơ quan: {name}")
        return True
        
    def create_custom_organ(self, name: str, display_name: str, color: str, category: str, 
                         hu_range: Tuple[int, int] = None, density: float = None, 
                         alpha_beta: float = None) -> OrganProperties:
        """Tạo cơ quan tùy chỉnh mới"""
        # Tạo tên không trùng lặp
        base_name = name
        counter = 1
        while name in self.organs:
            name = f"{base_name}_{counter}"
            counter += 1
            
        # Tạo cơ quan mới
        organ = OrganProperties(name, color, hu_range, density, alpha_beta, 0, category)
        organ.display_name = display_name
        organ.custom = True
        
        # Thêm vào thư viện
        self.organs[name] = organ
        logger.info(f"Đã tạo cơ quan tùy chỉnh: {name}")
        
        return organ

# Tạo instance singleton
_organ_library_instance = None

def get_organ_library() -> OrganLibrary:
    """Lấy instance của thư viện cơ quan"""
    global _organ_library_instance
    if _organ_library_instance is None:
        _organ_library_instance = OrganLibrary()
    return _organ_library_instance 