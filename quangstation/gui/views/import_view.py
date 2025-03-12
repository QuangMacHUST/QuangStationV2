#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module cung cấp giao diện nhập dữ liệu DICOM cho QuangStation V2.

Giao diện này cho phép người dùng:
1. Chọn thư mục chứa dữ liệu DICOM
2. Quét và kiểm tra tính tương thích của dữ liệu DICOM
3. Nhập dữ liệu vào hệ thống (CT, MRI, PET, RT Structure, RT Plan, RT Dose)
4. Theo dõi tiến trình nhập dữ liệu
"""

import os
import threading
import time
from typing import Dict, Any, Optional, List, Tuple, Callable
import traceback
import glob

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
except ImportError:
    tk = None
    ttk = None

from quangstation.core.utils.logging import get_logger
from quangstation.clinical.data_management.patient_db import PatientDatabase, Patient
from quangstation.clinical.data_management.import_interface import DataImportInterface
from quangstation.clinical.data_management.session_management import SessionManager
from quangstation.core.utils.dicom_error_handler import DICOMError, DICOMErrorCodes
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
        self.import_interface = DataImportInterface()
        self.session_manager = SessionManager()
        self.scan_result = None
        self.import_running = False
        self.compatibility_info = None
        
        # Xây dựng giao diện
        self._create_widgets()
        self._create_layout()
        
    def _create_widgets(self):
        """Tạo các widget cho giao diện"""
        # Frame chọn thư mục DICOM
        self.folder_frame = ttk.LabelFrame(self, text=get_text("import.select_folder", "Chọn thư mục DICOM"))
        
        self.folder_entry = ttk.Entry(self.folder_frame, textvariable=self.dicom_dir, width=50)
        self.browse_button = ttk.Button(
            self.folder_frame, 
            text=get_text("common.browse", "Duyệt"), 
            command=self._browse_folder
        )
        self.scan_button = ttk.Button(
            self.folder_frame, 
            text=get_text("import.scan", "Quét DICOM"), 
            command=self._scan_folder
        )
        
        # Frame thông tin bệnh nhân
        self.patient_frame = ttk.LabelFrame(self, text=get_text("import.patient_info", "Thông tin bệnh nhân"))
        
        self.name_label = ttk.Label(self.patient_frame, text=get_text("patient.name", "Họ tên") + ":")
        self.name_entry = ttk.Entry(self.patient_frame, textvariable=self.patient_name, width=30)
        
        self.id_label = ttk.Label(self.patient_frame, text=get_text("patient.id", "Mã") + ":")
        self.id_entry = ttk.Entry(self.patient_frame, textvariable=self.patient_id, width=20)
        
        # Frame chọn loại dữ liệu
        self.modality_frame = ttk.LabelFrame(self, text=get_text("import.data_type", "Loại dữ liệu"))
        
        self.ct_check = ttk.Checkbutton(self.modality_frame, text="CT", variable=self.modality_vars['ct'])
        self.mr_check = ttk.Checkbutton(self.modality_frame, text="MRI", variable=self.modality_vars['mr'])
        self.pt_check = ttk.Checkbutton(self.modality_frame, text="PET", variable=self.modality_vars['pt'])
        self.rtplan_check = ttk.Checkbutton(self.modality_frame, text="RT Plan", variable=self.modality_vars['rtplan'])
        self.rtdose_check = ttk.Checkbutton(self.modality_frame, text="RT Dose", variable=self.modality_vars['rtdose'])
        self.rtstruct_check = ttk.Checkbutton(self.modality_frame, text="RT Structure", variable=self.modality_vars['rtstruct'])
        
        # Frame thông tin DICOM
        self.info_frame = ttk.LabelFrame(self, text=get_text("import.dicom_info", "Thông tin DICOM"))
        
        self.info_tree = ttk.Treeview(self.info_frame, columns=('type', 'count', 'status'), show='headings', height=10)
        self.info_tree.heading('type', text=get_text("import.data_type", "Loại dữ liệu"))
        self.info_tree.heading('count', text=get_text("import.count", "Số lượng"))
        self.info_tree.heading('status', text=get_text("import.status", "Trạng thái"))
        self.info_tree.column('type', width=150)
        self.info_tree.column('count', width=80)
        self.info_tree.column('status', width=120)
        
        # Scrollbar cho info_tree
        self.info_scroll = ttk.Scrollbar(self.info_frame, orient='vertical', command=self.info_tree.yview)
        self.info_tree.configure(yscrollcommand=self.info_scroll.set)
        
        # Frame nút thao tác
        self.action_frame = ttk.Frame(self)
        
        self.import_button = ttk.Button(
            self.action_frame, 
            text=get_text("import.import", "Nhập DICOM"), 
            command=self._import_dicom,
            state='disabled'
        )
        
        self.verify_button = ttk.Button(
            self.action_frame,
            text=get_text("import.verify", "Kiểm tra tương thích"),
            command=self._verify_compatibility,
            state='disabled'
        )
        
        self.cancel_button = ttk.Button(
            self.action_frame, 
            text=get_text("common.cancel", "Hủy"), 
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
        self.verify_button.pack(side='left', padx=5, pady=5)
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
        dir_path = filedialog.askdirectory(title=get_text("import.select_folder", "Chọn thư mục DICOM"))
        if dir_path:
            self.dicom_dir.set(dir_path)
            # Tự động quét sau khi chọn thư mục
            self._scan_folder()
    
    def _scan_folder(self):
        """Quét thư mục để tìm các file DICOM"""
        dicom_dir = self.dicom_dir.get()
        
        if not dicom_dir or not os.path.exists(dicom_dir):
            messagebox.showerror(
                get_text("common.error", "Lỗi"),
                get_text("import.invalid_folder", "Vui lòng chọn thư mục DICOM hợp lệ")
            )
            return
        
        # Bắt đầu quét
        self._set_state('scanning')
        self.scan_result = None
        self.compatibility_info = None
        
        def scan_task():
            try:
                # Kiểm tra tính tương thích DICOM sử dụng DataImportInterface
                compatible, compatibility_info = self.import_interface.check_dicom_compatibility(dicom_dir)
                self.compatibility_info = compatibility_info
                
                # Nếu không tương thích, hiển thị cảnh báo nhưng vẫn tiếp tục
                if not compatible and compatibility_info.get('compatibility_issues'):
                    issues = compatibility_info.get('compatibility_issues', [])
                    logger.warning(f"Vấn đề tương thích DICOM: {issues}")
                
                # Hiển thị thông tin bệnh nhân
                patient_info = compatibility_info.get('patient_info', {})
                if patient_info:
                    name = patient_info.get('patient_name', '')
                    id = patient_info.get('patient_id', '')
                    self.patient_name.set(name)
                    self.patient_id.set(id)
                
                # Hiển thị thông tin file
                self.info_tree.delete(*self.info_tree.get_children())
                
                info_data = [
                    ('CT', compatibility_info.get('image_count', 0), 
                     "Sẵn sàng" if compatibility_info.get('has_image', False) else "Không có"),
                    ('RT Structure', compatibility_info.get('structure_count', 0), 
                     "Sẵn sàng" if compatibility_info.get('has_structure', False) else "Không có"),
                    ('RT Plan', 1 if compatibility_info.get('has_plan', False) else 0, 
                     "Sẵn sàng" if compatibility_info.get('has_plan', False) else "Không có"),
                    ('RT Dose', 1 if compatibility_info.get('has_dose', False) else 0, 
                     "Sẵn sàng" if compatibility_info.get('has_dose', False) else "Không có")
                ]
                
                for item_type, count, status in info_data:
                    self.info_tree.insert('', 'end', values=(item_type, count, status))
                
                # Kiểm tra xem có dữ liệu để nhập không
                has_data = compatibility_info.get('has_image', False) or \
                          compatibility_info.get('has_structure', False) or \
                          compatibility_info.get('has_plan', False) or \
                          compatibility_info.get('has_dose', False)
                
                # Kết thúc quét
                self.scan_result = has_data
                
                # Cập nhật giao diện trong main thread
                self.after(100, self._set_state, 'scan_complete')
                
            except DICOMError as e:
                logger.exception(f"Lỗi DICOM khi quét thư mục: [{e.error_code}] {e.message}")
                error_msg = f"{e.message}"
                self.after(100, self._handle_scan_error, error_msg)
            except Exception as e:
                logger.exception("Lỗi không xác định khi quét thư mục DICOM: %s", str(e))
                error_msg = str(e)
                self.after(100, self._handle_scan_error, error_msg)
        
        # Chạy quét trong thread riêng
        scan_thread = threading.Thread(target=scan_task)
        scan_thread.daemon = True
        scan_thread.start()
    
    def _import_dicom(self):
        """Nhập dữ liệu DICOM vào hệ thống"""
        # Kiểm tra lại trước khi nhập
        if not self.scan_result:
            messagebox.showerror(
                get_text("common.error", "Lỗi"),
                get_text("import.scan_first", "Vui lòng quét thư mục DICOM trước")
            )
            return
        
        dicom_dir = self.dicom_dir.get()
        patient_id = self.patient_id.get() if self.patient_id.get() else None
        
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
                # Thiết lập hàm callback tiến trình
                def progress_callback(progress_value, message):
                    if self.import_running:  # Kiểm tra xem quá trình có bị hủy không
                        self.after(100, self._update_progress, progress_value, message)
                
                # Sử dụng DataImportInterface để nhập dữ liệu
                result = self.import_interface.import_dicom_data(
                    dicom_dir, 
                    patient_id,
                    selected_modalities,
                    progress_callback
                )
                
                if not result:
                    raise Exception("Không thể nhập dữ liệu DICOM")
                
                # Tạo phiên làm việc mới nếu nhập thành công
                if 'patient_id' in result:
                    # Tạo phiên mới
                    self.session_manager.create_new_session(result['patient_id'])
                    logger.info(f"Đã tạo phiên mới cho bệnh nhân {result['patient_id']}")
                
                # Đã hoàn thành
                self.after(100, self._update_progress, 100, "Hoàn thành nhập dữ liệu!")
                time.sleep(0.5)  # Đợi để hiển thị hoàn thành
                
                # Kết thúc nhập dữ liệu
                if self.import_running:  # Kiểm tra xem quá trình có bị hủy không
                    self.after(100, self._import_complete, result)
                
            except DICOMError as error:
                logger.exception(f"Lỗi DICOM khi nhập dữ liệu: [{error.error_code}] {error.message}")
                if self.import_running:  # Kiểm tra xem quá trình có bị hủy không
                    self.after(100, self._handle_import_error, error.message)
            except Exception as error:
                logger.exception("Lỗi khi nhập dữ liệu DICOM: %s", str(error))
                if self.import_running:  # Kiểm tra xem quá trình có bị hủy không
                    self.after(100, self._handle_import_error, str(error))
        
        # Chạy nhập trong thread riêng
        import_thread = threading.Thread(target=import_task)
        import_thread.daemon = True
        import_thread.start()
    
    def _verify_compatibility(self):
        """Kiểm tra tính tương thích của dữ liệu DICOM"""
        dicom_dir = self.dicom_dir.get()
        
        if not dicom_dir or not os.path.exists(dicom_dir):
            messagebox.showerror(
                get_text("common.error", "Lỗi"),
                get_text("import.invalid_folder", "Vui lòng chọn thư mục DICOM hợp lệ")
            )
            return
        
        # Bắt đầu kiểm tra
        self._set_state('scanning')
        
        def verify_task():
            try:
                # Kiểm tra tính tương thích sử dụng DataImportInterface
                compatible, compatibility_info = self.import_interface.check_dicom_compatibility(dicom_dir)
                self.compatibility_info = compatibility_info
                
                # Tạo thông báo tương thích
                message = "Kết quả kiểm tra tương thích:\n\n"
                
                # Thông tin bệnh nhân
                patient_info = compatibility_info.get('patient_info', {})
                if patient_info:
                    message += f"Bệnh nhân: {patient_info.get('patient_name', 'Không xác định')}\n"
                    message += f"ID: {patient_info.get('patient_id', 'Không xác định')}\n\n"
                
                # Thông tin dữ liệu
                message += f"Hình ảnh: {'Có' if compatibility_info.get('has_image', False) else 'Không'}\n"
                message += f"Cấu trúc: {'Có' if compatibility_info.get('has_structure', False) else 'Không'}\n"
                message += f"Kế hoạch: {'Có' if compatibility_info.get('has_plan', False) else 'Không'}\n"
                message += f"Liều: {'Có' if compatibility_info.get('has_dose', False) else 'Không'}\n\n"
                
                # Số lượng
                message += f"Số lượng hình ảnh: {compatibility_info.get('image_count', 0)}\n"
                message += f"Số lượng cấu trúc: {compatibility_info.get('structure_count', 0)}\n\n"
                
                # Vấn đề tương thích
                issues = compatibility_info.get('compatibility_issues', [])
                if issues:
                    message += "Vấn đề tương thích:\n"
                    for issue in issues:
                        message += f"- {issue}\n"
                    
                    message += "\nLưu ý: Vẫn có thể nhập dữ liệu nhưng có thể gặp vấn đề."
                else:
                    message += "Không phát hiện vấn đề tương thích. Dữ liệu DICOM hợp lệ."
                
                # Hiển thị thông báo
                self.after(100, lambda: messagebox.showinfo("Kiểm tra tương thích", message))
                
                # Cập nhật giao diện
                self.after(100, self._set_state, 'scan_complete')
                
            except DICOMError as error:
                logger.exception(f"Lỗi DICOM khi kiểm tra tương thích: [{error.error_code}] {error.message}")
                self.after(100, self._handle_scan_error, error.message)
            except Exception as error:
                logger.exception("Lỗi khi kiểm tra tương thích DICOM: %s", str(error))
                self.after(100, self._handle_scan_error, str(error))
        
        # Chạy kiểm tra trong thread riêng
        verify_thread = threading.Thread(target=verify_task)
        verify_thread.daemon = True
        verify_thread.start()
    
    def _cancel_import(self):
        """Hủy quá trình nhập dữ liệu"""
        if self.import_running:
            self.import_running = False
            self._set_state('idle')
            self.status_label.config(text=get_text("import.canceled", "Đã hủy nhập"))
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
            self.name_entry.config(state='normal')
            self.id_entry.config(state='normal')
            self.browse_button.config(state='normal')
            self.scan_button.config(state='normal')
            self.import_button.config(state='disabled')
            self.verify_button.config(state='disabled')
            self.cancel_button.config(text=get_text("common.reset", "Đặt lại"))
            self.progress_var.set(0)
            self.status_label.config(text="")
            
        elif state == 'scanning':
            self.folder_entry.config(state='disabled')
            self.name_entry.config(state='normal')
            self.id_entry.config(state='normal')
            self.browse_button.config(state='disabled')
            self.scan_button.config(state='disabled')
            self.import_button.config(state='disabled')
            self.verify_button.config(state='disabled')
            self.cancel_button.config(text=get_text("common.cancel", "Hủy"))
            self.progress_var.set(0)
            self.status_label.config(text=get_text("import.scanning", "Đang quét thư mục DICOM..."))
            
        elif state == 'scan_complete':
            self.folder_entry.config(state='normal')
            self.name_entry.config(state='normal')
            self.id_entry.config(state='normal')
            self.browse_button.config(state='normal')
            self.scan_button.config(state='normal')
            
            # Chỉ kích hoạt nút Import và Verify nếu quét thành công
            if self.scan_result:
                self.import_button.config(state='normal')
                self.verify_button.config(state='normal')
                self.status_label.config(text=get_text("import.scan_complete", "Quét hoàn tất. Sẵn sàng nhập."))
                
                # Hiển thị thông tin modality dựa vào dữ liệu quét
                if self.compatibility_info:
                    self.modality_vars['ct'].set(self.compatibility_info.get('has_image', False))
                    self.modality_vars['mr'].set(False)  # Mặc định tắt, chỉ bật nếu phát hiện
                    self.modality_vars['pt'].set(False)  # Mặc định tắt, chỉ bật nếu phát hiện
                    self.modality_vars['rtstruct'].set(self.compatibility_info.get('has_structure', False))
                    self.modality_vars['rtplan'].set(self.compatibility_info.get('has_plan', False))
                    self.modality_vars['rtdose'].set(self.compatibility_info.get('has_dose', False))
            else:
                self.import_button.config(state='disabled')
                self.verify_button.config(state='disabled')
                self.status_label.config(text=get_text("import.no_dicom", "Không tìm thấy dữ liệu DICOM hợp lệ."))
                
            self.cancel_button.config(text=get_text("common.reset", "Đặt lại"))
            self.progress_var.set(0)
            
        elif state == 'importing':
            self.folder_entry.config(state='disabled')
            self.name_entry.config(state='disabled')
            self.id_entry.config(state='disabled')
            self.browse_button.config(state='disabled')
            self.scan_button.config(state='disabled')
            self.import_button.config(state='disabled')
            self.verify_button.config(state='disabled')
            self.cancel_button.config(text=get_text("common.cancel", "Hủy"))
    
    def _update_progress(self, value, message):
        """Cập nhật thanh tiến trình và thông báo"""
        self.progress_var.set(value)
        self.status_label.config(text=message)
    
    def _handle_scan_error(self, error_message):
        """Xử lý lỗi khi quét thư mục"""
        self._set_state('idle')
        messagebox.showerror(
            get_text("common.error", "Lỗi"),
            f"{get_text('import.scan_error', 'Lỗi khi quét thư mục DICOM')}: {error_message}"
        )
    
    def _handle_import_error(self, error_message):
        """Xử lý lỗi khi nhập dữ liệu"""
        self.import_running = False
        self._set_state('scan_complete')
        messagebox.showerror(
            get_text("common.error", "Lỗi"),
            f"{get_text('import.import_error', 'Lỗi khi nhập dữ liệu DICOM')}: {error_message}"
        )
    
    def _import_complete(self, result):
        """Xử lý khi nhập dữ liệu hoàn thành"""
        self.import_running = False
        self._set_state('idle')
        
        # Hiển thị thông báo thành công
        messagebox.showinfo(
            get_text("common.success", "Thành công"),
            get_text("import.import_success", "Đã nhập dữ liệu DICOM thành công")
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
        self.scan_result = None
        self.compatibility_info = None
