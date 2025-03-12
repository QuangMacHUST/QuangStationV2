#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dialog huấn luyện mô hình KBP (Knowledge-Based Planning)
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, List, Tuple, Optional, Any, Union, Callable

from quangstation.core.utils.logging import get_logger
from quangstation.core.utils.config import get_config
from quangstation.clinical.optimization.kbp_optimizer import KnowledgeBasedPlanningOptimizer

logger = get_logger(__name__)

class KBPTrainerDialog:
    """
    Dialog huấn luyện mô hình KBP (Knowledge-Based Planning)
    """
    
    def __init__(self, parent: tk.Toplevel = None):
        """
        Khởi tạo dialog huấn luyện KBP
        
        Args:
            parent: Widget cha
        """
        self.parent = parent
        self.logger = get_logger("KBPTrainer")
        self.config = get_config()
        self.optimizer = KnowledgeBasedPlanningOptimizer()
        
        # Trạng thái
        self.training_data = None  # Dữ liệu huấn luyện
        self.training_thread = None  # Luồng huấn luyện
        
        # Biến điều khiển
        self.organ_var = tk.StringVar()
        self.data_source_var = tk.StringVar(value="database")
        self.custom_data_path = tk.StringVar()
        self.test_size_var = tk.StringVar(value="0.2")
        self.model_name_var = tk.StringVar()
        
        # Tạo dialog
        self._create_dialog()
        
        # Điền thông tin ban đầu
        self._populate_initial_data()
    
    def _create_dialog(self):
        """Tạo giao diện dialog"""
        # Tạo cửa sổ dialog
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Huấn luyện mô hình KBP")
        self.dialog.geometry("900x700")
        self.dialog.minsize(800, 600)
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Tạo notebook (nhiều tab)
        self.notebook = ttk.Notebook(self.dialog)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: Cấu hình dữ liệu huấn luyện
        self.data_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.data_tab, text="Dữ liệu huấn luyện")
        
        # Tab 2: Cấu hình mô hình
        self.model_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.model_tab, text="Cấu hình mô hình")
        
        # Tab 3: Huấn luyện và đánh giá
        self.train_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.train_tab, text="Huấn luyện")
        
        # Cấu hình từng tab
        self._setup_data_tab()
        self._setup_model_tab()
        self._setup_train_tab()
        
        # Khung nút dưới cùng
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Hủy", command=self._on_close).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Bắt đầu huấn luyện", command=self._start_training).pack(side=tk.RIGHT, padx=5)
        
    def _setup_data_tab(self):
        """Cấu hình tab dữ liệu huấn luyện"""
        # Frame nguồn dữ liệu
        source_frame = ttk.LabelFrame(self.data_tab, text="Nguồn dữ liệu")
        source_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Các tùy chọn nguồn dữ liệu
        ttk.Radiobutton(source_frame, text="Trích xuất từ cơ sở dữ liệu", value="database", 
                        variable=self.data_source_var, command=self._on_data_source_change).pack(anchor=tk.W, padx=10, pady=5)
        
        ttk.Radiobutton(source_frame, text="Nhập từ file CSV", value="csv", 
                        variable=self.data_source_var, command=self._on_data_source_change).pack(anchor=tk.W, padx=10, pady=5)
        
        # Frame đường dẫn file
        self.file_frame = ttk.Frame(source_frame)
        self.file_frame.pack(fill=tk.X, padx=20, pady=5)
        ttk.Label(self.file_frame, text="File dữ liệu:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(self.file_frame, textvariable=self.custom_data_path, width=50).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(self.file_frame, text="...", width=3, command=self._browse_data_file).pack(side=tk.LEFT, padx=5)
        
        # Frame loại cơ quan
        organ_frame = ttk.LabelFrame(self.data_tab, text="Cơ quan mục tiêu")
        organ_frame.pack(fill=tk.X, padx=10, pady=10)
        
        organs = ["SpinalCord", "Brainstem", "ParotidLeft", "ParotidRight", "Larynx", 
                 "Lung", "Heart", "Liver", "Kidney", "Bladder", "Rectum", "Esophagus"]
        
        # Tạo combobox chọn cơ quan
        ttk.Label(organ_frame, text="Chọn cơ quan cần huấn luyện:").pack(anchor=tk.W, padx=10, pady=5)
        
        organ_combo = ttk.Combobox(organ_frame, textvariable=self.organ_var, values=organs, state="readonly", width=40)
        organ_combo.pack(anchor=tk.W, padx=10, pady=5)
        organ_combo.bind("<<ComboboxSelected>>", self._on_organ_selected)
        
        # Model name sẽ tự động cập nhật theo cơ quan
        model_name_frame = ttk.Frame(organ_frame)
        model_name_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(model_name_frame, text="Tên mô hình:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(model_name_frame, textvariable=self.model_name_var, width=40).pack(side=tk.LEFT, padx=5)
        
        # Frame xem trước dữ liệu
        preview_frame = ttk.LabelFrame(self.data_tab, text="Xem trước dữ liệu")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Treeview hiển thị dữ liệu
        columns = ["id", "ptv_volume", "total_dose", "fractions", "organ_volume", "D_mean", "D_max"]
        self.data_tree = ttk.Treeview(preview_frame, columns=columns, show="headings")
        
        # Cấu hình cột
        for col in columns:
            display_name = col
            if col == "ptv_volume":
                display_name = "Thể tích PTV (cc)"
            elif col == "total_dose":
                display_name = "Liều (Gy)"
            elif col == "fractions":
                display_name = "Số phân liều"
            elif col == "organ_volume":
                display_name = "Thể tích cơ quan (cc)"
            elif col == "D_mean":
                display_name = "Dmean (Gy)"
            elif col == "D_max":
                display_name = "Dmax (Gy)"
                
            self.data_tree.heading(col, text=display_name)
            self.data_tree.column(col, width=100, anchor=tk.CENTER)
        
        # Thêm scrollbar
        scrollbar = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.data_tree.yview)
        self.data_tree.configure(yscrollcommand=scrollbar.set)
        
        # Sắp xếp giao diện
        self.data_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Buttons
        button_frame = ttk.Frame(self.data_tab)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Tải dữ liệu", command=self._load_training_data).pack(side=tk.LEFT, padx=5)
        
        # Disable file frame ban đầu
        self.file_frame.pack_forget()
    
    def _setup_model_tab(self):
        """Cấu hình tab cấu hình mô hình"""
        # Frame tham số huấn luyện
        params_frame = ttk.LabelFrame(self.model_tab, text="Tham số huấn luyện")
        params_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Tỉ lệ dữ liệu kiểm tra
        test_size_frame = ttk.Frame(params_frame)
        test_size_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(test_size_frame, text="Tỉ lệ dữ liệu kiểm tra:").pack(side=tk.LEFT, padx=5)
        test_sizes = ["0.1", "0.2", "0.3", "0.4", "0.5"]
        ttk.Combobox(test_size_frame, textvariable=self.test_size_var, values=test_sizes, state="readonly", width=10).pack(side=tk.LEFT, padx=5)
        
        # Frame đặc trưng mô hình
        features_frame = ttk.LabelFrame(self.model_tab, text="Đặc trưng đầu vào")
        features_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Danh sách đặc trưng
        all_features = [
            ("ptv_volume", "Thể tích PTV", True),
            ("total_dose", "Liều kê toa", True),
            ("fractions", "Số phân liều", True),
            ("organ_volume", "Thể tích cơ quan", True),
            ("ptv_overlap", "Thể tích chồng lấp", True),
            ("ptv_overlap_percent", "% Thể tích chồng lấp", True),
            ("distance_to_ptv", "Khoảng cách đến PTV", True),
            ("ptv_diameter", "Đường kính PTV", False),
            ("organ_diameter", "Đường kính cơ quan", False),
            ("ptv_surface_area", "Diện tích bề mặt PTV", False)
        ]
        
        # Tạo checkbutton cho từng đặc trưng
        self.feature_vars = {}
        for i, (feature_name, display_name, default_state) in enumerate(all_features):
            var = tk.BooleanVar(value=default_state)
            self.feature_vars[feature_name] = var
            
            ttk.Checkbutton(features_frame, text=display_name, variable=var).grid(
                row=i//2, column=i%2, sticky=tk.W, padx=10, pady=5)
        
        # Frame mục tiêu dự đoán
        targets_frame = ttk.LabelFrame(self.model_tab, text="Mục tiêu dự đoán")
        targets_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Danh sách mục tiêu
        all_targets = [
            ("D_mean", "Liều trung bình (Dmean)", True),
            ("D_max", "Liều tối đa (Dmax)", True),
            ("D1cc", "D1cc", True),
            ("D2cc", "D2cc", True),
            ("D5cc", "D5cc", False),
            ("V5Gy", "V5Gy (%)", False),
            ("V10Gy", "V10Gy (%)", True),
            ("V15Gy", "V15Gy (%)", False),
            ("V20Gy", "V20Gy (%)", True),
            ("V30Gy", "V30Gy (%)", False),
            ("V40Gy", "V40Gy (%)", False),
            ("V50Gy", "V50Gy (%)", False)
        ]
        
        # Tạo checkbutton cho từng mục tiêu
        self.target_vars = {}
        for i, (target_name, display_name, default_state) in enumerate(all_targets):
            var = tk.BooleanVar(value=default_state)
            self.target_vars[target_name] = var
            
            ttk.Checkbutton(targets_frame, text=display_name, variable=var).grid(
                row=i//3, column=i%3, sticky=tk.W, padx=10, pady=5)
        
        # Frame tham số mô hình
        model_params_frame = ttk.LabelFrame(self.model_tab, text="Tham số mô hình Random Forest")
        model_params_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Số cây
        self.n_estimators_var = tk.StringVar(value="100")
        n_estimators_frame = ttk.Frame(model_params_frame)
        n_estimators_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(n_estimators_frame, text="Số cây (n_estimators):").pack(side=tk.LEFT, padx=5)
        ttk.Entry(n_estimators_frame, textvariable=self.n_estimators_var, width=10).pack(side=tk.LEFT, padx=5)
        
        # Độ sâu tối đa
        self.max_depth_var = tk.StringVar(value="None")
        max_depth_frame = ttk.Frame(model_params_frame)
        max_depth_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(max_depth_frame, text="Độ sâu tối đa (max_depth):").pack(side=tk.LEFT, padx=5)
        ttk.Combobox(max_depth_frame, textvariable=self.max_depth_var, 
                    values=["None", "5", "10", "15", "20", "25", "30"], width=10).pack(side=tk.LEFT, padx=5)
        
        # Số mẫu tối thiểu để phân chia
        self.min_samples_split_var = tk.StringVar(value="2")
        min_samples_frame = ttk.Frame(model_params_frame)
        min_samples_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(min_samples_frame, text="Số mẫu tối thiểu để phân chia:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(min_samples_frame, textvariable=self.min_samples_split_var, width=10).pack(side=tk.LEFT, padx=5)
    
    def _setup_train_tab(self):
        """Cấu hình tab huấn luyện"""
        # Frame tiến trình
        progress_frame = ttk.LabelFrame(self.train_tab, text="Tiến trình huấn luyện")
        progress_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Thanh tiến trình
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, mode="determinate")
        self.progress_bar.pack(fill=tk.X, padx=10, pady=10)
        
        # Nhãn trạng thái
        self.status_var = tk.StringVar(value="Chưa bắt đầu huấn luyện")
        ttk.Label(progress_frame, textvariable=self.status_var).pack(padx=10, pady=5)
        
        # Frame kết quả đánh giá
        eval_frame = ttk.LabelFrame(self.train_tab, text="Kết quả đánh giá")
        eval_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tạo không gian cho biểu đồ
        self.figure_frame = ttk.Frame(eval_frame)
        self.figure_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Frame thông tin đánh giá
        metrics_frame = ttk.Frame(eval_frame)
        metrics_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Các chỉ số đánh giá
        self.metrics_vars = {
            "R²": tk.StringVar(value="-"),
            "MAE": tk.StringVar(value="-"),
            "RMSE": tk.StringVar(value="-")
        }
        
        for i, (metric_name, var) in enumerate(self.metrics_vars.items()):
            ttk.Label(metrics_frame, text=f"{metric_name}:").grid(row=0, column=i*2, padx=5, pady=5)
            ttk.Label(metrics_frame, textvariable=var, font=("Arial", 10, "bold")).grid(row=0, column=i*2+1, padx=5, pady=5)
        
        # Frame nút
        button_frame = ttk.Frame(self.train_tab)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.save_button = ttk.Button(button_frame, text="Lưu mô hình", command=self._save_model, state=tk.DISABLED)
        self.save_button.pack(side=tk.RIGHT, padx=5)
    
    def _on_data_source_change(self):
        """Xử lý khi người dùng thay đổi nguồn dữ liệu"""
        source = self.data_source_var.get()
        if source == "csv":
            self.file_frame.pack(fill=tk.X, padx=20, pady=5)
        else:
            self.file_frame.pack_forget()
    
    def _on_organ_selected(self, event=None):
        """Xử lý khi người dùng chọn cơ quan"""
        organ = self.organ_var.get()
        if organ:
            self.model_name_var.set(organ)
    
    def _browse_data_file(self):
        """Mở hộp thoại chọn file dữ liệu"""
        filename = filedialog.askopenfilename(
            title="Chọn file dữ liệu",
            filetypes=[("CSV Files", "*.csv"), ("Excel Files", "*.xlsx"), ("All Files", "*.*")]
        )
        if filename:
            self.custom_data_path.set(filename)
    
    def _load_training_data(self):
        """Tải dữ liệu huấn luyện"""
        try:
            # Xóa dữ liệu cũ
            for item in self.data_tree.get_children():
                self.data_tree.delete(item)
            
            source = self.data_source_var.get()
            organ = self.organ_var.get()
            
            if not organ:
                messagebox.showwarning("Cảnh báo", "Vui lòng chọn một cơ quan để huấn luyện.")
                return
            
            # Cập nhật trạng thái
            self.status_var.set("Đang tải dữ liệu...")
            self.dialog.update_idletasks()
            
            # Tải dữ liệu từ nguồn
            if source == "database":
                self.training_data = self.optimizer.extract_training_data_from_db()
            else:  # csv
                file_path = self.custom_data_path.get()
                if not file_path or not os.path.exists(file_path):
                    messagebox.showwarning("Cảnh báo", "Vui lòng chọn file dữ liệu hợp lệ.")
                    return
                
                if file_path.endswith('.csv'):
                    self.training_data = pd.read_csv(file_path)
                elif file_path.endswith('.xlsx'):
                    self.training_data = pd.read_excel(file_path)
                else:
                    messagebox.showwarning("Cảnh báo", "Định dạng file không được hỗ trợ.")
                    return
            
            # Hiển thị dữ liệu
            if self.training_data is not None and not self.training_data.empty:
                # Lọc dữ liệu cho cơ quan đã chọn
                organ_data = self.training_data[self.training_data['organ_name'] == organ]
                
                if organ_data.empty:
                    messagebox.showinfo("Thông báo", f"Không có dữ liệu cho cơ quan {organ}.")
                    return
                
                # Hiển thị mẫu dữ liệu
                for i, row in organ_data.iterrows():
                    values = [i]
                    for col in ["ptv_volume", "total_dose", "fractions", "organ_volume", "D_mean", "D_max"]:
                        if col in row:
                            values.append(f"{row[col]:.2f}" if isinstance(row[col], (float, int)) else row[col])
                        else:
                            values.append("-")
                    self.data_tree.insert("", tk.END, values=values)
                
                self.status_var.set(f"Đã tải {len(organ_data)} dữ liệu cho {organ}")
            else:
                messagebox.showwarning("Cảnh báo", "Không thể tải dữ liệu hoặc dữ liệu trống.")
                self.status_var.set("Tải dữ liệu thất bại")
        
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi tải dữ liệu: {str(e)}")
            logger.error(f"Lỗi khi tải dữ liệu huấn luyện: {str(e)}")
            self.status_var.set("Tải dữ liệu thất bại")
    
    def _start_training(self):
        """Bắt đầu huấn luyện mô hình"""
        # Kiểm tra điều kiện
        if self.training_data is None or self.training_data.empty:
            messagebox.showwarning("Cảnh báo", "Vui lòng tải dữ liệu huấn luyện trước.")
            return
        
        organ = self.organ_var.get()
        if not organ:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một cơ quan để huấn luyện.")
            return
        
        # Lấy danh sách đặc trưng đã chọn
        selected_features = [feature for feature, var in self.feature_vars.items() if var.get()]
        if not selected_features:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn ít nhất một đặc trưng đầu vào.")
            return
        
        # Lấy danh sách mục tiêu đã chọn
        selected_targets = [target for target, var in self.target_vars.items() if var.get()]
        if not selected_targets:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn ít nhất một mục tiêu dự đoán.")
            return
        
        # Chuyển sang tab huấn luyện
        self.notebook.select(self.train_tab)
        
        # Cập nhật trạng thái
        self.status_var.set("Đang chuẩn bị huấn luyện...")
        self.progress_var.set(0)
        
        # Vô hiệu hóa các nút
        self.save_button.config(state=tk.DISABLED)
        
        # Xóa biểu đồ cũ nếu có
        for child in self.figure_frame.winfo_children():
            child.destroy()
        
        # Reset các chỉ số đánh giá
        for var in self.metrics_vars.values():
            var.set("-")
        
        # Lọc dữ liệu cho cơ quan đã chọn
        organ_data = self.training_data[self.training_data['organ_name'] == organ]
        
        if organ_data.empty:
            messagebox.showinfo("Thông báo", f"Không có dữ liệu cho cơ quan {organ}.")
            return
        
        # Lấy tham số mô hình
        try:
            test_size = float(self.test_size_var.get())
            n_estimators = int(self.n_estimators_var.get())
            max_depth = None if self.max_depth_var.get() == "None" else int(self.max_depth_var.get())
            min_samples_split = int(self.min_samples_split_var.get())
        except ValueError:
            messagebox.showwarning("Cảnh báo", "Giá trị tham số không hợp lệ.")
            return
        
        # Cấu hình mô hình RF
        from sklearn.ensemble import RandomForestRegressor
        model_params = {
            'n_estimators': n_estimators,
            'min_samples_split': min_samples_split,
            'random_state': 42
        }
        if max_depth is not None:
            model_params['max_depth'] = max_depth
        
        # Bắt đầu huấn luyện trong thread riêng
        self.training_thread = threading.Thread(
            target=self._train_thread,
            args=(organ, organ_data, selected_features, selected_targets, test_size, model_params)
        )
        self.training_thread.daemon = True
        self.training_thread.start()
    
    def _train_thread(self, organ_name, data, features, targets, test_size, model_params):
        """
        Thực hiện huấn luyện trong thread riêng
        """
        try:
            # Cập nhật trạng thái
            self._update_status("Đang huấn luyện mô hình...", 10)
            
            # Tạo bản sao dữ liệu an toàn cho thread
            data_copy = data.copy()
            
            # Huấn luyện mô hình
            results = self.optimizer.train_model(
                dataset=data_copy,
                organ_name=organ_name,
                features=features,
                targets=targets,
                test_size=test_size,
                save_model=False
            )
            
            # Cập nhật trạng thái
            self._update_status("Huấn luyện hoàn tất, đang xử lý kết quả...", 80)
            
            # Hiển thị kết quả
            self._display_training_results(results)
            
            # Cập nhật trạng thái
            self._update_status("Huấn luyện hoàn tất!", 100)
            
            # Kích hoạt nút lưu
            self.dialog.after(0, lambda: self.save_button.config(state=tk.NORMAL))
            
        except Exception as e:
            # Xử lý lỗi
            error_msg = f"Lỗi khi huấn luyện mô hình: {str(e)}"
            logger.error(error_msg)
            self.dialog.after(0, lambda: messagebox.showerror("Lỗi", error_msg))
            self._update_status("Huấn luyện thất bại", 0)
    
    def _update_status(self, message, progress):
        """Cập nhật trạng thái và tiến trình"""
        self.dialog.after(0, lambda: self.status_var.set(message))
        self.dialog.after(0, lambda: self.progress_var.set(progress))
    
    def _display_training_results(self, results):
        """Hiển thị kết quả huấn luyện"""
        # Cập nhật chỉ số đánh giá
        if 'metrics' in results:
            metrics = results['metrics']
            self.dialog.after(0, lambda: self.metrics_vars["R²"].set(f"{metrics.get('r2', 0):.4f}"))
            self.dialog.after(0, lambda: self.metrics_vars["MAE"].set(f"{metrics.get('mae', 0):.4f}"))
            self.dialog.after(0, lambda: self.metrics_vars["RMSE"].set(f"{metrics.get('rmse', 0):.4f}"))
        
        # Tạo biểu đồ đánh giá
        if 'actual' in results and 'predicted' in results:
            def create_plot():
                # Xóa biểu đồ cũ
                for child in self.figure_frame.winfo_children():
                    child.destroy()
                
                # Tạo biểu đồ
                fig = plt.Figure(figsize=(8, 6), dpi=100)
                canvas = FigureCanvasTkAgg(fig, master=self.figure_frame)
                
                # Thêm các đồ thị
                for i, target in enumerate(results['target_names']):
                    ax = fig.add_subplot(2, 3, i+1)
                    ax.scatter(results['actual'][:, i], results['predicted'][:, i], alpha=0.7)
                    ax.plot([0, max(results['actual'][:, i])], [0, max(results['actual'][:, i])], 'r--')
                    ax.set_xlabel('Thực tế')
                    ax.set_ylabel('Dự đoán')
                    ax.set_title(target)
                    
                fig.tight_layout()
                canvas.draw()
                canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            self.dialog.after(0, create_plot)
    
    def _save_model(self):
        """Lưu mô hình đã huấn luyện"""
        try:
            model_name = self.model_name_var.get()
            
            # Hiển thị hộp thoại xác nhận
            if messagebox.askyesno("Xác nhận", f"Bạn có muốn lưu mô hình {model_name} không?"):
                # Lưu mô hình
                self.optimizer.save_model(model_name)
                messagebox.showinfo("Thành công", f"Đã lưu mô hình {model_name} thành công.")
                
                # Cập nhật trạng thái
                self.status_var.set(f"Đã lưu mô hình {model_name}")
        
        except Exception as e:
            error_msg = f"Lỗi khi lưu mô hình: {str(e)}"
            logger.error(error_msg)
            messagebox.showerror("Lỗi", error_msg)
    
    def _populate_initial_data(self):
        """Điền thông tin ban đầu"""
        # Chọn cơ quan đầu tiên nếu có
        organs = ["SpinalCord", "Brainstem", "ParotidLeft", "ParotidRight", "Larynx"]
        if organs:
            self.organ_var.set(organs[0])
            self.model_name_var.set(organs[0])
    
    def _on_close(self):
        """Xử lý khi đóng dialog"""
        # Dừng thread huấn luyện nếu đang chạy
        if self.training_thread and self.training_thread.is_alive():
            if messagebox.askyesno("Xác nhận", "Huấn luyện đang diễn ra. Bạn có chắc chắn muốn dừng không?"):
                # Thread sẽ tự dừng khi dialog bị đóng (daemon=True)
                self.dialog.destroy()
        else:
            self.dialog.destroy() 