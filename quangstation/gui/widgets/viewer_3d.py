#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Widget hiển thị 3D cho QuangStation V2 sử dụng VTK.
"""

import tkinter as tk
from tkinter import ttk
import numpy as np
import vtk
from vtk.util import numpy_support
from vtk.tk.vtkTkRenderWindowInteractor import vtkTkRenderWindowInteractor
from typing import Dict, List, Tuple, Optional, Any, Callable

from quangstation.utils.logging import get_logger

logger = get_logger(__name__)

class Viewer3D(ttk.Frame):
    """
    Widget hiển thị 3D sử dụng VTK.
    Hỗ trợ hiển thị cấu trúc, chùm tia, và phân bố liều trong không gian 3D.
    """
    
    def __init__(self, parent, **kwargs):
        """
        Khởi tạo widget hiển thị 3D.
        
        Args:
            parent: Widget cha
            **kwargs: Các tham số bổ sung cho Frame
        """
        super().__init__(parent, **kwargs)
        
        # Khởi tạo các biến
        self.structures = {}  # Cấu trúc
        self.structure_colors = {}  # Màu sắc cấu trúc
        self.beams = {}  # Chùm tia
        self.dose_data = None  # Dữ liệu liều
        self.image_data = None  # Dữ liệu hình ảnh
        self.image_metadata = {}  # Metadata hình ảnh
        self.dose_metadata = {}  # Metadata liều
        
        # Khởi tạo các thành phần VTK
        self.renderer = vtk.vtkRenderer()
        self.renderer.SetBackground(0.1, 0.1, 0.1)  # Nền tối
        
        # Tạo render window
        self.render_window = vtk.vtkRenderWindow()
        self.render_window.AddRenderer(self.renderer)
        
        # Tạo frame chứa render window
        self.frame = ttk.Frame(self)
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        # Tạo VTK render window interactor
        self.interactor = vtkTkRenderWindowInteractor(self.frame, rw=self.render_window)
        self.interactor.pack(fill=tk.BOTH, expand=True)
        
        # Thiết lập style cho interactor
        self.interactor_style = vtk.vtkInteractorStyleTrackballCamera()
        self.interactor.SetInteractorStyle(self.interactor_style)
        
        # Khởi tạo interactor
        self.interactor.Initialize()
        
        # Tạo thanh công cụ
        self.create_toolbar()
        
        # Tạo các actor
        self.structure_actors = {}
        self.beam_actors = {}
        self.dose_actors = {}
        self.axes_actor = None
        
        # Thêm trục tọa độ
        self.add_coordinate_axes()
        
        # Thiết lập camera
        self.reset_camera()
        
        logger.info("Đã khởi tạo widget hiển thị 3D")
    
    def create_toolbar(self):
        """Tạo thanh công cụ."""
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        # Nút hiển thị cấu trúc
        ttk.Button(toolbar, text="Hiển thị cấu trúc", command=self.show_structures).pack(side=tk.LEFT, padx=2)
        
        # Nút hiển thị chùm tia
        ttk.Button(toolbar, text="Hiển thị chùm tia", command=self.show_beams).pack(side=tk.LEFT, padx=2)
        
        # Nút hiển thị liều
        ttk.Button(toolbar, text="Hiển thị liều", command=self.show_dose).pack(side=tk.LEFT, padx=2)
        
        # Nút hiển thị tất cả
        ttk.Button(toolbar, text="Hiển thị tất cả", command=self.show_all).pack(side=tk.LEFT, padx=2)
        
        # Nút ẩn tất cả
        ttk.Button(toolbar, text="Ẩn tất cả", command=self.hide_all).pack(side=tk.LEFT, padx=2)
        
        # Nút đặt lại camera
        ttk.Button(toolbar, text="Đặt lại camera", command=self.reset_camera).pack(side=tk.LEFT, padx=2)
        
        # Nút chụp ảnh
        ttk.Button(toolbar, text="Chụp ảnh", command=self.take_screenshot).pack(side=tk.LEFT, padx=2)
    
    def add_coordinate_axes(self):
        """Thêm trục tọa độ vào scene."""
        axes = vtk.vtkAxesActor()
        axes.SetTotalLength(50, 50, 50)  # Độ dài trục
        axes.SetShaftType(0)  # Trục dạng trụ
        axes.SetAxisLabels(1)  # Hiển thị nhãn trục
        
        # Thiết lập vị trí và kích thước của widget
        axes_widget = vtk.vtkOrientationMarkerWidget()
        axes_widget.SetOrientationMarker(axes)
        axes_widget.SetInteractor(self.interactor)
        axes_widget.SetViewport(0.0, 0.0, 0.2, 0.2)  # Vị trí góc dưới bên trái
        axes_widget.EnabledOn()
        axes_widget.InteractiveOff()
        
        self.axes_actor = axes
        self.axes_widget = axes_widget
    
    def set_structures(self, structures: Dict[str, np.ndarray], colors: Dict[str, Tuple[float, float, float]] = None):
        """
        Thiết lập dữ liệu cấu trúc.
        
        Args:
            structures: Dictionary chứa mask của các cấu trúc
            colors: Dictionary chứa màu sắc của các cấu trúc
        """
        self.structures = structures
        if colors:
            self.structure_colors = colors
        
        # Tạo màu mặc định cho các cấu trúc chưa có màu
        for name in structures:
            if name not in self.structure_colors:
                # Tạo màu ngẫu nhiên
                import random
                self.structure_colors[name] = (random.random(), random.random(), random.random())
        
        logger.info(f"Đã thiết lập {len(structures)} cấu trúc cho hiển thị 3D")
    
    def set_beams(self, beams: Dict[str, Dict]):
        """
        Thiết lập dữ liệu chùm tia.
        
        Args:
            beams: Dictionary chứa thông tin các chùm tia
        """
        self.beams = beams
        logger.info(f"Đã thiết lập {len(beams)} chùm tia cho hiển thị 3D")
    
    def set_dose_data(self, dose_data: np.ndarray, metadata: Dict = None):
        """
        Thiết lập dữ liệu liều.
        
        Args:
            dose_data: Mảng 3D chứa dữ liệu liều
            metadata: Metadata của dữ liệu liều
        """
        self.dose_data = dose_data
        if metadata:
            self.dose_metadata = metadata
        logger.info(f"Đã thiết lập dữ liệu liều cho hiển thị 3D")
    
    def set_image_data(self, image_data: np.ndarray, metadata: Dict = None):
        """
        Thiết lập dữ liệu hình ảnh.
        
        Args:
            image_data: Mảng 3D chứa dữ liệu hình ảnh
            metadata: Metadata của dữ liệu hình ảnh
        """
        self.image_data = image_data
        if metadata:
            self.image_metadata = metadata
        logger.info(f"Đã thiết lập dữ liệu hình ảnh cho hiển thị 3D")
    
    def show_structures(self):
        """Hiển thị các cấu trúc."""
        if not self.structures:
            logger.warning("Không có cấu trúc để hiển thị")
            return
        
        # Xóa các actor cấu trúc cũ
        for actor in self.structure_actors.values():
            self.renderer.RemoveActor(actor)
        self.structure_actors.clear()
        
        # Lấy kích thước voxel
        voxel_size = self.image_metadata.get('voxel_size', [1.0, 1.0, 1.0])
        
        # Hiển thị từng cấu trúc
        for name, mask in self.structures.items():
            # Tạo isosurface từ mask
            surface = self._create_surface_from_mask(mask, voxel_size)
            
            # Tạo mapper
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputData(surface)
            
            # Tạo actor
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            
            # Thiết lập màu sắc và độ trong suốt
            color = self.structure_colors.get(name, (1.0, 0.0, 0.0))  # Mặc định là màu đỏ
            actor.GetProperty().SetColor(color)
            actor.GetProperty().SetOpacity(0.5)  # Độ trong suốt 50%
            
            # Thêm actor vào renderer
            self.renderer.AddActor(actor)
            self.structure_actors[name] = actor
        
        # Cập nhật hiển thị
        self.render_window.Render()
        
        logger.info(f"Đã hiển thị {len(self.structures)} cấu trúc")
    
    def show_beams(self):
        """Hiển thị các chùm tia."""
        if not self.beams:
            logger.warning("Không có chùm tia để hiển thị")
            return
        
        # Xóa các actor chùm tia cũ
        for actor in self.beam_actors.values():
            self.renderer.RemoveActor(actor)
        self.beam_actors.clear()
        
        # Lấy tâm xoay (isocenter)
        isocenter = self.image_metadata.get('isocenter', [0, 0, 0])
        
        # Hiển thị từng chùm tia
        for beam_id, beam in self.beams.items():
            # Lấy thông tin chùm tia
            gantry_angle = beam.get('gantry_angle', 0)
            collimator_angle = beam.get('collimator_angle', 0)
            couch_angle = beam.get('couch_angle', 0)
            
            # Tạo hình nón biểu diễn chùm tia
            beam_actor = self._create_beam_actor(isocenter, gantry_angle, couch_angle)
            
            # Thêm actor vào renderer
            self.renderer.AddActor(beam_actor)
            self.beam_actors[beam_id] = beam_actor
        
        # Cập nhật hiển thị
        self.render_window.Render()
        
        logger.info(f"Đã hiển thị {len(self.beams)} chùm tia")
    
    def show_dose(self):
        """Hiển thị liều."""
        if self.dose_data is None:
            logger.warning("Không có dữ liệu liều để hiển thị")
            return
        
        # Xóa các actor liều cũ
        for actor in self.dose_actors.values():
            self.renderer.RemoveActor(actor)
        self.dose_actors.clear()
        
        # Lấy kích thước voxel
        voxel_size = self.dose_metadata.get('voxel_size', [1.0, 1.0, 1.0])
        
        # Tạo volume rendering cho dữ liệu liều
        # Chuyển đổi dữ liệu liều thành VTK image data
        vtk_data = numpy_support.numpy_to_vtk(self.dose_data.flatten(), deep=True, array_type=vtk.VTK_FLOAT)
        image_data = vtk.vtkImageData()
        image_data.SetDimensions(self.dose_data.shape[2], self.dose_data.shape[1], self.dose_data.shape[0])
        image_data.SetSpacing(voxel_size)
        image_data.SetOrigin(0, 0, 0)
        image_data.GetPointData().SetScalars(vtk_data)
        
        # Tạo các isosurface cho các mức liều
        dose_levels = [10, 20, 30, 50, 70, 90, 95]  # Các mức liều (% của liều max)
        dose_max = np.max(self.dose_data)
        
        for level_idx, level_percent in enumerate(dose_levels):
            level_value = dose_max * level_percent / 100.0
            
            # Tạo isosurface
            contour = vtk.vtkMarchingCubes()
            contour.SetInputData(image_data)
            contour.SetValue(0, level_value)
            contour.Update()
            
            # Tạo mapper
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(contour.GetOutputPort())
            mapper.ScalarVisibilityOff()
            
            # Tạo actor
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            
            # Thiết lập màu sắc và độ trong suốt
            # Gradient màu từ xanh đến đỏ theo mức liều
            r = level_percent / 100.0
            g = 1.0 - level_percent / 100.0
            b = 0.0
            
            actor.GetProperty().SetColor(r, g, b)
            actor.GetProperty().SetOpacity(0.2)  # Độ trong suốt cao
            
            # Thêm actor vào renderer
            self.renderer.AddActor(actor)
            self.dose_actors[f"dose_{level_percent}"] = actor
        
        # Cập nhật hiển thị
        self.render_window.Render()
        
        logger.info("Đã hiển thị phân bố liều")
    
    def show_all(self):
        """Hiển thị tất cả: cấu trúc, chùm tia và liều."""
        self.show_structures()
        self.show_beams()
        self.show_dose()
    
    def hide_all(self):
        """Ẩn tất cả các actor."""
        # Xóa tất cả actor khỏi renderer
        self.renderer.RemoveAllViewProps()
        
        # Thêm lại actor trục tọa độ
        if self.axes_actor:
            self.renderer.AddActor(self.axes_actor)
        
        # Xóa các tham chiếu đến actor
        self.structure_actors.clear()
        self.beam_actors.clear()
        self.dose_actors.clear()
        
        # Cập nhật hiển thị
        self.render_window.Render()
        
        logger.info("Đã ẩn tất cả các đối tượng")
    
    def reset_camera(self):
        """Đặt lại camera về vị trí mặc định."""
        self.renderer.ResetCamera()
        self.render_window.Render()
    
    def take_screenshot(self):
        """Chụp ảnh hiện tại và lưu vào file."""
        from tkinter import filedialog
        import os
        
        # Hiển thị hộp thoại lưu file
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPG files", "*.jpg"), ("All files", "*.*")],
            title="Lưu ảnh 3D"
        )
        
        if not file_path:
            return
        
        # Lấy pixel từ render window
        window_to_image = vtk.vtkWindowToImageFilter()
        window_to_image.SetInput(self.render_window)
        window_to_image.SetInputBufferTypeToRGB()
        window_to_image.ReadFrontBufferOff()
        window_to_image.Update()
        
        # Xác định định dạng lưu file
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == ".jpg" or file_extension == ".jpeg":
            writer = vtk.vtkJPEGWriter()
        else:
            writer = vtk.vtkPNGWriter()
        
        writer.SetFileName(file_path)
        writer.SetInputConnection(window_to_image.GetOutputPort())
        writer.Write()
        
        logger.info(f"Đã lưu ảnh 3D vào {file_path}")
    
    def _create_surface_from_mask(self, mask: np.ndarray, voxel_size: List[float]) -> vtk.vtkPolyData:
        """
        Tạo surface (bề mặt) từ mask 3D.
        
        Args:
            mask: Mảng 3D chứa mask (0 hoặc 1)
            voxel_size: Kích thước voxel [dx, dy, dz]
        
        Returns:
            vtk.vtkPolyData: Đối tượng surface
        """
        # Chuyển đổi mask thành VTK image data
        vtk_data = numpy_support.numpy_to_vtk(mask.flatten(), deep=True, array_type=vtk.VTK_UNSIGNED_CHAR)
        image_data = vtk.vtkImageData()
        image_data.SetDimensions(mask.shape[2], mask.shape[1], mask.shape[0])
        image_data.SetSpacing(voxel_size)
        image_data.SetOrigin(0, 0, 0)
        image_data.GetPointData().SetScalars(vtk_data)
        
        # Tạo surface từ mask bằng Marching Cubes
        contour = vtk.vtkMarchingCubes()
        contour.SetInputData(image_data)
        contour.SetValue(0, 0.5)  # Giá trị ngưỡng
        contour.Update()
        
        # Làm mịn surface
        smoother = vtk.vtkSmoothPolyDataFilter()
        smoother.SetInputConnection(contour.GetOutputPort())
        smoother.SetNumberOfIterations(15)
        smoother.SetRelaxationFactor(0.1)
        smoother.Update()
        
        # Giảm số lượng tam giác
        decimator = vtk.vtkDecimatePro()
        decimator.SetInputConnection(smoother.GetOutputPort())
        decimator.SetTargetReduction(0.1)  # Giảm 10% số tam giác
        decimator.PreserveTopologyOn()
        decimator.Update()
        
        # Tính pháp tuyến bề mặt cho hiển thị đẹp hơn
        normals = vtk.vtkPolyDataNormals()
        normals.SetInputConnection(decimator.GetOutputPort())
        normals.SetFeatureAngle(60.0)
        normals.Update()
        
        return normals.GetOutput()
    
    def _create_beam_actor(self, isocenter: List[float], gantry_angle: float, couch_angle: float) -> vtk.vtkActor:
        """
        Tạo actor biểu diễn chùm tia.
        
        Args:
            isocenter: Tọa độ tâm xoay [x, y, z]
            gantry_angle: Góc gantry (độ)
            couch_angle: Góc bàn (độ)
            
        Returns:
            vtk.vtkActor: Actor biểu diễn chùm tia
        """
        # Tạo hình nón biểu diễn chùm tia
        cone = vtk.vtkConeSource()
        cone.SetHeight(400)  # Chiều dài chùm tia
        cone.SetAngle(10)    # Góc mở của chùm tia
        cone.SetResolution(20)  # Độ chi tiết
        cone.SetDirection(0, 0, -1)  # Hướng: theo trục Z âm
        cone.Update()
        
        # Tạo mapper
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(cone.GetOutputPort())
        
        # Tạo actor
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        
        # Thiết lập màu sắc và độ trong suốt
        actor.GetProperty().SetColor(1.0, 1.0, 0.0)  # Màu vàng
        actor.GetProperty().SetOpacity(0.3)          # Độ trong suốt
        
        # Áp dụng các phép biến đổi
        # 1. Đặt actor tại tâm xoay
        actor.SetPosition(isocenter)
        
        # 2. Xoay theo góc gantry
        transform = vtk.vtkTransform()
        transform.RotateY(gantry_angle)
        
        # 3. Xoay theo góc bàn
        transform.RotateZ(couch_angle)
        
        # Áp dụng biến đổi
        actor.SetUserTransform(transform)
        
        return actor 