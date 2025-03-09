"""
Module kiểm soát chất lượng (QA) cho hệ thống QuangStation V2
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional
import os
import json
from datetime import datetime

from quangstation.utils.logging import get_logger
from quangstation.utils.config import get_config
from quangstation.plan_evaluation.dvh import DVHCalculator

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
        
        # Tạo DVH Calculator
        self.dvh_calculator = DVHCalculator()
        self.dvh_calculator.set_dose_data(self.dose_data)
        
        # Tính toán DVH cho tất cả cấu trúc
        self.dvh_data = {}
        for name, structure in self.structures.items():
            self.dvh_calculator.add_structure(name, structure)
            self.dvh_data[name] = self.dvh_calculator.calculate_dvh(structure_name=name)
        
        logger.info("Khởi tạo module kiểm soát chất lượng kế hoạch")
    
    def check_dose_coverage(self, target_name: str, prescription_dose: float, 
                           coverage_threshold: float = 95.0) -> Dict:
        """
        Kiểm tra độ phủ liều trên thể tích đích
        
        Args:
            target_name: Tên cấu trúc đích
            prescription_dose: Liều kê toa (Gy)
            coverage_threshold: Ngưỡng phần trăm thể tích (thường 95%)
            
        Returns:
            Dict kết quả kiểm tra
        """
        results = {
            'test_name': 'Target Coverage',
            'target': target_name,
            'prescription_dose': prescription_dose,
            'coverage_threshold': coverage_threshold,
            'passed': False,
            'details': {}
        }
        
        try:
            # Kiểm tra xem cấu trúc đích có tồn tại không
            if target_name not in self.structures:
                results['error'] = f"Không tìm thấy cấu trúc đích '{target_name}'"
                return results
                
            # Lấy dữ liệu DVH của cấu trúc đích
            if target_name not in self.dvh_data:
                results['error'] = f"Không có dữ liệu DVH cho cấu trúc đích '{target_name}'"
                return results
                
            dvh_result = self.dvh_data[target_name]
            
            # Tính phần trăm thể tích nhận đủ liều kê toa
            dose_bins = dvh_result['cumulative']['dose']
            volume_bins = dvh_result['cumulative']['volume']
            
            # Tìm chỉ số bin gần liều kê toa nhất
            idx = np.abs(dose_bins - prescription_dose).argmin()
            
            # Lấy phần trăm thể tích tại mức liều này
            if idx < len(volume_bins):
                coverage = volume_bins[idx]
            else:
                coverage = 0.0
                
            # Cũng kiểm tra V90, V95, V100 và V105
            v90 = self._get_volume_at_dose_percent(dvh_result, prescription_dose * 0.9)
            v95 = self._get_volume_at_dose_percent(dvh_result, prescription_dose * 0.95)
            v100 = self._get_volume_at_dose_percent(dvh_result, prescription_dose)
            v105 = self._get_volume_at_dose_percent(dvh_result, prescription_dose * 1.05)
            v110 = self._get_volume_at_dose_percent(dvh_result, prescription_dose * 1.1)
            
            # Tính thể tích chưa đạt liều
            under_dosed = 100.0 - coverage
            
            # Đánh giá kết quả
            passed = coverage >= coverage_threshold
            
            # Lưu chi tiết
            results['details'] = {
                'coverage': coverage,
                'under_dosed': under_dosed,
                'V90': v90,
                'V95': v95,
                'V100': v100,
                'V105': v105,
                'V110': v110
            }
            results['passed'] = passed
            
            # Thêm nhận xét
            if passed:
                results['comment'] = f"Thể tích PTV nhận đủ liều kê toa: {coverage:.1f}% (yêu cầu: {coverage_threshold}%)"
            else:
                results['comment'] = f"Thể tích PTV nhận đủ liều kê toa: {coverage:.1f}% (thấp hơn yêu cầu: {coverage_threshold}%)"
            
            logger.info(f"Kiểm tra độ phủ liều của {target_name}: {coverage:.1f}% (ngưỡng: {coverage_threshold}%) - {'Đạt' if passed else 'Không đạt'}")
            
            return results
            
        except Exception as error:
            logger.error(f"Lỗi khi kiểm tra độ phủ liều: {str(error)}")
            results['error'] = str(error)
            return results
    
    def _get_volume_at_dose_percent(self, dvh_result, dose_level):
        """Lấy thể tích (%) tại mức liều nhất định"""
        dose_bins = dvh_result['cumulative']['dose']
        volume_bins = dvh_result['cumulative']['volume']
        
        # Tìm chỉ số bin gần liều nhất
        idx = np.abs(dose_bins - dose_level).argmin()
        
        # Lấy phần trăm thể tích tại mức liều này
        if idx < len(volume_bins):
            return volume_bins[idx]
        else:
            return 0.0
    
    def check_oar_constraints(self, constraints: Dict[str, Dict]) -> Dict:
        """
        Kiểm tra ràng buộc cho các cơ quan nguy cấp
        
        Args:
            constraints: Dict các ràng buộc liều:
                {
                    "organ_name": {
                        "max_dose": 45.0,   # Liều tối đa (Gy)
                        "mean_dose": 20.0,  # Liều trung bình (Gy)
                        "D1cc": 50.0,       # Liều tối đa trên 1cc (Gy)
                        "V20Gy": 35.0       # Thể tích tối đa (%) nhận ít nhất 20Gy
                    }
                }
            
        Returns:
            Dict kết quả kiểm tra
        """
        results = {
            'test_name': 'OAR Constraints',
            'constraints': constraints,
            'passed': True,
            'results_by_organ': {}
        }
        
        try:
            all_passed = True
            
            # Kiểm tra từng cơ quan
            for organ_name, organ_constraints in constraints.items():
                if organ_name not in self.structures:
                    logger.warning(f"Không tìm thấy cơ quan '{organ_name}' trong danh sách cấu trúc")
                    continue
                    
                if organ_name not in self.dvh_data:
                    logger.warning(f"Không có dữ liệu DVH cho cơ quan '{organ_name}'")
                    continue
                
                # Lấy dữ liệu DVH
                dvh_result = self.dvh_data[organ_name]
                
                # Lấy cấu trúc và liều
                structure = self.structures[organ_name]
                
                # Kiểm tra từng ràng buộc
                organ_result = {
                    'name': organ_name,
                    'constraints': organ_constraints,
                    'constraint_results': {},
                    'passed': True
                }
                
                # Kiểm tra liều tối đa
                if 'max_dose' in organ_constraints:
                    max_dose_limit = organ_constraints['max_dose']
                    actual_max_dose = np.max(self.dose_data[structure > 0])
                    max_dose_passed = actual_max_dose <= max_dose_limit
                    
                    organ_result['constraint_results']['max_dose'] = {
                        'limit': max_dose_limit,
                        'actual': actual_max_dose,
                        'passed': max_dose_passed
                    }
                    
                    if not max_dose_passed:
                        organ_result['passed'] = False
                
                # Kiểm tra liều trung bình
                if 'mean_dose' in organ_constraints:
                    mean_dose_limit = organ_constraints['mean_dose']
                    actual_mean_dose = np.mean(self.dose_data[structure > 0])
                    mean_dose_passed = actual_mean_dose <= mean_dose_limit
                    
                    organ_result['constraint_results']['mean_dose'] = {
                        'limit': mean_dose_limit,
                        'actual': actual_mean_dose,
                        'passed': mean_dose_passed
                    }
                    
                    if not mean_dose_passed:
                        organ_result['passed'] = False
                
                # Kiểm tra các ràng buộc VxGy
                for constraint_name, constraint_value in organ_constraints.items():
                    if constraint_name.startswith('V') and constraint_name.endswith('Gy'):
                        # Ví dụ: V20Gy, trích xuất mức liều 20
                        try:
                            dose_level = float(constraint_name[1:-2])  # Bỏ 'V' và 'Gy'
                            volume_limit = constraint_value
                            
                            # Lấy thể tích thực tế tại mức liều này
                            actual_volume = self._get_volume_at_dose_percent(dvh_result, dose_level)
                            volume_passed = actual_volume <= volume_limit
                            
                            organ_result['constraint_results'][constraint_name] = {
                                'limit': volume_limit,
                                'actual': actual_volume,
                                'passed': volume_passed
                            }
                            
                            if not volume_passed:
                                organ_result['passed'] = False
                        except ValueError:
                            logger.warning(f"Không thể phân tích ràng buộc '{constraint_name}'")
                
                # Cập nhật trạng thái chung
                if not organ_result['passed']:
                    all_passed = False
                
                # Lưu kết quả cho cơ quan này
                results['results_by_organ'][organ_name] = organ_result
            
            # Cập nhật trạng thái chung
            results['passed'] = all_passed
            
            # Thêm nhận xét
            if all_passed:
                results['comment'] = "Tất cả ràng buộc cho cơ quan nguy cấp đều được thỏa mãn"
            else:
                violated_organs = [name for name, result in results['results_by_organ'].items() 
                                 if not result['passed']]
                results['comment'] = f"Ràng buộc không thỏa mãn cho các cơ quan: {', '.join(violated_organs)}"
            
            logger.info(f"Kiểm tra ràng buộc cơ quan nguy cấp: {'Đạt' if all_passed else 'Không đạt'}")
            
            return results
            
        except Exception as error:
            logger.error(f"Lỗi khi kiểm tra ràng buộc cơ quan nguy cấp: {str(error)}")
            results['error'] = str(error)
            results['passed'] = False
            return results
    
    def check_plan_conformity(self, target_name: str, prescription_isodose: float = 95.0) -> Dict:
        """
        Kiểm tra tính phù hợp của kế hoạch (Conformity Index)
        
        Args:
            target_name: Tên cấu trúc đích
            prescription_isodose: Phần trăm liều kê toa
            
        Returns:
            Dict kết quả kiểm tra
        """
        results = {
            'test_name': 'Plan Conformity',
            'target': target_name,
            'prescription_isodose': prescription_isodose,
            'passed': False,
            'details': {}
        }
        
        try:
            # Kiểm tra xem cấu trúc đích có tồn tại không
            if target_name not in self.structures:
                results['error'] = f"Không tìm thấy cấu trúc đích '{target_name}'"
                return results
            
            # Lấy liều kê toa
            if 'prescribed_dose' in self.plan_data:
                prescription_dose = self.plan_data['prescribed_dose']
            else:
                prescription_dose = 50.0  # Giá trị mặc định
                logger.warning(f"Không tìm thấy liều kê toa, sử dụng giá trị mặc định {prescription_dose} Gy")
            
            # Tính liều theo phần trăm kê toa
            prescription_iso_dose = prescription_dose * (prescription_isodose / 100.0)
            
            # Tính thể tích nhận liều kê toa (PIV - Prescription Isodose Volume)
            piv_mask = self.dose_data >= prescription_iso_dose
            piv_volume = np.sum(piv_mask)
            
            # Lấy thể tích đích (TV - Target Volume)
            target_mask = self.structures[target_name]
            tv_volume = np.sum(target_mask)
            
            # Tính thể tích chung (TV&PIV)
            overlap_mask = np.logical_and(target_mask, piv_mask)
            overlap_volume = np.sum(overlap_mask)
            
            # Tính chỉ số CI (Conformity Index) = (TV&PIV)^2 / (TV * PIV)
            if tv_volume > 0 and piv_volume > 0:
                ci = (overlap_volume ** 2) / (tv_volume * piv_volume)
            else:
                ci = 0.0
                
            # Tính RTOG CI = PIV/TV
            if tv_volume > 0:
                rtog_ci = piv_volume / tv_volume
            else:
                rtog_ci = 0.0
                
            # Tính Paddick CI
            if tv_volume > 0 and piv_volume > 0:
                paddick_ci = (overlap_volume ** 2) / (tv_volume * piv_volume)
            else:
                paddick_ci = 0.0
                
            # Tính GI (Gradient Index) - độ dốc của gradiant liều
            gi_mask = self.dose_data >= (prescription_iso_dose / 2.0)
            gi_volume = np.sum(gi_mask)
            
            if piv_volume > 0:
                gi = gi_volume / piv_volume
            else:
                gi = 0.0
                
            # Đánh giá kết quả
            # Theo RTOG:
            # CI < 1.0: dưới liều, CI > 1.0: quá liều
            # 1.0 <= CI <= 2.0: sự tuân thủ theo protocol
            # 0.9 <= CI < 1.0 hoặc 2.0 < CI <= 2.5: sự sai lệch nhỏ
            # CI < 0.9 hoặc CI > 2.5: sự sai lệch lớn
            
            if 0.9 <= rtog_ci <= 2.0:
                passed = True
                comment = "Chỉ số phù hợp trong giới hạn chấp nhận được"
            else:
                passed = False
                if rtog_ci < 0.9:
                    comment = "Dưới liều: liều kê toa không bao phủ đủ thể tích đích"
                else:  # > 2.0
                    comment = "Quá liều: liều kê toa bao phủ quá nhiều vùng ngoài thể tích đích"
            
            # Lưu chi tiết
            results['details'] = {
                'prescription_dose': prescription_dose,
                'prescription_iso_dose': prescription_iso_dose,
                'tv_volume': tv_volume,
                'piv_volume': piv_volume,
                'overlap_volume': overlap_volume,
                'ci': ci,
                'rtog_ci': rtog_ci,
                'paddick_ci': paddick_ci,
                'gi': gi
            }
            
            results['passed'] = passed
            results['comment'] = comment
            
            logger.info(f"Kiểm tra tính phù hợp kế hoạch: CI = {rtog_ci:.3f}, GI = {gi:.3f} - {'Đạt' if passed else 'Không đạt'}")
            
            return results
            
        except Exception as error:
            logger.error(f"Lỗi khi kiểm tra tính phù hợp kế hoạch: {str(error)}")
            results['error'] = str(error)
            return results
    
    def check_plan_homogeneity(self, target_name: str) -> Dict:
        """
        Kiểm tra tính đồng nhất của kế hoạch (Homogeneity Index)
        
        Args:
            target_name: Tên cấu trúc đích
            
        Returns:
            Dict kết quả kiểm tra
        """
        results = {
            'test_name': 'Plan Homogeneity',
            'target': target_name,
            'passed': False,
            'details': {}
        }
        
        try:
            # Kiểm tra xem cấu trúc đích có tồn tại không
            if target_name not in self.structures:
                results['error'] = f"Không tìm thấy cấu trúc đích '{target_name}'"
                return results
            
            # Lấy thể tích đích và liều
            target_mask = self.structures[target_name]
            target_doses = self.dose_data[target_mask > 0]
            
            if len(target_doses) == 0:
                results['error'] = f"Cấu trúc đích '{target_name}' không có voxel nào"
                return results
            
            # Tính các liều đặc trưng
            d_max = np.max(target_doses)
            d_min = np.min(target_doses)
            d_mean = np.mean(target_doses)
            d_median = np.median(target_doses)
            
            # Tìm liều cho các phần trăm thể tích - D98, D95, D5, D2
            # Sắp xếp liều tăng dần
            sorted_doses = np.sort(target_doses)
            num_voxels = len(sorted_doses)
            
            # Tính các liều
            d2 = sorted_doses[int(num_voxels * 0.98)]  # Liều nhận bởi 2% thể tích (cận trên)
            d5 = sorted_doses[int(num_voxels * 0.95)]  # Liều nhận bởi 5% thể tích
            d95 = sorted_doses[int(num_voxels * 0.05)]  # Liều nhận bởi 95% thể tích
            d98 = sorted_doses[int(num_voxels * 0.02)]  # Liều nhận bởi 98% thể tích (cận dưới)
            
            # Tính các chỉ số đồng nhất
            # RTOG HI = Dmax / Dp (liều kê toa)
            prescribed_dose = self.plan_data.get('prescribed_dose', d_mean)  # Dùng d_mean nếu không có liều kê toa
            rtog_hi = d_max / prescribed_dose
            
            # ICRU HI = (D2 - D98) / Dp
            icru_hi = (d2 - d98) / prescribed_dose
            
            # D5/D95 HI
            d5_d95_hi = d5 / d95 if d95 > 0 else float('inf')
            
            # Đánh giá kết quả
            # Theo ICRU 83: HI càng gần 0 càng tốt
            # HI < 0.05: xuất sắc
            # 0.05 <= HI <= 0.07: tốt
            # 0.07 < HI < 0.1: chấp nhận được
            # HI >= 0.1: kém
            
            if icru_hi < 0.07:
                passed = True
                if icru_hi < 0.05:
                    comment = "Tính đồng nhất xuất sắc"
                else:
                    comment = "Tính đồng nhất tốt"
            else:
                if icru_hi < 0.1:
                    passed = True
                    comment = "Tính đồng nhất chấp nhận được"
                else:
                    passed = False
                    comment = "Tính đồng nhất kém"
            
            # Lưu chi tiết
            results['details'] = {
                'd_max': d_max,
                'd_min': d_min,
                'd_mean': d_mean,
                'd_median': d_median,
                'd2': d2,
                'd5': d5,
                'd95': d95,
                'd98': d98,
                'rtog_hi': rtog_hi,
                'icru_hi': icru_hi,
                'd5_d95_hi': d5_d95_hi
            }
            
            results['passed'] = passed
            results['comment'] = comment
            
            logger.info(f"Kiểm tra tính đồng nhất kế hoạch: HI = {icru_hi:.3f} - {'Đạt' if passed else 'Không đạt'}")
            
            return results
            
        except Exception as error:
            logger.error(f"Lỗi khi kiểm tra tính đồng nhất kế hoạch: {str(error)}")
            results['error'] = str(error)
            return results
    
    def run_all_checks(self, target_name: str, prescription_dose: float, 
                      oar_constraints: Dict[str, Dict]) -> Dict:
        """
        Chạy tất cả kiểm tra chất lượng kế hoạch.
        
        Args:
            target_name: Tên cấu trúc đích
            prescription_dose: Liều kê toa (Gy)
            oar_constraints: Ràng buộc cho các cơ quan nguy cấp
            
        Returns:
            Dict kết quả kiểm tra
        """
        # Cập nhật liều kê toa trong dữ liệu kế hoạch
        if 'prescribed_dose' not in self.plan_data:
            self.plan_data['prescribed_dose'] = prescription_dose
        
        # Chạy các kiểm tra
        coverage_result = self.check_dose_coverage(target_name, prescription_dose)
        oar_result = self.check_oar_constraints(oar_constraints)
        conformity_result = self.check_plan_conformity(target_name)
        homogeneity_result = self.check_plan_homogeneity(target_name)
        
        # Tổng hợp kết quả
        all_results = {
            'target': target_name,
            'prescription_dose': prescription_dose,
            'timestamp': datetime.now().isoformat(),
            'all_passed': (
                coverage_result['passed'] and 
                oar_result['passed'] and 
                conformity_result['passed'] and 
                homogeneity_result['passed']
            ),
            'results': {
                'coverage': coverage_result,
                'oar_constraints': oar_result,
                'conformity': conformity_result,
                'homogeneity': homogeneity_result
            }
        }
        
        # Lưu kết quả
        self.qa_results = all_results
        
        logger.info(f"Hoàn thành kiểm tra QA kế hoạch - {'Đạt' if all_results['all_passed'] else 'Không đạt'}")
        
        return all_results
    
    def generate_qa_report(self, output_path: str = None) -> str:
        """
        Tạo báo cáo QA.
        
        Args:
            output_path: Đường dẫn file báo cáo. Nếu None sẽ tạo file tự động.
            
        Returns:
            Đường dẫn file báo cáo.
        """
        if not self.qa_results:
            logger.warning("Chưa có kết quả QA để tạo báo cáo")
            return None
            
        # Tạo đường dẫn file báo cáo mặc định nếu không chỉ định
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"qa_report_{timestamp}.json"
            
        try:
            # Lưu báo cáo dưới dạng JSON
            with open(output_path, 'w') as f:
                json.dump(self.qa_results, f, indent=2)
                
            logger.info(f"Đã tạo báo cáo QA tại {output_path}")
            return output_path
            
        except Exception as error:
            logger.error(f"Lỗi khi tạo báo cáo QA: {str(error)}")
            return None

class MachineQA:
    """Lớp kiểm soát chất lượng máy xạ trị"""
    
    def __init__(self):
        """Khởi tạo đối tượng kiểm soát chất lượng máy"""
        self.qa_results = {}
        logger.info("Khởi tạo module kiểm soát chất lượng máy")
    
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
                logger.warning(f"Không có dữ liệu đo cho năng lượng: {energy}")
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
        
        logger.info(f"Kiểm tra đầu ra chùm tia: {sum(1 for r in results.values() if r['passed'])}/{len(results)} đạt yêu cầu")
        
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
        
        logger.info(f"Kiểm tra độ phẳng và đối xứng: {sum(1 for r in results.values() if r['status'] == 'pass')}/{len(results)} đạt yêu cầu")
        
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
            logger.error("Chưa có kết quả QA để tạo báo cáo")
            return None
        
        if output_path is None:
            output_dir = get_config("paths.export", os.path.expanduser("~/QuangStationV2/export"))
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"machine_qa_report_{datetime.now().strftime('%Y%m%d')}.json")
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.qa_results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Đã tạo báo cáo QA máy tại: {output_path}")
            return output_path
        except Exception as error:
            logger.error(f"Lỗi khi tạo báo cáo QA máy: {error}")
            return None 