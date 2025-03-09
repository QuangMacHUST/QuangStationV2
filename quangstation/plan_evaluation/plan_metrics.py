#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module đánh giá chỉ số chất lượng kế hoạch xạ trị cho QuangStation V2.
Cung cấp các phương pháp đánh giá toàn diện cho kế hoạch, bao gồm các chỉ số độ tuân thủ,
độ đồng nhất, độ che chắn, gradient index, và các chỉ số khác.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union
import pandas as pd
import matplotlib.pyplot as plt

from quangstation.utils.logging import get_logger
from quangstation.plan_evaluation.dvh import calculate_dvh

logger = get_logger(__name__)

class PlanQualityMetrics:
    """
    Lớp đánh giá chỉ số chất lượng kế hoạch xạ trị.
    """
    
    def __init__(self, dose_matrix: np.ndarray, structures: Dict[str, np.ndarray], 
                 prescribed_dose: float, target_name: str):
        """
        Khởi tạo với dữ liệu từ kế hoạch
        
        Args:
            dose_matrix: Ma trận liều 3D
            structures: Từ điển chứa các cấu trúc (name: mask)
            prescribed_dose: Liều kê toa (Gy)
            target_name: Tên cấu trúc đích (PTV)
        """
        self.dose_matrix = dose_matrix
        self.structures = structures
        self.prescribed_dose = prescribed_dose
        self.target_name = target_name
        
        # Kiểm tra xem cấu trúc đích có tồn tại không
        if target_name not in structures:
            logger.error(f"Cấu trúc đích {target_name} không tồn tại trong dữ liệu!")
            raise ValueError(f"Cấu trúc đích {target_name} không tồn tại!")
        
        # Tính DVH cho tất cả các cấu trúc
        self.dvh_data = {}
        for name, struct_mask in structures.items():
            struct_dose = dose_matrix * struct_mask
            doses_in_structure = struct_dose[struct_mask > 0]
            if doses_in_structure.size > 0:
                dvh = calculate_dvh(doses_in_structure, name)
                self.dvh_data[name] = dvh
        
        logger.info(f"Đã khởi tạo đánh giá chất lượng cho kế hoạch với liều {prescribed_dose}Gy")
    
    def calculate_conformity_index(self) -> float:
        """
        Tính chỉ số tuân thủ (Conformity Index - CI)
        CI = V95% / V_PTV, trong đó V95% là thể tích nhận 95% liều kê toa
        
        Returns:
            Giá trị chỉ số tuân thủ
        """
        if self.target_name not in self.dvh_data:
            logger.error(f"Không có dữ liệu DVH cho cấu trúc đích {self.target_name}!")
            return 0.0
        
        # Tính thể tích nhận 95% liều kê toa
        ref_dose = 0.95 * self.prescribed_dose
        dose_95_volume = 0.0
        target_volume = 0.0
        
        # Tìm tất cả các voxel nhận ít nhất 95% liều kê toa
        dose_95_mask = self.dose_matrix >= ref_dose
        dose_95_volume = np.sum(dose_95_mask)
        
        # Thể tích PTV
        target_volume = np.sum(self.structures[self.target_name])
        
        if target_volume == 0:
            logger.warning("Thể tích đích bằng 0, không thể tính chỉ số tuân thủ!")
            return 0.0
        
        ci = dose_95_volume / target_volume
        logger.info(f"Chỉ số tuân thủ (CI): {ci:.3f}")
        return ci
    
    def calculate_paddick_ci(self) -> float:
        """
        Tính chỉ số tuân thủ Paddick (Paddick Conformity Index)
        Paddick CI = (TV_PIV)² / (TV × PIV)
        TV_PIV: thể tích đích nhận liều kê toa
        TV: thể tích đích
        PIV: thể tích nhận liều kê toa
        
        Returns:
            Giá trị chỉ số tuân thủ Paddick
        """
        # Thể tích đích
        target_mask = self.structures[self.target_name]
        target_volume = np.sum(target_mask)
        
        # Thể tích nhận liều kê toa (PIV)
        piv_mask = self.dose_matrix >= self.prescribed_dose
        piv_volume = np.sum(piv_mask)
        
        # Thể tích đích nhận liều kê toa (TV_PIV)
        tv_piv_mask = np.logical_and(target_mask, piv_mask)
        tv_piv_volume = np.sum(tv_piv_mask)
        
        if target_volume == 0 or piv_volume == 0:
            logger.warning("Thể tích đích hoặc PIV bằng 0, không thể tính Paddick CI!")
            return 0.0
        
        paddick_ci = (tv_piv_volume ** 2) / (target_volume * piv_volume)
        logger.info(f"Chỉ số tuân thủ Paddick: {paddick_ci:.3f}")
        return paddick_ci
    
    def calculate_gradient_index(self) -> float:
        """
        Tính chỉ số độ dốc (Gradient Index)
        GI = V50% / V100%, trong đó V50% là thể tích nhận 50% liều kê toa
        
        Returns:
            Giá trị chỉ số độ dốc
        """
        # Tính thể tích nhận 50% và 100% liều kê toa
        v50_mask = self.dose_matrix >= (0.5 * self.prescribed_dose)
        v100_mask = self.dose_matrix >= self.prescribed_dose
        
        v50_volume = np.sum(v50_mask)
        v100_volume = np.sum(v100_mask)
        
        if v100_volume == 0:
            logger.warning("Thể tích nhận 100% liều bằng 0, không thể tính GI!")
            return 0.0
        
        gi = v50_volume / v100_volume
        logger.info(f"Chỉ số độ dốc (GI): {gi:.3f}")
        return gi
    
    def calculate_homogeneity_index(self) -> float:
        """
        Tính chỉ số đồng nhất (Homogeneity Index)
        HI = (D2% - D98%) / D50%
        
        Returns:
            Giá trị chỉ số đồng nhất (lý tưởng là gần 0)
        """
        if self.target_name not in self.dvh_data:
            logger.error(f"Không có dữ liệu DVH cho cấu trúc đích {self.target_name}!")
            return 0.0
        
        # Lấy dữ liệu liều từ DVH
        dvh = self.dvh_data[self.target_name]
        
        # Chức năng trích xuất liều tại % thể tích, nội suy từ DVH
        def get_dose_at_volume_percent(dvh_data, volume_percent):
            for vol, dose in zip(dvh_data['volumePercent'], dvh_data['dose']):
                if vol <= volume_percent:
                    return dose
            return 0.0
        
        # Trích xuất D2%, D50%, D98%
        d2 = get_dose_at_volume_percent(dvh, 2)
        d50 = get_dose_at_volume_percent(dvh, 50)
        d98 = get_dose_at_volume_percent(dvh, 98)
        
        if d50 == 0:
            logger.warning("D50% bằng 0, không thể tính HI!")
            return 0.0
        
        hi = (d2 - d98) / d50
        logger.info(f"Chỉ số đồng nhất (HI): {hi:.3f}")
        return hi
    
    def calculate_target_coverage(self) -> float:
        """
        Tính độ bao phủ đích (TC - Target Coverage)
        TC = V95% / V_PTV, trong đó V95% là thể tích PTV nhận 95% liều kê toa
        
        Returns:
            Độ bao phủ đích (0-1)
        """
        # Tính thể tích đích
        target_mask = self.structures[self.target_name]
        target_volume = np.sum(target_mask)
        
        # Tính thể tích đích nhận 95% liều kê toa
        ref_dose = 0.95 * self.prescribed_dose
        target_dose = self.dose_matrix * target_mask
        target_95_mask = target_dose >= ref_dose
        target_95_volume = np.sum(target_95_mask)
        
        if target_volume == 0:
            logger.warning("Thể tích đích bằng 0, không thể tính độ bao phủ!")
            return 0.0
        
        tc = target_95_volume / target_volume
        logger.info(f"Độ bao phủ đích (TC): {tc:.3f}")
        return tc
    
    def calculate_oar_sparing_metrics(self, oar_constraints: Dict[str, Dict]) -> Dict[str, float]:
        """
        Tính toán các chỉ số bảo vệ cơ quan nguy cấp
        
        Args:
            oar_constraints: Từ điển các ràng buộc cơ quan nguy cấp
                           {organ_name: {constraint_type: value}}
        
        Returns:
            Từ điển các chỉ số bảo vệ theo cơ quan
        """
        oar_metrics = {}
        
        for organ, constraints in oar_constraints.items():
            if organ not in self.structures:
                logger.warning(f"Cơ quan {organ} không tồn tại trong dữ liệu!")
                continue
            
            # Tính các chỉ số bảo vệ cho từng cơ quan
            organ_mask = self.structures[organ]
            organ_dose = self.dose_matrix * organ_mask
            organ_dose = organ_dose[organ_mask > 0]  # Chỉ lấy các voxel trong cơ quan
            
            if len(organ_dose) == 0:
                logger.warning(f"Không có dữ liệu liều cho cơ quan {organ}!")
                continue
            
            organ_metrics = {}
            
            # Liều tối đa
            organ_metrics['max_dose'] = np.max(organ_dose)
            
            # Liều trung bình
            organ_metrics['mean_dose'] = np.mean(organ_dose)
            
            # Kiểm tra ràng buộc
            oar_status = True
            for constraint_type, constraint_value in constraints.items():
                if constraint_type == 'max_dose':
                    if organ_metrics['max_dose'] > constraint_value:
                        oar_status = False
                elif constraint_type == 'mean_dose':
                    if organ_metrics['mean_dose'] > constraint_value:
                        oar_status = False
                # Có thể thêm nhiều loại ràng buộc khác
            
            organ_metrics['constraint_met'] = oar_status
            oar_metrics[organ] = organ_metrics
        
        return oar_metrics
    
    def calculate_all_metrics(self) -> Dict[str, Any]:
        """
        Tính toán tất cả các chỉ số chất lượng kế hoạch
        
        Returns:
            Từ điển chứa tất cả các chỉ số
        """
        metrics = {}
        
        # Các chỉ số đích
        metrics['conformity_index'] = self.calculate_conformity_index()
        metrics['paddick_ci'] = self.calculate_paddick_ci()
        metrics['homogeneity_index'] = self.calculate_homogeneity_index()
        metrics['gradient_index'] = self.calculate_gradient_index()
        metrics['target_coverage'] = self.calculate_target_coverage()
        
        # Thêm các thông tin tổng hợp
        if self.target_name in self.dvh_data:
            dvh = self.dvh_data[self.target_name]
            metrics['target_min_dose'] = dvh.get('min', 0)
            metrics['target_max_dose'] = dvh.get('max', 0)
            metrics['target_mean_dose'] = dvh.get('mean', 0)
            metrics['target_d95'] = dvh.get('d95', 0)
        
        logger.info(f"Đã tính toán {len(metrics)} chỉ số chất lượng kế hoạch")
        return metrics
    
    def generate_quality_report(self, output_file: str = None) -> pd.DataFrame:
        """
        Tạo báo cáo chất lượng kế hoạch chi tiết
        
        Args:
            output_file: Đường dẫn đến file xuất báo cáo (tùy chọn)
        
        Returns:
            DataFrame chứa các chỉ số chất lượng
        """
        metrics = self.calculate_all_metrics()
        
        # Tạo DataFrame từ metrics
        metrics_df = pd.DataFrame([metrics])
        
        # Thêm các thông tin bổ sung
        metrics_df['target_name'] = self.target_name
        metrics_df['prescribed_dose'] = self.prescribed_dose
        metrics_df['evaluation_time'] = pd.Timestamp.now()
        
        # Xuất sang file nếu được yêu cầu
        if output_file:
            if output_file.endswith('.csv'):
                metrics_df.to_csv(output_file, index=False)
            elif output_file.endswith('.xlsx'):
                metrics_df.to_excel(output_file, index=False)
            else:
                # Mặc định là CSV
                metrics_df.to_csv(output_file + '.csv', index=False)
            
            logger.info(f"Đã xuất báo cáo chất lượng sang {output_file}")
        
        return metrics_df
    
    def plot_quality_radar(self, ax=None, min_values=None, max_values=None) -> plt.Figure:
        """
        Vẽ biểu đồ radar cho các chỉ số chất lượng kế hoạch
        
        Args:
            ax: trục matplotlib (tùy chọn)
            min_values: giá trị tối thiểu cho các chỉ số (để chuẩn hóa)
            max_values: giá trị tối đa cho các chỉ số (để chuẩn hóa)
        
        Returns:
            Đối tượng Figure của matplotlib
        """
        metrics = self.calculate_all_metrics()
        
        # Chọn các chỉ số chính để hiển thị trên biểu đồ radar
        selected_metrics = {
            'CI': metrics['conformity_index'],
            'HI': 1 - metrics['homogeneity_index'],  # Đảo ngược để cao hơn = tốt hơn
            'TC': metrics['target_coverage'],
            'GI': 1 / metrics['gradient_index'],  # Đảo ngược để cao hơn = tốt hơn
            'Paddick CI': metrics['paddick_ci']
        }
        
        # Chuẩn hóa giá trị (0-1)
        if min_values is None:
            min_values = {'CI': 0, 'HI': 0, 'TC': 0, 'GI': 0, 'Paddick CI': 0}
        
        if max_values is None:
            max_values = {'CI': 1.5, 'HI': 1, 'TC': 1, 'GI': 0.5, 'Paddick CI': 1}
        
        # Chuẩn hóa
        normalized_metrics = {}
        for key, value in selected_metrics.items():
            min_val = min_values.get(key, 0)
            max_val = max_values.get(key, 1)
            normalized_metrics[key] = (value - min_val) / (max_val - min_val)
            # Giới hạn trong khoảng [0, 1]
            normalized_metrics[key] = max(0, min(1, normalized_metrics[key]))
        
        # Tạo biểu đồ radar
        if ax is None:
            fig = plt.figure(figsize=(10, 8))
            ax = fig.add_subplot(111, polar=True)
        else:
            fig = ax.figure
        
        # Số lượng biến
        categories = list(normalized_metrics.keys())
        N = len(categories)
        
        # Góc cho mỗi trục
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]  # Đóng đường đa giác
        
        # Giá trị cho mỗi trục
        values = list(normalized_metrics.values())
        values += values[:1]  # Đóng đường đa giác
        
        # Vẽ biểu đồ
        ax.plot(angles, values, linewidth=2, linestyle='solid', label=self.target_name)
        ax.fill(angles, values, alpha=0.1)
        
        # Thiết lập trục
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories)
        
        # Tùy chỉnh biểu đồ
        ax.set_yticks([0.25, 0.5, 0.75, 1.0])
        ax.set_yticklabels(["0.25", "0.5", "0.75", "1.0"])
        ax.set_ylim(0, 1)
        
        # Thêm tiêu đề
        plt.title('Biểu đồ chỉ số chất lượng kế hoạch', size=15, y=1.1)
        plt.tight_layout()
        
        return fig
    
    def compare_with_other_plan(self, other_metrics: Dict[str, float], labels: List[str] = None) -> plt.Figure:
        """
        So sánh chỉ số chất lượng với kế hoạch khác
        
        Args:
            other_metrics: Từ điển chỉ số chất lượng của kế hoạch khác
            labels: Nhãn cho các kế hoạch
        
        Returns:
            Biểu đồ so sánh
        """
        # Tính toán chỉ số của kế hoạch hiện tại
        current_metrics = self.calculate_all_metrics()
        
        # Chọn các chỉ số để so sánh
        metrics_to_compare = ['conformity_index', 'paddick_ci', 'homogeneity_index', 
                              'gradient_index', 'target_coverage']
        
        # Chuẩn bị dữ liệu cho biểu đồ
        metrics_data = []
        
        for metric in metrics_to_compare:
            current_value = current_metrics.get(metric, 0)
            other_value = other_metrics.get(metric, 0)
            metrics_data.append({'Metric': metric, 'Current Plan': current_value, 'Other Plan': other_value})
        
        # Chuyển thành DataFrame
        df = pd.DataFrame(metrics_data)
        
        # Vẽ biểu đồ
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Vị trí thanh trên trục x
        x = np.arange(len(metrics_to_compare))
        width = 0.35
        
        # Vẽ các thanh
        rects1 = ax.bar(x - width/2, df['Current Plan'], width, label='Current Plan' if labels is None else labels[0])
        rects2 = ax.bar(x + width/2, df['Other Plan'], width, label='Other Plan' if labels is None else labels[1])
        
        # Thêm nhãn, tiêu đề và chú thích
        ax.set_ylabel('Value')
        ax.set_title('So sánh chỉ số chất lượng kế hoạch')
        ax.set_xticks(x)
        ax.set_xticklabels(metrics_to_compare)
        ax.legend()
        
        # Thêm giá trị trên mỗi thanh
        def autolabel(rects):
            for rect in rects:
                height = rect.get_height()
                ax.annotate(f'{height:.2f}',
                           xy=(rect.get_x() + rect.get_width()/2, height),
                           xytext=(0, 3),  # Vị trí text so với thanh
                           textcoords="offset points",
                           ha='center', va='bottom')
        
        autolabel(rects1)
        autolabel(rects2)
        
        plt.tight_layout()
        return fig
    
    def save_metrics_to_json(self, file_path: str):
        """
        Lưu các chỉ số chất lượng sang file JSON
        
        Args:
            file_path: Đường dẫn đến file JSON
        """
        import json
        
        metrics = self.calculate_all_metrics()
        
        # Thêm các thông tin bổ sung
        metrics['target_name'] = self.target_name
        metrics['prescribed_dose'] = float(self.prescribed_dose)
        metrics['evaluation_time'] = str(pd.Timestamp.now())
        
        # Chuyển đổi các giá trị numpy sang Python native types
        for key, value in metrics.items():
            if isinstance(value, np.ndarray):
                metrics[key] = value.tolist()
            elif isinstance(value, np.generic):
                metrics[key] = value.item()
        
        # Lưu sang file JSON
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=4)
        
        logger.info(f"Đã lưu các chỉ số chất lượng sang {file_path}")

# Hàm tiện ích để tạo đối tượng PlanQualityMetrics từ kế hoạch
def evaluate_plan_quality(dose_matrix: np.ndarray, structures: Dict[str, np.ndarray],
                         prescribed_dose: float, target_name: str) -> PlanQualityMetrics:
    """
    Đánh giá chất lượng kế hoạch xạ trị
    
    Args:
        dose_matrix: Ma trận liều 3D
        structures: Từ điển các cấu trúc
        prescribed_dose: Liều kê toa (Gy)
        target_name: Tên cấu trúc đích
    
    Returns:
        Đối tượng PlanQualityMetrics
    """
    return PlanQualityMetrics(dose_matrix, structures, prescribed_dose, target_name) 