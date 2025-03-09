#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Wrapper Python cho module tối ưu hóa C++.
"""

import os
import numpy as np
from typing import Dict, List, Tuple, Optional, Any

try:
    from quangstation.optimization._optimizer import GradientOptimizer, GeneticOptimizer
    HAS_CPP_MODULE = True
except ImportError:
    HAS_CPP_MODULE = False
    from quangstation.utils.logging import get_logger
    logger = get_logger("Optimization")
    logger.log_warning("Không thể import module C++ _optimizer. Sử dụng phiên bản Python thuần túy.")

class PlanOptimizer:
    """
    Lớp wrapper cho các thuật toán tối ưu hóa kế hoạch xạ trị.
    Hỗ trợ cả triển khai C++ và Python thuần túy.
    """
    
    ALGO_GRADIENT = "gradient"
    ALGO_GENETIC = "genetic"
    
    def __init__(self, algorithm: str = ALGO_GRADIENT):
        """
        Khởi tạo bộ tối ưu hóa
        
        Args:
            algorithm: Thuật toán tối ưu hóa ('gradient' hoặc 'genetic')
        """
        self.algorithm = algorithm
        self.dose_matrices = []
        self.structures = {}
        self.objectives = []
        self.beam_weights = None
        
        # Tham số cho thuật toán gradient
        self.learning_rate = 0.01
        self.max_iterations = 100
        self.convergence_threshold = 1e-4
        
        # Tham số cho thuật toán di truyền
        self.population_size = 50
        self.max_generations = 100
        self.mutation_rate = 0.1
        self.crossover_rate = 0.8
        
        # Lưu trữ kết quả
        self.optimized_weights = None
        self.objective_values = []
        
        # Nếu có module C++, sử dụng nó
        self._algo = None
    
    def set_dose_matrices(self, dose_matrices: List[np.ndarray]):
        """
        Đặt các ma trận liều cho từng chùm tia
        
        Args:
            dose_matrices: Danh sách các ma trận liều, mỗi ma trận cho một chùm tia
        """
        self.dose_matrices = dose_matrices
    
    def add_structure(self, name: str, mask: np.ndarray):
        """
        Thêm cấu trúc
        
        Args:
            name: Tên cấu trúc
            mask: Ma trận mask của cấu trúc (0 hoặc 1)
        """
        self.structures[name] = mask
    
    def add_objective(self, structure_name: str, objective_type: str, dose: float, 
                     volume: float = None, weight: float = 1.0):
        """
        Thêm mục tiêu tối ưu
        
        Args:
            structure_name: Tên cấu trúc
            objective_type: Loại mục tiêu (MAX_DOSE, MIN_DOSE, MAX_DVH, MIN_DVH, vv)
            dose: Giá trị liều mục tiêu (Gy)
            volume: Phần trăm thể tích (cho mục tiêu DVH)
            weight: Trọng số, càng cao càng quan trọng
        """
        objective = {
            "structure_name": structure_name,
            "type": objective_type,
            "dose": dose,
            "volume": volume,
            "weight": weight
        }
        self.objectives.append(objective)
    
    def set_gradient_parameters(self, learning_rate: float = None, max_iterations: int = None,
                             convergence_threshold: float = None):
        """
        Đặt tham số cho thuật toán gradient
        
        Args:
            learning_rate: Tốc độ học
            max_iterations: Số lần lặp tối đa
            convergence_threshold: Ngưỡng hội tụ
        """
        if learning_rate is not None:
            self.learning_rate = learning_rate
        if max_iterations is not None:
            self.max_iterations = max_iterations
        if convergence_threshold is not None:
            self.convergence_threshold = convergence_threshold
    
    def set_genetic_parameters(self, population_size: int = None, max_generations: int = None,
                            mutation_rate: float = None, crossover_rate: float = None):
        """
        Đặt tham số cho thuật toán di truyền
        
        Args:
            population_size: Kích thước quần thể
            max_generations: Số thế hệ tối đa
            mutation_rate: Tỷ lệ đột biến
            crossover_rate: Tỷ lệ lai ghép
        """
        if population_size is not None:
            self.population_size = population_size
        if max_generations is not None:
            self.max_generations = max_generations
        if mutation_rate is not None:
            self.mutation_rate = mutation_rate
        if crossover_rate is not None:
            self.crossover_rate = crossover_rate
    
    def initialize_optimizer(self):
        """
        Khởi tạo bộ tối ưu hóa dựa trên dữ liệu đã đặt
        """
        if not self.dose_matrices:
            raise ValueError("Chưa đặt ma trận liều")
        
        if not self.structures:
            raise ValueError("Chưa thêm cấu trúc")
        
        if not self.objectives:
            raise ValueError("Chưa thêm mục tiêu tối ưu")
        
        # Nếu có module C++, sử dụng nó
        if HAS_CPP_MODULE:
            # Tạo tổng ma trận liều
            dose_matrix = sum(self.dose_matrices)
            
            if self.algorithm == self.ALGO_GRADIENT:
                self._algo = GradientOptimizer(
                    dose_matrix,
                    self.structures,
                    self.learning_rate,
                    self.max_iterations,
                    self.convergence_threshold
                )
                
                # Thêm mục tiêu
                for objective in self.objectives:
                    self._algo.add_objective(objective)
                
                # Thêm ma trận liều cho từng chùm tia
                for dose_matrix in self.dose_matrices:
                    self._algo.add_beam_dose_matrix(dose_matrix)
                
                # Khởi tạo trọng số chùm tia
                self._algo.initialize_beam_weights()
            
            elif self.algorithm == self.ALGO_GENETIC:
                self._algo = GeneticOptimizer(
                    dose_matrix,
                    self.structures,
                    self.population_size,
                    self.max_generations,
                    self.mutation_rate,
                    self.crossover_rate
                )
                
                # Thêm mục tiêu
                for objective in self.objectives:
                    self._algo.add_objective(objective)
                
                # Thêm ma trận liều cho từng chùm tia
                for dose_matrix in self.dose_matrices:
                    self._algo.add_beam_dose_matrix(dose_matrix)
                
                # Khởi tạo quần thể
                self._algo.initialize_population(len(self.dose_matrices))
            
            else:
                raise ValueError(f"Thuật toán không hợp lệ: {self.algorithm}")
    
    def optimize(self) -> List[float]:
        """
        Thực hiện tối ưu hóa
        
        Returns:
            Danh sách trọng số chùm tia tối ưu
        """
        # Nếu chưa khởi tạo optimizer, khởi tạo nó
        if self._algo is None:
            self.initialize_optimizer()
        
        # Nếu có module C++, sử dụng nó
        if HAS_CPP_MODULE and self._algo:
            self.optimized_weights = self._optimize_cpp()
        else:
            self.optimized_weights = self._optimize_python()
        
        return self.optimized_weights
    
    def _optimize_cpp(self) -> List[float]:
        """
        Tối ưu hóa sử dụng module C++
        
        Returns:
            Danh sách trọng số chùm tia tối ưu
        """
        # Thực hiện tối ưu hóa
        if self.algorithm == self.ALGO_GRADIENT:
            self._algo.optimize()
            # Lấy trọng số tối ưu
            return self._algo.get_optimized_weights()
        elif self.algorithm == self.ALGO_GENETIC:
            return self._algo.optimize()
    
    def _optimize_python(self) -> List[float]:
        """
        Tối ưu hóa sử dụng triển khai Python thuần túy
        
        Returns:
            List[float]: Danh sách trọng số chùm tia tối ưu
        """
        # Đảm bảo logger được import đúng cách
        from quangstation.utils.logging import get_logger
        logger = get_logger("Optimization")
        logger.info("Bắt đầu tối ưu hóa với phiên bản Python thuần túy")
        
        # Khởi tạo hẹn giờ để đo thời gian tối ưu hóa
        import time
        start_time = time.time()
        
        # Khởi tạo trọng số chùm tia ngẫu nhiên
        import random
        import numpy as np
        
        # Khởi tạo trọng số với giá trị nhỏ ngẫu nhiên 
        weights = [random.uniform(0.1, 1.0) for _ in range(len(self.dose_matrices))]
        
        # Chuẩn hóa trọng số
        total = sum(weights)
        weights = [w / total for w in weights]
        
        logger.info(f"Khởi tạo ngẫu nhiên {len(weights)} trọng số chùm tia")
        
        # Tạo ma trận liều tổng
        total_dose = np.zeros_like(self.dose_matrices[0])
        for i, dose_matrix in enumerate(self.dose_matrices):
            total_dose += weights[i] * dose_matrix
        
        # Chuẩn bị các hàm đánh giá mục tiêu
        def calculate_objective(dose_matrix, objective):
            """Tính giá trị mục tiêu từ ma trận liều"""
            structure_name = objective['structure_name']
            obj_type = objective['type']
            target_dose = objective['dose']
            volume = objective.get('volume', None)
            weight = objective.get('weight', 1.0)
            
            # Lấy cấu trúc
            if structure_name not in self.structures:
                logger.warning(f"Cấu trúc {structure_name} không tồn tại")
                return 0.0
            
            structure_mask = self.structures[structure_name]
            
            # Lấy liều trong cấu trúc
            structure_dose = dose_matrix[structure_mask]
            
            if len(structure_dose) == 0:
                logger.warning(f"Cấu trúc {structure_name} không có voxel nào")
                return 0.0
            
            # Tính giá trị mục tiêu
            if obj_type == 'MAX_DOSE':
                # Phạt khi liều tối đa vượt quá giới hạn
                max_dose = np.max(structure_dose)
                if max_dose > target_dose:
                    return weight * ((max_dose - target_dose) / target_dose) ** 2
                return 0.0
                
            elif obj_type == 'MIN_DOSE':
                # Phạt khi liều tối thiểu dưới mức
                min_dose = np.min(structure_dose)
                if min_dose < target_dose:
                    return weight * ((target_dose - min_dose) / target_dose) ** 2
                return 0.0
                
            elif obj_type == 'MEAN_DOSE':
                # Phạt khi liều trung bình khác mục tiêu
                mean_dose = np.mean(structure_dose)
                return weight * ((mean_dose - target_dose) / target_dose) ** 2
                
            elif obj_type == 'MAX_DVH':
                # Phạt khi phần trăm thể tích vượt quá liều
                if volume is None:
                    logger.warning(f"Thiếu thông số volume cho mục tiêu MAX_DVH của {structure_name}")
                    return 0.0
                    
                # Tính phần trăm thể tích vượt quá liều
                vol_over_dose = np.sum(structure_dose > target_dose) / len(structure_dose) * 100
                if vol_over_dose > volume:
                    return weight * ((vol_over_dose - volume) / volume) ** 2
                return 0.0
                
            elif obj_type == 'MIN_DVH':
                # Phạt khi phần trăm thể tích dưới liều
                if volume is None:
                    logger.warning(f"Thiếu thông số volume cho mục tiêu MIN_DVH của {structure_name}")
                    return 0.0
                    
                # Tính phần trăm thể tích dưới liều
                vol_under_dose = np.sum(structure_dose < target_dose) / len(structure_dose) * 100
                if vol_under_dose > (100 - volume):
                    return weight * ((vol_under_dose - (100 - volume)) / (100 - volume)) ** 2
                return 0.0
                
            else:
                logger.warning(f"Loại mục tiêu không hỗ trợ: {obj_type}")
                return 0.0
        
        # Khởi tạo giá trị hàm mục tiêu
        self.objective_values = []
        
        # Hàm tính tổng giá trị mục tiêu
        def calculate_total_objective(w):
            # Tính ma trận liều tổng với trọng số mới
            dose = np.zeros_like(self.dose_matrices[0])
            for i, dose_matrix in enumerate(self.dose_matrices):
                dose += w[i] * dose_matrix
                
            # Tính tổng các giá trị mục tiêu
            total = 0.0
            for objective in self.objectives:
                total += calculate_objective(dose, objective)
                
            return total
        
        # Tính giá trị hàm mục tiêu ban đầu
        current_objective = calculate_total_objective(weights)
        self.objective_values.append(current_objective)
        
        logger.info(f"Giá trị hàm mục tiêu ban đầu: {current_objective:.6f}")
        
        # Tối ưu bằng thuật toán Gradient Descent đơn giản
        for iteration in range(self.max_iterations):
            # Tính gradient
            gradients = []
            for i in range(len(weights)):
                # Tính đạo hàm riêng theo trọng số i bằng phương pháp sai phân
                delta = 0.001  # Bước nhỏ để tính đạo hàm
                w_plus = weights.copy()
                w_plus[i] += delta
                
                # Chuẩn hóa lại
                w_plus_sum = sum(w_plus)
                w_plus = [w / w_plus_sum for w in w_plus]
                
                # Tính giá trị hàm mục tiêu với trọng số mới
                obj_plus = calculate_total_objective(w_plus)
                
                # Tính gradient
                gradient = (obj_plus - current_objective) / delta
                gradients.append(gradient)
            
            # Cập nhật trọng số theo gradient
            new_weights = []
            for i, w in enumerate(weights):
                # Cập nhật theo hướng giảm gradient
                new_w = w - self.learning_rate * gradients[i]
                # Đảm bảo trọng số không âm
                new_weights.append(max(0.0, new_w))
            
            # Chuẩn hóa trọng số mới
            total = sum(new_weights)
            if total > 0:
                new_weights = [w / total for w in new_weights]
            else:
                # Nếu tất cả trọng số đều 0, khởi tạo lại
                new_weights = [1.0 / len(weights) for _ in range(len(weights))]
            
            # Tính giá trị hàm mục tiêu mới
            new_objective = calculate_total_objective(new_weights)
            self.objective_values.append(new_objective)
            
            # Kiểm tra hội tụ
            if abs(new_objective - current_objective) < self.convergence_threshold:
                logger.info(f"Đã hội tụ sau {iteration + 1} vòng lặp: {new_objective:.6f}")
                break
                
            # Cập nhật trọng số và giá trị mục tiêu
            weights = new_weights
            current_objective = new_objective
            
            # Ghi log tiến độ
            if (iteration + 1) % 10 == 0 or iteration == 0:
                logger.info(f"Vòng lặp {iteration + 1}/{self.max_iterations}: {current_objective:.6f}")
        
        # Kết thúc và ghi log kết quả
        elapsed_time = time.time() - start_time
        logger.info(f"Hoàn thành tối ưu hóa sau {elapsed_time:.2f} giây")
        logger.info(f"Giá trị hàm mục tiêu cuối: {current_objective:.6f}")
        logger.info(f"Trọng số cuối: {weights}")
        
        return weights
    
    def get_objective_values(self) -> List[float]:
        """
        Lấy các giá trị hàm mục tiêu trong quá trình tối ưu
        
        Returns:
            Danh sách giá trị hàm mục tiêu
        """
        return self.objective_values
    
    def get_optimized_dose(self) -> np.ndarray:
        """
        Tính toán ma trận liều tối ưu dựa trên trọng số tối ưu
        
        Returns:
            Ma trận liều tối ưu
        """
        if self.optimized_weights is None:
            raise ValueError("Chưa thực hiện tối ưu hóa")
        
        # Tính tổng có trọng số
        optimized_dose = np.zeros_like(self.dose_matrices[0])
        
        for i, dose_matrix in enumerate(self.dose_matrices):
            optimized_dose += self.optimized_weights[i] * dose_matrix
        
        return optimized_dose
    
    def save_results(self, file_path: str):
        """
        Lưu kết quả tối ưu vào file
        
        Args:
            file_path: Đường dẫn file
        """
        if self.optimized_weights is None:
            raise ValueError("Chưa thực hiện tối ưu hóa")
        
        import json
        import os
        import datetime
        
        # Đảm bảo thư mục tồn tại
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        # Chuyển đổi các mảng numpy thành list để có thể lưu dưới dạng JSON
        results = {
            "algorithm": self.algorithm,
            "optimized_weights": self.optimized_weights,
            "objective_values": self.objective_values,
            "objectives": self.objectives,
            "parameters": {
                "learning_rate": self.learning_rate,
                "max_iterations": self.max_iterations,
                "convergence_threshold": self.convergence_threshold,
                "population_size": self.population_size,
                "max_generations": self.max_generations,
                "mutation_rate": self.mutation_rate,
                "crossover_rate": self.crossover_rate
            },
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Lưu vào file JSON
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=4)
    
    def load_results(self, file_path: str):
        """
        Tải kết quả tối ưu từ file
        
        Args:
            file_path: Đường dẫn file
            
        Returns:
            True nếu tải thành công, False nếu không
        """
        import json
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            # Cập nhật các tham số
            self.algorithm = results.get("algorithm", self.ALGO_GRADIENT)
            self.optimized_weights = results.get("optimized_weights", None)
            self.objective_values = results.get("objective_values", [])
            self.objectives = results.get("objectives", [])
            
            params = results.get("parameters", {})
            self.learning_rate = params.get("learning_rate", self.learning_rate)
            self.max_iterations = params.get("max_iterations", self.max_iterations)
            self.convergence_threshold = params.get("convergence_threshold", self.convergence_threshold)
            self.population_size = params.get("population_size", self.population_size)
            self.max_generations = params.get("max_generations", self.max_generations)
            self.mutation_rate = params.get("mutation_rate", self.mutation_rate)
            self.crossover_rate = params.get("crossover_rate", self.crossover_rate)
            
            return True
        except Exception as error:
            from quangstation.utils.logging import get_logger
            logger = get_logger("Optimization")
            logger.log_error(f"Lỗi khi tải kết quả tối ưu: {str(error)}")
            return False

# Tạo instance mặc định
default_optimizer = PlanOptimizer()
