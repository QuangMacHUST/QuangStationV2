#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
QuangStation V2 - GUI Module
============================

Module giao diện người dùng cho hệ thống QuangStation.
Bao gồm các thành phần giao diện để tương tác với người dùng,
hiển thị dữ liệu và thực hiện các thao tác lập kế hoạch xạ trị.

Phát triển bởi Mạc Đăng Quang, 2023-2024
"""

__version__ = "2.0.0"
__author__ = "Mạc Đăng Quang"

# Import các module chính
from quangstation.gui.main_window import MainWindow
from quangstation.gui.plan_design import PlanDesignWindow
from quangstation.gui.patient_manager import PatientManagerWidget
from quangstation.gui.struct_panel import StructurePanel
from quangstation.gui.mlc_animation import MLCAnimation
from quangstation.gui.splash_screen import SplashScreen

# Expose các class và hàm chính
__all__ = [
    'MainWindow',
    'PlanDesignWindow',
    'PatientManagerWidget',
    'StructurePanel',
    'MLCAnimation',
    'SplashScreen'
]

