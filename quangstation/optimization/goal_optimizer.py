#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module toi uu hoa dua tren muc tieu (goal-based optimization) cho QuangStation V2.
Module nay cung cap cac phuong phap toi uu hoa ke hoach xa tri tien tien dua tren
cac rang buoc muc tieu (goals) va trong so uu tien.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union, Callable
import time
import logging
from scipy.optimize import minimize, differential_evolution, basinhopping

from quangstation.utils.logging import get_logger

logger = get_logger(__name__)

class OptimizationGoal:
    """
    Lop dai dien cho mot muc tieu toi uu hoa.
    Moi muc tieu bao gom: co cau dich, loai rang buoc, gia tri muc tieu, trong so
    """
    
    # Cac loai muc tieu
    TYPE_MIN_DOSE = "min_dose"       # Lieu toi thieu
    TYPE_MAX_DOSE = "max_dose"       # Lieu toi da
    TYPE_MEAN_DOSE = "mean_dose"     # Lieu trung binh
    TYPE_MIN_DVH = "min_dvh"         # Rang buoc DVH toi thieu (DMIN cho X% the tich)
    TYPE_MAX_DVH = "max_dvh"         # Rang buoc DVH toi da (DMAX cho X% the tich)
    TYPE_UNIFORM_DOSE = "uniform"    # Lieu dong deu
    TYPE_CONFORMITY = "conformity"   # Do tuan thu
    TYPE_DOSE_FALL_OFF = "falloff"   # Do doc dang lieu
    
    def __init__(self, structure_name: str, goal_type: str, dose_value: float, 
                 volume_value: float = None, weight: float = 1.0, 
                 priority: int = 1, is_required: bool = False):
        """
        Khoi tao muc tieu toi uu hoa
        
        Args:
            structure_name: Ten cau truc
            goal_type: Loai muc tieu (xem cac hang so TYPE_*)
            dose_value: Gia tri lieu muc tieu (Gy)
            volume_value: Gia tri the tich cho rang buoc DVH (%)
            weight: Trong so cua muc tieu (mac dinh: 1.0)
            priority: Uu tien cua muc tieu (1: cao nhat, 2, 3, ...)
            is_required: Co bat buoc dap ung muc tieu nay khong
        """
        self.structure_name = structure_name
        self.goal_type = goal_type
        self.dose_value = dose_value
        self.volume_value = volume_value
        self.weight = weight
        self.priority = priority
        self.is_required = is_required
        
        # Xac thuc du lieu
        self._validate_input()
        
    def _validate_input(self):
        """Kiem tra tinh hop le cua cac tham so dau vao"""
        # Kiem tra goal_type
        valid_types = [self.TYPE_MIN_DOSE, self.TYPE_MAX_DOSE, self.TYPE_MEAN_DOSE,
                       self.TYPE_MIN_DVH, self.TYPE_MAX_DVH, self.TYPE_UNIFORM_DOSE,
                       self.TYPE_CONFORMITY, self.TYPE_DOSE_FALL_OFF]
        
        if self.goal_type not in valid_types:
            raise ValueError(f"Loai muc tieu khong hop le: {self.goal_type}")
        
        # Kiem tra gia tri volume cho cac rang buoc DVH
        if self.goal_type in [self.TYPE_MIN_DVH, self.TYPE_MAX_DVH] and self.volume_value is None:
            raise ValueError(f"Muc tieu {self.goal_type} can gia tri the tich (volume_value)")
            
        # Kiem tra trong so va uu tien
        if self.weight <= 0:
            raise ValueError(f"Trong so phai duong: {self.weight}")
        
        if self.priority <= 0:
            raise ValueError(f"Uu tien phai > 0: {self.priority}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Chuyen doi goal thanh tu dien"""
        return {
            "structure_name": self.structure_name,
            "goal_type": self.goal_type,
            "dose_value": self.dose_value,
            "volume_value": self.volume_value,
            "weight": self.weight,
            "priority": self.priority,
            "is_required": self.is_required
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OptimizationGoal':
        """Tao goal tu tu dien"""
        return cls(
            structure_name=data["structure_name"],
            goal_type=data["goal_type"],
            dose_value=data["dose_value"],
            volume_value=data.get("volume_value"),
            weight=data.get("weight", 1.0),
            priority=data.get("priority", 1),
            is_required=data.get("is_required", False)
        )
    
    def __str__(self) -> str:
        """Bieu dien goal duoi dang chuoi"""
        if self.goal_type == self.TYPE_MIN_DOSE:
            return f"{self.structure_name}: Lieu toi thieu >= {self.dose_value} Gy (w={self.weight})"
        elif self.goal_type == self.TYPE_MAX_DOSE:
            return f"{self.structure_name}: Lieu toi da <= {self.dose_value} Gy (w={self.weight})"
        elif self.goal_type == self.TYPE_MEAN_DOSE:
            return f"{self.structure_name}: Lieu trung binh <= {self.dose_value} Gy (w={self.weight})"
        elif self.goal_type == self.TYPE_MIN_DVH:
            return f"{self.structure_name}: D{self.volume_value}% >= {self.dose_value} Gy (w={self.weight})"
        elif self.goal_type == self.TYPE_MAX_DVH:
            return f"{self.structure_name}: D{self.volume_value}% <= {self.dose_value} Gy (w={self.weight})"
        elif self.goal_type == self.TYPE_UNIFORM_DOSE:
            return f"{self.structure_name}: Lieu dong deu = {self.dose_value} Gy (w={self.weight})"
        elif self.goal_type == self.TYPE_CONFORMITY:
            return f"{self.structure_name}: Do tuan thu >= {self.dose_value} (w={self.weight})"
        elif self.goal_type == self.TYPE_DOSE_FALL_OFF:
            return f"{self.structure_name}: Do doc {self.dose_value} Gy/cm (w={self.weight})"
        else:
            return f"{self.structure_name}: {self.goal_type} = {self.dose_value} (w={self.weight})"


class GoalBasedOptimizer:
    """
    Lop toi uu hoa ke hoach xa tri dua tren danh sach cac muc tieu (goals).
    """
    
    # Cac thuat toan ho tro
    ALGO_GRADIENT_DESCENT = "gradient_descent"
    ALGO_EVOLUTIONARY = "evolutionary"
    ALGO_BASIN_HOPPING = "basin_hopping"
    ALGO_HIERARCHICAL = "hierarchical"
    
    def __init__(self, algorithm: str = ALGO_GRADIENT_DESCENT):
        """
        Khoi tao bo toi uu hoa dua tren muc tieu
        
        Args:
            algorithm: Thuat toan su dung (xem cac hang so ALGO_*)
        """
        self.algorithm = algorithm
        self.goals = []  # Danh sach cac muc tieu
        self.structures = {}  # Dict cua cac cau truc
        self.beam_dose_contributions = []  # Dong gop lieu cua tung chum tia
        self.beam_weights = []  # Trong so chum tia hien tai
        self.dose_matrix = None  # Ma tran lieu (precomputed)
        self.voxel_sizes = None  # Kich thuoc cac voxel
        
        # Tham so toi uu
        self.max_iterations = 100
        self.tolerance = 1e-4
        self.learning_rate = 0.1
        self.population_size = 50  # Cho evolutionary
        self.mutation_rate = 0.2   # Cho evolutionary
        self.stopping_criteria = None  # Ham dieu kien dung
        
        # Ket qua
        self.optimized_weights = None
        self.objective_values = []
        self.convergence_history = []
        self.optimization_time = 0
        
        logger.info(f"Khoi tao bo toi uu hoa dua tren muc tieu voi thuat toan {algorithm}")
    
    def add_goal(self, goal: OptimizationGoal):
        """Them mot muc tieu toi uu hoa"""
        self.goals.append(goal)
        logger.info(f"Da them muc tieu: {goal}")
    
    def add_structure(self, name: str, mask: np.ndarray):
        """Them mot cau truc vao toi uu hoa"""
        self.structures[name] = mask
        logger.info(f"Da them cau truc {name} voi {np.sum(mask)} voxel")
    
    def set_beam_dose_contributions(self, beam_doses: List[np.ndarray]):
        """
        Thiet lap ma tran dong gop lieu cua tung chum tia
        
        Args:
            beam_doses: Danh sach ma tran lieu cho moi chum tia [beam1_dose, beam2_dose, ...]
                      Moi ma tran co cung kich thuoc voi du lieu hinh anh
        """
        self.beam_dose_contributions = beam_doses
        self.beam_weights = [1.0] * len(beam_doses)  # Khoi tao trong so bang nhau
        
        # Tao ma tran lieu ban dau
        self.dose_matrix = np.zeros_like(beam_doses[0])
        for i, beam_dose in enumerate(beam_doses):
            self.dose_matrix += beam_dose * self.beam_weights[i]
        
        logger.info(f"Da thiet lap {len(beam_doses)} ma tran dong gop lieu chum tia")
    
    def set_voxel_sizes(self, voxel_sizes: Tuple[float, float, float]):
        """Thiet lap kich thuoc voxel (mm)"""
        self.voxel_sizes = voxel_sizes
    
    def set_optimization_parameters(self, max_iterations: int = None, tolerance: float = None,
                                   learning_rate: float = None, population_size: int = None,
                                   mutation_rate: float = None):
        """Thiet lap cac tham so toi uu hoa"""
        if max_iterations is not None:
            self.max_iterations = max_iterations
        
        if tolerance is not None:
            self.tolerance = tolerance
        
        if learning_rate is not None:
            self.learning_rate = learning_rate
        
        if population_size is not None:
            self.population_size = population_size
        
        if mutation_rate is not None:
            self.mutation_rate = mutation_rate
        
        logger.info(f"Da cap nhat tham so toi uu hoa: "
                  f"max_iterations={self.max_iterations}, "
                  f"tolerance={self.tolerance}, "
                  f"learning_rate={self.learning_rate}")
    
    def set_stopping_criteria(self, criteria_func: Callable[[List[float], int], bool]):
        """
        Thiet lap ham kiem tra dieu kien dung
        
        Args:
            criteria_func: Ham nhan objective_values va iter_num, tra ve True neu nen dung
        """
        self.stopping_criteria = criteria_func
    
    def _calculate_objective_value(self, weights: np.ndarray = None) -> float:
        """
        Tinh gia tri ham muc tieu dua tren trong so chum tia
        
        Args:
            weights: Trong so chum tia (neu None, su dung self.beam_weights)
            
        Returns:
            Gia tri ham muc tieu (nho hon = tot hon)
        """
        if weights is None:
            weights = self.beam_weights
        
        # Tinh toan ma tran lieu voi trong so hien tai
        dose_matrix = np.zeros_like(self.beam_dose_contributions[0])
        for i, beam_dose in enumerate(self.beam_dose_contributions):
            dose_matrix += beam_dose * weights[i]
        
        # Gom nhom cac muc tieu theo uu tien
        priority_groups = {}
        for goal in self.goals:
            if goal.priority not in priority_groups:
                priority_groups[goal.priority] = []
            priority_groups[goal.priority].append(goal)
        
        # Tinh toan gia tri ham muc tieu cho tung nhom uu tien
        total_objective = 0.0
        priority_values = {}
        
        # Xu ly theo thu tu uu tien (tang dan)
        for priority in sorted(priority_groups.keys()):
            priority_objective = 0.0
            
            for goal in priority_groups[priority]:
                goal_value = self._evaluate_goal(goal, dose_matrix)
                priority_objective += goal_value * goal.weight
            
            # Luu gia tri muc tieu cho nhom uu tien nay
            priority_values[priority] = priority_objective
            
            # Nhan he so rat lon cho uu tien cao hon
            # (dam bao uu tien cao hon luon quan trong hon)
            scaling_factor = 10.0 ** (6 - priority)  # uu tien 1 se lon hon nhieu
            total_objective += priority_objective * scaling_factor
        
        return total_objective
    
    def _evaluate_goal(self, goal: OptimizationGoal, dose_matrix: np.ndarray) -> float:
        """
        Danh gia gia tri mot muc tieu cu the voi ma tran lieu cho truoc
        
        Args:
            goal: Muc tieu can danh gia
            dose_matrix: Ma tran lieu hien tai
            
        Returns:
            Gia tri muc tieu (nho hon = tot hon, 0 = hoan hao)
        """
        # Kiem tra xem cau truc co ton tai khong
        if goal.structure_name not in self.structures:
            logger.warning(f"Cau truc {goal.structure_name} khong co trong du lieu")
            return 0.0
        
        # Lay mat na cua cau truc
        structure_mask = self.structures[goal.structure_name]
        
        # Tinh lieu trong cau truc
        structure_dose = dose_matrix * structure_mask
        dose_in_structure = structure_dose[structure_mask > 0]
        
        if len(dose_in_structure) == 0:
            logger.warning(f"Khong co voxel nao trong cau truc {goal.structure_name}")
            return 0.0
        
        # Tinh toan gia tri muc tieu dua tren loai muc tieu
        if goal.goal_type == OptimizationGoal.TYPE_MIN_DOSE:
            # Lieu toi thieu: penalty neu lieu < gia tri muc tieu
            min_dose = np.min(dose_in_structure)
            return max(0, goal.dose_value - min_dose) ** 2
        
        elif goal.goal_type == OptimizationGoal.TYPE_MAX_DOSE:
            # Lieu toi da: penalty neu lieu > gia tri muc tieu
            max_dose = np.max(dose_in_structure)
            return max(0, max_dose - goal.dose_value) ** 2
        
        elif goal.goal_type == OptimizationGoal.TYPE_MEAN_DOSE:
            # Lieu trung binh: penalty neu lieu trung binh > gia tri muc tieu
            mean_dose = np.mean(dose_in_structure)
            return max(0, mean_dose - goal.dose_value) ** 2
        
        elif goal.goal_type == OptimizationGoal.TYPE_MIN_DVH:
            # DVH toi thieu: D_x% >= dose_value
            sorted_dose = np.sort(dose_in_structure)
            index = int(len(sorted_dose) * (1 - goal.volume_value / 100))
            actual_dose = sorted_dose[min(index, len(sorted_dose) - 1)]
            return max(0, goal.dose_value - actual_dose) ** 2
        
        elif goal.goal_type == OptimizationGoal.TYPE_MAX_DVH:
            # DVH toi da: D_x% <= dose_value
            sorted_dose = np.sort(dose_in_structure)
            index = int(len(sorted_dose) * (1 - goal.volume_value / 100))
            actual_dose = sorted_dose[min(index, len(sorted_dose) - 1)]
            return max(0, actual_dose - goal.dose_value) ** 2
        
        elif goal.goal_type == OptimizationGoal.TYPE_UNIFORM_DOSE:
            # Lieu dong deu: minimize standard deviation
            std_dev = np.std(dose_in_structure)
            return std_dev ** 2
        
        elif goal.goal_type == OptimizationGoal.TYPE_CONFORMITY:
            # Do tuan thu: minimize (V95% - PTV) where V95% is volume receiving 95% of prescription
            if goal.volume_value is None:
                ref_dose = 0.95 * goal.dose_value  # Mac dinh: 95% lieu ke toa
            else:
                ref_dose = (goal.volume_value / 100) * goal.dose_value
                
            # Tinh thể tich nhan it nhat ref_dose
            dose_95_mask = dose_matrix >= ref_dose
            dose_95_volume = np.sum(dose_95_mask)
            
            # Tinh the tich PTV
            ptv_volume = np.sum(structure_mask)
            
            # Tinh so luong voxel trong V95 nhung khong nam trong PTV
            outside_ptv = np.logical_and(dose_95_mask, np.logical_not(structure_mask))
            outside_volume = np.sum(outside_ptv)
            
            # V95 phai bao phu PTV va khong qua lon
            ci_penalty = ((dose_95_volume - ptv_volume) / ptv_volume) ** 2
            
            return ci_penalty
        
        elif goal.goal_type == OptimizationGoal.TYPE_DOSE_FALL_OFF:
            # Do doc cua lieu: gradient
            if self.voxel_sizes is None:
                logger.warning("Khong co thong tin kich thuoc voxel cho tinh toan do doc lieu")
                return 0.0
            
            # Tinh do doc trung binh tai bien cua cau truc
            # TODO: Implement dose falloff calculation
            
            return 0.0
        
        return 0.0
    
    def _objective_function(self, weights: np.ndarray) -> float:
        """
        Ham muc tieu cho bo toi uu (interface cho scipy.optimize)
        
        Args:
            weights: Trong so chum tia
            
        Returns:
            Gia tri ham muc tieu
        """
        # Gioi han trong so trong pham vi [0, inf)
        weights = np.maximum(weights, 0)
        
        # Chuan hoa trong so de tong bang 1, neu co it nhat 1 trong so > 0
        if np.sum(weights) > 0:
            weights = weights / np.sum(weights)
        
        return self._calculate_objective_value(weights)
    
    def _gradient_function(self, weights: np.ndarray) -> np.ndarray:
        """
        Tinh gradient cua ham muc tieu (cho gradient descent)
        
        Args:
            weights: Trong so chum tia hien tai
            
        Returns:
            Gradient (vector dao ham theo moi trong so)
        """
        # Su dung phuong phap chenh lech huu han de tinh gradient
        gradient = np.zeros_like(weights)
        h = 1e-6  # Buoc nho
        
        # Tinh gia tri ham muc tieu tai diem hien tai
        f0 = self._objective_function(weights)
        
        # Tinh dao ham doi voi tung trong so
        for i in range(len(weights)):
            weights_h = weights.copy()
            weights_h[i] += h
            f1 = self._objective_function(weights_h)
            gradient[i] = (f1 - f0) / h
        
        return gradient
    
    def _optimize_gradient_descent(self) -> Tuple[np.ndarray, List[float]]:
        """
        Toi uu hoa bang thuat toan gradient descent
        
        Returns:
            (optimized_weights, convergence_history)
        """
        weights = np.array(self.beam_weights)
        history = []
        
        for iteration in range(self.max_iterations):
            # Tinh gia tri ham muc tieu
            objective = self._objective_function(weights)
            history.append(objective)
            
            # Kiem tra dieu kien dung
            if iteration > 0 and abs(history[-1] - history[-2]) < self.tolerance:
                logger.info(f"Da hoi tu sau {iteration} vong lap")
                break
                
            if self.stopping_criteria and self.stopping_criteria(history, iteration):
                logger.info(f"Da dung theo dieu kien tai vong lap {iteration}")
                break
            
            # Tinh gradient
            gradient = self._gradient_function(weights)
            
            # Cap nhat trong so
            weights = weights - self.learning_rate * gradient
            
            # Gioi han trong so >= 0
            weights = np.maximum(weights, 0)
            
            # Chuan hoa trong so
            if np.sum(weights) > 0:
                weights = weights / np.sum(weights)
            
            # Ghi thong tin
            if iteration % 10 == 0:
                logger.info(f"Vong lap {iteration}: objective = {objective:.6f}")
        
        return weights, history
    
    def _optimize_evolutionary(self) -> Tuple[np.ndarray, List[float]]:
        """
        Toi uu hoa bang thuat toan tiến hóa
        
        Returns:
            (optimized_weights, convergence_history)
        """
        # Gioi han trong so: [0, 1]
        bounds = [(0, 1) for _ in range(len(self.beam_weights))]
        
        # Thi hanh differential evolution
        result = differential_evolution(
            self._objective_function,
            bounds,
            popsize=self.population_size,
            mutation=self.mutation_rate,
            maxiter=self.max_iterations,
            tol=self.tolerance,
            callback=lambda xk, convergence: logger.info(f"DE iter: obj = {self._objective_function(xk):.6f}")
        )
        
        # Lay trong so toi uu
        weights = result.x
        
        # Chuan hoa trong so
        if np.sum(weights) > 0:
            weights = weights / np.sum(weights)
        
        # Can tao history
        history = []  # Khong co lich su hoi tu trong differential_evolution
        
        return weights, history
    
    def _optimize_basin_hopping(self) -> Tuple[np.ndarray, List[float]]:
        """
        Toi uu hoa bang thuat toan basin hopping
        
        Returns:
            (optimized_weights, convergence_history)
        """
        # Khoi tao diem bat dau voi trong so hien tai
        x0 = np.array(self.beam_weights)
        
        # Thi hanh basin hopping
        result = basinhopping(
            self._objective_function,
            x0,
            niter=self.max_iterations,
            T=1.0,
            stepsize=0.1,
            minimizer_kwargs={"method": "L-BFGS-B", 
                             "bounds": [(0, None) for _ in range(len(self.beam_weights))]}
        )
        
        # Lay trong so toi uu
        weights = result.x
        
        # Chuan hoa trong so
        if np.sum(weights) > 0:
            weights = weights / np.sum(weights)
        
        # Can tao history
        history = []  # Khong co lich su hoi tu trong basinhopping
        
        return weights, history
    
    def _optimize_hierarchical(self) -> Tuple[np.ndarray, List[float]]:
        """
        Toi uu hoa theo phuong phap phan cap theo muc do uu tien
        
        Returns:
            (optimized_weights, convergence_history)
        """
        # Gom nhom cac muc tieu theo uu tien
        priority_groups = {}
        for goal in self.goals:
            if goal.priority not in priority_groups:
                priority_groups[goal.priority] = []
            priority_groups[goal.priority].append(goal)
        
        weights = np.array(self.beam_weights)
        history = []
        
        # Xu ly theo thu tu uu tien (tang dan)
        for priority in sorted(priority_groups.keys()):
            logger.info(f"Dang toi uu nhom uu tien {priority}")
            
            # Chi giu lai cac muc tieu co uu tien hien tai va cao hon
            current_goals = []
            for p in sorted(priority_groups.keys()):
                if p <= priority:  # Chi bao gom cac uu tien cao hơn hoac bang
                    current_goals.extend(priority_groups[p])
            
            # Tam thoi thay the goals bang nhom hien tai
            saved_goals = self.goals
            self.goals = current_goals
            
            # Chay toi uu
            if self.algorithm == self.ALGO_GRADIENT_DESCENT:
                weights, step_history = self._optimize_gradient_descent()
            elif self.algorithm == self.ALGO_EVOLUTIONARY:
                weights, step_history = self._optimize_evolutionary()
            elif self.algorithm == self.ALGO_BASIN_HOPPING:
                weights, step_history = self._optimize_basin_hopping()
            else:
                logger.error(f"Thuat toan khong duoc ho tro: {self.algorithm}")
                weights, step_history = weights, []
            
            # Luu lich su
            history.extend(step_history)
            
            # Khoi phuc goals
            self.goals = saved_goals
        
        return weights, history
    
    def optimize(self) -> Dict[str, Any]:
        """
        Thuc hien toi uu hoa
        
        Returns:
            Dict chua ket qua toi uu
        """
        # Kiem tra dieu kien truoc khi toi uu
        if not self.goals:
            logger.error("Khong co muc tieu nao duoc them vao")
            return {"success": False, "message": "Khong co muc tieu nao"}
        
        if not self.beam_dose_contributions:
            logger.error("Khong co ma tran dong gop lieu chum tia")
            return {"success": False, "message": "Thieu ma tran dong gop lieu"}
        
        if not self.structures:
            logger.error("Khong co cau truc nao duoc them vao")
            return {"success": False, "message": "Khong co cau truc"}
        
        # Bat dau toi uu hoa
        start_time = time.time()
        logger.info(f"Bat dau toi uu hoa voi {len(self.goals)} muc tieu, "
                  f"{len(self.beam_weights)} chum tia, "
                  f"thuat toan {self.algorithm}")
        
        # Toi uu hoa theo thuat toan duoc chon
        if self.algorithm == self.ALGO_GRADIENT_DESCENT:
            weights, history = self._optimize_gradient_descent()
        elif self.algorithm == self.ALGO_EVOLUTIONARY:
            weights, history = self._optimize_evolutionary()
        elif self.algorithm == self.ALGO_BASIN_HOPPING:
            weights, history = self._optimize_basin_hopping()
        elif self.algorithm == self.ALGO_HIERARCHICAL:
            weights, history = self._optimize_hierarchical()
        else:
            logger.error(f"Thuat toan khong duoc ho tro: {self.algorithm}")
            return {"success": False, "message": f"Thuat toan khong duoc ho tro: {self.algorithm}"}
        
        # Luu ket qua
        self.optimized_weights = weights
        self.convergence_history = history
        self.optimization_time = time.time() - start_time
        
        # Tinh toan lai ma tran lieu voi trong so toi uu
        self.dose_matrix = np.zeros_like(self.beam_dose_contributions[0])
        for i, beam_dose in enumerate(self.beam_dose_contributions):
            self.dose_matrix += beam_dose * weights[i]
        
        # Tinh objective value sau cung
        final_objective = self._calculate_objective_value(weights)
        self.objective_values.append(final_objective)
        
        logger.info(f"Da hoan thanh toi uu hoa sau {self.optimization_time:.2f} giay")
        logger.info(f"Gia tri muc tieu cuoi cung: {final_objective:.6f}")
        logger.info(f"Trong so toi uu: {weights}")
        
        # Tra ve ket qua toi uu
        results = {
            "success": True,
            "weights": weights.tolist(),
            "objective_value": final_objective,
            "optimization_time": self.optimization_time,
            "iterations": len(history),
            "convergence_history": history,
            "algorithm": self.algorithm
        }
        
        return results
    
    def get_optimized_dose(self) -> np.ndarray:
        """
        Lay ma tran lieu sau khi toi uu
        
        Returns:
            Ma tran lieu da toi uu
        """
        if self.optimized_weights is None:
            logger.warning("Chua thuc hien toi uu hoa")
            return None
        
        return self.dose_matrix
    
    def get_dose_for_structure(self, structure_name: str) -> np.ndarray:
        """
        Lay ma tran lieu trong mot cau truc cu the
        
        Args:
            structure_name: Ten cau truc
            
        Returns:
            Ma tran lieu trong cau truc, None neu khong tim thay
        """
        if structure_name not in self.structures:
            logger.warning(f"Cau truc {structure_name} khong ton tai")
            return None
        
        if self.dose_matrix is None:
            logger.warning("Chua tinh toan ma tran lieu")
            return None
        
        # Lay mat na cau truc
        structure_mask = self.structures[structure_name]
        
        # Ap dung mat na vao ma tran lieu
        structure_dose = self.dose_matrix * structure_mask
        
        return structure_dose
    
    def evaluate_goals_after_optimization(self) -> Dict[str, Dict[str, Any]]:
        """
        Danh gia cac muc tieu sau khi toi uu
        
        Returns:
            Dict chua ket qua danh gia moi muc tieu
        """
        if self.optimized_weights is None:
            logger.warning("Chua thuc hien toi uu hoa")
            return {}
        
        # Danh gia tung muc tieu
        goal_results = {}
        
        for goal in self.goals:
            # Danh gia muc tieu
            goal_value = self._evaluate_goal(goal, self.dose_matrix)
            is_satisfied = goal_value < 0.01  # Coi la thoa man neu gia tri < 0.01
            
            # Tao chuoi mo ta
            description = str(goal)
            
            # Them ket qua vao dictionary
            goal_results[goal.structure_name + "_" + goal.goal_type] = {
                "goal": goal.to_dict(),
                "value": goal_value,
                "is_satisfied": is_satisfied,
                "description": description
            }
            
            # Ghi log
            status = "THOA MAN" if is_satisfied else "KHONG THOA MAN"
            logger.info(f"Muc tieu: {description} - {status} (gia tri = {goal_value:.6f})")
        
        return goal_results
    
    def save_results_to_json(self, file_path: str):
        """
        Luu ket qua toi uu sang file JSON
        
        Args:
            file_path: Duong dan den file JSON
        """
        import json
        
        # Kiem tra xem da toi uu chua
        if self.optimized_weights is None:
            logger.warning("Chua thuc hien toi uu hoa, khong co gi de luu")
            return
        
        # Chuan bi du lieu de luu
        results = {
            "algorithm": self.algorithm,
            "goals": [goal.to_dict() for goal in self.goals],
            "optimized_weights": self.optimized_weights.tolist(),
            "objective_value": self.objective_values[-1] if self.objective_values else None,
            "optimization_time": self.optimization_time,
            "iterations": len(self.convergence_history),
            "parameters": {
                "max_iterations": self.max_iterations,
                "tolerance": self.tolerance,
                "learning_rate": self.learning_rate,
                "population_size": self.population_size,
                "mutation_rate": self.mutation_rate
            },
            "goal_evaluation": self.evaluate_goals_after_optimization()
        }
        
        # Luu sang file JSON
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=4)
        
        logger.info(f"Da luu ket qua toi uu hoa sang {file_path}")


def create_optimizer(algorithm: str = "gradient_descent") -> GoalBasedOptimizer:
    """
    Ham utility de tao doi tuong toi uu hoa
    
    Args:
        algorithm: Thuat toan toi uu
        
    Returns:
        Doi tuong GoalBasedOptimizer
    """
    if algorithm == "gradient_descent":
        return GoalBasedOptimizer(GoalBasedOptimizer.ALGO_GRADIENT_DESCENT)
    elif algorithm == "evolutionary":
        return GoalBasedOptimizer(GoalBasedOptimizer.ALGO_EVOLUTIONARY)
    elif algorithm == "basin_hopping":
        return GoalBasedOptimizer(GoalBasedOptimizer.ALGO_BASIN_HOPPING)
    elif algorithm == "hierarchical":
        return GoalBasedOptimizer(GoalBasedOptimizer.ALGO_HIERARCHICAL)
    else:
        logger.warning(f"Thuat toan {algorithm} khong duoc ho tro, su dung gradient_descent")
        return GoalBasedOptimizer(GoalBasedOptimizer.ALGO_GRADIENT_DESCENT) 