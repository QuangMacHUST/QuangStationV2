import numpy as np
import os
import sys
import pydicom
import SimpleITK as sitk
from typing import Dict, List, Tuple, Optional, Any, Union
import cv2
from scipy.ndimage import zoom

# Import module DICOMParser từ data_management
from quangstation.data_management.dicom_parser import DICOMParser
from quangstation.utils.logging import get_logger

logger = get_logger("ImageLoader")

class ImageLoader:
    """
    Lớp tải và xử lý chuỗi ảnh y tế (CT/MRI/PET/SPECT).
    Hỗ trợ hiển thị theo các trục Axial, Coronal, Sagittal và dựng mô hình 3D.
    """
    
    # Các hằng số cho các trục
    AXIAL = 0
    CORONAL = 1
    SAGITTAL = 2
    
    def __init__(self):
        self.image_series = None  # Đối tượng SimpleITK.Image
        self.image_type = None    # Loại ảnh (CT, MRI, PET, SPECT)
        self.spacing = None       # Khoảng cách giữa các pixel (mm)
        self.origin = None        # Điểm gốc của ảnh (mm)
        self.direction = None     # Ma trận hướng
        self.metadata = {}        # Metadata từ DICOM
        self.volume_data = None   # Dữ liệu thể tích dạng numpy.ndarray
        self.pixel_data_loaded = False  # Flag kiểm tra đã tải pixel data hay chưa
        self.window_center = None  # Window center mặc định
        self.window_width = None   # Window width mặc định
        self.dicom_parser = None   # Đối tượng DICOMParser
    
    def load_dicom_series(self, directory: str) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Tải chuỗi ảnh DICOM từ thư mục và tạo thể tích 3D.
        
        Args:
            directory: Đường dẫn đến thư mục chứa các file DICOM
            
        Returns:
            Tuple[np.ndarray, Dict]: Mảng numpy 3D và metadata
        """
        logger.info(f"Đang tải dữ liệu DICOM từ thư mục: {directory}")
        
        try:
            # Sử dụng DICOMParser để phân loại và lấy danh sách file
            self.dicom_parser = DICOMParser(directory)
            
            # Lấy thông tin bệnh nhân
            patient_info = self.dicom_parser.extract_patient_info()
            
            # Kiểm tra xem có hình ảnh CT/MRI/PET/SPECT không
            modalities = self.dicom_parser.get_modalities()
            
            # Xác định modality để tải dữ liệu
            if modalities['CT'] > 0:
                self.image_type = 'CT'
            elif modalities['MRI'] > 0:
                self.image_type = 'MRI'
            elif modalities['PET'] > 0:
                self.image_type = 'PET'
            elif modalities['SPECT'] > 0:
                self.image_type = 'SPECT'
            else:
                logger.error("Không tìm thấy dữ liệu ảnh y tế trong thư mục")
                return None, {}
                
            logger.info(f"Phát hiện dữ liệu hình ảnh kiểu: {self.image_type}")
            
            # Trích xuất khối dữ liệu hình ảnh
            volume_data, metadata = self.dicom_parser.extract_image_volume(self.image_type)
            
            if volume_data is None or volume_data.size == 0:
                logger.error("Không thể tạo khối dữ liệu hình ảnh")
                return None, {}
                
            # Lưu dữ liệu vào thuộc tính
            self.volume_data = volume_data
            self.metadata = metadata
            
            # Thiết lập thông tin không gian
            if 'pixel_spacing' in metadata and metadata['pixel_spacing'] is not None:
                pixel_spacing = metadata['pixel_spacing']
                if len(pixel_spacing) >= 2:
                    # SimpleITK spacing theo thứ tự [z, y, x]
                    slice_thickness = metadata.get('slice_thickness', 1.0)
                    self.spacing = (float(pixel_spacing[0]), float(pixel_spacing[1]), float(slice_thickness))
                else:
                    self.spacing = (1.0, 1.0, 1.0)
            else:
                self.spacing = (1.0, 1.0, 1.0)
                logger.warning("Không tìm thấy thông tin pixel spacing, sử dụng giá trị mặc định (1.0, 1.0, 1.0)")
            
            # Xác định origin
            if hasattr(metadata.get('slices', [{}])[0], 'ImagePositionPatient'):
                first_slice = metadata['slices'][0]
                self.origin = (
                    float(first_slice.ImagePositionPatient[0]),
                    float(first_slice.ImagePositionPatient[1]),
                    float(first_slice.ImagePositionPatient[2])
                )
            else:
                self.origin = (0.0, 0.0, 0.0)
                logger.warning("Không tìm thấy thông tin origin, sử dụng giá trị mặc định (0.0, 0.0, 0.0)")
            
            # Xác định direction
            if hasattr(metadata.get('slices', [{}])[0], 'ImageOrientationPatient'):
                first_slice = metadata['slices'][0]
                orientation = first_slice.ImageOrientationPatient
                # Tạo ma trận hướng 3x3 từ 6 giá trị orientation
                self.direction = (
                    float(orientation[0]), float(orientation[1]), float(orientation[2]),
                    float(orientation[3]), float(orientation[4]), float(orientation[5]),
                    0.0, 0.0, 1.0  # Giả định trục Z là thẳng đứng
                )
            else:
                self.direction = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
                logger.warning("Không tìm thấy thông tin direction, sử dụng giá trị mặc định (identity)")
            
            # Thiết lập window/level mặc định dựa trên loại ảnh
            self._set_default_window_level()
            
            # Đánh dấu đã tải pixel data
            self.pixel_data_loaded = True
            
            logger.info(f"Đã tải thành công dữ liệu ảnh {self.image_type}, kích thước: {self.volume_data.shape}")
            logger.info(f"Spacing: {self.spacing}, Origin: {self.origin}")
            
            return self.volume_data, patient_info
            
        except Exception as error:
            import traceback
            logger.error(f"Lỗi khi tải dữ liệu DICOM: {str(error)}")
            logger.error(traceback.format_exc())
            return None, {}
    
    def _set_default_window_level(self):
        """Thiết lập giá trị mặc định cho window/level dựa vào loại ảnh"""
        if self.image_type == 'CT':
            self.window_center = 40    # Giá trị cho soft tissue
            self.window_width = 400
        elif self.image_type == 'MRI':
            # Tính toán dựa trên dữ liệu
            if self.volume_data is not None:
                p5 = np.percentile(self.volume_data, 5)
                p95 = np.percentile(self.volume_data, 95)
                self.window_width = p95 - p5
                self.window_center = (p95 + p5) / 2
            else:
                self.window_center = 500
                self.window_width = 1000
        elif self.image_type == 'PET' or self.image_type == 'SPECT':
            # Cho PET/SPECT thường là SUV hoặc count
            if self.volume_data is not None:
                p99 = np.percentile(self.volume_data, 99)
                self.window_width = p99
                self.window_center = p99 / 2
            else:
                self.window_center = 5
                self.window_width = 10
    
    def get_slice(self, slice_index: int, orientation: int = AXIAL, apply_window: bool = True) -> np.ndarray:
        """
        Lấy một lát cắt theo hướng chỉ định.
        
        Args:
            slice_index: Chỉ số lát cắt
            orientation: Hướng lát cắt (AXIAL=0, CORONAL=1, SAGITTAL=2)
            apply_window: Áp dụng cửa sổ Hounsfield cho CT
            
        Returns:
            np.ndarray: Lát cắt dạng ảnh 2D
        """
        if not self.pixel_data_loaded or self.volume_data is None:
            logger.error("Dữ liệu ảnh chưa được tải. Hãy gọi load_dicom_series trước.")
            raise ValueError("Dữ liệu ảnh chưa được tải.")
            
        # Lấy slice theo orientation
        if orientation == self.AXIAL:  # Axial (z-plane)
            if slice_index >= 0 and slice_index < self.volume_data.shape[0]:
                slice_data = self.volume_data[slice_index, :, :]
            else:
                raise IndexError(f"Chỉ số lát cắt axial nằm ngoài phạm vi: {slice_index}. Phạm vi hợp lệ: 0-{self.volume_data.shape[0]-1}")
        elif orientation == self.CORONAL:  # Coronal (y-plane)
            if slice_index >= 0 and slice_index < self.volume_data.shape[1]:
                slice_data = self.volume_data[:, slice_index, :]
            else:
                raise IndexError(f"Chỉ số lát cắt coronal nằm ngoài phạm vi: {slice_index}. Phạm vi hợp lệ: 0-{self.volume_data.shape[1]-1}")
        elif orientation == self.SAGITTAL:  # Sagittal (x-plane)
            if slice_index >= 0 and slice_index < self.volume_data.shape[2]:
                slice_data = self.volume_data[:, :, slice_index]
            else:
                raise IndexError(f"Chỉ số lát cắt sagittal nằm ngoài phạm vi: {slice_index}. Phạm vi hợp lệ: 0-{self.volume_data.shape[2]-1}")
        else:
            raise ValueError(f"Orientation không hợp lệ: {orientation}. Sử dụng AXIAL(0), CORONAL(1), hoặc SAGITTAL(2).")
            
        # Áp dụng cửa sổ Hounsfield nếu là CT
        if apply_window and self.image_type == 'CT':
            slice_data = self.apply_window_level(slice_data, self.window_center, self.window_width)
            
        return slice_data
    
    def apply_window_level(self, image_data: np.ndarray, window_center: float, window_width: float) -> np.ndarray:
        """
        Áp dụng cửa sổ Hounsfield cho ảnh CT.
        
        Args:
            image_data: Dữ liệu ảnh gốc
            window_center: Trung tâm cửa sổ
            window_width: Độ rộng cửa sổ
            
        Returns:
            np.ndarray: Ảnh đã áp dụng cửa sổ, giá trị từ 0-255
        """
        # Tính toán min và max
        min_value = window_center - window_width / 2
        max_value = window_center + window_width / 2
        
        # Clip dữ liệu trong khoảng [min_value, max_value]
        windowed = np.clip(image_data, min_value, max_value)
        
        # Chuyển đổi sang khoảng [0, 255]
        if max_value != min_value:  # Tránh chia cho 0
            windowed = ((windowed - min_value) / (max_value - min_value)) * 255.0
        else:
            windowed = np.zeros_like(image_data)
            
        return windowed.astype(np.uint8)
    
    def set_window_level(self, window_center: float, window_width: float):
        """
        Thiết lập thông số cửa sổ mới.
        
        Args:
            window_center: Trung tâm cửa sổ mới
            window_width: Độ rộng cửa sổ mới
        """
        self.window_center = window_center
        self.window_width = window_width
        logger.info(f"Đã thiết lập cửa sổ mới: C={window_center}, W={window_width}")
    
    def get_volume_shape(self) -> Tuple[int, int, int]:
        """
        Lấy kích thước thể tích dữ liệu.
            
        Returns:
            Tuple[int, int, int]: Kích thước (depth, height, width)
        """
        if self.volume_data is None:
            logger.error("Dữ liệu thể tích chưa được tải.")
            raise ValueError("Dữ liệu thể tích chưa được tải.")
        
        return self.volume_data.shape
    
    def get_volume_center(self) -> Tuple[float, float, float]:
        """
        Lấy tọa độ tâm thể tích theo tọa độ DICOM (mm).
        
        Returns:
            Tuple[float, float, float]: Tọa độ tâm (x, y, z) mm
        """
        if self.volume_data is None or self.origin is None or self.spacing is None:
            logger.error("Dữ liệu thể tích hoặc thông tin không gian chưa được tải.")
            raise ValueError("Dữ liệu không đầy đủ để tính tọa độ tâm.")
            
        shape = self.volume_data.shape  # (z, y, x)
        
        # Tính tọa độ tâm (mm) = origin + spacing * (shape / 2)
        center_x = self.origin[0] + self.spacing[0] * shape[2] / 2
        center_y = self.origin[1] + self.spacing[1] * shape[1] / 2
        center_z = self.origin[2] + self.spacing[2] * shape[0] / 2
        
        return (center_x, center_y, center_z)
    
    def resample_volume(self, new_spacing: Tuple[float, float, float]) -> np.ndarray:
        """
        Resampling thể tích dữ liệu theo spacing mới.
        
        Args:
            new_spacing: Khoảng cách mới (mm) theo trục (x, y, z)
            
        Returns:
            np.ndarray: Thể tích đã được resampling
        """
        if self.volume_data is None or self.spacing is None:
            logger.error("Dữ liệu thể tích hoặc thông tin không gian chưa được tải.")
            raise ValueError("Dữ liệu không đầy đủ để thực hiện resampling.")
            
        # Tính tỷ lệ scaling
        spacing_ratio = (
            self.spacing[2] / new_spacing[0],  # x
            self.spacing[1] / new_spacing[1],  # y
            self.spacing[0] / new_spacing[2]   # z
        )
        
        # Tính kích thước mới
        new_shape = (
            int(round(self.volume_data.shape[0] * spacing_ratio[2])),
            int(round(self.volume_data.shape[1] * spacing_ratio[1])),
            int(round(self.volume_data.shape[2] * spacing_ratio[0]))
        )
        
        # Sử dụng scipy.ndimage.zoom để resampling
        resampled_volume = zoom(self.volume_data, spacing_ratio, order=3)
        
        logger.info(f"Đã resampling thể tích từ {self.volume_data.shape} sang {resampled_volume.shape}")
        
        return resampled_volume
    
    def generate_mpr_views(self, slice_indices: Dict[str, int]) -> Dict[str, np.ndarray]:
        """
        Tạo các view MPR (Multiplanar Reconstruction) cho điểm hiện tại.
        
        Args:
            slice_indices: Dict chứa chỉ số slice cho mỗi hướng {'axial': idx, 'coronal': idx, 'sagittal': idx}
            
        Returns:
            Dict[str, np.ndarray]: Dict chứa các view {'axial': img, 'coronal': img, 'sagittal': img}
        """
        if not self.pixel_data_loaded:
            raise ValueError("Dữ liệu ảnh chưa được tải.")
            
        result = {}
            
        # Lấy các lát cắt theo các hướng
        if 'axial' in slice_indices:
            result['axial'] = self.get_slice(slice_indices['axial'], orientation=self.AXIAL)
            
        if 'coronal' in slice_indices:
            result['coronal'] = self.get_slice(slice_indices['coronal'], orientation=self.CORONAL)
            
        if 'sagittal' in slice_indices:
            result['sagittal'] = self.get_slice(slice_indices['sagittal'], orientation=self.SAGITTAL)
            
        return result
    
    def get_hounsfield_value(self, x: int, y: int, z: int) -> float:
        """
        Lấy giá trị Hounsfield tại một điểm trong thể tích.
        
        Args:
            x, y, z: Tọa độ điểm trong thể tích (voxel coordinates)
            
        Returns:
            float: Giá trị Hounsfield
        """
        if self.volume_data is None:
            raise ValueError("Dữ liệu thể tích chưa được tải.")
            
        if (0 <= z < self.volume_data.shape[0] and 
            0 <= y < self.volume_data.shape[1] and 
            0 <= x < self.volume_data.shape[2]):
            return float(self.volume_data[z, y, x])
        else:
            raise IndexError("Tọa độ nằm ngoài phạm vi thể tích.")
    
    def export_to_nifti(self, output_path: str):
        """
        Xuất dữ liệu thể tích sang định dạng NIfTI.
        
        Args:
            output_path: Đường dẫn đến file NIfTI xuất ra
        """
        if self.image_series is None:
            raise ValueError("Dữ liệu ảnh chưa được tải.")
            
        sitk.WriteImage(self.image_series, output_path)
        logger.info(f"Đã xuất dữ liệu thể tích sang file NIfTI: {output_path}")
    
    def create_3d_rendering_data(self, threshold_min: Optional[float] = None, threshold_max: Optional[float] = None) -> np.ndarray:
        """
        Tạo dữ liệu cho việc dựng hình 3D từ thể tích hiện tại.
        
        Args:
            threshold_min: Ngưỡng dưới (HU) cho dựng hình
            threshold_max: Ngưỡng trên (HU) cho dựng hình
            
        Returns:
            np.ndarray: Thể tích đã được áp dụng ngưỡng
        """
        if self.volume_data is None:
            raise ValueError("Dữ liệu thể tích chưa được tải.")
            
        # Mặc định ngưỡng dựa vào loại ảnh
        if threshold_min is None:
            if self.image_type == 'CT':
                threshold_min = 400  # Xương
            else:
                threshold_min = np.percentile(self.volume_data, 75)
                
        if threshold_max is None:
            if self.image_type == 'CT':
                threshold_max = 3000
            else:
                threshold_max = np.percentile(self.volume_data, 99)
        
        # Áp dụng ngưỡng
        thresholded_volume = np.clip(self.volume_data, threshold_min, threshold_max)
        
        # Chuẩn hóa về khoảng [0, 1]
        if threshold_max != threshold_min:
            thresholded_volume = (thresholded_volume - threshold_min) / (threshold_max - threshold_min)
        else:
            thresholded_volume = np.zeros_like(self.volume_data)
            
        logger.info(f"Đã tạo dữ liệu cho dựng hình 3D với ngưỡng [{threshold_min}, {threshold_max}]")
        
        return thresholded_volume