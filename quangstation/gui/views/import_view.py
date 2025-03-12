#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module cung cấp giao diện nhập dữ liệu DICOM cho QuangStation V2.
"""

import os
import threading
import time
from typing import Callable

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
except ImportError:
    tk = None
    ttk = None

from quangstation.core.utils.logging import get_logger
from quangstation.core.io.dicom_parser import DICOMParser
from quangstation.core.io.dicom_import import import_plan_from_dicom
from quangstation.core.lang.language import get_text

logger = get_logger(__name__)

class ImportView(ttk.Frame):
    """
    Giao diện nhập dữ liệu DICOM, cho phép người dùng chọn thư mục
    và xem trước thông tin DICOM trước khi nhập vào hệ thống.
    """
    
    def __init__(self, parent, on_import_complete: Callable = None, **kwargs):
        """
        Khởi tạo giao diện nhập dữ liệu.
        
        Args:
            parent: Widget cha
            on_import_complete: Callback khi nhập xong
        """
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.on_import_complete = on_import_complete
        
        # Biến lưu trữ dữ liệu
        self.dicom_dir = tk.StringVar()
        self.patient_name = tk.StringVar()
        self.patient_id = tk.StringVar()
        self.modality_vars = {
            'ct': tk.BooleanVar(value=True),
            'mr': tk.BooleanVar(value=True),
            'pt': tk.BooleanVar(value=True),
            'rtplan': tk.BooleanVar(value=True),
            'rtdose': tk.BooleanVar(value=True),
            'rtstruct': tk.BooleanVar(value=True)
        }
        
        # Biến khác
        self.parser = None
        self.scan_result = None
        self.import_running = False
        
        # Xây dựng giao diện
        self._create_widgets()
        self._create_layout()
        
    def _create_widgets(self):
        """Tạo các widget cho giao diện"""
        # Frame chọn thư mục DICOM
        self.folder_frame = ttk.LabelFrame(self, text=get_text("import.select_folder", "Select DICOM Folder"))
        
        self.folder_entry = ttk.Entry(self.folder_frame, textvariable=self.dicom_dir, width=50)
        self.browse_button = ttk.Button(
            self.folder_frame, 
            text=get_text("common.browse", "Browse"), 
            command=self._browse_folder
        )
        self.scan_button = ttk.Button(
            self.folder_frame, 
            text=get_text("import.scan", "Scan DICOM"), 
            command=self._scan_folder
        )
        
        # Frame thông tin bệnh nhân
        self.patient_frame = ttk.LabelFrame(self, text=get_text("import.patient_info", "Patient Information"))
        
        self.name_label = ttk.Label(self.patient_frame, text=get_text("patient.name", "Name") + ":")
        self.name_entry = ttk.Entry(self.patient_frame, textvariable=self.patient_name, state='readonly', width=30)
        
        self.id_label = ttk.Label(self.patient_frame, text=get_text("patient.id", "ID") + ":")
        self.id_entry = ttk.Entry(self.patient_frame, textvariable=self.patient_id, state='readonly', width=20)
        
        # Frame chọn loại dữ liệu
        self.modality_frame = ttk.LabelFrame(self, text=get_text("import.data_type", "Data Types"))
        
        self.ct_check = ttk.Checkbutton(self.modality_frame, text="CT", variable=self.modality_vars['ct'])
        self.mr_check = ttk.Checkbutton(self.modality_frame, text="MRI", variable=self.modality_vars['mr'])
        self.pt_check = ttk.Checkbutton(self.modality_frame, text="PET", variable=self.modality_vars['pt'])
        self.rtplan_check = ttk.Checkbutton(self.modality_frame, text="RT Plan", variable=self.modality_vars['rtplan'])
        self.rtdose_check = ttk.Checkbutton(self.modality_frame, text="RT Dose", variable=self.modality_vars['rtdose'])
        self.rtstruct_check = ttk.Checkbutton(self.modality_frame, text="RT Structure", variable=self.modality_vars['rtstruct'])
        
        # Frame thông tin DICOM
        self.info_frame = ttk.LabelFrame(self, text=get_text("import.dicom_info", "DICOM Information"))
        
        self.info_tree = ttk.Treeview(self.info_frame, columns=('type', 'count'), show='headings', height=10)
        self.info_tree.heading('type', text=get_text("import.data_type", "Data Type"))
        self.info_tree.heading('count', text=get_text("import.count", "Count"))
        self.info_tree.column('type', width=150)
        self.info_tree.column('count', width=80)
        
        # Scrollbar cho info_tree
        self.info_scroll = ttk.Scrollbar(self.info_frame, orient='vertical', command=self.info_tree.yview)
        self.info_tree.configure(yscrollcommand=self.info_scroll.set)
        
        # Frame nút thao tác
        self.action_frame = ttk.Frame(self)
        
        self.import_button = ttk.Button(
            self.action_frame, 
            text=get_text("import.import", "Import DICOM"), 
            command=self._import_dicom,
            state='disabled'
        )
        
        self.cancel_button = ttk.Button(
            self.action_frame, 
            text=get_text("common.cancel", "Cancel"), 
            command=self._cancel_import
        )
        
        # Thanh tiến trình
        self.progress_frame = ttk.Frame(self)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.progress_frame, variable=self.progress_var, mode='determinate')
        self.status_label = ttk.Label(self.progress_frame, text="")
        
    def _create_layout(self):
        """Thiết lập layout cho giao diện"""
        # Layout cho folder_frame
        self.folder_entry.pack(side='left', fill='x', expand=True, padx=5, pady=5)
        self.browse_button.pack(side='left', padx=5, pady=5)
        self.scan_button.pack(side='left', padx=5, pady=5)
        
        # Layout cho patient_frame
        self.name_label.grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.name_entry.grid(row=0, column=1, sticky='w', padx=5, pady=5)
        self.id_label.grid(row=0, column=2, sticky='w', padx=5, pady=5)
        self.id_entry.grid(row=0, column=3, sticky='w', padx=5, pady=5)
        
        # Layout cho modality_frame
        self.ct_check.grid(row=0, column=0, sticky='w', padx=15, pady=5)
        self.mr_check.grid(row=0, column=1, sticky='w', padx=15, pady=5)
        self.pt_check.grid(row=0, column=2, sticky='w', padx=15, pady=5)
        self.rtplan_check.grid(row=1, column=0, sticky='w', padx=15, pady=5)
        self.rtdose_check.grid(row=1, column=1, sticky='w', padx=15, pady=5)
        self.rtstruct_check.grid(row=1, column=2, sticky='w', padx=15, pady=5)
        
        # Layout cho info_frame
        self.info_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        self.info_scroll.pack(side='right', fill='y', pady=5)
        
        # Layout cho action_frame
        self.import_button.pack(side='left', padx=5, pady=5)
        self.cancel_button.pack(side='left', padx=5, pady=5)
        
        # Layout cho progress_frame
        self.progress_bar.pack(side='top', fill='x', padx=5, pady=2)
        self.status_label.pack(side='top', fill='x', padx=5)
        
        # Layout chính
        self.folder_frame.pack(fill='x', padx=10, pady=5)
        self.patient_frame.pack(fill='x', padx=10, pady=5)
        self.modality_frame.pack(fill='x', padx=10, pady=5)
        self.info_frame.pack(fill='both', expand=True, padx=10, pady=5)
        self.action_frame.pack(fill='x', padx=10, pady=5)
        self.progress_frame.pack(fill='x', padx=10, pady=5)
    
    def _browse_folder(self):
        """Mở hộp thoại chọn thư mục DICOM"""
        dir_path = filedialog.askdirectory(title=get_text("import.select_folder", "Select DICOM Folder"))
        if dir_path:
            self.dicom_dir.set(dir_path)
            # Tự động quét sau khi chọn thư mục
            self._scan_folder()
    
    def _scan_folder(self):
        """Quét thư mục để tìm các file DICOM"""
        dicom_dir = self.dicom_dir.get()
        
        if not dicom_dir or not os.path.exists(dicom_dir):
            messagebox.showerror(
                get_text("common.error", "Error"),
                get_text("import.invalid_folder", "Please select a valid DICOM folder")
            )
            return
        
        # Bắt đầu quét
        self._set_state('scanning')
        self.scan_result = None
        self.parser = None
        
        def scan_task():
            try:
                # Sử dụng parser để quét thư mục DICOM
                self.parser = DICOMParser(dicom_dir)
                
                # Lấy dữ liệu từ parser
                has_data = self.parser.has_valid_data()
                
                # Hiển thị thông tin bệnh nhân
                if self.parser.patient_info:
                    name = self.parser.patient_info.get('PatientName', '')
                    id = self.parser.patient_info.get('PatientID', '')
                    self.patient_name.set(name)
                    self.patient_id.set(id)
                
                # Hiển thị thông tin file
                self.info_tree.delete(*self.info_tree.get_children())
                
                info_data = [
                    ('CT', len(self.parser.ct_files)),
                    ('MRI', len(self.parser.mri_files)),
                    ('PET', len(self.parser.pet_files)),
                    ('RT Structure', 1 if self.parser.rt_struct else 0),
                    ('RT Dose', 1 if self.parser.rt_dose else 0),
                    ('RT Plan', 1 if self.parser.rt_plan else 0)
                ]
                
                for item_type, count in info_data:
                    self.info_tree.insert('', 'end', values=(item_type, count))
                
                # Kiểm tra xem có dữ liệu để nhập không
                has_data = any(count > 0 for _, count in info_data)
                
                # Kết thúc quét
                self.scan_result = has_data
                
                # Cập nhật giao diện trong main thread
                self.after(100, self._set_state, 'scan_complete')
                
            except Exception as e:
                logger.exception("Lỗi khi quét thư mục DICOM: %s", str(e))
                error_msg = str(e)
                self.after(100, self._handle_scan_error, error_msg)
        
        # Chạy quét trong thread riêng
        scan_thread = threading.Thread(target=scan_task)
        scan_thread.daemon = True
        scan_thread.start()
    
    def _import_dicom(self):
        """Nhập dữ liệu DICOM vào hệ thống"""
        # Kiểm tra lại trước khi nhập
        if not self.parser or not self.scan_result:
            messagebox.showerror(
                get_text("common.error", "Error"),
                get_text("import.scan_first", "Please scan the DICOM folder first")
            )
            return
        
        dicom_dir = self.dicom_dir.get()
        
        # Lấy các loại dữ liệu được chọn
        selected_modalities = {k: v.get() for k, v in self.modality_vars.items()}
        
        # Thêm thông tin lựa chọn vào log
        logger.info("Nhập dữ liệu DICOM từ %s với các loại: %s", 
                   dicom_dir, 
                   ', '.join([k for k, v in selected_modalities.items() if v]))
        
        # Bắt đầu nhập
        self._set_state('importing')
        self.import_running = True
        
        def import_task():
            try:
                # Thiết lập trạng thái ban đầu
                self.after(100, self._update_progress, 0, "Đang chuẩn bị nhập dữ liệu...")
                time.sleep(0.5)  # Đợi giao diện cập nhật
                
                # Nhập dữ liệu
                self.after(100, self._update_progress, 10, "Đang đọc file DICOM...")
                
                # Gọi hàm nhập dữ liệu với bộ lọc modality
                result = import_plan_from_dicom(
                    dicom_dir, 
                    modality_filters=selected_modalities
                )
                
                if not result:
                    raise Exception("Không thể nhập dữ liệu DICOM")
                
                self.after(100, self._update_progress, 50, "Đang xử lý dữ liệu...")
                time.sleep(0.5)  # Giả lập xử lý
                
                self.after(100, self._update_progress, 80, "Đang tạo cấu trúc dữ liệu...")
                time.sleep(0.5)  # Giả lập xử lý
                
                self.after(100, self._update_progress, 100, "Hoàn thành nhập dữ liệu!")
                time.sleep(0.5)  # Đợi để hiển thị hoàn thành
                
                # Kết thúc nhập dữ liệu
                if self.import_running:  # Kiểm tra xem quá trình có bị hủy không
                    self.after(100, self._import_complete, result)
                
            except Exception as error:
                logger.exception("Lỗi khi nhập dữ liệu DICOM: %s", str(error))
                error_message = str(error)
                if self.import_running:  # Kiểm tra xem quá trình có bị hủy không
                    self.after(100, self._handle_import_error, error_message)
        
        # Chạy nhập trong thread riêng
        import_thread = threading.Thread(target=import_task)
        import_thread.daemon = True
        import_thread.start()
    
    def _cancel_import(self):
        """Hủy quá trình nhập dữ liệu"""
        if self.import_running:
            self.import_running = False
            self._set_state('idle')
            self.status_label.config(text=get_text("import.canceled", "Import canceled"))
        else:
            self._reset()
    
    def _set_state(self, state):
        """
        Thiết lập trạng thái của giao diện.
        
        Args:
            state: Trạng thái ('idle', 'scanning', 'scan_complete', 'importing')
        """
        if state == 'idle':
            self.folder_entry.config(state='normal')
            self.browse_button.config(state='normal')
            self.scan_button.config(state='normal')
            self.import_button.config(state='disabled')
            self.cancel_button.config(text=get_text("common.reset", "Reset"))
            self.progress_var.set(0)
            self.status_label.config(text="")
            
        elif state == 'scanning':
            self.folder_entry.config(state='disabled')
            self.browse_button.config(state='disabled')
            self.scan_button.config(state='disabled')
            self.import_button.config(state='disabled')
            self.cancel_button.config(text=get_text("common.cancel", "Cancel"))
            self.progress_var.set(0)
            self.status_label.config(text=get_text("import.scanning", "Scanning DICOM folder..."))
            
        elif state == 'scan_complete':
            self.folder_entry.config(state='normal')
            self.browse_button.config(state='normal')
            self.scan_button.config(state='normal')
            
            # Chỉ kích hoạt nút Import nếu quét thành công
            if self.scan_result:
                self.import_button.config(state='normal')
                self.status_label.config(text=get_text("import.scan_complete", "Scan complete. Ready to import."))
                
                # Hiển thị thông tin modality
                modality_counts = {
                    'CT': len(self.parser.ct_files),
                    'MRI': len(self.parser.mri_files),
                    'PET': len(self.parser.pet_files),
                    'RT Structure': 1 if self.parser.rt_struct else 0,
                    'RT Dose': 1 if self.parser.rt_dose else 0,
                    'RT Plan': 1 if self.parser.rt_plan else 0
                }
                
                # Cập nhật thông tin loại dữ liệu
                for modality, count in modality_counts.items():
                    if count > 0:
                        if modality in ['CT', 'MRI', 'PET']:
                            self.modality_vars[modality.lower()].set(True)
                        elif modality == 'RT Structure':
                            self.modality_vars['rtstruct'].set(True)
                        elif modality == 'RT Dose':
                            self.modality_vars['rtdose'].set(True)
                        elif modality == 'RT Plan':
                            self.modality_vars['rtplan'].set(True)
            else:
                self.import_button.config(state='disabled')
                self.status_label.config(text=get_text("import.no_dicom", "No valid DICOM data found."))
                
            self.cancel_button.config(text=get_text("common.reset", "Reset"))
            self.progress_var.set(0)
            
        elif state == 'importing':
            self.folder_entry.config(state='disabled')
            self.browse_button.config(state='disabled')
            self.scan_button.config(state='disabled')
            self.import_button.config(state='disabled')
            self.cancel_button.config(text=get_text("common.cancel", "Cancel"))
    
    def _update_progress(self, value, message):
        """Cập nhật thanh tiến trình và thông báo"""
        self.progress_var.set(value)
        self.status_label.config(text=message)
    
    def _handle_scan_error(self, error_message):
        """Xử lý lỗi khi quét thư mục"""
        self._set_state('idle')
        messagebox.showerror(
            get_text("common.error", "Error"),
            f"{get_text('import.scan_error', 'Error scanning DICOM folder')}: {error_message}"
        )
    
    def _handle_import_error(self, error_message):
        """Xử lý lỗi khi nhập dữ liệu"""
        self.import_running = False
        self._set_state('scan_complete')
        messagebox.showerror(
            get_text("common.error", "Error"),
            f"{get_text('import.import_error', 'Error importing DICOM data')}: {error_message}"
        )
    
    def _import_complete(self, result):
        """Xử lý khi nhập dữ liệu hoàn thành"""
        self.import_running = False
        self._set_state('idle')
        
        # Hiển thị thông báo thành công
        messagebox.showinfo(
            get_text("common.success", "Success"),
            get_text("import.import_success", "DICOM data imported successfully")
        )
        
        # Gọi callback nếu có
        if self.on_import_complete:
            self.on_import_complete(result)
    
    def _reset(self):
        """Đặt lại giao diện về trạng thái ban đầu"""
        self.dicom_dir.set("")
        self.patient_name.set("")
        self.patient_id.set("")
        
        # Đặt lại các checkbox
        for var in self.modality_vars.values():
            var.set(True)
            
        # Xóa thông tin DICOM
        self.info_tree.delete(*self.info_tree.get_children())
        
        # Đặt lại trạng thái
        self._set_state('idle')
        
        # Xóa các biến lưu trữ
        self.parser = None
        self.scan_result = None
