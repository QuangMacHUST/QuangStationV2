"""
Module dvh.py
------------
Module này cung cấp các công cụ để tính toán và hiển thị biểu đồ DVH (Dose Volume Histogram)
trong hệ thống QuangStation V2.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from typing import Dict, List, Tuple, Union, Optional
import os
import json

# Import utility modules
from quangstation.utils.logging import get_logger

# Initialize logger
logger = get_logger("DVH")

class DVHCalculator:
    """
    Lớp tính toán Dose Volume Histogram (DVH) từ dữ liệu liều và cấu trúc.
    Hỗ trợ tính toán DVH tích lũy và vi phân.
    """
    
    def __init__(self):
        """Khởi tạo DVH Calculator"""
        self.structures = {}  # Dict lưu trữ mặt nạ cấu trúc
        self.dose_data = None  # Dữ liệu liều 3D
        self.dose_grid_scaling = 1.0  # Hệ số nhân liều (Gy)
        self.voxel_size = [1.0, 1.0, 1.0]  # Kích thước voxel (mm)
        self.dvh_results = {}  # Kết quả DVH đã tính
        
        logger.log_info("Đã khởi tạo DVH Calculator")
    
    def set_dose_data(self, dose_data: np.ndarray, dose_grid_scaling: float = None, voxel_size: List[float] = None):
        """
        Thiết lập dữ liệu liều cho DVH.
        
        Args:
            dose_data: Ma trận 3D chứa dữ liệu liều
            dose_grid_scaling: Hệ số liều (Gy/giá trị)
            voxel_size: Kích thước voxel theo [x, y, z] (mm)
        """
        self.dose_data = dose_data
        
        if dose_grid_scaling is not None:
            self.dose_grid_scaling = dose_grid_scaling
            
        if voxel_size is not None:
            self.voxel_size = voxel_size
            
        logger.log_info(f"Đã thiết lập dữ liệu liều: shape={dose_data.shape}, scaling={self.dose_grid_scaling}, voxel_size={self.voxel_size}")
    
    def add_structure(self, name: str, mask: np.ndarray, color: str = None):
        """
        Thêm cấu trúc để tính DVH.
        
        Args:
            name: Tên cấu trúc
            mask: Ma trận 3D boolean đánh dấu vị trí của cấu trúc
            color: Màu hiển thị (hex code hoặc tên màu)
        """
        if mask.shape != self.dose_data.shape and self.dose_data is not None:
            logger.log_error(f"Kích thước mặt nạ cấu trúc {name} ({mask.shape}) không khớp với dữ liệu liều ({self.dose_data.shape})")
            raise ValueError(f"Kích thước mặt nạ cấu trúc phải khớp với dữ liệu liều")
            
        # Lưu thông tin cấu trúc
        default_colors = {
            "ptv": "#FF0000",  # Đỏ
            "ctv": "#FFA500",  # Cam
            "gtv": "#800000",  # Đỏ sẫm
            "body": "#00FF00",  # Xanh lá
            "cord": "#FFFF00",  # Vàng
            "lung": "#ADD8E6",  # Xanh nhạt
            "heart": "#FF69B4",  # Hồng
            "liver": "#8B4513",  # Nâu
            "kidney": "#800080",  # Tím
            "brain": "#808080",  # Xám
        }
        
        # Tìm màu mặc định dựa trên tên cấu trúc
        if color is None:
            for key in default_colors:
                if key in name.lower():
                    color = default_colors[key]
                    break
            
            # Nếu không tìm thấy, sử dụng màu xanh lam mặc định
            if color is None:
                color = "#0000FF"  # Xanh lam
                
        # Lưu cấu trúc vào dictionary
        self.structures[name] = {
            "mask": mask,
            "color": color,
            "volume_cc": np.sum(mask) * (self.voxel_size[0] * self.voxel_size[1] * self.voxel_size[2]) / 1000,  # cm3
        }
        
        logger.log_info(f"Đã thêm cấu trúc: {name}, thể tích = {self.structures[name]['volume_cc']:.2f} cc")
    
    def remove_structure(self, name: str):
        """
        Xóa cấu trúc khỏi danh sách.
        
        Args:
            name: Tên cấu trúc cần xóa
        """
        if name in self.structures:
            del self.structures[name]
            # Xóa kết quả DVH nếu có
            if name in self.dvh_results:
                del self.dvh_results[name]
            logger.log_info(f"Đã xóa cấu trúc: {name}")
        else:
            logger.log_warning(f"Không tìm thấy cấu trúc: {name}")
    
    def calculate_dvh(self, structure_name: str, bins: int = 100, dose_max: float = None) -> Dict:
        """
        Tính toán DVH cho một cấu trúc.
        
        Args:
            structure_name: Tên cấu trúc
            bins: Số lượng bins trong histogram
            dose_max: Liều tối đa để chuẩn hóa (Gy)
            
        Returns:
            Dict chứa thông tin DVH
        """
        if structure_name not in self.structures:
            logger.log_error(f"Không tìm thấy cấu trúc: {structure_name}")
            raise ValueError(f"Cấu trúc {structure_name} không tồn tại")
            
        if self.dose_data is None:
            logger.log_error("Chưa thiết lập dữ liệu liều")
            raise ValueError("Cần thiết lập dữ liệu liều trước khi tính DVH")
            
        # Lấy dữ liệu liều trong cấu trúc
        structure_mask = self.structures[structure_name]["mask"]
        doses_in_structure = self.dose_data[structure_mask] * self.dose_grid_scaling  # Chuyển đổi sang Gy
        
        # Xác định liều tối đa nếu không được chỉ định
        if dose_max is None:
            dose_max = np.max(doses_in_structure) * 1.1  # Thêm 10% dư
            
        # Tạo bins liều
        dose_bins = np.linspace(0, dose_max, bins + 1)
        dvh_values = np.zeros(bins)
        
        # Tính histogram
        hist, edges = np.histogram(doses_in_structure, bins=bins, range=(0, dose_max))
        
        # Tính DVH tích lũy
        dvh = np.cumsum(hist[::-1])[::-1]
        
        # Kiểm tra trường hợp cấu trúc không có voxel nào
        if dvh.size > 0 and dvh[0] > 0:
            dvh = dvh / dvh[0] * 100
        else:
            # Trường hợp cấu trúc không có voxel hoặc tất cả voxel nằm ngoài phạm vi liều
            dvh = np.zeros_like(dvh)
            logger.log_warning(f"Cấu trúc {structure_name} không có dữ liệu liều hợp lệ để tính DVH")
        
        # Tính các thông số DVH
        d_min = np.min(doses_in_structure)
        d_max = np.max(doses_in_structure)
        d_mean = np.mean(doses_in_structure)
        
        # Tính các thông số đánh giá thêm
        volume_cc = self.structures[structure_name]["volume_cc"]
        
        # Tính D95, D50, D2cc
        sorted_doses = np.sort(doses_in_structure)
        index_95 = int(len(sorted_doses) * 0.05)  # 95% thể tích nhận liều lớn hơn hoặc bằng D95
        index_50 = int(len(sorted_doses) * 0.5)   # 50% thể tích nhận liều lớn hơn hoặc bằng D50
        
        d95 = sorted_doses[index_95] if index_95 < len(sorted_doses) else 0
        d50 = sorted_doses[index_50] if index_50 < len(sorted_doses) else 0
        
        # D2cc - Liều tại 2cc thể tích cao nhất
        voxel_volume_cc = (self.voxel_size[0] * self.voxel_size[1] * self.voxel_size[2]) / 1000
        voxels_in_2cc = min(int(2 / voxel_volume_cc), len(sorted_doses) - 1)
        d2cc = sorted_doses[-voxels_in_2cc] if voxels_in_2cc > 0 else d_max
        
        # Tính V95, V100 (% thể tích nhận 95%/100% liều chỉ định)
        # Giả sử liều chỉ định = d_max
        prescribed_dose = d_max
        v95 = np.sum(doses_in_structure >= 0.95 * prescribed_dose) / len(doses_in_structure) * 100
        v100 = np.sum(doses_in_structure >= prescribed_dose) / len(doses_in_structure) * 100
        
        # Lưu kết quả DVH
        result = {
            "structure_name": structure_name,
            "color": self.structures[structure_name]["color"],
            "volume_cc": volume_cc,
            "dose_bins": dose_bins[:-1].tolist(),  # Bỏ giá trị cuối cùng
            "dvh_values": dvh_values.tolist(),
            "dose_metrics": {
                "d_min": float(d_min),
                "d_max": float(d_max),
                "d_mean": float(d_mean),
                "d95": float(d95),
                "d50": float(d50),
                "d2cc": float(d2cc),
                "v95": float(v95),
                "v100": float(v100)
            }
        }
        
        # Lưu kết quả để sử dụng sau
        self.dvh_results[structure_name] = result
        
        logger.log_info(f"Đã tính DVH cho {structure_name}: Dmin={d_min:.2f}Gy, Dmax={d_max:.2f}Gy, Dmean={d_mean:.2f}Gy")
        
        return result
    
    def calculate_dvh_for_all(self, bins: int = 100, dose_max: float = None) -> Dict[str, Dict]:
        """
        Tính toán DVH cho tất cả các cấu trúc.
        
        Args:
            bins: Số lượng bins trong histogram
            dose_max: Liều tối đa để chuẩn hóa (Gy)
            
        Returns:
            Dict chứa thông tin DVH của tất cả cấu trúc
        """
        results = {}
        
        # Xác định liều tối đa từ dữ liệu nếu không được chỉ định
        if dose_max is None and self.dose_data is not None:
            dose_max = np.max(self.dose_data) * self.dose_grid_scaling * 1.1
            
        # Tính DVH cho từng cấu trúc
        for name in self.structures:
            try:
                results[name] = self.calculate_dvh(name, bins, dose_max)
            except Exception as e:
                logger.log_error(f"Lỗi khi tính DVH cho {name}: {e}")
                
        return results
    
    def compare_dose_metrics(self, structures: List[str] = None) -> Dict:
        """
        So sánh các thông số liều giữa các cấu trúc.
        
        Args:
            structures: Danh sách tên cấu trúc cần so sánh (mặc định: tất cả)
            
        Returns:
            Dict chứa bảng so sánh các thông số
        """
        if structures is None:
            structures = list(self.dvh_results.keys())
            
        comparison = {}
        for structure in structures:
            if structure in self.dvh_results:
                comparison[structure] = self.dvh_results[structure]["dose_metrics"]
                
        return comparison
    
    def get_dvh_data(self, structure_name: str) -> Dict:
        """
        Lấy dữ liệu DVH đã tính cho một cấu trúc.
        
        Args:
            structure_name: Tên cấu trúc
            
        Returns:
            Dict chứa thông tin DVH của cấu trúc
        """
        if structure_name in self.dvh_results:
            return self.dvh_results[structure_name]
        elif structure_name in self.structures:
            # Tính toán DVH nếu chưa có
            return self.calculate_dvh(structure_name)
        else:
            logger.log_error(f"Không tìm thấy cấu trúc: {structure_name}")
            raise ValueError(f"Cấu trúc {structure_name} không tồn tại")
    
    def save_dvh_results(self, filename: str):
        """
        Lưu kết quả DVH vào file.
        
        Args:
            filename: Tên file để lưu (JSON)
        """
        try:
            with open(filename, 'w') as f:
                json.dump(self.dvh_results, f, indent=2)
            logger.log_info(f"Đã lưu kết quả DVH vào: {filename}")
        except Exception as e:
            logger.log_error(f"Lỗi khi lưu DVH: {e}")
    
    def load_dvh_results(self, filename: str):
        """
        Tải kết quả DVH từ file.
        
        Args:
            filename: Tên file để tải (JSON)
        """
        try:
            with open(filename, 'r') as f:
                self.dvh_results = json.load(f)
            logger.log_info(f"Đã tải kết quả DVH từ: {filename}")
        except Exception as e:
            logger.log_error(f"Lỗi khi tải DVH: {e}")


class DVHPlotter:
    """
    Lớp vẽ biểu đồ DVH từ dữ liệu đã tính.
    Hỗ trợ vẽ trên matplotlib Figure hoặc trong Tkinter.
    """
    
    def __init__(self, dvh_calculator: DVHCalculator = None):
        """
        Khởi tạo DVH Plotter.
        
        Args:
            dvh_calculator: Đối tượng DVHCalculator đã có (tùy chọn)
        """
        self.dvh_calculator = dvh_calculator if dvh_calculator else DVHCalculator()
        self.figure = None
        self.canvas = None
        logger.log_info("Đã khởi tạo DVH Plotter")
    
    def create_figure(self, figsize: Tuple[int, int] = (10, 6), dpi: int = 100) -> Figure:
        """
        Tạo đối tượng Figure của matplotlib để vẽ DVH.
        
        Args:
            figsize: Kích thước figure (inches)
            dpi: Độ phân giải (dots per inch)
            
        Returns:
            matplotlib.figure.Figure
        """
        self.figure = Figure(figsize=figsize, dpi=dpi)
        return self.figure
    
    def plot_dvh(self, structures: List[str] = None, figure: Figure = None,
                title: str = "Dose Volume Histogram", grid: bool = True,
                legend_loc: str = "upper right", show_metrics: bool = True,
                highlight_prescription: bool = True, prescription_dose: float = None) -> Figure:
        """
        Vẽ biểu đồ DVH cho các cấu trúc.
        
        Args:
            structures: Danh sách tên cấu trúc cần vẽ (mặc định: tất cả)
            figure: Đối tượng Figure để vẽ (mặc định: tạo mới)
            title: Tiêu đề biểu đồ
            grid: Hiển thị lưới nền
            legend_loc: Vị trí chú thích
            show_metrics: Hiển thị thông số DVH trên chú thích
            highlight_prescription: Đánh dấu liều chỉ định trên biểu đồ
            prescription_dose: Liều chỉ định (Gy)
            
        Returns:
            matplotlib.figure.Figure
        """
        # Tạo figure mới nếu không được cung cấp
        if figure is None:
            figure = self.create_figure()
        self.figure = figure
            
        # Xác định danh sách cấu trúc cần vẽ
        dvh_results = self.dvh_calculator.dvh_results
        if not dvh_results:
            logger.log_warning("Không có dữ liệu DVH để vẽ")
            return figure
            
        if structures is None:
            structures = list(dvh_results.keys())
            
        # Tạo axes để vẽ
        ax = figure.add_subplot(111)
        
        # Vẽ từng cấu trúc
        for structure in structures:
            if structure in dvh_results:
                data = dvh_results[structure]
                dose_bins = data["dose_bins"]
                dvh_values = data["dvh_values"]
                color = data["color"]
                
                # Tạo nhãn với thông số nếu cần
                if show_metrics:
                    metrics = data["dose_metrics"]
                    label = f"{structure} - V95: {metrics['v95']:.1f}%, Dmax: {metrics['d_max']:.1f}Gy, Dmean: {metrics['d_mean']:.1f}Gy"
                else:
                    label = structure
                    
                # Vẽ đường DVH
                ax.plot(dose_bins, dvh_values, label=label, color=color, linewidth=2)
        
        # Đánh dấu liều chỉ định nếu được yêu cầu
        if highlight_prescription and prescription_dose is not None:
            ax.axvline(x=prescription_dose, color='black', linestyle='--', linewidth=1, 
                     label=f"Liều chỉ định: {prescription_dose}Gy")
            
        # Cấu hình axes
        ax.set_xlim(0, max([max(dvh_results[s]["dose_bins"]) for s in structures if s in dvh_results]) * 1.05)
        ax.set_ylim(0, 105)
        ax.set_xlabel("Liều (Gy)", fontsize=12)
        ax.set_ylabel("Thể tích (%)", fontsize=12)
        ax.set_title(title, fontsize=14)
        
        # Thêm lưới nếu được yêu cầu
        if grid:
            ax.grid(True, linestyle='--', alpha=0.7)
            
        # Thêm chú thích
        ax.legend(loc=legend_loc, fontsize=10)
        
        # Cập nhật figure
        figure.tight_layout()
        
        return figure
    
    def embed_in_tkinter(self, parent_frame: tk.Frame, structures: List[str] = None) -> FigureCanvasTkAgg:
        """
        Nhúng biểu đồ DVH vào widget Tkinter.
        
        Args:
            parent_frame: Frame Tkinter để chứa biểu đồ
            structures: Danh sách tên cấu trúc cần vẽ
            
        Returns:
            matplotlib.backends.backend_tkagg.FigureCanvasTkAgg
        """
        # Tạo figure mới nếu chưa có
        if self.figure is None:
            self.create_figure()
            
        # Vẽ DVH
        self.plot_dvh(structures=structures)
        
        # Tạo canvas Tkinter
        self.canvas = FigureCanvasTkAgg(self.figure, master=parent_frame)
        self.canvas.draw()
        
        # Đóng gói canvas vào frame
        canvas_widget = self.canvas.get_tk_widget()
        canvas_widget.pack(fill=tk.BOTH, expand=True)
        
        return self.canvas
    
    def save_plot(self, filename: str, dpi: int = 300):
        """
        Lưu biểu đồ DVH vào file hình ảnh.
        
        Args:
            filename: Tên file để lưu
            dpi: Độ phân giải (dots per inch)
        """
        if self.figure is None:
            logger.log_error("Không có biểu đồ để lưu")
            return
            
        try:
            self.figure.savefig(filename, dpi=dpi, bbox_inches='tight')
            logger.log_info(f"Đã lưu biểu đồ DVH vào: {filename}")
        except Exception as e:
            logger.log_error(f"Lỗi khi lưu biểu đồ: {e}")
    
    def update_plot(self, structures: List[str] = None):
        """
        Cập nhật biểu đồ DVH hiện tại.
        
        Args:
            structures: Danh sách tên cấu trúc cần vẽ
        """
        if self.figure is None:
            self.create_figure()
            
        # Xóa tất cả axes hiện tại
        self.figure.clear()
        
        # Vẽ lại biểu đồ
        self.plot_dvh(structures=structures, figure=self.figure)
        
        # Cập nhật canvas nếu đang hiển thị trong Tkinter
        if self.canvas:
            self.canvas.draw()
    
    def add_constraints_to_plot(self, constraints: Dict[str, List[Dict]], figure: Figure = None) -> Figure:
        """
        Thêm đường ràng buộc liều lượng lên biểu đồ DVH.
        
        Args:
            constraints: Dict chứa các ràng buộc theo cấu trúc
                {structure_name: [{dose: float, volume: float, type: "max"/"min"}]}
            figure: Đối tượng Figure để vẽ (mặc định: figure hiện tại)
            
        Returns:
            matplotlib.figure.Figure
        """
        if figure is None:
            figure = self.figure
            
        if figure is None:
            logger.log_error("Không có biểu đồ để thêm ràng buộc")
            return None
            
        ax = figure.axes[0] if figure.axes else figure.add_subplot(111)
        
        for structure_name, constraint_list in constraints.items():
            if structure_name not in self.dvh_calculator.dvh_results:
                continue
                
            color = self.dvh_calculator.dvh_results[structure_name]["color"]
            
            for constraint in constraint_list:
                dose = constraint.get("dose", 0)
                volume = constraint.get("volume", 0)
                constraint_type = constraint.get("type", "max")
                
                if constraint_type.lower() == "max":
                    # Ràng buộc tối đa: không quá volume% thể tích nhận liều lớn hơn dose Gy
                    ax.plot([dose, dose], [0, volume], color=color, linestyle=':', linewidth=1.5)
                    ax.plot([0, dose], [volume, volume], color=color, linestyle=':', linewidth=1.5)
                    ax.scatter([dose], [volume], color=color, marker='o', s=30)
                    
                elif constraint_type.lower() == "min":
                    # Ràng buộc tối thiểu: ít nhất volume% thể tích nhận liều lớn hơn dose Gy
                    ax.plot([dose, dose], [volume, 100], color=color, linestyle=':', linewidth=1.5)
                    ax.plot([0, dose], [volume, volume], color=color, linestyle=':', linewidth=1.5)
                    ax.scatter([dose], [volume], color=color, marker='s', s=30)
        
        # Cập nhật canvas nếu đang hiển thị trong Tkinter
        if self.canvas:
            self.canvas.draw()
            
        return figure


# Hàm tiện ích
def calculate_and_plot_dvh(dose_data: np.ndarray, structures: Dict[str, np.ndarray], 
                         dose_grid_scaling: float = 1.0, voxel_size: List[float] = [1.0, 1.0, 1.0],
                         output_file: str = None, show_plot: bool = True) -> Dict:
    """
    Hàm tiện ích để tính toán và vẽ DVH trong một lần gọi.
    
    Args:
        dose_data: Ma trận 3D chứa dữ liệu liều
        structures: Dict chứa mặt nạ cấu trúc {tên: mask}
        dose_grid_scaling: Hệ số liều (Gy/giá trị)
        voxel_size: Kích thước voxel (mm)
        output_file: Tên file để lưu biểu đồ (tùy chọn)
        show_plot: Hiển thị biểu đồ ngay lập tức
        
    Returns:
        Dict chứa kết quả DVH của tất cả cấu trúc
    """
    # Tạo calculator và plotter
    calculator = DVHCalculator()
    plotter = DVHPlotter(calculator)
    
    # Thiết lập dữ liệu
    calculator.set_dose_data(dose_data, dose_grid_scaling, voxel_size)
    
    # Thêm các cấu trúc
    for name, mask in structures.items():
        calculator.add_structure(name, mask)
    
    # Tính toán DVH cho tất cả cấu trúc
    results = calculator.calculate_dvh_for_all()
    
    # Vẽ biểu đồ
    if show_plot or output_file:
        figure = plotter.plot_dvh()
        
        # Lưu biểu đồ nếu cần
        if output_file:
            plotter.save_plot(output_file)
        
        # Hiển thị biểu đồ nếu cần
        if show_plot:
            plt.figure(figure.number)
            plt.show()
    
    return results
