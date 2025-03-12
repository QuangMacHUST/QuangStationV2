#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module cung cấp giao diện hiển thị thông tin bệnh nhân cho QuangStation V2.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Dict, Any, List, Optional

from quangstation.core.utils.logging import get_logger
from quangstation.core.lang.language import get_text
from quangstation.clinical.data_management.patient_db import PatientDatabase, Patient
from quangstation.clinical.data_management.session_management import SessionManager
from quangstation.gui.dialogs.patient_dialog import PatientDialog

logger = get_logger(__name__)

class PatientView(ttk.Frame):
    """
    Giao diện hiển thị danh sách bệnh nhân và thông tin chi tiết.
    """
    
    def __init__(self, parent, on_patient_selected: Callable = None, **kwargs):
        """
        Khởi tạo giao diện hiển thị bệnh nhân.
        
        Args:
            parent: Widget cha
            on_patient_selected: Callback khi chọn bệnh nhân
        """
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.on_patient_selected = on_patient_selected
        
        # Khởi tạo cơ sở dữ liệu và quản lý phiên
        self.db = PatientDatabase()
        self.session_manager = SessionManager()
        
        # Biến lưu trữ dữ liệu
        self.current_patient_id = None
        self.patients_data = []
        
        # Xây dựng giao diện
        self._create_widgets()
        self._create_layout()
        
        # Tải danh sách bệnh nhân
        self.load_patients()
        
    def _create_widgets(self):
        """Tạo các widget cho giao diện"""
        # Frame danh sách bệnh nhân
        self.patients_frame = ttk.LabelFrame(self, text=get_text("patient.list", "Patient List"))
        
        # Tạo thanh công cụ
        self.toolbar_frame = ttk.Frame(self.patients_frame)
        
        self.add_button = ttk.Button(
            self.toolbar_frame, 
            text=get_text("common.add", "Add"),
            command=self._add_patient
        )
        
        self.refresh_button = ttk.Button(
            self.toolbar_frame, 
            text=get_text("common.refresh", "Refresh"),
            command=self.load_patients
        )
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.toolbar_frame, textvariable=self.search_var, width=20)
        self.search_entry.bind("<KeyRelease>", self._filter_patients)
        
        self.search_label = ttk.Label(self.toolbar_frame, text=get_text("common.search", "Search") + ":")
        
        # Tạo danh sách bệnh nhân
        self.patients_tree = ttk.Treeview(
            self.patients_frame, 
            columns=('id', 'name', 'date', 'studies'),
            show='headings',
            height=15
        )
        
        self.patients_tree.heading('id', text=get_text("patient.id", "ID"))
        self.patients_tree.heading('name', text=get_text("patient.name", "Name"))
        self.patients_tree.heading('date', text=get_text("patient.date", "Date"))
        self.patients_tree.heading('studies', text=get_text("patient.studies", "Studies"))
        
        self.patients_tree.column('id', width=100)
        self.patients_tree.column('name', width=200)
        self.patients_tree.column('date', width=100)
        self.patients_tree.column('studies', width=80)
        
        # Binding cho danh sách bệnh nhân
        self.patients_tree.bind('<<TreeviewSelect>>', self._on_patient_selected)
        self.patients_tree.bind('<Double-1>', self._on_patient_double_click)
        
        # Scrollbar cho danh sách bệnh nhân
        self.patients_scroll = ttk.Scrollbar(self.patients_frame, orient='vertical', command=self.patients_tree.yview)
        self.patients_tree.configure(yscrollcommand=self.patients_scroll.set)
        
        # Menu chuột phải cho danh sách bệnh nhân
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label=get_text("common.open", "Open"), command=self._open_patient)
        self.context_menu.add_command(label=get_text("common.edit", "Edit"), command=self._edit_patient)
        self.context_menu.add_separator()
        self.context_menu.add_command(label=get_text("common.delete", "Delete"), command=self._delete_patient)
        
        self.patients_tree.bind("<Button-3>", self._show_context_menu)
        
        # Frame thông tin chi tiết bệnh nhân
        self.details_frame = ttk.LabelFrame(self, text=get_text("patient.details", "Patient Details"))
        
        # Các label thông tin
        self.info_frame = ttk.Frame(self.details_frame)
        
        self.id_label = ttk.Label(self.info_frame, text=get_text("patient.id", "ID") + ":", width=15, anchor='e')
        self.id_value = ttk.Label(self.info_frame, text="", width=30, anchor='w')
        
        self.name_label = ttk.Label(self.info_frame, text=get_text("patient.name", "Name") + ":", width=15, anchor='e')
        self.name_value = ttk.Label(self.info_frame, text="", width=30, anchor='w')
        
        self.birth_label = ttk.Label(self.info_frame, text=get_text("patient.birth", "Birth Date") + ":", width=15, anchor='e')
        self.birth_value = ttk.Label(self.info_frame, text="", width=30, anchor='w')
        
        self.gender_label = ttk.Label(self.info_frame, text=get_text("patient.gender", "Gender") + ":", width=15, anchor='e')
        self.gender_value = ttk.Label(self.info_frame, text="", width=30, anchor='w')
        
        self.diagnosis_label = ttk.Label(self.info_frame, text=get_text("patient.diagnosis", "Diagnosis") + ":", width=15, anchor='e')
        self.diagnosis_value = ttk.Label(self.info_frame, text="", width=30, anchor='w')
        
        # Thêm các label mới
        self.cancer_type_label = ttk.Label(self.info_frame, text=get_text("patient.cancer_type", "Cancer Type") + ":", width=15, anchor='e')
        self.cancer_type_value = ttk.Label(self.info_frame, text="", width=30, anchor='w')
        
        self.stage_label = ttk.Label(self.info_frame, text=get_text("patient.stage", "Stage") + ":", width=15, anchor='e')
        self.stage_value = ttk.Label(self.info_frame, text="", width=30, anchor='w')
        
        self.doctor_label = ttk.Label(self.info_frame, text=get_text("patient.doctor", "Doctor") + ":", width=15, anchor='e')
        self.doctor_value = ttk.Label(self.info_frame, text="", width=30, anchor='w')
        
        # Tab thông tin chi tiết
        self.details_notebook = ttk.Notebook(self.details_frame)
        
        # Tab dữ liệu hình ảnh
        self.images_frame = ttk.Frame(self.details_notebook)
        self.details_notebook.add(self.images_frame, text=get_text("patient.images", "Images"))
        
        # Danh sách hình ảnh
        self.images_tree = ttk.Treeview(
            self.images_frame, 
            columns=('date', 'type', 'slices', 'description'),
            show='headings',
            height=8
        )
        
        self.images_tree.heading('date', text=get_text("common.date", "Date"))
        self.images_tree.heading('type', text=get_text("common.type", "Type"))
        self.images_tree.heading('slices', text=get_text("common.slices", "Slices"))
        self.images_tree.heading('description', text=get_text("common.description", "Description"))
        
        self.images_tree.column('date', width=100)
        self.images_tree.column('type', width=80)
        self.images_tree.column('slices', width=60)
        self.images_tree.column('description', width=200)
        
        # Scrollbar cho danh sách hình ảnh
        self.images_scroll = ttk.Scrollbar(self.images_frame, orient='vertical', command=self.images_tree.yview)
        self.images_tree.configure(yscrollcommand=self.images_scroll.set)
        
        # Tab cấu trúc
        self.structures_frame = ttk.Frame(self.details_notebook)
        self.details_notebook.add(self.structures_frame, text=get_text("patient.structures", "Structures"))
        
        # Danh sách cấu trúc
        self.structures_tree = ttk.Treeview(
            self.structures_frame, 
            columns=('name', 'type', 'color', 'volume'),
            show='headings',
            height=8
        )
        
        self.structures_tree.heading('name', text=get_text("common.name", "Name"))
        self.structures_tree.heading('type', text=get_text("common.type", "Type"))
        self.structures_tree.heading('color', text=get_text("common.color", "Color"))
        self.structures_tree.heading('volume', text=get_text("common.volume", "Volume (cc)"))
        
        self.structures_tree.column('name', width=150)
        self.structures_tree.column('type', width=100)
        self.structures_tree.column('color', width=80)
        self.structures_tree.column('volume', width=100)
        
        # Scrollbar cho danh sách cấu trúc
        self.structures_scroll = ttk.Scrollbar(self.structures_frame, orient='vertical', command=self.structures_tree.yview)
        self.structures_tree.configure(yscrollcommand=self.structures_scroll.set)
        
        # Tab kế hoạch
        self.plans_frame = ttk.Frame(self.details_notebook)
        self.details_notebook.add(self.plans_frame, text=get_text("patient.plans", "Plans"))
        
        # Danh sách kế hoạch
        self.plans_tree = ttk.Treeview(
            self.plans_frame, 
            columns=('name', 'date', 'technique', 'status'),
            show='headings',
            height=8
        )
        
        self.plans_tree.heading('name', text=get_text("common.name", "Name"))
        self.plans_tree.heading('date', text=get_text("common.date", "Date"))
        self.plans_tree.heading('technique', text=get_text("common.technique", "Technique"))
        self.plans_tree.heading('status', text=get_text("common.status", "Status"))
        
        self.plans_tree.column('name', width=150)
        self.plans_tree.column('date', width=100)
        self.plans_tree.column('technique', width=100)
        self.plans_tree.column('status', width=80)
        
        # Scrollbar cho danh sách kế hoạch
        self.plans_scroll = ttk.Scrollbar(self.plans_frame, orient='vertical', command=self.plans_tree.yview)
        self.plans_tree.configure(yscrollcommand=self.plans_scroll.set)
        
        # Tab phiên làm việc
        self.sessions_frame = ttk.Frame(self.details_notebook)
        self.details_notebook.add(self.sessions_frame, text=get_text("patient.sessions", "Sessions"))
        
        # Danh sách phiên làm việc
        self.sessions_tree = ttk.Treeview(
            self.sessions_frame, 
            columns=('id', 'date', 'user', 'status'),
            show='headings',
            height=8
        )
        
        self.sessions_tree.heading('id', text=get_text("common.id", "ID"))
        self.sessions_tree.heading('date', text=get_text("common.date", "Date"))
        self.sessions_tree.heading('user', text=get_text("common.user", "User"))
        self.sessions_tree.heading('status', text=get_text("common.status", "Status"))
        
        self.sessions_tree.column('id', width=100)
        self.sessions_tree.column('date', width=150)
        self.sessions_tree.column('user', width=100)
        self.sessions_tree.column('status', width=80)
        
        # Scrollbar cho danh sách phiên làm việc
        self.sessions_scroll = ttk.Scrollbar(self.sessions_frame, orient='vertical', command=self.sessions_tree.yview)
        self.sessions_tree.configure(yscrollcommand=self.sessions_scroll.set)
        
        # Khung nút tác vụ
        self.action_frame = ttk.Frame(self.details_frame)
        
        self.open_button = ttk.Button(
            self.action_frame, 
            text=get_text("common.open", "Open"),
            command=self._open_patient,
            state='disabled'
        )
        
        self.edit_button = ttk.Button(
            self.action_frame, 
            text=get_text("common.edit", "Edit"),
            command=self._edit_patient,
            state='disabled'
        )
        
        self.delete_button = ttk.Button(
            self.action_frame, 
            text=get_text("common.delete", "Delete"),
            command=self._delete_patient,
            state='disabled'
        )
    
    def _create_layout(self):
        """Thiết lập layout cho giao diện"""
        # Layout cho thanh công cụ
        self.search_label.pack(side='left', padx=5, pady=5)
        self.search_entry.pack(side='left', padx=5, pady=5)
        self.refresh_button.pack(side='right', padx=5, pady=5)
        self.add_button.pack(side='right', padx=5, pady=5)
        
        # Layout cho danh sách bệnh nhân
        self.toolbar_frame.pack(fill='x', padx=5, pady=5)
        self.patients_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        self.patients_scroll.pack(side='right', fill='y', pady=5)
        
        # Layout cho thông tin bệnh nhân
        row = 0
        self.id_label.grid(row=row, column=0, sticky=tk.W, pady=2)
        self.id_value.grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1
        
        self.name_label.grid(row=row, column=0, sticky=tk.W, pady=2)
        self.name_value.grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1
        
        self.birth_label.grid(row=row, column=0, sticky=tk.W, pady=2)
        self.birth_value.grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1
        
        self.gender_label.grid(row=row, column=0, sticky=tk.W, pady=2)
        self.gender_value.grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1
        
        self.diagnosis_label.grid(row=row, column=0, sticky=tk.W, pady=2)
        self.diagnosis_value.grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1
        
        # Thêm các trường mới vào bố cục
        self.cancer_type_label.grid(row=row, column=0, sticky=tk.W, pady=2)
        self.cancer_type_value.grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1
        
        self.stage_label.grid(row=row, column=0, sticky=tk.W, pady=2)
        self.stage_value.grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1
        
        self.doctor_label.grid(row=row, column=0, sticky=tk.W, pady=2)
        self.doctor_value.grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1
        
        # Layout cho tab hình ảnh
        self.images_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        self.images_scroll.pack(side='right', fill='y', pady=5)
        
        # Layout cho tab cấu trúc
        self.structures_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        self.structures_scroll.pack(side='right', fill='y', pady=5)
        
        # Layout cho tab kế hoạch
        self.plans_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        self.plans_scroll.pack(side='right', fill='y', pady=5)
        
        # Layout cho tab phiên làm việc
        self.sessions_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        self.sessions_scroll.pack(side='right', fill='y', pady=5)
        
        # Layout cho nút tác vụ
        self.open_button.pack(side='left', padx=5, pady=5)
        self.edit_button.pack(side='left', padx=5, pady=5)
        self.delete_button.pack(side='left', padx=5, pady=5)
        
        # Layout cho khung thông tin chi tiết
        self.info_frame.pack(fill='x', padx=5, pady=5)
        self.details_notebook.pack(fill='both', expand=True, padx=5, pady=5)
        self.action_frame.pack(fill='x', padx=5, pady=5)
        
        # Layout chính
        self.patients_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        self.details_frame.pack(side='right', fill='both', expand=True, padx=5, pady=5)
    
    def load_patients(self):
        """Tải danh sách bệnh nhân từ cơ sở dữ liệu"""
        # Xóa dữ liệu cũ
        self.patients_tree.delete(*self.patients_tree.get_children())
        
        try:
            # Lấy danh sách bệnh nhân
            patients = self.db.get_all_patients()
            self.patients_data = patients
            
            # Hiển thị danh sách bệnh nhân
            for patient in patients:
                patient_id = patient.patient_id
                name = patient.demographics.get('name', 'Unknown')
                date = patient.demographics.get('birth_date', '')
                
                # Đếm số lượng nghiên cứu
                studies_count = 0
                if hasattr(patient, 'images'):
                    studies_count += len(patient.images)
                
                # Thêm vào bảng
                self.patients_tree.insert('', 'end', values=(patient_id, name, date, studies_count))
            
            # Thông báo số lượng bệnh nhân
            logger.info(f"Đã tải {len(patients)} bệnh nhân")
            
        except Exception as error:
            logger.exception(f"Lỗi khi tải danh sách bệnh nhân: {str(error)}")
            messagebox.showerror(
                get_text("common.error", "Error"),
                f"{get_text('patient.load_error', 'Error loading patient list')}: {str(error)}"
            )
    
    def _filter_patients(self, event):
        """Lọc danh sách bệnh nhân theo từ khóa tìm kiếm"""
        # Lấy từ khóa tìm kiếm
        search_term = self.search_var.get().lower()
        
        # Xóa dữ liệu cũ
        self.patients_tree.delete(*self.patients_tree.get_children())
        
        # Lọc và hiển thị danh sách bệnh nhân
        for patient in self.patients_data:
            patient_id = patient.patient_id
            name = patient.demographics.get('name', 'Unknown')
            date = patient.demographics.get('birth_date', '')
            
            # Đếm số lượng nghiên cứu
            studies_count = 0
            if hasattr(patient, 'images'):
                studies_count += len(patient.images)
            
            # Kiểm tra xem từ khóa tìm kiếm có khớp không
            if (search_term in patient_id.lower() or 
                search_term in name.lower()):
                # Thêm vào bảng
                self.patients_tree.insert('', 'end', values=(patient_id, name, date, studies_count))
    
    def _on_patient_selected(self, event):
        """Xử lý khi chọn bệnh nhân từ danh sách"""
        # Lấy dòng đang chọn
        selection = self.patients_tree.selection()
        if not selection:
            return
        
        # Lấy ID bệnh nhân
        item = self.patients_tree.item(selection[0])
        patient_id = item['values'][0]
        
        # Cập nhật bệnh nhân hiện tại
        self.current_patient_id = patient_id
        
        # Tải thông tin chi tiết
        self._load_patient_details(patient_id)
        
        # Kích hoạt các nút
        self.open_button.config(state='normal')
        self.edit_button.config(state='normal')
        self.delete_button.config(state='normal')
        
        # Gọi callback nếu có
        if self.on_patient_selected:
            self.on_patient_selected(patient_id)
    
    def _on_patient_double_click(self, event):
        """Xử lý khi double-click vào bệnh nhân"""
        self._open_patient()
    
    def _show_context_menu(self, event):
        """Hiển thị menu chuột phải"""
        # Kiểm tra xem có dòng nào được chọn không
        item = self.patients_tree.identify_row(event.y)
        if item:
            # Chọn dòng
            self.patients_tree.selection_set(item)
            
            # Hiển thị menu
            self.context_menu.post(event.x_root, event.y_root)
    
    def _load_patient_details(self, patient_id: str):
        """Tải thông tin chi tiết của bệnh nhân"""
        try:
            # Lấy thông tin bệnh nhân
            patient = self.db.get_patient(patient_id)
            if not patient:
                logger.error(f"Không tìm thấy bệnh nhân với ID: {patient_id}")
                return
            
            # Cập nhật thông tin hiển thị
            self.id_value.config(text=patient_id)
            self.name_value.config(text=patient.demographics.get('name', 'Unknown'))
            self.birth_value.config(text=patient.demographics.get('birth_date', ''))
            self.gender_value.config(text=patient.demographics.get('gender', ''))
            self.diagnosis_value.config(text=patient.clinical_info.get('diagnosis', ''))
            
            # Cập nhật các trường mới
            self.cancer_type_value.config(text=patient.clinical_info.get('cancer_type', ''))
            self.stage_value.config(text=patient.clinical_info.get('stage', ''))
            self.doctor_value.config(text=patient.clinical_info.get('physician', ''))
            
            # Xóa dữ liệu cũ
            self.images_tree.delete(*self.images_tree.get_children())
            self.structures_tree.delete(*self.structures_tree.get_children())
            self.plans_tree.delete(*self.plans_tree.get_children())
            self.sessions_tree.delete(*self.sessions_tree.get_children())
            
            # Tải dữ liệu hình ảnh
            if hasattr(patient, 'images'):
                for image_id, image_data in patient.images.items():
                    modality = image_data.get('metadata', {}).get('modality', 'Unknown')
                    date = image_data.get('metadata', {}).get('study_date', '')
                    slices = image_data.get('metadata', {}).get('num_slices', 0)
                    description = image_data.get('metadata', {}).get('study_description', '')
                    
                    self.images_tree.insert('', 'end', values=(date, modality, slices, description))
            
            # Tải dữ liệu cấu trúc
            if hasattr(patient, 'structures'):
                for struct_id, struct_data in patient.structures.items():
                    name = struct_data.get('name', 'Unknown')
                    struct_type = struct_data.get('type', 'Unknown')
                    color = struct_data.get('color', '')
                    volume = struct_data.get('volume', 0)
                    
                    self.structures_tree.insert('', 'end', values=(name, struct_type, color, volume))
            
            # Tải dữ liệu kế hoạch
            if hasattr(patient, 'plans'):
                for plan_id, plan_data in patient.plans.items():
                    name = plan_data.get('name', 'Unknown')
                    date = plan_data.get('created_date', '')
                    technique = plan_data.get('technique', '')
                    status = plan_data.get('status', 'Draft')
                    
                    self.plans_tree.insert('', 'end', values=(name, date, technique, status))
            
            # Tải dữ liệu phiên làm việc
            sessions = self.session_manager.get_sessions_for_patient(patient_id)
            for session in sessions:
                session_id = session.get('session_id', '')
                date = session.get('created_date', '')
                user = session.get('user', 'Unknown')
                status = session.get('status', 'Active')
                
                self.sessions_tree.insert('', 'end', values=(session_id, date, user, status))
            
        except Exception as error:
            logger.exception(f"Lỗi khi tải thông tin chi tiết bệnh nhân: {str(error)}")
            messagebox.showerror(
                get_text("common.error", "Error"),
                f"{get_text('patient.load_details_error', 'Error loading patient details')}: {str(error)}"
            )
    
    def _add_patient(self):
        """Thêm bệnh nhân mới"""
        try:
            # Hiển thị dialog thêm bệnh nhân
            dialog = PatientDialog(self)
            patient_info = dialog.show()
            
            if patient_info:
                # Tạo đối tượng Patient
                patient = Patient(patient_id=patient_info.get('patient_id'))
                
                # Cập nhật thông tin
                patient.demographics.update({
                    'name': patient_info.get('name', ''),
                    'birth_date': patient_info.get('birth_date', ''),
                    'gender': patient_info.get('gender', ''),
                    'address': patient_info.get('address', ''),
                    'phone': patient_info.get('phone', ''),
                    'email': patient_info.get('email', '')
                })
                
                patient.clinical_info.update({
                    'diagnosis': patient_info.get('diagnosis', ''),
                    'diagnosis_date': patient_info.get('diagnosis_date', ''),
                    'cancer_type': patient_info.get('cancer_type', ''),
                    'stage': patient_info.get('stage', ''),
                    'physician': patient_info.get('doctor', ''),
                    'notes': patient_info.get('notes', '')
                })
                
                # Thêm vào cơ sở dữ liệu
                self.db.add_patient(patient)
                
                # Tải lại danh sách
                self.load_patients()
                
                # Thông báo thành công
                messagebox.showinfo(
                    get_text("common.success", "Thành công"),
                    get_text("patient.add_success", "Thêm bệnh nhân thành công")
                )
                
        except Exception as error:
            logger.exception(f"Lỗi khi thêm bệnh nhân: {str(error)}")
            messagebox.showerror(
                get_text("common.error", "Lỗi"),
                f"{get_text('patient.add_error', 'Lỗi khi thêm bệnh nhân')}: {str(error)}"
            )
    
    def _edit_patient(self):
        """Chỉnh sửa thông tin bệnh nhân"""
        if not self.current_patient_id:
            return
        
        try:
            # Lấy thông tin bệnh nhân hiện tại
            patient = self.db.get_patient(self.current_patient_id)
            if not patient:
                logger.error(f"Không tìm thấy bệnh nhân với ID: {self.current_patient_id}")
                return
            
            # Tạo dữ liệu cho dialog
            patient_info = {
                'patient_id': self.current_patient_id,
                'name': patient.demographics.get('name', ''),
                'birth_date': patient.demographics.get('birth_date', ''),
                'gender': patient.demographics.get('gender', ''),
                'address': patient.demographics.get('address', ''),
                'phone': patient.demographics.get('phone', ''),
                'email': patient.demographics.get('email', ''),
                'doctor': patient.clinical_info.get('physician', ''),
                'diagnosis': patient.clinical_info.get('diagnosis', ''),
                'diagnosis_date': patient.clinical_info.get('diagnosis_date', ''),
                'cancer_type': patient.clinical_info.get('cancer_type', ''),
                'stage': patient.clinical_info.get('stage', ''),
                'notes': patient.clinical_info.get('notes', '')
            }
            
            # Hiển thị dialog
            dialog = PatientDialog(self, patient_data=patient_info)
            updated_info = dialog.show()
            
            if updated_info:
                # Cập nhật thông tin bệnh nhân
                patient.demographics.update({
                    'name': updated_info.get('name', ''),
                    'birth_date': updated_info.get('birth_date', ''),
                    'gender': updated_info.get('gender', ''),
                    'address': updated_info.get('address', ''),
                    'phone': updated_info.get('phone', ''),
                    'email': updated_info.get('email', '')
                })
                
                patient.clinical_info.update({
                    'diagnosis': updated_info.get('diagnosis', ''),
                    'diagnosis_date': updated_info.get('diagnosis_date', ''),
                    'cancer_type': updated_info.get('cancer_type', ''),
                    'stage': updated_info.get('stage', ''),
                    'physician': updated_info.get('doctor', ''),
                    'notes': updated_info.get('notes', '')
                })
                
                # Cập nhật vào cơ sở dữ liệu
                self.db.update_patient(patient)
                
                # Tải lại danh sách và thông tin chi tiết
                self.load_patients()
                self._load_patient_details(self.current_patient_id)
                
                # Thông báo thành công
                messagebox.showinfo(
                    get_text("common.success", "Thành công"),
                    get_text("patient.update_success", "Cập nhật thông tin bệnh nhân thành công")
                )
                
        except Exception as error:
            logger.exception(f"Lỗi khi cập nhật thông tin bệnh nhân: {str(error)}")
            messagebox.showerror(
                get_text("common.error", "Lỗi"),
                f"{get_text('patient.update_error', 'Lỗi khi cập nhật thông tin bệnh nhân')}: {str(error)}"
            )
    
    def _delete_patient(self):
        """Xóa bệnh nhân"""
        if not self.current_patient_id:
            return
        
        # Xác nhận xóa
        confirm = messagebox.askyesno(
            get_text("common.confirm", "Confirm"),
            get_text("patient.delete_confirm", "Are you sure you want to delete this patient and all associated data?"),
            icon='warning'
        )
        
        if confirm:
            try:
                # Xóa bệnh nhân
                self.db.delete_patient(self.current_patient_id)
                
                # Tải lại danh sách
                self.load_patients()
                
                # Xóa thông tin chi tiết
                self.id_value.config(text="")
                self.name_value.config(text="")
                self.birth_value.config(text="")
                self.gender_value.config(text="")
                self.diagnosis_value.config(text="")
                
                # Xóa dữ liệu cũ
                self.images_tree.delete(*self.images_tree.get_children())
                self.structures_tree.delete(*self.structures_tree.get_children())
                self.plans_tree.delete(*self.plans_tree.get_children())
                self.sessions_tree.delete(*self.sessions_tree.get_children())
                
                # Vô hiệu hóa các nút
                self.open_button.config(state='disabled')
                self.edit_button.config(state='disabled')
                self.delete_button.config(state='disabled')
                
                # Đặt lại biến lưu trữ
                self.current_patient_id = None
                
                # Thông báo thành công
                messagebox.showinfo(
                    get_text("common.success", "Success"),
                    get_text("patient.delete_success", "Patient deleted successfully")
                )
                
            except Exception as error:
                logger.exception(f"Lỗi khi xóa bệnh nhân: {str(error)}")
                messagebox.showerror(
                    get_text("common.error", "Error"),
                    f"{get_text('patient.delete_error', 'Error deleting patient')}: {str(error)}"
                )
    
    def _open_patient(self):
        """Mở bệnh nhân để làm việc"""
        if not self.current_patient_id:
            return
        
        try:
            # Tạo phiên làm việc mới
            session = self.session_manager.create_new_session(self.current_patient_id)
            
            # Thông báo
            messagebox.showinfo(
                get_text("common.success", "Success"),
                f"{get_text('patient.open_success', 'Patient opened successfully')}\n"
                f"{get_text('session.created', 'Session created')}: {session.get('session_id', '')}"
            )
            
            # Gọi callback nếu có
            if self.on_patient_selected:
                self.on_patient_selected(self.current_patient_id, session)
                
        except Exception as error:
            logger.exception(f"Lỗi khi mở bệnh nhân: {str(error)}")
            messagebox.showerror(
                get_text("common.error", "Error"),
                f"{get_text('patient.open_error', 'Error opening patient')}: {str(error)}"
            )

# Hàm test
def test_patient_view():
    root = tk.Tk()
    root.title("Patient View")
    root.geometry("1024x768")
    
    def on_selected(patient_id):
        print(f"Selected patient: {patient_id}")
    
    app = PatientView(root, on_patient_selected=on_selected)
    app.pack(fill='both', expand=True)
    
    root.mainloop()

# Chạy test khi file được thực thi trực tiếp
if __name__ == "__main__":
    test_patient_view()
