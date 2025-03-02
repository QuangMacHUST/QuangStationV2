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
        
        # Lưu contours bằng pickle
        with open(contours_file, 'wb') as f:
            pickle.dump(contours_data, f)
        
        return True
    
    def save_dose_data(self, dose_data):
        """Lưu dữ liệu liều"""
        if not self.current_patient_id or not self.current_plan_id:
            raise ValueError("Chưa tạo phiên làm việc")
        
        # Tạo đường dẫn đến file dose
        plan_dir = os.path.join(self.workspace_dir, self.current_patient_id, self.current_plan_id)
        dose_file = os.path.join(plan_dir, "dose.npz")
        
        # Lưu dose data dưới dạng npz
        np.savez_compressed(dose_file, dose=dose_data)
        
        return True
    
    def list_plans(self, patient_id=None):
        """Liệt kê các kế hoạch của bệnh nhân"""
        if patient_id is None:
            patient_id = self.current_patient_id
        
        if not patient_id:
            raise ValueError("Chưa chọn bệnh nhân")
        
        # Tạo đường dẫn đến thư mục bệnh nhân
        patient_dir = os.path.join(self.workspace_dir, patient_id)
        
        if not os.path.exists(patient_dir):
            return []
        
        # Liệt kê các thư mục kế hoạch
        plans = []
        for plan_id in os.listdir(patient_dir):
            plan_dir = os.path.join(patient_dir, plan_id)
            if os.path.isdir(plan_dir):
                metadata_file = os.path.join(plan_dir, "metadata.json")
                if os.path.exists(metadata_file):
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        plans.append({
                            'plan_id': plan_id,
                            'metadata': metadata
                        })
                else:
                    plans.append({
                        'plan_id': plan_id,
                        'metadata': {'created_at': plan_id.replace('plan_', '')}
                    })
        
        # Sắp xếp theo thời gian
        plans.sort(key=lambda x: x.get('metadata', {}).get('created_at', ''), reverse=True)
        
        return plans
    
    def load_plan(self, patient_id, plan_id):
        """Tải kế hoạch"""
        # Thiết lập ID hiện tại
        self.current_patient_id = patient_id
        self.current_plan_id = plan_id
        
        # Tạo đường dẫn đến thư mục kế hoạch
        plan_dir = os.path.join(self.workspace_dir, patient_id, plan_id)
        
        if not os.path.exists(plan_dir):
            raise ValueError(f"Không tìm thấy kế hoạch {plan_id} cho bệnh nhân {patient_id}")
        
        # Tải metadata
        metadata_file = os.path.join(plan_dir, "metadata.json")
        metadata = None
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        
        # Tải contours
        contours_file = os.path.join(plan_dir, "contours.pkl")
        contours = None
        if os.path.exists(contours_file):
            with open(contours_file, 'rb') as f:
                contours = pickle.load(f)
        
        # Tải dose data
        dose_file = os.path.join(plan_dir, "dose.npz")
        dose_data = None
        if os.path.exists(dose_file):
            dose_data = np.load(dose_file)['dose']
        
        return {
            'patient_id': patient_id,
            'plan_id': plan_id,
            'metadata': metadata,
            'contours': contours,
            'dose_data': dose_data
        }
    
    def export_plan(self, output_dir=None):
        """Xuất kế hoạch ra thư mục"""
        if not self.current_patient_id or not self.current_plan_id:
            raise ValueError("Chưa tải kế hoạch")
        
        if output_dir is None:
            output_dir = os.path.join(self.workspace_dir, 'exports')
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
        
        # Tạo tên file xuất
        export_name = f"{self.current_patient_id}_{self.current_plan_id}.zip"
        export_path = os.path.join(output_dir, export_name)
        
        # Tạo zip file
        import zipfile
        plan_dir = os.path.join(self.workspace_dir, self.current_patient_id, self.current_plan_id)
        with zipfile.ZipFile(export_path, 'w') as zipf:
            for root, dirs, files in os.walk(plan_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, plan_dir))
        
        return export_path