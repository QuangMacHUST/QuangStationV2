#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module tính toán hiệu quả sinh học cho QuangStation V2.
Bao gồm các chỉ số BED (Biologically Effective Dose), EQD2 (Equivalent Dose in 2Gy fractions),
và các mô hình phản hồi sinh học khác.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Union
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

from quangstation.utils.logging import get_logger

logger = get_logger("BiologicalEffects")

class BiologicalEffectsCalculator:
    """Lớp tính toán hiệu quả sinh học cho kế hoạch xạ trị"""
    
    def __init__(self):
        """Khởi tạo calculator"""
        self.logger = get_logger("BiologicalEffects")
        
        # Các giá trị α/β mặc định (Gy) cho các loại mô và khối u
        self.default_alphabeta_values = {
            # Khối u
            "PROSTATE": 1.5,
            "BREAST": 4.0,
            "HEAD_NECK": 10.0,
            "LUNG": 10.0,
            "BRAIN": 10.0,
            "GBM": 10.0,
            "CERVIX": 10.0,
            "COLORECTAL": 5.0,
            "MELANOMA": 2.5,
            
            # Mô lành
            "SPINAL_CORD": 2.0,
            "BRAINSTEM": 2.0,
            "LUNG_NORMAL": 3.0,
            "HEART": 2.5,
            "ESOPHAGUS": 3.0,
            "RECTUM": 3.0,
            "BLADDER": 5.0,
            "KIDNEY": 2.5,
            "LIVER": 2.5,
            "PAROTID": 3.0,
            "OPTIC_NERVE": 3.0,
            "COCHLEA": 3.0,
            "LENS": 1.2,
            "SKIN": 2.8,
        }
    
    def calculate_bed(self, 
                     dose: float, 
                     fractions: int, 
                     alpha_beta: Optional[float] = None, 
                     structure_name: Optional[str] = None) -> float:
        """
        Tính toán Biologically Effective Dose (BED)
        
        BED = D × (1 + d/(α/β))
        
        Trong đó:
        - D = tổng liều
        - d = liều/phân liều (D/n)
        - α/β = tỷ số alpha/beta cho loại mô cụ thể
        
        Args:
            dose: Tổng liều (Gy)
            fractions: Số phân liều
            alpha_beta: Tỷ số alpha/beta cho loại mô (Gy)
            structure_name: Tên cấu trúc (để lấy α/β mặc định nếu không cung cấp)
            
        Returns:
            Giá trị BED (Gy)
        """
        # Kiểm tra đầu vào
        if dose <= 0:
            self.logger.log_warning("Liều không hợp lệ")
            return 0
        
        if fractions <= 0:
            self.logger.log_warning("Số phân liều không hợp lệ")
            return 0
        
        # Xác định α/β
        if alpha_beta is None:
            if structure_name and structure_name.upper() in self.default_alphabeta_values:
                alpha_beta = self.default_alphabeta_values[structure_name.upper()]
            else:
                alpha_beta = 10.0  # Giá trị mặc định cho khối u
                self.logger.log_warning(f"Sử dụng α/β mặc định: {alpha_beta} Gy")
        
        # Tính liều mỗi phân liều
        dose_per_fraction = dose / fractions
        
        # Tính BED
        bed = dose * (1 + dose_per_fraction / alpha_beta)
        
        return bed
    
    def calculate_eqd2(self, 
                      dose: float, 
                      fractions: int, 
                      alpha_beta: Optional[float] = None, 
                      structure_name: Optional[str] = None) -> float:
        """
        Tính toán Equivalent Dose in 2Gy fractions (EQD2)
        
        EQD2 = D × ((d + (α/β)) / (2 + (α/β)))
        
        Trong đó:
        - D = tổng liều
        - d = liều/phân liều (D/n)
        - α/β = tỷ số alpha/beta cho loại mô cụ thể
        
        Args:
            dose: Tổng liều (Gy)
            fractions: Số phân liều
            alpha_beta: Tỷ số alpha/beta cho loại mô (Gy)
            structure_name: Tên cấu trúc (để lấy α/β mặc định nếu không cung cấp)
            
        Returns:
            Giá trị EQD2 (Gy)
        """
        # Kiểm tra đầu vào
        if dose <= 0:
            self.logger.log_warning("Liều không hợp lệ")
            return 0
        
        if fractions <= 0:
            self.logger.log_warning("Số phân liều không hợp lệ")
            return 0
        
        # Xác định α/β
        if alpha_beta is None:
            if structure_name and structure_name.upper() in self.default_alphabeta_values:
                alpha_beta = self.default_alphabeta_values[structure_name.upper()]
            else:
                alpha_beta = 10.0  # Giá trị mặc định cho khối u
                self.logger.log_warning(f"Sử dụng α/β mặc định: {alpha_beta} Gy")
        
        # Tính liều mỗi phân liều
        dose_per_fraction = dose / fractions
        
        # Tính EQD2
        eqd2 = dose * ((dose_per_fraction + alpha_beta) / (2 + alpha_beta))
        
        return eqd2
    
    def calculate_bed_distribution(self, 
                                  dose_matrix: np.ndarray, 
                                  fractions: int, 
                                  alpha_beta: float) -> np.ndarray:
        """
        Tính toán phân bố BED từ phân bố liều
        
        Args:
            dose_matrix: Ma trận phân bố liều (Gy)
            fractions: Số phân liều
            alpha_beta: Tỷ số alpha/beta cho loại mô (Gy)
            
        Returns:
            Ma trận phân bố BED (Gy)
        """
        # Kiểm tra đầu vào
        if fractions <= 0:
            self.logger.log_warning("Số phân liều không hợp lệ")
            return np.zeros_like(dose_matrix)
        
        # Tính liều mỗi phân liều
        dose_per_fraction = dose_matrix / fractions
        
        # Tính BED
        bed_matrix = dose_matrix * (1 + dose_per_fraction / alpha_beta)
        
        return bed_matrix
    
    def calculate_eqd2_distribution(self, 
                                   dose_matrix: np.ndarray, 
                                   fractions: int, 
                                   alpha_beta: float) -> np.ndarray:
        """
        Tính toán phân bố EQD2 từ phân bố liều
        
        Args:
            dose_matrix: Ma trận phân bố liều (Gy)
            fractions: Số phân liều
            alpha_beta: Tỷ số alpha/beta cho loại mô (Gy)
            
        Returns:
            Ma trận phân bố EQD2 (Gy)
        """
        # Kiểm tra đầu vào
        if fractions <= 0:
            self.logger.log_warning("Số phân liều không hợp lệ")
            return np.zeros_like(dose_matrix)
        
        # Tính liều mỗi phân liều
        dose_per_fraction = dose_matrix / fractions
        
        # Tính EQD2
        eqd2_matrix = dose_matrix * ((dose_per_fraction + alpha_beta) / (2 + alpha_beta))
        
        return eqd2_matrix
    
    def calculate_ntcp(self, 
                      mean_dose: float, 
                      td5: float, 
                      m: float = 0.18, 
                      n: float = 1.0) -> float:
        """
        Tính toán Normal Tissue Complication Probability (NTCP)
        sử dụng mô hình Lyman-Kutcher-Burman (LKB)
        
        NTCP = 1/√(2π) ∫_{-∞}^{t} exp(-x²/2) dx
        
        Trong đó:
        - t = (D - TD50) / (m × TD50)
        - TD50 = liều gây ra 50% biến chứng
        - m = độ dốc của đường cong liều-đáp ứng
        - n = thông số thể tích
        
        Args:
            mean_dose: Liều trung bình (Gy)
            td5: Liều gây ra 5% biến chứng (Gy)
            m: Thông số độ dốc
            n: Thông số thể tích
            
        Returns:
            Giá trị NTCP (0-1)
        """
        from scipy.stats import norm
        
        # Tính TD50 từ TD5
        td50 = td5 / (1 - 0.5**(1/0.05))
        
        # Tính giá trị t
        t = (mean_dose - td50) / (m * td50)
        
        # Tính NTCP
        ntcp = norm.cdf(t)
        
        return ntcp
    
    def calculate_tcp(self, 
                     dose: float, 
                     fractions: int, 
                     alpha: float = 0.3, 
                     alpha_beta: float = 10.0, 
                     clonogen_density: float = 1e7) -> float:
        """
        Tính toán Tumor Control Probability (TCP)
        sử dụng mô hình Linear-Quadratic (LQ)
        
        TCP = exp(-N × exp(-α × BED))
        
        Trong đó:
        - N = số tế bào clonogenic
        - α = độ nhạy phóng xạ
        - BED = Biologically Effective Dose
        
        Args:
            dose: Tổng liều (Gy)
            fractions: Số phân liều
            alpha: Hệ số α (Gy^-1)
            alpha_beta: Tỷ số α/β (Gy)
            clonogen_density: Mật độ tế bào clonogenic
            
        Returns:
            Giá trị TCP (0-1)
        """
        # Tính BED
        bed = self.calculate_bed(dose, fractions, alpha_beta)
        
        # Tính TCP
        tcp = np.exp(-clonogen_density * np.exp(-alpha * bed))
        
        return tcp
    
    def combine_plans(self, 
                     plans: List[Dict], 
                     structure_name: str, 
                     alpha_beta: Optional[float] = None) -> Dict:
        """
        Kết hợp nhiều kế hoạch xạ trị
        
        Args:
            plans: Danh sách các kế hoạch {dose, fractions}
            structure_name: Tên cấu trúc
            alpha_beta: Tỷ số α/β (Gy)
            
        Returns:
            Kế hoạch tương đương {total_dose, fractions, eqd2, bed}
        """
        # Xác định α/β
        if alpha_beta is None:
            if structure_name and structure_name.upper() in self.default_alphabeta_values:
                alpha_beta = self.default_alphabeta_values[structure_name.upper()]
            else:
                alpha_beta = 10.0  # Giá trị mặc định cho khối u
                self.logger.log_warning(f"Sử dụng α/β mặc định: {alpha_beta} Gy")
        
        # Tính tổng BED
        total_bed = 0
        total_fractions = 0
        
        for plan in plans:
            dose = plan.get("dose", 0)
            fractions = plan.get("fractions", 0)
            
            if dose <= 0 or fractions <= 0:
                continue
            
            bed = self.calculate_bed(dose, fractions, alpha_beta)
            total_bed += bed
            total_fractions += fractions
        
        # Tính liều tương đương
        if total_fractions > 0:
            # Tính EQD2
            eqd2 = total_bed / (1 + 2 / alpha_beta)
            
            # Tính liều tương đương với số phân liều total_fractions
            equivalent_dose_per_fraction = (-alpha_beta + np.sqrt(alpha_beta**2 + 4 * alpha_beta * total_bed / total_fractions)) / 2
            equivalent_dose = equivalent_dose_per_fraction * total_fractions
            
            return {
                "total_dose": equivalent_dose,
                "fractions": total_fractions,
                "eqd2": eqd2,
                "bed": total_bed
            }
        else:
            return {
                "total_dose": 0,
                "fractions": 0,
                "eqd2": 0,
                "bed": 0
            }
    
    def get_alphabeta_value(self, structure_name: str) -> float:
        """
        Lấy giá trị α/β cho cấu trúc
        
        Args:
            structure_name: Tên cấu trúc
            
        Returns:
            Giá trị α/β (Gy)
        """
        if structure_name and structure_name.upper() in self.default_alphabeta_values:
            return self.default_alphabeta_values[structure_name.upper()]
        else:
            return 10.0  # Giá trị mặc định
    
    def get_all_alphabeta_values(self) -> Dict[str, float]:
        """
        Lấy tất cả giá trị α/β mặc định
        
        Returns:
            Dictionary các giá trị α/β {tên_cấu_trúc: giá_trị}
        """
        return self.default_alphabeta_values.copy()
    
    def create_fractionation_chart(self, 
                                  dose_range: Tuple[float, float],
                                  fractions_list: List[int],
                                  target_structures: List[str],
                                  oar_structures: List[str],
                                  output_file: Optional[str] = None) -> plt.Figure:
        """
        Tạo biểu đồ phân liều cho các cấu trúc
        
        Args:
            dose_range: Khoảng liều (min, max) tính theo Gy
            fractions_list: Danh sách số phân liều cần so sánh
            target_structures: Danh sách cấu trúc đích
            oar_structures: Danh sách cấu trúc nguy cơ
            output_file: Đường dẫn file đầu ra (nếu cần lưu)
            
        Returns:
            Đối tượng Figure của matplotlib
        """
        try:
            # Tạo dữ liệu
            min_dose, max_dose = dose_range
            dose_values = np.linspace(min_dose, max_dose, 100)
            
            # Tạo figure
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 12))
            
            # Vẽ biểu đồ EQD2 cho cấu trúc đích
            ax1.set_title("EQD2 cho cấu trúc đích", fontsize=14)
            ax1.set_xlabel("Tổng liều (Gy)", fontsize=12)
            ax1.set_ylabel("EQD2 (Gy)", fontsize=12)
            
            for structure in target_structures:
                alpha_beta = self.get_alphabeta_value(structure)
                
                for fractions in fractions_list:
                    eqd2_values = [self.calculate_eqd2(dose, fractions, alpha_beta) for dose in dose_values]
                    ax1.plot(dose_values, eqd2_values, label=f"{structure} - {fractions} phân liều (α/β = {alpha_beta} Gy)")
            
            ax1.legend(fontsize=10)
            ax1.grid(True)
            
            # Vẽ biểu đồ EQD2 cho cấu trúc nguy cơ
            ax2.set_title("EQD2 cho cấu trúc nguy cơ", fontsize=14)
            ax2.set_xlabel("Tổng liều (Gy)", fontsize=12)
            ax2.set_ylabel("EQD2 (Gy)", fontsize=12)
            
            for structure in oar_structures:
                alpha_beta = self.get_alphabeta_value(structure)
                
                for fractions in fractions_list:
                    eqd2_values = [self.calculate_eqd2(dose, fractions, alpha_beta) for dose in dose_values]
                    ax2.plot(dose_values, eqd2_values, label=f"{structure} - {fractions} phân liều (α/β = {alpha_beta} Gy)")
            
            ax2.legend(fontsize=10)
            ax2.grid(True)
            
            plt.tight_layout()
            
            # Lưu file nếu cần
            if output_file:
                plt.savefig(output_file, dpi=300, bbox_inches='tight')
            
            return fig
            
        except Exception as e:
            self.logger.log_error(f"Lỗi khi tạo biểu đồ phân liều: {str(e)}")
            return plt.figure()
    
    def create_summary_table(self, 
                            structures: List[str], 
                            dose: float, 
                            fractions: int,
                            output_file: Optional[str] = None) -> pd.DataFrame:
        """
        Tạo bảng tóm tắt các chỉ số sinh học
        
        Args:
            structures: Danh sách các cấu trúc
            dose: Tổng liều (Gy)
            fractions: Số phân liều
            output_file: Đường dẫn file đầu ra (nếu cần lưu)
            
        Returns:
            DataFrame chứa thông tin tóm tắt
        """
        try:
            # Tạo DataFrame
            data = []
            
            for structure in structures:
                alpha_beta = self.get_alphabeta_value(structure)
                bed = self.calculate_bed(dose, fractions, alpha_beta)
                eqd2 = self.calculate_eqd2(dose, fractions, alpha_beta)
                
                data.append({
                    "Cấu trúc": structure,
                    "α/β (Gy)": alpha_beta,
                    "Tổng liều (Gy)": dose,
                    "Phân liều (Gy)": dose / fractions,
                    "Số phân liều": fractions,
                    "BED (Gy)": bed,
                    "EQD2 (Gy)": eqd2
                })
            
            df = pd.DataFrame(data)
            
            # Lưu file nếu cần
            if output_file:
                if output_file.endswith('.csv'):
                    df.to_csv(output_file, index=False)
                elif output_file.endswith('.xlsx'):
                    df.to_excel(output_file, index=False)
                else:
                    self.logger.log_warning(f"Không hỗ trợ định dạng file: {output_file}")
            
            return df
            
        except Exception as e:
            self.logger.log_error(f"Lỗi khi tạo bảng tóm tắt: {str(e)}")
            return pd.DataFrame()

# Tạo instance mặc định
biological_calculator = BiologicalEffectsCalculator() 