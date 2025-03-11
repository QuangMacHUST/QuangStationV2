#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module phân tích dữ liệu DICOM và trích xuất thông tin từ các file DICOM
"""

import os
import numpy as np
import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Any, Tuple, Union
from collections import defaultdict

# Sử dụng module external_integration để quản lý thư viện bên ngoài một cách nhất quán
from quangstation.utils.external_integration import get_module
from quangstation.utils.logging import get_logger
from quangstation.io.dicom_constants import *  # Import các hằng số DICOM
from quangstation.data_models.image_data import ImageData
from quangstation.data_models.structure_data import Structure, StructureSet, StructureType
from quangstation.data_models.plan_data import PlanConfig, BeamConfig, PrescriptionConfig, TechniqueType, RadiationType
from quangstation.data_models.dose_data import DoseData, DoseType

logger = get_logger("DICOMParser")

# Lấy module pydicom từ external_integration
pydicom = get_module("pydicom")
if not pydicom:
    logger.error("Không thể import pydicom. Nhiều chức năng sẽ không hoạt động.")
    
class DICOMParser:
    def __init__(self, folder_path: str):
        """
        Khởi tạo parser với đường dẫn đến thư mục chứa file DICOM.
        
        Args:
            folder_path: Đường dẫn đến thư mục chứa các file DICOM
        """
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
        
        # Kiểm tra xem pydicom có sẵn không
        if not pydicom:
            logger.error("Không thể phân tích DICOM vì thiếu thư viện pydicom")
            return
            
        # Phân loại các file
        self._classify_files()
        
        # Log số lượng file tìm thấy
        logger.info(f"Tìm thấy {len(self.files)} file DICOM trong thư mục {folder_path}")
        logger.info(f"CT: {len(self.ct_files)}, MRI: {len(self.mri_files)}, PET: {len(self.pet_files)}, SPECT: {len(self.spect_files)}")
        logger.info(f"RT Structure: {self.rt_struct is not None}, RT Dose: {self.rt_dose is not None}, RT Plan: {self.rt_plan is not None}")

    def _get_dicom_files(self, folder_path: str) -> List[str]:
        """
        Lấy danh sách các file DICOM trong thư mục.
        
        Args:
            folder_path: Đường dẫn đến thư mục
            
        Returns:
            List[str]: Danh sách đường dẫn đến các file DICOM
        """
        dicom_files = []
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    if pydicom and pydicom.misc.is_dicom(file_path):
                        dicom_files.append(file_path)
                except:
                    continue
        return dicom_files

    def _classify_files(self):
        """Phân loại các file DICOM theo modality."""
        if not self.files:
            logger.warning("Không có file DICOM nào để phân loại")
            return
            
        for file_path in self.files:
            try:
                ds = pydicom.dcmread(file_path, stop_before_pixels=True)
                modality = ds.Modality if hasattr(ds, 'Modality') else None
                sop_class_uid = ds.SOPClassUID if hasattr(ds, 'SOPClassUID') else None
                
                if modality == MODALITY_CT or sop_class_uid == CT_IMAGE_STORAGE:
                    self.ct_files.append(file_path)
                elif modality == MODALITY_MR or sop_class_uid == MR_IMAGE_STORAGE:
                    self.mri_files.append(file_path)
                elif modality == MODALITY_PT or sop_class_uid == PET_IMAGE_STORAGE:
                    self.pet_files.append(file_path)
                elif modality == MODALITY_NM or sop_class_uid == SPECT_IMAGE_STORAGE:
                    self.spect_files.append(file_path)
                elif modality == MODALITY_RTSTRUCT or sop_class_uid == RT_STRUCTURE_SET_STORAGE:
                    self.rt_struct = file_path
                elif modality == MODALITY_RTDOSE or sop_class_uid == RT_DOSE_STORAGE:
                    self.rt_dose = file_path
                elif modality == MODALITY_RTPLAN or sop_class_uid == RT_PLAN_STORAGE:
                    self.rt_plan = file_path
                elif modality == MODALITY_RTIMAGE or sop_class_uid == RT_IMAGE_STORAGE:
                    self.rt_image = file_path
                    
                # Lưu thông tin bệnh nhân từ file đầu tiên
                if not self.patient_info:
                    self._extract_patient_info_from_dataset(ds)
                    
            except Exception as e:
                logger.warning(f"Không thể đọc file {file_path}: {str(e)}")
                continue
                
        # Sắp xếp các file theo vị trí slice
        self.ct_files = self._sort_dicom_files(self.ct_files)
        self.mri_files = self._sort_dicom_files(self.mri_files)
        self.pet_files = self._sort_dicom_files(self.pet_files)
        self.spect_files = self._sort_dicom_files(self.spect_files)
        
        logger.info(f"Đã phân loại: {len(self.ct_files)} CT, {len(self.mri_files)} MRI, "
                   f"{len(self.pet_files)} PET, {len(self.spect_files)} SPECT")
        logger.info(f"RT files: Structure={bool(self.rt_struct)}, Dose={bool(self.rt_dose)}, "
                   f"Plan={bool(self.rt_plan)}, Image={bool(self.rt_image)}")
        
        # Tạo danh sách vị trí slice từ file CT nếu có
        if self.ct_files:
            self.reference_slice_positions = self._extract_slice_positions(self.ct_files)
            
        # Log số lượng file theo loại
        modality_counts = {
            'CT': len(self.ct_files),
            'MRI': len(self.mri_files),
            'PET': len(self.pet_files),
            'SPECT': len(self.spect_files),
            'RTSTRUCT': 1 if self.rt_struct else 0,
            'RTDOSE': 1 if self.rt_dose else 0,
            'RTPLAN': 1 if self.rt_plan else 0,
            'RTIMAGE': 1 if self.rt_image else 0
        }
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

    def extract_image_volume(self, modality: str = 'CT') -> Tuple[Optional[ImageData], Dict[str, Any]]:
        """
        Trích xuất dữ liệu hình ảnh 3D từ các file DICOM.
        
        Args:
            modality: Loại ảnh cần trích xuất ('CT', 'MR', 'PT', 'SPECT')
            
        Returns:
            Tuple[Optional[ImageData], Dict[str, Any]]: (Dữ liệu hình ảnh, metadata)
        """
        files = None
        if modality == 'CT':
            files = self.ct_files
        elif modality == 'MR':
            files = self.mri_files
        elif modality == 'PT':
            files = self.pet_files
        elif modality == 'SPECT':
            files = self.spect_files
            
        if not files:
            logger.error(f"Không có file {modality} để trích xuất")
            return None, {}
            
        try:
            # Đọc file đầu tiên để lấy thông tin chung
            first_ds = pydicom.dcmread(files[0])
            
            # Lấy thông tin không gian
            pixel_spacing = first_ds.PixelSpacing
            slice_thickness = getattr(first_ds, 'SliceThickness', pixel_spacing[0])
            spacing = (float(pixel_spacing[0]), float(pixel_spacing[1]), float(slice_thickness))
            
            origin = [float(x) for x in first_ds.ImagePositionPatient]
            direction = [float(x) for x in first_ds.ImageOrientationPatient] + [0, 0, 1]
            
            # Lấy thông tin window/level
            window_center = getattr(first_ds, 'WindowCenter', 40)
            window_width = getattr(first_ds, 'WindowWidth', 400)
            if isinstance(window_center, list):
                window_center = window_center[0]
            if isinstance(window_width, list):
                window_width = window_width[0]
                
            # Lấy thông tin rescale
            rescale_slope = float(getattr(first_ds, 'RescaleSlope', 1.0))
            rescale_intercept = float(getattr(first_ds, 'RescaleIntercept', 0.0))
            
            # Đọc tất cả các slice
            slices = []
            for file in files:
                ds = pydicom.dcmread(file)
                slices.append(ds.pixel_array)
                
            # Tạo volume 3D
            volume = np.stack(slices)
            
            # Tạo đối tượng ImageData
            image_data = ImageData(
                pixel_array=volume,
                spacing=spacing,
                origin=tuple(origin),
                direction=tuple(direction),
                modality=modality,
                patient_position=getattr(first_ds, 'PatientPosition', 'HFS'),
                study_uid=first_ds.StudyInstanceUID,
                series_uid=first_ds.SeriesInstanceUID,
                frame_of_reference_uid=getattr(first_ds, 'FrameOfReferenceUID', ''),
                window_center=float(window_center),
                window_width=float(window_width),
                rescale_slope=rescale_slope,
                rescale_intercept=rescale_intercept,
                metadata={
                    'manufacturer': getattr(first_ds, 'Manufacturer', ''),
                    'model_name': getattr(first_ds, 'ManufacturerModelName', ''),
                    'series_description': getattr(first_ds, 'SeriesDescription', '')
                }
            )
            
            return image_data, self.patient_info
            
        except Exception as error:
            logger.error(f"Lỗi khi trích xuất dữ liệu {modality}: {str(error)}")
            return None, {}

    def extract_rt_structure(self, referenced_image: Optional[ImageData] = None) -> Optional[StructureSet]:
        """
        Trích xuất dữ liệu cấu trúc từ file RTSTRUCT.
        
        Args:
            referenced_image: Dữ liệu hình ảnh tham chiếu
            
        Returns:
            Optional[StructureSet]: Tập hợp các cấu trúc
        """
        if not self.rt_struct:
            logger.error("Không có file RTSTRUCT để trích xuất")
            return None
            
        try:
            ds = pydicom.dcmread(self.rt_struct)
            
            # Kiểm tra xem có dữ liệu ROI không
            if not hasattr(ds, 'ROIContourSequence') or not hasattr(ds, 'StructureSetROISequence'):
                logger.error("File RTSTRUCT không có dữ liệu ROI")
                return None
                
            # Tạo dict chứa thông tin ROI
            roi_info = {}
            for roi in ds.StructureSetROISequence:
                roi_number = str(roi.ROINumber)
                roi_name = str(roi.ROIName)
                roi_info[roi_number] = {
                    'name': roi_name,
                    'number': int(roi_number)
                }
                
            # Tạo dict chứa các cấu trúc
            structures = {}
            
            # Lấy thông tin không gian từ ảnh tham chiếu hoặc từ RTSTRUCT
            if referenced_image:
                spacing = referenced_image.spacing
                origin = referenced_image.origin
                direction = referenced_image.direction
                shape = referenced_image.shape
            else:
                # Lấy thông tin từ referenced image sequence trong RTSTRUCT
                ref_frame = ds.ReferencedFrameOfReferenceSequence[0]
                ref_study = ref_frame.RTReferencedStudySequence[0]
                ref_series = ref_study.RTReferencedSeriesSequence[0]
                
                # Đọc file CT đầu tiên để lấy thông tin không gian
                first_ct = pydicom.dcmread(self.ct_files[0])
                spacing = (
                    float(first_ct.PixelSpacing[0]),
                    float(first_ct.PixelSpacing[1]),
                    float(first_ct.SliceThickness)
                )
                origin = tuple(float(x) for x in first_ct.ImagePositionPatient)
                direction = tuple(float(x) for x in first_ct.ImageOrientationPatient) + (0, 0, 1)
                shape = (len(self.ct_files), first_ct.Rows, first_ct.Columns)
                
            # Lặp qua từng ROI trong ROIContourSequence
            for roi in ds.ROIContourSequence:
                roi_number = str(roi.ReferencedROINumber)
                if roi_number not in roi_info:
                    continue
                    
                roi_name = roi_info[roi_number]['name']
                
                # Xác định loại cấu trúc
                if 'PTV' in roi_name or 'CTV' in roi_name or 'GTV' in roi_name:
                    structure_type = StructureType.TARGET
                elif roi_name.lower() in ['body', 'external', 'patient']:
                    structure_type = StructureType.EXTERNAL
                elif roi_name.lower() in ['couch', 'table', 'support']:
                    structure_type = StructureType.SUPPORT
                else:
                    structure_type = StructureType.OAR
                    
                # Tạo mask rỗng
                mask = np.zeros(shape, dtype=bool)
                
                # Lấy màu sắc
                if hasattr(roi, 'ROIDisplayColor'):
                    color = tuple(float(x)/255 for x in roi.ROIDisplayColor)
                else:
                    color = (1.0, 0.0, 0.0)  # Đỏ
                    
                # Tạo cấu trúc mới
                structure = Structure(
                    name=roi_name,
                    type=structure_type,
                    number=roi_info[roi_number]['number'],
                    mask=mask,
                    color=color
                )
                
                # Thêm vào dict
                structures[roi_name] = structure
                
            # Tạo StructureSet
            structure_set = StructureSet(
                structures=structures,
                spacing=spacing,
                origin=origin,
                direction=direction,
                study_uid=ds.StudyInstanceUID,
                series_uid=ds.SeriesInstanceUID,
                frame_of_reference_uid=ds.FrameOfReferenceUID,
                structure_set_uid=ds.SOPInstanceUID
            )
            
            return structure_set
            
        except Exception as error:
            logger.error(f"Lỗi khi trích xuất RT Structure: {str(error)}")
            return None

    def extract_rt_plan(self) -> Optional[PlanConfig]:
        """
        Trích xuất thông tin kế hoạch từ file RTPLAN.
        
        Returns:
            Optional[PlanConfig]: Cấu hình kế hoạch
        """
        if not self.rt_plan:
            logger.error("Không có file RTPLAN để trích xuất")
            return None
            
        try:
            ds = pydicom.dcmread(self.rt_plan)
            
            # Tạo prescription config
            prescription = PrescriptionConfig(
                total_dose=0.0,  # Sẽ được cập nhật sau
                fraction_count=1,  # Giá trị mặc định
                fraction_dose=0.0,  # Sẽ được cập nhật sau
                target_name='',  # Sẽ được cập nhật sau
                target_type='PTV'  # Giá trị mặc định
            )
            
            # Cập nhật thông tin phân liều từ FractionGroupSequence
            if hasattr(ds, 'FractionGroupSequence'):
                fg = ds.FractionGroupSequence[0]
                prescription.fraction_count = int(fg.NumberOfFractionsPlanned)
                
                # Tìm liều kê trong DoseReferenceSequence
                if hasattr(ds, 'DoseReferenceSequence'):
                    for dose_ref in ds.DoseReferenceSequence:
                        if hasattr(dose_ref, 'TargetPrescriptionDose'):
                            prescription.total_dose = float(dose_ref.TargetPrescriptionDose)
                            prescription.fraction_dose = prescription.total_dose / prescription.fraction_count
                            if hasattr(dose_ref, 'DoseReferenceStructureType'):
                                prescription.target_type = dose_ref.DoseReferenceStructureType
                            break
                            
            # Tạo danh sách beam
            beams = []
            if hasattr(ds, 'BeamSequence'):
                for beam in ds.BeamSequence:
                    # Xác định loại kỹ thuật
                    if beam.BeamType == 'STATIC':
                        technique = TechniqueType.STATIC
                    elif beam.BeamType == 'DYNAMIC':
                        technique = TechniqueType.VMAT
                    else:
                        technique = TechniqueType.STATIC
                        
                    # Xác định loại bức xạ
                    if beam.RadiationType == 'PHOTON':
                        radiation_type = RadiationType.PHOTON
                    elif beam.RadiationType == 'ELECTRON':
                        radiation_type = RadiationType.ELECTRON
                    elif beam.RadiationType == 'PROTON':
                        radiation_type = RadiationType.PROTON
                    else:
                        radiation_type = RadiationType.PHOTON
                        
                    # Lấy thông tin control point đầu tiên
                    cp = beam.ControlPointSequence[0]
                    
                    # Tạo beam config
                    beam_config = BeamConfig(
                        name=beam.BeamName,
                        number=beam.BeamNumber,
                        type=technique,
                        radiation_type=radiation_type,
                        machine_name=beam.TreatmentMachineName,
                        energy=str(cp.NominalBeamEnergy),
                        isocenter=tuple(float(x) for x in cp.IsocenterPosition),
                        gantry_angle=float(cp.GantryAngle),
                        collimator_angle=float(cp.BeamLimitingDeviceAngle),
                        couch_angle=float(cp.PatientSupportAngle),
                        field_x=(-50.0, 50.0),  # Giá trị mặc định
                        field_y=(-50.0, 50.0),  # Giá trị mặc định
                        sad=float(beam.SourceAxisDistance)
                    )
                    
                    # Thêm thông tin field size từ BeamLimitingDevicePositionSequence
                    if hasattr(cp, 'BeamLimitingDevicePositionSequence'):
                        for device in cp.BeamLimitingDevicePositionSequence:
                            if device.RTBeamLimitingDeviceType == 'X':
                                beam_config.field_x = tuple(float(x) for x in device.LeafJawPositions)
                            elif device.RTBeamLimitingDeviceType == 'Y':
                                beam_config.field_y = tuple(float(x) for x in device.LeafJawPositions)
                            elif device.RTBeamLimitingDeviceType == 'MLCX':
                                beam_config.mlc_segments = [list(float(x) for x in device.LeafJawPositions)]
                                
                    # Thêm thông tin VMAT
                    if technique == TechniqueType.VMAT and len(beam.ControlPointSequence) > 1:
                        last_cp = beam.ControlPointSequence[-1]
                        beam_config.arc_direction = cp.GantryRotationDirection
                        beam_config.arc_start_angle = float(cp.GantryAngle)
                        beam_config.arc_stop_angle = float(last_cp.GantryAngle)
                        
                    beams.append(beam_config)
                    
            # Tạo plan config
            plan_config = PlanConfig(
                plan_id=ds.SOPInstanceUID,
                plan_name=ds.RTPlanLabel,
                technique=TechniqueType.STATIC,  # Sẽ được cập nhật dựa trên beam
                radiation_type=RadiationType.PHOTON,  # Sẽ được cập nhật dựa trên beam
                machine_name=beams[0].machine_name if beams else 'LINAC',
                energy=beams[0].energy if beams else '6MV',
                patient_id=self.patient_info.get('PatientID', ''),
                patient_name=str(self.patient_info.get('PatientName', '')),
                patient_position=getattr(ds, 'PatientPosition', 'HFS'),
                prescription=prescription,
                beams=beams,
                created_time=datetime.datetime.now(),
                modified_time=datetime.datetime.now()
            )
            
            # Cập nhật technique và radiation_type từ beam đầu tiên
            if beams:
                plan_config.technique = beams[0].type
                plan_config.radiation_type = beams[0].radiation_type
                
            return plan_config
            
        except Exception as error:
            logger.error(f"Lỗi khi trích xuất RT Plan: {str(error)}")
            return None

    def extract_rt_dose(self) -> Optional[DoseData]:
        """
        Trích xuất dữ liệu liều từ file RTDOSE.
        
        Returns:
            Optional[DoseData]: Dữ liệu liều
        """
        if not self.rt_dose:
            logger.error("Không có file RTDOSE để trích xuất")
            return None
            
        try:
            ds = pydicom.dcmread(self.rt_dose)
            
            # Lấy thông tin không gian
            spacing = (
                float(ds.PixelSpacing[0]),
                float(ds.PixelSpacing[1]),
                float(ds.SliceThickness)
            )
            origin = tuple(float(x) for x in ds.ImagePositionPatient)
            direction = tuple(float(x) for x in ds.ImageOrientationPatient) + (0, 0, 1)
            
            # Lấy dữ liệu pixel và áp dụng scaling
            dose_scaling = float(ds.DoseGridScaling)
            dose_array = ds.pixel_array * dose_scaling
            
            # Tạo DoseData
            dose_data = DoseData(
                dose_matrix=dose_array,
                spacing=spacing,
                origin=origin,
                direction=direction,
                dose_type=DoseType.PHYSICAL,
                dose_unit='GY',
                dose_summation_type=ds.DoseSummationType,
                referenced_plan_uid=None,  # Sẽ được cập nhật nếu có
                metadata={
                    'manufacturer': getattr(ds, 'Manufacturer', ''),
                    'model_name': getattr(ds, 'ManufacturerModelName', ''),
                    'series_description': getattr(ds, 'SeriesDescription', '')
                }
            )
            
            # Thêm tham chiếu đến RT Plan nếu có
            if hasattr(ds, 'ReferencedRTPlanSequence'):
                ref_plan = ds.ReferencedRTPlanSequence[0]
                dose_data.referenced_plan_uid = ref_plan.ReferencedSOPInstanceUID
                
            return dose_data
            
        except Exception as error:
            logger.error(f"Lỗi khi trích xuất RT Dose: {str(error)}")
            return None

    def _get_slice_location(self, file_path):
        """Lấy vị trí slice từ file DICOM."""
        ds = pydicom.dcmread(file_path, stop_before_pixels=True)
        if hasattr(ds, 'ImagePositionPatient'):
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