import numpy as np
import cv2
import matplotlib.pyplot as plt
from skimage import measure, morphology, segmentation, filters, feature
from scipy import ndimage
from typing import Dict, List, Tuple, Optional, Union, Any
import os
from datetime import datetime

from quangstation.core.utils.external_integration import get_module
from quangstation.core.utils.logging import get_logger
from quangstation.clinical.contouring.contour_tools import ContourTools

"""
Module này cung cấp công cụ phân vùng tự động và thủ công cho ảnh y tế.
Hỗ trợ nhiều thuật toán phân đoạn và tích hợp với ContourTools.
"""
logger = get_logger("Segmentation")

# Lấy module pydicom từ external_integration
pydicom = get_module("pydicom")
if not pydicom:
    logger.error("Không thể import pydicom. Nhiều chức năng sẽ không hoạt động.")

class Segmentation:
    """
    Cung cấp công cụ phân vùng tự động và thủ công cho ảnh y tế.
    Hỗ trợ nhiều thuật toán phân đoạn và tích hợp với ContourTools.
    """
    
    def __init__(self, image_data, spacing=(1.0, 1.0, 1.0), origin=(0.0, 0.0, 0.0), direction=(1,0,0,0,1,0,0,0,1)):
        """
        Khởi tạo lớp Segmentation.
        
        Args:
            image_data: Dữ liệu ảnh 3D (numpy array)
            spacing: Khoảng cách giữa các pixel (mm)
            origin: Điểm gốc của ảnh (mm)
            direction: Ma trận hướng
        """
        self.image_data = image_data
        self.spacing = spacing
        self.origin = origin
        self.direction = direction
        self.masks = {}  # Dictionary lưu trữ các mask với tên là key
        self.slice_positions = []  # Vị trí z của các slice
        self.reference_frame_uid = None  # UID của frame tham chiếu
        self.patient_info = {}  # Thông tin bệnh nhân
        
        # Tính vị trí z của các slice
        for i in range(image_data.shape[0]):
            z_pos = origin[2] + i * spacing[2]
            self.slice_positions.append(z_pos)
            
        logger.info(f"Khởi tạo Segmentation với ảnh kích thước {image_data.shape}")
    
    def create_empty_mask(self, shape=None):
        """
        Tạo mask trống.
        
        Args:
            shape: Kích thước mask, mặc định là kích thước ảnh
            
        Returns:
            np.ndarray: Mask trống
        """
        if shape is None:
            shape = self.image_data.shape
        return np.zeros(shape, dtype=np.uint8)
    
    def add_mask(self, name, mask=None):
        """
        Thêm một mask mới.
        
        Args:
            name: Tên mask
            mask: Dữ liệu mask, mặc định là mask trống
            
        Returns:
            np.ndarray: Mask đã thêm
        """
        if mask is None:
            mask = self.create_empty_mask()
        self.masks[name] = mask
        logger.info(f"Đã thêm mask '{name}'")
        return mask
    
    def get_mask(self, name):
        """
        Lấy mask theo tên.
        
        Args:
            name: Tên mask
            
        Returns:
            np.ndarray: Mask nếu tồn tại, None nếu không
        """
        return self.masks.get(name, None)
    
    def threshold_segmentation(self, name, slice_index=None, axis='axial', min_value=None, max_value=None):
        """
        Phân vùng theo ngưỡng.
        
        Args:
            name: Tên mask
            slice_index: Chỉ số lát cắt, None để xử lý toàn bộ thể tích
            axis: Trục lát cắt ('axial', 'coronal', 'sagittal')
            min_value: Giá trị ngưỡng dưới
            max_value: Giá trị ngưỡng trên
            
        Returns:
            np.ndarray: Mask sau khi phân vùng
        """
        # Xử lý toàn bộ thể tích
        if slice_index is None:
            mask = np.zeros_like(self.image_data, dtype=np.uint8)
            
            # Phân vùng theo ngưỡng
            if min_value is not None and max_value is not None:
                mask = np.logical_and(self.image_data >= min_value, self.image_data <= max_value)
            elif min_value is not None:
                mask = self.image_data >= min_value
            elif max_value is not None:
                mask = self.image_data <= max_value
            
            # Chuyển về kiểu uint8
            mask = mask.astype(np.uint8) * 255
            
            # Lưu mask
            self.masks[name] = mask
            logger.info(f"Đã tạo mask '{name}' với ngưỡng min={min_value}, max={max_value}")
            return mask
        
        # Xử lý một lát cắt
        if axis == 'axial':
            slice_data = self.image_data[slice_index, :, :]
        elif axis == 'coronal':
            slice_data = self.image_data[:, slice_index, :]
        elif axis == 'sagittal':
            slice_data = self.image_data[:, :, slice_index]
        else:
            raise ValueError(f"Trục không hợp lệ: {axis}")
        
        # Phân vùng theo ngưỡng
        slice_mask = np.zeros_like(slice_data, dtype=np.uint8)
        if min_value is not None and max_value is not None:
            slice_mask = np.logical_and(slice_data >= min_value, slice_data <= max_value)
        elif min_value is not None:
            slice_mask = slice_data >= min_value
        elif max_value is not None:
            slice_mask = slice_data <= max_value
        
        slice_mask = slice_mask.astype(np.uint8) * 255
        
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
        
        logger.info(f"Đã cập nhật mask '{name}' tại slice {slice_index} (axis={axis})")
        return slice_mask
    
    def manual_contour(self, name, slice_index, points, axis='axial'):
        """
        Tạo contour thủ công từ danh sách điểm.
        
        Args:
            name: Tên mask
            slice_index: Chỉ số lát cắt
            points: Danh sách các điểm [(x1,y1), (x2,y2), ...]
            axis: Trục lát cắt ('axial', 'coronal', 'sagittal')
            
        Returns:
            np.ndarray: Mask cho lát cắt đã xử lý
        """
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
        
        logger.info(f"Đã vẽ contour thủ công cho mask '{name}' tại slice {slice_index} (axis={axis})")
        return slice_mask
    
    def auto_contour_body(self, name="BODY", threshold=-300, add_margin_mm=None):
        """
        Phân vùng tự động cho body contour.
        
        Args:
            name: Tên mask
            threshold: Ngưỡng HU để phân biệt tissue với không khí
            add_margin_mm: Lề thêm vào bên ngoài contour (mm)
            
        Returns:
            np.ndarray: Mask body
        """
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
                slice_mask = slice_mask.astype(np.uint8) * 255
                
                # Thêm lề nếu cần
                if add_margin_mm is not None and add_margin_mm > 0:
                    # Chuyển từ mm sang pixel
                    margin_x = int(round(add_margin_mm / self.spacing[0]))
                    margin_y = int(round(add_margin_mm / self.spacing[1]))
                    
                    # Áp dụng phép giãn nở
                    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2*margin_x+1, 2*margin_y+1))
                    slice_mask = cv2.dilate(slice_mask, kernel, iterations=1)
                
                # Lưu vào mask tổng
                body_mask[i, :, :] = slice_mask
        
        # Lưu mask
        self.masks[name] = body_mask
        
        logger.info(f"Đã tạo body contour '{name}' với ngưỡng {threshold} HU")
        if add_margin_mm is not None:
            logger.info(f"Đã thêm lề {add_margin_mm} mm cho body contour")
            
        return body_mask
    
    def auto_segment_lungs(self, name="LUNGS", threshold=-400, remove_trachea=True, fill_vessels=True):
        """
        Phân đoạn tự động phổi trên CT.
        
        Args:
            name: Tên mask
            threshold: Ngưỡng HU để phân biệt phổi (-400 đến -600 thường phù hợp)
            remove_trachea: Loại bỏ trachea tự động
            fill_vessels: Điền các mạch máu trong phổi
            
        Returns:
            np.ndarray: Mask phổi
        """
        # Tạo mask mới
        lung_mask = np.zeros_like(self.image_data, dtype=np.uint8)
        
        # Xử lý từng lát cắt
        for i in range(self.image_data.shape[0]):
            # Lấy lát cắt
            slice_data = self.image_data[i, :, :]
            
            # Áp dụng ngưỡng ban đầu
            thresh = (slice_data < threshold).astype(np.uint8) * 255
            
            # Làm sạch nhiễu
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
            
            # Lấy các connected component
            labels = measure.label(thresh)
            props = measure.regionprops(labels)
            
            # Lọc các thành phần quá nhỏ
            for prop in props:
                if prop.area < 100:  # vùng quá nhỏ
                    labels[labels == prop.label] = 0
            
            # Chuyển lại thành binary mask
            thresh = (labels > 0).astype(np.uint8) * 255
            
            # Loại bỏ các thành phần chạm biên (nếu yêu cầu loại bỏ trachea)
            if remove_trachea:
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for contour in contours:
                    # Kiểm tra xem contour có chạm biên trên không
                    x, y, w, h = cv2.boundingRect(contour)
                    if y <= 1:  # chạm biên trên
                        cv2.drawContours(thresh, [contour], 0, 0, -1)
            
            # Lọc lại chỉ giữ 2 thành phần lớn nhất (phổi trái và phải)
            labels = measure.label(thresh)
            regions = measure.regionprops(labels)
            
            # Sắp xếp theo kích thước và lấy 2 vùng lớn nhất
            if len(regions) > 2:
                sorted_regions = sorted(regions, key=lambda x: x.area, reverse=True)
                lung_mask_slice = np.zeros_like(thresh)
                
                # Lấy 2 region lớn nhất
                for j in range(min(2, len(sorted_regions))):
                    lung_mask_slice[labels == sorted_regions[j].label] = 255
                
                thresh = lung_mask_slice
            
            # Điền các lỗ trong phổi (mạch máu)
            if fill_vessels:
                thresh = morphology.remove_small_holes(thresh.astype(bool), area_threshold=500)
                thresh = thresh.astype(np.uint8) * 255
            
            # Lưu vào mask tổng
            lung_mask[i, :, :] = thresh
        
        # Lưu mask
        self.masks[name] = lung_mask
        
        logger.info(f"Đã tạo lung contour '{name}' với ngưỡng {threshold} HU")
        return lung_mask
    
    def auto_segment_bones(self, name="BONES", threshold=300):
        """
        Phân đoạn tự động xương trên CT.
        
        Args:
            name: Tên mask
            threshold: Ngưỡng HU để phân biệt xương (thường 300+)
            
        Returns:
            np.ndarray: Mask xương
        """
        # Phân đoạn dựa vào ngưỡng
        bone_mask = (self.image_data > threshold).astype(np.uint8) * 255
        
        # Làm sạch nhiễu
        for i in range(bone_mask.shape[0]):
            # Mở morphology để loại bỏ nhiễu nhỏ
            bone_mask[i] = cv2.morphologyEx(bone_mask[i], cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        
        # Lưu mask
        self.masks[name] = bone_mask
        
        logger.info(f"Đã tạo bone contour '{name}' với ngưỡng {threshold} HU")
        return bone_mask
    
    def region_growing(self, name, start_points, threshold_min=None, threshold_max=None):
        """
        Thuật toán region growing từ một hoặc nhiều điểm.
        
        Args:
            name: Tên mask
            start_points: Danh sách các điểm xuất phát [(z1,y1,x1), (z2,y2,x2), ...]
            threshold_min: Ngưỡng dưới
            threshold_max: Ngưỡng trên
            
        Returns:
            np.ndarray: Mask sau khi region growing
        """
        # Tạo mask trống
        mask = np.zeros_like(self.image_data, dtype=np.uint8)
        
        # Lấy intensity tại các điểm xuất phát
        intensities = [self.image_data[z, y, x] for z, y, x in start_points]
        avg_intensity = np.mean(intensities)
        
        # Nếu không có ngưỡng, lấy ngưỡng tự động
        if threshold_min is None:
            threshold_min = avg_intensity - 100
        if threshold_max is None:
            threshold_max = avg_intensity + 100
        
        # Tạo mask ban đầu dựa vào ngưỡng
        thresh_mask = np.logical_and(
            self.image_data >= threshold_min,
            self.image_data <= threshold_max
        ).astype(np.uint8)
        
        # Thực hiện region growing với từng điểm xuất phát
        for z, y, x in start_points:
            # Tạo mask kết quả cho điểm này
            point_mask = np.zeros_like(self.image_data, dtype=np.uint8)
            
            # Đảm bảo điểm xuất phát nằm trong ngưỡng
            if thresh_mask[z, y, x] == 0:
                continue
                
            # Sử dụng binary_fill_holes để tìm connected region
            # Tạo mask ảnh nhị phân từ thresholded image
            mask_slice = thresh_mask[z].copy()
            
            # Đánh dấu seed point
            seed_mask = np.zeros_like(mask_slice, dtype=np.uint8)
            seed_mask[y, x] = 1
            
            # Sử dụng label để tìm connected component chứa seed
            labels, num = ndimage.label(mask_slice, structure=np.ones((3, 3)))
            if labels[y, x] > 0:
                component = (labels == labels[y, x])
                point_mask[z] = component.astype(np.uint8)
                
            # Kết hợp với kết quả
            mask = np.logical_or(mask, point_mask).astype(np.uint8)
        
        # Làm sạch kết quả
        mask = mask * 255
        
        # Lưu mask
        self.masks[name] = mask
        
        logger.info(f"Đã tạo mask '{name}' bằng region growing từ {len(start_points)} điểm")
        return mask
    
    def watershed_segmentation(self, name, slice_index, markers=None, axis='axial'):
        """
        Phân đoạn bằng thuật toán watershed.
        
        Args:
            name: Tên mask
            slice_index: Chỉ số lát cắt
            markers: Markers cho watershed (None để tạo tự động)
            axis: Trục lát cắt ('axial', 'coronal', 'sagittal')
            
        Returns:
            np.ndarray: Mask sau khi phân đoạn
        """
        # Lấy lát cắt
        if axis == 'axial':
            slice_data = self.image_data[slice_index, :, :]
        elif axis == 'coronal':
            slice_data = self.image_data[:, slice_index, :]
        elif axis == 'sagittal':
            slice_data = self.image_data[:, :, slice_index]
        else:
            raise ValueError(f"Trục không hợp lệ: {axis}")
            
        # Chuẩn hóa ảnh về khoảng [0, 1]
        normalized = (slice_data - np.min(slice_data)) / (np.max(slice_data) - np.min(slice_data))
        
        # Tính gradient
        gradient = filters.sobel(normalized)
        
        # Nếu không có markers, tạo markers tự động
        if markers is None:
            # Tạo markers từ các vùng cực tiểu
            markers = feature.peak_local_max(
                -gradient, 
                min_distance=20, 
                indices=False
            )
            
            # Label các markers
            markers = measure.label(markers)
            
        # Thực hiện watershed
        labels = segmentation.watershed(gradient, markers, mask=normalized > 0)
        
        # Tạo mask từ kết quả watershed
        result_mask = np.zeros_like(slice_data, dtype=np.uint8)
        
        # Hiển thị các vùng watershed khác nhau
        for label_id in range(1, labels.max() + 1):
            result_mask[labels == label_id] = 255
        
        # Thêm vào dictionary nếu chưa tồn tại
        if name not in self.masks:
            self.masks[name] = np.zeros_like(self.image_data, dtype=np.uint8)
        
        # Cập nhật mask cho lát cắt
        if axis == 'axial':
            self.masks[name][slice_index, :, :] = result_mask
        elif axis == 'coronal':
            self.masks[name][:, slice_index, :] = result_mask
        elif axis == 'sagittal':
            self.masks[name][:, :, slice_index] = result_mask
        
        logger.info(f"Đã tạo mask '{name}' bằng watershed tại slice {slice_index} (axis={axis})")
        return result_mask
    
    def extract_contour_points(self, name, slice_index, axis='axial'):
        """
        Trích xuất điểm contour từ mask.
        
        Args:
            name: Tên mask
            slice_index: Chỉ số lát cắt
            axis: Trục lát cắt ('axial', 'coronal', 'sagittal')
            
        Returns:
            List[List[Tuple[int, int]]]: Danh sách các contour points
        """
        # Kiểm tra mask tồn tại
        if name not in self.masks:
            logger.warning(f"Mask '{name}' không tồn tại")
            return []
            
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
    
    def get_volume_cm3(self, name, apply_spacing=True):
        """
        Tính thể tích cấu trúc trong cm3.
        
        Args:
            name: Tên mask
            apply_spacing: Áp dụng spacing khi tính thể tích
            
        Returns:
            float: Thể tích (cm3)
        """
        if name not in self.masks:
            logger.warning(f"Mask '{name}' không tồn tại")
            return 0
        
        # Tính số voxel
        voxel_count = np.sum(self.masks[name] > 0)
        
        if not apply_spacing:
            # Trả về số voxel nếu không apply spacing
            return voxel_count / 1000  # Chia cho 1000 để có đơn vị cm3 gần đúng
        
        # Tính thể tích (cm3)
        voxel_volume = self.spacing[0] * self.spacing[1] * self.spacing[2] / 1000  # mm3 to cm3
        return voxel_count * voxel_volume
    
    def export_to_contour_tools(self, color_dict=None):
        """
        Chuyển đổi masks thành ContourTools để xuất RT Structure.
        
        Args:
            color_dict: Dictionary ánh xạ tên cấu trúc sang màu sắc
            
        Returns:
            ContourTools: Đối tượng ContourTools chứa các contour từ masks
        """
        # Khởi tạo ContourTools
        contour_tools = ContourTools(
            self.image_data, 
            self.spacing, 
            self.origin, 
            self.direction
        )
        
        # Thiết lập thông tin tham chiếu
        if self.reference_frame_uid:
            contour_tools.set_reference_data(self.reference_frame_uid, self.slice_positions)
            
        # Thiết lập thông tin bệnh nhân
        if self.patient_info:
            contour_tools.set_patient_info(self.patient_info)
            
        # Chuyển đổi từng mask thành contour
        for name, mask in self.masks.items():
            # Tạo màu sắc mặc định
            color = None
            if color_dict and name in color_dict:
                color = color_dict[name]
                
            # Thêm cấu trúc mới
            contour_tools.add_structure(name, color)
            
            # Xử lý từng slice
            for slice_idx in range(mask.shape[0]):
                slice_mask = mask[slice_idx]
                
                # Bỏ qua các slice không có mask
                if np.sum(slice_mask) == 0:
                    continue
                    
                # Trích xuất contour
                contours, _ = cv2.findContours(slice_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                # Thêm contour lớn nhất vào ContourTools
                if contours:
                    # Chọn contour lớn nhất
                    max_contour = max(contours, key=cv2.contourArea)
                    points = max_contour.reshape(-1, 2).tolist()
                    
                    # Thêm vào ContourTools
                    contour_tools.add_contour_points(slice_idx, points)
        
        logger.info(f"Đã chuyển {len(self.masks)} mask sang ContourTools")
        return contour_tools
    
    def set_patient_info(self, patient_info):
        """
        Thiết lập thông tin bệnh nhân.
        
        Args:
            patient_info: Dictionary chứa thông tin bệnh nhân
        """
        self.patient_info = patient_info
        logger.info("Đã cập nhật thông tin bệnh nhân")
    
    def set_reference_frame_uid(self, uid):
        """
        Thiết lập UID của frame tham chiếu.
        
        Args:
            uid: UID của frame tham chiếu
        """
        self.reference_frame_uid = uid
        logger.info(f"Đã thiết lập reference frame UID: {uid}")
    
    def export_contours_as_rt_struct(self, output_file, reference_dicom=None):
        """
        Xuất contours sang định dạng DICOM RT Struct.
        
        Args:
            output_file: Đường dẫn đến file RT Struct xuất ra
            reference_dicom: Đường dẫn đến file DICOM tham chiếu (optional)
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            # Chuyển đổi sang ContourTools
            contour_tools = self.export_to_contour_tools()
            
            # Xuất sang DICOM RT Structure
            result = contour_tools.save_to_dicom_rtstruct(output_file, reference_dicom)
            
            if result:
                logger.info(f"Đã lưu RT Structure thành công vào: {output_file}")
            else:
                logger.error(f"Lỗi khi lưu RT Structure")
                
            return result
            
        except Exception as error:
            import traceback
            logger.error(f"Lỗi khi xuất RT Structure: {str(error)}")
            logger.error(traceback.format_exc())
            return False