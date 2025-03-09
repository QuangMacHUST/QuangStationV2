"""
Module giao diện người dùng cho thiết kế kế hoạch xạ trị.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from typing import Dict, List, Optional, Callable, Any, Union
import os
import json
import threading

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
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        # Nút tạo kế hoạch
        create_btn = ttk.Button(toolbar, text="Tạo kế hoạch", command=self.create_plan)
        create_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        # Nút lưu kế hoạch
        save_btn = ttk.Button(toolbar, text="Lưu kế hoạch", command=self.save_plan)
        save_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        # Nút tải kế hoạch
        load_btn = ttk.Button(toolbar, text="Tải kế hoạch", command=self.load_plan)
        load_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        # Nút tính toán liều
        calculate_btn = ttk.Button(toolbar, text="Tính liều", command=self.calculate_dose)
        calculate_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        # Nút tối ưu hóa
        optimize_btn = ttk.Button(toolbar, text="Tối ưu hóa", command=self.optimize_plan)
        optimize_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        # Nút kiểm tra QA
        qa_btn = ttk.Button(toolbar, text="Kiểm tra QA", command=self.check_plan_qa)
        qa_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        # Nút tạo báo cáo
        report_btn = ttk.Button(toolbar, text="Tạo báo cáo", command=self.create_report)
        report_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        # Nút xuất RT Plan
        export_btn = ttk.Button(toolbar, text="Xuất RT Plan", command=self.export_rt_plan)
        export_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
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
        """Tính toán phân bố liều cho kế hoạch hiện tại."""
        try:
            # Hiển thị hộp thoại với các tùy chọn tính toán
            # TODO: Triển khai hộp thoại tùy chọn
            
            # Tạo đối tượng DoseCalculator
            dose_calculator = DoseCalculator()
            
            # Lấy thông tin kế hoạch
            plan_data = self.get_plan_data()
            
            # Hiển thị thanh tiến trình
            progress_window = tk.Toplevel(self.window)
            progress_window.title("Đang tính toán...")
            progress_window.geometry("300x100")
            progress_window.resizable(False, False)
            
            progress_label = ttk.Label(progress_window, text="Đang tính toán phân bố liều...")
            progress_label.pack(pady=10)
            
            progress_bar = ttk.Progressbar(progress_window, mode='indeterminate')
            progress_bar.pack(fill=tk.X, padx=20, pady=10)
            progress_bar.start()
            
            # Thực hiện tính toán trong một luồng riêng
            def run_calculation():
                try:
                    # Thực hiện tính toán
                    dose_result = dose_calculator.calculate_dose(
                        technique=plan_data.get('technique', '3DCRT'),
                        structures=self.structures
                    )
                    
                    # Khi hoàn thành, cập nhật giao diện
                    self.window.after(0, lambda: self.update_dose_display(dose_result))
                    self.window.after(0, progress_window.destroy)
                except Exception as exc:
                    error_msg = str(exc)
                    self.window.after(0, lambda: messagebox.showerror("Lỗi", f"Lỗi tính toán: {error_msg}"))
                    self.window.after(0, progress_window.destroy)
                    logger.error(f"Lỗi tính toán liều: {error_msg}")
            
            # Khởi động luồng tính toán
            threading.Thread(target=run_calculation, daemon=True).start()
        except Exception as error:
            logger.error(f"Lỗi khi khởi tạo tính toán liều: {str(error)}")
            messagebox.showerror("Lỗi", f"Không thể tính toán liều: {str(error)}")
    
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
        messagebox.showinfo("Thông báo", "Tính năng tạo báo cáo đang được phát triển")
        logger.info("Đã kích hoạt tính năng tạo báo cáo (chưa triển khai)")
    
    def export_rt_plan(self):
        """Xuất kế hoạch xạ trị sang định dạng DICOM RT Plan."""
        messagebox.showinfo("Thông báo", "Tính năng xuất RT Plan đang được phát triển")
        logger.info("Đã kích hoạt tính năng xuất RT Plan (chưa triển khai)")
    
    def find_isocenter(self):
        """Tự động tìm tâm điều trị dựa trên cấu trúc đích."""
        messagebox.showinfo("Thông báo", "Tính năng tìm tâm tự động đang được phát triển")
        logger.info("Đã kích hoạt tính năng tìm tâm tự động (chưa triển khai)")
    
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
        messagebox.showinfo("Thành công", "Đã tính toán phân bố liều")
        logger.info("Đã cập nhật hiển thị phân bố liều")
        # TODO: Cập nhật hiển thị phân bố liều trên giao diện

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
