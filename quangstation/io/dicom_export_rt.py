#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module cung cấp chức năng xuất dữ liệu xạ trị (RT) sang định dạng DICOM.
Bao gồm RT Plan, RT Dose, RT Structure, RT Image.
"""

import os
import datetime
import numpy as np
from typing import Dict, List, Any, Optional, Tuple

# Sử dụng module external_integration để quản lý thư viện bên ngoài
from quangstation.utils.external_integration import get_module
from quangstation.utils.logging import get_logger
from quangstation.io.dicom_constants import *  # Import các hằng số DICOM

logger = get_logger(__name__)

# Lấy module pydicom từ external_integration
pydicom = get_module("pydicom")
if not pydicom:
    logger.error("Không thể import pydicom. Chức năng xuất DICOM sẽ không hoạt động.")
else:
    from pydicom.dataset import Dataset, FileDataset
    from pydicom.sequence import Sequence

def export_dicom_data(export_folder: str, image_data: Optional[np.ndarray] = None, 
                    structures: Optional[Dict] = None, plan_config: Optional[Dict] = None, 
                    dose_data: Optional[np.ndarray] = None, 
                    patient_info: Optional[Dict] = None,
                    dose_spacing: Optional[Tuple[float, float, float]] = None,
                    dose_origin: Optional[Tuple[float, float, float]] = None,
                    dose_positions: Optional[List[float]] = None,
                    structure_uid: Optional[str] = None,
                    rtplan_uid: Optional[str] = None) -> Dict[str, str]:
    """
    Xuất dữ liệu sang định dạng DICOM.
    
    Args:
        export_folder: Thư mục đích.
        image_data: Dữ liệu hình ảnh 3D (numpy array).
        structures: Thông tin cấu trúc cần xuất.
        plan_config: Cấu hình kế hoạch xạ trị.
        dose_data: Dữ liệu liều 3D (numpy array).
        patient_info: Thông tin bệnh nhân.
        dose_spacing: Khoảng cách giữa các điểm liều (mm).
        dose_origin: Điểm gốc của lưới liều (mm).
        dose_positions: Vị trí các lát cắt liều (mm).
        structure_uid: UID của RT Structure Set.
        rtplan_uid: UID của RT Plan.
            
    Returns:
        Dict[str, str]: Đường dẫn đến các file DICOM đã xuất.
    """
    if not pydicom:
        logger.error("Không thể xuất DICOM vì thiếu thư viện pydicom")
        return {}
    
    try:
        # Tạo thư mục xuất nếu chưa tồn tại
        os.makedirs(export_folder, exist_ok=True)
        
        # Khởi tạo dict lưu đường dẫn file xuất
        exported_files = {}
        
        # Xuất dữ liệu hình ảnh CT nếu có
        if image_data is not None:
            ct_folder = os.path.join(export_folder, 'CT')
            os.makedirs(ct_folder, exist_ok=True)
            exported_files['ct'] = export_ct_images(image_data, ct_folder, patient_info)
            logger.info(f"Đã xuất {len(exported_files['ct'])} file CT")
        
        # Xuất RT Structure nếu có
        if structures:
            struct_path = os.path.join(export_folder, 'structure.dcm')
            exported_files['structure'] = export_rt_structure(structures, struct_path, patient_info, structure_uid)
            logger.info(f"Đã xuất RT Structure: {struct_path}")
        
        # Xuất RT Plan nếu có
        if plan_config:
            plan_path = os.path.join(export_folder, 'plan.dcm')
            exported_files['plan'] = export_rt_plan(plan_config, plan_path, patient_info, structure_uid)
            logger.info(f"Đã xuất RT Plan: {plan_path}")
        
        # Xuất RT Dose nếu có
        if dose_data is not None:
            dose_path = os.path.join(export_folder, 'dose.dcm')
            exported_files['dose'] = export_rt_dose(dose_data, dose_path, patient_info, 
                                                  dose_spacing, dose_origin, dose_positions, rtplan_uid)
            logger.info(f"Đã xuất RT Dose: {dose_path}")
        
        return exported_files
        
    except Exception as error:
        logger.error(f"Lỗi khi xuất dữ liệu DICOM: {str(error)}")
        return {}

def export_ct_images(image_data: np.ndarray, output_folder: str, 
                    patient_info: Optional[Dict] = None) -> List[str]:
    """
    Xuất dữ liệu hình ảnh CT sang các file DICOM.
    
    Args:
        image_data: Dữ liệu hình ảnh 3D.
        output_folder: Thư mục xuất.
        patient_info: Thông tin bệnh nhân.
        
    Returns:
        List[str]: Danh sách đường dẫn đến các file CT đã xuất.
    """
    try:
        exported_files = []
        
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(output_folder, exist_ok=True)
        
        # Lấy kích thước dữ liệu
        num_slices, rows, cols = image_data.shape
        
        # Tạo study và series UID
        study_uid = pydicom.uid.generate_uid()
        series_uid = pydicom.uid.generate_uid()
        
        # Xuất từng slice
        for i in range(num_slices):
            # Tạo file path
            output_path = os.path.join(output_folder, f'CT_{i+1:04d}.dcm')
            
            # Tạo dataset mới
            file_meta = Dataset()
            file_meta.MediaStorageSOPClassUID = CT_IMAGE_STORAGE
            file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
            file_meta.TransferSyntaxUID = EXPLICIT_VR_LITTLE_ENDIAN
            
            # Tạo dataset chính
            ds = FileDataset(output_path, {}, file_meta=file_meta, preamble=b"\0" * 128)
            
            # Thiết lập các thẻ bắt buộc
            ds.SOPClassUID = CT_IMAGE_STORAGE
            ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
            ds.StudyInstanceUID = study_uid
            ds.SeriesInstanceUID = series_uid
            ds.Modality = MODALITY_CT
            
            # Thêm thông tin bệnh nhân nếu có
            if patient_info:
                for key, value in patient_info.items():
                    if hasattr(ds, key):
                        setattr(ds, key, value)
            
            # Thiết lập thông tin hình ảnh
            ds.SamplesPerPixel = 1
            ds.PhotometricInterpretation = "MONOCHROME2"
            ds.Rows = rows
            ds.Columns = cols
            ds.BitsAllocated = 16
            ds.BitsStored = 16
            ds.HighBit = 15
            ds.PixelRepresentation = 1  # Signed
            
            # Chuyển đổi slice thành mảng 16-bit
            pixel_array = image_data[i].astype(np.int16)
            ds.PixelData = pixel_array.tobytes()
            
            # Lưu file
            ds.save_as(output_path)
            exported_files.append(output_path)
            
        return exported_files
        
    except Exception as error:
        logger.error(f"Lỗi khi xuất CT images: {str(error)}")
        return []

def export_rt_structure(structures: Dict, output_path: str,
                       patient_info: Optional[Dict] = None,
                       referenced_ct_uid: Optional[str] = None) -> str:
    """
    Xuất dữ liệu cấu trúc sang file DICOM RT Structure Set.
    
    Args:
        structures: Dict chứa thông tin các cấu trúc.
        output_path: Đường dẫn file xuất.
        patient_info: Thông tin bệnh nhân.
        referenced_ct_uid: UID của series CT tham chiếu.
        
    Returns:
        str: Đường dẫn đến file RT Structure đã xuất.
    """
    try:
        # Tạo file meta
        file_meta = Dataset()
        file_meta.MediaStorageSOPClassUID = RT_STRUCTURE_SET_STORAGE
        file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
        file_meta.TransferSyntaxUID = EXPLICIT_VR_LITTLE_ENDIAN
        
        # Tạo dataset chính
        ds = FileDataset(output_path, {}, file_meta=file_meta, preamble=b"\0" * 128)
        
        # Thiết lập các thẻ bắt buộc
        ds.SOPClassUID = RT_STRUCTURE_SET_STORAGE
        ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
        ds.Modality = MODALITY_RTSTRUCT
        
        # Thêm thông tin bệnh nhân nếu có
        if patient_info:
            for key, value in patient_info.items():
                if hasattr(ds, key):
                    setattr(ds, key, value)
        
        # Tạo Structure Set sequence
        ds.StructureSetROISequence = Sequence()
        ds.ROIContourSequence = Sequence()
        ds.RTROIObservationsSequence = Sequence()
        
        # Thêm từng cấu trúc
        for roi_number, (name, struct_data) in enumerate(structures.items(), start=1):
            # Structure Set ROI Sequence
            structure_set_roi = Dataset()
            structure_set_roi.ROINumber = roi_number
            structure_set_roi.ROIName = name
            structure_set_roi.ROIGenerationAlgorithm = 'MANUAL'
            ds.StructureSetROISequence.append(structure_set_roi)
            
            # ROI Contour Sequence
            roi_contour = Dataset()
            roi_contour.ROIDisplayColor = struct_data.get('color', [255, 0, 0])
            roi_contour.ReferencedROINumber = roi_number
            roi_contour.ContourSequence = Sequence()
            
            # Thêm dữ liệu contour
            for contour_data in struct_data.get('contour_data', []):
                contour = Dataset()
                contour.ContourGeometricType = 'CLOSED_PLANAR'
                contour.NumberOfContourPoints = len(contour_data) // 3
                contour.ContourData = contour_data
                roi_contour.ContourSequence.append(contour)
                
            ds.ROIContourSequence.append(roi_contour)
            
            # RT ROI Observations Sequence
            rt_roi_obs = Dataset()
            rt_roi_obs.ObservationNumber = roi_number
            rt_roi_obs.ReferencedROINumber = roi_number
            rt_roi_obs.ROIObservationLabel = name
            rt_roi_obs.RTROIInterpretedType = 'ORGAN'
            ds.RTROIObservationsSequence.append(rt_roi_obs)
        
        # Lưu file
        ds.save_as(output_path)
        return output_path
        
    except Exception as error:
        logger.error(f"Lỗi khi xuất RT Structure: {str(error)}")
        return ""

def export_rt_plan(plan_config: Dict, output_path: str,
                  patient_info: Optional[Dict] = None,
                  structure_uid: Optional[str] = None) -> str:
    """
    Xuất dữ liệu kế hoạch sang file DICOM RT Plan.
    
    Args:
        plan_config: Cấu hình kế hoạch xạ trị.
        output_path: Đường dẫn file xuất.
        patient_info: Thông tin bệnh nhân.
        structure_uid: UID của RT Structure Set tham chiếu.
        
    Returns:
        str: Đường dẫn đến file RT Plan đã xuất.
    """
    try:
        # Tạo file meta
        file_meta = Dataset()
        file_meta.MediaStorageSOPClassUID = RT_PLAN_STORAGE
        file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
        file_meta.TransferSyntaxUID = EXPLICIT_VR_LITTLE_ENDIAN
        
        # Tạo dataset chính
        ds = FileDataset(output_path, {}, file_meta=file_meta, preamble=b"\0" * 128)
        
        # Thiết lập các thẻ bắt buộc
        ds.SOPClassUID = RT_PLAN_STORAGE
        ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
        ds.Modality = MODALITY_RTPLAN
        
        # Thêm thông tin bệnh nhân nếu có
        if patient_info:
            for key, value in patient_info.items():
                if hasattr(ds, key):
                    setattr(ds, key, value)
        
        # Thiết lập thông tin kế hoạch
        ds.RTPlanLabel = plan_config.get('plan_name', 'Plan')
        ds.RTPlanDate = datetime.datetime.now().strftime('%Y%m%d')
        ds.RTPlanTime = datetime.datetime.now().strftime('%H%M%S')
        
        # Tạo Fraction Group Sequence
        ds.FractionGroupSequence = Sequence()
        fg = Dataset()
        fg.FractionGroupNumber = 1
        fg.NumberOfFractionsPlanned = plan_config.get('fraction_count', 1)
        fg.NumberOfBeams = len(plan_config.get('beams', []))
        fg.NumberOfBrachyApplicationSetups = 0
        ds.FractionGroupSequence.append(fg)
        
        # Tạo Beam Sequence
        ds.BeamSequence = Sequence()
        for i, beam in enumerate(plan_config.get('beams', []), start=1):
            beam_ds = Dataset()
            beam_ds.BeamNumber = i
            beam_ds.BeamName = beam.get('name', f'Beam {i}')
            beam_ds.BeamType = beam.get('type', 'STATIC')
            beam_ds.RadiationType = beam.get('radiation_type', 'PHOTON')
            beam_ds.TreatmentMachineName = beam.get('machine_name', 'LINAC')
            beam_ds.SourceAxisDistance = beam.get('sad', "1000")
            
            # Control Point Sequence
            beam_ds.ControlPointSequence = Sequence()
            cp = Dataset()
            cp.ControlPointIndex = 0
            cp.NominalBeamEnergy = beam.get('energy', 6)
            cp.DoseRateSet = beam.get('dose_rate', 600)
            cp.GantryAngle = beam.get('gantry_angle', 0)
            cp.BeamLimitingDeviceAngle = beam.get('collimator_angle', 0)
            cp.PatientSupportAngle = beam.get('couch_angle', 0)
            beam_ds.ControlPointSequence.append(cp)
            
            ds.BeamSequence.append(beam_ds)
        
        # Lưu file
        ds.save_as(output_path)
        return output_path
        
    except Exception as error:
        logger.error(f"Lỗi khi xuất RT Plan: {str(error)}")
        return ""

def export_rt_dose(dose_data: np.ndarray, output_path: str,
                  patient_info: Optional[Dict] = None,
                  dose_spacing: Optional[Tuple[float, float, float]] = None,
                  dose_origin: Optional[Tuple[float, float, float]] = None,
                  dose_positions: Optional[List[float]] = None,
                  rtplan_uid: Optional[str] = None) -> str:
    """
    Xuất dữ liệu liều sang file DICOM RT Dose.
    
    Args:
        dose_data: Dữ liệu liều 3D.
        output_path: Đường dẫn file xuất.
        patient_info: Thông tin bệnh nhân.
        dose_spacing: Khoảng cách giữa các điểm liều (mm).
        dose_origin: Điểm gốc của lưới liều (mm).
        dose_positions: Vị trí các lát cắt liều (mm).
        rtplan_uid: UID của RT Plan tham chiếu.
        
    Returns:
        str: Đường dẫn đến file RT Dose đã xuất.
    """
    try:
        # Tạo file meta
        file_meta = Dataset()
        file_meta.MediaStorageSOPClassUID = RT_DOSE_STORAGE
        file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
        file_meta.TransferSyntaxUID = EXPLICIT_VR_LITTLE_ENDIAN
        
        # Tạo dataset chính
        ds = FileDataset(output_path, {}, file_meta=file_meta, preamble=b"\0" * 128)
        
        # Thiết lập các thẻ bắt buộc
        ds.SOPClassUID = RT_DOSE_STORAGE
        ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
        ds.Modality = MODALITY_RTDOSE
        
        # Thêm thông tin bệnh nhân nếu có
        if patient_info:
            for key, value in patient_info.items():
                if hasattr(ds, key):
                    setattr(ds, key, value)
        
        # Thiết lập thông tin liều
        ds.DoseUnits = 'GY'
        ds.DoseType = 'PHYSICAL'
        ds.DoseComment = 'Dose calculated by QuangStation'
        ds.DoseSummationType = 'PLAN'
        
        # Thiết lập thông tin không gian
        if dose_spacing:
            ds.PixelSpacing = [dose_spacing[0], dose_spacing[1]]
            ds.SliceThickness = dose_spacing[2]
        else:
            ds.PixelSpacing = [2.0, 2.0]
            ds.SliceThickness = 2.0
            
        if dose_origin:
            ds.ImagePositionPatient = list(dose_origin)
        else:
            ds.ImagePositionPatient = [0.0, 0.0, 0.0]
            
        ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
        
        # Thiết lập thông tin pixel
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.Rows = dose_data.shape[1]
        ds.Columns = dose_data.shape[2]
        ds.NumberOfFrames = dose_data.shape[0]
        ds.BitsAllocated = 16
        ds.BitsStored = 16
        ds.HighBit = 15
        ds.PixelRepresentation = 0
        
        # Chuyển đổi dữ liệu liều
        dose_scaling = 1000.0  # Scale để giữ độ chính xác
        scaled_dose = (dose_data * dose_scaling).astype(np.uint16)
        ds.PixelData = scaled_dose.tobytes()
        ds.DoseGridScaling = 1.0 / dose_scaling
        
        # Thiết lập GridFrameOffsetVector
        if dose_positions:
            ds.GridFrameOffsetVector = [pos - dose_positions[0] for pos in dose_positions]
        else:
            ds.GridFrameOffsetVector = [i * ds.SliceThickness for i in range(ds.NumberOfFrames)]
        
        # Thêm tham chiếu đến RT Plan nếu có
        if rtplan_uid:
            ds.ReferencedRTPlanSequence = Sequence()
            ref_plan = Dataset()
            ref_plan.ReferencedSOPClassUID = RT_PLAN_STORAGE
            ref_plan.ReferencedSOPInstanceUID = rtplan_uid
            ds.ReferencedRTPlanSequence.append(ref_plan)
        
        # Lưu file
        ds.save_as(output_path)
        return output_path
        
    except Exception as error:
        logger.error(f"Lỗi khi xuất RT Dose: {str(error)}")
        return "" 