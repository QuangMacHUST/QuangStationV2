#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Widget hiển thị hình ảnh y tế cho QuangStation V2.
"""

import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.patches as patches
from typing import Dict, List, Tuple, Optional, Any, Callable

class ImageViewer(ttk.Frame):
    """
    Widget hiển thị hình ảnh y tế với các công cụ điều khiển.
    Hỗ trợ hiển thị hình ảnh DICOM, điều chỉnh cửa sổ/mức (window/level),
    di chuyển lát cắt, đo đạc và vẽ contour.
    """
    
    def __init__(self, parent, **kwargs):
        """
        Khởi tạo widget hiển thị hình ảnh.
        
        Args:
            parent: Widget cha
            **kwargs: Các tham số bổ sung cho Frame
        """
        super().__init__(parent, **kwargs)
        
        # Trạng thái hiển thị
        self.image_data = None  # Dữ liệu hình ảnh 3D (z, y, x)
        self.spacing = [1.0, 1.0, 1.0]  # Khoảng cách voxel (mm)
        self.current_slice = 0  # Lát cắt hiện tại
        self.window_width = 400  # Độ rộng cửa sổ mặc định
        self.window_level = 40   # Mức cửa sổ mặc định
        
        # Contours
        self.contours = {}  # dictionary chứa contours cho từng lát cắt
        self.active_contour = None  # tên contour đang hoạt động
        self.contour_colors = {}  # màu sắc cho từng contour
        
        # Callbacks
        self.on_slice_change_callback = None
        self.on_click_callback = None
        self.on_draw_callback = None
        
        # Trạng thái vẽ
        self.drawing = False
        self.drawing_mode = None  # "pencil", "brush", "eraser", etc.
        self.drawing_size = 1  # kích thước vẽ
        
        # Tạo giao diện
        self._create_widgets()
        
        # Cập nhật kích thước khi thay đổi
        self.bind("<Configure>", self._on_resize)
    
    def _create_widgets(self):
        """Tạo các phần tử giao diện"""
        # Frame chính
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame hiển thị hình ảnh
        image_frame = ttk.Frame(main_frame)
        image_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Tạo figure và axes cho matplotlib
        self.fig = Figure(figsize=(5, 5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_axis_off()
        
        # Tạo canvas để hiển thị figure
        self.canvas = FigureCanvasTkAgg(self.fig, master=image_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Thiết lập sự kiện chuột
        self.canvas.mpl_connect('button_press_event', self._on_mouse_press)
        self.canvas.mpl_connect('button_release_event', self._on_mouse_release)
        self.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)
        self.canvas.mpl_connect('scroll_event', self._on_scroll)
        
        # Frame điều khiển
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        
        # Điều khiển lát cắt
        slice_frame = ttk.LabelFrame(control_frame, text="Lát cắt")
        slice_frame.pack(fill=tk.X, pady=5)
        
        self.slice_var = tk.IntVar(value=0)
        self.slice_slider = ttk.Scale(slice_frame, from_=0, to=99, orient=tk.HORIZONTAL, 
                                     variable=self.slice_var, command=self._on_slice_change)
        self.slice_slider.pack(fill=tk.X, padx=5, pady=5)
        
        self.slice_info = ttk.Label(slice_frame, text="0/0")
        self.slice_info.pack(pady=2)
        
        # Điều khiển cửa sổ/mức
        wl_frame = ttk.LabelFrame(control_frame, text="Cửa sổ/Mức")
        wl_frame.pack(fill=tk.X, pady=5)
        
        window_frame = ttk.Frame(wl_frame)
        window_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(window_frame, text="Cửa sổ:").pack(side=tk.LEFT)
        self.window_var = tk.IntVar(value=self.window_width)
        self.window_slider = ttk.Scale(window_frame, from_=1, to=4000, orient=tk.HORIZONTAL, 
                                      variable=self.window_var, command=self._on_window_change)
        self.window_slider.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5)
        
        level_frame = ttk.Frame(wl_frame)
        level_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(level_frame, text="Mức:").pack(side=tk.LEFT)
        self.level_var = tk.IntVar(value=self.window_level)
        self.level_slider = ttk.Scale(level_frame, from_=-1000, to=3000, orient=tk.HORIZONTAL, 
                                     variable=self.level_var, command=self._on_level_change)
        self.level_slider.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5)
        
        # Nút preset window/level
        preset_frame = ttk.Frame(wl_frame)
        preset_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(preset_frame, text="Phổi", width=8, 
                  command=lambda: self.set_window_level(1500, -600)).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="Xương", width=8, 
                  command=lambda: self.set_window_level(2000, 400)).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="Mô mềm", width=8, 
                  command=lambda: self.set_window_level(400, 40)).pack(side=tk.LEFT, padx=2)
        
        # Điều khiển contour
        contour_frame = ttk.LabelFrame(control_frame, text="Contour")
        contour_frame.pack(fill=tk.X, pady=5)
        
        # Combobox chọn contour
        contour_select_frame = ttk.Frame(contour_frame)
        contour_select_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(contour_select_frame, text="Contour:").pack(side=tk.LEFT)
        self.contour_var = tk.StringVar()
        self.contour_combobox = ttk.Combobox(contour_select_frame, textvariable=self.contour_var, 
                                            state="readonly", width=15)
        self.contour_combobox.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5)
        self.contour_combobox.bind("<<ComboboxSelected>>", self._on_contour_select)
        
        # Nút công cụ contour
        tool_frame = ttk.Frame(contour_frame)
        tool_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(tool_frame, text="Bút", width=6, 
                  command=lambda: self.set_drawing_mode("pencil")).pack(side=tk.LEFT, padx=2)
        ttk.Button(tool_frame, text="Cọ", width=6, 
                  command=lambda: self.set_drawing_mode("brush")).pack(side=tk.LEFT, padx=2)
        ttk.Button(tool_frame, text="Tẩy", width=6, 
                  command=lambda: self.set_drawing_mode("eraser")).pack(side=tk.LEFT, padx=2)
        
        # Kích thước công cụ
        size_frame = ttk.Frame(contour_frame)
        size_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(size_frame, text="Kích thước:").pack(side=tk.LEFT)
        self.size_var = tk.IntVar(value=1)
        ttk.Scale(size_frame, from_=1, to=10, orient=tk.HORIZONTAL, 
                variable=self.size_var, command=self._on_size_change).pack(side=tk.RIGHT, 
                                                                          fill=tk.X, 
                                                                          expand=True, 
                                                                          padx=5)
        
        # Hiển thị trạng thái
        self.status_var = tk.StringVar(value="Sẵn sàng")
        self.status_label = ttk.Label(control_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(fill=tk.X, pady=5)
    
    def set_image_data(self, image_data, spacing=None):
        """
        Thiết lập dữ liệu hình ảnh 3D
        
        Args:
            image_data: Mảng 3D với dạng (z, y, x)
            spacing: Khoảng cách voxel [z, y, x] (mm)
        """
        if image_data is None:
            return
        
        self.image_data = image_data
        if spacing is not None:
            self.spacing = spacing
        
        # Cập nhật slider lát cắt
        num_slices = image_data.shape[0]
        self.slice_slider.configure(from_=0, to=num_slices-1)
        self.slice_var.set(num_slices // 2)
        self.current_slice = num_slices // 2
        
        # Cập nhật thông tin lát cắt
        self.slice_info.configure(text=f"{self.current_slice+1}/{num_slices}")
        
        # Hiển thị hình ảnh
        self._update_image()
    
    def set_contours(self, contours, contour_colors=None):
        """
        Thiết lập dữ liệu contour
        
        Args:
            contours: Dictionary chứa contours cho từng lát cắt
            contour_colors: Dictionary chứa màu sắc cho từng contour
        """
        self.contours = contours
        
        if contour_colors:
            self.contour_colors = contour_colors
        
        # Cập nhật combobox chọn contour
        contour_names = list(contours.keys())
        self.contour_combobox['values'] = contour_names
        
        if contour_names:
            self.contour_var.set(contour_names[0])
            self.active_contour = contour_names[0]
        
        # Cập nhật hiển thị
        self._update_image()
    
    def set_window_level(self, window, level):
        """
        Thiết lập cửa sổ/mức
        
        Args:
            window: Độ rộng cửa sổ
            level: Mức cửa sổ
        """
        self.window_width = window
        self.window_level = level
        
        # Cập nhật slider
        self.window_var.set(window)
        self.level_var.set(level)
        
        # Cập nhật hiển thị
        self._update_image()
    
    def set_drawing_mode(self, mode):
        """
        Thiết lập chế độ vẽ
        
        Args:
            mode: Chế độ vẽ ("pencil", "brush", "eraser", etc.)
        """
        self.drawing_mode = mode
        self.status_var.set(f"Chế độ: {mode}")
    
    def _on_window_change(self, value):
        """Xử lý khi thay đổi độ rộng cửa sổ"""
        self.window_width = int(float(value))
        self._update_image()
    
    def _on_level_change(self, value):
        """Xử lý khi thay đổi mức cửa sổ"""
        self.window_level = int(float(value))
        self._update_image()
    
    def _on_slice_change(self, value):
        """Xử lý khi thay đổi lát cắt"""
        self.current_slice = int(float(value))
        if self.image_data is not None:
            self.slice_info.configure(text=f"{self.current_slice+1}/{self.image_data.shape[0]}")
        self._update_image()
        
        if self.on_slice_change_callback:
            self.on_slice_change_callback(self.current_slice)
    
    def _on_size_change(self, value):
        """Xử lý khi thay đổi kích thước công cụ vẽ"""
        self.drawing_size = int(float(value))
    
    def _on_contour_select(self, event):
        """Xử lý khi chọn contour"""
        self.active_contour = self.contour_var.get()
        self._update_image()
    
    def _on_mouse_press(self, event):
        """Xử lý khi nhấn chuột"""
        if not self.drawing_mode or not self.active_contour:
            return
        
        self.drawing = True
        
        # Gọi callback nếu có
        if self.on_click_callback:
            self.on_click_callback(event.xdata, event.ydata, self.current_slice, self.active_contour)
    
    def _on_mouse_release(self, event):
        """Xử lý khi thả chuột"""
        self.drawing = False
    
    def _on_mouse_move(self, event):
        """Xử lý khi di chuyển chuột"""
        if not self.drawing or not self.drawing_mode or not self.active_contour:
            return
        
        # Gọi callback vẽ nếu có
        if self.on_draw_callback:
            self.on_draw_callback(event.xdata, event.ydata, self.current_slice, 
                                 self.active_contour, self.drawing_mode, self.drawing_size)
    
    def _on_scroll(self, event):
        """Xử lý khi cuộn chuột"""
        if self.image_data is None:
            return
        
        # Thay đổi lát cắt dựa vào hướng cuộn
        direction = 1 if event.button == 'up' else -1
        new_slice = max(0, min(self.current_slice + direction, self.image_data.shape[0] - 1))
        self.slice_var.set(new_slice)
    
    def _on_resize(self, event):
        """Xử lý khi widget thay đổi kích thước"""
        self._update_image()
    
    def _update_image(self):
        """Cập nhật hiển thị hình ảnh với cửa sổ/mức hiện tại"""
        if self.image_data is None:
            return
        
        # Kiểm tra giới hạn lát cắt
        if self.current_slice >= self.image_data.shape[0]:
            self.current_slice = self.image_data.shape[0] - 1
        
        # Lấy lát cắt hiện tại
        img_slice = self.image_data[self.current_slice]
        
        # Áp dụng cửa sổ/mức
        vmin = self.window_level - self.window_width / 2
        vmax = self.window_level + self.window_width / 2
        
        # Xóa axes
        self.ax.clear()
        
        # Hiển thị hình ảnh
        self.ax.imshow(img_slice, cmap='gray', vmin=vmin, vmax=vmax, aspect='equal')
        
        # Hiển thị contours nếu có
        if self.active_contour and self.active_contour in self.contours:
            contour_data = self.contours[self.active_contour]
            # Tìm dữ liệu contour cho lát cắt hiện tại
            if str(self.current_slice) in contour_data:
                slice_contours = contour_data[str(self.current_slice)]
                for contour in slice_contours:
                    # Mỗi contour là một danh sách các điểm (x, y)
                    x = [pt[0] for pt in contour]
                    y = [pt[1] for pt in contour]
                    color = self.contour_colors.get(self.active_contour, 'red')
                    self.ax.plot(x, y, color=color, linewidth=2)
        
        # Tắt trục
        self.ax.set_axis_off()
        
        # Cập nhật canvas
        self.canvas.draw()
    
    def set_callbacks(self, on_slice_change=None, on_click=None, on_draw=None):
        """
        Thiết lập callbacks
        
        Args:
            on_slice_change: Callback khi thay đổi lát cắt
            on_click: Callback khi nhấn chuột
            on_draw: Callback khi vẽ
        """
        self.on_slice_change_callback = on_slice_change
        self.on_click_callback = on_click
        self.on_draw_callback = on_draw 