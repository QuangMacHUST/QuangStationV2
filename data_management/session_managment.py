import os
import json
import pickle
import datetime
from data_management.patient_db import PatientDatabase

class SessionManager:
    """Quản lý phiên làm việc, lưu và tải kế hoạch xạ trị"""
    
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
    
    def save_plan_metadata(self, metadata):
        """Lưu metadata cho kế hoạch"""
        if not self.current_patient_id or not self.current_plan_id:
            raise ValueError("Chưa tạo phiên làm việc")
        
        # Tạo đường dẫn đến file metadata
        plan_dir = os.path.join(self.workspace_dir, self.current_patient_id, self.current_plan_id)
        metadata_file = os.path.join(plan_dir, "metadata.json")
        
        # Lưu metadata
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        return True
    
    def save_contours(self, contours_data):
        """Lưu dữ liệu contour"""
        if not self.current_patient_id or not self.current_plan_id:
            raise ValueError("Chưa tạo phiên làm việc")
        
        # Tạo đường dẫn đến file contours
        plan_dir = os.path.join(self.workspace_dir, self.current_patient_id, self.current_plan_id)
        contours_file = os.path.join(plan_dir, "contours.pkl")
        
        # Lưu contours dưới dạng pickle
        with open(contours_file, 'wb') as f:
            pickle.dump(contours_data, f)
        
        return True
    
    def save_beam_settings(self, beam_settings):
        """Lưu cài đặt chùm tia"""
        if not self.current_patient_id or not self.current_plan_id:
            raise ValueError("Chưa tạo phiên làm việc")
        
        # Tạo đường dẫn đến file beam settings
        plan_dir = os.path.join(self.workspace_dir, self.current_patient_id, self.current_plan_id)
        beam_file = os.path.join(plan_dir, "beam_settings.json")
        
        # Lưu beam settings
        with open(beam_file, 'w', encoding='utf-8') as f:
            json.dump(beam_settings, f, ensure_ascii=False, indent=2)
        
        return True
    
    def save_dose_calculation(self, dose_data):
        """Lưu dữ liệu tính liều"""
        if not self.current_patient_id or not self.current_plan_id:
            raise ValueError("Chưa tạo phiên làm việc")
        
        # Tạo đường dẫn đến file dose
        plan_dir = os.path.join(self.workspace_dir, self.current_patient_id, self.current_plan_id)
        dose_file = os.path.join(plan_dir, "dose.pkl")
        
        # Lưu dose data dưới dạng pickle
        with open(dose_file, 'wb') as f:
            pickle.dump(dose_data, f)
        
        return True
    
    def save_dvh_data(self, dvh_data):
        """Lưu dữ liệu DVH"""
        if not self.current_patient_id or not self.current_plan_id:
            raise ValueError("Chưa tạo phiên làm việc")
        
        # Tạo đường dẫn đến file DVH
        plan_dir = os.path.join(self.workspace_dir, self.current_patient_id, self.current_plan_id)
        dvh_file = os.path.join(plan_dir, "dvh.pkl")
        
        # Lưu DVH data dưới dạng pickle
        with open(dvh_file, 'wb') as f:
            pickle.dump(dvh_data, f)
        
        return True
    
    def load_session(self, patient_id, plan_id):
        """Tải phiên làm việc"""
        self.current_patient_id = patient_id
        self.current_plan_id = plan_id
        
        # Kiểm tra xem phiên làm việc có tồn tại
        plan_dir = os.path.join(self.workspace_dir, patient_id, plan_id)
        if not os.path.exists(plan_dir):
            raise FileNotFoundError(f"Không tìm thấy kế hoạch: {plan_id} cho bệnh nhân: {patient_id}")
        
        # Tải metadata
        metadata_file = os.path.join(plan_dir, "metadata.json")
        metadata = None
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        
        # Tải contours
        contours_file = os.path.join(plan_dir, "contours.pkl")
        contours_data = None
        if os.path.exists(contours_file):
            with open(contours_file, 'rb') as f:
                contours_data = pickle.load(f)
        
        # Tải beam settings
        beam_file = os.path.join(plan_dir, "beam_settings.json")
        beam_settings = None
        if os.path.exists(beam_file):
            with open(beam_file, 'r', encoding='utf-8') as f:
                beam_settings = json.load(f)
        
        # Tải dose data
        dose_file = os.path.join(plan_dir, "dose.pkl")
        dose_data = None
        if os.path.exists(dose_file):
            with open(dose_file, 'rb') as f:
                dose_data = pickle.load(f)
        
        # Tải DVH data
        dvh_file = os.path.join(plan_dir, "dvh.pkl")
        dvh_data = None
        if os.path.exists(dvh_file):
            with open(dvh_file, 'rb') as f:
                dvh_data = pickle.load(f)
        
        return {
            'metadata': metadata,
            'contours': contours_data,
            'beam_settings': beam_settings,
            'dose_data': dose_data,
            'dvh_data': dvh_data
        }
    
    def list_patients(self):
        """Liệt kê danh sách bệnh nhân"""
        patients = []
        
        # Liệt kê thư mục con trong workspace
        if os.path.exists(self.workspace_dir):
            for item in os.listdir(self.workspace_dir):
                patient_dir = os.path.join(self.workspace_dir, item)
                if os.path.isdir(patient_dir):
                    patients.append(item)
        
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
                    metadata_file = os.path.join(plan_dir, "metadata.json")
                    metadata = None
                    if os.path.exists(metadata_file):
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                    
                    plans.append({
                        'plan_id': item,
                        'metadata': metadata
                    })
        
        return plans
    
    def delete_plan(self, patient_id, plan_id):
        """Xóa một kế hoạch"""
        plan_dir = os.path.join(self.workspace_dir, patient_id, plan_id)
        
        if not os.path.exists(plan_dir):
            return False
        
        # Xóa các file trong thư mục kế hoạch
        for item in os.listdir(plan_dir):
            file_path = os.path.join(plan_dir, item)
            if os.path.isfile(file_path):
                os.remove(file_path)
        
        # Xóa thư mục kế hoạch
        os.rmdir(plan_dir)
        
        # Reset current plan nếu đang chọn kế hoạch bị xóa
        if self.current_patient_id == patient_id and self.current_plan_id == plan_id:
            self.current_plan_id = None
        
        return True
    
    def export_plan(self, output_dir):
        """Xuất kế hoạch hiện tại ra thư mục khác"""
        if not self.current_patient_id or not self.current_plan_id:
            raise ValueError("Chưa tạo phiên làm việc")
        
        plan_dir = os.path.join(self.workspace_dir, self.current_patient_id, self.current_plan_id)
        
        # Tạo thư mục đích nếu chưa tồn tại
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Sao chép các file từ plan_dir sang output_dir
        import shutil
        for item in os.listdir(plan_dir):
            src_path = os.path.join(plan_dir, item)
            dst_path = os.path.join(output_dir, item)
            if os.path.isfile(src_path):
                shutil.copy2(src_path, dst_path)
        
        return True