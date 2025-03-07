"""
Module kiểm soát chất lượng (QA) cho hệ thống QuangStation V2
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional
import os
import json
from datetime import datetime

from utils.logging import get_logger
from utils.config import get_config

logger = get_logger("QualityAssurance")

class PlanQA:
    """Lớp kiểm soát chất lượng kế hoạch xạ trị"""
    
    def __init__(self, plan_data, dose_data, structures):
        """
        Khởi tạo đối tượng kiểm soát chất lượng
        
        Args:
            plan_data (dict): Thông tin kế hoạch xạ trị
            dose_data (np.ndarray): Dữ liệu liều
            structures (dict): Thông tin các cấu trúc
        """
        self.plan_data = plan_data
        self.dose_data = dose_data
        self.structures = structures
        self.qa_results = {}
        
        logger.log_info("Khởi tạo module kiểm soát chất lượng kế hoạch")
    
    def check_dose_coverage(self, target_name: str, prescription_dose: float, 
                           coverage_threshold: float = 95.0) -> Dict:
        """
        Kiểm tra độ phủ liều cho thể tích mục tiêu
        
        Args:
            target_name: Tên cấu trúc mục tiêu (PTV, CTV, GTV)
            prescription_dose: Liều chỉ định (Gy)
            coverage_threshold: Ngưỡng độ phủ (%, mặc định 95%)
            
        Returns:
            Dict chứa kết quả kiểm tra
        """
        if target_name not in self.structures:
            logger.log_error(f"Không tìm thấy cấu trúc mục tiêu: {target_name}")
            return {"status": "error", "message": f"Không tìm thấy cấu trúc mục tiêu: {target_name}"}
        
        # Lấy mặt nạ cấu trúc mục tiêu
        target_mask = self.structures[target_name]["mask"]
        
        # Lấy liều trong thể tích mục tiêu
        target_dose = self.dose_data[target_mask]
        
        # Tính phần trăm thể tích nhận đủ liều chỉ định
        volume_covered = np.sum(target_dose >= prescription_dose) / len(target_dose) * 100
        
        # Kiểm tra độ phủ
        passed = volume_covered >= coverage_threshold
        
        result = {
            "target": target_name,
            "prescription_dose": prescription_dose,
            "coverage_threshold": coverage_threshold,
            "volume_covered": volume_covered,
            "passed": passed,
            "status": "pass" if passed else "fail"
        }
        
        # Lưu kết quả
        self.qa_results[f"dose_coverage_{target_name}"] = result
        
        logger.log_info(f"Kiểm tra độ phủ liều cho {target_name}: {result['status']}")
        
        return result
    
    def check_oar_constraints(self, constraints: Dict[str, Dict]) -> Dict:
        """
        Kiểm tra ràng buộc liều cho các cơ quan nguy cấp (OAR)
        
        Args:
            constraints: Dict chứa các ràng buộc liều
                {organ_name: {"max_dose": float, "mean_dose": float, "volume_dose": [(volume_percent, dose)]}}
                
        Returns:
            Dict chứa kết quả kiểm tra
        """
        results = {}
        
        for organ_name, constraint in constraints.items():
            if organ_name not in self.structures:
                logger.log_warning(f"Không tìm thấy cấu trúc: {organ_name}")
                continue
            
            # Lấy mặt nạ cơ quan
            organ_mask = self.structures[organ_name]["mask"]
            
            # Lấy liều trong cơ quan
            organ_dose = self.dose_data[organ_mask]
            
            organ_result = {"name": organ_name, "checks": []}
            
            # Kiểm tra liều tối đa
            if "max_dose" in constraint:
                max_dose_limit = constraint["max_dose"]
                actual_max_dose = np.max(organ_dose)
                max_dose_passed = actual_max_dose <= max_dose_limit
                
                organ_result["checks"].append({
                    "type": "max_dose",
                    "limit": max_dose_limit,
                    "actual": actual_max_dose,
                    "passed": max_dose_passed
                })
            
            # Kiểm tra liều trung bình
            if "mean_dose" in constraint:
                mean_dose_limit = constraint["mean_dose"]
                actual_mean_dose = np.mean(organ_dose)
                mean_dose_passed = actual_mean_dose <= mean_dose_limit
                
                organ_result["checks"].append({
                    "type": "mean_dose",
                    "limit": mean_dose_limit,
                    "actual": actual_mean_dose,
                    "passed": mean_dose_passed
                })
            
            # Kiểm tra ràng buộc thể tích-liều
            if "volume_dose" in constraint:
                for volume_percent, dose_limit in constraint["volume_dose"]:
                    # Tính phần trăm thể tích nhận liều lớn hơn dose_limit
                    volume_receiving_dose = np.sum(organ_dose > dose_limit) / len(organ_dose) * 100
                    volume_passed = volume_receiving_dose <= volume_percent
                    
                    organ_result["checks"].append({
                        "type": "volume_dose",
                        "volume_limit": volume_percent,
                        "dose_limit": dose_limit,
                        "actual_volume": volume_receiving_dose,
                        "passed": volume_passed
                    })
            
            # Xác định trạng thái tổng thể
            all_passed = all(check["passed"] for check in organ_result["checks"])
            organ_result["status"] = "pass" if all_passed else "fail"
            
            results[organ_name] = organ_result
        
        # Lưu kết quả
        self.qa_results["oar_constraints"] = results
        
        logger.log_info(f"Kiểm tra ràng buộc OAR: {sum(1 for r in results.values() if r['status'] == 'pass')}/{len(results)} đạt yêu cầu")
        
        return results
    
    def check_plan_conformity(self, target_name: str, prescription_isodose: float = 95.0) -> Dict:
        """
        Kiểm tra độ tương thích của kế hoạch
        
        Args:
            target_name: Tên cấu trúc mục tiêu
            prescription_isodose: Phần trăm đường đồng liều chỉ định (%)
            
        Returns:
            Dict chứa kết quả kiểm tra
        """
        if target_name not in self.structures:
            logger.log_error(f"Không tìm thấy cấu trúc mục tiêu: {target_name}")
            return {"status": "error", "message": f"Không tìm thấy cấu trúc mục tiêu: {target_name}"}
        
        # Lấy mặt nạ cấu trúc mục tiêu
        target_mask = self.structures[target_name]["mask"]
        
        # Tính liều chỉ định
        prescription_dose = self.plan_data.get("prescribed_dose", 0)
        if prescription_dose == 0:
            logger.log_error("Không tìm thấy liều chỉ định trong kế hoạch")
            return {"status": "error", "message": "Không tìm thấy liều chỉ định trong kế hoạch"}
        
        # Tính ngưỡng liều
        dose_threshold = prescription_dose * prescription_isodose / 100
        
        # Tạo mặt nạ cho vùng nhận liều lớn hơn ngưỡng
        dose_mask = self.dose_data >= dose_threshold
        
        # Tính thể tích mục tiêu
        target_volume = np.sum(target_mask)
        
        # Tính thể tích nhận liều lớn hơn ngưỡng
        prescription_volume = np.sum(dose_mask)
        
        # Tính thể tích mục tiêu nhận liều lớn hơn ngưỡng
        target_covered = np.sum(np.logical_and(target_mask, dose_mask))
        
        # Tính chỉ số tương thích (CI)
        ci = (target_covered ** 2) / (target_volume * prescription_volume) if prescription_volume > 0 else 0
        
        # Đánh giá CI
        if ci >= 0.8:
            ci_status = "excellent"
        elif ci >= 0.6:
            ci_status = "good"
        elif ci >= 0.4:
            ci_status = "fair"
        else:
            ci_status = "poor"
        
        result = {
            "target": target_name,
            "prescription_isodose": prescription_isodose,
            "conformity_index": ci,
            "evaluation": ci_status,
            "status": "pass" if ci >= 0.6 else "fail"
        }
        
        # Lưu kết quả
        self.qa_results["plan_conformity"] = result
        
        logger.log_info(f"Kiểm tra độ tương thích kế hoạch: CI = {ci:.3f}, đánh giá: {ci_status}")
        
        return result
    
    def check_plan_homogeneity(self, target_name: str) -> Dict:
        """
        Kiểm tra độ đồng nhất của kế hoạch
        
        Args:
            target_name: Tên cấu trúc mục tiêu
            
        Returns:
            Dict chứa kết quả kiểm tra
        """
        if target_name not in self.structures:
            logger.log_error(f"Không tìm thấy cấu trúc mục tiêu: {target_name}")
            return {"status": "error", "message": f"Không tìm thấy cấu trúc mục tiêu: {target_name}"}
        
        # Lấy mặt nạ cấu trúc mục tiêu
        target_mask = self.structures[target_name]["mask"]
        
        # Lấy liều trong thể tích mục tiêu
        target_dose = self.dose_data[target_mask]
        
        # Tính liều tối đa, tối thiểu và trung bình
        max_dose = np.max(target_dose)
        min_dose = np.min(target_dose)
        mean_dose = np.mean(target_dose)
        
        # Tính chỉ số đồng nhất (HI)
        hi = (max_dose - min_dose) / mean_dose
        
        # Đánh giá HI
        if hi <= 0.05:
            hi_status = "excellent"
        elif hi <= 0.1:
            hi_status = "good"
        elif hi <= 0.2:
            hi_status = "fair"
        else:
            hi_status = "poor"
        
        result = {
            "target": target_name,
            "max_dose": max_dose,
            "min_dose": min_dose,
            "mean_dose": mean_dose,
            "homogeneity_index": hi,
            "evaluation": hi_status,
            "status": "pass" if hi <= 0.1 else "fail"
        }
        
        # Lưu kết quả
        self.qa_results["plan_homogeneity"] = result
        
        logger.log_info(f"Kiểm tra độ đồng nhất kế hoạch: HI = {hi:.3f}, đánh giá: {hi_status}")
        
        return result
    
    def run_all_checks(self, target_name: str, prescription_dose: float, 
                      oar_constraints: Dict[str, Dict]) -> Dict:
        """
        Chạy tất cả các kiểm tra QA
        
        Args:
            target_name: Tên cấu trúc mục tiêu
            prescription_dose: Liều chỉ định (Gy)
            oar_constraints: Ràng buộc cho các cơ quan nguy cấp
            
        Returns:
            Dict chứa tất cả kết quả kiểm tra
        """
        # Kiểm tra độ phủ liều
        self.check_dose_coverage(target_name, prescription_dose)
        
        # Kiểm tra ràng buộc OAR
        self.check_oar_constraints(oar_constraints)
        
        # Kiểm tra độ tương thích
        self.check_plan_conformity(target_name)
        
        # Kiểm tra độ đồng nhất
        self.check_plan_homogeneity(target_name)
        
        # Tổng hợp kết quả
        all_passed = all(
            result.get("status") == "pass" 
            for result in self.qa_results.values() 
            if isinstance(result, dict) and "status" in result
        )
        
        summary = {
            "plan_name": self.plan_data.get("plan_name", "Unknown"),
            "target": target_name,
            "prescription_dose": prescription_dose,
            "overall_status": "pass" if all_passed else "fail",
            "results": self.qa_results
        }
        
        logger.log_info(f"Kết quả kiểm tra QA: {summary['overall_status']}")
        
        return summary
    
    def generate_qa_report(self, output_path: str = None) -> str:
        """
        Tạo báo cáo QA
        
        Args:
            output_path: Đường dẫn file báo cáo
            
        Returns:
            Đường dẫn file báo cáo
        """
        if not self.qa_results:
            logger.log_error("Chưa có kết quả QA để tạo báo cáo")
            return None
        
        if output_path is None:
            output_dir = get_config("paths.export", os.path.expanduser("~/QuangStationV2/export"))
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"qa_report_{self.plan_data.get('plan_id', 'unknown')}.json")
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.qa_results, f, indent=2, ensure_ascii=False)
            
            logger.log_info(f"Đã tạo báo cáo QA tại: {output_path}")
            return output_path
        except Exception as e:
            logger.log_error(f"Lỗi khi tạo báo cáo QA: {e}")
            return None

class MachineQA:
    """Lớp kiểm soát chất lượng máy xạ trị"""
    
    def __init__(self):
        """Khởi tạo đối tượng kiểm soát chất lượng máy"""
        self.qa_results = {}
        logger.log_info("Khởi tạo module kiểm soát chất lượng máy")
    
    def check_beam_output(self, measured_data: Dict[str, float], 
                         reference_data: Dict[str, float],
                         tolerance: float = 2.0) -> Dict:
        """
        Kiểm tra đầu ra chùm tia
        
        Args:
            measured_data: Dữ liệu đo được
            reference_data: Dữ liệu tham chiếu
            tolerance: Dung sai cho phép (%)
            
        Returns:
            Dict chứa kết quả kiểm tra
        """
        results = {}
        
        for energy, reference_value in reference_data.items():
            if energy not in measured_data:
                logger.log_warning(f"Không có dữ liệu đo cho năng lượng: {energy}")
                continue
            
            measured_value = measured_data[energy]
            
            # Tính phần trăm chênh lệch
            percent_diff = abs(measured_value - reference_value) / reference_value * 100
            
            # Kiểm tra dung sai
            passed = percent_diff <= tolerance
            
            results[energy] = {
                "reference": reference_value,
                "measured": measured_value,
                "percent_diff": percent_diff,
                "tolerance": tolerance,
                "passed": passed
            }
        
        # Lưu kết quả
        self.qa_results["beam_output"] = results
        
        logger.log_info(f"Kiểm tra đầu ra chùm tia: {sum(1 for r in results.values() if r['passed'])}/{len(results)} đạt yêu cầu")
        
        return results
    
    def check_flatness_symmetry(self, profiles: Dict[str, Dict[str, np.ndarray]], 
                              tolerance_flatness: float = 3.0,
                              tolerance_symmetry: float = 2.0) -> Dict:
        """
        Kiểm tra độ phẳng và đối xứng của chùm tia
        
        Args:
            profiles: Dict chứa profile theo năng lượng và hướng
                {energy: {"x": x_profile, "y": y_profile}}
            tolerance_flatness: Dung sai độ phẳng (%)
            tolerance_symmetry: Dung sai độ đối xứng (%)
            
        Returns:
            Dict chứa kết quả kiểm tra
        """
        results = {}
        
        for energy, profile_data in profiles.items():
            energy_result = {"flatness": {}, "symmetry": {}}
            
            for direction, profile in profile_data.items():
                # Tính độ phẳng
                max_value = np.max(profile)
                min_value = np.min(profile)
                flatness = (max_value - min_value) / (max_value + min_value) * 100
                
                # Kiểm tra độ phẳng
                flatness_passed = flatness <= tolerance_flatness
                
                energy_result["flatness"][direction] = {
                    "value": flatness,
                    "tolerance": tolerance_flatness,
                    "passed": flatness_passed
                }
                
                # Tính độ đối xứng
                mid_point = len(profile) // 2
                left_side = profile[:mid_point]
                right_side = profile[mid_point:][::-1]  # Đảo ngược để so sánh
                
                # Đảm bảo cùng kích thước
                min_length = min(len(left_side), len(right_side))
                left_side = left_side[-min_length:]
                right_side = right_side[-min_length:]
                
                # Tính độ đối xứng
                symmetry = np.max(np.abs(left_side - right_side) / (left_side + right_side) * 100)
                
                # Kiểm tra độ đối xứng
                symmetry_passed = symmetry <= tolerance_symmetry
                
                energy_result["symmetry"][direction] = {
                    "value": symmetry,
                    "tolerance": tolerance_symmetry,
                    "passed": symmetry_passed
                }
            
            # Xác định trạng thái tổng thể cho năng lượng này
            all_flatness_passed = all(item["passed"] for item in energy_result["flatness"].values())
            all_symmetry_passed = all(item["passed"] for item in energy_result["symmetry"].values())
            
            energy_result["status"] = "pass" if (all_flatness_passed and all_symmetry_passed) else "fail"
            
            results[energy] = energy_result
        
        # Lưu kết quả
        self.qa_results["flatness_symmetry"] = results
        
        logger.log_info(f"Kiểm tra độ phẳng và đối xứng: {sum(1 for r in results.values() if r['status'] == 'pass')}/{len(results)} đạt yêu cầu")
        
        return results
    
    def generate_qa_report(self, output_path: str = None) -> str:
        """
        Tạo báo cáo QA máy
        
        Args:
            output_path: Đường dẫn file báo cáo
            
        Returns:
            Đường dẫn file báo cáo
        """
        if not self.qa_results:
            logger.log_error("Chưa có kết quả QA để tạo báo cáo")
            return None
        
        if output_path is None:
            output_dir = get_config("paths.export", os.path.expanduser("~/QuangStationV2/export"))
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"machine_qa_report_{datetime.now().strftime('%Y%m%d')}.json")
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.qa_results, f, indent=2, ensure_ascii=False)
            
            logger.log_info(f"Đã tạo báo cáo QA máy tại: {output_path}")
            return output_path
        except Exception as e:
            logger.log_error(f"Lỗi khi tạo báo cáo QA máy: {e}")
            return None 