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
    
        # Lấy dữ liệu volume mới từ database
        volume_data = self.db.get_volume(self.patient_id, 'CT')
        if volume_data is not None and len(volume_data) == 2:
            self.volume, self.metadata = volume_data
            # Reset current slice to middle of new volume
            self.current_slice = self.volume.shape[0] // 2
        else:
            # Xử lý trường hợp không tìm thấy dữ liệu volume
            print(f"Không tìm thấy dữ liệu CT cho bệnh nhân {patient_id}")
            self.volume = np.zeros((10, 10, 10), dtype=np.float32)  # Tạo volume rỗng
            self.metadata = None
            self.current_slice = 0
        
        # Cập nhật hiển thị 2D
        self.display_interface()
    
        # Cập nhật hiển thị 3D
        self.update_vtk_data()
    
        # Cập nhật text hiển thị thông tin
        if hasattr(self, 'text_actor'):
            self.text_actor.SetInput(f"Patient ID: {self.patient_id}")
        
        # Lấy và hiển thị dữ liệu RT Structure nếu có
        self.rt_structures = self.db.get_rt_struct(self.patient_id)
        if self.rt_structures:
            print(f"Đã tải {len(self.rt_structures)} cấu trúc RT")
            # Hiển thị contours trên các slice 2D
            self.display_rt_structures()
        else:
            print(f"Không tìm thấy dữ liệu RT Structure cho bệnh nhân {patient_id}")

    def update_vtk_data(self):
        """Cập nhật dữ liệu VTK khi đổi bệnh nhân"""
        if not hasattr(self, 'vtk_data') or not hasattr(self, 'volume_actor'):
            print("Chưa khởi tạo VTK renderer")
            return False
        
        # Lấy pixel spacing từ metadata nếu có
        pixel_spacing = [1.0, 1.0, 1.0]  # Mặc định
        if self.metadata and 'pixel_spacing' in self.metadata and self.metadata['pixel_spacing']:
            pixel_spacing[0] = self.metadata['pixel_spacing'][0]
            pixel_spacing[1] = self.metadata['pixel_spacing'][1]
        
        if self.metadata and 'slice_thickness' in self.metadata and self.metadata['slice_thickness']:
            pixel_spacing[2] = self.metadata['slice_thickness']
    
        # Cập nhật VTK image data
        self.vtk_data.SetDimensions(self.volume.shape[2], self.volume.shape[1], self.volume.shape[0])
        self.vtk_data.SetSpacing(pixel_spacing[0], pixel_spacing[1], pixel_spacing[2])
    
        # Chuyển đổi numpy array sang vtk array và gán cho image data
        flat_volume = self.volume.ravel(order='F')  # 'F' để phù hợp với thứ tự của VTK
        vtk_array = vtk.util.numpy_support.numpy_to_vtk(flat_volume, deep=True, array_type=vtk.VTK_FLOAT)
        self.vtk_data.GetPointData().SetScalars(vtk_array)
    
        # Cập nhật VTK renderer
        self.vtk_data.Modified()
        self.ren.ResetCamera()
        self.ren_win.Render()
    
        return True

    def add_rt_structure_to_vtk(self, structure_name):
        """Thêm hiển thị RT Structure vào VTK renderer"""
        if not self.rt_structures:
            print("Không có dữ liệu RT Structure")
            return False
        
        # Tìm structure theo tên
        structure = None
        for roi_number, struct in self.rt_structures.items():
            if struct.get('name', '') == structure_name:
                structure = struct
                break
            
        if structure is None:
            print(f"Không tìm thấy cấu trúc RT có tên {structure_name}")
            return False
        
        # Tạo VTK mesh từ contour data
        contour_data = structure.get('contour_data', [])
        if not contour_data:
            print(f"Cấu trúc {structure_name} không có dữ liệu contour")
            return False
        
        # Tạo vtkPoints để lưu các điểm
        points = vtk.vtkPoints()
        # Tạo vtkCellArray để lưu các đường contour
        polys = vtk.vtkCellArray()
    
        # Tạo một điểm tham chiếu cho mỗi contour
        contour_count = 0
    
        for contour in contour_data:
            point_data = contour.get('points', [])
            if len(point_data) < 3:  # Bỏ qua contour không đủ điểm
                continue
            
            # Thêm các điểm vào vtkPoints
            start_point_id = points.GetNumberOfPoints()
            for point in point_data:
                points.InsertNextPoint(point[0], point[1], point[2])
            
            # Tạo polygon từ các điểm
            polygon = vtk.vtkPolygon()
            polygon.GetPointIds().SetNumberOfIds(len(point_data))
            for i in range(len(point_data)):
                polygon.GetPointIds().SetId(i, start_point_id + i)
            
            # Thêm polygon vào cell array
            polys.InsertNextCell(polygon)
            contour_count += 1
    
        if contour_count == 0:
            print(f"Không tạo được mesh cho cấu trúc {structure_name}")
            return False
        
        # Tạo vtkPolyData
        polyData = vtk.vtkPolyData()
        polyData.SetPoints(points)
        polyData.SetPolys(polys)
    
        # Tạo normals
        normals = vtk.vtkPolyDataNormals()
        normals.SetInputData(polyData)
        normals.SetFeatureAngle(60.0)
        normals.SetConsistency(1)
        normals.SetSplitting(1)
    
        # Tạo mapper
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(normals.GetOutputPort())
    
        # Tạo actor
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
    
        # Đặt màu sắc
        color = structure.get('color', [1, 0, 0])  # Mặc định đỏ
        actor.GetProperty().SetColor(color[0], color[1], color[2])
        actor.GetProperty().SetOpacity(0.5)  # Đặt độ trong suốt
    
        # Thêm vào renderer
        self.ren.AddActor(actor)
        self.ren_win.Render()
    
        # Lưu actor để có thể xóa sau này
        if not hasattr(self, 'structure_actors'):
            self.structure_actors = {}
        self.structure_actors[structure_name] = actor
    
        return True

    def remove_rt_structure_from_vtk(self, structure_name):
        """Xóa hiển thị RT Structure khỏi VTK renderer"""
        if not hasattr(self, 'structure_actors') or structure_name not in self.structure_actors:
            print(f"Không tìm thấy cấu trúc {structure_name} trong renderer")
            return False
        
        # Xóa actor khỏi renderer
        self.ren.RemoveActor(self.structure_actors[structure_name])
        del self.structure_actors[structure_name]
        self.ren_win.Render()
    
        return True

    def toggle_rt_structure_visibility(self, structure_name, visible=True):
        """Bật/tắt hiển thị RT Structure trong VTK renderer"""
        if not hasattr(self, 'structure_actors') or structure_name not in self.structure_actors:
            if visible:
                # Nếu cần hiển thị nhưng chưa có actor, tạo mới
                return self.add_rt_structure_to_vtk(structure_name)
            return False
        
        # Thay đổi trạng thái hiển thị
        self.structure_actors[structure_name].SetVisibility(1 if visible else 0)
        self.ren_win.Render()
    
        return True

    def update_window_level(self, window, level):
        """Cập nhật window/level cho hiển thị"""
        # Lưu giá trị window/level
        self.window = window
        self.level = level
    
        # Cập nhật hiển thị 2D
        self.display_interface()
    
        # Cập nhật hiển thị 3D
        if hasattr(self, 'volume_actor'):
            # Lấy volume property
            volume_property = self.volume_actor.GetProperty()
        
            # Tính lại transfer function dựa trên window/level mới
            opacity_tf = vtk.vtkPiecewiseFunction()
            color_tf = vtk.vtkColorTransferFunction()
        
            # Tính giá trị min và max từ window/level
            min_value = level - window/2
            max_value = level + window/2
        
            # Thiết lập transfer function phù hợp với window/level
            opacity_tf.AddPoint(min_value, 0.0)
            opacity_tf.AddPoint(min_value + window*0.25, 0.2)
            opacity_tf.AddPoint(level, 0.5)
            opacity_tf.AddPoint(max_value - window*0.25, 0.8)
            opacity_tf.AddPoint(max_value, 1.0)
        
            color_tf.AddRGBPoint(min_value, 0.0, 0.0, 0.0)
            color_tf.AddRGBPoint(min_value + window*0.25, 0.5, 0.5, 0.5)
            color_tf.AddRGBPoint(level, 0.8, 0.8, 0.8)
            color_tf.AddRGBPoint(max_value - window*0.25, 0.9, 0.9, 0.9)
            color_tf.AddRGBPoint(max_value, 1.0, 1.0, 1.0)
        
            # Áp dụng transfer function mới
            volume_property.SetScalarOpacity(opacity_tf)
            volume_property.SetColor(color_tf)
        
            # Cập nhật renderer
            self.ren_win.Render()
    
        return True

    def display_dose_overlay(self, show_dose=True, opacity=0.5):
        """Hiển thị phủ liều (dose overlay) lên ảnh CT"""
        # Kiểm tra xem có dữ liệu liều không
        dose_data = self.db.get_rt_dose(self.patient_id)
        if dose_data is None:
            print("Không có dữ liệu liều RT Dose")
            return False
    
        if not hasattr(self, 'dose_actor'):
            # Chưa có actor hiển thị liều, tạo mới
            dose_volume, dose_metadata = dose_data
        
            # Tạo VTK data cho dữ liệu liều
            dose_vtk_data = vtk.vtkImageData()
            dose_vtk_data.SetDimensions(dose_volume.shape[2], dose_volume.shape[1], dose_volume.shape[0])
        
            # Lấy thông tin spacing từ metadata
            pixel_spacing = [1.0, 1.0, 1.0]  # Mặc định
            if dose_metadata and 'pixel_spacing' in dose_metadata and dose_metadata['pixel_spacing']:
                pixel_spacing[0] = dose_metadata['pixel_spacing'][0]
                pixel_spacing[1] = dose_metadata['pixel_spacing'][1]
            
            if dose_metadata and 'slice_thickness' in dose_metadata and dose_metadata['slice_thickness']:
                pixel_spacing[2] = dose_metadata['slice_thickness']
            
            dose_vtk_data.SetSpacing(pixel_spacing[0], pixel_spacing[1], pixel_spacing[2])
        
            # Chuyển đổi numpy array sang vtk array và gán cho image data
            flat_dose = dose_volume.ravel(order='F')
            vtk_array = vtk.util.numpy_support.numpy_to_vtk(flat_dose, deep=True, array_type=vtk.VTK_FLOAT)
            dose_vtk_data.GetPointData().SetScalars(vtk_array)
        
            # Tạo volume property cho liều
            dose_property = vtk.vtkVolumeProperty()
            dose_property.SetInterpolationTypeToLinear()
            dose_property.ShadeOff()
        
            # Tạo transfer function cho opacity và màu sắc
            opacity_tf = vtk.vtkPiecewiseFunction()
            opacity_tf.AddPoint(0.0, 0.0)     # Liều 0 không hiển thị
            opacity_tf.AddPoint(1.0, opacity)  # Áp dụng độ trong suốt theo đối số
            dose_property.SetScalarOpacity(opacity_tf)
        
            # Tạo color transfer function dạng cầu vồng
            color_tf = vtk.vtkColorTransferFunction()
            color_tf.AddRGBPoint(0.0, 0.0, 0.0, 1.0)   # Xanh dương cho liều thấp
            color_tf.AddRGBPoint(0.25, 0.0, 1.0, 1.0)  # Xanh lam
            color_tf.AddRGBPoint(0.5, 0.0, 1.0, 0.0)   # Xanh lá
            color_tf.AddRGBPoint(0.75, 1.0, 1.0, 0.0)  # Vàng
            color_tf.AddRGBPoint(1.0, 1.0, 0.0, 0.0)   # Đỏ cho liều cao
            dose_property.SetColor(color_tf)
        
            # Tạo volume mapper
            dose_mapper = vtk.vtkGPUVolumeRayCastMapper()
            dose_mapper.SetInputData