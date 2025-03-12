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

from quangstation.core.utils.logging import get_logger
from quangstation.core.utils.config import get_config
from quangstation.clinical.planning import create_technique
from quangstation.clinical.dose_calculation.dose_engine_wrapper import DoseCalculator
from quangstation.clinical.plan_evaluation.dvh import DVHCalculator, DVHPlotter

# Import các view module con
from quangstation.gui.views.beam_setup_view import BeamSetupView
from quangstation.gui.views.dose_view import DoseView
from quangstation.gui.views.structure_view import StructureView
from quangstation.gui.views.optimization_view import OptimizationView

logger = get_logger(__name__)

class PlanDesignView:
    """
    Cửa sổ thiết kế kế hoạch xạ trị.
    
    Lớp này là lớp chính quản lý giao diện thiết kế kế hoạch, phối hợp các thành phần:
    - Thiết lập chùm tia (BeamSetupView)
    - Quản lý cấu trúc (StructureView)
    - Hiển thị liều (DoseView)
    - Tối ưu hóa kế hoạch (OptimizationView)
    """
    
    def __init__(self, parent, patient_id: str, structures: Dict[str, np.ndarray] = None, 
                 callback: Callable = None, plan_id: str = None, plan_data: Dict[str, Any] = None):
        """
        Khởi tạo cửa sổ thiết kế kế hoạch.
        
        Args:
            parent: Widget cha
            patient_id: ID bệnh nhân
            structures: Dictionary các cấu trúc {name: mask}
            callback: Hàm callback khi đóng cửa sổ
            plan_id: ID kế hoạch (nếu chỉnh sửa kế hoạch hiện có)
            plan_data: Dữ liệu kế hoạch (nếu chỉnh sửa kế hoạch hiện có)
        """
        self.parent = parent
        self.patient_id = patient_id
        self.structures = structures if structures else {}
        self.callback = callback
        self.plan_id = plan_id
        
        # Biến lưu trữ dữ liệu
        if plan_data:
            self.plan_data = plan_data
        else:
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
        
        # Đối tượng kỹ thuật xạ trị
        self.rt_technique = None
        
        # Đối tượng tính toán liều
        self.dose_calculator = None
        
        # Đối tượng DVH
        self.dvh_calculator = None
        self.dvh_plotter = None
        
        # Sub-views
        self.beam_setup_view = None
        self.dose_view = None
        self.structure_view = None
        self.optimization_view = None
        
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
        """Thiết lập giao diện người dùng"""
        # Frame chính
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Notebook cho các tab
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tạo các tab
        self.setup_plan_tab()
        self.setup_beam_tab()
        self.setup_structure_tab()
        self.setup_dose_tab()
        self.setup_optimization_tab()
        self.setup_evaluation_tab()
        
        # Thanh nút điều khiển
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(control_frame, text="Tính toán liều", command=self.calculate_dose).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Tối ưu kế hoạch", command=self.optimize_plan).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Lưu kế hoạch", command=self.save_plan).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Đóng", command=self.on_close).pack(side=tk.RIGHT, padx=5)
    
    def setup_plan_tab(self):
        """Thiết lập tab thông tin kế hoạch"""
        plan_frame = ttk.Frame(self.notebook)
        self.notebook.add(plan_frame, text="Thông tin kế hoạch")
        
        # Thông tin cơ bản
        info_frame = ttk.LabelFrame(plan_frame, text="Thông tin cơ bản")
        info_frame.pack(fill=tk.X, pady=10, padx=10)
        
        # Tên kế hoạch
        ttk.Label(info_frame, text="Tên kế hoạch:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.plan_name_var = tk.StringVar(value=self.plan_data.get('plan_name', f"Plan_{self.patient_id}"))
        ttk.Entry(info_frame, textvariable=self.plan_name_var).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Liều xạ trị
        ttk.Label(info_frame, text="Tổng liều (Gy):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.total_dose_var = tk.DoubleVar(value=self.plan_data.get('total_dose', 60.0))
        ttk.Entry(info_frame, textvariable=self.total_dose_var).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(info_frame, text="Số phân liều:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.fraction_count_var = tk.IntVar(value=self.plan_data.get('fraction_count', 30))
        ttk.Entry(info_frame, textvariable=self.fraction_count_var).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(info_frame, text="Liều mỗi phân liều (Gy):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.fraction_dose_var = tk.DoubleVar(value=self.plan_data.get('fraction_dose', 2.0))
        ttk.Entry(info_frame, textvariable=self.fraction_dose_var).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Kỹ thuật xạ trị
        technique_frame = ttk.LabelFrame(plan_frame, text="Kỹ thuật xạ trị")
        technique_frame.pack(fill=tk.X, pady=10, padx=10)
        
        ttk.Label(technique_frame, text="Kỹ thuật:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.technique_var = tk.StringVar(value=self.plan_data.get('technique', '3DCRT'))
        technique_combo = ttk.Combobox(technique_frame, textvariable=self.technique_var)
        technique_combo['values'] = ('3DCRT', 'IMRT', 'VMAT', 'SRS', 'SBRT', 'Proton', 'Adaptive')
        technique_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        technique_combo.bind('<<ComboboxSelected>>', self.on_technique_changed)
        
        # Mô tả kế hoạch
        desc_frame = ttk.LabelFrame(plan_frame, text="Mô tả")
        desc_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=10)
        
        self.plan_desc = tk.Text(desc_frame, height=10)
        self.plan_desc.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.plan_desc.insert(tk.END, self.plan_data.get('description', ''))
    
    def setup_beam_tab(self):
        """Thiết lập tab chùm tia"""
        beam_frame = ttk.Frame(self.notebook)
        self.notebook.add(beam_frame, text="Chùm tia")
        
        # Tạo đối tượng quản lý chùm tia
        self.beam_setup_view = BeamSetupView(beam_frame, self)
    
    def setup_structure_tab(self):
        """Thiết lập tab cấu trúc"""
        structure_frame = ttk.Frame(self.notebook)
        self.notebook.add(structure_frame, text="Cấu trúc")
        
        # Tạo đối tượng quản lý cấu trúc
        self.structure_view = StructureView(structure_frame, self)
    
    def setup_dose_tab(self):
        """Thiết lập tab liều"""
        dose_frame = ttk.Frame(self.notebook)
        self.notebook.add(dose_frame, text="Liều")
        
        # Tạo đối tượng hiển thị liều
        self.dose_view = DoseView(dose_frame, self)
    
    def setup_optimization_tab(self):
        """Thiết lập tab tối ưu hóa"""
        optimization_frame = ttk.Frame(self.notebook)
        self.notebook.add(optimization_frame, text="Tối ưu hóa")
        
        # Tạo đối tượng tối ưu hóa
        self.optimization_view = OptimizationView(optimization_frame, self)
    
    def setup_evaluation_tab(self):
        """Thiết lập tab đánh giá kế hoạch"""
        evaluation_frame = ttk.Frame(self.notebook)
        self.notebook.add(evaluation_frame, text="Đánh giá")
        
        # Frame cho DVH
        dvh_frame = ttk.LabelFrame(evaluation_frame, text="Biểu đồ DVH")
        dvh_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=10)
        
        # Tạo biểu đồ DVH
        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.ax.set_title("Biểu đồ liều-thể tích (DVH)")
        self.ax.set_xlabel("Liều (Gy)")
        self.ax.set_ylabel("Thể tích (%)")
        self.ax.grid(True)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=dvh_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Frame cho thống kê DVH
        stats_frame = ttk.LabelFrame(evaluation_frame, text="Thống kê DVH")
        stats_frame.pack(fill=tk.X, pady=10, padx=10)
        
        self.stats_text = tk.Text(stats_frame, height=10)
        self.stats_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def on_technique_changed(self, event):
        """Xử lý khi thay đổi kỹ thuật xạ trị"""
        technique = self.technique_var.get()
        
        # Ánh xạ từ tên kỹ thuật hiển thị sang tên kỹ thuật nội bộ
        technique_map = {
            '3DCRT': 'Conventional3DCRT',
            'IMRT': 'IMRT',
            'VMAT': 'VMAT',
            'SRS': 'Stereotactic',
            'SBRT': 'Stereotactic',
            'Proton': 'ProtonTherapy',
            'Adaptive': 'AdaptiveRT'
        }
        
        # Thiết lập kỹ thuật xạ trị
        self.set_rt_technique(technique_map.get(technique, 'Conventional3DCRT'))
    
    def set_rt_technique(self, technique_name: str):
        """Thiết lập kỹ thuật xạ trị"""
        self.rt_technique = create_technique(technique_name)
        logger.info(f"Đã thiết lập kỹ thuật xạ trị: {technique_name}")
        
        # Cập nhật UI nếu cần
        if hasattr(self, 'beam_setup_view') and self.beam_setup_view:
            self.beam_setup_view.update_for_technique(technique_name)
    
    def calculate_dose(self):
        """Tính toán liều"""
        # Kiểm tra dữ liệu đầu vào
        if not self.plan_data.get('beams'):
            messagebox.showerror("Lỗi", "Vui lòng thiết lập ít nhất một chùm tia trước khi tính toán liều")
            return
        
        # Hiển thị thông báo đang tính toán
        messagebox.showinfo("Thông báo", "Đang tính toán liều. Quá trình này có thể mất vài phút.")
        
        # Tạo đối tượng tính toán liều nếu chưa có
        if not self.dose_calculator:
            self.dose_calculator = DoseCalculator()
        
        # Bắt đầu tính toán trong một thread riêng biệt
        threading.Thread(target=self._calculate_dose_thread).start()
    
    def _calculate_dose_thread(self):
        """Thread tính toán liều"""
        try:
            # Lấy thông tin từ UI
            algorithm = self.plan_data.get('dose_algorithm', 'CCC')
            beams = self.plan_data.get('beams', [])
            
            # Tính toán liều
            self.dose_data = self.dose_calculator.calculate(
                patient_id=self.patient_id,
                beams=beams,
                algorithm=algorithm,
                structures=self.structures
            )
            
            # Tính toán DVH
            self._calculate_dvh()
            
            # Cập nhật UI trong thread chính
            self.window.after(0, self._update_ui_after_dose_calc)
        except Exception as e:
            logger.error(f"Lỗi khi tính toán liều: {str(e)}")
            self.window.after(0, lambda: messagebox.showerror("Lỗi", f"Lỗi khi tính toán liều: {str(e)}"))
    
    def _calculate_dvh(self):
        """Tính toán DVH"""
        if not self.dose_data or not self.structures:
            return
        
        # Tạo đối tượng tính toán DVH nếu chưa có
        if not self.dvh_calculator:
            self.dvh_calculator = DVHCalculator()
        
        # Tính toán DVH cho từng cấu trúc
        self.dvh_data = {}
        for name, structure in self.structures.items():
            self.dvh_data[name] = self.dvh_calculator.calculate(
                dose_matrix=self.dose_data,
                structure_mask=structure
            )
    
    def _update_ui_after_dose_calc(self):
        """Cập nhật UI sau khi tính toán liều hoàn tất"""
        # Cập nhật tab liều
        if self.dose_view:
            self.dose_view.update_dose_display(self.dose_data)
        
        # Cập nhật tab đánh giá
        self._update_dvh_plot()
        self._update_dvh_stats()
        
        # Thông báo hoàn tất
        messagebox.showinfo("Thông báo", "Đã hoàn tất tính toán liều")
    
    def _update_dvh_plot(self):
        """Cập nhật biểu đồ DVH"""
        if not self.dvh_data:
            return
        
        # Tạo đối tượng vẽ DVH nếu chưa có
        if not self.dvh_plotter:
            self.dvh_plotter = DVHPlotter()
        
        # Xóa biểu đồ cũ
        self.ax.clear()
        self.ax.set_title("Biểu đồ liều-thể tích (DVH)")
        self.ax.set_xlabel("Liều (Gy)")
        self.ax.set_ylabel("Thể tích (%)")
        self.ax.grid(True)
        
        # Vẽ DVH cho từng cấu trúc
        for name, dvh in self.dvh_data.items():
            self.dvh_plotter.plot(self.ax, dvh, name)
        
        # Thêm legend
        self.ax.legend(loc='upper right')
        
        # Cập nhật canvas
        self.canvas.draw()
    
    def _update_dvh_stats(self):
        """Cập nhật thống kê DVH"""
        if not self.dvh_data:
            return
        
        # Xóa nội dung cũ
        self.stats_text.delete(1.0, tk.END)
        
        # Hiển thị thống kê cho từng cấu trúc
        for name, dvh in self.dvh_data.items():
            stats = f"--- {name} ---\n"
            stats += f"D95: {dvh.get('D95', 0):.2f} Gy\n"
            stats += f"D90: {dvh.get('D90', 0):.2f} Gy\n"
            stats += f"D50: {dvh.get('D50', 0):.2f} Gy\n"
            stats += f"Dmin: {dvh.get('Dmin', 0):.2f} Gy\n"
            stats += f"Dmean: {dvh.get('Dmean', 0):.2f} Gy\n"
            stats += f"Dmax: {dvh.get('Dmax', 0):.2f} Gy\n"
            stats += f"V95: {dvh.get('V95', 0):.2f}%\n"
            stats += "\n"
            
            self.stats_text.insert(tk.END, stats)
    
    def optimize_plan(self):
        """Tối ưu hóa kế hoạch"""
        # Kiểm tra dữ liệu đầu vào
        if not self.dose_data:
            messagebox.showerror("Lỗi", "Vui lòng tính toán liều trước khi tối ưu hóa kế hoạch")
            return
        
        # Chuyển đến tab tối ưu hóa
        self.notebook.select(4)  # Index của tab tối ưu hóa
        
        # Gọi phương thức tối ưu hóa trong tab tối ưu hóa
        if self.optimization_view:
            self.optimization_view.run_optimization()
    
    def save_plan(self):
        """Lưu kế hoạch"""
        # Lấy dữ liệu từ UI
        plan_data = self._get_plan_data_from_ui()
        
        # Lưu dữ liệu
        from quangstation.clinical.data_management.plan_manager import PlanManager
        plan_manager = PlanManager()
        
        try:
            if self.plan_id:
                # Cập nhật kế hoạch hiện có
                plan_manager.update_plan(self.patient_id, self.plan_id, plan_data)
                messagebox.showinfo("Thông báo", f"Đã cập nhật kế hoạch {self.plan_id}")
            else:
                # Tạo kế hoạch mới
                self.plan_id = plan_manager.save_plan(self.patient_id, plan_data)
                self.window.title(f"Thiết kế kế hoạch xạ trị - Bệnh nhân {self.patient_id} - Kế hoạch {self.plan_id}")
                messagebox.showinfo("Thông báo", f"Đã lưu kế hoạch mới với ID: {self.plan_id}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu kế hoạch: {str(e)}")
            messagebox.showerror("Lỗi", f"Lỗi khi lưu kế hoạch: {str(e)}")
    
    def _get_plan_data_from_ui(self):
        """Lấy dữ liệu kế hoạch từ UI"""
        plan_data = {
            'plan_name': self.plan_name_var.get(),
            'total_dose': self.total_dose_var.get(),
            'fraction_count': self.fraction_count_var.get(),
            'fraction_dose': self.fraction_dose_var.get(),
            'technique': self.technique_var.get(),
            'description': self.plan_desc.get(1.0, tk.END),
            'beams': self.plan_data.get('beams', []),
            'dose_algorithm': self.plan_data.get('dose_algorithm', 'CCC'),
            'created_at': self.plan_data.get('created_at', datetime.now().isoformat()),
            'modified_at': datetime.now().isoformat(),
        }
        
        # Nếu có dữ liệu liều, lưu path
        if self.dose_data is not None:
            plan_data['dose_file'] = f"patient_{self.patient_id}_plan_{self.plan_id or 'new'}_dose.npy"
        
        return plan_data
    
    def on_close(self):
        """Xử lý khi đóng cửa sổ"""
        # Hỏi người dùng có muốn lưu kế hoạch không
        response = messagebox.askyesnocancel("Xác nhận", "Bạn có muốn lưu kế hoạch trước khi đóng không?")
        
        if response is None:  # Cancel
            return
        elif response:  # Yes
            self.save_plan()
        
        # Dọn dẹp tài nguyên
        plt.close(self.fig)
        
        # Gọi callback nếu có
        if self.callback:
            self.callback()
        
        # Đóng cửa sổ
        self.window.destroy() 