#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module hiển thị biểu đồ DVH (Dose Volume Histogram) cho QuangStation V2.
"""

import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.pyplot as plt
from typing import Dict, List, Any, Optional, Tuple

from quangstation.utils.logging import get_logger

class DVHViewer(ttk.Frame):
    """
    Widget hiển thị biểu đồ DVH (Dose Volume Histogram).
    """
    
    def __init__(self, parent):
        """
        Khởi tạo DVH Viewer
        
        Args:
            parent: Widget cha
        """
        super().__init__(parent)
        self.logger = get_logger("DVHViewer")
        
        # Dữ liệu DVH
        self.dvh_data = {}
        self.structures = {}
        self.structure_colors = {}
        
        # Tạo giao diện
        self._create_widgets()
    
    def _create_widgets(self):
        """Tạo các widget cho DVH Viewer"""
        # Frame chính
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame điều khiển
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Nút làm mới
        refresh_button = ttk.Button(control_frame, text="Làm mới", command=self.refresh)
        refresh_button.pack(side=tk.LEFT, padx=5)
        
        # Nút xuất dữ liệu
        export_button = ttk.Button(control_frame, text="Xuất dữ liệu", command=self.export_data)
        export_button.pack(side=tk.LEFT, padx=5)
        
        # Nút hiển thị/ẩn cấu trúc
        self.show_structures_var = tk.BooleanVar(value=True)
        show_structures_check = ttk.Checkbutton(
            control_frame, text="Hiển thị cấu trúc", 
            variable=self.show_structures_var, command=self.refresh
        )
        show_structures_check.pack(side=tk.LEFT, padx=5)
        
        # Nút hiển thị/ẩn PTV
        self.show_ptv_var = tk.BooleanVar(value=True)
        show_ptv_check = ttk.Checkbutton(
            control_frame, text="Hiển thị PTV", 
            variable=self.show_ptv_var, command=self.refresh
        )
        show_ptv_check.pack(side=tk.LEFT, padx=5)
        
        # Nút hiển thị/ẩn lưới
        self.show_grid_var = tk.BooleanVar(value=True)
        show_grid_check = ttk.Checkbutton(
            control_frame, text="Hiển thị lưới", 
            variable=self.show_grid_var, command=self.refresh
        )
        show_grid_check.pack(side=tk.LEFT, padx=5)
        
        # Frame biểu đồ
        chart_frame = ttk.Frame(main_frame)
        chart_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tạo biểu đồ
        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Thêm thanh công cụ
        toolbar_frame = ttk.Frame(chart_frame)
        toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X)
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.update()
        
        # Frame thông tin
        info_frame = ttk.LabelFrame(main_frame, text="Thông tin DVH")
        info_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        # Tạo Text widget để hiển thị thông tin
        self.info_text = tk.Text(info_frame, height=5, wrap=tk.WORD)
        info_scroll = ttk.Scrollbar(info_frame, orient="vertical", command=self.info_text.yview)
        self.info_text.configure(yscrollcommand=info_scroll.set)
        
        self.info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        info_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Thiết lập trạng thái mặc định
        self.info_text.insert(tk.END, "Chưa có dữ liệu DVH. Vui lòng tính toán liều trước.")
        self.info_text.config(state=tk.DISABLED)
        
        # Vẽ biểu đồ trống
        self._draw_empty_chart()
    
    def _draw_empty_chart(self):
        """Vẽ biểu đồ trống"""
        self.ax.clear()
        self.ax.set_title("Biểu đồ DVH")
        self.ax.set_xlabel("Liều (Gy)")
        self.ax.set_ylabel("Thể tích (%)")
        self.ax.set_xlim(0, 100)
        self.ax.set_ylim(0, 100)
        self.ax.grid(self.show_grid_var.get())
        self.canvas.draw()
    
    def set_dvh_data(self, dvh_data: Dict[str, Any], structures: Dict[str, Any] = None, 
                    structure_colors: Dict[str, str] = None):
        """
        Thiết lập dữ liệu DVH
        
        Args:
            dvh_data: Dữ liệu DVH
            structures: Thông tin cấu trúc
            structure_colors: Màu sắc của các cấu trúc
        """
        self.dvh_data = dvh_data or {}
        self.structures = structures or {}
        self.structure_colors = structure_colors or {}
        
        # Làm mới biểu đồ
        self.refresh()
    
    def refresh(self):
        """Làm mới biểu đồ DVH"""
        # Xóa biểu đồ cũ
        self.ax.clear()
        
        # Kiểm tra dữ liệu
        if not self.dvh_data:
            self._draw_empty_chart()
            return
        
        # Thiết lập tiêu đề và nhãn
        self.ax.set_title("Biểu đồ DVH")
        self.ax.set_xlabel("Liều (Gy)")
        self.ax.set_ylabel("Thể tích (%)")
        
        # Vẽ đường DVH cho từng cấu trúc
        max_dose = 0
        for structure_name, dvh in self.dvh_data.items():
            # Kiểm tra xem có hiển thị cấu trúc này không
            if structure_name.startswith("PTV") and not self.show_ptv_var.get():
                continue
            if not structure_name.startswith("PTV") and not self.show_structures_var.get():
                continue
            
            # Lấy dữ liệu DVH
            if isinstance(dvh, dict) and 'dose' in dvh and 'volume' in dvh:
                dose = dvh['dose']
                volume = dvh['volume']
            elif isinstance(dvh, (list, tuple)) and len(dvh) >= 2:
                dose = dvh[0]
                volume = dvh[1]
            else:
                continue
            
            # Chuyển đổi thành mảng numpy nếu cần
            if not isinstance(dose, np.ndarray):
                dose = np.array(dose)
            if not isinstance(volume, np.ndarray):
                volume = np.array(volume)
            
            # Lấy màu sắc
            color = self.structure_colors.get(structure_name, None)
            
            # Vẽ đường DVH
            self.ax.plot(dose, volume, label=structure_name, color=color)
            
            # Cập nhật liều tối đa
            if len(dose) > 0:
                max_dose = max(max_dose, np.max(dose))
        
        # Thiết lập giới hạn trục
        self.ax.set_xlim(0, max_dose * 1.1)
        self.ax.set_ylim(0, 100)
        
        # Hiển thị lưới
        self.ax.grid(self.show_grid_var.get())
        
        # Hiển thị chú thích
        self.ax.legend(loc='upper right')
        
        # Cập nhật canvas
        self.canvas.draw()
        
        # Cập nhật thông tin
        self._update_info_text()
    
    def _update_info_text(self):
        """Cập nhật thông tin DVH"""
        # Xóa nội dung cũ
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)
        
        # Kiểm tra dữ liệu
        if not self.dvh_data:
            self.info_text.insert(tk.END, "Chưa có dữ liệu DVH. Vui lòng tính toán liều trước.")
            self.info_text.config(state=tk.DISABLED)
            return
        
        # Thêm thông tin cho từng cấu trúc
        for structure_name, dvh in self.dvh_data.items():
            # Lấy dữ liệu DVH
            if isinstance(dvh, dict):
                dose = dvh.get('dose', [])
                volume = dvh.get('volume', [])
                metrics = dvh.get('metrics', {})
            else:
                continue
            
            # Chuyển đổi thành mảng numpy nếu cần
            if not isinstance(dose, np.ndarray):
                dose = np.array(dose)
            if not isinstance(volume, np.ndarray):
                volume = np.array(volume)
            
            # Thêm thông tin cấu trúc
            self.info_text.insert(tk.END, f"{structure_name}:\n")
            
            # Thêm các chỉ số DVH
            if metrics:
                for metric_name, metric_value in metrics.items():
                    self.info_text.insert(tk.END, f"  {metric_name}: {metric_value}\n")
            else:
                # Tính các chỉ số cơ bản nếu không có sẵn
                if len(dose) > 0 and len(volume) > 0:
                    max_dose = np.max(dose)
                    mean_dose = np.mean(dose)
                    min_dose = np.min(dose)
                    
                    self.info_text.insert(tk.END, f"  Liều tối đa: {max_dose:.2f} Gy\n")
                    self.info_text.insert(tk.END, f"  Liều trung bình: {mean_dose:.2f} Gy\n")
                    self.info_text.insert(tk.END, f"  Liều tối thiểu: {min_dose:.2f} Gy\n")
            
            self.info_text.insert(tk.END, "\n")
        
        self.info_text.config(state=tk.DISABLED)
    
    def export_data(self):
        """Xuất dữ liệu DVH"""
        # Hiển thị hộp thoại lưu file
        file_path = tk.filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Lưu dữ liệu DVH"
        )
        
        if not file_path:
            return
        
        try:
            # Mở file để ghi
            with open(file_path, 'w') as f:
                # Ghi tiêu đề
                f.write("Structure,Dose (Gy),Volume (%)\n")
                
                # Ghi dữ liệu cho từng cấu trúc
                for structure_name, dvh in self.dvh_data.items():
                    # Lấy dữ liệu DVH
                    if isinstance(dvh, dict) and 'dose' in dvh and 'volume' in dvh:
                        dose = dvh['dose']
                        volume = dvh['volume']
                    elif isinstance(dvh, (list, tuple)) and len(dvh) >= 2:
                        dose = dvh[0]
                        volume = dvh[1]
                    else:
                        continue
                    
                    # Ghi dữ liệu
                    for i in range(len(dose)):
                        f.write(f"{structure_name},{dose[i]},{volume[i]}\n")
            
            # Hiển thị thông báo thành công
            tk.messagebox.showinfo("Thành công", f"Đã xuất dữ liệu DVH vào file {file_path}")
            
        except Exception as e:
            # Hiển thị thông báo lỗi
            tk.messagebox.showerror("Lỗi", f"Không thể xuất dữ liệu DVH: {str(e)}")
            self.logger.error(f"Lỗi khi xuất dữ liệu DVH: {str(e)}")
    
    def update_display(self):
        """Cập nhật hiển thị biểu đồ DVH"""
        self.refresh() 