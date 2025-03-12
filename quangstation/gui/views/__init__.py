"""
Package chứa các màn hình chính của giao diện người dùng QuangStation.
"""

from quangstation.gui.views.main_view import MainView
from quangstation.gui.views.patient_view import PatientView
from quangstation.gui.views.plan_view import PlanView
from quangstation.gui.views.contour_view import ContourView
from quangstation.gui.views.dose_view import DoseView
from quangstation.gui.views.evaluation_view import EvaluationView
from quangstation.gui.views.plan_design_view import PlanDesignView
from quangstation.gui.views.beam_setup_view import BeamSetupView
from quangstation.gui.views.structure_view import StructureView
from quangstation.gui.views.optimization_view import OptimizationView

__all__ = [
    'MainView',
    'PatientView',
    'PlanView',
    'ContourView',
    'DoseView',
    'EvaluationView',
    'PlanDesignView',
    'BeamSetupView',
    'StructureView',
    'OptimizationView',
]
