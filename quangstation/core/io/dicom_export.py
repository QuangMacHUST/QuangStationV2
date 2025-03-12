#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module cung cấp chức năng xuất kế hoạch xạ trị sang định dạng DICOM.
"""

import os
from typing import Dict, Any
import datetime

# Sử dụng module external_integration để quản lý thư viện bên ngoài một cách nhất quán
from quangstation.core.utils.external_integration import get_module
from quangstation.core.utils.logging import get_logger

logger = get_logger(__name__)

# Lấy module pydicom từ external_integration
pydicom = get_module("pydicom")
if pydicom:
    from pydicom.dataset import Dataset, FileDataset
    from pydicom.sequence import Sequence
else:
    logger.error("Không thể import pydicom. Vui lòng cài đặt thư viện này.")
    Dataset = None
    FileDataset = None
    Sequence = None

def export_plan_to_dicom(plan_data: Dict[str, Any], output_dir: str) -> Dict[str, str]:
    """
    Xuất kế hoạch xạ trị sang định dạng DICOM (RT Plan, RT Dose, RT Struct)
    
    Args:
        plan_data: Dữ liệu kế hoạch xạ trị
        output_dir: Thư mục đầu ra
        
    Returns:
        Dict[str, str]: Đường dẫn đến các file DICOM đã xuất
    """
    if not pydicom:
        logger.error("Không thể xuất DICOM vì thiếu thư viện pydicom")
        return {}
        
    logger.info(f"Đang xuất kế hoạch sang DICOM vào thư mục {output_dir}")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Tạo File UIDs
    rt_plan_uid = pydicom.uid.generate_uid()
    rt_struct_uid = pydicom.uid.generate_uid()
    rt_dose_uid = pydicom.uid.generate_uid()
    
    # Xuất RT Plan
    rt_plan_path = os.path.join(output_dir, "rt_plan.dcm")
    _create_rt_plan(plan_data, rt_plan_path, rt_plan_uid)
    
    # Xuất RT Structure
    rt_structure_path = os.path.join(output_dir, "rt_structure.dcm")
    _create_rt_structure(plan_data, rt_structure_path, rt_struct_uid, rt_plan_uid)
    
    # Xuất RT Dose
    rt_dose_path = os.path.join(output_dir, "rt_dose.dcm")
    _create_rt_dose(plan_data, rt_dose_path, rt_dose_uid, rt_plan_uid)
    
    logger.info("Xuất kế hoạch DICOM thành công.")
    
    return {
        "rt_plan": rt_plan_path,
        "rt_structure": rt_structure_path,
        "rt_dose": rt_dose_path
    }

def _create_rt_plan(plan_data: Dict[str, Any], output_path: str, rt_plan_uid: str) -> None:
    """
    Tạo file RT Plan DICOM
    
    Args:
        plan_data: Dữ liệu kế hoạch xạ trị
        output_path: Đường dẫn file đầu ra
        rt_plan_uid: UID của kế hoạch
    """
    # Tạo dataset cơ bản
    file_meta = Dataset()
    file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.481.5'  # RT Plan Storage
    file_meta.MediaStorageSOPInstanceUID = rt_plan_uid
    file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
    
    # Tạo file dataset
    ds = FileDataset(output_path, {}, file_meta=file_meta, preamble=b"\0" * 128)
    
    # Thiết lập các thông tin bắt buộc
    ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.481.5'  # RT Plan Storage
    ds.SOPInstanceUID = rt_plan_uid
    ds.StudyDate = datetime.datetime.now().strftime('%Y%m%d')
    ds.StudyTime = datetime.datetime.now().strftime('%H%M%S')
    ds.AccessionNumber = ''
    ds.Modality = 'RTPLAN'
    ds.Manufacturer = 'QuangStation V2'
    
    # Thông tin bệnh nhân
    patient_info = plan_data.get('patient', {})
    ds.PatientName = patient_info.get('name', 'ANONYMOUS')
    ds.PatientID = patient_info.get('id', '00000000')
    ds.PatientBirthDate = patient_info.get('birth_date', '')
    ds.PatientSex = patient_info.get('gender', '')
    
    # Thông tin kế hoạch
    ds.RTPlanLabel = plan_data.get('name', 'Unnamed Plan')
    ds.RTPlanDate = datetime.datetime.now().strftime('%Y%m%d')
    ds.RTPlanTime = datetime.datetime.now().strftime('%H%M%S')
    ds.RTPlanGeometry = 'PATIENT'
    
    # Lưu file
    ds.save_as(output_path)
    logger.info(f"Đã tạo file RT Plan: {output_path}")

def _create_rt_structure(plan_data: Dict[str, Any], output_path: str, rt_struct_uid: str, rt_plan_uid: str) -> None:
    """
    Tạo file RT Structure DICOM
    
    Args:
        plan_data: Dữ liệu kế hoạch xạ trị
        output_path: Đường dẫn file đầu ra
        rt_struct_uid: UID của cấu trúc
        rt_plan_uid: UID của kế hoạch
    """
    # Tạo dataset cơ bản
    file_meta = Dataset()
    file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.481.3'  # RT Structure Set Storage
    file_meta.MediaStorageSOPInstanceUID = rt_struct_uid
    file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
    
    # Tạo file dataset
    ds = FileDataset(output_path, {}, file_meta=file_meta, preamble=b"\0" * 128)
    
    # Thiết lập các thông tin bắt buộc
    ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.481.3'  # RT Structure Set Storage
    ds.SOPInstanceUID = rt_struct_uid
    ds.StudyDate = datetime.datetime.now().strftime('%Y%m%d')
    ds.StudyTime = datetime.datetime.now().strftime('%H%M%S')
    ds.AccessionNumber = ''
    ds.Modality = 'RTSTRUCT'
    ds.Manufacturer = 'QuangStation V2'
    
    # Thông tin bệnh nhân
    patient_info = plan_data.get('patient', {})
    ds.PatientName = patient_info.get('name', 'ANONYMOUS')
    ds.PatientID = patient_info.get('id', '00000000')
    ds.PatientBirthDate = patient_info.get('birth_date', '')
    ds.PatientSex = patient_info.get('gender', '')
    
    # Lưu file
    ds.save_as(output_path)
    logger.info(f"Đã tạo file RT Structure: {output_path}")

def _create_rt_dose(plan_data: Dict[str, Any], output_path: str, rt_dose_uid: str, rt_plan_uid: str) -> None:
    """
    Tạo file RT Dose DICOM
    
    Args:
        plan_data: Dữ liệu kế hoạch xạ trị
        output_path: Đường dẫn file đầu ra
        rt_dose_uid: UID của liều
        rt_plan_uid: UID của kế hoạch
    """
    # Tạo dataset cơ bản
    file_meta = Dataset()
    file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.481.2'  # RT Dose Storage
    file_meta.MediaStorageSOPInstanceUID = rt_dose_uid
    file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
    
    # Tạo file dataset
    ds = FileDataset(output_path, {}, file_meta=file_meta, preamble=b"\0" * 128)
    
    # Thiết lập các thông tin bắt buộc
    ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.481.2'  # RT Dose Storage
    ds.SOPInstanceUID = rt_dose_uid
    ds.StudyDate = datetime.datetime.now().strftime('%Y%m%d')
    ds.StudyTime = datetime.datetime.now().strftime('%H%M%S')
    ds.AccessionNumber = ''
    ds.Modality = 'RTDOSE'
    ds.Manufacturer = 'QuangStation V2'
    
    # Thông tin bệnh nhân
    patient_info = plan_data.get('patient', {})
    ds.PatientName = patient_info.get('name', 'ANONYMOUS')
    ds.PatientID = patient_info.get('id', '00000000')
    ds.PatientBirthDate = patient_info.get('birth_date', '')
    ds.PatientSex = patient_info.get('gender', '')
    
    # Tham chiếu đến RT Plan
    ds.ReferencedRTPlanSequence = Sequence([Dataset()])
    ref_plan = ds.ReferencedRTPlanSequence[0]
    ref_plan.ReferencedSOPClassUID = '1.2.840.10008.5.1.4.1.1.481.5'  # RT Plan Storage
    ref_plan.ReferencedSOPInstanceUID = rt_plan_uid
    
    # Lưu file
    ds.save_as(output_path)
    logger.info(f"Đã tạo file RT Dose: {output_path}") 