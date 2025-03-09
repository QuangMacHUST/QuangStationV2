#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Hộp thoại thông tin bệnh nhân cho QuangStation V2.
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Callable, Optional
import datetime

class PatientDialog:
    """
    Lớp hiển thị hộp thoại nhập thông tin bệnh nhân.
    """
    
    def __init__(self, parent, title="Thông tin bệnh nhân", patient_data=None, callback=None):
        """
        Khởi tạo hộp thoại.
        
        Args:
            parent: Widget cha (thường là cửa sổ chính)
            title: Tiêu đề hộp thoại
            patient_data: Dữ liệu bệnh nhân hiện có (nếu là chỉnh sửa)
            callback: Hàm callback khi lưu thông tin
        """
        self.parent = parent
        self.title = title
        self.patient_data = patient_data or {}
        self.callback = callback
        
        # Tạo cửa sổ dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("500x500")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Tạo UI
        self._create_widgets()
        
        # Đặt giá trị mặc định nếu có
        self._set_default_values()
        
    def _create_widgets(self):
        """Tạo các phần tử giao diện"""
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tiêu đề
        header = ttk.Label(main_frame, text=self.title, font=("Helvetica", 14, "bold"))
        header.pack(pady=(0, 10))
        
        # Frame chứa form
        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Thiết lập grid
        for i in range(12):
            form_frame.grid_rowconfigure(i, weight=1)
        form_frame.grid_columnconfigure(0, weight=1)
        form_frame.grid_columnconfigure(1, weight=3)
        
        # Các trường thông tin
        row = 0
        
        # Họ tên bệnh nhân
        ttk.Label(form_frame, text="Họ và tên:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.name_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.name_var, width=40).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1
        
        # Mã bệnh nhân
        ttk.Label(form_frame, text="Mã bệnh nhân:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.patient_id_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.patient_id_var, width=20).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1
        
        # Ngày sinh
        ttk.Label(form_frame, text="Ngày sinh:").grid(row=row, column=0, sticky=tk.W, pady=5)
        dob_frame = ttk.Frame(form_frame)
        dob_frame.grid(row=row, column=1, sticky=tk.W, pady=5)
        
        # Chọn ngày/tháng/năm
        self.day_var = tk.StringVar()
        self.month_var = tk.StringVar()
        self.year_var = tk.StringVar()
        
        day_values = [str(i).zfill(2) for i in range(1, 32)]
        month_values = [str(i).zfill(2) for i in range(1, 13)]
        current_year = datetime.datetime.now().year
        year_values = [str(i) for i in range(current_year-100, current_year+1)]
        
        ttk.Combobox(dob_frame, textvariable=self.day_var, values=day_values, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Label(dob_frame, text="/").pack(side=tk.LEFT)
        ttk.Combobox(dob_frame, textvariable=self.month_var, values=month_values, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Label(dob_frame, text="/").pack(side=tk.LEFT)
        ttk.Combobox(dob_frame, textvariable=self.year_var, values=year_values, width=5).pack(side=tk.LEFT, padx=2)
        row += 1
        
        # Giới tính
        ttk.Label(form_frame, text="Giới tính:").grid(row=row, column=0, sticky=tk.W, pady=5)
        gender_frame = ttk.Frame(form_frame)
        gender_frame.grid(row=row, column=1, sticky=tk.W, pady=5)
        
        self.gender_var = tk.StringVar(value="Nam")
        ttk.Radiobutton(gender_frame, text="Nam", variable=self.gender_var, value="Nam").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(gender_frame, text="Nữ", variable=self.gender_var, value="Nữ").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(gender_frame, text="Khác", variable=self.gender_var, value="Khác").pack(side=tk.LEFT, padx=5)
        row += 1
        
        # Địa chỉ
        ttk.Label(form_frame, text="Địa chỉ:").grid(row=row, column=0, sticky=tk.W + tk.N, pady=5)
        self.address_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.address_var, width=40).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1
        
        # Số điện thoại
        ttk.Label(form_frame, text="Số điện thoại:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.phone_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.phone_var, width=20).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1
        
        # Email
        ttk.Label(form_frame, text="Email:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.email_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.email_var, width=30).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1
        
        # Bác sĩ phụ trách
        ttk.Label(form_frame, text="Bác sĩ phụ trách:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.doctor_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.doctor_var, width=30).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1
        
        # Chẩn đoán
        ttk.Label(form_frame, text="Chẩn đoán:").grid(row=row, column=0, sticky=tk.W + tk.N, pady=5)
        self.diagnosis_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.diagnosis_var, width=40).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1
        
        # Ghi chú
        ttk.Label(form_frame, text="Ghi chú:").grid(row=row, column=0, sticky=tk.W + tk.N, pady=5)
        self.notes_var = tk.StringVar()
        notes_entry = tk.Text(form_frame, width=30, height=3)
        notes_entry.grid(row=row, column=1, sticky=tk.W, pady=5)
        self.notes_entry = notes_entry  # Lưu tham chiếu
        row += 1
        
        # Frame chứa nút
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # Nút lưu và hủy
        ttk.Button(button_frame, text="Hủy", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Lưu", command=self._save_data).pack(side=tk.RIGHT, padx=5)
    
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
            except Exception:
                pass
        
        # Các trường khác
        self.gender_var.set(self.patient_data.get("gender", "Nam"))
        self.address_var.set(self.patient_data.get("address", ""))
        self.phone_var.set(self.patient_data.get("phone", ""))
        self.email_var.set(self.patient_data.get("email", ""))
        self.doctor_var.set(self.patient_data.get("doctor", ""))
        self.diagnosis_var.set(self.patient_data.get("diagnosis", ""))
        
        # Ghi chú: cần xử lý đặc biệt vì dùng widget Text
        notes = self.patient_data.get("notes", "")
        if notes:
            self.notes_entry.insert("1.0", notes)
    
    def _save_data(self):
        """Lưu dữ liệu bệnh nhân"""
        # Lấy dữ liệu từ form
        name = self.name_var.get().strip()
        
        # Kiểm tra tên bệnh nhân
        if not name:
            tk.messagebox.showerror("Lỗi", "Vui lòng nhập tên bệnh nhân")
            return
        
        # Thu thập dữ liệu
        birth_date = f"{self.year_var.get()}-{self.month_var.get()}-{self.day_var.get()}"
        
        patient_data = {
            "name": name,
            "patient_id": self.patient_id_var.get().strip(),
            "birth_date": birth_date,
            "gender": self.gender_var.get(),
            "address": self.address_var.get().strip(),
            "phone": self.phone_var.get().strip(),
            "email": self.email_var.get().strip(),
            "doctor": self.doctor_var.get().strip(),
            "diagnosis": self.diagnosis_var.get().strip(),
            "notes": self.notes_entry.get("1.0", "end-1c"),
            "last_modified": datetime.datetime.now().isoformat()
        }
        
        # Gọi callback nếu có
        if self.callback:
            self.callback(patient_data)
        
        # Đóng dialog
        self.dialog.destroy()
        
    def show(self):
        """Hiển thị dialog và đợi cho đến khi nó đóng"""
        self.dialog.wait_window() 