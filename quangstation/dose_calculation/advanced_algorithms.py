"""
Module chứa các thuật toán tính toán liều tiên tiến cho QuangStation V2.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any
import os
import json
from scipy.ndimage import gaussian_filter, map_coordinates
import warnings

from quangstation.utils.logging import get_logger
"""
Module này chứa các thuật toán tính toán liều tiên tiến cho QuangStation V2.
"""
logger = get_logger(__name__)

class AdvancedDoseAlgorithm:
    """
    Lớp cơ sở cho các thuật toán tính toán liều tiên tiến.
    """
    
    def __init__(self, name: str, version: str = "1.0"):
        self.name = name
        self.version = version
        self.configuration = {}
        self.patient_data = None
        self.structures = {}
        self.beams = []
        
    def set_configuration(self, config: Dict[str, Any]) -> None:
        """Thiết lập cấu hình cho thuật toán."""
        self.configuration.update(config)
        logger.log_info(f"Đã cập nhật cấu hình cho thuật toán {self.name}")
        
    def set_patient_data(self, image_data: np.ndarray, spacing: List[float]) -> None:
        """Thiết lập dữ liệu bệnh nhân."""
        if not isinstance(image_data, np.ndarray):
            raise TypeError("image_data phải là numpy array")
        if len(image_data.shape) != 3:
            raise ValueError("image_data phải là mảng 3D")
            
        self.patient_data = {
            'image': image_data,
            'spacing': spacing
        }
        logger.log_info(f"Đã thiết lập dữ liệu bệnh nhân cho thuật toán {self.name}")
        
    def add_structure(self, name: str, mask: np.ndarray) -> None:
        """Thêm cấu trúc giải phẫu."""
        if not isinstance(mask, np.ndarray):
            raise TypeError("mask phải là numpy array")
        if mask.dtype != bool and mask.dtype != np.uint8:
            mask = mask.astype(np.uint8)
            
        self.structures[name] = mask
        logger.log_info(f"Đã thêm cấu trúc {name} cho thuật toán {self.name}")
        
    def add_beam(self, beam_data: Dict[str, Any]) -> None:
        """Thêm chùm tia."""
        required_fields = ['id', 'energy', 'gantry_angle']
        for field in required_fields:
            if field not in beam_data:
                raise ValueError(f"beam_data thiếu trường bắt buộc: {field}")
                
        getattr(self, "beams", {}).append(beam_data)
        logger.log_info(f"Đã thêm chùm tia {beam_data['id']} cho thuật toán {self.name}")
        
    def calculate(self) -> np.ndarray:
        """Tính toán phân bố liều."""
        if self.patient_data is None:
            raise ValueError("Chưa thiết lập dữ liệu bệnh nhân")
        if not getattr(self, "beams", {}):
            raise ValueError("Chưa thêm chùm tia nào")
            
        logger.log_info(f"Bắt đầu tính toán liều với thuật toán {self.name}")
        
        # Phương thức này cần được ghi đè trong các lớp con
        raise NotImplementedError("Phương thức này cần được ghi đè trong các lớp con")
        
    def save_configuration(self, file_path: str) -> None:
        """Lưu cấu hình ra file."""
        try:
            config_data = {
                'algorithm': self.name,
                'version': self.version,
                'configuration': self.configuration
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2)
                
            logger.log_info(f"Đã lưu cấu hình thuật toán {self.name} vào {file_path}")
        except Exception as error:
            logger.log_error(f"Lỗi khi lưu cấu hình: {str(error)}")
            raise
            
    def load_configuration(self, file_path: str) -> None:
        """Tải cấu hình từ file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                
            if config_data.get('algorithm') != self.name:
                warnings.warn(f"Cấu hình trong file là cho {config_data.get('algorithm')}, "
                             f"không phải {self.name}")
                
            self.configuration = config_data.get('configuration', {})
            logger.log_info(f"Đã tải cấu hình cho thuật toán {self.name} từ {file_path}")
        except Exception as error:
            logger.log_error(f"Lỗi khi tải cấu hình: {str(error)}")
            raise


class GridBasedDoseCalculation(AdvancedDoseAlgorithm):
    """
    Thuật toán tính toán liều dựa trên lưới voxel.
    """
    
    def __init__(self, resolution_mm: float = 3.0):
        super().__init__("GridBasedDoseCalculation", "1.0")
        self.resolution_mm = resolution_mm
        self.configuration['resolution_mm'] = resolution_mm
        
    def calculate(self) -> np.ndarray:
        """Tính toán phân bố liều dựa trên thuật toán lưới."""
        image_data = self.patient_data['image']
        spacing = self.patient_data['spacing']
        
        # Tạo lưới liều trống
        dose_grid = np.zeros_like(image_data, dtype=np.float32)
        
        logger.log_info("Bắt đầu tính toán liều dựa trên thuật toán lưới")
        
        # Tính toán cho từng chùm tia
        for beam in getattr(self, "beams", {}):
            beam_dose = self._calculate_beam_dose(beam)
            
            # Cộng liều từ chùm vào tổng liều
            dose_grid += beam_dose
            
        logger.log_info("Hoàn thành tính toán liều dựa trên thuật toán lưới")
        return dose_grid
        
    def _calculate_beam_dose(self, beam: Dict[str, Any]) -> np.ndarray:
        """
        Tính toán liều từ một chùm tia sử dụng ray tracing
        
        Args:
            beam: Thông tin chùm tia
            
        Returns:
            Mảng 3D chứa liều từ chùm tia
        """
        # Lấy thông tin chùm tia
        energy = beam.get('energy', 6.0)  # MV
        gantry_angle = beam.get('gantry_angle', 0.0)  # độ
        collimator_angle = beam.get('collimator_angle', 0.0)  # độ
        field_size = beam.get('field_size', [10.0, 10.0])  # cm
        sad = beam.get('sad', 100.0)  # cm (Source-to-Axis Distance)
        weight = beam.get('weight', 1.0)
        
        # Chuyển đổi góc sang radian
        gantry_rad = np.radians(gantry_angle)
        collimator_rad = np.radians(collimator_angle)
        
        # Xác định hướng chùm tia
        beam_dir = np.array([
            np.sin(gantry_rad),
            np.cos(gantry_rad),
            0.0
        ])
        
        # Tính tâm khối hình ảnh
        shape = self.patient_data['image'].shape
        center = np.array(shape) / 2
        
        # Khởi tạo mảng liều
        dose = np.zeros_like(self.patient_data['image'], dtype=np.float32)
        
        # Triển khai thuật toán ray tracing và tích phân liều
        # Bước 1: Tính toán các thông số cơ bản
        spacing = np.array(self.patient_data['spacing'])  # mm
        
        # Chuyển đổi SAD từ cm sang mm
        sad_mm = sad * 10.0
        
        # Tính toán vị trí nguồn (source) dựa trên SAD và hướng chùm tia
        source_pos = center * spacing - beam_dir * sad_mm
        
        # Tính toán các vector vuông góc với hướng chùm tia để xác định trường chiếu
        # Vector vuông góc thứ nhất (nằm trong mặt phẳng ngang)
        perp1 = np.array([-beam_dir[1], beam_dir[0], 0.0])
        if np.linalg.norm(perp1) < 1e-6:
            perp1 = np.array([1.0, 0.0, 0.0])
        else:
            perp1 = perp1 / np.linalg.norm(perp1)
            
        # Vector vuông góc thứ hai (vuông góc với cả beam_dir và perp1)
        perp2 = np.cross(beam_dir, perp1)
        perp2 = perp2 / np.linalg.norm(perp2)
        
        # Xoay các vector vuông góc theo góc collimator
        cos_coll = np.cos(collimator_rad)
        sin_coll = np.sin(collimator_rad)
        perp1_rot = cos_coll * perp1 + sin_coll * perp2
        perp2_rot = -sin_coll * perp1 + cos_coll * perp2
        
        # Chuyển đổi kích thước trường từ cm sang mm
        field_size_mm = np.array(field_size) * 10.0
        
        # Tính toán PDD (Percentage Depth Dose) và profile cơ bản
        pdd = self._calculate_pdd(energy)
        profile = self._calculate_beam_profile(energy)
        
        # Bước 2: Duyệt qua tất cả các voxel và tính liều
        # Sử dụng vectorization để tăng tốc độ tính toán
        z_indices, y_indices, x_indices = np.meshgrid(
            np.arange(shape[0]), 
            np.arange(shape[1]), 
            np.arange(shape[2]), 
            indexing='ij'
        )
        
        # Tính tọa độ thực (mm) của mỗi voxel
        positions = np.stack([
            z_indices * spacing[0],
            y_indices * spacing[1],
            x_indices * spacing[2]
        ], axis=-1)
        
        # Tính vector từ nguồn đến mỗi voxel
        source_to_voxel = positions - source_pos
        
        # Tính khoảng cách từ nguồn đến mỗi voxel
        distances = np.linalg.norm(source_to_voxel, axis=-1)
        
        # Chuẩn hóa vector hướng
        directions = source_to_voxel / distances[..., np.newaxis]
        
        # Tính góc giữa hướng chùm tia và hướng đến voxel
        dot_products = np.sum(directions * beam_dir, axis=-1)
        
        # Chỉ tính liều cho các voxel nằm trong nửa không gian theo hướng chùm tia
        valid_voxels = dot_products > 0
        
        # Tính chiều dài đường đi qua mỗi voxel
        step_size = min(spacing) / 2.0  # mm
        
        # Bước 3: Tính toán liều cho mỗi voxel hợp lệ
        for z in range(shape[0]):
            for y in range(shape[1]):
                for x in range(shape[2]):
                    if not valid_voxels[z, y, x]:
                        continue
                    
                    # Tính vị trí voxel trong không gian thực (mm)
                    pos = np.array([z, y, x]) * spacing
                    
                    # Tính vector từ nguồn đến voxel
                    ray = pos - source_pos
                    ray_length = np.linalg.norm(ray)
                    ray_dir = ray / ray_length
                    
                    # Tính khoảng cách dọc theo trục chùm tia (độ sâu)
                    depth = np.dot(ray, beam_dir)
                    
                    # Tính tọa độ chiếu của voxel lên mặt phẳng vuông góc với chùm tia
                    proj1 = np.dot(ray, perp1_rot)
                    proj2 = np.dot(ray, perp2_rot)
                    
                    # Tính khoảng cách từ tâm trường chiếu
                    field_dist1 = abs(proj1)
                    field_dist2 = abs(proj2)
                    
                    # Kiểm tra xem voxel có nằm trong trường chiếu không
                    half_field1 = field_size_mm[0] / 2.0
                    half_field2 = field_size_mm[1] / 2.0
                    
                    if field_dist1 > half_field1 or field_dist2 > half_field2:
                        continue  # Voxel nằm ngoài trường chiếu
                    
                    # Tính hệ số suy giảm theo độ sâu (PDD)
                    depth_idx = min(int(depth / 10.0), len(pdd) - 1)  # Chuyển đổi mm sang cm và lấy chỉ số
                    depth_factor = pdd[depth_idx]
                    
                    # Tính hệ số profile theo khoảng cách từ tâm trường
                    profile_idx1 = min(int(field_dist1 / 5.0), len(profile) - 1)  # Chuyển đổi mm sang 0.5cm và lấy chỉ số
                    profile_idx2 = min(int(field_dist2 / 5.0), len(profile) - 1)
                    profile_factor = profile[profile_idx1] * profile[profile_idx2]
                    
                    # Tính hệ số khoảng cách nghịch đảo bình phương
                    inverse_square = (sad_mm / ray_length) ** 2
                    
                    # Tính hệ số suy giảm do mật độ mô
                    attenuation = 1.0
                    
                    # Thực hiện ray tracing để tính suy giảm
                    # Bắt đầu từ nguồn và di chuyển theo bước nhỏ đến voxel
                    current_pos = source_pos.copy()
                    total_steps = int(ray_length / step_size)
                    
                    for step in range(total_steps):
                        # Di chuyển một bước nhỏ dọc theo tia
                        current_pos += ray_dir * step_size
                        
                        # Tính chỉ số voxel tại vị trí hiện tại
                        current_idx = np.round(current_pos / spacing).astype(int)
                        
                        # Kiểm tra xem chỉ số có hợp lệ không
                        if (0 <= current_idx[0] < shape[0] and 
                            0 <= current_idx[1] < shape[1] and 
                            0 <= current_idx[2] < shape[2]):
                            
                            # Lấy giá trị HU tại vị trí hiện tại
                            hu_value = self.patient_data['image'][current_idx[0], current_idx[1], current_idx[2]]
                            
                            # Chuyển đổi HU sang hệ số suy giảm
                            density_factor = self._hu_to_density_factor(hu_value)
                            
                            # Cập nhật hệ số suy giảm tổng
                            attenuation *= np.exp(-density_factor * step_size / 10.0)  # Giả sử hệ số suy giảm tuyến tính
                    
                    # Tính liều cuối cùng
                    dose[z, y, x] = depth_factor * profile_factor * inverse_square * attenuation * weight
        
        # Chuẩn hóa liều
        if np.max(dose) > 0:
            dose = dose / np.max(dose) * 100.0  # Chuẩn hóa về thang 100
        
        return dose
        
    def _calculate_pdd(self, energy: float) -> np.ndarray:
        """Tính toán đường cong PDD (Percentage Depth Dose) cho một năng lượng."""
        # Số điểm dữ liệu
        num_points = 500
        
        # Tạo mảng độ sâu (mm)
        depths = np.linspace(0, 500, num_points)
        
        # Tạo PDD dựa trên công thức thực nghiệm
        if energy <= 6:  # Photon 6MV
            pdd = 100 * np.exp(-0.00577 * depths) * (1 - np.exp(-0.0533 * depths)) * \
                  (0.25 * np.exp(-0.0193 * depths) + 0.75)
        elif energy <= 10:  # Photon 10MV
            pdd = 100 * np.exp(-0.00519 * depths) * (1 - np.exp(-0.0597 * depths)) * \
                  (0.21 * np.exp(-0.0164 * depths) + 0.79)
        else:  # Photon >10MV
            pdd = 100 * np.exp(-0.00478 * depths) * (1 - np.exp(-0.0661 * depths)) * \
                  (0.18 * np.exp(-0.0144 * depths) + 0.82)
                  
        return pdd
        
    def _calculate_beam_profile(self, energy: float) -> np.ndarray:
        """Tính toán profile ngang của chùm tia."""
        # Số điểm dữ liệu
        num_points = 200
        
        # Tạo mảng khoảng cách ngang (mm)
        distances = np.linspace(0, 200, num_points)
        
        # Tạo profile dựa trên hàm Gaussian
        if energy <= 6:  # Photon 6MV
            sigma = 40.0
        elif energy <= 10:  # Photon 10MV
            sigma = 45.0
        else:  # Photon >10MV
            sigma = 50.0
            
        profile = np.exp(-(distances**2) / (2 * sigma**2))
        
        return profile
        
    def _hu_to_density_factor(self, hu_value: float) -> float:
        """Chuyển đổi giá trị HU sang hệ số mật độ điện tử."""
        # Công thức đơn giản chuyển đổi HU sang hệ số mật độ điện tử
        if hu_value < -1000:
            return 0.0
        elif hu_value < 0:
            return 1.0 + hu_value * 0.001
        elif hu_value < 1000:
            return 1.0 + hu_value * 0.0005
        else:
            return 1.5 + (hu_value - 1000) * 0.0001


class ConvolutionSuperposition(AdvancedDoseAlgorithm):
    """
    Thuật toán tính toán liều Convolution/Superposition.
    """
    
    def __init__(self):
        super().__init__("ConvolutionSuperposition", "1.0")
        self.configuration['num_angles'] = 128
        self.configuration['kernel_size'] = 65
        
    def calculate(self) -> np.ndarray:
        """Tính toán phân bố liều dựa trên thuật toán convolution/superposition."""
        image_data = self.patient_data['image']
        spacing = self.patient_data['spacing']
        
        # Tạo lưới liều trống
        dose_grid = np.zeros_like(image_data, dtype=np.float32)
        
        logger.log_info("Bắt đầu tính toán liều với thuật toán Convolution/Superposition")
        
        # Tính liều cho từng chùm tia
        for beam in getattr(self, "beams", {}):
            # Tính TERMA (Total Energy Released per unit MAss)
            terma_grid = self._calculate_terma(beam)
            
            # Tạo kernel tán xạ
            scatter_kernel = self._create_scatter_kernel(beam['energy'])
            
            # Tính tích chập (convolution)
            beam_dose = self._perform_convolution(terma_grid, scatter_kernel)
            
            # Áp dụng trọng số chùm tia
            beam_weight = beam.get('weight', 1.0)
            beam_dose *= beam_weight
            
            # Cộng liều từ chùm vào tổng liều
            dose_grid += beam_dose
            
        logger.log_info("Hoàn thành tính toán liều với thuật toán Convolution/Superposition")
        return dose_grid
        
    def _calculate_terma(self, beam: Dict[str, Any]) -> np.ndarray:
        """Tính toán TERMA cho một chùm tia."""
        # TODO: Triển khai tính toán TERMA thực tế
        # Đây chỉ là triển khai mẫu
        
        image_data = self.patient_data['image']
        spacing = self.patient_data['spacing']
        
        # Tạo lưới TERMA trống
        terma_grid = np.zeros_like(image_data, dtype=np.float32)
        
        # Tính hướng chùm tia
        gantry_angle = beam['gantry_angle']
        gantry_rad = np.radians(gantry_angle)
        beam_dir = np.array([
            np.sin(gantry_rad),
            np.cos(gantry_rad),
            0.0
        ])
        
        # Tính tâm khối hình ảnh
        shape = image_data.shape
        center = np.array(shape) / 2
        
        # Duyệt qua tất cả các voxel
        for z in range(shape[0]):
            for y in range(shape[1]):
                for x in range(shape[2]):
                    # Tính vị trí tương đối so với tâm
                    rel_pos = np.array([z, y, x]) - center
                    
                    # Tính độ sâu dọc theo hướng chùm tia
                    depth = np.dot(rel_pos, beam_dir)
                    
                    # Tính khoảng cách vuông góc với trục chùm tia
                    proj = rel_pos - depth * beam_dir
                    lateral_dist = np.linalg.norm(proj)
                    
                    # Tính giá trị TERMA
                    if depth > 0:  # Chỉ tính TERMA phía sau nguồn
                        # Áp dụng suy giảm theo độ sâu
                        attenuation = np.exp(-0.02 * depth)
                        
                        # Áp dụng suy giảm theo khoảng cách ngang
                        profile = np.exp(-(lateral_dist**2) / (2 * 40.0**2))
                        
                        # Áp dụng hệ số chuyển đổi HU sang mật độ
                        hu_value = image_data[z, y, x]
                        density_factor = self._hu_to_density_factor(hu_value)
                        
                        # Lưu giá trị TERMA
                        terma_grid[z, y, x] = attenuation * profile * density_factor
        
        return terma_grid
        
    def _create_scatter_kernel(self, energy: float) -> np.ndarray:
        """Tạo kernel tán xạ cho thuật toán convolution."""
        # Tạo kernel 3D
        kernel_size = self.configuration['kernel_size']
        half_size = kernel_size // 2
        
        # Tạo lưới tọa độ
        x, y, z = np.mgrid[-half_size:half_size+1, -half_size:half_size+1, -half_size:half_size+1]
        
        # Tính khoảng cách từ tâm
        distances = np.sqrt(x**2 + y**2 + z**2)
        
        # Tránh chia cho 0
        distances = np.maximum(distances, 0.1)
        
        # Hàm kernel dạng exponential
        if energy <= 6:
            a, b = 2.0, 0.018
        elif energy <= 10:
            a, b = 1.8, 0.016
        else:
            a, b = 1.6, 0.014
            
        kernel = a * np.exp(-b * distances) / (distances**2)
        
        # Chuẩn hóa kernel
        kernel = kernel / kernel.sum()
        
        return kernel
        
    def _perform_convolution(self, terma_grid: np.ndarray, scatter_kernel: np.ndarray) -> np.ndarray:
        """Thực hiện tích chập TERMA với kernel tán xạ."""
        from scipy.signal import fftconvolve
        
        # Sử dụng tích chập FFT để tăng tốc độ
        try:
            logger.log_info("Bắt đầu tính chập FFT")
            dose_grid = fftconvolve(terma_grid, scatter_kernel, mode='same')
            logger.log_info("Hoàn thành tính chập FFT")
        except Exception as error:
            logger.log_error(f"Lỗi khi tính chập FFT: {str(error)}")
            logger.log_info("Chuyển sang tính chập trực tiếp (chậm hơn)")
            
            # Sử dụng tích chập trực tiếp nếu FFT thất bại
            dose_grid = np.zeros_like(terma_grid)
            kernel_size = scatter_kernel.shape[0]
            half_size = kernel_size // 2
            
            # Chỉ tính chập cho một phần của grid để tăng tốc
            step = 2  # Bước nhảy để giảm số lượng tính toán
            
            for z in range(0, terma_grid.shape[0], step):
                for y in range(0, terma_grid.shape[1], step):
                    for x in range(0, terma_grid.shape[2], step):
                        # Lấy vùng con từ terma_grid
                        z_start = max(0, z - half_size)
                        z_end = min(terma_grid.shape[0], z + half_size + 1)
                        y_start = max(0, y - half_size)
                        y_end = min(terma_grid.shape[1], y + half_size + 1)
                        x_start = max(0, x - half_size)
                        x_end = min(terma_grid.shape[2], x + half_size + 1)
                        
                        # Tính chỉ số tương ứng trong kernel
                        kz_start = half_size - (z - z_start)
                        kz_end = half_size + (z_end - z)
                        ky_start = half_size - (y - y_start)
                        ky_end = half_size + (y_end - y)
                        kx_start = half_size - (x - x_start)
                        kx_end = half_size + (x_end - x)
                        
                        # Trích xuất vùng con từ terma_grid và kernel
                        terma_sub = terma_grid[z_start:z_end, y_start:y_end, x_start:x_end]
                        kernel_sub = scatter_kernel[kz_start:kz_end, ky_start:ky_end, kx_start:kx_end]
                        
                        # Tính giá trị chập
                        dose_grid[z, y, x] = np.sum(terma_sub * kernel_sub)
            
            # Nội suy các điểm bị bỏ qua
            for z in range(terma_grid.shape[0]):
                for y in range(terma_grid.shape[1]):
                    for x in range(terma_grid.shape[2]):
                        if z % step != 0 or y % step != 0 or x % step != 0:
                            # Tìm các điểm lân cận đã tính
                            nearby_points = []
                            for dz in range(-1, 2):
                                for dy in range(-1, 2):
                                    for dx in range(-1, 2):
                                        nz = (z // step) * step + dz * step
                                        ny = (y // step) * step + dy * step
                                        nx = (x // step) * step + dx * step
                                        
                                        if (0 <= nz < terma_grid.shape[0] and 
                                            0 <= ny < terma_grid.shape[1] and 
                                            0 <= nx < terma_grid.shape[2]):
                                            nearby_points.append((nz, ny, nx))
                            
                            # Tính giá trị trung bình
                            if nearby_points:
                                total = 0.0
                                for nz, ny, nx in nearby_points:
                                    total += dose_grid[nz, ny, nx]
                                dose_grid[z, y, x] = total / len(nearby_points)
        
        return dose_grid
        
    def _hu_to_density_factor(self, hu_value: float) -> float:
        """Chuyển đổi giá trị HU sang hệ số mật độ điện tử."""
        # Công thức đơn giản chuyển đổi HU sang hệ số mật độ điện tử
        if hu_value < -1000:
            return 0.0
        elif hu_value < 0:
            return 1.0 + hu_value * 0.001
        elif hu_value < 1000:
            return 1.0 + hu_value * 0.0005
        else:
            return 1.5 + (hu_value - 1000) * 0.0001


class AccurosXB(AdvancedDoseAlgorithm):
    """
    Mô phỏng thuật toán Acuros XB - phương pháp giải phương trình vận chuyển bức xạ tuyến tính.
    """
    
    def __init__(self):
        super().__init__("AccurosXB", "1.0")
        self.configuration['num_angles'] = 32
        self.configuration['electron_cutoff'] = 500  # keV
        self.configuration['photon_cutoff'] = 10     # keV
        self.configuration['max_iterations'] = 20
        
    def calculate(self) -> np.ndarray:
        """Tính toán phân bố liều dựa trên thuật toán Acuros XB."""
        image_data = self.patient_data['image']
        spacing = self.patient_data['spacing']
        
        # Tạo lưới liều trống
        dose_grid = np.zeros_like(image_data, dtype=np.float32)
        
        logger.log_info("Bắt đầu tính toán liều với thuật toán Acuros XB")
        
        # Phân loại vật liệu dựa trên HU
        material_grid = self._classify_materials(image_data)
        
        # Tính liều cho từng chùm tia
        for beam in getattr(self, "beams", {}):
            # Tính liều cho chùm tia
            beam_dose = self._calculate_beam_dose_lbte(beam, material_grid)
            
            # Áp dụng trọng số chùm tia
            beam_weight = beam.get('weight', 1.0)
            beam_dose *= beam_weight
            
            # Cộng liều từ chùm vào tổng liều
            dose_grid += beam_dose
            
        logger.log_info("Hoàn thành tính toán liều với thuật toán Acuros XB")
        return dose_grid
        
    def _classify_materials(self, image_data: np.ndarray) -> np.ndarray:
        """Phân loại vật liệu dựa trên giá trị HU."""
        # Tạo lưới vật liệu (0: không khí, 1: phổi, 2: mô mềm, 3: xương, 4: kim loại)
        material_grid = np.zeros_like(image_data, dtype=np.uint8)
        
        # Phân loại vật liệu dựa trên giá trị HU
        material_grid[(image_data >= -1000) & (image_data < -400)] = 1  # Phổi
        material_grid[(image_data >= -400) & (image_data < 200)] = 2    # Mô mềm
        material_grid[(image_data >= 200) & (image_data < 1200)] = 3    # Xương
        material_grid[image_data >= 1200] = 4                          # Kim loại
        
        return material_grid
        
    def _calculate_beam_dose_lbte(self, beam: Dict[str, Any], material_grid: np.ndarray) -> np.ndarray:
        """Tính toán liều bằng cách giải gần đúng phương trình vận chuyển bức xạ tuyến tính."""
        # Đây là một triển khai đơn giản/mô phỏng của thuật toán Acuros XB
        # Thuật toán thực tế phức tạp hơn nhiều
        
        image_data = self.patient_data['image']
        spacing = self.patient_data['spacing']
        
        # Tạo lưới liều trống
        dose_grid = np.zeros_like(image_data, dtype=np.float32)
        
        # Tính hướng chùm tia
        gantry_angle = beam['gantry_angle']
        gantry_rad = np.radians(gantry_angle)
        couch_angle = beam.get('couch_angle', 0)
        couch_rad = np.radians(couch_angle)
        
        beam_dir = np.array([
            np.sin(gantry_rad) * np.cos(couch_rad),
            np.cos(gantry_rad) * np.cos(couch_rad),
            np.sin(couch_rad)
        ])
        
        # Tạo lưới fluence photon ban đầu
        fluence_grid = self._create_initial_fluence(beam, image_data.shape)
        
        # Giải phương trình vận chuyển (mô phỏng)
        max_iterations = self.configuration['max_iterations']
        
        for iteration in range(max_iterations):
            logger.log_info(f"Acuros XB: Lặp {iteration+1}/{max_iterations}")
            
            # Lan truyền fluence theo hướng chùm tia
            updated_fluence = self._propagate_fluence(fluence_grid, material_grid, beam_dir, spacing)
            
            # Kiểm tra hội tụ
            diff = np.max(np.abs(updated_fluence - fluence_grid))
            fluence_grid = updated_fluence
            
            if diff < 1e-4:
                logger.log_info(f"Acuros XB: Hội tụ sau {iteration+1} lần lặp")
                break
        
        # Chuyển đổi fluence sang liều
        dose_grid = self._convert_fluence_to_dose(fluence_grid, material_grid)
        
        return dose_grid
        
    def _create_initial_fluence(self, beam: Dict[str, Any], shape: Tuple[int, int, int]) -> np.ndarray:
        """Tạo fluence ban đầu cho chùm tia."""
        # Tạo fluence ban đầu là một trường vuông góc với hướng chùm tia
        fluence_grid = np.zeros(shape, dtype=np.float32)
        
        # Lấy thông số chùm tia
        energy = beam['energy']
        field_size_x = beam.get('field_size_x', 100.0)  # mm
        field_size_y = beam.get('field_size_y', 100.0)  # mm
        
        # Tính tâm khối hình ảnh
        center = np.array(shape) / 2
        
        # Tạo fluence ban đầu
        for z in range(shape[0]):
            for y in range(shape[1]):
                for x in range(shape[2]):
                    # Tính vị trí tương đối so với tâm
                    rel_pos = np.array([z, y, x]) - center
                    
                    # Kiểm tra xem điểm có nằm trong trường chiếu không
                    if (abs(rel_pos[1]) <= field_size_x/2 and 
                        abs(rel_pos[2]) <= field_size_y/2 and
                        rel_pos[0] <= 0):  # Chỉ phía trước nguồn (giả sử nguồn ở z âm)
                        
                        # Tạo fluence ban đầu với cường độ tỷ lệ thuận với năng lượng
                        fluence_grid[z, y, x] = energy
        
        return fluence_grid
        
    def _propagate_fluence(self, fluence_grid: np.ndarray, material_grid: np.ndarray, 
                          beam_dir: np.ndarray, spacing: List[float]) -> np.ndarray:
        """Lan truyền fluence photon qua các vật liệu."""
        # Tạo bản sao fluence_grid để cập nhật
        updated_fluence = fluence_grid.copy()
        
        # Tính bước dịch theo hướng chùm tia
        step_size = min(spacing) / 2  # mm
        step_vector = beam_dir * step_size
        
        # Hệ số suy giảm photon cho từng loại vật liệu (1/mm)
        attenuation_coeffs = [0.0, 0.0005, 0.003, 0.015, 0.05]  # Không khí, Phổi, Mô mềm, Xương, Kim loại
        
        # Duyệt qua tất cả các voxel
        shape = fluence_grid.shape
        for z in range(shape[0]):
            for y in range(shape[1]):
                for x in range(shape[2]):
                    if fluence_grid[z, y, x] > 0:
                        # Lấy loại vật liệu và hệ số suy giảm
                        material = material_grid[z, y, x]
                        mu = attenuation_coeffs[material]
                        
                        # Tính fluence bị suy giảm
                        updated_fluence[z, y, x] *= np.exp(-mu * step_size)
                        
                        # Tính vị trí voxel tiếp theo
                        next_z = z + int(round(step_vector[0]))
                        next_y = y + int(round(step_vector[1]))
                        next_x = x + int(round(step_vector[2]))
                        
                        # Kiểm tra xem vị trí tiếp theo có hợp lệ không
                        if (0 <= next_z < shape[0] and 
                            0 <= next_y < shape[1] and 
                            0 <= next_x < shape[2]):
                            
                            # Truyền fluence đến voxel tiếp theo
                            updated_fluence[next_z, next_y, next_x] += updated_fluence[z, y, x]
        
        return updated_fluence
        
    def _convert_fluence_to_dose(self, fluence_grid: np.ndarray, material_grid: np.ndarray) -> np.ndarray:
        """Chuyển đổi fluence photon sang liều hấp thụ."""
        # Tạo lưới liều
        dose_grid = np.zeros_like(fluence_grid, dtype=np.float32)
        
        # Hệ số chuyển đổi fluence sang liều cho từng loại vật liệu
        # (đơn vị: Gy/(MV*fluence))
        dose_conversion = [0.0, 0.8, 1.0, 1.1, 0.9]  # Không khí, Phổi, Mô mềm, Xương, Kim loại
        
        # Duyệt qua tất cả các voxel
        shape = fluence_grid.shape
        for z in range(shape[0]):
            for y in range(shape[1]):
                for x in range(shape[2]):
                    # Lấy loại vật liệu và hệ số chuyển đổi
                    material = material_grid[z, y, x]
                    conversion = dose_conversion[material]
                    
                    # Tính liều hấp thụ
                    dose_grid[z, y, x] = fluence_grid[z, y, x] * conversion
        
        return dose_grid


# Tạo factory function để dễ dàng khởi tạo thuật toán
def create_dose_algorithm(algorithm_name: str, **kwargs) -> AdvancedDoseAlgorithm:
    """Tạo thuật toán tính toán liều dựa trên tên."""
    algorithm_map = {
        'grid_based': GridBasedDoseCalculation,
        'convolution_superposition': ConvolutionSuperposition,
        'acuros_xb': AccurosXB,
    }
    
    if algorithm_name not in algorithm_map:
        raise ValueError(f"Thuật toán không được hỗ trợ: {algorithm_name}")
        
    return algorithm_map[algorithm_name](**kwargs) 