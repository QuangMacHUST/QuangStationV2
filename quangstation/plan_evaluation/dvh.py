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
        
        logger.info("Đã khởi tạo DVH Calculator")
    
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
            
        logger.info(f"Đã thiết lập dữ liệu liều: shape={dose_data.shape}, scaling={self.dose_grid_scaling}, voxel_size={self.voxel_size}")
    
    def add_structure(self, name: str, mask: np.ndarray, color: str = None):
        """
        Thêm cấu trúc để tính DVH.
        
        Args:
            name: Tên cấu trúc
            mask: Ma trận 3D boolean đánh dấu vị trí của cấu trúc
            color: Màu hiển thị (hex code hoặc tên màu)
        """
        if mask.shape != self.dose_data.shape and self.dose_data is not None:
            logger.error(f"Kích thước mặt nạ cấu trúc {name} ({mask.shape}) không khớp với dữ liệu liều ({self.dose_data.shape})")
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
        
        logger.info(f"Đã thêm cấu trúc: {name}, thể tích = {self.structures[name]['volume_cc']:.2f} cc")
    
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
            logger.info(f"Đã xóa cấu trúc: {name}")
        else:
            logger.warning(f"Không tìm thấy cấu trúc: {name}")
    
    def calculate_dvh(self, structure_name: str = None, structure_mask: np.ndarray = None, 
                  dose_volume: np.ndarray = None, bins: int = 100, dose_max: float = None) -> Dict:
        """
        Tính toán DVH cho một cấu trúc.
        
        Args:
            structure_name: Tên cấu trúc (khi đã add_structure)
            structure_mask: Có thể truyền trực tiếp mask thay vì dùng tên cấu trúc
            dose_volume: Có thể truyền trực tiếp volume thay vì dùng dose_data thiết lập trước
            bins: Số lượng bins trong histogram
            dose_max: Liều tối đa để chuẩn hóa (Gy)
            
        Returns:
            Dict chứa thông tin DVH
        """
        # Thiết lập dữ liệu đầu vào
        if dose_volume is None:
            if self.dose_data is None:
                raise ValueError("Chưa thiết lập dữ liệu liều")
            dose_volume = self.dose_data
        
        # Thiết lập cấu trúc
        if structure_mask is None:
            if structure_name is None:
                raise ValueError("Phải chỉ định structure_name hoặc structure_mask")
            if structure_name not in self.structures:
                raise ValueError(f"Cấu trúc {structure_name} không tồn tại")
            structure_mask = self.structures[structure_name]
        
        # Kiểm tra kích thước
        if structure_mask.shape != dose_volume.shape:
            raise ValueError(f"Kích thước mặt nạ cấu trúc ({structure_mask.shape}) không khớp với dữ liệu liều ({dose_volume.shape})")
        
        try:
            # Lấy giá trị liều trong cấu trúc
            mask_indices = np.where(structure_mask > 0)
            if len(mask_indices[0]) == 0:
                logger.warning(f"Cấu trúc trống (không có voxel nào)")
                return {
                    'name': structure_name,
                    'volume_cc': 0,
                    'differential': {'dose': [], 'volume': []},
                    'cumulative': {'dose': [], 'volume': []},
                    'dose_metrics': {},
                    'volume_metrics': {}
                }
            
            # Tính thể tích cấu trúc (cc)
            voxel_volume_cc = np.prod(self.voxel_size) / 1000  # mm³ -> cc
            structure_volume_cc = len(mask_indices[0]) * voxel_volume_cc
            
            # Lấy giá trị liều trong cấu trúc
            dose_values = dose_volume[mask_indices] * self.dose_grid_scaling  # Chuyển sang Gy
            
            # Xác định giá trị liều tối đa nếu không được chỉ định
            if dose_max is None:
                dose_max = np.max(dose_values) * 1.1  # Thêm 10% lề
            
            # Tính histogram vi phân
            hist, bin_edges = np.histogram(dose_values, bins=bins, range=(0, dose_max))
            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
            
            # Chuyển sang thể tích tương đối (%)
            rel_volumes = hist / len(dose_values) * 100
            
            # Tính DVH tích lũy
            cum_volumes = np.zeros_like(rel_volumes)
            for i in range(len(rel_volumes)):
                cum_volumes[i] = np.sum(rel_volumes[i:])
            
            # Làm trơn DVH để trông đẹp hơn
            try:
                from scipy.signal import savgol_filter
                if len(cum_volumes) > 11:  # Cần ít nhất window_length điểm
                    cum_volumes_smooth = savgol_filter(cum_volumes, 11, 3)
                    cum_volumes = np.maximum(cum_volumes_smooth, 0)  # Đảm bảo không âm
            except ImportError:
                logger.info("Không có scipy, không làm trơn DVH")
            
            # Tính các chỉ số liều
            dose_metrics = self.calculate_dose_metrics(dose_values)
            
            # Tính các chỉ số thể tích
            volume_metrics = self.calculate_volume_metrics(bin_centers, cum_volumes)
            
            # Tạo kết quả DVH
            dvh_data = {
                'name': structure_name,
                'volume_cc': structure_volume_cc,
                'differential': {
                    'dose': bin_centers.tolist(),
                    'volume': rel_volumes.tolist()
                },
                'cumulative': {
                    'dose': bin_centers.tolist(),
                    'volume': cum_volumes.tolist()
                },
                'dose_metrics': dose_metrics,
                'volume_metrics': volume_metrics
            }
            
            # Lưu kết quả
            if structure_name is not None:
                self.dvh_results[structure_name] = dvh_data
                
            logger.info(f"Đã tính DVH cho {'cấu trúc ' + structure_name if structure_name else 'mask được cung cấp'}")
            return dvh_data
            
        except Exception as error:
            import traceback
            logger.error(f"Lỗi khi tính DVH: {str(error)}")
            logger.error(traceback.format_exc())
            return None
    
    def calculate_dose_metrics(self, dose_values: np.ndarray) -> Dict[str, float]:
        """
        Tính các chỉ số liều từ tập hợp giá trị liều.
        Dx = Liều nhận bởi x% thể tích
        
        Args:
            dose_values: Mảng 1D chứa các giá trị liều trong cấu trúc
            
        Returns:
            Dict chứa các chỉ số liều
        """
        metrics = {}
        
        # Chỉ số cơ bản
        metrics["min"] = float(np.min(dose_values))
        metrics["max"] = float(np.max(dose_values))
        metrics["mean"] = float(np.mean(dose_values))
        metrics["median"] = float(np.median(dose_values))
        
        # Các chỉ số Dx (liều nhận bởi x% thể tích)
        dose_sorted = np.sort(dose_values)
        total_voxels = len(dose_sorted)
        
        for x in [1, 2, 5, 10, 20, 50, 80, 90, 95, 98, 99]:
            # Chỉ số tương ứng với tỷ lệ phần trăm x
            idx = int(np.round(total_voxels * (100 - x) / 100))
            
            # Đảm bảo chỉ số nằm trong khoảng hợp lệ
            if idx >= total_voxels:
                idx = total_voxels - 1
            elif idx < 0:
                idx = 0
                
            metrics[f"D{x}"] = float(dose_sorted[idx])
        
        return metrics
    
    def calculate_volume_metrics(self, bin_centers, cum_volumes):
        """
        Tính các chỉ số thể tích từ DVH tích lũy.
        
        Args:
            bin_centers: Mảng giá trị liều ở tâm bin
            cum_volumes: Mảng phần trăm thể tích tích lũy
            
        Returns:
            Dict chứa các chỉ số thể tích
        """
        # TODO: Triển khai tính V5, V10, V20, v.v.
        volume_metrics = {}
        
        # Tính Vx
        for dose_level in [5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95]:
            # Tìm chỉ số bin gần nhất với mức liều
            idx = np.abs(bin_centers - dose_level).argmin()
            
            # Lấy thể tích tại bin này
            if idx < len(cum_volumes):
                volume_metrics[f'V{dose_level}'] = cum_volumes[idx]
            else:
                volume_metrics[f'V{dose_level}'] = 0.0
                
        return volume_metrics
    
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
                results[name] = self.calculate_dvh(
                    structure_name=name,
                    bins=bins,
                    dose_max=dose_max
                )
            except Exception as error:
                logger.error(f"Lỗi khi tính DVH cho {name}: {e}")
                
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
            logger.error(f"Không tìm thấy cấu trúc: {structure_name}")
            raise ValueError(f"Cấu trúc {structure_name} không tồn tại")
    
    def save_dvh_results(self, filename: str):
        """
        Lưu kết quả DVH vào file.
        
        Args:
            filename: Tên file để lưu (JSON)
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.dvh_results, f, indent=2, ensure_ascii=False)
            logger.info(f"Đã lưu kết quả DVH vào: {filename}")
            return True
        except Exception as error:
            logger.error(f"Lỗi khi lưu DVH: {e}")
            return False
    
    def load_dvh_results(self, filename: str):
        """
        Tải kết quả DVH từ file.
        
        Args:
            filename: Tên file để tải (JSON)
        """
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                self.dvh_results = json.load(f)
            logger.info(f"Đã tải kết quả DVH từ: {filename}")
            return True
        except Exception as error:
            logger.error(f"Lỗi khi tải DVH: {e}")
            return False

    def create_figure(self, figsize=(10, 6)):
        """
        Tạo figure matplotlib để vẽ biểu đồ DVH.
        
        Args:
            figsize: Kích thước figure (inch)
            
        Returns:
            matplotlib.figure.Figure
        """
        fig = plt.figure(figsize=figsize)
        ax = fig.add_subplot(111)
        ax.set_title("Dose Volume Histogram (DVH)")
        ax.set_xlabel("Dose (Gy)")
        ax.set_ylabel("Volume (%)")
        ax.grid(True)
        return fig
        
    def plot_dvh(self, figure=None, structures=None):
        """
        Vẽ biểu đồ DVH.
        
        Args:
            figure: Figure để vẽ (nếu None sẽ tạo mới)
            structures: Danh sách tên cấu trúc cần vẽ (nếu None sẽ vẽ tất cả)
            
        Returns:
            matplotlib.figure.Figure
        """
        if figure is None:
            figure = self.create_figure()
            
        ax = figure.gca()
        
        # Xác định cấu trúc cần vẽ
        if structures is None:
            structures = list(self.dvh_results.keys())
        elif isinstance(structures, str):
            structures = [structures]
            
        # Vẽ DVH cho từng cấu trúc
        for name in structures:
            if name not in self.dvh_results:
                continue
                
            dvh_data = self.dvh_results[name]
            
            # Lấy màu từ dữ liệu cấu trúc
            if name in self.structures and 'color' in self.structures[name]:
                color = self.structures[name]['color']
            else:
                # Màu mặc định
                color = None
                
            # Vẽ đường DVH tích lũy
            ax.plot(
                dvh_data['cumulative']['dose'],
                dvh_data['cumulative']['volume'],
                label=name,
                color=color
            )
            
        # Thêm legend
        ax.legend(loc='upper right')
        
        return figure
        
    def save_plot(self, file_path):
        """
        Lưu biểu đồ DVH ra file.
        
        Args:
            file_path: Đường dẫn file đích
            
        Returns:
            bool: True nếu thành công
        """
        try:
            fig = self.create_figure()
            
            # Vẽ DVH
            self.plot_dvh(figure=fig)
            
            # Lưu ra file
            fig.savefig(file_path, dpi=150, bbox_inches='tight')
            
            return True
        except Exception as error:
            logger.error(f"Lỗi khi lưu biểu đồ DVH: {str(error)}")
            return False


class DVHPlotter:
    """
    Vẽ biểu đồ DVH (Dose Volume Histogram).
    """
    
    def __init__(self, dvh_calculator: DVHCalculator = None):
        self.dvh_calculator = dvh_calculator
        self.figure = None
        self.canvas = None
        self.logger = get_logger(__name__)
        
    def create_figure(self, figsize: Tuple[int, int] = (10, 6), dpi: int = 100) -> Figure:
        """Tạo figure matplotlib."""
        import matplotlib.pyplot as plt
        
        # Tạo figure mới
        self.figure = plt.figure(figsize=figsize, dpi=dpi)
        
        return self.figure
        
    def plot_dvh(self, structures: List[str] = None, figure: Figure = None,
                title: str = "Dose Volume Histogram", grid: bool = True,
                legend_loc: str = "upper right", show_metrics: bool = True,
                highlight_prescription: bool = True, prescription_dose: float = None) -> Figure:
        """
        Vẽ biểu đồ DVH.
        
        Args:
            structures: Danh sách các cấu trúc cần vẽ (mặc định: tất cả)
            figure: Figure matplotlib để vẽ (mặc định: tạo mới)
            title: Tiêu đề biểu đồ
            grid: Hiển thị lưới
            legend_loc: Vị trí chú thích
            show_metrics: Hiển thị các chỉ số DVH
            highlight_prescription: Đánh dấu liều kê toa
            prescription_dose: Liều kê toa (Gy)
            
        Returns:
            Figure matplotlib
        """
        if self.dvh_calculator is None:
            self.logger.error("DVHCalculator chưa được thiết lập")
            return None
            
        # Sử dụng figure được cung cấp hoặc tạo mới
        if figure is not None:
            self.figure = figure
        elif self.figure is None:
            self.create_figure()
            
        # Xóa axes cũ nếu có
        self.figure.clear()
        
        # Tạo axes mới
        ax = self.figure.add_subplot(111)
        
        # Xác định danh sách cấu trúc cần vẽ
        if structures is None:
            structures = list(self.dvh_calculator.structures.keys())
            
        if not structures:
            ax.text(0.5, 0.5, "Không có dữ liệu", horizontalalignment='center',
                   verticalalignment='center', transform=ax.transAxes)
            return self.figure
            
        # Vẽ DVH cho từng cấu trúc
        max_dose = 0
        for name in structures:
            try:
                # Lấy dữ liệu DVH
                dvh_data = self.dvh_calculator.get_dvh_data(name)
                
                # Vẽ đường DVH
                ax.plot(dvh_data['dose_bins'], dvh_data['dvh_values'], 
                       label=f"{name} ({dvh_data['volume_cc']:.1f} cm³)",
                       color=dvh_data['color'], linewidth=2)
                       
                # Cập nhật liều tối đa
                max_dose = max(max_dose, dvh_data['dose_metrics']['d_max'])
                
                # Hiển thị các chỉ số nếu yêu cầu
                if show_metrics:
                    # Vẽ điểm D95
                    if 'd95' in dvh_data['dose_metrics']:
                        d95 = dvh_data['dose_metrics']['d95']
                        ax.plot([d95], [95], 'o', color=dvh_data['color'], markersize=5)
                        ax.text(d95 + 0.2, 95, f"D95={d95:.2f}Gy", fontsize=8, 
                               color=dvh_data['color'], verticalalignment='center')
                    
                    # Vẽ điểm V20
                    if 'v95' in dvh_data['dose_metrics']:
                        v20 = dvh_data['dose_metrics']['v95']
                        ax.plot([20], [v20], 's', color=dvh_data['color'], markersize=5)
                        ax.text(20, v20 + 2, f"V20={v20:.1f}%", fontsize=8,
                               color=dvh_data['color'], horizontalalignment='center')
                
            except Exception as error:
                self.logger.error(f"Lỗi khi vẽ DVH cho {name}: {str(error)}")
                
        # Đánh dấu liều kê toa nếu yêu cầu
        if highlight_prescription and prescription_dose is not None and prescription_dose > 0:
            ax.axvline(x=prescription_dose, color='red', linestyle='--', linewidth=1.5)
            ax.text(prescription_dose + 0.2, 5, f"Prescription: {prescription_dose}Gy", 
                   color='red', fontsize=9, rotation=90, verticalalignment='bottom')
            
        # Thiết lập các thuộc tính của biểu đồ
        ax.set_xlabel("Liều (Gy)")
        ax.set_ylabel("Thể tích (%)")
        ax.set_title(title)
        ax.set_xlim(0, max_dose * 1.1)  # Thêm 10% để nhìn rõ hơn
        ax.set_ylim(0, 105)
        
        if grid:
            ax.grid(True, linestyle='--', alpha=0.7)
            
        # Thêm chú thích
        if structures:
            ax.legend(loc=legend_loc, fontsize=9)
            
        # Điều chỉnh layout
        self.figure.tight_layout()
        
        return self.figure
        
    def embed_in_tkinter(self, parent_frame: tk.Frame, structures: List[str] = None) -> FigureCanvasTkAgg:
        """
        Nhúng biểu đồ DVH vào widget Tkinter.
        
        Args:
            parent_frame: Frame Tkinter để nhúng biểu đồ
            structures: Danh sách các cấu trúc cần vẽ
            
        Returns:
            Canvas matplotlib nhúng trong Tkinter
        """
        # Tạo figure với kích thước phù hợp
        self.create_figure(figsize=(6, 4), dpi=80)
        
        # Vẽ biểu đồ DVH
        self.plot_dvh(structures=structures)
        
        # Tạo canvas
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
        
        # Xóa canvas cũ nếu có
        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()
            
        # Tạo canvas mới
        self.canvas = FigureCanvasTkAgg(self.figure, master=parent_frame)
        self.canvas.draw()
        
        # Thêm canvas vào frame
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Thêm thanh công cụ
        toolbar_frame = tk.Frame(parent_frame)
        toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X)
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.update()
        
        return self.canvas
        
    def save_plot(self, filename: str, dpi: int = 300):
        """Lưu biểu đồ DVH ra file."""
        if self.figure is None:
            self.logger.error("Không có biểu đồ để lưu")
            return False
            
        try:
            self.figure.savefig(filename, dpi=dpi, bbox_inches='tight')
            self.logger.info(f"Đã lưu biểu đồ DVH vào file {filename}")
            return True
        except Exception as error:
            self.logger.error(f"Lỗi khi lưu biểu đồ: {str(error)}")
            return False
            
    def update_plot(self, structures: List[str] = None):
        """Cập nhật biểu đồ DVH."""
        if self.figure is None:
            self.create_figure()
            
        self.plot_dvh(structures=structures, figure=self.figure)
        
        # Cập nhật canvas nếu đang hiển thị
        if self.canvas is not None:
            self.canvas.draw()
            
    def add_constraints_to_plot(self, constraints: Dict[str, List[Dict]], figure: Figure = None) -> Figure:
        """
        Thêm các ràng buộc liều lượng vào biểu đồ DVH.
        
        Args:
            constraints: Dictionary các ràng buộc liều lượng theo cấu trúc
                {structure_name: [
                    {'type': 'max_dose', 'value': 50.0, 'unit': 'Gy'},
                    {'type': 'V20', 'value': 30.0, 'unit': '%'},
                    ...
                ]}
            figure: Figure matplotlib để vẽ
            
        Returns:
            Figure matplotlib
        """
        # Sử dụng figure được cung cấp hoặc figure hiện tại
        if figure is not None:
            self.figure = figure
        elif self.figure is None:
            self.create_figure()
            
        # Lấy axes hiện tại
        ax = self.figure.gca()
        
        # Thêm các ràng buộc vào biểu đồ
        for structure_name, structure_constraints in constraints.items():
            # Kiểm tra xem cấu trúc có tồn tại không
            if structure_name not in self.dvh_calculator.structures:
                self.logger.warning(f"Cấu trúc {structure_name} không tồn tại, bỏ qua ràng buộc")
                continue
                
            # Lấy màu của cấu trúc
            color = self.dvh_calculator.structures[structure_name]['color']
            
            # Thêm từng ràng buộc
            for constraint in structure_constraints:
                constraint_type = constraint.get('type', '').lower()
                value = constraint.get('value', 0.0)
                unit = constraint.get('unit', '')
                
                if 'max_dose' in constraint_type:
                    # Ràng buộc liều tối đa
                    ax.axvline(x=value, color=color, linestyle=':', linewidth=1.5)
                    ax.text(value + 0.2, 50, f"{structure_name} Max: {value}{unit}", 
                           color=color, fontsize=8, rotation=90)
                           
                elif 'mean_dose' in constraint_type:
                    # Ràng buộc liều trung bình
                    ax.axvline(x=value, color=color, linestyle='-.', linewidth=1.5)
                    ax.text(value + 0.2, 60, f"{structure_name} Mean: {value}{unit}", 
                           color=color, fontsize=8, rotation=90)
                           
                elif constraint_type.startswith('v') and constraint_type[1:].isdigit():
                    # Ràng buộc Vx
                    dose_level = float(constraint_type[1:])
                    ax.axhline(y=value, xmin=dose_level/ax.get_xlim()[1], color=color, 
                              linestyle=':', linewidth=1.5)
                    ax.text(dose_level + 1, value + 2, f"{structure_name} {constraint_type.upper()}: {value}{unit}", 
                           color=color, fontsize=8)
                           
                elif constraint_type.startswith('d') and constraint_type[1:].isdigit():
                    # Ràng buộc Dx
                    volume_level = float(constraint_type[1:])
                    ax.axvline(x=value, ymin=volume_level/100, color=color, 
                              linestyle=':', linewidth=1.5)
                    ax.text(value + 0.2, volume_level - 2, f"{structure_name} {constraint_type.upper()}: {value}{unit}", 
                           color=color, fontsize=8, rotation=90)
        
        # Cập nhật canvas nếu đang hiển thị
        if self.canvas is not None:
            self.canvas.draw()
            
        return self.figure


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
