#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Hộp thoại tính toán liều cho QuangStation V2.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, Callable, Optional
import threading
import time
import numpy as np

class DoseDialog:
    """
    Lớp hiển thị hộp thoại tính toán liều xạ trị.
    """
    
    def __init__(self, parent, plan_data=None, callback=None, title="Tính toán liều xạ trị"):
        """
        Khởi tạo hộp thoại.
        
        Args:
            parent: Widget cha (thường là cửa sổ chính)
            plan_data: Dữ liệu kế hoạch (nếu có)
            callback: Hàm callback khi tính toán xong
            title: Tiêu đề hộp thoại
        """
        self.parent = parent
        self.plan_data = plan_data or {}
        self.callback = callback
        self.title = title
        self.calculation_thread = None
        self.calculation_cancelled = False
        
        # Tạo cửa sổ dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("550x450")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Tạo UI
        self._create_widgets()
    
    def _create_widgets(self):
        """Tạo các phần tử giao diện"""
        main_frame = ttk.Frame(self.dialog, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tiêu đề
        ttk.Label(main_frame, text="Thiết lập tính toán liều", font=('Helvetica', 12, 'bold')).pack(pady=10)
        
        # Frame chứa các tùy chọn tính toán
        options_frame = ttk.LabelFrame(main_frame, text="Tùy chọn tính toán")
        options_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Grid cho các tùy chọn
        option_grid = ttk.Frame(options_frame)
        option_grid.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Thuật toán tính liều
        ttk.Label(option_grid, text="Thuật toán:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.algorithm_var = tk.StringVar(value="CCC")
        ttk.Combobox(option_grid, textvariable=self.algorithm_var, 
                    values=["CCC", "AxB", "AAA", "Monte Carlo"], 
                    state="readonly", width=20).grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # Độ phân giải lưới liều
        ttk.Label(option_grid, text="Độ phân giải lưới liều (mm):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.grid_size_var = tk.DoubleVar(value=2.5)
        ttk.Combobox(option_grid, textvariable=self.grid_size_var, 
                    values=[1.0, 2.0, 2.5, 3.0, 5.0], 
                    width=10).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Tính liều ngoài điểm quan tâm
        ttk.Label(option_grid, text="Tính liều ngoài ROI:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.outside_roi_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(option_grid, variable=self.outside_roi_var).grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # Độ chính xác
        ttk.Label(option_grid, text="Độ chính xác:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.accuracy_var = tk.StringVar(value="standard")
        ttk.Combobox(option_grid, textvariable=self.accuracy_var, 
                    values=["low", "standard", "high"], 
                    state="readonly", width=15).grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # Số lượng thread
        ttk.Label(option_grid, text="Số lượng thread CPU:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.thread_var = tk.IntVar(value=4)
        thread_spinner = ttk.Spinbox(option_grid, from_=1, to=16, textvariable=self.thread_var, width=5)
        thread_spinner.grid(row=4, column=1, sticky=tk.W, pady=5)
        
        # Sử dụng GPU
        ttk.Label(option_grid, text="Sử dụng GPU (nếu có):").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.gpu_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(option_grid, variable=self.gpu_var).grid(row=5, column=1, sticky=tk.W, pady=5)
        
        # Thiết bị GPU
        ttk.Label(option_grid, text="Thiết bị GPU:").grid(row=6, column=0, sticky=tk.W, pady=5)
        self.device_var = tk.StringVar(value="auto")
        ttk.Combobox(option_grid, textvariable=self.device_var, 
                    values=["auto", "cuda:0", "cuda:1"], 
                    width=10).grid(row=6, column=1, sticky=tk.W, pady=5)
        
        # Thông tin ước tính
        info_frame = ttk.LabelFrame(main_frame, text="Thông tin ước tính")
        info_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(info_frame, text="Ước tính thời gian tính toán:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        ttk.Label(info_frame, text="~2-5 phút").grid(row=0, column=1, sticky=tk.W, padx=10, pady=5)
        
        ttk.Label(info_frame, text="Dung lượng bộ nhớ cần thiết:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        ttk.Label(info_frame, text="~1.2 GB").grid(row=1, column=1, sticky=tk.W, padx=10, pady=5)
        
        # Thanh tiến trình
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=10)
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress = ttk.Progressbar(progress_frame, orient="horizontal", 
                                       length=100, mode="determinate", 
                                       variable=self.progress_var)
        self.progress.pack(fill=tk.X)
        
        # Label hiển thị trạng thái
        self.status_var = tk.StringVar(value="Sẵn sàng tính toán")
        self.status_label = ttk.Label(progress_frame, textvariable=self.status_var)
        self.status_label.pack(anchor=tk.W, pady=5)
        
        # Frame chứa các nút
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # Nút hủy và tính toán
        self.cancel_button = ttk.Button(button_frame, text="Hủy", command=self._on_cancel)
        self.cancel_button.pack(side=tk.RIGHT, padx=5)
        
        self.calculate_button = ttk.Button(button_frame, text="Bắt đầu tính toán", command=self._on_calculate)
        self.calculate_button.pack(side=tk.RIGHT, padx=5)
    
    def _on_calculate(self):
        """Xử lý khi người dùng bấm nút tính toán"""
        # Lấy các tùy chọn tính toán
        options = {
            "algorithm": self.algorithm_var.get(),
            "grid_size": self.grid_size_var.get(),
            "outside_roi": self.outside_roi_var.get(),
            "accuracy": self.accuracy_var.get(),
            "num_threads": self.thread_var.get(),
            "use_gpu": self.gpu_var.get(),
            "device": self.device_var.get()
        }
        
        # Disable nút tính toán
        self.calculate_button.configure(state="disabled")
        
        # Reset biến hủy
        self.calculation_cancelled = False
        
        # Bắt đầu luồng tính toán
        self.calculation_thread = threading.Thread(target=self._calculate_dose, args=(options,))
        self.calculation_thread.daemon = True
        self.calculation_thread.start()
    
    def _on_cancel(self):
        """Xử lý khi người dùng bấm nút hủy"""
        if self.calculation_thread and self.calculation_thread.is_alive():
            # Đánh dấu hủy
            self.calculation_cancelled = True
            self.status_var.set("Đang hủy tính toán...")
        else:
            # Đóng dialog
            self.dialog.destroy()
    
    def _calculate_dose(self, options):
        """
        Tính toán liều trong một luồng riêng biệt
        
        Args:
            options: Tùy chọn tính toán
        """
        try:
            # Cập nhật trạng thái
            self._update_ui("Đang chuẩn bị tính toán...", 5)
            
            # Mô phỏng quá trình tính toán
            steps = [
                ("Đang tải dữ liệu CT...", 5, 10),
                ("Đang chuẩn bị hình học mô giả...", 10, 25),
                ("Đang tính toán liều chùm tia 1/3...", 25, 40),
                ("Đang tính toán liều chùm tia 2/3...", 40, 60),
                ("Đang tính toán liều chùm tia 3/3...", 60, 80),
                ("Đang tính tổng liều...", 80, 90),
                ("Đang lưu kết quả...", 90, 100)
            ]
            
            # Thực hiện các bước tính toán
            for step_text, start_progress, end_progress in steps:
                # Kiểm tra hủy
                if self.calculation_cancelled:
                    self._update_ui("Tính toán đã bị hủy", 0)
                    self._enable_calculate_button()
                    return
                
                # Cập nhật trạng thái
                self._update_ui(step_text, start_progress)
                
                # Mô phỏng tính toán
                progress_step = (end_progress - start_progress) / 10
                for i in range(10):
                    if self.calculation_cancelled:
                        self._update_ui("Tính toán đã bị hủy", 0)
                        self._enable_calculate_button()
                        return
                    
                    progress = start_progress + i * progress_step
                    self._update_ui(step_text, progress)
                    time.sleep(0.2)  # Giả lập thời gian xử lý
            
            # Hoàn thành
            self._update_ui("Tính toán hoàn tất!", 100)
            
            # Tạo dữ liệu giả
            dose_data = np.random.rand(100, 100, 100) * 70  # Tạo dữ liệu giả
            dose_metadata = {
                "algorithm": options["algorithm"],
                "grid_size": options["grid_size"],
                "calculation_time": "00:02:34",
                "calculation_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "options": options
            }
            
            # Gọi callback nếu có
            if self.callback:
                self.parent.after(100, lambda: self.callback(dose_data, dose_metadata))
            
            # Đóng dialog sau 1 giây
            self.parent.after(1000, self.dialog.destroy)
            
        except Exception as error:
            # Xử lý lỗi
            error_message = str(error)
            self._update_ui(f"Lỗi: {error_message}", 0)
            self._enable_calculate_button()
            
            # Hiển thị thông báo lỗi
            messagebox.showerror("Lỗi tính toán", f"Đã xảy ra lỗi khi tính toán liều: {error_message}")
    
    def _update_ui(self, status_text, progress_value):
        """Cập nhật giao diện từ luồng tính toán"""
        self.parent.after(0, lambda: self.status_var.set(status_text))
        self.parent.after(0, lambda: self.progress_var.set(progress_value))
    
    def _enable_calculate_button(self):
        """Bật lại nút tính toán"""
        self.parent.after(0, lambda: self.calculate_button.configure(state="normal"))
    
    def show(self):
        """Hiển thị dialog và đợi cho đến khi nó đóng"""
        self.dialog.wait_window() 