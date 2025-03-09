#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module phân đoạn tự động dựa trên AI cho QuangStation V2.
Sử dụng các mô hình học sâu để phân đoạn cơ quan tự động từ ảnh CT/MRI.
"""

import os
import numpy as np
import time
from typing import Dict, List, Tuple, Optional, Union, Any
from pathlib import Path

from quangstation.utils.logging import get_logger

logger = get_logger("AutoSegmentation")

# Kiểm tra các thư viện học sâu có sẵn
try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    logger.log_warning("PyTorch không có sẵn. Một số chức năng phân đoạn tự động sẽ bị vô hiệu hóa.")

class SegmentationModel:
    """Lớp cơ sở cho các mô hình phân đoạn"""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Khởi tạo mô hình phân đoạn
        
        Args:
            model_path: Đường dẫn đến file mô hình (nếu có)
        """
        self.model_path = model_path
        self.model = None
        self.device = 'cpu'
        
        if HAS_TORCH:
            # Sử dụng GPU nếu có
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            logger.log_info(f"Sử dụng thiết bị: {self.device}")
    
    def load_model(self):
        """Tải mô hình từ file"""
        if not HAS_TORCH:
            logger.log_error("Không thể tải mô hình: PyTorch không có sẵn")
            return False
        
        if not self.model_path or not os.path.exists(self.model_path):
            logger.log_error(f"Không tìm thấy file mô hình: {self.model_path}")
            return False
        
        try:
            self.model = torch.load(self.model_path, map_location=self.device)
            self.model.eval()
            logger.log_info(f"Đã tải mô hình từ: {self.model_path}")
            return True
        except Exception as e:
            logger.log_error(f"Lỗi khi tải mô hình: {str(e)}")
            return False
    
    def preprocess(self, image: np.ndarray) -> Union[np.ndarray, torch.Tensor]:
        """
        Tiền xử lý hình ảnh đầu vào
        
        Args:
            image: Hình ảnh đầu vào (3D numpy array)
            
        Returns:
            Hình ảnh đã xử lý
        """
        # Chuẩn hóa
        image = (image - np.min(image)) / (np.max(image) - np.min(image) + 1e-8)
        
        if HAS_TORCH:
            # Chuyển sang torch tensor
            image_tensor = torch.from_numpy(image).float()
            
            # Thêm chiều batch và channel
            if len(image_tensor.shape) == 3:
                image_tensor = image_tensor.unsqueeze(0).unsqueeze(0)
            
            return image_tensor.to(self.device)
        
        return image
    
    def predict(self, image: np.ndarray) -> np.ndarray:
        """
        Dự đoán mask từ hình ảnh đầu vào
        
        Args:
            image: Hình ảnh đầu vào (3D numpy array)
            
        Returns:
            Mask dự đoán (3D numpy array)
        """
        if not HAS_TORCH or self.model is None:
            logger.log_error("Không thể dự đoán: Mô hình chưa được tải")
            # Trả về mask trống
            return np.zeros_like(image)
        
        try:
            # Tiền xử lý
            processed_image = self.preprocess(image)
            
            # Dự đoán
            with torch.no_grad():
                output = self.model(processed_image)
            
            # Hậu xử lý
            if isinstance(output, torch.Tensor):
                output = output.cpu().numpy()
            
            # Loại bỏ chiều batch và channel
            if output.shape[0] == 1:
                output = output[0]
            if len(output.shape) > 3 and output.shape[0] == 1:
                output = output[0]
            
            # Chuyển sang mask nhị phân
            mask = (output > 0.5).astype(np.uint8)
            
            return mask
        
        except Exception as e:
            logger.log_error(f"Lỗi khi dự đoán: {str(e)}")
            return np.zeros_like(image)

class UNetModel(SegmentationModel):
    """Mô hình U-Net cho phân đoạn hình ảnh y tế"""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Khởi tạo mô hình U-Net
        
        Args:
            model_path: Đường dẫn đến file mô hình (nếu có)
        """
        super().__init__(model_path)
        
        # Tải mô hình mặc định nếu không chỉ định
        if not model_path and HAS_TORCH:
            # Tìm mô hình mặc định trong thư mục resources
            default_models_dir = Path(__file__).parent.parent.parent / "resources" / "models"
            default_model_path = default_models_dir / "unet_ct_organs.pth"
            
            if default_model_path.exists():
                self.model_path = str(default_model_path)
                self.load_model()
            else:
                logger.log_warning(f"Không tìm thấy mô hình mặc định tại: {default_model_path}")
    
    def preprocess(self, image: np.ndarray) -> Union[np.ndarray, torch.Tensor]:
        """
        Tiền xử lý hình ảnh đầu vào cho U-Net
        
        Args:
            image: Hình ảnh đầu vào (3D numpy array)
            
        Returns:
            Hình ảnh đã xử lý
        """
        # Chỉnh window/level cho ảnh CT
        min_val = -1000
        max_val = 1000
        image = np.clip(image, min_val, max_val)
        
        # Chuẩn hóa về [0, 1]
        image = (image - min_val) / (max_val - min_val)
        
        if HAS_TORCH:
            # Chuyển sang torch tensor
            image_tensor = torch.from_numpy(image).float()
            
            # Thêm chiều batch và channel
            if len(image_tensor.shape) == 3:
                image_tensor = image_tensor.unsqueeze(0).unsqueeze(0)
            
            return image_tensor.to(self.device)
        
        return image

class AutoSegmentation:
    """Lớp chính cho phân đoạn tự động"""
    
    def __init__(self):
        """Khởi tạo AutoSegmentation"""
        self.logger = get_logger("AutoSegmentation")
        self.models = {}
        self.default_model = None
        
        # Khởi tạo các mô hình có sẵn
        self._initialize_models()
    
    def _initialize_models(self):
        """Khởi tạo các mô hình có sẵn"""
        if HAS_TORCH:
            # Tạo thư mục models trong resources nếu chưa tồn tại
            models_dir = Path(__file__).parent.parent.parent / "resources" / "models"
            models_dir.mkdir(parents=True, exist_ok=True)
            
            # Các mô hình có sẵn
            standard_models = {
                "unet_ct_general": "U-Net cho ảnh CT tổng quát",
                "unet_brain": "U-Net cho phân đoạn não",
                "unet_thorax": "U-Net cho phân đoạn ngực",
                "unet_pelvis": "U-Net cho phân đoạn vùng chậu"
            }
            
            # Kiểm tra mô hình nào có sẵn
            for model_name, model_desc in standard_models.items():
                model_path = models_dir / f"{model_name}.pth"
                
                if model_path.exists():
                    self.logger.log_info(f"Tìm thấy mô hình: {model_name} - {model_desc}")
                    self.models[model_name] = {
                        "path": str(model_path),
                        "description": model_desc,
                        "instance": None  # Sẽ tải khi cần
                    }
            
            # Đặt mô hình mặc định
            if "unet_ct_general" in self.models:
                self.default_model = "unet_ct_general"
            elif len(self.models) > 0:
                self.default_model = list(self.models.keys())[0]
            
            # Tìm các model đã lưu
            if not os.path.exists(models_dir):
                os.makedirs(models_dir, exist_ok=True)
            model_dirs = [f for f in os.listdir(models_dir) if os.path.isdir(os.path.join(models_dir, f))]
            
            for model_dir in model_dirs:
                # ... existing code ...
    
    def get_available_models(self) -> List[Dict[str, str]]:
        """
        Lấy danh sách các mô hình có sẵn
        
        Returns:
            Danh sách các mô hình có sẵn
        """
        result = []
        for name, model_info in self.models.items():
            result.append({
                "name": name,
                "description": model_info["description"]
            })
        return result
    
    def segment_volume(self, image_data: np.ndarray, model_name: Optional[str] = None) -> Dict[str, np.ndarray]:
        """
        Phân đoạn tự động từ dữ liệu hình ảnh 3D
        
        Args:
            image_data: Dữ liệu hình ảnh 3D (numpy array)
            model_name: Tên mô hình cần sử dụng (nếu không cung cấp, sử dụng mô hình mặc định)
            
        Returns:
            Dictionary chứa các cấu trúc phân đoạn {tên_cấu_trúc: mask}
        """
        if not HAS_TORCH:
            self.logger.log_error("PyTorch không có sẵn. Không thể thực hiện phân đoạn tự động.")
            return {}
        
        # Sử dụng mô hình mặc định nếu không chỉ định
        if not model_name:
            model_name = self.default_model
        
        if not model_name or model_name not in self.models:
            self.logger.log_error(f"Không tìm thấy mô hình: {model_name}")
            return {}
        
        # Tải mô hình nếu chưa tải
        if self.models[model_name]["instance"] is None:
            start_time = time.time()
            self.logger.log_info(f"Đang tải mô hình: {model_name}")
            
            model_path = self.models[model_name]["path"]
            model = UNetModel(model_path)
            if not model.load_model():
                self.logger.log_error(f"Không thể tải mô hình: {model_name}")
                return {}
            
            self.models[model_name]["instance"] = model
            self.logger.log_info(f"Đã tải mô hình: {model_name} ({time.time() - start_time:.2f} giây)")
        
        # Lấy mô hình
        model = self.models[model_name]["instance"]
        
        # Thực hiện phân đoạn
        start_time = time.time()
        self.logger.log_info("Bắt đầu phân đoạn tự động")
        
        try:
            result = {}
            
            # Thực hiện dự đoán
            prediction = model.predict(image_data)
            
            # Nếu kết quả có nhiều kênh, mỗi kênh là một cấu trúc
            if len(prediction.shape) == 4:
                for i in range(prediction.shape[0]):
                    structure_name = f"AUTO_STRUCT_{i+1}"
                    result[structure_name] = prediction[i]
            else:
                # Nếu chỉ có một cấu trúc
                result["AUTO_STRUCT"] = prediction
            
            self.logger.log_info(f"Hoàn thành phân đoạn tự động ({time.time() - start_time:.2f} giây)")
            return result
            
        except Exception as e:
            self.logger.log_error(f"Lỗi khi thực hiện phân đoạn tự động: {str(e)}")
            return {}
    
    def segment_structure(self, image_data: np.ndarray, structure_name: str, model_name: Optional[str] = None) -> np.ndarray:
        """
        Phân đoạn một cấu trúc cụ thể
        
        Args:
            image_data: Dữ liệu hình ảnh 3D (numpy array)
            structure_name: Tên cấu trúc cần phân đoạn
            model_name: Tên mô hình cần sử dụng (nếu không cung cấp, sẽ chọn mô hình phù hợp)
            
        Returns:
            Mask của cấu trúc
        """
        # Map tên cấu trúc với mô hình phù hợp
        structure_to_model = {
            "BRAIN": "unet_brain",
            "BRAINSTEM": "unet_brain",
            "LUNG_LEFT": "unet_thorax",
            "LUNG_RIGHT": "unet_thorax",
            "HEART": "unet_thorax",
            "SPINAL_CORD": "unet_thorax",
            "LIVER": "unet_thorax",
            "BLADDER": "unet_pelvis",
            "RECTUM": "unet_pelvis",
            "PROSTATE": "unet_pelvis",
        }
        
        # Nếu không chỉ định mô hình, chọn mô hình phù hợp
        if not model_name:
            if structure_name.upper() in structure_to_model:
                model_name = structure_to_model[structure_name.upper()]
                
                # Kiểm tra mô hình có tồn tại không
                if model_name not in self.models:
                    model_name = self.default_model
            else:
                model_name = self.default_model
        
        # Thực hiện phân đoạn
        results = self.segment_volume(image_data, model_name)
        
        # Trả về mask trống nếu không thành công
        if not results:
            return np.zeros_like(image_data)
        
        # Trả về kết quả đầu tiên
        return list(results.values())[0]

# Tạo instance mặc định
auto_segmentation = AutoSegmentation() 