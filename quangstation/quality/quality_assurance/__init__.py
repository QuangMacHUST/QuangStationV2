"""
Module kiểm tra chất lượng (Quality Assurance) cho QuangStation.

Module này cung cấp các công cụ để đảm bảo chất lượng kế hoạch xạ trị
và hiệu chuẩn máy xạ trị.

Các tính năng chính:
- Kiểm tra chất lượng kế hoạch (PlanQA)
- Kiểm tra chất lượng máy xạ trị (MachineQA)
- Kiểm tra chất lượng nâng cao (AdvancedQA)

Version: 2.0.0
Author: QuangStation Team
License: MIT
"""

from quangstation.quality.quality_assurance.qa_tools import PlanQA, MachineQA
from quangstation.quality.quality_assurance.advanced_qa import AdvancedQA

__version__ = "2.0.0"
__author__ = "QuangStation Team"

__all__ = ["PlanQA", "MachineQA", "AdvancedQA"]
