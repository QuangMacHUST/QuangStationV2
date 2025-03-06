import numpy as np
import os
import sys
import tkinter as tk
from tkinter import messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tempfile

# Tự động cài đặt các thư viện nếu chưa có
try:
    import vtk
    from vtk.util.numpy_support import numpy_to_vtk
except ImportError:
    print("Thư viện VTK chưa được cài đặt. Đang cài đặt...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "vtk"])
    import vtk
    from vtk.util.numpy_support import numpy_to_vtk

try:
    import cv2
except ImportError:
    print("Thư viện OpenCV chưa được cài đặt. Đang cài đặt...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "opencv-python"])
    import cv2

try:
    from scipy.ndimage import zoom
except ImportError:
    print("Thư viện SciPy chưa được cài đặt. Đang cài đặt...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "scipy"])
    from scipy.ndimage import zoom

# Import image_loader từ module image_processing
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from image_processing.image_loader import ImageLoader
from contouring.contour_tools import ContourTools

class Display:
    def __init__(self, root, patient_id, db):
        """Khởi tạo giao diện hiển thị"""
        self.root = root
        self.patient_id = patient_id
        self.db = db
        self.volume = None
        self.ct_volume = None
        self.rt_structures = None
        self.rt_dose = None
        self.metadata = None
        self.current_slice = 0
        self.show_dose = False
        self.show_dose_on_slice = False
        self.dose_opacity = 0.5
        self.dose_colormap = 'jet'
        self.contour_tools = None
        self.active_tool = None
        self.measurement_points = []
        self.slice_positions = []
        self.measurement_mode = None
        self.canvas = None
        self.rt_structs = {}
        
        # Biến để lưu trữ dữ liệu RT Image
        self.rt_image = None
        self.rt_image_metadata = None
        
        # Thiết lập giao diện
        self.setup_ui()
        
        # Tải dữ liệu bệnh nhân
        self.update_patient(patient_id)
    
    def setup_ui(self):
        """Thiết lập giao diện người dùng"""
        # Tạo frame chính
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tạo frame cho hiển thị 2D
        self.frame_2d = tk.Frame(self.main_frame)
        self.frame_2d.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Tạo hình ảnh 2D với matplotlib
        self.fig_2d = plt.figure(figsize=(8, 8))
        self.canvas_2d = FigureCanvasTkAgg(self.fig_2d, self.frame_2d)
        self.canvas_2d.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Thiết lập canvas từ matplotlib cho các phép đo
        self.canvas = self.canvas_2d.get_tk_widget()
        
        # Tạo frame cho hiển thị 3D
        self.frame_3d = tk.Frame(self.main_frame)
        self.frame_3d.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Tạo VTK widget cho hiển thị 3D
        self.vtk_widget = tk.Frame(self.frame_3d, width=400, height=400)
        self.vtk_widget.pack(fill=tk.BOTH, expand=True)
        
        # Tạo frame điều khiển
        self.control_frame = tk.Frame(self.root)
        self.control_frame.pack(fill=tk.X)
        
        # Tạo các nút điều khiển
        self.create_control_buttons()
        
        # Liên kết sự kiện
        self.bind_events()
    
    def init_vtk(self):
        """Khởi tạo môi trường VTK"""
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
        
        # Kiểm tra xem volume có tồn tại không trước khi tiến hành
        if self.volume is None or len(self.volume) == 0:
            return
        
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
        opacity_tf.AddPoint(200, 0.2)     # Soft tissue
        opacity_tf.AddPoint(1000, 0.4)    # Bone
        volume_property.SetScalarOpacity(opacity_tf)
        
        color_tf = vtk.vtkColorTransferFunction()
        color_tf.AddRGBPoint(-1000, 0.0, 0.0, 0.0)  # Air
        color_tf.AddRGBPoint(-400, 0.6, 0.6, 0.9)   # Lung
        color_tf.AddRGBPoint(-100, 0.9, 0.8, 0.9)   # Fat
        color_tf.AddRGBPoint(200, 1.0, 0.8, 0.7)    # Soft tissue
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
        self.ren.AddViewProp(self.volume_actor)
        
        # Thêm text hiển thị thông tin
        self.text_actor = vtk.vtkTextActor()
        self.text_actor.SetInput(f"Patient ID: {self.patient_id}")
        self.text_actor.GetTextProperty().SetFontSize(14)
        self.text_actor.GetTextProperty().SetColor(1.0, 1.0, 1.0)
        self.text_actor.SetPosition(10, 10)
        self.ren.AddActor2D(self.text_actor)
        
        # Reset camera
        self.ren.ResetCamera()
        
        # Hiển thị rendering
        self.ren_win.Render()
        
        # Kết nối với widget Tkinter
        def vtk_widget_configure(event):
            self.ren_win.SetSize(event.width, event.height)
        
        self.vtk_widget.bind("<Configure>", vtk_widget_configure)
        
        # Khởi tạo interactor
        self.iren.Initialize()
        self.iren.Start()
    
    def create_control_buttons(self):
        """Tạo các nút điều khiển"""
        # Nút hiển thị/ẩn liều
        self.dose_button = tk.Button(
            self.control_frame, 
            text="Hiển thị liều", 
            command=lambda: self.display_dose_overlay(not self.show_dose)
        )
        self.dose_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Nút hiển thị RT Structures
        self.structures_button = tk.Button(
            self.control_frame, 
            text="Hiển thị cấu trúc", 
            command=self.display_rt_structures
        )
        self.structures_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Nút công cụ đo
        self.measurement_button = tk.Button(
            self.control_frame, 
            text="Công cụ đo", 
            command=self.add_measurement_tools
        )
        self.measurement_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Nút chụp màn hình
        self.screenshot_button = tk.Button(
            self.control_frame, 
            text="Chụp màn hình", 
            command=lambda: self.create_screenshot("screenshot.png")
        )
        self.screenshot_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Thanh trượt slice
        self.slice_label = tk.Label(self.control_frame, text="Slice:")
        self.slice_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.slice_scale = tk.Scale(
            self.control_frame, 
            from_=0, 
            to=100, 
            orient=tk.HORIZONTAL,
            command=self.on_slice_change
        )
        self.slice_scale.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        
    def on_slice_change(self, event):
        """Xử lý sự kiện thay đổi slice"""
        if self.volume is not None and len(self.volume) > 0:
            self.current_slice = int(self.slice_scale.get())
            self.display_interface()
            if self.rt_structures:
                self.display_rt_structures()
            if self.show_dose_on_slice:
                self.display_dose_on_slice(True)
                
    def bind_events(self):
        """Liên kết các sự kiện"""
        # Sự kiện cuộn chuột để thay đổi slice
        self.canvas_2d.get_tk_widget().bind("<MouseWheel>", self.on_scroll)
        # Sự kiện click để đo
        self.canvas_2d.get_tk_widget().bind("<Button-1>", self.on_click)
    
    def update_patient(self, patient_id):
        """Cập nhật thông tin bệnh nhân"""
        self.patient_id = patient_id
        
        # Lấy dữ liệu volume từ cơ sở dữ liệu
        volume_data = self.db.get_volume(patient_id, 'CT')
        if volume_data:
            self.volume, self.metadata = volume_data
            self.ct_volume = self.volume.copy()  # Lưu bản sao của CT volume
            
            # Cập nhật thanh trượt slice
            if self.volume is not None and len(self.volume) > 0:
                self.slice_scale.config(to=len(self.volume) - 1)
                self.current_slice = len(self.volume) // 2
                self.slice_scale.set(self.current_slice)
            
            # Khởi tạo công cụ contour
            self.contour_tools = ContourTools(self.volume, spacing=self.metadata.get('pixel_spacing', [1.0, 1.0, 1.0]))
            
            # Hiển thị giao diện
            self.display_interface()
            
            # Khởi tạo VTK
            self.init_vtk()
        else:
            messagebox.showerror("Lỗi", f"Không tìm thấy dữ liệu CT cho bệnh nhân {patient_id}")
        
        # Lấy và hiển thị dữ liệu RT Structure nếu có
        self.rt_structures = self.db.get_rt_struct(patient_id)
        if self.rt_structures:
            print(f"Đã tải {len(self.rt_structures)} cấu trúc RT")
            self.rt_structs = self.rt_structures  # Gán cho biến rt_structs
            # Hiển thị contours trên các slice 2D
            self.display_rt_structures()
        
        # Lấy và hiển thị dữ liệu RT Dose nếu có
        dose_data = self.db.get_rt_dose(patient_id)
        if dose_data:
            self.dose_volume, self.dose_metadata = dose_data
            self.display_dose_overlay(True)
    
    def clear_measurements(self):
        """Xóa tất cả phép đo"""
        self.measurement_points = []
        self.display_interface()
        if self.rt_structures:
            self.display_rt_structures()
        if self.show_dose_on_slice:
            self.display_dose_on_slice(True)
    
    def measure_hu_value(self):
        """Đo giá trị HU tại điểm chọn"""
        if len(self.measurement_points) > 0:
            point = self.measurement_points[0]
            x, y = point
            self.display_hu_value(x, y)
    
    def on_scroll(self, event):
        """Xử lý sự kiện cuộn chuột để di chuyển qua các slice"""
        if self.volume is None or len(self.volume) == 0:
            return
        
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
            dose_mapper.SetInputData(dose_vtk_data)
            # Tạo volume actor
            self.dose_actor = vtk.vtkVolume()
            self.dose_actor.SetMapper(dose_mapper)
            self.dose_actor.SetProperty(dose_property)
            
            # Thêm vào renderer
            self.ren.AddVolume(self.dose_actor)

        # Hiển thị hoặc ẩn actor theo đối số
        if hasattr(self, 'dose_actor'):
            self.dose_actor.SetVisibility(1 if show_dose else 0)
            
            # Cập nhật opacity nếu đang hiển thị
            if show_dose:
                opacity_tf = vtk.vtkPiecewiseFunction()
                opacity_tf.AddPoint(0.0, 0.0)
                opacity_tf.AddPoint(1.0, opacity)
                self.dose_actor.GetProperty().SetScalarOpacity(opacity_tf)
            # Cập nhật renderer
            self.ren_win.Render()
            
        return True
    def display_dose_on_slice(self, show_dose=True):
        """Hiển thị phủ liều trên các slice 2D"""
        # Kiểm tra xem có dữ liệu liều không
        dose_data = self.db.get_rt_dose(self.patient_id)
        if dose_data is None:
            print("Không có dữ liệu liều RT Dose")
            return False
        
        # Lưu trạng thái hiển thị dose
        self.show_dose_on_slice = show_dose
        
        # Hiển thị lại giao diện để cập nhật với hiển thị liều
        self.display_interface()
        
        # Hiển thị cấu trúc RT nếu có
        if self.rt_structures:
            self.display_rt_structures()
            
        return True
    
    def display_interface_with_dose(self):
        """Phiên bản mở rộng của display_interface có hiển thị liều"""
        # Hiển thị thông thường
        self.display_interface()
        
        # Nếu không cần hiển thị liều, thoát
        if not hasattr(self, 'show_dose_on_slice') or not self.show_dose_on_slice:
            return
        
        # Lấy dữ liệu liều
        dose_data = self.db.get_rt_dose(self.patient_id)
        if dose_data is None:
            return
        
        dose_volume, dose_metadata = dose_data
        
        # Tạo colormap cho liều
        cmap = plt.cm.jet
        cmap.set_under('k', alpha=0)  # Liều 0 thành trong suốt
        
        # Hiển thị liều trên các slice
        if self.fig_2d.axes and len(self.fig_2d.axes) >= 3:
            axial_ax = self.fig_2d.axes[0]
            coronal_ax = self.fig_2d.axes[1]
            sagittal_ax = self.fig_2d.axes[2]
            
            # Cần nội suy dữ liệu liều vào không gian của CT
            # Ở đây giả sử chúng ta có hàm nội suy liều từ dữ liệu RT Dose
            interpolated_dose = self.interpolate_dose_to_ct(dose_volume, dose_metadata)
            
            if interpolated_dose is not None:
                # Hiển thị liều trên các slice với alpha=0.5
                if interpolated_dose.shape[0] > self.current_slice:
                    axial_dose = interpolated_dose[self.current_slice, :, :]
                    axial_ax.imshow(axial_dose, cmap=cmap, alpha=0.5, vmin=0.1)
                
                if interpolated_dose.shape[1] > 0:
                    mid_coronal = interpolated_dose.shape[1] // 2
                    coronal_dose = interpolated_dose[:, mid_coronal, :]
                    coronal_ax.imshow(coronal_dose, cmap=cmap, alpha=0.5, vmin=0.1)
                
                if interpolated_dose.shape[2] > 0:
                    mid_sagittal = interpolated_dose.shape[2] // 2
                    sagittal_dose = interpolated_dose[:, :, mid_sagittal]
                    sagittal_ax.imshow(sagittal_dose, cmap=cmap, alpha=0.5, vmin=0.1)
            
            # Cập nhật canvas
            self.canvas_2d.draw()
    
    def interpolate_dose_to_ct(self, dose_volume, dose_metadata):
        """Nội suy dữ liệu liều vào không gian CT"""
        # Đây là phương thức giả định, cần cài đặt nội suy thực tế
        # dựa trên thông tin không gian từ metadata
        
        # Kiểm tra xem có metadata đầy đủ không
        if dose_metadata is None or 'position' not in dose_metadata:
            print("Thiếu thông tin không gian cho dữ liệu liều")
            return None
        
        # Phương pháp đơn giản là giả sử hai không gian phù hợp
        # Tuy nhiên, trong thực tế cần áp dụng phép biến đổi không gian
        
        # Tạo mảng liều có cùng kích thước với CT
        interpolated_dose = np.zeros_like(self.volume)
        
        # Xác định vị trí và kích thước của liều trong không gian CT
        # Đây là đơn giản hóa, thực tế cần nội suy dựa trên metadata
        
        # Giả sử dose_origin và dose_spacing có thể lấy từ metadata
        dose_origin = dose_metadata.get('position', [0, 0, 0])
        dose_spacing = dose_metadata.get('pixel_spacing', [1, 1])
        dose_thickness = dose_metadata.get('slice_thickness', 1)
        
        # Giả sử ct_origin và ct_spacing có thể lấy từ metadata
        ct_origin = [0, 0, 0]
        ct_spacing = [1, 1, 1]
        
        if self.metadata:
            if 'slices' in self.metadata and len(self.metadata['slices']) > 0:
                ct_origin = self.metadata['slices'][0].get('position', [0, 0, 0])
            
            ct_spacing = [1, 1, 1]
            if 'pixel_spacing' in self.metadata and self.metadata['pixel_spacing']:
                ct_spacing[0] = self.metadata['pixel_spacing'][0]
                ct_spacing[1] = self.metadata['pixel_spacing'][1]
            
            if 'slice_thickness' in self.metadata and self.metadata['slice_thickness']:
                ct_spacing[2] = self.metadata['slice_thickness']
        
        # Đây là phép nội suy đơn giản, cần cải thiện trong thực tế
        # Phép nội suy thực tế cần xem xét sự khác biệt về vị trí và hướng
        
        # Trong trường hợp đơn giản, chỉ resize liều để phù hợp với CT
        try:
            # Sử dụng scipy.ndimage để resize
            from scipy.ndimage import zoom
            
            # Tính tỷ lệ nội suy
            scale_x = self.volume.shape[2] / dose_volume.shape[2]
            scale_y = self.volume.shape[1] / dose_volume.shape[1]
            scale_z = self.volume.shape[0] / dose_volume.shape[0]
            
            # Resize liều
            interpolated_dose = zoom(dose_volume, (scale_z, scale_y, scale_x), order=1)
            
            # Đảm bảo kích thước giống với CT
            if interpolated_dose.shape != self.volume.shape:
                print(f"Kích thước sau nội suy không khớp: {interpolated_dose.shape} vs {self.volume.shape}")
                return None
            
            return interpolated_dose
            
        except Exception as e:
            print(f"Lỗi khi nội suy liều: {e}")
            return None

    def export_visualization(self, output_path, file_format='png', dpi=300):
        """Xuất kết quả hiển thị ra file"""
        try:
            # Kiểm tra định dạng được hỗ trợ
            supported_formats = ['png', 'jpg', 'jpeg', 'pdf', 'svg']
            if file_format not in supported_formats:
                print(f"Định dạng {file_format} không được hỗ trợ. Chọn một trong: {supported_formats}")
                return False
            
            # Lưu hình ảnh 2D
            self.fig_2d.savefig(output_path, format=file_format, dpi=dpi, bbox_inches='tight')
            print(f"Đã lưu hình ảnh tại: {output_path}")
            
            # Nếu muốn lưu hình ảnh 3D VTK
            vtk_path = output_path.replace(f".{file_format}", f"_3d.{file_format}")
            
            # Lưu hình ảnh từ VTK renderer
            window_to_image = vtk.vtkWindowToImageFilter()
            window_to_image.SetInput(self.ren_win)
            window_to_image.Update()
            
            # Chọn writer phù hợp với định dạng
            if file_format == 'png':
                writer = vtk.vtkPNGWriter()
            elif file_format in ['jpg', 'jpeg']:
                writer = vtk.vtkJPEGWriter()
            else:
                print(f"Định dạng {file_format} không được hỗ trợ cho hình ảnh 3D")
                return False
            
            writer.SetInputConnection(window_to_image.GetOutputPort())
            writer.SetFileName(vtk_path)
            writer.Write()
            print(f"Đã lưu hình ảnh 3D tại: {vtk_path}")
            
            return True
        except Exception as e:
            print(f"Lỗi khi xuất hình ảnh: {e}")
            return False

    def load_with_image_loader(self, directory):
        """Tải dữ liệu sử dụng ImageLoader"""
        try:
            # Khởi tạo ImageLoader
            loader = ImageLoader()
            
            # Tải chuỗi DICOM
            volume_data = loader.load_dicom_series(directory)
            
            if volume_data is not None:
                self.volume, self.metadata = volume_data
                self.current_slice = self.volume.shape[0] // 2

                # Cập nhật hiển thị
                self.display_interface()

                # Cập nhật hiển thị 3D
                self.update_vtk_data()

                print(f"Đã tải thành công dữ liệu từ {directory}")
                
                # Kiểm tra và tải RT Structure nếu có
                rt_structure_path = loader.find_rt_structure(directory)
                if rt_structure_path:
                    self.rt_structures = loader.load_rt_structure(rt_structure_path)
                    if self.rt_structures:
                        self.display_rt_structures()
                
                # Kiểm tra và tải RT Dose nếu có
                rt_dose_path = loader.find_rt_dose(directory)
                if rt_dose_path:
                    dose_data = loader.load_rt_dose(rt_dose_path)
                    if dose_data:
                        self.dose_volume, self.dose_metadata = dose_data
                        self.display_dose_overlay()
                
                # Kiểm tra và tải RT Image nếu có
                rt_image_path = loader.find_rt_image(directory)
                if rt_image_path:
                    self.load_rt_image(rt_image_path)
                
                return True
            else:
                print(f"Không thể tải dữ liệu từ {directory}")
                return False
        except Exception as e:
            print(f"Lỗi khi tải dữ liệu: {e}")
            return False
    
    def load_rt_image(self, rt_image_path):
        """Tải và hiển thị RT Image"""
        try:
            # Khởi tạo ImageLoader
            loader = ImageLoader()
            
            # Tải RT Image
            rt_image_data = loader.load_rt_image(rt_image_path)
            
            if rt_image_data is not None:
                self.rt_image, self.rt_image_metadata = rt_image_data
                
                # Hiển thị RT Image
                self.display_rt_image()
                
                print(f"Đã tải thành công RT Image từ {rt_image_path}")
                return True
            else:
                print(f"Không thể tải RT Image từ {rt_image_path}")
                return False
        except Exception as e:
            print(f"Lỗi khi tải RT Image: {e}")
            return False
    
    def display_rt_image(self):
        """Hiển thị RT Image"""
        if not hasattr(self, 'rt_image') or self.rt_image is None:
            print("Không có dữ liệu RT Image để hiển thị")
            return
        
        # Tạo cửa sổ mới để hiển thị RT Image
        rt_window = tk.Toplevel(self.root)
        rt_window.title(f"RT Image - {self.patient_id}")
        rt_window.geometry("800x600")
        
        # Tạo frame chứa hình ảnh
        image_frame = tk.Frame(rt_window)
        image_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tạo figure và axes cho matplotlib
        fig = plt.Figure(figsize=(8, 6), dpi=100)
        ax = fig.add_subplot(111)
        
        # Hiển thị RT Image
        img_display = ax.imshow(self.rt_image, cmap='gray')
        
        # Thêm thanh colorbar
        fig.colorbar(img_display, ax=ax, label='Intensity')
        
        # Thêm thông tin từ metadata
        title = "RT Image"
        if hasattr(self, 'rt_image_metadata'):
            metadata = self.rt_image_metadata
            if 'rt_image_label' in metadata and metadata['rt_image_label']:
                title += f" - {metadata['rt_image_label']}"
            if 'gantry_angle' in metadata and metadata['gantry_angle'] is not None:
                title += f" - Gantry: {metadata['gantry_angle']}°"
        
        ax.set_title(title)
        
        # Tạo canvas để hiển thị figure
        canvas = FigureCanvasTkAgg(fig, master=image_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Thêm toolbar
        from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
        toolbar = NavigationToolbar2Tk(canvas, image_frame)
        toolbar.update()
        
        # Thêm frame thông tin
        info_frame = tk.Frame(rt_window)
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Hiển thị thông tin từ metadata
        if hasattr(self, 'rt_image_metadata'):
            metadata = self.rt_image_metadata
            info_text = ""
            
            if 'radiation_machine_name' in metadata and metadata['radiation_machine_name']:
                info_text += f"Máy xạ trị: {metadata['radiation_machine_name']}\n"
            
            if 'gantry_angle' in metadata and metadata['gantry_angle'] is not None:
                info_text += f"Góc gantry: {metadata['gantry_angle']}°\n"
            
            if 'beam_limiting_device_angle' in metadata and metadata['beam_limiting_device_angle'] is not None:
                info_text += f"Góc collimator: {metadata['beam_limiting_device_angle']}°\n"
            
            if 'patient_support_angle' in metadata and metadata['patient_support_angle'] is not None:
                info_text += f"Góc bàn: {metadata['patient_support_angle']}°\n"
            
            info_label = tk.Label(info_frame, text=info_text, justify=tk.LEFT)
            info_label.pack(anchor=tk.W)
        
        # Thêm nút để lưu hình ảnh
        button_frame = tk.Frame(rt_window)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        save_button = tk.Button(button_frame, text="Lưu hình ảnh", 
                               command=lambda: self.save_rt_image(fig))
        save_button.pack(side=tk.LEFT, padx=5)
        
        close_button = tk.Button(button_frame, text="Đóng", 
                                command=rt_window.destroy)
        close_button.pack(side=tk.RIGHT, padx=5)
    
    def save_rt_image(self, figure, filename=None):
        """Lưu RT Image ra file"""
        if filename is None:
            # Tạo tên file mặc định
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"rt_image_{self.patient_id}_{timestamp}.png"
        
        # Hiển thị hộp thoại để chọn nơi lưu file
        from tkinter import filedialog
        save_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")],
            initialfile=filename
        )
        
        if save_path:
            try:
                figure.savefig(save_path, dpi=300, bbox_inches='tight')
                print(f"Đã lưu RT Image tại: {save_path}")
                
                # Hiển thị thông báo thành công
                from tkinter import messagebox
                messagebox.showinfo("Thành công", f"Đã lưu hình ảnh tại:\n{save_path}")
                
                return True
            except Exception as e:
                print(f"Lỗi khi lưu RT Image: {e}")
                
                # Hiển thị thông báo lỗi
                from tkinter import messagebox
                messagebox.showerror("Lỗi", f"Không thể lưu hình ảnh:\n{str(e)}")
                
                return False
        
        return False

    def close(self):
        """Dọn dẹp tài nguyên khi đóng ứng dụng"""
        # Dừng VTK interactor nếu đang chạy
        if hasattr(self, 'iren') and self.iren:
            self.iren.TerminateApp()
    
        # Giải phóng tài nguyên VTK
        if hasattr(self, 'ren_win') and self.ren_win:
            self.ren_win.Finalize()
    
        # Xóa các tham chiếu đến VTK objects
        if hasattr(self, 'volume_actor'):
            del self.volume_actor
        if hasattr(self, 'vtk_data'):
            del self.vtk_data
        if hasattr(self, 'ren'):
            del self.ren
        if hasattr(self, 'ren_win'):
            del self.ren_win
        if hasattr(self, 'iren'):
            del self.iren
    
        # Dọn dẹp các biến khác
        if hasattr(self, 'structure_actors'):
            del self.structure_actors
        if hasattr(self, 'dose_actor'):
            del self.dose_actor
    
        print("Đã giải phóng tài nguyên hiển thị")

    def create_screenshot(self, output_path):
        """Tạo ảnh chụp màn hình của giao diện hiện tại"""
        try:
            # Lưu hình ảnh 2D
            self.fig_2d.savefig(output_path, format='png', dpi=150)
        
            # Tạo ảnh chụp từ VTK renderer
            vtk_path = output_path.replace('.png', '_3d.png')
        
            window_to_image = vtk.vtkWindowToImageFilter()
            window_to_image.SetInput(self.ren_win)
            window_to_image.Update()
        
            writer = vtk.vtkPNGWriter()
            writer.SetInputConnection(window_to_image.GetOutputPort())
            writer.SetFileName(vtk_path)
            writer.Write()
        
            print(f"Đã lưu ảnh chụp màn hình tại: {output_path} và {vtk_path}")
            return True
        except Exception as e:
            print(f"Lỗi khi tạo ảnh chụp màn hình: {e}")
            return False

    def generate_3d_model_from_struct(self, structure_name, output_stl=None):
        """Tạo mô hình 3D từ cấu trúc RT và xuất ra file STL nếu cần"""
        if not self.rt_structures:
            print("Không có dữ liệu RT Structure")
            return None
    
        # Tìm structure theo tên
        structure = None
        for roi_number, struct in self.rt_structures.items():
            if struct.get('name', '') == structure_name:
                structure = struct
                break
            
        if structure is None:
            print(f"Không tìm thấy cấu trúc RT có tên {structure_name}")
            return None
    
        try:
            # Tạo mô hình 3D từ cấu trúc RT
            points = vtk.vtkPoints()
            cells = vtk.vtkCellArray()
        
            # Thêm các điểm từ contour data
            contour_data = structure.get('contour_data', [])
            if not contour_data:
                print(f"Cấu trúc {structure_name} không có dữ liệu contour")
                return None
        
            # Tạo các polygon từ contour data
            for contour in contour_data:
                point_data = contour.get('points', [])
                if len(point_data) < 3:  # Bỏ qua contour không đủ điểm
                    continue
                
                # Thêm points và tạo polygon
                polygon = vtk.vtkPolygon()
                polygon.GetPointIds().SetNumberOfIds(len(point_data))
            
                for i, point in enumerate(point_data):
                    point_id = points.InsertNextPoint(point)
                    polygon.GetPointIds().SetId(i, point_id)
                
                cells.InsertNextCell(polygon)
        
            # Tạo polydata
            polydata = vtk.vtkPolyData()
            polydata.SetPoints(points)
            polydata.SetPolys(cells)
        
            # Sử dụng Delaunay3D để tạo bề mặt
            delaunay = vtk.vtkDelaunay3D()
            delaunay.SetInputData(polydata)
            delaunay.Update()
        
            # Chuyển đổi sang bề mặt
            surface = vtk.vtkGeometryFilter()
            surface.SetInputConnection(delaunay.GetOutputPort())
            surface.Update()
        
            # Làm mịn bề mặt
            smoother = vtk.vtkSmoothPolyDataFilter()
            smoother.SetInputConnection(surface.GetOutputPort())
            smoother.SetNumberOfIterations(15)
            smoother.SetRelaxationFactor(0.1)
            smoother.Update()
        
            # Tính toán normal vectors
            normals = vtk.vtkPolyDataNormals()
            normals.SetInputConnection(smoother.GetOutputPort())
            normals.ComputePointNormalsOn()
            normals.ComputeCellNormalsOn()
            normals.SplittingOff()
            normals.Update()
        
            # Xuất STL nếu cần
            if output_stl:
                writer = vtk.vtkSTLWriter()
                writer.SetInputConnection(normals.GetOutputPort())
                writer.SetFileName(output_stl)
                writer.Write()
                print(f"Đã xuất mô hình 3D ra file STL: {output_stl}")
        
            # Trả về dữ liệu polydata đã xử lý
            return normals.GetOutput()
        
        except Exception as e:
            print(f"Lỗi khi tạo mô hình 3D: {e}")
            import traceback
            traceback.print_exc()
            return None

    def add_measurement_tools(self):
        """Thêm công cụ đo lường vào giao diện"""
        # Tạo frame chứa các công cụ đo lường
        self.measurement_frame = tk.Frame(self.root)
        self.measurement_frame.pack(fill=tk.X)
    
        # Nút đo khoảng cách
        self.measure_distance_btn = tk.Button(self.measurement_frame, text="Đo khoảng cách",command=self.activate_distance_measurement)
        self.measure_distance_btn.pack(side=tk.LEFT, padx=5, pady=5)
    
        # Nút đo góc
        self.measure_angle_btn = tk.Button(self.measurement_frame, text="Đo góc",command=self.activate_angle_measurement)
        self.measure_angle_btn.pack(side=tk.LEFT, padx=5, pady=5)
    
        # Nút đo HU (Hounsfield Units)
        self.measure_hu_btn = tk.Button(self.measurement_frame, text="Đo giá trị HU",command=self.activate_hu_measurement)
        self.measure_hu_btn.pack(side=tk.LEFT, padx=5, pady=5)
    
        # Nút xóa các phép đo
        self.clear_measurements_btn = tk.Button(self.measurement_frame, text="Xóa phép đo",command=self.clear_measurements)
        self.clear_measurements_btn.pack(side=tk.LEFT, padx=5, pady=5)
    
        # Biến lưu trạng thái đo lường hiện tại
        self.measurement_mode = None
    
        # Biến lưu các điểm đã chọn
        self.measurement_points = []
    
        # Kết nối sự kiện click chuột vào canvas matplotlib
        self.canvas_2d.mpl_connect('button_press_event', self.on_click)

    def activate_distance_measurement(self):
        """Kích hoạt chế độ đo khoảng cách"""
        self.measurement_mode = 'distance'
        self.measurement_points = []
        print("Đã kích hoạt chế độ đo khoảng cách. Hãy chọn hai điểm.")

    def activate_angle_measurement(self):
        """Kích hoạt chế độ đo góc"""
        self.measurement_mode = 'angle'
        self.measurement_points = []
        print("Đã kích hoạt chế độ đo góc. Hãy chọn ba điểm để tạo hai vector.")

    def activate_hu_measurement(self):
        """Kích hoạt chế độ đo giá trị HU"""
        self.measurement_mode = 'hu'
        self.measurement_points = []
        print("Đã kích hoạt chế độ đo giá trị HU. Hãy chọn một điểm.")

    def on_click(self, event):
        """Xử lý sự kiện click chuột"""
        if not self.measurement_mode or event.inaxes is None:
            return
    
        # Lấy tọa độ pixel hiện tại
        x, y = int(event.xdata), int(event.ydata)
    
        # Thêm điểm vào danh sách
        self.measurement_points.append((x, y))
    
        # Xử lý theo chế độ đo lường
        if self.measurement_mode == 'distance' and len(self.measurement_points) == 2:
            self.calculate_distance()
        elif self.measurement_mode == 'angle' and len(self.measurement_points) == 3:
            self.calculate_angle()
        elif self.measurement_mode == 'hu' and len(self.measurement_points) == 1:
            self.measure_hu_value()

    def calculate_distance(self):
        """Tính toán khoảng cách giữa hai điểm"""
        if len(self.measurement_points) != 2:
            return
    
        p1, p2 = self.measurement_points
    
        # Lấy thông tin pixel spacing từ metadata
        pixel_spacing = [1.0, 1.0]  # Mặc định nếu không có metadata
        if self.metadata and 'pixel_spacing' in self.metadata and self.metadata['pixel_spacing']:
            pixel_spacing = self.metadata['pixel_spacing']
    
        # Tính khoảng cách theo pixel
        pixel_distance = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
    
        # Tính khoảng cách thực (mm)
        real_distance = pixel_distance * pixel_spacing[0]  # Giả sử spacing đều
    
        # Hiển thị khoảng cách trên hình
        ax = self.fig_2d.axes[0]  # Giả sử đang hiển thị trên axial view
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], 'r-', linewidth=2)
        ax.text((p1[0] + p2[0])/2, (p1[1] + p2[1])/2, f'{real_distance:.2f} mm',color='red', fontsize=9, backgroundcolor='white')
    
        self.canvas_2d.draw()
    
        # Reset chế độ đo
        self.measurement_mode = None
        self.measurement_points = []
        print(f"Khoảng cách: {real_distance:.2f} mm")

    def calculate_angle(self):
        """Tính toán góc giữa hai vector tạo bởi ba điểm"""
        if len(self.measurement_points) != 3:
            return
    
        p1, p2, p3 = self.measurement_points
    
        # Tạo hai vector
        v1 = np.array([p1[0] - p2[0], p1[1] - p2[1]])
        v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
    
        # Tính góc (radian)
        dot_product = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
    
        if norm_v1 == 0 or norm_v2 == 0:
            print("Không thể tính góc: vector có độ dài bằng 0")
            return
        
        cos_angle = dot_product / (norm_v1 * norm_v2)
        # Đảm bảo giá trị nằm trong khoảng [-1, 1] để tránh lỗi do làm tròn số
        cos_angle = max(-1, min(1, cos_angle))
        angle_rad = np.arccos(cos_angle)
        angle_deg = np.degrees(angle_rad)
        
        # Hiển thị kết quả
        print(f"Góc: {angle_deg:.2f} độ")
        
        # Vẽ góc lên hình
        self.draw_angle_measurement(p1, p2, p3, angle_deg)
        
        return angle_deg
    
    def draw_angle_measurement(self, p1, p2, p3, angle):
        """Vẽ góc đo lên hình"""
        # Xóa các đối tượng đo góc cũ nếu có
        for item in self.canvas.find_withtag("angle_measurement"):
            self.canvas.delete(item)
        
        # Vẽ các đường thẳng
        self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill="yellow", width=2, tags="angle_measurement")
        self.canvas.create_line(p2[0], p2[1], p3[0], p3[1], fill="yellow", width=2, tags="angle_measurement")
        
        # Vẽ cung tròn biểu thị góc
        radius = 30  # Bán kính cung tròn
        
        # Tính góc bắt đầu và góc quét dựa trên vị trí các điểm
        v1 = np.array([p1[0] - p2[0], p1[1] - p2[1]])
        v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
        
        angle1 = np.degrees(np.arctan2(v1[1], v1[0]))
        angle2 = np.degrees(np.arctan2(v2[1], v2[0]))
        
        # Đảm bảo góc bắt đầu nhỏ hơn góc kết thúc
        if angle1 > angle2:
            angle1, angle2 = angle2, angle1
        
        # Vẽ cung tròn
        self.canvas.create_arc(p2[0] - radius, p2[1] - radius, 
                              p2[0] + radius, p2[1] + radius,
                              start=angle1, extent=angle2-angle1,
                              outline="yellow", style="arc", width=2,
                              tags="angle_measurement")
        
        # Hiển thị giá trị góc
        text_x = p2[0] + radius * 0.7 * np.cos(np.radians((angle1 + angle2) / 2))
        text_y = p2[1] + radius * 0.7 * np.sin(np.radians((angle1 + angle2) / 2))
        self.canvas.create_text(text_x, text_y, text=f"{angle:.1f}°", 
                               fill="yellow", font=("Arial", 10, "bold"),
                               tags="angle_measurement")
    
    def calculate_hu_value(self, x, y, slice_index):
        """Tính giá trị HU tại một điểm"""
        if self.ct_volume is None:
            return None
        
        # Chuyển đổi từ tọa độ pixel sang chỉ số mảng
        i, j = int(y), int(x)
        
        # Kiểm tra giới hạn
        if (0 <= slice_index < self.ct_volume.shape[0] and 
            0 <= i < self.ct_volume.shape[1] and 
            0 <= j < self.ct_volume.shape[2]):
            return self.ct_volume[slice_index, i, j]
        
        return None
    
    def display_hu_value(self, x, y):
        """Hiển thị giá trị HU tại vị trí chuột"""
        if self.current_slice is None or self.ct_volume is None:
            return
        
        hu_value = self.calculate_hu_value(x, y, self.current_slice)
        if hu_value is not None:
            # Xóa text cũ
            for item in self.canvas.find_withtag("hu_display"):
                self.canvas.delete(item)
            
            # Hiển thị giá trị HU
            self.canvas.create_text(x + 20, y - 20, 
                                   text=f"HU: {int(hu_value)}", 
                                   fill="white", font=("Arial", 10),
                                   tags="hu_display")
            
            # Hiển thị thêm thông tin về mật độ vật lý nếu có
            if hasattr(self, 'image_loader'):
                density = self.image_loader.hounsfield_to_density(hu_value)
                self.canvas.create_text(x + 20, y - 5, 
                                       text=f"Density: {density:.3f} g/cm³", 
                                       fill="white", font=("Arial", 10),
                                       tags="hu_display")
    
    def generate_dvh(self, structure_name, dose_data):
        """Tạo biểu đồ DVH cho một cấu trúc"""
        if self.rt_structs is None or structure_name not in self.rt_structs:
            messagebox.showerror("Lỗi", f"Không tìm thấy cấu trúc {structure_name}")
            return None
        
        # Lấy mask của cấu trúc
        structure_mask = self.get_structure_mask(structure_name)
        if structure_mask is None:
            return None
        
        # Đảm bảo dose_data và structure_mask có cùng kích thước
        if dose_data.shape != structure_mask.shape:
            # Nội suy dose_data về cùng kích thước với structure_mask
            dose_data = self.interpolate_dose_to_ct(dose_data, None)
        
        # Lấy các giá trị liều trong vùng cấu trúc
        structure_dose = dose_data[structure_mask > 0]
        
        if len(structure_dose) == 0:
            messagebox.showerror("Lỗi", f"Không có voxel nào trong cấu trúc {structure_name}")
            return None
        
        # Tính toán DVH
        hist, bin_edges = np.histogram(structure_dose, bins=100, range=(0, np.max(dose_data)))
        dvh = np.cumsum(hist[::-1])[::-1]  # Tính tích lũy ngược
        dvh = dvh / dvh[0] * 100 if dvh[0] > 0 else dvh  # Chuẩn hóa về phần trăm
        
        # Tính các thông số thống kê
        d_min = np.min(structure_dose)
        d_max = np.max(structure_dose)
        d_mean = np.mean(structure_dose)
        
        # Tính D95, D50, V95, V100
        dose_bins = bin_edges[:-1]  # Lấy giá trị giữa của các bin
        
        # Nội suy tuyến tính để tìm D95, D50
        d95 = np.interp(95, dvh[::-1], dose_bins[::-1])
        d50 = np.interp(50, dvh[::-1], dose_bins[::-1])
        
        # Tìm V95, V100
        prescribed_dose = np.max(dose_data)  # Giả sử liều kê đơn là liều tối đa
        v95_idx = np.argmin(np.abs(dose_bins - 0.95 * prescribed_dose))
        v100_idx = np.argmin(np.abs(dose_bins - prescribed_dose))
        
        v95 = dvh[v95_idx]
        v100 = dvh[v100_idx]
        
        # Tạo đối tượng DVH
        dvh_obj = {
            'structure_name': structure_name,
            'dose_bins': dose_bins.tolist(),
            'volume': dvh.tolist(),
            'd_min': d_min,
            'd_max': d_max,
            'd_mean': d_mean,
            'd95': d95,
            'd50': d50,
            'v95': v95,
            'v100': v100
        }
        
        return dvh_obj
    
    def plot_dvh(self, dvh_data_list):
        """Vẽ biểu đồ DVH từ danh sách dữ liệu DVH"""
        if not dvh_data_list:
            return
        
        # Tạo cửa sổ mới cho biểu đồ DVH
        dvh_window = tk.Toplevel(self.root)
        dvh_window.title("Biểu đồ DVH")
        dvh_window.geometry("800x600")
        
        # Tạo figure và axes
        fig = plt.Figure(figsize=(10, 6), dpi=100)
        ax = fig.add_subplot(111)
        
        # Vẽ DVH cho từng cấu trúc
        for dvh_data in dvh_data_list:
            structure_name = dvh_data['structure_name']
            dose_bins = dvh_data['dose_bins']
            volume = dvh_data['volume']
            
            # Lấy màu cho cấu trúc
            color = self.get_structure_color(structure_name)
            
            # Vẽ đường DVH
            ax.plot(dose_bins, volume, label=f"{structure_name}", color=color)
            
            # Đánh dấu các điểm quan trọng
            ax.plot(dvh_data['d95'], 95, 'o', color=color)
            ax.plot(dvh_data['d50'], 50, 'o', color=color)
        
        # Thiết lập trục và nhãn
        ax.set_xlabel('Liều (Gy)')
        ax.set_ylabel('Thể tích (%)')
        ax.set_title('Biểu đồ DVH')
        ax.grid(True)
        ax.legend()
        
        # Thêm figure vào cửa sổ Tkinter
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        canvas = FigureCanvasTkAgg(fig, master=dvh_window)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        
        # Thêm toolbar
        from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
        toolbar = NavigationToolbar2Tk(canvas, dvh_window)
        toolbar.update()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
    
    def get_structure_color(self, structure_name):
        """Lấy màu của cấu trúc"""
        if self.rt_structs is None or structure_name not in self.rt_structs:
            return 'blue'  # Màu mặc định
        
        # Lấy màu từ dữ liệu RT Structure
        color = self.rt_structs[structure_name].get('color', [1, 0, 0])
        
        # Chuyển đổi từ dạng [r, g, b] sang chuỗi màu
        return f'#{int(color[0]*255):02x}{int(color[1]*255):02x}{int(color[2]*255):02x}'
    
    def get_structure_mask(self, structure_name):
        """Tạo mask cho một cấu trúc"""
        if self.rt_structs is None or structure_name not in self.rt_structs:
            return None
        
        # Tạo mask trống
        mask = np.zeros_like(self.ct_volume)
        
        # Lấy dữ liệu contour
        contour_data = self.rt_structs[structure_name].get('contour_data', [])
        
        # Duyệt qua từng contour
        for contour in contour_data:
            points = contour.get('points', [])
            slice_z = contour.get('slice_z', 0)
            
            # Tìm slice index tương ứng với slice_z
            slice_index = self.find_nearest_slice(slice_z)
            
            if slice_index is None:
                continue
            
            # Chuyển đổi điểm từ tọa độ DICOM sang chỉ số pixel
            pixel_points = []
            for point in points:
                pixel_x, pixel_y = self.convert_dicom_to_pixel(point[0], point[1])
                pixel_points.append([pixel_x, pixel_y])
            
            # Tạo mask cho contour này
            if pixel_points:
                pixel_points = np.array(pixel_points, dtype=np.int32)
                slice_mask = np.zeros((self.ct_volume.shape[1], self.ct_volume.shape[2]), dtype=np.uint8)
                cv2.fillPoly(slice_mask, [pixel_points], 1)
                
                # Cập nhật mask tổng
                mask[slice_index] = np.logical_or(mask[slice_index], slice_mask)
        
        return mask
    
    def find_nearest_slice(self, z_position):
        """Tìm chỉ số slice gần nhất với vị trí z"""
        if not hasattr(self, 'slice_positions') or not self.slice_positions:
            return None
        
        # Tìm chỉ số của slice gần nhất
        distances = np.abs(np.array(self.slice_positions) - z_position)
        nearest_idx = np.argmin(distances)
        
        return nearest_idx

    def setup_ui(self):
        """Thiết lập giao diện người dùng"""
        # Tạo frame chính
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tạo frame cho hiển thị 2D
        self.frame_2d = tk.Frame(self.main_frame)
        self.frame_2d.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Tạo hình ảnh 2D với matplotlib
        self.fig_2d = plt.figure(figsize=(8, 8))
        self.canvas_2d = FigureCanvasTkAgg(self.fig_2d, self.frame_2d)
        self.canvas_2d.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Tạo frame cho hiển thị 3D
        self.frame_3d = tk.Frame(self.main_frame)
        self.frame_3d.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Tạo VTK widget cho hiển thị 3D
        self.vtk_widget = tk.Frame(self.frame_3d, width=400, height=400)
        self.vtk_widget.pack(fill=tk.BOTH, expand=True)
        
        # Khởi tạo VTK renderer
        self.init_vtk()
        
        # Tạo frame điều khiển
        self.control_frame = tk.Frame(self.root)
        self.control_frame.pack(fill=tk.X)
        
        # Tạo các nút điều khiển
        self.create_control_buttons()
        
        # Liên kết sự kiện
        self.bind_events()

    def create_control_buttons(self):
        """Tạo các nút điều khiển"""
        # Nút hiển thị/ẩn liều
        self.dose_button = tk.Button(
            self.control_frame, 
            text="Hiển thị liều", 
            command=lambda: self.display_dose_overlay(not self.show_dose)
        )
        self.dose_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Nút hiển thị RT Structures
        self.structures_button = tk.Button(
            self.control_frame, 
            text="Hiển thị cấu trúc", 
            command=self.display_rt_structures
        )
        self.structures_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Nút công cụ đo
        self.measurement_button = tk.Button(
            self.control_frame, 
            text="Công cụ đo", 
            command=self.add_measurement_tools
        )
        self.measurement_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Nút chụp màn hình
        self.screenshot_button = tk.Button(
            self.control_frame, 
            text="Chụp màn hình", 
            command=lambda: self.create_screenshot("screenshot.png")
        )
        self.screenshot_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Thanh trượt slice
        self.slice_label = tk.Label(self.control_frame, text="Slice:")
        self.slice_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.slice_scale = tk.Scale(
            self.control_frame, 
            from_=0, 
            to=100, 
            orient=tk.HORIZONTAL,
            command=self.on_slice_change
        )
        self.slice_scale.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        
    def on_slice_change(self, event):
        """Xử lý sự kiện thay đổi slice"""
        if self.volume is not None and len(self.volume) > 0:
            self.current_slice = int(self.slice_scale.get())
            self.display_interface()
            if self.rt_structures:
                self.display_rt_structures()
            if self.show_dose_on_slice:
                self.display_dose_on_slice(True)
                
    def bind_events(self):
        """Liên kết các sự kiện"""
        # Sự kiện cuộn chuột để thay đổi slice
        self.canvas_2d.get_tk_widget().bind("<MouseWheel>", self.on_scroll)
        # Sự kiện click để đo
        self.canvas_2d.get_tk_widget().bind("<Button-1>", self.on_click)