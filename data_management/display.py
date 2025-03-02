import vtk
import numpy as np
import tkinter as tk
from vtk.util.numpy_support import numpy_to_vtk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class Display:
    def __init__(self, root, patient_id, db):
        self.root = root
        self.patient_id = patient_id
        self.db = db
        
        # Lấy dữ liệu volume từ cơ sở dữ liệu
        volume_data = self.db.get_volume(self.patient_id, 'CT')
        if volume_data is not None and len(volume_data) == 2:
            self.volume, self.metadata = volume_data
        else:
            # Xử lý trường hợp không tìm thấy dữ liệu volume
            print(f"Không tìm thấy dữ liệu CT cho bệnh nhân {patient_id}")
            self.volume = np.zeros((10, 10, 10), dtype=np.float32)  # Tạo volume rỗng
            self.metadata = None
            
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

        # Hiển thị giao diện ban đầu
        self.display_interface()
        
        # Lấy và hiển thị dữ liệu RT Structure nếu có
        self.rt_structures = self.db.get_rt_struct(self.patient_id)
        if self.rt_structures:
            print(f"Đã tải {len(self.rt_structures)} cấu trúc RT")
            # Hiển thị contours trên các slice 2D
            self.display_rt_structures()

    def init_vtk(self):
        # Tạo render window
        self.vtk_widget = tk.Frame(self.vtk_frame, width=400, height=400)
        self.vtk_widget.pack(fill=tk.BOTH, expand=True)

        # Tạo renderer và render window
        self.ren = vtk.vtkRenderer()
        self.ren_win = vtk.vtkRenderWindow()
        self.ren_win.AddRenderer(self.ren)
        
        # Tạo render window interactor
        self.iren = vtk.vtkRenderWindowInteractor()
        self.iren.SetRenderWindow(self.ren_win)

        # Tạo interactor style
        style = vtk.vtkInteractorStyleTrackballCamera()
        self.iren.SetInteractorStyle(style)

        # Lấy pixel spacing từ metadata nếu có
        pixel_spacing = [1.0, 1.0, 1.0]  # Mặc định
        if self.metadata and 'pixel_spacing' in self.metadata and self.metadata['pixel_spacing']:
            pixel_spacing[0] = self.metadata['pixel_spacing'][0]
            pixel_spacing[1] = self.metadata['pixel_spacing'][1]
            
        if self.metadata and 'slice_thickness' in self.metadata and self.metadata['slice_thickness']:
            pixel_spacing[2] = self.metadata['slice_thickness']

        # Tạo pipeline VTK cho volume rendering
        self.vtk_data = vtk.vtkImageData()
        self.vtk_data.SetDimensions(self.volume.shape[2], self.volume.shape[1], self.volume.shape[0])
        self.vtk_data.SetSpacing(pixel_spacing[0], pixel_spacing[1], pixel_spacing[2])
        self.vtk_data.SetOrigin(0, 0, 0)
        
        # Chuyển đổi numpy array sang vtk array và gán cho image data
        flat_volume = self.volume.ravel(order='F')  # 'F' để phù hợp với thứ tự của VTK
        vtk_array = numpy_to_vtk(flat_volume, deep=True, array_type=vtk.VTK_FLOAT)
        self.vtk_data.GetPointData().SetScalars(vtk_array)

        # Tạo volume property
        volume_property = vtk.vtkVolumeProperty()
        volume_property.ShadeOn()
        volume_property.SetInterpolationTypeToLinear()

        # Tạo transfer function cho opacity và màu sắc
        opacity_tf = vtk.vtkPiecewiseFunction()
        opacity_tf.AddPoint(-1000, 0.0)   # Air
        opacity_tf.AddPoint(-400, 0.0)    # Lung
        opacity_tf.AddPoint(-100, 0.1)    # Fat
        opacity_tf.AddPoint(200, 0.4)     # Soft tissue
        opacity_tf.AddPoint(1000, 0.8)    # Bone
        volume_property.SetScalarOpacity(opacity_tf)

        color_tf = vtk.vtkColorTransferFunction()
        color_tf.AddRGBPoint(-1000, 0.0, 0.0, 0.0)  # Air
        color_tf.AddRGBPoint(-400, 0.6, 0.6, 0.9)   # Lung
        color_tf.AddRGBPoint(-100, 0.9, 0.8, 0.9)   # Fat
        color_tf.AddRGBPoint(200, 0.9, 0.7, 0.7)    # Soft tissue
        color_tf.AddRGBPoint(1000, 1.0, 1.0, 0.9)   # Bone
        volume_property.SetColor(color_tf)

        # Tạo volume mapper
        # Sử dụng GPU Volume Ray Cast Mapper cho hiệu suất tốt hơn
        volume_mapper = vtk.vtkGPUVolumeRayCastMapper()
        volume_mapper.SetInputData(self.vtk_data)

        # Tạo volume actor
        self.volume_actor = vtk.vtkVolume()
        self.volume_actor.SetMapper(volume_mapper)
        self.volume_actor.SetProperty(volume_property)

        # Thêm vào renderer
        self.ren.AddVolume(self.volume_actor)
        self.ren.ResetCamera()
        
        # Thêm text hiển thị thông tin
        self.text_actor = vtk.vtkTextActor()
        self.text_actor.SetInput(f"Patient ID: {self.patient_id}")
        self.text_actor.GetTextProperty().SetFontSize(14)
        self.text_actor.GetTextProperty().SetColor(1.0, 1.0, 1.0)
        self.text_actor.SetPosition(10, 10)
        self.ren.AddActor2D(self.text_actor)

        # Chỉnh màu background
        self.ren.SetBackground(0.1, 0.1, 0.2)
        
        # Bắt đầu interactor
        self.ren_win.SetSize(400, 400)
        self.ren_win.Render()
        
        # Tạo rendering window ở tk widget
        def vtk_widget_configure(event):
            self.ren_win.SetSize(event.width, event.height)
            
        self.vtk_widget.bind("<Configure>", vtk_widget_configure)
        
        # Nhúng VTK rendering window vào Tkinter frame
        self.ren_win.SetWindowInfo(str(int(self.vtk_widget.winfo_id())))
        self.iren.Initialize()
        self.ren_win.Render()
        
    def display_interface(self):
        # Hiển thị 2D
        self.fig_2d.clear()
        
        # Axial view
        ax1 = self.fig_2d.add_subplot(221)
        if self.volume.shape[0] > self.current_slice:
            axial_slice = self.volume[self.current_slice, :, :]
            ax1.imshow(axial_slice, cmap='gray', vmin=-100, vmax=300)
            ax1.set_title(f"Axial - Slice {self.current_slice}")
        else:
            ax1.set_title("Invalid Axial Slice")
        ax1.axis('off')

        # Coronal view
        ax2 = self.fig_2d.add_subplot(222)
        if self.volume.shape[1] > 0:
            mid_coronal = self.volume.shape[1] // 2
            coronal_slice = self.volume[:, mid_coronal, :]
            ax2.imshow(coronal_slice, cmap='gray', vmin=-100, vmax=300)
            ax2.set_title(f"Coronal - Slice {mid_coronal}")
        else:
            ax2.set_title("Invalid Coronal Slice")
        ax2.axis('off')

        # Sagittal view
        ax3 = self.fig_2d.add_subplot(223)
        if self.volume.shape[2] > 0:
            mid_sagittal = self.volume.shape[2] // 2
            sagittal_slice = self.volume[:, :, mid_sagittal]
            ax3.imshow(sagittal_slice, cmap='gray', vmin=-100, vmax=300)
            ax3.set_title(f"Sagittal - Slice {mid_sagittal}")
        else:
            ax3.set_title("Invalid Sagittal Slice")
        ax3.axis('off')
        
        # Histogram
        ax4 = self.fig_2d.add_subplot(224)
        flat_data = self.volume.flatten()
        ax4.hist(flat_data, bins=100, range=(-1000, 1000), color='blue', alpha=0.7)
        ax4.set_title("Histogram")
        ax4.set_xlabel("Hounsfield Units")
        ax4.set_ylabel("Frequency")

        self.fig_2d.tight_layout()
        self.canvas_2d.draw()
        
    def display_rt_structures(self):
        # Hiển thị contours RT Structure trên các slice 2D
        if not self.rt_structures:
            return
            
        # Refreshing the interface to draw contours
        self.display_interface()  # This redraws the base images
        
        # Get current axes from the figure
        axial_ax = self.fig_2d.axes[0]
        
        # Draw RT structures on axial slice
        for roi_number, structure in self.rt_structures.items():
            name = structure.get('name', f'Structure {roi_number}')
            color = structure.get('color', [1, 0, 0])  # Default to red if no color specified
            
            contour_data = structure.get('contour_data', [])
            for contour in contour_data:
                # Check if this contour belongs to the current slice
                points = contour.get('points', [])
                slice_z = contour.get('slice_z', 0)
                
                # Find closest slice in volume that matches the RT structure slice position
                # This depends on your coordinate system and may need adjustment
                if self.metadata and 'slices' in self.metadata:
                    current_z = self.metadata['slices'][self.current_slice].get('position', [0, 0, 0])[2]
                    slice_thickness = self.metadata.get('slice_thickness', 1.0)
                    
                    # Check if contour is within this slice (with some tolerance)
                    if abs(slice_z - current_z) <= slice_thickness/2:
                        # Convert 3D points to 2D pixel coordinates for this slice
                        if len(points) > 0:
                            x_points = []
                            y_points = []
                            
                            for point in points:
                                # This conversion depends on your DICOM coordinate system
                                # You may need to adjust this based on patient position and image orientation
                                x, y = self.convert_dicom_to_pixel(point[0], point[1])
                                x_points.append(x)
                                y_points.append(y)
                                
                            # Plot the contour
                            axial_ax.plot(x_points, y_points, color=color, linewidth=1.5)
        
        # Update the canvas
        self.canvas_2d.draw()
    
    def convert_dicom_to_pixel(self, x, y):
        """
        Convert DICOM physical coordinates to pixel coordinates
        This is a simplified conversion and may need refinement based on
        the DICOM coordinate system and image orientation
        """
        # Get pixel spacing from metadata
        pixel_spacing = [1.0, 1.0]  # Default
        if self.metadata and 'pixel_spacing' in self.metadata and self.metadata['pixel_spacing']:
            pixel_spacing = self.metadata['pixel_spacing']
            
        # Get image position (origin) from metadata
        origin = [0.0, 0.0, 0.0]  # Default
        if self.metadata and 'slices' in self.metadata and len(self.metadata['slices']) > 0:
            if 'position' in self.metadata['slices'][0] and self.metadata['slices'][0]['position']:
                origin = self.metadata['slices'][0]['position']
        
        # Simple conversion assuming standard orientation
        # This needs refinement based on your specific coordinate system
        pixel_x = int((x - origin[0]) / pixel_spacing[0])
        pixel_y = int((y - origin[1]) / pixel_spacing[1])
        
        # Ensure within image bounds
        pixel_x = max(0, min(pixel_x, self.volume.shape[2]-1))
        pixel_y = max(0, min(pixel_y, self.volume.shape[1]-1))
        
        return pixel_x, pixel_y

    def on_scroll(self, event):
        if event.button == 'up' and self.current_slice < self.volume.shape[0] - 1:
            self.current_slice += 1
        elif event.button == 'down' and self.current_slice > 0:
            self.current_slice -= 1
        
        self.display_interface()
        # Re-draw RT structures if they exist
        if self.rt_structures:
            self.display_rt_structures()
            
    def update_patient(self, patient_id):
        """Update display for a new patient"""
        self.patient_id = patient_id