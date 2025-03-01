import pydicom
import numpy as np

class DICOMParser:
    def __init__(self, dicom_file):
        self.dicom_file = dicom_file
        self.dataset = pydicom.dcmread(dicom_file)
    
    def extract_patient_info(self):
        """Trích xuất thông tin bệnh nhân"""
        return {
            'patient_id': self.dataset.PatientID,
            'patient_name': str(self.dataset.PatientName),
            'study_date': self.dataset.StudyDate
        }
    
    def extract_image_data(self):
        """Trích xuất dữ liệu hình ảnh"""
        pixel_array = self.dataset.pixel_array
        return pixel_array  # Ma trận 2D hoặc 3D
    
    def extract_rt_struct(self):
        """Trích xuất contour từ DICOM-RT"""
        if 'StructureSetROISequence' in self.dataset:
            contours = []
            for roi in self.dataset.StructureSetROISequence:
                contours.append({
                    'roi_number': roi.ROINumber,
                    'roi_name': roi.ROIName,
                    'contours': []  # Thêm logic trích xuất contour nếu cần
                })
            return contours
        return None