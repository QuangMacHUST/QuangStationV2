#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module chứa các utility cho hiển thị thông tin
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import numpy as np
from PIL import Image, ImageTk
from datetime import datetime

def format_date(date_str, input_format="%Y-%m-%dT%H:%M:%S.%f", output_format="%d/%m/%Y %H:%M"):
    """
    Định dạng lại chuỗi ngày tháng
    
    Args:
        date_str: Chuỗi ngày tháng đầu vào
        input_format: Định dạng đầu vào
        output_format: Định dạng đầu ra
        
    Returns:
        Chuỗi ngày tháng đã định dạng
    """
    try:
        # Cắt bỏ phần microsecond nếu chuỗi không có
        if date_str.find('.') == -1 and input_format.find('.%f') != -1:
            input_format = input_format.replace('.%f', '')
            
        # Chuyển đổi thành đối tượng datetime
        date_obj = datetime.strptime(date_str, input_format)
        
        # Định dạng lại
        return date_obj.strftime(output_format)
    except Exception:
        return date_str

def create_patient_info_panel(parent, patient_data, icons=None):
    """
    Tạo panel hiển thị thông tin bệnh nhân
    
    Args:
        parent: Widget cha
        patient_data: Dữ liệu bệnh nhân
        icons: Dictionary chứa các biểu tượng
        
    Returns:
        Frame chứa thông tin bệnh nhân
    """
    # Tạo frame chứa thông tin
    patient_frame = ttk.LabelFrame(parent, text="Thông tin bệnh nhân")
    
    # Kiểm tra dữ liệu
    if not patient_data:
        ttk.Label(patient_frame, text="Không có thông tin bệnh nhân").pack(padx=10, pady=10)
        return patient_frame
        
    # Lấy dữ liệu demographics
    demo = patient_data.get('demographics', {})
    
    # Frame nội dung
    content_frame = ttk.Frame(patient_frame)
    content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Cột trái: Thông tin cá nhân
    left_frame = ttk.Frame(content_frame)
    left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    # Thông tin cá nhân
    ttk.Label(left_frame, text="Họ tên:", anchor=tk.W).grid(row=0, column=0, sticky=tk.W, pady=2)
    ttk.Label(left_frame, text=demo.get('name', 'N/A'), font=('Helvetica', 10, 'bold'), anchor=tk.W).grid(row=0, column=1, sticky=tk.W, pady=2)
    
    ttk.Label(left_frame, text="Mã bệnh nhân:", anchor=tk.W).grid(row=1, column=0, sticky=tk.W, pady=2)
    ttk.Label(left_frame, text=patient_data.get('patient_id', 'N/A'), anchor=tk.W).grid(row=1, column=1, sticky=tk.W, pady=2)
    
    ttk.Label(left_frame, text="Ngày sinh:", anchor=tk.W).grid(row=2, column=0, sticky=tk.W, pady=2)
    ttk.Label(left_frame, text=demo.get('birth_date', 'N/A'), anchor=tk.W).grid(row=2, column=1, sticky=tk.W, pady=2)
    
    ttk.Label(left_frame, text="Giới tính:", anchor=tk.W).grid(row=3, column=0, sticky=tk.W, pady=2)
    ttk.Label(left_frame, text=demo.get('gender', 'N/A'), anchor=tk.W).grid(row=3, column=1, sticky=tk.W, pady=2)
    
    # Cột phải: Thông tin y tế
    right_frame = ttk.Frame(content_frame)
    right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    ttk.Label(right_frame, text="Chẩn đoán:", anchor=tk.W).grid(row=0, column=0, sticky=tk.W, pady=2)
    ttk.Label(right_frame, text=demo.get('diagnosis', 'N/A'), anchor=tk.W).grid(row=0, column=1, sticky=tk.W, pady=2)
    
    ttk.Label(right_frame, text="Bác sĩ:", anchor=tk.W).grid(row=1, column=0, sticky=tk.W, pady=2)
    ttk.Label(right_frame, text=demo.get('physician', 'N/A'), anchor=tk.W).grid(row=1, column=1, sticky=tk.W, pady=2)
    
    ttk.Label(right_frame, text="Ngày tạo:", anchor=tk.W).grid(row=2, column=0, sticky=tk.W, pady=2)
    created_date = format_date(patient_data.get('created_date', 'N/A'))
    ttk.Label(right_frame, text=created_date, anchor=tk.W).grid(row=2, column=1, sticky=tk.W, pady=2)
    
    ttk.Label(right_frame, text="Cập nhật:", anchor=tk.W).grid(row=3, column=0, sticky=tk.W, pady=2)
    modified_date = format_date(patient_data.get('modified_date', 'N/A'))
    ttk.Label(right_frame, text=modified_date, anchor=tk.W).grid(row=3, column=1, sticky=tk.W, pady=2)
    
    return patient_frame

def create_plan_info_panel(parent, plan_data, icons=None):
    """
    Tạo panel hiển thị thông tin kế hoạch
    
    Args:
        parent: Widget cha
        plan_data: Dữ liệu kế hoạch
        icons: Dictionary chứa các biểu tượng
        
    Returns:
        Frame chứa thông tin kế hoạch
    """
    # Tạo frame chứa thông tin
    plan_frame = ttk.LabelFrame(parent, text="Thông tin kế hoạch")
    
    # Kiểm tra dữ liệu
    if not plan_data:
        ttk.Label(plan_frame, text="Không có thông tin kế hoạch").pack(padx=10, pady=10)
        return plan_frame
    
    # Frame nội dung
    content_frame = ttk.Frame(plan_frame)
    content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Cột trái: Thông tin cơ bản
    left_frame = ttk.Frame(content_frame)
    left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    # Thông tin cơ bản
    ttk.Label(left_frame, text="Tên kế hoạch:", anchor=tk.W).grid(row=0, column=0, sticky=tk.W, pady=2)
    ttk.Label(left_frame, text=plan_data.get('name', 'N/A'), font=('Helvetica', 10, 'bold'), anchor=tk.W).grid(row=0, column=1, sticky=tk.W, pady=2)
    
    ttk.Label(left_frame, text="Mã kế hoạch:", anchor=tk.W).grid(row=1, column=0, sticky=tk.W, pady=2)
    ttk.Label(left_frame, text=plan_data.get('plan_id', 'N/A'), anchor=tk.W).grid(row=1, column=1, sticky=tk.W, pady=2)
    
    ttk.Label(left_frame, text="Trạng thái:", anchor=tk.W).grid(row=2, column=0, sticky=tk.W, pady=2)
    ttk.Label(left_frame, text=plan_data.get('status', 'N/A').upper(), anchor=tk.W).grid(row=2, column=1, sticky=tk.W, pady=2)
    
    ttk.Label(left_frame, text="Kỹ thuật:", anchor=tk.W).grid(row=3, column=0, sticky=tk.W, pady=2)
    ttk.Label(left_frame, text=plan_data.get('technique', 'N/A'), anchor=tk.W).grid(row=3, column=1, sticky=tk.W, pady=2)
    
    # Cột phải: Thông tin liều
    right_frame = ttk.Frame(content_frame)
    right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    ttk.Label(right_frame, text="Liều chỉ định:", anchor=tk.W).grid(row=0, column=0, sticky=tk.W, pady=2)
    prescribed_dose = f"{plan_data.get('prescribed_dose', 0.0):.2f} Gy"
    ttk.Label(right_frame, text=prescribed_dose, anchor=tk.W).grid(row=0, column=1, sticky=tk.W, pady=2)
    
    ttk.Label(right_frame, text="Số phân liều:", anchor=tk.W).grid(row=1, column=0, sticky=tk.W, pady=2)
    ttk.Label(right_frame, text=str(plan_data.get('fraction_count', 0)), anchor=tk.W).grid(row=1, column=1, sticky=tk.W, pady=2)
    
    ttk.Label(right_frame, text="Liều mỗi phân liều:", anchor=tk.W).grid(row=2, column=0, sticky=tk.W, pady=2)
    fraction_dose = f"{plan_data.get('fraction_dose', 0.0):.2f} Gy"
    ttk.Label(right_frame, text=fraction_dose, anchor=tk.W).grid(row=2, column=1, sticky=tk.W, pady=2)
    
    ttk.Label(right_frame, text="Năng lượng:", anchor=tk.W).grid(row=3, column=0, sticky=tk.W, pady=2)
    ttk.Label(right_frame, text=plan_data.get('energy', 'N/A'), anchor=tk.W).grid(row=3, column=1, sticky=tk.W, pady=2)
    
    return plan_frame

def create_beam_list_panel(parent, plan_data, on_select=None, icons=None):
    """
    Tạo panel hiển thị danh sách chùm tia
    
    Args:
        parent: Widget cha
        plan_data: Dữ liệu kế hoạch
        on_select: Hàm callback khi chọn chùm tia
        icons: Dictionary chứa các biểu tượng
        
    Returns:
        Frame chứa danh sách chùm tia
    """
    # Tạo frame chứa danh sách
    beam_frame = ttk.LabelFrame(parent, text="Danh sách chùm tia")
    
    # Kiểm tra dữ liệu
    if not plan_data or 'beams' not in plan_data or not plan_data['beams']:
        ttk.Label(beam_frame, text="Không có thông tin chùm tia").pack(padx=10, pady=10)
        return beam_frame
    
    # Frame nội dung
    content_frame = ttk.Frame(beam_frame)
    content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Tạo treeview
    columns = ("name", "gantry", "coll", "energy", "mu", "weight")
    tree = ttk.Treeview(content_frame, columns=columns, show="headings")
    
    # Thiết lập tiêu đề cột
    tree.heading("name", text="Tên")
    tree.heading("gantry", text="Gantry")
    tree.heading("coll", text="Coll")
    tree.heading("energy", text="Năng lượng")
    tree.heading("mu", text="MU")
    tree.heading("weight", text="Trọng số")
    
    # Thiết lập độ rộng cột
    tree.column("name", width=100)
    tree.column("gantry", width=70)
    tree.column("coll", width=70)
    tree.column("energy", width=80)
    tree.column("mu", width=70)
    tree.column("weight", width=70)
    
    # Thêm scrollbar
    scrollbar = ttk.Scrollbar(content_frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    
    # Pack vào frame
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    # Thêm dữ liệu
    for beam in plan_data['beams']:
        tree.insert("", tk.END, values=(
            beam.get('name', 'N/A'),
            f"{beam.get('gantry_angle', 0):.1f}°",
            f"{beam.get('collimator_angle', 0):.1f}°",
            beam.get('energy', 'N/A'),
            f"{beam.get('monitor_units', 0):.1f}",
            f"{beam.get('weight', 1.0):.2f}"
        ))
    
    # Thiết lập sự kiện khi chọn chùm tia
    if on_select:
        tree.bind("<<TreeviewSelect>>", on_select)
    
    return beam_frame

def create_structure_list_panel(parent, plan_data, on_select=None, icons=None):
    """
    Tạo panel hiển thị danh sách cấu trúc
    
    Args:
        parent: Widget cha
        plan_data: Dữ liệu kế hoạch
        on_select: Hàm callback khi chọn cấu trúc
        icons: Dictionary chứa các biểu tượng
        
    Returns:
        Frame chứa danh sách cấu trúc
    """
    # Tạo frame chứa danh sách
    structure_frame = ttk.LabelFrame(parent, text="Danh sách cấu trúc")
    
    # Kiểm tra dữ liệu
    if not plan_data or 'structures' not in plan_data or not plan_data['structures']:
        ttk.Label(structure_frame, text="Không có thông tin cấu trúc").pack(padx=10, pady=10)
        return structure_frame
    
    # Frame nội dung
    content_frame = ttk.Frame(structure_frame)
    content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Tạo treeview
    columns = ("name", "type", "volume", "color")
    tree = ttk.Treeview(content_frame, columns=columns, show="headings")
    
    # Thiết lập tiêu đề cột
    tree.heading("name", text="Tên")
    tree.heading("type", text="Loại")
    tree.heading("volume", text="Thể tích (cc)")
    tree.heading("color", text="Màu sắc")
    
    # Thiết lập độ rộng cột
    tree.column("name", width=120)
    tree.column("type", width=80)
    tree.column("volume", width=100)
    tree.column("color", width=80)
    
    # Thêm scrollbar
    scrollbar = ttk.Scrollbar(content_frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    
    # Pack vào frame
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    # Thêm dữ liệu
    for struct in plan_data['structures']:
        # Tạo ô màu
        color = struct.get('color', '#FF0000')
        
        tree.insert("", tk.END, values=(
            struct.get('name', 'N/A'),
            struct.get('type', 'UNKNOWN'),
            f"{struct.get('volume', 0.0):.2f}",
            color
        ))
        
        # Thiết lập màu nền cho ô màu
        # Lưu ý: Đây là cách không chuẩn để thay đổi màu nền của cell trong Treeview,
        # nhưng tkinter không hỗ trợ trực tiếp chức năng này
    
    # Thiết lập sự kiện khi chọn cấu trúc
    if on_select:
        tree.bind("<<TreeviewSelect>>", on_select)
    
    return structure_frame 