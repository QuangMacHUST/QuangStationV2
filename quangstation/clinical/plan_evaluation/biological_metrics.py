"""
Module tính toán các chỉ số sinh học cho kế hoạch xạ trị.

Module này cung cấp các hàm và lớp để tính toán các chỉ số sinh học 
như EUD (Equivalent Uniform Dose), TCP (Tumor Control Probability),
và NTCP (Normal Tissue Complication Probability).
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any
import math

from quangstation.core.utils.logging import get_logger

logger = get_logger(__name__)

class BiologicalCalculator:
    """
    Lớp tính toán các chỉ số sinh học dựa trên phân bố liều và các tham số mô.
    """
    
    def __init__(self):
        # Giá trị mặc định để tránh lỗi "biến chưa được khởi tạo"
        structure_mask = np.zeros_like(self.volume)
        """Khởi tạo calculator."""
        logger.debug("Khởi tạo BiologicalCalculator")
    
    def calculate_eud(self, dose: np.ndarray, structure_mask: np.ndarray, a: float) -> float:
        """
        Tính toán Equivalent Uniform Dose (EUD).
        
        EUD = (1/N * sum(Di^a))^(1/a)
        
        Args:
            dose: Mảng 3D chứa dữ liệu liều.
            structure_mask: Mảng 3D chứa mask của cấu trúc.
            a: Tham số a. 
                - a < 0 cho mô bình thường (nhạy với liều cao)
                - a > 0 cho khối u (nhạy với liều thấp)
                
        Returns:
            Giá trị EUD tính bằng Gy.
        """
        try:
            # Kiểm tra dữ liệu đầu vào
            if dose.shape != structure_mask.shape:
                raise ValueError("Kích thước mảng dose và structure_mask phải giống nhau")
            
            # Lấy các giá trị liều trong cấu trúc
            mask_indices = structure_mask > 0
            structure_dose = dose[mask_indices]
            
            if len(structure_dose) == 0:
                logger.warning("Không có voxel nào trong cấu trúc")
                return 0.0
            
            # Tính EUD
            # Chuyển đổi thành đơn vị Gy nếu cần
            structure_dose_gy = structure_dose
            
            # Tính EUD theo công thức
            N = len(structure_dose_gy)
            eud = np.power(np.sum(np.power(structure_dose_gy, a)) / N, 1.0 / a)
            
            logger.info(f"Đã tính EUD = {eud:.2f} Gy với tham số a = {a}")
            return eud
        except Exception as error:
            logger.error(f"Lỗi khi tính EUD: {str(error)}")
            return 0.0
    
    def calculate_tcp(self, dose: np.ndarray, structure_mask: np.ndarray, 
                     tcd50: float = 60.0, gamma50: float = 2.0) -> float:
        """
        Tính toán Tumor Control Probability (TCP).
        
        TCP = 1 / (1 + (TCD50/EUD)^(4*gamma50))
        
        Args:
            dose: Mảng 3D chứa dữ liệu liều.
            structure_mask: Mảng 3D chứa mask của cấu trúc.
            tcd50: Liều cần thiết để đạt 50% TCP (Gy).
            gamma50: Độ dốc của đường cong liều-đáp ứng tại 50% (%.Gy^-1 / 100).
            
        Returns:
            Xác suất kiểm soát khối u (0-1).
        """
        try:
            # Tính EUD với a=0.1 (giá trị điển hình cho khối u)
            eud = self.calculate_eud(dose, structure_mask, a=0.1)
            
            # Tính TCP dựa trên mô hình logistic
            exponent = 4 * gamma50 * (1 - eud / tcd50)
            tcp = 1.0 / (1.0 + np.exp(exponent))
            
            logger.info(f"Đã tính TCP = {tcp:.4f} với TCD50 = {tcd50} Gy, gamma50 = {gamma50}")
            return tcp
        except Exception as error:
            logger.error(f"Lỗi khi tính TCP: {str(error)}")
            return 0.0
    
    def calculate_ntcp_lkb(self, dose: np.ndarray, structure_mask: np.ndarray,
                         td50: float, m: float, n: float) -> float:
        """
        Tính toán Normal Tissue Complication Probability (NTCP) theo mô hình Lyman-Kutcher-Burman.
        
        Args:
            dose: Mảng 3D chứa dữ liệu liều.
            structure_mask: Mảng 3D chứa mask của cấu trúc.
            td50: Liều dung nạp gây ra biến chứng 50% (Gy).
            m: Độ dốc của đường cong liều-đáp ứng.
            n: Tham số thể tích (volume parameter).
            
        Returns:
            Xác suất biến chứng mô bình thường (0-1).
        """
        try:
            # Tính gEUD với tham số a = 1/n
            a = 1.0 / n
            eud = self.calculate_eud(dose, structure_mask, a=-a)
            
            # Tính t
            t = (eud - td50) / (m * td50)
            
            # Tính NTCP
            ntcp = 0.5 * (1.0 + math.erf(t / math.sqrt(2.0)))
            
            logger.info(f"Đã tính NTCP = {ntcp:.4f} với tham số td50 = {td50}, m = {m}, n = {n}")
            return ntcp
        except Exception as error:
            logger.error(f"Lỗi khi tính NTCP theo mô hình LKB: {str(error)}")
            return 0.0
    
    def calculate_ntcp_rs(self, dose: np.ndarray, structure_mask: np.ndarray,
                        alpha: float, beta: float) -> float:
        """
        Tính toán NTCP theo mô hình Relative Seriality.
        
        Args:
            dose: Mảng 3D chứa dữ liệu liều.
            structure_mask: Mảng 3D chứa mask của cấu trúc.
            alpha: Tỷ lệ tuyến tính cho mô hình tuyến tính-bậc hai (LQ).
            beta: Tỷ lệ bậc hai cho mô hình LQ.
            
        Returns:
            Xác suất biến chứng mô bình thường (0-1).
        """
        try:
            # Lấy các giá trị liều trong cấu trúc
            mask_indices = structure_mask > 0
            structure_dose = dose[mask_indices]
            
            if len(structure_dose) == 0:
                logger.warning("Không có voxel nào trong cấu trúc")
                return 0.0
            
            # Tính cái chết tế bào (cell kill) theo mô hình LQ
            cell_kill = np.exp(-alpha * structure_dose - beta * structure_dose**2)
            
            # Tính xác suất sống sót
            survival_probability = np.mean(cell_kill)
            
            # Tính NTCP
            ntcp = 1.0 - survival_probability
            
            logger.info(f"Đã tính NTCP = {ntcp:.4f} theo mô hình Relative Seriality")
            return ntcp
        except Exception as error:
            logger.error(f"Lỗi khi tính NTCP theo mô hình RS: {str(error)}")
            return 0.0
    
    def evaluate_plan(self, dose: np.ndarray, structures: Dict[str, np.ndarray], 
                     params: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """
        Đánh giá kế hoạch xạ trị dựa trên các chỉ số sinh học.
        
        Args:
            dose: Mảng 3D chứa dữ liệu liều.
            structures: Dictionary các cấu trúc {name: mask}.
            params: Dictionary chứa tham số cho mỗi cấu trúc.
                {
                    'PTV': {'type': 'target', 'tcd50': 60.0, 'gamma50': 2.0, 'a': 0.1},
                    'OAR1': {'type': 'organ', 'td50': 40.0, 'm': 0.1, 'n': 0.5, 'a': -8}
                }
                
        Returns:
            Dictionary chứa kết quả đánh giá cho mỗi cấu trúc.
        """
        try:
            results = {}
            
            for name, mask in structures.items():
                if name not in params:
                    logger.warning(f"Không có tham số cho cấu trúc {name}")
                    continue
                
                structure_params = params[name]
                structure_type = structure_params.get('type', 'organ')
                
                # Khởi tạo kết quả cho cấu trúc
                results[name] = {}
                
                # Tính EUD
                a_value = structure_params.get('a', 0.1 if structure_type == 'target' else -8)
                eud = self.calculate_eud(dose, mask, a=a_value)
                results[name]['EUD'] = eud
                
                # Tính các chỉ số khác tùy theo loại cấu trúc
                if structure_type == 'target':
                    # Tính TCP cho khối u
                    tcd50 = structure_params.get('tcd50', 60.0)
                    gamma50 = structure_params.get('gamma50', 2.0)
                    tcp = self.calculate_tcp(dose, mask, tcd50, gamma50)
                    results[name]['TCP'] = tcp
                else:
                    # Tính NTCP cho mô bình thường
                    if 'td50' in structure_params and 'm' in structure_params and 'n' in structure_params:
                        td50 = structure_params['td50']
                        m = structure_params['m']
                        n = structure_params['n']
                        ntcp_lkb = self.calculate_ntcp_lkb(dose, mask, td50, m, n)
                        results[name]['NTCP_LKB'] = ntcp_lkb
                    
                    if 'alpha' in structure_params and 'beta' in structure_params:
                        alpha = structure_params['alpha']
                        beta = structure_params['beta']
                        ntcp_rs = self.calculate_ntcp_rs(dose, mask, alpha, beta)
                        results[name]['NTCP_RS'] = ntcp_rs
            
            logger.info(f"Đã đánh giá kế hoạch xạ trị cho {len(results)} cấu trúc")
            return results
        except Exception as error:
            logger.error(f"Lỗi khi đánh giá kế hoạch: {str(error)}")
            return {}
    
    def get_standard_organ_parameters(self) -> Dict[str, Dict[str, Any]]:
        """
        Lấy tham số tiêu chuẩn cho các cơ quan.
        
        Returns:
            Dictionary chứa tham số chuẩn cho các cơ quan phổ biến.
        """
        return {
            # Khối u
            'PTV': {
                'type': 'target',
                'a': 0.1,
                'tcd50': 60.0,
                'gamma50': 2.0
            },
            # Não
            'Brain': {
                'type': 'organ',
                'a': -8,
                'td50': 60.0,
                'm': 0.15,
                'n': 0.25
            },
            # Tủy sống
            'Spinal Cord': {
                'type': 'organ',
                'a': -20,  # Cơ quan nối tiếp
                'td50': 50.0,
                'm': 0.175,
                'n': 0.05
            },
            # Phổi
            'Lung': {
                'type': 'organ',
                'a': -1.2,  # Cơ quan song song
                'td50': 30.8,
                'm': 0.37,
                'n': 0.99
            },
            # Tim
            'Heart': {
                'type': 'organ',
                'a': -3.1,
                'td50': 48.0,
                'm': 0.1,
                'n': 0.35
            },
            # Thực quản
            'Esophagus': {
                'type': 'organ',
                'a': -19,
                'td50': 68.0,
                'm': 0.11,
                'n': 0.06
            },
            # Tuyến mang tai
            'Parotid': {
                'type': 'organ',
                'a': -2.2,
                'td50': 39.9,
                'm': 0.4,
                'n': 1.0
            },
            # Thận
            'Kidney': {
                'type': 'organ',
                'a': -3.0,
                'td50': 28.0,
                'm': 0.5,
                'n': 0.7
            },
            # Gan
            'Liver': {
                'type': 'organ',
                'a': -2.0,
                'td50': 40.0,
                'm': 0.28,
                'n': 0.7
            },
            # Bàng quang
            'Bladder': {
                'type': 'organ',
                'a': -3.63,
                'td50': 80.0,
                'm': 0.11,
                'n': 0.5
            },
            # Trực tràng
            'Rectum': {
                'type': 'organ',
                'a': -8.33,
                'td50': 80.0,
                'm': 0.14,
                'n': 0.12
            }
        }
    
    def calculate_complication_free_tumor_control(self, tcp: float, ntcp_values: List[float], 
                                              weighting_factors: List[float] = None) -> float:
        """
        Tính toán xác suất kiểm soát khối u mà không gây biến chứng (P+).
        
        Args:
            tcp: Xác suất kiểm soát khối u.
            ntcp_values: Danh sách các giá trị NTCP cho các cơ quan nguy cấp.
            weighting_factors: Danh sách các hệ số trọng số cho mỗi cơ quan.
                Nếu None, tất cả các cơ quan có trọng số bằng nhau.
                
        Returns:
            Xác suất kiểm soát khối u mà không gây biến chứng (0-1).
        """
        if not ntcp_values:
            return tcp
        
        # Nếu không có trọng số, gán trọng số bằng nhau
        if weighting_factors is None:
            weighting_factors = [1.0] * len(ntcp_values)
        elif len(weighting_factors) != len(ntcp_values):
            logger.warning("Số lượng trọng số không khớp với số lượng giá trị NTCP")
            weighting_factors = [1.0] * len(ntcp_values)
        
        # Chuẩn hóa trọng số
        total_weight = sum(weighting_factors)
        if total_weight > 0:
            weighting_factors = [w / total_weight for w in weighting_factors]
        else:
            weighting_factors = [1.0 / len(ntcp_values)] * len(ntcp_values)
        
        # Tính NTCP tổng hợp
        overall_ntcp = 0.0
        for ntcp, weight in zip(ntcp_values, weighting_factors):
            overall_ntcp += ntcp * weight
        
        # Tính P+
        p_plus = tcp * (1 - overall_ntcp)
        
        logger.info(f"Đã tính P+ = {p_plus:.4f} với TCP = {tcp:.4f}, NTCP tổng hợp = {overall_ntcp:.4f}")
        return p_plus 