import vtk
import numpy as np
import tkinter as tk
from vtk.util.numpy_support import vtk_to_numpy

class Display:
    def __init__(self, root, patient_id, db):
        self.root = root
        self.patient_id = patient_id
        self.db = db
        self.volume = self.db.get_volume(self.patient_id, 'CT')
        self.current_slice = self.volume.shape[0] // 2

        # Tạo giao diện Tkinter
        self.fig_frame = tk.Frame(self.root)
        self.fig_frame.pack(fill=tk.BOTH, expand=True)

        # Hiển thị 2D bằng matplotlib
        self.fig_2d = plt.Figure(figsize=(9, 6))
        self.canvas_2d = FigureCanvasTkAgg(self.fig_2d, master=self.fig_frame)
        self.canvas_2d.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas_2d.mpl_connect('scroll_event', self.on_scroll)

        # Hiển thị 3D bằng VTK
        self.vtk_frame = tk.Frame(self.root)
        self.vtk_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.init_vtk()

        self.display_interface()

    def init_vtk(self):
        # Tạo render window
        self.vtk_widget = tk.Frame(self.vtk_frame, width=400, height=400)
        self.vtk_widget.pack(fill=tk.BOTH, expand=True)

        # Tạo renderer và render window
        self.ren = vtk.vtkRenderer()
        self.ren_win = vtk.vtkRenderWindow()
        self.ren_win.AddRenderer(self.ren)
        self.iren = vtk.vtkRenderWindowInteractor()
        self.iren.SetRenderWindow(self.ren_win)

        # Tạo interactor style
        style = vtk.vtkInteractorStyleTrackballCamera()
        self.iren.SetInteractorStyle(style)

        # Tạo pipeline VTK cho volume rendering
        self.vtk_data = vtk.vtkImageData()
        self.vtk_data.SetDimensions(self.volume.shape[2], self.volume.shape[1], self.volume.shape[0])
        vtk_array = vtk.util.numpy_support.numpy_to_vtk(self.volume.ravel(), deep=True, array_type=vtk.VTK_FLOAT)
        self.vtk_data.SetSpacing(1.0, 1.0, 1.0)  # Có thể lấy từ DICOM spacing
        self.vtk_data.SetOrigin(0, 0, 0)
        self.vtk_data.GetPointData().SetScalars(vtk_array)

        # Tạo volume property
        volume_property = vtk.vtkVolumeProperty()
        volume_property.ShadeOn()
        volume_property.SetInterpolationTypeToLinear()

        # Tạo transfer function cho opacity và màu sắc
        opacity_tf = vtk.vtkPiecewiseFunction()
        opacity_tf.AddPoint(0, 0.0)
        opacity_tf.AddPoint(100, 0.1)
        opacity_tf.AddPoint(255, 0.8)
        volume_property.SetScalarOpacity(opacity_tf)

        color_tf = vtk.vtkColorTransferFunction()
        color_tf.AddRGBPoint(0, 0.0, 0.0, 0.0)  # Màu đen cho giá trị thấp
        color_tf.AddRGBPoint(100, 0.5, 0.5, 0.5)  # Màu xám
        color_tf.AddRGBPoint(255, 1.0, 1.0, 1.0)  # Màu trắng
        volume_property.SetColor(color_tf)

        # Tạo volume mapper
        volume_mapper = vtk.vtkVolumeRayCastMapper()
        volume_mapper.SetInputData(self.vtk_data)

        # Tạo volume actor
        self.volume_actor = vtk.vtkVolume()
        self.volume_actor.SetMapper(volume_mapper)
        self.volume_actor.SetProperty(volume_property)

        # Thêm vào renderer
        self.ren.AddVolume(self.volume_actor)
        self.ren.ResetCamera()

        # Bắt đầu interactor
        self.iren.Initialize()
        self.ren_win.Render()
        self.iren.Start()

    def display_interface(self):
        # Hiển thị 2D
        ax1 = self.fig_2d.add_subplot(221)
        ax1.clear()
        ax1.imshow(self.volume[self.current_slice, :, :], cmap='gray')
        ax1.set_title(f"Axial - Slice {self.current_slice}")
        ax1.axis('off')

        ax2 = self.fig_2d.add_subplot(222)
        ax2.clear()
        mid_coronal = self.volume.shape[1] // 2
        ax2.imshow(self.volume[:, mid_coronal, :], cmap='gray')
        ax2.set_title("Coronal")
        ax2.axis('off')

        ax3 = self.fig_2d.add_subplot(223)
        ax3.clear()
        mid_sagittal = self.volume.shape[2] // 2
        ax3.imshow(self.volume[:, :, mid_sagittal], cmap='gray')
        ax3.set_title("Sagittal")
        ax3.axis('off')

        self.fig_2d.tight_layout()
        self.canvas_2d.draw()

    def on_scroll(self, event):
        if event.button == 'up' and self.current_slice < self.volume.shape[0] - 1:
            self.current_slice += 1
        elif event.button == 'down' and self.current_slice > 0:
            self.current_slice -= 1
        self.display_interface()