#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
QuangStation V2 - Hệ thống Lập kế hoạch Xạ trị Mã nguồn Mở
Phát triển bởi Mạc Đăng Quang

Điểm vào chính của ứng dụng.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, Optional, List

# Import các module nội bộ
from quangstation.utils.logging import get_logger, setup_exception_logging, log_system_info
from quangstation.utils.config import GlobalConfig, get_config
from quangstation.data_management.patient_db import PatientDatabase
from quangstation.data_management.display import Display
from quangstation.data_management.session_management import SessionManager

class MainApp:
    """
    Lớp ứng dụng chính quản lý toàn bộ giao diện và hành vi của QuangStation V2
    """
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
        """Thiết lập giao diện người dùng"""
        # Thiết lập kích thước cửa sổ
        window_size = get_config("ui.window_size", [1280, 800])
        self.root.geometry(f"{window_size[0]}x{window_size[1]}")
        
        # Tạo menu
        self.create_menu()
        
        # Tạo frame chính
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tạo panedwindow để phân chia màn hình
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Frame bên trái: danh sách bệnh nhân
        self.patient_frame = ttk.Frame(paned, width=300)
        paned.add(self.patient_frame, weight=1)
        
        # Frame bên phải: hiển thị dữ liệu
        self.display_frame = ttk.Frame(paned)
        paned.add(self.display_frame, weight=4)
        
        # Tạo danh sách bệnh nhân
        self.create_patient_list()
        
        # Thanh trạng thái
        self.status_var = tk.StringVar()
        self.status_var.set("Sẵn sàng")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def create_menu(self):
        """Tạo menu chính của ứng dụng"""
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
        """Tạo danh sách bệnh nhân"""
        # Frame chứa tiêu đề
        title_frame = ttk.Frame(self.patient_frame)
        title_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Tiêu đề
        title_label = ttk.Label(title_frame, text="Danh sách bệnh nhân", font=("Arial", 12, "bold"))
        title_label.pack(side=tk.LEFT, pady=5)
        
        # Nút thêm bệnh nhân
        self.add_patient_button = ttk.Button(title_frame, text="+", width=3, command=self.add_new_patient)
        self.add_patient_button.pack(side=tk.RIGHT, padx=5)
        
        # Frame tìm kiếm
        search_frame = ttk.Frame(self.patient_frame)
        search_frame.pack(fill=tk.X, pady=5)
        
        # Ô tìm kiếm
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # Nút tìm kiếm
        search_button = ttk.Button(search_frame, text="Tìm", command=self.search_patients)
        search_button.pack(side=tk.RIGHT)
        
        # Frame chứa Treeview
        tree_frame = ttk.Frame(self.patient_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tạo Treeview cho danh sách bệnh nhân
        columns = ("id", "name", "date")
        self.patient_tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        
        # Đặt tiêu đề cho các cột
        self.patient_tree.heading("id", text="ID")
        self.patient_tree.heading("name", text="Họ tên")
        self.patient_tree.heading("date", text="Ngày")
        
        # Đặt chiều rộng cột
        self.patient_tree.column("id", width=70)
        self.patient_tree.column("name", width=150)
        self.patient_tree.column("date", width=80)
        
        # Thêm thanh cuộn
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.patient_tree.yview)
        self.patient_tree.configure(yscrollcommand=scrollbar.set)
        
        # Đặt vị trí
        self.patient_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Frame chứa nút xóa và các nút khác
        button_frame = ttk.Frame(self.patient_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        # Nút xóa bệnh nhân
        self.delete_patient_button = ttk.Button(button_frame, text="Xóa", command=self.delete_patient)
        self.delete_patient_button.pack(side=tk.LEFT, padx=5)

    def update_patient_list(self):
        """Cập nhật danh sách bệnh nhân từ database"""
        # Xóa danh sách cũ
        for item in self.patient_tree.get_children():
            self.patient_tree.delete(item)
        
        # Lấy danh sách bệnh nhân từ database
        patients = self.patient_manager.db.get_all_patients()
        
        # Thêm vào Treeview
        for patient in patients:
            patient_id = patient[0]
            name = patient[1]
            date = patient[2]
            self.patient_tree.insert("", tk.END, values=(patient_id, name, date))
        
        self.logger.log_info(f"Đã tải {len(patients)} bệnh nhân")

    def on_patient_select(self, event):
        """Xử lý sự kiện khi chọn bệnh nhân trong danh sách"""
        # Lấy item được chọn
        selection = self.patient_tree.selection()
        if not selection:
            return
        
        # Lấy thông tin bệnh nhân
        item = self.patient_tree.item(selection[0])
        patient_id = item["values"][0]
        
        # Hiển thị dữ liệu bệnh nhân
        self.display_data(patient_id)
        self.current_patient_id = patient_id

    def display_data(self, patient_id):
        """Hiển thị dữ liệu bệnh nhân"""
        # Xóa frame hiển thị hiện tại
        for widget in self.display_frame.winfo_children():
            widget.destroy()
        
        # Tạo đối tượng hiển thị mới
        self.current_display = Display(self.display_frame, patient_id, self.patient_manager.db)
        
        self.logger.log_info(f"Đã tải dữ liệu bệnh nhân {patient_id}")

    # Các hàm xử lý menu
    def import_dicom(self):
        """Nhập dữ liệu DICOM"""
        from quangstation.data_management.import_interface import ImportInterface
        ImportInterface(self.root, self.update_patient_list)

    def export_plan(self):
        """Xuất kế hoạch điều trị"""
        if not self.current_patient_id:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn bệnh nhân trước")
            return
        
        # TODO: Implement export functionality
        self.logger.log_info(f"Xuất kế hoạch cho bệnh nhân {self.current_patient_id}")

    def add_new_patient(self):
        """Thêm bệnh nhân mới"""
        # Tạo cửa sổ thêm bệnh nhân mới
        patient_window = tk.Toplevel(self.root)
        patient_window.title("Thêm bệnh nhân mới")
        patient_window.grab_set()  # Modal dialog
        
        # Frame chứa form
        form_frame = ttk.Frame(patient_window, padding="10")
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Form nhập thông tin
        ttk.Label(form_frame, text="Mã bệnh nhân:").grid(row=0, column=0, sticky=tk.W, pady=5)
        id_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=id_var).grid(row=0, column=1, pady=5, padx=5)
        
        ttk.Label(form_frame, text="Họ tên:").grid(row=1, column=0, sticky=tk.W, pady=5)
        name_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=name_var).grid(row=1, column=1, pady=5, padx=5)
        
        ttk.Label(form_frame, text="Ngày sinh:").grid(row=2, column=0, sticky=tk.W, pady=5)
        dob_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=dob_var).grid(row=2, column=1, pady=5, padx=5)
        
        ttk.Label(form_frame, text="Giới tính:").grid(row=3, column=0, sticky=tk.W, pady=5)
        gender_var = tk.StringVar(value="Nam")
        ttk.Combobox(form_frame, textvariable=gender_var, values=["Nam", "Nữ"]).grid(row=3, column=1, pady=5, padx=5)
        
        # Frame chứa nút
        button_frame = ttk.Frame(patient_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def save_patient():
            # Lấy thông tin từ form
            patient_info = {
                "id": id_var.get(),
                "name": name_var.get(),
                "dob": dob_var.get(),
                "gender": gender_var.get(),
                "date": "Auto"  # Tự động lấy ngày hiện tại
            }
            
            # Kiểm tra dữ liệu
            if not patient_info["id"] or not patient_info["name"]:
                messagebox.showwarning("Cảnh báo", "Vui lòng nhập đầy đủ thông tin bắt buộc")
                return
            
            # Lưu vào database
            success = self.patient_manager.db.insert_patient(patient_info)
            
            if success:
                messagebox.showinfo("Thông báo", "Thêm bệnh nhân thành công")
                patient_window.destroy()
                self.update_patient_list()
            else:
                messagebox.showerror("Lỗi", "Không thể thêm bệnh nhân")
        
        # Nút lưu và hủy
        ttk.Button(button_frame, text="Lưu", command=save_patient).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Hủy", command=patient_window.destroy).pack(side=tk.RIGHT, padx=5)

    def delete_patient(self):
        """Xóa bệnh nhân"""
        # Lấy bệnh nhân được chọn
        selection = self.patient_tree.selection()
        if not selection:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn bệnh nhân để xóa")
            return
        
        # Lấy thông tin bệnh nhân
        item = self.patient_tree.item(selection[0])
        patient_id = item["values"][0]
        patient_name = item["values"][1]
        
        # Xác nhận xóa
        confirm = messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn xóa bệnh nhân {patient_name}?")
        if not confirm:
            return
        
        # TODO: Implement delete functionality
        self.logger.log_info(f"Xóa bệnh nhân {patient_id}")
        messagebox.showinfo("Thông báo", f"Đã xóa bệnh nhân {patient_name}")
        self.update_patient_list()

    def create_new_plan(self):
        """Tạo kế hoạch mới"""
        # TODO: Implement create plan functionality
        self.logger.log_info("Tạo kế hoạch mới")

    def copy_plan(self):
        """Sao chép kế hoạch"""
        # TODO: Implement copy plan functionality
        self.logger.log_info("Sao chép kế hoạch")

    def delete_plan(self):
        """Xóa kế hoạch"""
        # TODO: Implement delete plan functionality
        self.logger.log_info("Xóa kế hoạch")

    def auto_contour(self):
        """Contour tự động"""
        # TODO: Implement auto contour functionality
        self.logger.log_info("Contour tự động")

    def calculate_dose(self):
        """Tính toán liều"""
        # TODO: Implement dose calculation functionality
        self.logger.log_info("Tính toán liều")

    def optimize_plan(self):
        """Tối ưu hóa kế hoạch"""
        # TODO: Implement plan optimization functionality
        self.logger.log_info("Tối ưu hóa kế hoạch")

    def show_dvh(self):
        """Hiển thị DVH"""
        # TODO: Implement DVH display functionality
        self.logger.log_info("Hiển thị DVH")

    def search_patients(self):
        """Tìm kiếm bệnh nhân"""
        search_text = self.search_var.get().strip().lower()
        if not search_text:
            self.update_patient_list()
            return
        
        # TODO: Implement search functionality
        self.logger.log_info(f"Tìm kiếm bệnh nhân: {search_text}")

    def show_help(self):
        """Hiển thị trợ giúp"""
        help_window = tk.Toplevel(self.root)
        help_window.title("Hướng dẫn sử dụng")
        help_window.geometry("600x400")
        
        # Tạo text widget để hiển thị nội dung trợ giúp
        text = tk.Text(help_window, wrap=tk.WORD, padx=10, pady=10)
        text.pack(fill=tk.BOTH, expand=True)
        
        # Thêm nội dung trợ giúp
        help_content = """
        # HƯỚNG DẪN SỬ DỤNG QUANGSTATION V2
        
        ## 1. Quản lý bệnh nhân
        - Thêm bệnh nhân mới: Click vào nút "+" hoặc vào menu "Bệnh nhân > Thêm bệnh nhân mới"
        - Xóa bệnh nhân: Chọn bệnh nhân, click nút "Xóa" hoặc vào menu "Bệnh nhân > Xóa bệnh nhân"
        - Tìm kiếm bệnh nhân: Nhập từ khóa vào ô tìm kiếm và click "Tìm"
        
        ## 2. Nhập/Xuất dữ liệu
        - Nhập DICOM: Menu "File > Nhập DICOM"
        - Xuất kế hoạch: Menu "File > Xuất kế hoạch"
        
        ## 3. Lập kế hoạch
        - Tạo kế hoạch mới: Menu "Kế hoạch > Tạo kế hoạch mới"
        - Contour tự động: Menu "Công cụ > Contour tự động"
        - Tính toán liều: Menu "Công cụ > Tính toán liều"
        - Tối ưu hóa kế hoạch: Menu "Công cụ > Tối ưu hóa kế hoạch"
        - Hiển thị DVH: Menu "Công cụ > DVH"
        
        ## 4. Hỗ trợ
        - Email: quangmacdang@gmail.com
        - Website: https://github.com/quangmac/QuangStationV2
        """
        
        text.insert(tk.END, help_content)
        text.config(state=tk.DISABLED)  # Chỉ đọc
        
        # Thêm thanh cuộn
        scrollbar = ttk.Scrollbar(text, orient=tk.VERTICAL, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def show_about(self):
        """Hiển thị thông tin về ứng dụng"""
        about_text = """
        QuangStation V2
        
        Hệ thống Lập kế hoạch Xạ trị Mã nguồn Mở
        Phiên bản: 2.0.0-beta
        
        Phát triển bởi: Mạc Đăng Quang
        Email: quangmacdang@gmail.com
        Phone: 0974478238
        
        © 2024 Bản quyền
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
    """Lớp quản lý bệnh nhân"""
    def __init__(self):
        """Khởi tạo quản lý bệnh nhân"""
        self.db = PatientDatabase()
        self.logger = get_logger("PatientManager")
    
    def create_patient(self, patient_info: Dict[str, Any]) -> str:
        """Tạo bệnh nhân mới"""
        try:
            patient_id = self.db.insert_patient(patient_info)
            self.logger.log_info(f"Tạo bệnh nhân mới: {patient_id}")
            return patient_id
        except Exception as e:
            self.logger.log_error(f"Lỗi khi tạo bệnh nhân: {e}")
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

def main():
    """Hàm chính để khởi động ứng dụng"""
    # Thiết lập bắt ngoại lệ
    setup_exception_logging()
    
    # Ghi log thông tin hệ thống
    log_system_info()
    
    # Tạo cửa sổ chính
    root = tk.Tk()
    app = MainApp(root)
    
    # Khởi động ứng dụng
    root.mainloop()

if __name__ == "__main__":
    main() 