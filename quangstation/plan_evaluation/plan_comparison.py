#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module so sánh kế hoạch xạ trị cho QuangStation V2.
Cung cấp các chức năng so sánh nhiều kế hoạch xạ trị để hỗ trợ việc ra quyết định.
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional, Union, Any
from pathlib import Path
import json

from quangstation.utils.logging import get_logger
from quangstation.plan_evaluation.dvh import DVHCalculator
from quangstation.plan_evaluation.dose_map import DoseMap
from quangstation.plan_evaluation.biological_effects import BiologicalEffectsCalculator

logger = get_logger("PlanComparison")

class PlanComparison:
    """Lớp so sánh và đánh giá các kế hoạch xạ trị"""
    
    def __init__(self):
        """Khởi tạo đối tượng so sánh kế hoạch"""
        self.logger = get_logger("PlanComparison")
        self.plans = {}
        self.common_structures = []
        self.dvh_calculator = DVHCalculator()
        self.biological_calculator = BiologicalEffectsCalculator()
        
        # Các chỉ số đánh giá kế hoạch
        self.evaluation_metrics = {
            "conformity_index": "Chỉ số tương thích (CI)",
            "homogeneity_index": "Chỉ số đồng nhất (HI)",
            "gradient_index": "Chỉ số gradient (GI)",
            "d95": "D95 (%)",
            "d98": "D98 (%)",
            "d50": "D50 (%)",
            "d2": "D2 (%)",
            "v95": "V95 (%)",
            "v100": "V100 (%)",
            "v107": "V107 (%)",
            "max_dose": "Liều tối đa (%)",
            "min_dose": "Liều tối thiểu (%)",
            "mean_dose": "Liều trung bình (%)"
        }
    
    def add_plan(self, plan_id: str, plan_data: Dict):
        """
        Thêm kế hoạch xạ trị để so sánh
        
        Args:
            plan_id: ID của kế hoạch
            plan_data: Dữ liệu kế hoạch
        """
        # Kiểm tra dữ liệu kế hoạch
        required_keys = ["dose_matrix", "structures", "prescription_dose"]
        for key in required_keys:
            if key not in plan_data:
                self.logger.log_error(f"Dữ liệu kế hoạch thiếu thông tin: {key}")
                return False
        
        # Thêm kế hoạch
        self.plans[plan_id] = plan_data
        self.logger.log_info(f"Đã thêm kế hoạch: {plan_id}")
        
        # Cập nhật cấu trúc chung
        structures = set(plan_data["structures"].keys())
        
        if not self.common_structures:
            # Đây là kế hoạch đầu tiên
            self.common_structures = list(structures)
        else:
            # Cập nhật cấu trúc chung (giao giữa các kế hoạch)
            self.common_structures = list(set(self.common_structures).intersection(structures))
        
        return True
    
    def remove_plan(self, plan_id: str):
        """
        Xóa kế hoạch xạ trị khỏi danh sách so sánh
        
        Args:
            plan_id: ID của kế hoạch
        """
        if plan_id in self.plans:
            del self.plans[plan_id]
            self.logger.log_info(f"Đã xóa kế hoạch: {plan_id}")
            
            # Cập nhật lại cấu trúc chung
            if self.plans:
                self.common_structures = list(set.intersection(*[set(plan["structures"].keys()) for plan in self.plans.values()]))
            else:
                self.common_structures = []
            
            return True
        else:
            self.logger.log_warning(f"Không tìm thấy kế hoạch: {plan_id}")
            return False
    
    def compare_dvhs(self, structure_name: str, normalization: str = "prescription") -> Tuple[plt.Figure, Dict]:
        """
        So sánh DVH của cùng một cấu trúc giữa các kế hoạch
        
        Args:
            structure_name: Tên cấu trúc cần so sánh
            normalization: Phương pháp chuẩn hóa ('prescription', 'max', hoặc 'none')
            
        Returns:
            Figure và dữ liệu DVH
        """
        if structure_name not in self.common_structures:
            self.logger.log_warning(f"Cấu trúc {structure_name} không có trong tất cả các kế hoạch")
            return plt.figure(), {}
        
        # Tạo hình
        fig, ax = plt.subplots(figsize=(10, 8))
        dvh_data = {}
        
        for plan_id, plan in self.plans.items():
            # Lấy ma trận liều và mask cấu trúc
            dose_matrix = plan["dose_matrix"]
            structure_mask = plan["structures"][structure_name]
            prescription_dose = plan.get("prescription_dose", 100.0)
            
            # Chuẩn hóa liều nếu cần
            if normalization == "prescription":
                # Chuẩn hóa theo liều kê toa
                normalized_dose = dose_matrix / prescription_dose * 100
            elif normalization == "max":
                # Chuẩn hóa theo liều tối đa
                max_dose = np.max(dose_matrix)
                normalized_dose = dose_matrix / max_dose * 100
            else:
                # Không chuẩn hóa
                normalized_dose = dose_matrix
            
            # Tính DVH
            dose_values = []
            volume_percent = []
            
            # Lấy giá trị liều trong cấu trúc
            dose_in_structure = normalized_dose[structure_mask > 0]
            
            if len(dose_in_structure) == 0:
                self.logger.log_warning(f"Không có dữ liệu liều trong cấu trúc {structure_name} cho kế hoạch {plan_id}")
                continue
            
            # Sắp xếp giá trị liều
            sorted_dose = np.sort(dose_in_structure)
            total_voxels = len(sorted_dose)
            
            # Tính DVH tích lũy
            for i, dose in enumerate(sorted_dose):
                dose_values.append(dose)
                volume_percent.append(100 * (total_voxels - i) / total_voxels)
            
            # Vẽ DVH
            ax.plot(dose_values, volume_percent, label=f"{plan_id}", linewidth=2)
            
            # Lưu dữ liệu
            dvh_data[plan_id] = {
                "dose": dose_values,
                "volume": volume_percent
            }
        
        # Trang trí biểu đồ
        if normalization == "prescription":
            ax.set_xlabel("Liều (%)", fontsize=12)
        elif normalization == "max":
            ax.set_xlabel("Liều (% Liều tối đa)", fontsize=12)
        else:
            ax.set_xlabel("Liều (Gy)", fontsize=12)
            
        ax.set_ylabel("Thể tích (%)", fontsize=12)
        ax.set_title(f"So sánh DVH cho {structure_name}", fontsize=14)
        ax.grid(True)
        ax.legend(fontsize=10)
        
        # Các đường liều tham chiếu
        if normalization in ["prescription", "max"]:
            for dose_level in [95, 100, 105]:
                ax.axvline(x=dose_level, color='gray', linestyle='--', alpha=0.5)
                ax.text(dose_level + 0.5, 50, f"{dose_level}%", rotation=90, alpha=0.7)
        
        plt.tight_layout()
        
        return fig, dvh_data
    
    def compare_dose_metrics(self, structure_name: str = None) -> pd.DataFrame:
        """
        So sánh các chỉ số liều giữa các kế hoạch
        
        Args:
            structure_name: Tên cấu trúc cần so sánh (nếu None, so sánh tất cả cấu trúc chung)
            
        Returns:
            DataFrame chứa kết quả so sánh
        """
        structures_to_compare = [structure_name] if structure_name else self.common_structures
        
        if not structures_to_compare:
            self.logger.log_warning("Không có cấu trúc chung giữa các kế hoạch")
            return pd.DataFrame()
        
        results = []
        
        for structure in structures_to_compare:
            if structure not in self.common_structures:
                self.logger.log_warning(f"Cấu trúc {structure} không có trong tất cả các kế hoạch")
                continue
            
            structure_metrics = {"Structure": structure}
            
            for plan_id, plan in self.plans.items():
                # Lấy ma trận liều và mask cấu trúc
                dose_matrix = plan["dose_matrix"]
                structure_mask = plan["structures"][structure]
                prescription_dose = plan.get("prescription_dose", 100.0)
                
                # Chuẩn hóa liều theo liều kê toa
                normalized_dose = dose_matrix / prescription_dose * 100
                
                # Lấy giá trị liều trong cấu trúc
                dose_in_structure = normalized_dose[structure_mask > 0]
                
                if len(dose_in_structure) == 0:
                    self.logger.log_warning(f"Không có dữ liệu liều trong cấu trúc {structure} cho kế hoạch {plan_id}")
                    continue
                
                # Tính các chỉ số liều
                metrics = {}
                
                # Chỉ số cơ bản
                metrics["min_dose"] = np.min(dose_in_structure)
                metrics["max_dose"] = np.max(dose_in_structure)
                metrics["mean_dose"] = np.mean(dose_in_structure)
                
                # Các chỉ số Dx (liều nhận bởi x% thể tích)
                sorted_dose = np.sort(dose_in_structure)
                total_voxels = len(sorted_dose)
                
                for x in [2, 50, 95, 98]:
                    index = int(np.round(total_voxels * (100 - x) / 100))
                    if index >= total_voxels:
                        index = total_voxels - 1
                    metrics[f"d{x}"] = sorted_dose[index]
                
                # Các chỉ số Vx (thể tích nhận ít nhất x% liều)
                for x in [95, 100, 107]:
                    metrics[f"v{x}"] = 100 * np.sum(dose_in_structure >= x) / total_voxels
                
                # Chỉ số tương thích (CI) cho PTV
                if "PTV" in structure.upper():
                    v100 = np.sum(normalized_dose >= 100)
                    v100_in_ptv = np.sum((normalized_dose >= 100) & (structure_mask > 0))
                    ptv_volume = np.sum(structure_mask > 0)
                    
                    if v100 > 0 and ptv_volume > 0:
                        metrics["conformity_index"] = (v100_in_ptv ** 2) / (v100 * ptv_volume)
                    else:
                        metrics["conformity_index"] = 0
                
                # Chỉ số đồng nhất (HI) cho PTV
                if "PTV" in structure.upper():
                    if metrics["d2"] > 0:
                        metrics["homogeneity_index"] = (metrics["d2"] - metrics["d98"]) / metrics["d50"]
                    else:
                        metrics["homogeneity_index"] = 0
                
                # Thêm chỉ số cho kế hoạch này
                for metric, value in metrics.items():
                    structure_metrics[f"{plan_id}_{metric}"] = value
            
            results.append(structure_metrics)
        
        # Tạo DataFrame
        df = pd.DataFrame(results)
        
        return df
    
    def compare_biological_metrics(self, structure_list: Optional[List[str]] = None) -> pd.DataFrame:
        """
        So sánh các chỉ số hiệu quả sinh học giữa các kế hoạch
        
        Args:
            structure_list: Danh sách cấu trúc cần so sánh (nếu None, so sánh tất cả cấu trúc chung)
            
        Returns:
            DataFrame chứa kết quả so sánh
        """
        structures_to_compare = structure_list if structure_list else self.common_structures
        
        if not structures_to_compare:
            self.logger.log_warning("Không có cấu trúc chung giữa các kế hoạch")
            return pd.DataFrame()
        
        results = []
        
        for structure in structures_to_compare:
            if structure not in self.common_structures:
                self.logger.log_warning(f"Cấu trúc {structure} không có trong tất cả các kế hoạch")
                continue
            
            # Lấy giá trị α/β
            alpha_beta = self.biological_calculator.get_alphabeta_value(structure)
            
            structure_metrics = {
                "Structure": structure,
                "AlphaBeta": alpha_beta
            }
            
            for plan_id, plan in self.plans.items():
                # Lấy thông tin kế hoạch
                dose_matrix = plan["dose_matrix"]
                structure_mask = plan["structures"][structure]
                prescription_dose = plan.get("prescription_dose", 100.0)
                fractions = plan.get("fractions", 1)
                
                # Lấy giá trị liều trong cấu trúc (Gy)
                dose_in_structure = dose_matrix[structure_mask > 0]
                
                if len(dose_in_structure) == 0:
                    self.logger.log_warning(f"Không có dữ liệu liều trong cấu trúc {structure} cho kế hoạch {plan_id}")
                    continue
                
                # Tính liều trung bình
                mean_dose = np.mean(dose_in_structure)
                
                # Tính BED và EQD2
                bed = self.biological_calculator.calculate_bed(mean_dose, fractions, alpha_beta)
                eqd2 = self.biological_calculator.calculate_eqd2(mean_dose, fractions, alpha_beta)
                
                # Tính TCP cho khối u
                tcp = 0
                if "PTV" in structure.upper() or "GTV" in structure.upper() or "CTV" in structure.upper():
                    tcp = self.biological_calculator.calculate_tcp(mean_dose, fractions, alpha_beta=alpha_beta)
                
                # Tính NTCP cho cơ quan nguy cơ
                ntcp = 0
                if "PTV" not in structure.upper() and "GTV" not in structure.upper() and "CTV" not in structure.upper():
                    # Giả định TD5 dựa trên cấu trúc
                    td5 = 0
                    if "SPINAL_CORD" in structure.upper():
                        td5 = 47  # TD5 for spinal cord
                    elif "BRAINSTEM" in structure.upper():
                        td5 = 54  # TD5 for brainstem
                    elif "LUNG" in structure.upper():
                        td5 = 17.5  # TD5 for lung
                    elif "HEART" in structure.upper():
                        td5 = 40  # TD5 for heart
                    elif "LIVER" in structure.upper():
                        td5 = 30  # TD5 for liver
                    elif "KIDNEY" in structure.upper():
                        td5 = 23  # TD5 for kidney
                    elif "RECTUM" in structure.upper():
                        td5 = 60  # TD5 for rectum
                    elif "BLADDER" in structure.upper():
                        td5 = 65  # TD5 for bladder
                    else:
                        td5 = 45  # Default TD5
                    
                    if td5 > 0:
                        ntcp = self.biological_calculator.calculate_ntcp(eqd2, td5)
                
                # Thêm chỉ số cho kế hoạch này
                structure_metrics[f"{plan_id}_mean_dose"] = mean_dose
                structure_metrics[f"{plan_id}_bed"] = bed
                structure_metrics[f"{plan_id}_eqd2"] = eqd2
                
                if tcp > 0:
                    structure_metrics[f"{plan_id}_tcp"] = tcp
                
                if ntcp > 0:
                    structure_metrics[f"{plan_id}_ntcp"] = ntcp
            
            results.append(structure_metrics)
        
        # Tạo DataFrame
        df = pd.DataFrame(results)
        
        return df
    
    def generate_comparison_report(self, output_dir: str = None, base_plan_id: Optional[str] = None) -> Dict:
        """
        Tạo báo cáo so sánh chi tiết
        
        Args:
            output_dir: Thư mục đầu ra
            base_plan_id: ID kế hoạch cơ sở để so sánh (nếu None, sử dụng kế hoạch đầu tiên)
            
        Returns:
            Dictionary chứa kết quả so sánh và đường dẫn file
        """
        if not self.plans:
            self.logger.log_warning("Không có kế hoạch nào để so sánh")
            return {}
        
        # Xác định kế hoạch cơ sở
        if not base_plan_id:
            base_plan_id = list(self.plans.keys())[0]
        
        if base_plan_id not in self.plans:
            self.logger.log_warning(f"Không tìm thấy kế hoạch cơ sở: {base_plan_id}")
            base_plan_id = list(self.plans.keys())[0]
        
        # Tạo thư mục đầu ra nếu cần
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Tạo báo cáo chỉ số liều
        dose_metrics_df = self.compare_dose_metrics()
        
        # Tạo báo cáo chỉ số sinh học
        bio_metrics_df = self.compare_biological_metrics()
        
        # Tạo biểu đồ DVH cho các cấu trúc quan trọng
        dvh_figures = {}
        ptv_structures = [s for s in self.common_structures if "PTV" in s.upper()]
        oar_structures = [s for s in self.common_structures if "PTV" not in s.upper() and s.upper() != "BODY"]
        
        for structure in ptv_structures + oar_structures:
            fig, data = self.compare_dvhs(structure)
            dvh_figures[structure] = {"figure": fig, "data": data}
            
            if output_dir:
                file_path = os.path.join(output_dir, f"dvh_{structure}.png")
                fig.savefig(file_path, dpi=300, bbox_inches="tight")
        
        # Tạo báo cáo tóm tắt
        summary = {
            "plans": list(self.plans.keys()),
            "base_plan": base_plan_id,
            "common_structures": self.common_structures,
            "ptv_structures": ptv_structures,
            "oar_structures": oar_structures
        }
        
        # Lưu các DataFrame
        if output_dir:
            dose_metrics_file = os.path.join(output_dir, "dose_metrics.csv")
            bio_metrics_file = os.path.join(output_dir, "bio_metrics.csv")
            summary_file = os.path.join(output_dir, "summary.json")
            
            dose_metrics_df.to_csv(dose_metrics_file, index=False)
            bio_metrics_df.to_csv(bio_metrics_file, index=False)
            
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=4)
        
        # Trả về báo cáo
        result = {
            "summary": summary,
            "dose_metrics": dose_metrics_df,
            "bio_metrics": bio_metrics_df,
            "dvh_figures": dvh_figures
        }
        
        if output_dir:
            result["output_dir"] = output_dir
        
        return result
    
    def highlight_best_plan(self, mode: str = "auto") -> Dict[str, str]:
        """
        Đánh dấu kế hoạch tốt nhất dựa trên các tiêu chí khác nhau
        
        Args:
            mode: Chế độ đánh dấu ('auto', 'target', 'oar', hoặc 'balanced')
            
        Returns:
            Dictionary các tiêu chí và kế hoạch tốt nhất tương ứng
        """
        if not self.plans:
            self.logger.log_warning("Không có kế hoạch nào để so sánh")
            return {}
        
        # Lấy dữ liệu chỉ số
        dose_metrics_df = self.compare_dose_metrics()
        bio_metrics_df = self.compare_biological_metrics()
        
        best_plans = {}
        
        # Các cấu trúc PTV
        ptv_structures = [s for s in self.common_structures if "PTV" in s.upper()]
        
        # Các cấu trúc OAR
        oar_structures = [s for s in self.common_structures if "PTV" not in s.upper() and s.upper() != "BODY"]
        
        # Đánh giá dựa trên chỉ số đích
        if mode in ["auto", "target", "balanced"]:
            for structure in ptv_structures:
                # Lấy dữ liệu cho cấu trúc này
                structure_data = dose_metrics_df[dose_metrics_df["Structure"] == structure]
                
                if structure_data.empty:
                    continue
                
                # Chỉ số tương thích (CI)
                ci_columns = [col for col in structure_data.columns if "conformity_index" in col]
                if ci_columns:
                    ci_values = {col.split("_")[0]: structure_data[col].values[0] for col in ci_columns}
                    best_ci_plan = max(ci_values.items(), key=lambda x: x[1])[0]
                    best_plans[f"{structure}_conformity"] = best_ci_plan
                
                # Chỉ số đồng nhất (HI)
                hi_columns = [col for col in structure_data.columns if "homogeneity_index" in col]
                if hi_columns:
                    hi_values = {col.split("_")[0]: structure_data[col].values[0] for col in hi_columns}
                    best_hi_plan = min(hi_values.items(), key=lambda x: x[1])[0]
                    best_plans[f"{structure}_homogeneity"] = best_hi_plan
                
                # Độ bao phủ (V95)
                v95_columns = [col for col in structure_data.columns if "v95" in col]
                if v95_columns:
                    v95_values = {col.split("_")[0]: structure_data[col].values[0] for col in v95_columns}
                    best_v95_plan = max(v95_values.items(), key=lambda x: x[1])[0]
                    best_plans[f"{structure}_coverage"] = best_v95_plan
        
        # Đánh giá dựa trên chỉ số OAR
        if mode in ["auto", "oar", "balanced"]:
            for structure in oar_structures:
                # Lấy dữ liệu cho cấu trúc này
                structure_data = dose_metrics_df[dose_metrics_df["Structure"] == structure]
                
                if structure_data.empty:
                    continue
                
                # Liều trung bình
                mean_dose_columns = [col for col in structure_data.columns if "mean_dose" in col]
                if mean_dose_columns:
                    mean_dose_values = {col.split("_")[0]: structure_data[col].values[0] for col in mean_dose_columns}
                    best_mean_dose_plan = min(mean_dose_values.items(), key=lambda x: x[1])[0]
                    best_plans[f"{structure}_mean_dose"] = best_mean_dose_plan
                
                # Liều tối đa
                max_dose_columns = [col for col in structure_data.columns if "max_dose" in col]
                if max_dose_columns:
                    max_dose_values = {col.split("_")[0]: structure_data[col].values[0] for col in max_dose_columns}
                    best_max_dose_plan = min(max_dose_values.items(), key=lambda x: x[1])[0]
                    best_plans[f"{structure}_max_dose"] = best_max_dose_plan
                
                # Chỉ số sinh học NTCP
                bio_structure_data = bio_metrics_df[bio_metrics_df["Structure"] == structure]
                if not bio_structure_data.empty:
                    ntcp_columns = [col for col in bio_structure_data.columns if "ntcp" in col]
                    if ntcp_columns:
                        ntcp_values = {col.split("_")[0]: bio_structure_data[col].values[0] for col in ntcp_columns}
                        best_ntcp_plan = min(ntcp_values.items(), key=lambda x: x[1])[0]
                        best_plans[f"{structure}_ntcp"] = best_ntcp_plan
        
        # Đánh giá tổng thể
        if mode in ["auto", "balanced"]:
            # Đếm số lần mỗi kế hoạch được đánh giá là tốt nhất
            plan_counts = {}
            for plan_id in self.plans.keys():
                plan_counts[plan_id] = 0
            
            for metric, plan_id in best_plans.items():
                plan_counts[plan_id] += 1
            
            # Kế hoạch tổng thể tốt nhất
            if plan_counts:
                best_overall_plan = max(plan_counts.items(), key=lambda x: x[1])[0]
                best_plans["overall"] = best_overall_plan
        
        return best_plans

# Tạo instance mặc định
plan_comparison = PlanComparison() 