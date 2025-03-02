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
        self.rt_dose = None
        self.rt_plan = None
        self._classify_files()

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
        """Trích xuất dữ liệu kế hoạch RT Plan"""
        if not self.rt_plan:
            return None
        
        try:
            ds = pydicom.dcmread(self.rt_plan)
            plan_data = {
                'plan_label': getattr(ds, 'RTPlanLabel', 'Unknown Plan'),
                'plan_name': getattr(ds, 'RTPlanName', 'Unknown'),
                'plan_description': getattr(ds, 'RTPlanDescription', ''),
                'fraction_groups': []
            }
            
            # Trích xuất thông tin về phân đoạn điều trị
            if hasattr(ds, 'FractionGroupSequence'):
                for fg in ds.FractionGroupSequence:
                    fraction_group = {
                        'number_of_fractions': fg.NumberOfFractionsPlanned,
                        'number_of_beams': fg.NumberOfBeams if hasattr(fg, 'NumberOfBeams') else 0,
                        'beams': []
                    }
                    
                    # Trích xuất thông tin về các trường chiếu
                    if hasattr(fg, 'ReferencedBeamSequence'):
                        for rb in fg.ReferencedBeamSequence:
                            fraction_group['beams'].append({
                                'beam_number': rb.ReferencedBeamNumber,
                                'dose': rb.BeamDose if hasattr(rb, 'BeamDose') else 0,
                                'dose_units': rb.BeamDoseSpecificationPoint if hasattr(rb, 'BeamDoseSpecificationPoint') else None
                            })
                    
                    plan_data['fraction_groups'].append(fraction_group)
            
            # Trích xuất thông tin về các trường chiếu
            if hasattr(ds, 'BeamSequence'):
                plan_data['beams'] = []
                for beam in ds.BeamSequence:
                    beam_data = {
                        'beam_number': beam.BeamNumber,
                        'beam_name': beam.BeamName,
                        'beam_type': beam.BeamType,
                        'radiation_type': beam.RadiationType,
                        'source_axis_distance': beam.SourceAxisDistance,
                        'gantry_angle': beam.ControlPointSequence[0].GantryAngle if hasattr(beam, 'ControlPointSequence') else 0,
                        'collimator_angle': beam.ControlPointSequence[0].BeamLimitingDeviceAngle if hasattr(beam, 'ControlPointSequence') else 0,
                        'patient_support_angle': beam.ControlPointSequence[0].PatientSupportAngle if hasattr(beam, 'ControlPointSequence') and hasattr(beam.ControlPointSequence[0], 'PatientSupportAngle') else 0
                    }
                    
                    # Trích xuất thông tin về MLC nếu có
                    if hasattr(beam, 'ControlPointSequence') and hasattr(beam.ControlPointSequence[0], 'BeamLimitingDevicePositionSequence'):
                        for device in beam.ControlPointSequence[0].BeamLimitingDevicePositionSequence:
                            if device.RTBeamLimitingDeviceType == 'MLCX' or device.RTBeamLimitingDeviceType == 'MLCY':
                                beam_data['mlc_positions'] = device.LeafJawPositions
                    
                    plan_data['beams'].append(beam_data)
            
            return plan_data
        except Exception as e:
            print(f"Lỗi trích xuất RT Plan: {e}")
            return None