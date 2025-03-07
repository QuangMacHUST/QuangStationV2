# pylint: disable=E1101
import numpy as np
import cv2  # pylint: disable=E1101
import matplotlib.pyplot as plt
from matplotlib.path import Path
from typing import Dict, List, Tuple, Any, Optional

# Disable pylint errors for OpenCV functions
# pylint: disable=no-member

class ContourTools:
    """Cung cấp công cụ để vẽ và chỉnh sửa contour"""
    
    def __init__(self, image_data, spacing=(1.0, 1.0, 1.0)):
        self.image_data = image_data
        self.spacing = spacing
        self.contours = {}  # Dictionary lưu các contour của các cấu trúc
        self.colors = {}    # Dictionary lưu màu sắc cho các cấu trúc
        self.current_struct = None
        self.isocenter = None
    
    def add_structure(self, name, color=None):
        """Thêm một cấu trúc mới"""
        if name not in self.contours:
            self.contours[name] = {}  # Dictionary lưu contour theo slice {slice_idx: points}
            
            # Gán màu mặc định nếu không cung cấp
            if color is None:
                # Một số màu mặc định cho các cấu trúc phổ biến
                if name.lower() == "ptv" or name.lower().startswith("ptv"):
                    color = (255, 0, 0)  # Đỏ cho PTV
                elif name.lower() == "ctv" or name.lower().startswith("ctv"):
                    color = (255, 165, 0)  # Cam cho CTV
                elif name.lower() == "gtv" or name.lower().startswith("gtv"):
                    color = (255, 0, 255)  # Hồng cho GTV
                elif "heart" in name.lower() or "tim" in name.lower():
                    color = (255, 0, 0)  # Đỏ cho tim
                elif "lung" in name.lower() or "phoi" in name.lower():
                    color = (0, 0, 255)  # Xanh dương cho phổi
                elif "spinal" in name.lower() or "cord" in name.lower() or "tuy" in name.lower():
                    color = (255, 255, 0)  # Vàng cho tủy sống
                elif "liver" in name.lower() or "gan" in name.lower():
                    color = (165, 42, 42)  # Nâu cho gan
                elif "kidney" in name.lower() or "than" in name.lower():
                    color = (128, 0, 128)  # Tím cho thận
                elif "brain" in name.lower() or "nao" in name.lower():
                    color = (0, 255, 0)  # Xanh lá cho não
                elif "external" in name.lower() or "body" in name.lower() or "than" in name.lower():
                    color = (0, 255, 255)  # Xanh lam cho body
                else:
                    # Tạo màu ngẫu nhiên nếu không có màu mặc định
                    color = (
                        np.random.randint(0, 256),
                        np.random.randint(0, 256),
                        np.random.randint(0, 256)
                    )
            
            self.colors[name] = color
            self.current_struct = name
            return True
        return False
    
    def set_current_structure(self, name):
        """Thiết lập cấu trúc đang hoạt động"""
        if name in self.contours:
            self.current_struct = name
            return True
        return False
    
    def add_contour_points(self, slice_index, points, axis='axial'):
        """Thêm điểm contour cho cấu trúc hiện tại và lát cắt"""
        if self.current_struct is None:
            raise ValueError("Chưa chọn cấu trúc")
        
        key = f"{axis}_{slice_index}"
        
        if key not in self.contours[self.current_struct]:
            self.contours[self.current_struct][key] = []
        
        self.contours[self.current_struct][key].append(points)
        
        return True
    
    def delete_contour(self, name, slice_index=None, axis='axial'):
        """Xóa contour của một cấu trúc"""
        if name not in self.contours:
            return False
        
        if slice_index is None:
            # Xóa tất cả contour của cấu trúc
            self.contours[name] = {}
        else:
            # Xóa contour của một lát cắt cụ thể
            key = f"{axis}_{slice_index}"
            if key in self.contours[name]:
                del self.contours[name][key]
        
        return True
    
    def set_isocenter(self, position):
        """Thiết lập tâm isocenter"""
        self.isocenter = position  # (x, y, z) trong hệ tọa độ DICOM (mm)
        return True
    
    def get_isocenter(self):
        """Lấy vị trí tâm isocenter"""
        return self.isocenter
    
    def generate_mask_from_contour(self, name, shape):
        """Tạo mask từ contour"""
        if name not in self.contours:
            return None
        
        mask = np.zeros(shape, dtype=np.uint8)
        
        for key, contour_list in self.contours[name].items():
            axis, slice_idx = key.split('_')
            slice_idx = int(slice_idx)
            
            # Xác định kích thước lát cắt dựa trên trục
            if axis == 'axial':
                slice_shape = (shape[1], shape[2])
                for contour in contour_list:
                    points = np.array(contour, dtype=np.int32)
                    slice_mask = np.zeros(slice_shape, dtype=np.uint8)
                    cv2.fillPoly(slice_mask, [points], 1)
                    mask[slice_idx, :, :] = np.logical_or(mask[slice_idx, :, :], slice_mask)
            
            elif axis == 'coronal':
                slice_shape = (shape[0], shape[2])
                for contour in contour_list:
                    points = np.array(contour, dtype=np.int32)
                    slice_mask = np.zeros(slice_shape, dtype=np.uint8)
                    cv2.fillPoly(slice_mask, [points], 1)
                    mask[:, slice_idx, :] = np.logical_or(mask[:, slice_idx, :], slice_mask)
            
            elif axis == 'sagittal':
                slice_shape = (shape[0], shape[1])
                for contour in contour_list:
                    points = np.array(contour, dtype=np.int32)
                    slice_mask = np.zeros(slice_shape, dtype=np.uint8)
                    cv2.fillPoly(slice_mask, [points], 1)
                    mask[:, :, slice_idx] = np.logical_or(mask[:, :, slice_idx], slice_mask)
        
        return mask
    
    def interpolate_contours(self, name, axis='axial'):
        """Nội suy contour giữa các lát cắt"""
        if name not in self.contours:
            return False
        
        # Lấy danh sách lát cắt có contour
        slice_keys = [key for key in self.contours[name].keys() if key.startswith(f"{axis}_")]
        slice_indices = [int(key.split('_')[1]) for key in slice_keys]
        
        if len(slice_indices) < 2:
            return False  # Cần ít nhất 2 lát cắt để nội suy
        
        slice_indices.sort()
        
        # Nội suy giữa các lát cắt liên tiếp
        for i in range(len(slice_indices) - 1):
            start_idx = slice_indices[i]
            end_idx = slice_indices[i + 1]
            
            # Bỏ qua nếu các lát cắt liên tiếp
            if end_idx - start_idx <= 1:
                continue
            
            start_key = f"{axis}_{start_idx}"
            end_key = f"{axis}_{end_idx}"
            
            # Lấy contour đầu và cuối (chỉ lấy contour đầu tiên nếu có nhiều contour)
            start_contour = self.contours[name][start_key][0]
            end_contour = self.contours[name][end_key][0]
            
            # Chuyển đổi thành mảng numpy để dễ xử lý
            start_points = np.array(start_contour)
            end_points = np.array(end_contour)
            
            # Đảm bảo cả hai contour có cùng số điểm
            if len(start_points) != len(end_points):
                # Đơn giản hóa để cùng số điểm (có thể cải thiện)
                min_points = min(len(start_points), len(end_points))
                start_points = start_points[:min_points]
                end_points = end_points[:min_points]
            
            # Số lát cắt nội suy
            num_slices = end_idx - start_idx - 1
            
            # Tạo contour nội suy
            for j in range(1, num_slices + 1):
                # Hệ số nội suy
                t = j / (num_slices + 1)
                
                # Tính điểm nội suy
                interp_points = start_points * (1 - t) + end_points * t
                interp_points = interp_points.astype(int)
                
                # Thêm contour nội suy
                interp_slice_idx = start_idx + j
                interp_key = f"{axis}_{interp_slice_idx}"
                
                if interp_key not in self.contours[name]:
                    self.contours[name][interp_key] = []
                
                self.contours[name][interp_key].append(interp_points.tolist())
        
        return True
    
    def get_contour_points(self, name, slice_index, axis='axial'):
        """Lấy điểm contour cho một lát cắt cụ thể"""
        if name not in self.contours:
            return []
        
        key = f"{axis}_{slice_index}"
        return self.contours[name].get(key, [])
    
    def render_contours(self, ax, name, slice_index, axis='axial'):
        """Vẽ contour lên trục matplotlib"""
        if name not in self.contours:
            return
        
        key = f"{axis}_{slice_index}"
        if key not in self.contours[name]:
            return
        
        color = self.colors.get(name, (255, 0, 0))
        # Chuyển màu từ BGR sang RGB cho matplotlib
        rgb_color = (color[2]/255, color[1]/255, color[0]/255)
        
        for contour in self.contours[name][key]:
            points = np.array(contour)
            # Vẽ contour
            ax.plot(points[:, 0], points[:, 1], color=rgb_color, linewidth=2)
            # Vẽ điểm
            ax.scatter(points[:, 0], points[:, 1], color=rgb_color, s=10)
    
    def render_isocenter(self, ax, slice_index, axis='axial'):
        """Vẽ tâm isocenter lên trục matplotlib"""
        if self.isocenter is None:
            return
        
        x, y, z = self.isocenter
        
        # Vẽ tâm dựa vào trục hiện tại
        if axis == 'axial' and abs(z - slice_index * self.spacing[0]) < self.spacing[0]/2:
            ax.plot(x/self.spacing[1], y/self.spacing[2], 'r+', markersize=10, markeredgewidth=2)
        elif axis == 'coronal' and abs(y - slice_index * self.spacing[1]) < self.spacing[1]/2:
            ax.plot(x/self.spacing[2], z/self.spacing[0], 'r+', markersize=10, markeredgewidth=2)
        elif axis == 'sagittal' and abs(x - slice_index * self.spacing[2]) < self.spacing[2]/2:
            ax.plot(y/self.spacing[1], z/self.spacing[0], 'r+', markersize=10, markeredgewidth=2)
    
    def copy_structure(self, source_name, target_name, color=None):
        """Sao chép một cấu trúc từ một cấu trúc khác
        
        Args:
            source_name (str): Tên cấu trúc nguồn
            target_name (str): Tên cấu trúc đích
            color (tuple, optional): Màu sắc của cấu trúc mới. Mặc định là None (sẽ sử dụng màu từ nguồn).
            
        Returns:
            bool: True nếu sao chép thành công, False nếu thất bại
        """
        # Kiểm tra xem cấu trúc nguồn có tồn tại không
        if source_name not in self.contours:
            print(f"Cấu trúc nguồn '{source_name}' không tồn tại")
            return False
        
        # Kiểm tra xem tên cấu trúc đích đã tồn tại chưa
        if target_name in self.contours:
            print(f"Cấu trúc đích '{target_name}' đã tồn tại. Việc sao chép sẽ ghi đè.")
        
        # Lấy màu sắc từ nguồn nếu không được chỉ định
        if color is None:
            color = self.colors[source_name]
        
        # Tạo cấu trúc mới
        self.add_structure(target_name, color)
        
        # Sao chép dữ liệu từ cấu trúc nguồn
        for axis in ['axial', 'coronal', 'sagittal']:
            # Sao chép contours cho từng slice
            slice_indices = self.contours[source_name].get(axis, {}).keys()
            for slice_idx in slice_indices:
                points = self.get_contour_points(source_name, slice_idx, axis)
                if points and len(points) > 0:
                    self.add_contour_points(slice_idx, points, axis)
        
        # Sao chép thông tin khác
        self.current_struct = target_name
        
        print(f"Đã sao chép cấu trúc từ '{source_name}' sang '{target_name}'")
        return True
    
    def expand_structure(self, source_name, target_name, margin_mm, color=None):
        """Mở rộng một cấu trúc với lề xác định
        
        Args:
            source_name (str): Tên cấu trúc nguồn
            target_name (str): Tên cấu trúc đích sau khi mở rộng
            margin_mm (float): Lề mở rộng tính bằng mm
            color (tuple, optional): Màu sắc của cấu trúc mới
            
        Returns:
            bool: True nếu mở rộng thành công, False nếu thất bại
        """
        import cv2
        import numpy as np
        
        # Kiểm tra xem cấu trúc nguồn có tồn tại không
        if source_name not in self.contours:
            print(f"Cấu trúc nguồn '{source_name}' không tồn tại")
            return False
        
        # Tạo cấu trúc mới
        if color is None:
            color = self.colors[source_name]
        self.add_structure(target_name, color)
        
        # Tính số pixel cần mở rộng dựa trên spacing
        margin_pixels_x = int(round(margin_mm / self.spacing[0]))
        margin_pixels_y = int(round(margin_mm / self.spacing[1]))
        margin_pixels_z = int(round(margin_mm / self.spacing[2]))
        
        # Mở rộng trên mỗi slice axial
        for slice_idx, contour_points in self.contours[source_name].get('axial', {}).items():
            if not contour_points or len(contour_points) == 0:
                continue
            
            # Tạo mask từ contour
            shape = self.image_data.shape[1:] if self.image_data.ndim == 3 else self.image_data.shape
            mask = np.zeros(shape, dtype=np.uint8)
            
            # Vẽ contour lên mask
            contour = np.array(contour_points, dtype=np.int32)
            cv2.fillPoly(mask, [contour], 1)
            
            # Áp dụng phép giãn nở
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2*margin_pixels_x+1, 2*margin_pixels_y+1))
            dilated_mask = cv2.dilate(mask, kernel, iterations=1)
            
            # Tìm contour mới từ mask đã giãn nở
            contours, _ = cv2.findContours(dilated_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Thêm contour mới vào cấu trúc đích
            for contour in contours:
                contour = contour.reshape(-1, 2).tolist()
                self.add_contour_points(slice_idx, contour, 'axial')
        
        # Mở rộng theo trục Z bằng cách sao chép contour vào các slice lân cận
        axial_slices = sorted(list(self.contours[source_name].get('axial', {}).keys()))
        
        # Tạo danh sách các slice mới cần thêm
        new_slices = []
        for slice_idx in axial_slices:
            for offset in range(1, margin_pixels_z + 1):
                if slice_idx + offset not in axial_slices:
                    new_slices.append((slice_idx, slice_idx + offset))
                if slice_idx - offset not in axial_slices:
                    new_slices.append((slice_idx, slice_idx - offset))
        
        # Thêm contour vào các slice mới
        for original_slice, new_slice in new_slices:
            if 0 <= new_slice < self.image_data.shape[0]:  # Kiểm tra slice mới có nằm trong phạm vi không
                points = self.get_contour_points(source_name, original_slice, 'axial')
                if points and len(points) > 0:
                    self.add_contour_points(new_slice, points, 'axial')
        
        print(f"Đã mở rộng cấu trúc '{source_name}' thành '{target_name}' với lề {margin_mm}mm")
        return True