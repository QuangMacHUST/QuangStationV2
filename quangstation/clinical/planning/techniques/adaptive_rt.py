#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module ky thuat xa tri thich ung (Adaptive RT) cho QuangStation V2.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import os
import datetime

from quangstation.clinical.planning.techniques.base import RTTechnique
from quangstation.core.utils.logging import get_logger

logger = get_logger(__name__)

class AdaptiveRT(RTTechnique):
    """
    Lop ky thuat xa tri thich ung (Adaptive RT) - cho phep dieu chinh ke hoach
    dua tren thay doi hinh thai cua benh nhan trong qua trinh dieu tri.
    """
    
    def __init__(self):
        """Khoi tao ky thuat xa tri thich ung."""
        super().__init__()
        self.name = "Adaptive RT"
        self.reference_plan = None
        self.monitoring_sessions = []
        self.session_structures = {}
        self.session_doses = {}
        self.adaptation_thresholds = {
            "volume_change_percent": 10.0,  # Thay doi the tich > 10%
            "weight_change_kg": 3.0,        # Thay doi can nang > 3kg
            "setup_error_mm": 5.0,          # Loi thiet lap > 5mm
            "dose_deviation_percent": 5.0   # Chenh lech lieu > 5%
        }
        self.deformable_registration = True  # Su dung dang ky bien dang
        self.accumulated_dose = None
        self.beams = []
        self.adaptation_history = []
    
    def create_plan(self, structures: Dict[str, np.ndarray]) -> Dict:
        """Tao ke hoach xa tri thich ung co ban."""
        plan_data = super().create_plan(structures)
        plan_data.update({
            "technique": "AdaptiveRT",
            "reference_date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "monitoring_schedule": "weekly",
            "adaptation_criteria": self.adaptation_thresholds,
            "deformable_registration": self.deformable_registration
        })
        
        # Them cac chum tia mac dinh (co the thay doi theo benh nhan)
        beam_angles = [0, 72, 144, 216, 288]
        for i, angle in enumerate(beam_angles):
            beam_id = f"beam_{i+1}"
            self.add_beam({
                "id": beam_id,
                "gantry_angle": angle,
                "energy": 6.0,
                "type": "photon",
                "technique": "IMRT",
                "segments": 10  # So doan MLC cho moi chum
            })
        
        return plan_data
    
    def set_reference_plan(self, plan_data: Dict[str, Any]):
        """Cai dat ke hoach tham chieu ban dau."""
        self.reference_plan = plan_data
        logger.info(f"Da cai dat ke hoach tham chieu: {plan_data.get('plan_id', 'Unknown')}")
    
    def add_monitoring_session(self, session_data: Dict[str, Any]):
        """Them phien giam sat/danh gia."""
        session_id = len(self.monitoring_sessions) + 1
        session = {
            "session_id": session_id,
            "date": session_data.get("date", datetime.datetime.now().strftime("%Y-%m-%d")),
            "image_dataset": session_data.get("image_dataset"),
            "structures": session_data.get("structures", {}),
            "setup_errors": session_data.get("setup_errors", {"x": 0.0, "y": 0.0, "z": 0.0}),
            "weight": session_data.get("weight", 0.0),
            "requires_adaptation": False,
            "adaptation_reasons": []
        }
        
        self.monitoring_sessions.append(session)
        
        # Luu cau truc cua phien
        if "structures" in session_data:
            self.session_structures[session_id] = session_data["structures"]
        
        logger.info(f"Da them phien giam sat #{session_id} - {session['date']}")
        return session_id
    
    def evaluate_adaptation_need(self, session_id: int) -> Dict[str, Any]:
        """Danh gia xem co can thich ung ke hoach khong."""
        if session_id > len(self.monitoring_sessions):
            logger.error(f"Phien #{session_id} khong ton tai")
            return {"requires_adaptation": False, "reasons": ["Phien khong ton tai"]}
        
        session = self.monitoring_sessions[session_id - 1]
        requires_adaptation = False
        reasons = []
        
        # Kiem tra thay doi cau truc (neu co)
        if session_id in self.session_structures and self.reference_plan:
            ref_structures = self.reference_plan.get("structures", {})
            new_structures = self.session_structures[session_id]
            
            for struct_name, struct_mask in new_structures.items():
                if struct_name in ref_structures:
                    # Tinh thay doi the tich
                    ref_volume = np.sum(ref_structures[struct_name])
                    new_volume = np.sum(struct_mask)
                    if ref_volume > 0:
                        volume_change_percent = abs(new_volume - ref_volume) / ref_volume * 100
                        if volume_change_percent > self.adaptation_thresholds["volume_change_percent"]:
                            requires_adaptation = True
                            reasons.append(f"The tich cua {struct_name} thay doi {volume_change_percent:.1f}%")
        
        # Kiem tra loi thiet lap
        setup_errors = session.get("setup_errors", {"x": 0.0, "y": 0.0, "z": 0.0})
        max_error = max(abs(setup_errors["x"]), abs(setup_errors["y"]), abs(setup_errors["z"]))
        if max_error > self.adaptation_thresholds["setup_error_mm"]:
            requires_adaptation = True
            reasons.append(f"Loi thiet lap ({max_error:.1f}mm) vuot qua nguong")
        
        # Kiem tra thay doi can nang
        if "weight" in session and self.reference_plan and "weight" in self.reference_plan:
            weight_change = abs(session["weight"] - self.reference_plan["weight"])
            if weight_change > self.adaptation_thresholds["weight_change_kg"]:
                requires_adaptation = True
                reasons.append(f"Can nang thay doi {weight_change:.1f}kg")
        
        # Cap nhat ket qua
        session["requires_adaptation"] = requires_adaptation
        session["adaptation_reasons"] = reasons
        
        result = {
            "requires_adaptation": requires_adaptation,
            "reasons": reasons,
            "session_id": session_id,
            "date": session["date"]
        }
        
        logger.info(f"Danh gia thich ung cho phien #{session_id}: " + 
                    ("Can thich ung" if requires_adaptation else "Khong can thich ung"))
        
        return result
    
    def generate_adapted_plan(self, session_id: int) -> Dict[str, Any]:
        """Tao ke hoach thich ung tu phien giam sat."""
        if session_id > len(self.monitoring_sessions):
            logger.error(f"Phien #{session_id} khong ton tai")
            return None
        
        session = self.monitoring_sessions[session_id - 1]
        if not session["requires_adaptation"]:
            logger.warning(f"Phien #{session_id} khong yeu cau thich ung, nhung van tao ke hoach")
        
        # Lay cau truc moi tu phien giam sat
        new_structures = self.session_structures.get(session_id, {})
        if not new_structures:
            logger.error("Khong co cau truc moi cho ke hoach thich ung")
            return None
        
        # Tao ke hoach moi dua tren ke hoach tham chieu
        adapted_plan = self.create_plan(new_structures)
        adapted_plan.update({
            "plan_id": f"{self.reference_plan.get('plan_id', 'Plan')}_Adapt{session_id}",
            "technique": "AdaptiveRT",
            "adaptation_date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "reference_plan_id": self.reference_plan.get("plan_id"),
            "adaptation_reasons": session["adaptation_reasons"],
            "session_id": session_id
        })
        
        # Luu lich su thich ung
        adaptation_record = {
            "date": adapted_plan["adaptation_date"],
            "session_id": session_id,
            "reasons": session["adaptation_reasons"],
            "plan_id": adapted_plan["plan_id"]
        }
        self.adaptation_history.append(adaptation_record)
        
        logger.info(f"Da tao ke hoach thich ung: {adapted_plan['plan_id']}")
        return adapted_plan
    
    def calculate_accumulated_dose(self, dose_matrices: List[np.ndarray], 
                                 weights: Optional[List[float]] = None) -> np.ndarray:
        """Tinh toan lieu tich luy tu nhieu ma tran lieu."""
        if not dose_matrices:
            logger.error("Khong co ma tran lieu de tich luy")
            return None
        
        # Neu khong co trong so, gan deu
        if weights is None:
            weights = [1.0 / len(dose_matrices)] * len(dose_matrices)
        
        # Dam bao tong trong so = 1
        total_weight = sum(weights)
        if abs(total_weight - 1.0) > 1e-6:
            weights = [w / total_weight for w in weights]
        
        # Kiem tra so luong ma tran lieu va trong so
        if len(dose_matrices) != len(weights):
            logger.error("So luong ma tran lieu va trong so khong khop")
            return None
        
        # Tinh lieu tich luy
        accumulated = np.zeros_like(dose_matrices[0])
        for dose, weight in zip(dose_matrices, weights):
            accumulated += dose * weight
        
        self.accumulated_dose = accumulated
        logger.info(f"Da tinh toan lieu tich luy tu {len(dose_matrices)} ma tran lieu")
        
        return accumulated
    
    def set_adaptation_thresholds(self, thresholds: Dict[str, float]):
        """Cap nhat cac nguong thich ung."""
        for key, value in thresholds.items():
            if key in self.adaptation_thresholds:
                self.adaptation_thresholds[key] = value
        
        logger.info(f"Da cap nhat nguong thich ung: {self.adaptation_thresholds}")
    
    def get_adaptation_history(self) -> List[Dict[str, Any]]:
        """Lay lich su thich ung."""
        return self.adaptation_history
    
    def set_monitoring_schedule(self, schedule: str):
        """Cai dat lich trinh giam sat (hang ngay, hang tuan, ...)."""
        valid_schedules = ["daily", "weekly", "biweekly", "monthly", "custom"]
        if schedule in valid_schedules:
            self.monitoring_schedule = schedule
            logger.info(f"Da cai dat lich trinh giam sat: {schedule}")
        else:
            logger.warning(f"Lich trinh khong hop le. Su dung mot trong: {valid_schedules}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Chuyen doi thanh tu dien de luu tru."""
        data = super().to_dict()
        data.update({
            "technique_type": "AdaptiveRT",
            "reference_plan": self.reference_plan,
            "monitoring_sessions": self.monitoring_sessions,
            "adaptation_thresholds": self.adaptation_thresholds,
            "deformable_registration": self.deformable_registration,
            "adaptation_history": self.adaptation_history,
            "monitoring_schedule": getattr(self, "monitoring_schedule", "weekly")
        })
        return data
    
    def from_dict(self, data: Dict[str, Any]):
        """Khoi phuc tu du lieu da luu."""
        super().from_dict(data)
        self.reference_plan = data.get("reference_plan")
        self.monitoring_sessions = data.get("monitoring_sessions", [])
        self.adaptation_thresholds = data.get("adaptation_thresholds", self.adaptation_thresholds)
        self.deformable_registration = data.get("deformable_registration", True)
        self.adaptation_history = data.get("adaptation_history", [])
        self.monitoring_schedule = data.get("monitoring_schedule", "weekly")
        
        # Tao lai cac cau truc phien
        for session in self.monitoring_sessions:
            if "structures" in session:
                self.session_structures[session["session_id"]] = session["structures"]
        
        logger.info(f"Da khoi phuc ky thuat AdaptiveRT voi {len(self.monitoring_sessions)} phien giam sat") 