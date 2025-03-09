#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dialog tối ưu hóa dựa trên mục tiêu cho QuangStation V2.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import time
from typing import Dict, List, Tuple, Optional, Any, Callable

from quangstation.optimization.goal_optimizer import OptimizationGoal, GoalBasedOptimizer
from quangstation.utils.logging import get_logger

logger = get_logger(__name__)

class GoalOptimizerDialog:
    """
    Dialog cho tương tác với tối ưu hóa dựa trên mục tiêu (Goal-Based Optimization).
    """
    
    def __init__(self, parent, structures: Dict[str, np.ndarray], 
                 beam_dose_matrices: List[np.ndarray], voxel_sizes: Tuple[float, float, float],
                 callback: Callable = None):
        """
        Khởi tạo dialog.
        
        Args:
            parent: Widget cha
            structures: Dict chứa mặt nạ các cấu trúc
            beam_dose_matrices: List các ma trận liều chùm tia
            voxel_sizes: Kích thước voxel (mm)
            callback: Hàm callback khi tối ưu hóa hoàn tất
        """
        self.parent = parent
        self.structures = structures
        self.beam_dose_matrices = beam_dose_matrices
        self.voxel_sizes = voxel_sizes
        self.callback = callback
        
        # Tạo optimizer
        self.optimizer = GoalBasedOptimizer()
        self.optimization_running = False
        self.optimization_thread = None
        
        # Thiết lập dữ liệu cho optimizer
        for name, mask in structures.items():
            self.optimizer.add_structure(name, mask)
        
        self.optimizer.set_beam_dose_contributions(beam_dose_matrices)
        self.optimizer.set_voxel_sizes(voxel_sizes)
        
        # Giao diện dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Tối ưu hóa dựa trên mục tiêu")
        self.dialog.geometry("1000x800")
        self.dialog.minsize(800, 600)
        
        # Biến lưu trữ
        self.goals = []  # Danh sách các mục tiêu
        self.algorithm_var = tk.StringVar(value=GoalBasedOptimizer.ALGO_GRADIENT_DESCENT)
        self.priority_var = tk.IntVar(value=1)
        self.weight_var = tk.DoubleVar(value=1.0)
        self.is_required_var = tk.BooleanVar(value=False)
        self.max_iterations_var = tk.IntVar(value=200)
        self.learning_rate_var = tk.DoubleVar(value=0.05)
        
        # Tạo UI
        self.create_ui()
        
        # Thiết lập sự kiện đóng dialog
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Đặt focus
        self.dialog.focus_set()
        
    def create_ui(self):
        """Tạo giao diện người dùng."""
        # Tạo frame chính
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Chia thành bên trái và bên phải
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Frame bên trái: Thiết lập mục tiêu
        goal_frame = ttk.LabelFrame(left_frame, text="Thiết lập mục tiêu", padding=10)
        goal_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Chọn cấu trúc
        ttk.Label(goal_frame, text="Cấu trúc:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.structure_combo = ttk.Combobox(goal_frame, state="readonly", width=20)
        self.structure_combo.grid(row=0, column=1, sticky=tk.W, pady=2)
        self.structure_combo['values'] = list(self.structures.keys())
        if self.structures:
            self.structure_combo.current(0)
        
        # Chọn loại mục tiêu
        ttk.Label(goal_frame, text="Loại mục tiêu:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.goal_type_combo = ttk.Combobox(goal_frame, state="readonly", width=20)
        self.goal_type_combo.grid(row=1, column=1, sticky=tk.W, pady=2)
        self.goal_type_combo['values'] = [
            "Liều tối thiểu", 
            "Liều tối đa", 
            "Liều trung bình", 
            "DVH tối thiểu", 
            "DVH tối đa", 
            "Liều đồng đều",
            "Độ tuân thủ",
            "Độ dốc liều"
        ]
        self.goal_type_combo.current(0)
        self.goal_type_combo.bind("<<ComboboxSelected>>", self.on_goal_type_change)
        
        # Giá trị liều
        ttk.Label(goal_frame, text="Giá trị liều (Gy):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.dose_var = tk.DoubleVar(value=50.0)
        self.dose_entry = ttk.Entry(goal_frame, textvariable=self.dose_var, width=10)
        self.dose_entry.grid(row=2, column=1, sticky=tk.W, pady=2)
        
        # Giá trị thể tích (chỉ cho DVH)
        ttk.Label(goal_frame, text="Thể tích (%):").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.volume_var = tk.DoubleVar(value=95.0)
        self.volume_entry = ttk.Entry(goal_frame, textvariable=self.volume_var, width=10)
        self.volume_entry.grid(row=3, column=1, sticky=tk.W, pady=2)
        self.volume_entry.config(state="disabled")  # Mặc định vô hiệu hóa
        
        # Ưu tiên (priority)
        ttk.Label(goal_frame, text="Ưu tiên:").grid(row=4, column=0, sticky=tk.W, pady=2)
        priority_frame = ttk.Frame(goal_frame)
        priority_frame.grid(row=4, column=1, sticky=tk.W, pady=2)
        
        for i in range(1, 4):
            ttk.Radiobutton(priority_frame, text=str(i), variable=self.priority_var, value=i).pack(side=tk.LEFT)
        
        # Trọng số (weight)
        ttk.Label(goal_frame, text="Trọng số:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.weight_scale = ttk.Scale(goal_frame, from_=0.1, to=10.0, orient=tk.HORIZONTAL, 
                                   variable=self.weight_var, length=200)
        self.weight_scale.grid(row=5, column=1, sticky=tk.W, pady=2)
        ttk.Label(goal_frame, textvariable=self.weight_var).grid(row=5, column=2, sticky=tk.W, pady=2)
        
        # Bắt buộc hay không
        ttk.Checkbutton(goal_frame, text="Mục tiêu bắt buộc", variable=self.is_required_var).grid(
            row=6, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        # Nút thêm mục tiêu
        ttk.Button(goal_frame, text="Thêm mục tiêu", command=self.add_goal).grid(
            row=7, column=0, columnspan=3, sticky=tk.W, pady=10)
        
        # Danh sách mục tiêu
        ttk.Label(goal_frame, text="Danh sách mục tiêu:").grid(
            row=8, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        goals_frame = ttk.Frame(goal_frame)
        goals_frame.grid(row=9, column=0, columnspan=3, sticky=tk.NSEW, pady=5)
        goal_frame.rowconfigure(9, weight=1)
        goal_frame.columnconfigure(2, weight=1)
        
        self.goals_list = tk.Listbox(goals_frame, height=10, width=60)
        self.goals_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        goals_scrollbar = ttk.Scrollbar(goals_frame, orient=tk.VERTICAL, command=self.goals_list.yview)
        goals_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.goals_list.config(yscrollcommand=goals_scrollbar.set)
        
        # Nút xóa mục tiêu được chọn
        ttk.Button(goal_frame, text="Xóa mục tiêu đã chọn", command=self.remove_goal).grid(
            row=10, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        # Frame bên phải: Thiết lập tối ưu hóa và kết quả
        optimize_frame = ttk.LabelFrame(right_frame, text="Thiết lập tối ưu hóa", padding=10)
        optimize_frame.pack(fill=tk.X, expand=False, padx=5, pady=5)
        
        # Chọn thuật toán
        ttk.Label(optimize_frame, text="Thuật toán:").grid(row=0, column=0, sticky=tk.W, pady=2)
        algorithm_combo = ttk.Combobox(optimize_frame, textvariable=self.algorithm_var, state="readonly")
        algorithm_combo.grid(row=0, column=1, sticky=tk.W, pady=2)
        algorithm_combo['values'] = [
            GoalBasedOptimizer.ALGO_GRADIENT_DESCENT,
            GoalBasedOptimizer.ALGO_EVOLUTIONARY,
            GoalBasedOptimizer.ALGO_BASIN_HOPPING,
            GoalBasedOptimizer.ALGO_HIERARCHICAL,
            GoalBasedOptimizer.ALGO_PREDICTIVE
        ]
        
        # Số lần lặp tối đa
        ttk.Label(optimize_frame, text="Số lần lặp tối đa:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(optimize_frame, textvariable=self.max_iterations_var, width=10).grid(
            row=1, column=1, sticky=tk.W, pady=2)
        
        # Learning rate (cho gradient descent)
        ttk.Label(optimize_frame, text="Tốc độ học:").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Entry(optimize_frame, textvariable=self.learning_rate_var, width=10).grid(
            row=2, column=1, sticky=tk.W, pady=2)
        
        # Nút tối ưu hóa
        ttk.Button(optimize_frame, text="Bắt đầu tối ưu hóa", command=self.start_optimization).grid(
            row=3, column=0, columnspan=2, sticky=tk.EW, pady=10)
        
        # Thanh tiến trình
        ttk.Label(optimize_frame, text="Tiến trình:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_bar = ttk.Progressbar(optimize_frame, variable=self.progress_var, mode='determinate')
        self.progress_bar.grid(row=4, column=1, sticky=tk.EW, pady=2)
        
        # Frame kết quả
        result_frame = ttk.LabelFrame(right_frame, text="Kết quả tối ưu hóa", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tạo biểu đồ
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(6, 8))
        self.canvas = FigureCanvasTkAgg(self.fig, master=result_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Khởi tạo biểu đồ trống
        self.ax1.set_title('Đường cong hội tụ')
        self.ax1.set_xlabel('Lần lặp')
        self.ax1.set_ylabel('Giá trị hàm mục tiêu')
        self.ax1.grid(True)
        
        self.ax2.set_title('Trọng số tối ưu')
        self.ax2.set_xlabel('Chùm tia')
        self.ax2.set_ylabel('Trọng số')
        self.ax2.grid(True)
        
        self.fig.tight_layout()
        self.canvas.draw()
        
        # Các nút
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Áp dụng kết quả", command=self.apply_results).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Lưu kết quả", command=self.save_results).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Tải kết quả", command=self.load_results).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Đóng", command=self.on_close).pack(side=tk.RIGHT, padx=5)
        
    def on_goal_type_change(self, event):
        """Xử lý khi loại mục tiêu thay đổi."""
        goal_type = self.get_goal_type_from_display()
        # Kích hoạt/vô hiệu hóa trường thể tích tùy theo loại mục tiêu
        if goal_type in [OptimizationGoal.TYPE_MIN_DVH, OptimizationGoal.TYPE_MAX_DVH]:
            self.volume_entry.config(state="normal")
        else:
            self.volume_entry.config(state="disabled")
    
    def get_goal_type_from_display(self) -> str:
        """Lấy loại mục tiêu từ combobox."""
        display_to_type = {
            "Liều tối thiểu": OptimizationGoal.TYPE_MIN_DOSE,
            "Liều tối đa": OptimizationGoal.TYPE_MAX_DOSE,
            "Liều trung bình": OptimizationGoal.TYPE_MEAN_DOSE,
            "DVH tối thiểu": OptimizationGoal.TYPE_MIN_DVH,
            "DVH tối đa": OptimizationGoal.TYPE_MAX_DVH,
            "Liều đồng đều": OptimizationGoal.TYPE_UNIFORM_DOSE,
            "Độ tuân thủ": OptimizationGoal.TYPE_CONFORMITY,
            "Độ dốc liều": OptimizationGoal.TYPE_DOSE_FALL_OFF
        }
        display_text = self.goal_type_combo.get()
        return display_to_type.get(display_text, OptimizationGoal.TYPE_MAX_DOSE)
    
    def add_goal(self):
        """Thêm mục tiêu vào danh sách."""
        # Lấy dữ liệu từ UI
        structure_name = self.structure_combo.get()
        if not structure_name:
            messagebox.showerror("Lỗi", "Vui lòng chọn cấu trúc")
            return
            
        goal_type = self.get_goal_type_from_display()
        dose_value = self.dose_var.get()
        
        volume_value = None
        if goal_type in [OptimizationGoal.TYPE_MIN_DVH, OptimizationGoal.TYPE_MAX_DVH]:
            volume_value = self.volume_var.get()
            
        weight = self.weight_var.get()
        priority = self.priority_var.get()
        is_required = self.is_required_var.get()
        
        # Tạo mục tiêu
        try:
            goal = OptimizationGoal(
                structure_name=structure_name,
                goal_type=goal_type,
                dose_value=dose_value,
                volume_value=volume_value,
                weight=weight,
                priority=priority,
                is_required=is_required
            )
            
            # Thêm vào optimizer
            self.optimizer.add_goal(goal)
            
            # Thêm vào danh sách UI
            self.goals.append(goal)
            self.goals_list.insert(tk.END, str(goal))
            
            logger.info(f"Đã thêm mục tiêu: {str(goal)}")
            
        except ValueError as error:
            messagebox.showerror("Lỗi", f"Không thể tạo mục tiêu: {str(error)}")
    
    def remove_goal(self):
        """Xóa mục tiêu được chọn."""
        selection = self.goals_list.curselection()
        if not selection:
            messagebox.showinfo("Thông báo", "Vui lòng chọn mục tiêu cần xóa")
            return
            
        index = selection[0]
        self.goals_list.delete(index)
        
        # Xây dựng lại danh sách mục tiêu
        self.optimizer = GoalBasedOptimizer(algorithm=self.algorithm_var.get())
        
        # Thiết lập lại dữ liệu cho optimizer
        for name, mask in self.structures.items():
            self.optimizer.add_structure(name, mask)
        
        self.optimizer.set_beam_dose_contributions(self.beam_dose_matrices)
        self.optimizer.set_voxel_sizes(self.voxel_sizes)
        
        # Thêm lại các mục tiêu còn lại
        self.goals.pop(index)
        for goal in self.goals:
            self.optimizer.add_goal(goal)
            
        logger.info(f"Đã xóa mục tiêu tại vị trí {index}")
    
    def start_optimization(self):
        """Bắt đầu quá trình tối ưu hóa."""
        # Kiểm tra điều kiện
        if not self.goals:
            messagebox.showerror("Lỗi", "Vui lòng thêm ít nhất một mục tiêu")
            return
            
        if self.optimization_running:
            messagebox.showinfo("Thông báo", "Quá trình tối ưu hóa đang chạy")
            return
            
        # Thiết lập tham số tối ưu hóa
        max_iterations = self.max_iterations_var.get()
        learning_rate = self.learning_rate_var.get()
        
        self.optimizer.set_optimization_parameters(
            max_iterations=max_iterations,
            learning_rate=learning_rate
        )
        
        # Thiết lập thuật toán
        algorithm = self.algorithm_var.get()
        self.optimizer = GoalBasedOptimizer(algorithm=algorithm)
        
        # Thiết lập lại dữ liệu cho optimizer
        for name, mask in self.structures.items():
            self.optimizer.add_structure(name, mask)
        
        self.optimizer.set_beam_dose_contributions(self.beam_dose_matrices)
        self.optimizer.set_voxel_sizes(self.voxel_sizes)
        
        # Thêm lại các mục tiêu
        for goal in self.goals:
            self.optimizer.add_goal(goal)
        
        # Thiết lập callback theo dõi tiến trình
        self.optimizer.set_progress_callback(self.update_progress)
        
        # Bắt đầu tối ưu hóa trong thread riêng
        self.optimization_running = True
        self.progress_var.set(0)
        self.optimization_thread = threading.Thread(target=self.run_optimization)
        self.optimization_thread.daemon = True
        self.optimization_thread.start()
        
        logger.info(f"Bắt đầu tối ưu hóa với thuật toán {algorithm}, {max_iterations} lần lặp")
    
    def run_optimization(self):
        """Thực hiện tối ưu hóa (chạy trong thread riêng)."""
        try:
            start_time = time.time()
            
            # Thực hiện tối ưu hóa
            result = self.optimizer.optimize()
            
            # Cập nhật UI với kết quả
            if result["success"]:
                self.dialog.after(0, self.update_results, result)
                logger.info(f"Tối ưu hóa hoàn tất trong {time.time() - start_time:.2f} giây")
            else:
                self.dialog.after(0, messagebox.showerror, "Lỗi", f"Tối ưu hóa thất bại: {result['message']}")
                logger.error(f"Tối ưu hóa thất bại: {result['message']}")
                
        except Exception as error:
            logger.error(f"Lỗi khi tối ưu hóa: {str(error)}")
            self.dialog.after(0, messagebox.showerror, "Lỗi", f"Lỗi khi tối ưu hóa: {str(error)}")
            
        finally:
            self.optimization_running = False
    
    def update_progress(self, iteration: int, objective_value: float, weights: List[float]):
        """Cập nhật tiến trình tối ưu hóa."""
        max_iterations = self.max_iterations_var.get()
        progress = min(100.0, (iteration / max_iterations) * 100.0)
        
        # Cập nhật UI từ thread chính
        self.dialog.after(0, lambda: self.progress_var.set(progress))
    
    def update_results(self, result: Dict[str, Any]):
        """Cập nhật kết quả tối ưu hóa lên UI."""
        # Lấy dữ liệu
        optimized_weights = result.get("optimized_weights", [])
        objective_values = result.get("objective_values", [])
        
        # Cập nhật biểu đồ hội tụ
        self.ax1.clear()
        self.ax1.set_title('Đường cong hội tụ')
        self.ax1.set_xlabel('Lần lặp')
        self.ax1.set_ylabel('Giá trị hàm mục tiêu')
        
        if objective_values:
            iterations = list(range(len(objective_values)))
            self.ax1.plot(iterations, objective_values, 'b-')
            self.ax1.set_ylim(0, max(objective_values) * 1.1)
        
        self.ax1.grid(True)
        
        # Cập nhật biểu đồ trọng số
        self.ax2.clear()
        self.ax2.set_title('Trọng số tối ưu')
        self.ax2.set_xlabel('Chùm tia')
        self.ax2.set_ylabel('Trọng số')
        
        if optimized_weights:
            beam_indices = list(range(1, len(optimized_weights) + 1))
            self.ax2.bar(beam_indices, optimized_weights)
            for i, weight in enumerate(optimized_weights):
                self.ax2.text(i + 1, weight, f"{weight:.3f}", ha='center', va='bottom')
                
        self.ax2.grid(True)
        
        self.fig.tight_layout()
        self.canvas.draw()
        
        # Hiển thị kết quả đánh giá mục tiêu
        goal_evaluation = result.get("goal_evaluation", {})
        if goal_evaluation:
            evaluation_text = "Kết quả đánh giá mục tiêu:\n\n"
            for goal_name, evaluation in goal_evaluation.items():
                achieved = evaluation.get("achieved", False)
                actual_value = evaluation.get("actual_value", 0)
                target_value = evaluation.get("target_value", 0)
                
                status = "✓" if achieved else "✗"
                evaluation_text += f"{status} {goal_name}: {actual_value:.2f} / {target_value:.2f}\n"
            
            messagebox.showinfo("Kết quả đánh giá", evaluation_text)
        
        # Đánh dấu hoàn tất
        self.progress_var.set(100)
        messagebox.showinfo("Thành công", "Tối ưu hóa hoàn tất")
    
    def apply_results(self):
        """Áp dụng kết quả tối ưu hóa."""
        if not hasattr(self.optimizer, 'optimized_weights') or self.optimizer.optimized_weights is None:
            messagebox.showinfo("Thông báo", "Chưa có kết quả tối ưu hóa để áp dụng")
            return
            
        # Gọi callback với kết quả
        if self.callback:
            optimized_dose = self.optimizer.get_optimized_dose()
            optimized_weights = self.optimizer.optimized_weights.tolist()
            
            self.callback(optimized_weights, optimized_dose)
            logger.info(f"Đã áp dụng kết quả tối ưu hóa: {optimized_weights}")
            
            messagebox.showinfo("Thành công", "Đã áp dụng kết quả tối ưu hóa")
    
    def save_results(self):
        """Lưu kết quả tối ưu hóa ra file."""
        if not hasattr(self.optimizer, 'optimized_weights') or self.optimizer.optimized_weights is None:
            messagebox.showinfo("Thông báo", "Chưa có kết quả tối ưu hóa để lưu")
            return
            
        from tkinter import filedialog
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Lưu kết quả tối ưu hóa"
        )
        
        if file_path:
            try:
                self.optimizer.save_results_to_json(file_path)
                logger.info(f"Đã lưu kết quả tối ưu hóa vào {file_path}")
                messagebox.showinfo("Thành công", f"Đã lưu kết quả tối ưu hóa vào:\n{file_path}")
            except Exception as error:
                logger.error(f"Lỗi khi lưu kết quả: {str(error)}")
                messagebox.showerror("Lỗi", f"Không thể lưu kết quả: {str(error)}")
    
    def load_results(self):
        """Tải kết quả tối ưu hóa từ file."""
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Tải kết quả tối ưu hóa"
        )
        
        if file_path:
            try:
                # Tạo optimizer mới
                self.optimizer = GoalBasedOptimizer()
                
                # Thiết lập dữ liệu
                for name, mask in self.structures.items():
                    self.optimizer.add_structure(name, mask)
                
                self.optimizer.set_beam_dose_contributions(self.beam_dose_matrices)
                self.optimizer.set_voxel_sizes(self.voxel_sizes)
                
                # Tải mô hình
                success = self.optimizer.load_model_from_file(file_path)
                
                if success:
                    # Cập nhật UI
                    self.goals = []
                    self.goals_list.delete(0, tk.END)
                    
                    # Thêm các mục tiêu vào danh sách
                    for goal in self.optimizer.goals:
                        self.goals.append(goal)
                        self.goals_list.insert(tk.END, str(goal))
                    
                    # Tạo kết quả giả để hiển thị
                    result = {
                        "success": True,
                        "optimized_weights": self.optimizer.optimized_weights,
                        "objective_values": self.optimizer.objective_values
                    }
                    
                    self.update_results(result)
                    
                    logger.info(f"Đã tải kết quả tối ưu hóa từ {file_path}")
                    messagebox.showinfo("Thành công", f"Đã tải kết quả tối ưu hóa")
                else:
                    messagebox.showerror("Lỗi", "Không thể tải mô hình từ file")
                    
            except Exception as error:
                logger.error(f"Lỗi khi tải kết quả: {str(error)}")
                messagebox.showerror("Lỗi", f"Không thể tải kết quả: {str(error)}")
    
    def on_close(self):
        """Xử lý sự kiện đóng dialog."""
        if self.optimization_running:
            if not messagebox.askyesno("Xác nhận", "Quá trình tối ưu hóa đang chạy. Bạn có chắc muốn hủy không?"):
                return
        
        self.optimization_running = False
        self.dialog.destroy()
    
    def show(self):
        """Hiển thị dialog."""
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        self.parent.wait_window(self.dialog)
