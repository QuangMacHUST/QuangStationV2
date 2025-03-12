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
import numpy as np

# Import các module nội bộ
from quangstation.core.utils.logging import get_logger, setup_exception_logging, log_system_info
from quangstation.core.utils.config import GlobalConfig, get_config
from quangstation.clinical.data_management.patient_db import PatientDatabase, Patient
#from quangstation.clinical.data_management.display import Display
from quangstation.clinical.data_management.import_interface import ImportInterface
from quangstation.clinical.data_management.session_management import SessionManager
from quangstation.clinical.planning.plan_config import PlanConfig
from quangstation.quality.reporting.comprehensive_report import ComprehensiveReport

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
            patient_data = patient.to_dict()
            self.db.update_patient(patient_id, patient_data)
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
            
    def create_plan(self, patient_id: str, plan_data: Dict[str, Any]) -> str:
        """
        Tạo kế hoạch mới cho bệnh nhân
        
        Args:
            patient_id: ID bệnh nhân
            plan_data: Dữ liệu kế hoạch
            
        Returns:
            str: ID của kế hoạch mới tạo
        """
        try:
            # Lấy thông tin bệnh nhân
            patient = self.db.get_patient(patient_id)
            if not patient:
                raise ValueError(f"Không tìm thấy bệnh nhân với ID: {patient_id}")
            
            # Tạo ID kế hoạch mới
            plan_id = plan_data.get('plan_id', str(uuid.uuid4()))
            
            # Thêm thông tin thời gian
            if 'created_date' not in plan_data:
                plan_data['created_date'] = datetime.now().isoformat()
            plan_data['modified_date'] = datetime.now().isoformat()
            
            # Thêm kế hoạch vào bệnh nhân
            patient.add_plan(plan_id, plan_data)
            
            # Lưu thay đổi
            patient_data = patient.to_dict()
            self.db.update_patient(patient_id, patient_data)
            
            self.logger.info(f"Đã tạo kế hoạch mới {plan_id} cho bệnh nhân {patient_id}")
            return plan_id
        except Exception as error:
            self.logger.error(f"Lỗi tạo kế hoạch: {str(error)}")
            raise
            
    def get_patient_plans(self, patient_id: str) -> List[Dict[str, Any]]:
        """
        Lấy danh sách kế hoạch của bệnh nhân
        
        Args:
            patient_id: ID bệnh nhân
            
        Returns:
            List[Dict]: Danh sách kế hoạch
        """
        try:
            # Lấy thông tin bệnh nhân
            patient = self.db.get_patient(patient_id)
            if not patient:
                return []
            
            # Chuyển từ dictionary sang list với plan_id
            plans = []
            for plan_id, plan_data in patient.plans.items():
                plan_with_id = dict(plan_data)
                plan_with_id['plan_id'] = plan_id
                plans.append(plan_with_id)
            
            return plans
        except Exception as error:
            self.logger.error(f"Lỗi lấy danh sách kế hoạch: {str(error)}")
            return []
            
    def update_plan(self, patient_id: str, plan_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Cập nhật thông tin kế hoạch
        
        Args:
            patient_id: ID bệnh nhân
            plan_id: ID kế hoạch
            update_data: Dữ liệu cập nhật
            
        Returns:
            bool: True nếu cập nhật thành công, False nếu không
        """
        try:
            # Lấy thông tin bệnh nhân
            patient = self.db.get_patient(patient_id)
            if not patient:
                return False
            
            # Kiểm tra kế hoạch có tồn tại không
            if plan_id not in patient.plans:
                return False
            
            # Cập nhật dữ liệu
            patient.plans[plan_id].update(update_data)
            patient.plans[plan_id]['modified_date'] = datetime.now().isoformat()
            
            # Lưu thay đổi
            patient_data = patient.to_dict()
            self.db.update_patient(patient_id, patient_data)
            
            self.logger.info(f"Đã cập nhật kế hoạch {plan_id} cho bệnh nhân {patient_id}")
            return True
        except Exception as error:
            self.logger.error(f"Lỗi cập nhật kế hoạch: {str(error)}")
            return False
            
    def delete_plan(self, patient_id: str, plan_id: str) -> bool:
        """
        Xóa kế hoạch
        
        Args:
            patient_id: ID bệnh nhân
            plan_id: ID kế hoạch
            
        Returns:
            bool: True nếu xóa thành công, False nếu không
        """
        try:
            # Lấy thông tin bệnh nhân
            patient = self.db.get_patient(patient_id)
            if not patient:
                return False
            
            # Xóa kế hoạch
            if plan_id in patient.plans:
                del patient.plans[plan_id]
                
                # Lưu thay đổi
                patient_data = patient.to_dict()
                self.db.update_patient(patient_id, patient_data)
                
                self.logger.info(f"Đã xóa kế hoạch {plan_id} của bệnh nhân {patient_id}")
                return True
            
            return False
        except Exception as error:
            self.logger.error(f"Lỗi xóa kế hoạch: {str(error)}")
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
        # Thiết lập cửa sổ chính
        self.root = root
        self.root.title("QuangStation V2 - Hệ thống Lập kế hoạch Xạ trị")
        self.root.geometry("1200x800")
        
        # Thiết lập logger
        self.logger = get_logger("MainApp")
        
        # Tạo status_var
        self.status_var = tk.StringVar()
        self.status_var.set("Sẵn sàng")
        
        # Khởi tạo các thành phần quản lý
        self.patient_manager = PatientManager()
        self.session_manager = SessionManager()
        
        # Khởi tạo Display khi cần, không phải lúc khởi tạo MainApp
        self.display = None  # Sẽ khởi tạo sau khi chọn bệnh nhân
        
        # Khởi tạo ImportInterface với self.root và hàm callback
        self.import_interface = ImportInterface(root=self.root, update_callback=self.update_patient_list)
        
        # Khởi tạo IntegrationManager
        from quangstation.integration import IntegrationManager
        self.integration_manager = IntegrationManager()
        
        # Dữ liệu hiện tại
        self.current_patient_id = None
        self.current_plan_id = None
        
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
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tạo panedwindow để phân chia màn hình
        self.main_pane = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True)
        
        # Frame bên trái: danh sách bệnh nhân
        self.patient_frame = ttk.Frame(self.main_pane, width=300)
        self.main_pane.add(self.patient_frame, weight=1)
        
        # Frame bên phải: hiển thị dữ liệu
        self.display_frame = ttk.Frame(self.main_pane)
        self.main_pane.add(self.display_frame, weight=3)
        
        # Tạo danh sách bệnh nhân
        self.create_patient_list()
        
        # Tạo vùng hiển thị thông tin bệnh nhân
        self.patient_info_label = ttk.Label(self.display_frame, text="Chưa chọn bệnh nhân", font=('Helvetica', 14, 'bold'))
        self.patient_info_label.pack(anchor=tk.W, pady=10)
        
        # Tạo các tab cho hiển thị
        self.display_notebook = ttk.Notebook(self.display_frame)
        self.display_notebook.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Tab xem hình ảnh (MPR)
        self.image_tab = ttk.Frame(self.display_notebook)
        self.display_notebook.add(self.image_tab, text="Hình ảnh")
        
        # Tạo MPR viewer
        try:
            from quangstation.gui.widgets.mpr_viewer import MPRViewer
            self.mpr_view = MPRViewer(self.image_tab)
            self.mpr_view.pack(fill=tk.BOTH, expand=True)
        except Exception as e:
            self.logger.error(f"Không thể tạo MPR viewer: {e}")
            ttk.Label(self.image_tab, text="Không thể tạo MPR viewer").pack(pady=50)
            self.mpr_view = None
        
        # Tab xem DVH
        self.dvh_tab = ttk.Frame(self.display_notebook)
        self.display_notebook.add(self.dvh_tab, text="DVH")
        
        # Tạo DVH viewer
        try:
            from quangstation.gui.widgets.dvh_viewer import DVHViewer
            self.dvh_view = DVHViewer(self.dvh_tab)
            self.dvh_view.pack(fill=tk.BOTH, expand=True)
        except Exception as e:
            self.logger.error(f"Không thể tạo DVH viewer: {e}")
            ttk.Label(self.dvh_tab, text="Không thể tạo DVH viewer").pack(pady=50)
            self.dvh_view = None
        
        # Tab thông tin kế hoạch
        self.plan_tab = ttk.Frame(self.display_notebook)
        self.display_notebook.add(self.plan_tab, text="Kế hoạch")
        
        # Thanh trạng thái
        self.status_bar = ttk.Label(self.root, text="Sẵn sàng", relief=tk.SUNKEN, anchor=tk.W)
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
        """Cập nhật danh sách bệnh nhân"""
        # Xóa danh sách hiện tại
        self.patient_listbox.delete(0, tk.END)
        
        # Lấy danh sách bệnh nhân
        patients = self.patient_manager.get_all_patients()
        
        # Thêm bệnh nhân vào listbox
        for patient in patients:
            display_name = f"{patient.demographics.get('name', 'Không có tên')} ({patient.patient_id})"
            self.patient_listbox.insert(tk.END, display_name)
            self.patient_listbox.itemconfig(tk.END, {'patient_id': patient.patient_id})
    
    def on_patient_selected(self, event):
        """Xử lý sự kiện khi người dùng chọn bệnh nhân từ danh sách
        
        Args:
            event: Sự kiện ListboxSelect
        """
        selection = self.patient_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        patient_id = self.patient_listbox.itemcget(index, 'patient_id')
        
        if patient_id:
            # Lấy thông tin chi tiết của bệnh nhân
            patient = self.patient_manager.db.get_patient(patient_id)
            
            if patient:
                # Cập nhật thông tin bệnh nhân lên giao diện
                self.update_patient_details(patient)
                
                # Lấy danh sách kế hoạch của bệnh nhân
                plans = self.patient_manager.get_patient_plans(patient_id)
                
                # Hiển thị danh sách kế hoạch
                self.update_plan_list(plans)
                
                # Thiết lập phiên làm việc hiện tại
                self.session_manager.update_current_session({'patient_id': patient_id})
                
                # Cập nhật trạng thái
                self.status_var.set(f"Đã chọn bệnh nhân: {patient.demographics.get('name', 'Không có tên')}")

    def display_data(self, patient_id):
        """Hiển thị dữ liệu bệnh nhân
        
        Args:
            patient_id: ID bệnh nhân
        """
        # Khởi tạo Display nếu chưa có
        if self.display is None:
            self.display = Display(self.root, patient_id, self.patient_manager.db)
        else:
            # Cập nhật bệnh nhân mới
            self.display.update_patient(patient_id)
    
    def update_plan_info(self, plan_id):
        """Cập nhật thông tin kế hoạch trong giao diện"""
        if not plan_id or not self.current_patient_id:
            return
            
        # Lấy thông tin kế hoạch
        plan_data = self.patient_manager.get_plan_details(self.current_patient_id, plan_id)
        if not plan_data:
            self.logger.warning(f"Không tìm thấy thông tin kế hoạch {plan_id}")
            return
        
        # Tạo frame nếu chưa có
        if not hasattr(self, 'plan_info_frame'):
            self.plan_info_frame = ttk.Frame(self.main_frame)
            self.plan_info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        else:
            # Xóa thông tin cũ
            for widget in self.plan_info_frame.winfo_children():
                widget.destroy()
        
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
        """Tạo contour tự động với AI"""
        # Kiểm tra xem đã chọn bệnh nhân và kế hoạch chưa
        if not self.current_patient_id:
            messagebox.showerror("Lỗi", "Vui lòng chọn bệnh nhân trước khi tạo contour tự động")
            return
            
        if not self.current_plan_id:
            messagebox.showerror("Lỗi", "Vui lòng chọn kế hoạch trước khi tạo contour tự động")
            return
            
        # Kiểm tra xem có dữ liệu hình ảnh không
        current_session = self.session_manager.get_current_session()
        if not current_session or 'image_data' not in current_session:
            messagebox.showerror("Lỗi", "Không tìm thấy dữ liệu hình ảnh. Vui lòng tải hình ảnh trước")
            return
            
        # Tạo dialog cho auto contour
        auto_dialog = tk.Toplevel(self.root)
        auto_dialog.title("Phân đoạn Cấu trúc Tự động")
        auto_dialog.geometry("500x600")
        auto_dialog.transient(self.root)
        auto_dialog.grab_set()
        
        # Frame chính
        main_frame = ttk.Frame(auto_dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tiêu đề
        ttk.Label(main_frame, text="Phân đoạn Tự động với AI", font=('Helvetica', 16, 'bold')).pack(pady=10)
        
        # Chọn mô hình AI
        model_frame = ttk.LabelFrame(main_frame, text="Mô hình AI", padding="10")
        model_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(model_frame, text="Loại mô hình:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        model_type_var = tk.StringVar(value="unet")
        ttk.Combobox(model_frame, textvariable=model_type_var, values=["unet", "segnet", "custom"]).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(model_frame, text="Đường dẫn mô hình (tùy chọn):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        model_path_var = tk.StringVar()
        model_path_entry = ttk.Entry(model_frame, textvariable=model_path_var, width=30)
        model_path_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        def browse_model():
            path = filedialog.askopenfilename(
                title="Chọn mô hình",
                filetypes=[("Model Files", "*.h5 *.pb *.onnx *.pt"), ("All Files", "*.*")]
            )
            if path:
                model_path_var.set(path)
        
        ttk.Button(model_frame, text="Duyệt...", command=browse_model).grid(row=1, column=2, padx=5, pady=5)
        
        # Chọn cấu trúc để phân đoạn
        struct_frame = ttk.LabelFrame(main_frame, text="Chọn cấu trúc để phân đoạn", padding="10")
        struct_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Danh sách cấu trúc
        organs = [
            ("Brain", "brain"),
            ("Brainstem", "brainstem"),
            ("Spinal Cord", "spinal_cord"),
            ("Left Parotid", "parotid_l"),
            ("Right Parotid", "parotid_r"),
            ("Left Eye", "eye_l"),
            ("Right Eye", "eye_r"),
            ("Left Lens", "lens_l"),
            ("Right Lens", "lens_r"),
            ("Left Optic Nerve", "optic_nerve_l"),
            ("Right Optic Nerve", "optic_nerve_r"),
            ("Optic Chiasm", "optic_chiasm"),
            ("Pituitary", "pituitary"),
            ("Left Cochlea", "cochlea_l"),
            ("Right Cochlea", "cochlea_r"),
            ("Mandible", "mandible"),
            ("Larynx", "larynx"),
            ("Left Lung", "lung_l"),
            ("Right Lung", "lung_r"),
            ("Heart", "heart"),
            ("Liver", "liver"),
            ("Left Kidney", "kidney_l"),
            ("Right Kidney", "kidney_r"),
            ("Stomach", "stomach"),
            ("Bowel", "bowel"),
            ("Bladder", "bladder"),
            ("Rectum", "rectum"),
            ("Prostate", "prostate"),
            ("Body", "body")
        ]
        
        # Tạo canvas với scrollbar
        canvas = tk.Canvas(struct_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(struct_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Biến lưu trữ checkbox
        organ_vars = {}
        
        # Thêm các checkbox
        for i, (name, id_str) in enumerate(organs):
            var = tk.BooleanVar(value=False)
            organ_vars[id_str] = var
            ttk.Checkbutton(scrollable_frame, text=name, variable=var).grid(row=i, column=0, sticky=tk.W, padx=5, pady=3)
        
        # Frame trạng thái
        status_frame = ttk.LabelFrame(main_frame, text="Tiến trình", padding="10")
        status_frame.pack(fill=tk.X, pady=10)
        
        status_var = tk.StringVar(value="Sẵn sàng phân đoạn")
        ttk.Label(status_frame, textvariable=status_var).pack(fill=tk.X, pady=5)
        
        progress_var = tk.IntVar(value=0)
        progress = ttk.Progressbar(status_frame, variable=progress_var, maximum=100)
        progress.pack(fill=tk.X, pady=5)
        
        # Frame nút
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        # Hàm đóng dialog
        def cancel():
            auto_dialog.destroy()
        
        # Hàm xử lý sự kiện khi nhấn OK
        def run_auto_segmentation():
            # Lấy danh sách các cơ quan được chọn
            selected_organs = [k for k, v in organ_vars.items() if v.get()]
            
            if not selected_organs:
                messagebox.showwarning("Cảnh báo", "Vui lòng chọn ít nhất một cấu trúc để phân đoạn")
                return
            
            # Lấy thông tin mô hình
            model_type = model_type_var.get()
            model_path = model_path_var.get() if model_path_var.get() else None
            
            # Cập nhật UI
            status_var.set("Đang phân đoạn... Vui lòng đợi")
            progress_var.set(0)
            auto_dialog.update()
            
            # Ẩn nút OK trong quá trình xử lý
            btn_frame.grid_remove()
            
            # Gọi hàm thực hiện phân đoạn tự động
            self.create_auto_contours(selected_organs, model_type, model_path, status_var, progress_var, auto_dialog, btn_frame)
        
        cancel_button = ttk.Button(btn_frame, text="Hủy", command=cancel)
        cancel_button.pack(side=tk.RIGHT, padx=5)
        
        ok_button = ttk.Button(btn_frame, text="Bắt đầu phân đoạn", command=run_auto_segmentation)
        ok_button.pack(side=tk.RIGHT, padx=5)
        
    def create_auto_contours(self, selected_organs, model_type, model_path, status_var, progress_var, auto_dialog, btn_frame):
        """
        Thực hiện phân đoạn tự động và tạo contour
        
        Args:
            selected_organs: Danh sách tên các cơ quan cần phân đoạn
            model_type: Loại mô hình AI
            model_path: Đường dẫn đến file mô hình (nếu có)
            status_var: Biến StringVar để cập nhật trạng thái
            progress_var: Biến IntVar để cập nhật tiến trình
            auto_dialog: Dialog phân đoạn tự động
            btn_frame: Frame chứa các nút điều khiển
        """
        try:
            # Tạo đối tượng ContourTools nếu chưa có
            from quangstation.contouring.contour_tools import ContourTools
            
            # Lấy dữ liệu từ phiên làm việc hiện tại
            current_session = self.session_manager.get_current_session()
            if not current_session or 'image_data' not in current_session:
                raise ValueError("Không tìm thấy dữ liệu ảnh trong phiên làm việc hiện tại")
            
            # Chuẩn bị ContourTools
            if not hasattr(self, 'contour_tools') or self.contour_tools is None:
                # Lấy dữ liệu ảnh và thông tin không gian
                image_data = current_session['image_data']
                spacing = current_session.get('spacing', (1.0, 1.0, 1.0))
                origin = current_session.get('origin', (0.0, 0.0, 0.0))
                direction = current_session.get('direction', (1,0,0,0,1,0,0,0,1))
                
                # Khởi tạo ContourTools
                self.contour_tools = ContourTools(
                    image_data=image_data,
                    spacing=spacing,
                    origin=origin,
                    direction=direction
                )
                
                # Nếu đã có cấu trúc contour, cập nhật vào contour_tools
                if 'structures' in current_session:
                    for struct_name, struct_data in current_session['structures'].items():
                        if 'mask' in struct_data:
                            self.contour_tools.add_structure(struct_name, struct_data['mask'])
            
            # Tạo contour cho từng cơ quan đã chọn
            total_organs = len(selected_organs)
            for i, organ in enumerate(selected_organs):
                # Cập nhật trạng thái
                status_var.set(f"Đang tạo contour cho {organ}...")
                progress_var.set(int(20 + (i / total_organs) * 70))
                auto_dialog.update()
                
                # Mô phỏng thời gian xử lý
                import time
                time.sleep(0.5)  # Trong ứng dụng thực, đây sẽ là thời gian để AI xử lý
                
                # Tự động tạo contour sử dụng AI hoặc thuật toán phân đoạn
                if organ.lower() == "body":
                    # Tạo contour body đơn giản bằng thresholding
                    self.contour_tools.create_body_contour(threshold=-500)  # HU threshold cho body
                else:
                    # Sử dụng mô hình AI được chọn
                    if model_path and os.path.exists(model_path):
                        success = self.contour_tools.auto_segment_with_model(
                            organ_name=organ,
                            model_path=model_path,
                            model_type=model_type
                        )
                    else:
                        # Sử dụng phương pháp phân đoạn mặc định nếu không có mô hình
                        success = self.contour_tools.auto_segment(organ)
            
            # Lưu contours vào phiên làm việc hiện tại
            self.save_contours()
            
            # Cập nhật trạng thái
            status_var.set("Hoàn thành phân đoạn tự động!")
            progress_var.set(100)
            auto_dialog.update()
            
            # Hiển thị thông báo thành công
            messagebox.showinfo("Thành công", f"Đã tạo contour cho {total_organs} cơ quan")
            
            # Cập nhật hiển thị
            self.display_data(self.current_patient_id)
            
            # Đóng dialog
            auto_dialog.destroy()
            
        except Exception as e:
            self.logger.error(f"Lỗi khi tạo contour tự động: {str(e)}")
            status_var.set(f"Lỗi: {str(e)}")
            progress_var.set(0)
            messagebox.showerror("Lỗi", f"Không thể tạo contour tự động: {str(e)}")
            
            # Hiển thị lại nút OK
            btn_frame.grid()
            ok_button = [child for child in btn_frame.winfo_children() if child.cget("text") == "Bắt đầu phân đoạn"]
            if ok_button:
                ok_button[0].config(state=tk.NORMAL)
            auto_dialog.update()

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
            
            # Kỹ thuật xạ trị
            ttk.Label(option_grid, text="Kỹ thuật xạ trị:").grid(row=7, column=0, sticky=tk.W, pady=5)
            technique_var = tk.StringVar(value="VMAT")
            ttk.Combobox(option_grid, textvariable=technique_var, 
                         values=["3DCRT", "IMRT", "VMAT", "SBRT", "SRS"], 
                         width=10).grid(row=7, column=1, sticky=tk.W, pady=5)
            
            # Bảng hiệu chỉnh và các tùy chọn khác
            ttk.Label(option_grid, text="File hiệu chuẩn:").grid(row=8, column=0, sticky=tk.W, pady=5)
            calibration_file_var = tk.StringVar()
            calibration_entry = ttk.Entry(option_grid, textvariable=calibration_file_var, width=20)
            calibration_entry.grid(row=8, column=1, sticky=tk.W, pady=5)
            
            # Hiệu chỉnh không đồng nhất
            ttk.Label(option_grid, text="Hiệu chỉnh không đồng nhất:").grid(row=9, column=0, sticky=tk.W, pady=5)
            hetero_correction_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(option_grid, variable=hetero_correction_var).grid(row=9, column=1, sticky=tk.W, pady=5)
            
            # Tùy chọn Monte Carlo
            ttk.Label(option_grid, text="Số lịch sử MC:").grid(row=10, column=0, sticky=tk.W, pady=5)
            mc_histories_var = tk.IntVar(value=10000)
            ttk.Spinbox(option_grid, from_=1000, to=1000000, increment=1000, textvariable=mc_histories_var, width=10).grid(row=10, column=1, sticky=tk.W, pady=5)
            
            # Số lần lặp tối đa
            ttk.Label(option_grid, text="Số lần lặp tối đa:").grid(row=11, column=0, sticky=tk.W, pady=5)
            max_iterations_var = tk.IntVar(value=100)
            ttk.Spinbox(option_grid, from_=10, to=1000, increment=10, textvariable=max_iterations_var, width=10).grid(row=11, column=1, sticky=tk.W, pady=5)
            
            # Độ phân giải
            ttk.Label(option_grid, text="Độ phân giải (mm):").grid(row=12, column=0, sticky=tk.W, pady=5)
            resolution_var = tk.DoubleVar(value=2.5)
            ttk.Combobox(option_grid, textvariable=resolution_var, 
                         values=[1.0, 2.0, 2.5, 3.0, 5.0], 
                         width=10).grid(row=12, column=1, sticky=tk.W, pady=5)
            
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
                    # Tích hợp với module tính liều thực tế
                    from quangstation.dose_calculation.dose_engine_wrapper import DoseCalculator
                    
                    # Lấy dữ liệu từ phiên làm việc hiện tại
                    current_session = self.session_manager.get_current_session()
                    if not current_session:
                        raise ValueError("Không tìm thấy phiên làm việc hiện tại")
                    
                    # Khởi tạo bộ tính toán liều với thuật toán được chọn
                    dose_calculator = DoseCalculator(
                        algorithm=algorithm,
                        resolution_mm=float(grid_size_var.get())
                    )
                    
                    # Thiết lập dữ liệu bệnh nhân (ảnh CT)
                    if 'image_data' not in current_session:
                        raise ValueError("Không tìm thấy dữ liệu ảnh trong phiên làm việc hiện tại")
                    
                    # Cập nhật trạng thái
                    status_var.set("Đang thiết lập dữ liệu bệnh nhân...")
                    progress_var.set(10)
                    dose_dialog.update()
                    
                    # Thiết lập dữ liệu CT và spacing
                    image_data = current_session['image_data']
                    spacing = current_session.get('spacing', (1.0, 1.0, 1.0))
                    dose_calculator.set_patient_data(image_data, spacing)
                    
                    # Thiết lập bảng chuyển đổi HU sang mật độ
                    calibration_file = calibration_file_var.get()
                    if calibration_file and os.path.exists(calibration_file):
                        dose_calculator.set_hu_to_density_file(calibration_file)
                    
                    # Bật/tắt hiệu chỉnh không đồng nhất
                    dose_calculator.set_heterogeneity_correction(hetero_correction_var.get())
                    
                    # Thiết lập các cấu trúc
                    if 'structures' in current_session:
                        status_var.set("Đang thiết lập cấu trúc...")
                        progress_var.set(15)
                        dose_dialog.update()
                        
                        for struct_name, struct_data in current_session['structures'].items():
                            if 'mask' in struct_data:
                                dose_calculator.add_structure(struct_name, struct_data['mask'])
                    
                    # Thiết lập các chùm tia
                    if 'beams' in current_session:
                        status_var.set("Đang thiết lập chùm tia...")
                        progress_var.set(20)
                        dose_dialog.update()
                        
                        for beam in current_session['beams']:
                            dose_calculator.add_beam(beam)
                    else:
                        # Tạo chùm tia mặc định nếu không có
                        default_beam = {
                            'iso_center': [
                                image_data.shape[0] // 2,
                                image_data.shape[1] // 2,
                                image_data.shape[2] // 2
                            ],
                            'gantry_angle': 0,
                            'collimator_angle': 0,
                            'couch_angle': 0,
                            'sad': 1000,  # mm
                            'field_size': [100, 100],  # mm
                            'energy': 6,  # MV
                            'dose_rate': 600,  # MU/min
                            'mu': 100
                        }
                        dose_calculator.add_beam(default_beam)
                    
                    # Thiết lập các tùy chọn tính toán
                    options = {
                        'grid_size': int(grid_size_var.get()),
                        'max_iterations': int(max_iterations_var.get()),
                        'monte_carlo_histories': int(mc_histories_var.get()) if algorithm_var.get() == 'monte_carlo' else 0,
                        'dose_grid_resolution': float(resolution_var.get())
                    }
                    dose_calculator.set_calculation_options(options)
                    
                    # Tính toán liều
                    status_var.set("Đang tính toán liều...")
                    progress_var.set(30)
                    dose_dialog.update()
                    
                    # Tính toán liều với kỹ thuật được chọn
                    technique = technique_var.get()
                    structures = {}
                    if 'structures' in current_session:
                        structures = current_session['structures']
                    
                    dose_matrix = dose_calculator.calculate_dose(technique=technique, structures=structures)
                    
                    # Cập nhật giá trị liều tối đa
                    max_dose = np.max(dose_matrix)
                    current_session['max_dose'] = float(max_dose)
                    
                    # Lưu ma trận liều vào phiên làm việc
                    current_session['dose_matrix'] = dose_matrix
                    
                    # Cập nhật thông tin kế hoạch với liều đã tính
                    if 'plans' not in current_session:
                        current_session['plans'] = {}
                    
                    if self.current_plan_id not in current_session['plans']:
                        current_session['plans'][self.current_plan_id] = {}
                    
                    current_session['plans'][self.current_plan_id]['has_dose'] = True
                    current_session['plans'][self.current_plan_id]['max_dose'] = float(max_dose)
                    current_session['plans'][self.current_plan_id]['dose_algorithm'] = algorithm_var.get()
                    current_session['plans'][self.current_plan_id]['technique'] = technique_var.get()
                    
                    # Cập nhật phiên làm việc
                    self.session_manager.update_current_session(current_session)
                    
                    # Cập nhật trạng thái
                    status_var.set("Hoàn thành tính toán liều!")
                    progress_var.set(100)
                    
                    # Hiển thị thông tin liều
                    messagebox.showinfo("Thành công", f"Đã tính toán liều thành công!\nLiều tối đa: {max_dose:.2f} Gy")
                    
                    # Cập nhật hiển thị liều
                    self.update_dose_display()

                except Exception as e:
                    self.logger.error(f"Lỗi khi tính toán liều: {str(e)}")
                    status_var.set(f"Lỗi: {str(e)}")
                    progress_var.set(0)
                    messagebox.showerror("Lỗi", f"Không thể tính toán liều: {str(e)}")
                finally:
                    # Ghi log
                    self.logger.info(f"Đã tính toán liều với thuật toán {algorithm_var.get()}")
                    
                    # Đóng dialog sau khi hoàn thành
                    dose_dialog.destroy()
            
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
        if not self.current_patient_id or not self.current_plan_id:
            return
        
        try:
            # Lấy phiên làm việc hiện tại
            current_session = self.session_manager.get_current_session()
            if not current_session:
                return
            
            # Kiểm tra xem có dữ liệu liều không
            if 'dose_matrix' not in current_session:
                self.logger.warning("Không tìm thấy dữ liệu liều trong phiên làm việc hiện tại")
                return
            
            # Lấy ma trận liều
            dose_matrix = current_session['dose_matrix']
            
            # Cập nhật hiển thị liều trên các view MPR
            if hasattr(self, 'mpr_view') and self.mpr_view:
                # Thiết lập dữ liệu liều cho MPR view
                self.mpr_view.set_dose_data(dose_matrix)
                
                # Cập nhật màu sắc và thông số hiển thị liều
                if 'plans' in current_session and self.current_plan_id in current_session['plans']:
                    plan_data = current_session['plans'][self.current_plan_id]
                    max_dose = plan_data.get('max_dose', np.max(dose_matrix) if dose_matrix is not None else 0)
                    self.mpr_view.set_dose_display_params(
                        max_dose=max_dose,
                        colormap='jet',
                        alpha=0.5
                    )
                
                # Kích hoạt hiển thị liều
                self.mpr_view.toggle_dose_display(True)
                
                # Cập nhật hiển thị
                self.mpr_view.update_display()
            
            # Cập nhật histogram liều-thể tích nếu có
            self.update_dvh_display()
            
            self.logger.info("Đã cập nhật hiển thị liều")
            
        except Exception as e:
            self.logger.error(f"Lỗi khi cập nhật hiển thị liều: {str(e)}")
            
    def update_dvh_display(self):
        """Cập nhật hiển thị histogram liều-thể tích (DVH)"""
        if not self.current_patient_id or not self.current_plan_id:
            return
        
        try:
            # Lấy phiên làm việc hiện tại
            current_session = self.session_manager.get_current_session()
            if not current_session:
                return
            
            # Kiểm tra xem có dữ liệu liều không
            if 'dose_matrix' not in current_session or 'structures' not in current_session:
                return
            
            # Lấy ma trận liều và cấu trúc
            dose_matrix = current_session['dose_matrix']
            structures = current_session['structures']
            
            # Tính toán và hiển thị DVH nếu có giao diện DVH
            if hasattr(self, 'dvh_view') and self.dvh_view:
                dvhs = {}
                
                # Tính DVH cho từng cấu trúc
                for struct_name, struct_data in structures.items():
                    if 'mask' in struct_data:
                        # Lấy mask của cấu trúc
                        mask = struct_data['mask']
                        
                        # Tính DVH
                        doses = dose_matrix[mask > 0]
                        if len(doses) > 0:
                            # Tạo histogram
                            hist, bin_edges = np.histogram(doses, bins=100, range=(0, np.max(dose_matrix)))
                            dvhs[struct_name] = {
                                'hist': hist,
                                'bin_edges': bin_edges,
                                'color': struct_data.get('color', (1.0, 0.0, 0.0))
                            }
                
                # Cập nhật hiển thị DVH
                self.dvh_view.set_dvh_data(dvhs)
                self.dvh_view.update_display()
            
        except Exception as e:
            self.logger.error(f"Lỗi khi cập nhật hiển thị DVH: {str(e)}")

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
        self.patient_tree.bind('<<TreeviewSelect>>', self.on_patient_selected)
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

    def save_contours(self):
        """
        Lưu các contour từ contour_tools vào phiên làm việc hiện tại
        """
        if not hasattr(self, 'contour_tools') or self.contour_tools is None:
            self.logger.warning("Không thể lưu contours: contour_tools chưa được khởi tạo")
            return
        
        try:
            # Lấy phiên làm việc hiện tại
            current_session = self.session_manager.get_current_session()
            if not current_session:
                self.logger.warning("Không tìm thấy phiên làm việc hiện tại")
                return
            
            # Nếu không có key 'structures' trong session, tạo mới
            if 'structures' not in current_session:
                current_session['structures'] = {}
            
            # Lấy contours từ contour_tools và lưu vào session
            for struct_name, contour_data in self.contour_tools.contours.items():
                # Chuyển đổi contour thành mask nếu cần
                if 'mask' not in contour_data:
                    mask = self.contour_tools.contour_to_mask(struct_name)
                else:
                    mask = contour_data['mask']
                
                # Lưu vào structures của session
                current_session['structures'][struct_name] = {
                    'mask': mask,
                    'color': self.contour_tools.colors.get(struct_name, (1.0, 0.0, 0.0)),  # Mặc định là màu đỏ
                    'name': struct_name,
                    'type': 'ORGAN' if struct_name.startswith('PTV') or struct_name.startswith('CTV') else 'ORGAN',
                    'modified_date': datetime.now().isoformat()
                }
            
            # Cập nhật phiên làm việc
            self.session_manager.update_current_session(current_session)
            
            self.logger.info(f"Đã lưu {len(self.contour_tools.contours)} contours vào phiên làm việc")
            return True
        except Exception as e:
            self.logger.error(f"Lỗi khi lưu contours: {str(e)}")
            return False
            
    def has_contours(self):
        """
        Kiểm tra xem có contours trong phiên làm việc hiện tại không
        
        Returns:
            bool: True nếu có contours, False nếu không
        """
        current_session = self.session_manager.get_current_session()
        if not current_session or 'structures' not in current_session:
            return False
        return len(current_session['structures']) > 0
    
    def get_contour_tools(self):
        """
        Lấy đối tượng ContourTools
        
        Returns:
            ContourTools: Đối tượng ContourTools hoặc None nếu chưa khởi tạo
        """
        return self.contour_tools if hasattr(self, 'contour_tools') else None
    
    def set_contour_tools(self, contour_tools):
        """
        Thiết lập đối tượng ContourTools
        
        Args:
            contour_tools: Đối tượng ContourTools mới
        """
        self.contour_tools = contour_tools

    def show_dvh(self):
        """Hiển thị Histogram Liều-Thể tích (DVH)"""
        if not self.current_patient_id or not self.current_plan_id:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn bệnh nhân và kế hoạch trước khi xem DVH")
            return
            
        # Kiểm tra xem kế hoạch đã có dữ liệu liều chưa
        current_session = self.session_manager.get_current_session()
        if not current_session or 'dose_matrix' not in current_session:
            messagebox.showwarning("Cảnh báo", "Chưa có dữ liệu liều cho kế hoạch này. Vui lòng tính liều trước khi xem DVH.")
            return
            
        # Chuyển đến tab DVH
        self.display_notebook.select(self.dvh_tab)
        
        # Cập nhật hiển thị DVH
        self.update_dvh_display()
        
    def update_plan_list(self, plans):
        """Cập nhật danh sách kế hoạch của bệnh nhân
        
        Args:
            plans: Danh sách các kế hoạch điều trị
        """
        # Tạo plan_listbox nếu chưa tồn tại
        if not hasattr(self, 'plan_listbox'):
            # Tạo frame chứa danh sách kế hoạch
            plan_frame = ttk.LabelFrame(self.patient_frame, text="Kế hoạch")
            plan_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Tạo Listbox và thanh cuộn
            plan_scroll = ttk.Scrollbar(plan_frame)
            self.plan_listbox = tk.Listbox(plan_frame, yscrollcommand=plan_scroll.set)
            plan_scroll.config(command=self.plan_listbox.yview)
            
            self.plan_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            plan_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Sự kiện khi chọn kế hoạch
            self.plan_listbox.bind('<<ListboxSelect>>', self.on_plan_selected)
        else:
            # Xóa danh sách kế hoạch cũ
            self.plan_listbox.delete(0, tk.END)
        
        # Thêm kế hoạch vào listbox
        if plans:
            for plan in plans:
                plan_name = plan.get('name', f"Kế hoạch {plan.get('plan_id', '')}")
                self.plan_listbox.insert(tk.END, plan_name)
                # Lưu plan_id như một thuộc tính của mục trong listbox
                self.plan_listbox.itemconfig(tk.END, {'plan_id': plan.get('plan_id', '')})
    
    def on_plan_selected(self, event):
        """Xử lý sự kiện khi người dùng chọn kế hoạch từ danh sách
        
        Args:
            event: Sự kiện ListboxSelect
        """
        selection = self.plan_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        plan_id = self.plan_listbox.itemcget(index, 'plan_id')
        
        if not plan_id:
            return
        
        # Lấy thông tin phiên làm việc hiện tại
        current_session = self.session_manager.get_current_session()
        if not current_session:
            return
        
        patient_id = current_session.get('patient_id')
        if not patient_id:
            return
        
        # Lấy thông tin chi tiết kế hoạch
        plan_details = self.patient_manager.get_plan_details(patient_id, plan_id)
        
        if plan_details:
            # Cập nhật kế hoạch hiện tại trong phiên làm việc
            self.session_manager.update_current_session({'plan_id': plan_id})
            
            # Cập nhật hiển thị thông tin kế hoạch
            self.update_plan_details(plan_details)
            
            # Cập nhật hiển thị dữ liệu volume và cấu trúc
            if 'ct_series_uid' in plan_details:
                self.load_ct_data(patient_id, plan_details['ct_series_uid'])
            
            if 'structures' in plan_details:
                self.load_structures(patient_id, plan_details['structures'])
            
            # Cập nhật trạng thái
            self.status_var.set(f"Đã chọn kế hoạch: {plan_details.get('name', 'Không tên')}")
    
    def get_patient_plans(self, patient_id):
        """
        Lấy danh sách kế hoạch của bệnh nhân
        
        Args:
            patient_id: ID bệnh nhân
            
        Returns:
            List[Dict]: Danh sách kế hoạch
        """
        # Kiểm tra xem đã khởi tạo session_manager chưa
        if not hasattr(self, "session_manager") or not self.session_manager:
            return []
            
        # Lấy danh sách kế hoạch từ phiên làm việc hiện tại
        try:
            patient = self.patient_manager.db.get_patient(patient_id)
            if not patient:
                return []
                
            # Lấy danh sách kế hoạch từ Patient object
            plans = []
            for plan_id, plan_data in patient.plans.items():
                # Thêm plan_id vào dữ liệu
                plan_data_with_id = dict(plan_data)
                plan_data_with_id["plan_id"] = plan_id
                plans.append(plan_data_with_id)
                
            return plans
        except Exception as e:
            self.logger.error(f"Lỗi khi lấy danh sách kế hoạch: {str(e)}")
            return []

    def search_patients(self):
        """Tìm kiếm bệnh nhân theo từ khóa"""
        # Lấy từ khóa tìm kiếm
        search_text = self.search_entry.get().strip()
        
        # Nếu không có từ khóa, hiển thị tất cả
        if not search_text:
            # Nếu không có từ khóa, hiển thị tất cả
            self.update_patient_list()
            return
        
        # Tạo patient_listbox nếu chưa có
        if not hasattr(self, 'patient_listbox'):
            self._create_patient_listbox()
        
        # Xóa danh sách hiện tại
        self.patient_listbox.delete(0, tk.END)
        
        # Tìm kiếm với từ khóa
        results = self.patient_manager.search_patients(search_text=search_text)
        
        # Hiển thị kết quả
        for patient in results:
            display_text = f"{patient.get('name', 'Không tên')} (ID: {patient.get('patient_id', 'N/A')})"
            self.patient_listbox.insert(tk.END, display_text)
            # Lưu ID bệnh nhân vào item
            self.patient_listbox.itemconfig(tk.END, {'patient_id': patient.get('patient_id')})
        
        # Cập nhật trạng thái
        self.status_bar.config(text=f"Tìm thấy {len(results)} kết quả cho '{search_text}'")
        
        # Ghi log
        self.logger.info(f"Tìm kiếm bệnh nhân với từ khóa: {search_text}, {len(results)} kết quả")
    
    def _create_patient_listbox(self):
        """Tạo patient_listbox nếu chưa có"""
        # Tạo frame chứa danh sách bệnh nhân
        patient_list_frame = ttk.LabelFrame(self.patient_frame, text="Danh sách bệnh nhân")
        patient_list_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Tạo Listbox và Scrollbar
        self.patient_listbox = tk.Listbox(patient_list_frame, height=15)
        patient_scroll = ttk.Scrollbar(patient_list_frame, orient="vertical", command=self.patient_listbox.yview)
        self.patient_listbox.configure(yscrollcommand=patient_scroll.set)
        
        self.patient_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        patient_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Thêm sự kiện khi chọn bệnh nhân
        self.patient_listbox.bind('<<ListboxSelect>>', self.on_patient_selected)

    def update_patient_details(self, patient):
        """Cập nhật hiển thị thông tin chi tiết bệnh nhân
        
        Args:
            patient: Đối tượng bệnh nhân
        """
        # Tạo hoặc cập nhật frame thông tin bệnh nhân
        if not hasattr(self, 'patient_info_frame'):
            self.patient_info_frame = ttk.LabelFrame(self.patient_frame, text="Thông tin bệnh nhân")
            self.patient_info_frame.pack(fill=tk.X, padx=5, pady=5)
            
            # Tạo grid layout cho thông tin
            for i in range(4):
                self.patient_info_frame.columnconfigure(i, weight=1)
            
            # Tạo các nhãn
            ttk.Label(self.patient_info_frame, text="ID:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
            self.patient_id_label = ttk.Label(self.patient_info_frame, text="")
            self.patient_id_label.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
            
            ttk.Label(self.patient_info_frame, text="Họ tên:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
            self.patient_name_label = ttk.Label(self.patient_info_frame, text="")
            self.patient_name_label.grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)
            
            ttk.Label(self.patient_info_frame, text="Ngày sinh:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
            self.patient_dob_label = ttk.Label(self.patient_info_frame, text="")
            self.patient_dob_label.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
            
            ttk.Label(self.patient_info_frame, text="Giới tính:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
            self.patient_gender_label = ttk.Label(self.patient_info_frame, text="")
            self.patient_gender_label.grid(row=1, column=3, sticky=tk.W, padx=5, pady=2)
            
            ttk.Label(self.patient_info_frame, text="Chẩn đoán:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
            self.patient_diagnosis_label = ttk.Label(self.patient_info_frame, text="")
            self.patient_diagnosis_label.grid(row=2, column=1, columnspan=3, sticky=tk.W, padx=5, pady=2)
        
        # Cập nhật thông tin
        self.patient_id_label.config(text=patient.patient_id)
        self.patient_name_label.config(text=patient.demographics.get('name', ''))
        self.patient_dob_label.config(text=patient.demographics.get('birth_date', ''))
        self.patient_gender_label.config(text=patient.demographics.get('gender', ''))
        self.patient_diagnosis_label.config(text=patient.clinical_info.get('diagnosis', ''))
    
    def update_plan_details(self, plan_details):
        """Cập nhật hiển thị thông tin chi tiết kế hoạch
        
        Args:
            plan_details: Thông tin chi tiết kế hoạch
        """
        # Tạo hoặc cập nhật frame thông tin kế hoạch
        if not hasattr(self, 'plan_info_frame'):
            self.plan_info_frame = ttk.LabelFrame(self.patient_frame, text="Thông tin kế hoạch")
            self.plan_info_frame.pack(fill=tk.X, padx=5, pady=5)
            
            # Tạo grid layout cho thông tin
            for i in range(4):
                self.plan_info_frame.columnconfigure(i, weight=1)
            
            # Tạo các nhãn
            ttk.Label(self.plan_info_frame, text="Tên kế hoạch:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
            self.plan_name_label = ttk.Label(self.plan_info_frame, text="")
            self.plan_name_label.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
            
            ttk.Label(self.plan_info_frame, text="Kỹ thuật:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
            self.plan_technique_label = ttk.Label(self.plan_info_frame, text="")
            self.plan_technique_label.grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)
            
            ttk.Label(self.plan_info_frame, text="Ngày tạo:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
            self.plan_date_label = ttk.Label(self.plan_info_frame, text="")
            self.plan_date_label.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
            
            ttk.Label(self.plan_info_frame, text="Trạng thái:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
            self.plan_status_label = ttk.Label(self.plan_info_frame, text="")
            self.plan_status_label.grid(row=1, column=3, sticky=tk.W, padx=5, pady=2)
            
            ttk.Label(self.plan_info_frame, text="Mô tả:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
            self.plan_description_label = ttk.Label(self.plan_info_frame, text="")
            self.plan_description_label.grid(row=2, column=1, columnspan=3, sticky=tk.W, padx=5, pady=2)
        
        # Cập nhật thông tin
        self.plan_name_label.config(text=plan_details.get('name', ''))
        self.plan_technique_label.config(text=plan_details.get('technique', ''))
        self.plan_date_label.config(text=plan_details.get('created_date', ''))
        self.plan_status_label.config(text=plan_details.get('status', 'Mới'))
        self.plan_description_label.config(text=plan_details.get('description', ''))
    
    def load_ct_data(self, patient_id, series_uid):
        """Tải dữ liệu hình ảnh CT
        
        Args:
            patient_id: ID bệnh nhân
            series_uid: UID của series CT
        """
        try:
            # Giả lập tải dữ liệu CT do PatientDatabase không có phương thức get_volume
            # Thực tế sẽ cần thực hiện điều này trong PatientDatabase
            self.logger.info(f"Giả lập tải dữ liệu CT cho bệnh nhân {patient_id}, series {series_uid}")
            
            # Tạo dữ liệu giả lập
            import numpy as np
            volume_data = np.zeros((100, 100, 100), dtype=np.float32)
            
            # Cập nhật vào phiên làm việc hiện tại
            self.session_manager.update_current_session({'ct_volume': volume_data})
            
            # Hiển thị dữ liệu CT trên MPR viewer
            if hasattr(self, 'mpr_view'):
                self.mpr_view.set_volume(volume_data)
        except Exception as e:
            self.logger.error(f"Lỗi khi tải dữ liệu CT: {str(e)}")
    
    def load_structures(self, patient_id, structure_set_uid):
        """Tải dữ liệu cấu trúc
        
        Args:
            patient_id: ID bệnh nhân
            structure_set_uid: UID của bộ cấu trúc
        """
        try:
            # Giả lập tải dữ liệu cấu trúc do PatientDatabase không có phương thức get_rt_struct
            # Thực tế sẽ cần thực hiện điều này trong PatientDatabase
            self.logger.info(f"Giả lập tải dữ liệu cấu trúc cho bệnh nhân {patient_id}")
            
            # Tạo dữ liệu giả lập
            import numpy as np
            
            # Tạo một số cấu trúc mẫu
            structures = {
                "PTV": {
                    "mask": np.zeros((100, 100, 100), dtype=bool),
                    "color": (1.0, 0.0, 0.0)  # Đỏ
                },
                "OAR1": {
                    "mask": np.zeros((100, 100, 100), dtype=bool),
                    "color": (0.0, 1.0, 0.0)  # Xanh lá
                }
            }
            
            # Điền một số giá trị cho mask
            structures["PTV"]["mask"][40:60, 40:60, 40:60] = True
            structures["OAR1"]["mask"][30:40, 30:40, 30:40] = True
            
            # Cập nhật vào phiên làm việc hiện tại
            self.session_manager.update_current_session({'structures': structures})
            
            # Hiển thị dữ liệu cấu trúc trên MPR viewer
            if hasattr(self, 'mpr_view'):
                # Tạo dictionary đúng định dạng cho MPR viewer
                structure_data = {}
                structure_colors = {}
                
                for struct_id, struct_info in structures.items():
                    if 'mask' in struct_info and 'color' in struct_info:
                        structure_data[struct_id] = {'mask': struct_info['mask']}
                        structure_colors[struct_id] = struct_info['color']
                
                self.mpr_view.set_structures(structure_data, structure_colors)
        except Exception as e:
            self.logger.error(f"Lỗi khi tải dữ liệu cấu trúc: {str(e)}")

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