#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Hộp thoại thông tin bệnh nhân cho QuangStation V2.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, Callable, Optional
import datetime
import re
from quangstation.core.utils.logging import get_logger
from quangstation.core.lang.language import get_text

logger = get_logger(__name__)

class PatientDialog:
    """
    Lớp hiển thị hộp thoại nhập thông tin bệnh nhân.
    """
    
    def __init__(self, parent, patient_data=None, callback=None, title=None):
        """
        Khởi tạo hộp thoại.
        
        Args:
            parent: Widget cha (thường là cửa sổ chính)
            patient_data: Dữ liệu bệnh nhân hiện có (nếu là chỉnh sửa)
            callback: Hàm callback khi lưu thông tin
            title: Tiêu đề hộp thoại (tùy chọn)
        """
        self.parent = parent
        self.patient_data = patient_data or {}
        self.callback = callback
        
        # Xác định tiêu đề dựa trên dữ liệu
        if title:
            self.title = title
        else:
            self.title = get_text("patient.edit_title", "Chỉnh sửa thông tin bệnh nhân") if patient_data else get_text("patient.add_title", "Thêm bệnh nhân mới")
        
        # Kết quả
        self.result = None
        
        # Tạo cửa sổ dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(self.title)
        self.dialog.geometry("600x650")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Đặt biểu tượng
        try:
            self.dialog.iconbitmap("resources/icons/patient.ico")
        except:
            pass  # Bỏ qua nếu không tìm thấy biểu tượng
        
        # Tạo UI
        self._create_widgets()
        
        # Đặt giá trị mặc định nếu có
        self._set_default_values()
        
        # Đặt focus vào trường đầu tiên
        self.name_entry.focus_set()
        
    def _create_widgets(self):
        """Tạo các phần tử giao diện"""
        # Sử dụng style mới
        style = ttk.Style()
        style.configure("TLabel", font=("Helvetica", 10))
        style.configure("TButton", font=("Helvetica", 10))
        style.configure("TEntry", font=("Helvetica", 10))
        style.configure("Header.TLabel", font=("Helvetica", 14, "bold"))
        
        # Frame chính
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tiêu đề
        header = ttk.Label(main_frame, text=self.title, style="Header.TLabel")
        header.pack(pady=(0, 20))
        
        # Notebook để tổ chức thông tin
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Tab thông tin cá nhân
        personal_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(personal_frame, text=get_text("patient.personal_info", "Thông tin cá nhân"))
        
        # Tab thông tin lâm sàng
        clinical_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(clinical_frame, text=get_text("patient.clinical_info", "Thông tin lâm sàng"))
        
        # Thiết lập grid cho tab thông tin cá nhân
        for i in range(10):
            personal_frame.grid_rowconfigure(i, weight=1)
        personal_frame.grid_columnconfigure(0, weight=1)
        personal_frame.grid_columnconfigure(1, weight=3)
        
        # Thiết lập grid cho tab thông tin lâm sàng
        for i in range(10):
            clinical_frame.grid_rowconfigure(i, weight=1)
        clinical_frame.grid_columnconfigure(0, weight=1)
        clinical_frame.grid_columnconfigure(1, weight=3)
        
        # === TAB THÔNG TIN CÁ NHÂN ===
        row = 0
        
        # Mã bệnh nhân
        ttk.Label(personal_frame, text=get_text("patient.id", "Mã bệnh nhân") + ":", anchor='e').grid(row=row, column=0, sticky=tk.W, pady=8, padx=5)
        self.patient_id_var = tk.StringVar()
        self.patient_id_entry = ttk.Entry(personal_frame, textvariable=self.patient_id_var, width=20)
        self.patient_id_entry.grid(row=row, column=1, sticky=tk.W, pady=8, padx=5)
        
        # Tạo ID tự động nếu là bệnh nhân mới
        if not self.patient_data:
            auto_id_button = ttk.Button(personal_frame, text=get_text("patient.generate_id", "Tạo mã"), command=self._generate_patient_id, width=10)
            auto_id_button.grid(row=row, column=1, sticky=tk.E, pady=8, padx=5)
        
        row += 1
        
        # Họ tên bệnh nhân
        ttk.Label(personal_frame, text=get_text("patient.name", "Họ và tên") + ":", anchor='e').grid(row=row, column=0, sticky=tk.W, pady=8, padx=5)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(personal_frame, textvariable=self.name_var, width=40)
        self.name_entry.grid(row=row, column=1, sticky=tk.W, pady=8, padx=5)
        row += 1
        
        # Ngày sinh
        ttk.Label(personal_frame, text=get_text("patient.birth_date", "Ngày sinh") + ":", anchor='e').grid(row=row, column=0, sticky=tk.W, pady=8, padx=5)
        dob_frame = ttk.Frame(personal_frame)
        dob_frame.grid(row=row, column=1, sticky=tk.W, pady=8, padx=5)
        
        # Chọn ngày/tháng/năm
        self.day_var = tk.StringVar()
        self.month_var = tk.StringVar()
        self.year_var = tk.StringVar()
        
        day_values = [str(i).zfill(2) for i in range(1, 32)]
        month_values = [str(i).zfill(2) for i in range(1, 13)]
        current_year = datetime.datetime.now().year
        year_values = [str(i) for i in range(current_year-100, current_year+1)]
        
        ttk.Label(dob_frame, text=get_text("common.day", "Ngày") + ":").pack(side=tk.LEFT, padx=2)
        self.day_combo = ttk.Combobox(dob_frame, textvariable=self.day_var, values=day_values, width=3)
        self.day_combo.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(dob_frame, text=get_text("common.month", "Tháng") + ":").pack(side=tk.LEFT, padx=2)
        self.month_combo = ttk.Combobox(dob_frame, textvariable=self.month_var, values=month_values, width=3)
        self.month_combo.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(dob_frame, text=get_text("common.year", "Năm") + ":").pack(side=tk.LEFT, padx=2)
        self.year_combo = ttk.Combobox(dob_frame, textvariable=self.year_var, values=year_values, width=5)
        self.year_combo.pack(side=tk.LEFT, padx=2)
        
        # Đặt giá trị mặc định cho ngày sinh
        today = datetime.datetime.now()
        self.day_var.set(str(today.day).zfill(2))
        self.month_var.set(str(today.month).zfill(2))
        self.year_var.set(str(today.year - 40))  # Mặc định 40 tuổi
        
        row += 1
        
        # Giới tính
        ttk.Label(personal_frame, text=get_text("patient.gender", "Giới tính") + ":", anchor='e').grid(row=row, column=0, sticky=tk.W, pady=8, padx=5)
        gender_frame = ttk.Frame(personal_frame)
        gender_frame.grid(row=row, column=1, sticky=tk.W, pady=8, padx=5)
        
        self.gender_var = tk.StringVar(value="Nam")
        ttk.Radiobutton(gender_frame, text=get_text("patient.male", "Nam"), variable=self.gender_var, value="Nam").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(gender_frame, text=get_text("patient.female", "Nữ"), variable=self.gender_var, value="Nữ").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(gender_frame, text=get_text("patient.other", "Khác"), variable=self.gender_var, value="Khác").pack(side=tk.LEFT, padx=5)
        row += 1
        
        # Địa chỉ
        ttk.Label(personal_frame, text=get_text("patient.address", "Địa chỉ") + ":", anchor='e').grid(row=row, column=0, sticky=tk.W + tk.N, pady=8, padx=5)
        self.address_var = tk.StringVar()
        self.address_entry = ttk.Entry(personal_frame, textvariable=self.address_var, width=40)
        self.address_entry.grid(row=row, column=1, sticky=tk.W, pady=8, padx=5)
        row += 1
        
        # Số điện thoại
        ttk.Label(personal_frame, text=get_text("patient.phone", "Số điện thoại") + ":", anchor='e').grid(row=row, column=0, sticky=tk.W, pady=8, padx=5)
        self.phone_var = tk.StringVar()
        self.phone_entry = ttk.Entry(personal_frame, textvariable=self.phone_var, width=20)
        self.phone_entry.grid(row=row, column=1, sticky=tk.W, pady=8, padx=5)
        row += 1
        
        # Email
        ttk.Label(personal_frame, text=get_text("patient.email", "Email") + ":", anchor='e').grid(row=row, column=0, sticky=tk.W, pady=8, padx=5)
        self.email_var = tk.StringVar()
        self.email_entry = ttk.Entry(personal_frame, textvariable=self.email_var, width=30)
        self.email_entry.grid(row=row, column=1, sticky=tk.W, pady=8, padx=5)
        row += 1
        
        # === TAB THÔNG TIN LÂM SÀNG ===
        row = 0
        
        # Bác sĩ phụ trách
        ttk.Label(clinical_frame, text=get_text("patient.doctor", "Bác sĩ phụ trách") + ":", anchor='e').grid(row=row, column=0, sticky=tk.W, pady=8, padx=5)
        self.doctor_var = tk.StringVar()
        self.doctor_entry = ttk.Entry(clinical_frame, textvariable=self.doctor_var, width=30)
        self.doctor_entry.grid(row=row, column=1, sticky=tk.W, pady=8, padx=5)
        row += 1
        
        # Chẩn đoán
        ttk.Label(clinical_frame, text=get_text("patient.diagnosis", "Chẩn đoán") + ":", anchor='e').grid(row=row, column=0, sticky=tk.W + tk.N, pady=8, padx=5)
        self.diagnosis_var = tk.StringVar()
        self.diagnosis_entry = ttk.Entry(clinical_frame, textvariable=self.diagnosis_var, width=40)
        self.diagnosis_entry.grid(row=row, column=1, sticky=tk.W, pady=8, padx=5)
        row += 1
        
        # Ngày chẩn đoán
        ttk.Label(clinical_frame, text=get_text("patient.diagnosis_date", "Ngày chẩn đoán") + ":", anchor='e').grid(row=row, column=0, sticky=tk.W, pady=8, padx=5)
        diagnosis_date_frame = ttk.Frame(clinical_frame)
        diagnosis_date_frame.grid(row=row, column=1, sticky=tk.W, pady=8, padx=5)
        
        # Chọn ngày/tháng/năm cho ngày chẩn đoán
        self.diagnosis_day_var = tk.StringVar()
        self.diagnosis_month_var = tk.StringVar()
        self.diagnosis_year_var = tk.StringVar()
        
        ttk.Label(diagnosis_date_frame, text=get_text("common.day", "Ngày") + ":").pack(side=tk.LEFT, padx=2)
        ttk.Combobox(diagnosis_date_frame, textvariable=self.diagnosis_day_var, values=day_values, width=3).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(diagnosis_date_frame, text=get_text("common.month", "Tháng") + ":").pack(side=tk.LEFT, padx=2)
        ttk.Combobox(diagnosis_date_frame, textvariable=self.diagnosis_month_var, values=month_values, width=3).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(diagnosis_date_frame, text=get_text("common.year", "Năm") + ":").pack(side=tk.LEFT, padx=2)
        ttk.Combobox(diagnosis_date_frame, textvariable=self.diagnosis_year_var, values=year_values, width=5).pack(side=tk.LEFT, padx=2)
        
        # Đặt giá trị mặc định cho ngày chẩn đoán
        self.diagnosis_day_var.set(str(today.day).zfill(2))
        self.diagnosis_month_var.set(str(today.month).zfill(2))
        self.diagnosis_year_var.set(str(today.year))
        
        row += 1
        
        # Loại ung thư
        ttk.Label(clinical_frame, text=get_text("patient.cancer_type", "Loại ung thư") + ":", anchor='e').grid(row=row, column=0, sticky=tk.W, pady=8, padx=5)
        self.cancer_type_var = tk.StringVar()
        cancer_types = ["Ung thư phổi", "Ung thư vú", "Ung thư đại trực tràng", "Ung thư tuyến tiền liệt", 
                        "Ung thư não", "Ung thư gan", "Ung thư dạ dày", "Ung thư tụy", "Ung thư thực quản", 
                        "Ung thư máu", "Ung thư da", "Ung thư tử cung", "Ung thư buồng trứng", "Khác"]
        self.cancer_type_combo = ttk.Combobox(clinical_frame, textvariable=self.cancer_type_var, values=cancer_types, width=30)
        self.cancer_type_combo.grid(row=row, column=1, sticky=tk.W, pady=8, padx=5)
        row += 1
        
        # Giai đoạn
        ttk.Label(clinical_frame, text=get_text("patient.stage", "Giai đoạn") + ":", anchor='e').grid(row=row, column=0, sticky=tk.W, pady=8, padx=5)
        stage_frame = ttk.Frame(clinical_frame)
        stage_frame.grid(row=row, column=1, sticky=tk.W, pady=8, padx=5)
        
        self.stage_var = tk.StringVar(value="I")
        ttk.Radiobutton(stage_frame, text="I", variable=self.stage_var, value="I").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(stage_frame, text="II", variable=self.stage_var, value="II").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(stage_frame, text="III", variable=self.stage_var, value="III").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(stage_frame, text="IV", variable=self.stage_var, value="IV").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(stage_frame, text=get_text("patient.unknown", "Không xác định"), variable=self.stage_var, value="Không xác định").pack(side=tk.LEFT, padx=5)
        row += 1
        
        # Ghi chú
        ttk.Label(clinical_frame, text=get_text("patient.notes", "Ghi chú") + ":", anchor='e').grid(row=row, column=0, sticky=tk.W + tk.N, pady=8, padx=5)
        self.notes_text = tk.Text(clinical_frame, width=40, height=6)
        self.notes_text.grid(row=row, column=1, sticky=tk.W, pady=8, padx=5)
        
        # Thêm scrollbar cho ghi chú
        notes_scroll = ttk.Scrollbar(clinical_frame, orient='vertical', command=self.notes_text.yview)
        notes_scroll.grid(row=row, column=1, sticky=tk.E + tk.N + tk.S, pady=8)
        self.notes_text.configure(yscrollcommand=notes_scroll.set)
        
        row += 1
        
        # Frame chứa nút
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # Nút lưu và hủy
        ttk.Button(button_frame, text=get_text("common.cancel", "Hủy"), command=self.dialog.destroy, width=10).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text=get_text("common.save", "Lưu"), command=self._save_data, width=10).pack(side=tk.RIGHT, padx=5)
    
    def _set_default_values(self):
        """Đặt giá trị mặc định từ dữ liệu bệnh nhân hiện có"""
        if not self.patient_data:
            return
        
        # Đặt giá trị cho các biến
        self.name_var.set(self.patient_data.get("name", ""))
        self.patient_id_var.set(self.patient_data.get("patient_id", ""))
        
        # Xử lý ngày sinh
        birth_date = self.patient_data.get("birth_date", "")
        if birth_date:
            try:
                # Chuyển đổi chuỗi ngày tháng thành ngày/tháng/năm
                if "-" in birth_date:
                    parts = birth_date.split("-")
                    if len(parts) == 3:
                        self.year_var.set(parts[0])
                        self.month_var.set(parts[1])
                        self.day_var.set(parts[2])
                elif "/" in birth_date:
                    parts = birth_date.split("/")
                    if len(parts) == 3:
                        self.day_var.set(parts[0])
                        self.month_var.set(parts[1])
                        self.year_var.set(parts[2])
            except Exception as e:
                logger.error(f"Lỗi khi xử lý ngày sinh: {str(e)}")
        
        # Các trường khác
        self.gender_var.set(self.patient_data.get("gender", "Nam"))
        self.address_var.set(self.patient_data.get("address", ""))
        self.phone_var.set(self.patient_data.get("phone", ""))
        self.email_var.set(self.patient_data.get("email", ""))
        self.doctor_var.set(self.patient_data.get("doctor", ""))
        self.diagnosis_var.set(self.patient_data.get("diagnosis", ""))
        
        # Xử lý ngày chẩn đoán
        diagnosis_date = self.patient_data.get("diagnosis_date", "")
        if diagnosis_date:
            try:
                if "-" in diagnosis_date:
                    parts = diagnosis_date.split("-")
                    if len(parts) == 3:
                        self.diagnosis_year_var.set(parts[0])
                        self.diagnosis_month_var.set(parts[1])
                        self.diagnosis_day_var.set(parts[2])
                elif "/" in diagnosis_date:
                    parts = diagnosis_date.split("/")
                    if len(parts) == 3:
                        self.diagnosis_day_var.set(parts[0])
                        self.diagnosis_month_var.set(parts[1])
                        self.diagnosis_year_var.set(parts[2])
            except Exception as e:
                logger.error(f"Lỗi khi xử lý ngày chẩn đoán: {str(e)}")
        
        # Loại ung thư và giai đoạn
        self.cancer_type_var.set(self.patient_data.get("cancer_type", ""))
        self.stage_var.set(self.patient_data.get("stage", "I"))
        
        # Ghi chú: cần xử lý đặc biệt vì dùng widget Text
        notes = self.patient_data.get("notes", "")
        if notes:
            self.notes_text.delete("1.0", tk.END)
            self.notes_text.insert("1.0", notes)
    
    def _generate_patient_id(self):
        """Tạo mã bệnh nhân tự động"""
        # Tạo mã bệnh nhân dựa trên thời gian hiện tại
        now = datetime.datetime.now()
        prefix = "PT"
        timestamp = now.strftime("%y%m%d%H%M")
        patient_id = f"{prefix}{timestamp}"
        
        # Đặt giá trị cho trường mã bệnh nhân
        self.patient_id_var.set(patient_id)
    
    def _validate_email(self, email):
        """Xác thực định dạng email"""
        if not email:
            return True  # Email không bắt buộc
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _validate_phone(self, phone):
        """Xác thực số điện thoại"""
        if not phone:
            return True  # Số điện thoại không bắt buộc
        
        # Chấp nhận các định dạng: 0912345678, 091-234-5678, +84912345678
        pattern = r'^(\+\d{1,3})?[\s.-]?\d{3}[\s.-]?\d{3}[\s.-]?\d{3,4}$'
        return re.match(pattern, phone) is not None
    
    def _save_data(self):
        """Lưu dữ liệu bệnh nhân"""
        try:
            # Lấy dữ liệu từ form
            name = self.name_var.get().strip()
            patient_id = self.patient_id_var.get().strip()
            
            # Kiểm tra các trường bắt buộc
            if not name:
                messagebox.showerror(
                    get_text("common.error", "Lỗi"),
                    get_text("patient.name_required", "Vui lòng nhập tên bệnh nhân")
                )
                self.name_entry.focus_set()
                return
            
            if not patient_id:
                messagebox.showerror(
                    get_text("common.error", "Lỗi"),
                    get_text("patient.id_required", "Vui lòng nhập mã bệnh nhân")
                )
                self.patient_id_entry.focus_set()
                return
            
            # Kiểm tra định dạng email
            email = self.email_var.get().strip()
            if email and not self._validate_email(email):
                messagebox.showerror(
                    get_text("common.error", "Lỗi"),
                    get_text("patient.invalid_email", "Định dạng email không hợp lệ")
                )
                self.email_entry.focus_set()
                return
            
            # Kiểm tra định dạng số điện thoại
            phone = self.phone_var.get().strip()
            if phone and not self._validate_phone(phone):
                messagebox.showerror(
                    get_text("common.error", "Lỗi"),
                    get_text("patient.invalid_phone", "Định dạng số điện thoại không hợp lệ")
                )
                self.phone_entry.focus_set()
                return
            
            # Thu thập dữ liệu ngày sinh
            birth_date = f"{self.year_var.get()}-{self.month_var.get()}-{self.day_var.get()}"
            
            # Thu thập dữ liệu ngày chẩn đoán
            diagnosis_date = f"{self.diagnosis_year_var.get()}-{self.diagnosis_month_var.get()}-{self.diagnosis_day_var.get()}"
            
            # Thu thập tất cả dữ liệu
            patient_data = {
                "name": name,
                "patient_id": patient_id,
                "birth_date": birth_date,
                "gender": self.gender_var.get(),
                "address": self.address_var.get().strip(),
                "phone": phone,
                "email": email,
                "doctor": self.doctor_var.get().strip(),
                "diagnosis": self.diagnosis_var.get().strip(),
                "diagnosis_date": diagnosis_date,
                "cancer_type": self.cancer_type_var.get(),
                "stage": self.stage_var.get(),
                "notes": self.notes_text.get("1.0", "end-1c"),
                "last_modified": datetime.datetime.now().isoformat()
            }
            
            # Lưu kết quả
            self.result = patient_data
            
            # Gọi callback nếu có
            if self.callback:
                self.callback(patient_data)
            
            # Đóng dialog
            self.dialog.destroy()
            
        except Exception as e:
            logger.exception(f"Lỗi khi lưu dữ liệu bệnh nhân: {str(e)}")
            messagebox.showerror(
                get_text("common.error", "Lỗi"),
                f"{get_text('patient.save_error', 'Lỗi khi lưu dữ liệu')}: {str(e)}"
            )
        
    def show(self):
        """Hiển thị dialog và đợi cho đến khi nó đóng"""
        self.dialog.wait_window()
        return self.result 