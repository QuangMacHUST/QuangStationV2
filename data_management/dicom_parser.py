import pydicom
import numpy as np
import os
from concurrent.futures import ThreadPoolExecutor

class DICOMParser:
    def __init__(self, folder_path):
        self.folder_path = folder_path
        self.files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.dcm')]
        self.ct_files = []
        self.mri_files = []
        self.rt_struct = None
        self._classify_files()

    def _classify_files(self):
        for file in self.files:
            try:
                ds = pydicom.dcmread(file, stop_before_pixels=True)
                if ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.2':  # CT Image
                    self.ct_files.append(file)
                elif ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.4':  # MR Image
                    self.mri_files.append(file)
                elif ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.481.3':  # RT Structure Set
                    self.rt_struct = file
            except Exception as e:
                print(f"Bỏ qua file lỗi: {file} - {e}")

        if self.ct_files:
            self.ct_files.sort(key=self._get_slice_location)
        if self.mri_files:
            self.mri_files.sort(key=self._get_slice_location)

    def _get_slice_location(self, file_path):
        ds = pydicom.dcmread(file_path, stop_before_pixels=True)
        return float(ds.SliceLocation if 'SliceLocation' in ds else ds.InstanceNumber)

    def extract_image_volume(self, modality='CT', max_workers=4):
        files = self.ct_files if modality == 'CT' else self.mri_files
        if not files:
            raise ValueError(f"Không có chuỗi ảnh {modality}")

        def read_dicom(file):
            try:
                ds = pydicom.dcmread(file)
                return ds.pixel_array
            except Exception as e:
                print(f"Lỗi đọc file {file}: {e}")
                return None

        # Đọc song song các file
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            slices = list(executor.map(read_dicom, files))

        # Lọc bỏ None (file lỗi)
        slices = [s for s in slices if s is not None and s.size > 0]

        if not slices:
            raise ValueError(f"Không có slice hợp lệ cho {modality}")

        # Đảm bảo kích thước đồng nhất
        first_shape = slices[0].shape
        valid_slices = []
        for slice_data in slices:
            if slice_data.shape == first_shape:
                valid_slices.append(slice_data)
            else:
                print(f"Bỏ qua slice do kích thước không khớp: {slice_data.shape}")

        if not valid_slices:
            raise ValueError(f"Không có slice hợp lệ cùng kích thước cho {modality}")

        volume = np.stack(valid_slices, axis=0).astype(np.float32)
        print(f"Đã tạo khối 3D với kích thước: {volume.shape}")
        return volume
    def extract_patient_info(self):
        """Trích xuất thông tin bệnh nhân từ file DICOM đầu tiên"""
        if self.ct_files:
            ds = pydicom.dcmread(self.ct_files[0])
        elif self.mri_files:
            ds = pydicom.dcmread(self.mri_files[0])
        else:
            raise ValueError("Không có file CT hoặc MRI để trích xuất thông tin bệnh nhân")
        
        return {
            'patient_id': getattr(ds, 'PatientID', 'Unknown'),
            'patient_name': str(getattr(ds, 'PatientName', 'Unknown')),
            'study_date': getattr(ds, 'StudyDate', 'Unknown')
        }