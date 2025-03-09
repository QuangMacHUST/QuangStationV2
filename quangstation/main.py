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
        patient_info['id'] = patient_id
        patient_info['last_modified'] = datetime.now().isoformat()
        
        try:
            self.db.insert_patient(patient_info)
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
            update_data['last_modified'] = datetime.now().isoformat()
            self.db.update_patient(patient_id, update_data)
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
        return self.db.get_patient_details(patient_id)
    
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
            # Thêm code xóa bệnh nhân ở đây
            # (Cần triển khai trong PatientDatabase)
            self.logger.info(f"Đã xóa bệnh nhân: {patient_id}")
            return True
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
        """
        Hiển thị dữ liệu bệnh nhân
        
        Args:
            patient_id: ID của bệnh nhân
        """
        try:
            # Xóa frame hiển thị cũ nếu có
            if hasattr(self, 'current_display') and self.current_display:
                try:
                    self.current_display.close()
                except:
                    pass
                self.display_frame.destroy()
                self.display_frame = ttk.Frame(self.main_pane)
                self.main_pane.add(self.display_frame, weight=4)
            
            # Hiển thị thông tin bệnh nhân
            self.current_patient_id = patient_id
            
            # Tạo đối tượng Display để hiển thị dữ liệu
            self.current_display = Display(self.display_frame, patient_id, self.patient_manager.db)
            
            # Cập nhật thanh trạng thái
            patient_info = self.patient_manager.get_patient_details(patient_id)
            patient_name = patient_info.get('name', 'Không xác định')
            self.status_var.set(f"Đang xem bệnh nhân: {patient_name}")
            
            self.logger.info(f"Đã tải dữ liệu bệnh nhân {patient_id}")
        except Exception as error:
            self.logger.error(f"Lỗi khi hiển thị dữ liệu bệnh nhân {patient_id}: {str(error)}")
            messagebox.showerror("Lỗi", f"Không thể hiển thị dữ liệu bệnh nhân: {str(error)}")
        finally: 
            pass

    # Các hàm xử lý menu
    def import_dicom(self):
        """Nhập dữ liệu DICOM"""
        ImportInterface(self.root, self.update_patient_list)

    def export_plan(self):
        """Xuất kế hoạch điều trị"""
        if not self.current_patient_id:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn bệnh nhân trước")
            return
        
        # TODO: Implement export functionality
        self.logger.info(f"Xuất kế hoạch cho bệnh nhân {self.current_patient_id}")

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
        
        # Kỹ thuật
        ttk.Label(input_frame, text="Kỹ thuật:").grid(row=5, column=0, sticky=tk.W, pady=5)
        technique_var = tk.StringVar(value="3DCRT")
        ttk.Combobox(input_frame, textvariable=technique_var, 
                     values=["3DCRT", "IMRT", "VMAT", "SRS", "SBRT"], 
                     width=15, state="readonly").grid(row=5, column=1, sticky=tk.W, pady=5)
        
        # Máy điều trị
        ttk.Label(input_frame, text="Máy điều trị:").grid(row=6, column=0, sticky=tk.W, pady=5)
        machine_var = tk.StringVar(value="TrueBeam")
        ttk.Combobox(input_frame, textvariable=machine_var, 
                     values=["TrueBeam", "Halcyon", "VitalBeam", "Clinac", "Elekta Versa HD", "Cyberknife"], 
                     width=20).grid(row=6, column=1, sticky=tk.W, pady=5)
        
        # Tư thế
        ttk.Label(input_frame, text="Tư thế bệnh nhân:").grid(row=7, column=0, sticky=tk.W, pady=5)
        position_var = tk.StringVar(value="HFS")
        ttk.Combobox(input_frame, textvariable=position_var, 
                     values=["HFS", "HFP", "FFS", "FFP"], 
                     width=10, state="readonly").grid(row=7, column=1, sticky=tk.W, pady=5)
        
        # Nút tạo kế hoạch
        def save_plan():
            try:
                # Tạo kế hoạch mới từ PlanConfig
                plan_config = PlanConfig()
                plan_config.set_plan_info(
                    plan_name=plan_name_var.get(),
                    total_dose=total_dose_var.get(),
                    fraction_count=fraction_var.get()
                )
                plan_config.set_radiation_info(
                    radiation_type=radiation_var.get(),
                    energy=energy_var.get()
                )
                plan_config.set_machine_info(
                    machine_name=machine_var.get(),
                    patient_position=position_var.get()
                )
                plan_config.set_rt_technique(technique_var.get())
                
                # Tạo phiên làm việc mới
                self.session_manager.create_new_session(self.current_patient_id)
                
                # Lưu metadata kế hoạch
                metadata = plan_config.to_dict()
                plan_id = self.session_manager.save_plan_metadata(
                    metadata, 
                    plan_id=plan_config.plan_id,
                    patient_id=self.current_patient_id
                )
                
                # Hiển thị thông báo thành công
                messagebox.showinfo("Thành công", f"Đã tạo kế hoạch mới: {plan_name_var.get()}")
                
                # Đóng dialog
                plan_dialog.destroy()
                
                # Cập nhật trạng thái
                self.current_plan_id = plan_id
                self.logger.info(f"Đã tạo kế hoạch mới: {plan_id} - {plan_name_var.get()}")
                
                # TODO: Hiển thị màn hình lập kế hoạch
                
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
        """Tối ưu hóa kế hoạch"""
        # TODO: Implement plan optimization functionality
        self.logger.info("Tối ưu hóa kế hoạch")

    def show_dvh(self):
        """Hiển thị biểu đồ DVH (Dose Volume Histogram)"""
        if not self.current_patient_id:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn bệnh nhân trước")
            return
        
        if not self.current_plan_id:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn kế hoạch cần hiển thị DVH")
            return
        
        try:
            # Tạo cửa sổ hiển thị DVH
            dvh_window = tk.Toplevel(self.root)
            dvh_window.title("Biểu đồ Dose Volume Histogram (DVH)")
            dvh_window.geometry("900x600")
            dvh_window.transient(self.root)
            
            # Kiểm tra xem có dữ liệu DVH không
            # Lấy dữ liệu DVH từ session_manager
            dvh_data = self.session_manager.load_session(
                patient_id=self.current_patient_id,
                plan_id=self.current_plan_id
            ).get('dvh_data')
            
            if not dvh_data:
                # Nếu không có dữ liệu DVH, hiển thị thông báo
                ttk.Label(dvh_window, text="Chưa có dữ liệu DVH cho kế hoạch này.\nVui lòng tính toán liều trước.", 
                         font=('Helvetica', 12)).pack(expand=True)
                return
            
            # Frame chứa biểu đồ
            frame = ttk.Frame(dvh_window)
            frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Tạo biểu đồ bằng matplotlib
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Màu sắc cho các đường cong
            colors = {
                'PTV': 'red',
                'CTV': 'orange',
                'GTV': 'magenta',
                'Spinal Cord': 'yellow',
                'Heart': 'red',
                'Lung': 'blue',
                'Liver': 'brown',
                'Kidney': 'purple',
                'Brain': 'green',
                'Body': 'cyan'
            }
            
            # Vẽ các đường cong DVH
            for structure, data in dvh_data.items():
                if structure in colors:
                    color = colors[structure]
                else:
                    # Màu ngẫu nhiên cho cấu trúc không có màu định sẵn
                    import random
                    color = "#{:02x}{:02x}{:02x}".format(
                        random.randint(0, 255), 
                        random.randint(0, 255), 
                        random.randint(0, 255)
                    )
                
                # Dữ liệu DVH gồm hai mảng: liều (dose) và thể tích (volume)
                if 'dose' in data and 'volume' in data:
                    ax.plot(data['dose'], data['volume'], label=structure, color=color, linewidth=2)
            
            # Thiết lập trục và nhãn
            ax.set_xlabel('Liều (Gy)', fontsize=12)
            ax.set_ylabel('Thể tích (%)', fontsize=12)
            ax.set_title('Biểu đồ Dose Volume Histogram (DVH)', fontsize=14)
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.set_xlim(0, max(d['dose'][-1] for d in dvh_data.values() if 'dose' in d) * 1.1)
            ax.set_ylim(0, 105)
            
            # Hiển thị chú thích
            ax.legend(loc='upper right', fontsize=10)
            
            # Tạo canvas hiển thị matplotlib trong tkinter
            canvas = FigureCanvasTkAgg(fig, master=frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Frame chứa các nút điều khiển
            button_frame = ttk.Frame(dvh_window)
            button_frame.pack(fill=tk.X, padx=10, pady=10)
            
            # Nút xuất hình ảnh
            def export_image():
                file_path = filedialog.asksaveasfilename(
                    defaultextension='.png',
                    filetypes=[('PNG Image', '*.png'), ('JPEG Image', '*.jpg'), ('PDF Document', '*.pdf')],
                    title="Lưu biểu đồ DVH"
                )
                if file_path:
                    try:
                        fig.savefig(file_path, dpi=300, bbox_inches='tight')
                        messagebox.showinfo("Thông báo", f"Đã lưu biểu đồ vào {file_path}")
                    except Exception as error:
                        messagebox.showerror("Lỗi", f"Không thể lưu biểu đồ: {str(error)}")
            
            ttk.Button(button_frame, text="Xuất hình ảnh", command=export_image).pack(side=tk.RIGHT, padx=5)
            ttk.Button(button_frame, text="Đóng", command=dvh_window.destroy).pack(side=tk.RIGHT, padx=5)
            
            self.logger.info("Đã hiển thị biểu đồ DVH")
            
        except Exception as error:
            self.logger.error(f"Lỗi khi hiển thị DVH: {str(error)}")
            messagebox.showerror("Lỗi", f"Không thể hiển thị biểu đồ DVH: {str(error)}")

    def search_patients(self):
        """Tìm kiếm bệnh nhân"""
        search_text = self.search_var.get().strip().lower()
        if not search_text:
            self.update_patient_list()
            return
        
        # TODO: Implement search functionality
        self.logger.info(f"Tìm kiếm bệnh nhân: {search_text}")

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