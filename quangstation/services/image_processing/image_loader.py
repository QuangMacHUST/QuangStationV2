#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module xử lý và tải hình ảnh y tế.
Hỗ trợ đọc các định dạng DICOM, NIfTI, và các định dạng hình ảnh thông thường.
"""

import numpy as np
import os
import sys
from typing import Dict, List, Tuple, Optional, Any, Union
import SimpleITK as sitk
import cv2
from scipy.ndimage import zoom

from quangstation.core.utils.external_integration import get_module
from quangstation.core.io.dicom_parser import DICOMParser
from quangstation.core.utils.logging import get_logger
from quangstation.core.data_models.image_data import ImageData

logger = get_logger("ImageLoader")

class ImageLoader:
    """
    Lớp xử lý và tải hình ảnh y tế.
    Hỗ trợ nhiều định dạng và cung cấp các phương thức tiền xử lý.
    """
    
    def __init__(self):
        """Khởi tạo ImageLoader"""
        self.supported_formats = {
            'dicom': ['.dcm', '.ima'],
            'nifti': ['.nii', '.nii.gz'],
            'image': ['.jpg', '.jpeg', '.png', '.bmp']
        }
        
    def load_dicom_series(self, folder_path: str) -> Optional[ImageData]:
        """
        Tải chuỗi ảnh DICOM từ thư mục.
        
        Args:
            folder_path: Đường dẫn đến thư mục chứa file DICOM
            
        Returns:
            Optional[ImageData]: Dữ liệu hình ảnh nếu thành công, None nếu thất bại
        """
        try:
            parser = DICOMParser(folder_path)
            image_data, _ = parser.extract_image_volume()
            return image_data
        except Exception as e:
            logger.error(f"Lỗi khi tải chuỗi DICOM từ {folder_path}: {str(e)}")
            return None
            
    def load_nifti(self, file_path: str) -> Optional[ImageData]:
        """
        Tải file NIfTI.
        
        Args:
            file_path: Đường dẫn đến file NIfTI
            
        Returns:
            Optional[ImageData]: Dữ liệu hình ảnh nếu thành công, None nếu thất bại
        """
        try:
            img = sitk.ReadImage(file_path)
            array = sitk.GetArrayFromImage(img)
            spacing = img.GetSpacing()
            origin = img.GetOrigin()
            direction = img.GetDirection()
            
            return ImageData(
                pixel_array=array,
                spacing=spacing,
                origin=origin,
                direction=direction,
                modality='CT',  # Giả định CT
                window_center=40,
                window_width=400
            )
        except Exception as e:
            logger.error(f"Lỗi khi tải file NIfTI {file_path}: {str(e)}")
            return None
            
    def load_image(self, file_path: str) -> Optional[np.ndarray]:
        """
        Tải file hình ảnh thông thường.
        
        Args:
            file_path: Đường dẫn đến file hình ảnh
            
        Returns:
            Optional[np.ndarray]: Mảng pixel nếu thành công, None nếu thất bại
        """
        try:
            img = cv2.imread(file_path)
            if img is None:
                raise ValueError(f"Không thể đọc file {file_path}")
            return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        except Exception as e:
            logger.error(f"Lỗi khi tải file hình ảnh {file_path}: {str(e)}")
            return None
            
    def preprocess_image(self, image: np.ndarray, target_size: Optional[Tuple[int, int]] = None,
                        normalize: bool = True) -> np.ndarray:
        """
        Tiền xử lý hình ảnh.
        
        Args:
            image: Mảng pixel đầu vào
            target_size: Kích thước đích (width, height)
            normalize: Chuẩn hóa pixel về khoảng [0,1]
            
        Returns:
            np.ndarray: Hình ảnh đã xử lý
        """
        # Resize nếu cần
        if target_size is not None:
            scale_x = target_size[0] / image.shape[1]
            scale_y = target_size[1] / image.shape[0]
            image = zoom(image, (scale_y, scale_x) + (1,) * (image.ndim - 2))
            
        # Chuẩn hóa nếu cần
        if normalize:
            image = image.astype(float)
            if image.max() > image.min():
                image = (image - image.min()) / (image.max() - image.min())
                
        return image
        
    def auto_window_level(self, image: np.ndarray, percentile_low: float = 1,
                         percentile_high: float = 99) -> Tuple[float, float]:
        """
        Tự động tính window/level dựa trên histogram.
        
        Args:
            image: Mảng pixel đầu vào
            percentile_low: Phần trăm dưới
            percentile_high: Phần trăm trên
            
        Returns:
            Tuple[float, float]: (window_center, window_width)
        """
        p_low = np.percentile(image, percentile_low)
        p_high = np.percentile(image, percentile_high)
        window_width = p_high - p_low
        window_center = (p_high + p_low) / 2
        return window_center, window_width