#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module kiểm tra chất lượng kế hoạch xạ trị (Plan QA) cho QuangStation V2.
Sử dụng phương pháp kiểm tra tự động dựa trên dữ liệu lịch sử (Knowledge-Based Planning).
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional, Any, Union
import pickle
import json
import logging
import datetime
import csv
from io import StringIO
import scipy.interpolate as interp

from quangstation.utils.logging import get_logger
from quangstation.utils.config import config, get_config
from quangstation.data_management.patient_db import PatientDatabase
from quangstation.plan_evaluation.dvh import DVHCalculator
from quangstation.optimization.goal_optimizer import OptimizationGoal
from quangstation.optimization.kbp_optimizer import KnowledgeBasedPlanningOptimizer

logger = get_logger(__name__)

class PlanQAResult:
    """
    Lớp lưu trữ kết quả của một kiểm tra kế hoạch.
    """
    def __init__(self, structure_name: str, metric_name: str, 
                 actual_value: float, predicted_value: float, 
                 lower_threshold: float, upper_threshold: float,
                 is_passed: bool, importance: int = 1):
        """
        Khởi tạo kết quả kiểm tra kế hoạch.
        
        Args:
            structure_name: Tên cấu trúc được kiểm tra
            metric_name: Tên chỉ số (ví dụ: D_mean, D_max, V20)
            actual_value: Giá trị thực tế trong kế hoạch hiện tại
            predicted_value: Giá trị dự đoán từ mô hình KBP
            lower_threshold: Ngưỡng dưới cho giá trị đạt yêu cầu
            upper_threshold: Ngưỡng trên cho giá trị đạt yêu cầu
            is_passed: Kết quả kiểm tra (True nếu giá trị thực tế nằm trong ngưỡng)
            importance: Độ quan trọng của kiểm tra (1-5, 5 là quan trọng nhất)
        """
        self.structure_name = structure_name
        self.metric_name = metric_name
        self.actual_value = actual_value
        self.predicted_value = predicted_value
        self.lower_threshold = lower_threshold
        self.upper_threshold = upper_threshold
        self.is_passed = is_passed
        self.importance = importance
        self.delta = actual_value - predicted_value
        self.delta_percent = (self.delta / predicted_value * 100) if predicted_value != 0 else 0
    
    def __str__(self) -> str:
        """Biểu diễn chuỗi của kết quả kiểm tra."""
        status = "✓" if self.is_passed else "✗"
        return (f"{status} {self.structure_name} - {self.metric_name}: "
                f"{self.actual_value:.2f} vs {self.predicted_value:.2f} "
                f"(Δ: {self.delta:.2f}, {self.delta_percent:.1f}%) "
                f"Ngưỡng: [{self.lower_threshold:.2f}, {self.upper_threshold:.2f}]")


class PlanQAModule:
    """
    Module kiểm tra chất lượng kế hoạch xạ trị tự động dựa trên KBP.
    """
    
    def __init__(self, model_path: Optional[str] = None, tolerance: float = 0.05):
        """
        Khởi tạo module kiểm tra kế hoạch.
        
        Args:
            model_path: Đường dẫn đến thư mục chứa mô hình KBP
            tolerance: Mức dung sai cho kiểm tra (% của giá trị dự đoán)
        """
        self.logger = get_logger("PlanQA")
        # Sửa cách lấy cấu hình
        self.config = config
        self.tolerance = tolerance
        self.db = PatientDatabase()
        
        # Khởi tạo bộ tối ưu hóa KBP
        self.kbp_optimizer = KnowledgeBasedPlanningOptimizer(model_path)
        
        # Khởi tạo bộ tính DVH
        self.dvh_calculator = DVHCalculator()
        
        # Danh sách các kết quả kiểm tra
        self.qa_results = []
        
        # Đường dẫn lưu báo cáo
        self.report_dir = os.path.join(
            self.config.get("app_data_dir", os.path.expanduser("~/.quangstation")),
            "reports", "plan_qa"
        )
        os.makedirs(self.report_dir, exist_ok=True)
    
    def check_plan(self, plan_data: Dict[str, Any], dose_data: np.ndarray, 
                  structures: Dict[str, np.ndarray], 
                  reference_plans: List[str] = None) -> List[PlanQAResult]:
        """
        Kiểm tra chất lượng kế hoạch xạ trị.
        
        Args:
            plan_data: Thông tin kế hoạch
            dose_data: Ma trận liều 3D
            structures: Dictionary chứa mặt nạ cấu trúc {tên: mặt nạ 3D}
            reference_plans: Danh sách ID kế hoạch tham khảo (nếu không có, sẽ sử dụng mô hình KBP)
            
        Returns:
            Danh sách kết quả kiểm tra
        """
        self.qa_results = []
        
        # Thiết lập dữ liệu liều và cấu trúc cho DVH
        self.dvh_calculator.set_dose_data(dose_data)
        for name, mask in structures.items():
            self.dvh_calculator.add_structure(name, mask)
        
        # Tính toán DVH cho tất cả các cấu trúc
        dvh_data = self.dvh_calculator.calculate_dvh_for_all()
        
        # Sử dụng mô hình KBP để dự đoán các chỉ số liều
        features = self.kbp_optimizer.extract_features(structures, plan_data)
        
        # Kiểm tra từng cấu trúc
        for structure_name, struct_mask in structures.items():
            # Bỏ qua các cấu trúc mục tiêu (PTV, CTV, GTV)
            if structure_name.startswith('PTV') or structure_name.startswith('CTV') or structure_name.startswith('GTV'):
                continue
            
            # Dự đoán chỉ số liều từ mô hình KBP
            predicted_metrics = self.kbp_optimizer.predict_dose_metrics(features, structure_name)
            
            # Nếu không có dự đoán từ mô hình, tiếp tục với cấu trúc khác
            if not predicted_metrics:
                self.logger.warning(f"Không có dự đoán cho cấu trúc {structure_name}")
                continue
            
            # Lấy dữ liệu DVH thực tế
            actual_dvh = dvh_data.get(structure_name, {})
            if not actual_dvh:
                self.logger.warning(f"Không có dữ liệu DVH cho cấu trúc {structure_name}")
                continue
            
            # Kiểm tra các chỉ số liều
            for metric_name, predicted_value in predicted_metrics.items():
                # Lấy giá trị thực tế từ DVH
                actual_value = self._get_actual_metric_value(actual_dvh, metric_name)
                
                if actual_value is None:
                    continue
                
                # Xác định ngưỡng dựa trên loại chỉ số và cấu trúc
                lower_threshold, upper_threshold = self._get_threshold(
                    structure_name, metric_name, predicted_value)
                
                # Kiểm tra xem giá trị thực tế có nằm trong ngưỡng không
                is_passed = lower_threshold <= actual_value <= upper_threshold
                
                # Xác định độ quan trọng dựa trên cấu trúc
                importance = self._get_structure_importance(structure_name)
                
                # Tạo kết quả kiểm tra
                result = PlanQAResult(
                    structure_name=structure_name,
                    metric_name=metric_name,
                    actual_value=actual_value,
                    predicted_value=predicted_value,
                    lower_threshold=lower_threshold,
                    upper_threshold=upper_threshold,
                    is_passed=is_passed,
                    importance=importance
                )
                
                # Thêm vào danh sách kết quả
                self.qa_results.append(result)
        
        # Sắp xếp kết quả theo mức độ quan trọng và trạng thái
        self.qa_results.sort(key=lambda x: (x.importance, not x.is_passed), reverse=True)
        
        return self.qa_results
    
    def _get_actual_metric_value(self, dvh_data: Dict, metric_name: str) -> Optional[float]:
        """
        Lấy giá trị thực tế của chỉ số từ dữ liệu DVH.
        
        Args:
            dvh_data: Dữ liệu DVH của cấu trúc
            metric_name: Tên chỉ số cần lấy giá trị
            
        Returns:
            Giá trị của chỉ số hoặc None nếu không tìm thấy
        """
        # Lấy giá trị liều trung bình
        if metric_name == 'D_mean':
            return dvh_data.get('mean_dose', None)
        
        # Lấy giá trị liều tối đa
        if metric_name == 'D_max':
            return dvh_data.get('max_dose', None)
        
        # Xử lý các chỉ số DX (liều nhận bởi X% thể tích)
        if metric_name.startswith('D') and '_' in metric_name:
            try:
                percent = float(metric_name.split('_')[1])
                # Tìm trong volume_metrics
                volume_metrics = dvh_data.get('volume_metrics', {})
                
                # Kiểm tra nếu đã có giá trị trong volume_metrics
                if f'D{percent}' in volume_metrics:
                    return volume_metrics[f'D{percent}']
                
                # Nếu không có, cần nội suy từ differential_dvh
                differential_dvh = dvh_data.get('differential_dvh', {})
                if differential_dvh:
                    doses = differential_dvh.get('dose', [])
                    volumes = differential_dvh.get('volume', [])
                    
                    if doses and volumes:
                        # Nội suy để tìm giá trị liều tại percent% thể tích
                        try:
                            # Tính toán thể tích tích lũy
                            cum_volumes = np.cumsum(volumes) / np.sum(volumes) * 100
                            
                            # Tạo hàm nội suy
                            f_interp = interp.interp1d(cum_volumes, doses, bounds_error=False, fill_value=(doses[0], doses[-1]))
                            
                            # Nội suy giá trị liều tại percent% thể tích
                            interpolated_dose = f_interp(percent)
                            
                            return interpolated_dose
                        except Exception as e:
                            self.logger.error(f"Lỗi khi nội suy D{percent}: {str(e)}")
                            pass
            except ValueError:
                pass
        
        # Xử lý các chỉ số VX (% thể tích nhận ít nhất X Gy)
        if metric_name.startswith('V') and '_' in metric_name:
            try:
                dose = float(metric_name.split('_')[1])
                # Tìm trong volume_metrics
                volume_metrics = dvh_data.get('volume_metrics', {})
                
                # Kiểm tra nếu đã có giá trị trong volume_metrics
                if f'V{dose}' in volume_metrics:
                    return volume_metrics[f'V{dose}']
                
                # Nếu không có, cần nội suy từ cumulative_dvh
                cumulative_dvh = dvh_data.get('cumulative_dvh', {})
                if cumulative_dvh:
                    doses = cumulative_dvh.get('dose', [])
                    volumes = cumulative_dvh.get('volume', [])
                    
                    if doses and volumes:
                        # Nội suy để tìm giá trị thể tích tại dose Gy
                        try:
                            # Tạo hàm nội suy
                            f_interp = interp.interp1d(doses, volumes, bounds_error=False, fill_value=(volumes[-1], volumes[0]))
                            
                            # Nội suy giá trị thể tích tại dose Gy
                            interpolated_volume = f_interp(dose)
                            
                            # Chuyển đổi thành phần trăm
                            volume_percent = (interpolated_volume / np.sum(volumes)) * 100
                            
                            return volume_percent
                        except Exception as e:
                            self.logger.error(f"Lỗi khi nội suy V{dose}: {str(e)}")
                            pass
            except ValueError:
                pass
        
        # Không tìm thấy chỉ số
        return None
    
    def _get_threshold(self, structure_name: str, metric_name: str, 
                      predicted_value: float) -> Tuple[float, float]:
        """
        Xác định ngưỡng cho kiểm tra dựa trên loại cấu trúc và chỉ số.
        
        Args:
            structure_name: Tên cấu trúc
            metric_name: Tên chỉ số
            predicted_value: Giá trị dự đoán
            
        Returns:
            Tuple chứa ngưỡng dưới và ngưỡng trên
        """
        # Xác định loại cấu trúc
        is_oar = not (structure_name.startswith('PTV') or 
                     structure_name.startswith('CTV') or 
                     structure_name.startswith('GTV'))
        
        # Điều chỉnh dung sai dựa trên loại cấu trúc và chỉ số
        if is_oar:
            # Đối với cơ quan nguy cấp (OAR)
            if metric_name in ['D_mean', 'D_max'] or metric_name.startswith('D'):
                # Ngưỡng dưới: không giới hạn (càng thấp càng tốt)
                # Ngưỡng trên: giá trị dự đoán + dung sai
                lower_threshold = -float('inf')
                upper_threshold = predicted_value * (1 + self.tolerance)
            else:  # VX
                # Ngưỡng dưới: không giới hạn (càng thấp càng tốt)
                # Ngưỡng trên: giá trị dự đoán + dung sai
                lower_threshold = -float('inf')
                upper_threshold = predicted_value * (1 + self.tolerance)
        else:
            # Đối với thể tích mục tiêu (PTV, CTV, GTV)
            if metric_name in ['D_mean', 'D_min'] or metric_name.startswith('D'):
                # Ngưỡng dưới: giá trị dự đoán - dung sai
                # Ngưỡng trên: không giới hạn (càng cao càng tốt)
                lower_threshold = predicted_value * (1 - self.tolerance)
                upper_threshold = float('inf')
            else:  # VX
                # Ngưỡng dưới: giá trị dự đoán - dung sai
                # Ngưỡng trên: không giới hạn (càng cao càng tốt)
                lower_threshold = predicted_value * (1 - self.tolerance)
                upper_threshold = float('inf')
        
        # Điều chỉnh ngưỡng dựa trên cấu trúc cụ thể
        if 'SpinalCord' in structure_name or 'BrainStem' in structure_name:
            # Cấu trúc quan trọng, dung sai thấp hơn
            tolerance_factor = self.tolerance * 0.5
            if is_oar:
                upper_threshold = predicted_value * (1 + tolerance_factor)
        
        return lower_threshold, upper_threshold
    
    def _get_structure_importance(self, structure_name: str) -> int:
        """
        Xác định độ quan trọng của cấu trúc (1-5, 5 là quan trọng nhất).
        
        Args:
            structure_name: Tên cấu trúc
            
        Returns:
            Độ quan trọng của cấu trúc
        """
        # Cấu trúc quan trọng nhất
        critical_organs = ['SpinalCord', 'BrainStem', 'OpticChiasm', 'OpticNerve', 'Lens']
        for organ in critical_organs:
            if organ in structure_name:
                return 5
        
        # Cấu trúc quan trọng bậc 2
        important_organs = ['Parotid', 'Larynx', 'Esophagus', 'Heart', 'Lung']
        for organ in important_organs:
            if organ in structure_name:
                return 4
        
        # Cấu trúc quan trọng bậc 3
        medium_organs = ['Cochlea', 'OralCavity', 'Mandible', 'Thyroid', 'Liver', 'Kidney']
        for organ in medium_organs:
            if organ in structure_name:
                return 3
        
        # Cấu trúc ít quan trọng hơn
        less_important_organs = ['Submandibular', 'Mastoid', 'Pituitary', 'Cerebellum']
        for organ in less_important_organs:
            if organ in structure_name:
                return 2
        
        # Cấu trúc ít quan trọng nhất
        return 1
    
    def generate_report(self, plan_name: str, output_format: str = 'pdf') -> str:
        """
        Tạo báo cáo kiểm tra kế hoạch.
        
        Args:
            plan_name: Tên kế hoạch
            output_format: Định dạng đầu ra ('pdf', 'html', 'csv')
            
        Returns:
            Đường dẫn đến file báo cáo
        """
        if not self.qa_results:
            self.logger.warning("Không có kết quả kiểm tra để tạo báo cáo")
            return None
        
        # Tạo đường dẫn đầu ra
        timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(self.report_dir, f"plan_qa_{plan_name}_{timestamp}")
        
        # Tạo báo cáo dựa trên định dạng
        if output_format == 'csv':
            return self._generate_csv_report(output_file + '.csv')
        elif output_format == 'html':
            return self._generate_html_report(output_file + '.html')
        elif output_format == 'pdf':
            return self._generate_pdf_report(output_file + '.pdf')
        else:
            self.logger.error(f"Định dạng báo cáo không được hỗ trợ: {output_format}")
            return None
    
    def _generate_csv_report(self, output_file: str) -> str:
        """
        Tạo báo cáo dạng CSV.
        
        Args:
            output_file: Đường dẫn đến file đầu ra
            
        Returns:
            Đường dẫn đến file báo cáo
        """
        try:
            # Tạo DataFrame từ kết quả
            data = []
            for result in self.qa_results:
                data.append({
                    'Structure': result.structure_name,
                    'Metric': result.metric_name,
                    'Actual': result.actual_value,
                    'Predicted': result.predicted_value,
                    'Delta': result.delta,
                    'Delta (%)': result.delta_percent,
                    'Lower Threshold': result.lower_threshold,
                    'Upper Threshold': result.upper_threshold,
                    'Passed': result.is_passed,
                    'Importance': result.importance
                })
            
            # Tạo DataFrame và lưu thành CSV
            df = pd.DataFrame(data)
            df.to_csv(output_file, index=False)
            
            self.logger.info(f"Đã tạo báo cáo CSV: {output_file}")
            return output_file
        except Exception as e:
            self.logger.error(f"Lỗi khi tạo báo cáo CSV: {str(e)}")
            return None
    
    def _generate_html_report(self, output_file: str) -> str:
        """
        Tạo báo cáo dạng HTML.
        
        Args:
            output_file: Đường dẫn đến file đầu ra
            
        Returns:
            Đường dẫn đến file báo cáo
        """
        try:
            # Tạo DataFrame từ kết quả
            data = []
            for result in self.qa_results:
                data.append({
                    'Structure': result.structure_name,
                    'Metric': result.metric_name,
                    'Actual': f"{result.actual_value:.2f}",
                    'Predicted': f"{result.predicted_value:.2f}",
                    'Delta': f"{result.delta:.2f}",
                    'Delta (%)': f"{result.delta_percent:.1f}%",
                    'Thresholds': f"[{result.lower_threshold:.2f}, {result.upper_threshold:.2f}]",
                    'Status': '✓' if result.is_passed else '✗'
                })
            
            # Tạo DataFrame
            df = pd.DataFrame(data)
            
            # Tạo HTML với kiểu dáng
            html_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Plan QA Report</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    h1 { color: #2c3e50; }
                    table { border-collapse: collapse; width: 100%; margin-top: 20px; }
                    th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
                    th { background-color: #3498db; color: white; }
                    tr:nth-child(even) { background-color: #f2f2f2; }
                    .pass { color: green; font-weight: bold; }
                    .fail { color: red; font-weight: bold; }
                    .summary { margin-top: 20px; padding: 10px; border: 1px solid #ddd; background-color: #f8f9fa; }
                </style>
            </head>
            <body>
                <h1>Plan QA Report</h1>
                <div class="summary">
                    <h3>Summary</h3>
                    <p>Total checks: {total_checks}</p>
                    <p>Passed: {passed_checks} ({pass_percent:.1f}%)</p>
                    <p>Failed: {failed_checks} ({fail_percent:.1f}%)</p>
                </div>
                {table}
            </body>
            </html>
            """
            
            # Tính tổng kết
            total_checks = len(self.qa_results)
            passed_checks = sum(1 for result in self.qa_results if result.is_passed)
            failed_checks = total_checks - passed_checks
            pass_percent = (passed_checks / total_checks * 100) if total_checks > 0 else 0
            fail_percent = (failed_checks / total_checks * 100) if total_checks > 0 else 0
            
            # Tạo HTML cho bảng với kiểu đánh dấu trạng thái
            table_html = df.to_html(index=False, escape=False)
            table_html = table_html.replace('>✓<', ' class="pass">✓<').replace('>✗<', ' class="fail">✗<')
            
            # Thay thế các giá trị vào template
            html_content = html_template.format(
                total_checks=total_checks,
                passed_checks=passed_checks,
                failed_checks=failed_checks,
                pass_percent=pass_percent,
                fail_percent=fail_percent,
                table=table_html
            )
            
            # Lưu HTML vào file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.info(f"Đã tạo báo cáo HTML: {output_file}")
            return output_file
        except Exception as e:
            self.logger.error(f"Lỗi khi tạo báo cáo HTML: {str(e)}")
            return None
    
    def _generate_pdf_report(self, output_file: str) -> str:
        """
        Tạo báo cáo dạng PDF.
        
        Args:
            output_file: Đường dẫn đến file đầu ra
            
        Returns:
            Đường dẫn đến file báo cáo
        """
        try:
            # Tạo báo cáo HTML trước
            html_file = output_file.replace('.pdf', '.html')
            self._generate_html_report(html_file)
            
            # Chuyển đổi HTML sang PDF
            try:
                import weasyprint
                from weasyprint import HTML
                
                # Tạo PDF từ HTML
                HTML(html_file).write_pdf(output_file)
                
                # Xóa file HTML tạm
                os.remove(html_file)
                
                self.logger.info(f"Đã tạo báo cáo PDF: {output_file}")
                return output_file
            except ImportError:
                self.logger.warning("Thư viện weasyprint không được cài đặt. Sử dụng báo cáo HTML thay thế.")
                return html_file
        except Exception as e:
            self.logger.error(f"Lỗi khi tạo báo cáo PDF: {str(e)}")
            return None
    
    def visualize_results(self, display=True, save_path=None):
        """
        Tạo biểu đồ trực quan hóa kết quả kiểm tra.
        
        Args:
            display: Hiển thị biểu đồ
            save_path: Đường dẫn để lưu biểu đồ
            
        Returns:
            Figure matplotlib
        """
        if not self.qa_results:
            self.logger.warning("Không có kết quả kiểm tra để trực quan hóa")
            return None
        
        # Tạo DataFrame cho trực quan hóa
        data = []
        for result in self.qa_results:
            data.append({
                'Structure': result.structure_name,
                'Metric': result.metric_name,
                'Actual': result.actual_value,
                'Predicted': result.predicted_value,
                'Delta (%)': result.delta_percent,
                'Passed': result.is_passed
            })
        
        df = pd.DataFrame(data)
        
        # Tính tổng kết
        total_checks = len(self.qa_results)
        passed_checks = sum(1 for result in self.qa_results if result.is_passed)
        failed_checks = total_checks - passed_checks
        
        # Tạo biểu đồ
        fig, axs = plt.subplots(2, 1, figsize=(12, 10))
        
        # Biểu đồ 1: Số lượng kiểm tra đạt/không đạt
        axs[0].bar(['Passed', 'Failed'], [passed_checks, failed_checks], 
                 color=['green', 'red'])
        axs[0].set_title('Plan QA Results Summary')
        axs[0].set_ylabel('Number of checks')
        
        # Biểu đồ 2: Delta % cho mỗi cấu trúc
        structures = df['Structure'].unique()
        
        # Lấy delta cho mỗi cấu trúc
        structure_deltas = []
        for structure in structures:
            struct_df = df[df['Structure'] == structure]
            avg_delta = struct_df['Delta (%)'].mean()
            structure_deltas.append((structure, avg_delta))
        
        # Sắp xếp theo delta giảm dần
        structure_deltas.sort(key=lambda x: abs(x[1]), reverse=True)
        
        # Lấy 10 cấu trúc có delta lớn nhất
        top_structures = structure_deltas[:10]
        
        # Tạo biểu đồ
        s_names = [s[0] for s in top_structures]
        s_deltas = [s[1] for s in top_structures]
        colors = ['red' if d > 0 else 'green' for d in s_deltas]
        
        axs[1].bar(s_names, s_deltas, color=colors)
        axs[1].set_title('Average Delta (%) by Structure')
        axs[1].set_ylabel('Delta (%)')
        axs[1].set_xlabel('Structure')
        axs[1].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        # Lưu biểu đồ nếu cần
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        # Hiển thị biểu đồ nếu cần
        if display:
            plt.show()
        
        return fig


# Instance mặc định
plan_qa = PlanQAModule() 