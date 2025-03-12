"""
Module giao diện người dùng cho quản lý cấu trúc trong kế hoạch xạ trị.
"""

import tkinter as tk
from tkinter import ttk, messagebox, colorchooser, simpledialog
import numpy as np
from typing import Dict, List, Optional, Callable, Any
import uuid
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from quangstation.core.utils.logging import get_logger
from quangstation.clinical.contouring.contour_tools import ContourTools

logger = get_logger(__name__)

class StructureView:
    """
    Giao diện quản lý cấu trúc giải phẫu trong kế hoạch xạ trị.
    
    Lớp này cung cấp giao diện để:
    - Hiển thị danh sách cấu trúc
    - Thêm/xóa/sửa cấu trúc
    - Thiết lập thuộc tính cấu trúc (loại, màu, v.v.)
    - Hiển thị thống kê cấu trúc
    """
    
    # Các loại cấu trúc tiêu chuẩn
    STRUCTURE_TYPES = [
        "PTV", "CTV", "GTV", "BODY", "ORGAN", "EXTERNAL", "BOLUS", 
        "SUPPORT", "FIXATION", "CONTRAST", "CAVITY", "ARTIFACT"
    ]
    
    # Các màu mặc định cho các loại cấu trúc
    DEFAULT_COLORS = {
        "PTV": "#FF0000",     # Đỏ
        "CTV": "#FFA500",     # Cam
        "GTV": "#FFFF00",     # Vàng
        "BODY": "#00FF00",    # Xanh lá
        "ORGAN": "#0000FF",   # Xanh dương
        "EXTERNAL": "#808080", # Xám
        "BOLUS": "#800080",   # Tím
        "SUPPORT": "#A52A2A", # Nâu
        "FIXATION": "#2E8B57", # Xanh biển
        "CONTRAST": "#FF1493", # Hồng
        "CAVITY": "#40E0D0",  # Xanh ngọc
        "ARTIFACT": "#FF6347"  # Cà chua
    }
    
    def __init__(self, parent, main_view):
        """
        Khởi tạo giao diện quản lý cấu trúc.
        
        Args:
            parent: Widget cha
            main_view: Đối tượng view chính (PlanDesignView)
        """
        self.parent = parent
        self.main_view = main_view
        
        # Biến điều khiển UI
        self.structure_name_var = tk.StringVar()
        self.structure_type_var = tk.StringVar(value="ORGAN")
        self.structure_color_var = tk.StringVar(value="#0000FF")
        self.structure_opacity_var = tk.DoubleVar(value=0.5)
        self.structure_visible_var = tk.BooleanVar(value=True)
        
        # Cấu trúc hiện tại được chọn
        self.selected_structure_index = None
        
        # Danh sách cấu trúc
        self.structures = []
        if hasattr(self.main_view, 'structures') and self.main_view.structures:
            for name, mask in self.main_view.structures.items():
                # Tạo cấu trúc với dữ liệu cơ bản
                structure = {
                    'id': str(uuid.uuid4()),
                    'name': name,
                    'type': self._guess_structure_type(name),
                    'color': self._get_default_color(name),
                    'opacity': 0.5,
                    'visible': True,
                    'mask': mask  # Lưu trữ mask numpy
                }
                self.structures.append(structure)
        
        # Công cụ contour
        self.contour_tools = ContourTools()
        
        # Thiết lập UI
        self.setup_ui()
        
        # Cập nhật danh sách cấu trúc
        self.update_structure_list()
        
        logger.info("Đã khởi tạo giao diện quản lý cấu trúc")

    def _guess_structure_type(self, name):
        """Đoán loại cấu trúc dựa trên tên"""
        name_upper = name.upper()
        
        if "PTV" in name_upper:
            return "PTV"
        elif "CTV" in name_upper:
            return "CTV"
        elif "GTV" in name_upper:
            return "GTV"
        elif "BODY" in name_upper or "EXTERNAL" in name_upper:
            return "BODY"
        elif "BOLUS" in name_upper:
            return "BOLUS"
        else:
            return "ORGAN"
    
    def _get_default_color(self, name):
        """Lấy màu mặc định dựa trên tên/loại cấu trúc"""
        structure_type = self._guess_structure_type(name)
        return self.DEFAULT_COLORS.get(structure_type, "#0000FF")  # Mặc định là màu xanh dương
    
    def setup_ui(self):
        """Thiết lập giao diện người dùng"""
        # Frame chính
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Chia thành 2 phần: trái và phải
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Frame trái - Danh sách cấu trúc
        left_frame = ttk.Frame(paned_window)
        paned_window.add(left_frame, weight=1)
        
        # Tiêu đề
        ttk.Label(left_frame, text="Danh sách cấu trúc", font=("Arial", 10, "bold")).pack(pady=5)
        
        # Danh sách cấu trúc
        structure_frame = ttk.Frame(left_frame)
        structure_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Thêm thanh cuộn
        scrollbar = ttk.Scrollbar(structure_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.structure_listbox = tk.Listbox(structure_frame, width=40, height=20, yscrollcommand=scrollbar.set)
        self.structure_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.structure_listbox.yview)
        
        self.structure_listbox.bind('<<ListboxSelect>>', self.on_structure_select)
        
        # Nút điều khiển
        control_frame = ttk.Frame(left_frame)
        control_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(control_frame, text="Thêm", command=self.add_structure).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Xóa", command=self.delete_structure).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Sao chép", command=self.duplicate_structure).pack(side=tk.LEFT, padx=2)
        
        # Frame phải - Thông tin và thống kê cấu trúc
        right_frame = ttk.Frame(paned_window)
        paned_window.add(right_frame, weight=2)
        
        # Notebook cho các tab
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tab thuộc tính
        properties_frame = ttk.Frame(self.notebook)
        self.notebook.add(properties_frame, text="Thuộc tính")
        
        # Thông tin cơ bản
        basic_frame = ttk.LabelFrame(properties_frame, text="Thông tin cơ bản")
        basic_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Tên cấu trúc
        ttk.Label(basic_frame, text="Tên:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(basic_frame, textvariable=self.structure_name_var).grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # Loại cấu trúc
        ttk.Label(basic_frame, text="Loại:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        type_combo = ttk.Combobox(basic_frame, textvariable=self.structure_type_var)
        type_combo['values'] = self.STRUCTURE_TYPES
        type_combo.grid(row=1, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        type_combo.bind('<<ComboboxSelected>>', self.on_type_changed)
        
        # Màu sắc
        ttk.Label(basic_frame, text="Màu:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        color_frame = ttk.Frame(basic_frame)
        color_frame.grid(row=2, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        color_entry = ttk.Entry(color_frame, textvariable=self.structure_color_var, width=10)
        color_entry.pack(side=tk.LEFT, padx=5)
        
        color_button = ttk.Button(color_frame, text="Chọn", command=self.choose_color)
        color_button.pack(side=tk.LEFT, padx=5)
        
        self.color_preview = tk.Canvas(color_frame, width=20, height=20, bg=self.structure_color_var.get())
        self.color_preview.pack(side=tk.LEFT, padx=5)
        
        # Độ trong suốt
        ttk.Label(basic_frame, text="Độ trong suốt:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        opacity_scale = ttk.Scale(basic_frame, variable=self.structure_opacity_var, from_=0.0, to=1.0, 
                                 orient=tk.HORIZONTAL, length=200)
        opacity_scale.grid(row=3, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # Hiển thị
        visible_check = ttk.Checkbutton(basic_frame, text="Hiển thị", variable=self.structure_visible_var)
        visible_check.grid(row=4, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        # Nút cập nhật
        update_button = ttk.Button(basic_frame, text="Cập nhật", command=self.update_structure)
        update_button.grid(row=5, column=0, columnspan=2, sticky=tk.E, padx=5, pady=10)
        
        # Tab thống kê
        stats_frame = ttk.Frame(self.notebook)
        self.notebook.add(stats_frame, text="Thống kê")
        
        # Bảng thống kê
        self.stats_text = tk.Text(stats_frame, height=15, width=50)
        self.stats_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tab hiển thị 3D
        view3d_frame = ttk.Frame(self.notebook)
        self.notebook.add(view3d_frame, text="Hiển thị 3D")
        
        # Hiển thị 3D sẽ được triển khai sau
        ttk.Label(view3d_frame, text="Chức năng hiển thị 3D sẽ được triển khai sau").pack(pady=20)
    
    def update_structure_list(self):
        """Cập nhật danh sách cấu trúc"""
        # Xóa danh sách cũ
        self.structure_listbox.delete(0, tk.END)
        
        # Thêm các cấu trúc vào danh sách
        for i, structure in enumerate(self.structures):
            name = structure.get('name', f"Structure_{i+1}")
            type_str = structure.get('type', 'ORGAN')
            self.structure_listbox.insert(tk.END, f"{name} ({type_str})")
            
            # Nếu cấu trúc không hiển thị, đổi màu sang xám
            if not structure.get('visible', True):
                self.structure_listbox.itemconfig(i, fg='gray')
        
        # Cập nhật cấu trúc trong main_view.structures
        if hasattr(self.main_view, 'structures'):
            structures_dict = {}
            for structure in self.structures:
                name = structure.get('name', '')
                mask = structure.get('mask', None)
                if name and mask is not None:
                    structures_dict[name] = mask
            
            self.main_view.structures = structures_dict
    
    def on_structure_select(self, event):
        """Xử lý khi chọn cấu trúc từ danh sách"""
        try:
            # Lấy index của cấu trúc được chọn
            index = self.structure_listbox.curselection()[0]
            
            # Lưu index
            self.selected_structure_index = index
            
            # Hiển thị thông tin của cấu trúc
            self.display_structure_info(self.structures[index])
            
            # Hiển thị thống kê của cấu trúc
            self.display_structure_stats(self.structures[index])
        except (IndexError, KeyError) as e:
            logger.warning(f"Lỗi khi chọn cấu trúc: {str(e)}")
    
    def display_structure_info(self, structure):
        """Hiển thị thông tin của cấu trúc"""
        # Cập nhật biến điều khiển UI
        self.structure_name_var.set(structure.get('name', ''))
        self.structure_type_var.set(structure.get('type', 'ORGAN'))
        
        color = structure.get('color', '#0000FF')
        self.structure_color_var.set(color)
        self.color_preview.config(bg=color)
        
        self.structure_opacity_var.set(structure.get('opacity', 0.5))
        self.structure_visible_var.set(structure.get('visible', True))
    
    def display_structure_stats(self, structure):
        """Hiển thị thống kê của cấu trúc"""
        # Xóa nội dung cũ
        self.stats_text.delete(1.0, tk.END)
        
        # Lấy mask của cấu trúc
        mask = structure.get('mask', None)
        if mask is None:
            self.stats_text.insert(tk.END, "Không có dữ liệu cấu trúc")
            return
        
        # Tính toán thống kê
        try:
            volume_cc = np.sum(mask) * 0.001  # Giả sử mỗi voxel có thể tích 1mm³
            surface_area = self.contour_tools.calculate_surface_area(mask)
            min_x, max_x, min_y, max_y, min_z, max_z = self.contour_tools.get_bounding_box(mask)
            
            # Hiển thị thống kê
            stats = f"--- {structure.get('name', '')} ---\n\n"
            stats += f"Loại: {structure.get('type', 'ORGAN')}\n"
            stats += f"Thể tích: {volume_cc:.2f} cc\n"
            stats += f"Diện tích bề mặt: {surface_area:.2f} mm²\n\n"
            
            stats += "Kích thước:\n"
            stats += f"Chiều rộng (X): {max_x - min_x:.2f} mm\n"
            stats += f"Chiều cao (Y): {max_y - min_y:.2f} mm\n"
            stats += f"Chiều dài (Z): {max_z - min_z:.2f} mm\n\n"
            
            stats += "Vị trí:\n"
            stats += f"X: {min_x:.1f} đến {max_x:.1f} mm\n"
            stats += f"Y: {min_y:.1f} đến {max_y:.1f} mm\n"
            stats += f"Z: {min_z:.1f} đến {max_z:.1f} mm\n"
            
            self.stats_text.insert(tk.END, stats)
        except Exception as e:
            logger.error(f"Lỗi khi tính toán thống kê cấu trúc: {str(e)}")
            self.stats_text.insert(tk.END, f"Lỗi khi tính toán thống kê: {str(e)}")
    
    def on_type_changed(self, event):
        """Xử lý khi thay đổi loại cấu trúc"""
        # Lấy loại mới
        new_type = self.structure_type_var.get()
        
        # Cập nhật màu mặc định theo loại
        if new_type in self.DEFAULT_COLORS:
            color = self.DEFAULT_COLORS[new_type]
            self.structure_color_var.set(color)
            self.color_preview.config(bg=color)
    
    def choose_color(self):
        """Mở hộp thoại chọn màu"""
        # Lấy màu hiện tại
        current_color = self.structure_color_var.get()
        
        # Mở hộp thoại chọn màu
        color = colorchooser.askcolor(initialcolor=current_color)
        
        # Nếu người dùng chọn màu (không nhấn Cancel)
        if color[1]:
            self.structure_color_var.set(color[1])
            self.color_preview.config(bg=color[1])
    
    def add_structure(self):
        """Thêm cấu trúc mới"""
        # Mở hộp thoại nhập tên cấu trúc
        name = simpledialog.askstring("Thêm cấu trúc", "Nhập tên cấu trúc:")
        if not name:
            return
        
        # Tạo cấu trúc mới
        structure_type = "ORGAN"  # Mặc định
        color = self.DEFAULT_COLORS.get(structure_type, "#0000FF")
        
        new_structure = {
            'id': str(uuid.uuid4()),
            'name': name,
            'type': structure_type,
            'color': color,
            'opacity': 0.5,
            'visible': True,
            'mask': None  # Chưa có dữ liệu mask
        }
        
        # Thêm vào danh sách
        self.structures.append(new_structure)
        
        # Cập nhật danh sách
        self.update_structure_list()
        
        # Chọn cấu trúc mới
        self.structure_listbox.selection_clear(0, tk.END)
        self.structure_listbox.selection_set(len(self.structures) - 1)
        self.structure_listbox.see(len(self.structures) - 1)
        self.on_structure_select(None)
        
        # Thông báo
        messagebox.showinfo("Thông báo", "Đã thêm cấu trúc mới. \nBạn cần vẽ contour cho cấu trúc này.")
        
        logger.info(f"Đã thêm cấu trúc mới: {name}")
    
    def delete_structure(self):
        """Xóa cấu trúc đã chọn"""
        if self.selected_structure_index is None:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một cấu trúc để xóa")
            return
        
        # Xác nhận xóa
        structure_name = self.structures[self.selected_structure_index].get('name', 'cấu trúc này')
        if not messagebox.askyesno("Xác nhận", f"Bạn có chắc chắn muốn xóa {structure_name}?"):
            return
        
        # Xóa khỏi danh sách
        del self.structures[self.selected_structure_index]
        
        # Cập nhật danh sách
        self.update_structure_list()
        
        # Xóa lựa chọn
        self.selected_structure_index = None
        
        logger.info(f"Đã xóa cấu trúc: {structure_name}")
    
    def duplicate_structure(self):
        """Sao chép cấu trúc đã chọn"""
        if self.selected_structure_index is None:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một cấu trúc để sao chép")
            return
        
        # Lấy cấu trúc gốc
        original_structure = self.structures[self.selected_structure_index]
        
        # Tạo bản sao
        import copy
        new_structure = copy.deepcopy(original_structure)
        
        # Tạo ID mới
        new_structure['id'] = str(uuid.uuid4())
        
        # Đổi tên
        original_name = original_structure.get('name', 'Structure')
        new_structure['name'] = f"{original_name}_copy"
        
        # Thêm vào danh sách
        self.structures.append(new_structure)
        
        # Cập nhật danh sách
        self.update_structure_list()
        
        # Chọn cấu trúc mới
        self.structure_listbox.selection_clear(0, tk.END)
        self.structure_listbox.selection_set(len(self.structures) - 1)
        self.structure_listbox.see(len(self.structures) - 1)
        self.on_structure_select(None)
        
        logger.info(f"Đã sao chép cấu trúc: {original_name} -> {new_structure['name']}")
    
    def update_structure(self):
        """Cập nhật thông tin cấu trúc đã chọn"""
        if self.selected_structure_index is None:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một cấu trúc để cập nhật")
            return
        
        try:
            # Lấy cấu trúc hiện tại
            structure = self.structures[self.selected_structure_index]
            
            # Lưu tên cũ để kiểm tra xem có thay đổi không
            old_name = structure.get('name', '')
            
            # Cập nhật thông tin
            structure['name'] = self.structure_name_var.get()
            structure['type'] = self.structure_type_var.get()
            structure['color'] = self.structure_color_var.get()
            structure['opacity'] = self.structure_opacity_var.get()
            structure['visible'] = self.structure_visible_var.get()
            
            # Nếu tên thay đổi, cập nhật lại dictionary structures trong main_view
            if old_name != structure['name'] and hasattr(self.main_view, 'structures'):
                if old_name in self.main_view.structures:
                    mask = self.main_view.structures.pop(old_name)
                    self.main_view.structures[structure['name']] = mask
            
            # Cập nhật danh sách
            self.update_structure_list()
            
            # Cập nhật lựa chọn
            self.structure_listbox.selection_clear(0, tk.END)
            self.structure_listbox.selection_set(self.selected_structure_index)
            
            # Thông báo
            messagebox.showinfo("Thông báo", f"Đã cập nhật thông tin cấu trúc: {structure['name']}")
            
            logger.info(f"Đã cập nhật thông tin cấu trúc: {structure['name']}")
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật cấu trúc: {str(e)}")
            messagebox.showerror("Lỗi", f"Lỗi khi cập nhật cấu trúc: {str(e)}")
