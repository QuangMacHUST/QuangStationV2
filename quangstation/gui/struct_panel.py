#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module giao diện quản lý cấu trúc cơ thể cho QuangStation V2.
"""

import tkinter as tk
from tkinter import ttk, colorchooser, messagebox
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Callable

from quangstation.contouring.organ_library import get_organ_library, OrganProperties
from quangstation.contouring.contour_tools import ContourTools
from quangstation.utils.logging import get_logger

logger = get_logger("StructPanel")

class StructPanel(ttk.Frame):
    """Panel quản lý cấu trúc và contour"""
    
    def __init__(self, parent, contour_tools: ContourTools, on_select_callback: Callable = None,
               on_update_callback: Callable = None):
        """
        Khởi tạo panel struct
        
        Args:
            parent: Tkinter parent widget
            contour_tools: Instance của ContourTools
            on_select_callback: Hàm callback khi chọn cấu trúc
            on_update_callback: Hàm callback khi cập nhật cấu trúc
        """
        super().__init__(parent)
        self.contour_tools = contour_tools
        self.on_select_callback = on_select_callback
        self.on_update_callback = on_update_callback
        self.organ_library = get_organ_library()
        self.structures = {}  # Dictionary chứa các cấu trúc đã tạo
        self.current_structure = None
        
        # Tạo giao diện
        self._create_widgets()
        
    def _create_widgets(self):
        """Tạo các widget cho panel"""
        # Frame chứa danh sách cấu trúc
        struct_frame = ttk.LabelFrame(self, text="Cấu trúc đã tạo")
        struct_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tạo treeview hiển thị danh sách cấu trúc
        columns = ("name", "color", "volume", "category")
        self.struct_tree = ttk.Treeview(struct_frame, columns=columns, show="headings", 
                                     selectmode="browse", height=10)
        
        # Định nghĩa các cột
        self.struct_tree.heading("name", text="Tên")
        self.struct_tree.heading("color", text="Màu")
        self.struct_tree.heading("volume", text="Thể tích (cc)")
        self.struct_tree.heading("category", text="Danh mục")
        
        # Cấu hình độ rộng cột
        self.struct_tree.column("name", width=150)
        self.struct_tree.column("color", width=50)
        self.struct_tree.column("volume", width=80)
        self.struct_tree.column("category", width=100)
        
        # Thêm scrollbar
        scrollbar = ttk.Scrollbar(struct_frame, orient="vertical", command=self.struct_tree.yview)
        self.struct_tree.configure(yscrollcommand=scrollbar.set)
        
        # Đặt vị trí
        self.struct_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Binding
        self.struct_tree.bind("<<TreeviewSelect>>", self._on_struct_select)
        
        # Frame chứa các nút thao tác
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Nút thêm cấu trúc
        ttk.Button(button_frame, text="Thêm cấu trúc", command=self._add_structure_dialog).pack(side=tk.LEFT, padx=2)
        
        # Nút chỉnh sửa cấu trúc
        ttk.Button(button_frame, text="Chỉnh sửa", command=self._edit_structure_dialog).pack(side=tk.LEFT, padx=2)
        
        # Nút xóa cấu trúc
        ttk.Button(button_frame, text="Xóa", command=self._delete_structure).pack(side=tk.LEFT, padx=2)
        
        # Nút đổi màu
        ttk.Button(button_frame, text="Đổi màu", command=self._change_color).pack(side=tk.LEFT, padx=2)
        
        # Frame chứa các công cụ contour
        contour_frame = ttk.LabelFrame(self, text="Công cụ Contour")
        contour_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Nút vẽ contour tự do
        ttk.Button(contour_frame, text="Vẽ tự do", command=self._activate_free_contour).pack(side=tk.LEFT, padx=2)
        
        # Nút vẽ contour hình chữ nhật
        ttk.Button(contour_frame, text="Hình chữ nhật", command=self._activate_rect_contour).pack(side=tk.LEFT, padx=2)
        
        # Nút vẽ contour hình tròn
        ttk.Button(contour_frame, text="Hình tròn", command=self._activate_circle_contour).pack(side=tk.LEFT, padx=2)
        
        # Nút tự động tạo contour
        ttk.Button(contour_frame, text="Tự động", command=self._auto_contour).pack(side=tk.LEFT, padx=2)
        
        # Nút nội suy contour
        ttk.Button(contour_frame, text="Nội suy", command=self._interpolate_contour).pack(side=tk.LEFT, padx=2)
        
    def update_struct_list(self):
        """Cập nhật danh sách cấu trúc"""
        # Xóa danh sách cũ
        for item in self.struct_tree.get_children():
            self.struct_tree.delete(item)
            
        # Thêm cấu trúc vào danh sách
        for name, struct in self.structures.items():
            # Tính thể tích
            volume = self.contour_tools.calculate_volume(name) if name in self.contour_tools.contours else 0.0
            volume_str = f"{volume:.2f}" if volume > 0 else "N/A"
            
            # Lấy thông tin cơ quan từ thư viện nếu có
            organ = self.organ_library.get_organ(name)
            category = organ.category if organ else "Other"
            
            # Thêm vào tree
            self.struct_tree.insert("", tk.END, values=(name, struct["color"], volume_str, category))
            
        # Cập nhật background color của các item
        for item in self.struct_tree.get_children():
            values = self.struct_tree.item(item, "values")
            if values:
                name, color = values[0], values[1]
                if name == self.current_structure:
                    self.struct_tree.item(item, tags=("selected",))
                else:
                    self.struct_tree.item(item, tags=("normal",))
                    
        # Định nghĩa màu sắc cho tags
        self.struct_tree.tag_configure("selected", background="#e0e0ff")
        
    def add_structure(self, name: str, color: str = None, category: str = "Other"):
        """
        Thêm cấu trúc mới
        
        Args:
            name: Tên cấu trúc
            color: Màu sắc (hex code)
            category: Danh mục
        """
        # Kiểm tra xem cấu trúc đã tồn tại chưa
        if name in self.structures:
            logger.log_warning(f"Cấu trúc {name} đã tồn tại")
            return False
            
        # Lấy thông tin từ thư viện cơ quan nếu có
        organ = self.organ_library.get_organ(name)
        if organ:
            if not color:
                color = organ.color
            category = organ.category
            
        # Nếu không có màu, tạo màu ngẫu nhiên
        if not color:
            import random
            color = f"#{random.randint(0, 0xFFFFFF):06x}"
            
        # Thêm cấu trúc vào contour_tools
        self.contour_tools.add_structure(name, color)
        
        # Thêm vào danh sách
        self.structures[name] = {
            "color": color,
            "category": category
        }
        
        # Cập nhật UI
        self.update_struct_list()
        
        # Đặt làm cấu trúc hiện tại
        self.set_current_structure(name)
        
        logger.log_info(f"Đã thêm cấu trúc: {name}")
        return True
        
    def set_current_structure(self, name: str):
        """Đặt cấu trúc hiện tại"""
        if name in self.structures:
            self.current_structure = name
            self.contour_tools.set_current_structure(name)
            
            # Cập nhật UI
            self.update_struct_list()
            
            # Gọi callback
            if self.on_select_callback:
                self.on_select_callback(name)
                
            logger.log_info(f"Đã chọn cấu trúc: {name}")
            return True
        else:
            logger.log_warning(f"Không tìm thấy cấu trúc: {name}")
            return False
            
    def _on_struct_select(self, event):
        """Xử lý sự kiện chọn cấu trúc"""
        selection = self.struct_tree.selection()
        if selection:
            item = selection[0]
            values = self.struct_tree.item(item, "values")
            if values:
                name = values[0]
                self.set_current_structure(name) 

    def _add_structure_dialog(self):
        """Hiển thị dialog thêm cấu trúc"""
        dialog = tk.Toplevel(self)
        dialog.title("Thêm cấu trúc")
        dialog.geometry("400x500")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        
        # Frame chứa các tab
        tab_control = ttk.Notebook(dialog)
        
        # Tab chọn từ thư viện
        tab_library = ttk.Frame(tab_control)
        tab_control.add(tab_library, text="Từ thư viện")
        
        # Tab tạo cấu trúc tùy chỉnh
        tab_custom = ttk.Frame(tab_control)
        tab_control.add(tab_custom, text="Tùy chỉnh")
        
        tab_control.pack(expand=1, fill="both", padx=5, pady=5)
        
        # Thiết kế Tab thư viện
        # Frame chứa combobox danh mục
        cat_frame = ttk.Frame(tab_library)
        cat_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(cat_frame, text="Danh mục:").pack(side=tk.LEFT)
        cat_combo = ttk.Combobox(cat_frame, values=list(self.organ_library.categories.keys()))
        cat_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        cat_combo.current(0)
        
        # Frame chứa list cơ quan
        organs_frame = ttk.Frame(tab_library)
        organs_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ttk.Label(organs_frame, text="Cơ quan:").pack(anchor=tk.W)
        
        # Tạo listbox kèm scrollbar
        organs_listbox = tk.Listbox(organs_frame, selectmode=tk.SINGLE, height=10)
        scrollbar = ttk.Scrollbar(organs_frame, orient="vertical", command=organs_listbox.yview)
        organs_listbox.configure(yscrollcommand=scrollbar.set)
        
        organs_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Cập nhật listbox khi chọn danh mục
        def update_organs_list(event=None):
            category = cat_combo.get()
            organs = self.organ_library.get_organs_by_category(category)
            
            organs_listbox.delete(0, tk.END)
            for organ in organs:
                organs_listbox.insert(tk.END, f"{organ.name} ({organ.display_name})")
        
        cat_combo.bind("<<ComboboxSelected>>", update_organs_list)
        update_organs_list()  # Cập nhật ban đầu
        
        # Hiển thị thông tin chi tiết khi chọn cơ quan
        info_frame = ttk.LabelFrame(tab_library, text="Thông tin chi tiết")
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        info_text = tk.Text(info_frame, height=6, width=40, wrap=tk.WORD)
        info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        info_text.config(state=tk.DISABLED)
        
        def show_organ_info(event=None):
            selection = organs_listbox.curselection()
            if selection:
                idx = selection[0]
                organ_name = organs_listbox.get(idx).split(" (")[0]
                organ = self.organ_library.get_organ(organ_name)
                
                if organ:
                    info_text.config(state=tk.NORMAL)
                    info_text.delete(1.0, tk.END)
                    info_text.insert(tk.END, f"Tên: {organ.display_name}\n")
                    info_text.insert(tk.END, f"Danh mục: {organ.category}\n")
                    info_text.insert(tk.END, f"Màu: {organ.color}\n")
                    info_text.insert(tk.END, f"Phạm vi HU: {organ.hu_range}\n")
                    info_text.insert(tk.END, f"Mật độ: {organ.density} g/cm³\n")
                    info_text.insert(tk.END, f"α/β: {organ.alpha_beta} Gy\n")
                    
                    if organ.dose_constraints:
                        info_text.insert(tk.END, "\nGiới hạn liều:\n")
                        for constraint in organ.dose_constraints:
                            if constraint["volume"] is not None:
                                info_text.insert(tk.END, f"- {constraint['type']} {constraint['dose']} Gy cho {constraint['volume']}%\n")
                            else:
                                info_text.insert(tk.END, f"- {constraint['type']} {constraint['dose']} Gy\n")
                    
                    info_text.config(state=tk.DISABLED)
        
        organs_listbox.bind("<<ListboxSelect>>", show_organ_info)
        
        # Thiết kế Tab tùy chỉnh
        custom_frame = ttk.Frame(tab_custom)
        custom_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ttk.Label(custom_frame, text="Tên cấu trúc:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        name_entry = ttk.Entry(custom_frame, width=30)
        name_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(custom_frame, text="Tên hiển thị:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        display_name_entry = ttk.Entry(custom_frame, width=30)
        display_name_entry.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(custom_frame, text="Danh mục:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        custom_cat_combo = ttk.Combobox(custom_frame, values=list(self.organ_library.categories.keys()))
        custom_cat_combo.grid(row=2, column=1, padx=5, pady=5)
        custom_cat_combo.current(0)
        
        ttk.Label(custom_frame, text="Màu sắc:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        color_frame = ttk.Frame(custom_frame)
        color_frame.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)
        
        color_preview = tk.Canvas(color_frame, width=20, height=20, bg="#FF0000")
        color_preview.pack(side=tk.LEFT, padx=5)
        
        current_color = "#FF0000"
        
        def choose_color():
            nonlocal current_color
            color = colorchooser.askcolor(title="Chọn màu", initialcolor=current_color)
            if color[1]:
                current_color = color[1]
                color_preview.config(bg=current_color)
        
        ttk.Button(color_frame, text="Chọn màu", command=choose_color).pack(side=tk.LEFT)
        
        ttk.Label(custom_frame, text="Phạm vi HU:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        hu_frame = ttk.Frame(custom_frame)
        hu_frame.grid(row=4, column=1, padx=5, pady=5)
        
        ttk.Label(hu_frame, text="Min:").pack(side=tk.LEFT)
        hu_min_entry = ttk.Entry(hu_frame, width=6)
        hu_min_entry.pack(side=tk.LEFT, padx=2)
        hu_min_entry.insert(0, "-100")
        
        ttk.Label(hu_frame, text="Max:").pack(side=tk.LEFT, padx=5)
        hu_max_entry = ttk.Entry(hu_frame, width=6)
        hu_max_entry.pack(side=tk.LEFT)
        hu_max_entry.insert(0, "100")
        
        ttk.Label(custom_frame, text="Mật độ (g/cm³):").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        density_entry = ttk.Entry(custom_frame, width=10)
        density_entry.grid(row=5, column=1, sticky=tk.W, padx=5, pady=5)
        density_entry.insert(0, "1.0")
        
        ttk.Label(custom_frame, text="α/β (Gy):").grid(row=6, column=0, sticky=tk.W, padx=5, pady=5)
        alphabeta_entry = ttk.Entry(custom_frame, width=10)
        alphabeta_entry.grid(row=6, column=1, sticky=tk.W, padx=5, pady=5)
        alphabeta_entry.insert(0, "10.0")
        
        # Frame chứa nút
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=5, pady=10)
        
        # Hàm thêm cấu trúc
        def add_selected_structure():
            if tab_control.index(tab_control.select()) == 0:  # Tab thư viện
                selection = organs_listbox.curselection()
                if not selection:
                    messagebox.showwarning("Cảnh báo", "Vui lòng chọn một cơ quan từ danh sách.")
                    return
                    
                idx = selection[0]
                organ_name = organs_listbox.get(idx).split(" (")[0]
                organ = self.organ_library.get_organ(organ_name)
                
                if organ:
                    # Chuyển mã màu hex sang RGB cho ContourTools
                    color_hex = organ.color.lstrip('#')
                    color_rgb = tuple(int(color_hex[i:i+2], 16) for i in (0, 2, 4))
                    
                    # Thêm vào danh sách
                    success = self.add_structure(organ.name, color_rgb, organ.category)
                    if success:
                        messagebox.showinfo("Thông báo", f"Đã thêm cấu trúc {organ.display_name}.")
                        dialog.destroy()
                    else:
                        messagebox.showwarning("Cảnh báo", f"Cấu trúc {organ.display_name} đã tồn tại.")
            else:  # Tab tùy chỉnh
                name = name_entry.get().strip()
                display_name = display_name_entry.get().strip()
                category = custom_cat_combo.get()
                
                if not name:
                    messagebox.showwarning("Cảnh báo", "Vui lòng nhập tên cấu trúc.")
                    return
                    
                if not display_name:
                    display_name = name
                    
                try:
                    hu_min = int(hu_min_entry.get())
                    hu_max = int(hu_max_entry.get())
                    density = float(density_entry.get())
                    alphabeta = float(alphabeta_entry.get())
                except ValueError:
                    messagebox.showwarning("Cảnh báo", "Giá trị phạm vi HU, mật độ hoặc α/β không hợp lệ.")
                    return
                    
                # Tạo cơ quan tùy chỉnh
                organ = self.organ_library.create_custom_organ(
                    name, display_name, current_color, category,
                    (hu_min, hu_max), density, alphabeta
                )
                
                # Chuyển mã màu hex sang RGB cho ContourTools
                color_hex = current_color.lstrip('#')
                color_rgb = tuple(int(color_hex[i:i+2], 16) for i in (0, 2, 4))
                
                # Thêm vào danh sách
                success = self.add_structure(organ.name, color_rgb, organ.category)
                if success:
                    messagebox.showinfo("Thông báo", f"Đã tạo cấu trúc tùy chỉnh {organ.display_name}.")
                    dialog.destroy()
                else:
                    messagebox.showwarning("Cảnh báo", f"Cấu trúc {organ.display_name} đã tồn tại.")
        
        ttk.Button(button_frame, text="Thêm", command=add_selected_structure).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Hủy", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def _edit_structure_dialog(self):
        """Hiển thị dialog chỉnh sửa cấu trúc"""
        if not self.current_structure:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một cấu trúc để chỉnh sửa.")
            return
        
        # Lấy thông tin cấu trúc hiện tại
        struct_name = self.current_structure
        organ = self.organ_library.get_organ(struct_name)
        
        if not organ:
            messagebox.showwarning("Cảnh báo", f"Không tìm thấy thông tin cấu trúc {struct_name} trong thư viện.")
            return
        
        # Tạo dialog
        dialog = tk.Toplevel(self)
        dialog.title(f"Chỉnh sửa cấu trúc: {organ.display_name}")
        dialog.geometry("400x400")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        
        # Frame chính
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Các field chỉnh sửa
        ttk.Label(main_frame, text="Tên hiển thị:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        display_name_entry = ttk.Entry(main_frame, width=30)
        display_name_entry.grid(row=0, column=1, padx=5, pady=5)
        display_name_entry.insert(0, organ.display_name)
        
        ttk.Label(main_frame, text="Danh mục:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        cat_combo = ttk.Combobox(main_frame, values=list(self.organ_library.categories.keys()))
        cat_combo.grid(row=1, column=1, padx=5, pady=5)
        cat_combo.set(organ.category)
        
        ttk.Label(main_frame, text="Màu sắc:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        color_frame = ttk.Frame(main_frame)
        color_frame.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
        color_preview = tk.Canvas(color_frame, width=20, height=20, bg=organ.color)
        color_preview.pack(side=tk.LEFT, padx=5)
        
        current_color = organ.color
        
        def choose_color():
            nonlocal current_color
            color = colorchooser.askcolor(title="Chọn màu", initialcolor=current_color)
            if color[1]:
                current_color = color[1]
                color_preview.config(bg=current_color)
        
        ttk.Button(color_frame, text="Chọn màu", command=choose_color).pack(side=tk.LEFT)
        
        ttk.Label(main_frame, text="Phạm vi HU:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        hu_frame = ttk.Frame(main_frame)
        hu_frame.grid(row=3, column=1, padx=5, pady=5)
        
        ttk.Label(hu_frame, text="Min:").pack(side=tk.LEFT)
        hu_min_entry = ttk.Entry(hu_frame, width=6)
        hu_min_entry.pack(side=tk.LEFT, padx=2)
        hu_min_entry.insert(0, str(organ.hu_range[0]))
        
        ttk.Label(hu_frame, text="Max:").pack(side=tk.LEFT, padx=5)
        hu_max_entry = ttk.Entry(hu_frame, width=6)
        hu_max_entry.pack(side=tk.LEFT)
        hu_max_entry.insert(0, str(organ.hu_range[1]))
        
        ttk.Label(main_frame, text="Mật độ (g/cm³):").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        density_entry = ttk.Entry(main_frame, width=10)
        density_entry.grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        density_entry.insert(0, str(organ.density))
        
        ttk.Label(main_frame, text="α/β (Gy):").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        alphabeta_entry = ttk.Entry(main_frame, width=10)
        alphabeta_entry.grid(row=5, column=1, sticky=tk.W, padx=5, pady=5)
        alphabeta_entry.insert(0, str(organ.alpha_beta))
        
        # Frame chứa giới hạn liều
        constraints_frame = ttk.LabelFrame(main_frame, text="Giới hạn liều")
        constraints_frame.grid(row=6, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W+tk.E)
        
        # Listbox hiển thị giới hạn liều
        constraints_listbox = tk.Listbox(constraints_frame, height=5)
        constraints_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Hiển thị các giới hạn liều
        for constraint in organ.dose_constraints:
            if constraint["volume"] is not None:
                constraints_listbox.insert(tk.END, f"{constraint['type']} {constraint['dose']} Gy cho {constraint['volume']}%")
            else:
                constraints_listbox.insert(tk.END, f"{constraint['type']} {constraint['dose']} Gy")
        
        # Frame chứa nút
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=5, pady=10)
        
        # Hàm cập nhật cấu trúc
        def update_structure():
            try:
                hu_min = int(hu_min_entry.get())
                hu_max = int(hu_max_entry.get())
                density = float(density_entry.get())
                alphabeta = float(alphabeta_entry.get())
            except ValueError:
                messagebox.showwarning("Cảnh báo", "Giá trị phạm vi HU, mật độ hoặc α/β không hợp lệ.")
                return
            
            # Cập nhật thông tin cơ quan trong thư viện
            organ.display_name = display_name_entry.get().strip()
            organ.category = cat_combo.get()
            organ.color = current_color
            organ.hu_range = (hu_min, hu_max)
            organ.density = density
            organ.alpha_beta = alphabeta
            
            # Cập nhật lại thư viện
            self.organ_library.update_organ(organ)
            
            # Cập nhật màu sắc trong contour_tools
            color_hex = current_color.lstrip('#')
            color_rgb = tuple(int(color_hex[i:i+2], 16) for i in (0, 2, 4))
            self.contour_tools.colors[struct_name] = color_rgb
            
            # Cập nhật giao diện
            self.update_struct_list()
            
            # Thông báo
            messagebox.showinfo("Thông báo", f"Đã cập nhật cấu trúc {organ.display_name}.")
            dialog.destroy()
        
        ttk.Button(button_frame, text="Cập nhật", command=update_structure).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Hủy", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def _delete_structure(self):
        """Xóa cấu trúc đang chọn"""
        if not self.current_structure:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một cấu trúc để xóa.")
            return
        
        # Xác nhận xóa
        confirm = messagebox.askyesno("Xác nhận", f"Bạn có chắc chắn muốn xóa cấu trúc {self.current_structure}?")
        if not confirm:
            return
        
        # Xóa contour
        self.contour_tools.delete_contour(self.current_structure)
        
        # Xóa khỏi danh sách
        if self.current_structure in self.structures:
            del self.structures[self.current_structure]
        
        # Cập nhật giao diện
        self.current_structure = None
        self.update_struct_list()
        
        # Gọi callback
        if self.on_update_callback:
            self.on_update_callback()
        
        # Thông báo
        messagebox.showinfo("Thông báo", "Đã xóa cấu trúc.")

    def _change_color(self):
        """Đổi màu cấu trúc"""
        if not self.current_structure:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một cấu trúc để đổi màu.")
            return
        
        # Lấy thông tin cấu trúc hiện tại
        struct_name = self.current_structure
        organ = self.organ_library.get_organ(struct_name)
        
        if not organ:
            messagebox.showwarning("Cảnh báo", f"Không tìm thấy thông tin cấu trúc {struct_name} trong thư viện.")
            return
        
        # Tạo dialog để chọn màu
        color = colorchooser.askcolor(title="Chọn màu", initialcolor=organ.color)
        if color[1]:
            # Cập nhật màu sắc của cấu trúc trong thư viện
            organ.color = color[1]
            
            # Cập nhật màu sắc trong contour_tools
            self.contour_tools.colors[struct_name] = tuple(int(color[1][i:i+2], 16) for i in (0, 2, 4))
            
            # Cập nhật giao diện
            self.update_struct_list()
            
            # Thông báo
            messagebox.showinfo("Thông báo", f"Đã đổi màu cấu trúc {struct_name} thành {color[1]}.")

    def _activate_free_contour(self):
        """Kích hoạt chức năng vẽ contour tự do"""
        # Implementation of _activate_free_contour method
        pass

    def _activate_rect_contour(self):
        """Kích hoạt chức năng vẽ contour hình chữ nhật"""
        # Implementation of _activate_rect_contour method
        pass

    def _activate_circle_contour(self):
        """Kích hoạt chức năng vẽ contour hình tròn"""
        # Implementation of _activate_circle_contour method
        pass

    def _auto_contour(self):
        """Kích hoạt chức năng tự động tạo contour"""
        # Implementation of _auto_contour method
        pass

    def _interpolate_contour(self):
        """Kích hoạt chức năng nội suy contour"""
        # Implementation of _interpolate_contour method
        pass 