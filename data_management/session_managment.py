import os
import json
import datetime
import shutil
import sys
import numpy as np
from data_management.patient_db import PatientDatabase

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

class SessionManager:
    """Quản lý phiên làm việc, lưu và tải kế hoạch xạ trị sử dụng định dạng DICOM"""
    
    def __init__(self, workspace_dir='workspace'):
        self.workspace_dir = workspace_dir
        self.current_patient_id = None
        self.current_plan_id = None
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
        """Tạo file DICOM với metadata cơ bản"""
        # Tạo file DICOM mới
        file_meta = Dataset()
        file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.481.3'  # RT Plan Storage
        file_meta.MediaStorageSOPInstanceUID = generate_uid()
        file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
        
        # Tạo dataset
        ds = FileDataset(filename, {}, file_meta=file_meta, preamble=b"\0" * 128)
        
        # Thêm các thẻ bắt buộc
        ds.PatientID = self.current_patient_id
        ds.PatientName = self.db.get_patient_info(self.current_patient_id).get('patient_name', 'Unknown')
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
            ds.add_new([0x0071, 0x1004], 'OB', str(data).encode('utf-8'))
        
        # Lưu file
        file_path = os.path.join(directory, f"{filename}.dcm")
        ds.save_as(file_path)
        
        return file_path
    
    def _load_dicom_data(self, file_path):
        """Đọc dữ liệu từ file DICOM"""
        if not os.path.exists(file_path):
            return None
        
        ds = pydicom.dcmread(file_path)
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
            
            # Phân tích chuỗi shape và dtype
            shape = tuple(map(int, shape_str.strip('()').split(',')))
            if shape[-1] == '':  # Xử lý trường hợp shape = (n,)
                shape = (shape[0],)
                
            # Tạo lại mảng numpy
            arr_bytes = ds[0x0071, 0x1001].value
            arr = np.frombuffer(arr_bytes, dtype=np.dtype(dtype_str))
            
            if len(shape) > 1:
                arr = arr.reshape(shape)
            
            return arr
        
        elif data_type == 'STRING':
            # Chuyển đổi chuỗi thành dữ liệu gốc
            data_str = ds[0x0071, 0x1004].value.decode('utf-8')
            return data_str
        
        return None
    
    def save_plan_metadata(self, metadata, plan_id=None, patient_id=None):
        """Lưu metadata của kế hoạch xạ trị
        
        Args:
            metadata (dict): Thông tin metadata cần lưu
            plan_id (str, optional): ID của kế hoạch. Nếu None, sẽ lấy từ metadata
            patient_id (str, optional): ID của bệnh nhân. Nếu None, sẽ lấy từ metadata
        
        Returns:
            bool: True nếu lưu thành công, False nếu thất bại
        """
        try:
            # Lấy patient_id và plan_id từ metadata nếu không được cung cấp
            if not patient_id:
                patient_id = metadata.get('patient_id')
                if not patient_id:
                    print("Không tìm thấy patient_id trong metadata")
                    return False
            
            if not plan_id:
                plan_id = metadata.get('plan_id')
                if not plan_id:
                    # Nếu không có plan_id, tạo một plan_id mới
                    import datetime
                    import uuid
                    plan_id = f"plan_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}"
                    metadata['plan_id'] = plan_id
            
            # Đường dẫn đến thư mục của bệnh nhân
            patient_dir = os.path.join(self.workspace_dir, patient_id)
            if not os.path.exists(patient_dir):
                os.makedirs(patient_dir)
            
            # Đường dẫn đến thư mục của kế hoạch
            plan_dir = os.path.join(patient_dir, plan_id)
            if not os.path.exists(plan_dir):
                os.makedirs(plan_dir)
            
            # Đường dẫn đến file metadata
            metadata_file = os.path.join(plan_dir, 'plan_metadata.json')
            
            # Thêm thời gian chỉnh sửa cuối cùng
            metadata['last_modified'] = datetime.datetime.now().isoformat()
            
            # Lưu metadata dưới dạng file JSON
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=4)
            
            print(f"Đã lưu metadata kế hoạch tại: {metadata_file}")
            return True
        
        except Exception as e:
            print(f"Lỗi khi lưu metadata kế hoạch: {e}")
            return False
    
    def save_contours(self, contours_data):
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
        """Tải phiên làm việc từ các file DICOM"""
        self.current_patient_id = patient_id
        self.current_plan_id = plan_id
        
        # Kiểm tra xem phiên làm việc có tồn tại
        plan_dir = os.path.join(self.workspace_dir, patient_id, plan_id)
        if not os.path.exists(plan_dir):
            raise FileNotFoundError(f"Không tìm thấy kế hoạch: {plan_id} cho bệnh nhân: {patient_id}")
        
        # Tải metadata
        metadata_file = os.path.join(plan_dir, "metadata.dcm")
        metadata = None
        if os.path.exists(metadata_file):
            metadata = self._load_dicom_data(metadata_file)
        
        # Tải contours
        contours_file = os.path.join(plan_dir, "contours.dcm")
        contours_data = None
        if os.path.exists(contours_file):
            contours_data = self._load_dicom_data(contours_file)
        
        # Tải beam settings
        beam_file = os.path.join(plan_dir, "beam_settings.dcm")
        beam_settings = None
        if os.path.exists(beam_file):
            beam_settings = self._load_dicom_data(beam_file)
        
        # Tải dose data
        dose_file = os.path.join(plan_dir, "dose.dcm")
        dose_data = None
        if os.path.exists(dose_file):
            dose_data = self._load_dicom_data(dose_file)
        
        # Tải dose metadata
        dose_metadata_file = os.path.join(plan_dir, "dose_metadata.dcm")
        dose_metadata = None
        if os.path.exists(dose_metadata_file):
            dose_metadata = self._load_dicom_data(dose_metadata_file)
        
        # Tải DVH data
        dvh_file = os.path.join(plan_dir, "dvh.dcm")
        dvh_data = None
        if os.path.exists(dvh_file):
            dvh_data = self._load_dicom_data(dvh_file)
        
        # Tải kết quả tối ưu hóa
        opt_file = os.path.join(plan_dir, "optimization_results.dcm")
        optimization_results = None
        if os.path.exists(opt_file):
            optimization_results = self._load_dicom_data(opt_file)
        
        return {
            'metadata': metadata,
            'contours': contours_data,
            'beam_settings': beam_settings,
            'dose_data': dose_data,
            'dose_metadata': dose_metadata,
            'dvh_data': dvh_data,
            'optimization_results': optimization_results
        }
    
    def list_patients(self):
        """Liệt kê danh sách bệnh nhân"""
        patients = []
        
        # Liệt kê thư mục con trong workspace
        if os.path.exists(self.workspace_dir):
            for item in os.listdir(self.workspace_dir):
                patient_dir = os.path.join(self.workspace_dir, item)
                if os.path.isdir(patient_dir):
                    # Lấy thông tin bệnh nhân từ database nếu có
                    patient_info = self.db.get_patient_info(item)
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
        except Exception as e:
            print(f"Lỗi khi xóa kế hoạch: {e}")
            return False
    
    def export_plan(self, output_dir, include_screenshots=True):
        """Xuất kế hoạch hiện tại ra thư mục khác"""
        if not self.current_patient_id or not self.current_plan_id:
            raise ValueError("Chưa tạo phiên làm việc")
        
        plan_dir = os.path.join(self.workspace_dir, self.current_patient_id, self.current_plan_id)
        
        # Tạo thư mục đích nếu chưa tồn tại
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Sao chép các file từ plan_dir sang output_dir
        for item in os.listdir(plan_dir):
            src_path = os.path.join(plan_dir, item)
            dst_path = os.path.join(output_dir, item)
            
            if os.path.isfile(src_path):
                shutil.copy2(src_path, dst_path)
            elif os.path.isdir(src_path) and item == "screenshots" and include_screenshots:
                # Sao chép thư mục screenshots nếu có và được yêu cầu
                if not os.path.exists(dst_path):
                    os.makedirs(dst_path)
                
                for screenshot in os.listdir(src_path):
                    src_screenshot = os.path.join(src_path, screenshot)
                    dst_screenshot = os.path.join(dst_path, screenshot)
                    if os.path.isfile(src_screenshot):
                        shutil.copy2(src_screenshot, dst_screenshot)
        
        return True
    
    def duplicate_plan(self, patient_id, plan_id, new_plan_name=None):
        """Tạo bản sao của một kế hoạch"""
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
                
                for subitem in os.listdir(src_path):
                    src_subitem = os.path.join(src_path, subitem)
                    dst_subitem = os.path.join(dst_path, subitem)
                    if os.path.isfile(src_subitem):
                        shutil.copy2(src_subitem, dst_subitem)
        
        # Cập nhật metadata nếu có
        metadata_file = os.path.join(target_plan_dir, "metadata.dcm")
        if os.path.exists(metadata_file):
            metadata = self._load_dicom_data(metadata_file)
            
            # Cập nhật tên kế hoạch nếu được chỉ định
            if metadata is not None:
                if new_plan_name:
                    metadata['plan_name'] = new_plan_name
                else:
                    metadata['plan_name'] = f"Copy of {metadata.get('plan_name', 'Unknown Plan')}"
                
                # Cập nhật thời gian
                metadata['created_at'] = datetime.datetime.now().isoformat()
                metadata['modified_at'] = metadata['created_at']
                
                # Lưu metadata đã cập nhật
                self._create_dicom_file(metadata, 'RTPLAN', target_plan_dir, "metadata")
        
        return {
            'patient_id': patient_id,
            'plan_id': new_plan_id,
            'plan_name': new_plan_name or f"Copy of {plan_id}"
        }
    
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
            raise ValueError("Chưa chọn kế hoạch")
        
        plan_dir = os.path.join(self.workspace_dir, patient_id, plan_id)
        if not os.path.exists(plan_dir):
            raise FileNotFoundError(f"Không tìm thấy kế hoạch: {plan_id}")
        
        # Tải metadata
        metadata_file = os.path.join(plan_dir, "metadata.dcm")
        metadata = None
        if os.path.exists(metadata_file):
            metadata = self._load_dicom_data(metadata_file)
        
        # Tải beam settings
        beam_file = os.path.join(plan_dir, "beam_settings.dcm")
        beam_settings = None
        if os.path.exists(beam_file):
            beam_settings = self._load_dicom_data(beam_file)
        
        # Tải DVH data
        dvh_file = os.path.join(plan_dir, "dvh.dcm")
        dvh_data = None
        if os.path.exists(dvh_file):
            dvh_data = self._load_dicom_data(dvh_file)
        
        # Tạo summary
        summary = {
            'patient_id': patient_id,
            'plan_id': plan_id,
            'plan_name': metadata.get('plan_name', 'Unknown') if metadata else 'Unknown',
            'created_at': metadata.get('created_at', 'Unknown') if metadata else 'Unknown',
            'modified_at': metadata.get('modified_at', 'Unknown') if metadata else 'Unknown',
            'technique': metadata.get('technique', 'Unknown') if metadata else 'Unknown',
            'total_dose': metadata.get('total_dose', 0) if metadata else 0,
            'fraction_count': metadata.get('fraction_count', 0) if metadata else 0,
            'beam_count': len(beam_settings.get('beams', [])) if beam_settings else 0,
            'structures': list(dvh_data.keys()) if dvh_data else []
        }
        
        return summary