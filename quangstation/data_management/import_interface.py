import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import time
from datetime import datetime
from pathlib import Path
import glob
import pydicom

from quangstation.data_management.dicom_parser import DICOMParser
from quangstation.data_management.patient_db import PatientDatabase
from quangstation.data_management.session_management import SessionManager
from quangstation.image_processing.image_loader import ImageLoader

"""
Module này tạo giao diện nhập dữ liệu DICOM
"""
class ImportInterface:
    def __init__(self, root, update_callback=None):
        """Khởi tạo giao diện nhập dữ liệu DICOM
        
        Args:
            root: Cửa sổ gốc Tkinter
            update_callback: Hàm callback để cập nhật giao diện chính sau khi nhập
        """
        self.root = root
        self.db = PatientDatabase()
        self.session_manager = SessionManager()
        self.image_loader = ImageLoader()
        self.update_callback = update_callback
        
        # Biến theo dõi tiến trình
        self.is_importing = False
        self.current_task = ""
        self.progress_value = 0
        
        # Tạo giao diện
        self.create_widgets()
    
    def create_widgets(self):
        """Tạo các widget cho giao diện nhập DICOM"""
        self.root.title("Nhập dữ liệu DICOM - QuangStation V2")
        
        # Frame chính
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame tiêu đề
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(title_frame, text="Nhập dữ liệu DICOM", font=("Arial", 14, "bold")).pack(side=tk.LEFT)
        
        # Frame nhập dữ liệu
        import_frame = ttk.LabelFrame(main_frame, text="Tùy chọn nhập dữ liệu", padding=10)
        import_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tạo layout grid
        import_frame.columnconfigure(0, weight=1)
        import_frame.columnconfigure(1, weight=3)
        
        # Hàng 1: Chọn thư mục
        ttk.Label(import_frame, text="Thư mục DICOM:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        folder_frame = ttk.Frame(import_frame)
        folder_frame.grid(row=0, column=1, sticky=tk.EW, pady=5)
        
        self.folder_var = tk.StringVar()
        ttk.Entry(folder_frame, textvariable=self.folder_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(folder_frame, text="Duyệt...", command=self.browse_folder).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Hàng 2: Các tùy chọn nhập
        ttk.Label(import_frame, text="Tùy chọn:").grid(row=1, column=0, sticky=tk.W, pady=5)
        
        options_frame = ttk.Frame(import_frame)
        options_frame.grid(row=1, column=1, sticky=tk.EW, pady=5)
        
        self.import_ct_var = tk.BooleanVar(value=True)
        self.import_mri_var = tk.BooleanVar(value=True)
        self.import_struct_var = tk.BooleanVar(value=True)
        self.import_dose_var = tk.BooleanVar(value=True)
        self.import_plan_var = tk.BooleanVar(value=True)
        self.import_rtimg_var = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(options_frame, text="CT", variable=self.import_ct_var).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(options_frame, text="MRI", variable=self.import_mri_var).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(options_frame, text="RT Structure", variable=self.import_struct_var).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(options_frame, text="RT Dose", variable=self.import_dose_var).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(options_frame, text="RT Plan", variable=self.import_plan_var).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(options_frame, text="RT Image", variable=self.import_rtimg_var).pack(side=tk.LEFT, padx=5)
        
        # Hàng 3: Thông tin bệnh nhân
        ttk.Label(import_frame, text="ID bệnh nhân:").grid(row=2, column=0, sticky=tk.W, pady=5)
        
        patient_frame = ttk.Frame(import_frame)
        patient_frame.grid(row=2, column=1, sticky=tk.EW, pady=5)
        
        self.patient_id_var = tk.StringVar()
        self.patient_id_entry = ttk.Entry(patient_frame, textvariable=self.patient_id_var, width=20)
        self.patient_id_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(patient_frame, text="Tên bệnh nhân:").pack(side=tk.LEFT)
        self.patient_name_var = tk.StringVar()
        ttk.Entry(patient_frame, textvariable=self.patient_name_var, width=30).pack(side=tk.LEFT, padx=(5, 0))
        
        # Hàng 4: Tạo nút nhập dữ liệu
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.import_button = ttk.Button(
            button_frame, 
            text="Nhập dữ liệu", 
            command=self.start_import_thread, 
            style="Accent.TButton"
        )
        self.import_button.pack(side=tk.RIGHT)
        
        ttk.Button(
            button_frame, 
            text="Hủy", 
            command=self.root.destroy
        ).pack(side=tk.RIGHT, padx=5)
        
        # Frame trạng thái và tiến trình
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_var = tk.StringVar(value="Sẵn sàng để nhập dữ liệu DICOM")
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT)
        
        # Thanh tiến trình
        self.progress = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress.pack(fill=tk.X, pady=(5, 0))
        
        # Thêm style cho nút
        style = ttk.Style()
        if style.theme_use() == 'vista': 
            # Windows
            style.configure("Accent.TButton", foreground="white", background="#007bff")
        else:
            # MacOS và Linux
            style.configure("Accent.TButton", font=("Arial", 10, "bold"))
    
    def browse_folder(self):
        """Chọn thư mục chứa dữ liệu DICOM"""
        folder_path = filedialog.askdirectory(title="Chọn thư mục chứa dữ liệu DICOM")
        if folder_path:
            self.folder_var.set(folder_path)
            # Quét sơ bộ thư mục để lấy thông tin bệnh nhân
            self.scan_dicom_folder(folder_path)
    
    def scan_dicom_folder(self, folder_path):
        """Quét sơ bộ thư mục DICOM để lấy thông tin bệnh nhân
        
        Args:
            folder_path: Đường dẫn đến thư mục chứa dữ liệu DICOM
        """
        try:
            # Tìm file DICOM đầu tiên
            dicom_file = None
            for root, _, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        import pydicom
                        ds = pydicom.dcmread(file_path, stop_before_pixels=True)
                        # Lấy thông tin bệnh nhân
                        if hasattr(ds, 'PatientID') and hasattr(ds, 'PatientName'):
                            self.patient_id_var.set(ds.PatientID)
                            self.patient_name_var.set(str(ds.PatientName))
                            return
                    except:
                        continue
        except Exception as error:
            print(f"Lỗi khi quét thư mục DICOM: {error}")
    
    def start_import_thread(self):
        """Bắt đầu tiến trình nhập dữ liệu trong một thread riêng"""
        if not self.folder_var.get():
            messagebox.showerror("Lỗi", "Vui lòng chọn thư mục DICOM")
            return
        
        # Vô hiệu hóa nút nhập trong quá trình import
        self.import_button.config(state=tk.DISABLED)
        
        # Bắt đầu tiến trình import trong thread riêng
        self.is_importing = True
        import_thread = threading.Thread(target=self.import_dicom_folder)
        import_thread.daemon = True
        import_thread.start()
        
        # Bắt đầu cập nhật thanh tiến trình
        self.update_progress()
    
    def update_progress(self):
        """Cập nhật thanh tiến trình và trạng thái"""
        if self.is_importing:
            self.progress['value'] = self.progress_value
            self.status_var.set(self.current_task)
            self.root.after(100, self.update_progress)
        else:
            self.progress['value'] = 100
            self.import_button.config(state=tk.NORMAL)
    
    def import_dicom_folder(self):
        """Nhập dữ liệu DICOM từ thư mục đã chọn"""
        folder_path = self.folder_var.get()
        
        try:
            # Cập nhật tiến trình
            self.current_task = "Đang phân tích dữ liệu DICOM..."
            self.progress_value = 10
            
            # Tạo parser
            parser = DICOMParser(folder_path)
            
            # Trích xuất thông tin bệnh nhân
            patient_info = parser.extract_patient_info()
            
            # Nếu người dùng đã nhập ID bệnh nhân mới, cập nhật thông tin
            if self.patient_id_var.get() and self.patient_id_var.get() != patient_info.get('patient_id', ''):
                patient_info['patient_id'] = self.patient_id_var.get()
            
            # Nếu người dùng đã nhập tên bệnh nhân mới, cập nhật thông tin
            if self.patient_name_var.get() and self.patient_name_var.get() != patient_info.get('patient_name', ''):
                patient_info['patient_name'] = self.patient_name_var.get()
            
            # Thêm thông tin thời gian nếu chưa có
            if 'study_date' not in patient_info or not patient_info['study_date']:
                patient_info['study_date'] = datetime.now().strftime("%Y%m%d")
            
            # Lưu thông tin bệnh nhân vào cơ sở dữ liệu
            self.db.insert_patient(patient_info)
            
            patient_id = patient_info['patient_id']
            
            # Cập nhật tiến trình
            self.progress_value = 20
            
            # Import CT nếu được chọn và có file CT
            if self.import_ct_var.get() and parser.ct_files:
                self.current_task = "Đang nhập dữ liệu CT..."
                try:
                    ct_volume, ct_metadata = parser.extract_image_volume('CT')
                    self.db.insert_volume(patient_id, 'CT', ct_volume, ct_metadata)
                except Exception as error:
                    messagebox.showerror("Lỗi CT", f"Không thể nhập dữ liệu CT: {error}")
            
            self.progress_value = 40
            
            # Import MRI nếu được chọn và có file MRI
            if self.import_mri_var.get() and parser.mri_files:
                self.current_task = "Đang nhập dữ liệu MRI..."
                try:
                    mri_volume, mri_metadata = parser.extract_image_volume('MRI')
                    self.db.insert_volume(patient_id, 'MRI', mri_volume, mri_metadata)
                except Exception as error:
                    messagebox.showerror("Lỗi MRI", f"Không thể nhập dữ liệu MRI: {error}")
            
            self.progress_value = 50
            
            # Import RT Structure nếu được chọn và có file RT Structure
            if self.import_struct_var.get() and parser.rt_struct:
                self.current_task = "Đang nhập dữ liệu RT Structure..."
                try:
                    rt_struct_data = parser.extract_rt_struct()
                    self.db.insert_rt_struct(patient_id, rt_struct_data)
                except Exception as error:
                    messagebox.showerror("Lỗi RT Structure", f"Không thể nhập dữ liệu RT Structure: {error}")
            
            self.progress_value = 60
            
            # Import RT Dose nếu được chọn và có file RT Dose
            if self.import_dose_var.get() and parser.rt_dose:
                self.current_task = "Đang nhập dữ liệu RT Dose..."
                try:
                    rt_dose_data, rt_dose_metadata = parser.extract_rt_dose()
                    self.db.insert_rt_dose(patient_id, rt_dose_data, rt_dose_metadata)
                except Exception as error:
                    messagebox.showerror("Lỗi RT Dose", f"Không thể nhập dữ liệu RT Dose: {error}")
            
            self.progress_value = 70
            
            # Import RT Plan nếu được chọn và có file RT Plan
            if self.import_plan_var.get() and parser.rt_plan:
                self.current_task = "Đang nhập dữ liệu RT Plan..."
                try:
                    rt_plan_data = parser.extract_rt_plan()
                    self.db.insert_rt_plan(patient_id, rt_plan_data)
                except Exception as error:
                    messagebox.showerror("Lỗi RT Plan", f"Không thể nhập dữ liệu RT Plan: {error}")
            
            self.progress_value = 80
            
            # Import RT Image nếu được chọn và có file RT Image
            if self.import_rtimg_var.get() and parser.rt_image:
                self.current_task = "Đang nhập dữ liệu RT Image..."
                try:
                    # Sử dụng image_loader để tải RT Image
                    rt_image_path = parser.rt_image
                    rt_image_data, rt_image_metadata = self.image_loader.load_dicom_series(rt_image_path)
                    
                    # Lưu vào cơ sở dữ liệu - cần mở rộng PatientDatabase để hỗ trợ RT Image
                    if hasattr(self.db, 'insert_rt_image'):
                        self.db.insert_rt_image(patient_id, rt_image_data, rt_image_metadata)
                except Exception as error:
                    messagebox.showerror("Lỗi RT Image", f"Không thể nhập dữ liệu RT Image: {error}")
            
            self.progress_value = 90
            
            # Tạo phiên làm việc mới cho bệnh nhân
            self.current_task = "Đang tạo phiên làm việc..."
            self.session_manager.create_new_session(patient_id)
            
            # Hoàn thành nhập dữ liệu
            self.current_task = "Hoàn tất nhập dữ liệu DICOM"
            self.progress_value = 100
            
            # Hiển thị thông báo thành công
            messagebox.showinfo("Thành công", f"Đã nhập dữ liệu cho bệnh nhân {patient_info.get('patient_name', patient_id)}")
            
            # Gọi callback để cập nhật giao diện chính
            if self.update_callback:
                self.root.after(0, lambda: self.update_callback())
            
            # Đóng cửa sổ nhập dữ liệu
            self.root.after(500, self.root.destroy)
            
        except Exception as error:
            messagebox.showerror("Lỗi", f"Không thể nhập dữ liệu DICOM: {error}")
        
        # Đánh dấu kết thúc quá trình nhập
        self.is_importing = False

# Hàm test giao diện khi chạy trực tiếp file này
def test_interface():
    root = tk.Tk()
    root.geometry("600x400")
    app = ImportInterface(root)
    root.mainloop()

# Chạy test khi file được thực thi trực tiếp
if __name__ == "__main__":
    test_interface()