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
        getattr(self, "structure_colors", {}) = {}  # Màu sắc cấu trúc
        self.beams = {}  # Chùm tia
        self.dose_data = None  # Dữ liệu liều
        self.image_data = None  # Dữ liệu hình ảnh
        getattr(self, "image_metadata", {}) = {}  # Metadata hình ảnh
        
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
        getattr(self, "structure_colors", {}) = colors or {}
        
        # Tạo màu mặc định cho các cấu trúc chưa có màu
        for name in structures:
            if name not in getattr(self, "structure_colors", {}):
                # Tạo màu ngẫu nhiên
                import random
                getattr(self, "structure_colors", {})[name] = (random.random(), random.random(), random.random())
        
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
            getattr(self, "image_metadata", {}) = metadata
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
        voxel_size = getattr(self, "image_metadata", {}).get('voxel_size', [1.0, 1.0, 1.0])
        
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
            color = getattr(self, "structure_colors", {}).get(name, (1.0, 0.0, 0.0))  # Mặc định là màu đỏ
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
        if not getattr(self, "beams", {}):
            logger.warning("Không có chùm tia để hiển thị")
            return
        
        # Xóa các actor chùm tia cũ
        for actor in self.beam_actors.values():
            self.renderer.RemoveActor(actor)
        self.beam_actors.clear()
        
        # Lấy tâm xoay (isocenter)
        isocenter = getattr(self, "image_metadata", {}).get('isocenter', [0, 0, 0])
        
        # Hiển thị từng chùm tia
        for beam_id, beam in getattr(self, "beams", {}).items():
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
        
        logger.info(f"Đã hiển thị {len(getattr(self, "beams", {}))} chùm tia")
    
    def show_dose(self):
        """Hiển thị phân bố liều."""
        if self.dose_data is None:
            logger.warning("Không có dữ liệu liều để hiển thị")
            return
        
        # Xóa các actor liều cũ
        for actor in self.dose_actors.values():
            self.renderer.RemoveActor(actor)
        self.dose_actors.clear()
        
        # Lấy kích thước voxel
        voxel_size = getattr(self, "image_metadata", {}).get('voxel_size', [1.0, 1.0, 1.0])
        
        # Lấy liều kê toa
        prescribed_dose = 50.0  # Giá trị mặc định
        
        # Tạo các isodose levels (ví dụ: 95%, 80%, 50% của liều kê toa)
        isodose_levels = [0.95, 0.8, 0.5]
        isodose_colors = [(1.0, 0.0, 0.0), (1.0, 0.5, 0.0), (1.0, 1.0, 0.0)]  # Đỏ, Cam, Vàng
        
        # Hiển thị từng mức liều
        for i, (level, color) in enumerate(zip(isodose_levels, isodose_colors)):
            # Tính giá trị ngưỡng
            threshold = level * prescribed_dose
            
            # Tạo mask cho mức liều này
            dose_mask = (self.dose_data >= threshold).astype(np.uint8)
            
            # Tạo isosurface từ mask
            surface = self._create_surface_from_mask(dose_mask, voxel_size)
            
            # Tạo mapper
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputData(surface)
            
            # Tạo actor
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            
            # Thiết lập màu sắc và độ trong suốt
            actor.GetProperty().SetColor(color)
            actor.GetProperty().SetOpacity(0.3)  # Độ trong suốt 70%
            
            # Thêm actor vào renderer
            self.renderer.AddActor(actor)
            self.dose_actors[f"isodose_{int(level*100)}"] = actor
        
        # Cập nhật hiển thị
        self.render_window.Render()
        
        logger.info(f"Đã hiển thị phân bố liều với {len(isodose_levels)} mức liều")
    
    def show_all(self):
        """Hiển thị tất cả: cấu trúc, chùm tia, và liều."""
        self.show_structures()
        self.show_beams()
        self.show_dose()
        
        # Đặt lại camera
        self.reset_camera()
    
    def hide_all(self):
        """Ẩn tất cả các actor."""
        # Xóa tất cả actor
        for actor in self.structure_actors.values():
            self.renderer.RemoveActor(actor)
        
        for actor in self.beam_actors.values():
            self.renderer.RemoveActor(actor)
        
        for actor in self.dose_actors.values():
            self.renderer.RemoveActor(actor)
        
        # Xóa các dictionary
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
        """Chụp ảnh màn hình hiện tại."""
        # Tạo window to image filter
        window_to_image = vtk.vtkWindowToImageFilter()
        window_to_image.SetInput(self.render_window)
        window_to_image.SetInputBufferTypeToRGB()
        window_to_image.ReadFrontBufferOff()
        window_to_image.Update()
        
        # Tạo writer
        writer = vtk.vtkPNGWriter()
        
        # Mở hộp thoại lưu file
        from tkinter import filedialog
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")],
            title="Lưu ảnh 3D"
        )
        
        if file_path:
            writer.SetFileName(file_path)
            writer.SetInputConnection(window_to_image.GetOutputPort())
            writer.Write()
            logger.info(f"Đã lưu ảnh 3D tại: {file_path}")
    
    def _create_surface_from_mask(self, mask: np.ndarray, voxel_size: List[float]) -> vtk.vtkPolyData:
        """
        Tạo bề mặt (surface) từ mask 3D.
        
        Args:
            mask: Mảng 3D mask
            voxel_size: Kích thước voxel [dx, dy, dz]
            
        Returns:
            vtkPolyData: Bề mặt đã tạo
        """
        # Chuyển đổi mask thành vtkImageData
        vtk_image = vtk.vtkImageData()
        vtk_image.SetDimensions(mask.shape[2], mask.shape[1], mask.shape[0])
        vtk_image.SetSpacing(voxel_size)
        vtk_image.SetOrigin(0, 0, 0)
        
        # Chuyển đổi numpy array thành vtk array
        flat_mask = mask.ravel(order='F').astype(np.uint8)
        vtk_array = numpy_support.numpy_to_vtk(flat_mask)
        vtk_array.SetName("mask")
        
        # Gán dữ liệu cho vtkImageData
        vtk_image.GetPointData().SetScalars(vtk_array)
        
        # Tạo isosurface bằng marching cubes
        marching_cubes = vtk.vtkMarchingCubes()
        marching_cubes.SetInputData(vtk_image)
        marching_cubes.SetValue(0, 0.5)  # Ngưỡng
        marching_cubes.Update()
        
        # Làm mịn bề mặt
        smoother = vtk.vtkSmoothPolyDataFilter()
        smoother.SetInputConnection(marching_cubes.GetOutputPort())
        smoother.SetNumberOfIterations(15)
        smoother.SetRelaxationFactor(0.1)
        smoother.Update()
        
        # Giảm số lượng tam giác
        decimator = vtk.vtkDecimatePro()
        decimator.SetInputConnection(smoother.GetOutputPort())
        decimator.SetTargetReduction(0.5)  # Giảm 50% số tam giác
        decimator.PreserveTopologyOn()
        decimator.Update()
        
        # Tính toán normal vectors
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
            vtkActor: Actor biểu diễn chùm tia
        """
        # Tạo hình nón
        cone = vtk.vtkConeSource()
        cone.SetHeight(300)  # Chiều dài chùm tia
        cone.SetRadius(0)  # Bán kính tại đỉnh
        cone.SetRadius2(60)  # Bán kính tại đáy
        cone.SetResolution(20)  # Số lượng mặt
        cone.SetDirection(0, 0, -1)  # Hướng mặc định (dọc trục Z)
        cone.Update()
        
        # Tạo mapper
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(cone.GetOutputPort())
        
        # Tạo actor
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        
        # Thiết lập màu sắc và độ trong suốt
        actor.GetProperty().SetColor(1.0, 0.0, 0.0)  # Màu đỏ
        actor.GetProperty().SetOpacity(0.3)  # Độ trong suốt 70%
        
        # Đặt vị trí tại isocenter
        actor.SetPosition(isocenter)
        
        # Xoay theo góc gantry và couch
        import math
        gantry_rad = math.radians(gantry_angle)
        couch_rad = math.radians(couch_angle)
        
        # Xoay quanh trục Y (góc gantry)
        actor.RotateY(gantry_angle)
        
        # Xoay quanh trục Z (góc couch)
        actor.RotateZ(couch_angle)
        
        return actor 