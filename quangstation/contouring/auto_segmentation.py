#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module phân đoạn tự động dựa trên AI cho QuangStation V2.
Sử dụng các mô hình học sâu để phân đoạn cơ quan tự động từ ảnh CT/MRI.
"""

import os
import numpy as np
import time
import json
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
    logger.warning("PyTorch không có sẵn. Một số chức năng phân đoạn tự động sẽ bị vô hiệu hóa.")

class SegmentationModel:
    """
    Lớp cơ sở cho các mô hình phân đoạn tự động.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        self.model = None
        self.device = "cpu"
        self.logger = get_logger(__name__)
        
        # Kiểm tra GPU
        try:
            if torch.cuda.is_available():
                self.device = "cuda"
                self.logger.info("Phát hiện GPU, sử dụng CUDA cho phân đoạn tự động")
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                self.device = "mps"  # Apple Silicon GPU
                self.logger.info("Phát hiện Apple GPU, sử dụng MPS cho phân đoạn tự động")
        except ImportError:
            self.logger.warning("Không tìm thấy PyTorch, sẽ sử dụng CPU cho phân đoạn tự động")
        except Exception as error:
            self.logger.error(f"Lỗi khi kiểm tra GPU: {str(error)}")
    
    def load_model(self):
        """Tải mô hình từ file"""
        try:
            if not HAS_TORCH:
                self.logger.warning("PyTorch không có sẵn. Không thể tải mô hình.")
                return False
            
            if not self.model_path or not os.path.exists(self.model_path):
                self.logger.error(f"Không tìm thấy file mô hình: {self.model_path}")
                return False
            
            # Tải mô hình
            self.model = torch.load(self.model_path, map_location=self.device)
            self.model.eval()  # Đặt ở chế độ đánh giá
            
            self.logger.info(f"Đã tải mô hình từ {self.model_path}")
            return True
            
        except Exception as error:
            self.logger.error(f"Lỗi khi tải mô hình: {str(error)}")
            return False
    
    def preprocess(self, image: np.ndarray) -> Union[np.ndarray, torch.Tensor]:
        """Tiền xử lý hình ảnh đầu vào."""
        raise NotImplementedError("Phương thức này cần được ghi đè trong lớp con")
    
    def predict(self, image: np.ndarray) -> np.ndarray:
        """Thực hiện phân đoạn trên hình ảnh đầu vào."""
        if self.model is None:
            self.load_model()
            
        try:
            import torch
            
            # Tiền xử lý hình ảnh
            input_tensor = self.preprocess(image)
            
            # Thực hiện phân đoạn
            with torch.no_grad():
                output = self.model(input_tensor)
                
            # Hậu xử lý kết quả
            if isinstance(output, tuple):
                output = output[0]  # Lấy đầu ra chính nếu mô hình trả về nhiều đầu ra
                
            # Chuyển về CPU và numpy
            output = output.cpu().numpy()
            
            # Nếu đầu ra là one-hot encoding, chuyển về nhãn
            if len(output.shape) == 4 and output.shape[1] > 1:  # [batch, classes, height, width]
                output = np.argmax(output, axis=1)
                
            # Loại bỏ chiều batch nếu có
            if len(output.shape) == 3 and output.shape[0] == 1:
                output = output[0]
                
            # Đảm bảo kiểu dữ liệu là uint8 cho mask
            output = output.astype(np.uint8)
            
            return output
            
        except Exception as error:
            self.logger.error(f"Lỗi khi thực hiện phân đoạn: {str(error)}")
            raise

class UNetModel(SegmentationModel):
    """
    Mô hình UNet cho phân đoạn tự động.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        super().__init__(model_path)
        
        # Thông số chuẩn hóa
        self.mean = 0.0
        self.std = 1.0
        self.input_size = (256, 256)  # Kích thước đầu vào của mô hình
        
        # Tải thông số chuẩn hóa từ file config nếu có
        if model_path and os.path.exists(model_path):
            config_path = os.path.join(os.path.dirname(model_path), "config.json")
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        self.mean = config.get("mean", self.mean)
                        self.std = config.get("std", self.std)
                        self.input_size = tuple(config.get("input_size", self.input_size))
                except Exception as error:
                    self.logger.warning(f"Không thể tải cấu hình mô hình: {str(error)}")
    
    def preprocess(self, image: np.ndarray) -> Union[np.ndarray, torch.Tensor]:
        """Tiền xử lý hình ảnh cho mô hình UNet."""
        try:
            import torch
            from torchvision import transforms
            from PIL import Image
            
            # Đảm bảo kiểu dữ liệu và phạm vi là 0-255
            if image.dtype != np.uint8:
                image_min = np.min(image)
                image_max = np.max(image)
                
                # Nếu là ảnh CT (HU), chuyển về thang xám 0-255
                if image_min < -100:  # Có thể là ảnh CT
                    # Chuẩn hóa cửa sổ CT (-1000, 1000) thành 0-255
                    image = np.clip(image, -1000, 1000)
                    image = ((image + 1000) / 2000 * 255).astype(np.uint8)
                else:
                    # Chuẩn hóa thông thường
                    image = ((image - image_min) / (image_max - image_min) * 255).astype(np.uint8)
            
            # Chuyển sang ảnh PIL
            pil_image = Image.fromarray(image)
            
            # Đổi kích thước về kích thước đầu vào của mô hình
            pil_image = pil_image.resize(self.input_size, Image.BICUBIC)
            
            # Áp dụng các biến đổi
            transform = transforms.Compose([
                transforms.ToTensor(),
                transforms.Normalize(mean=[self.mean], std=[self.std])
            ])
            
            # Biến đổi và thêm chiều batch
            input_tensor = transform(pil_image).unsqueeze(0)
            
            # Chuyển sang device của mô hình
            input_tensor = input_tensor.to(self.device)
            
            return input_tensor
            
        except ImportError as error:
            self.logger.error(f"Lỗi import thư viện khi tiền xử lý: {str(error)}")
            raise
        except Exception as error:
            self.logger.error(f"Lỗi khi tiền xử lý hình ảnh: {str(error)}")
            raise

class AutoSegmentation:
    """
    Quản lý và thực hiện phân đoạn tự động.
    """
    
    def __init__(self):
        self.models = {}
        self.structure_to_model = {}
        self.logger = get_logger(__name__)
        
        # Khởi tạo các mô hình
        self._initialize_models()
    
    def _initialize_models(self):
        """Khởi tạo các mô hình phân đoạn."""
        try:
            # Kiểm tra xem có PyTorch không
            import torch
        except ImportError:
            self.logger.warning("PyTorch không được cài đặt. Phân đoạn tự động sẽ không khả dụng.")
            return
            
        # Đường dẫn đến thư mục chứa mô hình
        from quangstation.utils.config import get_config
        models_dir = get_config("paths.models_dir", "models")
        
        if not os.path.exists(models_dir):
            self.logger.warning(f"Thư mục mô hình không tồn tại: {models_dir}")
            
            # Tạo thư mục nếu không tồn tại
            try:
                os.makedirs(models_dir, exist_ok=True)
                self.logger.info(f"Đã tạo thư mục mô hình: {models_dir}")
            except Exception as error:
                self.logger.error(f"Không thể tạo thư mục mô hình: {str(error)}")
            return
        
        # Tìm tất cả các file mô hình
        model_files = []
        for root, _, files in os.walk(models_dir):
            for file in files:
                if file.endswith(".pt") or file.endswith(".pth"):
                    model_files.append(os.path.join(root, file))
        
        if not model_files:
            self.logger.warning(f"Không tìm thấy file mô hình nào trong {models_dir}")
            return
            
        # Đọc thông tin mô hình từ file config
        for model_file in model_files:
            model_name = os.path.basename(model_file).split(".")[0]
            config_file = os.path.join(os.path.dirname(model_file), f"{model_name}_config.json")
            
            try:
                # Đọc cấu hình mô hình
                if os.path.exists(config_file):
                    with open(config_file, 'r') as f:
                        model_config = json.load(f)
                else:
                    # Tạo cấu hình mặc định
                    model_config = {
                        "type": "unet",
                        "structures": [model_name],
                        "description": f"Mô hình phân đoạn {model_name}"
                    }
                
                # Khởi tạo mô hình dựa trên loại
                model_type = model_config.get("type", "unet").lower()
                if model_type == "unet":
                    self.models[model_name] = UNetModel(model_file)
                else:
                    self.logger.warning(f"Loại mô hình không được hỗ trợ: {model_type}")
                    continue
                
                # Liên kết các cấu trúc với mô hình
                for structure in model_config.get("structures", [model_name]):
                    self.structure_to_model[structure.lower()] = model_name
                    
                self.logger.info(f"Đã đăng ký mô hình {model_name} cho các cấu trúc: {model_config.get('structures', [model_name])}")
                    
            except Exception as error:
                self.logger.error(f"Lỗi khi khởi tạo mô hình {model_name}: {str(error)}")
    
    def get_available_models(self) -> List[Dict[str, str]]:
        """Lấy danh sách các mô hình có sẵn."""
        result = []
        
        for model_name, model in self.models.items():
            structures = [s for s, m in self.structure_to_model.items() if m == model_name]
            
            result.append({
                "name": model_name,
                "structures": structures,
                "description": f"Mô hình phân đoạn {model_name}"
            })
            
        return result
    
    def segment_volume(self, image_data: np.ndarray, model_name: Optional[str] = None) -> Dict[str, np.ndarray]:
        """Phân đoạn toàn bộ khối hình ảnh."""
        if not self.models:
            self.logger.warning("Không có mô hình phân đoạn nào được tải.")
            return {}
            
        # Nếu không chỉ định model_name, sử dụng mô hình đầu tiên
        if model_name is None:
            model_name = next(iter(self.models.keys()))
        
        # Kiểm tra xem mô hình có tồn tại không
        if model_name not in self.models:
            self.logger.error(f"Không tìm thấy mô hình: {model_name}")
            return {}
            
        try:
            model = self.models[model_name]
            
            # Kích thước của khối hình ảnh
            depth, height, width = image_data.shape
            self.logger.info(f"Bắt đầu phân đoạn khối hình ảnh kích thước {depth}x{height}x{width}")
            
            # Kết quả phân đoạn cho từng lát cắt
            results = {}
            
            # Xác định các cấu trúc mà mô hình này có thể phân đoạn
            structures = [s for s, m in self.structure_to_model.items() if m == model_name]
            
            # Khởi tạo mask cho từng cấu trúc
            for structure in structures:
                results[structure] = np.zeros((depth, height, width), dtype=np.uint8)
            
            # Phân đoạn từng lát cắt
            for z in range(depth):
                try:
                    # Lấy lát cắt
                    slice_data = image_data[z, :, :]
                    
                    # Thực hiện phân đoạn
                    prediction = model.predict(slice_data)
                    
                    # Xử lý kết quả phân đoạn
                    if len(prediction.shape) == 2:  # Nhãn đơn
                        # Đối với mỗi cấu trúc, tạo mask riêng
                        for i, structure in enumerate(structures, 1):
                            results[structure][z] = (prediction == i).astype(np.uint8) * 255
                    else:  # Nhiều nhãn
                        for i, structure in enumerate(structures):
                            results[structure][z] = prediction[i].astype(np.uint8) * 255
                    
                    if (z + 1) % 10 == 0 or z == depth - 1:
                        self.logger.info(f"Đã phân đoạn {z+1}/{depth} lát cắt")
                        
                except Exception as error:
                    self.logger.error(f"Lỗi khi phân đoạn lát cắt {z}: {str(error)}")
            
            self.logger.info(f"Đã hoàn thành phân đoạn với mô hình {model_name}")
            return results
            
        except Exception as error:
            self.logger.error(f"Lỗi khi phân đoạn khối hình ảnh: {str(error)}")
            return {}
    
    def segment_structure(self, image_data: np.ndarray, structure_name: str, model_name: Optional[str] = None) -> np.ndarray:
        """Phân đoạn một cấu trúc cụ thể."""
        # Chuẩn hóa tên cấu trúc
        structure_name_lower = structure_name.lower()
        
        # Nếu không chỉ định model_name, tìm mô hình phù hợp cho cấu trúc
        if model_name is None:
            if structure_name_lower in self.structure_to_model:
                model_name = self.structure_to_model[structure_name_lower]
                
                # Kiểm tra mô hình có tồn tại không
                if model_name not in self.models:
                    model_name = next(iter(self.models.keys()))
            
        # Thực hiện phân đoạn
        results = self.segment_volume(image_data, model_name)
        
        # Trả về mask trống nếu không thành công
        if not results:
            return np.zeros_like(image_data)
        
        # Trả về kết quả đầu tiên
        return list(results.values())[0]

# Tạo instance mặc định
auto_segmentation = AutoSegmentation() 