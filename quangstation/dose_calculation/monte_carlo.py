#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module tính toán liều sử dụng phương pháp Monte Carlo đơn giản cho QuangStation V2.
Mô phỏng quá trình lan truyền hạt photon trong môi trường vật chất thông qua kỹ thuật Monte Carlo.
"""

import os
import numpy as np
from numpy.random import RandomState
import time
from typing import Dict, List, Tuple, Optional, Union, Any
from concurrent.futures import ProcessPoolExecutor, as_completed
import itertools
from pathlib import Path

from quangstation.utils.logging import get_logger

logger = get_logger("MonteCarlo")

class MonteCarlo:
    """Lớp tính toán liều bằng phương pháp Monte Carlo"""
    
    def __init__(self, num_particles: int = 1000000, voxel_size_mm: List[float] = None, 
                num_threads: int = None):
        """
        Khởi tạo engine Monte Carlo
        
        Args:
            num_particles: Số hạt sử dụng trong mô phỏng
            voxel_size_mm: Kích thước voxel theo mm [x, y, z]
            num_threads: Số luồng xử lý song song
        """
        self.logger = get_logger("MonteCarlo")
        self.num_particles = num_particles
        self.voxel_size_mm = voxel_size_mm or [2.5, 2.5, 2.5]
        
        # Xác định số luồng xử lý
        if num_threads is None:
            import multiprocessing
            self.num_threads = max(1, multiprocessing.cpu_count() - 1)
        else:
            self.num_threads = max(1, num_threads)
        
        # Khởi tạo các bảng dữ liệu vật lý
        self._initialize_physics_tables()
        
        # Khởi tạo thành phần tính toán
        self.reset()
    
    def _initialize_physics_tables(self):
        """Khởi tạo các bảng dữ liệu vật lý cho mô phỏng Monte Carlo"""
        # Mật độ electron tương đối các vật liệu theo giá trị HU
        # Bảng HU to RED (Relative Electron Density)
        self.hu_to_density = {
            -1000: 0.001,  # Không khí
            -950: 0.05,    # Phổi ít khí
            -700: 0.25,    # Phổi
            -300: 0.6,     # Mỡ
            -100: 0.92,    # Mỡ-nước
            0: 1.0,        # Nước
            200: 1.07,     # Cơ, mô mềm
            800: 1.3,      # Xương xốp
            1500: 1.6,     # Xương đặc
            2000: 1.8,     # Xương dày đặc
            3000: 2.0      # Kim loại, răng
        }
        
        # Hệ số suy giảm tuyến tính (cm^-1) tại năng lượng 6 MV
        self.attenuation_coeff = {
            0.001: 0.00004,  # Không khí
            0.05: 0.019,     # Phổi ít khí
            0.25: 0.019,     # Phổi
            0.6: 0.03,       # Mỡ
            0.92: 0.03,      # Mỡ-nước
            1.0: 0.04,       # Nước
            1.07: 0.043,     # Cơ, mô mềm
            1.3: 0.05,       # Xương xốp
            1.6: 0.06,       # Xương đặc
            1.8: 0.07,       # Xương dày đặc
            2.0: 0.08        # Kim loại, răng
        }
        
        # Thông số tương tác cho các loại vật liệu
        # Tỷ lệ tán xạ Compton / hấp thụ quang điện (0-1)
        self.compton_ratio = {
            0.001: 0.9999,   # Không khí
            0.05: 0.99,      # Phổi ít khí
            0.25: 0.98,      # Phổi
            0.6: 0.97,       # Mỡ
            0.92: 0.95,      # Mỡ-nước
            1.0: 0.95,       # Nước
            1.07: 0.93,      # Cơ, mô mềm
            1.3: 0.9,        # Xương xốp
            1.6: 0.85,       # Xương đặc
            1.8: 0.8,        # Xương dày đặc
            2.0: 0.7         # Kim loại, răng
        }
    
    def reset(self):
        """Khởi tạo lại các biến trạng thái"""
        self.ct_data = None
        self.mask_data = None
        self.dose_grid = None
        self.variance_grid = None
        self.beams = []
        self.isocenter = [0, 0, 0]
        self.dose_grid_shape = None
        self.density_grid = None
        self.uncertainty = None
    
    def set_ct_data(self, ct_data: np.ndarray):
        """
        Đặt dữ liệu CT
        
        Args:
            ct_data: Mảng 3D chứa giá trị HU
        """
        self.ct_data = ct_data
        self.dose_grid_shape = ct_data.shape
        
        # Khởi tạo lưới liều
        self.dose_grid = np.zeros(self.dose_grid_shape, dtype=np.float32)
        self.variance_grid = np.zeros(self.dose_grid_shape, dtype=np.float32)
        
        # Chuyển đổi dữ liệu CT thành mật độ electron tương đối
        self._convert_ct_to_density()
        
        self.logger.log_info(f"Đã khởi tạo lưới liều kích thước: {self.dose_grid_shape}")
    
    def _convert_ct_to_density(self):
        """Chuyển đổi giá trị HU sang mật độ electron tương đối"""
        if self.ct_data is None:
            self.logger.log_error("Chưa có dữ liệu CT")
            return
        
        # Khởi tạo lưới mật độ
        self.density_grid = np.zeros_like(self.ct_data, dtype=np.float32)
        
        # Lấy danh sách các giá trị HU từ bảng
        hu_values = sorted(list(self.hu_to_density.keys()))
        
        # Chuyển đổi từng voxel
        for i in range(len(hu_values) - 1):
            hu1, hu2 = hu_values[i], hu_values[i + 1]
            density1, density2 = self.hu_to_density[hu1], self.hu_to_density[hu2]
            
            # Tìm các voxel trong khoảng HU
            mask = (self.ct_data >= hu1) & (self.ct_data < hu2)
            
            # Tính nội suy tuyến tính
            if hu2 != hu1:
                slope = (density2 - density1) / (hu2 - hu1)
                self.density_grid[mask] = density1 + (self.ct_data[mask] - hu1) * slope
            else:
                self.density_grid[mask] = density1
        
        # Xử lý các voxel dưới giá trị HU thấp nhất
        mask = self.ct_data < hu_values[0]
        self.density_grid[mask] = self.hu_to_density[hu_values[0]]
        
        # Xử lý các voxel trên giá trị HU cao nhất
        mask = self.ct_data >= hu_values[-1]
        self.density_grid[mask] = self.hu_to_density[hu_values[-1]]
    
    def add_beam(self, beam_config: Dict):
        """
        Thêm chùm tia
        
        Args:
            beam_config: Cấu hình chùm tia
        """
        required_keys = ["gantry_angle", "energy", "ssd", "field_size"]
        for key in required_keys:
            if key not in beam_config:
                self.logger.log_error(f"Cấu hình chùm tia thiếu thông tin: {key}")
                return False
        
        getattr(self, "beams", {}).append(beam_config)
        self.logger.log_info(f"Đã thêm chùm tia: {beam_config}")
        return True
    
    def set_isocenter(self, isocenter: List[int]):
        """
        Đặt tâm xoay
        
        Args:
            isocenter: Tọa độ tâm xoay [x, y, z] (đơn vị voxel)
        """
        self.isocenter = isocenter
        self.logger.log_info(f"Đã đặt tâm xoay tại: {isocenter}")
    
    def calculate_dose(self, beams: List[Dict[str, Any]], isocenter: List[float] = None, 
                      mask_data: np.ndarray = None, uncertainty_target: float = 0.02,
                      max_iterations: int = 10, particles_per_iteration: int = None):
        """
        Tính toán liều bằng phương pháp Monte Carlo
        
        Args:
            beams: Danh sách các chùm tia, mỗi chùm tia là một dict với các thông số
                {
                    'gantry_angle': góc gantry (độ),
                    'collimator_angle': góc collimator (độ),
                    'couch_angle': góc bàn (độ),
                    'sad': khoảng cách từ nguồn đến tâm (mm),
                    'field_size': kích thước trường [width, height] (mm),
                    'energy': năng lượng (MV),
                    'weight': trọng số của chùm tia,
                    'mlc': thông tin MLC (nếu có)
                }
            isocenter: Tọa độ tâm xạ trị [x, y, z] (mm)
            mask_data: Mảng 3D chứa mặt nạ tính toán (1: tính, 0: bỏ qua)
            uncertainty_target: Độ không đảm bảo mục tiêu (mặc định: 0.02 tức 2%)
            max_iterations: Số lần lặp tối đa
            particles_per_iteration: Số hạt mỗi lần lặp (nếu None, sẽ tự động tính)
        
        Returns:
            np.ndarray: Mảng 3D chứa phân bố liều
        """
        if self.ct_data is None or self.density_grid is None:
            self.logger.error("Chưa có dữ liệu CT hoặc mật độ")
            return None
        
        # Lưu thông tin đầu vào
        self.beams = beams
        if isocenter is not None:
            self.isocenter = isocenter
        self.mask_data = mask_data
        
        # Khởi tạo lưới liều và phương sai
        self.dose_grid = np.zeros(self.dose_grid_shape, dtype=np.float32)
        self.variance_grid = np.zeros(self.dose_grid_shape, dtype=np.float32)
        
        # Tính số hạt mỗi lần lặp nếu không được chỉ định
        if particles_per_iteration is None:
            # Tính dựa trên kích thước vùng tính toán
            if mask_data is not None:
                volume_voxels = np.sum(mask_data)
            else:
                volume_voxels = np.prod(self.dose_grid_shape)
            
            # Ước tính số hạt cần thiết (công thức thực nghiệm)
            particles_per_iteration = int(min(1e6, max(1e5, volume_voxels / 10)))
        
        self.logger.info(f"Bắt đầu tính toán Monte Carlo với {len(beams)} chùm tia")
        self.logger.info(f"Số hạt mỗi lần lặp: {particles_per_iteration}")
        
        # Tính tổng trọng số của các chùm tia
        total_weight = sum(beam.get('weight', 1.0) for beam in beams)
        
        # Phân bổ số hạt cho từng chùm tia theo trọng số
        beam_particles = []
        for beam in beams:
            weight = beam.get('weight', 1.0)
            n_particles = int(particles_per_iteration * weight / total_weight)
            beam_particles.append(n_particles)
        
        # Lặp cho đến khi đạt độ chính xác mong muốn hoặc số lần lặp tối đa
        current_uncertainty = float('inf')
        iteration = 0
        
        while current_uncertainty > uncertainty_target and iteration < max_iterations:
            iteration += 1
            self.logger.info(f"Lần lặp {iteration}/{max_iterations}, độ không đảm bảo hiện tại: {current_uncertainty:.4f}")
            
            # Tính toán song song cho từng chùm tia
            with ProcessPoolExecutor(max_workers=self.num_threads) as executor:
                futures = []
                
                for i, beam in enumerate(beams):
                    n_particles = beam_particles[i]
                    futures.append(
                        executor.submit(
                            self._simulate_beam_particles,
                            beam,
                            n_particles,
                            self.isocenter,
                            self.density_grid,
                            self.dose_grid_shape,
                            self.voxel_size_mm,
                            i  # seed = beam_index để đảm bảo tính lặp lại
                        )
                    )
                
                # Thu thập kết quả
                for future in as_completed(futures):
                    try:
                        beam_dose, beam_variance = future.result()
                        # Cộng dồn vào lưới liều và phương sai tổng
                        self.dose_grid += beam_dose
                        self.variance_grid += beam_variance
                    except Exception as e:
                        self.logger.error(f"Lỗi khi mô phỏng chùm tia: {str(e)}")
            
            # Tính độ không đảm bảo hiện tại
            if mask_data is not None:
                # Chỉ tính trong vùng quan tâm
                masked_dose = self.dose_grid * mask_data
                masked_variance = self.variance_grid * mask_data
                # Tránh chia cho 0
                nonzero_mask = (masked_dose > 0)
                if np.sum(nonzero_mask) > 0:
                    relative_uncertainty = np.sqrt(masked_variance[nonzero_mask]) / masked_dose[nonzero_mask]
                    current_uncertainty = np.mean(relative_uncertainty)
                else:
                    current_uncertainty = float('inf')
            else:
                # Tính trên toàn bộ lưới
                nonzero_mask = (self.dose_grid > 0)
                if np.sum(nonzero_mask) > 0:
                    relative_uncertainty = np.sqrt(self.variance_grid[nonzero_mask]) / self.dose_grid[nonzero_mask]
                    current_uncertainty = np.mean(relative_uncertainty)
                else:
                    current_uncertainty = float('inf')
        
        # Chuẩn hóa liều
        if np.max(self.dose_grid) > 0:
            self.dose_grid = self.dose_grid / np.max(self.dose_grid) * 100.0  # Chuẩn hóa về thang 100
        
        # Lưu độ không đảm bảo cuối cùng
        self.uncertainty = current_uncertainty
        
        self.logger.info(f"Hoàn thành tính toán Monte Carlo sau {iteration} lần lặp")
        self.logger.info(f"Độ không đảm bảo cuối cùng: {current_uncertainty:.4f}")
        
        return self.dose_grid
    
    def _simulate_beam_particles(self, beam: Dict[str, Any], n_particles: int, 
                               isocenter: List[float], density_grid: np.ndarray,
                               grid_shape: Tuple[int, int, int], voxel_size: List[float],
                               seed: int = 0) -> Tuple[np.ndarray, np.ndarray]:
        """
        Mô phỏng các hạt từ một chùm tia
        
        Args:
            beam: Thông tin chùm tia
            n_particles: Số hạt cần mô phỏng
            isocenter: Tọa độ tâm xạ trị
            density_grid: Lưới mật độ electron
            grid_shape: Kích thước lưới
            voxel_size: Kích thước voxel (mm)
            seed: Hạt giống cho bộ sinh số ngẫu nhiên
        
        Returns:
            Tuple[np.ndarray, np.ndarray]: (lưới liều, lưới phương sai)
        """
        # Khởi tạo bộ sinh số ngẫu nhiên với hạt giống xác định
        rng = RandomState(seed)
        
        # Khởi tạo lưới liều và phương sai cho chùm tia này
        dose_grid = np.zeros(grid_shape, dtype=np.float32)
        variance_grid = np.zeros(grid_shape, dtype=np.float32)
        
        # Lấy thông tin chùm tia
        gantry_angle = np.radians(beam.get('gantry_angle', 0.0))
        collimator_angle = np.radians(beam.get('collimator_angle', 0.0))
        couch_angle = np.radians(beam.get('couch_angle', 0.0))
        sad = beam.get('sad', 1000.0)  # mm
        field_size = beam.get('field_size', [100.0, 100.0])  # mm
        energy = beam.get('energy', 6.0)  # MV
        
        # Tính ma trận biến đổi từ hệ tọa độ chùm tia sang hệ tọa độ bệnh nhân
        # (Đơn giản hóa, không tính đến góc collimator và couch)
        beam_to_patient = np.array([
            [np.cos(gantry_angle), 0, np.sin(gantry_angle)],
            [0, 1, 0],
            [-np.sin(gantry_angle), 0, np.cos(gantry_angle)]
        ])
        
        # Vị trí nguồn trong hệ tọa độ bệnh nhân
        source_pos = np.array(isocenter) + np.dot(beam_to_patient, np.array([0, 0, -sad]))
        
        # Mô phỏng từng hạt
        for i in range(n_particles):
            # Tạo vị trí ban đầu của hạt (tại nguồn)
            particle_pos = np.array(source_pos, dtype=np.float32)
            
            # Tạo hướng ban đầu (trong hệ tọa độ chùm tia)
            # Lấy mẫu ngẫu nhiên trong trường xạ
            x_field = (rng.random() - 0.5) * field_size[0]
            y_field = (rng.random() - 0.5) * field_size[1]
            
            # Điểm đích trên mặt phẳng isocenter
            target_pos = np.array(isocenter) + np.dot(beam_to_patient, np.array([x_field, y_field, 0]))
            
            # Hướng từ nguồn đến đích
            direction = target_pos - particle_pos
            direction = direction / np.linalg.norm(direction)
            
            # Năng lượng ban đầu của hạt (đơn vị tùy ý, sẽ được chuẩn hóa sau)
            energy_value = 1.0
            
            # Theo dõi hạt cho đến khi nó rời khỏi lưới hoặc bị hấp thụ hoàn toàn
            while energy_value > 0.01:
                # Chuyển đổi vị trí hạt sang chỉ số voxel
                voxel_idx = np.array([
                    int((particle_pos[0] - isocenter[0]) / voxel_size[0] + grid_shape[0] / 2),
                    int((particle_pos[1] - isocenter[1]) / voxel_size[1] + grid_shape[1] / 2),
                    int((particle_pos[2] - isocenter[2]) / voxel_size[2] + grid_shape[2] / 2)
                ])
                
                # Kiểm tra xem hạt có nằm trong lưới không
                if (voxel_idx[0] < 0 or voxel_idx[0] >= grid_shape[0] or
                    voxel_idx[1] < 0 or voxel_idx[1] >= grid_shape[1] or
                    voxel_idx[2] < 0 or voxel_idx[2] >= grid_shape[2]):
                    break
                
                # Lấy mật độ tại voxel hiện tại
                density = density_grid[voxel_idx[0], voxel_idx[1], voxel_idx[2]]
                
                # Tính hệ số suy giảm tại mật độ này
                # Nội suy tuyến tính từ bảng
                density_values = sorted(list(self.attenuation_coeff.keys()))
                idx = np.searchsorted(density_values, density)
                if idx == 0:
                    attenuation = self.attenuation_coeff[density_values[0]]
                elif idx == len(density_values):
                    attenuation = self.attenuation_coeff[density_values[-1]]
                else:
                    d1, d2 = density_values[idx-1], density_values[idx]
                    a1, a2 = self.attenuation_coeff[d1], self.attenuation_coeff[d2]
                    attenuation = a1 + (a2 - a1) * (density - d1) / (d2 - d1)
                
                # Tính xác suất tương tác trong một bước
                step_size = min(voxel_size) / 2.0  # mm
                interaction_prob = 1.0 - np.exp(-attenuation * step_size / 10.0)  # Chuyển đổi từ cm^-1 sang mm^-1
                
                # Kiểm tra xem có tương tác không
                if rng.random() < interaction_prob:
                    # Tính năng lượng lắng đọng tại voxel này
                    deposited_energy = energy_value * 0.01  # Giả sử 1% năng lượng được lắng đọng
                    
                    # Cập nhật lưới liều và phương sai
                    dose_grid[voxel_idx[0], voxel_idx[1], voxel_idx[2]] += deposited_energy
                    variance_grid[voxel_idx[0], voxel_idx[1], voxel_idx[2]] += deposited_energy**2
                    
                    # Giảm năng lượng hạt
                    energy_value -= deposited_energy
                    
                    # Xác định loại tương tác (Compton hoặc quang điện)
                    compton_prob = self.compton_ratio.get(density, 0.95)
                    
                    if rng.random() < compton_prob:
                        # Tán xạ Compton - thay đổi hướng
                        # Góc tán xạ (đơn giản hóa)
                        theta = rng.random() * np.pi  # 0 đến pi
                        phi = rng.random() * 2 * np.pi  # 0 đến 2pi
                        
                        # Tính hướng mới
                        # Tạo hệ tọa độ cục bộ với trục z là hướng ban đầu
                        z_axis = direction
                        x_axis = np.array([1, 0, 0])
                        if np.abs(np.dot(z_axis, x_axis)) > 0.9:
                            x_axis = np.array([0, 1, 0])
                        x_axis = x_axis - np.dot(x_axis, z_axis) * z_axis
                        x_axis = x_axis / np.linalg.norm(x_axis)
                        y_axis = np.cross(z_axis, x_axis)
                        
                        # Tính hướng mới trong hệ tọa độ cục bộ
                        new_dir_local = np.array([
                            np.sin(theta) * np.cos(phi),
                            np.sin(theta) * np.sin(phi),
                            np.cos(theta)
                        ])
                        
                        # Chuyển về hệ tọa độ chính
                        direction = (new_dir_local[0] * x_axis + 
                                    new_dir_local[1] * y_axis + 
                                    new_dir_local[2] * z_axis)
                        direction = direction / np.linalg.norm(direction)
                    else:
                        # Hấp thụ quang điện - hạt bị hấp thụ hoàn toàn
                        # Lắng đọng toàn bộ năng lượng còn lại
                        dose_grid[voxel_idx[0], voxel_idx[1], voxel_idx[2]] += energy_value
                        variance_grid[voxel_idx[0], voxel_idx[1], voxel_idx[2]] += energy_value**2
                        energy_value = 0
                        break
                
                # Di chuyển hạt
                particle_pos += direction * step_size
        
        return dose_grid, variance_grid
    
    def get_dose_matrix(self) -> np.ndarray:
        """
        Lấy ma trận liều
        
        Returns:
            Ma trận liều
        """
        return self.dose_grid
    
    def get_uncertainty(self) -> float:
        """
        Lấy độ không đảm bảo
        
        Returns:
            Độ không đảm bảo (%)
        """
        return self.uncertainty
    
    def save_result(self, output_file: str):
        """
        Lưu kết quả tính toán
        
        Args:
            output_file: Đường dẫn file đầu ra
        """
        if self.dose_grid is None:
            self.logger.log_error("Chưa có kết quả để lưu")
            return False
        
        try:
            np.savez_compressed(
                output_file,
                dose=self.dose_grid,
                variance=self.variance_grid,
                uncertainty=self.uncertainty,
                beams=self.beams,
                isocenter=self.isocenter,
                voxel_size=self.voxel_size_mm
            )
            self.logger.log_info(f"Đã lưu kết quả vào: {output_file}")
            return True
        except Exception as error:
            self.logger.log_error(f"Lỗi khi lưu kết quả: {str(error)}")
            return False
    
    def load_result(self, input_file: str):
        """
        Tải kết quả tính toán từ file
        
        Args:
            input_file: Đường dẫn file đầu vào
        """
        try:
            data = np.load(input_file)
            self.dose_grid = data["dose"]
            self.variance_grid = data["variance"]
            self.uncertainty = float(data["uncertainty"])
            self.beams = data["beams"].tolist() if "beams" in data else []
            self.isocenter = data["isocenter"].tolist() if "isocenter" in data else [0, 0, 0]
            self.voxel_size_mm = data["voxel_size"].tolist() if "voxel_size" in data else [2.5, 2.5, 2.5]
            
            self.dose_grid_shape = self.dose_grid.shape
            self.logger.log_info(f"Đã tải kết quả từ: {input_file}")
            return True
        except Exception as error:
            self.logger.log_error(f"Lỗi khi tải kết quả: {str(error)}")
            return False

# Tạo instance mặc định
monte_carlo = MonteCarlo() 