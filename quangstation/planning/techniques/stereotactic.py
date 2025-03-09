#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module ky thuat xa phau dinh vi lap the (SRS/SBRT) cho QuangStation V2.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import os

from quangstation.planning.techniques.base import RTTechnique
from quangstation.utils.logging import get_logger

logger = get_logger(__name__)

class StereotacticRT(RTTechnique):
    """
    Lop ky thuat xa phau dinh vi lap the (SRS/SBRT)
    Ho tro ca xa phau nao (SRS) va xa tri than dinh vi (SBRT).
    """
    
    def __init__(self):
        """Khoi tao ky thuat xa phau dinh vi lap the."""
        super().__init__()
        self.name = "Stereotactic RT"
        self.is_srs = True          # True: SRS (nao), False: SBRT (than)
        self.use_couch_rotation = True  # Su dung xoay ban
        self.max_dose_per_fraction = 24.0  # Gy
        self.high_resolution = True  # Su dung luoi tinh toan do phan giai cao
        self.use_non_coplanar = True  # Su dung chum khong dong phang
        self.margin_mm = 1.0        # Le PTV mac dinh (mm)
        self.use_multiple_isocenters = False  # Nhieu tam
        self.isocenters = []
        self.beam_configuration = "dynamic_arcs"  # "static", "dynamic_arcs", "hybrid"
        self.beams = []
        self.arc_spacing_deg = 45.0  # Do phan cach giua cac cung (do)
        self.arc_length_deg = 120.0  # Chieu dai cung (do)
        
    def create_plan(self, structures: Dict[str, np.ndarray]) -> Dict:
        """Tao ke hoach xa phau dinh vi co ban."""
        plan_data = super().create_plan(structures)
        
        # Cap nhat thong tin ky thuat cho ke hoach
        technique_type = "SRS" if self.is_srs else "SBRT"
        plan_data.update({
            "technique": technique_type,
            "technique_subtype": "StereotacticRT",
            "fractions": 1 if self.is_srs else 5,  # Mac dinh: SRS: 1 lan, SBRT: 5 lan
            "high_resolution": self.high_resolution,
            "use_non_coplanar": self.use_non_coplanar,
            "margin_mm": self.margin_mm,
            "use_multiple_isocenters": self.use_multiple_isocenters,
            "beam_configuration": self.beam_configuration
        })
        
        # Tinh toan va dien lieu ke toa
        if self.is_srs:
            # SRS mac dinh: lam mot lan, lieu cao
            plan_data["prescribed_dose"] = 18.0  # Gy
            plan_data["dose_per_fraction"] = 18.0  # Gy
        else:
            # SBRT mac dinh: 5 lan, 10Gy moi lan, 50Gy tong cong
            plan_data["prescribed_dose"] = 50.0  # Gy
            plan_data["dose_per_fraction"] = 10.0  # Gy
        
        # Tao cac chum tia/cung mac dinh
        self._create_default_beams(plan_data)
        
        return plan_data
    
    def _create_default_beams(self, plan_data: Dict[str, Any]):
        """Tao cac chum tia/cung mac dinh dua tren cau hinh."""
        self.beams = []
        
        # Cau hinh chum cho SRS/SBRT phu thuoc vao loai
        if self.beam_configuration == "static":
            # Tao cac chum tia co dinh (khong phai cung)
            if self.use_non_coplanar:
                # Chum khong dong phang
                beam_configs = [
                    {"gantry_angle": 0, "couch_angle": 0},      # Thang dung
                    {"gantry_angle": 90, "couch_angle": 0},     # Ben trai
                    {"gantry_angle": 270, "couch_angle": 0},    # Ben phai
                    {"gantry_angle": 180, "couch_angle": 0},    # Phia sau
                    {"gantry_angle": 45, "couch_angle": 45},    # Cheo trai truoc tren
                    {"gantry_angle": 315, "couch_angle": 45},   # Cheo phai truoc tren
                    {"gantry_angle": 45, "couch_angle": 315},   # Cheo trai truoc duoi
                    {"gantry_angle": 315, "couch_angle": 315},  # Cheo phai truoc duoi
                    {"gantry_angle": 0, "couch_angle": 90}      # Dinh dau
                ]
            else:
                # Chum dong phang
                beam_configs = [
                    {"gantry_angle": 0, "couch_angle": 0},
                    {"gantry_angle": 45, "couch_angle": 0},
                    {"gantry_angle": 90, "couch_angle": 0},
                    {"gantry_angle": 135, "couch_angle": 0},
                    {"gantry_angle": 180, "couch_angle": 0},
                    {"gantry_angle": 225, "couch_angle": 0},
                    {"gantry_angle": 270, "couch_angle": 0},
                    {"gantry_angle": 315, "couch_angle": 0}
                ]
            
            # Tao cac chum tia
            for i, config in enumerate(beam_configs):
                beam_id = f"beam_{i+1}"
                beam = {
                    "id": beam_id,
                    "gantry_angle": config["gantry_angle"],
                    "couch_angle": config["couch_angle"],
                    "collimator_angle": 0,
                    "energy": 6.0,  # MV - Pho to nang luong cao
                    "type": "photon",
                    "technique": "static",
                    "mlc_pattern": "conformal",  # Tao hinh theo khoi u
                    "field_size": [5.0, 5.0]  # cm
                }
                self.add_beam(beam)
        
        elif self.beam_configuration == "dynamic_arcs":
            # Tao cac cung dong (VMAT)
            if self.use_non_coplanar:
                # Cung khong dong phang
                arc_configs = [
                    {"start_angle": 181, "stop_angle": 179, "couch_angle": 0},    # Cung toan bo (cw)
                    {"start_angle": 300, "stop_angle": 60, "couch_angle": 45},    # Cung tren dau (cw)
                    {"start_angle": 181, "stop_angle": 0, "couch_angle": 90},     # Cung ben phai (cw)
                    {"start_angle": 0, "stop_angle": 179, "couch_angle": 270}     # Cung ben trai (ccw)
                ]
            else:
                # Cung dong phang
                arc_configs = [
                    {"start_angle": 181, "stop_angle": 179, "couch_angle": 0},    # Cung hoan chinh (cw)
                    {"start_angle": 179, "stop_angle": 181, "couch_angle": 0}     # Cung hoan chinh (ccw)
                ]
            
            # Tao cac cung
            for i, config in enumerate(arc_configs):
                beam_id = f"arc_{i+1}"
                beam = {
                    "id": beam_id,
                    "gantry_start_angle": config["start_angle"],
                    "gantry_stop_angle": config["stop_angle"],
                    "gantry_angle": config["start_angle"],  # Goc bat dau
                    "couch_angle": config["couch_angle"],
                    "collimator_angle": 45,  # Xoay 45 do de toi uu viec che chan MLC
                    "energy": 6.0,  # MV
                    "type": "photon",
                    "technique": "VMAT",
                    "is_arc": True,
                    "control_points": 72  # So diem dieu khien
                }
                self.add_beam(beam)
                
        elif self.beam_configuration == "hybrid":
            # Ket hop cung va chum tia tinh
            # Tao cung chinh
            main_arc = {
                "id": "arc_1",
                "gantry_start_angle": 181,
                "gantry_stop_angle": 179,
                "gantry_angle": 181,
                "couch_angle": 0,
                "collimator_angle": 45,
                "energy": 6.0,
                "type": "photon",
                "technique": "VMAT",
                "is_arc": True,
                "control_points": 72
            }
            self.add_beam(main_arc)
            
            # Them cac chum tinh co chon loc
            static_beams = [
                {"gantry_angle": 45, "couch_angle": 45},
                {"gantry_angle": 315, "couch_angle": 45},
                {"gantry_angle": 0, "couch_angle": 90}
            ]
            
            for i, config in enumerate(static_beams):
                beam_id = f"beam_{i+1}"
                beam = {
                    "id": beam_id,
                    "gantry_angle": config["gantry_angle"],
                    "couch_angle": config["couch_angle"],
                    "collimator_angle": 0,
                    "energy": 6.0,
                    "type": "photon",
                    "technique": "static",
                    "mlc_pattern": "conformal",
                    "field_size": [4.0, 4.0]  # cm
                }
                self.add_beam(beam)
        
        # Cap nhat thong tin chum tia vao ke hoach
        plan_data["beams"] = {}
        for beam in self.beams:
            plan_data["beams"][beam["id"]] = beam
        
        logger.info(f"Da tao {len(self.beams)} chum/cung cho ke hoach {plan_data['technique']}")
    
    def optimize_beam_angles(self, target_mask: np.ndarray, oar_masks: Dict[str, np.ndarray]) -> List[Dict[str, Any]]:
        """Toi uu hoa goc chum de giam lieu cho co quan nguy cap."""
        if not target_mask.any():
            logger.error("Khong co mat na dich de toi uu hoa goc")
            return []
        
        logger.info("Toi uu hoa goc chum cho SRS/SBRT...")
        
        # Tien hanh toi uu hoa theo cac thuat toan chuyen dung cho SRS/SBRT
        # O day chi mo phong ket qua, thuc te can tich hop thuat toan toi uu
        
        # Tao cau hinh chum toi uu (mau)
        if self.is_srs:
            # Vi du cau hinh SRS
            optimized_beams = [
                {"gantry_angle": 0, "couch_angle": 0, "weight": 1.0},
                {"gantry_angle": 40, "couch_angle": 0, "weight": 0.8},
                {"gantry_angle": 80, "couch_angle": 0, "weight": 0.7},
                {"gantry_angle": 120, "couch_angle": 0, "weight": 0.8},
                {"gantry_angle": 160, "couch_angle": 0, "weight": 0.7},
                {"gantry_angle": 200, "couch_angle": 0, "weight": 0.8},
                {"gantry_angle": 240, "couch_angle": 0, "weight": 0.7},
                {"gantry_angle": 280, "couch_angle": 0, "weight": 0.8},
                {"gantry_angle": 320, "couch_angle": 0, "weight": 0.7}
            ]
            if self.use_non_coplanar:
                # Them cac chum khong dong phang cho SRS
                non_coplanar = [
                    {"gantry_angle": 45, "couch_angle": 45, "weight": 0.6},
                    {"gantry_angle": 315, "couch_angle": 45, "weight": 0.6},
                    {"gantry_angle": 0, "couch_angle": 90, "weight": 0.5}
                ]
                optimized_beams.extend(non_coplanar)
        else:
            # Vi du cau hinh SBRT
            if self.beam_configuration == "dynamic_arcs":
                # Toi uu cung cho SBRT
                optimized_beams = [
                    {
                        "is_arc": True, 
                        "gantry_start_angle": 181, 
                        "gantry_stop_angle": 179, 
                        "couch_angle": 0,
                        "weight": 1.0
                    },
                    {
                        "is_arc": True, 
                        "gantry_start_angle": 179, 
                        "gantry_stop_angle": 181, 
                        "couch_angle": 0,
                        "weight": 0.8
                    }
                ]
                if self.use_non_coplanar:
                    # Them cung khong dong phang
                    optimized_beams.append({
                        "is_arc": True, 
                        "gantry_start_angle": 220, 
                        "gantry_stop_angle": 140, 
                        "couch_angle": 30,
                        "weight": 0.7
                    })
            else:
                # Cau hinh tinh cho SBRT
                optimized_beams = [
                    {"gantry_angle": 0, "couch_angle": 0, "weight": 1.0},
                    {"gantry_angle": 72, "couch_angle": 0, "weight": 0.8},
                    {"gantry_angle": 144, "couch_angle": 0, "weight": 0.8},
                    {"gantry_angle": 216, "couch_angle": 0, "weight": 0.8},
                    {"gantry_angle": 288, "couch_angle": 0, "weight": 0.8}
                ]
                if self.use_non_coplanar:
                    # Them chum khong dong phang
                    optimized_beams.append(
                        {"gantry_angle": 30, "couch_angle": 30, "weight": 0.6}
                    )
        
        return optimized_beams
    
    def set_srs_mode(self, is_srs: bool = True):
        """Cai dat che do SRS (True) hoac SBRT (False)."""
        self.is_srs = is_srs
        mode_name = "SRS" if is_srs else "SBRT"
        logger.info(f"Da chuyen sang che do {mode_name}")
        
        # Cap nhat cac tham so mac dinh theo che do
        if is_srs:
            # Cac gia tri mac dinh cho SRS
            self.margin_mm = 1.0
            self.max_dose_per_fraction = 24.0
        else:
            # Cac gia tri mac dinh cho SBRT
            self.margin_mm = 3.0
            self.max_dose_per_fraction = 18.0
    
    def set_beam_configuration(self, config_type: str):
        """Cai dat loai cau hinh chum tia: static, dynamic_arcs, hybrid."""
        valid_configs = ["static", "dynamic_arcs", "hybrid"]
        if config_type in valid_configs:
            self.beam_configuration = config_type
            logger.info(f"Da cai dat cau hinh chum tia: {config_type}")
        else:
            logger.warning(f"Cau hinh khong hop le. Su dung mot trong: {valid_configs}")
    
    def set_non_coplanar(self, use_non_coplanar: bool):
        """Cai dat che do su dung chum khong dong phang."""
        self.use_non_coplanar = use_non_coplanar
        status = "Su dung" if use_non_coplanar else "Khong su dung"
        logger.info(f"{status} chum khong dong phang")
    
    def set_multiple_isocenters(self, use_multiple: bool):
        """Cai dat che do su dung nhieu tam."""
        self.use_multiple_isocenters = use_multiple
        status = "Su dung" if use_multiple else "Khong su dung"
        logger.info(f"{status} nhieu tam")
    
    def add_isocenter(self, position: List[float]):
        """Them vi tri tam moi cho ke hoach nhieu tam."""
        if not self.use_multiple_isocenters:
            logger.warning("Che do nhieu tam chua duoc kich hoat")
        
        self.isocenters.append(position)
        logger.info(f"Da them tam tai vi tri {position}")
    
    def calculate_conformal_margins(self, ptv_mask: np.ndarray, 
                                  oar_masks: Dict[str, np.ndarray]) -> Dict[str, float]:
        """Tinh toan le bao quanh cho PTV dua tren cac co quan lan can."""
        margins = {"default": self.margin_mm}
        
        # O day se tinh toan le dua tren vi tri co quan nguy cap
        # Thuong se giam le o noi gan co quan nhay cam
        # Chi mo phong ket qua
        
        if self.is_srs:
            # Vi du: Giam le gan cac co quan nhay cam trong SRS
            for organ_name, mask in oar_masks.items():
                if "brainstem" in organ_name.lower():
                    margins["brainstem_side"] = 0.5  # Giam xuong 0.5mm
                elif "optic" in organ_name.lower():
                    margins["optic_side"] = 0.8  # Giam xuong 0.8mm
                elif "chiasm" in organ_name.lower():
                    margins["chiasm_side"] = 0.5  # Giam xuong 0.5mm
        else:
            # Vi du: Tinh toan le cho SBRT
            for organ_name, mask in oar_masks.items():
                if "cord" in organ_name.lower():
                    margins["spinal_cord_side"] = 1.5  # 1.5mm gan tuy song
                elif "heart" in organ_name.lower():
                    margins["heart_side"] = 2.0  # 2mm gan tim
        
        logger.info(f"Da tinh toan le theo chuc nang: {margins}")
        return margins
    
    def set_margin(self, margin_mm: float):
        """Cai dat le mac dinh (mm)."""
        self.margin_mm = margin_mm
        logger.info(f"Da cai dat le mac dinh: {margin_mm}mm")
    
    def set_arc_parameters(self, arc_spacing_deg: float = None, arc_length_deg: float = None):
        """Cai dat tham so cung cho ke hoach dung cung."""
        if arc_spacing_deg is not None:
            self.arc_spacing_deg = arc_spacing_deg
            logger.info(f"Da cai dat khoang cach cung: {arc_spacing_deg} do")
            
        if arc_length_deg is not None:
            self.arc_length_deg = arc_length_deg
            logger.info(f"Da cai dat chieu dai cung: {arc_length_deg} do")
    
    def configure_high_dose_constraints(self, targets: List[str], 
                                      max_dose_percent: float = 130.0) -> Dict[str, Dict]:
        """Tao rang buoc lieu cao cho ke hoach SRS/SBRT."""
        constraints = {}
        
        # Tao rang buoc mac dinh
        for target in targets:
            constraints[target] = {
                "min_dose": 100.0,  # Lieu toi thieu la 100% lieu ke toa
                "coverage": 95.0,   # Bao phu it nhat 95% the tich
                "max_dose": max_dose_percent,  # Lieu toi da (% cua lieu ke toa)
                "priority": 100     # Uu tien cao
            }
        
        # Rang buoc dac biet cho SRS/SBRT
        if self.is_srs:
            # SRS can giam lieu cho co quan nguy cap nao
            constraints["brainstem"] = {
                "max_dose": 12.0,   # Gy
                "priority": 90
            }
            constraints["optic_chiasm"] = {
                "max_dose": 8.0,    # Gy
                "priority": 90
            }
            constraints["optic_nerve"] = {
                "max_dose": 8.0,    # Gy
                "priority": 90
            }
        else:
            # SBRT co the can rang buoc cho nhieu co quan khac
            # Vi du: rang buoc cho SBRT phoi
            constraints["spinal_cord"] = {
                "max_dose": 30.0,   # Gy
                "priority": 90
            }
            constraints["heart"] = {
                "mean_dose": 20.0,  # Gy
                "priority": 80
            }
            constraints["normal_lung"] = {
                "V20Gy": 20.0,      # 20% the tich nhan <20Gy
                "priority": 80
            }
        
        logger.info(f"Da tao {len(constraints)} rang buoc cho ke hoach {self.name}")
        return constraints
    
    def to_dict(self) -> Dict[str, Any]:
        """Chuyen doi thanh tu dien de luu tru."""
        data = super().to_dict()
        data.update({
            "technique_type": "StereotacticRT",
            "is_srs": self.is_srs,
            "use_couch_rotation": self.use_couch_rotation,
            "max_dose_per_fraction": self.max_dose_per_fraction,
            "high_resolution": self.high_resolution,
            "use_non_coplanar": self.use_non_coplanar,
            "margin_mm": self.margin_mm,
            "use_multiple_isocenters": self.use_multiple_isocenters,
            "isocenters": self.isocenters,
            "beam_configuration": self.beam_configuration,
            "arc_spacing_deg": self.arc_spacing_deg,
            "arc_length_deg": self.arc_length_deg
        })
        return data
    
    def from_dict(self, data: Dict[str, Any]):
        """Khoi phuc tu du lieu da luu."""
        super().from_dict(data)
        self.is_srs = data.get("is_srs", True)
        self.use_couch_rotation = data.get("use_couch_rotation", True)
        self.max_dose_per_fraction = data.get("max_dose_per_fraction", 24.0)
        self.high_resolution = data.get("high_resolution", True)
        self.use_non_coplanar = data.get("use_non_coplanar", True)
        self.margin_mm = data.get("margin_mm", 1.0)
        self.use_multiple_isocenters = data.get("use_multiple_isocenters", False)
        self.isocenters = data.get("isocenters", [])
        self.beam_configuration = data.get("beam_configuration", "dynamic_arcs")
        self.arc_spacing_deg = data.get("arc_spacing_deg", 45.0)
        self.arc_length_deg = data.get("arc_length_deg", 120.0)
        
        logger.info(f"Da khoi phuc ky thuat {self.name} - {'SRS' if self.is_srs else 'SBRT'}") 