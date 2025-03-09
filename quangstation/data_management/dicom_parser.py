import os
import sys
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict

# Sửa lỗi import pydicom
try:
    import pydicom
except ImportError:
    print("Thư viện pydicom chưa được cài đặt. Đang cài đặt...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pydicom"])
    import pydicom

# Import logging module
from quangstation.utils.logging import get_logger
logger = get_logger("DICOMParser")
    
""" 
    Module này nhập dữ liệu DICOM và phân loại chúng thành các loại khác nhau
    
    """
class DICOMParser:
    def __init__(self, folder_path: str):
        """Khởi tạo parser với đường dẫn đến thư mục chứa file DICOM"""
        self.folder_path = folder_path
        self.files = self._get_dicom_files(folder_path)
        self.ct_files = []
        self.mri_files = []
        self.pet_files = []  # Thêm support cho PET
        self.spect_files = []  # Thêm support cho SPECT
        self.rt_struct = None
        self.rt_dose = None
        self.rt_plan = None
        self.rt_image = None
        self.patient_info = {}
        
        # Thêm thuộc tính file_groups và reference_slice_positions
        self.file_groups = {}
        self.reference_slice_positions = []
        
        # Phân loại các file
        self._classify_files()
        
        # Log số lượng file tìm thấy
        logger.info(f"Tìm thấy {len(self.files)} file DICOM trong thư mục {folder_path}")
        logger.info(f"CT: {len(self.ct_files)}, MRI: {len(self.mri_files)}, PET: {len(self.pet_files)}, SPECT: {len(self.spect_files)}")
        logger.info(f"RT Structure: {self.rt_struct is not None}, RT Dose: {self.rt_dose is not None}, RT Plan: {self.rt_plan is not None}")

    def _get_dicom_files(self, folder_path: str) -> List[str]:
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
                except Exception as error:
                    # Bỏ qua các file không phải DICOM
                    continue
        return dicom_files

    def _classify_files(self):
        """Phân loại các file DICOM theo loại"""
        modality_counts = defaultdict(int)
        
        # Lặp qua từng file để phân loại
        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            results = list(executor.map(self._read_and_classify_dicom, self.files))
        
        # Xử lý kết quả và phân loại
        for file_path, modality, ds in results:
            if ds is None:
                continue
                
            modality_counts[modality] += 1
            
            # Phân loại theo loại file
            if modality == 'CT':
                self.ct_files.append(file_path)
            elif modality == 'MR':
                self.mri_files.append(file_path)
            elif modality == 'PT':
                self.pet_files.append(file_path)
            elif modality == 'NM' and hasattr(ds, 'SeriesDescription') and 'SPECT' in ds.SeriesDescription:
                self.spect_files.append(file_path)
            elif modality == 'RTSTRUCT':
                self.rt_struct = file_path
                # Trích xuất thông tin bệnh nhân từ RTSTRUCT nếu có
                self._extract_patient_info_from_dataset(ds)
            elif modality == 'RTDOSE':
                self.rt_dose = file_path
            elif modality == 'RTPLAN':
                self.rt_plan = file_path
            elif modality == 'RTIMAGE':
                self.rt_image = file_path
        
        # Sắp xếp file theo thứ tự slice
        if self.ct_files:
            self.ct_files = self._sort_dicom_files(self.ct_files)
            self.file_groups['CT'] = self.ct_files
        
        if self.mri_files:
            self.mri_files = self._sort_dicom_files(self.mri_files)
            self.file_groups['MRI'] = self.mri_files
            
        if self.pet_files:
            self.pet_files = self._sort_dicom_files(self.pet_files)
            self.file_groups['PET'] = self.pet_files
            
        if self.spect_files:
            self.spect_files = self._sort_dicom_files(self.spect_files)
            self.file_groups['SPECT'] = self.spect_files
        
        # Tạo danh sách vị trí slice từ file CT nếu có
        if self.ct_files:
            self.reference_slice_positions = self._extract_slice_positions(self.ct_files)
            
        # Log số lượng file theo loại
        logger.info(f"Phân loại DICOM: {modality_counts}")

    def _read_and_classify_dicom(self, file_path: str) -> Tuple[str, str, Optional[pydicom.dataset.FileDataset]]:
        """Đọc file DICOM và trả về modality của nó"""
        try:
            ds = pydicom.dcmread(file_path, stop_before_pixels=True)
            modality = getattr(ds, 'Modality', 'Unknown')
            return file_path, modality, ds
        except Exception as error:
            logger.error(f"Lỗi khi đọc file DICOM {file_path}: {str(error)}")
            return file_path, 'Unknown', None

    def _sort_dicom_files(self, files: List[str]) -> List[str]:
        """Sắp xếp các file DICOM theo vị trí slice"""
        position_files = []
        for file in files:
            try:
                ds = pydicom.dcmread(file, stop_before_pixels=True)
                if hasattr(ds, 'ImagePositionPatient'):
                    z_pos = float(ds.ImagePositionPatient[2])
                    position_files.append((z_pos, file))
            except Exception as error:
                logger.error(f"Lỗi khi đọc vị trí file DICOM {file}: {str(error)}")
        
        position_files.sort()  # Sắp xếp theo vị trí z
        return [file for _, file in position_files]

    def _extract_patient_info_from_dataset(self, ds: pydicom.dataset.FileDataset):
        """Trích xuất thông tin bệnh nhân từ dataset DICOM"""
        # Trích xuất các trường thông tin cơ bản
        fields = [
            'PatientName', 'PatientID', 'PatientBirthDate', 'PatientSex',
            'StudyDescription', 'StudyDate', 'StudyTime', 'StudyInstanceUID',
            'SeriesDescription', 'SeriesDate', 'SeriesTime', 'SeriesInstanceUID',
            'Manufacturer', 'ManufacturerModelName', 'SoftwareVersions'
        ]
        
        for field in fields:
            if hasattr(ds, field):
                value = getattr(ds, field)
                # Xử lý các kiểu dữ liệu đặc biệt từ pydicom
                if hasattr(value, 'original_string'):
                    value = str(value)
                self.patient_info[field] = value

    def extract_patient_info(self) -> Dict[str, Any]:
        """Trích xuất thông tin bệnh nhân từ các file DICOM"""
        # Nếu chưa có thông tin bệnh nhân và có file DICOM, đọc file đầu tiên
        if not self.patient_info and self.files:
            try:
                first_file = self.files[0]
                ds = pydicom.dcmread(first_file, stop_before_pixels=True)
                self._extract_patient_info_from_dataset(ds)
            except Exception as error:
                logger.error(f"Lỗi khi trích xuất thông tin bệnh nhân: {str(error)}")
        
        return self.patient_info

    def get_modalities(self) -> Dict[str, int]:
        """Trả về số lượng file theo từng modality"""
        return {
            'CT': len(self.ct_files),
            'MRI': len(self.mri_files),
            'PET': len(self.pet_files),
            'SPECT': len(self.spect_files),
            'RTSTRUCT': 1 if self.rt_struct else 0,
            'RTDOSE': 1 if self.rt_dose else 0,
            'RTPLAN': 1 if self.rt_plan else 0,
            'RTIMAGE': 1 if self.rt_image else 0
        }

    def has_complete_rt_data(self) -> bool:
        """Kiểm tra xem có đủ dữ liệu RT không (CT + Structure + Plan + Dose)"""
        return len(self.ct_files) > 0 and self.rt_struct is not None and self.rt_plan is not None and self.rt_dose is not None

    def extract_image_volume(self, modality='CT', max_workers=4):
        """Trích xuất khối dữ liệu hình ảnh từ các file DICOM."""
        if modality not in self.file_groups:
            raise ValueError(f"Không tìm thấy dữ liệu hình ảnh cho loại {modality}")
        
        files = self.file_groups[modality]
        
        # Kiểm tra số lượng file
        if len(files) == 0:
            raise ValueError(f"Không có file {modality} nào được tìm thấy")
        
        # Hàm đọc file DICOM đã được cải tiến
        def read_dicom(file):
            try:
                dicom_data = pydicom.dcmread(file, force=True)
                
                # Xử lý trường hợp thiếu tag RescaleSlope và RescaleIntercept
                rescale_slope = 1.0
                rescale_intercept = 0.0
                
                if hasattr(dicom_data, 'RescaleSlope'):
                    rescale_slope = float(dicom_data.RescaleSlope)
                if hasattr(dicom_data, 'RescaleIntercept'):
                    rescale_intercept = float(dicom_data.RescaleIntercept)
                    
                # Chuyển đổi pixel data sang numpy array
                if dicom_data.pixel_array.dtype != np.float32:
                    pixel_array = dicom_data.pixel_array.astype(np.float32)
                else:
                    pixel_array = dicom_data.pixel_array
                    
                # Áp dụng tỷ lệ và điểm cắt để chuyển về HU
                pixel_array = pixel_array * rescale_slope + rescale_intercept
                
                # Lấy vị trí slice
                slice_pos = self._get_slice_location(file)
                
                return {
                    'data': pixel_array,
                    'position': slice_pos,
                    'metadata': dicom_data
                }
            except Exception as error:
                logger.error(f"Lỗi khi đọc file {file}: {str(error)}")
                return None
        
        # Đọc song song các file
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(read_dicom, files))
        
        slices = []
        metadata_list = []
        positions = []
        
        for result in results:
            if result is not None:
                slices.append(result['data'])
                metadata_list.append(result['metadata'])
                positions.append(result['position'])

        if not slices:
            raise ValueError(f"Không có slice hợp lệ cho {modality}")

        # Sắp xếp slices theo vị trí
        if positions and any(pos is not None for pos in positions):
            # Lọc ra các slice có vị trí hợp lệ
            valid_indices = [i for i, pos in enumerate(positions) if pos is not None]
            
            if valid_indices:
                # Sắp xếp chỉ các slice có vị trí hợp lệ
                sorted_indices = [i for i in sorted(valid_indices, key=lambda i: positions[i])]
                
                # Tạo danh sách mới với các slice đã sắp xếp
                sorted_slices = [slices[i] for i in sorted_indices]
                sorted_metadata = [metadata_list[i] for i in sorted_indices]
                sorted_positions = [positions[i] for i in sorted_indices]
                
                slices = sorted_slices
                metadata_list = sorted_metadata
                positions = sorted_positions

        # Đảm bảo kích thước đồng nhất
        first_shape = slices[0].shape
        valid_slices = []
        valid_metadata = []
        valid_positions = []
        
        for i, slice_data in enumerate(slices):
            if slice_data.shape == first_shape:
                valid_slices.append(slice_data)
                valid_metadata.append(metadata_list[i])
                if i < len(positions):
                    valid_positions.append(positions[i])
            else:
                logger.warning(f"Bỏ qua slice do kích thước không khớp: {slice_data.shape}")

        if not valid_slices:
            raise ValueError(f"Không có slice hợp lệ cùng kích thước cho {modality}")

        # Tạo khối 3D
        volume = np.stack(valid_slices, axis=0).astype(np.float32)
        
        # Lấy thông tin không gian từ metadata
        first_metadata = valid_metadata[0]
        
        # Pixel Spacing
        pixel_spacing = None
        if hasattr(first_metadata, 'PixelSpacing'):
            pixel_spacing = first_metadata.PixelSpacing
        elif hasattr(first_metadata, 'ImagerPixelSpacing'):
            pixel_spacing = first_metadata.ImagerPixelSpacing
        
        # Slice Thickness
        slice_thickness = None
        if hasattr(first_metadata, 'SliceThickness'):
            slice_thickness = first_metadata.SliceThickness
        elif len(valid_positions) > 1:
            # Ước tính từ khoảng cách giữa các slice liền kề
            slice_thickness = abs(valid_positions[1] - valid_positions[0])
        
        # Origin
        origin = None
        if hasattr(first_metadata, 'ImagePositionPatient'):
            origin = first_metadata.ImagePositionPatient
        
        # Orientation
        direction = None
        if hasattr(first_metadata, 'ImageOrientationPatient'):
            orientation = first_metadata.ImageOrientationPatient
            # Mở rộng thành ma trận 3x3
            row_x, row_y, row_z = orientation[:3]
            col_x, col_y, col_z = orientation[3:]
            # Tính vector normal
            normal_x = row_y * col_z - row_z * col_y
            normal_y = row_z * col_x - row_x * col_z
            normal_z = row_x * col_y - row_y * col_x
            
            direction = (
                row_x, row_y, row_z,
                col_x, col_y, col_z,
                normal_x, normal_y, normal_z
            )
        
        # Tạo thông tin metadata
        volume_metadata = {
            'shape': volume.shape,
            'modality': modality,
            'slices': valid_metadata,
            'pixel_spacing': pixel_spacing,
            'slice_thickness': slice_thickness,
            'origin': origin,
            'direction': direction,
            'slice_positions': valid_positions
        }
        
        # Cập nhật thông tin slice positions
        if valid_positions:
            self.reference_slice_positions = valid_positions
        
        logger.info(f"Đã tạo khối 3D với kích thước: {volume.shape}")
        
        return volume, volume_metadata

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
        except Exception as error:
            print(f"Lỗi trích xuất RT Structure Set: {error}")
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
        except Exception as error:
            print(f"Lỗi trích xuất RT Dose: {error}")
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
        except Exception as error:
            print(f"Lỗi khi đọc RT Plan: {error}")
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
        except Exception as error:
            print(f"Lỗi khi đọc RT Image: {error}")
            return None

    def _get_slice_location(self, file_path):
        """Lấy vị trí lát cắt để sắp xếp"""
        ds = pydicom.dcmread(file_path, stop_before_pixels=True)
        if 'SliceLocation' in ds:
            return float(ds.SliceLocation)
        elif 'ImagePositionPatient' in ds:
            return float(ds.ImagePositionPatient[2])  # Z position
        else:
            return float(ds.InstanceNumber)

    def _extract_slice_positions(self, files: List[str]) -> List[float]:
        """Trích xuất vị trí các slice từ danh sách file."""
        positions = []
        for file in files:
            try:
                pos = self._get_slice_location(file)
                if pos is not None:
                    positions.append(pos)
            except Exception as error:
                logger.error(f"Lỗi khi đọc vị trí slice từ {file}: {str(error)}")
                
        # Sắp xếp theo vị trí tăng dần
        positions.sort()
        return positions