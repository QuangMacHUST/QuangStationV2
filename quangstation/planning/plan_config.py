import json
import numpy as np
from datetime import datetime

class PlanConfig:
    """Lớp quản lý cấu hình kế hoạch xạ trị"""
    
    def __init__(self):
        # Thông tin cơ bản
        self.plan_name = "Unnamed Plan"
        self.plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.created_at = datetime.now().isoformat()
        self.modified_at = self.created_at
        
        # Thông tin liều lượng
        self.total_dose = 0.0  # Liều tổng (Gy)
        self.fraction_count = 0  # Số buổi điều trị
        self.fraction_dose = 0.0  # Liều mỗi buổi (Gy)
        
        # Thông tin loại bức xạ
        self.radiation_type = "photon"  # photon, electron, proton
        self.energy = ""  # Ví dụ: "6MV", "10MeV"
        
        # Thông tin thiết bị và tư thế
        self.machine_name = ""  # Tên máy xạ trị
        self.patient_position = "HFS"  # HFS, HFP, FFS, FFP
        
        # Kỹ thuật xạ trị
        self.technique = "3DCRT"  # 3DCRT, IMRT, VMAT, SRS, SBRT
        
        # Thông tin isocenter
        self.isocenter = [0.0, 0.0, 0.0]  # Tọa độ (x, y, z) mm
        
        # Danh sách trường chiếu
        self.beams = []
        
        # Thuật toán tính liều
        self.dose_algorithm = "CCC"  # CCC, AxB, AAA
        
        # Mục tiêu ràng buộc tối ưu
        self.optimization_constraints = []
        
        # Danh sách cấu trúc và chỉ số liều mục tiêu
        self.structure_objectives = {}
    
    def set_plan_info(self, plan_name, total_dose, fraction_count):
        """Thiết lập thông tin cơ bản cho kế hoạch"""
        self.plan_name = plan_name
        self.total_dose = float(total_dose)
        self.fraction_count = int(fraction_count)
        
        if self.fraction_count > 0:
            self.fraction_dose = self.total_dose / self.fraction_count
        else:
            self.fraction_dose = 0.0
        
        self.modified_at = datetime.now().isoformat()
        return True
    
    def set_radiation_info(self, radiation_type, energy):
        """Thiết lập thông tin loại bức xạ"""
        # Kiểm tra loại bức xạ hợp lệ
        valid_types = ["photon", "electron", "proton"]
        if radiation_type.lower() not in valid_types:
            raise ValueError(f"Loại bức xạ không hợp lệ. Chọn một trong: {valid_types}")
        
        self.radiation_type = radiation_type.lower()
        self.energy = energy
        self.modified_at = datetime.now().isoformat()
        return True
    
    def set_machine_info(self, machine_name, patient_position):
        """Thiết lập thông tin máy xạ trị và tư thế bệnh nhân"""
        self.machine_name = machine_name
        
        # Kiểm tra tư thế hợp lệ
        valid_positions = ["HFS", "HFP", "FFS", "FFP"]
        if patient_position.upper() not in valid_positions:
            raise ValueError(f"Tư thế bệnh nhân không hợp lệ. Chọn một trong: {valid_positions}")
        
        self.patient_position = patient_position.upper()
        self.modified_at = datetime.now().isoformat()
        return True
    
    def set_technique(self, technique):
        """Thiết lập kỹ thuật xạ trị"""
        # Kiểm tra kỹ thuật hợp lệ
        valid_techniques = ["3DCRT", "IMRT", "VMAT", "SRS", "SBRT"]
        if technique.upper() not in valid_techniques:
            raise ValueError(f"Kỹ thuật xạ trị không hợp lệ. Chọn một trong: {valid_techniques}")
        
        self.technique = technique.upper()
        self.modified_at = datetime.now().isoformat()
        return True
    
    def set_isocenter(self, x, y, z):
        """Thiết lập tâm isocenter"""
        self.isocenter = [float(x), float(y), float(z)]
        self.modified_at = datetime.now().isoformat()
        return True
    
    def set_dose_algorithm(self, algorithm):
        """Thiết lập thuật toán tính liều"""
        # Kiểm tra thuật toán hợp lệ
        valid_algorithms = ["CCC", "AxB", "AAA", "Monte Carlo", "PB"]
        if algorithm not in valid_algorithms:
            raise ValueError(f"Thuật toán tính liều không hợp lệ. Chọn một trong: {valid_algorithms}")
        
        self.dose_algorithm = algorithm
        self.modified_at = datetime.now().isoformat()
        return True
    
    def add_beam(self, beam_info):
        """Thêm một trường chiếu mới"""
        # Kiểm tra thông tin cần thiết
        required_fields = ["name", "gantry_angle", "collimator_angle", "couch_angle"]
        for field in required_fields:
            if field not in beam_info:
                raise ValueError(f"Thiếu thông tin bắt buộc '{field}' cho trường chiếu")
        
        # Tạo ID beam nếu chưa có
        if "id" not in beam_info:
            beam_info["id"] = f"beam_{len(self.beams) + 1}"
        
        # Thêm trọng số mặc định nếu chưa có
        if "weight" not in beam_info:
            beam_info["weight"] = 1.0
        
        # Thêm beam vào danh sách
        self.beams.append(beam_info)
        self.modified_at = datetime.now().isoformat()
        return beam_info["id"]
    
    def update_beam(self, beam_id, beam_info):
        """Cập nhật thông tin trường chiếu"""
        for i, beam in enumerate(self.beams):
            if beam["id"] == beam_id:
                self.beams[i].update(beam_info)
                self.modified_at = datetime.now().isoformat()
                return True
        
        return False
    
    def remove_beam(self, beam_id):
        """Xóa một trường chiếu"""
        for i, beam in enumerate(self.beams):
            if beam["id"] == beam_id:
                del self.beams[i]
                self.modified_at = datetime.now().isoformat()
                return True
        
        return False
    
    def add_mlc_segment(self, beam_id, mlc_positions):
        """Thêm phân đoạn MLC cho trường chiếu"""
        for i, beam in enumerate(self.beams):
            if beam["id"] == beam_id:
                if "mlc_segments" not in beam:
                    beam["mlc_segments"] = []
                
                beam["mlc_segments"].append(mlc_positions)
                self.modified_at = datetime.now().isoformat()
                return True
        
        return False
    
    def add_arc_segment(self, beam_id, start_angle, stop_angle, control_points):
        """Thêm phân đoạn cung quay cho VMAT"""
        for i, beam in enumerate(self.beams):
            if beam["id"] == beam_id:
                if "arc_segments" not in beam:
                    beam["arc_segments"] = []
                
                arc_segment = {
                    "start_angle": start_angle,
                    "stop_angle": stop_angle,
                    "control_points": control_points
                }
                
                beam["arc_segments"].append(arc_segment)
                self.modified_at = datetime.now().isoformat()
                return True
        
        return False
    
    def add_bolus(self, bolus_info):
        """Thêm bolus"""
        if "bolus" not in self.__dict__:
            self.bolus = []
        
        # Kiểm tra thông tin cần thiết
        required_fields = ["name", "thickness", "material"]
        for field in required_fields:
            if field not in bolus_info:
                raise ValueError(f"Thiếu thông tin bắt buộc '{field}' cho bolus")
        
        # Tạo ID bolus nếu chưa có
        if "id" not in bolus_info:
            bolus_info["id"] = f"bolus_{len(self.bolus) + 1}"
        
        # Thêm bolus vào danh sách
        self.bolus.append(bolus_info)
        self.modified_at = datetime.now().isoformat()
        return bolus_info["id"]
    
    def add_structure_objective(self, structure_name, objective_type, dose, volume=None, weight=1.0):
        """Thêm ràng buộc liều cho một cấu trúc"""
        if structure_name not in self.structure_objectives:
            self.structure_objectives[structure_name] = []
        
        # Kiểm tra loại ràng buộc hợp lệ
        valid_types = ["min_dose", "max_dose", "mean_dose", "min_dvh", "max_dvh"]
        if objective_type not in valid_types:
            raise ValueError(f"Loại ràng buộc không hợp lệ. Chọn một trong: {valid_types}")
        
        objective = {
            "type": objective_type,
            "dose": float(dose),
            "weight": float(weight)
        }
        
        # Thêm thông tin khối lượng cho ràng buộc DVH
        if objective_type in ["min_dvh", "max_dvh"]:
            if volume is None:
                raise ValueError("Cần chỉ định khối lượng (%) cho ràng buộc DVH")
            objective["volume"] = float(volume)
        
        self.structure_objectives[structure_name].append(objective)
        self.modified_at = datetime.now().isoformat()
        return True
    
    def remove_structure_objective(self, structure_name, index):
        """Xóa ràng buộc liều cho một cấu trúc"""
        if structure_name in self.structure_objectives:
            if 0 <= index < len(self.structure_objectives[structure_name]):
                del self.structure_objectives[structure_name][index]
                self.modified_at = datetime.now().isoformat()
                return True
        
        return False
    
    def to_dict(self):
        """Chuyển đổi cấu hình thành dictionary"""
        return {
            "plan_name": self.plan_name,
            "plan_id": self.plan_id,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "total_dose": self.total_dose,
            "fraction_count": self.fraction_count,
            "fraction_dose": self.fraction_dose,
            "radiation_type": self.radiation_type,
            "energy": self.energy,
            "machine_name": self.machine_name,
            "patient_position": self.patient_position,
            "technique": self.technique,
            "isocenter": self.isocenter,
            "beams": self.beams,
            "dose_algorithm": self.dose_algorithm,
            "optimization_constraints": self.optimization_constraints,
            "structure_objectives": self.structure_objectives,
            "bolus": self.bolus if hasattr(self, "bolus") else []
        }
    
    def from_dict(self, data):
        """Cập nhật cấu hình từ dictionary"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        return True
    
    def to_json(self, file_path=None):
        """Chuyển đổi cấu hình thành JSON"""
        data = self.to_dict()
        
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    def from_json(self, json_data, is_file=False):
        """Cập nhật cấu hình từ JSON"""
        if is_file:
            with open(json_data, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = json.loads(json_data)
        
        return self.from_dict(data)