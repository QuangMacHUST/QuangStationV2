import tkinter as tk
from tkinter import filedialog
from dicom_parser import DICOMParser
from patient_db import PatientDatabase

class ImportInterface:
    def __init__(self, root):
        self.root = root
        self.db = PatientDatabase()
        self.create_widgets()
    
    def create_widgets(self):
        """Tạo giao diện"""
        btn = tk.Button(self.root, text="Tải file DICOM", command=self.import_dicom)
        btn.pack()
    
    def import_dicom(self):
        """Nhập file DICOM"""
        file_path = filedialog.askopenfilename(filetypes=[("DICOM files", "*.dcm")])
        if file_path:
            parser = DICOMParser(file_path)
            patient_info = parser.extract_patient_info()
            image_data = parser.extract_image_data()
            self.db.insert_patient(patient_info)
            self.db.insert_image(patient_info['patient_id'], image_data)
            print(f"Đã nhập bệnh nhân {patient_info['patient_name']}")