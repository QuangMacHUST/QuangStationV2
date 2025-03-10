#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Wrapper Python cho module tính toán liều C++.
"""

import os
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import time
import importlib
from datetime import datetime

try:
    from quangstation.dose_calculation._dose_engine import CollapsedConeConvolution, PencilBeam, AAA, AcurosXB
    HAS_CPP_MODULE = True
except ImportError:
    HAS_CPP_MODULE = False
    from quangstation.utils.logging import get_logger
    logger = get_logger("DoseCalculation")
    logger.warning("Không thể import module C++ _dose_engine. Sử dụng phiên bản Python thuần túy.")

class DoseCalculator:
    """
    Lớp wrapper cho các thuật toán tính toán liều.
    Hỗ trợ cả triển khai C++ và Python thuần túy.
    """
    
    ALGO_COLLAPSED_CONE = "collapsed_cone"
    ALGO_PENCIL_BEAM = "pencil_beam"
    ALGO_AAA = "aaa"
    ALGO_ACUROS_XB = "acuros_xb"
    ALGO_MONTE_CARLO = "monte_carlo"
    ALGO_GRID_BASED = "grid_based"
    ALGO_CONVOLUTION = "convolution_superposition"
    
    def __init__(self, algorithm: str = ALGO_COLLAPSED_CONE, resolution_mm: float = 3.0):
        """
        Khởi tạo bộ tính toán liều.
        
        Args:
            algorithm: Thuật toán tính toán liều
            resolution_mm: Độ phân giải tính toán (mm)
        """
        self.algorithm = algorithm
        self.resolution_mm = resolution_mm
        self.image_data = None
        self.spacing = None
        self.beams = []
        self.structures = {}
        self.dose_matrix = None
        self.hu_to_density_file = None
        self.heterogeneity_correction = True
        self.options = {}
        self.advanced_algorithm = None
        self.logger = get_logger(__name__)
        self.use_cpp = True  # Mặc định sẽ cố gắng sử dụng module C++ nếu có
        
        self.logger.info(f"Khởi tạo bộ tính toán liều với thuật toán {algorithm}, "
                        f"độ phân giải {resolution_mm} mm")

    def set_patient_data(self, image_data: np.ndarray, spacing: List[float]):
        """
        Thiết lập dữ liệu bệnh nhân.
        
        Args:
            image_data: Dữ liệu hình ảnh CT 3D (HU)
            spacing: Khoảng cách giữa các voxel (mm)
        """
        if not isinstance(image_data, np.ndarray):
            raise TypeError("image_data phải là numpy array")
            
        if len(image_data.shape) != 3:
            raise ValueError("image_data phải là mảng 3D")
            
        if len(spacing) != 3:
            raise ValueError("spacing phải có 3 phần tử (mm)")
            
        self.image_data = image_data
        self.spacing = spacing
        
        # Ước tính bộ nhớ đang sử dụng
        memory_mb = image_data.nbytes / (1024 * 1024)
        self.logger.info(f"Đã thiết lập dữ liệu bệnh nhân kích thước {image_data.shape}, "
                        f"bộ nhớ: {memory_mb:.1f} MB")
        
        # Reset dữ liệu liều
        self.dose_matrix = None
        
        # Khởi tạo thuật toán tiên tiến nếu cần
        if self.algorithm in [self.ALGO_GRID_BASED, self.ALGO_CONVOLUTION, self.ALGO_ACUROS_XB]:
            self._initialize_advanced_algorithm()

    def set_hu_to_density_file(self, file_path: str):
        """
        Thiết lập file chuyển đổi HU sang mật độ điện tử.
        
        Args:
            file_path: Đường dẫn đến file chuyển đổi
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Không tìm thấy file: {file_path}")
            
        self.hu_to_density_file = file_path
        self.logger.info(f"Đã thiết lập file chuyển đổi HU sang mật độ: {file_path}")

    def set_heterogeneity_correction(self, enabled: bool):
        """
        Bật/tắt tính toán hiệu chỉnh không đồng nhất.
        
        Args:
            enabled: True để bật, False để tắt
        """
        self.heterogeneity_correction = enabled
        self.logger.info(f"{'Bật' if enabled else 'Tắt'} hiệu chỉnh không đồng nhất")

    def set_calculation_options(self, options: Dict[str, Any]):
        """
        Thiết lập các tùy chọn tính toán.
        
        Args:
            options: Dictionary các tùy chọn
        """
        self.options.update(options)
        self.logger.info(f"Đã cập nhật tùy chọn tính toán: {options}")
        
        # Cập nhật cấu hình cho thuật toán tiên tiến nếu đã được khởi tạo
        if self.advanced_algorithm is not None:
            self.advanced_algorithm.set_configuration(options)

    def add_beam(self, beam_data: Dict[str, Any]):
        """
        Thêm chùm tia.
        
        Args:
            beam_data: Thông tin chùm tia
        """
        getattr(self, "beams", {}).append(beam_data.copy())
        self.logger.info(f"Đã thêm chùm tia {beam_data.get('id', len(getattr(self, "beams", {})))}")
        
        # Thêm chùm tia vào thuật toán tiên tiến nếu đã được khởi tạo
        if self.advanced_algorithm is not None:
            self.advanced_algorithm.add_beam(beam_data)

    def add_structure(self, name: str, mask: np.ndarray):
        """
        Thêm cấu trúc giải phẫu.
        
        Args:
            name: Tên cấu trúc
            mask: Mặt nạ cấu trúc (đồng kích thước với image_data)
        """
        if self.image_data is not None and mask.shape != self.image_data.shape:
            raise ValueError(f"Kích thước mask ({mask.shape}) không khớp với kích thước ảnh ({self.image_data.shape})")
            
        self.structures[name] = mask.astype(bool)
        self.logger.info(f"Đã thêm cấu trúc {name}")
        
        # Thêm cấu trúc vào thuật toán tiên tiến nếu đã được khởi tạo
        if self.advanced_algorithm is not None:
            self.advanced_algorithm.add_structure(name, mask)

    def calculate_dose(self, technique=None, structures=None) -> np.ndarray:
        """
        Tính toán liều dựa trên kỹ thuật xạ trị và các cấu trúc.
        
        Args:
            technique: Đối tượng kỹ thuật xạ trị (RTTechnique)
            structures: Dictionary các cấu trúc {name: mask}
            
        Returns:
            np.ndarray: Ma trận liều 3D hoặc None nếu có lỗi
        """
        # Khởi tạo hẹn giờ để đo thời gian tính toán
        start_time = datetime.now()
        self.logger.info(f"Bắt đầu tính toán liều với thuật toán {self.algorithm} lúc {start_time.strftime('%H:%M:%S')}")
        
        # Kiểm tra thiết lập dữ liệu
        if self.image_data is None:
            self.logger.error("Chưa thiết lập dữ liệu hình ảnh")
            return None
            
        # Nếu có technique, thiết lập beams từ technique
        if technique is not None:
            self.logger.info(f"Sử dụng kỹ thuật xạ trị: {technique}")
            try:
                if hasattr(technique, 'get_beams'):
                    new_beams = technique.get_beams()
                    if new_beams:
                        self.beams = new_beams
                        self.logger.info(f"Đã thiết lập {len(new_beams)} chùm tia từ kỹ thuật {technique}")
                    else:
                        self.logger.warning(f"Kỹ thuật {technique} không cung cấp chùm tia nào")
            except Exception as error:
                self.logger.error(f"Lỗi khi lấy chùm tia từ kỹ thuật: {str(error)}")
        
        # Thêm cấu trúc nếu được cung cấp
        if structures is not None:
            self.logger.info(f"Nhận được {len(structures)} cấu trúc để tính toán")
            try:
                for name, mask in structures.items():
                    self.add_structure(name, mask)
            except Exception as error:
                self.logger.error(f"Lỗi khi thêm cấu trúc: {str(error)}")
        
        # Kiểm tra xem có chùm tia nào không
        if not getattr(self, "beams", {}):
            self.logger.error("Không có chùm tia nào để tính toán liều")
            return None
            
        # Tính toán liều dựa trên phương pháp được chọn
        self.logger.info(f"Bắt đầu tính toán liều với thuật toán {self.algorithm}")
        
        result = None
        try:
            # Kiểm tra xem có thể sử dụng C++ không
            use_cpp = self._has_cpp_extension() and self.use_cpp
            if use_cpp:
                self.logger.info("Sử dụng phiên bản C++ để tính toán")
                result = self._calculate_dose_cpp()
            else:
                self.logger.info("Sử dụng phiên bản Python thuần túy để tính toán")
                result = self._calculate_dose_python()
                
            # Kiểm tra kết quả
            if result is None:
                self.logger.error("Không thể tính toán liều (kết quả là None)")
                return None
                
            # Ghi log thông tin
            elapsed_time = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"Tính toán liều hoàn tất trong {elapsed_time:.2f} giây")
            self.logger.info(f"Kích thước ma trận liều: {result.shape}")
            self.logger.info(f"Liều tối thiểu: {np.min(result):.4f}, Liều tối đa: {np.max(result):.4f}, Liều trung bình: {np.mean(result):.4f}")
            
            # Lưu kết quả
            self.dose_matrix = result
            
            # Cập nhật thông tin tính toán
            self.calculation_info['completion_time'] = datetime.now().isoformat()
            self.calculation_info['algorithm'] = self.algorithm
            self.calculation_info['voxel_count'] = np.prod(result.shape)
            self.calculation_info['elapsed_time'] = elapsed_time
            self.calculation_info['min_dose'] = float(np.min(result))
            self.calculation_info['max_dose'] = float(np.max(result))
            self.calculation_info['mean_dose'] = float(np.mean(result))
            
            return result
            
        except Exception as error:
            import traceback
            self.logger.error(f"Lỗi khi tính toán liều: {str(error)}")
            self.logger.error(traceback.format_exc())
            
            # Cập nhật thông tin về lỗi
            self.calculation_info['error'] = str(error)
            self.calculation_info['error_time'] = datetime.now().isoformat()
            
            return None

    def _has_cpp_extension(self) -> bool:
        """
        Kiểm tra xem có extension C++ của module dose_engine hay không.
        
        Returns:
            bool: True nếu có extension C++, False nếu không
        """
        try:
            if self.algorithm == self.ALGO_COLLAPSED_CONE:
                module_name = "quangstation.dose_calculation._dose_engine"
                class_name = "CollapsedConeConvolution"
            elif self.algorithm == self.ALGO_PENCIL_BEAM:
                module_name = "quangstation.dose_calculation._dose_engine"
                class_name = "PencilBeam"
            elif self.algorithm == self.ALGO_AAA:
                module_name = "quangstation.dose_calculation._dose_engine"
                class_name = "AAA"
            elif self.algorithm == self.ALGO_ACUROS_XB:
                module_name = "quangstation.dose_calculation._dose_engine"
                class_name = "AcurosXB"
            elif self.algorithm == self.ALGO_MONTE_CARLO:
                module_name = "quangstation.dose_calculation._dose_engine"
                class_name = "MonteCarlo"
            elif self.algorithm == self.ALGO_GRID_BASED:
                module_name = "quangstation.dose_calculation._dose_engine"
                class_name = "GridBased"
            elif self.algorithm == self.ALGO_CONVOLUTION:
                module_name = "quangstation.dose_calculation._dose_engine"
                class_name = "ConvolutionSuperposition"
            else:
                self.logger.warning(f"Thuật toán không rõ: {self.algorithm}. Thử truy cập module base.")
                module_name = "quangstation.dose_calculation._dose_engine"
                class_name = "DoseAlgorithm"
            
            # Thử import module và lớp
            module = importlib.import_module(module_name)
            getattr(module, class_name)
            
            # Nếu không lỗi, có extension C++
            self.logger.info(f"Đã tìm thấy extension C++ cho thuật toán {self.algorithm}")
            return True
        except (ImportError, AttributeError) as e:
            self.logger.info(f"Không tìm thấy extension C++ cho thuật toán {self.algorithm}: {str(e)}")
            
            # Nếu ta đã cấu hình sử dụng C++ nhưng không tìm thấy, ghi log cảnh báo
            if self.use_cpp:
                self.logger.warning("Đã cấu hình sử dụng C++ nhưng không tìm thấy extension, sẽ sử dụng Python thuần túy")
            return False
        except Exception as error:
            self.logger.error(f"Lỗi không xác định khi kiểm tra extension C++: {str(error)}")
            return False
    
    def _calculate_dose_cpp(self) -> np.ndarray:
        """
        Tính toán liều bằng extension C++.
        
        Returns:
            np.ndarray: Ma trận liều 3D
        """
        try:
            # Kiểm tra module C++ tương ứng
            if self.algorithm == self.ALGO_COLLAPSED_CONE:
                module_name = "quangstation.dose_calculation._dose_engine"
                class_name = "CollapsedConeConvolution"
            elif self.algorithm == self.ALGO_PENCIL_BEAM:
                module_name = "quangstation.dose_calculation._dose_engine"
                class_name = "PencilBeam"
            elif self.algorithm == self.ALGO_AAA:
                module_name = "quangstation.dose_calculation._dose_engine"
                class_name = "AAA"
            elif self.algorithm == self.ALGO_ACUROS_XB:
                module_name = "quangstation.dose_calculation._dose_engine"
                class_name = "AcurosXB"
            elif self.algorithm == self.ALGO_MONTE_CARLO:
                module_name = "quangstation.dose_calculation._dose_engine"
                class_name = "MonteCarlo"
            else:
                raise ValueError(f"Thuật toán C++ không được hỗ trợ: {self.algorithm}")
            
            self.logger.info(f"Đang khởi tạo thuật toán C++ {class_name} từ module {module_name}")
            
            # Động thử import module
            try:
                module = importlib.import_module(module_name)
                algorithm_class = getattr(module, class_name)
            except (ImportError, AttributeError) as e:
                self.logger.warning(f"Không thể import module C++ {module_name}.{class_name}: {str(e)}")
                self.logger.info("Chuyển sang bản Python thuần túy")
                return self._calculate_dose_python()
            
            # Ghi log bắt đầu tính toán
            start_time = datetime.now()
            self.logger.info(f"Bắt đầu tính toán liều với thuật toán C++ {class_name} lúc {start_time.isoformat()}")
            
            # Khởi tạo thuật toán
            algo = algorithm_class(resolution=self.resolution_mm)
            
            # Thiết lập file chuyển đổi HU nếu có
            if hasattr(algo, 'set_hu_to_ed_conversion_file') and self.hu_to_density_file:
                self.logger.info(f"Thiết lập file chuyển đổi HU-ED: {self.hu_to_density_file}")
                algo.set_hu_to_ed_conversion_file(self.hu_to_density_file)
            
            # Thiết lập hiệu chỉnh không đồng nhất nếu có
            if hasattr(algo, 'set_heterogeneity_correction'):
                self.logger.info(f"Thiết lập hiệu chỉnh không đồng nhất: {self.heterogeneity_correction}")
                algo.set_heterogeneity_correction(self.heterogeneity_correction)
            
            # Thiết lập các tùy chọn khác nếu có
            option_methods = {
                'set_num_photons': 'num_photons',
                'set_max_scatter_radius': 'max_scatter_radius',
                'set_beta_param': 'beta_param',
                'set_num_threads': 'num_threads'
            }
            
            for method, option_key in option_methods.items():
                if hasattr(algo, method) and option_key in self.options:
                    getattr(algo, method)(self.options[option_key])
            
            # Chuyển đổi dữ liệu Python sang định dạng C++
            # Kiểm tra xem có phương thức nào hỗ trợ trực tiếp numpy array không
            if hasattr(algo, 'calculate_from_numpy'):
                # Nếu có, sử dụng trực tiếp
                beams_data = []
                for beam in getattr(self, "beams", {}):
                    # Chuyển đổi beam sang format phù hợp
                    beams_data.append({
                        'id': beam.get('id', ''),
                        'type': beam.get('type', 'photon'),
                        'energy': beam.get('energy', 6.0),
                        'gantry_angle': beam.get('gantry_angle', 0.0),
                        'collimator_angle': beam.get('collimator_angle', 0.0),
                        'couch_angle': beam.get('couch_angle', 0.0),
                        'isocenter': beam.get('isocenter', [0, 0, 0]),
                        'weight': beam.get('weight', 1.0),
                        'mlc_positions': beam.get('mlc_positions', []),
                        'is_arc': beam.get('is_arc', False),
                        'arc_start_angle': beam.get('arc_start_angle', 0.0),
                        'arc_stop_angle': beam.get('arc_stop_angle', 0.0),
                        'arc_direction': beam.get('arc_direction', 1)
                    })
                
                prescription = self.options.get('prescribed_dose', 0.0)
                fractions = self.options.get('fractions', 1)
                
                return algo.calculate_from_numpy(
                    self.image_data, 
                    self.spacing, 
                    beams_data, 
                    prescription,
                    fractions
                )
            else:
                # Nếu không, cần chuyển đổi dữ liệu sang cấu trúc C++
                # Đảm bảo mọi người đang sử dụng mã này đọc kỹ tài liệu API C++
                logger.warning("API C++ không hỗ trợ trực tiếp numpy arrays, chuyển sang bản Python thuần túy")
                return self._calculate_dose_python()
            
        except Exception as error:
            logger.error(f"Lỗi khi tính toán liều bằng C++: {str(error)}")
            logger.info("Chuyển sang bản Python thuần túy")
            return self._calculate_dose_python()
    
    def _calculate_dose_python(self) -> np.ndarray:
        """Tính toán liều bằng Python thuần túy."""
        # Tạo ma trận liều trống
        dose_matrix = np.zeros_like(self.image_data, dtype=np.float32)
        
        # Kiểm tra nếu không có chùm tia
        if not getattr(self, "beams", {}):
            self.logger.error("Không có chùm tia nào để tính toán liều")
            return dose_matrix
            
        # Tính toán liều cho từng chùm tia
        self.logger.info(f"Tính toán liều cho {len(getattr(self, "beams", {}))} chùm tia")
        
        for i, beam in enumerate(getattr(self, "beams", {})):
            self.logger.info(f"Tính toán liều cho chùm tia {i+1}/{len(getattr(self, "beams", {}))}")
            
            # Lấy thông số chùm tia
            gantry_angle = beam.get('gantry_angle', 0.0)
            collimator_angle = beam.get('collimator_angle', 0.0)
            couch_angle = beam.get('couch_angle', 0.0)
            energy = beam.get('energy', 6.0)
            weight = beam.get('weight', 1.0)
            field_size = beam.get('field_size', [10.0, 10.0])
            
            # Lấy isocenter
            isocenter = beam.get('isocenter', None)
            
            # Tính tọa độ isocenter trong chỉ số voxel
            if isocenter is None:
                # Mặc định là giữa khối hình ảnh
                isocenter_idx = [d // 2 for d in self.image_data.shape]
            else:
                # Chuyển từ tọa độ vật lý (mm) sang chỉ số voxel
                isocenter_idx = [
                    int(isocenter[0] / self.spacing[0]),
                    int(isocenter[1] / self.spacing[1]),
                    int(isocenter[2] / self.spacing[2])
                ]
                
            # Tính vector hướng chùm tia từ góc quay
            gantry_rad = np.radians(gantry_angle)
            couch_rad = np.radians(couch_angle)
            
            # Tính toán hướng chùm tia với góc gantry và couch
            # Xoay quanh trục z (gantry) rồi xoay quanh trục y (couch)
            source_direction = [
                np.sin(gantry_rad) * np.cos(couch_rad),
                np.cos(gantry_rad) * np.cos(couch_rad),
                np.sin(couch_rad)
            ]
            
            # Chuẩn hóa vector hướng
            norm = np.sqrt(sum(d*d for d in source_direction))
            source_direction = [d/norm for d in source_direction]
            
            # Lấy thông tin MLC nếu có
            mlc = beam.get('mlc', None)
            
            # Lấy thông tin wedge nếu có
            wedge = beam.get('wedge', None)
            
            # Lấy thông tin bolus nếu có
            bolus = beam.get('bolus', None)
            
            # Gọi thuật toán tính toán dựa trên loại
            if self.algorithm == self.ALGO_PENCIL_BEAM:
                self._calculate_simple_pencil_beam(dose_matrix, self.image_data, self.spacing, 
                                               isocenter_idx, source_direction, energy, weight,
                                               field_size=field_size, mlc=mlc, wedge=wedge)
            elif self.algorithm == self.ALGO_AAA:
                self._calculate_simple_aaa(dose_matrix, self.image_data, self.spacing, 
                                         isocenter_idx, source_direction, energy, weight,
                                         field_size=field_size, mlc=mlc, wedge=wedge)
            elif self.algorithm == self.ALGO_COLLAPSED_CONE:
                self._calculate_simple_collapsed_cone(dose_matrix, self.image_data, self.spacing, 
                                                   isocenter_idx, source_direction, energy, weight,
                                                   field_size=field_size, mlc=mlc, wedge=wedge)
            elif self.algorithm == self.ALGO_ACUROS_XB:
                self._calculate_simple_acuros(dose_matrix, self.image_data, self.spacing, 
                                            isocenter_idx, source_direction, energy, weight,
                                            field_size=field_size, mlc=mlc, wedge=wedge)
            else:
                # Mặc định sử dụng pencil beam
                self.logger.warning(f"Thuật toán {self.algorithm} không được hỗ trợ trong Python thuần túy. Sử dụng Pencil Beam.")
                self._calculate_simple_pencil_beam(dose_matrix, self.image_data, self.spacing, 
                                               isocenter_idx, source_direction, energy, weight,
                                               field_size=field_size, mlc=mlc, wedge=wedge)
        
        # Chuẩn hóa liều nếu cần
        if 'prescribed_dose' in self.options:
            prescribed_dose = self.options['prescribed_dose']
            
            # Xác định điểm chuẩn hóa
            if 'normalization_point' in self.options:
                # Sử dụng điểm được chỉ định
                norm_point = self.options['normalization_point']
                
                # Chuyển từ tọa độ vật lý (mm) sang chỉ số voxel
                norm_idx = [
                    int(norm_point[0] / self.spacing[0]),
                    int(norm_point[1] / self.spacing[1]),
                    int(norm_point[2] / self.spacing[2])
                ]
                
                # Chuẩn hóa liều
                dose_at_norm = dose_matrix[norm_idx[0], norm_idx[1], norm_idx[2]]
                if dose_at_norm > 0:
                    scale_factor = prescribed_dose / dose_at_norm
                    dose_matrix *= scale_factor
                    self.logger.info(f"Đã chuẩn hóa liều tại điểm ({norm_point}) thành {prescribed_dose} Gy")
            elif 'normalization_volume' in self.options and 'normalization_percent' in self.options:
                # Chuẩn hóa theo thể tích (ví dụ: D95 = prescribed_dose)
                norm_volume_name = self.options['normalization_volume']
                norm_percent = self.options['normalization_percent']
                
                if norm_volume_name in self.structures:
                    volume_mask = self.structures[norm_volume_name]
                    dose_in_volume = dose_matrix[volume_mask > 0]
                    
                    if len(dose_in_volume) > 0:
                        # Sắp xếp giá trị liều
                        sorted_dose = np.sort(dose_in_volume)
                        
                        # Tìm điểm phân vị (ví dụ: D95)
                        index = int(len(sorted_dose) * (100 - norm_percent) / 100)
                        dose_at_percentile = sorted_dose[index]
                        
                        if dose_at_percentile > 0:
                            scale_factor = prescribed_dose / dose_at_percentile
                            dose_matrix *= scale_factor
                            self.logger.info(f"Đã chuẩn hóa D{norm_percent} của {norm_volume_name} thành {prescribed_dose} Gy")
                
        self.logger.info("Đã hoàn thành tính toán liều bằng Python thuần túy")
        
        return dose_matrix
    
    def _calculate_simple_pencil_beam(self, dose_matrix, image_data, spacing, iso_idx, source_direction, energy, weight, **kwargs):
        """Tính toán liều bằng thuật toán Pencil Beam đơn giản."""
        # Lấy kích thước hình ảnh
        shape = image_data.shape
        
        # Tính ma trận tọa độ
        z_coords, y_coords, x_coords = np.meshgrid(
            np.arange(shape[0]),
            np.arange(shape[1]),
            np.arange(shape[2]),
            indexing='ij'
        )
        
        # Tính khoảng cách từ mỗi voxel đến isocenter
        dx = (x_coords - iso_idx[2]) * spacing[2]
        dy = (y_coords - iso_idx[1]) * spacing[1]
        dz = (z_coords - iso_idx[0]) * spacing[0]
        
        # Tính vector từ isocenter đến mỗi voxel
        dist_vector = np.stack([dz, dy, dx], axis=-1)
        
        # Tính độ sâu dọc theo hướng chùm tia
        depths = np.dot(dist_vector, source_direction)
        
        # Tính khoảng cách vuông góc với trục chùm tia
        perp_dist = np.linalg.norm(
            dist_vector - np.expand_dims(depths, -1) * np.array(source_direction),
            axis=-1
        )
        
        # Tạo mặt nạ cho vùng có độ sâu dương (phía sau isocenter theo hướng chùm tia)
        mask = depths > 0
        
        # Tạo kernel cho PDD (Percentage Depth Dose)
        if energy <= 6:  # 6MV
            # Dmax ở khoảng 15mm
            dmax = 15.0
            mu = 0.0461  # Hệ số suy giảm cho nước
        elif energy <= 10:  # 10MV
            dmax = 25.0
            mu = 0.0327
        else:  # >10MV
            dmax = 35.0
            mu = 0.0286
            
        # Tính PDD
        depths_mm = depths * spacing[0]  # Chuyển về mm
        pdd = np.exp(-mu * (depths_mm - dmax)) * (1 - np.exp(-0.06 * depths_mm))
        pdd = np.where(depths_mm < 0, 0, pdd)  # Loại bỏ giá trị âm
        
        # Tính profile ngang
        sigma = 30.0 + 0.5 * depths_mm  # Độ rộng tăng theo độ sâu
        profile = np.exp(-(perp_dist**2) / (2 * sigma**2))
        
        # Hiệu chỉnh theo mật độ điện tử (đơn giản)
        density_correction = np.where(image_data > -100, 1.0, 0.25)  # Đơn giản: không khí vs. mô
        
        if not self.heterogeneity_correction:
            density_correction = np.ones_like(density_correction)
            
        # Tính liều cuối cùng
        beam_dose = pdd * profile * density_correction * weight
        
        # Cộng vào ma trận liều
        dose_matrix += beam_dose
        
        self.logger.info(f"Đã tính toán liều cho chùm {energy}MV với thuật toán Pencil Beam")

    def _calculate_simple_aaa(self, dose_matrix, image_data, spacing, iso_idx, source_direction, energy, weight, **kwargs):
        """Tính toán liều bằng thuật toán AAA đơn giản."""
        # Lấy kích thước hình ảnh
        shape = image_data.shape
        
        # Tính ma trận tọa độ
        z_coords, y_coords, x_coords = np.meshgrid(
            np.arange(shape[0]),
            np.arange(shape[1]),
            np.arange(shape[2]),
            indexing='ij'
        )
        
        # Tính khoảng cách từ mỗi voxel đến isocenter
        dx = (x_coords - iso_idx[2]) * spacing[2]
        dy = (y_coords - iso_idx[1]) * spacing[1]
        dz = (z_coords - iso_idx[0]) * spacing[0]
        
        # Tính vector từ isocenter đến mỗi voxel
        dist_vector = np.stack([dz, dy, dx], axis=-1)
        
        # Tính độ sâu dọc theo hướng chùm tia
        depths = np.dot(dist_vector, source_direction)
        
        # Tính khoảng cách vuông góc với trục chùm tia
        perp_dist = np.linalg.norm(
            dist_vector - np.expand_dims(depths, -1) * np.array(source_direction),
            axis=-1
        )
        
        # Tính PDD (dựa trên thông số thực nghiệm)
        depths_mm = depths * spacing[0]  # Chuyển về mm
        
        # Thông số cho AAA
        if energy <= 6:  # 6MV
            alpha = 0.0158
            beta = 0.00364
            gamma = 0.668
        elif energy <= 10:  # 10MV
            alpha = 0.0117
            beta = 0.00345
            gamma = 0.772
        else:  # >10MV
            alpha = 0.0102
            beta = 0.00352
            gamma = 0.821
            
        # Build-up + exponential attenuation
        pdd = np.exp(-alpha * depths_mm) * (1 - np.exp(-beta * depths_mm)) * np.exp(gamma * np.log(100.0 / depths_mm) * np.exp(-depths_mm / 100.0))
        pdd = np.where(depths_mm <= 0, 0, pdd)  # Loại bỏ giá trị âm
        pdd = np.where(depths_mm < 1, pdd[depths_mm >= 1].min() if np.any(depths_mm >= 1) else 0, pdd)  # Xử lý vùng build-up
        
        # Profile ngang (Off-Axis Ratio)
        sigma_inplane = 27.0 + 0.35 * depths_mm
        sigma_crossplane = 27.0 + 0.35 * depths_mm
        profile = np.exp(-(perp_dist**2) / (2 * sigma_inplane * sigma_crossplane))
        
        # Hiệu chỉnh theo mật độ điện tử
        density_correction = np.ones_like(image_data, dtype=np.float32)
        
        if self.heterogeneity_correction:
            # Chuyển đổi HU sang mật độ điện tử tương đối (đơn giản)
            for z in range(shape[0]):
                for y in range(shape[1]):
                    for x in range(shape[2]):
                        density_correction[z, y, x] = self._simple_hu_to_density(image_data[z, y, x])
        
        # Tính liều sơ bộ (không có tán xạ)
        primary_dose = pdd * profile
        
        # Mô phỏng đơn giản của tán xạ
        from scipy.ndimage import gaussian_filter
        scatter_dose = gaussian_filter(primary_dose * density_correction, sigma=5.0) * 0.15
        
        # Tổng liều
        beam_dose = (primary_dose + scatter_dose) * density_correction * weight
        
        # Cộng vào ma trận liều
        dose_matrix += beam_dose
        
        self.logger.info(f"Đã tính toán liều cho chùm {energy}MV với thuật toán AAA")

    def _calculate_simple_acuros(self, dose_matrix, image_data, spacing, iso_idx, source_direction, energy, weight, **kwargs):
        """Tính toán liều bằng thuật toán Acuros đơn giản."""
        # Lấy kích thước hình ảnh
        shape = image_data.shape
        
        # Phân loại vật liệu dựa trên HU
        material_grid = np.zeros_like(image_data, dtype=np.uint8)
        material_grid[(image_data >= -1000) & (image_data < -400)] = 1  # Phổi
        material_grid[(image_data >= -400) & (image_data < 200)] = 2    # Mô mềm
        material_grid[(image_data >= 200) & (image_data < 1200)] = 3    # Xương
        material_grid[image_data >= 1200] = 4                          # Kim loại
        
        # Hệ số suy giảm cho từng vật liệu (1/mm) - giá trị tương đối
        mu_values = [0.0, 0.25, 1.0, 1.1, 1.5]  # Không khí, Phổi, Mô mềm, Xương, Kim loại
        
        # Chuyển đổi sang ma trận hệ số suy giảm
        mu_grid = np.zeros_like(image_data, dtype=np.float32)
        for i in range(len(mu_values)):
            mu_grid[material_grid == i] = mu_values[i]
            
        # Tính ma trận tọa độ
        z_coords, y_coords, x_coords = np.meshgrid(
            np.arange(shape[0]),
            np.arange(shape[1]),
            np.arange(shape[2]),
            indexing='ij'
        )
        
        # Tính khoảng cách từ mỗi voxel đến isocenter
        dx = (x_coords - iso_idx[2]) * spacing[2]
        dy = (y_coords - iso_idx[1]) * spacing[1]
        dz = (z_coords - iso_idx[0]) * spacing[0]
        
        # Tính vector từ isocenter đến mỗi voxel
        dist_vector = np.stack([dz, dy, dx], axis=-1)
        
        # Tính độ sâu dọc theo hướng chùm tia
        depths = np.dot(dist_vector, source_direction)
        
        # Tính khoảng cách vuông góc với trục chùm tia
        perp_dist = np.linalg.norm(
            dist_vector - np.expand_dims(depths, -1) * np.array(source_direction),
            axis=-1
        )
        
        # Tạo mặt nạ cho vùng trong trường chiếu
        field_size = 100.0  # mm
        in_field = (perp_dist <= field_size/2) & (depths >= 0)
        
        # Tính fluence photon ban đầu (đơn giản)
        fluence_grid = np.zeros_like(image_data, dtype=np.float32)
        fluence_grid[in_field] = 1.0
        
        # Điều chỉnh fluence dựa trên tỷ lệ liều theo độ sâu (PDD)
        depths_mm = depths * spacing[0]
        depths_mm = np.where(depths_mm < 0, 0, depths_mm)
        
        # Thông số PDD
        if energy <= 6:  # 6MV
            alpha = 0.0158
            beta = 0.00364
            gamma = 0.668
        elif energy <= 10:  # 10MV
            alpha = 0.0117
            beta = 0.00345
            gamma = 0.772
        else:  # >10MV
            alpha = 0.0102
            beta = 0.00352
            gamma = 0.821
            
        # Tính PDD
        pdd = np.exp(-alpha * depths_mm) * (1 - np.exp(-beta * depths_mm))
        pdd = np.where(depths_mm <= 0, 0, pdd)
        
        # Điều chỉnh fluence
        fluence_grid *= pdd
        
        # Mô phỏng đơn giản việc giải phương trình vận chuyển bức xạ tuyến tính
        # Lặp qua các lớp theo độ sâu tăng dần
        
        # Sắp xếp các voxel theo độ sâu
        sorted_indices = np.argsort(depths.flatten())
        flat_shape = depths.size
        
        # Tạo ma trận fluence mới
        new_fluence = np.copy(fluence_grid)
        
        # Lan truyền fluence qua các voxel
        for idx in sorted_indices:
            if idx == 0:
                continue  # Bỏ qua voxel đầu tiên
                
            # Chuyển từ chỉ số 1D sang 3D
            z, temp = divmod(idx, shape[1] * shape[2])
            y, x = divmod(temp, shape[2])
            
            # Lấy fluence và mu tại vị trí hiện tại
            current_mu = mu_grid[z, y, x]
            
            # Không xử lý nếu fluence = 0 hoặc mu = 0
            if new_fluence[z, y, x] == 0 or current_mu == 0:
                continue
                
            # Tìm voxel tiếp theo theo hướng chùm tia
            next_z = z + round(source_direction[0])
            next_y = y + round(source_direction[1])
            next_x = x + round(source_direction[2])
            
            # Kiểm tra xem vị trí tiếp theo có hợp lệ không
            if (0 <= next_z < shape[0] and 
                0 <= next_y < shape[1] and 
                0 <= next_x < shape[2]):
                
                # Tính fluence bị suy giảm
                step_size = np.mean(spacing)
                attenuation = np.exp(-current_mu * step_size * 0.01)  # Hệ số 0.01 để mô phỏng
                
                # Lan truyền fluence đến voxel tiếp theo
                new_fluence[next_z, next_y, next_x] += new_fluence[z, y, x] * attenuation
        
        # Chuyển đổi fluence sang liều
        # Hệ số chuyển đổi fluence sang liều cho từng loại vật liệu
        dose_conversion = [0.0, 0.8, 1.0, 1.1, 0.9]  # Không khí, Phổi, Mô mềm, Xương, Kim loại
        
        # Tạo ma trận chuyển đổi
        conversion_grid = np.zeros_like(image_data, dtype=np.float32)
        for i in range(len(dose_conversion)):
            conversion_grid[material_grid == i] = dose_conversion[i]
            
        # Tính liều
        beam_dose = new_fluence * conversion_grid * weight
        
        # Cộng vào ma trận liều
        dose_matrix += beam_dose
        
        self.logger.info(f"Đã tính toán liều cho chùm {energy}MV với thuật toán Acuros XB")

    def _simple_hu_to_density(self, hu_value):
        """Chuyển đổi HU sang mật độ điện tử (đơn giản)."""
        if hu_value < -1000:
            return 0.0
        elif hu_value < -100:  # Phổi
            return 0.25 + 0.0025 * (hu_value + 1000)
        elif hu_value < 0:  # Mỡ
            return 0.9 + 0.0010 * hu_value
        elif hu_value < 1000:  # Mô mềm và xương
            return 1.0 + 0.0005 * hu_value
        else:  # Kim loại
            return 1.5 + 0.0003 * (hu_value - 1000)

    def _initialize_advanced_algorithm(self):
        """Khởi tạo thuật toán tính toán liều tiên tiến."""
        try:
            from quangstation.dose_calculation.advanced_algorithms import create_dose_algorithm
            
            if self.algorithm == self.ALGO_GRID_BASED:
                self.advanced_algorithm = create_dose_algorithm('grid_based', 
                                                              resolution_mm=self.resolution_mm)
            elif self.algorithm == self.ALGO_CONVOLUTION:
                self.advanced_algorithm = create_dose_algorithm('convolution_superposition')
            elif self.algorithm == self.ALGO_ACUROS_XB:
                self.advanced_algorithm = create_dose_algorithm('acuros_xb')
            else:
                return
                
            # Thiết lập dữ liệu bệnh nhân
            if self.image_data is not None:
                self.advanced_algorithm.set_patient_data(self.image_data, self.spacing)
                
            # Thiết lập cấu hình
            self.advanced_algorithm.set_configuration(self.options)
            
            # Thêm cấu trúc đã có
            for name, mask in self.structures.items():
                self.advanced_algorithm.add_structure(name, mask)
                
            # Thêm chùm tia đã có
            for beam in getattr(self, "beams", {}):
                self.advanced_algorithm.add_beam(beam)
                
            self.logger.info(f"Đã khởi tạo thuật toán tiên tiến: {self.algorithm}")
            
        except ImportError as e:
            self.logger.warning(f"Không thể khởi tạo thuật toán tiên tiến: {str(e)}")
        except Exception as error:
            self.logger.error(f"Lỗi khi khởi tạo thuật toán tiên tiến: {str(e)}")

    def _calculate_with_advanced_algorithm(self) -> np.ndarray:
        """Tính toán liều với thuật toán tiên tiến."""
        if self.advanced_algorithm is None:
            self._initialize_advanced_algorithm()
            
        if self.advanced_algorithm is None:
            self.logger.warning(f"Không thể khởi tạo thuật toán tiên tiến {self.algorithm}, "
                                   "chuyển sang AAA đơn giản")
            # Sử dụng AAA đơn giản thay thế
            dose_matrix = np.zeros_like(self.image_data, dtype=np.float32)
            for i, beam in enumerate(getattr(self, "beams", {})):
                gantry_angle = beam.get('gantry_angle', 0.0)
                energy = beam.get('energy', 6.0)
                weight = beam.get('weight', 1.0)
                isocenter = beam.get('isocenter', None)
                
                # Tính tọa độ isocenter trong chỉ số voxel
                if isocenter is None:
                    isocenter_idx = [d // 2 for d in self.image_data.shape]
                else:
                    isocenter_idx = [
                        int(isocenter[0] / self.spacing[0]),
                        int(isocenter[1] / self.spacing[1]),
                        int(isocenter[2] / self.spacing[2])
                    ]
                # Tính vector hướng chùm tia từ góc quay
                gantry_rad = np.radians(gantry_angle)
                source_direction = [
                    np.sin(gantry_rad),
                    np.cos(gantry_rad),
                    0.0
                ]
                
                self._calculate_simple_aaa(dose_matrix, self.image_data, self.spacing, 
                                         isocenter_idx, source_direction, energy, weight)
                                         
            return dose_matrix
            
        try:
            # Tính toán liều với thuật toán tiên tiến
            dose_matrix = self.advanced_algorithm.calculate()
            return dose_matrix
        except Exception as error:
            self.logger.error(f"Lỗi khi tính toán liều với thuật toán tiên tiến: {str(error)}")
            # Sử dụng AAA đơn giản thay thế
            self.logger.info("Chuyển sang AAA đơn giản")
            
            dose_matrix = np.zeros_like(self.image_data, dtype=np.float32)
            for i, beam in enumerate(getattr(self, "beams", {})):
                gantry_angle = beam.get('gantry_angle', 0.0)
                energy = beam.get('energy', 6.0)
                weight = beam.get('weight', 1.0)
                isocenter = beam.get('isocenter', None)
                
                # Tính tọa độ isocenter trong chỉ số voxel
                if isocenter is None:
                    isocenter_idx = [d // 2 for d in self.image_data.shape]
                else:
                    isocenter_idx = [
                        int(isocenter[0] / self.spacing[0]),
                        int(isocenter[1] / self.spacing[1]),
                        int(isocenter[2] / self.spacing[2])
                    ]
                    
                # Tính vector hướng chùm tia từ góc quay
                gantry_rad = np.radians(gantry_angle)
                source_direction = [
                    np.sin(gantry_rad),
                    np.cos(gantry_rad),
                    0.0
                ]
                
                self._calculate_simple_aaa(dose_matrix, self.image_data, self.spacing, 
                                         isocenter_idx, source_direction, energy, weight)
                                         
            return dose_matrix

    def _calculate_monte_carlo(self) -> np.ndarray:
        """Tính toán liều bằng thuật toán Monte Carlo."""
        try:
            from quangstation.dose_calculation.monte_carlo import MonteCarlo
            
            # Lấy thông số
            num_particles = self.options.get('num_particles', 1000000)
            num_threads = self.options.get('num_threads', None)
            
            # Khởi tạo Monte Carlo
            mc = MonteCarlo(num_particles=num_particles, 
                           voxel_size_mm=self.spacing,
                           num_threads=num_threads)
            
            # Thiết lập dữ liệu CT
            mc.set_ct_data(self.image_data)
            
            # Thêm các chùm tia
            for beam in getattr(self, "beams", {}):
                mc.add_beam(beam)
                
            # Thiết lập isocenter
            isocenter = self.beams[0].get('isocenter', None) if self.beams else None
            if isocenter is not None:
                # Chuyển từ tọa độ vật lý (mm) sang chỉ số voxel
                isocenter_idx = [
                    int(isocenter[0] / self.spacing[0]),
                    int(isocenter[1] / self.spacing[1]),
                    int(isocenter[2] / self.spacing[2])
                ]
                mc.set_isocenter(isocenter_idx)
                
            # Tính toán liều
            self.logger.info(f"Bắt đầu tính toán Monte Carlo với {num_particles} hạt")
            dose_matrix, uncertainty = mc.calculate_dose()
            
            self.logger.info(f"Đã hoàn thành tính toán Monte Carlo (độ không chắc chắn: {uncertainty:.2f}%)")
            
            return dose_matrix
            
        except ImportError as e:
            self.logger.warning(f"Không thể tính toán Monte Carlo: {str(error)}")
            # Sử dụng AAA đơn giản thay thế
            self.logger.info("Chuyển sang AAA đơn giản")
            
            dose_matrix = np.zeros_like(self.image_data, dtype=np.float32)
            for i, beam in enumerate(getattr(self, "beams", {})):
                gantry_angle = beam.get('gantry_angle', 0.0)
                energy = beam.get('energy', 6.0)
                weight = beam.get('weight', 1.0)
                isocenter = beam.get('isocenter', None)
                
                # Tính tọa độ isocenter trong chỉ số voxel
                if isocenter is None:
                    isocenter_idx = [d // 2 for d in self.image_data.shape]
                else:
                    isocenter_idx = [
                        int(isocenter[0] / self.spacing[0]),
                        int(isocenter[1] / self.spacing[1]),
                        int(isocenter[2] / self.spacing[2])
                    ]
                    
                # Tính vector hướng chùm tia từ góc quay
                gantry_rad = np.radians(gantry_angle)
                source_direction = [
                    np.sin(gantry_rad),
                    np.cos(gantry_rad),
                    0.0
                ]
                
                self._calculate_simple_aaa(dose_matrix, self.image_data, self.spacing, 
                                         isocenter_idx, source_direction, energy, weight)
                                         
            return dose_matrix
            
        except Exception as error:
            self.logger.error(f"Lỗi khi tính toán Monte Carlo: {str(error)}")
            # Sử dụng AAA đơn giản thay thế
            self.logger.info("Chuyển sang AAA đơn giản")
            
            dose_matrix = np.zeros_like(self.image_data, dtype=np.float32)
            for i, beam in enumerate(getattr(self, "beams", {})):
                gantry_angle = beam.get('gantry_angle', 0.0)
                energy = beam.get('energy', 6.0)
                weight = beam.get('weight', 1.0)
                isocenter = beam.get('isocenter', None)
                
                # Tính tọa độ isocenter trong chỉ số voxel
                if isocenter is None:
                    isocenter_idx = [d // 2 for d in self.image_data.shape]
                else:
                    isocenter_idx = [
                        int(isocenter[0] / self.spacing[0]),
                        int(isocenter[1] / self.spacing[1]),
                        int(isocenter[2] / self.spacing[2])
                    ]
                    
                # Tính vector hướng chùm tia từ góc quay
                gantry_rad = np.radians(gantry_angle)
                source_direction = [
                    np.sin(gantry_rad),
                    np.cos(gantry_rad),
                    0.0
                ]
                
                self._calculate_simple_aaa(dose_matrix, self.image_data, self.spacing, 
                                         isocenter_idx, source_direction, energy, weight)
                                         
            return dose_matrix

    def _calculate_simple_collapsed_cone(self, dose_matrix, image_data, spacing, iso_idx, source_direction, energy, weight, **kwargs):
        """
        Thuật toán Collapsed Cone đơn giản.
        
        Args:
            dose_matrix: Ma trận liều kết quả
            image_data: Dữ liệu hình ảnh CT
            spacing: Khoảng cách giữa các voxel
            iso_idx: Tọa độ tâm xạ trị trong chỉ số voxel
            source_direction: Vector hướng nguồn
            energy: Năng lượng (MV)
            weight: Trọng số
            **kwargs: Các tham số khác
        """
        self.logger.info("Sử dụng thuật toán Collapsed Cone đơn giản")
        
        # Collapsed Cone là một phiên bản nâng cao của AAA
        # Thêm xử lý tính toán tán xạ theo các hướng cone (nón)
        
        # Đầu tiên, tính toán phân bố liều sơ bộ bằng AAA
        self._calculate_simple_aaa(dose_matrix, image_data, spacing, iso_idx, source_direction, energy, weight, **kwargs)
        
        # Số lượng nón trong không gian
        n_cones = 16  # Mặc định
        if 'n_cones' in kwargs:
            n_cones = kwargs['n_cones']
            
        # Hiệu chỉnh liều theo các hướng nón
        # Đây là mô phỏng đơn giản, không phải thuật toán Collapsed Cone đầy đủ
        
        # Chỉ thực hiện hiệu chỉnh cho các vùng có liều
        dose_points = np.where(dose_matrix > 0)
        
        for i in range(len(dose_points[0])):
            x, y, z = dose_points[0][i], dose_points[1][i], dose_points[2][i]
            
            # Hiệu chỉnh liều dựa trên mật độ voxel và khoảng cách tới tâm
            if self.heterogeneity_correction:
                density = self._simple_hu_to_density(image_data[x, y, z])
                r = np.sqrt(((x - iso_idx[0]) * spacing[0])**2 + 
                           ((y - iso_idx[1]) * spacing[1])**2 + 
                           ((z - iso_idx[2]) * spacing[2])**2)
                
                if r > 0:
                    # Hiệu chỉnh liều dựa trên model đơn giản
                    # Trong thuật toán Collapsed Cone thực, đây sẽ là tính toán phức tạp hơn nhiều
                    correction = 1.0 + 0.1 * (density - 1.0) * np.exp(-0.05 * r)
                    dose_matrix[x, y, z] *= correction
        
        self.logger.info("Đã hoàn thành tính toán liều với thuật toán Collapsed Cone đơn giản")
    
    def save_dose_matrix(self, file_path: str):
        """
        Lưu ma trận liều ra file.
        
        Args:
            file_path: Đường dẫn file
        """
        if self.dose_matrix is None:
            raise ValueError("Chưa tính toán liều")
            
        try:
            # Tạo thư mục cha nếu chưa tồn tại
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            
            # Lưu ma trận liều và metadata
            metadata = {
                'algorithm': self.algorithm,
                'resolution_mm': self.resolution_mm,
                'spacing': self.spacing,
                'heterogeneity_correction': self.heterogeneity_correction,
                'options': self.options,
                'shape': self.dose_matrix.shape
            }
            
            # Lưu dữ liệu
            with open(file_path, 'wb') as f:
                np.savez_compressed(
                    f, 
                    dose_matrix=self.dose_matrix,
                    metadata=metadata
                )
                
            self.logger.info(f"Đã lưu ma trận liều vào file {file_path}")
            
            return True
            
        except Exception as error:
            self.logger.error(f"Lỗi khi lưu ma trận liều: {str(error)}")
            return False
            
    def load_dose_matrix(self, file_path: str) -> np.ndarray:
        """
        Tải ma trận liều từ file.
        
        Args:
            file_path: Đường dẫn file
            
        Returns:
            Ma trận liều đã tải
        """
        try:
            # Tải dữ liệu
            with np.load(file_path, allow_pickle=True) as data:
                self.dose_matrix = data['dose_matrix']
                metadata = data.get('metadata', None)
                
                # Kiểm tra và cập nhật metadata
                if metadata is not None:
                    metadata = metadata.item() if hasattr(metadata, 'item') else metadata
                    self.algorithm = metadata.get('algorithm', self.algorithm)
                    self.resolution_mm = metadata.get('resolution_mm', self.resolution_mm)
                    self.spacing = metadata.get('spacing', self.spacing)
                    self.heterogeneity_correction = metadata.get('heterogeneity_correction', self.heterogeneity_correction)
                    self.options = metadata.get('options', self.options)
                
            self.logger.info(f"Đã tải ma trận liều từ file {file_path}")
            
            return self.dose_matrix
            
        except Exception as error:
            self.logger.error(f"Lỗi khi tải ma trận liều: {str(error)}")
            raise

# Tạo instance mặc định
default_calculator = DoseCalculator()
