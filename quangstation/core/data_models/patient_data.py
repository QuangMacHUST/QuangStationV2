#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module định nghĩa cấu trúc dữ liệu cho thông tin bệnh nhân.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

@dataclass
class PatientData:
    """
    Class chứa thông tin chi tiết về bệnh nhân.
    """
    
    # Thông tin nhận dạng
    patient_id: str  # Mã bệnh nhân
    patient_name: str  # Họ tên bệnh nhân
    
    # Thông tin cá nhân
    gender: Optional[str] = None  # Nam, Nữ, Khác
    dob: Optional[datetime] = None  # Ngày sinh
    age: Optional[int] = None  # Tuổi
    
    # Thông tin nghiên cứu
    study_uid: Optional[str] = None  # UID của nghiên cứu
    study_date: Optional[datetime] = None  # Ngày thực hiện nghiên cứu
    study_description: Optional[str] = None  # Mô tả nghiên cứu
    
    # Thông tin y tế
    diagnoses: List[str] = field(default_factory=list)  # Danh sách các chẩn đoán
    clinical_history: Optional[str] = None  # Tiền sử lâm sàng
    weight: Optional[float] = None  # Cân nặng (kg)
    height: Optional[float] = None  # Chiều cao (cm)
    
    # Thông tin xạ trị
    prescription: Optional[str] = None  # Toa xạ trị
    fractions: Optional[int] = None  # Số phân liều
    total_dose: Optional[float] = None  # Tổng liều (Gy)
    
    # Thông tin khác
    referring_physician: Optional[str] = None  # Bác sĩ chỉ định
    attending_physician: Optional[str] = None  # Bác sĩ điều trị
    institution_name: Optional[str] = None  # Tên cơ sở y tế
    
    # Thông tin bổ sung
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def patient_full_id(self) -> str:
        """Trả về mã nhận dạng đầy đủ của bệnh nhân."""
        return f"{self.patient_id}_{self.patient_name.replace(' ', '_')}"
    
    @property
    def age_at_study(self) -> Optional[int]:
        """Tính tuổi của bệnh nhân tại thời điểm nghiên cứu."""
        if not self.dob or not self.study_date:
            return self.age
            
        age = self.study_date.year - self.dob.year
        # Kiểm tra xem đã qua sinh nhật trong năm đó chưa
        if (self.study_date.month, self.study_date.day) < (self.dob.month, self.dob.day):
            age -= 1
            
        return age
    
    @property
    def bmi(self) -> Optional[float]:
        """Tính chỉ số khối cơ thể (BMI)."""
        if not self.weight or not self.height or self.height <= 0:
            return None
            
        # BMI = cân nặng (kg) / (chiều cao (m) * chiều cao (m))
        height_m = self.height / 100  # Chuyển từ cm sang m
        return self.weight / (height_m * height_m)
    
    def set_diagnosis(self, diagnosis: str, index: int = 0):
        """
        Thiết lập hoặc cập nhật chẩn đoán.
        
        Args:
            diagnosis: Chẩn đoán bệnh
            index: Vị trí trong danh sách (0 = chính, 1 = thứ cấp, ...)
        """
        while len(self.diagnoses) <= index:
            self.diagnoses.append("")
        self.diagnoses[index] = diagnosis
    
    def get_diagnosis(self, index: int = 0) -> Optional[str]:
        """
        Lấy chẩn đoán tại vị trí cụ thể.
        
        Args:
            index: Vị trí trong danh sách (0 = chính, 1 = thứ cấp, ...)
            
        Returns:
            str: Chẩn đoán tại vị trí đó, hoặc None nếu không tồn tại
        """
        if 0 <= index < len(self.diagnoses):
            return self.diagnoses[index]
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Chuyển đổi thông tin bệnh nhân thành dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary chứa thông tin bệnh nhân
        """
        result = {
            "patient_id": self.patient_id,
            "patient_name": self.patient_name,
            "gender": self.gender,
            "age": self.age,
            "diagnoses": self.diagnoses,
            "clinical_history": self.clinical_history,
            "study_uid": self.study_uid,
            "study_description": self.study_description,
            "metadata": self.metadata
        }
        
        # Định dạng các ngày tháng thành chuỗi
        if self.dob:
            result["dob"] = self.dob.strftime("%Y-%m-%d")
            
        if self.study_date:
            result["study_date"] = self.study_date.strftime("%Y-%m-%d")
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PatientData':
        """
        Tạo đối tượng PatientData từ dictionary.
        
        Args:
            data: Dictionary chứa thông tin bệnh nhân
            
        Returns:
            PatientData: Đối tượng bệnh nhân
        """
        # Xử lý các trường ngày tháng
        dob = None
        if "dob" in data and data["dob"]:
            try:
                dob = datetime.strptime(data["dob"], "%Y-%m-%d")
            except ValueError:
                pass
                
        study_date = None
        if "study_date" in data and data["study_date"]:
            try:
                study_date = datetime.strptime(data["study_date"], "%Y-%m-%d")
            except ValueError:
                pass
        
        # Tạo đối tượng từ dữ liệu
        return cls(
            patient_id=data.get("patient_id", ""),
            patient_name=data.get("patient_name", ""),
            gender=data.get("gender"),
            dob=dob,
            age=data.get("age"),
            study_uid=data.get("study_uid"),
            study_date=study_date,
            study_description=data.get("study_description"),
            diagnoses=data.get("diagnoses", []),
            clinical_history=data.get("clinical_history"),
            weight=data.get("weight"),
            height=data.get("height"),
            prescription=data.get("prescription"),
            fractions=data.get("fractions"),
            total_dose=data.get("total_dose"),
            referring_physician=data.get("referring_physician"),
            attending_physician=data.get("attending_physician"),
            institution_name=data.get("institution_name"),
            metadata=data.get("metadata", {})
        )
