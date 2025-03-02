import tkinter as tk
from tkinter import filedialog, messagebox
from data_management.dicom_parser import DICOMParser
from data_management.patient_db import PatientDatabase

class ImportInterface:
    def __init__(self, root, display_callback):
        self.root = root
        self.db = PatientDatabase()
        self.display_callback = display_callback
        self.create_widgets()

    def create_widgets(self):
        self.root.title("Nhập liệu dữ liệu DICOM")
        frame = tk.Frame(self.root, padx=10, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame, text="Tải dữ liệu DICOM", font=("Arial", 12)).pack(pady=5)
        tk.Button(frame, text="Chọn thư mục", command=self.import_dicom_folder, bg="lightblue").pack(pady=5)
        self.status_label = tk.Label(frame, text="", font=("Arial", 10))
        self.status_label.pack(pady=5)

    def import_dicom_folder(self):
        folder_path = tk.filedialog.askdirectory(title="Chọn thư mục chứa dữ liệu DICOM")
        if folder_path:
            try:
                parser = DICOMParser(folder_path)
                patient_info = parser.extract_patient_info()
                self.db.insert_patient(patient_info)
            
                if parser.ct_files:
                    try:
                        ct_volume = parser.extract_image_volume('CT')
                        self.db.insert_volume(patient_info['patient_id'], 'CT', ct_volume)
                    except ValueError as e:
                        messagebox.showerror("Lỗi", str(e))
            
                if parser.mri_files:
                    try:
                        mri_volume = parser.extract_image_volume('MRI')
                        self.db.insert_volume(patient_info['patient_id'], 'MRI', mri_volume)
                    except ValueError as e:
                        messagebox.showerror("Lỗi", str(e))
            
                if parser.rt_struct:
                    rt_struct_data = parser.extract_rt_struct()
                    self.db.insert_rt_struct(patient_info['patient_id'], rt_struct_data)
            
                self.status_label.config(text=f"Đã nhập dữ liệu cho bệnh nhân {patient_info['patient_name']}")
                self.display_callback(patient_info['patient_id'])
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể nhập thư mục: {e}")