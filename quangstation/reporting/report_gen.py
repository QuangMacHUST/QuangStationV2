"""
Module báo cáo điều trị cho hệ thống QuangStation V2
"""

import os
import json
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

from plan_evaluation.dvh import DVHPlotter
from utils.logging import get_logger

logger = get_logger("ReportGenerator")

class TreatmentReport:
    """Lớp tạo báo cáo điều trị chi tiết"""
    
    def __init__(self, patient_data, plan_data, dose_data, structures):
        """
        Khởi tạo báo cáo điều trị
        
        Args:
            patient_data (dict): Thông tin bệnh nhân
            plan_data (dict): Thông tin kế hoạch điều trị
            dose_data (np.ndarray): Dữ liệu liều
            structures (dict): Thông tin các cấu trúc
        """
        self.patient_data = patient_data
        self.plan_data = plan_data
        self.dose_data = dose_data
        self.structures = structures
        
        # Tạo DVH Plotter
        self.dvh_plotter = DVHPlotter()
        
        logger.log_info("Khởi tạo báo cáo điều trị")
    
    def generate_pdf_report(self, output_path=None):
        """
        Tạo báo cáo PDF chi tiết
        
        Args:
            output_path (str): Đường dẫn file PDF
        """
        if output_path is None:
            output_path = f"treatment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        try:
            # Tạo PDF
            doc = SimpleDocTemplate(output_path, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            # Tiêu đề báo cáo
            title = Paragraph("Báo cáo Kế hoạch Xạ trị", styles['Title'])
            story.append(title)
            
            # Thông tin bệnh nhân
            patient_info = [
                ["Thông tin Bệnh nhân"],
                ["Tên", self.patient_data.get('patient_name', 'N/A')],
                ["ID", self.patient_data.get('patient_id', 'N/A')],
                ["Ngày sinh", self.patient_data.get('birth_date', 'N/A')],
                ["Giới tính", self.patient_data.get('sex', 'N/A')]
            ]
            patient_table = Table(patient_info, colWidths=[2*inch, 4*inch])
            patient_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.grey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 12),
                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                ('BACKGROUND', (0,1), (-1,-1), colors.beige),
                ('GRID', (0,0), (-1,-1), 1, colors.black)
            ]))
            story.append(patient_table)
            
            # Thông tin kế hoạch
            plan_info = [
                ["Thông tin Kế hoạch"],
                ["Tên kế hoạch", self.plan_data.get('plan_name', 'N/A')],
                ["Kỹ thuật", self.plan_data.get('technique', 'N/A')],
                ["Liều tổng", f"{self.plan_data.get('total_dose', 'N/A')} Gy"],
                ["Số phân đoạn", self.plan_data.get('fractions', 'N/A')],
                ["Liều mỗi phân đoạn", f"{self.plan_data.get('fraction_dose', 'N/A')} Gy"]
            ]
            plan_table = Table(plan_info, colWidths=[2*inch, 4*inch])
            plan_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.grey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 12),
                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                ('BACKGROUND', (0,1), (-1,-1), colors.beige),
                ('GRID', (0,0), (-1,-1), 1, colors.black)
            ]))
            story.append(plan_table)
            
            # Tạo DVH
            dvh_figure = self.dvh_plotter.create_figure()
            self.dvh_plotter.plot_dvh(figure=dvh_figure)
            
            # Lưu DVH làm ảnh tạm
            dvh_path = "temp_dvh.png"
            self.dvh_plotter.save_plot(dvh_path)
            
            # Thêm DVH vào báo cáo
            story.append(Paragraph("Biểu đồ Liều-Thể tích (DVH)", styles['Heading2']))
            
            # Xây dựng PDF
            doc.build(story)
            
            logger.log_info(f"Đã tạo báo cáo tại: {output_path}")
            return output_path
        
        except Exception as e:
            logger.log_error(f"Lỗi khi tạo báo cáo: {e}")
            return None
    
    def export_json_summary(self, output_path=None):
        """
        Xuất báo cáo dưới dạng JSON
        
        Args:
            output_path (str): Đường dẫn file JSON
        """
        if output_path is None:
            output_path = f"treatment_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        summary = {
            "patient_info": self.patient_data,
            "plan_details": self.plan_data,
            "dose_statistics": {
                "max_dose": float(np.max(self.dose_data)),
                "min_dose": float(np.min(self.dose_data)),
                "mean_dose": float(np.mean(self.dose_data))
            },
            "structures": {name: {"volume": struct.get("volume_cc", 0)} for name, struct in self.structures.items()}
        }
        
        try:
            with open(output_path, 'w') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            logger.log_info(f"Đã xuất báo cáo JSON tại: {output_path}")
            return output_path
        
        except Exception as e:
            logger.log_error(f"Lỗi khi xuất báo cáo JSON: {e}")
            return None

def generate_treatment_report(patient_data, plan_data, dose_data, structures, 
                              pdf_output=None, json_output=None):
    """
    Hàm tiện ích để tạo báo cáo điều trị
    
    Args:
        patient_data (dict): Thông tin bệnh nhân
        plan_data (dict): Thông tin kế hoạch
        dose_data (np.ndarray): Dữ liệu liều
        structures (dict): Thông tin các cấu trúc
        pdf_output (str, optional): Đường dẫn file PDF
        json_output (str, optional): Đường dẫn file JSON
    
    Returns:
        tuple: Đường dẫn file PDF và JSON
    """
    report = TreatmentReport(patient_data, plan_data, dose_data, structures)
    
    pdf_path = report.generate_pdf_report(pdf_output)
    json_path = report.export_json_summary(json_output)
    
    return pdf_path, json_path
