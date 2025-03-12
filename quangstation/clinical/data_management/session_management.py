#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module quản lý phiên làm việc cho QuangStation V2.
"""

import os
import json
import datetime
import shutil
import sys
import numpy as np
from quangstation.clinical.data_management.patient_db import PatientDatabase
import time
from quangstation.core.utils.logging import get_logger

# Sửa lỗi import pydicom
try:
    import pydicom
    from pydicom.dataset import Dataset, FileDataset
    from pydicom.sequence import Sequence
    from pydicom.uid import generate_uid
except ImportError:
    print("Thư viện pydicom chưa được cài đặt. Đang cài đặt...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pydicom"])
    import pydicom
    from pydicom.dataset import Dataset, FileDataset
    from pydicom.sequence import Sequence
    from pydicom.uid import generate_uid
import tempfile

logger = get_logger(__name__)

"""
Module này quản lý phiên làm việc, lưu và tải kế hoạch xạ trị sử dụng định dạng DICOM
"""
class SessionManager:
    """Quản lý phiên làm việc, lưu và tải kế hoạch xạ trị sử dụng định dạng DICOM"""
    
    def __init__(self, workspace_dir='workspace'):
        self.workspace_dir = workspace_dir
        self.current_patient_id = None
        self.current_plan_id = None
        self.current_session = None  # Thêm biến lưu trữ phiên hiện tại
        self.db = PatientDatabase()
        
        # Tạo thư mục workspace nếu chưa tồn tại
        if not os.path.exists(workspace_dir):
            os.makedirs(workspace_dir)
    
    def create_new_session(self, patient_id):
        """Tạo phiên làm việc mới cho bệnh nhân"""
        self.current_patient_id = patient_id
        
        # Tạo thư mục cho bệnh nhân
        patient_dir = os.path.join(self.workspace_dir, patient_id)
        if not os.path.exists(patient_dir):
            os.makedirs(patient_dir)
        
        # Tạo ID kế hoạch mới dựa trên thời gian
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_plan_id = f"plan_{timestamp}"
        
        # Tạo thư mục cho kế hoạch
        plan_dir = os.path.join(patient_dir, self.current_plan_id)
        if not os.path.exists(plan_dir):
            os.makedirs(plan_dir)
        
        return {
            'patient_id': self.current_patient_id,
            'plan_id': self.current_plan_id,
            'created_at': timestamp
        }
    
    def _create_dicom_file(self, data, modality, directory, filename):
        """
        Tạo file DICOM với metadata cơ bản
        
        Args:
            data: Dữ liệu cần lưu
            modality: Loại dữ liệu DICOM (RTPLAN, RTDOSE, ...)
            directory: Thư mục lưu file
            filename: Tên file (không bao gồm đuôi .dcm)
        
        Returns:
            str: Đường dẫn đến file đã tạo
        """
        try:
            # Tạo file DICOM mới
            file_meta = Dataset()
            file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.481.3'  # RT Plan Storage
            file_meta.MediaStorageSOPInstanceUID = generate_uid()
            file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
            
            # Tạo dataset
            ds = FileDataset(filename, {}, file_meta=file_meta, preamble=b"\0" * 128)
            
            # Thêm các thẻ bắt buộc
            ds.PatientID = self.current_patient_id
            
            # Lấy thông tin bệnh nhân
            try:
                patient_info = self.db.get_patient_details(self.current_patient_id)
                patient_name = patient_info.get('name', 'Unknown')
            except Exception as e:
                logger.error(f"Lỗi khi lấy thông tin bệnh nhân: {str(e)}")
                patient_name = 'Unknown'
                
            ds.PatientName = patient_name
            ds.StudyInstanceUID = generate_uid()
            ds.SeriesInstanceUID = generate_uid()
            ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
            ds.SOPClassUID = file_meta.MediaStorageSOPClassUID
            ds.Modality = modality
            ds.InstanceCreationDate = datetime.datetime.now().strftime('%Y%m%d')
            ds.InstanceCreationTime = datetime.datetime.now().strftime('%H%M%S')
            
            # Thêm dữ liệu vào thuộc tính riêng của chúng ta
            ds.ContentDescription = f"{self.current_plan_id}_{filename}"
            
            # Lưu dữ liệu thực tế vào thuộc tính private tag
            if isinstance(data, dict):
                # Chuyển đổi dict thành chuỗi JSON
                ds.add_new([0x0071, 0x0010], 'LO', 'JSON')
                ds.add_new([0x0071, 0x1000], 'OB', str(data).encode('utf-8'))
            elif isinstance(data, np.ndarray):
                # Lưu mảng numpy
                ds.add_new([0x0071, 0x0010], 'LO', 'NUMPY')
                ds.add_new([0x0071, 0x1001], 'OB', data.tobytes())
                ds.add_new([0x0071, 0x1002], 'LO', str(data.shape))
                ds.add_new([0x0071, 0x1003], 'LO', str(data.dtype))
            else:
                # Lưu dữ liệu dưới dạng đã được chuyển thành chuỗi
                ds.add_new([0x0071, 0x0010], 'LO', 'STRING')
                ds.add_new([0x0071, 0x1000], 'OB', str(data).encode('utf-8'))
            
            # Đảm bảo thư mục tồn tại
            if not os.path.exists(directory):
                os.makedirs(directory)
            
            # Lưu file DICOM
            full_path = os.path.join(directory, f"{filename}.dcm")
            ds.save_as(full_path)
            
            return full_path
            
        except Exception as error:
            logger.error(f"Lỗi khi tạo file DICOM: {str(error)}", include_traceback=True)
            raise ValueError(f"Không thể tạo file DICOM: {str(error)}")
    
    def _load_dicom_data(self, file_path):
        """
        Đọc dữ liệu từ file DICOM
        
        Args:
            file_path: Đường dẫn đến file DICOM
            
        Returns:
            Any: Dữ liệu được lưu trong file DICOM
        """
        try:
            if not os.path.exists(file_path):
                return None
            
            ds = pydicom.dcmread(file_path)
            
            # Kiểm tra xem có tag dữ liệu riêng hay không
            if (0x0071, 0x0010) not in ds:
                return None
                
            data_type = ds[0x0071, 0x0010].value
            
            if data_type == 'JSON':
                # Chuyển đổi dữ liệu JSON thành dict
                json_str = ds[0x0071, 0x1000].value.decode('utf-8')
                try:
                    # Cố gắng chuyển chuỗi Python thành dict
                    import ast
                    return ast.literal_eval(json_str)
                except:
                    # Trả về dạng chuỗi nếu không thể chuyển đổi
                    return json_str
            
            elif data_type == 'NUMPY':
                # Chuyển đổi dữ liệu thành mảng numpy
                shape_str = ds[0x0071, 0x1002].value
                dtype_str = ds[0x0071, 0x1003].value
                
                # Phân tích chuỗi shape một cách an toàn
                try:
                    # Loại bỏ ngoặc và khoảng trắng
                    clean_shape_str = shape_str.strip('() ')
                    
                    # Xử lý trường hợp shape có một phần tử
                    if ',' not in clean_shape_str:
                        shape = (int(clean_shape_str),)
                    else:
                        # Xử lý các trường hợp phức tạp
                        parts = clean_shape_str.split(',')
                        shape = tuple(int(p.strip()) for p in parts if p.strip())
                        
                        # Xử lý trường hợp phần tử cuối là dấu phẩy
                        if shape_str.endswith(','):
                            shape = shape + (1,)
                except Exception as error:
                    logger.error(f"Lỗi khi phân tích shape: {shape_str}, lỗi: {str(error)}")
                    return None
                
                # Lấy dữ liệu mảng
                arr_bytes = ds[0x0071, 0x1001].value
                
                try:
                    # Tạo lại mảng numpy
                    arr = np.frombuffer(arr_bytes, dtype=np.dtype(dtype_str))
                    
                    # Reshape nếu có nhiều hơn 1 phần tử
                    if len(shape) > 1 or shape[0] > 1:
                        arr = arr.reshape(shape)
                    
                    return arr
                except Exception as error:
                    logger.error(f"Lỗi khi tạo lại mảng numpy: {str(error)}")
                    return None
            
            elif data_type == 'STRING':
                # Đọc dữ liệu dạng chuỗi
                string_data = ds[0x0071, 0x1000].value.decode('utf-8')
                return string_data
            
            else:
                logger.warning(f"Không xác định được kiểu dữ liệu: {data_type}")
                return None
        
        except Exception as error:
            logger.error(f"Lỗi khi đọc file DICOM {file_path}: {str(error)}")
            return None
    
    def save_plan_metadata(self, metadata, plan_id=None, patient_id=None):
        """
        Lưu metadata của kế hoạch xạ trị
        
        Args:
            metadata (dict): Thông tin metadata cần lưu
            plan_id (str, optional): ID của kế hoạch. Nếu None, sẽ lấy từ metadata
            patient_id (str, optional): ID của bệnh nhân. Nếu None, sẽ lấy từ metadata
        
        Returns:
            str: ID của kế hoạch nếu lưu thành công, None nếu thất bại
        """
        try:
            # Lấy patient_id và plan_id từ metadata nếu không được cung cấp
            if not patient_id:
                patient_id = metadata.get('patient_id', self.current_patient_id)
                if not patient_id:
                    logger.error("Không tìm thấy patient_id trong metadata và không được cung cấp")
                    return None
            
            if not plan_id:
                plan_id = metadata.get('plan_id')
                if not plan_id:
                    # Nếu không có plan_id, tạo một plan_id mới
                    import datetime
                    import uuid
                    plan_id = f"plan_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}"
                    metadata['plan_id'] = plan_id
            
            # Đảm bảo metadata chứa thông tin bệnh nhân
            metadata['patient_id'] = patient_id
            
            # Tạo thư mục cho kế hoạch nếu chưa tồn tại
            patient_dir = os.path.join(self.workspace_dir, patient_id)
            plan_dir = os.path.join(patient_dir, plan_id)
            
            if not os.path.exists(patient_dir):
                os.makedirs(patient_dir)
            if not os.path.exists(plan_dir):
                os.makedirs(plan_dir)
            
            # Lưu metadata dưới dạng JSON
            metadata_file = os.path.join(plan_dir, 'plan_metadata.json')
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            # Cập nhật trạng thái hiện tại
            self.current_patient_id = patient_id
            self.current_plan_id = plan_id
            
            logger.info(f"Đã lưu metadata kế hoạch: {plan_id}")
            
            return plan_id
            
        except Exception as error:
            logger.error(f"Lỗi khi lưu metadata kế hoạch: {str(error)}")
            return None
    
    def save_contours_dicom(self, contours_data):
        """Lưu dữ liệu contour dưới dạng DICOM"""
        if not self.current_patient_id or not self.current_plan_id:
            raise ValueError("Chưa tạo phiên làm việc")
        
        # Tạo đường dẫn đến thư mục kế hoạch
        plan_dir = os.path.join(self.workspace_dir, self.current_patient_id, self.current_plan_id)
        
        # Lưu contours dưới dạng DICOM - mô phỏng RTSTRUCT
        self._create_dicom_file(contours_data, 'RTSTRUCT', plan_dir, "contours")
        
        return True
    
    def save_beam_settings(self, beam_settings):
        """Lưu cài đặt chùm tia dưới dạng DICOM"""
        if not self.current_patient_id or not self.current_plan_id:
            raise ValueError("Chưa tạo phiên làm việc")
        
        # Tạo đường dẫn đến thư mục kế hoạch
        plan_dir = os.path.join(self.workspace_dir, self.current_patient_id, self.current_plan_id)
        
        # Lưu beam settings dưới dạng DICOM - phần của RTPLAN
        self._create_dicom_file(beam_settings, 'RTPLAN', plan_dir, "beam_settings")
        
        return True
    
    def save_dose_calculation(self, dose_data, dose_metadata=None):
        """Lưu dữ liệu tính liều dưới dạng DICOM"""
        if not self.current_patient_id or not self.current_plan_id:
            raise ValueError("Chưa tạo phiên làm việc")
        
        # Tạo đường dẫn đến thư mục kế hoạch
        plan_dir = os.path.join(self.workspace_dir, self.current_patient_id, self.current_plan_id)
        
        # Lưu dose data dưới dạng DICOM - mô phỏng RTDOSE
        self._create_dicom_file(dose_data, 'RTDOSE', plan_dir, "dose")
        
        # Lưu metadata nếu có
        if dose_metadata:
            self._create_dicom_file(dose_metadata, 'RTDOSE', plan_dir, "dose_metadata")
        
        return True
    
    def save_dvh_data(self, dvh_data):
        """Lưu dữ liệu DVH dưới dạng DICOM"""
        if not self.current_patient_id or not self.current_plan_id:
            raise ValueError("Chưa tạo phiên làm việc")
        
        # Tạo đường dẫn đến thư mục kế hoạch
        plan_dir = os.path.join(self.workspace_dir, self.current_patient_id, self.current_plan_id)
        
        # Lưu DVH data dưới dạng DICOM (dùng supplementary tag trong RTDOSE)
        self._create_dicom_file(dvh_data, 'RTDOSE', plan_dir, "dvh")
        
        return True
    
    def save_optimization_results(self, optimization_results):
        """Lưu kết quả tối ưu hóa dưới dạng DICOM"""
        if not self.current_patient_id or not self.current_plan_id:
            raise ValueError("Chưa tạo phiên làm việc")
        
        # Tạo đường dẫn đến thư mục kế hoạch
        plan_dir = os.path.join(self.workspace_dir, self.current_patient_id, self.current_plan_id)
        
        # Lưu kết quả tối ưu hóa dưới dạng DICOM (dùng private tags)
        self._create_dicom_file(optimization_results, 'RTPLAN', plan_dir, "optimization_results")
        
        return True
    
    def update_plan_optimization(self, patient_id, plan_id, optimization_result):
        """
        Cập nhật kế hoạch với kết quả tối ưu hóa
        
        Args:
            patient_id: ID của bệnh nhân
            plan_id: ID của kế hoạch
            optimization_result: Kết quả tối ưu hóa từ PlanOptimizer
            
        Returns:
            bool: True nếu cập nhật thành công, False nếu không
        """
        try:
            # Lưu trạng thái hiện tại
            current_patient = self.current_patient_id
            current_plan = self.current_plan_id
            
            # Chuyển sang kế hoạch cần cập nhật
            self.load_session(patient_id, plan_id)
            
            # Lưu kết quả tối ưu hóa
            self.save_optimization_results(optimization_result)
            
            # Cập nhật trạng thái kế hoạch
            plan_metadata = self.get_plan_summary(patient_id, plan_id)
            if plan_metadata:
                # Cập nhật trạng thái
                plan_metadata["optimization_status"] = "completed"
                plan_metadata["optimization_timestamp"] = time.time()
                plan_metadata["optimization_summary"] = {
                    "initial_objective": optimization_result.get("initial_objective", 0),
                    "final_objective": optimization_result.get("final_objective", 0),
                    "iterations": optimization_result.get("iterations", 0),
                    "runtime": optimization_result.get("runtime", 0)
                }
                
                # Lưu metadata đã cập nhật
                self.save_plan_metadata(plan_metadata)
            
            # Khôi phục trạng thái trước đó nếu cần
            if current_patient != patient_id or current_plan != plan_id:
                self.load_session(current_patient, current_plan)
                
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật kế hoạch với kết quả tối ưu hóa: {str(e)}")
            return False
    
    def save_screenshot(self, image_data, filename="screenshot.png"):
        """Lưu ảnh chụp màn hình dưới dạng DICOM Secondary Capture"""
        if not self.current_patient_id or not self.current_plan_id:
            raise ValueError("Chưa tạo phiên làm việc")
        
        # Tạo thư mục screenshots nếu chưa tồn tại
        plan_dir = os.path.join(self.workspace_dir, self.current_patient_id, self.current_plan_id)
        screenshots_dir = os.path.join(plan_dir, "screenshots")
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)
        
        # Tạo tên file không có phần mở rộng
        base_filename = os.path.splitext(filename)[0]
        
        # Lưu ảnh tạm thời để lấy thông tin (nếu nó là đối tượng PIL Image)
        temp_file = os.path.join(tempfile.gettempdir(), filename)
        image_data.save(temp_file)
        
        # Đọc ảnh vào mảng numpy
        from PIL import Image
        import numpy as np
        pil_image = Image.open(temp_file)
        img_array = np.array(pil_image)
        
        # Lưu ảnh dưới dạng DICOM Secondary Capture
        dcm_filename = os.path.join(screenshots_dir, f"{base_filename}.dcm")
        self._create_dicom_file(img_array, 'SC', screenshots_dir, base_filename)
        
        # Xóa file tạm thời
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        return dcm_filename
    
    def load_session(self, patient_id, plan_id):
        """Tải phiên làm việc từ thư mục workspace."""
        try:
            session_dir = os.path.join(self.workspace_dir, patient_id, plan_id)
            
            if not os.path.exists(session_dir):
                logger.error(f"Không tìm thấy thư mục phiên: {session_dir}")
                raise FileNotFoundError(f"Không tìm thấy phiên {plan_id} cho bệnh nhân {patient_id}")
            
            session_data = {}
            
            # Tải metadata kế hoạch
            metadata_file = os.path.join(session_dir, 'plan_metadata.json')
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    session_data['plan_metadata'] = json.load(f)
            else:
                logger.warning(f"Không tìm thấy file metadata: {metadata_file}")
                session_data['plan_metadata'] = {}
            
            # Tải dữ liệu contour
            contours_file = os.path.join(session_dir, 'contours.json')
            if os.path.exists(contours_file):
                with open(contours_file, 'r', encoding='utf-8') as f:
                    session_data['contours'] = json.load(f)
            else:
                logger.warning(f"Không tìm thấy file contours: {contours_file}")
                session_data['contours'] = {}
            
            # Tải beam settings
            beam_file = os.path.join(session_dir, "beam_settings.dcm")
            beam_settings = None
            if os.path.exists(beam_file):
                beam_settings = self._load_dicom_data(beam_file)
            
            # Tải dose data
            dose_file = os.path.join(session_dir, "dose.dcm")
            dose_data = None
            if os.path.exists(dose_file):
                dose_data = self._load_dicom_data(dose_file)
            
            # Tải dose metadata
            dose_metadata_file = os.path.join(session_dir, "dose_metadata.dcm")
            dose_metadata = None
            if os.path.exists(dose_metadata_file):
                dose_metadata = self._load_dicom_data(dose_metadata_file)
            
            # Tải DVH data
            dvh_file = os.path.join(session_dir, "dvh.dcm")
            dvh_data = None
            if os.path.exists(dvh_file):
                dvh_data = self._load_dicom_data(dvh_file)
            
            # Tải kết quả tối ưu hóa
            opt_file = os.path.join(session_dir, "optimization_results.dcm")
            optimization_results = None
            if os.path.exists(opt_file):
                optimization_results = self._load_dicom_data(opt_file)
            
            logger.info(f"Đã tải phiên {plan_id} cho bệnh nhân {patient_id}")
            return {
                'metadata': session_data['plan_metadata'],
                'contours': session_data['contours'],
                'beam_settings': beam_settings,
                'dose_data': dose_data,
                'dose_metadata': dose_metadata,
                'dvh_data': dvh_data,
                'optimization_results': optimization_results
            }
        
        except Exception as error:
            logger.error(f"Lỗi khi tải phiên: {str(error)}", include_traceback=True)
            raise
    
    def list_patients(self):
        """Liệt kê danh sách bệnh nhân"""
        patients = []
        
        # Liệt kê thư mục con trong workspace
        if os.path.exists(self.workspace_dir):
            for item in os.listdir(self.workspace_dir):
                patient_dir = os.path.join(self.workspace_dir, item)
                if os.path.isdir(patient_dir):
                    # Lấy thông tin bệnh nhân từ database nếu có
                    patient_info = self.db.get_patient_details(item)
                    if patient_info:
                        patients.append(patient_info)
                    else:
                        patients.append({'patient_id': item, 'patient_name': 'Unknown'})
        
        return patients
    
    def list_plans(self, patient_id):
        """Liệt kê danh sách kế hoạch của một bệnh nhân"""
        plans = []
        
        # Liệt kê thư mục con trong thư mục bệnh nhân
        patient_dir = os.path.join(self.workspace_dir, patient_id)
        if os.path.exists(patient_dir):
            for item in os.listdir(patient_dir):
                plan_dir = os.path.join(patient_dir, item)
                if os.path.isdir(plan_dir):
                    # Tải metadata để hiển thị thông tin
                    metadata_file = os.path.join(plan_dir, "metadata.dcm")
                    metadata = None
                    if os.path.exists(metadata_file):
                        metadata = self._load_dicom_data(metadata_file)
                    
                    # Lấy thời gian tạo từ tên kế hoạch nếu có định dạng plan_YYYYMMDD_HHMMSS
                    created_at = None
                    if item.startswith("plan_") and len(item) >= 20:
                        try:
                            date_str = item[5:13]
                            time_str = item[14:20]
                            created_at = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
                        except:
                            pass
                    
                    plan_info = {
                        'plan_id': item,
                        'metadata': metadata,
                        'created_at': created_at or 'Unknown'
                    }
                    
                    plans.append(plan_info)
        
        # Sắp xếp kế hoạch theo thời gian tạo (mới nhất lên đầu)
        plans.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return plans
    
    def delete_plan(self, patient_id, plan_id):
        """Xóa một kế hoạch"""
        plan_dir = os.path.join(self.workspace_dir, patient_id, plan_id)
        
        if not os.path.exists(plan_dir):
            return False
        
        try:
            # Xóa toàn bộ thư mục kế hoạch
            shutil.rmtree(plan_dir)
            
            # Reset current plan nếu đang chọn kế hoạch bị xóa
            if self.current_patient_id == patient_id and self.current_plan_id == plan_id:
                self.current_plan_id = None
            
            return True
        except Exception as error:
            print(f"Lỗi khi xóa kế hoạch: {error}")
            return False
    
    def export_plan(self, export_folder, include_screenshots=False):
        """
        Xuất kế hoạch ra định dạng JSON
        
        Args:
            export_folder: Thư mục xuất ra
            include_screenshots: Có xuất ảnh chụp màn hình không
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            if not self.current_patient_id or not self.current_plan_id:
                logger.warning("Chưa chọn bệnh nhân hoặc kế hoạch")
                return False
                
            # Tạo thư mục xuất nếu chưa có
            os.makedirs(export_folder, exist_ok=True)
            
            # Thư mục kế hoạch hiện tại
            plan_dir = os.path.join(self.workspace_dir, self.current_patient_id, self.current_plan_id)
            
            # Xuất thông tin kế hoạch
            plan_data = self.get_plan_summary(self.current_patient_id, self.current_plan_id)
            if plan_data:
                plan_json_file = os.path.join(export_folder, "plan_info.json")
                with open(plan_json_file, 'w', encoding='utf-8') as f:
                    json.dump(plan_data, f, ensure_ascii=False, indent=2)
                logger.info(f"Đã xuất thông tin kế hoạch sang {plan_json_file}")
            
            # Xuất cấu hình kế hoạch
            plan_config = self.get_plan_config(self.current_patient_id, self.current_plan_id)
            if plan_config:
                config_json_file = os.path.join(export_folder, "plan_config.json")
                with open(config_json_file, 'w', encoding='utf-8') as f:
                    json.dump(plan_config.to_dict(), f, ensure_ascii=False, indent=2)
                logger.info(f"Đã xuất cấu hình kế hoạch sang {config_json_file}")
            
            # Xuất dữ liệu cấu trúc
            structure_data = self.get_structure_data(self.current_patient_id, self.current_plan_id)
            if structure_data:
                struct_json_file = os.path.join(export_folder, "structures.json")
                with open(struct_json_file, 'w', encoding='utf-8') as f:
                    json.dump(structure_data, f, ensure_ascii=False, indent=2)
                logger.info(f"Đã xuất dữ liệu cấu trúc sang {struct_json_file}")
            
            # Xuất dữ liệu liều
            dose_data = self.get_dose_data(self.current_patient_id, self.current_plan_id)
            if dose_data:
                dose_json_file = os.path.join(export_folder, "dose.json")
                with open(dose_json_file, 'w', encoding='utf-8') as f:
                    json.dump(dose_data, f, ensure_ascii=False, indent=2)
                logger.info(f"Đã xuất dữ liệu liều sang {dose_json_file}")
            
            # Xuất ảnh chụp màn hình nếu được yêu cầu
            if include_screenshots:
                # Tạo thư mục ảnh
                screenshots_dir = os.path.join(export_folder, "screenshots")
                os.makedirs(screenshots_dir, exist_ok=True)
                
                # Xuất ảnh từ thư mục kế hoạch
                screenshots_src_dir = os.path.join(plan_dir, "screenshots")
                if os.path.exists(screenshots_src_dir):
                    for file in os.listdir(screenshots_src_dir):
                        if file.endswith(('.png', '.jpg', '.jpeg')):
                            src_file = os.path.join(screenshots_src_dir, file)
                            dst_file = os.path.join(screenshots_dir, file)
                            shutil.copy2(src_file, dst_file)
                    logger.info(f"Đã xuất ảnh chụp màn hình sang {screenshots_dir}")
            
            # Tạo file README
            readme_file = os.path.join(export_folder, "README.txt")
            with open(readme_file, 'w', encoding='utf-8') as f:
                f.write(f"Kế hoạch xạ trị: {plan_data.get('name', 'Không tên')}\n")
                f.write(f"ID: {self.current_plan_id}\n")
                f.write(f"Bệnh nhân: {plan_data.get('patient_name', 'Không tên')}\n")
                f.write(f"Ngày xuất: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("Nội dung:\n")
                f.write("- plan_info.json: Thông tin kế hoạch\n")
                f.write("- plan_config.json: Cấu hình kế hoạch\n")
                f.write("- structures.json: Dữ liệu cấu trúc\n")
                if dose_data:
                    f.write("- dose.json: Dữ liệu liều\n")
                if include_screenshots:
                    f.write("- screenshots/: Thư mục chứa ảnh chụp màn hình\n")
            
            logger.info(f"Đã xuất kế hoạch thành công sang {export_folder}")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi xuất kế hoạch: {str(e)}")
            return False
    
    def duplicate_plan(self, patient_id, plan_id, new_plan_name=None):
        """
        Tạo bản sao của một kế hoạch
        
        Args:
            patient_id (str): ID của bệnh nhân
            plan_id (str): ID của kế hoạch cần sao chép
            new_plan_name (str, optional): Tên mới cho bản sao kế hoạch
            
        Returns:
            str: ID của kế hoạch mới nếu thành công, None nếu thất bại
        """
        try:
            # Tạo phiên làm việc mới
            self.create_new_session(patient_id)
            new_plan_id = self.current_plan_id
            
            # Đường dẫn đến kế hoạch nguồn và đích
            source_plan_dir = os.path.join(self.workspace_dir, patient_id, plan_id)
            target_plan_dir = os.path.join(self.workspace_dir, patient_id, new_plan_id)
            
            if not os.path.exists(source_plan_dir):
                raise FileNotFoundError(f"Không tìm thấy kế hoạch nguồn: {plan_id}")
            
            # Sao chép các file từ kế hoạch nguồn sang kế hoạch đích
            for item in os.listdir(source_plan_dir):
                src_path = os.path.join(source_plan_dir, item)
                dst_path = os.path.join(target_plan_dir, item)
                
                if os.path.isfile(src_path):
                    shutil.copy2(src_path, dst_path)
                elif os.path.isdir(src_path):
                    # Sao chép thư mục con (như screenshots)
                    if not os.path.exists(dst_path):
                        os.makedirs(dst_path)
                    
                    for file_item in os.listdir(src_path):
                        src_file = os.path.join(src_path, file_item)
                        dst_file = os.path.join(dst_path, file_item)
                        if os.path.isfile(src_file):
                            shutil.copy2(src_file, dst_file)
            
            # Cập nhật metadata
            metadata_json_file = os.path.join(target_plan_dir, "plan_metadata.json")
            if os.path.exists(metadata_json_file):
                # Đọc metadata
                with open(metadata_json_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # Cập nhật thông tin
                metadata['plan_id'] = new_plan_id
                
                # Cập nhật tên kế hoạch nếu được cung cấp
                if new_plan_name:
                    metadata['plan_name'] = new_plan_name
                else:
                    # Mặc định thêm "- Bản sao" vào tên
                    metadata['plan_name'] = metadata.get('plan_name', 'Kế hoạch') + " - Bản sao"
                
                # Cập nhật thời gian sửa đổi
                metadata['modified_at'] = datetime.datetime.now().isoformat()
                
                # Ghi lại metadata
                with open(metadata_json_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            # Ghi log
            logger.info(f"Đã sao chép kế hoạch {plan_id} thành kế hoạch mới {new_plan_id}")
            
            return new_plan_id
            
        except Exception as error:
            logger.error(f"Lỗi khi sao chép kế hoạch: {str(error)}", include_traceback=True)
            return None
    
    def backup_workspace(self, backup_dir):
        """Sao lưu toàn bộ workspace"""
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # Tạo tên file backup dựa trên thời gian
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"workspace_backup_{timestamp}.zip")
        
        # Tạo file zip chứa toàn bộ workspace
        shutil.make_archive(backup_file[:-4], 'zip', self.workspace_dir)
        
        return backup_file
    
    def restore_from_backup(self, backup_file):
        """Khôi phục workspace từ file backup"""
        if not os.path.exists(backup_file):
            raise FileNotFoundError(f"Không tìm thấy file backup: {backup_file}")
        
        # Tạo thư mục tạm để giải nén
        temp_dir = os.path.join(os.path.dirname(backup_file), "temp_restore")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
        
        # Giải nén file backup
        shutil.unpack_archive(backup_file, temp_dir)
        
        # Xóa workspace hiện tại
        if os.path.exists(self.workspace_dir):
            shutil.rmtree(self.workspace_dir)
        
        # Di chuyển dữ liệu từ thư mục tạm sang workspace
        shutil.move(temp_dir, self.workspace_dir)
        
        # Reset trạng thái hiện tại
        self.current_patient_id = None
        self.current_plan_id = None
        
        return True
    
    def get_plan_summary(self, patient_id=None, plan_id=None):
        """Lấy thông tin tóm tắt về kế hoạch"""
        if patient_id is None:
            patient_id = self.current_patient_id
        if plan_id is None:
            plan_id = self.current_plan_id
            
        if not patient_id or not plan_id:
            return None
            
        # Thử đọc từ file JSON
        plan_dir = os.path.join(self.workspace_dir, patient_id, plan_id)
        json_file = os.path.join(plan_dir, "plan_metadata.json")
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r') as f:
                    return json.load(f)
            except Exception as error:
                logger.error(f"Lỗi khi đọc plan_metadata.json: {str(error)}")
        
        # Thử đọc từ file DICOM
        metadata_file = os.path.join(plan_dir, "metadata.dcm")
        if os.path.exists(metadata_file):
            try:
                return self._load_dicom_data(metadata_file)
            except Exception as error:
                logger.error(f"Lỗi khi đọc metadata.dcm: {str(error)}")
        
        return None
    
    def get_structure_data(self, patient_id=None, plan_id=None):
        """
        Lấy dữ liệu cấu trúc cho kế hoạch
        
        Args:
            patient_id: ID của bệnh nhân (mặc định là bệnh nhân hiện tại)
            plan_id: ID của kế hoạch (mặc định là kế hoạch hiện tại)
            
        Returns:
            Dict: Dữ liệu cấu trúc hoặc None nếu không tìm thấy
        """
        if patient_id is None:
            patient_id = self.current_patient_id
        if plan_id is None:
            plan_id = self.current_plan_id
            
        if not patient_id or not plan_id:
            return None
            
        # Đường dẫn đến thư mục kế hoạch
        plan_dir = os.path.join(self.workspace_dir, patient_id, plan_id)
        
        # Thử đọc từ file DICOM
        structure_file = os.path.join(plan_dir, "structures.dcm")
        if os.path.exists(structure_file):
            try:
                return self._load_dicom_data(structure_file)
            except Exception as error:
                logger.error(f"Lỗi khi đọc structures.dcm: {str(error)}")
        
        # Thử đọc từ file JSON
        json_file = os.path.join(plan_dir, "structures.json")
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r') as f:
                    return json.load(f)
            except Exception as error:
                logger.error(f"Lỗi khi đọc structures.json: {str(error)}")
        
        return None
    
    def get_dose_data(self, patient_id=None, plan_id=None):
        """
        Lấy dữ liệu liều cho kế hoạch
        
        Args:
            patient_id: ID của bệnh nhân (mặc định là bệnh nhân hiện tại)
            plan_id: ID của kế hoạch (mặc định là kế hoạch hiện tại)
            
        Returns:
            Dict: Dữ liệu liều hoặc None nếu không tìm thấy
        """
        if patient_id is None:
            patient_id = self.current_patient_id
        if plan_id is None:
            plan_id = self.current_plan_id
            
        if not patient_id or not plan_id:
            return None
            
        # Đường dẫn đến thư mục kế hoạch
        plan_dir = os.path.join(self.workspace_dir, patient_id, plan_id)
        
        # Thử đọc từ file DICOM
        dose_file = os.path.join(plan_dir, "dose.dcm")
        if os.path.exists(dose_file):
            try:
                return self._load_dicom_data(dose_file)
            except Exception as error:
                logger.error(f"Lỗi khi đọc dose.dcm: {str(error)}")
        
        # Thử đọc từ file JSON
        json_file = os.path.join(plan_dir, "dose.json")
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r') as f:
                    return json.load(f)
            except Exception as error:
                logger.error(f"Lỗi khi đọc dose.json: {str(error)}")
        
        return None
    
    def get_structure_list(self, patient_id=None, plan_id=None):
        """
        Lấy danh sách các cấu trúc trong kế hoạch
        
        Args:
            patient_id: ID của bệnh nhân (mặc định là bệnh nhân hiện tại)
            plan_id: ID của kế hoạch (mặc định là kế hoạch hiện tại)
            
        Returns:
            List: Danh sách các cấu trúc hoặc danh sách rỗng nếu không tìm thấy
        """
        structure_data = self.get_structure_data(patient_id, plan_id)
        if not structure_data:
            return []
            
        structures = []
        
        # Lấy danh sách cấu trúc
        if "structures" in structure_data:
            for name, struct in structure_data["structures"].items():
                structure_info = {
                    "name": name,
                    "type": struct.get("type", "Unknown"),
                    "color": struct.get("color", "#FFFFFF"),
                    "volume": struct.get("volume", 0)
                }
                structures.append(structure_info)
        
        return structures
    
    def has_dose_calculation(self, patient_id=None, plan_id=None):
        """
        Kiểm tra xem kế hoạch đã có dữ liệu liều chưa
        
        Args:
            patient_id: ID của bệnh nhân (mặc định là bệnh nhân hiện tại)
            plan_id: ID của kế hoạch (mặc định là kế hoạch hiện tại)
            
        Returns:
            bool: True nếu đã có dữ liệu liều, False nếu chưa
        """
        dose_data = self.get_dose_data(patient_id, plan_id)
        return dose_data is not None and (
            "dose_matrix" in dose_data or 
            "dose_grid" in dose_data
        )
    
    def has_contours(self, patient_id=None, plan_id=None):
        """
        Kiểm tra xem kế hoạch đã có contour chưa
        
        Args:
            patient_id: ID của bệnh nhân (mặc định là bệnh nhân hiện tại)
            plan_id: ID của kế hoạch (mặc định là kế hoạch hiện tại)
            
        Returns:
            bool: True nếu đã có contour, False nếu chưa
        """
        structure_data = self.get_structure_data(patient_id, plan_id)
        if not structure_data:
            return False
            
        # Kiểm tra xem có cấu trúc nào không
        if "structures" in structure_data and structure_data["structures"]:
            return len(structure_data["structures"]) > 0
            
        return False
    
    def get_contour_tools(self):
        """
        Lấy đối tượng ContourTools hiện tại
        
        Returns:
            ContourTools: Đối tượng ContourTools hoặc None nếu chưa có
        """
        if hasattr(self, 'contour_tools'):
            return self.contour_tools
        return None
    
    def set_contour_tools(self, contour_tools):
        """
        Thiết lập đối tượng ContourTools
        
        Args:
            contour_tools: Đối tượng ContourTools
        """
        self.contour_tools = contour_tools
    
    def save_contours(self):
        """
        Lưu contour vào session
        
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            if not hasattr(self, 'contour_tools') or self.contour_tools is None:
                logger.warning("Không có contour để lưu")
                return False
                
            if not self.current_patient_id or not self.current_plan_id:
                logger.warning("Chưa chọn bệnh nhân hoặc kế hoạch")
                return False
                
            # Lấy dữ liệu contour
            contours = self.contour_tools.get_all_contours()
            
            # Tạo cấu trúc dữ liệu
            structure_data = {
                "structures": {}
            }
            
            # Thêm từng contour vào dữ liệu
            for name, contour in contours.items():
                structure_data["structures"][name] = {
                    "contour_data": contour,
                    "color": self.contour_tools.get_color(name),
                    "type": self.contour_tools.get_type(name)
                }
            
            # Lưu vào file
            plan_dir = os.path.join(self.workspace_dir, self.current_patient_id, self.current_plan_id)
            os.makedirs(plan_dir, exist_ok=True)
            
            # Lưu dưới dạng JSON
            json_file = os.path.join(plan_dir, "structures.json")
            with open(json_file, 'w') as f:
                json.dump(structure_data, f)
            
            logger.info(f"Đã lưu contour vào {json_file}")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu contour: {str(e)}")
            return False
    
    def get_plan_config(self, patient_id=None, plan_id=None):
        """
        Lấy cấu hình kế hoạch
        
        Args:
            patient_id: ID của bệnh nhân (mặc định là bệnh nhân hiện tại)
            plan_id: ID của kế hoạch (mặc định là kế hoạch hiện tại)
            
        Returns:
            PlanConfig: Đối tượng PlanConfig hoặc None nếu không tìm thấy
        """
        if patient_id is None:
            patient_id = self.current_patient_id
        if plan_id is None:
            plan_id = self.current_plan_id
            
        if not patient_id or not plan_id:
            return None
            
        # Đường dẫn đến thư mục kế hoạch
        plan_dir = os.path.join(self.workspace_dir, patient_id, plan_id)
        
        # Thử đọc từ file JSON
        json_file = os.path.join(plan_dir, "plan_config.json")
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r') as f:
                    config_data = json.load(f)
                    
                # Tạo đối tượng PlanConfig
                from quangstation.planning.plan_config import PlanConfig
                config = PlanConfig()
                
                # Cập nhật từ dữ liệu JSON
                for key, value in config_data.items():
                    setattr(config, key, value)
                    
                return config
            except Exception as error:
                logger.error(f"Lỗi khi đọc plan_config.json: {str(error)}")
        
        return None
    
    def get_current_session(self):
        """
        Lấy phiên làm việc hiện tại
        
        Returns:
            Dict hoặc None: Dữ liệu phiên làm việc hiện tại hoặc None nếu chưa có phiên nào
        """
        if self.current_patient_id and self.current_plan_id:
            # Nếu chưa load session, load từ file
            if self.current_session is None:
                self.load_session(self.current_patient_id, self.current_plan_id)
            return self.current_session
        return None
    
    def update_current_session(self, session_data):
        """
        Cập nhật phiên làm việc hiện tại và lưu vào file
        
        Args:
            session_data: Dữ liệu phiên làm việc mới
            
        Returns:
            bool: True nếu cập nhật thành công, False nếu thất bại
        """
        if self.current_patient_id is None or self.current_plan_id is None:
            logger.error("Không có phiên làm việc hiện tại để cập nhật")
            return False
        
        try:
            # Cập nhật biến session
            self.current_session = session_data
            
            # Lưu dữ liệu vào các file
            session_dir = os.path.join(self.workspace_dir, self.current_patient_id, self.current_plan_id)
            if not os.path.exists(session_dir):
                os.makedirs(session_dir)
            
            # Lưu metadata
            if 'plan_metadata' in session_data:
                metadata_file = os.path.join(session_dir, 'plan_metadata.json')
                with open(metadata_file, 'w') as f:
                    json.dump(session_data['plan_metadata'], f, indent=2)
            
            # Lưu contours
            if 'structures' in session_data:
                # Chỉ lưu thông tin cơ bản, không lưu mask (quá lớn)
                contours_data = {}
                for struct_id, struct_data in session_data['structures'].items():
                    contours_data[struct_id] = {
                        'name': struct_data.get('name', ''),
                        'color': struct_data.get('color', [1.0, 0.0, 0.0]),
                        'type': struct_data.get('type', 'ORGAN'),
                        'modified_date': struct_data.get('modified_date', datetime.datetime.now().isoformat())
                    }
                
                contours_file = os.path.join(session_dir, 'contours.json')
                with open(contours_file, 'w') as f:
                    json.dump(contours_data, f, indent=2)
                
                # Lưu mask vào file riêng (dạng nén numpy)
                for struct_id, struct_data in session_data['structures'].items():
                    if 'mask' in struct_data:
                        mask_file = os.path.join(session_dir, f'mask_{struct_id}.npz')
                        np.savez_compressed(mask_file, mask=struct_data['mask'])
            
            # Lưu dose matrix nếu có
            if 'dose_matrix' in session_data:
                dose_file = os.path.join(session_dir, 'dose_matrix.npz')
                np.savez_compressed(dose_file, dose=session_data['dose_matrix'])
            
            # Lưu thông tin kế hoạch
            if 'plans' in session_data and self.current_plan_id in session_data['plans']:
                plan_file = os.path.join(session_dir, 'plan_data.json')
                with open(plan_file, 'w') as f:
                    json.dump(session_data['plans'][self.current_plan_id], f, indent=2)
            
            # Lưu thông tin beams
            if 'beams' in session_data:
                beams_file = os.path.join(session_dir, 'beams.json')
                with open(beams_file, 'w') as f:
                    json.dump(session_data['beams'], f, indent=2)
            
            logger.info(f"Đã cập nhật phiên làm việc: {self.current_patient_id}/{self.current_plan_id}")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật phiên làm việc: {str(e)}")
            return False