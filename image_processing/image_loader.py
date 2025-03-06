import numpy as np
import os
import sys

# Thêm thư viện pydicom và SimpleITK
try:
    import pydicom
except ImportError:
    print("Thư viện pydicom chưa được cài đặt. Đang cài đặt...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pydicom"])
    import pydicom

try:
    import SimpleITK as sitk
except ImportError:
    print("Thư viện SimpleITK chưa được cài đặt. Đang cài đặt...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "SimpleITK"])
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
        """Tải một file DICOM đơn lẻ"""
        # Đọc file DICOM
        ds = pydicom.dcmread(file_path)
        
        # Tạo một SimpleITK Image từ dữ liệu DICOM
        img = sitk.ReadImage(file_path)
        self.image_series = img
        
        # Lấy thông tin không gian
        self.spacing = img.GetSpacing()
        self.origin = img.GetOrigin()
        self.direction = img.GetDirection()
        
        # Xác định loại ảnh từ metadata
        self.image_type = ds.Modality
        
        # Trích xuất thông tin cơ bản
        self.metadata = {
            'patient_name': getattr(ds, 'PatientName', None),
            'patient_id': getattr(ds, 'PatientID', None),
            'study_date': getattr(ds, 'StudyDate', None),
            'modality': self.image_type,
            'bits_allocated': getattr(ds, 'BitsAllocated', None),
            'pixel_spacing': getattr(ds, 'PixelSpacing', [1, 1]),
            'position': getattr(ds, 'ImagePositionPatient', [0, 0, 0])
        }
        
        return self.get_numpy_array(), self.metadata
    
    def load_rt_image(self, file_path):
        """Tải file RT Image DICOM
        
        Args:
            file_path: Đường dẫn đến file RT Image
            
        Returns:
            Tuple (numpy_array, metadata): Mảng numpy chứa dữ liệu ảnh và metadata
        """
        try:
            # Đọc file DICOM
            ds = pydicom.dcmread(file_path)
            
            # Kiểm tra xem file có phải là RT Image không
            if ds.SOPClassUID != '1.2.840.10008.5.1.4.1.1.481.1':
                print(f"File không phải RT Image: {file_path}")
                return None, None
            
            # Lấy dữ liệu pixel
            image_data = ds.pixel_array.astype(np.float32)
            
            # Áp dụng rescale slope và intercept nếu có
            if hasattr(ds, 'RescaleSlope') and hasattr(ds, 'RescaleIntercept'):
                image_data = image_data * ds.RescaleSlope + ds.RescaleIntercept
            
            # Tạo metadata
            metadata = {
                'patient_name': getattr(ds, 'PatientName', None),
                'patient_id': getattr(ds, 'PatientID', None),
                'study_date': getattr(ds, 'StudyDate', None),
                'position': getattr(ds, 'ImagePositionPatient', [0, 0, 0]),
                'pixel_spacing': getattr(ds, 'PixelSpacing', [1, 1]),
                'slice_thickness': getattr(ds, 'SliceThickness', 1),
                'rows': getattr(ds, 'Rows', 0),
                'columns': getattr(ds, 'Columns', 0),
                'beam_limiting_device_angle': getattr(ds, 'BeamLimitingDeviceAngle', None),
                'patient_position': getattr(ds, 'PatientPosition', None),
                'gantry_angle': getattr(ds, 'GantryAngle', None),
                'radiation_type': getattr(ds, 'RadiationType', None),
                'referenced_plan_seq': []
            }
            
            # Lấy thông tin tham chiếu đến kế hoạch RT Plan
            if hasattr(ds, 'ReferencedRTPlanSequence'):
                for ref_plan in ds.ReferencedRTPlanSequence:
                    plan_ref = {
                        'rt_plan_uid': getattr(ref_plan, 'ReferencedSOPInstanceUID', None)
                    }
                    
                    # Thông tin beam reference
                    if hasattr(ref_plan, 'ReferencedBeamNumber'):
                        plan_ref['beam_number'] = ref_plan.ReferencedBeamNumber
                    
                    metadata['referenced_plan_seq'].append(plan_ref)
            
            # Lưu trữ dữ liệu
            self.image_type = "RT_IMAGE"
            
            return image_data, metadata
            
        except Exception as e:
            print(f"Lỗi khi tải RT Image: {e}")
            return None, None
    
    def find_rt_image(self, directory):
        """Tìm file RT Image trong thư mục
        
        Args:
            directory: Thư mục cần tìm
            
        Returns:
            Đường dẫn đến file RT Image nếu tìm thấy, None nếu không có
        """
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    ds = pydicom.dcmread(file_path, stop_before_pixels=True)
                    if ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.481.1':  # RT Image
                        return file_path
                except:
                    continue
        return None
    
    def get_numpy_array(self):
        """Chuyển đổi SimpleITK image thành mảng NumPy"""
        if self.image_series is None:
        return None
        
        # Chuyển đổi SimpleITK image thành mảng NumPy
        array = sitk.GetArrayFromImage(self.image_series)
        return array
    
    def get_slice(self, axis, slice_index):
        """Lấy một slice theo trục và chỉ số slice"""
        array = self.get_numpy_array()
        if array is None:
            return None
        
        if axis == 'axial':
            # Trục Z
            if 0 <= slice_index < array.shape[0]:
                return array[slice_index]
        elif axis == 'coronal':
            # Trục Y
            if 0 <= slice_index < array.shape[1]:
                return array[:, slice_index, :]
        elif axis == 'sagittal':
            # Trục X
            if 0 <= slice_index < array.shape[2]:
                return array[:, :, slice_index]
        
        return None
    
    def apply_window_level(self, image, window, level):
        """Áp dụng window/level cho ảnh (để hiển thị)
        
        Args:
            image: Mảng NumPy chứa dữ liệu ảnh
            window: Độ rộng cửa sổ (window width)
            level: Giá trị trung tâm cửa sổ (window level/center)
            
        Returns:
            Mảng NumPy đã được điều chỉnh window/level
        """
        # Tính toán giá trị min/max
        min_value = level - window / 2
        max_value = level + window / 2
        
        # Clip và normalize về khoảng [0, 1]
        windowed = np.clip(image, min_value, max_value)
        windowed = (windowed - min_value) / (max_value - min_value)
        
        return windowed
    
    def hounsfield_to_density(self, hu_value):
        """Chuyển đổi giá trị Hounsfield thành giá trị mật độ"""
        # Bảng chuyển đổi đơn giản từ HU sang mật độ tương đối
        conversion_table = [
            (-1000, 0.00),  # Không khí
            (-800, 0.20),   # Phổi
            (-500, 0.45),   # Phổi
            (-100, 0.95),   # Mỡ
            (0, 1.00),      # Nước
            (400, 1.10),    # Mô mềm
            (1000, 1.85),   # Xương xốp
            (2000, 2.35),   # Xương đặc
            (3000, 2.70)    # Xương dày đặc
        ]
        
        # Nội suy tuyến tính giữa các điểm trong bảng
        for i in range(len(conversion_table) - 1):
            hu1, density1 = conversion_table[i]
            hu2, density2 = conversion_table[i + 1]
            
            if hu1 <= hu_value <= hu2:
                # Nội suy tuyến tính
                density = density1 + (density2 - density1) * (hu_value - hu1) / (hu2 - hu1)
                return density
        
        # Nằm ngoài bảng
        if hu_value < conversion_table[0][0]:
            return conversion_table[0][1]
        else:
            return conversion_table[-1][1]
    
    def get_hounsfield_range(self):
        """Trả về phạm vi giá trị Hounsfield trong dữ liệu"""
        if self.image_series is None:
            return None
        
        array = self.get_numpy_array()
        return np.min(array), np.max(array)
    
    def get_window_preset(self, preset="default"):
        """Trả về các giá trị window level và width theo preset"""
        presets = {
            "default": (40, 400),        # Mặc định
            "lung": (-600, 1500),        # Phổi
            "bone": (400, 1800),         # Xương
            "brain": (40, 80),           # Não
            "soft_tissue": (50, 450),    # Mô mềm
            "mediastinum": (50, 350)     # Trung thất
        }
        
        return presets.get(preset.lower(), presets["default"])
    
    def find_rt_structure(self, directory):
        """Tìm file RT Structure trong thư mục
        
        Args:
            directory: Thư mục cần tìm
            
        Returns:
            Đường dẫn đến file RT Structure nếu tìm thấy, None nếu không có
        """
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    ds = pydicom.dcmread(file_path, stop_before_pixels=True)
                    if ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.481.3':  # RT Structure Set
                        return file_path
                except:
                    continue
        return None
    
    def load_rt_structure(self, file_path):
        """Tải file RT Structure Set
        
        Args:
            file_path: Đường dẫn đến file RT Structure
            
        Returns:
            Dictionary chứa thông tin các cấu trúc
        """
        try:
            # Đọc file DICOM
            ds = pydicom.dcmread(file_path)
            
            # Kiểm tra xem file có phải là RT Structure không
            if ds.SOPClassUID != '1.2.840.10008.5.1.4.1.1.481.3':
                print(f"File không phải RT Structure: {file_path}")
                return None
            
            # Dictionary để lưu trữ thông tin các cấu trúc
            structures = {}
            
            # Lặp qua các cấu trúc trong RT Structure
            if hasattr(ds, 'StructureSetROISequence'):
                for roi in ds.StructureSetROISequence:
                    roi_number = roi.ROINumber
                    roi_name = roi.ROIName
                    
                    # Khởi tạo cấu trúc
                    structures[roi_name] = {
                        'id': roi_number,
                        'name': roi_name,
                        'color': [1, 0, 0],  # Màu mặc định là đỏ
                        'contour_data': []
                    }
            
            # Lấy màu sắc và dữ liệu contour
            if hasattr(ds, 'ROIContourSequence'):
                for roi_contour in ds.ROIContourSequence:
                    # Tìm thông tin ROI tương ứng
                    roi_number = roi_contour.ReferencedROINumber
                    
                    # Tìm tên ROI từ ROI Number
                    roi_name = None
                    for structure_name, structure_data in structures.items():
                        if structure_data['id'] == roi_number:
                            roi_name = structure_name
                            break
                    
                    if roi_name is None:
                        continue
                    
                    # Lấy màu sắc nếu có
                    if hasattr(roi_contour, 'ROIDisplayColor'):
                        color = [float(c) / 255.0 for c in roi_contour.ROIDisplayColor]
                        structures[roi_name]['color'] = color
                    
                    # Lấy dữ liệu contour
                    if hasattr(roi_contour, 'ContourSequence'):
                        for contour in roi_contour.ContourSequence:
                            contour_data = {
                                'points': [],
                                'z': 0.0
                            }
                            
                            # Lấy số điểm và dữ liệu điểm
                            num_points = contour.NumberOfContourPoints
                            contour_data_raw = contour.ContourData
                            
                            # Chia dữ liệu thành các điểm (x, y, z)
                            for i in range(num_points):
                                x = float(contour_data_raw[i*3])
                                y = float(contour_data_raw[i*3 + 1])
                                z = float(contour_data_raw[i*3 + 2])
                                contour_data['points'].append([x, y, z])
                                
                            # Gán z-coordinate (thường là giống nhau cho tất cả các điểm trong một contour)
                            if len(contour_data['points']) > 0:
                                contour_data['z'] = contour_data['points'][0][2]
                            
                            # Thêm vào danh sách contour của cấu trúc
                            structures[roi_name]['contour_data'].append(contour_data)
            
            return structures
            
        except Exception as e:
            print(f"Lỗi khi tải RT Structure: {e}")
            return None
    
    def find_rt_dose(self, directory):
        """Tìm file RT Dose trong thư mục
        
        Args:
            directory: Thư mục cần tìm
            
        Returns:
            Đường dẫn đến file RT Dose nếu tìm thấy, None nếu không có
        """
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    ds = pydicom.dcmread(file_path, stop_before_pixels=True)
                    if ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.481.2':  # RT Dose
                        return file_path
                except:
                    continue
        return None
    
    def load_rt_dose(self, file_path):
        """Tải file RT Dose
        
        Args:
            file_path: Đường dẫn đến file RT Dose
            
        Returns:
            Tuple (numpy_array, metadata): Mảng numpy chứa dữ liệu liều và metadata
        """
        try:
            # Đọc file DICOM
            ds = pydicom.dcmread(file_path)
            
            # Kiểm tra xem file có phải là RT Dose không
            if ds.SOPClassUID != '1.2.840.10008.5.1.4.1.1.481.2':
                print(f"File không phải RT Dose: {file_path}")
                return None, None
            
            # Lấy dữ liệu pixel
            dose_data = ds.pixel_array.astype(np.float32)
            
            # Áp dụng rescale slope và intercept nếu có
            if hasattr(ds, 'DoseGridScaling'):
                dose_data = dose_data * ds.DoseGridScaling
            
            # Thêm chiều nếu cần thiết
            if len(dose_data.shape) == 2:
                dose_data = dose_data.reshape(1, dose_data.shape[0], dose_data.shape[1])
            
            # Tạo metadata
            metadata = {
                'patient_name': getattr(ds, 'PatientName', None),
                'patient_id': getattr(ds, 'PatientID', None),
                'study_date': getattr(ds, 'StudyDate', None),
                'dose_units': getattr(ds, 'DoseUnits', 'GY'),
                'dose_type': getattr(ds, 'DoseType', None),
                'dose_summation_type': getattr(ds, 'DoseSummationType', None),
                'dose_comment': getattr(ds, 'DoseComment', None),
                'grid_frame_offset_vector': getattr(ds, 'GridFrameOffsetVector', None),
                'dose_grid_scaling': getattr(ds, 'DoseGridScaling', 1.0),
                'dose_max': float(np.max(dose_data)) if dose_data is not None else 0,
                'dose_min': float(np.min(dose_data)) if dose_data is not None else 0,
                'position': getattr(ds, 'ImagePositionPatient', [0, 0, 0]),
                'pixel_spacing': getattr(ds, 'PixelSpacing', [1, 1]),
                'slice_thickness': getattr(ds, 'SliceThickness', 1),
                'rows': getattr(ds, 'Rows', 0),
                'columns': getattr(ds, 'Columns', 0)
            }
            
            return dose_data, metadata
            
        except Exception as e:
            print(f"Lỗi khi tải RT Dose: {e}")
            return None, None