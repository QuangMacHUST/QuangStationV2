#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module ky thuat xa tri proton cho QuangStation V2.
Ho tro ca PBS (Pencil Beam Scanning) va PSPT (Passive Scattering Proton Therapy).
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import os

from quangstation.clinical.planning.techniques.base import RTTechnique
from quangstation.core.utils.logging import get_logger

logger = get_logger(__name__)

class ProtonTherapy(RTTechnique):
    """
    Lop ky thuat xa tri proton, ho tro ca PBS va PSPT.
    """
    
    # Cac loai xa tri proton
    PBS = "PBS"  # Pencil Beam Scanning
    PSPT = "PSPT"  # Passive Scattering Proton Therapy
    
    def __init__(self):
        """Khoi tao ky thuat xa tri proton."""
        super().__init__()
        self.name = "Proton Therapy"
        self.proton_type = self.PBS  # Mac dinh la PBS
        self.energy_range = (70, 230)  # Tam nang luong (MeV)
        self.use_range_modulator = True  # Su dung bo dieu bien tam
        self.use_range_shifter = False  # Su dung bo dich chuyen tam
        self.range_shifter_thickness = 0.0  # Do day bo dich chuyen tam (mm)
        self.spot_size = 5.0  # Kich thuoc diem (mm) cho PBS
        self.scanning_pattern = "continuous"  # "continuous" hoac "discrete"
        self.use_robust_optimization = True  # Su dung toi uu hoa ben vung
        self.robustness_parameters = {
            "setup_uncertainty": 3.0,  # mm
            "range_uncertainty": 3.5   # %
        }
        self.beams = []
        self.num_spots = 1000  # So diem cho PBS
        self.distal_margin = 3.0  # Le xa (mm)
        self.use_aperture = True  # Chi danh cho PSPT (khe mo)
        self.use_compensator = True  # Chi danh cho PSPT (bo bu)
        self.aperture_margin = 5.0  # Le khe mo (mm) cho PSPT
        self.compensator_smearing = 3.0  # Do lam mo bo bu (mm) cho PSPT
    
    def create_plan(self, structures: Dict[str, np.ndarray]) -> Dict:
        """Tao ke hoach xa tri proton co ban."""
        plan_data = super().create_plan(structures)
        
        # Cap nhat thong tin ky thuat cho ke hoach
        plan_data.update({
            "technique": "ProtonTherapy",
            "technique_subtype": self.proton_type,
            "fractions": 30,  # Mac dinh la 30 lan
            "energy_range": self.energy_range,
            "use_robust_optimization": self.use_robust_optimization,
            "robustness_parameters": self.robustness_parameters
        })
        
        # Thong tin rieng cho PBS hoac PSPT
        if self.proton_type == self.PBS:
            plan_data.update({
                "spot_size": self.spot_size,
                "scanning_pattern": self.scanning_pattern,
                "num_spots": self.num_spots
            })
        else:  # PSPT
            plan_data.update({
                "use_aperture": self.use_aperture,
                "use_compensator": self.use_compensator,
                "aperture_margin": self.aperture_margin,
                "compensator_smearing": self.compensator_smearing
            })
        
        # Cap nhat lieu ke toa mac dinh
        plan_data["prescribed_dose"] = 60.0  # Gy(RBE)
        plan_data["dose_per_fraction"] = 2.0  # Gy(RBE)
        
        # Tao cac chum tia mac dinh
        self._create_default_beams(plan_data)
        
        return plan_data
    
    def _create_default_beams(self, plan_data: Dict[str, Any]):
        """Tao cac chum proton mac dinh."""
        self.beams = []
        
        # Goc chum mac dinh cho xa tri proton (thuong co it chum hon xa tri photon)
        beam_angles = [0, 90, 180, 270]  # Vi du: 4 chum co ban
        field_ids = ["anterior", "right", "posterior", "left"]
        
        # Tao chum tia
        for i, (angle, field_id) in enumerate(zip(beam_angles, field_ids)):
            beam_id = f"beam_{i+1}"
            
            # Cau hinh chung
            beam = {
                "id": beam_id,
                "name": field_id,
                "gantry_angle": angle,
                "couch_angle": 0,
                "energy": self.energy_range[0],  # Nang luong khoi dau
                "type": "proton",
                "technique": self.proton_type,
                "distal_margin": self.distal_margin,  # mm
                "use_range_shifter": self.use_range_shifter,
                "range_shifter_thickness": self.range_shifter_thickness
            }
            
            # Thong tin rieng cho PBS/PSPT
            if self.proton_type == self.PBS:
                beam.update({
                    "spot_size": self.spot_size,
                    "scanning_pattern": self.scanning_pattern,
                    "energy_layers": self._create_energy_layers(),
                    "spot_map": {}  # Se duoc dien trong qua trinh toi uu
                })
            else:  # PSPT
                beam.update({
                    "use_aperture": self.use_aperture,
                    "aperture_margin": self.aperture_margin,
                    "use_compensator": self.use_compensator,
                    "compensator_smearing": self.compensator_smearing,
                    "range_modulator": self._create_range_modulator() if self.use_range_modulator else None
                })
            
            self.add_beam(beam)
        
        # Cap nhat thong tin chum tia vao ke hoach
        plan_data["beams"] = {}
        for beam in self.beams:
            plan_data["beams"][beam["id"]] = beam
        
        logger.info(f"Da tao {len(self.beams)} chum proton cho ke hoach {plan_data['technique']}")
    
    def _create_energy_layers(self) -> List[Dict[str, Any]]:
        """Tao cac lop nang luong cho PBS."""
        # Trong thuc te, cac lop nang luong se duoc tinh toan dua tren
        # pham vi ngan chan cua dich
        
        # Tao mau cac lop nang luong
        min_energy, max_energy = self.energy_range
        num_layers = 10  # So lop nang luong
        
        energy_step = (max_energy - min_energy) / (num_layers - 1)
        
        layers = []
        for i in range(num_layers):
            energy = min_energy + i * energy_step
            layer = {
                "energy": energy,  # MeV
                "spots": [],       # Danh sach diem
                "weight": 1.0      # Trong so mac dinh
            }
            layers.append(layer)
        
        return layers
    
    def _create_range_modulator(self) -> Dict[str, Any]:
        """Tao thong tin bo dieu bien tam cho PSPT."""
        # Mo phong thong so bo dieu bien
        modulator = {
            "type": "wheel",  # "wheel" hoac "ridge_filter"
            "steps": 10,
            "modulation_width": 50.0,  # mm
            "min_range": 50.0,  # mm
            "max_range": 100.0   # mm
        }
        return modulator
    
    def set_proton_type(self, proton_type: str):
        """Cai dat loai xa tri proton (PBS hoac PSPT)."""
        if proton_type in [self.PBS, self.PSPT]:
            self.proton_type = proton_type
            logger.info(f"Da cai dat che do xa tri proton: {proton_type}")
        else:
            logger.warning(f"Loai xa tri proton khong hop le. Su dung PBS hoac PSPT")
    
    def set_energy_range(self, min_energy: float, max_energy: float):
        """Cai dat pham vi nang luong proton (MeV)."""
        if 70 <= min_energy <= max_energy <= 250:
            self.energy_range = (min_energy, max_energy)
            logger.info(f"Da cai dat pham vi nang luong proton: {min_energy}-{max_energy} MeV")
        else:
            logger.warning("Pham vi nang luong khong hop le. Gioi han: 70-250 MeV")
    
    def set_spot_parameters(self, spot_size: float = None, num_spots: int = None, pattern: str = None):
        """Cai dat tham so diem (chi cho PBS)."""
        if self.proton_type != self.PBS:
            logger.warning("Tham so diem chi ap dung cho PBS")
            return
        
        if spot_size is not None:
            self.spot_size = spot_size
            logger.info(f"Da cai dat kich thuoc diem: {spot_size} mm")
        
        if num_spots is not None:
            self.num_spots = num_spots
            logger.info(f"Da cai dat so diem: {num_spots}")
        
        if pattern is not None and pattern in ["continuous", "discrete"]:
            self.scanning_pattern = pattern
            logger.info(f"Da cai dat kieu quet: {pattern}")
    
    def set_passive_scattering_parameters(self, use_aperture: bool = None, aperture_margin: float = None,
                                       use_compensator: bool = None, compensator_smearing: float = None):
        """Cai dat tham so cho xa tri proton thu dong (PSPT)."""
        if self.proton_type != self.PSPT:
            logger.warning("Cac tham so nay chi ap dung cho PSPT")
            return
        
        if use_aperture is not None:
            self.use_aperture = use_aperture
            logger.info(f"{'Su dung' if use_aperture else 'Khong su dung'} khe mo")
        
        if aperture_margin is not None:
            self.aperture_margin = aperture_margin
            logger.info(f"Da cai dat le khe mo: {aperture_margin} mm")
        
        if use_compensator is not None:
            self.use_compensator = use_compensator
            logger.info(f"{'Su dung' if use_compensator else 'Khong su dung'} bo bu")
        
        if compensator_smearing is not None:
            self.compensator_smearing = compensator_smearing
            logger.info(f"Da cai dat do lam mo bo bu: {compensator_smearing} mm")
    
    def set_robust_optimization(self, use_robust: bool, setup_uncertainty: float = None, 
                             range_uncertainty: float = None):
        """Cai dat tham so toi uu hoa ben vung."""
        self.use_robust_optimization = use_robust
        
        if setup_uncertainty is not None:
            self.robustness_parameters["setup_uncertainty"] = setup_uncertainty
        
        if range_uncertainty is not None:
            self.robustness_parameters["range_uncertainty"] = range_uncertainty
        
        logger.info(f"{'Bat' if use_robust else 'Tat'} che do toi uu hoa ben vung")
        if use_robust:
            logger.info(f"Tham so ben vung: Sai so thiet lap={self.robustness_parameters['setup_uncertainty']}mm, " 
                      f"Sai so tam={self.robustness_parameters['range_uncertainty']}%")
    
    def calculate_range_in_water(self, energy: float) -> float:
        """Tinh pham vi proton trong nuoc dua tren nang luong (MeV)."""
        # Cong thuc tinh pham vi proton trong nuoc
        # R = 0.0022 * E^1.77 (xap xi)
        range_cm = 0.0022 * (energy ** 1.77)
        range_mm = range_cm * 10
        return range_mm
    
    def create_spot_map(self, target_mask: np.ndarray, spacing_mm: float = 5.0) -> Dict[str, List]:
        """Tao ban do diem cho PBS dua tren hinh dang muc tieu."""
        if self.proton_type != self.PBS:
            logger.warning("Ban do diem chi ap dung cho PBS")
            return {}
        
        # Trong thuc te, ban do diem nen duoc tao dua tren thuat toan toi uu
        # Va phu thuoc vao hinh dang 3D cua muc tieu
        # Day chi la mo phong don gian
        
        logger.info(f"Tao ban do diem voi khoang cach {spacing_mm}mm")
        
        # Mo phong: Mau ban do diem
        spot_map = {
            "energy_indices": [],  # Chi so lop nang luong
            "positions_x": [],     # Vi tri x (mm)
            "positions_y": [],     # Vi tri y (mm)
            "weights": []          # Trong so
        }
        
        # Tao ngau nhien cac diem (chi vi du)
        num_energy_layers = len(self._create_energy_layers())
        np.random.seed(42)  # Cho ket qua kha thi
        
        for _ in range(self.num_spots):
            # Phan bo diem deu qua cac lop nang luong
            energy_idx = np.random.randint(0, num_energy_layers)
            spot_map["energy_indices"].append(energy_idx)
            
            # Vi tri ngau nhien trong muc tieu
            spot_map["positions_x"].append((np.random.rand() - 0.5) * 100)  # -50 to 50mm
            spot_map["positions_y"].append((np.random.rand() - 0.5) * 100)  # -50 to 50mm
            
            # Trong so mac dinh
            spot_map["weights"].append(1.0)
        
        return spot_map
    
    def create_aperture(self, target_mask: np.ndarray) -> Dict[str, Any]:
        """Tao khe mo cho PSPT dua tren muc tieu."""
        if self.proton_type != self.PSPT or not self.use_aperture:
            logger.warning("Khe mo chi ap dung cho PSPT")
            return {}
        
        # Trong thuc te, khe mo se duoc tao dua tren tia chieu (beam's eye view)
        # cua muc tieu, cong them le.
        
        # Tao mau
        aperture = {
            "shape": "custom",  # "custom", "circular", "rectangular"
            "margin": self.aperture_margin,  # mm
            "material": "brass",
            "thickness": 60.0,  # mm
            "contour_points": []  # Se duoc dien boi thuat toan tao khe mo thuc te
        }
        
        logger.info(f"Da tao khe mo cho PSPT voi le {self.aperture_margin}mm")
        return aperture
    
    def create_compensator(self, target_mask: np.ndarray, 
                         oar_masks: Dict[str, np.ndarray]) -> Dict[str, Any]:
        """Tao bo bu cho PSPT dua tren muc tieu va co quan nguy cap."""
        if self.proton_type != self.PSPT or not self.use_compensator:
            logger.warning("Bo bu chi ap dung cho PSPT")
            return {}
        
        # Trong thuc te, bo bu se duoc tao dua tren hinh dang distal cua
        # muc tieu va vi tri co quan nguy cap
        
        # Tao mau
        compensator = {
            "material": "acrylic",
            "maximum_thickness": 100.0,  # mm
            "minimum_thickness": 5.0,    # mm
            "smearing": self.compensator_smearing,  # mm
            "grid_resolution": 2.5,      # mm
            "thickness_map": []          # Se duoc dien boi thuat toan tao bo bu thuc te
        }
        
        logger.info(f"Da tao bo bu cho PSPT voi do lam mo {self.compensator_smearing}mm")
        return compensator
    
    def estimate_rbe(self, dose_physical: np.ndarray) -> np.ndarray:
        """Uoc tinh RBE (Relative Biological Effectiveness) cho lieu proton."""
        # Trong thuc te, RBE se thay doi theo vi tri, LET, va cac tham so sinh hoc khac
        # Nhung mac dinh thuong su dung RBE = 1.1 cho lieu proton
        
        rbe = 1.1
        dose_rbe = dose_physical * rbe
        
        logger.info(f"Da uoc tinh lieu RBE voi he so RBE = {rbe}")
        return dose_rbe
    
    def calculate_let(self, energy_layers: List[Dict], 
                    spot_weights: np.ndarray) -> np.ndarray:
        """Tinh toan LET (Linear Energy Transfer) cho lieu proton."""
        # LET la do mat nang luong tuyen tinh, mot thong so quan trong trong
        # danh gia hieu qua sinh hoc cua xa tri proton
        
        # Day chi la mo phong, trong thuc te can cac thuat toan phuc tap hon
        
        # Gia lap ma tran LET (mA·g/cm²)
        let_matrix = np.zeros_like(spot_weights)
        
        # LET se cao hon o cuoi tam proton (Bragg peak)
        # Va thap hon o dau vao
        
        # Trong thuc te, LET duoc tinh bang cac mo hinh vat ly chi tiet
        logger.info("Da tinh toan ma tran LET (mo phong)")
        return let_matrix
    
    def optimize_beam_angles_for_oar_sparing(self, target_mask: np.ndarray, 
                                           oar_masks: Dict[str, np.ndarray]) -> List[Dict]:
        """Toi uu hoa cac goc chum de toi thieu lieu tren co quan nguy cap."""
        logger.info("Toi uu hoa goc chum proton de bao ve co quan nguy cap")
        
        # Chi tao mau cac chum da toi uu
        optimized_configs = [
            {"gantry_angle": 0, "couch_angle": 0, "weight": 1.0},
            {"gantry_angle": 150, "couch_angle": 0, "weight": 0.8},
            {"gantry_angle": 210, "couch_angle": 0, "weight": 0.8}
        ]
        
        return optimized_configs
    
    def get_recommended_fractionation(self, indication: str, 
                                    total_dose: float = None) -> Dict[str, float]:
        """Lay thong tin phan lieu theo chi dinh."""
        fractionation_schemes = {
            "prostate": {
                "total_dose": 70.0,  # Gy(RBE)
                "fractions": 28,
                "dose_per_fraction": 2.5  # Gy(RBE)
            },
            "lung_sbrt": {
                "total_dose": 50.0,  # Gy(RBE)
                "fractions": 5,
                "dose_per_fraction": 10.0  # Gy(RBE)
            },
            "head_neck": {
                "total_dose": 70.0,  # Gy(RBE)
                "fractions": 35,
                "dose_per_fraction": 2.0  # Gy(RBE)
            },
            "brain": {
                "total_dose": 54.0,  # Gy(RBE)
                "fractions": 30,
                "dose_per_fraction": 1.8  # Gy(RBE)
            },
            "pediatric": {
                "total_dose": 36.0,  # Gy(RBE)
                "fractions": 20,
                "dose_per_fraction": 1.8  # Gy(RBE)
            }
        }
        
        # Neu khong co chi dinh cu the, tra ve mac dinh
        if indication not in fractionation_schemes:
            logger.warning(f"Khong co chi dinh {indication}, su dung mac dinh")
            result = {
                "total_dose": 60.0,
                "fractions": 30,
                "dose_per_fraction": 2.0
            }
        else:
            result = fractionation_schemes[indication]
        
        # Neu co tong lieu duoc chi dinh, dieu chinh so frac hoac lieu moi frac
        if total_dose is not None:
            result["total_dose"] = total_dose
            # Giu nguyen lieu moi frac, dieu chinh so frac
            result["fractions"] = round(total_dose / result["dose_per_fraction"])
            # Dieu chinh lai lieu moi frac de dam bao tong lieu chinh xac
            result["dose_per_fraction"] = total_dose / result["fractions"]
        
        logger.info(f"De xuat phan lieu cho {indication}: {result['total_dose']}Gy " +
                  f"trong {result['fractions']} lan, {result['dose_per_fraction']}Gy/lan")
        
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """Chuyen doi thanh tu dien de luu tru."""
        data = super().to_dict()
        data.update({
            "technique_type": "ProtonTherapy",
            "proton_type": self.proton_type,
            "energy_range": self.energy_range,
            "use_range_modulator": self.use_range_modulator,
            "use_range_shifter": self.use_range_shifter,
            "range_shifter_thickness": self.range_shifter_thickness,
            "spot_size": self.spot_size,
            "scanning_pattern": self.scanning_pattern,
            "use_robust_optimization": self.use_robust_optimization,
            "robustness_parameters": self.robustness_parameters,
            "num_spots": self.num_spots,
            "distal_margin": self.distal_margin,
            "use_aperture": self.use_aperture,
            "use_compensator": self.use_compensator,
            "aperture_margin": self.aperture_margin,
            "compensator_smearing": self.compensator_smearing
        })
        return data
    
    def from_dict(self, data: Dict[str, Any]):
        """Khoi phuc tu du lieu da luu."""
        super().from_dict(data)
        self.proton_type = data.get("proton_type", self.PBS)
        self.energy_range = data.get("energy_range", (70, 230))
        self.use_range_modulator = data.get("use_range_modulator", True)
        self.use_range_shifter = data.get("use_range_shifter", False)
        self.range_shifter_thickness = data.get("range_shifter_thickness", 0.0)
        self.spot_size = data.get("spot_size", 5.0)
        self.scanning_pattern = data.get("scanning_pattern", "continuous")
        self.use_robust_optimization = data.get("use_robust_optimization", True)
        self.robustness_parameters = data.get("robustness_parameters", self.robustness_parameters)
        self.num_spots = data.get("num_spots", 1000)
        self.distal_margin = data.get("distal_margin", 3.0)
        self.use_aperture = data.get("use_aperture", True)
        self.use_compensator = data.get("use_compensator", True)
        self.aperture_margin = data.get("aperture_margin", 5.0)
        self.compensator_smearing = data.get("compensator_smearing", 3.0)
        
        logger.info(f"Da khoi phuc ky thuat {self.name} - {self.proton_type}") 