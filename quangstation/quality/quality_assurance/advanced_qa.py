#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module cung cấp các tính năng QA nâng cao cho QuangStation V2.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional, Union, Any
import json
import pandas as pd
from scipy.ndimage import gaussian_filter
from scipy.interpolate import RegularGridInterpolator
import datetime

from quangstation.core.utils.logging import get_logger
from quangstation.clinical.plan_evaluation.dvh import DVHCalculator
from quangstation.clinical.plan_evaluation.plan_metrics import PlanMetrics

logger = get_logger(__name__)

class AdvancedQA:
    """
    Lớp cung cấp các tính năng QA nâng cao cho hệ thống xạ trị.
    """
    
    def __init__(self, patient_id: str = None, plan_id: str = None, db = None):
        """
        Khởi tạo đối tượng AdvancedQA.
        
        Args:
            patient_id: ID của bệnh nhân
            plan_id: ID của kế hoạch
            db: Đối tượng cơ sở dữ liệu
        """
        self.patient_id = patient_id
        self.plan_id = plan_id
        self.db = db
        self.patient_data = None
        self.plan_data = None
        self.measured_data = None
        self.calculated_data = None
        
        # Tải dữ liệu nếu có
        if patient_id and plan_id and db:
            self.load_data()
    
    def load_data(self):
        """Tải dữ liệu bệnh nhân và kế hoạch từ cơ sở dữ liệu."""
        if not self.db:
            logger.error("Không có kết nối cơ sở dữ liệu.")
            return False
            
        try:
            # Tải thông tin bệnh nhân
            self.patient_data = self.db.get_patient(self.patient_id)
            if not self.patient_data:
                logger.error(f"Không tìm thấy bệnh nhân với ID: {self.patient_id}")
                return False
                
            # Tải thông tin kế hoạch
            if self.plan_id in self.patient_data.plans:
                self.plan_data = self.patient_data.plans[self.plan_id]
                logger.info(f"Đã tải kế hoạch {self.plan_id} cho bệnh nhân {self.patient_id}")
                return True
            else:
                logger.error(f"Không tìm thấy kế hoạch {self.plan_id} cho bệnh nhân {self.patient_id}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu: {str(e)}")
            return False
    
    def import_measured_data(self, file_path: str, data_format: str = 'csv'):
        """
        Nhập dữ liệu đo đạc từ file.
        
        Args:
            file_path: Đường dẫn đến file dữ liệu
            data_format: Định dạng dữ liệu ('csv', 'dicom', 'txt')
            
        Returns:
            bool: True nếu nhập thành công, False nếu thất bại
        """
        try:
            if data_format.lower() == 'csv':
                self.measured_data = pd.read_csv(file_path)
            elif data_format.lower() == 'txt':
                self.measured_data = pd.read_csv(file_path, delimiter='\t')
            elif data_format.lower() == 'dicom':
                # Xử lý file DICOM
                from pydicom import dcmread
                ds = dcmread(file_path)
                # Chuyển đổi dữ liệu DICOM thành định dạng phù hợp
                # Đây là một ví dụ đơn giản, cần điều chỉnh tùy theo cấu trúc DICOM cụ thể
                if hasattr(ds, 'pixel_array'):
                    self.measured_data = {
                        'dose_matrix': ds.pixel_array,
                        'metadata': {
                            'dose_grid_scaling': getattr(ds, 'DoseGridScaling', 1.0),
                            'pixel_spacing': getattr(ds, 'PixelSpacing', [1.0, 1.0]),
                            'slice_thickness': getattr(ds, 'SliceThickness', 1.0)
                        }
                    }
                else:
                    logger.error("File DICOM không chứa dữ liệu pixel.")
                    return False
            else:
                logger.error(f"Định dạng dữ liệu không được hỗ trợ: {data_format}")
                return False
                
            logger.info(f"Đã nhập dữ liệu đo đạc từ {file_path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi nhập dữ liệu đo đạc: {str(e)}")
            return False
    
    def calculate_gamma_index(self, 
                             dose_criteria_percent: float = 3.0, 
                             distance_criteria_mm: float = 3.0,
                             threshold_percent: float = 10.0,
                             global_normalization: bool = True) -> Dict[str, Any]:
        """
        Tính toán chỉ số Gamma giữa liều tính toán và liều đo đạc.
        
        Args:
            dose_criteria_percent: Tiêu chí sai khác liều (% của liều tối đa)
            distance_criteria_mm: Tiêu chí khoảng cách (mm)
            threshold_percent: Ngưỡng liều để tính Gamma (% của liều tối đa)
            global_normalization: Sử dụng chuẩn hóa toàn cục (True) hoặc cục bộ (False)
            
        Returns:
            Dict: Kết quả phân tích Gamma
        """
        if self.calculated_data is None or self.measured_data is None:
            logger.error("Thiếu dữ liệu liều tính toán hoặc đo đạc.")
            return None
            
        try:
            # Trích xuất dữ liệu liều
            calc_dose = self.calculated_data['dose_matrix']
            meas_dose = self.measured_data['dose_matrix']
            
            # Đảm bảo hai ma trận có cùng kích thước
            if calc_dose.shape != meas_dose.shape:
                logger.warning("Kích thước ma trận liều khác nhau. Đang nội suy...")
                # Nội suy ma trận liều đo đạc về cùng kích thước với ma trận tính toán
                meas_dose = self._interpolate_dose(meas_dose, calc_dose.shape)
            
            # Chuẩn hóa liều
            if global_normalization:
                calc_max = np.max(calc_dose)
                meas_max = np.max(meas_dose)
            else:
                calc_max = 1.0
                meas_max = 1.0
                
            norm_calc_dose = calc_dose / calc_max * 100.0
            norm_meas_dose = meas_dose / meas_max * 100.0
            
            # Tạo mask cho vùng trên ngưỡng
            threshold = threshold_percent
            mask = norm_calc_dose >= threshold
            
            # Tính toán chỉ số Gamma
            gamma_map = np.zeros_like(calc_dose)
            gamma_map.fill(np.inf)
            
            # Lấy thông tin khoảng cách giữa các điểm
            pixel_spacing = self.calculated_data['metadata']['pixel_spacing']
            slice_thickness = self.calculated_data['metadata']['slice_thickness']
            
            # Tính toán Gamma cho từng điểm
            for i in range(calc_dose.shape[0]):
                for j in range(calc_dose.shape[1]):
                    for k in range(calc_dose.shape[2]):
                        if mask[i, j, k]:
                            gamma_map[i, j, k] = self._calculate_gamma_at_point(
                                norm_calc_dose, norm_meas_dose, 
                                i, j, k, 
                                dose_criteria_percent, 
                                distance_criteria_mm,
                                pixel_spacing, slice_thickness
                            )
            
            # Tính tỷ lệ điểm vượt qua (gamma <= 1.0)
            gamma_pass_rate = np.sum(gamma_map[mask] <= 1.0) / np.sum(mask) * 100.0
            
            # Kết quả
            result = {
                'gamma_map': gamma_map,
                'pass_rate': gamma_pass_rate,
                'mean_gamma': np.mean(gamma_map[mask]),
                'max_gamma': np.max(gamma_map[mask]),
                'dose_criteria': dose_criteria_percent,
                'distance_criteria': distance_criteria_mm,
                'threshold': threshold_percent,
                'global_normalization': global_normalization
            }
            
            logger.info(f"Tỷ lệ vượt qua Gamma: {gamma_pass_rate:.2f}%")
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi tính toán chỉ số Gamma: {str(e)}")
            return None
    
    def _calculate_gamma_at_point(self, 
                                 calc_dose: np.ndarray, 
                                 meas_dose: np.ndarray,
                                 i: int, j: int, k: int,
                                 dose_criteria: float,
                                 distance_criteria: float,
                                 pixel_spacing: List[float],
                                 slice_thickness: float) -> float:
        """
        Tính toán chỉ số Gamma tại một điểm.
        
        Args:
            calc_dose: Ma trận liều tính toán
            meas_dose: Ma trận liều đo đạc
            i, j, k: Tọa độ điểm
            dose_criteria: Tiêu chí sai khác liều (%)
            distance_criteria: Tiêu chí khoảng cách (mm)
            pixel_spacing: Khoảng cách giữa các pixel [dx, dy]
            slice_thickness: Độ dày lát cắt (dz)
            
        Returns:
            float: Giá trị Gamma tại điểm
        """
        # Giá trị liều tại điểm tính toán
        calc_dose_value = calc_dose[i, j, k]
        
        # Tìm giá trị Gamma nhỏ nhất
        min_gamma = np.inf
        
        # Giới hạn vùng tìm kiếm để tối ưu hóa
        search_distance = 3 * distance_criteria  # mm
        
        # Chuyển đổi khoảng cách tìm kiếm sang số lượng voxel
        di_max = int(search_distance / slice_thickness) + 1
        dj_max = int(search_distance / pixel_spacing[0]) + 1
        dk_max = int(search_distance / pixel_spacing[1]) + 1
        
        # Giới hạn vùng tìm kiếm trong phạm vi ma trận
        i_min = max(0, i - di_max)
        i_max = min(calc_dose.shape[0] - 1, i + di_max)
        j_min = max(0, j - dj_max)
        j_max = min(calc_dose.shape[1] - 1, j + dj_max)
        k_min = max(0, k - dk_max)
        k_max = min(calc_dose.shape[2] - 1, k + dk_max)
        
        # Tìm giá trị Gamma nhỏ nhất trong vùng tìm kiếm
        for ii in range(i_min, i_max + 1):
            for jj in range(j_min, j_max + 1):
                for kk in range(k_min, k_max + 1):
                    # Tính khoảng cách không gian
                    di = (ii - i) * slice_thickness
                    dj = (jj - j) * pixel_spacing[0]
                    dk = (kk - k) * pixel_spacing[1]
                    r = np.sqrt(di*di + dj*dj + dk*dk)
                    
                    # Tính sai khác liều
                    meas_dose_value = meas_dose[ii, jj, kk]
                    delta_dose = abs(calc_dose_value - meas_dose_value)
                    
                    # Tính giá trị Gamma
                    if dose_criteria > 0 and distance_criteria > 0:
                        gamma = np.sqrt(
                            (r / distance_criteria)**2 + 
                            (delta_dose / dose_criteria)**2
                        )
                        min_gamma = min(min_gamma, gamma)
        
        return min_gamma
    
    def _interpolate_dose(self, dose_matrix: np.ndarray, target_shape: Tuple[int, int, int]) -> np.ndarray:
        """
        Nội suy ma trận liều về kích thước mong muốn.
        
        Args:
            dose_matrix: Ma trận liều gốc
            target_shape: Kích thước đích (z, y, x)
            
        Returns:
            np.ndarray: Ma trận liều đã nội suy
        """
        # Tạo lưới tọa độ cho ma trận gốc
        z = np.linspace(0, 1, dose_matrix.shape[0])
        y = np.linspace(0, 1, dose_matrix.shape[1])
        x = np.linspace(0, 1, dose_matrix.shape[2])
        
        # Tạo hàm nội suy
        interpolator = RegularGridInterpolator((z, y, x), dose_matrix)
        
        # Tạo lưới tọa độ cho ma trận đích
        z_new = np.linspace(0, 1, target_shape[0])
        y_new = np.linspace(0, 1, target_shape[1])
        x_new = np.linspace(0, 1, target_shape[2])
        
        # Tạo lưới điểm cho nội suy
        zz, yy, xx = np.meshgrid(z_new, y_new, x_new, indexing='ij')
        points = np.stack((zz, yy, xx), axis=-1)
        
        # Thực hiện nội suy
        interpolated_dose = interpolator(points)
        
        return interpolated_dose
    
    def analyze_delivery_log(self, log_file_path: str) -> Dict[str, Any]:
        """
        Phân tích file log từ máy xạ trị.
        
        Args:
            log_file_path: Đường dẫn đến file log
            
        Returns:
            Dict: Kết quả phân tích
        """
        try:
            # Đọc file log
            with open(log_file_path, 'r') as f:
                log_content = f.readlines()
            
            # Phân tích dữ liệu log (cần điều chỉnh tùy theo định dạng log cụ thể)
            # Đây là một ví dụ đơn giản
            mlc_positions = []
            gantry_angles = []
            collimator_angles = []
            mu_delivered = []
            
            for line in log_content:
                if line.startswith('MLC:'):
                    # Ví dụ: MLC: 1.2,2.3,3.4,...
                    positions = [float(x) for x in line.split(':')[1].strip().split(',')]
                    mlc_positions.append(positions)
                elif line.startswith('GANTRY:'):
                    # Ví dụ: GANTRY: 45.2
                    angle = float(line.split(':')[1].strip())
                    gantry_angles.append(angle)
                elif line.startswith('COLLIMATOR:'):
                    # Ví dụ: COLLIMATOR: 10.5
                    angle = float(line.split(':')[1].strip())
                    collimator_angles.append(angle)
                elif line.startswith('MU:'):
                    # Ví dụ: MU: 123.4
                    mu = float(line.split(':')[1].strip())
                    mu_delivered.append(mu)
            
            # So sánh với kế hoạch
            if self.plan_data and 'beams' in self.plan_data:
                planned_mlc = []
                planned_gantry = []
                planned_collimator = []
                planned_mu = []
                
                for beam in self.plan_data['beams']:
                    if 'mlc_positions' in beam:
                        planned_mlc.extend(beam['mlc_positions'])
                    if 'gantry_angle' in beam:
                        planned_gantry.append(beam['gantry_angle'])
                    if 'collimator_angle' in beam:
                        planned_collimator.append(beam['collimator_angle'])
                    if 'mu' in beam:
                        planned_mu.append(beam['mu'])
                
                # Tính sai số
                mlc_error = self._calculate_error(planned_mlc, mlc_positions)
                gantry_error = self._calculate_error(planned_gantry, gantry_angles)
                collimator_error = self._calculate_error(planned_collimator, collimator_angles)
                mu_error = self._calculate_error(planned_mu, mu_delivered)
                
                result = {
                    'mlc_positions': mlc_positions,
                    'gantry_angles': gantry_angles,
                    'collimator_angles': collimator_angles,
                    'mu_delivered': mu_delivered,
                    'mlc_error': mlc_error,
                    'gantry_error': gantry_error,
                    'collimator_error': collimator_error,
                    'mu_error': mu_error,
                    'pass': all([
                        mlc_error['max'] < 2.0,  # mm
                        gantry_error['max'] < 1.0,  # độ
                        collimator_error['max'] < 1.0,  # độ
                        mu_error['max'] < 1.0  # %
                    ])
                }
            else:
                # Nếu không có dữ liệu kế hoạch để so sánh
                result = {
                    'mlc_positions': mlc_positions,
                    'gantry_angles': gantry_angles,
                    'collimator_angles': collimator_angles,
                    'mu_delivered': mu_delivered
                }
            
            logger.info(f"Đã phân tích file log: {log_file_path}")
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi phân tích file log: {str(e)}")
            return None
    
    def _calculate_error(self, planned: List[float], actual: List[float]) -> Dict[str, float]:
        """
        Tính toán sai số giữa giá trị kế hoạch và thực tế.
        
        Args:
            planned: Danh sách giá trị kế hoạch
            actual: Danh sách giá trị thực tế
            
        Returns:
            Dict: Thông tin sai số
        """
        # Đảm bảo hai danh sách có cùng độ dài
        min_len = min(len(planned), len(actual))
        planned = planned[:min_len]
        actual = actual[:min_len]
        
        # Tính sai số
        errors = [abs(p - a) for p, a in zip(planned, actual)]
        
        return {
            'mean': np.mean(errors),
            'max': np.max(errors),
            'min': np.min(errors),
            'std': np.std(errors)
        }
    
    def generate_qa_report(self, output_path: str = None) -> str:
        """
        Tạo báo cáo QA.
        
        Args:
            output_path: Đường dẫn lưu báo cáo
            
        Returns:
            str: Đường dẫn đến file báo cáo
        """
        try:
            from quangstation.reporting.qa_report import QAReport
            
            # Tạo báo cáo QA
            qa_report = QAReport(
                patient_id=self.patient_id,
                plan_id=self.plan_id,
                db=self.db
            )
            
            # Thêm dữ liệu QA
            if hasattr(self, 'gamma_result') and self.gamma_result:
                qa_report.add_gamma_analysis(self.gamma_result)
            
            if hasattr(self, 'log_analysis') and self.log_analysis:
                qa_report.add_delivery_log_analysis(self.log_analysis)
            
            # Tạo báo cáo
            report_path = qa_report.generate_report(output_path)
            
            logger.info(f"Đã tạo báo cáo QA: {report_path}")
            return report_path
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo QA: {str(e)}")
            return None

    def analyze_qa_results(self, gamma_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phân tích kết quả QA và đưa ra đánh giá.
        
        Args:
            gamma_results: Kết quả phân tích Gamma
            
        Returns:
            Dict: Kết quả đánh giá QA
        """
        if gamma_results is None:
            return {
                'passed': False,
                'message': 'Không có dữ liệu phân tích Gamma'
            }
        
        # Các tiêu chí đánh giá
        pass_rate_threshold = 95.0  # Tỷ lệ vượt qua tối thiểu (%)
        max_gamma_threshold = 2.0   # Giá trị Gamma tối đa cho phép
        
        # Kiểm tra các tiêu chí
        pass_rate = gamma_results['pass_rate']
        max_gamma = gamma_results['max_gamma']
        mean_gamma = gamma_results['mean_gamma']
        
        # Đánh giá kết quả
        passed = pass_rate >= pass_rate_threshold and max_gamma <= max_gamma_threshold
        
        result = {
            'passed': passed,
            'pass_rate': pass_rate,
            'max_gamma': max_gamma,
            'mean_gamma': mean_gamma,
            'criteria': {
                'pass_rate_threshold': pass_rate_threshold,
                'max_gamma_threshold': max_gamma_threshold
            },
            'details': {
                'pass_rate_check': pass_rate >= pass_rate_threshold,
                'max_gamma_check': max_gamma <= max_gamma_threshold
            }
        }
        
        # Thêm thông báo chi tiết
        messages = []
        if pass_rate < pass_rate_threshold:
            messages.append(f"Tỷ lệ vượt qua ({pass_rate:.1f}%) thấp hơn ngưỡng yêu cầu ({pass_rate_threshold}%)")
        if max_gamma > max_gamma_threshold:
            messages.append(f"Giá trị Gamma tối đa ({max_gamma:.2f}) vượt quá ngưỡng cho phép ({max_gamma_threshold})")
        
        result['messages'] = messages if messages else ["Tất cả các tiêu chí đều đạt yêu cầu"]
        
        return result

    def export_qa_report(self, output_path: str, gamma_results: Dict[str, Any], 
                        analysis_results: Dict[str, Any]) -> bool:
        """
        Xuất báo cáo QA ra file PDF.
        
        Args:
            output_path: Đường dẫn file báo cáo
            gamma_results: Kết quả phân tích Gamma
            analysis_results: Kết quả đánh giá QA
            
        Returns:
            bool: True nếu xuất thành công, False nếu thất bại
        """
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            
            # Tạo document
            doc = SimpleDocTemplate(output_path, pagesize=letter)
            styles = getSampleStyleSheet()
            elements = []
            
            # Tiêu đề
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=30
            )
            elements.append(Paragraph("Báo cáo Kiểm tra Chất lượng (QA)", title_style))
            
            # Thông tin cơ bản
            if self.patient_data and self.plan_data:
                basic_info = [
                    ["ID bệnh nhân:", self.patient_id],
                    ["Tên bệnh nhân:", self.patient_data.get('name', 'N/A')],
                    ["ID kế hoạch:", self.plan_id],
                    ["Ngày kiểm tra:", datetime.now().strftime("%Y-%m-%d %H:%M")]
                ]
                
                t = Table(basic_info)
                t.setStyle(TableStyle([
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey)
                ]))
                elements.append(t)
            
            # Kết quả phân tích Gamma
            elements.append(Paragraph("Kết quả phân tích Gamma", styles['Heading2']))
            gamma_info = [
                ["Tiêu chí", "Giá trị"],
                ["Tỷ lệ vượt qua:", f"{gamma_results['pass_rate']:.1f}%"],
                ["Gamma trung bình:", f"{gamma_results['mean_gamma']:.3f}"],
                ["Gamma tối đa:", f"{gamma_results['max_gamma']:.3f}"],
                ["Tiêu chí liều:", f"{gamma_results['dose_criteria']}%"],
                ["Tiêu chí khoảng cách:", f"{gamma_results['distance_criteria']} mm"]
            ]
            
            t = Table(gamma_info)
            t.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey)
            ]))
            elements.append(t)
            
            # Kết quả đánh giá
            elements.append(Paragraph("Kết luận", styles['Heading2']))
            status = "ĐẠT" if analysis_results['passed'] else "KHÔNG ĐẠT"
            color = colors.green if analysis_results['passed'] else colors.red
            
            result_style = ParagraphStyle(
                'Result',
                parent=styles['Normal'],
                fontSize=12,
                textColor=color
            )
            elements.append(Paragraph(f"Kết quả: {status}", result_style))
            
            # Chi tiết đánh giá
            for message in analysis_results['messages']:
                elements.append(Paragraph(f"- {message}", styles['Normal']))
            
            # Tạo PDF
            doc.build(elements)
            logger.info(f"Đã xuất báo cáo QA: {output_path}")
            return True
            
        except Exception as error:
            logger.error(f"Lỗi khi xuất báo cáo QA: {str(error)}")
            return False
