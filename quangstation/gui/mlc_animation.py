#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module hiển thị MLC chuyển động cho QuangStation V2.
Cung cấp các công cụ hiển thị MLC trong Beam's Eye View (BEV) với hiệu ứng chuyển động.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
import matplotlib.animation as animation
from PIL import Image, ImageTk
import time
import json
from typing import Dict, List, Any, Optional, Tuple, Union
import threading

from quangstation.utils.logging import get_logger

""" Module hiển thị MLC chuyển động cho QuangStation V2"""

logger = get_logger(__name__)

class MLCAnimation:
    """
    Hiển thị chuyển động của MLC (Multi-Leaf Collimator) trong Beam's Eye View.
    """
    
    def __init__(self, parent, beam_data: Dict[str, Any], target_contour: Optional[np.ndarray] = None):
        """
        Khởi tạo lớp hiển thị chuyển động MLC.
        
        Args:
            parent: Widget cha chứa hiển thị
            beam_data: Dữ liệu chùm tia
            target_contour: Contour của mục tiêu (optional)
        """
        self.parent = parent
        self.beam_data = beam_data
        self.target_contour = target_contour
        self.control_points = beam_data.get('control_points', [])
        
        # Đảm bảo có ít nhất các điểm điều khiển tối thiểu
        if not self.control_points or len(self.control_points) < 2:
            self._create_default_control_points()
        
        # Khởi tạo các biến thành viên
        self.animation = None
        self.is_playing = False
        self.frame_index = 0
        self.delay = 100  # ms
        self.fig = None
        self.ax = None
        self.canvas = None
        self.play_button = None
        self.slider = None
        self.slider_var = None
        self.info_label = None
        
        # Tạo UI
        self._create_ui()
    
    def _create_default_control_points(self):
        """Tạo các điểm điều khiển mặc định nếu không có."""
        # Tạo MLC mặc định (mở)
        default_mlc = self._create_default_mlc()
        
        # Tạo các điểm điều khiển
        self.control_points = [
            {
                "index": 0,
                "mlc_positions": default_mlc,
                "rel_time": 0.0
            },
            {
                "index": 1,
                "mlc_positions": default_mlc,
                "rel_time": 1.0
            }
        ]
    
    def _create_default_mlc(self) -> List[Dict[str, float]]:
        """
        Tạo vị trí MLC mặc định (mở hoàn toàn).
        
        Returns:
            List[Dict[str, float]]: Danh sách các vị trí MLC
        """
        mlc = []
        leaf_width = 5.0  # mm
        
        # Giả sử có 60 lá (30 cặp)
        num_leaves = 60
        field_size_y = 200.0  # mm
        
        # Tính toán vị trí bắt đầu
        start_y = -field_size_y / 2
        
        for i in range(num_leaves):
            leaf_index = i + 1
            side = "A" if i < num_leaves // 2 else "B"
            leaf_y = start_y + (i % (num_leaves // 2)) * leaf_width
            
            # Lá bên A (trái) hoàn toàn rút vào bên trái
            # Lá bên B (phải) hoàn toàn rút vào bên phải
            leaf_position = {
                "leaf_index": leaf_index,
                "side": side,
                "y_position": leaf_y,
                "x_position": -100.0 if side == "A" else 100.0
            }
            
            mlc.append(leaf_position)
        
        return mlc
    
    def _create_ui(self):
        """Tạo giao diện cho animation MLC."""
        # Main frame
        self.main_frame = ttk.Frame(self.parent)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tạo figure và canvas Matplotlib
        self.fig = Figure(figsize=(8, 6), dpi=100)
        self.ax = self.fig.add_subplot(111)
        
        # Cài đặt trục
        self.ax.set_aspect('equal')
        self.ax.set_xlabel('X (mm)')
        self.ax.set_ylabel('Y (mm)')
        self.ax.set_title('Multi-Leaf Collimator (MLC) Animation')
        
        # Thiết lập giới hạn trục
        field_size = 200  # mm
        self.ax.set_xlim(-field_size/2 - 20, field_size/2 + 20)
        self.ax.set_ylim(-field_size/2 - 20, field_size/2 + 20)
        
        # Vẽ contour mục tiêu nếu có
        if self.target_contour is not None:
            self._plot_target()
        
        # Vẽ field boundary
        self._plot_field_boundary()
        
        # Canvas matplotlib
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.main_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Frame cho điều khiển
        controls_frame = ttk.Frame(self.main_frame)
        controls_frame.pack(fill=tk.X, pady=10)
        
        # Nút Play/Pause
        self.play_button = ttk.Button(controls_frame, text="▶ Play", command=self.toggle_play)
        self.play_button.pack(side=tk.LEFT, padx=5)
        
        # Slider time
        slider_frame = ttk.Frame(controls_frame)
        slider_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        
        self.slider_var = tk.DoubleVar()
        self.slider = ttk.Scale(
            slider_frame, 
            from_=0, 
            to=len(self.control_points)-1, 
            orient=tk.HORIZONTAL,
            variable=self.slider_var,
            command=self.on_slider_change
        )
        self.slider.pack(fill=tk.X, expand=True)
        
        # Label thông tin
        self.info_label = ttk.Label(
            controls_frame, 
            text=f"Frame: 1/{len(self.control_points)}",
            font=('Helvetica', 10)
        )
        self.info_label.pack(side=tk.RIGHT, padx=5)
        
        # Nút điều khiển tốc độ
        speed_frame = ttk.Frame(controls_frame)
        speed_frame.pack(side=tk.RIGHT, padx=10)
        
        ttk.Label(speed_frame, text="Tốc độ:").pack(side=tk.LEFT)
        
        speed_slow = ttk.Button(speed_frame, text="0.5x", command=lambda: self.set_speed(0.5))
        speed_slow.pack(side=tk.LEFT, padx=2)
        
        speed_normal = ttk.Button(speed_frame, text="1x", command=lambda: self.set_speed(1.0))
        speed_normal.pack(side=tk.LEFT, padx=2)
        
        speed_fast = ttk.Button(speed_frame, text="2x", command=lambda: self.set_speed(2.0))
        speed_fast.pack(side=tk.LEFT, padx=2)
        
        # Toolbar Matplotlib
        toolbar = NavigationToolbar2Tk(self.canvas, self.main_frame)
        toolbar.update()
        
        # Vẽ frame đầu tiên
        self._update_frame(0)
    
    def _plot_target(self):
        """Vẽ contour mục tiêu."""
        if self.target_contour is None:
            return
            
        # Vẽ contour với màu đỏ
        self.ax.contour(self.target_contour, colors='red', levels=[0.5])
    
    def _plot_field_boundary(self):
        """Vẽ biên của field."""
        field_size = 200  # mm
        rect = Rectangle(
            (-field_size/2, -field_size/2), 
            field_size, 
            field_size, 
            linewidth=2, 
            edgecolor='blue', 
            facecolor='none', 
            linestyle='--'
        )
        self.ax.add_patch(rect)
    
    def _update_frame(self, frame_index):
        """
        Cập nhật hiển thị MLC cho một frame cụ thể.
        
        Args:
            frame_index: Index của control point để hiển thị
        """
        # Đảm bảo index nằm trong phạm vi
        if frame_index < 0 or frame_index >= len(self.control_points):
            return
            
        self.frame_index = frame_index
        
        # Xóa MLC hiện tại
        self.ax.clear()
        
        # Vẽ lại contour và field boundary
        if self.target_contour is not None:
            self._plot_target()
        self._plot_field_boundary()
        
        # Thiết lập lại các tham số trục
        field_size = 200  # mm
        self.ax.set_xlim(-field_size/2 - 20, field_size/2 + 20)
        self.ax.set_ylim(-field_size/2 - 20, field_size/2 + 20)
        self.ax.set_aspect('equal')
        self.ax.set_xlabel('X (mm)')
        self.ax.set_ylabel('Y (mm)')
        self.ax.set_title('Multi-Leaf Collimator (MLC) Animation')
        
        # Lấy dữ liệu MLC của frame hiện tại
        control_point = self.control_points[frame_index]
        mlc_positions = control_point.get('mlc_positions', [])
        
        # Vẽ các lá MLC
        for leaf in mlc_positions:
            side = leaf.get('side', 'A')
            x_pos = leaf.get('x_position', 0)
            y_pos = leaf.get('y_position', 0)
            leaf_width = 5.0  # mm
            
            # Xác định chiều dài và vị trí của lá
            if side == 'A':  # Bên trái
                width = x_pos + field_size/2
                x = -field_size/2
            else:  # Bên phải (B)
                width = field_size/2 - x_pos
                x = x_pos
            
            # Vẽ lá MLC
            rect = Rectangle(
                (x, y_pos), 
                width, 
                leaf_width, 
                linewidth=1, 
                edgecolor='black', 
                facecolor='gray', 
                alpha=0.7
            )
            self.ax.add_patch(rect)
        
        # Cập nhật canvas
        self.canvas.draw()
        
        # Cập nhật thông tin
        self.info_label.config(text=f"Frame: {frame_index+1}/{len(self.control_points)}")
        
        # Cập nhật slider nếu không đang kéo
        self.slider_var.set(frame_index)
    
    def toggle_play(self):
        """Chuyển đổi trạng thái phát/tạm dừng animation."""
        if self.is_playing:
            self.stop_animation()
        else:
            self.start_animation()
    
    def start_animation(self):
        """Bắt đầu phát animation."""
        self.is_playing = True
        self.play_button.config(text="⏸ Pause")
        
        # Bắt đầu từ frame hiện tại
        current_frame = int(self.slider_var.get())
        
        def animate():
            while self.is_playing:
                # Cập nhật frame
                current_frame = self.frame_index
                next_frame = (current_frame + 1) % len(self.control_points)
                
                # Cập nhật UI trong thread chính
                self.parent.after(0, lambda: self._update_frame(next_frame))
                
                # Tạm dừng
                time.sleep(self.delay / 1000)
        
        # Chạy animation trong thread riêng
        self.animation_thread = threading.Thread(target=animate)
        self.animation_thread.daemon = True
        self.animation_thread.start()
    
    def stop_animation(self):
        """Tạm dừng animation."""
        self.is_playing = False
        self.play_button.config(text="▶ Play")
    
    def on_slider_change(self, value):
        """
        Xử lý sự kiện khi slider thay đổi.
        
        Args:
            value: Giá trị mới của slider
        """
        if not self.is_playing:
            frame_index = int(float(value))
            self._update_frame(frame_index)
    
    def set_speed(self, speed_factor):
        """
        Thay đổi tốc độ animation.
        
        Args:
            speed_factor: Hệ số tốc độ (0.5 = chậm, 1.0 = bình thường, 2.0 = nhanh)
        """
        base_delay = 100  # ms
        self.delay = base_delay / speed_factor
    
    def interpolate_mlc(self, t):
        """
        Nội suy vị trí MLC tại thời điểm t (0-1).
        
        Args:
            t: Thời gian tương đối (0-1)
            
        Returns:
            List[Dict[str, float]]: Vị trí MLC được nội suy
        """
        if len(self.control_points) < 2:
            return self.control_points[0].get('mlc_positions', []) if self.control_points else []
        
        # Tìm các điểm điều khiển kề nhau
        cp1 = None
        cp2 = None
        t1 = 0
        t2 = 1
        
        for i, cp in enumerate(self.control_points):
            cp_time = cp.get('rel_time', i / (len(self.control_points) - 1))
            
            if cp_time <= t:
                cp1 = cp
                t1 = cp_time
            
            if cp_time >= t and cp2 is None:
                cp2 = cp
                t2 = cp_time
        
        # Xử lý trường hợp đặc biệt
        if cp1 is None:
            return self.control_points[0].get('mlc_positions', [])
        if cp2 is None:
            return self.control_points[-1].get('mlc_positions', [])
        if cp1 == cp2:
            return cp1.get('mlc_positions', [])
        
        # Nội suy tuyến tính
        weight = (t - t1) / (t2 - t1) if t2 > t1 else 0
        
        mlc1 = cp1.get('mlc_positions', [])
        mlc2 = cp2.get('mlc_positions', [])
        
        # Tạo dictionary để tra cứu nhanh
        mlc1_dict = {(leaf.get('leaf_index'), leaf.get('side')): leaf for leaf in mlc1}
        mlc2_dict = {(leaf.get('leaf_index'), leaf.get('side')): leaf for leaf in mlc2}
        
        # Tạo MLC được nội suy
        interpolated_mlc = []
        
        # Kết hợp tất cả các khóa
        all_keys = set(mlc1_dict.keys()) | set(mlc2_dict.keys())
        
        for key in all_keys:
            if key in mlc1_dict and key in mlc2_dict:
                # Lá xuất hiện trong cả hai vị trí
                leaf1 = mlc1_dict[key]
                leaf2 = mlc2_dict[key]
                
                # Nội suy vị trí x
                x1 = leaf1.get('x_position', 0)
                x2 = leaf2.get('x_position', 0)
                x_interp = x1 + weight * (x2 - x1)
                
                # Tạo lá mới với vị trí nội suy
                new_leaf = {
                    'leaf_index': leaf1.get('leaf_index'),
                    'side': leaf1.get('side'),
                    'y_position': leaf1.get('y_position'),
                    'x_position': x_interp
                }
                
                interpolated_mlc.append(new_leaf)
            elif key in mlc1_dict:
                # Lá chỉ xuất hiện trong vị trí 1
                interpolated_mlc.append(mlc1_dict[key])
            else:
                # Lá chỉ xuất hiện trong vị trí 2
                interpolated_mlc.append(mlc2_dict[key])
        
        return interpolated_mlc
    
    def save_animation(self, filename=None):
        """
        Lưu animation thành file GIF.
        
        Args:
            filename: Đường dẫn file để lưu
        """
        if filename is None:
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".gif",
                filetypes=[("GIF files", "*.gif"), ("All files", "*.*")]
            )
            
            if not filename:
                return
        
        # Tạm dừng animation hiện tại
        was_playing = self.is_playing
        if was_playing:
            self.stop_animation()
        
        try:
            # Tạo figure mới để lưu
            fig = Figure(figsize=(8, 6), dpi=100)
            ax = fig.add_subplot(111)
            
            def update_frame(frame_index):
                ax.clear()
                
                # Vẽ lại contour và field boundary
                if self.target_contour is not None:
                    ax.contour(self.target_contour, colors='red', levels=[0.5])
                
                field_size = 200  # mm
                rect = Rectangle(
                    (-field_size/2, -field_size/2), 
                    field_size, 
                    field_size, 
                    linewidth=2, 
                    edgecolor='blue', 
                    facecolor='none', 
                    linestyle='--'
                )
                ax.add_patch(rect)
                
                # Thiết lập lại các tham số trục
                ax.set_xlim(-field_size/2 - 20, field_size/2 + 20)
                ax.set_ylim(-field_size/2 - 20, field_size/2 + 20)
                ax.set_aspect('equal')
                ax.set_xlabel('X (mm)')
                ax.set_ylabel('Y (mm)')
                ax.set_title('Multi-Leaf Collimator (MLC) Animation')
                
                # Nội suy MLC
                t = frame_index / (20 - 1)  # 20 frames
                mlc_positions = self.interpolate_mlc(t)
                
                # Vẽ các lá MLC
                for leaf in mlc_positions:
                    side = leaf.get('side', 'A')
                    x_pos = leaf.get('x_position', 0)
                    y_pos = leaf.get('y_position', 0)
                    leaf_width = 5.0  # mm
                    
                    # Xác định chiều dài và vị trí của lá
                    if side == 'A':  # Bên trái
                        width = x_pos + field_size/2
                        x = -field_size/2
                    else:  # Bên phải (B)
                        width = field_size/2 - x_pos
                        x = x_pos
                    
                    # Vẽ lá MLC
                    rect = Rectangle(
                        (x, y_pos), 
                        width, 
                        leaf_width, 
                        linewidth=1, 
                        edgecolor='black', 
                        facecolor='gray', 
                        alpha=0.7
                    )
                    ax.add_patch(rect)
                
                return []
            
            # Tạo animation
            ani = animation.FuncAnimation(
                fig, 
                update_frame, 
                frames=20,  # 20 frames
                interval=100,
                blit=True
            )
            
            # Lưu animation
            ani.save(filename, writer='pillow', fps=10)
            
            messagebox.showinfo("Thành công", f"Đã lưu animation vào: {filename}")
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu animation: {str(e)}")
            messagebox.showerror("Lỗi", f"Không thể lưu animation: {str(e)}")
        
        # Khôi phục trạng thái phát
        if was_playing:
            self.start_animation()
    
    def on_close(self):
        """Dọn dẹp khi đóng cửa sổ."""
        self.stop_animation()
        self.main_frame.destroy() 