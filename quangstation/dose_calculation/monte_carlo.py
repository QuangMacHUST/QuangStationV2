#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module tính toán liều sử dụng phương pháp Monte Carlo đơn giản cho QuangStation V2.
Mô phỏng quá trình lan truyền hạt photon trong môi trường vật chất thông qua kỹ thuật Monte Carlo.
"""

import numpy as np
import time
import os
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
        
        self.beams.append(beam_config)
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
    
    def calculate_dose(self, num_particles: int = None, output_percent: bool = True) -> Tuple[np.ndarray, float]:
        """
        Tính toán liều bằng phương pháp Monte Carlo
        
        Args:
            num_particles: Số hạt sử dụng trong mô phỏng (ghi đè tham số mặc định)
            output_percent: Nếu True, chuẩn hóa kết quả về phần trăm liều
            
        Returns:
            Ma trận liều và độ không đảm bảo
        """
        if self.ct_data is None or self.density_grid is None:
            self.logger.log_error("Chưa có dữ liệu CT")
            return None, 0
        
        if not self.beams:
            self.logger.log_error("Chưa có chùm tia nào")
            return None, 0
        
        # Số hạt sử dụng
        if num_particles is not None:
            self.num_particles = num_particles
        
        # Reset lưới liều
        self.dose_grid = np.zeros(self.dose_grid_shape, dtype=np.float32)
        self.variance_grid = np.zeros(self.dose_grid_shape, dtype=np.float32)
        
        # Bắt đầu mô phỏng
        start_time = time.time()
        self.logger.log_info(f"Bắt đầu mô phỏng Monte Carlo với {self.num_particles:,} hạt...")
        
        # Phân chia công việc theo số luồng
        particles_per_thread = self.num_particles // self.num_threads
        
        # Tạo các tác vụ cho đa luồng
        with ProcessPoolExecutor(max_workers=self.num_threads) as executor:
            futures = []
            
            for i in range(self.num_threads):
                # Đảm bảo tổng số hạt chính xác
                particles = particles_per_thread
                if i == self.num_threads - 1:
                    particles = self.num_particles - (self.num_threads - 1) * particles_per_thread
                
                # Thêm tác vụ
                for beam in self.beams:
                    future = executor.submit(
                        self._simulate_particles,
                        particles,
                        beam,
                        self.density_grid,
                        self.dose_grid_shape,
                        self.isocenter,
                        self.voxel_size_mm,
                        i  # seed khác nhau cho mỗi luồng
                    )
                    futures.append(future)
            
            # Theo dõi tiến độ
            completed = 0
            for future in as_completed(futures):
                completed += 1
                self.logger.log_info(f"Tiến độ mô phỏng: {completed}/{len(futures)}")
                
                # Tích lũy kết quả
                part_dose, part_variance = future.result()
                self.dose_grid += part_dose
                self.variance_grid += part_variance
        
        # Tính độ không đảm bảo tổng thể
        total_uncertainty = 0
        if np.sum(self.dose_grid) > 0:
            non_zero_mask = self.dose_grid > 0
            rel_uncertainty = np.zeros_like(self.dose_grid)
            rel_uncertainty[non_zero_mask] = np.sqrt(self.variance_grid[non_zero_mask]) / self.dose_grid[non_zero_mask]
            # Độ không đảm bảo trung bình trong vùng liều > 50%
            high_dose_mask = self.dose_grid > 0.5 * np.max(self.dose_grid)
            if np.any(high_dose_mask):
                total_uncertainty = np.mean(rel_uncertainty[high_dose_mask]) * 100  # đơn vị phần trăm
        
        # Chuẩn hóa kết quả thành phần trăm nếu cần
        if output_percent and np.max(self.dose_grid) > 0:
            self.dose_grid = self.dose_grid / np.max(self.dose_grid) * 100
        
        self.uncertainty = total_uncertainty
        elapsed_time = time.time() - start_time
        self.logger.log_info(f"Hoàn thành mô phỏng sau {elapsed_time:.2f} giây. Độ không đảm bảo: {total_uncertainty:.2f}%")
        
        return self.dose_grid, total_uncertainty
    
    def _simulate_particles(self, num_particles: int, beam: Dict, density_grid: np.ndarray, 
                         shape: Tuple[int, int, int], isocenter: List[int], 
                         voxel_size_mm: List[float], seed: int = 0) -> Tuple[np.ndarray, np.ndarray]:
        """
        Mô phỏng quá trình lan truyền của các hạt photon
        
        Args:
            num_particles: Số hạt cần mô phỏng
            beam: Thông tin chùm tia
            density_grid: Lưới mật độ
            shape: Kích thước lưới
            isocenter: Tâm xoay
            voxel_size_mm: Kích thước voxel theo mm
            seed: Hạt giống cho số ngẫu nhiên
            
        Returns:
            Ma trận liều và ma trận phương sai
        """
        # Khởi tạo bộ sinh số ngẫu nhiên
        rng = np.random.RandomState(seed)
        
        # Khởi tạo ma trận kết quả
        dose_grid = np.zeros(shape, dtype=np.float32)
        variance_grid = np.zeros(shape, dtype=np.float32)
        
        # Lấy thông tin chùm tia
        gantry_angle = beam.get("gantry_angle", 0)
        energy = beam.get("energy", 6)  # MV
        ssd = beam.get("ssd", 1000)  # mm
        field_size = beam.get("field_size", [100, 100])  # mm x mm
        
        # Chuyển đổi góc quay thành radian
        gantry_rad = np.radians(gantry_angle)
        
        # Tọa độ tâm xoay (mm)
        iso_x = isocenter[0] * voxel_size_mm[0]
        iso_y = isocenter[1] * voxel_size_mm[1]
        iso_z = isocenter[2] * voxel_size_mm[2]
        
        # Hướng chùm tia (vector đơn vị)
        # Gantry quay trong mặt phẳng xz, với 0 độ ứng với hướng z
        beam_dir = np.array([
            np.sin(gantry_rad),  # x
            0,  # y
            -np.cos(gantry_rad)  # z (ngược hướng)
        ])
        
        # Các vector vuông góc với chùm tia để tạo mặt phẳng nguồn
        u_vec = np.array([np.cos(gantry_rad), 0, np.sin(gantry_rad)])
        v_vec = np.array([0, 1, 0])
        
        # Vị trí nguồn (mm)
        source_pos = np.array([
            iso_x - beam_dir[0] * ssd,
            iso_y - beam_dir[1] * ssd,
            iso_z - beam_dir[2] * ssd
        ])
        
        # Chuyển đổi hệ số suy giảm vào bảng tra cứu
        # Tạo bảng ánh xạ từ mật độ sang hệ số suy giảm
        density_values = sorted(list(self.attenuation_coeff.keys()))
        attenuation_lut = {}
        compton_lut = {}
        
        for i in range(len(density_values) - 1):
            d1, d2 = density_values[i], density_values[i + 1]
            a1, a2 = self.attenuation_coeff[d1], self.attenuation_coeff[d2]
            c1, c2 = self.compton_ratio[d1], self.compton_ratio[d2]
            
            # Tạo các điểm nội suy tại mỗi 0.01 mật độ
            for d in np.arange(d1, d2, 0.01):
                # Nội suy tuyến tính
                alpha = (d - d1) / (d2 - d1) if d2 != d1 else 0
                attenuation_lut[round(d, 2)] = a1 + alpha * (a2 - a1)
                compton_lut[round(d, 2)] = c1 + alpha * (c2 - c1)
        
        # Thêm điểm cuối
        attenuation_lut[density_values[-1]] = self.attenuation_coeff[density_values[-1]]
        compton_lut[density_values[-1]] = self.compton_ratio[density_values[-1]]
        
        # Mô phỏng từng hạt
        for i in range(num_particles):
            # Tạo hạt tại nguồn với hướng ngẫu nhiên trong vùng trường xạ
            # Tọa độ trong mặt phẳng nguồn
            width, height = field_size
            u = rng.uniform(-width/2, width/2)  # mm
            v = rng.uniform(-height/2, height/2)  # mm
            
            # Tọa độ điểm bắt đầu
            particle_pos = source_pos + u * u_vec + v * v_vec
            
            # Hướng: hướng chùm tia với nhiễu loạn nhỏ
            direction = beam_dir + rng.normal(0, 0.01, 3)
            direction = direction / np.linalg.norm(direction)
            
            # Năng lượng hạt (tỷ lệ với năng lượng chùm tia)
            energy_factor = energy / 6.0  # Chuẩn hóa với 6MV
            
            # Theo dõi hạt cho đến khi năng lượng < 5% hoặc ra khỏi lưới
            weight = 1.0  # trọng số hạt ban đầu
            
            while weight > 0.05:
                # Chuyển từ mm sang đơn vị voxel
                voxel_x = int(particle_pos[0] / voxel_size_mm[0])
                voxel_y = int(particle_pos[1] / voxel_size_mm[1])
                voxel_z = int(particle_pos[2] / voxel_size_mm[2])
                
                # Kiểm tra nếu hạt nằm ngoài lưới
                if (voxel_x < 0 or voxel_x >= shape[0] or 
                    voxel_y < 0 or voxel_y >= shape[1] or 
                    voxel_z < 0 or voxel_z >= shape[2]):
                    break
                
                # Lấy mật độ tại voxel hiện tại
                density = density_grid[voxel_x, voxel_y, voxel_z]
                density_rounded = round(float(density), 2)
                
                # Lấy hệ số suy giảm từ bảng tra cứu
                if density_rounded in attenuation_lut:
                    attenuation = attenuation_lut[density_rounded]
                    compton_prob = compton_lut[density_rounded]
                else:
                    # Lấy giá trị gần nhất
                    nearest_density = min(attenuation_lut.keys(), key=lambda x: abs(x - density_rounded))
                    attenuation = attenuation_lut[nearest_density]
                    compton_prob = compton_lut[nearest_density]
                
                # Điều chỉnh hệ số suy giảm theo năng lượng
                attenuation = attenuation * (6.0 / energy)
                
                # Tính quãng đường đi qua voxel
                # Tính khoảng cách đến biên voxel
                next_x = (int(voxel_x + 0.5 * (1 + np.sign(direction[0]))) * voxel_size_mm[0])
                next_y = (int(voxel_y + 0.5 * (1 + np.sign(direction[1]))) * voxel_size_mm[1])
                next_z = (int(voxel_z + 0.5 * (1 + np.sign(direction[2]))) * voxel_size_mm[2])
                
                dist_x = abs((next_x - particle_pos[0]) / direction[0]) if direction[0] != 0 else float('inf')
                dist_y = abs((next_y - particle_pos[1]) / direction[1]) if direction[1] != 0 else float('inf')
                dist_z = abs((next_z - particle_pos[2]) / direction[2]) if direction[2] != 0 else float('inf')
                
                # Quãng đường nhỏ nhất đến biên voxel
                step = min(dist_x, dist_y, dist_z)
                
                # Tính xác suất tương tác
                p_interact = 1.0 - np.exp(-attenuation * step / 10)  # chuyển từ mm sang cm
                
                # Tích lũy liều
                energy_deposit = weight * p_interact * (1.0 - compton_prob)
                dose_grid[voxel_x, voxel_y, voxel_z] += energy_deposit
                variance_grid[voxel_x, voxel_y, voxel_z] += energy_deposit ** 2
                
                # Kiểm tra xem hạt có tương tác không
                if rng.random() < p_interact:
                    # Có tương tác
                    if rng.random() < compton_prob:
                        # Tán xạ Compton
                        # Giảm trọng số
                        weight *= 0.8
                        
                        # Thay đổi hướng ngẫu nhiên (mô phỏng tán xạ Compton)
                        theta = rng.normal(0, 0.2)  # radian
                        phi = rng.uniform(0, 2 * np.pi)
                        
                        # Tạo vector hướng mới
                        cos_theta = np.cos(theta)
                        sin_theta = np.sin(theta)
                        cos_phi = np.cos(phi)
                        sin_phi = np.sin(phi)
                        
                        # Tạo hệ trục mới với trục z là hướng cũ
                        old_dir = direction
                        
                        # Tìm trục vuông góc thứ nhất
                        if abs(old_dir[0]) < 0.9:
                            axis1 = np.array([1, 0, 0])
                        else:
                            axis1 = np.array([0, 1, 0])
                        
                        axis1 = axis1 - np.dot(axis1, old_dir) * old_dir
                        axis1 = axis1 / np.linalg.norm(axis1)
                        
                        # Tìm trục vuông góc thứ hai
                        axis2 = np.cross(old_dir, axis1)
                        
                        # Tính hướng mới
                        new_dir = cos_theta * old_dir + sin_theta * cos_phi * axis1 + sin_theta * sin_phi * axis2
                        direction = new_dir / np.linalg.norm(new_dir)
                    else:
                        # Hấp thụ quang điện
                        break
                
                # Di chuyển hạt
                particle_pos = particle_pos + direction * step * 1.01  # 1.01 để tránh ở biên
        
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
        except Exception as e:
            self.logger.log_error(f"Lỗi khi lưu kết quả: {str(e)}")
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
        except Exception as e:
            self.logger.log_error(f"Lỗi khi tải kết quả: {str(e)}")
            return False

# Tạo instance mặc định
monte_carlo = MonteCarlo() 