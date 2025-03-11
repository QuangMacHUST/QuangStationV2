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
import sys
import requests
import tempfile
from zipfile import ZipFile
from tqdm import tqdm

from quangstation.utils.logging import get_logger

logger = get_logger(__name__)

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
        
        # Kiểm tra GPU
        try:
            if torch.cuda.is_available():
                self.device = "cuda"
                logger.info("Phát hiện GPU, sử dụng CUDA cho phân đoạn tự động")
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                self.device = "mps"  # Apple Silicon GPU
                logger.info("Phát hiện Apple GPU, sử dụng MPS cho phân đoạn tự động")
        except ImportError:
            logger.warning("Không tìm thấy PyTorch, sẽ sử dụng CPU cho phân đoạn tự động")
        except Exception as error:
            logger.error(f"Lỗi khi kiểm tra GPU: {str(error)}")
    
    def load_model(self):
        """Tải mô hình từ file"""
        try:
            if not HAS_TORCH:
                logger.warning("PyTorch không có sẵn. Không thể tải mô hình.")
                return False
            
            if not self.model_path or not os.path.exists(self.model_path):
                logger.error(f"Không tìm thấy file mô hình: {self.model_path}")
                return False
            
            # Tải mô hình
            self.model = torch.load(self.model_path, map_location=self.device)
            self.model.eval()  # Đặt ở chế độ đánh giá
            
            logger.info(f"Đã tải mô hình từ {self.model_path}")
            return True
            
        except Exception as error:
            logger.error(f"Lỗi khi tải mô hình: {str(error)}")
            return False
    
    def preprocess(self, image: np.ndarray) -> Union[np.ndarray, torch.Tensor]:
        """
        Tiền xử lý hình ảnh đầu vào để chuẩn bị cho quá trình phân đoạn.
        Base implementation cung cấp các bước tiền xử lý cơ bản.
        
        Args:
            image: Hình ảnh đầu vào dưới dạng numpy array 3D (Z, Y, X)
            
        Returns:
            Tensor hoặc numpy array đã được tiền xử lý
        """
        import torch
        logger.debug(f"Tiền xử lý hình ảnh kích thước: {image.shape}")
        
        # 1. Chuẩn hóa giá trị HU về khoảng [-1, 1]
        # Thông thường HU trong khoảng [-1000, 3000]
        image = np.clip(image, -1000, 3000)
        image = (image + 1000) / 4000 * 2 - 1
        
        # 2. Đảm bảo kích thước phù hợp với mô hình
        # Thông thường, mô hình U-Net yêu cầu đầu vào có kích thước là lũy thừa của 2
        target_size = (256, 256, 256)  # Kích thước mục tiêu
        
        # Crop hoặc pad hình ảnh để có kích thước phù hợp
        current_shape = image.shape
        pad_width = []
        
        for i in range(3):
            if i < len(current_shape):
                diff = target_size[i] - current_shape[i]
                # Nếu kích thước hiện tại nhỏ hơn kích thước mục tiêu, thêm padding
                if diff > 0:
                    pad_before = diff // 2
                    pad_after = diff - pad_before
                    pad_width.append((pad_before, pad_after))
                # Nếu kích thước hiện tại lớn hơn, cắt bớt
                elif diff < 0:
                    crop_before = abs(diff) // 2
                    pad_width.append((-crop_before, crop_before + diff))
                else:
                    pad_width.append((0, 0))
            else:
                # Nếu không có chiều này, thêm mới hoàn toàn
                pad_width.append((0, target_size[i]))
        
        # Áp dụng padding hoặc cropping
        processed_image = np.pad(image, pad_width, mode='constant', constant_values=-1)
        
        # 3. Thêm chiều batch và channel nếu cần thiết
        processed_image = np.expand_dims(processed_image, axis=0)  # Thêm chiều batch
        processed_image = np.expand_dims(processed_image, axis=0)  # Thêm chiều channel
        
        # 4. Chuyển đổi thành tensor PyTorch
        processed_tensor = torch.from_numpy(processed_image).float().to(self.device)
        
        logger.debug(f"Kết quả tiền xử lý: tensor kích thước {processed_tensor.shape}")
        self.original_shape = current_shape  # Lưu lại kích thước gốc để sử dụng trong postprocessing
        
        return processed_tensor
    
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
            logger.error(f"Lỗi khi thực hiện phân đoạn: {str(error)}")
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
                    logger.warning(f"Không thể tải cấu hình mô hình: {str(error)}")
    
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
            logger.error(f"Lỗi import thư viện khi tiền xử lý: {str(error)}")
            raise
        except Exception as error:
            logger.error(f"Lỗi khi tiền xử lý hình ảnh: {str(error)}")
            self.logger.error(f"Lỗi khi tiền xử lý hình ảnh: {str(error)}")
            raise

class AutoSegmentation:
    """
    Quản lý phân đoạn tự động sử dụng mô hình học sâu.
    """
    
    MODEL_REPO_URL = "https://github.com/open-radiation-therapy/model-zoo/releases/download/"
    
    def __init__(self):
        """Khởi tạo các mô hình và danh sách mô hình có sẵn."""
        self.models = {}
        self.available_models = []
        self.default_model = None
        self.model_dir = self._get_model_directory()
        self.logger = get_logger("AutoSegmentation")
        
        # Kiểm tra và tạo thư mục models nếu chưa tồn tại
        Path(self.model_dir).mkdir(parents=True, exist_ok=True)
        
        # Khởi tạo các mô hình
        self._initialize_models()
        
    def _get_model_directory(self) -> str:
        """Lấy thư mục lưu trữ mô hình."""
        # Ưu tiên thư mục models trong thư mục hiện tại
        local_models = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../models")
        if os.path.exists(local_models):
            return local_models
            
        # Thư mục người dùng
        user_models = os.path.join(str(Path.home()), ".quangstation", "models")
        Path(user_models).mkdir(parents=True, exist_ok=True)
        return user_models
        
    def _initialize_models(self):
        """Tìm và khởi tạo các mô hình có sẵn."""
        self.logger.info("Đang khởi tạo các mô hình phân đoạn tự động...")
        
        # Kiểm tra xem có PyTorch không
        if not HAS_TORCH:
            self.logger.warning("PyTorch không có sẵn. Không thể khởi tạo mô hình phân đoạn tự động.")
            return
            
        # Tạo danh sách mô hình có sẵn
        model_config_path = os.path.join(self.model_dir, "model_list.json")
        
        if os.path.exists(model_config_path):
            try:
                with open(model_config_path, 'r', encoding='utf-8') as f:
                    self.available_models = json.load(f)
                    self.logger.info(f"Đã tải danh sách {len(self.available_models)} mô hình")
            except Exception as e:
                self.logger.error(f"Lỗi khi tải danh sách mô hình: {str(e)}")
                self.available_models = self._create_default_model_list()
        else:
            self.available_models = self._create_default_model_list()
            
            # Lưu danh sách mẫu
            try:
                with open(model_config_path, 'w', encoding='utf-8') as f:
                    json.dump(self.available_models, f, indent=2, ensure_ascii=False)
            except Exception as e:
                self.logger.error(f"Lỗi khi lưu danh sách mô hình: {str(e)}")
        
        # Tải mô hình mặc định nếu được cấu hình
        default_models = [m for m in self.available_models if m.get('is_default', False)]
        if default_models:
            default_model = default_models[0]
            try:
                model_path = os.path.join(self.model_dir, default_model['filename'])
                
                # Tự động tải mô hình nếu chưa tồn tại
                if not os.path.exists(model_path) and default_model.get('auto_download', False):
                    self.logger.info(f"Mô hình mặc định không tồn tại. Đang tải về...")
                    self._download_model(default_model['name'], default_model.get('version', 'v1.0'))
                
                if os.path.exists(model_path):
                    self.default_model = self._load_model_by_name(default_model['name'])
                    self.logger.info(f"Đã tải mô hình mặc định: {default_model['name']}")
            except Exception as e:
                self.logger.error(f"Lỗi khi tải mô hình mặc định: {str(e)}")
                
    def _create_default_model_list(self) -> List[Dict[str, Any]]:
        """Tạo danh sách mô hình mặc định."""
        return [
            {
                "name": "general_ct",
                "display_name": "Mô hình phân đoạn đa cơ quan CT",
                "description": "Mô hình phân đoạn các cơ quan phổ biến từ ảnh CT",
                "structures": ["BODY", "LUNGS", "HEART", "LIVER", "KIDNEYS", "SPINAL_CORD", "BRAIN"],
                "modality": "CT", 
                "filename": "general_ct_v1.0.pt",
                "version": "v1.0",
                "url": "v1.0/general_ct_v1.0.zip",
                "is_default": True,
                "auto_download": True,
                "model_type": "UNet",
                "size_mb": 45.8
            },
            {
                "name": "thorax_ct",
                "display_name": "Mô hình phân đoạn vùng ngực",
                "description": "Mô hình chuyên biệt cho vùng ngực",
                "structures": ["LUNGS", "HEART", "ESOPHAGUS", "TRACHEA", "SPINAL_CORD"],
                "modality": "CT",
                "filename": "thorax_ct_v1.0.pt",
                "version": "v1.0",
                "url": "v1.0/thorax_ct_v1.0.zip",
                "is_default": False,
                "auto_download": False, 
                "model_type": "UNet",
                "size_mb": 48.2
            },
            {
                "name": "pelvis_ct",
                "display_name": "Mô hình phân đoạn vùng chậu",
                "description": "Mô hình chuyên biệt cho vùng chậu",
                "structures": ["BLADDER", "RECTUM", "PROSTATE", "FEMORAL_HEADS"],
                "modality": "CT",
                "filename": "pelvis_ct_v1.0.pt",
                "version": "v1.0",
                "url": "v1.0/pelvis_ct_v1.0.zip",
                "is_default": False,
                "auto_download": False,
                "model_type": "UNet",
                "size_mb": 46.4
            }
        ]
        
    def _download_model(self, model_name: str, version: str = "v1.0") -> bool:
        """Tải mô hình từ kho lưu trữ trực tuyến."""
        # Tìm thông tin mô hình
        model_info = None
        for model in self.available_models:
            if model['name'] == model_name:
                model_info = model
                break
                
        if not model_info:
            self.logger.error(f"Không tìm thấy thông tin mô hình {model_name}")
            return False
            
        try:
            # Tạo URL tải về
            download_url = f"{self.MODEL_REPO_URL}{model_info.get('url', f'{version}/{model_name}_{version}.zip')}"
            self.logger.info(f"Đang tải mô hình từ {download_url}")
            
            # Tải mô hình
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
                temp_path = temp_file.name
                
                response = requests.get(download_url, stream=True)
                total_size = int(response.headers.get('content-length', 0))
                block_size = 1024  # 1 Kibibyte
                
                self.logger.info(f"Kích thước mô hình: {total_size / (1024*1024):.2f} MB")
                
                t = tqdm(total=total_size, unit='iB', unit_scale=True)
                for data in response.iter_content(block_size):
                    t.update(len(data))
                    temp_file.write(data)
                t.close()
                
                if total_size != 0 and t.n != total_size:
                    self.logger.error("Lỗi khi tải mô hình - kích thước không khớp")
                    return False
            
            # Giải nén mô hình
            self.logger.info(f"Đang giải nén mô hình vào {self.model_dir}")
            with ZipFile(temp_path, 'r') as zip_ref:
                zip_ref.extractall(self.model_dir)
                
            # Xóa file tạm
            os.unlink(temp_path)
            
            self.logger.info(f"Đã tải và giải nén thành công mô hình {model_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Lỗi khi tải mô hình {model_name}: {str(e)}")
            return False
        
    def _load_model_by_name(self, model_name: str) -> Optional[SegmentationModel]:
        """Tải mô hình theo tên."""
        # Kiểm tra xem mô hình đã tải chưa
        if model_name in self.models:
            return self.models[model_name]
            
        # Tìm thông tin mô hình
        model_info = None
        for model in self.available_models:
            if model['name'] == model_name:
                model_info = model
                break
                
        if not model_info:
            self.logger.error(f"Không tìm thấy thông tin mô hình {model_name}")
            return None
            
        try:
            # Tạo đường dẫn đến file mô hình
            model_path = os.path.join(self.model_dir, model_info['filename'])
            
            # Kiểm tra xem file mô hình tồn tại không
            if not os.path.exists(model_path):
                self.logger.warning(f"Không tìm thấy file mô hình {model_path}")
                
                # Hỏi người dùng có muốn tải về không
                download = model_info.get('auto_download', False)
                if download:
                    self.logger.info(f"Đang tải mô hình {model_name}...")
                    if not self._download_model(model_name, model_info.get('version', 'v1.0')):
                        return None
                else:
                    return None
            
            # Tạo mô hình dựa trên loại
            model_type = model_info.get('model_type', 'UNet')
            if model_type == 'UNet':
                segmentation_model = UNetModel(model_path)
            else:
                self.logger.warning(f"Loại mô hình {model_type} chưa được hỗ trợ. Sử dụng UNet mặc định.")
                segmentation_model = UNetModel(model_path)
                
            # Tải mô hình
            segmentation_model.load_model()
            
            # Lưu mô hình vào cache
            self.models[model_name] = segmentation_model
            
            return segmentation_model
            
        except Exception as e:
            self.logger.error(f"Lỗi khi tải mô hình {model_name}: {str(e)}")
            return None
    
    def get_available_models(self) -> List[Dict[str, str]]:
        """Lấy danh sách các mô hình có sẵn."""
        # Chuyển đổi thành danh sách đơn giản hơn
        available_models = []
        for model in self.available_models:
            available_models.append({
                'name': model['name'],
                'display_name': model.get('display_name', model['name']),
                'description': model.get('description', ''),
                'structures': ', '.join(model.get('structures', [])),
                'modality': model.get('modality', 'CT'),
                'size_mb': model.get('size_mb', 0)
            })
        return available_models
        
    def download_model(self, model_name: str) -> bool:
        """Tải mô hình theo tên từ kho lưu trữ."""
        return self._download_model(model_name)
    
    def segment_volume(self, image_data: np.ndarray, model_name: Optional[str] = None) -> Dict[str, np.ndarray]:
        """
        Phân đoạn tự động các cấu trúc giải phẫu từ dữ liệu ảnh sử dụng mô hình đã chọn.
        
        Args:
            image_data: Dữ liệu ảnh 3D (numpy array)
            model_name: Tên mô hình sử dụng (nếu None, sử dụng mô hình mặc định)
            
        Returns:
            Dict map từ tên cấu trúc sang mask 3D
        """
        try:
            # Chọn mô hình
            model = None
            if model_name:
                model = self._load_model_by_name(model_name)
            
            if model is None and self.default_model is not None:
                model = self.default_model
                model_name = [m['name'] for m in self.available_models if m.get('is_default', False)][0]
                
            if model is None:
                self.logger.error("Không tìm thấy mô hình phù hợp và không có mô hình mặc định")
                return {}
                
            self.logger.info(f"Sử dụng mô hình {model_name} để phân đoạn tự động")
            
            # Tìm thông tin cấu trúc hỗ trợ từ mô hình
            structures = []
            for model_info in self.available_models:
                if model_info['name'] == model_name:
                    structures = model_info.get('structures', [])
                    break
                    
            # Chạy dự đoán
            masks = model.predict(image_data)
            
            # Tạo kết quả
            results = {}
            for i, structure_name in enumerate(structures):
                if i < masks.shape[0]:  # Đảm bảo chỉ số hợp lệ
                    results[structure_name] = masks[i] > 0.5  # Chuyển sang mask binary
                
            return results
            
        except Exception as e:
            self.logger.error(f"Lỗi khi phân đoạn tự động: {str(e)}")
            return {}

# Tạo instance mặc định
auto_segmentation = AutoSegmentation() 