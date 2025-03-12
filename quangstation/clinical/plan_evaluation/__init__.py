"""
Module đánh giá kế hoạch xạ trị cho QuangStation V2.

Module này cung cấp các công cụ để đánh giá kế hoạch xạ trị, bao gồm:
- Tính toán và hiển thị DVH (Dose Volume Histogram)
- Phân tích phân bố liều
- Tính toán các chỉ số sinh học
- So sánh các kế hoạch xạ trị
- Đánh giá chỉ số chất lượng kế hoạch
"""

from quangstation.clinical.plan_evaluation.dvh import DVHCalculator, DVHPlotter, calculate_and_plot_dvh
from quangstation.clinical.plan_evaluation.dose_map import DoseMap, DoseAnalyzer, DoseStatistics
from quangstation.clinical.plan_evaluation.biological_metrics import calculate_eud, calculate_tcp, calculate_ntcp
from quangstation.clinical.plan_evaluation.biological_effects import BEDCalculator, EDQCalculator
from quangstation.clinical.plan_evaluation.plan_comparison import PlanComparison
from quangstation.clinical.plan_evaluation.plan_metrics import PlanQualityMetrics, evaluate_plan_quality

__all__ = [
    'DVHCalculator', 'DVHPlotter', 'calculate_and_plot_dvh',
    'DoseMap', 'DoseAnalyzer', 'DoseStatistics',
    'calculate_eud', 'calculate_tcp', 'calculate_ntcp',
    'BEDCalculator', 'EDQCalculator',
    'PlanComparison',
    'PlanQualityMetrics', 'evaluate_plan_quality'
]
