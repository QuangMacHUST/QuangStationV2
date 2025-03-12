#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module tối ưu hóa kế hoạch xạ trị cho hệ thống QuangStation V2.
Cung cấp giao diện cao cấp cho việc tối ưu hóa kế hoạch xạ trị,
tích hợp với các thuật toán tối ưu hóa C++ và Python.
"""

import os
import numpy as np
import time
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
import json

from quangstation.core.utils.logging import get_logger
from quangstation.core.utils.config import get_config
from quangstation.clinical.data_management.patient_db import PatientDatabase
from quangstation.clinical.optimization.optimizer_wrapper import PlanOptimizer as OptimizerWrapper
from quangstation.clinical.optimization.goal_optimizer import OptimizationGoal

logger = get_logger(__name__)

class PlanOptimizer:
    """
    Lớp tối ưu hóa kế hoạch xạ trị cung cấp giao diện cao cấp
    cho việc tối ưu hóa kế hoạch xạ trị trong QuangStation V2.
    """
    
    # Các loại mục tiêu tối ưu hóa
    OBJECTIVE_TYPES = {
        "Liều tối đa": "MAX_DOSE",
        "Liều tối thiểu": "MIN_DOSE",
        "Liều trung bình": "MEAN_DOSE",
        "Liều tối đa cho x% thể tích": "MAX_DVH",
        "Liều tối thiểu cho x% thể tích": "MIN_DVH",
        "Độ tương thích": "CONFORMITY",
        "Độ đồng nhất": "HOMOGENEITY",
        "Độ đều": "UNIFORMITY"
    }
    
    # Các thuật toán tối ưu hóa
    ALGORITHMS = {
        "IPOPT": "ipopt",
        "Gradient Descent": "gradient",
        "L-BFGS": "lbfgs",
        "Simulated Annealing": "annealing",
        "Genetic Algorithm": "genetic"
    }
    
    def __init__(self):
        """Khởi tạo đối tượng tối ưu hóa kế hoạch"""
        self.logger = get_logger("PlanOptimizer")
        self.db = PatientDatabase()
        self.objectives = []
        self.settings = {
            "algorithm": "gradient",
            "max_iterations": 100,
            "tolerance": 0.001,
            "max_time": 30  # phút
        }
        self.optimizer = None
        self.patient_id = None
        self.plan_id = None
        self.dose_data = None
        self.structure_data = None
        
    def set_settings(self, settings: Dict[str, Any]) -> None:
        """
        Thiết lập các thông số tối ưu hóa
        
        Args:
            settings: Dictionary chứa các thông số tối ưu hóa
        """
        if not settings:
            return
            
        # Cập nhật các thông số
        if "algorithm" in settings:
            algo_name = settings["algorithm"]
            self.settings["algorithm"] = self.ALGORITHMS.get(algo_name, "gradient")
            
        if "max_iterations" in settings:
            self.settings["max_iterations"] = int(settings["max_iterations"])
            
        if "tolerance" in settings:
            self.settings["tolerance"] = float(settings["tolerance"])
            
        if "max_time" in settings:
            self.settings["max_time"] = int(settings["max_time"])
            
        self.logger.info(f"Đã thiết lập thông số tối ưu hóa: {self.settings}")
        
    def add_objective(self, structure_name: str, objective_type: str, 
                     value: float, weight: float = 1.0) -> None:
        """
        Thêm mục tiêu tối ưu hóa
        
        Args:
            structure_name: Tên cấu trúc
            objective_type: Loại mục tiêu (từ OBJECTIVE_TYPES)
            value: Giá trị mục tiêu (liều hoặc phần trăm)
            weight: Trọng số của mục tiêu
        """
        # Chuyển đổi loại mục tiêu từ giao diện sang mã nội bộ
        internal_type = self.OBJECTIVE_TYPES.get(objective_type, objective_type)
        
        # Xử lý các loại mục tiêu đặc biệt
        volume_percent = None
        if "DVH" in internal_type:
            # Tách giá trị liều và phần trăm thể tích từ chuỗi
            parts = str(value).split("/")
            if len(parts) == 2:
                dose_value = float(parts[0])
                volume_percent = float(parts[1])
            else:
                dose_value = float(value)
                volume_percent = 50.0  # Giá trị mặc định
        else:
            dose_value = float(value)
        
        # Tạo đối tượng mục tiêu
        objective = {
            "structure": structure_name,
            "type": internal_type,
            "dose": dose_value,
            "volume_percent": volume_percent,
            "weight": float(weight)
        }
        
        self.objectives.append(objective)
        self.logger.info(f"Đã thêm mục tiêu: {objective}")
        
    def optimize(self, patient_id: str, plan_id: str, 
                dose_data: Dict[str, Any], structure_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Thực hiện tối ưu hóa kế hoạch xạ trị
        
        Args:
            patient_id: ID của bệnh nhân
            plan_id: ID của kế hoạch
            dose_data: Dữ liệu liều
            structure_data: Dữ liệu cấu trúc
            
        Returns:
            Dictionary chứa kết quả tối ưu hóa
        """
        start_time = time.time()
        self.patient_id = patient_id
        self.plan_id = plan_id
        self.dose_data = dose_data
        self.structure_data = structure_data
        
        result = {
            "success": False,
            "message": "",
            "iterations": 0,
            "runtime": 0,
            "initial_objective": 0,
            "final_objective": 0
        }
        
        try:
            # Kiểm tra dữ liệu đầu vào
            if not self.objectives:
                result["message"] = "Không có mục tiêu tối ưu hóa"
                return result
                
            if not dose_data or not structure_data:
                result["message"] = "Dữ liệu liều hoặc cấu trúc không hợp lệ"
                return result
                
            # Khởi tạo bộ tối ưu hóa
            self.optimizer = OptimizerWrapper(algorithm=self.settings["algorithm"])
            
            # Thiết lập thông số
            if self.settings["algorithm"] == "gradient":
                self.optimizer.set_gradient_parameters(
                    learning_rate=0.01,
                    max_iterations=self.settings["max_iterations"],
                    convergence_threshold=self.settings["tolerance"]
                )
            elif self.settings["algorithm"] == "genetic":
                self.optimizer.set_genetic_parameters(
                    population_size=50,
                    max_generations=self.settings["max_iterations"],
                    mutation_rate=0.1,
                    crossover_rate=0.8
                )
            
            # Chuyển đổi dữ liệu liều và cấu trúc
            dose_matrix = self._convert_dose_data(dose_data)
            structure_masks = self._convert_structure_data(structure_data)
            
            # Thiết lập dữ liệu cho bộ tối ưu hóa
            self.optimizer.set_dose_matrices([dose_matrix])
            
            # Thêm cấu trúc
            for name, mask in structure_masks.items():
                self.optimizer.add_structure(name, mask)
            
            # Thêm mục tiêu
            for obj in self.objectives:
                self.optimizer.add_objective(
                    structure_name=obj["structure"],
                    objective_type=obj["type"],
                    dose=obj["dose"],
                    volume=obj.get("volume_percent"),
                    weight=obj["weight"]
                )
            
            # Khởi tạo bộ tối ưu hóa
            self.optimizer.initialize_optimizer()
            
            # Lấy giá trị mục tiêu ban đầu
            initial_objective = self.optimizer.get_objective_values()
            result["initial_objective"] = sum(initial_objective)
            
            # Thực hiện tối ưu hóa
            self.logger.info(f"Bắt đầu tối ưu hóa kế hoạch {plan_id} với thuật toán {self.settings['algorithm']}")
            
            # Thiết lập thời gian tối đa
            max_time_seconds = self.settings["max_time"] * 60
            
            # Thực hiện tối ưu hóa với giới hạn thời gian
            start_optimize_time = time.time()
            weights = self.optimizer.optimize()
            
            # Kiểm tra kết quả
            if weights is not None:
                # Lấy giá trị mục tiêu sau tối ưu
                final_objective = self.optimizer.get_objective_values()
                result["final_objective"] = sum(final_objective)
                
                # Lấy ma trận liều tối ưu
                optimized_dose = self.optimizer.get_optimized_dose()
                
                # Lưu kết quả
                self._save_optimization_result(weights, optimized_dose)
                
                # Cập nhật kết quả
                result["success"] = True
                result["iterations"] = self.optimizer.max_iterations
                result["weights"] = weights.tolist() if isinstance(weights, np.ndarray) else weights
                
                self.logger.info(f"Tối ưu hóa thành công: Giá trị mục tiêu từ {result['initial_objective']} xuống {result['final_objective']}")
            else:
                result["message"] = "Tối ưu hóa không hội tụ"
                
        except Exception as e:
            self.logger.error(f"Lỗi khi tối ưu hóa kế hoạch: {str(e)}")
            result["message"] = str(e)
            
        # Cập nhật thời gian chạy
        result["runtime"] = time.time() - start_time
        
        return result
    
    def _convert_dose_data(self, dose_data: Dict[str, Any]) -> np.ndarray:
        """
        Chuyển đổi dữ liệu liều từ định dạng lưu trữ sang ma trận numpy
        
        Args:
            dose_data: Dữ liệu liều từ hệ thống lưu trữ
            
        Returns:
            Ma trận liều 3D
        """
        try:
            # Lấy ma trận liều từ dữ liệu
            if "dose_matrix" in dose_data:
                return np.array(dose_data["dose_matrix"])
            elif "dose_grid" in dose_data:
                return np.array(dose_data["dose_grid"])
            else:
                raise ValueError("Không tìm thấy ma trận liều trong dữ liệu")
        except Exception as e:
            self.logger.error(f"Lỗi khi chuyển đổi dữ liệu liều: {str(e)}")
            raise
    
    def _convert_structure_data(self, structure_data: Dict[str, Any]) -> Dict[str, np.ndarray]:
        """
        Chuyển đổi dữ liệu cấu trúc từ định dạng lưu trữ sang ma trận numpy
        
        Args:
            structure_data: Dữ liệu cấu trúc từ hệ thống lưu trữ
            
        Returns:
            Dictionary chứa tên cấu trúc và ma trận mặt nạ tương ứng
        """
        try:
            structure_masks = {}
            
            # Lấy danh sách cấu trúc
            structures = structure_data.get("structures", {})
            
            for name, struct in structures.items():
                # Lấy ma trận mặt nạ
                if "mask" in struct:
                    structure_masks[name] = np.array(struct["mask"])
                elif "contour_data" in struct:
                    # Chuyển đổi dữ liệu contour thành mặt nạ
                    # Đây là phần phức tạp, có thể cần triển khai riêng
                    self.logger.warning(f"Chưa hỗ trợ chuyển đổi contour_data cho cấu trúc {name}")
                    continue
                else:
                    self.logger.warning(f"Không tìm thấy dữ liệu mặt nạ cho cấu trúc {name}")
            
            return structure_masks
            
        except Exception as e:
            self.logger.error(f"Lỗi khi chuyển đổi dữ liệu cấu trúc: {str(e)}")
            raise
    
    def _save_optimization_result(self, weights: List[float], optimized_dose: np.ndarray) -> None:
        """
        Lưu kết quả tối ưu hóa vào cơ sở dữ liệu
        
        Args:
            weights: Trọng số tối ưu
            optimized_dose: Ma trận liều tối ưu
        """
        try:
            # Tạo đối tượng kết quả
            result = {
                "weights": weights,
                "objectives": self.objectives,
                "settings": self.settings,
                "timestamp": time.time()
            }
            
            # Lưu kết quả vào cơ sở dữ liệu
            self.db.save_optimization_result(
                patient_id=self.patient_id,
                plan_id=self.plan_id,
                result=result
            )
            
            # Cập nhật ma trận liều tối ưu
            self.db.update_dose_matrix(
                patient_id=self.patient_id,
                plan_id=self.plan_id,
                dose_matrix=optimized_dose.tolist()
            )
            
            self.logger.info(f"Đã lưu kết quả tối ưu hóa cho kế hoạch {self.plan_id}")
            
        except Exception as e:
            self.logger.error(f"Lỗi khi lưu kết quả tối ưu hóa: {str(e)}")
            raise 