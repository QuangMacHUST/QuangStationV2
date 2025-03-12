"""
Module giao diện người dùng cho hiển thị và phân tích liều xạ trị.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import numpy as np
from typing import Dict, List, Optional, Callable, Any, Tuple, Union
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.colors as mcolors
from matplotlib.cm import ScalarMappable
from PIL import Image, ImageTk
import datetime

from quangstation.core.utils.logging import get_logger
from quangstation.clinical.plan_evaluation.dvh import DVHCalculator
from quangstation.core.data_models.dose_data import DoseData

logger = get_logger(__name__)

class DoseView:
    """
    Giao diện hiển thị và phân tích liều xạ trị.
    
    Lớp này cung cấp giao diện để:
    - Hiển thị phân bố liều 2D/3D
    - Điều chỉnh hiển thị liều (colorwash, isodose lines)
    - Hiển thị DVH (Dose Volume Histogram)
    - Phân tích thống kê liều
    """
    
    # Màu mặc định cho đường đẳng liều (isodose)
    ISODOSE_COLORS = {
        100: "#FF0000",  # Đỏ
        95: "#FF3300",   # Cam đỏ
        90: "#FF6600",   # Cam
        80: "#FFCC00",   # Vàng cam
        70: "#FFFF00",   # Vàng
        60: "#99FF00",   # Xanh vàng
        50: "#00FF00",   # Xanh lá
        40: "#00FFCC",   # Xanh lá nhạt
        30: "#00CCFF",   # Xanh dương nhạt
        20: "#0099FF",   # Xanh dương
        10: "#0000FF",   # Xanh dương đậm
        5: "#000099"     # Xanh đen
    }
    
    def __init__(self, parent, main_view):
        """
        Khởi tạo giao diện hiển thị liều.
        
        Args:
            parent: Widget cha
            main_view: Đối tượng view chính (PlanDesignView)
        """
        self.parent = parent
        self.main_view = main_view
        
        # Biến điều khiển UI
        self.dose_opacity_var = tk.DoubleVar(value=0.7)
        self.dose_min_var = tk.DoubleVar(value=0)
        self.dose_max_var = tk.DoubleVar(value=100)
        self.dose_unit_var = tk.StringVar(value="cGy")
        self.dose_normalization_var = tk.DoubleVar(value=100.0)
        
        # Hiển thị đường đẳng liều
        self.show_isodose_var = tk.BooleanVar(value=True)
        self.isodose_levels = [100, 95, 90, 80, 70, 60, 50, 40, 30, 20, 10, 5]
        self.isodose_checkboxes = {}
        self.isodose_vars = {}
        
        # Dữ liệu liều
        self.dose_data = None
        if hasattr(self.main_view, 'dose_data') and self.main_view.dose_data is not None:
            self.dose_data = self.main_view.dose_data
            self._update_dose_range()
        
        # Dữ liệu DVH
        self.dvh_data = None
        
        # Thiết lập UI
        self.setup_ui()
        
        logger.info("Đã khởi tạo giao diện hiển thị liều")
    
    def _update_dose_range(self):
        """Cập nhật phạm vi liều dựa trên dữ liệu liều"""
        if self.dose_data is not None:
            try:
                # Lấy giá trị liều tối đa
                max_dose = np.max(self.dose_data)
                
                # Cập nhật phạm vi liều
                self.dose_max_var.set(max_dose)
                
                # Liều tối thiểu là 5% của liều tối đa
                self.dose_min_var.set(max_dose * 0.05)
                
                logger.info(f"Đã cập nhật phạm vi liều: {self.dose_min_var.get()} - {self.dose_max_var.get()} {self.dose_unit_var.get()}")
            except Exception as e:
                logger.error(f"Lỗi khi cập nhật phạm vi liều: {str(e)}")
    
    def setup_ui(self):
        """Thiết lập giao diện người dùng"""
        # Frame chính
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Chia thành 2 phần: trên và dưới
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=5)
        
        # Chia top_frame thành hai phần: isodose và DVH
        paned_window = ttk.PanedWindow(top_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Frame trái - Hiển thị isodose
        left_frame = ttk.Frame(paned_window)
        paned_window.add(left_frame, weight=2)
        
        # Frame phải - Hiển thị DVH
        right_frame = ttk.Frame(paned_window)
        paned_window.add(right_frame, weight=3)
        
        # Frame điều khiển isodose
        isodose_control_frame = ttk.LabelFrame(left_frame, text="Đường đẳng liều")
        isodose_control_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Thiết lập hiển thị đường đẳng liều
        isodose_scroll_frame = ttk.Frame(isodose_control_frame)
        isodose_scroll_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Thêm thanh cuộn
        isodose_canvas = tk.Canvas(isodose_scroll_frame, height=250)
        scrollbar = ttk.Scrollbar(isodose_scroll_frame, orient="vertical", command=isodose_canvas.yview)
        
        isodose_scrollable_frame = ttk.Frame(isodose_canvas)
        isodose_scrollable_frame.bind(
            "<Configure>",
            lambda e: isodose_canvas.configure(
                scrollregion=isodose_canvas.bbox("all")
            )
        )
        
        isodose_canvas.create_window((0, 0), window=isodose_scrollable_frame, anchor="nw")
        isodose_canvas.configure(yscrollcommand=scrollbar.set)
        
        isodose_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Tạo các checkbox cho mỗi mức isodose
        header_frame = ttk.Frame(isodose_scrollable_frame)
        header_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(header_frame, text="Hiển thị", width=8).pack(side=tk.LEFT)
        ttk.Label(header_frame, text="Mức (%)", width=8).pack(side=tk.LEFT)
        ttk.Label(header_frame, text="Màu", width=8).pack(side=tk.LEFT)
        
        # Hiển thị checkbox cho mỗi mức isodose
        for level in self.isodose_levels:
            self.isodose_vars[level] = tk.BooleanVar(value=True)
            
            level_frame = ttk.Frame(isodose_scrollable_frame)
            level_frame.pack(fill=tk.X, padx=5, pady=2)
            
            # Checkbox hiển thị
            checkbox = ttk.Checkbutton(level_frame, variable=self.isodose_vars[level],
                                      command=self.update_dose_display)
            checkbox.pack(side=tk.LEFT, padx=5)
            self.isodose_checkboxes[level] = checkbox
            
            # Nhãn mức isodose
            ttk.Label(level_frame, text=f"{level}%", width=6).pack(side=tk.LEFT, padx=5)
            
            # Hiển thị màu
            color = self.ISODOSE_COLORS.get(level, "#000000")
            color_frame = tk.Frame(level_frame, bg=color, width=20, height=20)
            color_frame.pack(side=tk.LEFT, padx=5)
        
        # Nút điều khiển
        control_buttons_frame = ttk.Frame(isodose_control_frame)
        control_buttons_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(control_buttons_frame, text="Chọn tất cả", command=self.select_all_isodose).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_buttons_frame, text="Bỏ chọn tất cả", command=self.deselect_all_isodose).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_buttons_frame, text="Cập nhật", command=self.update_dose_display).pack(side=tk.LEFT, padx=2)
        
        # Frame hiển thị DVH
        dvh_frame = ttk.LabelFrame(right_frame, text="Biểu đồ Liều-Thể tích (DVH)")
        dvh_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tạo figure cho biểu đồ DVH
        self.dvh_figure = Figure(figsize=(5, 4), dpi=100)
        self.dvh_axes = self.dvh_figure.add_subplot(111)
        self.dvh_canvas = FigureCanvasTkAgg(self.dvh_figure, master=dvh_frame)
        self.dvh_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Tạo thanh công cụ cho biểu đồ
        toolbar_frame = ttk.Frame(dvh_frame)
        toolbar_frame.pack(fill=tk.X, pady=2)
        
        ttk.Button(toolbar_frame, text="Cập nhật DVH", command=self.update_dvh).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar_frame, text="Xuất PDF", command=self.export_dvh_pdf).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar_frame, text="Xuất CSV", command=self.export_dvh_csv).pack(side=tk.LEFT, padx=2)
        
        # Frame điều khiển hiển thị liều trong bottom_frame
        display_control_frame = ttk.LabelFrame(bottom_frame, text="Điều khiển hiển thị liều")
        display_control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Dòng 1: Điều khiển cơ bản
        basic_control_frame = ttk.Frame(display_control_frame)
        basic_control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Độ trong suốt
        ttk.Label(basic_control_frame, text="Độ trong suốt:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Scale(basic_control_frame, from_=0.0, to=1.0, orient=tk.HORIZONTAL, variable=self.dose_opacity_var,
                 command=lambda _: self.update_dose_display()).grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # Chuẩn hóa liều
        ttk.Label(basic_control_frame, text="Chuẩn hóa (%):").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(basic_control_frame, textvariable=self.dose_normalization_var, width=8).grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)
        
        # Đơn vị liều
        ttk.Label(basic_control_frame, text="Đơn vị:").grid(row=0, column=4, sticky=tk.W, padx=5, pady=5)
        unit_combo = ttk.Combobox(basic_control_frame, textvariable=self.dose_unit_var, width=8)
        unit_combo['values'] = ["cGy", "Gy", "%"]
        unit_combo.grid(row=0, column=5, sticky=tk.W, padx=5, pady=5)
        unit_combo.bind('<<ComboboxSelected>>', lambda _: self.update_dose_display())
        
        # Dòng 2: Phạm vi liều
        range_frame = ttk.Frame(display_control_frame)
        range_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Liều tối thiểu
        ttk.Label(range_frame, text="Liều tối thiểu:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(range_frame, textvariable=self.dose_min_var, width=8).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Liều tối đa
        ttk.Label(range_frame, text="Liều tối đa:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(range_frame, textvariable=self.dose_max_var, width=8).grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)
        
        # Nút cập nhật phạm vi
        ttk.Button(range_frame, text="Cập nhật phạm vi", command=self.update_dose_display).grid(row=0, column=4, sticky=tk.W, padx=5, pady=5)
        
        # Khởi tạo hiển thị ban đầu
        self._init_dvh()
        self.update_dose_display()
    
    def _init_dvh(self):
        """Khởi tạo biểu đồ DVH ban đầu"""
        # Xóa các đường cong cũ
        self.dvh_axes.clear()
        
        # Thiết lập tiêu đề và nhãn trục
        self.dvh_axes.set_title('Biểu đồ Liều-Thể tích (DVH)')
        self.dvh_axes.set_xlabel(f'Liều ({self.dose_unit_var.get()})')
        self.dvh_axes.set_ylabel('Thể tích (%)')
        
        # Thiết lập phạm vi
        self.dvh_axes.set_xlim([0, 110])
        self.dvh_axes.set_ylim([0, 105])
        
        # Thêm lưới
        self.dvh_axes.grid(True, linestyle='--', alpha=0.7)
        
        # Cập nhật canvas
        self.dvh_figure.tight_layout()
        self.dvh_canvas.draw()
    
    def update_dose_display(self):
        """Cập nhật hiển thị liều"""
        # Kiểm tra xem có dữ liệu liều không
        if not hasattr(self.main_view, 'dose_data') or self.main_view.dose_data is None:
            logger.warning("Không có dữ liệu liều để hiển thị")
            return
        
        try:
            # Lấy dữ liệu liều từ main_view
            self.dose_data = self.main_view.dose_data
            
            # Gửi thông báo tới main_view để cập nhật hiển thị liều
            if hasattr(self.main_view, 'update_dose_display'):
                # Thu thập các thông số hiển thị
                display_params = {
                    'opacity': self.dose_opacity_var.get(),
                    'min_dose': self.dose_min_var.get(),
                    'max_dose': self.dose_max_var.get(),
                    'unit': self.dose_unit_var.get(),
                    'normalization': self.dose_normalization_var.get(),
                    'show_isodose': self.show_isodose_var.get(),
                    'isodose_levels': {level: self.isodose_vars[level].get() for level in self.isodose_levels},
                    'isodose_colors': self.ISODOSE_COLORS
                }
                
                # Gọi hàm cập nhật hiển thị trong main_view
                self.main_view.update_dose_display(display_params)
                
                logger.info("Đã cập nhật hiển thị liều")
            else:
                logger.warning("Main view không hỗ trợ phương thức update_dose_display")
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật hiển thị liều: {str(e)}")
            messagebox.showerror("Lỗi", f"Lỗi khi cập nhật hiển thị liều: {str(e)}")
    
    def select_all_isodose(self):
        """Chọn tất cả các mức isodose"""
        for level in self.isodose_levels:
            self.isodose_vars[level].set(True)
    
    def deselect_all_isodose(self):
        """Bỏ chọn tất cả các mức isodose"""
        for level in self.isodose_levels:
            self.isodose_vars[level].set(False)
    
    def update_dvh(self):
        """Cập nhật biểu đồ DVH"""
        # Kiểm tra xem có cấu trúc và dữ liệu liều không
        if (not hasattr(self.main_view, 'structures') or not self.main_view.structures or
            not hasattr(self.main_view, 'dose_data') or self.main_view.dose_data is None):
            messagebox.showwarning("Cảnh báo", "Cần có cấu trúc và dữ liệu liều để tính toán DVH")
            return
        
        try:
            # Tính toán DVH
            if hasattr(self.main_view, 'calculate_dvh'):
                self.main_view.calculate_dvh()
                
                # Lấy dữ liệu DVH từ main_view
                if hasattr(self.main_view, 'dvh_data') and self.main_view.dvh_data:
                    self.dvh_data = self.main_view.dvh_data
                    self._plot_dvh()
                else:
                    logger.warning("Không có dữ liệu DVH sau khi tính toán")
            else:
                # Tự tính toán DVH nếu main_view không hỗ trợ
                self._calculate_dvh()
                self._plot_dvh()
            
            logger.info("Đã cập nhật biểu đồ DVH")
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật DVH: {str(e)}")
            messagebox.showerror("Lỗi", f"Lỗi khi cập nhật DVH: {str(e)}")
    
    def _calculate_dvh(self):
        """Tính toán DVH từ dữ liệu liều và cấu trúc"""
        try:
            # Tạo đối tượng DVHCalculator
            dvh_calculator = DVHCalculator()
            
            # Lấy dữ liệu liều từ main_view
            dose_data = self.main_view.dose_data
            
            # Lấy cấu trúc từ main_view
            structures = self.main_view.structures
            
            # Tính DVH cho mỗi cấu trúc
            dvh_results = {}
            for name, mask in structures.items():
                dvh_curve = dvh_calculator.calculate_dvh(dose_data, mask)
                dvh_results[name] = dvh_curve
            
            # Lưu kết quả DVH
            self.dvh_data = dvh_results
            
            logger.info(f"Đã tính toán DVH cho {len(dvh_results)} cấu trúc")
        except Exception as e:
            logger.error(f"Lỗi khi tính toán DVH: {str(e)}")
            raise
    
    def _plot_dvh(self):
        """Vẽ biểu đồ DVH từ dữ liệu có sẵn"""
        if not self.dvh_data:
            logger.warning("Không có dữ liệu DVH để vẽ biểu đồ")
            return
        
        try:
            # Xóa biểu đồ cũ
            self.dvh_axes.clear()
            
            # Thiết lập tiêu đề và nhãn trục
            self.dvh_axes.set_title('Biểu đồ Liều-Thể tích (DVH)')
            self.dvh_axes.set_xlabel(f'Liều ({self.dose_unit_var.get()})')
            self.dvh_axes.set_ylabel('Thể tích (%)')
            
            # Danh sách màu
            colors = plt.cm.tab10.colors
            
            # Vẽ DVH cho mỗi cấu trúc
            for i, (name, dvh_curve) in enumerate(self.dvh_data.items()):
                color = colors[i % len(colors)]
                dose_values = dvh_curve['dose']
                volume_values = dvh_curve['volume']
                
                # Vẽ đường cong DVH
                self.dvh_axes.plot(dose_values, volume_values, 
                                  label=name, color=color, linewidth=2)
            
            # Thiết lập phạm vi
            self.dvh_axes.set_xlim([0, max([1.1 * np.max(d['dose']) for d in self.dvh_data.values()])])
            self.dvh_axes.set_ylim([0, 105])
            
            # Thêm lưới
            self.dvh_axes.grid(True, linestyle='--', alpha=0.7)
            
            # Thêm chú thích
            self.dvh_axes.legend(loc='upper right')
            
            # Cập nhật canvas
            self.dvh_figure.tight_layout()
            self.dvh_canvas.draw()
            
            logger.info("Đã vẽ biểu đồ DVH")
        except Exception as e:
            logger.error(f"Lỗi khi vẽ biểu đồ DVH: {str(e)}")
            raise
    
    def export_dvh_pdf(self):
        """Xuất biểu đồ DVH dưới dạng PDF"""
        if not self.dvh_data:
            messagebox.showwarning("Cảnh báo", "Không có dữ liệu DVH để xuất")
            return
        
        try:
            from matplotlib.backends.backend_pdf import PdfPages
            
            # Mở hộp thoại lưu file
            from tkinter import filedialog
            filepath = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                title="Lưu biểu đồ DVH dưới dạng PDF"
            )
            
            if not filepath:
                return
            
            # Tạo PDF với nhiều trang
            with PdfPages(filepath) as pdf:
                # Trang 1: Biểu đồ DVH
                self.dvh_figure.savefig(pdf, format='pdf')
                
                # Trang 2: Bảng thống kê DVH
                fig_stats = self._create_dvh_stats_figure()
                fig_stats.savefig(pdf, format='pdf')
                
                # Thêm thông tin metadata
                d = pdf.infodict()
                d['Title'] = 'Biểu đồ DVH'
                d['Author'] = 'QuangStation V2'
                d['Subject'] = 'Dose Volume Histogram'
                d['Keywords'] = 'DVH, Radiation Therapy, Dose'
                d['CreationDate'] = datetime.datetime.now()
                d['ModDate'] = datetime.datetime.now()
            
            messagebox.showinfo("Thông báo", f"Đã xuất biểu đồ DVH sang file PDF: {filepath}")
            
            logger.info(f"Đã xuất biểu đồ DVH sang PDF: {filepath}")
        except Exception as e:
            logger.error(f"Lỗi khi xuất biểu đồ DVH sang PDF: {str(e)}")
            messagebox.showerror("Lỗi", f"Lỗi khi xuất biểu đồ DVH sang PDF: {str(e)}")
    
    def _create_dvh_stats_figure(self):
        """Tạo hình ảnh bảng thống kê DVH"""
        fig = Figure(figsize=(8.3, 11.7))  # A4 size
        ax = fig.add_subplot(111)
        
        # Ẩn các trục
        ax.axis('off')
        
        # Tạo dữ liệu bảng
        table_data = [['Cấu trúc', 'D5%', 'D50%', 'D95%', 'Dmax', 'Dmean', 'V80%', 'V90%', 'V95%']]
        
        for name, dvh_curve in self.dvh_data.items():
            # Tính các thống kê DVH
            dose = dvh_curve['dose']
            volume = dvh_curve['volume']
            
            d5 = self._get_dose_at_volume(dose, volume, 5)
            d50 = self._get_dose_at_volume(dose, volume, 50)
            d95 = self._get_dose_at_volume(dose, volume, 95)
            dmax = np.max(dose)
            dmean = np.sum(dose * volume) / np.sum(volume)
            
            v80 = self._get_volume_at_dose(dose, volume, 80)
            v90 = self._get_volume_at_dose(dose, volume, 90)
            v95 = self._get_volume_at_dose(dose, volume, 95)
            
            # Thêm vào bảng
            row = [
                name,
                f"{d5:.2f} {self.dose_unit_var.get()}",
                f"{d50:.2f} {self.dose_unit_var.get()}",
                f"{d95:.2f} {self.dose_unit_var.get()}",
                f"{dmax:.2f} {self.dose_unit_var.get()}",
                f"{dmean:.2f} {self.dose_unit_var.get()}",
                f"{v80:.2f}%",
                f"{v90:.2f}%",
                f"{v95:.2f}%"
            ]
            table_data.append(row)
        
        # Tạo bảng
        ax.table(
            cellText=table_data[1:],
            colLabels=table_data[0],
            loc='center',
            cellLoc='center',
            colWidths=[0.15, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]
        )
        
        # Thêm tiêu đề
        ax.set_title('Thống kê DVH', pad=20, fontsize=16)
        
        # Thêm thông tin phụ
        date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ax.text(0.5, 0.05, f"Ngày tạo: {date_str}", ha='center', transform=ax.transAxes)
        
        fig.tight_layout()
        return fig
    
    def _get_dose_at_volume(self, dose, volume, vol_percent):
        """Lấy giá trị liều tại thể tích cụ thể"""
        from scipy.interpolate import interp1d
        
        # Kiểm tra xem dose và volume có cùng kích thước không
        if len(dose) != len(volume):
            raise ValueError("Dose và volume phải có cùng kích thước")
        
        # Sắp xếp theo thứ tự giảm dần theo volume
        sorted_indices = np.argsort(volume)[::-1]
        sorted_volume = volume[sorted_indices]
        sorted_dose = dose[sorted_indices]
        
        # Tạo hàm nội suy
        interp_func = interp1d(sorted_volume, sorted_dose, bounds_error=False, fill_value=(sorted_dose[-1], sorted_dose[0]))
        
        # Nội suy giá trị
        return float(interp_func(vol_percent))
    
    def _get_volume_at_dose(self, dose, volume, dose_percent):
        """Lấy giá trị thể tích tại liều cụ thể"""
        from scipy.interpolate import interp1d
        
        # Chuẩn hóa dose về %
        max_dose = np.max(dose)
        norm_dose = 100 * dose / max_dose
        
        # Sắp xếp theo thứ tự tăng dần theo dose
        sorted_indices = np.argsort(norm_dose)
        sorted_dose = norm_dose[sorted_indices]
        sorted_volume = volume[sorted_indices]
        
        # Tạo hàm nội suy
        interp_func = interp1d(sorted_dose, sorted_volume, bounds_error=False, fill_value=(sorted_volume[-1], sorted_volume[0]))
        
        # Nội suy giá trị
        return float(interp_func(dose_percent))
    
    def export_dvh_csv(self):
        """Xuất dữ liệu DVH dưới dạng CSV"""
        if not self.dvh_data:
            messagebox.showwarning("Cảnh báo", "Không có dữ liệu DVH để xuất")
            return
        
        try:
            import csv
            
            # Mở hộp thoại lưu file
            from tkinter import filedialog
            filepath = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Lưu dữ liệu DVH dưới dạng CSV"
            )
            
            if not filepath:
                return
            
            # Mở file để ghi
            with open(filepath, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                
                # Viết header
                header = ['Dose']
                for structure_name in self.dvh_data.keys():
                    header.append(f"{structure_name} Volume (%)")
                
                writer.writerow(header)
                
                # Tìm số lượng điểm dữ liệu tối đa
                max_points = max([len(dvh['dose']) for dvh in self.dvh_data.values()])
                
                # Viết dữ liệu
                for i in range(max_points):
                    row = []
                    
                    # Lấy giá trị liều từ cấu trúc đầu tiên
                    first_struct = list(self.dvh_data.keys())[0]
                    if i < len(self.dvh_data[first_struct]['dose']):
                        row.append(self.dvh_data[first_struct]['dose'][i])
                    else:
                        row.append('')
                    
                    # Lấy giá trị thể tích cho mỗi cấu trúc
                    for name, dvh in self.dvh_data.items():
                        if i < len(dvh['volume']):
                            row.append(dvh['volume'][i])
                        else:
                            row.append('')
                    
                    writer.writerow(row)
            
            messagebox.showinfo("Thông báo", f"Đã xuất dữ liệu DVH sang file CSV: {filepath}")
            
            logger.info(f"Đã xuất dữ liệu DVH sang CSV: {filepath}")
        except Exception as e:
            logger.error(f"Lỗi khi xuất dữ liệu DVH sang CSV: {str(e)}")
            messagebox.showerror("Lỗi", f"Lỗi khi xuất dữ liệu DVH sang CSV: {str(e)}")
