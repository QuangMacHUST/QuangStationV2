"""
Module tạo báo cáo PDF cho kế hoạch xạ trị.
Hỗ trợ tạo báo cáo tóm tắt, báo cáo chi tiết, và báo cáo so sánh kế hoạch.
"""

import os
import io
import datetime
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.textlabels import Label

from quangstation.core.utils.logging import get_logger

logger = get_logger(__name__)

class PDFReport:
    """
    Lớp tạo báo cáo PDF cho kế hoạch xạ trị QuangStation V2.
    """
    
    def __init__(self, output_path: str, title: str = "Báo cáo Kế hoạch Xạ trị", 
                 pagesize: Tuple[float, float] = A4):
        """
        Khởi tạo tạo báo cáo PDF.
        
        Parameters:
        -----------
        output_path : str
            Đường dẫn lưu file PDF
        title : str
            Tiêu đề báo cáo
        pagesize : Tuple[float, float]
            Kích thước trang (mặc định: A4)
        """
        self.output_path = output_path
        self.title = title
        self.pagesize = pagesize
        self.styles = getSampleStyleSheet()
        
        # Tạo style tùy chỉnh
        self.styles.add(ParagraphStyle(
            name='TitleStyle',
            fontName='Helvetica-Bold',
            fontSize=16,
            alignment=1,  # center
            spaceAfter=12
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionStyle',
            fontName='Helvetica-Bold',
            fontSize=12,
            spaceBefore=10,
            spaceAfter=6
        ))
        
        self.styles.add(ParagraphStyle(
            name='NormalStyle',
            fontName='Helvetica',
            fontSize=10,
            spaceAfter=6
        ))
        
        # Danh sách các phần tử trong báo cáo
        self.elements = []
        
    def add_title(self):
        """Thêm tiêu đề báo cáo."""
        self.elements.append(Paragraph(self.title, self.styles['TitleStyle']))
        self.elements.append(Spacer(1, 0.25*inch))
        
    def add_header_info(self, patient_info: Dict[str, str]):
        """
        Thêm thông tin bệnh nhân và kế hoạch vào phần đầu báo cáo.
        
        Parameters:
        -----------
        patient_info : Dict[str, str]
            Thông tin bệnh nhân (ID, họ tên, ngày sinh, etc.)
        """
        # Tạo bảng thông tin bệnh nhân
        data = []
        for key, value in patient_info.items():
            data.append([key, value])
            
        table = Table(data, colWidths=[3*cm, 10*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        self.elements.append(Paragraph("Thông tin bệnh nhân", self.styles['SectionStyle']))
        self.elements.append(table)
        self.elements.append(Spacer(1, 0.2*inch))
        
    def add_plan_info(self, plan_info: Dict[str, str]):
        """
        Thêm thông tin kế hoạch xạ trị.
        
        Parameters:
        -----------
        plan_info : Dict[str, str]
            Thông tin kế hoạch xạ trị
        """
        data = []
        for key, value in plan_info.items():
            data.append([key, value])
            
        table = Table(data, colWidths=[5*cm, 8*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        self.elements.append(Paragraph("Thông tin kế hoạch xạ trị", self.styles['SectionStyle']))
        self.elements.append(table)
        self.elements.append(Spacer(1, 0.2*inch))
        
    def add_dvh_plot(self, dvh_data: Dict, width: int = 500, height: int = 300):
        """
        Thêm biểu đồ DVH vào báo cáo.
        
        Parameters:
        -----------
        dvh_data : Dict
            Dữ liệu DVH cho các cấu trúc
        width : int
            Chiều rộng hình (px)
        height : int
            Chiều cao hình (px)
        """
        buffer = io.BytesIO()
        plt.figure(figsize=(8, 5))
        
        for structure_name, data in dvh_data.items():
            dose_bins = data['dose_bins']
            volume = data['volume']
            color = data.get('color', 'blue')
            plt.plot(dose_bins, volume, label=structure_name, color=color, linewidth=2)
            
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.xlabel('Liều (Gy)')
        plt.ylabel('Thể tích (%)')
        plt.title('Biểu đồ Liều-Thể tích (DVH)')
        plt.legend(loc='upper right')
        plt.ylim(0, 105)
        
        plt.savefig(buffer, format='png', dpi=150)
        buffer.seek(0)
        
        img = Image(buffer, width=width, height=height)
        
        self.elements.append(Paragraph("Biểu đồ DVH", self.styles['SectionStyle']))
        self.elements.append(img)
        self.elements.append(Spacer(1, 0.2*inch))
        plt.close()
        
    def add_dose_metrics(self, metrics: Dict[str, Dict[str, float]]):
        """
        Thêm bảng các thông số liều quan trọng.
        
        Parameters:
        -----------
        metrics : Dict[str, Dict[str, float]]
            Thông số liều cho từng cấu trúc
        """
        # Tạo tiêu đề cho các cột
        headers = ['Cấu trúc', 'Dmin (Gy)', 'Dmax (Gy)', 'Dmean (Gy)', 'D95 (Gy)', 'V95 (%)', 'V100 (%)']
        data = [headers]
        
        # Thêm dữ liệu từng cấu trúc
        for structure_name, values in metrics.items():
            row = [
                structure_name,
                f"{values.get('d_min', 0):.2f}",
                f"{values.get('d_max', 0):.2f}",
                f"{values.get('d_mean', 0):.2f}",
                f"{values.get('d95', 0):.2f}",
                f"{values.get('v95', 0):.2f}",
                f"{values.get('v100', 0):.2f}"
            ]
            data.append(row)
            
        table = Table(data, colWidths=[3*cm, 2*cm, 2*cm, 2*cm, 2*cm, 2*cm, 2*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        self.elements.append(Paragraph("Chỉ số liều quan trọng", self.styles['SectionStyle']))
        self.elements.append(table)
        self.elements.append(Spacer(1, 0.2*inch))
        
    def add_dose_image(self, image_paths: List[str], captions: List[str], 
                       width: int = 250, height: int = 200):
        """
        Thêm hình ảnh phân bố liều vào báo cáo.
        
        Parameters:
        -----------
        image_paths : List[str]
            Danh sách đường dẫn ảnh
        captions : List[str]
            Chú thích cho mỗi ảnh
        width : int
            Chiều rộng mỗi ảnh
        height : int
            Chiều cao mỗi ảnh
        """
        self.elements.append(Paragraph("Phân bố liều", self.styles['SectionStyle']))
        
        # Xếp ảnh theo hàng, mỗi hàng 2 ảnh
        num_images = len(image_paths)
        for i in range(0, num_images, 2):
            # Tạo list chứa các ảnh và chú thích cho một hàng
            row_elements = []
            
            # Thêm ảnh đầu tiên
            img1 = Image(image_paths[i], width=width, height=height)
            caption1 = Paragraph(captions[i], self.styles['NormalStyle'])
            row_elements.extend([img1, caption1])
            
            # Nếu còn ảnh thứ hai thì thêm vào
            if i + 1 < num_images:
                img2 = Image(image_paths[i+1], width=width, height=height)
                caption2 = Paragraph(captions[i+1], self.styles['NormalStyle'])
                row_elements.extend([img2, caption2])
            
            # Tạo bảng chứa các ảnh trong hàng
            if i + 1 < num_images:
                image_table = Table([[img1, img2], [caption1, caption2]], 
                                   colWidths=[width+10, width+10])
            else:
                image_table = Table([[img1], [caption1]], 
                                   colWidths=[width+10])
            
            image_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            self.elements.append(image_table)
            self.elements.append(Spacer(1, 0.2*inch))
            
    def add_conformity_indices(self, indices: Dict[str, float]):
        """
        Thêm các chỉ số đánh giá kế hoạch.
        
        Parameters:
        -----------
        indices : Dict[str, float]
            Các chỉ số đánh giá kế hoạch
        """
        data = [['Chỉ số', 'Giá trị']]
        
        for name, value in indices.items():
            data.append([name, f"{value:.3f}"])
            
        table = Table(data, colWidths=[8*cm, 5*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        self.elements.append(Paragraph("Chỉ số đánh giá kế hoạch", self.styles['SectionStyle']))
        self.elements.append(table)
        self.elements.append(Spacer(1, 0.2*inch))
        
    def add_beam_info(self, beams: List[Dict[str, Any]]):
        """
        Thêm thông tin chùm tia.
        
        Parameters:
        -----------
        beams : List[Dict[str, Any]]
            Danh sách thông tin các chùm tia
        """
        headers = ['ID', 'Loại', 'Năng lượng', 'Góc Gantry', 'Góc Collimator', 'MU']
        data = [headers]
        
        for beam in beams:
            row = [
                beam.get('id', ''),
                beam.get('type', ''),
                f"{beam.get('energy', 0)} MV",
                f"{beam.get('gantry_angle', 0)}°",
                f"{beam.get('collimator_angle', 0)}°",
                f"{beam.get('mu', 0):.1f}"
            ]
            data.append(row)
            
        table = Table(data, colWidths=[2*cm, 2.5*cm, 2.5*cm, 3*cm, 3*cm, 2*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        self.elements.append(Paragraph("Thông tin chùm tia", self.styles['SectionStyle']))
        self.elements.append(table)
        self.elements.append(Spacer(1, 0.2*inch))
        
    def add_signatures(self, approved_by: str, checked_by: str = None, date: str = None):
        """
        Thêm phần ký duyệt vào báo cáo.
        
        Parameters:
        -----------
        approved_by : str
            Tên người duyệt
        checked_by : str
            Tên người kiểm tra
        date : str
            Ngày duyệt (mặc định: ngày hiện tại)
        """
        if date is None:
            date = datetime.datetime.now().strftime("%d/%m/%Y")
            
        data = [
            ['Người lập kế hoạch:', 'Người kiểm tra:', 'Người duyệt:'],
            ['', checked_by if checked_by else '', approved_by],
            ['Ngày: ' + date, '', '']
        ]
        
        table = Table(data, colWidths=[5*cm, 5*cm, 5*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEABOVE', (0, 1), (0, 1), 1, colors.black),
            ('LINEABOVE', (1, 1), (1, 1), 1, colors.black),
            ('LINEABOVE', (2, 1), (2, 1), 1, colors.black),
        ]))
        
        self.elements.append(Spacer(1, inch))
        self.elements.append(table)
        
    def add_notes(self, notes: str):
        """
        Thêm ghi chú vào báo cáo.
        
        Parameters:
        -----------
        notes : str
            Nội dung ghi chú
        """
        self.elements.append(Paragraph("Ghi chú:", self.styles['SectionStyle']))
        self.elements.append(Paragraph(notes, self.styles['NormalStyle']))
        self.elements.append(Spacer(1, 0.2*inch))
        
    def add_footer(self):
        """Thêm footer vào mỗi trang của báo cáo."""
        def add_page_number(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 9)
            # Vẽ đường kẻ phía trên footer
            canvas.line(doc.leftMargin, 0.75*inch, doc.width + doc.leftMargin, 0.75*inch)
            # Thêm thông tin footer
            footer_text = "QuangStation V2 - Hệ thống Lập kế hoạch Xạ trị Mã nguồn Mở"
            canvas.drawString(doc.leftMargin, 0.5*inch, footer_text)
            # Thêm số trang
            page_num = canvas.getPageNumber()
            canvas.drawRightString(doc.width + doc.leftMargin, 0.5*inch, f"Trang {page_num}")
            canvas.restoreState()
            
        return add_page_number
        
    def generate(self):
        """
        Tạo file PDF báo cáo.
        
        Returns:
        --------
        str
            Đường dẫn tới file PDF đã tạo
        """
        doc = SimpleDocTemplate(
            self.output_path,
            pagesize=self.pagesize,
            leftMargin=2*cm,
            rightMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # Tạo báo cáo
        doc.build(self.elements, onFirstPage=self.add_footer(), onLaterPages=self.add_footer())
        return self.output_path


def create_plan_report(
    patient_info: Dict[str, str],
    plan_info: Dict[str, str],
    dvh_data: Dict,
    dose_metrics: Dict[str, Dict[str, float]],
    image_paths: List[str],
    image_captions: List[str],
    conformity_indices: Dict[str, float],
    beams: List[Dict[str, Any]],
    approved_by: str,
    checked_by: str = None,
    notes: str = "",
    output_path: str = None
) -> str:
    """
    Hàm tiện ích để tạo báo cáo kế hoạch xạ trị.
    
    Parameters:
    -----------
    patient_info : Dict[str, str]
        Thông tin bệnh nhân
    plan_info : Dict[str, str]
        Thông tin kế hoạch
    dvh_data : Dict
        Dữ liệu biểu đồ DVH
    dose_metrics : Dict[str, Dict[str, float]]
        Các chỉ số liều cho từng cấu trúc
    image_paths : List[str]
        Danh sách đường dẫn ảnh liều
    image_captions : List[str]
        Danh sách chú thích cho ảnh
    conformity_indices : Dict[str, float]
        Các chỉ số đánh giá kế hoạch
    beams : List[Dict[str, Any]]
        Thông tin các chùm tia
    approved_by : str
        Tên người duyệt
    checked_by : str, optional
        Tên người kiểm tra
    notes : str, optional
        Ghi chú bổ sung
    output_path : str, optional
        Đường dẫn file PDF đầu ra
        
    Returns:
    --------
    str
        Đường dẫn tới file PDF đã tạo
    """
    if output_path is None:
        patient_id = patient_info.get('ID', 'unknown')
        plan_id = plan_info.get('ID kế hoạch', 'plan')
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        output_path = f"reports/{patient_id}_{plan_id}_{date_str}.pdf"
        
        # Đảm bảo thư mục reports tồn tại
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Tạo báo cáo
    report = PDFReport(output_path)
    report.add_title()
    report.add_header_info(patient_info)
    report.add_plan_info(plan_info)
    report.add_dvh_plot(dvh_data)
    report.add_dose_metrics(dose_metrics)
    report.add_dose_image(image_paths, image_captions)
    report.add_conformity_indices(conformity_indices)
    report.add_beam_info(beams)
    
    if notes:
        report.add_notes(notes)
        
    report.add_signatures(approved_by, checked_by)
    
    # Tạo file PDF
    return report.generate() 