#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
QuangStation V2 - Core Data Models
==================================

Module chứa các mô hình dữ liệu cơ bản cho hệ thống QuangStation V2.
Các mô hình này được sử dụng xuyên suốt ứng dụng để biểu diễn các thực thể
và đảm bảo tính nhất quán của dữ liệu.

Phát triển bởi Mạc Đăng Quang, 2023-2024
"""

# Import các class chính từ các module
from quangstation.core.data_models.image_data import ImageData
from quangstation.core.data_models.structure_data import (
    Structure, StructureSet, StructureType
)
from quangstation.core.data_models.plan_data import (
    PlanConfig, BeamConfig, PrescriptionConfig, TechniqueType, RadiationType
)
from quangstation.core.data_models.dose_data import (
    DoseData, DoseType
)
from quangstation.core.data_models.patient_data import PatientData
from quangstation.core.data_models.beam_data import (
    BeamData, MLCPosition, MLCSequence, MLCType, BeamType, 
    CollimatorType, RadiationType as BeamRadiationType
)

# Export các class để sử dụng dễ dàng
__all__ = [
    # Image Data
    'ImageData',
    
    # Structure Data
    'Structure', 'StructureSet', 'StructureType',
    
    # Plan Data
    'PlanConfig', 'BeamConfig', 'PrescriptionConfig', 
    'TechniqueType', 'RadiationType',
    
    # Dose Data
    'DoseData', 'DoseType',
    
    # Patient Data
    'PatientData',
    
    # Beam Data
    'BeamData', 'MLCPosition', 'MLCSequence', 'MLCType', 
    'BeamType', 'CollimatorType', 'BeamRadiationType'
]
