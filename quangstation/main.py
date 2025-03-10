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
from tkinter import ttk, messagebox, filedialog
from typing import Dict, Any, Optional, List
import threading
import uuid
from datetime import datetime

# Import các module nội bộ
from quangstation.utils.logging import get_logger, setup_exception_logging, log_system_info
from quangstation.utils.config import GlobalConfig, get_config
from quangstation.data_management.patient_db import PatientDatabase
from quangstation.data_management.display import Display
from quangstation.data_management.import_interface import ImportInterface
from quangstation.data_management.session_management import SessionManager
from quangstation.planning.plan_config import PlanConfig

class PatientManager:
    """Lớp quản lý thông tin bệnh nhân và tương tác với cơ sở dữ liệu"""
    
    def __init__(self):
        """Khởi tạo PatientManager"""
        self.db = PatientDatabase()
        self.logger = get_logger("PatientManager")
    
    def create_patient(self, patient_info: Dict[str, Any]) -> str:
        """
        Tạo bệnh nhân mới
        
        Args:
            patient_info: Thông tin bệnh nhân
            
        Returns:
            str: ID của bệnh nhân mới tạo
        """
        patient_id = str(uuid.uuid4())
        
        try:
            # Tạo đối tượng Patient mới
            patient = Patient(patient_id=patient_id)
            
            # Cập nhật thông tin từ patient_info
            if 'demographics' in patient_info:
                patient.demographics.update(patient_info['demographics'])
            elif 'name' in patient_info:
                # Hỗ trợ format cũ
                patient.demographics.update({
                    'name': patient_info.get('name', ''),
                    'birth_date': patient_info.get('birth_date', ''),
                    'gender': patient_info.get('gender', ''),
                    'address': patient_info.get('address', ''),
                    'phone': patient_info.get('phone', ''),
                    'email': patient_info.get('email', '')
                })
            
            if 'clinical_info' in patient_info:
                patient.clinical_info.update(patient_info['clinical_info'])
            elif 'diagnosis' in patient_info:
                # Hỗ trợ format cũ
                patient.clinical_info.update({
                    'diagnosis': patient_info.get('diagnosis', ''),
                    'diagnosis_date': patient_info.get('diagnosis_date', ''),
                    'physician': patient_info.get('physician', ''),
                    'notes': patient_info.get('notes', '')
                })
            
            # Thêm bệnh nhân vào database
            self.db.add_patient(patient)
            self.logger.info(f"Tạo bệnh nhân mới: {patient_id}")
            return patient_id
        except Exception as error:
            self.logger.error(f"Lỗi tạo bệnh nhân: {str(error)}")
            raise
    
    def update_patient(self, patient_id: str, update_data: Dict[str, Any]):
        """
        Cập nhật thông tin bệnh nhân
        
        Args:
            patient_id: ID bệnh nhân
            update_data: Dữ liệu cần cập nhật
        """
        try:
            # Lấy thông tin bệnh nhân hiện tại
            patient = self.db.get_patient(patient_id)
            if not patient:
                raise ValueError(f"Không tìm thấy bệnh nhân với ID: {patient_id}")
            
            # Cập nhật thông tin từ update_data
            if 'demographics' in update_data:
                patient.demographics.update(update_data['demographics'])
            elif 'name' in update_data:
                # Hỗ trợ format cũ
                patient.demographics.update({
                    'name': update_data.get('name', patient.demographics.get('name', '')),
                    'birth_date': update_data.get('birth_date', patient.demographics.get('birth_date', '')),
                    'gender': update_data.get('gender', patient.demographics.get('gender', '')),
                    'address': update_data.get('address', patient.demographics.get('address', '')),
                    'phone': update_data.get('phone', patient.demographics.get('phone', '')),
                    'email': update_data.get('email', patient.demographics.get('email', ''))
                })
            
            if 'clinical_info' in update_data:
                patient.clinical_info.update(update_data['clinical_info'])
            elif 'diagnosis' in update_data:
                # Hỗ trợ format cũ
                patient.clinical_info.update({
                    'diagnosis': update_data.get('diagnosis', patient.clinical_info.get('diagnosis', '')),
                    'diagnosis_date': update_data.get('diagnosis_date', patient.clinical_info.get('diagnosis_date', '')),
                    'physician': update_data.get('physician', patient.clinical_info.get('physician', '')),
                    'notes': update_data.get('notes', patient.clinical_info.get('notes', ''))
                })
            
            # Cập nhật và lưu
            patient.modified_date = datetime.now().isoformat()
            self.db.update_patient(patient)
            self.logger.info(f"Cập nhật bệnh nhân: {patient_id}")
        except Exception as error:
            self.logger.error(f"Lỗi cập nhật bệnh nhân: {str(error)}")
            raise
    
    def get_patient_details(self, patient_id: str) -> Dict[str, Any]:
        """
        Lấy chi tiết bệnh nhân
        
        Args:
            patient_id: ID bệnh nhân
            
        Returns:
            Dict: Thông tin chi tiết của bệnh nhân
        """
        patient = self.db.get_patient(patient_id)
        if patient:
            return patient.to_dict()
        return {}
    
    def get_plan_details(self, patient_id: str, plan_id: str) -> Dict[str, Any]:
        """
        Lấy chi tiết kế hoạch điều trị
        
        Args:
            patient_id: ID bệnh nhân
            plan_id: ID kế hoạch
            
        Returns:
            Dict: Thông tin chi tiết của kế hoạch, hoặc dict rỗng nếu không tìm thấy
        """
        patient = self.db.get_patient(patient_id)
        if patient and plan_id in patient.plans:
            return patient.plans[plan_id]
        return {}
    
    def search_patients(self, **kwargs):
        """
        Tìm kiếm bệnh nhân với nhiều tiêu chí
        
        Args:
            **kwargs: Các tiêu chí tìm kiếm
            
        Returns:
            List: Danh sách bệnh nhân thỏa mãn
        """
        return self.db.search_patients(**kwargs)
    
    def get_all_patients(self):
        """
        Lấy danh sách tất cả bệnh nhân
        
        Returns:
            List: Danh sách tất cả bệnh nhân
        """
        return self.db.get_all_patients()
    
    def delete_patient(self, patient_id: str) -> bool:
        """
        Xóa bệnh nhân
        
        Args:
            patient_id: ID bệnh nhân cần xóa
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            success = self.db.delete_patient(patient_id)
            if success:
                self.logger.info(f"Đã xóa bệnh nhân: {patient_id}")
            return success
        except Exception as error:
            self.logger.error(f"Lỗi xóa bệnh nhân: {str(error)}")
            return False

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
        
        # Thiết lập icon
        try:
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception as error:
            pass
        
        # Thiết lập theme
        self.setup_theme()
        
        # Khởi tạo logger
        self.logger = get_logger("MainApp")
        
        # Khởi tạo các thành phần quản lý dữ liệu (Model)
        self.patient_manager = PatientManager()
        self.session_manager = SessionManager()
        
        # Khởi tạo các biến trạng thái
        self.current_patient_id = None
        self.current_plan_id = None
        self.current_display = None  # Khởi tạo biến current_display
        
        # Thiết lập giao diện người dùng (View)
        self.setup_ui()
        
        # Cấu hình sự kiện (Controller)
        self.setup_event_handlers()
        
        # Cập nhật danh sách bệnh nhân
        self.update_patient_list()
        
        # Ghi log khởi động
        self.logger.info("Ứng dụng QuangStation V2 đã khởi động thành công")
    
    def setup_theme(self):
        """Thiết lập theme và style cho ứng dụng"""
        style = ttk.Style()
        
        # Sử dụng theme mặc định của hệ điều hành
        try:
            if sys.platform.startswith('win'):
                style.theme_use('vista')
            elif sys.platform.startswith('darwin'):
                style.theme_use('aqua')
            else:
                style.theme_use('clam')
        except tk.TclError:
            # Nếu không có theme phù hợp, sử dụng default
            style.theme_use('default')
        
        # Tùy chỉnh màu sắc và font
        style.configure("TButton", padding=6, relief="flat", background="#ccc")
        style.configure("TLabel", padding=6, font=('Helvetica', 10))
        style.configure("TFrame", background="#f5f5f5")
        style.configure("Treeview", rowheight=25, font=('Helvetica', 10))
        style.configure("Treeview.Heading", font=('Helvetica', 11, 'bold'))

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
        self.main_pane = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True)
        
        # Frame bên trái: danh sách bệnh nhân
        self.patient_frame = ttk.Frame(self.main_pane, width=300)
        self.main_pane.add(self.patient_frame, weight=1)
        
        # Frame bên phải: hiển thị dữ liệu
        self.display_frame = ttk.Frame(self.main_pane)
        self.main_pane.add(self.display_frame, weight=4)
        
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
        
        self.logger.info(f"Đã tải {len(patients)} bệnh nhân")

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
        if not patient_id:
            return
            
        # Lấy thông tin bệnh nhân
        patient_data = self.patient_manager.get_patient_details(patient_id)
        if not patient_data:
            messagebox.showerror("Lỗi", f"Không tìm thấy thông tin bệnh nhân {patient_id}")
            return
            
        # Cập nhật thông tin bệnh nhân
        self.patient_info_label.config(text=f"Bệnh nhân: {patient_data.get('name', 'Không tên')}")
        
        # Cập nhật danh sách kế hoạch
        self.update_plan_list(patient_id)
        
        # Cập nhật trạng thái
        self.current_patient_id = patient_id
        self.logger.info(f"Đã hiển thị dữ liệu bệnh nhân {patient_id}")
    
    def update_plan_info(self, plan_id):
        """Cập nhật thông tin kế hoạch trong giao diện"""
        if not plan_id or not self.current_patient_id:
            return
            
        # Lấy thông tin kế hoạch
        plan_data = self.patient_manager.get_plan_details(self.current_patient_id, plan_id)
        if not plan_data:
            self.logger.warning(f"Không tìm thấy thông tin kế hoạch {plan_id}")
            return
            
        # Xóa thông tin cũ
        if hasattr(self, 'plan_info_frame'):
            for widget in self.plan_info_frame.winfo_children():
                widget.destroy()
        else:
            # Tạo frame nếu chưa có
            self.plan_info_frame = ttk.Frame(self.main_frame)
            self.plan_info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Hiển thị thông tin kế hoạch
        ttk.Label(self.plan_info_frame, text=f"Kế hoạch: {plan_data.get('name', 'Không tên')}", 
                 font=('Helvetica', 12, 'bold')).pack(anchor=tk.W, pady=(10, 5))
        
        # Thông tin cơ bản
        info_frame = ttk.LabelFrame(self.plan_info_frame, text="Thông tin cơ bản")
        info_frame.pack(fill=tk.X, pady=5)
        
        # Grid layout cho thông tin
        ttk.Label(info_frame, text="Ngày tạo:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, text=plan_data.get('created_date', 'N/A')).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(info_frame, text="Kỹ thuật:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, text=plan_data.get('technique', 'N/A')).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(info_frame, text="Liều tổng:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, text=f"{plan_data.get('total_dose', 0)} Gy").grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(info_frame, text="Số buổi:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, text=str(plan_data.get('fraction_count', 0))).grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(info_frame, text="Liều mỗi buổi:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)
        fraction_dose = 0
        if plan_data.get('fraction_count', 0) > 0:
            fraction_dose = plan_data.get('total_dose', 0) / plan_data.get('fraction_count', 1)
        ttk.Label(info_frame, text=f"{fraction_dose:.2f} Gy").grid(row=4, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Thông tin máy và năng lượng
        ttk.Label(info_frame, text="Máy xạ trị:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, text=plan_data.get('machine', 'N/A')).grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(info_frame, text="Loại bức xạ:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, text=plan_data.get('radiation_type', 'N/A')).grid(row=1, column=3, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(info_frame, text="Năng lượng:").grid(row=2, column=2, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, text=plan_data.get('energy', 'N/A')).grid(row=2, column=3, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(info_frame, text="Tư thế:").grid(row=3, column=2, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, text=plan_data.get('position', 'N/A')).grid(row=3, column=3, sticky=tk.W, padx=5, pady=2)
        
        # Thông tin trạng thái
        status_frame = ttk.LabelFrame(self.plan_info_frame, text="Trạng thái")
        status_frame.pack(fill=tk.X, pady=5)
        
        # Kiểm tra xem đã có contour chưa
        has_contours = self.session_manager.has_contours(self.current_patient_id, plan_id)
        contour_status = "Đã tạo" if has_contours else "Chưa tạo"
        contour_color = "green" if has_contours else "red"
        
        # Kiểm tra xem đã tính liều chưa
        has_dose = self.session_manager.has_dose_calculation(self.current_patient_id, plan_id)
        dose_status = "Đã tính" if has_dose else "Chưa tính"
        dose_color = "green" if has_dose else "red"
        
        # Kiểm tra xem đã tối ưu chưa
        has_optimization = plan_data.get('optimization_status') == 'completed'
        optimization_status = "Đã tối ưu" if has_optimization else "Chưa tối ưu"
        optimization_color = "green" if has_optimization else "red"
        
        # Hiển thị trạng thái
        ttk.Label(status_frame, text="Contour:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(status_frame, text=contour_status, foreground=contour_color).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(status_frame, text="Tính liều:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(status_frame, text=dose_status, foreground=dose_color).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(status_frame, text="Tối ưu hóa:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(status_frame, text=optimization_status, foreground=optimization_color).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Nút tác vụ
        button_frame = ttk.Frame(self.plan_info_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Contour", command=self.auto_contour).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Tính liều", command=self.calculate_dose).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Tối ưu hóa", command=self.optimize_plan).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Xuất kế hoạch", command=self.export_plan).pack(side=tk.LEFT, padx=5)
        
        self.logger.info(f"Đã cập nhật thông tin kế hoạch {plan_id}")

    # Các hàm xử lý menu
    def import_dicom(self):
        """Nhập dữ liệu DICOM"""
        ImportInterface(self.root, self.update_patient_list)

    def export_plan(self):
        """Xuất kế hoạch điều trị"""
        if not self.current_patient_id:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn bệnh nhân trước")
            return
        
        if not self.current_plan_id:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn kế hoạch trước")
            return
        
        # Hỏi user về thư mục xuất ra
        export_folder = filedialog.askdirectory(title="Chọn thư mục xuất kế hoạch")
        if not export_folder:
            return
        
        # Tạo dialog chọn các thành phần để xuất
        export_dialog = tk.Toplevel(self.root)
        export_dialog.title("Xuất kế hoạch điều trị")
        export_dialog.geometry("400x300")
        export_dialog.transient(self.root)
        export_dialog.grab_set()
        
        # Tạo các biến để lưu trạng thái checkbox
        image_var = tk.BooleanVar(value=True)
        structure_var = tk.BooleanVar(value=True) 
        plan_var = tk.BooleanVar(value=True)
        dose_var = tk.BooleanVar(value=True)
        report_var = tk.BooleanVar(value=True)
        
        ttk.Label(export_dialog, text="Chọn các thành phần cần xuất:", font=('Helvetica', 12, 'bold')).pack(pady=10)
        
        # Tạo các checkbox
        ttk.Checkbutton(export_dialog, text="Hình ảnh CT/MRI", variable=image_var).pack(anchor=tk.W, padx=20, pady=5)
        ttk.Checkbutton(export_dialog, text="Cấu trúc giải phẫu", variable=structure_var).pack(anchor=tk.W, padx=20, pady=5)
        ttk.Checkbutton(export_dialog, text="Kế hoạch xạ trị", variable=plan_var).pack(anchor=tk.W, padx=20, pady=5)
        ttk.Checkbutton(export_dialog, text="Phân bố liều", variable=dose_var).pack(anchor=tk.W, padx=20, pady=5)
        ttk.Checkbutton(export_dialog, text="Báo cáo kế hoạch", variable=report_var).pack(anchor=tk.W, padx=20, pady=5)
        
        # Format xuất
        ttk.Label(export_dialog, text="Định dạng xuất:", font=('Helvetica', 11)).pack(anchor=tk.W, padx=10, pady=5)
        
        # Tạo biến radio button
        format_var = tk.StringVar(value="dicom")
        ttk.Radiobutton(export_dialog, text="DICOM", variable=format_var, value="dicom").pack(anchor=tk.W, padx=20, pady=2)
        ttk.Radiobutton(export_dialog, text="JSON (ngoại trừ hình ảnh)", variable=format_var, value="json").pack(anchor=tk.W, padx=20, pady=2)
        
        # Nút xuất và hủy
        button_frame = ttk.Frame(export_dialog)
        button_frame.pack(fill=tk.X, pady=20, padx=10)
        
        def do_export():
            try:
                export_items = []
                
                if image_var.get():
                    export_items.append('image')
                if structure_var.get():
                    export_items.append('structure')
                if plan_var.get():
                    export_items.append('plan')
                if dose_var.get():
                    export_items.append('dose')
                
                if not export_items:
                    messagebox.showwarning("Cảnh báo", "Vui lòng chọn ít nhất một thành phần để xuất")
                    return
                
                # Thực hiện xuất dữ liệu
                export_format = format_var.get()
                
                # Hiển thị progress bar
                progress = ttk.Progressbar(export_dialog, mode='indeterminate')
                progress.pack(fill=tk.X, padx=10, pady=10)
                progress.start(10)
                
                # Vô hiệu hóa các nút
                export_button.config(state=tk.DISABLED)
                cancel_button.config(state=tk.DISABLED)
                
                # Cập nhật UI
                export_dialog.update()
                
                # Xuất dữ liệu dựa trên định dạng
                if export_format == "dicom":
                    result = self.integration_manager.export_dicom_data(export_folder, export_items)
                else:  # json
                    result = self.session_manager.export_plan(export_folder, include_screenshots=True)
                
                progress.stop()
                progress.pack_forget()
                
                # Xuất báo cáo nếu được chọn
                if report_var.get():
                    report_path = os.path.join(export_folder, f"{self.current_plan_id}_report.pdf")
                    self.create_report(report_path)
                
                if result:
                    messagebox.showinfo("Thành công", f"Đã xuất kế hoạch thành công vào thư mục:\n{export_folder}")
                    export_dialog.destroy()
                else:
                    messagebox.showerror("Lỗi", "Xuất kế hoạch thất bại. Vui lòng kiểm tra log để biết chi tiết.")
                    export_button.config(state=tk.NORMAL)
                    cancel_button.config(state=tk.NORMAL)
                
            except Exception as error:
                self.logger.error(f"Lỗi khi xuất kế hoạch: {str(error)}")
                messagebox.showerror("Lỗi", f"Xuất kế hoạch thất bại: {str(error)}")
                export_button.config(state=tk.NORMAL)
                cancel_button.config(state=tk.NORMAL)
        
        export_button = ttk.Button(button_frame, text="Xuất", command=do_export)
        export_button.pack(side=tk.RIGHT, padx=5)
        
        cancel_button = ttk.Button(button_frame, text="Hủy", command=export_dialog.destroy)
        cancel_button.pack(side=tk.RIGHT, padx=5)
        
        self.logger.info(f"Mở hộp thoại xuất kế hoạch cho bệnh nhân {self.current_patient_id}")

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
            try:
                success = self.patient_manager.create_patient(patient_info)
                
                if success:
                    messagebox.showinfo("Thông báo", "Thêm bệnh nhân thành công")
                    # Cập nhật danh sách bệnh nhân
                    self.update_patient_list()
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể thêm bệnh nhân: {str(e)}")
                return
        
        # Nút lưu và hủy
        ttk.Button(button_frame, text="Lưu", command=save_patient).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Hủy", command=patient_window.destroy).pack(side=tk.RIGHT, padx=5)

    def delete_patient(self):
        """Xóa bệnh nhân"""
        if not self.current_patient_id:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn bệnh nhân trước khi xóa")
            return
        
        # Lấy thông tin bệnh nhân
        patient_info = self.patient_manager.get_patient_details(self.current_patient_id)
        patient_name = patient_info.get('name', 'Không rõ tên')
        
        # Xác nhận xóa
        confirm = messagebox.askyesno(
            "Xác nhận xóa", 
            f"Bạn có chắc chắn muốn xóa bệnh nhân {patient_name}?\n\n"
            "Tất cả dữ liệu liên quan sẽ bị xóa vĩnh viễn và không thể khôi phục.",
            icon="warning"
        )
        
        if not confirm:
            return
        
        # Tiến hành xóa
        success = self.patient_manager.delete_patient(self.current_patient_id)
        
        if success:
            self.logger.info(f"Đã xóa bệnh nhân {self.current_patient_id} ({patient_name})")
            messagebox.showinfo("Thành công", f"Đã xóa bệnh nhân {patient_name}")
            
            # Xóa hiển thị nếu đang hiển thị
            if hasattr(self, 'current_display') and self.current_display:
                try:
                    self.current_display.close()
                except:
                    pass
                self.display_frame.destroy()
                self.display_frame = ttk.Frame(self.main_pane)
                self.main_pane.add(self.display_frame, weight=4)
            
            # Cập nhật danh sách và thiết lập lại biến
            self.current_patient_id = None
            self.update_patient_list()
        else:
            self.logger.error(f"Lỗi khi xóa bệnh nhân {self.current_patient_id}")
            messagebox.showerror("Lỗi", f"Không thể xóa bệnh nhân {patient_name}. Vui lòng thử lại sau.")

    def create_new_plan(self):
        """Tạo kế hoạch mới"""
        if not self.current_patient_id:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn bệnh nhân trước khi tạo kế hoạch mới")
            return
        
        # Tạo cửa sổ dialog để nhập thông tin kế hoạch
        plan_dialog = tk.Toplevel(self.root)
        plan_dialog.title("Tạo kế hoạch mới")
        plan_dialog.geometry("500x400")
        plan_dialog.resizable(False, False)
        plan_dialog.transient(self.root)
        plan_dialog.grab_set()
        
        # Tạo các phần tử giao diện
        ttk.Label(plan_dialog, text="Thông tin kế hoạch xạ trị", font=('Helvetica', 12, 'bold')).pack(pady=10)
        
        # Frame chứa các trường nhập liệu
        input_frame = ttk.Frame(plan_dialog)
        input_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Tên kế hoạch
        ttk.Label(input_frame, text="Tên kế hoạch:").grid(row=0, column=0, sticky=tk.W, pady=5)
        plan_name_var = tk.StringVar(value="Kế hoạch mới")
        ttk.Entry(input_frame, textvariable=plan_name_var, width=30).grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # Liều tổng
        ttk.Label(input_frame, text="Tổng liều (Gy):").grid(row=1, column=0, sticky=tk.W, pady=5)
        total_dose_var = tk.DoubleVar(value=60.0)
        ttk.Entry(input_frame, textvariable=total_dose_var, width=10).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Số buổi (phân liều)
        ttk.Label(input_frame, text="Số buổi:").grid(row=2, column=0, sticky=tk.W, pady=5)
        fraction_var = tk.IntVar(value=30)
        ttk.Entry(input_frame, textvariable=fraction_var, width=10).grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # Loại bức xạ
        ttk.Label(input_frame, text="Loại bức xạ:").grid(row=3, column=0, sticky=tk.W, pady=5)
        radiation_var = tk.StringVar(value="photon")
        ttk.Combobox(input_frame, textvariable=radiation_var, values=["photon", "electron", "proton"], 
                     width=15, state="readonly").grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # Năng lượng
        ttk.Label(input_frame, text="Năng lượng:").grid(row=4, column=0, sticky=tk.W, pady=5)
        energy_var = tk.StringVar(value="6 MV")
        ttk.Combobox(input_frame, textvariable=energy_var, 
                     values=["6 MV", "10 MV", "15 MV", "6 MeV", "9 MeV", "12 MeV", "15 MeV"], 
                     width=15).grid(row=4, column=1, sticky=tk.W, pady=5)
        
        # Mô tả
        ttk.Label(input_frame, text="Mô tả:").grid(row=5, column=0, sticky=tk.W, pady=5)
        description_var = tk.StringVar(value="")
        ttk.Entry(input_frame, textvariable=description_var, width=30).grid(row=5, column=1, sticky=tk.W, pady=5)
        
        # Kỹ thuật
        ttk.Label(input_frame, text="Kỹ thuật:").grid(row=6, column=0, sticky=tk.W, pady=5)
        technique_var = tk.StringVar(value="3DCRT")
        ttk.Combobox(input_frame, textvariable=technique_var, 
                     values=["3DCRT", "IMRT", "VMAT", "SRS", "SBRT"], 
                     width=15, state="readonly").grid(row=6, column=1, sticky=tk.W, pady=5)
        
        # Máy điều trị
        ttk.Label(input_frame, text="Máy điều trị:").grid(row=7, column=0, sticky=tk.W, pady=5)
        machine_var = tk.StringVar(value="TrueBeam")
        ttk.Combobox(input_frame, textvariable=machine_var, 
                     values=["TrueBeam", "Halcyon", "VitalBeam", "Clinac", "Elekta Versa HD", "Cyberknife"], 
                     width=20).grid(row=7, column=1, sticky=tk.W, pady=5)
        
        # Tư thế
        ttk.Label(input_frame, text="Tư thế bệnh nhân:").grid(row=8, column=0, sticky=tk.W, pady=5)
        position_var = tk.StringVar(value="HFS")
        ttk.Combobox(input_frame, textvariable=position_var, 
                     values=["HFS", "HFP", "FFS", "FFP"], 
                     width=10, state="readonly").grid(row=8, column=1, sticky=tk.W, pady=5)
        
        # Nút tạo kế hoạch
        def save_plan():
            try:
                # Xử lý năng lượng (trích xuất giá trị số từ chuỗi như "6 MV")
                energy_str = energy_var.get()
                dose_per_fraction = 2.0  # Mặc định 2 Gy/fx
                
                # Tính liều trên mỗi phân liều từ tổng liều và số phân liều
                if fraction_var.get() > 0:
                    dose_per_fraction = total_dose_var.get() / fraction_var.get()
                
                # Thêm kế hoạch vào cơ sở dữ liệu
                plan_id = self.patient_manager.create_plan(
                    self.current_patient_id,
                    {
                        "name": plan_name_var.get(),
                        "description": description_var.get(),
                        "technique": technique_var.get(),
                        "fractions": int(fraction_var.get()),
                        "dose_per_fraction": float(dose_per_fraction),
                        "total_dose": float(total_dose_var.get()),
                        "energy": energy_str,
                        "machine": machine_var.get(),
                        "position": position_var.get(),
                        "radiation_type": radiation_var.get(),
                        "created_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                )
                
                # Hiển thị thông báo thành công
                messagebox.showinfo("Thành công", f"Đã tạo kế hoạch mới: {plan_name_var.get()}")
                
                # Đóng dialog
                plan_dialog.destroy()
                
                # Cập nhật trạng thái
                self.current_plan_id = plan_id
                self.logger.info(f"Đã tạo kế hoạch mới: {plan_id} - {plan_name_var.get()}")
                
                # Hiển thị màn hình lập kế hoạch
                try:
                    # Tải thông tin kế hoạch
                    plan_data = self.patient_manager.get_plan_details(self.current_patient_id, plan_id)
                    if not plan_data:
                        raise ValueError("Không tìm thấy thông tin kế hoạch")

                    # Mở màn hình lập kế hoạch trong cửa sổ mới
                    from quangstation.gui.plan_design import PlanDesignWindow
                    design_window = PlanDesignWindow(
                        tk.Toplevel(self.root),
                        patient_id=self.current_patient_id,
                        plan_id=plan_id,
                        plan_data=plan_data
                    )
                    
                    # Cập nhật UI sau khi tạo kế hoạch
                    self.display_data(self.current_patient_id)
                    
                except Exception as error:
                    self.logger.error(f"Lỗi khi mở màn hình lập kế hoạch: {str(error)}")
                    messagebox.showerror("Lỗi", f"Không thể mở màn hình lập kế hoạch: {str(error)}")
            
            except Exception as error:
                messagebox.showerror("Lỗi", f"Không thể tạo kế hoạch: {str(error)}")
                self.logger.error(f"Lỗi tạo kế hoạch: {str(error)}")
        
        # Frame chứa các nút
        button_frame = ttk.Frame(plan_dialog)
        button_frame.pack(fill=tk.X, padx=20, pady=15)
        
        ttk.Button(button_frame, text="Hủy", command=plan_dialog.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Tạo kế hoạch", command=save_plan).pack(side=tk.RIGHT, padx=5)

    def copy_plan(self):
        """Sao chép kế hoạch"""
        if not self.current_patient_id:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn bệnh nhân trước")
            return
        
        if not self.current_plan_id:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn kế hoạch cần sao chép")
            return
        
        # Lấy thông tin kế hoạch
        plan_summary = self.session_manager.get_plan_summary(
            patient_id=self.current_patient_id,
            plan_id=self.current_plan_id
        )
        
        if not plan_summary:
            messagebox.showwarning("Cảnh báo", "Không tìm thấy thông tin kế hoạch")
            return
        
        original_plan_name = plan_summary.get("plan_name", "Không rõ tên")
        
        # Tạo dialog để đặt tên mới cho kế hoạch
        copy_dialog = tk.Toplevel(self.root)
        copy_dialog.title("Sao chép kế hoạch")
        copy_dialog.geometry("400x150")
        copy_dialog.resizable(False, False)
        copy_dialog.transient(self.root)
        copy_dialog.grab_set()
        
        # Frame chứa các phần tử
        frame = ttk.Frame(copy_dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Label hiển thị kế hoạch gốc
        ttk.Label(frame, text=f"Kế hoạch gốc: {original_plan_name}").pack(anchor=tk.W, pady=5)
        
        # Entry nhập tên mới
        ttk.Label(frame, text="Tên kế hoạch mới:").pack(anchor=tk.W, pady=5)
        new_name_var = tk.StringVar(value=f"{original_plan_name} - Bản sao")
        ttk.Entry(frame, textvariable=new_name_var, width=40).pack(fill=tk.X, pady=5)
        
        # Frame chứa các nút
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        def do_copy():
            new_plan_name = new_name_var.get().strip()
            if not new_plan_name:
                messagebox.showwarning("Cảnh báo", "Vui lòng nhập tên kế hoạch mới")
                return
            
            try:
                # Thực hiện sao chép kế hoạch
                new_plan_id = self.session_manager.duplicate_plan(
                    patient_id=self.current_patient_id,
                    plan_id=self.current_plan_id,
                    new_plan_name=new_plan_name
                )
                
                if new_plan_id:
                    self.logger.info(f"Đã sao chép kế hoạch từ {self.current_plan_id} sang {new_plan_id}")
                    messagebox.showinfo("Thành công", f"Đã sao chép kế hoạch thành: {new_plan_name}")
                    copy_dialog.destroy()
                    
                    # Cập nhật trạng thái và hiển thị kế hoạch mới
                    self.current_plan_id = new_plan_id
                    # TODO: Cập nhật giao diện hiển thị kế hoạch mới
                    self.display_data(self.current_patient_id)
                    
                    # Hiển thị thông tin kế hoạch mới trong tab kế hoạch
                    if hasattr(self, 'plan_info_frame'):
                        self.update_plan_info(new_plan_id)
                else:
                    messagebox.showerror("Lỗi", "Không thể sao chép kế hoạch. Vui lòng thử lại.")
            except Exception as error:
                self.logger.error(f"Lỗi khi sao chép kế hoạch: {str(error)}")
                messagebox.showerror("Lỗi", f"Không thể sao chép kế hoạch: {str(error)}")
        
        ttk.Button(button_frame, text="Hủy", command=copy_dialog.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Sao chép", command=do_copy).pack(side=tk.RIGHT, padx=5)

    def delete_plan(self):
        """Xóa kế hoạch"""
        if not self.current_patient_id:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn bệnh nhân trước")
            return
        
        if not self.current_plan_id:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn kế hoạch cần xóa")
            return
        
        # Lấy thông tin kế hoạch
        plan_summary = self.session_manager.get_plan_summary(
            patient_id=self.current_patient_id,
            plan_id=self.current_plan_id
        )
        
        if not plan_summary:
            messagebox.showwarning("Cảnh báo", "Không tìm thấy thông tin kế hoạch")
            return
        
        plan_name = plan_summary.get("plan_name", "Không rõ tên")
        
        # Xác nhận xóa
        confirm = messagebox.askyesno(
            "Xác nhận xóa", 
            f"Bạn có chắc chắn muốn xóa kế hoạch '{plan_name}'?\n\n"
            "Dữ liệu kế hoạch sẽ bị xóa vĩnh viễn và không thể khôi phục.",
            icon="warning"
        )
        
        if not confirm:
            return
        
        # Tiến hành xóa
        success = self.session_manager.delete_plan(
            patient_id=self.current_patient_id,
            plan_id=self.current_plan_id
        )
        
        if success:
            self.logger.info(f"Đã xóa kế hoạch: {self.current_plan_id} - {plan_name}")
            messagebox.showinfo("Thành công", f"Đã xóa kế hoạch: {plan_name}")
            
            # Cập nhật trạng thái
            self.current_plan_id = None
            
            # TODO: Cập nhật giao diện hiển thị kế hoạch
            self.display_data(self.current_patient_id)
            
            # Xóa thông tin kế hoạch hiện tại khỏi giao diện
            if hasattr(self, 'plan_info_frame'):
                for widget in self.plan_info_frame.winfo_children():
                    widget.destroy()
                
                ttk.Label(self.plan_info_frame, text="Chưa chọn kế hoạch", font=('Helvetica', 10, 'italic')).pack(pady=20)
        else:
            self.logger.error(f"Lỗi khi xóa kế hoạch: {self.current_plan_id}")
            messagebox.showerror("Lỗi", f"Không thể xóa kế hoạch: {plan_name}. Vui lòng thử lại sau.")

    def auto_contour(self):
        """Tạo contour tự động cho cấu trúc giải phẫu"""
        if not self.current_patient_id:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn bệnh nhân trước")
            return
        
        # Kiểm tra xem đã tải dữ liệu hình ảnh chưa
        if not hasattr(self, 'current_display') or not self.current_display:
            messagebox.showwarning("Cảnh báo", "Vui lòng tải dữ liệu hình ảnh trước")
            return
        
        try:
            # Tạo cửa sổ dialog
            auto_dialog = tk.Toplevel(self.root)
            auto_dialog.title("Phân đoạn cấu trúc tự động")
            auto_dialog.geometry("500x600")
            auto_dialog.resizable(False, False)
            auto_dialog.transient(self.root)
            auto_dialog.grab_set()
            
            # Tạo frame chứa các phần tử giao diện
            main_frame = ttk.Frame(auto_dialog, padding=10)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Danh sách các cấu trúc có thể tự động phân đoạn
            organ_frame = ttk.LabelFrame(main_frame, text="Chọn cấu trúc cần phân đoạn")
            organ_frame.pack(fill=tk.BOTH, expand=True, pady=10)
            
            # Danh sách cấu trúc giải phẫu
            organs = [
                ("Brain (Não)", "brain"),
                ("Brainstem (Thân não)", "brainstem"),
                ("Spinal Cord (Tủy sống)", "spinal_cord"),
                ("Mandible (Xương hàm)", "mandible"),
                ("Parotid L (Tuyến mang tai trái)", "parotid_l"),
                ("Parotid R (Tuyến mang tai phải)", "parotid_r"),
                ("Eyes (Mắt)", "eyes"),
                ("Lens (Thủy tinh thể)", "lens"),
                ("Optic Nerve (Dây thần kinh thị giác)", "optic_nerve"),
                ("Optic Chiasm (Giao thoa thị giác)", "optic_chiasm"),
                ("Lung L (Phổi trái)", "lung_l"),
                ("Lung R (Phổi phải)", "lung_r"),
                ("Heart (Tim)", "heart"),
                ("Liver (Gan)", "liver"),
                ("Stomach (Dạ dày)", "stomach"),
                ("Kidneys (Thận)", "kidneys"),
                ("Bladder (Bàng quang)", "bladder"),
                ("Rectum (Trực tràng)", "rectum"),
                ("Femur L (Xương đùi trái)", "femur_l"),
                ("Femur R (Xương đùi phải)", "femur_r"),
                ("Body (Đường viền cơ thể)", "body")
            ]
            
            # Tạo frame cuộn cho danh sách cơ quan dài
            scroll_frame = ttk.Frame(organ_frame)
            scroll_frame.pack(fill=tk.BOTH, expand=True)
            
            # Tạo canvas và scrollbar
            canvas = tk.Canvas(scroll_frame)
            scrollbar = ttk.Scrollbar(scroll_frame, orient="vertical", command=canvas.yview)
            scroll_content = ttk.Frame(canvas)
            
            # Cấu hình canvas
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill=tk.Y)
            canvas.create_window((0, 0), window=scroll_content, anchor="nw")
            
            # Biến để lưu các checkbutton
            organ_vars = {}
            
            # Tạo checkbutton cho từng cơ quan
            for i, (organ_name, organ_id) in enumerate(organs):
                var = tk.BooleanVar(value=False)
                organ_vars[organ_id] = var
                ttk.Checkbutton(scroll_content, text=organ_name, variable=var).grid(
                    row=i, column=0, sticky=tk.W, pady=2)
            
            # Cấu hình cuộn
            scroll_content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            
            # Frame chứa các tùy chọn
            options_frame = ttk.LabelFrame(main_frame, text="Tùy chọn phân đoạn")
            options_frame.pack(fill=tk.X, pady=10)
            
            # Tùy chọn mô hình AI
            ttk.Label(options_frame, text="Mô hình AI:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
            model_var = tk.StringVar(value="model_standard")
            ttk.Combobox(options_frame, textvariable=model_var, 
                        values=["model_standard", "model_fast", "model_high_quality"], 
                        state="readonly", width=20).grid(row=0, column=1, pady=5, padx=5)
            
            # Tùy chọn độ chi tiết
            ttk.Label(options_frame, text="Độ chi tiết:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
            detail_var = tk.StringVar(value="medium")
            ttk.Combobox(options_frame, textvariable=detail_var, 
                        values=["low", "medium", "high"], 
                        state="readonly", width=20).grid(row=1, column=1, pady=5, padx=5)
            
            # Thanh tiến trình
            progress_var = tk.DoubleVar()
            progress = ttk.Progressbar(main_frame, orient="horizontal", length=100, mode="determinate", variable=progress_var)
            progress.pack(fill=tk.X, pady=10)
            progress_var.set(0)
            
            # Label hiển thị trạng thái
            status_var = tk.StringVar(value="Sẵn sàng phân đoạn tự động")
            status_label = ttk.Label(main_frame, textvariable=status_var)
            status_label.pack(pady=5)
            
            # Hàm thực hiện phân đoạn tự động
            def run_auto_segmentation():
                # Lấy danh sách các cơ quan được chọn
                selected_organs = [organ_id for organ_id, var in organ_vars.items() if var.get()]
                
                if not selected_organs:
                    messagebox.showwarning("Cảnh báo", "Vui lòng chọn ít nhất một cấu trúc để phân đoạn")
                    return
                
                # Cập nhật UI
                status_var.set("Đang phân đoạn... Vui lòng đợi")
                progress_var.set(0)
                auto_dialog.update()
                
                try:
                    # Mô phỏng quá trình phân đoạn
                    # Trong thực tế, đây sẽ là cuộc gọi đến module AI để phân đoạn
                    total_organs = len(selected_organs)
                    
                    for i, organ_id in enumerate(selected_organs):
                        # Cập nhật tiến độ
                        progress_var.set((i / total_organs) * 100)
                        status_var.set(f"Đang phân đoạn {organs[next(j for j, (_, oid) in enumerate(organs) if oid == organ_id)][0]}...")
                        auto_dialog.update()
                        
                        # Mô phỏng thời gian xử lý
                        import time
                        time.sleep(0.5)  # Trong ứng dụng thực, đây sẽ là thời gian để AI xử lý
                        
                        # TODO: Tích hợp với ContourTools để tạo contour thật
                        # Trong ứng dụng thực, đây sẽ là các đường viền do AI tạo ra
                        try:
                            # Tạo contour giả lập cho mục đích demo
                            from quangstation.contouring.contour_tools import ContourTools
                            
                            # Lấy dữ liệu hình ảnh
                            image_data = self.session_manager.get_image_data(self.current_patient_id, self.current_plan_id)
                            
                            if image_data is not None:
                                # Tạo đối tượng ContourTools
                                contour_tools = self.session_manager.get_contour_tools()
                                
                                if contour_tools is None:
                                    # Tạo mới nếu chưa có
                                    contour_tools = ContourTools(image_data)
                                    self.session_manager.set_contour_tools(contour_tools)
                                
                                # Tạo contour cho cấu trúc
                                contour_tools.add_structure(organs[next(j for j, (_, oid) in enumerate(organs) if oid == organ_id)][0])
                                
                                # Lưu contour vào session
                                self.session_manager.save_contours()
                        except Exception as contour_error:
                            self.logger.error(f"Lỗi khi tạo contour: {str(contour_error)}")
                    
                    # Hoàn thành
                    progress_var.set(100)
                    status_var.set("Phân đoạn hoàn tất!")
                    messagebox.showinfo("Thành công", f"Đã phân đoạn {total_organs} cấu trúc thành công")
                    auto_dialog.destroy()
                    
                    # Ghi log
                    self.logger.info(f"Đã phân đoạn tự động {total_organs} cấu trúc")
                    
                except Exception as error:
                    status_var.set(f"Lỗi: {str(error)}")
                    self.logger.error(f"Lỗi khi phân đoạn tự động: {str(error)}")
                    messagebox.showerror("Lỗi", f"Không thể phân đoạn tự động: {str(error)}")
            
            # Frame chứa các nút
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=10)
            
            ttk.Button(button_frame, text="Hủy", command=auto_dialog.destroy).pack(side=tk.RIGHT, padx=5)
            ttk.Button(button_frame, text="Bắt đầu phân đoạn", command=run_auto_segmentation).pack(side=tk.RIGHT, padx=5)
            
        except Exception as error:
            self.logger.error(f"Lỗi khi mở công cụ phân đoạn tự động: {str(error)}")
            messagebox.showerror("Lỗi", f"Không thể mở công cụ phân đoạn tự động: {str(error)}")

    def calculate_dose(self):
        """Tính toán phân bố liều xạ trị"""
        if not self.current_patient_id:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn bệnh nhân trước")
            return
        
        if not self.current_plan_id:
            messagebox.showwarning("Cảnh báo", "Vui lòng tạo hoặc chọn kế hoạch trước")
            return
        
        try:
            # Tạo cửa sổ dialog cho tính toán liều
            dose_dialog = tk.Toplevel(self.root)
            dose_dialog.title("Tính toán liều xạ trị")
            dose_dialog.geometry("550x450")
            dose_dialog.resizable(False, False)
            dose_dialog.transient(self.root)
            dose_dialog.grab_set()
            
            # Tạo frame chứa các phần tử giao diện
            main_frame = ttk.Frame(dose_dialog, padding=15)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Tiêu đề
            ttk.Label(main_frame, text="Thiết lập tính toán liều", font=('Helvetica', 12, 'bold')).pack(pady=10)
            
            # Frame chứa các tùy chọn tính toán
            options_frame = ttk.LabelFrame(main_frame, text="Tùy chọn tính toán")
            options_frame.pack(fill=tk.BOTH, expand=True, pady=10)
            
            # Grid cho các tùy chọn
            option_grid = ttk.Frame(options_frame)
            option_grid.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Thuật toán tính liều
            ttk.Label(option_grid, text="Thuật toán:").grid(row=0, column=0, sticky=tk.W, pady=5)
            algorithm_var = tk.StringVar(value="CCC")
            ttk.Combobox(option_grid, textvariable=algorithm_var, 
                         values=["CCC", "AxB", "AAA", "Monte Carlo"], 
                         state="readonly", width=20).grid(row=0, column=1, sticky=tk.W, pady=5)
            
            # Độ phân giải lưới liều
            ttk.Label(option_grid, text="Độ phân giải lưới liều (mm):").grid(row=1, column=0, sticky=tk.W, pady=5)
            grid_size_var = tk.DoubleVar(value=2.5)
            ttk.Combobox(option_grid, textvariable=grid_size_var, 
                         values=[1.0, 2.0, 2.5, 3.0, 5.0], 
                         width=10).grid(row=1, column=1, sticky=tk.W, pady=5)
            
            # Tính liều ngoài điểm quan tâm
            ttk.Label(option_grid, text="Tính liều ngoài ROI:").grid(row=2, column=0, sticky=tk.W, pady=5)
            outside_roi_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(option_grid, variable=outside_roi_var).grid(row=2, column=1, sticky=tk.W, pady=5)
            
            # Độ chính xác
            ttk.Label(option_grid, text="Độ chính xác:").grid(row=3, column=0, sticky=tk.W, pady=5)
            accuracy_var = tk.StringVar(value="standard")
            ttk.Combobox(option_grid, textvariable=accuracy_var, 
                         values=["low", "standard", "high"], 
                         state="readonly", width=15).grid(row=3, column=1, sticky=tk.W, pady=5)
            
            # Số lượng thread
            ttk.Label(option_grid, text="Số lượng thread CPU:").grid(row=4, column=0, sticky=tk.W, pady=5)
            thread_var = tk.IntVar(value=4)
            thread_spinner = ttk.Spinbox(option_grid, from_=1, to=16, textvariable=thread_var, width=5)
            thread_spinner.grid(row=4, column=1, sticky=tk.W, pady=5)
            
            # Sử dụng GPU
            ttk.Label(option_grid, text="Sử dụng GPU (nếu có):").grid(row=5, column=0, sticky=tk.W, pady=5)
            gpu_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(option_grid, variable=gpu_var).grid(row=5, column=1, sticky=tk.W, pady=5)
            
            # Thiết bị GPU
            ttk.Label(option_grid, text="Thiết bị GPU:").grid(row=6, column=0, sticky=tk.W, pady=5)
            device_var = tk.StringVar(value="auto")
            ttk.Combobox(option_grid, textvariable=device_var, 
                         values=["auto", "cuda:0", "cuda:1"], 
                         width=10).grid(row=6, column=1, sticky=tk.W, pady=5)
            
            # Thông tin ước tính
            info_frame = ttk.LabelFrame(main_frame, text="Thông tin ước tính")
            info_frame.pack(fill=tk.X, pady=10)
            
            ttk.Label(info_frame, text="Ước tính thời gian tính toán:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
            ttk.Label(info_frame, text="~2-5 phút").grid(row=0, column=1, sticky=tk.W, padx=10, pady=5)
            
            ttk.Label(info_frame, text="Dung lượng bộ nhớ cần thiết:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
            ttk.Label(info_frame, text="~1.2 GB").grid(row=1, column=1, sticky=tk.W, padx=10, pady=5)
            
            # Thanh tiến trình
            progress_frame = ttk.Frame(main_frame)
            progress_frame.pack(fill=tk.X, pady=10)
            
            progress_var = tk.DoubleVar(value=0)
            progress = ttk.Progressbar(progress_frame, orient="horizontal", 
                                      length=100, mode="determinate", 
                                      variable=progress_var)
            progress.pack(fill=tk.X)
            
            # Label hiển thị trạng thái
            status_var = tk.StringVar(value="Sẵn sàng tính toán")
            status_label = ttk.Label(progress_frame, textvariable=status_var)
            status_label.pack(anchor=tk.W, pady=5)
            
            # Hàm thực hiện tính toán liều
            def run_dose_calculation():
                # Lấy các tùy chọn tính toán
                algorithm = algorithm_var.get()
                grid_size = grid_size_var.get()
                outside_roi = outside_roi_var.get()
                accuracy = accuracy_var.get()
                num_threads = thread_var.get()
                use_gpu = gpu_var.get()
                device = device_var.get()
                
                # Cập nhật trạng thái
                status_var.set("Đang chuẩn bị tính toán...")
                progress_var.set(5)
                dose_dialog.update()
                
                try:
                    # TODO: Tích hợp với module tính liều thực tế
                    # Mô phỏng quá trình tính toán
                    
                    # Tích hợp với module tính liều thực
                    from quangstation.dose_calculation.dose_calculator import DoseCalculator
                    
                    # Lấy dữ liệu cần thiết
                    image_data = self.session_manager.get_image_data(self.current_patient_id, self.current_plan_id)
                    structures = self.session_manager.get_structure_data(self.current_patient_id, self.current_plan_id)
                    plan_config = self.session_manager.get_plan_config(self.current_patient_id, self.current_plan_id)
                    
                    if image_data is not None and structures is not None and plan_config is not None:
                        # Tạo đối tượng tính liều
                        calculator = DoseCalculator(algorithm=algorithm)
                        
                        # Thiết lập dữ liệu đầu vào
                        calculator.set_image_data(image_data)
                        calculator.set_structures(structures)
                        calculator.set_plan_config(plan_config)
                    
                    # Mô phỏng các bước tính liều
                    steps = [
                        ("Đang tải dữ liệu CT...", 5, 10),
                        ("Đang chuẩn bị hình học mô giả...", 10, 25),
                        ("Đang tính toán liều chùm tia 1/3...", 25, 40),
                        ("Đang tính toán liều chùm tia 2/3...", 40, 60),
                        ("Đang tính toán liều chùm tia 3/3...", 60, 80),
                        ("Đang tính tổng liều...", 80, 90),
                        ("Đang lưu kết quả...", 90, 100)
                    ]
                    
                    # Mô phỏng tiến trình tính toán
                    import time
                    for step_text, start_progress, end_progress in steps:
                        status_var.set(step_text)
                        for i in range(start_progress, end_progress):
                            progress_var.set(i)
                            dose_dialog.update()
                            time.sleep(0.05)  # Mô phỏng thời gian xử lý
                    
                    # Hoàn thành tính toán
                    progress_var.set(100)
                    status_var.set("Tính toán hoàn tất!")
                    
                    # Hiển thị thông báo thành công
                    messagebox.showinfo("Thành công", "Đã tính toán liều xạ trị thành công.")
                    
                    # Lưu kết quả vào session
                    import numpy as np
                    dose_data = np.random.rand(100, 100, 100) * 70  # Tạo dữ liệu giả
                    dose_metadata = {
                        "algorithm": algorithm,
                        "grid_size": grid_size,
                        "calculation_time": "00:02:34",
                        "calculation_date": datetime.now().isoformat()
                    }
                    
                    # Lưu vào session
                    self.session_manager.save_dose_calculation(
                        dose_data=dose_data,
                        dose_metadata=dose_metadata
                    )
                    
                    # Ghi log
                    self.logger.info(f"Đã tính toán liều thành công với thuật toán {algorithm}")
                    
                    # Đóng dialog
                    dose_dialog.destroy()
                    
                    # TODO: Cập nhật giao diện hiển thị liều
                    self.update_dose_display()
                    
                    # Hiển thị DVH nếu có
                    if hasattr(self, 'dvh_view') and self.dvh_view:
                        self.dvh_view.update_dvh()
                    
                    # Hiển thị thông báo thành công
                    messagebox.showinfo("Thành công", "Đã tính toán liều thành công!")
                    
                except Exception as error:
                    status_var.set(f"Lỗi: {str(error)}")
                    self.logger.error(f"Lỗi khi tính toán liều: {str(error)}")
                    messagebox.showerror("Lỗi", f"Không thể tính toán liều: {str(error)}")
            
            # Frame chứa các nút
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=10)
            
            ttk.Button(button_frame, text="Hủy", command=dose_dialog.destroy).pack(side=tk.RIGHT, padx=5)
            ttk.Button(button_frame, text="Bắt đầu tính toán", command=run_dose_calculation).pack(side=tk.RIGHT, padx=5)
            
        except Exception as error:
            self.logger.error(f"Lỗi khi mở công cụ tính toán liều: {str(error)}")
            messagebox.showerror("Lỗi", f"Không thể mở công cụ tính toán liều: {str(error)}")

    def optimize_plan(self):
        """Tối ưu hóa kế hoạch xạ trị"""
        if not self.current_patient_id or not self.current_plan_id:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn bệnh nhân và kế hoạch trước khi tối ưu hóa")
            return
            
        # Kiểm tra xem kế hoạch đã có dữ liệu liều chưa
        plan_data = self.patient_manager.get_plan_details(self.current_patient_id, self.current_plan_id)
        if not plan_data:
            messagebox.showerror("Lỗi", "Không tìm thấy thông tin kế hoạch")
            return
            
        # Kiểm tra xem đã tính liều chưa
        if not self.session_manager.has_dose_calculation(self.current_patient_id, self.current_plan_id):
            if not messagebox.askyesno("Cảnh báo", 
                                    "Chưa có dữ liệu liều cho kế hoạch này. Bạn cần tính liều trước khi tối ưu hóa.\n\nBạn có muốn tính liều ngay bây giờ không?"):
                return
            # Tính liều trước
            self.calculate_dose()
            return
        
        # Tạo dialog tối ưu hóa
        try:
            self.logger.info(f"Mở công cụ tối ưu hóa kế hoạch {self.current_plan_id}")
            
            optimization_dialog = tk.Toplevel(self.root)
            optimization_dialog.title("Tối ưu hóa kế hoạch xạ trị")
            optimization_dialog.geometry("700x600")
            optimization_dialog.transient(self.root)
            optimization_dialog.grab_set()
            
            # Khung trên
            top_frame = ttk.Frame(optimization_dialog)
            top_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Thông tin kế hoạch
            plan_name = plan_data.get("name", "Không có tên")
            ttk.Label(top_frame, text=f"Kế hoạch: {plan_name}", font=('Helvetica', 12, 'bold')).pack(side=tk.LEFT)
            
            # Khung giữa
            middle_frame = ttk.Frame(optimization_dialog)
            middle_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            # Notebook chứa các tab
            nb = ttk.Notebook(middle_frame)
            nb.pack(fill=tk.BOTH, expand=True)
            
            # Tab 1: Mục tiêu
            objectives_tab = ttk.Frame(nb)
            nb.add(objectives_tab, text="Mục tiêu")
            
            # Danh sách các cấu trúc
            structures_frame = ttk.LabelFrame(objectives_tab, text="Cấu trúc")
            structures_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
            
            # Danh sách các cấu trúc có sẵn từ contour
            structures = self.session_manager.get_structure_list(self.current_patient_id, self.current_plan_id)
            
            # Treeview hiển thị cấu trúc
            tree_structures = ttk.Treeview(structures_frame, columns=("name", "type"), show="headings", height=15)
            tree_structures.heading("name", text="Tên")
            tree_structures.heading("type", text="Loại")
            tree_structures.column("name", width=120)
            tree_structures.column("type", width=80)
            
            # Thêm các cấu trúc vào treeview
            for struct in structures:
                struct_name = struct.get("name", "Không tên")
                struct_type = struct.get("type", "Unknown")
                tree_structures.insert("", tk.END, values=(struct_name, struct_type))
                
            tree_structures.pack(fill=tk.BOTH, expand=True)
            
            # Khung mục tiêu
            objectives_frame = ttk.LabelFrame(objectives_tab, text="Mục tiêu tối ưu")
            objectives_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Treeview hiển thị mục tiêu
            tree_objectives = ttk.Treeview(objectives_frame, 
                                         columns=("structure", "type", "value", "weight"), 
                                         show="headings", 
                                         height=10)
            tree_objectives.heading("structure", text="Cấu trúc")
            tree_objectives.heading("type", text="Loại ràng buộc")
            tree_objectives.heading("value", text="Giá trị")
            tree_objectives.heading("weight", text="Trọng số")
            
            tree_objectives.column("structure", width=120)
            tree_objectives.column("type", width=100)
            tree_objectives.column("value", width=80)
            tree_objectives.column("weight", width=80)
            
            tree_objectives.pack(fill=tk.BOTH, expand=True, pady=5)
            
            # Frame các nút điều khiển
            obj_buttons_frame = ttk.Frame(objectives_frame)
            obj_buttons_frame.pack(fill=tk.X, pady=5)
            
            # Nút thêm, sửa, xóa mục tiêu
            ttk.Button(obj_buttons_frame, text="Thêm", 
                      command=lambda: self._add_objective(tree_objectives, tree_structures)).pack(side=tk.LEFT, padx=5)
            ttk.Button(obj_buttons_frame, text="Sửa", 
                      command=lambda: self._edit_objective(tree_objectives)).pack(side=tk.LEFT, padx=5)
            ttk.Button(obj_buttons_frame, text="Xóa", 
                      command=lambda: self._delete_objective(tree_objectives)).pack(side=tk.LEFT, padx=5)
            
            # Tab 2: Cài đặt tối ưu
            settings_tab = ttk.Frame(nb)
            nb.add(settings_tab, text="Cài đặt")
            
            # Frame thông số
            settings_frame = ttk.LabelFrame(settings_tab, text="Thông số tối ưu hóa")
            settings_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Chọn thuật toán tối ưu
            ttk.Label(settings_frame, text="Thuật toán:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
            algorithm_var = tk.StringVar(value="IPOPT")
            ttk.Combobox(settings_frame, textvariable=algorithm_var, 
                        values=["IPOPT", "Gradient Descent", "L-BFGS", "Simulated Annealing"], 
                        width=20, state="readonly").grid(row=0, column=1, sticky=tk.W, pady=5)
            
            # Số vòng lặp tối đa
            ttk.Label(settings_frame, text="Số vòng lặp tối đa:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
            max_iterations_var = tk.IntVar(value=100)
            ttk.Spinbox(settings_frame, from_=10, to=1000, increment=10, 
                       textvariable=max_iterations_var, width=10).grid(row=1, column=1, sticky=tk.W, pady=5)
            
            # Dung sai hội tụ
            ttk.Label(settings_frame, text="Dung sai hội tụ:").grid(row=2, column=0, sticky=tk.W, pady=5, padx=5)
            tolerance_var = tk.DoubleVar(value=0.001)
            ttk.Spinbox(settings_frame, from_=0.0001, to=0.1, increment=0.001, 
                       textvariable=tolerance_var, width=10).grid(row=2, column=1, sticky=tk.W, pady=5)
            
            # Thời gian tối đa (phút)
            ttk.Label(settings_frame, text="Thời gian tối đa (phút):").grid(row=3, column=0, sticky=tk.W, pady=5, padx=5)
            max_time_var = tk.IntVar(value=30)
            ttk.Spinbox(settings_frame, from_=1, to=180, increment=5, 
                       textvariable=max_time_var, width=10).grid(row=3, column=1, sticky=tk.W, pady=5)
            
            # Ô chữ nhật hiển thị thông tin
            ttk.Separator(settings_frame, orient=tk.HORIZONTAL).grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=10)
            
            ttk.Label(settings_frame, text="Thông tin thêm:", font=('Helvetica', 10, 'bold')).grid(
                row=5, column=0, columnspan=2, sticky=tk.W, pady=5, padx=5)
            
            info_text = tk.Text(settings_frame, height=8, width=50, wrap=tk.WORD)
            info_text.grid(row=6, column=0, columnspan=2, sticky=tk.NSEW, padx=5, pady=5)
            info_text.insert(tk.END, "Quá trình tối ưu hóa sẽ sử dụng thuật toán tối ưu phi tuyến để tìm " +
                           "phân bố liều tối ưu thỏa mãn các ràng buộc và mục tiêu đã đặt ra.\n\n" +
                           "Thời gian chạy phụ thuộc vào kích thước vấn đề và số lượng mục tiêu.")
            info_text.config(state=tk.DISABLED)
            
            # Thanh trạng thái
            status_var = tk.StringVar(value="Sẵn sàng tối ưu hóa")
            status_bar = ttk.Label(optimization_dialog, textvariable=status_var, relief=tk.SUNKEN, anchor=tk.W)
            status_bar.pack(side=tk.BOTTOM, fill=tk.X)
            
            # Khung dưới - nút điều khiển
            bottom_frame = ttk.Frame(optimization_dialog)
            bottom_frame.pack(fill=tk.X, padx=10, pady=10)
            
            # Nút thực hiện và hủy
            ttk.Button(bottom_frame, text="Hủy", 
                      command=optimization_dialog.destroy).pack(side=tk.RIGHT, padx=5)
            
            def run_optimization():
                # Thu thập thông tin mục tiêu tối ưu
                objectives = []
                for item_id in tree_objectives.get_children():
                    item = tree_objectives.item(item_id)
                    values = item["values"]
                    if len(values) >= 4:
                        objective = {
                            "structure": values[0],
                            "type": values[1],
                            "value": float(values[2]),
                            "weight": float(values[3])
                        }
                        objectives.append(objective)
                
                if not objectives:
                    messagebox.showwarning("Cảnh báo", "Vui lòng thêm ít nhất một mục tiêu tối ưu")
                    return
                
                # Thu thập thông số tối ưu
                settings = {
                    "algorithm": algorithm_var.get(),
                    "max_iterations": max_iterations_var.get(),
                    "tolerance": tolerance_var.get(),
                    "max_time": max_time_var.get()
                }
                
                # Cập nhật trạng thái
                status_var.set("Đang tối ưu hóa... Vui lòng đợi")
                
                try:
                    # Vô hiệu hóa nút tối ưu để tránh gọi nhiều lần
                    optimize_button.configure(state=tk.DISABLED)
                    optimization_dialog.update()
                    
                    # Lấy dữ liệu liều và cấu trúc hiện tại
                    dose_data = self.session_manager.get_dose_data(self.current_patient_id, self.current_plan_id)
                    structure_data = self.session_manager.get_structure_data(self.current_patient_id, self.current_plan_id)
                    
                    if not dose_data or not structure_data:
                        messagebox.showerror("Lỗi", "Không thể lấy dữ liệu liều hoặc cấu trúc")
                        optimize_button.configure(state=tk.NORMAL)
                        status_var.set("Tối ưu hóa thất bại")
                        return
                    
                    # Tạo đối tượng tối ưu hóa
                    from quangstation.optimization.plan_optimizer import PlanOptimizer
                    optimizer = PlanOptimizer()
                    
                    # Cập nhật thông số
                    optimizer.set_settings(settings)
                    
                    # Thêm các mục tiêu
                    for obj in objectives:
                        optimizer.add_objective(
                            structure_name=obj["structure"],
                            objective_type=obj["type"],
                            value=obj["value"],
                            weight=obj["weight"]
                        )
                    
                    # Thực hiện tối ưu hóa
                    self.logger.info(f"Bắt đầu tối ưu hóa kế hoạch {self.current_plan_id}")
                    result = optimizer.optimize(
                        patient_id=self.current_patient_id,
                        plan_id=self.current_plan_id,
                        dose_data=dose_data,
                        structure_data=structure_data
                    )
                    
                    if result["success"]:
                        # Cập nhật kế hoạch với kết quả tối ưu
                        self.session_manager.update_plan_optimization(
                            patient_id=self.current_patient_id,
                            plan_id=self.current_plan_id,
                            optimization_result=result
                        )
                        
                        # Cập nhật hiển thị
                        self.update_dose_display()
                        
                        # Hiển thị thông báo thành công
                        messagebox.showinfo("Thành công", 
                                          f"Tối ưu hóa kế hoạch hoàn tất.\n\n"
                                          f"Giá trị mục tiêu ban đầu: {result.get('initial_objective', 'N/A')}\n"
                                          f"Giá trị mục tiêu sau tối ưu: {result.get('final_objective', 'N/A')}\n"
                                          f"Số vòng lặp: {result.get('iterations', 'N/A')}")
                        
                        # Đóng dialog
                        optimization_dialog.destroy()
                    else:
                        # Hiển thị lỗi
                        error_msg = result.get("message", "Lỗi không xác định")
                        messagebox.showerror("Lỗi tối ưu hóa", f"Tối ưu hóa thất bại: {error_msg}")
                        status_var.set("Tối ưu hóa thất bại")
                        optimize_button.configure(state=tk.NORMAL)
                
                except Exception as e:
                    # Xử lý lỗi
                    self.logger.error(f"Lỗi khi thực hiện tối ưu hóa: {str(e)}")
                    messagebox.showerror("Lỗi", f"Tối ưu hóa thất bại: {str(e)}")
                    status_var.set("Tối ưu hóa thất bại")
                    optimize_button.configure(state=tk.NORMAL)
            
            # Nút tối ưu hóa
            optimize_button = ttk.Button(bottom_frame, text="Tối ưu hóa", command=run_optimization)
            optimize_button.pack(side=tk.RIGHT, padx=5)
            
        except Exception as error:
            self.logger.error(f"Lỗi khi mở công cụ tối ưu hóa: {str(error)}")
            messagebox.showerror("Lỗi", f"Không thể mở công cụ tối ưu hóa: {str(error)}")
    
    def _add_objective(self, tree_objectives, tree_structures):
        """Thêm mục tiêu tối ưu"""
        # Kiểm tra xem đã chọn cấu trúc chưa
        selection = tree_structures.selection()
        if not selection:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một cấu trúc")
            return
            
        # Lấy thông tin cấu trúc đã chọn
        item = tree_structures.item(selection[0])
        struct_name = item['values'][0] if item['values'] else "Không tên"
        
        # Tạo dialog nhập thông tin mục tiêu
        obj_dialog = tk.Toplevel()
        obj_dialog.title("Thêm mục tiêu")
        obj_dialog.geometry("400x250")
        obj_dialog.transient(self.root)
        obj_dialog.grab_set()
        
        # Tạo các phần tử giao diện
        ttk.Label(obj_dialog, text=f"Cấu trúc: {struct_name}").grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=10, pady=5)
        
        # Loại ràng buộc
        ttk.Label(obj_dialog, text="Loại ràng buộc:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        constraint_var = tk.StringVar(value="Max Dose")
        
        # Danh sách các loại ràng buộc phụ thuộc vào loại cấu trúc
        struct_type = item['values'][1] if len(item['values']) > 1 else "Unknown"
        
        if struct_type.lower() in ["ptv", "target", "gtv", "ctv"]:
            constraints = ["Min Dose", "Max Dose", "Mean Dose", "Dose Coverage", "Conformity", "Homogeneity"]
        else:  # OAR
            constraints = ["Max Dose", "Mean Dose", "Max DVH", "Dose Volume"]
            
        ttk.Combobox(obj_dialog, textvariable=constraint_var, 
                    values=constraints, 
                    width=15, state="readonly").grid(row=1, column=1, sticky=tk.W, padx=10, pady=5)
        
        # Giá trị
        ttk.Label(obj_dialog, text="Giá trị:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        value_var = tk.DoubleVar(value=50.0)
        ttk.Spinbox(obj_dialog, from_=0, to=100, increment=0.5, 
                   textvariable=value_var, width=10).grid(row=2, column=1, sticky=tk.W, padx=10, pady=5)
        
        # Đơn vị
        ttk.Label(obj_dialog, text="Đơn vị:").grid(row=3, column=0, sticky=tk.W, padx=10, pady=5)
        unit_var = tk.StringVar(value="Gy")
        ttk.Combobox(obj_dialog, textvariable=unit_var, 
                    values=["Gy", "%"], 
                    width=10, state="readonly").grid(row=3, column=1, sticky=tk.W, padx=10, pady=5)
        
        # Trọng số
        ttk.Label(obj_dialog, text="Trọng số:").grid(row=4, column=0, sticky=tk.W, padx=10, pady=5)
        weight_var = tk.DoubleVar(value=1.0)
        ttk.Spinbox(obj_dialog, from_=0.1, to=100, increment=0.1, 
                   textvariable=weight_var, width=10).grid(row=4, column=1, sticky=tk.W, padx=10, pady=5)
        
        # Nút lưu
        def save_objective():
            # Thêm mục tiêu vào treeview
            tree_objectives.insert("", tk.END, values=(
                struct_name,
                constraint_var.get(),
                value_var.get(),
                weight_var.get()
            ))
            obj_dialog.destroy()
            
        ttk.Button(obj_dialog, text="Hủy", command=obj_dialog.destroy).grid(row=5, column=0, padx=10, pady=10)
        ttk.Button(obj_dialog, text="Lưu", command=save_objective).grid(row=5, column=1, padx=10, pady=10)
    
    def _edit_objective(self, tree_objectives):
        """Chỉnh sửa mục tiêu tối ưu"""
        # Kiểm tra xem đã chọn mục tiêu chưa
        selection = tree_objectives.selection()
        if not selection:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một mục tiêu để chỉnh sửa")
            return
            
        # Lấy thông tin mục tiêu đã chọn
        item = tree_objectives.item(selection[0])
        struct_name = item['values'][0] if item['values'] else "Không tên"
        constraint_type = item['values'][1] if len(item['values']) > 1 else "Max Dose"
        value = item['values'][2] if len(item['values']) > 2 else 50.0
        weight = item['values'][3] if len(item['values']) > 3 else 1.0
        
        # Tạo dialog chỉnh sửa
        edit_dialog = tk.Toplevel()
        edit_dialog.title("Chỉnh sửa mục tiêu")
        edit_dialog.geometry("400x250")
        edit_dialog.transient(self.root)
        edit_dialog.grab_set()
        
        # Tạo các phần tử giao diện
        ttk.Label(edit_dialog, text=f"Cấu trúc: {struct_name}").grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=10, pady=5)
        
        # Loại ràng buộc
        ttk.Label(edit_dialog, text="Loại ràng buộc:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        constraint_var = tk.StringVar(value=constraint_type)
        
        # Cần xác định loại cấu trúc để hiển thị danh sách ràng buộc phù hợp
        # Giả định cấu trúc dựa trên tên
        if any(target_type in struct_name.lower() for target_type in ["ptv", "target", "gtv", "ctv"]):
            constraints = ["Min Dose", "Max Dose", "Mean Dose", "Dose Coverage", "Conformity", "Homogeneity"]
        else:  # OAR
            constraints = ["Max Dose", "Mean Dose", "Max DVH", "Dose Volume"]
            
        ttk.Combobox(edit_dialog, textvariable=constraint_var, 
                    values=constraints, 
                    width=15, state="readonly").grid(row=1, column=1, sticky=tk.W, padx=10, pady=5)
        
        # Giá trị
        ttk.Label(edit_dialog, text="Giá trị:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        value_var = tk.DoubleVar(value=float(value))
        ttk.Spinbox(edit_dialog, from_=0, to=100, increment=0.5, 
                   textvariable=value_var, width=10).grid(row=2, column=1, sticky=tk.W, padx=10, pady=5)
        
        # Đơn vị
        ttk.Label(edit_dialog, text="Đơn vị:").grid(row=3, column=0, sticky=tk.W, padx=10, pady=5)
        unit_var = tk.StringVar(value="Gy")
        ttk.Combobox(edit_dialog, textvariable=unit_var, 
                    values=["Gy", "%"], 
                    width=10, state="readonly").grid(row=3, column=1, sticky=tk.W, padx=10, pady=5)
        
        # Trọng số
        ttk.Label(edit_dialog, text="Trọng số:").grid(row=4, column=0, sticky=tk.W, padx=10, pady=5)
        weight_var = tk.DoubleVar(value=float(weight))
        ttk.Spinbox(edit_dialog, from_=0.1, to=100, increment=0.1, 
                   textvariable=weight_var, width=10).grid(row=4, column=1, sticky=tk.W, padx=10, pady=5)
        
        # Nút lưu
        def update_objective():
            # Cập nhật mục tiêu trong treeview
            tree_objectives.item(selection[0], values=(
                struct_name,
                constraint_var.get(),
                value_var.get(),
                weight_var.get()
            ))
            edit_dialog.destroy()
            
        ttk.Button(edit_dialog, text="Hủy", command=edit_dialog.destroy).grid(row=5, column=0, padx=10, pady=10)
        ttk.Button(edit_dialog, text="Lưu", command=update_objective).grid(row=5, column=1, padx=10, pady=10)
    
    def _delete_objective(self, tree_objectives):
        """Xóa mục tiêu tối ưu đã chọn"""
        selection = tree_objectives.selection()
        if not selection:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một mục tiêu để xóa")
            return
            
        if messagebox.askyesno("Xác nhận", "Bạn có chắc chắn muốn xóa mục tiêu này không?"):
            tree_objectives.delete(selection[0])
    
    def update_dose_display(self):
        """Cập nhật hiển thị liều sau khi tính toán hoặc tối ưu hóa"""
        try:
            # Kiểm tra xem có dữ liệu liều không
            if not self.session_manager.has_dose_calculation(self.current_patient_id, self.current_plan_id):
                return
                
            # Lấy dữ liệu liều
            dose_data = self.session_manager.get_dose_data(self.current_patient_id, self.current_plan_id)
            if not dose_data:
                return
                
            # Cập nhật hiển thị liều trong các view
            if hasattr(self, 'axial_view') and self.axial_view:
                self.axial_view.update_dose_display(dose_data)
                
            if hasattr(self, 'sagittal_view') and self.sagittal_view:
                self.sagittal_view.update_dose_display(dose_data)
                
            if hasattr(self, 'coronal_view') and self.coronal_view:
                self.coronal_view.update_dose_display(dose_data)
                
            # Cập nhật hiển thị DVH nếu có
            if hasattr(self, 'dvh_view') and self.dvh_view:
                self.dvh_view.update_dvh()
                
            # Cập nhật thông tin kế hoạch
            self.display_data(self.current_patient_id)
            
            self.logger.info("Đã cập nhật hiển thị liều")
            
        except Exception as e:
            self.logger.error(f"Lỗi khi cập nhật hiển thị liều: {str(e)}")
    
    def create_report(self, output_path):
        """
        Tạo báo cáo kế hoạch xạ trị
        
        Args:
            output_path: Đường dẫn đến file báo cáo xuất ra
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            if not self.current_patient_id or not self.current_plan_id:
                messagebox.showwarning("Cảnh báo", "Vui lòng chọn bệnh nhân và kế hoạch trước khi tạo báo cáo")
                return False
                
            # Lấy thông tin bệnh nhân và kế hoạch
            patient_data = self.patient_manager.get_patient_details(self.current_patient_id)
            plan_data = self.patient_manager.get_plan_details(self.current_patient_id, self.current_plan_id)
            
            if not patient_data or not plan_data:
                messagebox.showerror("Lỗi", "Không thể lấy thông tin bệnh nhân hoặc kế hoạch")
                return False
                
            # Xác định loại báo cáo dựa trên phần mở rộng
            report_type = "pdf"
            if output_path.lower().endswith(".docx"):
                report_type = "docx"
            elif output_path.lower().endswith(".html"):
                report_type = "html"
                
            # Tạo đối tượng báo cáo
            from quangstation.reporting.comprehensive_report import ComprehensiveReport
            
            # Lấy dữ liệu cần thiết
            structure_data = self.session_manager.get_structure_data(self.current_patient_id, self.current_plan_id)
            dose_data = self.session_manager.get_dose_data(self.current_patient_id, self.current_plan_id)
            
            # Tạo báo cáo
            report = ComprehensiveReport(
                patient_info=patient_data,
                plan_info=plan_data,
                structures=structure_data,
                dose_data=dose_data
            )
            
            # Thêm ảnh chụp màn hình nếu có
            screenshots_dir = os.path.join(self.session_manager.workspace_dir, 
                                         self.current_patient_id, 
                                         self.current_plan_id, 
                                         "screenshots")
            
            if os.path.exists(screenshots_dir):
                for file in os.listdir(screenshots_dir):
                    if file.endswith(('.png', '.jpg', '.jpeg')):
                        img_path = os.path.join(screenshots_dir, file)
                        report.add_image(img_path, file.split('.')[0])
            
            # Tạo báo cáo theo định dạng
            if report_type == "pdf":
                report.generate_pdf(output_path)
            elif report_type == "docx":
                report.generate_docx(output_path)
            elif report_type == "html":
                report.generate_html(output_path)
                
            self.logger.info(f"Đã tạo báo cáo: {output_path}")
            messagebox.showinfo("Thành công", f"Đã tạo báo cáo: {output_path}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Lỗi khi tạo báo cáo: {str(e)}")
            messagebox.showerror("Lỗi", f"Không thể tạo báo cáo: {str(e)}")
            return False

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
        self.logger.info("Đã thiết lập các trình xử lý sự kiện")

def main():
    """Hàm chính để khởi động ứng dụng"""
    # Thiết lập bắt ngoại lệ
    setup_exception_logging()
    
    # Ghi log thông tin hệ thống
    log_system_info()
    
    # Tạo cửa sổ chính
    root = tk.Tk()
    
    # Thiết lập kích thước cửa sổ
    window_width = 1280
    window_height = 800
    
    # Lấy kích thước màn hình
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    # Tính toán vị trí để đặt cửa sổ ở giữa màn hình
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    
    # Thiết lập kích thước và vị trí
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    # Thiết lập icon nếu tồn tại
    icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icons", "quangstation.ico")
    if os.path.exists(icon_path):
        try:
            root.iconbitmap(icon_path)
        except:
            pass  # Bỏ qua nếu không thể đặt icon
    
    # Khởi tạo ứng dụng
    app = MainApp(root)
    
    # Khởi động ứng dụng
    root.mainloop()

if __name__ == "__main__":
    main() 