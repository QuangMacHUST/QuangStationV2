"""
Module giao diện người dùng cho thiết lập chùm tia xạ trị.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
from typing import Dict, List, Optional, Callable, Any
import uuid

from quangstation.core.utils.logging import get_logger

logger = get_logger(__name__)

class BeamSetupView:
    """
    Giao diện thiết lập và quản lý chùm tia xạ trị.
    
    Lớp này cung cấp giao diện để:
    - Thêm/xóa/sửa chùm tia
    - Thiết lập thông số chùm tia (góc, năng lượng, v.v.)
    - Quản lý MLC (Multi-Leaf Collimator)
    """
    
    def __init__(self, parent, main_view):
        """
        Khởi tạo giao diện thiết lập chùm tia.
        
        Args:
            parent: Widget cha
            main_view: Đối tượng view chính (PlanDesignView)
        """
        self.parent = parent
        self.main_view = main_view
        
        # Biến điều khiển UI
        self.beam_name_var = tk.StringVar()
        self.beam_energy_var = tk.StringVar(value="6MV")
        self.beam_angle_var = tk.DoubleVar(value=0.0)
        self.beam_collimator_var = tk.DoubleVar(value=0.0)
        self.beam_gantry_var = tk.DoubleVar(value=0.0)
        self.beam_couch_var = tk.DoubleVar(value=0.0)
        self.beam_weight_var = tk.DoubleVar(value=1.0)
        self.beam_isocenter_x_var = tk.DoubleVar(value=0.0)
        self.beam_isocenter_y_var = tk.DoubleVar(value=0.0)
        self.beam_isocenter_z_var = tk.DoubleVar(value=0.0)
        
        # Beams list
        self.beams = self.main_view.plan_data.get('beams', [])
        
        # Selected beam index
        self.selected_beam_index = None
        
        # Thiết lập UI
        self.setup_ui()
        
        # Cập nhật danh sách chùm tia
        self.update_beam_list()
        
        logger.info("Đã khởi tạo giao diện thiết lập chùm tia")
    
    def setup_ui(self):
        """Thiết lập giao diện người dùng"""
        # Frame chính
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Frame trái - Danh sách chùm tia
        left_frame = ttk.LabelFrame(main_frame, text="Danh sách chùm tia")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Danh sách chùm tia
        self.beam_listbox = tk.Listbox(left_frame, width=40, height=20)
        self.beam_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.beam_listbox.bind('<<ListboxSelect>>', self.on_beam_select)
        
        # Nút điều khiển danh sách
        list_control_frame = ttk.Frame(left_frame)
        list_control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(list_control_frame, text="Thêm", command=self.add_beam).pack(side=tk.LEFT, padx=2)
        ttk.Button(list_control_frame, text="Xóa", command=self.delete_beam).pack(side=tk.LEFT, padx=2)
        ttk.Button(list_control_frame, text="Sao chép", command=self.duplicate_beam).pack(side=tk.LEFT, padx=2)
        
        # Frame phải - Thông số chùm tia
        right_frame = ttk.LabelFrame(main_frame, text="Thông số chùm tia")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Thông số cơ bản
        basic_frame = ttk.Frame(right_frame)
        basic_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Tên chùm tia
        ttk.Label(basic_frame, text="Tên chùm tia:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(basic_frame, textvariable=self.beam_name_var).grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # Năng lượng
        ttk.Label(basic_frame, text="Năng lượng:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        energy_combo = ttk.Combobox(basic_frame, textvariable=self.beam_energy_var)
        energy_combo['values'] = ('6MV', '10MV', '15MV', '6FFF', '10FFF', '6MeV', '9MeV', '12MeV', '15MeV')
        energy_combo.grid(row=1, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # Góc chùm tia
        angle_frame = ttk.LabelFrame(right_frame, text="Góc chùm tia")
        angle_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(angle_frame, text="Góc quay (°):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(angle_frame, textvariable=self.beam_angle_var).grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        ttk.Label(angle_frame, text="Góc cổng (°):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(angle_frame, textvariable=self.beam_gantry_var).grid(row=1, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        ttk.Label(angle_frame, text="Góc bàn (°):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(angle_frame, textvariable=self.beam_couch_var).grid(row=2, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        ttk.Label(angle_frame, text="Góc collimator (°):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(angle_frame, textvariable=self.beam_collimator_var).grid(row=3, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # Trọng số
        weight_frame = ttk.LabelFrame(right_frame, text="Trọng số")
        weight_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(weight_frame, text="Trọng số:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(weight_frame, textvariable=self.beam_weight_var).grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # Tâm chùm tia
        isocenter_frame = ttk.LabelFrame(right_frame, text="Tâm chùm tia")
        isocenter_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(isocenter_frame, text="X (mm):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(isocenter_frame, textvariable=self.beam_isocenter_x_var).grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        ttk.Label(isocenter_frame, text="Y (mm):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(isocenter_frame, textvariable=self.beam_isocenter_y_var).grid(row=1, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        ttk.Label(isocenter_frame, text="Z (mm):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(isocenter_frame, textvariable=self.beam_isocenter_z_var).grid(row=2, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # Nút điều khiển thông số
        control_frame = ttk.Frame(right_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(control_frame, text="Cập nhật", command=self.update_beam).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Thiết lập MLC", command=self.setup_mlc).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="BEV", command=self.show_beam_eye_view).pack(side=tk.LEFT, padx=2)
    
    def update_beam_list(self):
        """Cập nhật danh sách chùm tia"""
        # Xóa danh sách cũ
        self.beam_listbox.delete(0, tk.END)
        
        # Thêm các chùm tia vào danh sách
        for i, beam in enumerate(self.beams):
            self.beam_listbox.insert(tk.END, f"{i+1}. {beam.get('name', f'Beam_{i+1}')} - {beam.get('energy', '6MV')}")
        
        # Cập nhật danh sách chùm tia trong plan_data
        self.main_view.plan_data['beams'] = self.beams
    
    def on_beam_select(self, event):
        """Xử lý khi chọn chùm tia từ danh sách"""
        try:
            # Lấy index của chùm tia được chọn
            index = self.beam_listbox.curselection()[0]
            
            # Lưu index
            self.selected_beam_index = index
            
            # Hiển thị thông số của chùm tia
            self.display_beam_info(self.beams[index])
        except (IndexError, KeyError) as e:
            logger.warning(f"Lỗi khi chọn chùm tia: {str(e)}")
    
    def display_beam_info(self, beam: Dict[str, Any]):
        """Hiển thị thông tin của chùm tia"""
        # Cập nhật biến điều khiển UI
        self.beam_name_var.set(beam.get('name', ''))
        self.beam_energy_var.set(beam.get('energy', '6MV'))
        self.beam_angle_var.set(beam.get('angle', 0.0))
        self.beam_gantry_var.set(beam.get('gantry_angle', 0.0))
        self.beam_couch_var.set(beam.get('couch_angle', 0.0))
        self.beam_collimator_var.set(beam.get('collimator_angle', 0.0))
        self.beam_weight_var.set(beam.get('weight', 1.0))
        
        # Cập nhật tâm chùm tia
        isocenter = beam.get('isocenter', {'x': 0.0, 'y': 0.0, 'z': 0.0})
        self.beam_isocenter_x_var.set(isocenter.get('x', 0.0))
        self.beam_isocenter_y_var.set(isocenter.get('y', 0.0))
        self.beam_isocenter_z_var.set(isocenter.get('z', 0.0))
    
    def add_beam(self):
        """Thêm chùm tia mới"""
        # Tạo ID mới cho chùm tia
        beam_id = str(uuid.uuid4())
        
        # Tạo chùm tia mới
        new_beam = {
            'id': beam_id,
            'name': f"Beam_{len(self.beams) + 1}",
            'energy': '6MV',
            'angle': 0.0,
            'gantry_angle': 0.0,
            'couch_angle': 0.0,
            'collimator_angle': 0.0,
            'weight': 1.0,
            'isocenter': {'x': 0.0, 'y': 0.0, 'z': 0.0},
            'mlc': [],
            'jaws': {'x1': -100.0, 'x2': 100.0, 'y1': -100.0, 'y2': 100.0}
        }
        
        # Thêm vào danh sách
        self.beams.append(new_beam)
        
        # Cập nhật danh sách
        self.update_beam_list()
        
        # Chọn chùm tia mới
        self.beam_listbox.selection_clear(0, tk.END)
        self.beam_listbox.selection_set(len(self.beams) - 1)
        self.beam_listbox.see(len(self.beams) - 1)
        self.on_beam_select(None)
        
        logger.info(f"Đã thêm chùm tia mới: {new_beam['name']}")
    
    def delete_beam(self):
        """Xóa chùm tia đã chọn"""
        if self.selected_beam_index is None:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một chùm tia để xóa")
            return
        
        # Xác nhận xóa
        if not messagebox.askyesno("Xác nhận", "Bạn có chắc chắn muốn xóa chùm tia này?"):
            return
        
        # Lấy tên chùm tia để hiển thị thông báo
        beam_name = self.beams[self.selected_beam_index].get('name', f"Beam_{self.selected_beam_index+1}")
        
        # Xóa khỏi danh sách
        del self.beams[self.selected_beam_index]
        
        # Cập nhật danh sách
        self.update_beam_list()
        
        # Xóa lựa chọn
        self.selected_beam_index = None
        
        logger.info(f"Đã xóa chùm tia: {beam_name}")
    
    def duplicate_beam(self):
        """Sao chép chùm tia đã chọn"""
        if self.selected_beam_index is None:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một chùm tia để sao chép")
            return
        
        # Lấy chùm tia gốc
        original_beam = self.beams[self.selected_beam_index]
        
        # Tạo bản sao
        import copy
        new_beam = copy.deepcopy(original_beam)
        
        # Tạo ID mới
        new_beam['id'] = str(uuid.uuid4())
        
        # Đổi tên
        new_beam['name'] = f"{original_beam.get('name', 'Beam')} (Copy)"
        
        # Thêm vào danh sách
        self.beams.append(new_beam)
        
        # Cập nhật danh sách
        self.update_beam_list()
        
        # Chọn chùm tia mới
        self.beam_listbox.selection_clear(0, tk.END)
        self.beam_listbox.selection_set(len(self.beams) - 1)
        self.beam_listbox.see(len(self.beams) - 1)
        self.on_beam_select(None)
        
        logger.info(f"Đã sao chép chùm tia: {original_beam.get('name')} -> {new_beam['name']}")
    
    def update_beam(self):
        """Cập nhật thông số chùm tia đã chọn"""
        if self.selected_beam_index is None:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một chùm tia để cập nhật")
            return
        
        try:
            # Lấy chùm tia hiện tại
            beam = self.beams[self.selected_beam_index]
            
            # Cập nhật thông số
            beam['name'] = self.beam_name_var.get()
            beam['energy'] = self.beam_energy_var.get()
            beam['angle'] = self.beam_angle_var.get()
            beam['gantry_angle'] = self.beam_gantry_var.get()
            beam['couch_angle'] = self.beam_couch_var.get()
            beam['collimator_angle'] = self.beam_collimator_var.get()
            beam['weight'] = self.beam_weight_var.get()
            
            # Cập nhật tâm chùm tia
            beam['isocenter'] = {
                'x': self.beam_isocenter_x_var.get(),
                'y': self.beam_isocenter_y_var.get(),
                'z': self.beam_isocenter_z_var.get()
            }
            
            # Cập nhật danh sách
            self.update_beam_list()
            
            # Cập nhật lựa chọn
            self.beam_listbox.selection_clear(0, tk.END)
            self.beam_listbox.selection_set(self.selected_beam_index)
            
            logger.info(f"Đã cập nhật thông số chùm tia: {beam['name']}")
            
            # Hiển thị thông báo
            messagebox.showinfo("Thông báo", f"Đã cập nhật thông số chùm tia: {beam['name']}")
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật chùm tia: {str(e)}")
            messagebox.showerror("Lỗi", f"Lỗi khi cập nhật chùm tia: {str(e)}")
    
    def setup_mlc(self):
        """Thiết lập MLC cho chùm tia"""
        if self.selected_beam_index is None:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một chùm tia để thiết lập MLC")
            return
        
        try:
            # Lấy chùm tia hiện tại
            beam = self.beams[self.selected_beam_index]
            
            # Mở cửa sổ thiết lập MLC
            from quangstation.clinical.planning.mlc_manager import MLCManager
            mlc_manager = MLCManager(beam)
            
            # Hiển thị giao diện thiết lập MLC
            mlc_window = tk.Toplevel(self.parent)
            mlc_window.title(f"Thiết lập MLC - {beam['name']}")
            mlc_window.geometry("800x600")
            
            # TODO: Hiển thị giao diện thiết lập MLC
            # Tính năng này sẽ được triển khai sau
            
            messagebox.showinfo("Thông báo", "Chức năng thiết lập MLC sẽ được triển khai trong phiên bản tiếp theo")
        except Exception as e:
            logger.error(f"Lỗi khi thiết lập MLC: {str(e)}")
            messagebox.showerror("Lỗi", f"Lỗi khi thiết lập MLC: {str(e)}")
    
    def show_beam_eye_view(self):
        """Hiển thị góc nhìn chùm tia (Beam's Eye View)"""
        if self.selected_beam_index is None:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một chùm tia để hiển thị BEV")
            return
        
        try:
            # Lấy chùm tia hiện tại
            beam = self.beams[self.selected_beam_index]
            
            # Mở cửa sổ BEV
            bev_window = tk.Toplevel(self.parent)
            bev_window.title(f"Beam's Eye View - {beam['name']}")
            bev_window.geometry("800x600")
            
            # TODO: Hiển thị Beam's Eye View
            # Tính năng này sẽ được triển khai sau
            
            messagebox.showinfo("Thông báo", "Chức năng hiển thị BEV sẽ được triển khai trong phiên bản tiếp theo")
        except Exception as e:
            logger.error(f"Lỗi khi hiển thị BEV: {str(e)}")
            messagebox.showerror("Lỗi", f"Lỗi khi hiển thị BEV: {str(e)}")
    
    def update_for_technique(self, technique_name: str):
        """Cập nhật giao diện cho kỹ thuật xạ trị cụ thể"""
        # Các thay đổi UI dựa trên kỹ thuật
        technique_map = {
            'Conventional3DCRT': self.update_for_3dcrt,
            'IMRT': self.update_for_imrt,
            'VMAT': self.update_for_vmat,
            'Stereotactic': self.update_for_stereotactic,
            'ProtonTherapy': self.update_for_proton,
            'AdaptiveRT': self.update_for_adaptive
        }
        
        # Gọi hàm cập nhật tương ứng
        if technique_name in technique_map:
            technique_map[technique_name]()
    
    def update_for_3dcrt(self):
        """Cập nhật giao diện cho kỹ thuật 3D-CRT"""
        # Các thay đổi UI cho 3D-CRT
        pass
    
    def update_for_imrt(self):
        """Cập nhật giao diện cho kỹ thuật IMRT"""
        # Các thay đổi UI cho IMRT
        pass
    
    def update_for_vmat(self):
        """Cập nhật giao diện cho kỹ thuật VMAT"""
        # Các thay đổi UI cho VMAT
        pass
    
    def update_for_stereotactic(self):
        """Cập nhật giao diện cho kỹ thuật Stereotactic"""
        # Các thay đổi UI cho Stereotactic
        pass
    
    def update_for_proton(self):
        """Cập nhật giao diện cho kỹ thuật Proton"""
        # Các thay đổi UI cho Proton
        pass
    
    def update_for_adaptive(self):
        """Cập nhật giao diện cho kỹ thuật Adaptive"""
        # Các thay đổi UI cho Adaptive
        pass 