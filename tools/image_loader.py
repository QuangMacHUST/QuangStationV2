import numpy as np
import pydicom
import os
import SimpleITK as sitk
from data_management.dicom_parser import DICOMParser

class ImageLoader:
    """Lớp tải và xử lý chuỗi ảnh y tế (CT/MRI/PET/SPECT)"""
    
    def __init__(self):
        self.image_series = None
        self.image_type = None
        self.spacing = None
        self.origin = None
        self.direction = None
        self.metadata = {}
    
    def load_dicom_series(self, directory):
        """Tải chuỗi ảnh DICOM từ thư mục"""
        reader = sitk.ImageSeriesReader()
        dicom_names = reader.GetGDCMSeriesFileNames(directory)
        reader.SetFileNames(dicom_names)
        self.image_series = reader.Execute()
        
        # Lấy thông tin không gian
        self.spacing = self.image_series.GetSpacing()
        self.origin = self.image_series.GetOrigin()
        self.direction = self.image_series.GetDirection()
        
        # Xác định loại ảnh từ metadata
        first_dicom = pydicom.dcmread(dicom_names[0])
        self.image_type = first_dicom.Modality
        
        # Trích xuất thông tin cơ bản
        parser = DICOMParser(dicom_names[0])
        self.metadata = parser.extract_patient_info()
        
        return self.get_numpy_array()
    
    def load_single_dicom(self, file_path):
        """Tải một ảnh DICOM đơn lẻ"""
        reader = sitk.ImageFileReader()
        reader.SetFileName(file_path)
        self.image_series = reader.Execute()
        
        self.spacing = self.image_series.GetSpacing()
        self.origin = self.image_series.GetOrigin()
        self.direction = self.image_series.GetDirection()
        
        parser = DICOMParser(file_path)
        self.metadata = parser.extract_patient_info()
        
        return self.get_numpy_array()
    
    def get_numpy_array(self):
        """Chuyển đổi SimpleITK image thành mảng NumPy"""
        if self.image_series is not None:
            return sitk.GetArrayFromImage(self.image_series)
        return None
    
    def get_slice(self, axis, slice_index):
        """Lấy lát cắt theo trục"""
        if self.image_series is None:
            return None
        
        img_array = self.get_numpy_array()
        
        if axis == 'axial' or axis == 'z':
            return img_array[slice_index, :, :]
        elif axis == 'coronal' or axis == 'y':
            return img_array[:, slice_index, :]
        elif axis == 'sagittal' or axis == 'x':
            return img_array[:, :, slice_index]
        else:
            raise ValueError(f"Trục không hợp lệ: {axis}. Sử dụng 'axial', 'coronal', hoặc 'sagittal'")
    
    def apply_window_level(self, image, window, level):
        """Áp dụng windowing cho CT"""
        min_value = level - window/2
        max_value = level + window/2
        
        windowed = np.clip(image, min_value, max_value)
        # Normalize to 0-1 range
        windowed = (windowed - min_value) / window
        
        return windowed
    
    def hounsfield_to_density(self, hu_value):
        """Chuyển đổi giá trị Hounsfield sang mật độ vật lý"""
        # Bảng chuyển đổi đơn giản dựa trên quy tắc thực nghiệm
        if hu_value < -950:
            return 0.001  # Air
        elif hu_value < -700:
            return 0.044  # Lung
        elif hu_value < -98:
            return 0.92   # Fat
        elif hu_value < 14:
            return 1.03   # Water
        elif hu_value < 23:
            return 1.03   # Muscle
        elif hu_value < 100:
            return 1.06   # Soft Tissue
        elif hu_value < 400:
            return 1.15   # Bone
        elif hu_value < 1000:
            return 1.75   # Dense Bone
        else:
            return 1.90   # Metal