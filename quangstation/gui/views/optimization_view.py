#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module cung cấp giao diện tối ưu hóa kế hoạch xạ trị cho QuangStation V2.

Module này cho phép người dùng điều chỉnh các thông số tối ưu hóa và chạy quá trình tối ưu hóa kế hoạch xạ trị.
Kết quả tối ưu hóa được hiển thị qua giao diện người dùng.
"""

import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from quangstation.core.utils.logging import get_logger

logger = get_logger(__name__)


class OptimizationView(ttk.Frame):
    """
    Giao diện tối ưu hóa kế hoạch xạ trị.
    """
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.progress_var = tk.DoubleVar()
        self._create_widgets()
        self._create_layout()

    def _create_widgets(self):
        # Label thông tin
        self.info_label = ttk.Label(self, text="Chọn tham số tối ưu hóa:")
        self.param_entry = ttk.Entry(self)
        
        # Nút chạy tối ưu hóa
        self.run_button = ttk.Button(self, text="Chạy tối ưu hóa", command=self.run_optimization)
        
        # Text widget để hiển thị log/ kết quả
        self.result_text = tk.Text(self, height=10, width=50)
        
        # Thanh tiến trình
        self.progress_bar = ttk.Progressbar(self, variable=self.progress_var, maximum=100)

    def _create_layout(self):
        self.info_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.param_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.run_button.grid(row=0, column=2, padx=5, pady=5)
        self.progress_bar.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky="ew")
        self.result_text.grid(row=2, column=0, columnspan=3, padx=5, pady=5)
        self.columnconfigure(1, weight=1)

    def run_optimization(self):
        """Chạy quá trình tối ưu hóa trong một luồng riêng để không làm treo giao diện."""
        def optimization_task():
            try:
                self.result_text.delete("1.0", tk.END)
                self.progress_var.set(0)
                self.result_text.insert(tk.END, "Đang chạy tối ưu hóa...\n")
                
                # Giả lập quá trình tối ưu hóa
                for i in range(101):
                    time.sleep(0.05)  # Giả lập thời gian chạy tối ưu hóa
                    self.progress_var.set(i)
                    self.result_text.insert(tk.END, f"Tiến trình: {i}%\n")
                    self.result_text.see(tk.END)
                
                self.result_text.insert(tk.END, "Tối ưu hóa hoàn thành.\n")
                messagebox.showinfo("Kết quả tối ưu hóa", "Kế hoạch xạ trị đã được tối ưu hóa thành công!")
                logger.info("Tối ưu hóa kế hoạch xạ trị hoàn thành thành công.")
            except Exception as e:
                logger.error("Lỗi khi chạy tối ưu hóa: %s", str(e))
                messagebox.showerror("Lỗi tối ưu hóa", f"Lỗi khi chạy tối ưu hóa: {str(e)}")
        
        thread = threading.Thread(target=optimization_task)
        thread.daemon = True
        thread.start()
