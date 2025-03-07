import os
import sys
import numpy as np
from concurrent.futures import ThreadPoolExecutor

# Sửa lỗi import pydicom
try:
    import pydicom
except ImportError:
    print("Thư viện pydicom chưa được cài đặt. Đang cài đặt...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pydicom"])
    import pydicom

class DICOMParser:
    def __init__(self, folder_path):
        """Khởi tạo parser với đường dẫn đến thư mục chứa file DICOM"""
        self.folder_path = folder_path
        self.files = self._get_dicom_files(folder_path)
        self.ct_files = []
        self.mri_files = []
        self.rt_struct = None
        self.rt_dose = None
        self.rt_plan = None
        self.rt_image = None  # Thêm biến để lưu RT Image
        self._classify_files()

    def _get_dicom_files(self, folder_path):
        """Lấy danh sách tất cả các file DICOM trong thư mục"""
        dicom_files = []
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    # Kiểm tra nhanh xem file có phải là DICOM không
                    with open(file_path, 'rb') as f:
                        # Kiểm tra DICOM magic number (DICM ở byte 128-132)
                        f.seek(128)
                        if f.read(4) == b'DICM':
                            dicom_files.append(file_path)
                except Exception as e:
                    # Bỏ qua các file không phải DICOM
                    continue
        return dicom_files

    def _classify_files(self):
        """Phân loại các file DICOM theo loại"""
        for file in self.files:
            try:
                ds = pydicom.dcmread(file, stop_before_pixels=True)
                if ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.2':  # CT Image
                    self.ct_files.append(file)
                elif ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.4':  # MR Image
                    self.mri_files.append(file)
                elif ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.481.3':  # RT Structure Set
                    self.rt_struct = file
                elif ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.481.2':  # RT Dose
                    self.rt_dose = file
                elif ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.481.5':  # RT Plan
                    self.rt_plan = file
                elif ds.SOPClassUID == '1.2.840.10008.5.1.4.1.1.481.1':  # RT Image
                    self.rt_image = file
            except Exception as e:
                print(f"Bỏ qua file lỗi: {file} - {e}")

        if self.ct_files:
            self.ct_files.sort(key=self._get_slice_location)
        if self.mri_files:
            self.mri_files.sort(key=self._get_slice_location)

    def _get_slice_location(self, file_path):
        """Lấy vị trí lát cắt để sắp xếp"""
        ds = pydicom.dcmread(file_path, stop_before_pixels=True)
        if 'SliceLocation' in ds:
            return float(ds.SliceLocation)
        elif 'ImagePositionPatient' in ds:
            return float(ds.ImagePositionPatient[2])  # Z position
        else:
            return float(ds.InstanceNumber)

    def extract_image_volume(self, modality='CT', max_workers=4):
        """Trích xuất khối ảnh 3D từ các file DICOM"""
        files = self.ct_files if modality == 'CT' else self.mri_files
        if not files:
            raise ValueError(f"Không có chuỗi ảnh {modality}")

        def read_dicom(file):
            try:
                ds = pydicom.dcmread(file)
                # Tạo metadata cho slice này
                metadata = {
                    'position': ds.ImagePositionPatient if 'ImagePositionPatient' in ds else None,
                    'orientation': ds.ImageOrientationPatient if 'ImageOrientationPatient' in ds else None,
                    'pixel_spacing': ds.PixelSpacing if 'PixelSpacing' in ds else None,
                    'slice_thickness': ds.SliceThickness if 'SliceThickness' in ds else None,
                    'rescale_intercept': ds.RescaleIntercept if 'RescaleIntercept' in ds else 0,
                    'rescale_slope': ds.RescaleSlope if 'RescaleSlope' in ds else 1
                }
                pixel_array = ds.pixel_array
                # Áp dụng HU transformation nếu là CT
                if modality == 'CT' and 'RescaleIntercept' in ds and 'RescaleSlope' in ds:
                    pixel_array = pixel_array * ds.RescaleSlope + ds.RescaleIntercept
                return pixel_array, metadata
            except Exception as e:
                print(f"Lỗi đọc file {file}: {e}")
                return None, None

        # Đọc song song các file
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(read_dicom, files))
        
        slices = []
        metadata_list = []
        for pixel_array, metadata in results:
            if pixel_array is not None and metadata is not None:
                slices.append(pixel_array)
                metadata_list.append(metadata)

        if not slices:
            raise ValueError(f"Không có slice hợp lệ cho {modality}")

        # Đảm bảo kích thước đồng nhất
        first_shape = slices[0].shape
        valid_slices = []
        valid_metadata = []
        for i, slice_data in enumerate(slices):
            if slice_data.shape == first_shape:
                valid_slices.append(slice_data)
                valid_metadata.append(metadata_list[i])
            else:
                print(f"Bỏ qua slice do kích thước không khớp: {slice_data.shape}")

        if not valid_slices:
            raise ValueError(f"Không có slice hợp lệ cùng kích thước cho {modality}")

        volume = np.stack(valid_slices, axis=0).astype(np.float32)
        volume_metadata = {
            'shape': volume.shape,
            'modality': modality,
            'slices': valid_metadata,
            # Lấy thông tin chung từ slice đầu tiên
            'pixel_spacing': valid_metadata[0]['pixel_spacing'],
            'slice_thickness': valid_metadata[0]['slice_thickness']
        }
        
        print(f"Đã tạo khối 3D với kích thước: {volume.shape}")
        return volume, volume_metadata

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
            'study_date': getattr(ds, 'StudyDate', 'Unknown'),
            'birth_date': getattr(ds, 'PatientBirthDate', 'Unknown'),
            'sex': getattr(ds, 'PatientSex', 'Unknown'),
            'study_description': getattr(ds, 'StudyDescription', 'Unknown'),
            'series_description': getattr(ds, 'SeriesDescription', 'Unknown'),
            'institution_name': getattr(ds, 'InstitutionName', 'Unknown')
        }

    def extract_rt_struct(self):
        """Trích xuất dữ liệu RT Structure Set"""
        if not self.rt_struct:
            return None
        
        try:
            ds = pydicom.dcmread(self.rt_struct)
            structures = {}
            
            # Lấy thông tin contour sequences
            if hasattr(ds, 'ROIContourSequence'):
                for i, roi in enumerate(ds.ROIContourSequence):
                    roi_number = roi.ReferencedROINumber
                    contour_data = []
                    
                    # Lấy màu của ROI
                    roi_color = [int(c)/255 for c in roi.ROIDisplayColor] if hasattr(roi, 'ROIDisplayColor') else [1, 0, 0]
                    
                    # Lấy dữ liệu contour nếu có
                    if hasattr(roi, 'ContourSequence'):
                        for contour in roi.ContourSequence:
                            if hasattr(contour, 'ContourData'):
                                points = np.array(contour.ContourData).reshape(-1, 3)
                                contour_data.append({
                                    'points': points,
                                    'slice_z': points[0, 2]  # Z position
                                })
                    
                    structures[roi_number] = {
                        'contour_data': contour_data,
                        'color': roi_color
                    }
            
            # Lấy tên của các cấu trúc từ Structure Set ROI Sequence
            if hasattr(ds, 'StructureSetROISequence'):
                for roi in ds.StructureSetROISequence:
                    roi_number = roi.ROINumber
                    if roi_number in structures:
                        structures[roi_number]['name'] = roi.ROIName
            
            return structures
        except Exception as e:
            print(f"Lỗi trích xuất RT Structure Set: {e}")
            return None

    def extract_rt_dose(self):
        """Trích xuất dữ liệu liều RT Dose"""
        if not self.rt_dose:
            return None
        
        try:
            ds = pydicom.dcmread(self.rt_dose)
            dose_data = ds.pixel_array * ds.DoseGridScaling
            
            # Trích xuất thông tin về grid
            dose_metadata = {
                'shape': dose_data.shape,
                'position': ds.ImagePositionPatient if 'ImagePositionPatient' in ds else None,
                'orientation': ds.ImageOrientationPatient if 'ImageOrientationPatient' in ds else None,
                'pixel_spacing': ds.PixelSpacing if 'PixelSpacing' in ds else None,
                'slice_thickness': ds.SliceThickness if 'SliceThickness' in ds else None,
                'scaling': ds.DoseGridScaling if 'DoseGridScaling' in ds else 1.0
            }
            
            return dose_data, dose_metadata
        except Exception as e:
            print(f"Lỗi trích xuất RT Dose: {e}")
            return None

    def extract_rt_plan(self):
        """Trích xuất thông tin từ RT Plan"""
        if not self.rt_plan:
            return None
        
        try:
            ds = pydicom.dcmread(self.rt_plan)
            plan_data = {
                'plan_label': ds.RTPlanLabel if hasattr(ds, 'RTPlanLabel') else '',
                'plan_name': ds.RTPlanName if hasattr(ds, 'RTPlanName') else '',
                'plan_description': ds.RTPlanDescription if hasattr(ds, 'RTPlanDescription') else '',
                'plan_date': ds.RTPlanDate if hasattr(ds, 'RTPlanDate') else '',
                'plan_time': ds.RTPlanTime if hasattr(ds, 'RTPlanTime') else '',
                'beams': []
            }
            
            # Trích xuất thông tin về các beam
            if hasattr(ds, 'BeamSequence'):
                for beam in ds.BeamSequence:
                    beam_data = {
                        'beam_number': beam.BeamNumber if hasattr(beam, 'BeamNumber') else '',
                        'beam_name': beam.BeamName if hasattr(beam, 'BeamName') else '',
                        'beam_type': beam.BeamType if hasattr(beam, 'BeamType') else '',
                        'radiation_type': beam.RadiationType if hasattr(beam, 'RadiationType') else '',
                        'treatment_machine': beam.TreatmentMachineName if hasattr(beam, 'TreatmentMachineName') else ''
                    }
                    plan_data['beams'].append(beam_data)
            
            return plan_data
        except Exception as e:
            print(f"Lỗi khi đọc RT Plan: {e}")
            return None

    def extract_rt_image(self):
        """Trích xuất thông tin từ RT Image"""
        if not self.rt_image:
            return None
        
        try:
            ds = pydicom.dcmread(self.rt_image)
            
            # Trích xuất thông tin cơ bản
            rt_image_data = {
                'sop_instance_uid': ds.SOPInstanceUID,
                'rt_image_label': ds.RTImageLabel if hasattr(ds, 'RTImageLabel') else '',
                'rt_image_description': ds.RTImageDescription if hasattr(ds, 'RTImageDescription') else '',
                'rt_image_name': ds.RTImageName if hasattr(ds, 'RTImageName') else '',
                'image_type': ds.ImageType if hasattr(ds, 'ImageType') else [],
                'referenced_beam_number': ds.ReferencedBeamNumber if hasattr(ds, 'ReferencedBeamNumber') else None,
                'radiation_machine_name': ds.RadiationMachineName if hasattr(ds, 'RadiationMachineName') else '',
                'radiation_machine_sad': ds.RadiationMachineSAD if hasattr(ds, 'RadiationMachineSAD') else None,
                'rt_image_position': ds.RTImagePosition if hasattr(ds, 'RTImagePosition') else None,
                'rt_image_orientation': ds.RTImageOrientation if hasattr(ds, 'RTImageOrientation') else None,
                'gantry_angle': ds.GantryAngle if hasattr(ds, 'GantryAngle') else None,
                'beam_limiting_device_angle': ds.BeamLimitingDeviceAngle if hasattr(ds, 'BeamLimitingDeviceAngle') else None,
                'patient_support_angle': ds.PatientSupportAngle if hasattr(ds, 'PatientSupportAngle') else None,
                'exposure_sequence': []
            }
            
            # Trích xuất thông tin về các exposure
            if hasattr(ds, 'ExposureSequence'):
                for exposure in ds.ExposureSequence:
                    exposure_data = {
                        'exposure_time': exposure.ExposureTime if hasattr(exposure, 'ExposureTime') else None,
                        'kvp': exposure.KVP if hasattr(exposure, 'KVP') else None,
                        'x_ray_tube_current': exposure.XRayTubeCurrent if hasattr(exposure, 'XRayTubeCurrent') else None
                    }
                    rt_image_data['exposure_sequence'].append(exposure_data)
            
            # Trích xuất dữ liệu pixel
            if hasattr(ds, 'pixel_array'):
                rt_image_data['pixel_data'] = ds.pixel_array
                rt_image_data['rows'] = ds.Rows
                rt_image_data['columns'] = ds.Columns
                rt_image_data['bits_allocated'] = ds.BitsAllocated
                rt_image_data['bits_stored'] = ds.BitsStored
                rt_image_data['high_bit'] = ds.HighBit
                rt_image_data['pixel_representation'] = ds.PixelRepresentation
                
                # Xử lý window/level nếu có
                if hasattr(ds, 'WindowCenter') and hasattr(ds, 'WindowWidth'):
                    rt_image_data['window_center'] = ds.WindowCenter
                    rt_image_data['window_width'] = ds.WindowWidth
            
            return rt_image_data
        except Exception as e:
            print(f"Lỗi khi đọc RT Image: {e}")
            return None