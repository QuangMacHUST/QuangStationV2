#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module hiển thị hình ảnh MPR (Multi-Planar Reconstruction) cho QuangStation V2.
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

class MPRViewer(ttk.Frame):
    """
    Widget hiển thị hình ảnh MPR (Multi-Planar Reconstruction).
    """
    
    def __init__(self, parent):
        """
        Khởi tạo MPR Viewer
        
        Args:
            parent: Widget cha
        """
        super().__init__(parent)
        self.logger = get_logger("MPRViewer")
        
        # Dữ liệu hình ảnh
        self.volume = None
        self.structures = {}
        self.structure_colors = {}
        self.dose_matrix = None
        
        # Vị trí slice hiện tại
        self.axial_slice = 0
        self.coronal_slice = 0
        self.sagittal_slice = 0
        
        # Cửa sổ Hounsfield Unit
        self.window_center = 40  # Mặc định cho soft tissue
        self.window_width = 400
        
        # Tạo giao diện
        self._create_widgets()
    
    def _create_widgets(self):
        """Tạo các widget cho MPR Viewer"""
        # Frame chính
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame điều khiển
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Điều khiển window/level
        ttk.Label(control_frame, text="Window:").pack(side=tk.LEFT, padx=5)
        self.window_scale = ttk.Scale(control_frame, from_=1, to=4000, orient=tk.HORIZONTAL, 
                                      command=self._update_window_level)
        self.window_scale.set(self.window_width)
        self.window_scale.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        ttk.Label(control_frame, text="Level:").pack(side=tk.LEFT, padx=5)
        self.level_scale = ttk.Scale(control_frame, from_=-1000, to=1000, orient=tk.HORIZONTAL,
                                    command=self._update_window_level)
        self.level_scale.set(self.window_center)
        self.level_scale.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Frame hiển thị
        display_frame = ttk.Frame(main_frame)
        display_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tạo layout 2x2 cho 3 mặt phẳng + volume rendering/3D
        self.axial_frame = ttk.LabelFrame(display_frame, text="Axial")
        self.axial_frame.grid(row=0, column=0, sticky=tk.NSEW, padx=5, pady=5)
        
        self.coronal_frame = ttk.LabelFrame(display_frame, text="Coronal")
        self.coronal_frame.grid(row=0, column=1, sticky=tk.NSEW, padx=5, pady=5)
        
        self.sagittal_frame = ttk.LabelFrame(display_frame, text="Sagittal")
        self.sagittal_frame.grid(row=1, column=0, sticky=tk.NSEW, padx=5, pady=5)
        
        self.volume_frame = ttk.LabelFrame(display_frame, text="3D View")
        self.volume_frame.grid(row=1, column=1, sticky=tk.NSEW, padx=5, pady=5)
        
        # Đặt trọng số cho các hàng và cột
        display_frame.columnconfigure(0, weight=1)
        display_frame.columnconfigure(1, weight=1)
        display_frame.rowconfigure(0, weight=1)
        display_frame.rowconfigure(1, weight=1)
        
        # Tạo các hình cho từng mặt phẳng
        self._setup_axial_view()
        self._setup_coronal_view()
        self._setup_sagittal_view()
        self._setup_volume_view()
        
        # Thanh trạng thái
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="Sẵn sàng")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # Tạo slider chọn slice
        slider_frame = ttk.Frame(main_frame)
        slider_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        ttk.Label(slider_frame, text="Axial:").pack(side=tk.LEFT, padx=5)
        self.axial_slider = ttk.Scale(slider_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                                     command=self._update_axial_slice)
        self.axial_slider.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        ttk.Label(slider_frame, text="Coronal:").pack(side=tk.LEFT, padx=5)
        self.coronal_slider = ttk.Scale(slider_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                                       command=self._update_coronal_slice)
        self.coronal_slider.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        ttk.Label(slider_frame, text="Sagittal:").pack(side=tk.LEFT, padx=5)
        self.sagittal_slider = ttk.Scale(slider_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                                        command=self._update_sagittal_slice)
        self.sagittal_slider.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
    
    def _setup_axial_view(self):
        """Thiết lập khung xem Axial"""
        self.axial_fig = Figure(figsize=(5, 5), dpi=100)
        self.axial_ax = self.axial_fig.add_subplot(111)
        self.axial_canvas = FigureCanvasTkAgg(self.axial_fig, self.axial_frame)
        self.axial_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Tạo thanh công cụ
        toolbar_frame = ttk.Frame(self.axial_frame)
        toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X)
        toolbar = NavigationToolbar2Tk(self.axial_canvas, toolbar_frame)
        toolbar.update()
        
        # Vẽ hình trống
        self.axial_ax.set_title("Axial")
        self.axial_ax.set_xlabel("X")
        self.axial_ax.set_ylabel("Y")
        self.axial_ax.set_aspect('equal')
        self.axial_canvas.draw()
    
    def _setup_coronal_view(self):
        """Thiết lập khung xem Coronal"""
        self.coronal_fig = Figure(figsize=(5, 5), dpi=100)
        self.coronal_ax = self.coronal_fig.add_subplot(111)
        self.coronal_canvas = FigureCanvasTkAgg(self.coronal_fig, self.coronal_frame)
        self.coronal_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Tạo thanh công cụ
        toolbar_frame = ttk.Frame(self.coronal_frame)
        toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X)
        toolbar = NavigationToolbar2Tk(self.coronal_canvas, toolbar_frame)
        toolbar.update()
        
        # Vẽ hình trống
        self.coronal_ax.set_title("Coronal")
        self.coronal_ax.set_xlabel("X")
        self.coronal_ax.set_ylabel("Z")
        self.coronal_ax.set_aspect('equal')
        self.coronal_canvas.draw()
    
    def _setup_sagittal_view(self):
        """Thiết lập khung xem Sagittal"""
        self.sagittal_fig = Figure(figsize=(5, 5), dpi=100)
        self.sagittal_ax = self.sagittal_fig.add_subplot(111)
        self.sagittal_canvas = FigureCanvasTkAgg(self.sagittal_fig, self.sagittal_frame)
        self.sagittal_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Tạo thanh công cụ
        toolbar_frame = ttk.Frame(self.sagittal_frame)
        toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X)
        toolbar = NavigationToolbar2Tk(self.sagittal_canvas, toolbar_frame)
        toolbar.update()
        
        # Vẽ hình trống
        self.sagittal_ax.set_title("Sagittal")
        self.sagittal_ax.set_xlabel("Y")
        self.sagittal_ax.set_ylabel("Z")
        self.sagittal_ax.set_aspect('equal')
        self.sagittal_canvas.draw()
    
    def _setup_volume_view(self):
        """Thiết lập khung xem 3D"""
        self.volume_fig = Figure(figsize=(5, 5), dpi=100)
        self.volume_ax = self.volume_fig.add_subplot(111, projection='3d')
        self.volume_canvas = FigureCanvasTkAgg(self.volume_fig, self.volume_frame)
        self.volume_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Tạo thanh công cụ
        toolbar_frame = ttk.Frame(self.volume_frame)
        toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X)
        toolbar = NavigationToolbar2Tk(self.volume_canvas, toolbar_frame)
        toolbar.update()
        
        # Vẽ hình trống
        self.volume_ax.set_title("3D View")
        self.volume_ax.set_xlabel("X")
        self.volume_ax.set_ylabel("Y")
        self.volume_ax.set_zlabel("Z")
        self.volume_canvas.draw()
    
    def set_volume(self, volume: np.ndarray):
        """
        Thiết lập dữ liệu volume cho MPR Viewer
        
        Args:
            volume: Mảng 3D của dữ liệu hình ảnh
        """
        self.volume = volume
        
        # Cập nhật slider
        if volume is not None:
            z_size, y_size, x_size = volume.shape
            self.axial_slider.configure(to=z_size-1)
            self.coronal_slider.configure(to=y_size-1)
            self.sagittal_slider.configure(to=x_size-1)
            
            # Đặt giá trị mặc định ở giữa volume
            self.axial_slice = z_size // 2
            self.coronal_slice = y_size // 2
            self.sagittal_slice = x_size // 2
            
            self.axial_slider.set(self.axial_slice)
            self.coronal_slider.set(self.coronal_slice)
            self.sagittal_slider.set(self.sagittal_slice)
        
        # Cập nhật hiển thị
        self.update_display()
    
    def set_structures(self, structures: Dict[str, Any], colors: Dict[str, Tuple[float, float, float]] = None):
        """
        Thiết lập dữ liệu cấu trúc để hiển thị
        
        Args:
            structures: Dictionary của các cấu trúc, với key là tên cấu trúc, value là dữ liệu cấu trúc
            colors: Dictionary ánh xạ tên cấu trúc tới màu sắc (RGB tuple)
        """
        self.structures = structures
        if colors:
            self.structure_colors = colors
        
        # Cập nhật hiển thị
        self.update_display()
    
    def set_dose(self, dose_matrix: np.ndarray):
        """
        Thiết lập dữ liệu liều để hiển thị
        
        Args:
            dose_matrix: Mảng 3D của dữ liệu liều
        """
        self.dose_matrix = dose_matrix
        
        # Cập nhật hiển thị
        self.update_display()
    
    def set_dose_data(self, dose_matrix: np.ndarray):
        """
        Thiết lập dữ liệu liều để hiển thị (alias cho set_dose)
        
        Args:
            dose_matrix: Mảng 3D của dữ liệu liều
        """
        self.set_dose(dose_matrix)
    
    def set_dose_display_params(self, min_dose: float = None, max_dose: float = None, 
                               colormap: str = 'jet', alpha: float = 0.5):
        """
        Thiết lập các tham số hiển thị liều
        
        Args:
            min_dose: Giá trị liều tối thiểu để hiển thị (None để tự động)
            max_dose: Giá trị liều tối đa để hiển thị (None để tự động)
            colormap: Tên của colormap matplotlib để sử dụng
            alpha: Giá trị alpha (độ trong suốt) cho hiển thị liều
        """
        self.min_dose = min_dose
        self.max_dose = max_dose
        self.dose_colormap = colormap
        self.dose_alpha = alpha
        
        # Cập nhật hiển thị nếu đã có dữ liệu liều
        if self.dose_matrix is not None:
            self.update_display()
    
    def toggle_dose_display(self, show_dose: bool = None):
        """
        Bật/tắt hiển thị liều
        
        Args:
            show_dose: True để hiển thị liều, False để ẩn. None để chuyển đổi
        """
        if show_dose is None:
            self.show_dose = not getattr(self, 'show_dose', True)
        else:
            self.show_dose = show_dose
        
        # Cập nhật hiển thị
        self.update_display()
    
    def update_display(self):
        """Cập nhật tất cả các khung hiển thị"""
        self._update_axial_view()
        self._update_coronal_view()
        self._update_sagittal_view()
        self._update_volume_view()
    
    def _update_axial_view(self):
        """Cập nhật khung xem Axial"""
        self.axial_ax.clear()
        
        if self.volume is None:
            self.axial_canvas.draw()
            return
        
        # Lấy lát cắt Axial
        slice_index = min(self.axial_slice, self.volume.shape[0] - 1)
        slice_data = self.volume[slice_index, :, :]
        
        # Áp dụng window/level
        vmin = self.window_center - self.window_width/2
        vmax = self.window_center + self.window_width/2
        
        # Hiển thị lát cắt
        self.axial_ax.imshow(slice_data, cmap='gray', vmin=vmin, vmax=vmax, origin='lower')
        
        # Hiển thị cấu trúc
        self._overlay_structures_on_axial()
        
        # Hiển thị liều
        if hasattr(self, 'show_dose') and self.show_dose and self.dose_matrix is not None:
            if self.dose_matrix.shape == self.volume.shape:
                dose_slice = self.dose_matrix[slice_index, :, :]
                min_val = self.min_dose if self.min_dose is not None else dose_slice.min()
                max_val = self.max_dose if self.max_dose is not None else dose_slice.max()
                
                # Hiển thị slice liều
                self.axial_ax.imshow(dose_slice, cmap=self.dose_colormap, 
                                     alpha=self.dose_alpha, vmin=min_val, vmax=max_val,
                                     origin='lower')
        
        # Cập nhật canvas
        self.axial_canvas.draw()
    
    def _update_coronal_view(self):
        """Cập nhật khung xem Coronal"""
        self.coronal_ax.clear()
        
        if self.volume is None:
            self.coronal_canvas.draw()
            return
        
        # Lấy lát cắt Coronal
        slice_index = min(self.coronal_slice, self.volume.shape[1] - 1)
        slice_data = self.volume[:, slice_index, :]
        
        # Áp dụng window/level
        vmin = self.window_center - self.window_width/2
        vmax = self.window_center + self.window_width/2
        
        # Hiển thị lát cắt
        self.coronal_ax.imshow(slice_data, cmap='gray', vmin=vmin, vmax=vmax, origin='lower')
        
        # Hiển thị cấu trúc
        self._overlay_structures_on_coronal()
        
        # Hiển thị liều
        if hasattr(self, 'show_dose') and self.show_dose and self.dose_matrix is not None:
            if self.dose_matrix.shape == self.volume.shape:
                dose_slice = self.dose_matrix[:, slice_index, :]
                min_val = self.min_dose if self.min_dose is not None else dose_slice.min()
                max_val = self.max_dose if self.max_dose is not None else dose_slice.max()
                
                # Hiển thị slice liều
                self.coronal_ax.imshow(dose_slice, cmap=self.dose_colormap, 
                                      alpha=self.dose_alpha, vmin=min_val, vmax=max_val,
                                      origin='lower')
        
        # Cập nhật canvas
        self.coronal_canvas.draw()
    
    def _update_sagittal_view(self):
        """Cập nhật khung xem Sagittal"""
        self.sagittal_ax.clear()
        
        if self.volume is None:
            self.sagittal_canvas.draw()
            return
        
        # Lấy lát cắt Sagittal
        slice_index = min(self.sagittal_slice, self.volume.shape[2] - 1)
        slice_data = self.volume[:, :, slice_index]
        
        # Áp dụng window/level
        vmin = self.window_center - self.window_width/2
        vmax = self.window_center + self.window_width/2
        
        # Hiển thị lát cắt
        self.sagittal_ax.imshow(slice_data, cmap='gray', vmin=vmin, vmax=vmax, origin='lower')
        
        # Hiển thị cấu trúc
        self._overlay_structures_on_sagittal()
        
        # Hiển thị liều
        if hasattr(self, 'show_dose') and self.show_dose and self.dose_matrix is not None:
            if self.dose_matrix.shape == self.volume.shape:
                dose_slice = self.dose_matrix[:, :, slice_index]
                min_val = self.min_dose if self.min_dose is not None else dose_slice.min()
                max_val = self.max_dose if self.max_dose is not None else dose_slice.max()
                
                # Hiển thị slice liều
                self.sagittal_ax.imshow(dose_slice, cmap=self.dose_colormap, 
                                       alpha=self.dose_alpha, vmin=min_val, vmax=max_val,
                                       origin='lower')
        
        # Cập nhật canvas
        self.sagittal_canvas.draw()
    
    def _update_volume_view(self):
        """Cập nhật khung xem 3D"""
        self.volume_ax.clear()
        
        if self.volume is None:
            self.volume_canvas.draw()
            return
        
        # Tạo hình đại diện cho vị trí lát cắt hiện tại
        z_max, y_max, x_max = self.volume.shape
        
        # Vẽ các đường biên của volume
        x = np.array([0, x_max, x_max, 0, 0, x_max, x_max, 0])
        y = np.array([0, 0, y_max, y_max, 0, 0, y_max, y_max])
        z = np.array([0, 0, 0, 0, z_max, z_max, z_max, z_max])
        
        # Vẽ khung volume
        for i, j in [(0, 1), (1, 2), (2, 3), (3, 0),
                    (4, 5), (5, 6), (6, 7), (7, 4),
                    (0, 4), (1, 5), (2, 6), (3, 7)]:
            self.volume_ax.plot3D([x[i], x[j]], [y[i], y[j]], [z[i], z[j]], 'gray')
        
        # Vẽ lát cắt hiện tại
        self._draw_current_slices()
        
        # Thiết lập các trục
        self.volume_ax.set_xlabel('X')
        self.volume_ax.set_ylabel('Y')
        self.volume_ax.set_zlabel('Z')
        
        # Đặt giới hạn trục
        self.volume_ax.set_xlim(0, x_max)
        self.volume_ax.set_ylim(0, y_max)
        self.volume_ax.set_zlim(0, z_max)
        
        # Đặt góc nhìn
        self.volume_ax.view_init(elev=30, azim=45)
        
        # Cập nhật canvas
        self.volume_canvas.draw()
    
    def _draw_current_slices(self):
        """Vẽ các lát cắt hiện tại trong khung xem 3D"""
        if self.volume is None:
            return
        
        z_max, y_max, x_max = self.volume.shape
        
        # Vẽ lát cắt Axial
        z = self.axial_slice
        x = np.array([0, x_max, x_max, 0])
        y = np.array([0, 0, y_max, y_max])
        z = np.array([z, z, z, z])
        self.volume_ax.plot_trisurf(x, y, z, color='red', alpha=0.3)
        
        # Vẽ lát cắt Coronal
        y = self.coronal_slice
        x = np.array([0, x_max, x_max, 0])
        y = np.array([y, y, y, y])
        z = np.array([0, 0, z_max, z_max])
        self.volume_ax.plot_trisurf(x, y, z, color='green', alpha=0.3)
        
        # Vẽ lát cắt Sagittal
        x = self.sagittal_slice
        x = np.array([x, x, x, x])
        y = np.array([0, y_max, y_max, 0])
        z = np.array([0, 0, z_max, z_max])
        self.volume_ax.plot_trisurf(x, y, z, color='blue', alpha=0.3)
    
    def _overlay_structures_on_axial(self):
        """Hiển thị cấu trúc trên khung xem Axial"""
        if not hasattr(self, 'volume') or self.volume is None or not hasattr(self, 'structures') or not self.structures:
            return
        
        slice_index = min(self.axial_slice, self.volume.shape[0] - 1)
        
        # Hiển thị từng cấu trúc
        for struct_name, struct_data in self.structures.items():
            if 'mask' in struct_data:
                mask = struct_data['mask']
                # Nếu mask có cùng kích thước với volume
                if mask.shape == self.volume.shape:
                    # Lấy lát cắt của mask
                    mask_slice = mask[slice_index, :, :]
                    
                    # Lấy màu cho cấu trúc này
                    color = self.structure_colors.get(struct_name, (1.0, 0.0, 0.0))  # Mặc định là đỏ
                    
                    # Tạo mask màu
                    colored_mask = np.zeros((*mask_slice.shape, 4))
                    colored_mask[mask_slice > 0] = (*color, 0.5)  # Alpha = 0.5 cho trong suốt
                    
                    # Hiển thị mask
                    self.axial_ax.imshow(colored_mask, origin='lower')
    
    def _overlay_structures_on_coronal(self):
        """Hiển thị cấu trúc trên khung xem Coronal"""
        if not hasattr(self, 'volume') or self.volume is None or not hasattr(self, 'structures') or not self.structures:
            return
        
        slice_index = min(self.coronal_slice, self.volume.shape[1] - 1)
        
        # Hiển thị từng cấu trúc
        for struct_name, struct_data in self.structures.items():
            if 'mask' in struct_data:
                mask = struct_data['mask']
                # Nếu mask có cùng kích thước với volume
                if mask.shape == self.volume.shape:
                    # Lấy lát cắt của mask
                    mask_slice = mask[:, slice_index, :]
                    
                    # Lấy màu cho cấu trúc này
                    color = self.structure_colors.get(struct_name, (1.0, 0.0, 0.0))  # Mặc định là đỏ
                    
                    # Tạo mask màu
                    colored_mask = np.zeros((*mask_slice.shape, 4))
                    colored_mask[mask_slice > 0] = (*color, 0.5)  # Alpha = 0.5 cho trong suốt
                    
                    # Hiển thị mask
                    self.coronal_ax.imshow(colored_mask, origin='lower')
    
    def _overlay_structures_on_sagittal(self):
        """Hiển thị cấu trúc trên khung xem Sagittal"""
        if not hasattr(self, 'volume') or self.volume is None or not hasattr(self, 'structures') or not self.structures:
            return
        
        slice_index = min(self.sagittal_slice, self.volume.shape[2] - 1)
        
        # Hiển thị từng cấu trúc
        for struct_name, struct_data in self.structures.items():
            if 'mask' in struct_data:
                mask = struct_data['mask']
                # Nếu mask có cùng kích thước với volume
                if mask.shape == self.volume.shape:
                    # Lấy lát cắt của mask
                    mask_slice = mask[:, :, slice_index]
                    
                    # Lấy màu cho cấu trúc này
                    color = self.structure_colors.get(struct_name, (1.0, 0.0, 0.0))  # Mặc định là đỏ
                    
                    # Tạo mask màu
                    colored_mask = np.zeros((*mask_slice.shape, 4))
                    colored_mask[mask_slice > 0] = (*color, 0.5)  # Alpha = 0.5 cho trong suốt
                    
                    # Hiển thị mask
                    self.sagittal_ax.imshow(colored_mask, origin='lower')
    
    def _update_window_level(self, value=None):
        """Callback khi window/level thay đổi"""
        self.window_width = self.window_scale.get()
        self.window_center = self.level_scale.get()
        
        # Cập nhật hiển thị
        self.update_display()
    
    def _update_axial_slice(self, value=None):
        """Callback khi vị trí lát cắt axial thay đổi"""
        self.axial_slice = int(self.axial_slider.get())
        
        # Cập nhật hiển thị
        self._update_axial_view()
        self._update_volume_view()
    
    def _update_coronal_slice(self, value=None):
        """Callback khi vị trí lát cắt coronal thay đổi"""
        self.coronal_slice = int(self.coronal_slider.get())
        
        # Cập nhật hiển thị
        self._update_coronal_view()
        self._update_volume_view()
    
    def _update_sagittal_slice(self, value=None):
        """Callback khi vị trí lát cắt sagittal thay đổi"""
        self.sagittal_slice = int(self.sagittal_slider.get())
        
        # Cập nhật hiển thị
        self._update_sagittal_view()
        self._update_volume_view() 