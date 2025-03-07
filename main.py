import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from datetime import datetime
import uuid
from typing import Dict, Any

from data_management.patient_db import PatientDatabase
from data_management.display import Display
from data_management.import_interface import ImportInterface
from data_management.session_managment import SessionManager
from planning.plan_config import PlanConfig
from data.database import AdvancedDatabase
from utils.logging import get_logger

class MainApp:
    def __init__(self, root):
        """
        Khởi tạo ứng dụng chính
        
        Args:
            root: Cửa sổ gốc Tkinter
        """
        self.root = root
        self.root.title("QuangStation V2 - Hệ thống Lập kế hoạch Xạ trị")
        
        # Khởi tạo logger
        self.logger = get_logger("MainApp")
        self.logger.log_info("Khởi động ứng dụng QuangStation V2")
        
        # Khởi tạo các thành phần quản lý dữ liệu (Model)
        self.patient_manager = PatientManager()
        self.session_manager = SessionManager()
        
        # Khởi tạo các biến trạng thái
        self.current_patient_id = None
        self.current_plan_id = None
        
        # Thiết lập giao diện người dùng (View)
        self.setup_ui()
        
        # Cấu hình sự kiện (Controller)
        self.setup_event_handlers()
        
        # Cập nhật danh sách bệnh nhân
        self.update_patient_list()
        
        # Ghi log khởi động
        self.logger.log_info("Ứng dụng QuangStation V2 đã khởi động thành công")
    
    def setup_ui(self):
        # Tạo menu
        self.create_menu()
        
        # Tạo frame chính
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Chia frame chính thành hai phần: danh sách bệnh nhân và hiển thị
        self.patient_frame = ttk.Frame(self.main_frame, width=300)
        self.patient_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # Frame hiển thị sẽ chiếm phần còn lại
        self.display_frame = ttk.Frame(self.main_frame)
        self.display_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tạo danh sách bệnh nhân
        self.create_patient_list()
    
    def create_menu(self):
        self.menu_bar = tk.Menu(self.root)
        
        # Menu File
        self.menu_file = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_file.add_command(label="Nhập DICOM", command=self.import_dicom)
        self.menu_file.add_command(label="Xuất kế hoạch", command=self.export_plan)
        self.menu_file.add_separator()
        self.menu_file.add_command(label="Thoát", command=self.root.quit)
        self.menu_bar.add_cascade(label="File", menu=self.menu_file)
        
        # Menu Bệnh nhân
        self.menu_patient = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_patient.add_command(label="Thêm bệnh nhân mới", command=self.add_new_patient)
        self.menu_patient.add_command(label="Xóa bệnh nhân", command=self.delete_patient)
        self.menu_bar.add_cascade(label="Bệnh nhân", menu=self.menu_patient)
        
        # Menu Kế hoạch
        self.menu_plan = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_plan.add_command(label="Tạo kế hoạch mới", command=self.create_new_plan)
        self.menu_plan.add_command(label="Sao chép kế hoạch", command=self.copy_plan)
        self.menu_plan.add_command(label="Xóa kế hoạch", command=self.delete_plan)
        self.menu_bar.add_cascade(label="Kế hoạch", menu=self.menu_plan)
        
        # Menu Công cụ
        self.menu_tools = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_tools.add_command(label="Contour tự động", command=self.auto_contour)
        self.menu_tools.add_command(label="Tính toán liều", command=self.calculate_dose)
        self.menu_tools.add_command(label="Tối ưu hóa kế hoạch", command=self.optimize_plan)
        self.menu_tools.add_command(label="DVH", command=self.show_dvh)
        self.menu_bar.add_cascade(label="Công cụ", menu=self.menu_tools)
        
        # Menu Trợ giúp
        self.menu_help = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_help.add_command(label="Hướng dẫn sử dụng", command=self.show_help)
        self.menu_help.add_command(label="Giới thiệu", command=self.show_about)
        self.menu_bar.add_cascade(label="Trợ giúp", menu=self.menu_help)
        
        self.root.config(menu=self.menu_bar)
    
    def create_patient_list(self):
        # Frame chứa tiêu đề
        title_frame = ttk.Frame(self.patient_frame)
        title_frame.pack(fill=tk.X, pady=(0, 5))
        
        title_label = ttk.Label(title_frame, text="Danh sách bệnh nhân", font=("Arial", 12, "bold"))
        title_label.pack(side=tk.LEFT)
        
        refresh_button = ttk.Button(title_frame, text="Làm mới", command=self.update_patient_list)
        refresh_button.pack(side=tk.RIGHT)
        
        # Frame chứa danh sách bệnh nhân
        list_frame = ttk.Frame(self.patient_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tạo scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Tạo Treeview để hiển thị danh sách bệnh nhân
        self.patient_tree = ttk.Treeview(list_frame, yscrollcommand=scrollbar.set)
        self.patient_tree.pack(fill=tk.BOTH, expand=True)
        
        scrollbar.config(command=self.patient_tree.yview)
        
        # Định nghĩa các cột
        self.patient_tree["columns"] = ("patient_id", "name", "date")
        self.patient_tree.column("#0", width=0, stretch=tk.NO)  # Ẩn cột đầu tiên
        self.patient_tree.column("patient_id", width=80, anchor=tk.W)
        self.patient_tree.column("name", width=120, anchor=tk.W)
        self.patient_tree.column("date", width=80, anchor=tk.W)
        
        # Tạo headings
        self.patient_tree.heading("#0", text="", anchor=tk.W)
        self.patient_tree.heading("patient_id", text="ID", anchor=tk.W)
        self.patient_tree.heading("name", text="Họ tên", anchor=tk.W)
        self.patient_tree.heading("date", text="Ngày", anchor=tk.W)
        
        # Bắt sự kiện click
        self.patient_tree.bind("<Double-1>", self.on_patient_select)
    
    def update_patient_list(self):
        # Xóa danh sách cũ
        for item in self.patient_tree.get_children():
            self.patient_tree.delete(item)
        
        # Lấy danh sách bệnh nhân từ database
        patients = self.patient_manager.db.get_all_patients()
        
        # Thêm vào Treeview
        for patient in patients:
            patient_id = patient['patient_id']
            name = patient.get('name', 'Không có tên')
            date = patient.get('study_date', datetime.now().strftime("%Y-%m-%d"))
            
            self.patient_tree.insert("", tk.END, values=(patient_id, name, date))
        
        self.logger.log_info(f"Đã tải {len(patients)} bệnh nhân")
    
    def on_patient_select(self, event):
        # Lấy item được chọn
        selected_item = self.patient_tree.focus()
        if not selected_item:
            return
        
        # Lấy thông tin bệnh nhân
        patient_values = self.patient_tree.item(selected_item, "values")
        if not patient_values:
            return
        
        patient_id = patient_values[0]
        
        # Hiển thị dữ liệu bệnh nhân
        self.display_data(patient_id)
    
    def display_data(self, patient_id):
        """Hiển thị dữ liệu của bệnh nhân"""
        # Xóa hiển thị cũ nếu có
        for widget in self.display_frame.winfo_children():
            widget.destroy()
        
        # Tạo đối tượng hiển thị mới
        self.current_display = Display(self.display_frame, patient_id, self.patient_manager.db)
        
        self.logger.log_info(f"Đã tải dữ liệu bệnh nhân {patient_id}")
    
    # Các hàm xử lý menu
    def import_dicom(self):
        import_window = tk.Toplevel(self.root)
        import_window.title("Nhập dữ liệu DICOM")
        import_window.geometry("500x400")
        
        ImportInterface(import_window, self.update_patient_list)
    
    def export_plan(self):
        if not self.current_display:
            messagebox.showinfo("Thông báo", "Vui lòng chọn bệnh nhân trước")
            return
        
        # TODO: Triển khai xuất kế hoạch
        messagebox.showinfo("Thông báo", "Chức năng xuất kế hoạch đang được phát triển")
    
    def add_new_patient(self):
        # Tạo cửa sổ thêm bệnh nhân mới
        add_window = tk.Toplevel(self.root)
        add_window.title("Thêm bệnh nhân mới")
        add_window.geometry("400x300")
        
        # Các trường thông tin
        ttk.Label(add_window, text="ID bệnh nhân:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        ttk.Label(add_window, text="Họ tên:").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        ttk.Label(add_window, text="Ngày sinh:").grid(row=2, column=0, padx=10, pady=10, sticky=tk.W)
        ttk.Label(add_window, text="Giới tính:").grid(row=3, column=0, padx=10, pady=10, sticky=tk.W)
        
        patient_id_var = tk.StringVar()
        name_var = tk.StringVar()
        birth_var = tk.StringVar()
        gender_var = tk.StringVar(value="Nam")
        
        ttk.Entry(add_window, textvariable=patient_id_var).grid(row=0, column=1, padx=10, pady=10, sticky=tk.EW)
        ttk.Entry(add_window, textvariable=name_var).grid(row=1, column=1, padx=10, pady=10, sticky=tk.EW)
        ttk.Entry(add_window, textvariable=birth_var).grid(row=2, column=1, padx=10, pady=10, sticky=tk.EW)
        
        gender_frame = ttk.Frame(add_window)
        gender_frame.grid(row=3, column=1, padx=10, pady=10, sticky=tk.EW)
        
        ttk.Radiobutton(gender_frame, text="Nam", variable=gender_var, value="Nam").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(gender_frame, text="Nữ", variable=gender_var, value="Nữ").pack(side=tk.LEFT, padx=5)
        
        def save_patient():
            # Lấy thông tin từ form
            patient_info = {
                'patient_id': patient_id_var.get(),
                'name': name_var.get(),
                'birth_date': birth_var.get(),
                'gender': gender_var.get(),
                'study_date': datetime.now().strftime("%Y-%m-%d")
            }
            
            # Kiểm tra dữ liệu
            if not patient_info['patient_id'] or not patient_info['name']:
                messagebox.showerror("Lỗi", "ID và tên bệnh nhân không được để trống")
                return
            
            # Lưu vào database
            success = self.patient_manager.db.insert_patient(patient_info)
            
            if success:
                messagebox.showinfo("Thành công", "Đã thêm bệnh nhân mới")
                self.update_patient_list()
                add_window.destroy()
            else:
                messagebox.showerror("Lỗi", "Không thể thêm bệnh nhân")
        
        # Nút lưu
        ttk.Button(add_window, text="Lưu", command=save_patient).grid(row=4, column=1, pady=20, sticky=tk.E)
    
    def delete_patient(self):
        selected_item = self.patient_tree.focus()
        if not selected_item:
            messagebox.showinfo("Thông báo", "Vui lòng chọn bệnh nhân cần xóa")
            return
        
        patient_values = self.patient_tree.item(selected_item, "values")
        patient_id = patient_values[0]
        
        # Xác nhận xóa
        confirm = messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn xóa bệnh nhân {patient_id}?")
        if not confirm:
            return
        
        # TODO: Triển khai xóa bệnh nhân
        messagebox.showinfo("Thông báo", "Chức năng xóa bệnh nhân đang được phát triển")
    
    def create_new_plan(self):
        if not self.current_display:
            messagebox.showinfo("Thông báo", "Vui lòng chọn bệnh nhân trước")
            return
        
        # Tạo cửa sổ kế hoạch mới
        plan_window = tk.Toplevel(self.root)
        plan_window.title("Tạo kế hoạch mới")
        plan_window.geometry("500x400")
        
        # Tạo đối tượng kế hoạch
        plan_config = PlanConfig()
        
        # Các trường thông tin kế hoạch
        ttk.Label(plan_window, text="Tên kế hoạch:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        ttk.Label(plan_window, text="Tổng liều (Gy):").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        ttk.Label(plan_window, text="Số phân liều:").grid(row=2, column=0, padx=10, pady=10, sticky=tk.W)
        ttk.Label(plan_window, text="Kỹ thuật:").grid(row=3, column=0, padx=10, pady=10, sticky=tk.W)
        ttk.Label(plan_window, text="Loại bức xạ:").grid(row=4, column=0, padx=10, pady=10, sticky=tk.W)
        ttk.Label(plan_window, text="Năng lượng:").grid(row=5, column=0, padx=10, pady=10, sticky=tk.W)
        
        plan_name_var = tk.StringVar(value=f"Plan_{datetime.now().strftime('%Y%m%d')}")
        dose_var = tk.DoubleVar(value=60.0)
        fraction_var = tk.IntVar(value=30)
        
        technique_var = tk.StringVar(value="3DCRT")
        radiation_var = tk.StringVar(value="Photon")
        energy_var = tk.StringVar(value="6 MV")
        
        ttk.Entry(plan_window, textvariable=plan_name_var).grid(row=0, column=1, padx=10, pady=10, sticky=tk.EW)
        ttk.Entry(plan_window, textvariable=dose_var).grid(row=1, column=1, padx=10, pady=10, sticky=tk.EW)
        ttk.Entry(plan_window, textvariable=fraction_var).grid(row=2, column=1, padx=10, pady=10, sticky=tk.EW)
        
        technique_combo = ttk.Combobox(plan_window, textvariable=technique_var, values=["3DCRT", "IMRT", "VMAT", "SBRT"])
        technique_combo.grid(row=3, column=1, padx=10, pady=10, sticky=tk.EW)
        
        radiation_combo = ttk.Combobox(plan_window, textvariable=radiation_var, values=["Photon", "Electron", "Proton"])
        radiation_combo.grid(row=4, column=1, padx=10, pady=10, sticky=tk.EW)
        
        energy_combo = ttk.Combobox(plan_window, textvariable=energy_var, values=["6 MV", "10 MV", "15 MV", "6 FFF", "10 FFF"])
        energy_combo.grid(row=5, column=1, padx=10, pady=10, sticky=tk.EW)
        
        def save_plan():
            # Cập nhật thông tin vào PlanConfig
            plan_config.set_plan_info(
                plan_name_var.get(),
                dose_var.get(),
                fraction_var.get()
            )
            
            plan_config.set_technique(technique_var.get())
            plan_config.set_radiation_info(radiation_var.get(), energy_var.get())
            
            # Lưu kế hoạch vào cơ sở dữ liệu
            plan_data = plan_config.to_dict()
            
            # TODO: Lưu kế hoạch vào cơ sở dữ liệu
            patient_id = self.current_display.patient_id
            self.session_manager.save_plan_metadata(plan_data, patient_id=patient_id)
            
            messagebox.showinfo("Thành công", "Đã tạo kế hoạch mới")
            plan_window.destroy()
        
        # Nút lưu
        ttk.Button(plan_window, text="Tạo kế hoạch", command=save_plan).grid(row=6, column=1, pady=20, sticky=tk.E)
    
    def copy_plan(self):
        if not self.current_display:
            messagebox.showinfo("Thông báo", "Vui lòng chọn bệnh nhân trước")
            return
        # TODO: Triển khai sao chép kế hoạch
        messagebox.showinfo("Thông báo", "Chức năng sao chép kế hoạch đang được phát triển")
    
    def delete_plan(self):
        if not self.current_display:
            messagebox.showinfo("Thông báo", "Vui lòng chọn bệnh nhân trước")
            return
        # TODO: Triển khai xóa kế hoạch
        messagebox.showinfo("Thông báo", "Chức năng xóa kế hoạch đang được phát triển")
    
    def auto_contour(self):
        if not self.current_display:
            messagebox.showinfo("Thông báo", "Vui lòng chọn bệnh nhân trước")
            return
        # TODO: Triển khai contour tự động
        messagebox.showinfo("Thông báo", "Chức năng contour tự động đang được phát triển")
    
    def calculate_dose(self):
        if not self.current_display:
            messagebox.showinfo("Thông báo", "Vui lòng chọn bệnh nhân trước")
            return
        # TODO: Triển khai tính toán liều
        messagebox.showinfo("Thông báo", "Chức năng tính toán liều đang được phát triển")
    
    def optimize_plan(self):
        if not self.current_display:
            messagebox.showinfo("Thông báo", "Vui lòng chọn bệnh nhân trước")
            return
        # TODO: Triển khai tối ưu hóa kế hoạch
        messagebox.showinfo("Thông báo", "Chức năng tối ưu hóa kế hoạch đang được phát triển")
    
    def show_dvh(self):
        if not self.current_display:
            messagebox.showinfo("Thông báo", "Vui lòng chọn bệnh nhân trước")
            return
        # TODO: Triển khai hiển thị DVH
        messagebox.showinfo("Thông báo", "Chức năng hiển thị DVH đang được phát triển")
    
    def show_help(self):
        help_text = """
        Hướng dẫn sử dụng QuangStation V2:
        
        1. Nhập dữ liệu DICOM:
           - Chọn File > Nhập DICOM
           - Chọn thư mục chứa các file DICOM
           - Hệ thống sẽ tự động phân loại và nhập dữ liệu
        
        2. Tạo kế hoạch mới:
           - Chọn bệnh nhân từ danh sách
           - Chọn Kế hoạch > Tạo kế hoạch mới
           - Nhập các thông tin cần thiết
        
        3. Vẽ contour:
           - Chọn bệnh nhân
           - Chọn Công cụ > Contour tự động hoặc vẽ thủ công
        
        4. Tính toán liều:
           - Chọn Công cụ > Tính toán liều
           - Thiết lập thông số tính toán
        
        5. Tối ưu hóa kế hoạch:
           - Chọn Công cụ > Tối ưu hóa kế hoạch
           - Thiết lập các mục tiêu tối ưu
        
        6. Xem DVH:
           - Chọn Công cụ > DVH
           - Phân tích DVH của kế hoạch
        """
        
        help_window = tk.Toplevel(self.root)
        help_window.title("Hướng dẫn sử dụng")
        help_window.geometry("600x500")
        
        text_widget = tk.Text(help_window, wrap=tk.WORD)
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget.insert(tk.END, help_text)
        text_widget.config(state=tk.DISABLED)
    
    def show_about(self):
        about_text = """
        QuangStation V2
        
        Hệ thống lập kế hoạch xạ trị mã nguồn mở
        
        Phiên bản: 2.0.0
        Tác giả: Mạc Đăng Quang
        Liên hệ: 0974478238
        
        © 2023 Mạc Đăng Quang, Đại học Bách Khoa Hà Nội
        """
        
        messagebox.showinfo("Về chúng tôi", about_text)

    def setup_event_handlers(self):
        """Thiết lập các trình xử lý sự kiện cho ứng dụng"""
        # Các sự kiện menu
        self.menu_file.entryconfig("Nhập DICOM", command=self.import_dicom)
        self.menu_file.entryconfig("Xuất kế hoạch", command=self.export_plan)
        
        # Các sự kiện bệnh nhân
        self.patient_tree.bind('<<TreeviewSelect>>', self.on_patient_select)
        self.menu_patient.entryconfig("Thêm bệnh nhân mới", command=self.add_new_patient)
        self.menu_patient.entryconfig("Xóa bệnh nhân", command=self.delete_patient)
        
        # Các sự kiện kế hoạch
        self.menu_plan.entryconfig("Tạo kế hoạch mới", command=self.create_new_plan)
        self.menu_plan.entryconfig("Sao chép kế hoạch", command=self.copy_plan)
        self.menu_plan.entryconfig("Xóa kế hoạch", command=self.delete_plan)
        
        # Các sự kiện công cụ
        self.menu_tools.entryconfig("Contour tự động", command=self.auto_contour)
        self.menu_tools.entryconfig("Tính toán liều", command=self.calculate_dose)
        self.menu_tools.entryconfig("Tối ưu hóa kế hoạch", command=self.optimize_plan)
        self.menu_tools.entryconfig("DVH", command=self.show_dvh)
        
        # Các sự kiện trợ giúp
        self.menu_help.entryconfig("Hướng dẫn sử dụng", command=self.show_help)
        self.menu_help.entryconfig("Giới thiệu", command=self.show_about)
        
        # Ghi log
        self.logger.log_info("Đã thiết lập các trình xử lý sự kiện")

class PatientManager:
    def __init__(self):
        self.db = AdvancedDatabase()
        self.logger = get_logger("PatientManager")
    
    def create_patient(self, patient_info: Dict[str, Any]) -> str:
        """Tạo bệnh nhân mới"""
        patient_id = str(uuid.uuid4())
        patient_info['id'] = patient_id
        
        try:
            self.db.insert_patient(patient_info)
            self.logger.log_info(f"Tạo bệnh nhân mới: {patient_id}")
            return patient_id
        except Exception as e:
            self.logger.log_error(f"Lỗi tạo bệnh nhân: {e}")
            raise
    
    def update_patient(self, patient_id: str, update_data: Dict[str, Any]):
        """Cập nhật thông tin bệnh nhân"""
        try:
            self.db.update_patient(patient_id, update_data)
            self.logger.log_info(f"Cập nhật bệnh nhân: {patient_id}")
        except Exception as e:
            self.logger.log_error(f"Lỗi cập nhật bệnh nhân: {e}")
            raise
    
    def get_patient_details(self, patient_id: str) -> Dict[str, Any]:
        """Lấy chi tiết bệnh nhân"""
        return self.db.get_patient_details(patient_id)
    
    def search_patients(self, **kwargs):
        """Tìm kiếm bệnh nhân với nhiều tiêu chí"""
        return self.db.search_patients(**kwargs)

if __name__ == "__main__":
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()