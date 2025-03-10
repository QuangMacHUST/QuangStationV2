"""
QuangStation V2 - Module dialogs
--------------------------------
Các dialog dùng trong giao diện người dùng
"""

from quangstation.gui.dialogs.patient_dialog import PatientDialog
from quangstation.gui.dialogs.plan_dialog import PlanDialog
from quangstation.gui.dialogs.contour_dialog import ContourDialog
from quangstation.gui.dialogs.dose_dialog import DoseDialog
from quangstation.gui.dialogs.beam_dialog import BeamDialog
from quangstation.gui.dialogs.goal_optimizer_dialog import GoalOptimizerDialog
from quangstation.gui.dialogs.kbp_trainer_dialog import KBPTrainerDialog

__all__ = ['PatientDialog', 'PlanDialog', 'ContourDialog', 'DoseDialog', 'BeamDialog', 'GoalOptimizerDialog', 'KBPTrainerDialog'] 