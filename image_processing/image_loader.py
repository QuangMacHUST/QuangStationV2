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
        parser = DICOMParser(directory)
        self.metadata = parser.extract_patient_info()
        
        return self.get_numpy_array(), self.metadata
    
    def load_single_dicom(self, file_path):
        """Tải một ảnh DICOM đơn lẻ"""
        reader = sitk.ImageFileReader()
        reader.SetFileName(file_path)
        self.image_series = reader.Execute()
        
        self.spacing = self.image_series.GetSpacing()
        self.origin = self.image_series.GetOrigin()
        self.direction = self.image_series.GetDirection()
        
        # Trích xuất thông tin cơ bản
        ds = pydicom.dcmread(file_path)
        self.image_type = ds.Modality
        
        # Tạo metadata cơ bản
        self.metadata = {
            'patient_id': ds.PatientID if hasattr(ds, 'PatientID') else 'Unknown',
            'patient_name': str(ds.PatientName) if hasattr(ds, 'PatientName') else 'Unknown',
            'modality': ds.Modality if hasattr(ds, 'Modality') else 'Unknown'
        }
        
        return self.get_numpy_array(), self.metadata
    
    def load_rt_image(self, file_path):
        """Tải ảnh RT Image từ file DICOM"""
        try:
            # Đọc file DICOM
            ds = pydicom.dcmread(file_path)
            
            # Kiểm tra xem có phải là RT Image không
            if ds.SOPClassUID != '1.2.840.10008.5.1.4.1.1.481.1':
                raise ValueError("File không phải là RT Image")
            
            # Lấy dữ liệu pixel
            pixel_data = ds.pixel_array
            
            # Xử lý rescale nếu có
            if hasattr(ds, 'RescaleSlope') and hasattr(ds, 'RescaleIntercept'):
                pixel_data = pixel_data * ds.RescaleSlope + ds.RescaleIntercept
            
            # Tạo SimpleITK image từ numpy array
            sitk_image = sitk.GetImageFromArray(pixel_data)
            
            # Thiết lập thông tin không gian nếu có
            if hasattr(ds, 'PixelSpacing'):
                spacing = (ds.PixelSpacing[0], ds.PixelSpacing[1], 1.0)
                sitk_image.SetSpacing(spacing)
                self.spacing = spacing
            
            if hasattr(ds, 'ImagePositionPatient'):
                origin = tuple(ds.ImagePositionPatient)
                sitk_image.SetOrigin(origin)
                self.origin = origin
            
            self.image_series = sitk_image
            self.image_type = 'RTIMAGE'
            
            # Trích xuất metadata
            parser = DICOMParser(os.path.dirname(file_path))
            rt_image_data = parser.extract_rt_image()
            
            if rt_image_data:
                self.metadata = {
                    'patient_id': ds.PatientID if hasattr(ds, 'PatientID') else 'Unknown',
                    'patient_name': str(ds.PatientName) if hasattr(ds, 'PatientName') else 'Unknown',
                    'modality': 'RTIMAGE',
                    'rt_image_label': rt_image_data.get('rt_image_label', ''),
                    'gantry_angle': rt_image_data.get('gantry_angle', None),
                    'beam_limiting_device_angle': rt_image_data.get('beam_limiting_device_angle', None),
                    'patient_support_angle': rt_image_data.get('patient_support_angle', None),
                    'radiation_machine_name': rt_image_data.get('radiation_machine_name', '')
                }
            else:
                self.metadata = {
                    'patient_id': ds.PatientID if hasattr(ds, 'PatientID') else 'Unknown',
                    'patient_name': str(ds.PatientName) if hasattr(ds, 'PatientName') else 'Unknown',
                    'modality': 'RTIMAGE'
                }
            
            return pixel_data, self.metadata
            
        except Exception as e:
            print(f"Lỗi khi tải RT Image: {e}")
            return None, None
    
    def find_rt_image(self, directory):
        """Tìm file RT Image trong thư mục"""
        parser = DICOMParser(directory)
        return parser.rt_image
    
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