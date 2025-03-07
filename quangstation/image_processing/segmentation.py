import numpy as np
import cv2
import matplotlib.pyplot as plt
from skimage import measure, morphology, segmentation

class Segmentation:
    """Cung cấp công cụ phân vùng tự động và thủ công cho ảnh y tế"""
    
    def __init__(self, image_data):
        self.image_data = image_data
        self.masks = {}  # Dictionary lưu trữ các mask với tên là key
        
    def create_empty_mask(self, shape=None):
        """Tạo mask trống"""
        if shape is None:
            shape = self.image_data.shape
        return np.zeros(shape, dtype=np.uint8)
    
    def add_mask(self, name, mask=None):
        """Thêm một mask mới"""
        if mask is None:
            mask = self.create_empty_mask()
        self.masks[name] = mask
        return mask
    
    def get_mask(self, name):
        """Lấy mask theo tên"""
        return self.masks.get(name, None)
    
    def threshold_segmentation(self, name, slice_index, axis='axial', min_value=None, max_value=None):
        """Phân vùng theo ngưỡng"""
        if axis == 'axial':
            slice_data = self.image_data[slice_index, :, :]
        elif axis == 'coronal':
            slice_data = self.image_data[:, slice_index, :]
        elif axis == 'sagittal':
            slice_data = self.image_data[:, :, slice_index]
        else:
            raise ValueError(f"Trục không hợp lệ: {axis}")
        
        # Phân vùng theo ngưỡng
        mask = np.zeros_like(slice_data, dtype=np.uint8)
        if min_value is not None and max_value is not None:
            mask = np.logical_and(slice_data >= min_value, slice_data <= max_value)
        elif min_value is not None:
            mask = slice_data >= min_value
        elif max_value is not None:
            mask = slice_data <= max_value
        
        mask = mask.astype(np.uint8) * 255
        
        # Thêm vào dictionary nếu chưa tồn tại
        if name not in self.masks:
            self.masks[name] = np.zeros_like(self.image_data, dtype=np.uint8)
        
        # Cập nhật mask cho lát cắt
        if axis == 'axial':
            self.masks[name][slice_index, :, :] = mask
        elif axis == 'coronal':
            self.masks[name][:, slice_index, :] = mask
        elif axis == 'sagittal':
            self.masks[name][:, :, slice_index] = mask
        
        return mask
    
    def manual_contour(self, name, slice_index, points, axis='axial'):
        """Tạo contour thủ công từ danh sách điểm"""
        # Tạo mask cho lát cắt hiện tại
        if axis == 'axial':
            slice_shape = self.image_data[slice_index, :, :].shape
        elif axis == 'coronal':
            slice_shape = self.image_data[:, slice_index, :].shape
        elif axis == 'sagittal':
            slice_shape = self.image_data[:, :, slice_index].shape
        else:
            raise ValueError(f"Trục không hợp lệ: {axis}")
        
        # Chuyển đổi points thành mảng np
        points = np.array(points, dtype=np.int32)
        
        # Tạo mask trống
        slice_mask = np.zeros(slice_shape, dtype=np.uint8)
        
        # Vẽ contour và fill
        cv2.fillPoly(slice_mask, [points], 255)
        
        # Thêm vào dictionary nếu chưa tồn tại
        if name not in self.masks:
            self.masks[name] = np.zeros_like(self.image_data, dtype=np.uint8)
        
        # Cập nhật mask cho lát cắt
        if axis == 'axial':
            self.masks[name][slice_index, :, :] = slice_mask
        elif axis == 'coronal':
            self.masks[name][:, slice_index, :] = slice_mask
        elif axis == 'sagittal':
            self.masks[name][:, :, slice_index] = slice_mask
        
        return slice_mask
    
    def auto_contour_body(self, name, threshold=-300):
        """Phân vùng tự động cho body contour"""
        # Tạo mask mới
        body_mask = np.zeros_like(self.image_data, dtype=np.uint8)
        
        # Duyệt qua các lát cắt axial
        for i in range(self.image_data.shape[0]):
            # Áp dụng ngưỡng
            slice_data = self.image_data[i, :, :]
            thresh = (slice_data > threshold).astype(np.uint8) * 255
            
            # Tìm contour lớn nhất (body)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                # Lấy contour lớn nhất
                max_contour = max(contours, key=cv2.contourArea)
                
                # Tạo mask cho contour này
                slice_mask = np.zeros_like(thresh)
                cv2.drawContours(slice_mask, [max_contour], 0, 255, -1)
                
                # Fill các lỗ bên trong
                slice_mask = morphology.remove_small_holes(slice_mask.astype(bool), area_threshold=1000)
                
                # Lưu vào mask tổng
                body_mask[i, :, :] = slice_mask.astype(np.uint8) * 255
        
        # Lưu mask
        self.masks[name] = body_mask
        
        return body_mask
    
    def extract_contour_points(self, name, slice_index, axis='axial'):
        """Trích xuất điểm contour từ mask"""
        # Lấy mask cho lát cắt
        if axis == 'axial':
            slice_mask = self.masks[name][slice_index, :, :]
        elif axis == 'coronal':
            slice_mask = self.masks[name][:, slice_index, :]
        elif axis == 'sagittal':
            slice_mask = self.masks[name][:, :, slice_index]
        else:
            raise ValueError(f"Trục không hợp lệ: {axis}")
        
        # Tìm contours
        contours, _ = cv2.findContours(slice_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Trả về list các contour points
        return [contour.reshape(-1, 2).tolist() for contour in contours]
    
    def get_volume_cm3(self, name, voxel_spacing):
        """Tính thể tích cấu trúc trong cm3"""
        if name not in self.masks:
            return 0
        
        # Tính số voxel
        voxel_count = np.sum(self.masks[name] > 0)
        
        # Tính thể tích (cm3)
        voxel_volume = voxel_spacing[0] * voxel_spacing[1] * voxel_spacing[2] / 1000  # mm3 to cm3
        return voxel_count * voxel_volume
    
    def export_contours_as_rt_struct(self, output_file, patient_info, img_origin, img_spacing):
        """Xuất contours sang định dạng DICOM RT Struct"""
        # Đoạn mã này sẽ yêu cầu thư viện pydicom để tạo file RT Struct
        # Chi tiết cài đặt sẽ thêm sau nếu cần thiết
        pass