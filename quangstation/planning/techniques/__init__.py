#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Package cung cấp các kỹ thuật xạ trị khác nhau cho QuangStation V2.
"""

from quangstation.planning.techniques.base import RTTechnique
from quangstation.planning.techniques.conventional import Conventional3DCRT
from quangstation.planning.techniques.fif import FieldInField
from quangstation.planning.techniques.imrt import IMRT
from quangstation.planning.techniques.vmat import VMAT
from quangstation.planning.techniques.adaptive_rt import AdaptiveRT
from quangstation.planning.techniques.stereotactic import StereotacticRT
from quangstation.planning.techniques.proton_therapy import ProtonTherapy

# Export các class để người dùng có thể import trực tiếp
__all__ = ['RTTechnique', 'Conventional3DCRT', 'FieldInField', 'IMRT', 'VMAT', 
           'AdaptiveRT', 'StereotacticRT', 'ProtonTherapy', 'create_technique']

def create_technique(technique_name: str, **kwargs):
    """
    Tạo đối tượng kỹ thuật xạ trị dựa trên tên
    
    Args:
        technique_name: Tên kỹ thuật xạ trị ("3DCRT", "FIF", "IMRT", "VMAT", "SRS", "SBRT", 
                                            "ADAPTIVE", "PROTON_PBS", "PROTON_PSPT")
        **kwargs: Các tham số bổ sung để cấu hình kỹ thuật
        
    Returns:
        Đối tượng RTTechnique tương ứng
        
    Raises:
        ValueError: Nếu technique_name không hợp lệ
    """
    technique_name = technique_name.upper()
    
    if technique_name == "3DCRT":
        technique = Conventional3DCRT()
    elif technique_name == "FIF":
        technique = FieldInField()
    elif technique_name == "IMRT":
        technique = IMRT()
    elif technique_name == "VMAT":
        technique = VMAT()
    elif technique_name == "SRS":
        # Sử dụng kỹ thuật StereotacticRT với chế độ SRS
        technique = StereotacticRT()
        technique.set_srs_mode(True)  # Sử dụng chế độ SRS (xạ phẫu)
    elif technique_name == "SBRT":
        # Sử dụng kỹ thuật StereotacticRT với chế độ SBRT
        technique = StereotacticRT()
        technique.set_srs_mode(False)  # Sử dụng chế độ SBRT (thân)
    elif technique_name == "ADAPTIVE":
        technique = AdaptiveRT()
    elif technique_name == "PROTON_PBS":
        technique = ProtonTherapy()
        technique.set_proton_type(ProtonTherapy.PBS)
    elif technique_name == "PROTON_PSPT":
        technique = ProtonTherapy()
        technique.set_proton_type(ProtonTherapy.PSPT)
    else:
        raise ValueError(f"Kỹ thuật xạ trị không hợp lệ: {technique_name}")
    
    # Áp dụng các tham số cấu hình nếu có
    for key, value in kwargs.items():
        if key == "angles":
            technique.set_beam_angles(value)
        elif key == "energies":
            technique.set_beam_energies(value)
        elif key == "field_sizes":
            technique.set_field_sizes(value)
        elif key == "prescription_dose":
            fractions = kwargs.get("fractions", 1)
            technique.set_prescription(value, fractions)
        elif key == "isocenter":
            technique.set_isocenter(value)
        elif key == "beams":
            # Thay thế toàn bộ danh sách chùm tia
            technique.beams = value
        elif hasattr(technique, key):
            setattr(technique, key, value)
        else:
            # Lưu vào metadata
            technique.set_metadata(key, value)
    
    return technique 