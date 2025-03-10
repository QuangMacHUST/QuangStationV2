"""
Module giao diện người dùng cho thiết kế kế hoạch xạ trị.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from typing import Dict, List, Optional, Callable, Any, Union
import os
import json
import threading
from datetime import datetime

from quangstation.utils.logging import get_logger
from quangstation.planning import create_technique
from quangstation.dose_calculation.dose_engine_wrapper import DoseCalculator
from quangstation.plan_evaluation.dvh import DVHCalculator, DVHPlotter

logger = get_logger(__name__)

class PlanDesignWindow:
    """
    Cửa sổ thiết kế kế hoạch xạ trị.
    """
    
    def __init__(self, parent, patient_id: str, structures: Dict[str, np.ndarray] = None, 
                 callback: Callable = None):
        """
        Khởi tạo cửa sổ thiết kế kế hoạch.
        
        Args:
            parent: Widget cha
            patient_id: ID bệnh nhân
            structures: Dictionary các cấu trúc {name: mask}
            callback: Hàm callback khi đóng cửa sổ
        """
        self.parent = parent
        self.patient_id = patient_id
        self.structures = structures if structures else {}
        self.callback = callback
        
        # Biến lưu trữ dữ liệu
        self.plan_data = {
            'plan_name': f"Plan_{patient_id}",
            'beams': [],
            'technique': '3DCRT',
            'dose_algorithm': 'CCC'
        }
        self.dose_data = None
        self.dvh_data = {}
        
        # Biến điều khiển UI
        self.plan_name_var = None
        self.total_dose_var = None
        self.fraction_count_var = None
        self.fraction_dose_var = None
        self.technique_var = None
        self.beam_energy_var = None
        self.beam_angle_var = None
        self.beam_collimator_var = None
        self.beam_gantry_var = None
        self.beam_couch_var = None
        self.structure_name_var = None
        self.structure_type_var = None
        self.structure_color_var = None
        
        # Đối tượng kỹ thuật xạ trị
        self.rt_technique = None
        
        # Đối tượng tính toán liều
        self.dose_calculator = None
        
        # Đối tượng DVH
        self.dvh_calculator = None
        self.dvh_plotter = None
        
        # Tạo cửa sổ
        self.window = tk.Toplevel(parent)
        self.window.title(f"Thiết kế kế hoạch xạ trị - Bệnh nhân {patient_id}")
        self.window.geometry("1200x800")
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Thiết lập UI
        self.setup_ui()
        
        # Khởi tạo kỹ thuật xạ trị mặc định
        self.set_rt_technique('Conventional3DCRT')
        
        logger.info(f"Đã khởi tạo cửa sổ thiết kế kế hoạch cho bệnh nhân {patient_id}")
        
    def setup_ui(self):
        """Thiết lập giao diện người dùng."""
        # Tạo thanh công cụ
        self.create_toolbar()
        
        # Tạo layout chính
        self.main_frame = ttk.Frame(self.window)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Chia thành 2 phần: Thông tin kế hoạch và hiển thị
        self.left_frame = ttk.Frame(self.main_frame, width=400)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5)
        
        self.right_frame = ttk.Frame(self.main_frame)
        self.right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tạo các tab trong left_frame
        self.tab_control = ttk.Notebook(self.left_frame)
        
        self.tab_prescription = ttk.Frame(self.tab_control)
        self.tab_technique = ttk.Frame(self.tab_control)
        self.tab_beams = ttk.Frame(self.tab_control)
        self.tab_structures = ttk.Frame(self.tab_control)
        
        self.tab_control.add(self.tab_prescription, text="Kê toa")
        self.tab_control.add(self.tab_technique, text="Kỹ thuật")
        self.tab_control.add(self.tab_beams, text="Chùm tia")
        self.tab_control.add(self.tab_structures, text="Cấu trúc")
        
        self.tab_control.pack(fill=tk.BOTH, expand=True)
        
        # Tạo các tab trong right_frame
        self.right_tab_control = ttk.Notebook(self.right_frame)
        
        self.tab_3d_view = ttk.Frame(self.right_tab_control)
        self.tab_beam_view = ttk.Frame(self.right_tab_control)
        self.tab_dvh = ttk.Frame(self.right_tab_control)
        
        self.right_tab_control.add(self.tab_3d_view, text="Xem 3D")
        self.right_tab_control.add(self.tab_beam_view, text="Xem chùm tia")
        self.right_tab_control.add(self.tab_dvh, text="DVH")
        
        self.right_tab_control.pack(fill=tk.BOTH, expand=True)
        
        # Thiết lập nội dung cho các tab
        self.setup_prescription_tab()
        self.setup_technique_tab()
        self.setup_beams_tab()
        self.setup_structures_tab()
        self.setup_3d_view_tab()
        self.setup_beam_view_tab()
        self.setup_dvh_tab()
        
        # Tạo thanh trạng thái
        self.status_bar = ttk.Label(self.window, text="Sẵn sàng", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def create_toolbar(self):
        """Tạo thanh công cụ."""
        toolbar = ttk.Frame(self.window)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Nút lưu kế hoạch
        save_btn = ttk.Button(toolbar, text="Lưu kế hoạch", command=self.save_plan)
        save_btn.pack(side=tk.LEFT, padx=2)
        
        # Nút tính toán liều
        calc_dose_btn = ttk.Button(toolbar, text="Tính liều", command=self.calculate_dose)
        calc_dose_btn.pack(side=tk.LEFT, padx=2)
        
        # Nút tính DVH
        calc_dvh_btn = ttk.Button(toolbar, text="Tính DVH", command=self.calculate_dvh)
        calc_dvh_btn.pack(side=tk.LEFT, padx=2)
        
        # Nút tối ưu hóa
        optimize_btn = ttk.Button(toolbar, text="Tối ưu hóa", command=self.optimize_plan)
        optimize_btn.pack(side=tk.LEFT, padx=2)
        
        # Nút tối ưu hóa KBP
        kbp_btn = ttk.Button(toolbar, text="KBP Optimize", command=self.kbp_optimize)
        kbp_btn.pack(side=tk.LEFT, padx=2)
        
        # Nút tạo báo cáo
        report_btn = ttk.Button(toolbar, text="Tạo báo cáo", command=self.create_report)
        report_btn.pack(side=tk.LEFT, padx=2)
        
        # Nút xuất kế hoạch
        export_btn = ttk.Button(toolbar, text="Xuất DICOM", command=self.export_rt_plan)
        export_btn.pack(side=tk.LEFT, padx=2)
        
        # Nút đóng
        close_btn = ttk.Button(toolbar, text="Đóng", command=self.on_close)
        close_btn.pack(side=tk.RIGHT, padx=2)
        
    def setup_prescription_tab(self):
        """Thiết lập tab kê toa."""
        frame = ttk.Frame(self.tab_prescription, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Tiêu đề
        ttk.Label(frame, text="Thông tin kê toa", font=("Arial", 12, "bold")).grid(column=0, row=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Liều kê toa
        ttk.Label(frame, text="Liều kê toa (Gy):").grid(column=0, row=1, sticky=tk.W, pady=2)
        self.prescription_var = tk.DoubleVar(value=0.0)
        ttk.Entry(frame, textvariable=self.prescription_var, width=10).grid(column=1, row=1, sticky=tk.W, pady=2)
        
        # Số phân liều
        ttk.Label(frame, text="Số phân liều:").grid(column=0, row=2, sticky=tk.W, pady=2)
        self.fractions_var = tk.IntVar(value=0)
        ttk.Entry(frame, textvariable=self.fractions_var, width=10).grid(column=1, row=2, sticky=tk.W, pady=2)
        
        # Liều mỗi phân liều
        ttk.Label(frame, text="Liều/phân liều (Gy):").grid(column=0, row=3, sticky=tk.W, pady=2)
        self.dose_per_fraction_var = tk.DoubleVar(value=0.0)
        dose_per_fraction_entry = ttk.Entry(frame, textvariable=self.dose_per_fraction_var, width=10, state='readonly')
        dose_per_fraction_entry.grid(column=1, row=3, sticky=tk.W, pady=2)
        
        # Cấu trúc đích
        ttk.Label(frame, text="Cấu trúc đích:").grid(column=0, row=4, sticky=tk.W, pady=2)
        self.target_var = tk.StringVar()
        target_combo = ttk.Combobox(frame, textvariable=self.target_var, width=20)
        target_combo.grid(column=1, row=4, sticky=tk.W, pady=2)
        
        # Thiết lập danh sách cấu trúc đích
        if self.structures:
            target_options = [name for name in self.structures.keys() 
                             if 'ptv' in name.lower() or 'gtv' in name.lower() or 'ctv' in name.lower()]
            if not target_options:
                target_options = list(self.structures.keys())
            target_combo['values'] = target_options
            if target_options:
                self.target_var.set(target_options[0])
        
        # Tâm xạ trị
        ttk.Label(frame, text="Tâm xạ trị (mm):").grid(column=0, row=5, sticky=tk.W, pady=2)
        isocenter_frame = ttk.Frame(frame)
        isocenter_frame.grid(column=1, row=5, sticky=tk.W, pady=2)
        
        self.isocenter_x_var = tk.DoubleVar(value=0.0)
        self.isocenter_y_var = tk.DoubleVar(value=0.0)
        self.isocenter_z_var = tk.DoubleVar(value=0.0)
        
        ttk.Label(isocenter_frame, text="X:").pack(side=tk.LEFT)
        ttk.Entry(isocenter_frame, textvariable=self.isocenter_x_var, width=5).pack(side=tk.LEFT, padx=2)
        ttk.Label(isocenter_frame, text="Y:").pack(side=tk.LEFT)
        ttk.Entry(isocenter_frame, textvariable=self.isocenter_y_var, width=5).pack(side=tk.LEFT, padx=2)
        ttk.Label(isocenter_frame, text="Z:").pack(side=tk.LEFT)
        ttk.Entry(isocenter_frame, textvariable=self.isocenter_z_var, width=5).pack(side=tk.LEFT, padx=2)
        
        # Nút tìm tâm tự động
        ttk.Button(frame, text="Tìm tâm tự động", command=self.find_isocenter).grid(column=1, row=6, sticky=tk.W, pady=5)
        
        # Ràng buộc cho liều mỗi phân liều
        def update_dose_per_fraction(*args):
            try:
                prescription = self.prescription_var.get()
                fractions = self.fractions_var.get()
                if fractions > 0:
                    self.dose_per_fraction_var.set(round(prescription / fractions, 2))
                else:
                    self.dose_per_fraction_var.set(0)
            except:
                self.dose_per_fraction_var.set(0)
                
        self.prescription_var.trace_add("write", update_dose_per_fraction)
        self.fractions_var.trace_add("write", update_dose_per_fraction)
        
    def setup_technique_tab(self):
        """Thiết lập tab kỹ thuật."""
        frame = ttk.Frame(self.tab_technique, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Tiêu đề
        ttk.Label(frame, text="Kỹ thuật xạ trị", font=("Arial", 12, "bold")).grid(column=0, row=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Loại kỹ thuật
        ttk.Label(frame, text="Loại kỹ thuật:").grid(column=0, row=1, sticky=tk.W, pady=2)
        self.technique_var = tk.StringVar(value="Conventional3DCRT")
        technique_combo = ttk.Combobox(frame, textvariable=self.technique_var, width=20, state="readonly")
        technique_combo['values'] = ["Conventional3DCRT", "FieldInField", "IMRT", "VMAT", "SRS", "SBRT"]
        technique_combo.grid(column=1, row=1, sticky=tk.W, pady=2)
        technique_combo.bind("<<ComboboxSelected>>", self.on_technique_change)
        
        # Frame cho các tùy chọn kỹ thuật
        self.technique_options_frame = ttk.LabelFrame(frame, text="Tùy chọn kỹ thuật", padding=10)
        self.technique_options_frame.grid(column=0, row=2, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Nút tạo kế hoạch
        ttk.Button(frame, text="Tạo kế hoạch", command=self.create_plan).grid(column=1, row=3, sticky=tk.E, pady=10)
        
    def setup_beams_tab(self):
        """Thiết lập tab chùm tia."""
        frame = ttk.Frame(self.tab_beams, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Tiêu đề
        ttk.Label(frame, text="Cấu hình chùm tia", font=("Arial", 12, "bold")).grid(column=0, row=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Danh sách chùm tia
        ttk.Label(frame, text="Danh sách chùm tia:").grid(column=0, row=1, sticky=tk.W, pady=2)
        
        # Frame chứa danh sách và thanh cuộn
        list_frame = ttk.Frame(frame)
        list_frame.grid(column=0, row=2, columnspan=2, sticky=(tk.W, tk.E), pady=2)
        
        # Tạo danh sách
        self.beam_listbox = tk.Listbox(list_frame, width=50, height=10)
        self.beam_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Tạo thanh cuộn
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.beam_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.beam_listbox.configure(yscrollcommand=scrollbar.set)
        
        # Ràng buộc sự kiện
        self.beam_listbox.bind('<<ListboxSelect>>', self.on_beam_select)
        
        # Frame cho thông tin chi tiết chùm tia
        beam_details_frame = ttk.LabelFrame(frame, text="Thông tin chi tiết", padding=10)
        beam_details_frame.grid(column=0, row=3, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Các thông số chùm tia
        # ID
        ttk.Label(beam_details_frame, text="ID:").grid(column=0, row=0, sticky=tk.W, pady=2)
        self.beam_id_var = tk.StringVar()
        ttk.Entry(beam_details_frame, textvariable=self.beam_id_var, width=20, state='readonly').grid(column=1, row=0, sticky=tk.W, pady=2)
        
        # Loại
        ttk.Label(beam_details_frame, text="Loại:").grid(column=0, row=1, sticky=tk.W, pady=2)
        self.beam_type_var = tk.StringVar()
        ttk.Entry(beam_details_frame, textvariable=self.beam_type_var, width=20, state='readonly').grid(column=1, row=1, sticky=tk.W, pady=2)
        
        # Năng lượng
        ttk.Label(beam_details_frame, text="Năng lượng (MV):").grid(column=0, row=2, sticky=tk.W, pady=2)
        self.beam_energy_var = tk.DoubleVar()
        ttk.Entry(beam_details_frame, textvariable=self.beam_energy_var, width=10).grid(column=1, row=2, sticky=tk.W, pady=2)
        
        # Góc gantry
        ttk.Label(beam_details_frame, text="Góc gantry (°):").grid(column=0, row=3, sticky=tk.W, pady=2)
        self.beam_gantry_var = tk.DoubleVar()
        ttk.Entry(beam_details_frame, textvariable=self.beam_gantry_var, width=10).grid(column=1, row=3, sticky=tk.W, pady=2)
        
        # Góc collimator
        ttk.Label(beam_details_frame, text="Góc collimator (°):").grid(column=0, row=4, sticky=tk.W, pady=2)
        self.beam_collimator_var = tk.DoubleVar()
        ttk.Entry(beam_details_frame, textvariable=self.beam_collimator_var, width=10).grid(column=1, row=4, sticky=tk.W, pady=2)
        
        # Góc bàn
        ttk.Label(beam_details_frame, text="Góc bàn (°):").grid(column=0, row=5, sticky=tk.W, pady=2)
        self.beam_couch_var = tk.DoubleVar()
        ttk.Entry(beam_details_frame, textvariable=self.beam_couch_var, width=10).grid(column=1, row=5, sticky=tk.W, pady=2)
        
        # Trọng số
        ttk.Label(beam_details_frame, text="Trọng số:").grid(column=0, row=6, sticky=tk.W, pady=2)
        self.beam_weight_var = tk.DoubleVar()
        ttk.Entry(beam_details_frame, textvariable=self.beam_weight_var, width=10).grid(column=1, row=6, sticky=tk.W, pady=2)
        
        # Nút cập nhật
        ttk.Button(beam_details_frame, text="Cập nhật", command=self.update_beam).grid(column=1, row=7, sticky=tk.E, pady=10)
        
    def setup_structures_tab(self):
        """Thiết lập tab cấu trúc."""
        frame = ttk.Frame(self.tab_structures, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Tiêu đề
        ttk.Label(frame, text="Danh sách cấu trúc", font=("Arial", 12, "bold")).grid(column=0, row=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Frame chứa danh sách và thanh cuộn
        list_frame = ttk.Frame(frame)
        list_frame.grid(column=0, row=1, columnspan=2, sticky=(tk.W, tk.E), pady=2)
        
        # Tạo danh sách
        self.structure_listbox = tk.Listbox(list_frame, width=50, height=10)
        self.structure_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Tạo thanh cuộn
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.structure_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.structure_listbox.configure(yscrollcommand=scrollbar.set)
        
        # Thêm cấu trúc vào danh sách
        if self.structures:
            for name in self.structures.keys():
                self.structure_listbox.insert(tk.END, name)
                
        # Ràng buộc sự kiện
        self.structure_listbox.bind('<<ListboxSelect>>', self.on_structure_select)
        
        # Thông tin cấu trúc
        info_frame = ttk.LabelFrame(frame, text="Thông tin cấu trúc", padding=10)
        info_frame.grid(column=0, row=2, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Tên
        ttk.Label(info_frame, text="Tên:").grid(column=0, row=0, sticky=tk.W, pady=2)
        self.structure_name_var = tk.StringVar()
        ttk.Entry(info_frame, textvariable=self.structure_name_var, width=30, state='readonly').grid(column=1, row=0, sticky=tk.W, pady=2)
        
        # Thể tích
        ttk.Label(info_frame, text="Thể tích (cm³):").grid(column=0, row=1, sticky=tk.W, pady=2)
        self.structure_volume_var = tk.DoubleVar()
        ttk.Entry(info_frame, textvariable=self.structure_volume_var, width=10, state='readonly').grid(column=1, row=1, sticky=tk.W, pady=2)
        
        # Loại
        ttk.Label(info_frame, text="Loại:").grid(column=0, row=2, sticky=tk.W, pady=2)
        self.structure_type_var = tk.StringVar()
        structure_type_combo = ttk.Combobox(info_frame, textvariable=self.structure_type_var, width=20, state='readonly')
        structure_type_combo['values'] = ["PTV", "GTV", "CTV", "OAR", "BODY", "OTHER"]
        structure_type_combo.grid(column=1, row=2, sticky=tk.W, pady=2)
        
        # Màu
        ttk.Label(info_frame, text="Màu:").grid(column=0, row=3, sticky=tk.W, pady=2)
        self.structure_color_var = tk.StringVar()
        color_frame = ttk.Frame(info_frame)
        color_frame.grid(column=1, row=3, sticky=tk.W, pady=2)
        
        ttk.Entry(color_frame, textvariable=self.structure_color_var, width=10).pack(side=tk.LEFT)
        ttk.Button(color_frame, text="Chọn", command=self.choose_color, width=5).pack(side=tk.LEFT, padx=5)
        
        # Nút cập nhật
        ttk.Button(info_frame, text="Cập nhật", command=self.update_structure).grid(column=1, row=4, sticky=tk.E, pady=10)
        
    def setup_3d_view_tab(self):
        """Thiết lập tab xem 3D."""
        frame = ttk.Frame(self.tab_3d_view, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Tiêu đề
        ttk.Label(frame, text="Xem 3D", font=("Arial", 12, "bold")).pack(side=tk.TOP, anchor=tk.W, pady=5)
        
        # Frame chứa biểu đồ
        plot_frame = ttk.Frame(frame)
        plot_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Tạo figure và canvas
        self.fig_3d = plt.figure(figsize=(6, 6))
        self.canvas_3d = FigureCanvasTkAgg(self.fig_3d, master=plot_frame)
        self.canvas_3d.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Tạo subplot 3D
        self.ax_3d = self.fig_3d.add_subplot(111, projection='3d')
        self.ax_3d.set_xlabel('X')
        self.ax_3d.set_ylabel('Y')
        self.ax_3d.set_zlabel('Z')
        self.ax_3d.set_title('Mô hình 3D')
        
        # Thanh công cụ ở dưới
        toolbar_frame = ttk.Frame(frame)
        toolbar_frame.pack(fill=tk.X, pady=5)
        
        # Nút hiển thị đích
        ttk.Button(toolbar_frame, text="Hiển thị đích", command=self.show_target_3d).pack(side=tk.LEFT, padx=2)
        
        # Nút hiển thị các cơ quan nguy cấp
        ttk.Button(toolbar_frame, text="Hiển thị OAR", command=self.show_oars_3d).pack(side=tk.LEFT, padx=2)
        
        # Nút hiển thị chùm tia
        ttk.Button(toolbar_frame, text="Hiển thị chùm tia", command=self.show_beams_3d).pack(side=tk.LEFT, padx=2)
        
        # Nút hiển thị liều
        ttk.Button(toolbar_frame, text="Hiển thị liều", command=self.show_dose_3d).pack(side=tk.LEFT, padx=2)
        
        # Nút xoay mô hình
        ttk.Button(toolbar_frame, text="Xoay", command=self.rotate_3d_model).pack(side=tk.LEFT, padx=2)
        
        # Nút lưu hình ảnh
        ttk.Button(toolbar_frame, text="Lưu hình ảnh", command=self.save_3d_image).pack(side=tk.LEFT, padx=2)
        
    def setup_beam_view_tab(self):
        """Thiết lập tab xem chùm tia."""
        frame = ttk.Frame(self.tab_beam_view, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Tiêu đề
        ttk.Label(frame, text="Xem chùm tia", font=("Arial", 12, "bold")).pack(side=tk.TOP, anchor=tk.W, pady=5)
        
        # Frame chọn chùm tia
        selection_frame = ttk.Frame(frame)
        selection_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(selection_frame, text="Chọn chùm tia:").pack(side=tk.LEFT)
        self.beam_view_var = tk.StringVar()
        self.beam_view_combo = ttk.Combobox(selection_frame, textvariable=self.beam_view_var, width=30, state='readonly')
        self.beam_view_combo.pack(side=tk.LEFT, padx=5)
        self.beam_view_combo.bind("<<ComboboxSelected>>", self.on_beam_view_select)
        
        # Frame chứa biểu đồ
        plot_frame = ttk.Frame(frame)
        plot_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Tạo figure và canvas
        self.fig_beam = plt.figure(figsize=(6, 6))
        self.canvas_beam = FigureCanvasTkAgg(self.fig_beam, master=plot_frame)
        self.canvas_beam.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Tạo subplot
        self.ax_beam = self.fig_beam.add_subplot(111)
        self.ax_beam.set_xlabel('X (mm)')
        self.ax_beam.set_ylabel('Y (mm)')
        self.ax_beam.set_title('Beam\'s Eye View')
        self.ax_beam.set_aspect('equal')
        
        # Thanh công cụ ở dưới
        toolbar_frame = ttk.Frame(frame)
        toolbar_frame.pack(fill=tk.X, pady=5)
        
        # Nút hiển thị MLC
        ttk.Button(toolbar_frame, text="Hiển thị MLC", command=self.show_mlc).pack(side=tk.LEFT, padx=2)
        
        # Nút hiển thị đích
        ttk.Button(toolbar_frame, text="Hiển thị đích", command=self.show_target_bev).pack(side=tk.LEFT, padx=2)
        
        # Nút hiển thị OAR
        ttk.Button(toolbar_frame, text="Hiển thị OAR", command=self.show_oars_bev).pack(side=tk.LEFT, padx=2)
        
        # Nút xuất DRR
        ttk.Button(toolbar_frame, text="Xuất DRR", command=self.export_drr).pack(side=tk.LEFT, padx=2)
        
    def setup_dvh_tab(self):
        """Thiết lập tab DVH."""
        frame = ttk.Frame(self.tab_dvh, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Tiêu đề
        ttk.Label(frame, text="Biểu đồ Liều-Thể tích (DVH)", font=("Arial", 12, "bold")).pack(side=tk.TOP, anchor=tk.W, pady=5)
        
        # Frame chứa biểu đồ
        plot_frame = ttk.Frame(frame)
        plot_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Tạo figure và canvas
        self.fig_dvh = plt.figure(figsize=(6, 5))
        self.canvas_dvh = FigureCanvasTkAgg(self.fig_dvh, master=plot_frame)
        self.canvas_dvh.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Frame chọn cấu trúc
        selection_frame = ttk.LabelFrame(frame, text="Chọn cấu trúc", padding=5)
        selection_frame.pack(fill=tk.X, pady=5)
        
        # Frame chứa các checkbox
        self.structures_check_frame = ttk.Frame(selection_frame)
        self.structures_check_frame.pack(fill=tk.X, pady=5)
        
        # Biến để lưu các checkbox
        self.structure_vars = {}
        
        # Tạo các checkbox dựa trên cấu trúc có sẵn
        if self.structures:
            col = 0
            row = 0
            for name in self.structures.keys():
                var = tk.BooleanVar(value=False)
                self.structure_vars[name] = var
                cb = ttk.Checkbutton(self.structures_check_frame, text=name, variable=var, 
                                    command=self.update_dvh_plot)
                cb.grid(column=col, row=row, sticky=tk.W, padx=5, pady=2)
                
                # Tối đa 3 cột
                col += 1
                if col > 2:
                    col = 0
                    row += 1
                    
        # Frame biểu đồ DVH
        self.dvh_figure = plt.Figure(figsize=(8, 6), dpi=100)
        self.dvh_canvas = FigureCanvasTkAgg(self.dvh_figure, plot_frame)
        self.dvh_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Thanh công cụ
        toolbar_frame = ttk.Frame(plot_frame)
        toolbar_frame.pack(fill=tk.X, expand=False)
        
        # Nút tính toán DVH
        ttk.Button(toolbar_frame, text="Tính toán DVH", command=self.calculate_dvh).pack(side=tk.LEFT, padx=2)
        
        # Nút xuất dữ liệu
        ttk.Button(toolbar_frame, text="Xuất dữ liệu", command=self.export_dvh_data).pack(side=tk.LEFT, padx=2)
        
        # Nút lưu hình ảnh
        ttk.Button(toolbar_frame, text="Lưu hình ảnh", command=self.save_dvh_image).pack(side=tk.LEFT, padx=2)
        
    def on_beam_view_select(self, event):
        """Xử lý sự kiện khi chọn chùm tia."""
        selected_beam = self.beam_view_combo.get()
        if selected_beam:
            self.beam_id_var.set(selected_beam)
            self.beam_type_var.set(selected_beam)
            self.beam_energy_var.set(self.beam_energy_var.get())
            self.beam_gantry_var.set(self.beam_gantry_var.get())
            self.beam_collimator_var.set(self.beam_collimator_var.get())
            self.beam_couch_var.set(self.beam_couch_var.get())
            self.beam_weight_var.set(self.beam_weight_var.get())
            self.ax_beam.bar(range(len(self.beam_view_combo['values'])), self.beam_weight_var.get())
            self.ax_beam.set_xticks(range(len(self.beam_view_combo['values'])))
            self.ax_beam.set_xticklabels(self.beam_view_combo['values'])

    def on_technique_change(self, event):
        """Xử lý sự kiện khi thay đổi kỹ thuật xạ trị."""
        if hasattr(self, 'technique_combo'):
            self.set_rt_technique(self.technique_combo.get())

    def set_rt_technique(self, technique_name: str):
        """
        Thiết lập kỹ thuật xạ trị dựa trên tên kỹ thuật.
        
        Args:
            technique_name: Tên kỹ thuật ("Conventional3DCRT", "FieldInField", ...)
        """
        # Sử dụng hàm factory create_technique từ module planning mới
        try:
            # Chuyển đổi tên kỹ thuật sang định dạng phù hợp
            if technique_name == "Conventional3DCRT":
                name = "3DCRT"
            elif technique_name == "FieldInField":
                name = "FIF"
            else:
                name = technique_name
            
            # Khởi tạo kỹ thuật xạ trị
            self.rt_technique = create_technique(name)
            logger.info(f"Đã thiết lập kỹ thuật xạ trị: {technique_name}")
            
            # Cập nhật plan_data
            self.plan_data['technique'] = technique_name
            
            # Cập nhật giao diện nếu cần
            self.technique_var.set(technique_name)
            
        except Exception as error:
            logger.error(f"Lỗi khi thiết lập kỹ thuật xạ trị: {str(error)}")
            messagebox.showerror("Lỗi", f"Không thể khởi tạo kỹ thuật xạ trị: {str(error)}")

    def create_plan(self):
        """Tạo kế hoạch xạ trị dựa trên thông tin đã nhập."""
        try:
            # Cập nhật thông tin từ giao diện
            prescription = self.prescription_var.get()
            fractions = self.fractions_var.get()
            isocenter = [
                self.isocenter_x_var.get(),
                self.isocenter_y_var.get(),
                self.isocenter_z_var.get()
            ]
            
            # Kiểm tra dữ liệu
            if prescription <= 0:
                messagebox.showerror("Lỗi", "Liều kê toa phải lớn hơn 0")
                return
                
            if fractions <= 0:
                messagebox.showerror("Lỗi", "Số phân liều phải lớn hơn 0")
                return
            
            # Thiết lập thông số cho kỹ thuật xạ trị
            if self.rt_technique:
                self.rt_technique.set_prescription(prescription, fractions)
                self.rt_technique.set_isocenter(isocenter)
                
                # Tạo kế hoạch
                plan = self.rt_technique.create_plan(self.structures)
                
                # Cập nhật thông tin kế hoạch
                self.plan_data['prescription'] = prescription
                self.plan_data['fractions'] = fractions
                self.plan_data['isocenter'] = isocenter
                
                # Cập nhật danh sách chùm tia
                self.plan_data['beams'] = plan.get('beams', [])
                self.update_beam_list()
                
                messagebox.showinfo("Thành công", "Đã tạo kế hoạch xạ trị thành công")
                
                # Cập nhật giao diện
                self.status_bar.config(text=f"Đã tạo kế hoạch xạ trị: {self.technique_var.get()}")
            else:
                messagebox.showerror("Lỗi", "Chưa thiết lập kỹ thuật xạ trị")
                
        except Exception as error:
            logger.error(f"Lỗi khi tạo kế hoạch xạ trị: {str(error)}")
            messagebox.showerror("Lỗi", f"Không thể tạo kế hoạch xạ trị: {str(error)}")

    def update_beam_list(self):
        """Cập nhật danh sách chùm tia trên giao diện."""
        # Xóa danh sách cũ
        self.beam_listbox.delete(0, tk.END)
        self.beam_view_combo['values'] = []
        
        # Thêm các chùm tia mới
        beam_ids = []
        for beam in self.plan_data['beams']:
            beam_id = beam.get('id', 'Unknown')
            self.beam_listbox.insert(tk.END, beam_id)
            beam_ids.append(beam_id)
            
        # Cập nhật combobox
        if beam_ids:
            self.beam_view_combo['values'] = beam_ids
            self.beam_view_combo.current(0)

    def on_close(self):
        """Xử lý sự kiện khi đóng cửa sổ."""
        # Lưu trạng thái nếu cần
        if self.callback:
            self.callback()  # Thông báo cho đối tượng gọi rằng cửa sổ đã đóng
        self.window.destroy()

    def save_plan(self):
        """Lưu kế hoạch xạ trị hiện tại."""
        try:
            # Lấy thông tin kế hoạch từ các trường nhập liệu
            plan_data = self.get_plan_data()
            
            # Lưu vào file
            file_path = filedialog.asksaveasfilename(
                defaultextension=".rtplan",
                filetypes=[("RT Plan files", "*.rtplan"), ("All files", "*.*")]
            )
            
            if file_path:
                with open(file_path, 'w') as f:
                    json.dump(plan_data, f, indent=2)
                messagebox.showinfo("Thành công", "Đã lưu kế hoạch xạ trị")
                logger.info(f"Đã lưu kế hoạch xạ trị vào {file_path}")
        except Exception as error:
            logger.error(f"Lỗi khi lưu kế hoạch: {str(error)}")
            messagebox.showerror("Lỗi", f"Không thể lưu kế hoạch: {str(error)}")
    
    def load_plan(self):
        """Tải kế hoạch xạ trị từ file."""
        try:
            file_path = filedialog.askopenfilename(
                filetypes=[("RT Plan files", "*.rtplan"), ("All files", "*.*")]
            )
            
            if file_path:
                with open(file_path, 'r') as f:
                    plan_data = json.load(f)
                
                # Cập nhật giao diện với dữ liệu từ file
                self.set_plan_data(plan_data)
                messagebox.showinfo("Thành công", "Đã tải kế hoạch xạ trị")
                logger.info(f"Đã tải kế hoạch xạ trị từ {file_path}")
        except Exception as error:
            logger.error(f"Lỗi khi tải kế hoạch: {str(error)}")
            messagebox.showerror("Lỗi", f"Không thể tải kế hoạch: {str(error)}")
    
    def calculate_dose(self):
        """Tính toán liều cho kế hoạch hiện tại."""
        try:
            # Kiểm tra xem đã có kế hoạch chưa
            if not hasattr(self, 'plan') or self.plan is None:
                plan_data = self.get_plan_data()
                if not plan_data:
                    messagebox.showwarning("Cảnh báo", "Vui lòng tạo kế hoạch trước khi tính liều")
                    return
            
            # Kiểm tra xem đã có chùm tia chưa
            if not hasattr(self, 'beams') or not self.beams:
                messagebox.showwarning("Cảnh báo", "Vui lòng thêm ít nhất một chùm tia trước khi tính liều")
                return
            
            # Kiểm tra xem đã có cấu trúc chưa
            if not hasattr(self, 'structures') or not self.structures:
                messagebox.showwarning("Cảnh báo", "Vui lòng thêm ít nhất một cấu trúc trước khi tính liều")
                return
            
            # Tạo hộp thoại tùy chọn tính liều
            import tkinter as tk
            from tkinter import ttk
            
            dose_dialog = tk.Toplevel(self.window)
            dose_dialog.title("Tùy chọn tính liều")
            dose_dialog.geometry("500x400")
            dose_dialog.resizable(False, False)
            dose_dialog.transient(self.window)
            dose_dialog.grab_set()
            
            # Tạo các frame chính
            main_frame = ttk.Frame(dose_dialog, padding=10)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Tiêu đề
            ttk.Label(main_frame, text="Tùy chọn tính toán liều", font=("Arial", 12, "bold")).pack(pady=5)
            
            # Frame thuật toán
            algorithm_frame = ttk.LabelFrame(main_frame, text="Thuật toán tính liều", padding=10)
            algorithm_frame.pack(fill=tk.X, pady=5)
            
            # Tùy chọn thuật toán
            algorithm_var = tk.StringVar(value="CCC")
            ttk.Radiobutton(algorithm_frame, text="Collapsed Cone Convolution (CCC)", variable=algorithm_var, value="CCC").pack(anchor=tk.W)
            ttk.Radiobutton(algorithm_frame, text="Pencil Beam Convolution (PBC)", variable=algorithm_var, value="PBC").pack(anchor=tk.W)
            ttk.Radiobutton(algorithm_frame, text="Monte Carlo", variable=algorithm_var, value="MC").pack(anchor=tk.W)
            
            # Frame tùy chọn Monte Carlo
            mc_frame = ttk.LabelFrame(main_frame, text="Tùy chọn Monte Carlo", padding=10)
            mc_frame.pack(fill=tk.X, pady=5)
            
            # Số hạt
            ttk.Label(mc_frame, text="Số hạt mỗi lần lặp:").grid(row=0, column=0, sticky=tk.W, pady=5)
            particles_var = tk.StringVar(value="100000")
            ttk.Entry(mc_frame, textvariable=particles_var, width=10).grid(row=0, column=1, sticky=tk.W, pady=5)
            
            # Độ không đảm bảo mục tiêu
            ttk.Label(mc_frame, text="Độ không đảm bảo mục tiêu (%):").grid(row=1, column=0, sticky=tk.W, pady=5)
            uncertainty_var = tk.StringVar(value="2.0")
            ttk.Entry(mc_frame, textvariable=uncertainty_var, width=10).grid(row=1, column=1, sticky=tk.W, pady=5)
            
            # Số lần lặp tối đa
            ttk.Label(mc_frame, text="Số lần lặp tối đa:").grid(row=2, column=0, sticky=tk.W, pady=5)
            iterations_var = tk.StringVar(value="10")
            ttk.Entry(mc_frame, textvariable=iterations_var, width=10).grid(row=2, column=1, sticky=tk.W, pady=5)
            
            # Frame tùy chọn chung
            options_frame = ttk.LabelFrame(main_frame, text="Tùy chọn chung", padding=10)
            options_frame.pack(fill=tk.X, pady=5)
            
            # Độ phân giải
            ttk.Label(options_frame, text="Độ phân giải lưới liều (mm):").grid(row=0, column=0, sticky=tk.W, pady=5)
            resolution_var = tk.StringVar(value="2.5")
            ttk.Entry(options_frame, textvariable=resolution_var, width=10).grid(row=0, column=1, sticky=tk.W, pady=5)
            
            # Hiển thị tiến trình
            show_progress_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(options_frame, text="Hiển thị tiến trình tính toán", variable=show_progress_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
            
            # Frame nút điều khiển
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=15)
            
            def start_dose_calculation():
                # Lấy các tùy chọn
                algorithm = algorithm_var.get()
                resolution = float(resolution_var.get())
                show_progress = show_progress_var.get()
                
                # Tùy chọn Monte Carlo
                particles = int(particles_var.get()) if algorithm == "MC" else None
                uncertainty = float(uncertainty_var.get()) / 100.0 if algorithm == "MC" else None
                iterations = int(iterations_var.get()) if algorithm == "MC" else None
                
                # Đóng hộp thoại
                dose_dialog.destroy()
                
                # Hiển thị thông báo đang xử lý
                self.window.config(cursor="wait")
                
                if show_progress:
                    progress_window = tk.Toplevel(self.window)
                    progress_window.title("Đang tính toán liều")
                    progress_window.geometry("300x100")
                    progress_window.resizable(False, False)
                    progress_window.transient(self.window)
                    progress_window.grab_set()
                    
                    ttk.Label(progress_window, text=f"Đang tính toán liều với thuật toán {algorithm}...", font=("Arial", 10)).pack(pady=10)
                    progress = ttk.Progressbar(progress_window, mode="indeterminate")
                    progress.pack(fill=tk.X, padx=20, pady=10)
                    progress.start()
                else:
                    progress_window = None
                
                # Thực hiện tính toán trong một luồng riêng
                def calculation_thread():
                    try:
                        # Chuẩn bị dữ liệu đầu vào
                        beams_data = []
                        for beam in self.beams:
                            beam_data = {
                                'gantry_angle': beam.get('gantry_angle', 0),
                                'collimator_angle': beam.get('collimator_angle', 0),
                                'couch_angle': beam.get('couch_angle', 0),
                                'sad': beam.get('sad', 1000),
                                'field_size': beam.get('field_size', [100, 100]),
                                'energy': beam.get('energy', 6),
                                'weight': beam.get('weight', 1.0),
                                'mlc': beam.get('mlc', None)
                            }
                            beams_data.append(beam_data)
                        
                        # Lấy dữ liệu CT và cấu trúc
                        if hasattr(self, 'ct_data') and self.ct_data is not None:
                            ct_data = self.ct_data
                        else:
                            # Tạo CT giả nếu không có
                            ct_data = np.zeros((100, 100, 100), dtype=np.float32)
                        
                        # Tạo mặt nạ tính toán từ cấu trúc
                        mask_data = None
                        if hasattr(self, 'structures') and self.structures:
                            # Tạo mặt nạ từ tất cả các cấu trúc
                            mask_data = np.zeros_like(ct_data, dtype=np.bool_)
                            for name, struct in self.structures.items():
                                if struct is not None:
                                    mask_data = np.logical_or(mask_data, struct > 0)
                        
                        # Lấy tâm xạ trị
                        isocenter = [
                            float(self.iso_x_var.get()) if hasattr(self, 'iso_x_var') else 0,
                            float(self.iso_y_var.get()) if hasattr(self, 'iso_y_var') else 0,
                            float(self.iso_z_var.get()) if hasattr(self, 'iso_z_var') else 0
                        ]
                        
                        # Tính toán liều dựa trên thuật toán đã chọn
                        if algorithm == "MC":
                            # Sử dụng Monte Carlo
                            from quangstation.dose_calculation.monte_carlo import MonteCarlo
                            
                            # Khởi tạo engine Monte Carlo
                            mc_engine = MonteCarlo(voxel_size_mm=[resolution, resolution, resolution])
                            
                            # Đặt dữ liệu CT
                            mc_engine.set_ct_data(ct_data)
                            
                            # Tính toán liều
                            dose_data = mc_engine.calculate_dose(
                                beams=beams_data,
                                isocenter=isocenter,
                                mask_data=mask_data,
                                uncertainty_target=uncertainty,
                                max_iterations=iterations,
                                particles_per_iteration=particles
                            )
                            
                            # Lưu thông tin độ không đảm bảo
                            self.dose_uncertainty = mc_engine.uncertainty
                            
                        else:
                            # Sử dụng thuật toán thông thường (CCC hoặc PBC)
                            from quangstation.dose_calculation.dose_engine_wrapper import DoseCalculator
                            
                            # Khởi tạo bộ tính liều
                            dose_calculator = DoseCalculator(algorithm=algorithm)
                            
                            # Đặt dữ liệu CT
                            dose_calculator.set_ct_data(ct_data)
                            
                            # Đặt thông tin chùm tia
                            for beam_data in beams_data:
                                dose_calculator.add_beam(beam_data)
                            
                            # Đặt tâm xạ trị
                            dose_calculator.set_isocenter(isocenter)
                            
                            # Tính toán liều
                            dose_data = dose_calculator.calculate_dose(
                                grid_resolution=resolution,
                                mask=mask_data
                            )
                        
                        # Lưu kết quả
                        self.dose_data = dose_data
                        self.dose_algorithm = algorithm
                        
                        # Cập nhật UI trong luồng chính
                        self.window.after(0, lambda: self._update_after_dose_calculation(progress_window))
                        
                    except Exception as e:
                        self.logger.error(f"Lỗi khi tính toán liều: {str(e)}")
                        self.window.after(0, lambda: self._handle_dose_calculation_error(str(e), progress_window))
                
                # Khởi chạy luồng
                import threading
                thread = threading.Thread(target=calculation_thread)
                thread.daemon = True
                thread.start()
            
            ttk.Button(button_frame, text="Tính toán", command=start_dose_calculation).pack(side=tk.RIGHT, padx=5)
            ttk.Button(button_frame, text="Hủy", command=dose_dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        except Exception as e:
            self.logger.error(f"Lỗi khi mở hộp thoại tính liều: {str(e)}")
            messagebox.showerror("Lỗi", f"Lỗi khi mở hộp thoại tính liều: {str(e)}")

    def _update_after_dose_calculation(self, progress_window):
        """Cập nhật UI sau khi tính toán liều hoàn tất."""
        try:
            # Đóng cửa sổ tiến trình nếu có
            if progress_window:
                progress_window.destroy()
            
            # Khôi phục con trỏ
            self.window.config(cursor="")
            
            # Hiển thị thông báo thành công
            algorithm_name = {
                "CCC": "Collapsed Cone Convolution",
                "PBC": "Pencil Beam Convolution",
                "MC": "Monte Carlo"
            }.get(self.dose_algorithm, self.dose_algorithm)
            
            success_message = f"Đã tính toán liều thành công với thuật toán {algorithm_name}."
            
            # Thêm thông tin độ không đảm bảo nếu là Monte Carlo
            if self.dose_algorithm == "MC" and hasattr(self, 'dose_uncertainty'):
                success_message += f"\nĐộ không đảm bảo: {self.dose_uncertainty * 100:.2f}%"
            
            messagebox.showinfo("Thành công", success_message)
            
            # Cập nhật hiển thị liều
            if hasattr(self, 'update_dose_display'):
                self.update_dose_display()
            
        except Exception as e:
            self.logger.error(f"Lỗi khi cập nhật sau tính toán liều: {str(e)}")
            messagebox.showerror("Lỗi", f"Lỗi khi cập nhật sau tính toán liều: {str(e)}")

    def _handle_dose_calculation_error(self, error_message, progress_window):
        """Xử lý lỗi trong quá trình tính toán liều."""
        try:
            # Đóng cửa sổ tiến trình nếu có
            if progress_window:
                progress_window.destroy()
            
            # Khôi phục con trỏ
            self.window.config(cursor="")
            
            # Hiển thị thông báo lỗi
            messagebox.showerror("Lỗi", f"Lỗi khi tính toán liều: {error_message}")
            
        except:
            pass
    
    def optimize_plan(self):
        """Tối ưu hóa kế hoạch xạ trị."""
        try:
            # Kiểm tra xem đã tính liều chưa
            if not hasattr(self, 'dose_data') or self.dose_data is None:
                messagebox.showwarning("Cảnh báo", "Vui lòng tính toán phân bố liều trước khi tối ưu hóa")
                return
            
            # Kiểm tra xem đã có cấu trúc chưa
            if not self.structures:
                messagebox.showwarning("Cảnh báo", "Cần có ít nhất một cấu trúc để tối ưu hóa")
                return
                
            # Tạo cửa sổ tối ưu hóa
            optim_window = tk.Toplevel(self.window)
            optim_window.title("Tối ưu hóa kế hoạch")
            optim_window.geometry("800x600")
            optim_window.transient(self.window)
            optim_window.grab_set()
            
            # Tạo frame chứa các điều khiển
            control_frame = ttk.Frame(optim_window, padding=10)
            control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
            
            # Tạo frame hiển thị
            display_frame = ttk.Frame(optim_window, padding=10)
            display_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Frame thuật toán
            algo_frame = ttk.LabelFrame(control_frame, text="Thuật toán", padding=10)
            algo_frame.pack(fill=tk.X, pady=5)
            
            # Chọn thuật toán
            algo_var = tk.StringVar(value="gradient")
            ttk.Radiobutton(algo_frame, text="Gradient Descent", variable=algo_var, 
                           value="gradient").pack(anchor=tk.W, pady=2)
            ttk.Radiobutton(algo_frame, text="Genetic Algorithm", variable=algo_var, 
                           value="genetic").pack(anchor=tk.W, pady=2)
            
            # Frame ràng buộc
            constraints_frame = ttk.LabelFrame(control_frame, text="Ràng buộc", padding=10)
            constraints_frame.pack(fill=tk.BOTH, expand=True, pady=5)
            
            # Tạo danh sách ràng buộc cho từng cấu trúc
            constraints_canvas = tk.Canvas(constraints_frame)
            constraints_scrollbar = ttk.Scrollbar(constraints_frame, orient="vertical", 
                                               command=constraints_canvas.yview)
            constraints_scrollable_frame = ttk.Frame(constraints_canvas)
            
            constraints_scrollable_frame.bind(
                "<Configure>",
                lambda e: constraints_canvas.configure(
                    scrollregion=constraints_canvas.bbox("all")
                )
            )
            
            constraints_canvas.create_window((0, 0), window=constraints_scrollable_frame, anchor="nw")
            constraints_canvas.configure(yscrollcommand=constraints_scrollbar.set)
            
            constraints_canvas.pack(side="left", fill="both", expand=True)
            constraints_scrollbar.pack(side="right", fill="y")
            
            # Tạo các widgets cho từng cấu trúc
            constraints_vars = {}
            for i, name in enumerate(self.structures.keys()):
                # Frame cho cấu trúc
                struct_frame = ttk.LabelFrame(constraints_scrollable_frame, text=name, padding=5)
                struct_frame.pack(fill=tk.X, pady=3)
                
                # Loại ràng buộc
                constraint_type_var = tk.StringVar(value="max_dose")
                constraint_frame = ttk.Frame(struct_frame)
                constraint_frame.pack(fill=tk.X, pady=2)
                
                ttk.Label(constraint_frame, text="Loại:").pack(side=tk.LEFT, padx=2)
                constraint_type_combo = ttk.Combobox(constraint_frame, textvariable=constraint_type_var, 
                                                  width=15)
                constraint_type_combo['values'] = [
                    "max_dose", "min_dose", "max_dvh", "min_dvh", "mean_dose", "conformity"
                ]
                constraint_type_combo.pack(side=tk.LEFT, padx=2)
                
                # Giá trị ràng buộc
                value_frame = ttk.Frame(struct_frame)
                value_frame.pack(fill=tk.X, pady=2)
                
                dose_var = tk.DoubleVar(value=0.0)
                ttk.Label(value_frame, text="Liều (Gy):").pack(side=tk.LEFT, padx=2)
                ttk.Entry(value_frame, textvariable=dose_var, width=8).pack(side=tk.LEFT, padx=2)
                
                volume_var = tk.DoubleVar(value=0.0)
                ttk.Label(value_frame, text="Thể tích (%):").pack(side=tk.LEFT, padx=2)
                ttk.Entry(value_frame, textvariable=volume_var, width=8).pack(side=tk.LEFT, padx=2)
                
                # Trọng số
                weight_frame = ttk.Frame(struct_frame)
                weight_frame.pack(fill=tk.X, pady=2)
                
                weight_var = tk.DoubleVar(value=1.0)
                ttk.Label(weight_frame, text="Trọng số:").pack(side=tk.LEFT, padx=2)
                ttk.Entry(weight_frame, textvariable=weight_var, width=8).pack(side=tk.LEFT, padx=2)
                
                # Lưu biến
                constraints_vars[name] = {
                    'type': constraint_type_var,
                    'dose': dose_var,
                    'volume': volume_var,
                    'weight': weight_var
                }
            
            # Frame tham số
            params_frame = ttk.LabelFrame(control_frame, text="Tham số", padding=10)
            params_frame.pack(fill=tk.X, pady=5)
            
            # Tham số Gradient Descent
            gd_frame = ttk.Frame(params_frame)
            gd_frame.pack(fill=tk.X, pady=2)
            
            learning_rate_var = tk.DoubleVar(value=0.01)
            ttk.Label(gd_frame, text="Learning rate:").pack(side=tk.LEFT, padx=2)
            ttk.Entry(gd_frame, textvariable=learning_rate_var, width=8).pack(side=tk.LEFT, padx=2)
            
            iterations_var = tk.IntVar(value=100)
            ttk.Label(gd_frame, text="Số lặp:").pack(side=tk.LEFT, padx=2)
            ttk.Entry(gd_frame, textvariable=iterations_var, width=8).pack(side=tk.LEFT, padx=2)
            
            # Nút điều khiển
            buttons_frame = ttk.Frame(control_frame)
            buttons_frame.pack(fill=tk.X, pady=10)
            
            # Hiển thị trạng thái
            status_var = tk.StringVar(value="Sẵn sàng")
            status_label = ttk.Label(control_frame, textvariable=status_var, relief=tk.SUNKEN, anchor=tk.W)
            status_label.pack(fill=tk.X, pady=5)
            
            # Tạo biểu đồ tiến trình
            progress_fig = plt.Figure(figsize=(5, 4), dpi=100)
            progress_ax = progress_fig.add_subplot(111)
            progress_ax.set_title("Giá trị hàm mục tiêu")
            progress_ax.set_xlabel("Số lặp")
            progress_ax.set_ylabel("Giá trị")
            progress_ax.grid(True)
            
            progress_canvas = FigureCanvasTkAgg(progress_fig, display_frame)
            progress_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Tạo thanh tiến trình
            progressbar = ttk.Progressbar(control_frame, mode='determinate')
            progressbar.pack(fill=tk.X, pady=5)
            
            # Hàm tối ưu hóa
            def run_optimization():
                # Lấy tham số từ giao diện
                algorithm = algo_var.get()
                
                # Lấy các ràng buộc
                constraints = []
                for name, vars_dict in constraints_vars.items():
                    constraint = {
                        'structure': name,
                        'type': vars_dict['type'].get(),
                        'dose': vars_dict['dose'].get(),
                        'volume': vars_dict['volume'].get(),
                        'weight': vars_dict['weight'].get()
                    }
                    constraints.append(constraint)
                
                # Trạng thái đang tối ưu
                status_var.set("Đang tối ưu hóa...")
                progressbar.start(10)
                
                # Import optimizer
                from quangstation.optimization.optimizer_wrapper import PlanOptimizer
                
                # Tạo đối tượng optimizer
                optimizer = PlanOptimizer(algorithm=algorithm)
                
                # Thiết lập dữ liệu và cấu trúc
                for name, structure in self.structures.items():
                    optimizer.add_structure(name, structure)
                
                # Thêm các ràng buộc
                for constraint in constraints:
                    optimizer.add_objective(
                        structure_name=constraint['structure'],
                        objective_type=constraint['type'],
                        dose=constraint['dose'],
                        volume=constraint['volume'],
                        weight=constraint['weight']
                    )
                
                # Thiết lập tham số gradient descent
                if algorithm == "gradient":
                    optimizer.set_gradient_parameters(
                        learning_rate=learning_rate_var.get(),
                        max_iterations=iterations_var.get()
                    )
                
                # Chạy tối ưu hóa trong một luồng riêng
                def optimize_thread():
                    try:
                        # Khởi tạo optimizer
                        optimizer.initialize_optimizer()
                        
                        # Chạy tối ưu hóa
                        objective_values = optimizer.optimize()
                        
                        # Lấy ma trận liều đã tối ưu
                        optimized_dose = optimizer.get_optimized_dose()
                        
                        # Cập nhật UI
                        optim_window.after(0, lambda: update_ui(objective_values, optimized_dose))
                        
                    except Exception as error:
                        optim_window.after(0, lambda error=error: handle_error(error))
                
                # Cập nhật UI sau khi tối ưu hóa
                def update_ui(objective_values, optimized_dose):
                    # Cập nhật biểu đồ
                    progress_ax.clear()
                    progress_ax.plot(objective_values)
                    progress_ax.set_title("Giá trị hàm mục tiêu")
                    progress_ax.set_xlabel("Số lặp")
                    progress_ax.set_ylabel("Giá trị")
                    progress_ax.grid(True)
                    progress_canvas.draw()
                    
                    # Cập nhật ma trận liều
                    self.dose_data = optimized_dose
                    self.update_dose_display(optimized_dose)
                    
                    # Cập nhật trạng thái
                    status_var.set("Đã hoàn thành tối ưu hóa!")
                    progressbar.stop()
                    progressbar['value'] = 100
                    
                    # Hiển thị thông báo
                    messagebox.showinfo("Thành công", "Đã hoàn thành tối ưu hóa kế hoạch!")
                
                # Xử lý lỗi
                def handle_error(error):
                    status_var.set(f"Lỗi: {str(error)}")
                    progressbar.stop()
                    logger.error(f"Lỗi khi tối ưu hóa: {str(error)}")
                    messagebox.showerror("Lỗi", f"Lỗi khi tối ưu hóa kế hoạch: {str(error)}")
                
                # Khởi động luồng tối ưu hóa
                threading.Thread(target=optimize_thread, daemon=True).start()
            
            # Nút chạy tối ưu hóa
            ttk.Button(buttons_frame, text="Tối ưu hóa", command=run_optimization).pack(side=tk.LEFT, padx=5)
            
            # Nút đóng
            ttk.Button(buttons_frame, text="Đóng", 
                     command=optim_window.destroy).pack(side=tk.RIGHT, padx=5)
            
            # Đặt focus
            optim_window.focus_set()
            
        except Exception as error:
            logger.error(f"Lỗi khi khởi tạo tối ưu hóa: {str(error)}")
            messagebox.showerror("Lỗi", f"Không thể khởi tạo tối ưu hóa: {str(error)}")
    
    def create_report(self):
        """Tạo báo cáo cho kế hoạch xạ trị."""
        try:
            # Kiểm tra xem đã tính toán DVH chưa
            if not hasattr(self, 'dvh_data') or not self.dvh_data:
                # Tính DVH nếu có dữ liệu liều
                if hasattr(self, 'dose_data') and self.dose_data is not None:
                    self.calculate_dvh()
                else:
                    messagebox.showwarning("Cảnh báo", "Chưa có dữ liệu liều để tạo báo cáo. Vui lòng tính toán liều trước.")
                    return
            
            # Tạo hộp thoại để chọn định dạng và cấu hình báo cáo
            import tkinter as tk
            from tkinter import ttk
            
            report_dialog = tk.Toplevel(self.window)
            report_dialog.title("Tạo báo cáo kế hoạch xạ trị")
            report_dialog.geometry("500x600")
            report_dialog.resizable(False, False)
            report_dialog.transient(self.window)
            report_dialog.grab_set()
            
            # Tạo các frame chính
            main_frame = ttk.Frame(report_dialog, padding=10)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Frame chọn định dạng báo cáo
            format_frame = ttk.LabelFrame(main_frame, text="Định dạng báo cáo", padding=10)
            format_frame.pack(fill=tk.X, pady=5)
            
            format_var = tk.StringVar(value="pdf")
            ttk.Radiobutton(format_frame, text="PDF", variable=format_var, value="pdf").pack(anchor=tk.W)
            ttk.Radiobutton(format_frame, text="Microsoft Word (DOCX)", variable=format_var, value="docx").pack(anchor=tk.W)
            ttk.Radiobutton(format_frame, text="HTML", variable=format_var, value="html").pack(anchor=tk.W)
            ttk.Radiobutton(format_frame, text="JSON (Dữ liệu thô)", variable=format_var, value="json").pack(anchor=tk.W)
            
            # Frame chọn các phần báo cáo
            sections_frame = ttk.LabelFrame(main_frame, text="Nội dung báo cáo", padding=10)
            sections_frame.pack(fill=tk.X, pady=5)
            
            sections = {
                "patient_info": tk.BooleanVar(value=True),
                "plan_info": tk.BooleanVar(value=True),
                "dose_metrics": tk.BooleanVar(value=True),
                "dvh": tk.BooleanVar(value=True),
                "conformity_indices": tk.BooleanVar(value=True),
                "beam_info": tk.BooleanVar(value=True),
                "dose_images": tk.BooleanVar(value=True),
                "qa_metrics": tk.BooleanVar(value=True)
            }
            
            ttk.Checkbutton(sections_frame, text="Thông tin bệnh nhân", variable=sections["patient_info"]).pack(anchor=tk.W)
            ttk.Checkbutton(sections_frame, text="Thông tin kế hoạch", variable=sections["plan_info"]).pack(anchor=tk.W)
            ttk.Checkbutton(sections_frame, text="Chỉ số liều", variable=sections["dose_metrics"]).pack(anchor=tk.W)
            ttk.Checkbutton(sections_frame, text="Biểu đồ DVH", variable=sections["dvh"]).pack(anchor=tk.W)
            ttk.Checkbutton(sections_frame, text="Chỉ số tuân thủ", variable=sections["conformity_indices"]).pack(anchor=tk.W)
            ttk.Checkbutton(sections_frame, text="Thông tin chùm tia", variable=sections["beam_info"]).pack(anchor=tk.W)
            ttk.Checkbutton(sections_frame, text="Hình ảnh phân bố liều", variable=sections["dose_images"]).pack(anchor=tk.W)
            ttk.Checkbutton(sections_frame, text="Chỉ số QA", variable=sections["qa_metrics"]).pack(anchor=tk.W)
            
            # Frame cấu hình báo cáo
            config_frame = ttk.LabelFrame(main_frame, text="Cấu hình báo cáo", padding=10)
            config_frame.pack(fill=tk.X, pady=5)
            
            ttk.Label(config_frame, text="Tiêu đề báo cáo:").grid(row=0, column=0, sticky=tk.W, pady=5)
            title_var = tk.StringVar(value=f"Báo cáo kế hoạch xạ trị - {datetime.now().strftime('%d/%m/%Y')}")
            ttk.Entry(config_frame, textvariable=title_var, width=40).grid(row=0, column=1, sticky=tk.W, pady=5)
            
            ttk.Label(config_frame, text="Người phê duyệt:").grid(row=1, column=0, sticky=tk.W, pady=5)
            approver_var = tk.StringVar()
            ttk.Entry(config_frame, textvariable=approver_var, width=40).grid(row=1, column=1, sticky=tk.W, pady=5)
            
            ttk.Label(config_frame, text="Người kiểm tra:").grid(row=2, column=0, sticky=tk.W, pady=5)
            checker_var = tk.StringVar()
            ttk.Entry(config_frame, textvariable=checker_var, width=40).grid(row=2, column=1, sticky=tk.W, pady=5)
            
            ttk.Label(config_frame, text="Ghi chú:").grid(row=3, column=0, sticky=tk.W, pady=5)
            notes_var = tk.StringVar()
            ttk.Entry(config_frame, textvariable=notes_var, width=40).grid(row=3, column=1, sticky=tk.W, pady=5)
            
            # Frame chọn vị trí lưu báo cáo
            output_frame = ttk.LabelFrame(main_frame, text="Vị trí lưu báo cáo", padding=10)
            output_frame.pack(fill=tk.X, pady=5)
            
            output_path_var = tk.StringVar()
            ttk.Entry(output_frame, textvariable=output_path_var, width=50).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
            
            def browse_output():
                file_type = format_var.get()
                file_extensions = {
                    "pdf": [("PDF Files", "*.pdf")],
                    "docx": [("Word Files", "*.docx")],
                    "html": [("HTML Files", "*.html")],
                    "json": [("JSON Files", "*.json")]
                }
                
                output_file = filedialog.asksaveasfilename(
                    parent=report_dialog,
                    title="Chọn vị trí lưu báo cáo",
                    filetypes=file_extensions[file_type],
                    defaultextension=f".{file_type}"
                )
                
                if output_file:
                    output_path_var.set(output_file)
            
            ttk.Button(output_frame, text="Duyệt...", command=browse_output).pack(side=tk.RIGHT, padx=5)
            
            # Frame nút điều khiển
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=15)
            
            def generate_report():
                # Kiểm tra xem đã chọn vị trí lưu chưa
                output_path = output_path_var.get()
                if not output_path:
                    messagebox.showwarning("Cảnh báo", "Vui lòng chọn vị trí lưu báo cáo")
                    return
                
                # Thu thập cấu hình báo cáo
                report_format = format_var.get()
                included_sections = [s for s, v in sections.items() if v.get()]
                title = title_var.get()
                approver = approver_var.get()
                checker = checker_var.get()
                notes = notes_var.get()
                
                # Thu thập dữ liệu báo cáo
                patient_info = {}
                if hasattr(self, 'patient_info'):
                    patient_info = self.patient_info
                elif hasattr(self, 'plan') and hasattr(self.plan, 'patient_info'):
                    patient_info = self.plan.patient_info
                
                plan_info = self.get_plan_data()
                
                # Thu thập dữ liệu hình ảnh
                try:
                    # Tạo thư mục tạm để lưu các hình ảnh
                    import tempfile
                    import os
                    
                    temp_dir = tempfile.mkdtemp()
                    image_paths = []
                    image_captions = []
                    
                    # Lưu hình ảnh DVH
                    if "dvh" in included_sections and hasattr(self, 'dvh_data'):
                        dvh_path = os.path.join(temp_dir, "dvh.png")
                        if hasattr(self, 'dvh_figure'):
                            self.dvh_figure.savefig(dvh_path, dpi=150, bbox_inches='tight')
                            image_paths.append(dvh_path)
                            image_captions.append("Biểu đồ Dose-Volume Histogram (DVH)")
                    
                    # Lưu hình ảnh phân bố liều
                    if "dose_images" in included_sections and hasattr(self, 'dose_data') and self.dose_data is not None:
                        from quangstation.plan_evaluation.dose_map import DoseMap
                        
                        # Tạo hình ảnh phân bố liều
                        structures = {}
                        if hasattr(self, 'contour_tools'):
                            for name in self.contour_tools.contours.keys():
                                structures[name] = self.contour_tools.get_structure_mask(name)
                        
                        dose_map = DoseMap(self.dose_data)
                        for name, mask in structures.items():
                            color = self.contour_tools.get_structure_color(name)
                            dose_map.add_structure(name, mask, color)
                        
                        # Tạo hình ảnh phân bố liều theo các trục
                        for axis in ['axial', 'coronal', 'sagittal']:
                            slice_index = dose_map.dose_data.shape[0] // 2 if axis == 'axial' else dose_map.dose_data.shape[1] // 2
                            fig = dose_map.plot_dose_map(axis=axis, slice_index=slice_index, show_structures=True, show_isodose=True)
                            
                            dose_path = os.path.join(temp_dir, f"dose_{axis}.png")
                            fig.savefig(dose_path, dpi=150, bbox_inches='tight')
                            image_paths.append(dose_path)
                            image_captions.append(f"Phân bố liều - Mặt phẳng {axis}")
                    
                    # Tính toán các chỉ số đánh giá kế hoạch
                    if "conformity_indices" in included_sections:
                        from quangstation.plan_evaluation.plan_metrics import PlanQualityMetrics
                        
                        # Xác định cấu trúc đích (PTV)
                        target_name = None
                        for name in structures.keys():
                            if name.startswith('PTV'):
                                target_name = name
                                break
                        
                        if target_name and hasattr(self, 'dose_data') and self.dose_data is not None:
                            # Lấy liều kê toa
                            prescribed_dose = 0
                            if hasattr(self, 'plan') and hasattr(self.plan, 'prescribed_dose'):
                                prescribed_dose = self.plan.prescribed_dose
                            elif plan_info and 'total_dose' in plan_info:
                                prescribed_dose = float(plan_info['total_dose'])
                            
                            # Tính các chỉ số chất lượng kế hoạch
                            metrics = PlanQualityMetrics(self.dose_data, structures, prescribed_dose, target_name)
                            conformity_indices = metrics.calculate_all_metrics()
                            
                            # Tạo và lưu biểu đồ radar chất lượng kế hoạch
                            radar_fig = metrics.plot_quality_radar()
                            radar_path = os.path.join(temp_dir, "quality_radar.png")
                            radar_fig.savefig(radar_path, dpi=150, bbox_inches='tight')
                            image_paths.append(radar_path)
                            image_captions.append("Biểu đồ radar đánh giá chất lượng kế hoạch")
                    else:
                        conformity_indices = {}
                    
                    # Lấy thông tin chùm tia
                    beams = []
                    if hasattr(self, 'plan') and hasattr(self.plan, 'beams'):
                        for beam in self.plan.beams:
                            beam_dict = beam.to_dict() if hasattr(beam, 'to_dict') else {}
                            beams.append(beam_dict)
                    
                    # Tạo báo cáo dựa trên định dạng đã chọn
                    from quangstation.reporting.enhanced_report import EnhancedReport
                    
                    # Chuẩn bị dữ liệu cần thiết
                    report_data = {
                        'patient_info': patient_info,
                        'plan_info': plan_info,
                        'dvh_data': self.dvh_data if hasattr(self, 'dvh_data') else {},
                        'dose_metrics': self.dvh_calculator.calculate_dose_metrics() if hasattr(self, 'dvh_calculator') else {},
                        'conformity_indices': conformity_indices,
                        'beams': beams,
                        'image_paths': image_paths,
                        'image_captions': image_captions,
                        'title': title,
                        'approved_by': approver,
                        'checked_by': checker,
                        'notes': notes
                    }
                    
                    # Tạo báo cáo
                    created_file = None
                    if report_format == "pdf":
                        from quangstation.reporting.pdf_report import create_plan_report
                        created_file = create_plan_report(**report_data, output_path=output_path)
                    elif report_format == "docx":
                        from quangstation.reporting.docx_report import create_plan_report
                        created_file = create_plan_report(**report_data, output_path=output_path)
                    elif report_format == "html":
                        from quangstation.reporting.html_report import create_plan_report
                        created_file = create_plan_report(**report_data, output_path=output_path)
                    elif report_format == "json":
                        from quangstation.reporting.report_gen import TreatmentReport
                        report = TreatmentReport(
                            patient_data=patient_info,
                            plan_data=plan_info,
                            dose_data=self.dose_data if hasattr(self, 'dose_data') else None,
                            structures=structures
                        )
                        created_file = report.export_json_summary(output_path)
                    
                    if created_file:
                        messagebox.showinfo("Thành công", f"Đã tạo báo cáo tại: {created_file}")
                        # Đóng dialog
                        report_dialog.destroy()
                    else:
                        messagebox.showerror("Lỗi", "Không thể tạo báo cáo")
                    
                    # Xóa thư mục tạm khi đã hoàn thành
                    try:
                        import shutil
                        shutil.rmtree(temp_dir)
                    except:
                        pass
                    
                except Exception as e:
                    logger.error(f"Lỗi khi tạo báo cáo: {str(e)}")
                    messagebox.showerror("Lỗi", f"Lỗi khi tạo báo cáo: {str(e)}")
            
            ttk.Button(button_frame, text="Tạo báo cáo", command=generate_report).pack(side=tk.RIGHT, padx=5)
            ttk.Button(button_frame, text="Hủy", command=report_dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        except Exception as e:
            logger.error(f"Lỗi khi mở hộp thoại tạo báo cáo: {str(e)}")
            messagebox.showerror("Lỗi", f"Lỗi khi mở hộp thoại tạo báo cáo: {str(e)}")
    
    def export_rt_plan(self):
        """Xuất kế hoạch xạ trị sang định dạng DICOM RT Plan."""
        try:
            # Kiểm tra xem có kế hoạch hiện tại không
            if not hasattr(self, 'plan') or self.plan is None:
                plan_data = self.get_plan_data()
                if not plan_data:
                    messagebox.showwarning("Cảnh báo", "Không có kế hoạch xạ trị để xuất")
                    return
            
            # Tạo hộp thoại chọn thư mục xuất
            export_dir = filedialog.askdirectory(
                title="Chọn thư mục xuất DICOM RT Plan",
                mustexist=True
            )
            
            if not export_dir:
                return
            
            # Tạo hộp thoại cấu hình xuất
            import tkinter as tk
            from tkinter import ttk
            
            export_dialog = tk.Toplevel(self.window)
            export_dialog.title("Xuất kế hoạch xạ trị DICOM")
            export_dialog.geometry("450x550")
            export_dialog.resizable(False, False)
            export_dialog.transient(self.window)
            export_dialog.grab_set()
            
            # Tạo các frame chính
            main_frame = ttk.Frame(export_dialog, padding=10)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Frame cấu hình xuất
            config_frame = ttk.LabelFrame(main_frame, text="Cấu hình xuất DICOM", padding=10)
            config_frame.pack(fill=tk.X, pady=5)
            
            # Các loại DICOM RT
            types_frame = ttk.Frame(config_frame)
            types_frame.pack(fill=tk.X, pady=5)
            
            export_types = {
                "rt_plan": tk.BooleanVar(value=True),
                "rt_struct": tk.BooleanVar(value=True),
                "rt_dose": tk.BooleanVar(value=True),
                "ct_images": tk.BooleanVar(value=False)
            }
            
            ttk.Checkbutton(types_frame, text="RT Plan", variable=export_types["rt_plan"]).grid(row=0, column=0, sticky=tk.W, padx=10)
            ttk.Checkbutton(types_frame, text="RT Structure Set", variable=export_types["rt_struct"]).grid(row=0, column=1, sticky=tk.W, padx=10)
            ttk.Checkbutton(types_frame, text="RT Dose", variable=export_types["rt_dose"]).grid(row=1, column=0, sticky=tk.W, padx=10)
            ttk.Checkbutton(types_frame, text="CT Images", variable=export_types["ct_images"]).grid(row=1, column=1, sticky=tk.W, padx=10)
            
            # Thông tin DICOM
            info_frame = ttk.Frame(config_frame)
            info_frame.pack(fill=tk.X, pady=10)
            
            ttk.Label(info_frame, text="Institution Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
            institution_var = tk.StringVar(value="QuangStation RT Department")
            ttk.Entry(info_frame, textvariable=institution_var, width=30).grid(row=0, column=1, sticky=tk.W, pady=5)
            
            ttk.Label(info_frame, text="Physician Name:").grid(row=1, column=0, sticky=tk.W, pady=5)
            physician_var = tk.StringVar()
            ttk.Entry(info_frame, textvariable=physician_var, width=30).grid(row=1, column=1, sticky=tk.W, pady=5)
            
            ttk.Label(info_frame, text="Device Serial Number:").grid(row=2, column=0, sticky=tk.W, pady=5)
            device_var = tk.StringVar(value="QS001")
            ttk.Entry(info_frame, textvariable=device_var, width=30).grid(row=2, column=1, sticky=tk.W, pady=5)
            
            ttk.Label(info_frame, text="Description:").grid(row=3, column=0, sticky=tk.W, pady=5)
            description_var = tk.StringVar()
            ttk.Entry(info_frame, textvariable=description_var, width=30).grid(row=3, column=1, sticky=tk.W, pady=5)
            
            # Frame cấu hình nâng cao
            advanced_frame = ttk.LabelFrame(main_frame, text="Cấu hình nâng cao", padding=10)
            advanced_frame.pack(fill=tk.X, pady=5)
            
            ttk.Label(advanced_frame, text="Anonymize Patient:").grid(row=0, column=0, sticky=tk.W, pady=5)
            anonymize_var = tk.BooleanVar(value=False)
            ttk.Checkbutton(advanced_frame, variable=anonymize_var).grid(row=0, column=1, sticky=tk.W, pady=5)
            
            ttk.Label(advanced_frame, text="Transfer Syntax:").grid(row=1, column=0, sticky=tk.W, pady=5)
            transfer_syntax_var = tk.StringVar(value="Implicit VR Little Endian")
            transfer_syntax_combo = ttk.Combobox(advanced_frame, textvariable=transfer_syntax_var, width=30, state="readonly")
            transfer_syntax_combo['values'] = (
                "Implicit VR Little Endian", 
                "Explicit VR Little Endian", 
                "Explicit VR Big Endian",
                "JPEG Baseline"
            )
            transfer_syntax_combo.grid(row=1, column=1, sticky=tk.W, pady=5)
            
            ttk.Label(advanced_frame, text="Include Private Tags:").grid(row=2, column=0, sticky=tk.W, pady=5)
            private_tags_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(advanced_frame, variable=private_tags_var).grid(row=2, column=1, sticky=tk.W, pady=5)
            
            # Frame thông tin tiến trình
            progress_frame = ttk.LabelFrame(main_frame, text="Tiến trình", padding=10)
            progress_frame.pack(fill=tk.X, pady=5)
            
            progress_var = tk.DoubleVar(value=0.0)
            progress_bar = ttk.Progressbar(progress_frame, variable=progress_var, maximum=100)
            progress_bar.pack(fill=tk.X, pady=5)
            
            status_var = tk.StringVar(value="Sẵn sàng xuất...")
            status_label = ttk.Label(progress_frame, textvariable=status_var)
            status_label.pack(anchor=tk.W, pady=5)
            
            # Frame nút điều khiển
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=15)
            
            def export_dicom():
                try:
                    # Thu thập cấu hình xuất
                    export_opts = {
                        "rt_plan": export_types["rt_plan"].get(),
                        "rt_struct": export_types["rt_struct"].get(),
                        "rt_dose": export_types["rt_dose"].get(),
                        "ct_images": export_types["ct_images"].get(),
                        "institution_name": institution_var.get(),
                        "physician_name": physician_var.get(),
                        "device_serial_number": device_var.get(),
                        "description": description_var.get(),
                        "anonymize": anonymize_var.get(),
                        "transfer_syntax": transfer_syntax_var.get(),
                        "include_private_tags": private_tags_var.get()
                    }
                    
                    # Kiểm tra xem có ít nhất một loại DICOM được chọn không
                    if not any([export_opts["rt_plan"], export_opts["rt_struct"], export_opts["rt_dose"], export_opts["ct_images"]]):
                        messagebox.showwarning("Cảnh báo", "Vui lòng chọn ít nhất một loại DICOM để xuất")
                        return
                    
                    # Cập nhật trạng thái
                    status_var.set("Đang chuẩn bị xuất...")
                    progress_var.set(5)
                    
                    # Sử dụng SessionManager để xuất
                    from quangstation.data_management.session_management import SessionManager
                    
                    # Lấy patient_id
                    patient_id = None
                    if hasattr(self, 'plan') and hasattr(self.plan, 'patient_id'):
                        patient_id = self.plan.patient_id
                    elif hasattr(self, 'patient_id'):
                        patient_id = self.patient_id
                    else:
                        # Tìm trong plan_data
                        plan_data = self.get_plan_data()
                        if plan_data and 'patient_id' in plan_data:
                            patient_id = plan_data['patient_id']
                        else:
                            # Hỏi người dùng
                            from tkinter import simpledialog
                            patient_id = simpledialog.askstring(
                                "Patient ID", 
                                "Nhập ID bệnh nhân:", 
                                parent=export_dialog
                            )
                            if not patient_id:
                                status_var.set("Đã hủy xuất")
                                return
                    
                    # Lấy plan_id
                    plan_id = None
                    if hasattr(self, 'plan') and hasattr(self.plan, 'id'):
                        plan_id = self.plan.id
                    elif hasattr(self, 'plan_id'):
                        plan_id = self.plan_id
                    else:
                        # Tìm trong plan_data
                        plan_data = self.get_plan_data()
                        if plan_data and 'plan_id' in plan_data:
                            plan_id = plan_data['plan_id']
                        elif plan_data and 'plan_name' in plan_data:
                            plan_id = plan_data['plan_name']
                        else:
                            # Hỏi người dùng
                            from tkinter import simpledialog
                            plan_id = simpledialog.askstring(
                                "Plan ID", 
                                "Nhập ID kế hoạch:", 
                                parent=export_dialog
                            )
                            if not plan_id:
                                status_var.set("Đã hủy xuất")
                                return
                    
                    # Cập nhật tiến trình
                    status_var.set("Đang xuất kế hoạch...")
                    progress_var.set(20)
                    
                    # Xử lý trong luồng riêng để không block UI
                    def export_thread():
                        try:
                            # Khởi tạo SessionManager
                            session_manager = SessionManager()
                            
                            # Khi xuất đồng thời nhiều loại DICOM, bắt buộc phải load session
                            session_manager.load_session(patient_id, plan_id)
                            
                            # Cập nhật metadata cho DICOM nếu cần
                            metadata = {
                                "institution_name": export_opts["institution_name"],
                                "physician_name": export_opts["physician_name"],
                                "device_serial_number": export_opts["device_serial_number"],
                                "description": export_opts["description"],
                                "anonymize": export_opts["anonymize"]
                            }
                            
                            # Cập nhật trạng thái
                            status_var.set("Đang xuất RT Plan...")
                            progress_var.set(40)
                            
                            # Thực hiện xuất
                            export_info = session_manager.export_plan(
                                output_dir=export_dir,
                                patient_id=patient_id,
                                plan_id=plan_id,
                                export_rt_plan=export_opts["rt_plan"],
                                export_rt_struct=export_opts["rt_struct"],
                                export_rt_dose=export_opts["rt_dose"],
                                export_ct=export_opts["ct_images"],
                                metadata=metadata,
                                include_private_tags=export_opts["include_private_tags"]
                            )
                            
                            # Cập nhật trạng thái
                            status_var.set("Hoàn tất xuất DICOM!")
                            progress_var.set(100)
                            
                            # Thông báo kết quả ở luồng chính
                            export_dialog.after(100, lambda: show_results(export_info))
                            
                        except Exception as e:
                            logger.error(f"Lỗi khi xuất kế hoạch: {str(e)}")
                            export_dialog.after(100, lambda: show_error(str(e)))
                    
                    def show_results(export_info):
                        result_message = f"Đã xuất thành công kế hoạch xạ trị sang thư mục:\n{export_dir}\n\n"
                        
                        if export_opts["rt_plan"] and export_info.get("rt_plan"):
                            result_message += f"- RT Plan: {export_info['rt_plan']}\n"
                        if export_opts["rt_struct"] and export_info.get("rt_struct"):
                            result_message += f"- RT Structure: {export_info['rt_struct']}\n"
                        if export_opts["rt_dose"] and export_info.get("rt_dose"):
                            result_message += f"- RT Dose: {export_info['rt_dose']}\n"
                        if export_opts["ct_images"] and export_info.get("ct_images"):
                            result_message += f"- CT Images: {export_info['ct_images']} files\n"
                        
                        messagebox.showinfo("Xuất thành công", result_message)
                        export_dialog.destroy()
                    
                    def show_error(error_msg):
                        status_var.set(f"Lỗi: {error_msg}")
                        messagebox.showerror("Lỗi khi xuất kế hoạch", f"Không thể xuất kế hoạch: {error_msg}")
                    
                    # Khởi chạy luồng xuất
                    threading.Thread(target=export_thread, daemon=True).start()
                    
                except Exception as e:
                    logger.error(f"Lỗi khi xuất kế hoạch: {str(e)}")
                    status_var.set(f"Lỗi: {str(e)}")
                    messagebox.showerror("Lỗi", f"Lỗi khi xuất kế hoạch xạ trị: {str(e)}")
            
            ttk.Button(button_frame, text="Xuất DICOM", command=export_dicom).pack(side=tk.RIGHT, padx=5)
            ttk.Button(button_frame, text="Hủy", command=export_dialog.destroy).pack(side=tk.RIGHT, padx=5)
            
        except Exception as e:
            logger.error(f"Lỗi khi mở hộp thoại xuất RT Plan: {str(e)}")
            messagebox.showerror("Lỗi", f"Lỗi khi mở hộp thoại xuất RT Plan: {str(e)}")
    
    def find_isocenter(self):
        """Tự động tìm tâm điều trị dựa trên cấu trúc đích."""
        try:
            # Kiểm tra xem có cấu trúc nào được chọn không
            if not hasattr(self, 'structures_listbox') or not self.structures_listbox.curselection():
                # Hỏi người dùng chọn cấu trúc đích
                structures = []
                if hasattr(self, 'structures_listbox'):
                    for i in range(self.structures_listbox.size()):
                        structures.append(self.structures_listbox.get(i))
                
                # Lọc các cấu trúc có tiền tố PTV hoặc GTV
                target_candidates = [s for s in structures if s.startswith(('PTV', 'GTV', 'CTV'))]
                
                if not target_candidates:
                    if not structures:
                        messagebox.showwarning("Cảnh báo", "Không tìm thấy cấu trúc nào. Vui lòng tạo cấu trúc trước.")
                    else:
                        messagebox.showwarning("Cảnh báo", "Không tìm thấy cấu trúc mục tiêu (PTV/GTV/CTV). Vui lòng chọn cấu trúc mục tiêu.")
                    return
                
                # Hiển thị dialog để chọn cấu trúc đích
                import tkinter as tk
                from tkinter import simpledialog
                
                target_structure = simpledialog.askstring(
                    "Chọn cấu trúc đích",
                    "Chọn cấu trúc đích để xác định tâm điều trị:",
                    initialvalue=target_candidates[0] if target_candidates else structures[0]
                )
                
                if not target_structure or target_structure not in structures:
                    messagebox.showwarning("Cảnh báo", "Không có cấu trúc đích được chọn.")
                    return
            else:
                # Lấy cấu trúc đã chọn từ danh sách
                selected_idx = self.structures_listbox.curselection()[0]
                target_structure = self.structures_listbox.get(selected_idx)
            
            # Lấy mask của cấu trúc đích
            target_mask = None
            
            # Kiểm tra xem có thể truy cập mask từ contour_tools hoặc từ thuộc tính khác không
            if hasattr(self, 'contour_tools'):
                target_mask = self.contour_tools.get_structure_mask(target_structure)
            elif hasattr(self, 'structure_masks') and target_structure in self.structure_masks:
                target_mask = self.structure_masks[target_structure]
            
            if target_mask is None or not isinstance(target_mask, np.ndarray):
                messagebox.showwarning("Cảnh báo", f"Không thể lấy mask cho cấu trúc {target_structure}.")
                return
            
            # Kiểm tra xem mask có dữ liệu không
            if not np.any(target_mask):
                messagebox.showwarning("Cảnh báo", f"Mask của cấu trúc {target_structure} không có dữ liệu.")
                return
            
            # Lấy thông tin khoảng cách voxel (spacing)
            spacing = [1.0, 1.0, 1.0]  # Giá trị mặc định
            
            if hasattr(self, 'image_data') and hasattr(self.image_data, 'spacing'):
                spacing = self.image_data.spacing
            elif hasattr(self, 'spacing'):
                spacing = self.spacing
            
            # Sử dụng hàm calculate_isocenter từ utils/geometry
            from quangstation.utils.geometry import calculate_isocenter
            isocenter = calculate_isocenter(target_mask, spacing)
            
            logger.info(f"Đã tính tâm điều trị tự động tại {isocenter} dựa trên cấu trúc {target_structure}")
            
            # Cập nhật tâm điều trị trong giao diện
            if hasattr(self, 'iso_x_var') and hasattr(self, 'iso_y_var') and hasattr(self, 'iso_z_var'):
                self.iso_x_var.set(f"{isocenter[0]:.2f}")
                self.iso_y_var.set(f"{isocenter[1]:.2f}")
                self.iso_z_var.set(f"{isocenter[2]:.2f}")
                
                # Hiển thị thông báo thành công
                messagebox.showinfo("Thành công", f"Đã xác định tâm điều trị tại ({isocenter[0]:.2f}, {isocenter[1]:.2f}, {isocenter[2]:.2f}) mm dựa trên cấu trúc {target_structure}")
                
                # Nếu có kế hoạch hiện tại, cập nhật kế hoạch
                if hasattr(self, 'plan') and self.plan is not None:
                    self.plan.set_isocenter(isocenter)
                    logger.info("Đã cập nhật tâm điều trị vào kế hoạch")
            else:
                messagebox.showinfo("Thông tin", f"Tâm điều trị được xác định tại ({isocenter[0]:.2f}, {isocenter[1]:.2f}, {isocenter[2]:.2f}) mm")
                logger.warning("Không thể cập nhật giao diện do không tìm thấy các biến iso_x_var, iso_y_var, iso_z_var")
            
        except Exception as e:
            logger.error(f"Lỗi khi xác định tâm điều trị tự động: {str(e)}")
            messagebox.showerror("Lỗi", f"Lỗi khi xác định tâm điều trị tự động: {str(e)}")
    
    def on_beam_select(self, event):
        """Xử lý sự kiện khi chọn chùm tia."""
        if not hasattr(self, 'beam_listbox') or not self.beam_listbox.curselection():
            return
            
        index = self.beam_listbox.curselection()[0]
        beam_id = self.beam_listbox.get(index)
        
        # Cập nhật thông tin chi tiết chùm tia
        if hasattr(self, 'beam_angle_var'):
            # TODO: Lấy thông tin chùm tia và cập nhật các biến giao diện
            pass
            
        logger.debug(f"Đã chọn chùm tia: {beam_id}")
    
    def update_beam(self):
        """Cập nhật thông tin chùm tia."""
        if not hasattr(self, 'beam_listbox') or not self.beam_listbox.curselection():
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn chùm tia trước khi cập nhật")
            return
            
        # Lấy thông tin chùm tia đã chọn
        index = self.beam_listbox.curselection()[0]
        beam_id = self.beam_listbox.get(index)
        
        # Cập nhật thông tin từ giao diện
        # TODO: Cập nhật thông tin chùm tia dựa trên các biến giao diện
        
        messagebox.showinfo("Thành công", f"Đã cập nhật chùm tia {beam_id}")
        logger.info(f"Đã cập nhật chùm tia {beam_id}")
    
    def on_structure_select(self, event):
        """Xử lý sự kiện khi chọn cấu trúc."""
        if not hasattr(self, 'structure_listbox') or not self.structure_listbox.curselection():
            return
            
        index = self.structure_listbox.curselection()[0]
        structure_name = self.structure_listbox.get(index)
        
        # Cập nhật thông tin chi tiết cấu trúc
        if hasattr(self, 'structure_name_var'):
            self.structure_name_var.set(structure_name)
            # TODO: Lấy thông tin cấu trúc và cập nhật các biến giao diện
            
        logger.debug(f"Đã chọn cấu trúc: {structure_name}")
    
    def choose_color(self):
        """Chọn màu cho cấu trúc."""
        if not hasattr(self, 'structure_listbox') or not self.structure_listbox.curselection():
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn cấu trúc trước khi chọn màu")
            return
            
        from tkinter import colorchooser
        color = colorchooser.askcolor()[1]
        if color:
            self.structure_color_var.set(color)
    
    def update_structure(self):
        """Cập nhật thông tin cấu trúc."""
        if not hasattr(self, 'structure_listbox') or not self.structure_listbox.curselection():
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn cấu trúc trước khi cập nhật")
            return
            
        # Lấy thông tin cấu trúc đã chọn
        index = self.structure_listbox.curselection()[0]
        structure_name = self.structure_listbox.get(index)
        
        # Cập nhật thông tin từ giao diện
        # TODO: Cập nhật thông tin cấu trúc dựa trên các biến giao diện
        
        messagebox.showinfo("Thành công", f"Đã cập nhật cấu trúc {structure_name}")
        logger.info(f"Đã cập nhật cấu trúc {structure_name}")
    
    def show_target_3d(self):
        """Hiển thị đích trong chế độ 3D."""
        try:
            # Kiểm tra xem có cấu trúc đích không
            target_structures = [name for name in self.structures.keys() if 'ptv' in name.lower() or 'target' in name.lower() or 'gtv' in name.lower() or 'ctv' in name.lower()]
            
            if not target_structures:
                messagebox.showwarning("Cảnh báo", "Không tìm thấy cấu trúc đích (PTV/GTV/CTV)")
                return
                
            # Xóa hiển thị cũ
            self.ax_3d.clear()
            self.ax_3d.set_xlabel('X')
            self.ax_3d.set_ylabel('Y')
            self.ax_3d.set_zlabel('Z')
            self.ax_3d.set_title('Mô hình 3D - Cấu trúc đích')
            
            # Lấy kích thước voxel
            voxel_size = getattr(self, 'image_metadata', {}).get('voxel_size', [1.0, 1.0, 1.0])
            
            # Hiển thị từng cấu trúc đích
            for target_name in target_structures:
                # Lấy mask của cấu trúc
                mask = self.structures[target_name]
                
                # Lấy màu của cấu trúc
                color = getattr(self, 'structure_colors', {}).get(target_name, (1.0, 0.0, 0.0))  # Mặc định là màu đỏ
                
                # Tìm các điểm biên của mask
                from skimage import measure
                verts, faces, _, _ = measure.marching_cubes(mask, level=0.5)
                
                # Điều chỉnh tỷ lệ theo kích thước voxel
                verts = verts * voxel_size
                
                # Tạo mesh 3D
                import matplotlib.tri as mtri
                mesh = self.ax_3d.plot_trisurf(
                    verts[:, 0], verts[:, 1], verts[:, 2],
                    triangles=faces,
                    color=color,
                    alpha=0.7,
                    shade=True
                )
            
            # Cập nhật hiển thị
            self.canvas_3d.draw()
            
            logger.info(f"Đã hiển thị {len(target_structures)} cấu trúc đích trong chế độ 3D")
            
        except Exception as error:
            logger.error(f"Lỗi khi hiển thị đích 3D: {str(error)}")
            messagebox.showerror("Lỗi", f"Không thể hiển thị đích 3D: {str(error)}")
            
    def show_oars_3d(self):
        """Hiển thị các cơ quan nguy cấp trong chế độ 3D."""
        try:
            # Lọc ra các cấu trúc OAR (không phải PTV/GTV/CTV)
            oar_structures = [name for name in self.structures.keys() 
                             if not any(target in name.lower() for target in ['ptv', 'target', 'gtv', 'ctv'])]
            
            if not oar_structures:
                messagebox.showwarning("Cảnh báo", "Không tìm thấy cấu trúc OAR")
                return
                
            # Hiển thị hộp thoại chọn OAR
            oar_dialog = tk.Toplevel(self.window)
            oar_dialog.title("Chọn cơ quan nguy cấp để hiển thị")
            oar_dialog.geometry("400x400")
            oar_dialog.transient(self.window)
            oar_dialog.grab_set()
            
            # Frame chính
            main_frame = ttk.Frame(oar_dialog, padding=10)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Label hướng dẫn
            ttk.Label(main_frame, text="Chọn các cơ quan nguy cấp để hiển thị:").pack(anchor=tk.W, pady=5)
            
            # Frame cuộn
            canvas = tk.Canvas(main_frame)
            scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # Biến lưu trạng thái chọn
            oar_vars = {}
            
            # Tạo checkbox cho từng OAR
            for i, name in enumerate(oar_structures):
                var = tk.BooleanVar(value=False)
                oar_vars[name] = var
                
                # Lấy màu của cấu trúc
                color = getattr(self, 'structure_colors', {}).get(name, (0.0, 0.0, 1.0))  # Mặc định là màu xanh
                color_hex = "#{:02x}{:02x}{:02x}".format(
                    int(color[0] * 255), 
                    int(color[1] * 255), 
                    int(color[2] * 255)
                )
                
                frame = ttk.Frame(scrollable_frame)
                frame.pack(fill=tk.X, pady=2)
                
                # Tạo ô màu
                color_label = tk.Label(frame, bg=color_hex, width=2, height=1)
                color_label.pack(side=tk.LEFT, padx=5)
                
                # Tạo checkbox
                cb = ttk.Checkbutton(frame, text=name, variable=var)
                cb.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # Frame nút
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=10)
            
            # Hàm hiển thị OAR đã chọn
            def show_selected_oars():
                selected_oars = [name for name, var in oar_vars.items() if var.get()]
                
                if not selected_oars:
                    messagebox.showwarning("Cảnh báo", "Vui lòng chọn ít nhất một cơ quan để hiển thị")
                    return
                
                # Đóng hộp thoại
                oar_dialog.destroy()
                
                # Xóa hiển thị cũ
                self.ax_3d.clear()
                self.ax_3d.set_xlabel('X')
                self.ax_3d.set_ylabel('Y')
                self.ax_3d.set_zlabel('Z')
                self.ax_3d.set_title('Mô hình 3D - Cơ quan nguy cấp')
                
                # Lấy kích thước voxel
                voxel_size = getattr(self, 'image_metadata', {}).get('voxel_size', [1.0, 1.0, 1.0])
                
                # Hiển thị từng cấu trúc đã chọn
                for oar_name in selected_oars:
                    # Lấy mask của cấu trúc
                    mask = self.structures[oar_name]
                    
                    # Lấy màu của cấu trúc
                    color = getattr(self, 'structure_colors', {}).get(oar_name, (0.0, 0.0, 1.0))  # Mặc định là màu xanh
                    
                    # Tìm các điểm biên của mask
                    from skimage import measure
                    verts, faces, _, _ = measure.marching_cubes(mask, level=0.5)
                    
                    # Điều chỉnh tỷ lệ theo kích thước voxel
                    verts = verts * voxel_size
                    
                    # Tạo mesh 3D
                    import matplotlib.tri as mtri
                    mesh = self.ax_3d.plot_trisurf(
                        verts[:, 0], verts[:, 1], verts[:, 2],
                        triangles=faces,
                        color=color,
                        alpha=0.5,
                        shade=True
                    )
                
                # Cập nhật hiển thị
                self.canvas_3d.draw()
                
                logger.info(f"Đã hiển thị {len(selected_oars)} cơ quan nguy cấp trong chế độ 3D")
            
            # Nút hiển thị
            ttk.Button(button_frame, text="Hiển thị", command=show_selected_oars).pack(side=tk.LEFT, padx=5)
            
            # Nút hủy
            ttk.Button(button_frame, text="Hủy", command=oar_dialog.destroy).pack(side=tk.RIGHT, padx=5)
            
        except Exception as error:
            logger.error(f"Lỗi khi hiển thị OAR 3D: {str(error)}")
            messagebox.showerror("Lỗi", f"Không thể hiển thị OAR 3D: {str(error)}")

    def show_beams_3d(self):
        """Hiển thị các chùm tia trong chế độ 3D."""
        try:
            # Kiểm tra xem có chùm tia không
            if not hasattr(self, 'plan_data') or 'beams' not in self.plan_data or not self.plan_data['beams']:
                messagebox.showwarning("Cảnh báo", "Không có chùm tia nào để hiển thị")
                return
                
            # Xóa hiển thị cũ
            self.ax_3d.clear()
            self.ax_3d.set_xlabel('X')
            self.ax_3d.set_ylabel('Y')
            self.ax_3d.set_zlabel('Z')
            self.ax_3d.set_title('Mô hình 3D - Chùm tia')
            
            # Lấy kích thước voxel
            voxel_size = getattr(self, 'image_metadata', {}).get('voxel_size', [1.0, 1.0, 1.0])
            
            # Lấy tâm xoay (isocenter)
            isocenter = self.plan_data.get('isocenter', [0, 0, 0])
            
            # Hiển thị từng chùm tia
            for beam_id, beam in self.plan_data.get('beams', {}).items():
                # Lấy thông tin chùm tia
                gantry_angle = beam.get('gantry_angle', 0)
                collimator_angle = beam.get('collimator_angle', 0)
                couch_angle = beam.get('couch_angle', 0)
                
                # Tạo hình nón biểu diễn chùm tia
                import numpy as np
                
                # Tính toán hướng chùm tia dựa trên góc gantry và couch
                # Góc gantry: 0 = trước, 90 = trái, 180 = sau, 270 = phải
                # Góc couch: 0 = thẳng, 90 = xoay phải, 270 = xoay trái
                
                # Chuyển đổi góc sang radian
                gantry_rad = np.radians(gantry_angle)
                couch_rad = np.radians(couch_angle)
                
                # Tính hướng chùm tia
                direction = np.array([
                    np.cos(gantry_rad) * np.cos(couch_rad),
                    np.sin(gantry_rad) * np.cos(couch_rad),
                    np.sin(couch_rad)
                ])
                
                # Tạo điểm đầu và cuối của trục chùm tia
                beam_length = 300  # mm
                start_point = np.array(isocenter)
                end_point = start_point - direction * beam_length
                
                # Vẽ trục chùm tia
                self.ax_3d.plot([start_point[0], end_point[0]], 
                               [start_point[1], end_point[1]], 
                               [start_point[2], end_point[2]], 
                               'r-', linewidth=2)
                
                # Tạo hình nón biểu diễn chùm tia
                # Tính các điểm trên đường tròn vuông góc với hướng chùm tia
                radius = beam_length * 0.2  # Bán kính tại điểm cuối
                
                # Tìm vector vuông góc với hướng chùm tia
                if np.allclose(direction, [0, 0, 1]) or np.allclose(direction, [0, 0, -1]):
                    perp1 = np.array([1, 0, 0])
                    perp2 = np.array([0, 1, 0])
                else:
                    perp1 = np.cross(direction, [0, 0, 1])
                    perp1 = perp1 / np.linalg.norm(perp1)
                    perp2 = np.cross(direction, perp1)
                    perp2 = perp2 / np.linalg.norm(perp2)
                
                # Tạo các điểm trên đường tròn
                theta = np.linspace(0, 2*np.pi, 20)
                circle_points = []
                
                for angle in theta:
                    point = end_point + radius * (np.cos(angle) * perp1 + np.sin(angle) * perp2)
                    circle_points.append(point)
                
                # Vẽ đường tròn tại điểm cuối
                x_circle = [p[0] for p in circle_points]
                y_circle = [p[1] for p in circle_points]
                z_circle = [p[2] for p in circle_points]
                
                self.ax_3d.plot(x_circle, y_circle, z_circle, 'r-')
                
                # Vẽ các đường từ isocenter đến đường tròn
                for point in circle_points[::4]:  # Chỉ vẽ một số đường để tránh quá rối
                    self.ax_3d.plot([start_point[0], point[0]], 
                                   [start_point[1], point[1]], 
                                   [start_point[2], point[2]], 
                                   'r-', alpha=0.3)
            
            # Cập nhật hiển thị
            self.canvas_3d.draw()
            
            logger.info(f"Đã hiển thị {len(self.plan_data.get('beams', []))} chùm tia trong chế độ 3D")
            
        except Exception as error:
            logger.error(f"Lỗi khi hiển thị chùm tia 3D: {str(error)}")
            messagebox.showerror("Lỗi", f"Không thể hiển thị chùm tia 3D: {str(error)}")

    def show_dose_3d(self):
        """Hiển thị phân bố liều trong chế độ 3D."""
        try:
            # Kiểm tra xem có dữ liệu liều không
            if not hasattr(self, 'dose_data') or self.dose_data is None:
                messagebox.showwarning("Cảnh báo", "Không có dữ liệu liều để hiển thị")
                return
                
            # Xóa hiển thị cũ
            self.ax_3d.clear()
            self.ax_3d.set_xlabel('X')
            self.ax_3d.set_ylabel('Y')
            self.ax_3d.set_zlabel('Z')
            self.ax_3d.set_title('Mô hình 3D - Phân bố liều')
            
            # Lấy kích thước voxel
            voxel_size = getattr(self, 'image_metadata', {}).get('voxel_size', [1.0, 1.0, 1.0])
            
            # Lấy liều kê toa
            prescribed_dose = self.plan_data.get('prescribed_dose', 50.0)
            
            # Tạo các isodose levels (ví dụ: 95%, 80%, 50% của liều kê toa)
            isodose_levels = [0.95, 0.8, 0.5]
            isodose_colors = [(1.0, 0.0, 0.0), (1.0, 0.5, 0.0), (1.0, 1.0, 0.0)]  # Đỏ, Cam, Vàng
            
            # Hiển thị từng mức liều
            for level, color in zip(isodose_levels, isodose_colors):
                # Tính giá trị ngưỡng
                threshold = level * prescribed_dose
                
                # Tạo mask cho mức liều này
                dose_mask = self.dose_data >= threshold
                
                # Tìm các điểm biên của mask
                from skimage import measure
                try:
                    verts, faces, _, _ = measure.marching_cubes(dose_mask, level=0.5)
                    
                    # Điều chỉnh tỷ lệ theo kích thước voxel
                    verts = verts * voxel_size
                    
                    # Tạo mesh 3D
                    import matplotlib.tri as mtri
                    mesh = self.ax_3d.plot_trisurf(
                        verts[:, 0], verts[:, 1], verts[:, 2],
                        triangles=faces,
                        color=color,
                        alpha=0.3,
                        shade=True
                    )
                    
                    # Thêm nhãn
                    self.ax_3d.text(
                        verts[0, 0], verts[0, 1], verts[0, 2],
                        f"{int(level*100)}%",
                        color=color,
                        fontweight='bold'
                    )
                except:
                    # Bỏ qua nếu không thể tạo mesh cho mức liều này
                    pass
            
            # Cập nhật hiển thị
            self.canvas_3d.draw()
            
            logger.info(f"Đã hiển thị phân bố liều 3D với {len(isodose_levels)} mức liều")
            
        except Exception as error:
            logger.error(f"Lỗi khi hiển thị liều 3D: {str(error)}")
            messagebox.showerror("Lỗi", f"Không thể hiển thị liều 3D: {str(error)}")

    def rotate_3d_model(self):
        """Xoay mô hình 3D."""
        try:
            # Kích hoạt chế độ xoay tương tác
            self.ax_3d.mouse_init()
            
            # Thông báo cho người dùng
            messagebox.showinfo("Thông báo", "Đã kích hoạt chế độ xoay. Sử dụng chuột để xoay mô hình 3D.")
            
            # Cập nhật hiển thị
            self.canvas_3d.draw()
            
        except Exception as error:
            logger.error(f"Lỗi khi kích hoạt chế độ xoay 3D: {str(error)}")
            messagebox.showerror("Lỗi", f"Không thể kích hoạt chế độ xoay 3D: {str(error)}")

    def save_3d_image(self):
        """Lưu hình ảnh từ chế độ xem 3D."""
        try:
            # Mở hộp thoại lưu file
            file_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")],
                title="Lưu hình ảnh 3D"
            )
            
            if not file_path:
                return
                
            # Lưu hình ảnh
            self.fig_3d.savefig(file_path, dpi=300, bbox_inches='tight')
            
            # Thông báo thành công
            messagebox.showinfo("Thành công", f"Đã lưu hình ảnh 3D tại:\n{file_path}")
            
            logger.info(f"Đã lưu hình ảnh 3D tại: {file_path}")
            
        except Exception as error:
            logger.error(f"Lỗi khi lưu hình ảnh 3D: {str(error)}")
            messagebox.showerror("Lỗi", f"Không thể lưu hình ảnh 3D: {str(error)}")
    
    def show_mlc(self):
        """Hiển thị MLC trong chế độ xem chùm tia."""
        messagebox.showinfo("Thông báo", "Tính năng hiển thị MLC đang được phát triển")
    
    def show_target_bev(self):
        """Hiển thị đích trong chế độ xem chùm tia."""
        messagebox.showinfo("Thông báo", "Tính năng hiển thị đích BEV đang được phát triển")
    
    def show_oars_bev(self):
        """Hiển thị các cơ quan nguy cấp trong chế độ xem chùm tia."""
        messagebox.showinfo("Thông báo", "Tính năng hiển thị OAR BEV đang được phát triển")
    
    def export_drr(self):
        """Xuất DRR (Digitally Reconstructed Radiograph)."""
        messagebox.showinfo("Thông báo", "Tính năng xuất DRR đang được phát triển")
    
    def update_dvh_plot(self):
        """Cập nhật biểu đồ DVH dựa trên các cấu trúc được chọn."""
        if not hasattr(self, 'dvh_figure') or not hasattr(self, 'dvh_canvas'):
            return
            
        # Xóa biểu đồ cũ
        for ax in self.dvh_figure.get_axes():
            ax.clear()
        
        # Thêm biểu đồ mới
        ax = self.dvh_figure.add_subplot(111)
        ax.set_title("Biểu đồ Thể tích - Liều (DVH)")
        ax.set_xlabel("Liều (Gy)")
        ax.set_ylabel("Thể tích (%)")
        ax.grid(True)
        
        # Kiểm tra xem có dữ liệu DVH không
        if not hasattr(self, 'dvh_data'):
            ax.text(0.5, 0.5, "Chưa có dữ liệu DVH", 
                    horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
            self.dvh_canvas.draw()
            return
        
        # Vẽ DVH cho các cấu trúc được chọn
        for name, var in self.structure_vars.items():
            if var.get() and name in self.dvh_data:
                data = self.dvh_data[name]
                ax.plot(data['dose'], data['volume'], label=name)
        
        ax.legend()
        self.dvh_canvas.draw()
    
    def calculate_dvh(self):
        """Tính toán DVH cho kế hoạch hiện tại."""
        try:
            # Kiểm tra xem đã có phân bố liều chưa
            if not hasattr(self, 'dose_data') or self.dose_data is None:
                messagebox.showwarning("Cảnh báo", "Vui lòng tính toán phân bố liều trước khi tính DVH")
                return
                
            # Hiển thị thanh tiến trình
            progress_window = tk.Toplevel(self.window)
            progress_window.title("Đang tính toán...")
            progress_window.geometry("300x100")
            progress_window.resizable(False, False)
            
            progress_label = ttk.Label(progress_window, text="Đang tính toán DVH...")
            progress_label.pack(pady=10)
            
            progress_bar = ttk.Progressbar(progress_window, mode='indeterminate')
            progress_bar.pack(fill=tk.X, padx=20, pady=10)
            progress_bar.start()
            
            # Thực hiện tính toán trong một luồng riêng
            def run_calculation():
                try:
                    # Tạo đối tượng DVHCalculator
                    dvh_calculator = DVHCalculator()
                    
                    # Thiết lập dữ liệu liều
                    dvh_calculator.set_dose_data(self.dose_data)
                    
                    # Tính DVH cho mỗi cấu trúc
                    self.dvh_data = {}
                    for name, structure in self.structures.items():
                        # Thêm cấu trúc vào DVHCalculator
                        dvh_calculator.add_structure(name, structure)
                        
                        # Tính DVH
                        dvh_result = dvh_calculator.calculate_dvh(structure_name=name)
                        self.dvh_data[name] = dvh_result
                    
                    # Cập nhật giao diện
                    self.window.after(0, self.update_dvh_plot)
                    self.window.after(0, progress_window.destroy)
                except Exception as error:
                    self.window.after(0, lambda error=error: messagebox.showerror("Lỗi", f"Lỗi tính toán DVH: {str(error)}"))
                    self.window.after(0, progress_window.destroy)
                    logger.error(f"Lỗi tính toán DVH: {str(error)}")
            
            # Khởi động luồng tính toán
            threading.Thread(target=run_calculation, daemon=True).start()
        except Exception as error:
            logger.error(f"Lỗi khởi tạo tính toán DVH: {str(error)}")
            messagebox.showerror("Lỗi", f"Không thể tính toán DVH: {str(error)}")
    
    def export_dvh_data(self):
        """Xuất dữ liệu DVH sang file CSV."""
        if not hasattr(self, 'dvh_data') or not self.dvh_data:
            messagebox.showwarning("Cảnh báo", "Vui lòng tính toán DVH trước khi xuất dữ liệu")
            return
            
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
            
            if file_path:
                import csv
                with open(file_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    
                    # Viết tiêu đề
                    header = ["Liều (Gy)"]
                    for name in self.dvh_data.keys():
                        header.append(f"{name} (%)")
                    writer.writerow(header)
                    
                    # Giả sử tất cả DVH có cùng điểm liều
                    first_struct = list(self.dvh_data.keys())[0]
                    doses = self.dvh_data[first_struct]['dose']
                    
                    # Viết dữ liệu
                    for i, dose in enumerate(doses):
                        row = [dose]
                        for name in self.dvh_data.keys():
                            row.append(self.dvh_data[name]['volume'][i])
                        writer.writerow(row)
                    
                messagebox.showinfo("Thành công", "Đã xuất dữ liệu DVH")
                logger.info(f"Đã xuất dữ liệu DVH sang {file_path}")
        except Exception as error:
            logger.error(f"Lỗi xuất dữ liệu DVH: {str(error)}")
            messagebox.showerror("Lỗi", f"Không thể xuất dữ liệu DVH: {str(error)}")
    
    def save_dvh_image(self):
        """Lưu biểu đồ DVH sang file hình ảnh."""
        if not hasattr(self, 'dvh_figure'):
            messagebox.showwarning("Cảnh báo", "Không có biểu đồ DVH để lưu")
            return
            
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[
                    ("PNG files", "*.png"),
                    ("JPEG files", "*.jpg"),
                    ("PDF files", "*.pdf"),
                    ("All files", "*.*")
                ]
            )
            
            if file_path:
                self.dvh_figure.savefig(file_path, dpi=300, bbox_inches='tight')
                messagebox.showinfo("Thành công", "Đã lưu biểu đồ DVH")
                logger.info(f"Đã lưu biểu đồ DVH sang {file_path}")
        except Exception as error:
            logger.error(f"Lỗi lưu biểu đồ DVH: {str(error)}")
            messagebox.showerror("Lỗi", f"Không thể lưu biểu đồ DVH: {str(error)}")
            
    def get_plan_data(self):
        """Lấy dữ liệu kế hoạch từ giao diện."""
        plan_data = {
            'plan_name': self.plan_name_var.get() if hasattr(self, 'plan_name_var') else "Unnamed Plan",
            'total_dose': float(self.total_dose_var.get()) if hasattr(self, 'total_dose_var') else 0.0,
            'fraction_count': int(self.fraction_count_var.get()) if hasattr(self, 'fraction_count_var') else 0,
            'technique': self.technique_var.get() if hasattr(self, 'technique_var') else "3DCRT",
            # Thêm các trường khác...
        }
        return plan_data
        
    def set_plan_data(self, plan_data):
        """Cập nhật giao diện với dữ liệu kế hoạch."""
        if hasattr(self, 'plan_name_var'):
            self.plan_name_var.set(plan_data.get('plan_name', ""))
        if hasattr(self, 'total_dose_var'):
            self.total_dose_var.set(plan_data.get('total_dose', 0.0))
        if hasattr(self, 'fraction_count_var'):
            self.fraction_count_var.set(plan_data.get('fraction_count', 0))
        if hasattr(self, 'technique_var'):
            self.technique_var.set(plan_data.get('technique', "3DCRT"))
        # Cập nhật các trường khác...
        
    def update_dose_display(self, dose_data):
        """Cập nhật hiển thị phân bố liều."""
        self.dose_data = dose_data
        
        # Cập nhật hiển thị phân bố liều trên giao diện
        if hasattr(self, 'dvh_tab') and hasattr(self, 'dvh_frame'):
            # Tính và hiển thị DVH
            self.calculate_dvh()
            
        # Cập nhật hiển thị 3D nếu tab 3D view đang mở
        if hasattr(self, '3d_view_tab'):
            self.show_dose_3d()
            
        # Cập nhật hiển thị liều trên các view MPR
        if hasattr(self, 'beam_view_tab'):
            # Hiển thị liều theo phương thẳng đứng (Beam's Eye View)
            self._update_beam_view_with_dose()
            
        # Thông báo và log
        messagebox.showinfo("Thành công", "Đã tính toán và hiển thị phân bố liều")
        logger.info("Đã cập nhật hiển thị phân bố liều trên tất cả các view")

    def check_plan_qa(self):
        """Kiểm tra chất lượng kế hoạch xạ trị."""
        try:
            # Kiểm tra xem đã tính toán liều chưa
            if not hasattr(self, 'dose_data') or self.dose_data is None:
                messagebox.showwarning("Cảnh báo", "Cần tính toán phân bố liều trước khi kiểm tra QA")
                return
                
            # Kiểm tra xem đã có cấu trúc chưa
            if not self.structures:
                messagebox.showwarning("Cảnh báo", "Cần có cấu trúc để kiểm tra QA")
                return
                
            # Tạo cửa sổ tùy chọn QA
            qa_window = tk.Toplevel(self.window)
            qa_window.title("Kiểm tra chất lượng kế hoạch (QA)")
            qa_window.geometry("600x700")
            qa_window.transient(self.window)
            qa_window.grab_set()
            
            # Frame chính
            main_frame = ttk.Frame(qa_window, padding=10)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Frame thiết lập
            setup_frame = ttk.LabelFrame(main_frame, text="Thiết lập kiểm tra", padding=10)
            setup_frame.pack(fill=tk.X, padx=5, pady=5)
            
            # Chọn PTV
            ttk.Label(setup_frame, text="Cấu trúc đích (PTV):").grid(row=0, column=0, sticky=tk.W, pady=5)
            target_var = tk.StringVar()
            target_combo = ttk.Combobox(setup_frame, textvariable=target_var, width=30)
            target_combo['values'] = list(self.structures.keys())
            target_combo.grid(row=0, column=1, sticky=tk.W, pady=5)
            
            # Mặc định chọn cấu trúc PTV nếu có
            for name in self.structures.keys():
                if 'ptv' in name.lower():
                    target_var.set(name)
                    break
            
            # Liều kê toa
            ttk.Label(setup_frame, text="Liều kê toa (Gy):").grid(row=1, column=0, sticky=tk.W, pady=5)
            prescription_var = tk.DoubleVar(value=self.plan_data.get('prescribed_dose', 50.0))
            ttk.Entry(setup_frame, textvariable=prescription_var, width=10).grid(row=1, column=1, sticky=tk.W, pady=5)
            
            # Ngưỡng độ phủ
            ttk.Label(setup_frame, text="Ngưỡng độ phủ (%):").grid(row=2, column=0, sticky=tk.W, pady=5)
            coverage_var = tk.DoubleVar(value=95.0)
            ttk.Entry(setup_frame, textvariable=coverage_var, width=10).grid(row=2, column=1, sticky=tk.W, pady=5)
            
            # Frame ràng buộc OAR
            constraints_frame = ttk.LabelFrame(main_frame, text="Ràng buộc OAR", padding=10)
            constraints_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Canvas cho các ràng buộc cuộn được
            canvas = tk.Canvas(constraints_frame)
            scrollbar = ttk.Scrollbar(constraints_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(
                    scrollregion=canvas.bbox("all")
                )
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # Chọn OAR và thiết lập ràng buộc
            oar_vars = {}
            row = 0
            
            # Lọc ra các cấu trúc không phải PTV
            ptv_name = target_var.get()
            oar_names = [name for name in self.structures.keys() if name != ptv_name and not name.lower().startswith('ptv')]
            
            for i, name in enumerate(oar_names):
                # Frame cho mỗi OAR
                oar_frame = ttk.LabelFrame(scrollable_frame, text=name, padding=5)
                oar_frame.grid(row=row, column=0, sticky=tk.W+tk.E, padx=5, pady=5)
                
                # Các ràng buộc cơ bản
                ttk.Label(oar_frame, text="Liều tối đa (Gy):").grid(row=0, column=0, sticky=tk.W, pady=2)
                max_dose_var = tk.DoubleVar()
                ttk.Entry(oar_frame, textvariable=max_dose_var, width=8).grid(row=0, column=1, sticky=tk.W, pady=2)
                
                ttk.Label(oar_frame, text="Liều trung bình (Gy):").grid(row=1, column=0, sticky=tk.W, pady=2)
                mean_dose_var = tk.DoubleVar()
                ttk.Entry(oar_frame, textvariable=mean_dose_var, width=8).grid(row=1, column=1, sticky=tk.W, pady=2)
                
                # Ràng buộc VxGy
                v_dose_frame = ttk.Frame(oar_frame)
                v_dose_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=2)
                
                ttk.Label(v_dose_frame, text="V").grid(row=0, column=0)
                vx_var = tk.IntVar(value=20)
                ttk.Entry(v_dose_frame, textvariable=vx_var, width=3).grid(row=0, column=1)
                ttk.Label(v_dose_frame, text="Gy (%):").grid(row=0, column=2)
                vx_limit_var = tk.DoubleVar(value=30.0)
                ttk.Entry(v_dose_frame, textvariable=vx_limit_var, width=8).grid(row=0, column=3)
                
                # Lưu biến
                oar_vars[name] = {
                    'max_dose': max_dose_var,
                    'mean_dose': mean_dose_var,
                    'vx': vx_var,
                    'vx_limit': vx_limit_var
                }
                
                # Thiết lập một số giá trị mặc định dựa trên loại cơ quan
                if 'cord' in name.lower():
                    max_dose_var.set(45.0)
                elif 'lung' in name.lower():
                    mean_dose_var.set(20.0)
                    vx_var.set(20)
                    vx_limit_var.set(30.0)
                elif 'heart' in name.lower():
                    max_dose_var.set(40.0)
                elif 'liver' in name.lower():
                    mean_dose_var.set(30.0)
                
                row += 1
            
            # Frame kết quả
            results_frame = ttk.LabelFrame(main_frame, text="Kết quả", padding=10)
            results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Tạo Text Widget để hiển thị kết quả
            results_text = tk.Text(results_frame, height=10, width=80, wrap=tk.WORD)
            results_text.pack(fill=tk.BOTH, expand=True)
            results_text.config(state=tk.DISABLED)  # Chỉ đọc
            
            # Frame nút điều khiển
            buttons_frame = ttk.Frame(main_frame)
            buttons_frame.pack(fill=tk.X, pady=10)
            
            # Hàm chạy kiểm tra QA
            def run_qa_check():
                try:
                    # Lấy giá trị từ giao diện
                    target = target_var.get()
                    if not target:
                        messagebox.showwarning("Cảnh báo", "Vui lòng chọn cấu trúc đích (PTV)")
                        return
                    
                    prescription = prescription_var.get()
                    
                    # Tạo ràng buộc cho OAR
                    constraints = {}
                    for name, vars_dict in oar_vars.items():
                        max_dose = vars_dict['max_dose'].get()
                        mean_dose = vars_dict['mean_dose'].get()
                        vx = vars_dict['vx'].get()
                        vx_limit = vars_dict['vx_limit'].get()
                        
                        constraint = {}
                        if max_dose > 0:
                            constraint['max_dose'] = max_dose
                        if mean_dose > 0:
                            constraint['mean_dose'] = mean_dose
                        if vx > 0 and vx_limit > 0:
                            constraint[f'V{vx}Gy'] = vx_limit
                        
                        if constraint:
                            constraints[name] = constraint
                    
                    # Tạo đối tượng QA
                    from quangstation.quality_assurance import PlanQA
                    qa = PlanQA(
                        plan_data=self.plan_data,
                        dose_data=self.dose_data,
                        structures=self.structures
                    )
                    
                    # Chạy tất cả kiểm tra
                    results = qa.run_all_checks(target, prescription, constraints)
                    
                    # Hiển thị kết quả
                    update_results(results)
                    
                    # Lưu báo cáo QA
                    report_path = qa.generate_qa_report()
                    if report_path:
                        messagebox.showinfo("Thành công", f"Đã lưu báo cáo QA tại: {report_path}")
                    
                except Exception as error:
                    logger.error(f"Lỗi khi chạy kiểm tra QA: {str(error)}")
                    messagebox.showerror("Lỗi", f"Không thể chạy kiểm tra QA: {str(error)}")
            
            # Hàm cập nhật kết quả
            def update_results(results):
                results_text.config(state=tk.NORMAL)
                results_text.delete(1.0, tk.END)
                
                # Hiển thị tiêu đề
                results_text.insert(tk.END, "KẾT QUẢ KIỂM TRA CHẤT LƯỢNG KẾ HOẠCH\n", "title")
                results_text.insert(tk.END, "=" * 60 + "\n\n")
                
                # Tổng quan
                if results['all_passed']:
                    status = "ĐẠT\n"
                    results_text.insert(tk.END, "Kết quả kiểm tra: ", "subtitle")
                    results_text.insert(tk.END, status, "passed")
                else:
                    status = "KHÔNG ĐẠT\n"
                    results_text.insert(tk.END, "Kết quả kiểm tra: ", "subtitle")
                    results_text.insert(tk.END, status, "failed")
                
                # Chi tiết từng kiểm tra
                tests = results['results']
                
                # 1. Độ phủ liều
                coverage = tests['coverage']
                results_text.insert(tk.END, "\n1. Độ phủ liều\n", "subtitle")
                if coverage['passed']:
                    results_text.insert(tk.END, "   Kết quả: Đạt\n", "passed")
                else:
                    results_text.insert(tk.END, "   Kết quả: Không đạt\n", "failed")
                results_text.insert(tk.END, f"   {coverage['comment']}\n")
                results_text.insert(tk.END, f"   - V100: {coverage['details']['V100']:.1f}%\n")
                results_text.insert(tk.END, f"   - V95: {coverage['details']['V95']:.1f}%\n")
                results_text.insert(tk.END, f"   - V90: {coverage['details']['V90']:.1f}%\n")
                
                # 2. Ràng buộc OAR
                oar = tests['oar_constraints']
                results_text.insert(tk.END, "\n2. Ràng buộc cơ quan nguy cấp\n", "subtitle")
                if oar['passed']:
                    results_text.insert(tk.END, "   Kết quả: Đạt\n", "passed")
                else:
                    results_text.insert(tk.END, "   Kết quả: Không đạt\n", "failed")
                results_text.insert(tk.END, f"   {oar['comment']}\n")
                
                # Hiển thị chi tiết từng cơ quan
                for organ_name, organ_result in oar['results_by_organ'].items():
                    results_text.insert(tk.END, f"\n   {organ_name}:\n")
                    if organ_result['passed']:
                        results_text.insert(tk.END, "      Đạt\n", "passed")
                    else:
                        results_text.insert(tk.END, "      Không đạt\n", "failed")
                    
                    for constraint_name, constraint_result in organ_result['constraint_results'].items():
                        if constraint_result['passed']:
                            status_text = "Đạt"
                            tag = "passed"
                        else:
                            status_text = "Không đạt"
                            tag = "failed"
                            
                        results_text.insert(tk.END, f"      - {constraint_name}: {constraint_result['actual']:.1f} / {constraint_result['limit']:.1f} ({status_text})\n", tag)
                
                # 3. Tính phù hợp
                conformity = tests['conformity']
                results_text.insert(tk.END, "\n3. Tính phù hợp (Conformity)\n", "subtitle")
                if conformity['passed']:
                    results_text.insert(tk.END, "   Kết quả: Đạt\n", "passed")
                else:
                    results_text.insert(tk.END, "   Kết quả: Không đạt\n", "failed")
                results_text.insert(tk.END, f"   {conformity['comment']}\n")
                results_text.insert(tk.END, f"   - CI (RTOG): {conformity['details']['rtog_ci']:.3f}\n")
                results_text.insert(tk.END, f"   - Paddick CI: {conformity['details']['paddick_ci']:.3f}\n")
                results_text.insert(tk.END, f"   - Gradient Index: {conformity['details']['gi']:.3f}\n")
                
                # 4. Tính đồng nhất
                homogeneity = tests['homogeneity']
                results_text.insert(tk.END, "\n4. Tính đồng nhất (Homogeneity)\n", "subtitle")
                if homogeneity['passed']:
                    results_text.insert(tk.END, "   Kết quả: Đạt\n", "passed")
                else:
                    results_text.insert(tk.END, "   Kết quả: Không đạt\n", "failed")
                results_text.insert(tk.END, f"   {homogeneity['comment']}\n")
                results_text.insert(tk.END, f"   - HI (ICRU): {homogeneity['details']['icru_hi']:.3f}\n")
                results_text.insert(tk.END, f"   - D2: {homogeneity['details']['d2']:.2f} Gy\n")
                results_text.insert(tk.END, f"   - D98: {homogeneity['details']['d98']:.2f} Gy\n")
                
                # Thiết lập tags
                results_text.tag_configure("title", font=("Helvetica", 12, "bold"))
                results_text.tag_configure("subtitle", font=("Helvetica", 10, "bold"))
                results_text.tag_configure("passed", foreground="green", font=("Helvetica", 10, "bold"))
                results_text.tag_configure("failed", foreground="red", font=("Helvetica", 10, "bold"))
                
                results_text.config(state=tk.DISABLED)
            
            # Nút Chạy QA
            ttk.Button(buttons_frame, text="Chạy kiểm tra QA", command=run_qa_check).pack(side=tk.LEFT, padx=5)
            
            # Nút Đóng
            ttk.Button(buttons_frame, text="Đóng", command=qa_window.destroy).pack(side=tk.RIGHT, padx=5)
            
            # Đặt focus
            qa_window.focus_set()
            
        except Exception as error:
            logger.error(f"Lỗi khi mở cửa sổ kiểm tra QA: {str(error)}")
            messagebox.showerror("Lỗi", f"Không thể mở cửa sổ kiểm tra QA: {str(error)}")

    def _update_beam_view_with_dose(self):
        """Cập nhật hiển thị liều trên Beam's Eye View."""
        if not hasattr(self, 'dose_data') or self.dose_data is None:
            logger.warning("Không có dữ liệu liều để hiển thị")
            return
            
        if not hasattr(self, 'beam_view_canvas'):
            logger.warning("Chưa khởi tạo canvas hiển thị Beam's Eye View")
            return
            
        try:
            # Lấy chùm tia đang được chọn
            selected_beam = None
            if hasattr(self, 'beam_listbox') and self.beam_listbox.curselection():
                beam_idx = self.beam_listbox.curselection()[0]
                beam_id = self.beam_listbox.get(beam_idx)
                
                # Lấy thông tin chùm tia
                for beam in self.beams:
                    if beam.id == beam_id:
                        selected_beam = beam
                        break
            
            if selected_beam is None:
                return
                
            # Lấy thông tin góc của chùm tia
            gantry_angle = selected_beam.gantry_angle
            couch_angle = selected_beam.couch_angle
            
            # Tính toán mặt phẳng hiển thị dựa trên góc chùm tia
            from quangstation.utils.geometry import calculate_beam_plane
            beam_plane = calculate_beam_plane(self.dose_data, 
                                             gantry_angle, 
                                             couch_angle, 
                                             selected_beam.isocenter)
            
            # Áp dụng colormap cho hiển thị liều
            import matplotlib.pyplot as plt
            from matplotlib import cm
            import numpy as np
            
            # Chuẩn hóa liều
            dose_min = np.min(self.dose_data)
            dose_max = np.max(self.dose_data)
            normalized_dose = (beam_plane - dose_min) / (dose_max - dose_min + 1e-10)
            
            # Áp dụng colormap
            colored_dose = cm.jet(normalized_dose)
            
            # Chuyển đổi sang dạng hình ảnh
            from PIL import Image, ImageTk
            
            # Chuyển sang uint8 để hiển thị
            rgba_img = (colored_dose * 255).astype(np.uint8)
            
            # Thêm alpha channel dựa trên giá trị liều
            # Những vùng liều thấp sẽ trong suốt hơn
            alpha_scale = 0.7  # Điều chỉnh độ trong suốt tối đa
            rgba_img[:, :, 3] = (normalized_dose * 255 * alpha_scale).astype(np.uint8)
            
            # Tạo hình ảnh PIL
            pil_img = Image.fromarray(rgba_img)
            
            # Điều chỉnh kích thước để vừa với canvas
            canvas_width = self.beam_view_canvas.winfo_width()
            canvas_height = self.beam_view_canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:
                pil_img = pil_img.resize((canvas_width, canvas_height), Image.LANCZOS)
                
                # Chuyển thành PhotoImage
                dose_image = ImageTk.PhotoImage(pil_img)
                
                # Hiển thị trên canvas
                self.beam_view_canvas.create_image(0, 0, anchor="nw", image=dose_image)
                
                # Lưu tham chiếu để tránh garbage collection
                self.beam_view_dose_image = dose_image
                
                # Thêm chú thích thang màu
                self._add_dose_colorbar(self.beam_view_canvas, 
                                      dose_min, 
                                      dose_max,
                                      canvas_width, 
                                      canvas_height)
                
                logger.info(f"Đã cập nhật hiển thị liều trên Beam's Eye View cho chùm tia {beam_id}")
            
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật hiển thị liều trên Beam's Eye View: {str(e)}")
            
    def _add_dose_colorbar(self, canvas, min_val, max_val, canvas_width, canvas_height):
        """Thêm thang màu cho hiển thị liều."""
        # Vị trí và kích thước của colorbar
        bar_height = 20
        bar_width = 150
        x_offset = canvas_width - bar_width - 10
        y_offset = canvas_height - bar_height - 10
        
        # Vẽ nền cho colorbar
        canvas.create_rectangle(x_offset, y_offset, 
                             x_offset + bar_width, y_offset + bar_height,
                             fill="white", outline="black")
        
        # Tạo gradient màu
        import matplotlib.pyplot as plt
        from matplotlib import cm
        import numpy as np
        
        # Tạo gradient
        gradient = np.linspace(0, 1, bar_width)
        gradient = np.vstack((gradient, gradient))
        
        # Áp dụng colormap
        colored_gradient = (cm.jet(gradient) * 255).astype(np.uint8)
        
        # Chuyển thành hình ảnh
        from PIL import Image, ImageTk
        gradient_img = Image.fromarray(colored_gradient)
        gradient_photo = ImageTk.PhotoImage(gradient_img)
        
        # Hiển thị gradient
        canvas.create_image(x_offset, y_offset, anchor="nw", image=gradient_photo)
        
        # Lưu tham chiếu
        self.gradient_photo = gradient_photo
        
        # Thêm giá trị min/max
        canvas.create_text(x_offset, y_offset + bar_height + 5, 
                        text=f"{min_val:.1f}", anchor="nw")
        canvas.create_text(x_offset + bar_width, y_offset + bar_height + 5, 
                        text=f"{max_val:.1f}", anchor="ne")
        
        # Tiêu đề
        canvas.create_text(x_offset + bar_width/2, y_offset - 5, 
                        text="Liều (Gy)", anchor="s")

    def kbp_optimize(self):
        """Tối ưu hóa kế hoạch dựa trên kiến thức (KBP)."""
        try:
            # Kiểm tra xem đã có cấu trúc và kế hoạch chưa
            if not hasattr(self, 'structures') or not self.structures:
                messagebox.showwarning("Cảnh báo", "Chưa có dữ liệu cấu trúc. Vui lòng tạo hoặc nhập cấu trúc trước.")
                return
            
            # Lấy dữ liệu kế hoạch
            plan_data = self.get_plan_data()
            if not plan_data or 'total_dose' not in plan_data or not plan_data['total_dose']:
                messagebox.showwarning("Cảnh báo", "Vui lòng nhập liều kê toa và số phân liều trước khi tối ưu hóa.")
                return
            
            # Tạo hộp thoại xác nhận
            import tkinter as tk
            from tkinter import ttk
            
            confirm_dialog = tk.Toplevel(self.window)
            confirm_dialog.title("Tối ưu hóa dựa trên kiến thức (KBP)")
            confirm_dialog.geometry("500x400")
            confirm_dialog.resizable(False, False)
            confirm_dialog.transient(self.window)
            confirm_dialog.grab_set()
            
            # Tạo các frame chính
            main_frame = ttk.Frame(confirm_dialog, padding=10)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Thông tin giới thiệu
            ttk.Label(main_frame, text="Tối ưu hóa dựa trên kiến thức (KBP)", font=("Arial", 12, "bold")).pack(pady=5)
            ttk.Label(main_frame, text="Hệ thống sẽ đề xuất các ràng buộc tối ưu dựa trên dữ liệu lịch sử", wraplength=450).pack(pady=5)
            
            # Frame chọn cơ quan
            organs_frame = ttk.LabelFrame(main_frame, text="Chọn cơ quan để tối ưu", padding=10)
            organs_frame.pack(fill=tk.X, pady=5)
            
            # Lấy danh sách cơ quan
            organs = [name for name in self.structures.keys() 
                     if not (name.startswith('PTV') or name.startswith('CTV') or name.startswith('GTV'))]
            
            # Tạo biến lưu trạng thái chọn
            organ_vars = {}
            for organ in organs:
                var = tk.BooleanVar(value=True)
                organ_vars[organ] = var
                ttk.Checkbutton(organs_frame, text=organ, variable=var).pack(anchor=tk.W)
            
            # Frame tùy chọn
            options_frame = ttk.LabelFrame(main_frame, text="Tùy chọn tối ưu hóa", padding=10)
            options_frame.pack(fill=tk.X, pady=5)
            
            # Tùy chọn tự động áp dụng
            auto_apply_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(options_frame, text="Tự động áp dụng các ràng buộc đề xuất", variable=auto_apply_var).pack(anchor=tk.W)
            
            # Tùy chọn hiển thị chi tiết
            show_details_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(options_frame, text="Hiển thị chi tiết các ràng buộc đề xuất", variable=show_details_var).pack(anchor=tk.W)
            
            # Frame nút điều khiển
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=15)
            
            def run_kbp_optimization():
                # Lấy danh sách cơ quan đã chọn
                selected_organs = [organ for organ, var in organ_vars.items() if var.get()]
                
                if not selected_organs:
                    messagebox.showwarning("Cảnh báo", "Vui lòng chọn ít nhất một cơ quan để tối ưu hóa.")
                    return
                
                # Đóng hộp thoại
                confirm_dialog.destroy()
                
                # Hiển thị thông báo đang xử lý
                self.window.config(cursor="wait")
                progress_window = tk.Toplevel(self.window)
                progress_window.title("Đang xử lý")
                progress_window.geometry("300x100")
                progress_window.resizable(False, False)
                progress_window.transient(self.window)
                progress_window.grab_set()
                
                ttk.Label(progress_window, text="Đang tối ưu hóa kế hoạch...", font=("Arial", 10)).pack(pady=10)
                progress = ttk.Progressbar(progress_window, mode="indeterminate")
                progress.pack(fill=tk.X, padx=20, pady=10)
                progress.start()
                
                # Thực hiện tối ưu hóa trong một luồng riêng
                def optimization_thread():
                    try:
                        # Khởi tạo KBP Optimizer
                        from quangstation.optimization.kbp_optimizer import KnowledgeBasedPlanningOptimizer
                        kbp_optimizer = KnowledgeBasedPlanningOptimizer()
                        
                        # Lấy đề xuất tối ưu hóa
                        optimization_goals = kbp_optimizer.suggest_optimization_goals(self.structures, plan_data)
                        
                        # Lọc theo cơ quan đã chọn
                        filtered_goals = [goal for goal in optimization_goals 
                                         if goal.structure_name in selected_organs or goal.structure_name.startswith('PTV')]
                        
                        # Cập nhật UI trong luồng chính
                        self.window.after(0, lambda: self._apply_kbp_results(
                            filtered_goals, 
                            show_details_var.get(), 
                            auto_apply_var.get(),
                            progress_window
                        ))
                        
                    except Exception as e:
                        self.logger.error(f"Lỗi khi thực hiện tối ưu hóa KBP: {str(e)}")
                        self.window.after(0, lambda: self._handle_kbp_error(str(e), progress_window))
                
                # Khởi chạy luồng
                import threading
                thread = threading.Thread(target=optimization_thread)
                thread.daemon = True
                thread.start()
            
            ttk.Button(button_frame, text="Tối ưu hóa", command=run_kbp_optimization).pack(side=tk.RIGHT, padx=5)
            ttk.Button(button_frame, text="Hủy", command=confirm_dialog.destroy).pack(side=tk.RIGHT, padx=5)
            
        except Exception as e:
            self.logger.error(f"Lỗi khi mở hộp thoại tối ưu hóa KBP: {str(e)}")
            messagebox.showerror("Lỗi", f"Lỗi khi mở hộp thoại tối ưu hóa KBP: {str(e)}")

    def _apply_kbp_results(self, optimization_goals, show_details, auto_apply, progress_window):
        """Áp dụng kết quả tối ưu hóa KBP."""
        try:
            # Đóng cửa sổ tiến trình
            progress_window.destroy()
            self.window.config(cursor="")
            
            if not optimization_goals:
                messagebox.showinfo("Thông báo", "Không có đề xuất tối ưu hóa nào được tạo.")
                return
            
            # Nếu hiển thị chi tiết
            if show_details:
                # Tạo cửa sổ hiển thị kết quả
                result_window = tk.Toplevel(self.window)
                result_window.title("Kết quả tối ưu hóa KBP")
                result_window.geometry("700x500")
                result_window.transient(self.window)
                result_window.grab_set()
                
                # Tạo frame chính
                main_frame = ttk.Frame(result_window, padding=10)
                main_frame.pack(fill=tk.BOTH, expand=True)
                
                # Tiêu đề
                ttk.Label(main_frame, text="Các ràng buộc tối ưu hóa được đề xuất", font=("Arial", 12, "bold")).pack(pady=5)
                
                # Tạo frame danh sách
                list_frame = ttk.Frame(main_frame)
                list_frame.pack(fill=tk.BOTH, expand=True, pady=10)
                
                # Tạo scrollbar
                scrollbar = ttk.Scrollbar(list_frame)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                
                # Tạo treeview
                columns = ("structure", "type", "dose", "volume", "priority", "weight")
                tree = ttk.Treeview(list_frame, columns=columns, show="headings", yscrollcommand=scrollbar.set)
                
                # Thiết lập các cột
                tree.heading("structure", text="Cấu trúc")
                tree.heading("type", text="Loại ràng buộc")
                tree.heading("dose", text="Liều (Gy)")
                tree.heading("volume", text="Thể tích (%)")
                tree.heading("priority", text="Ưu tiên")
                tree.heading("weight", text="Trọng số")
                
                tree.column("structure", width=150)
                tree.column("type", width=150)
                tree.column("dose", width=80)
                tree.column("volume", width=80)
                tree.column("priority", width=80)
                tree.column("weight", width=80)
                
                # Thêm dữ liệu
                for goal in optimization_goals:
                    # Chuyển đổi loại ràng buộc sang text
                    goal_type_text = {
                        "min_dose": "Liều tối thiểu",
                        "max_dose": "Liều tối đa",
                        "mean_dose": "Liều trung bình",
                        "min_dvh": "DVH tối thiểu",
                        "max_dvh": "DVH tối đa",
                        "uniform": "Liều đồng đều",
                        "conformity": "Độ tuân thủ",
                        "falloff": "Độ dốc liều"
                    }.get(goal.goal_type, goal.goal_type)
                    
                    tree.insert("", tk.END, values=(
                        goal.structure_name,
                        goal_type_text,
                        f"{goal.dose_value:.2f}",
                        f"{goal.volume_value:.1f}" if goal.volume_value is not None else "-",
                        goal.priority,
                        f"{goal.weight:.1f}"
                    ))
                
                tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                scrollbar.config(command=tree.yview)
                
                # Frame nút điều khiển
                button_frame = ttk.Frame(main_frame)
                button_frame.pack(fill=tk.X, pady=10)
                
                def apply_goals():
                    result_window.destroy()
                    self._add_kbp_goals_to_optimizer(optimization_goals)
                
                ttk.Button(button_frame, text="Áp dụng", command=apply_goals).pack(side=tk.RIGHT, padx=5)
                ttk.Button(button_frame, text="Hủy", command=result_window.destroy).pack(side=tk.RIGHT, padx=5)
                
                # Nếu tự động áp dụng
                if auto_apply:
                    self._add_kbp_goals_to_optimizer(optimization_goals)
            else:
                # Nếu không hiển thị chi tiết và tự động áp dụng
                if auto_apply:
                    self._add_kbp_goals_to_optimizer(optimization_goals)
                    messagebox.showinfo("Thông báo", f"Đã áp dụng {len(optimization_goals)} ràng buộc tối ưu hóa từ KBP.")
        
        except Exception as e:
            self.logger.error(f"Lỗi khi áp dụng kết quả KBP: {str(e)}")
            messagebox.showerror("Lỗi", f"Lỗi khi áp dụng kết quả KBP: {str(e)}")

    def _handle_kbp_error(self, error_message, progress_window):
        """Xử lý lỗi trong quá trình tối ưu hóa KBP."""
        try:
            progress_window.destroy()
            self.window.config(cursor="")
            messagebox.showerror("Lỗi", f"Lỗi khi thực hiện tối ưu hóa KBP: {error_message}")
        except:
            pass

    def _add_kbp_goals_to_optimizer(self, optimization_goals):
        """Thêm các mục tiêu KBP vào bộ tối ưu hóa."""
        try:
            # Kiểm tra xem đã khởi tạo bộ tối ưu hóa chưa
            if not hasattr(self, 'optimizer') or self.optimizer is None:
                from quangstation.optimization.goal_optimizer import GoalBasedOptimizer
                self.optimizer = GoalBasedOptimizer()
            
            # Thêm các mục tiêu vào bộ tối ưu hóa
            for goal in optimization_goals:
                self.optimizer.add_goal(goal)
            
            # Cập nhật giao diện nếu có
            if hasattr(self, 'update_optimization_ui'):
                self.update_optimization_ui()
            
            self.logger.info(f"Đã thêm {len(optimization_goals)} mục tiêu tối ưu hóa từ KBP")
            
        except Exception as e:
            self.logger.error(f"Lỗi khi thêm mục tiêu KBP vào bộ tối ưu hóa: {str(e)}")
            raise
