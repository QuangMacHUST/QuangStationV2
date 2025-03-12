import numpy as np
import cv2  
import matplotlib.pyplot as plt
from matplotlib.path import Path
from typing import Dict, List, Tuple, Optional, Union, Any
from quangstation.core.utils.logging import get_logger
import pydicom
import os
from datetime import datetime

# Disable pylint errors for OpenCV functions
# pylint: disable=no-member
"""
Module này cung cấp công cụ để vẽ và chỉnh sửa contour.
Hỗ trợ tạo và lưu DICOM RT-STRUCT.
"""
logger = get_logger("Contouring")

class ContourTools:
    """
    Cung cấp công cụ để vẽ và chỉnh sửa contour.
    Hỗ trợ tạo và lưu DICOM RT-STRUCT.
    """
    
    def __init__(self, image_data, spacing=(1.0, 1.0, 1.0), origin=(0.0, 0.0, 0.0), direction=(1,0,0,0,1,0,0,0,1)):
        """
        Khởi tạo ContourTools với dữ liệu ảnh và thông tin không gian.
        
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
        self.contours = {}  # Dictionary lưu các contour của các cấu trúc
        self.colors = {}    # Dictionary lưu màu sắc cho các cấu trúc
        self.current_struct = None
        self.isocenter = None
        self.modified = False  # Flag đánh dấu có thay đổi chưa lưu
        self.reference_frame_uid = None  # UID của frame tham chiếu
        self.reference_slice_positions = []  # Vị trí các slice tham chiếu
        self.patient_info = {}  # Thông tin bệnh nhân
        
        # Màu mặc định cho các cấu trúc phổ biến
        self.default_colors = {
            "BODY": (1.0, 1.0, 0.0),      # Yellow
            "PTV": (1.0, 0.0, 0.0),       # Red
            "CTV": (1.0, 0.5, 0.0),       # Orange
            "GTV": (1.0, 0.0, 1.0),       # Magenta
            "RECTUM": (0.5, 0.0, 0.5),    # Purple
            "BLADDER": (1.0, 1.0, 0.0),   # Yellow
            "HEART": (1.0, 0.0, 0.0),     # Red
            "LUNG": (0.0, 0.5, 1.0),      # Light blue
            "SPINAL CORD": (1.0, 1.0, 0.0),  # Yellow
            "BRAIN": (0.5, 0.5, 0.5),     # Gray
            "EYES": (0.0, 1.0, 1.0),      # Cyan
            "PAROTID": (0.0, 1.0, 0.0),   # Green
            "MANDIBLE": (0.5, 0.25, 0.0), # Brown
        }
        
        logger.info(f"ContourTools được khởi tạo với dữ liệu ảnh kích thước {image_data.shape}")
    
    def add_structure(self, name: str, color: Optional[Tuple[float, float, float]] = None):
        """
        Thêm một cấu trúc mới.
        
        Args:
            name: Tên cấu trúc
            color: Màu sắc (R, G, B) trong khoảng [0, 1]
            
        Returns:
            bool: True nếu thành công, False nếu cấu trúc đã tồn tại
        """
        if name in self.contours:
            logger.warning(f"Cấu trúc '{name}' đã tồn tại")
            return False
            
        self.contours[name] = {}  # Dictionary lưu contour theo slice {slice_idx: points}
        
        # Gán màu mặc định nếu không cung cấp
        if color is None:
            # Nếu là cấu trúc phổ biến, sử dụng màu mặc định
            upper_name = name.upper()
            for default_name, default_color in self.default_colors.items():
                if default_name in upper_name:
                    color = default_color
                    break
            
            # Nếu vẫn không tìm thấy, tạo màu ngẫu nhiên
            if color is None:
                import random
                color = (random.random(), random.random(), random.random())
        
        self.colors[name] = color
        self.current_struct = name
        self.modified = True
        
        logger.info(f"Đã thêm cấu trúc mới: {name} với màu {color}")
        return True
    
    def set_current_structure(self, name: str):
        """
        Thiết lập cấu trúc hiện tại để chỉnh sửa.
        
        Args:
            name: Tên cấu trúc
            
        Returns:
            bool: True nếu thành công, False nếu cấu trúc không tồn tại
        """
        if name not in self.contours:
            logger.warning(f"Cấu trúc '{name}' không tồn tại")
            return False
            
        self.current_struct = name
        logger.info(f"Đã chọn cấu trúc: {name}")
        return True
    
    def remove_structure(self, name: str):
        """
        Xóa một cấu trúc.
        
        Args:
            name: Tên cấu trúc cần xóa
            
        Returns:
            bool: True nếu thành công, False nếu cấu trúc không tồn tại
        """
        if name not in self.contours:
            logger.warning(f"Cấu trúc '{name}' không tồn tại")
            return False
            
        del self.contours[name]
        if name in self.colors:
            del self.colors[name]
            
        if self.current_struct == name:
            self.current_struct = next(iter(self.contours)) if self.contours else None
            
        self.modified = True
        logger.info(f"Đã xóa cấu trúc: {name}")
        return True
    
    def add_contour_points(self, slice_idx: int, points: List[Tuple[float, float]], is_closed: bool = True):
        """
        Thêm các điểm contour vào một slice của cấu trúc hiện tại.
        
        Args:
            slice_idx: Chỉ số slice
            points: Danh sách các điểm (x, y) trong tọa độ pixel
            is_closed: Nếu True, đảm bảo contour đóng kín bằng cách thêm điểm đầu tiên vào cuối
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        if self.current_struct is None:
            logger.error("Chưa chọn cấu trúc hiện tại")
            return False
            
        if not points or len(points) < 3:
            logger.warning("Cần ít nhất 3 điểm để tạo contour")
            return False
        
        # Tạo bản sao để không thay đổi dữ liệu đầu vào
        points_copy = list(points)
        
        # Đảm bảo điểm đầu và cuối giống nhau (contour đóng)
        if is_closed and points_copy[0] != points_copy[-1]:
            points_copy.append(points_copy[0])
            
        # Kiểm tra xem slice đã có contour hay chưa
        if slice_idx not in self.contours[self.current_struct]:
            # Slice chưa có contour, tạo mới
            self.contours[self.current_struct][slice_idx] = points_copy
        else:
            # Slice đã có contour, chuyển đổi thành danh sách contour nếu cần
            existing = self.contours[self.current_struct][slice_idx]
            
            # Kiểm tra nếu existing đã là danh sách các contour
            if existing and isinstance(existing[0], list):
                # Đã là danh sách các contour, thêm contour mới
                existing.append(points_copy)
            else:
                # Chuyển từ contour đơn sang danh sách contour
                self.contours[self.current_struct][slice_idx] = [existing, points_copy]
                
        self.modified = True
        
        logger.info(f"Đã thêm contour ({len(points_copy)} điểm) cho cấu trúc '{self.current_struct}' tại slice {slice_idx}")
        return True
    
    def remove_contour_from_slice(self, name: str, slice_idx: int):
        """
        Xóa contour tại một slice của cấu trúc chỉ định.
        
        Args:
            name: Tên cấu trúc
            slice_idx: Chỉ số slice
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        if name not in self.contours:
            logger.warning(f"Cấu trúc '{name}' không tồn tại")
            return False
            
        if slice_idx not in self.contours[name]:
            logger.warning(f"Không có contour tại slice {slice_idx} của cấu trúc '{name}'")
            return False
            
        del self.contours[name][slice_idx]
        self.modified = True
        
        logger.info(f"Đã xóa contour tại slice {slice_idx} của cấu trúc '{name}'")
        return True
    
    def get_structure_color(self, name: str) -> Optional[Tuple[float, float, float]]:
        """
        Lấy màu sắc của một cấu trúc.
        
        Args:
            name: Tên cấu trúc
            
        Returns:
            Tuple[float, float, float]: Màu sắc (R, G, B) trong khoảng [0, 1]
        """
        if name not in self.colors:
            return None
            
        return self.colors[name]
    
    def set_structure_color(self, name: str, color: Tuple[float, float, float]):
        """
        Thiết lập màu sắc cho một cấu trúc.
        
        Args:
            name: Tên cấu trúc
            color: Màu sắc (R, G, B) trong khoảng [0, 1]
            
        Returns:
            bool: True nếu thành công, False nếu cấu trúc không tồn tại
        """
        if name not in self.contours:
            logger.warning(f"Cấu trúc '{name}' không tồn tại")
            return False
            
        self.colors[name] = color
        self.modified = True
        
        logger.info(f"Đã thiết lập màu {color} cho cấu trúc '{name}'")
        return True
    
    def get_structure_mask(self, name: str) -> Optional[np.ndarray]:
        """
        Tạo mặt nạ 3D của một cấu trúc.
        
        Args:
            name: Tên cấu trúc
            
        Returns:
            np.ndarray: Mặt nạ 3D với giá trị 1 bên trong contour, 0 bên ngoài
        """
        if name not in self.contours or not self.contours[name]:
            logger.warning(f"Cấu trúc '{name}' không tồn tại hoặc không có contour")
            return None
            
        # Khởi tạo mặt nạ trống
        mask = np.zeros(self.image_data.shape, dtype=np.uint8)
        
        # Điền contour cho từng slice
        for slice_idx, points_list in self.contours[name].items():
            if slice_idx < 0 or slice_idx >= self.image_data.shape[0]:
                logger.warning(f"Bỏ qua slice {slice_idx} nằm ngoài phạm vi hình ảnh")
                continue
                
            # Kiểm tra nếu points là danh sách contour hoặc contour đơn
            if not points_list:
                continue
                
            # Kiểm tra xem points_list có phải là danh sách các contour hay không
            is_multiple_contours = False
            if isinstance(points_list[0], list) or isinstance(points_list[0], tuple):
                if len(points_list) > 0 and isinstance(points_list[0], tuple) and len(points_list[0]) == 2:
                    # Đây là một contour đơn (danh sách các điểm)
                    contours_to_fill = [np.array(points_list, dtype=np.int32)]
                else:
                    # Đây là danh sách các contour
                    is_multiple_contours = True
                    contours_to_fill = [np.array(contour, dtype=np.int32) for contour in points_list]
            else:
                logger.warning(f"Định dạng contour không hợp lệ cho slice {slice_idx} của cấu trúc {name}")
                continue
            
            # Tạo slice mask cho slice hiện tại
            slice_mask = np.zeros((self.image_data.shape[1], self.image_data.shape[2]), dtype=np.uint8)
            
            # Điền contour vào slice mask
            for contour_points in contours_to_fill:
                if len(contour_points) < 3:  # Cần ít nhất 3 điểm để tạo đa giác
                    continue
                    
                # Đảm bảo contour đóng kín
                if not np.array_equal(contour_points[0], contour_points[-1]):
                    contour_points = np.vstack([contour_points, contour_points[0]])
                
                # Kiểm tra điểm nằm trong giới hạn ảnh
                valid_points = []
                for point in contour_points:
                    x, y = point[0], point[1]
                    if 0 <= x < self.image_data.shape[2] and 0 <= y < self.image_data.shape[1]:
                        valid_points.append([x, y])
                
                if len(valid_points) >= 3:  # Cần ít nhất 3 điểm hợp lệ
                    # Sử dụng fillPoly để điền đa giác
                    cv2.fillPoly(slice_mask, [np.array(valid_points, dtype=np.int32)], 1)
            
            # Gán vào mặt nạ 3D
            mask[slice_idx] = slice_mask
            
        return mask
    
    def calculate_volume(self, name: str) -> Optional[float]:
        """
        Tính thể tích của một cấu trúc (mm³).
        
        Args:
            name: Tên cấu trúc
            
        Returns:
            float: Thể tích (mm³)
        """
        try:
            mask = self.get_structure_mask(name)
            if mask is None:
                logger.warning(f"Không thể tạo mask cho cấu trúc '{name}'")
                return None
                
            # Đếm số voxel trong mask
            voxel_count = np.sum(mask)
            
            if voxel_count == 0:
                logger.warning(f"Cấu trúc '{name}' không có voxel nào")
                return 0.0
                
            # Tính thể tích một voxel (mm³)
            voxel_volume = self.spacing[0] * self.spacing[1] * self.spacing[2]
            
            # Tính tổng thể tích
            volume = voxel_count * voxel_volume
            
            logger.info(f"Đã tính thể tích cấu trúc '{name}': {volume:.2f} mm³")
            return float(volume)
            
        except Exception as error:
            logger.error(f"Lỗi khi tính thể tích cấu trúc '{name}': {str(error)}")
            return None
    
    def set_patient_info(self, patient_info: Dict[str, Any]):
        """
        Thiết lập thông tin bệnh nhân để tạo RT Structure.
        
        Args:
            patient_info: Dictionary chứa thông tin bệnh nhân
        """
        self.patient_info = patient_info
        logger.info("Đã cập nhật thông tin bệnh nhân")
    
    def set_reference_data(self, reference_frame_uid: str, slice_positions: List[float]):
        """
        Thiết lập thông tin tham chiếu cho RT Structure.
        
        Args:
            reference_frame_uid: UID của frame tham chiếu
            slice_positions: Danh sách vị trí các slice (mm)
        """
        self.reference_frame_uid = reference_frame_uid
        self.reference_slice_positions = slice_positions
        logger.info(f"Đã thiết lập thông tin tham chiếu: UID={reference_frame_uid}, {len(slice_positions)} slices")
    
    def save_to_dicom_rtstruct(self, output_path: str, reference_dicom: Optional[str] = None) -> bool:
        """
        Lưu các contour vào file DICOM RT Structure.
        
        Args:
            output_path: Đường dẫn đến file DICOM RT Structure xuất ra
            reference_dicom: Đường dẫn đến file DICOM tham chiếu
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            # Kiểm tra thông tin cần thiết
            if not self.contours:
                logger.error("Không có cấu trúc nào để lưu")
                return False
                
            if not self.reference_frame_uid:
                logger.error("Thiếu frame of reference UID")
                if not reference_dicom:
                    return False
                    
            # Tạo dataset RT Structure mới
            rtstruct_ds = pydicom.Dataset()
            
            # Thêm các phần tử bắt buộc cho thẻ File Meta
            file_meta = pydicom.Dataset()
            file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.481.3'  # RT Structure Set Storage
            file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
            file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
            file_meta.ImplementationClassUID = pydicom.uid.generate_uid()
            
            # Tạo đối tượng FileDataset
            rtstruct_ds = pydicom.FileDataset(output_path, {}, file_meta=file_meta, preamble=b"\0" * 128)
            
            # Thêm các thẻ bắt buộc
            rtstruct_ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.481.3'  # RT Structure Set Storage
            rtstruct_ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
            rtstruct_ds.Modality = 'RTSTRUCT'
            
            # Thiết lập các thẻ khác
            rtstruct_ds.SeriesDescription = 'RT Structure Set'
            rtstruct_ds.SeriesInstanceUID = pydicom.uid.generate_uid()
            rtstruct_ds.StructureSetLabel = 'QuangStation'
            rtstruct_ds.StructureSetName = 'QuangStation RT Structure'
            rtstruct_ds.StructureSetDate = datetime.now().strftime('%Y%m%d')
            rtstruct_ds.StructureSetTime = datetime.now().strftime('%H%M%S')
            
            # Thêm các thông tin bệnh nhân nếu có
            for key, value in self.patient_info.items():
                if key in pydicom.datadict.DicomDictionary:
                    setattr(rtstruct_ds, key, value)
            
            # Thiết lập FrameOfReferenceUID
            if self.reference_frame_uid:
                rtstruct_ds.FrameOfReferenceUID = self.reference_frame_uid
            elif reference_dicom:
                # Đọc từ file tham chiếu
                ref_ds = pydicom.dcmread(reference_dicom)
                if hasattr(ref_ds, 'FrameOfReferenceUID'):
                    rtstruct_ds.FrameOfReferenceUID = ref_ds.FrameOfReferenceUID
                    self.reference_frame_uid = ref_ds.FrameOfReferenceUID
            
            # Tạo ReferencedFrameOfReferenceSequence
            ref_frame_of_ref_seq = pydicom.Sequence()
            ref_frame_of_ref = pydicom.Dataset()
            ref_frame_of_ref.FrameOfReferenceUID = self.reference_frame_uid
            
            # Tạo RT Referenced Study Sequence
            rt_ref_study_seq = pydicom.Sequence()
            rt_ref_study = pydicom.Dataset()
            
            if 'StudyInstanceUID' in self.patient_info:
                rt_ref_study.ReferencedSOPInstanceUID = self.patient_info['StudyInstanceUID']
            else:
                rt_ref_study.ReferencedSOPInstanceUID = pydicom.uid.generate_uid()
                
            # Tạo RT Referenced Series Sequence
            rt_ref_series_seq = pydicom.Sequence()
            rt_ref_series = pydicom.Dataset()
            
            if 'SeriesInstanceUID' in self.patient_info:
                rt_ref_series.SeriesInstanceUID = self.patient_info['SeriesInstanceUID']
            else:
                rt_ref_series.SeriesInstanceUID = pydicom.uid.generate_uid()
                
            # Thêm vào sequences
            rt_ref_study.RTReferencedSeriesSequence = rt_ref_series_seq
            rt_ref_series_seq.append(rt_ref_series)
            
            rt_ref_study_seq.append(rt_ref_study)
            ref_frame_of_ref.RTReferencedStudySequence = rt_ref_study_seq
            
            ref_frame_of_ref_seq.append(ref_frame_of_ref)
            rtstruct_ds.ReferencedFrameOfReferenceSequence = ref_frame_of_ref_seq
            
            # Tạo StructureSetROISequence và ROIContourSequence
            structure_set_roi_seq = pydicom.Sequence()
            roi_contour_seq = pydicom.Sequence()
            
            # Xử lý từng cấu trúc
            for i, (name, contours) in enumerate(self.contours.items(), start=1):
                if not contours:  # Bỏ qua cấu trúc không có contour
                    continue
                    
                # Tạo cấu trúc trong StructureSetROISequence
                structure_set_roi = pydicom.Dataset()
                structure_set_roi.ROINumber = i
                structure_set_roi.ROIName = name
                structure_set_roi.ROIGenerationAlgorithm = 'MANUAL'
                structure_set_roi.FrameOfReferenceUID = self.reference_frame_uid
                structure_set_roi_seq.append(structure_set_roi)
                
                # Tạo cấu trúc trong ROIContourSequence
                roi_contour = pydicom.Dataset()
                roi_contour.ROIDisplayColor = self._convert_color_to_dicom(self.colors.get(name, (1.0, 0.0, 0.0)))
                roi_contour.ReferencedROINumber = i
                
                # Tạo Contour Sequence
                contour_seq = pydicom.Sequence()
                
                # Xử lý contour trên từng slice
                for slice_idx, points_data in contours.items():
                    if not points_data:
                        continue
                        
                    # Kiểm tra xem points_data là danh sách contour hay contour đơn
                    contour_list = []
                    if isinstance(points_data[0], list) or (isinstance(points_data[0], tuple) and isinstance(points_data[0][0], (list, tuple))):
                        # Đây là danh sách các contour
                        contour_list = points_data
                    else:
                        # Đây là contour đơn
                        contour_list = [points_data]
                        
                    # Xử lý từng contour
                    for points in contour_list:
                        if len(points) < 3:
                            continue
                            
                        # Tạo dataset Contour
                        contour = pydicom.Dataset()
                        contour.ContourGeometricType = 'CLOSED_PLANAR'
                        
                        # Lấy vị trí z của slice
                        z_pos = 0.0
                        if slice_idx < len(self.reference_slice_positions):
                            z_pos = self.reference_slice_positions[slice_idx]
                        else:
                            z_pos = self.origin[2] + slice_idx * self.spacing[2]
                            
                        # Chuyển từ tọa độ pixel sang tọa độ thế giới
                        contour_data = []
                        for x, y in points:
                            # Chuyển đổi tọa độ pixel sang tọa độ thế giới (mm)
                            world_x = self.origin[0] + x * self.spacing[0]
                            world_y = self.origin[1] + y * self.spacing[1]
                            world_z = z_pos
                            
                            # Thêm vào danh sách
                            contour_data.extend([world_x, world_y, world_z])
                            
                        # Thiết lập ContourData và NumberOfContourPoints
                        contour.ContourData = contour_data
                        contour.NumberOfContourPoints = len(points)
                        
                        # Thêm vào Contour Sequence
                        contour_seq.append(contour)
                        
                # Gán Contour Sequence cho ROI Contour
                roi_contour.ContourSequence = contour_seq
                roi_contour_seq.append(roi_contour)
                
            # Gán các sequences cho dataset
            rtstruct_ds.StructureSetROISequence = structure_set_roi_seq
            rtstruct_ds.ROIContourSequence = roi_contour_seq
            
            # Lưu file DICOM
            rtstruct_ds.save_as(output_path)
            
            logger.info(f"Đã lưu RT Structure vào file {output_path}")
            self.modified = False
            return True
            
        except Exception as error:
            import traceback
            logger.error(f"Lỗi khi lưu RT Structure: {str(error)}")
            logger.error(traceback.format_exc())
            return False
    
    def _convert_color_to_dicom(self, color: Tuple[float, float, float]) -> List[int]:
        """Chuyển đổi màu từ dạng [0,1] sang [0,255] cho DICOM"""
        return [int(c * 255) for c in color]
    
    def import_from_dicom_rtstruct(self, rtstruct_path: str) -> bool:
        """
        Nhập contour từ file DICOM RT Structure.
        
        Args:
            rtstruct_path: Đường dẫn đến file DICOM RT Structure
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            # Đọc file RT Structure
            rt_struct = pydicom.dcmread(rtstruct_path)
            
            # Kiểm tra xem có phải là RT Structure không
            if not hasattr(rt_struct, 'Modality') or rt_struct.Modality != 'RTSTRUCT':
                logger.error(f"File {rtstruct_path} không phải là DICOM RT Structure")
                return False
                
            # Trích xuất thông tin bệnh nhân
            self._extract_patient_info(rt_struct)
            
            # Trích xuất Frame of Reference UID
            if hasattr(rt_struct, 'ReferencedFrameOfReferenceSequence'):
                for ref_frame in rt_struct.ReferencedFrameOfReferenceSequence:
                    if hasattr(ref_frame, 'FrameOfReferenceUID'):
                        self.reference_frame_uid = ref_frame.FrameOfReferenceUID
                        break
            
            # Trích xuất thông tin cấu trúc
            if not hasattr(rt_struct, 'StructureSetROISequence') or not hasattr(rt_struct, 'ROIContourSequence'):
                logger.error("Thiếu thông tin cấu trúc trong RT Structure")
                return False
                
            # Tạo mapping giữa ROI Number và ROI Name
            roi_map = {}
            for roi in rt_struct.StructureSetROISequence:
                roi_number = getattr(roi, 'ROINumber', None)
                roi_name = getattr(roi, 'ROIName', None)
                if roi_number is not None and roi_name is not None:
                    roi_map[roi_number] = roi_name
            
            # Trích xuất contour từ ROIContourSequence
            for roi_contour in rt_struct.ROIContourSequence:
                roi_number = getattr(roi_contour, 'ReferencedROINumber', None)
                if roi_number is None or roi_number not in roi_map:
                    logger.warning(f"Bỏ qua ROI không xác định: {roi_number}")
                    continue
                    
                roi_name = roi_map[roi_number]
                
                # Thêm cấu trúc mới
                if roi_name in self.contours:
                    logger.warning(f"Cấu trúc '{roi_name}' đã tồn tại, sẽ ghi đè")
                    self.contours[roi_name] = {}
                else:
                    self.contours[roi_name] = {}
                
                # Thiết lập màu sắc
                if hasattr(roi_contour, 'ROIDisplayColor'):
                    color = [float(c)/255.0 for c in roi_contour.ROIDisplayColor]
                    if len(color) >= 3:
                        self.colors[roi_name] = tuple(color[:3])
                    
                # Kiểm tra xem có ContourSequence không
                if not hasattr(roi_contour, 'ContourSequence'):
                    logger.warning(f"Không có contour cho cấu trúc '{roi_name}'")
                    continue
                    
                for contour in roi_contour.ContourSequence:
                    if not hasattr(contour, 'ContourData') or not hasattr(contour, 'NumberOfContourPoints'):
                        continue
                        
                    points_data = contour.ContourData
                    num_points = contour.NumberOfContourPoints
                    
                    # Contour data là 1 mảng phẳng gồm x,y,z cho mỗi điểm
                    points = []
                    for i in range(0, len(points_data), 3):
                        if i+2 >= len(points_data):
                            break
                            
                        x = float(points_data[i])
                        y = float(points_data[i+1])
                        z = float(points_data[i+2])
                        
                        # Chuyển từ tọa độ thế giới sang tọa độ pixel
                        pixel_x = int(round((x - self.origin[0]) / self.spacing[0]))
                        pixel_y = int(round((y - self.origin[1]) / self.spacing[1]))
                        
                        points.append((pixel_x, pixel_y))
                    
                    # Tìm slice phù hợp dựa vào tọa độ z
                    z = float(points_data[2])  # Lấy z từ điểm đầu tiên
                    slice_idx = -1
                    
                    # Nếu có sẵn vị trí slice
                    if self.reference_slice_positions:
                        # Tìm slice gần nhất
                        closest_idx = -1
                        min_distance = float('inf')
                        for i, pos in enumerate(self.reference_slice_positions):
                            distance = abs(pos - z)
                            if distance < min_distance:
                                min_distance = distance
                                closest_idx = i
                        
                        # Nếu khoảng cách gần hơn 1/2 slice thickness, lấy slice đó
                        if closest_idx >= 0 and min_distance < self.spacing[2] / 2:
                            slice_idx = closest_idx
                    
                    # Nếu không tìm được slice từ vị trí, tính từ origin và spacing
                    if slice_idx == -1:
                        # Ước tính slice idx từ z và spacing
                        slice_idx = int(round((z - self.origin[2]) / self.spacing[2]))
                    
                    # Kiểm tra slice_idx hợp lệ
                    if slice_idx < 0 or slice_idx >= self.image_data.shape[0]:
                        logger.warning(f"Slice index {slice_idx} nằm ngoài phạm vi {self.image_data.shape[0]} slices")
                        continue
                    
                    # Thêm contour vào slice
                    if points and len(points) >= 3:  # Cần ít nhất 3 điểm để tạo contour
                        # Đảm bảo contour khép kín
                        if points[0] != points[-1]:
                            points.append(points[0])
                        self.contours[roi_name][slice_idx] = points
            
            self.modified = False
            self.current_struct = next(iter(self.contours)) if self.contours else None
            
            logger.info(f"Đã nhập {len(self.contours)} cấu trúc từ file {rtstruct_path}")
            return True
            
        except Exception as error:
            import traceback
            logger.error(f"Lỗi khi nhập DICOM RT Structure: {str(error)}")
            logger.error(traceback.format_exc())
            return False
            
    def _extract_patient_info(self, dicom_ds):
        """Trích xuất thông tin bệnh nhân từ dataset DICOM."""
        fields = [
            'PatientName', 'PatientID', 'PatientBirthDate', 'PatientSex',
            'StudyDescription', 'StudyDate', 'StudyTime', 'StudyInstanceUID',
            'SeriesDescription', 'SeriesDate', 'SeriesTime', 'SeriesInstanceUID'
        ]
        
        for field in fields:
            if hasattr(dicom_ds, field):
                value = getattr(dicom_ds, field)
                # Xử lý các kiểu dữ liệu đặc biệt từ pydicom
                if hasattr(value, 'original_string'):
                    value = str(value)
                self.patient_info[field] = value
    
    def get_contour_statistics(self) -> Dict[str, Dict[str, Any]]:
        """
        Lấy thông tin thống kê về các contour.
        
        Returns:
            Dict: Dictionary chứa thông tin về từng cấu trúc
        """
        stats = {}
        for name in self.contours:
            structure_stats = {
                'name': name,
                'color': self.colors.get(name, (1, 0, 0)),
                'slice_count': len(self.contours[name]),
                'volume_mm3': self.calculate_volume(name),
                'slices': sorted(list(self.contours[name].keys()))
            }
            stats[name] = structure_stats
            
        return stats
    
    def save_to_json(self, output_file: str) -> bool:
        """
        Lưu thông tin contours ra file JSON.
        
        Args:
            output_file: Đường dẫn file JSON đầu ra
            
        Returns:
            bool: True nếu lưu thành công, False nếu có lỗi
        """
        import json
        
        try:
            # Chuẩn bị dữ liệu
            data = {
                "version": "1.0",
                "created_time": datetime.now().isoformat(),
                "patient_info": self.patient_info,
                "structures": {},
                "reference_frame_uid": self.reference_frame_uid,
                "isocenter": self.isocenter
            }
            
            # Thêm thông tin về contours
            for name, contours in self.contours.items():
                # Chuyển đổi contours sang định dạng có thể serialize
                serializable_contours = {}
                for slice_idx, points_list in contours.items():
                    # Chuyển danh sách điểm sang danh sách có thể serialize
                    serializable_points = []
                    for points in points_list:
                        serializable_points.append(points.tolist() if isinstance(points, np.ndarray) else points)
                    serializable_contours[str(slice_idx)] = serializable_points
                
                # Lưu thông tin cho structure này
                data["structures"][name] = {
                    "contours": serializable_contours,
                    "color": self.colors.get(name, [1.0, 0.0, 0.0])
                }
            
            # Ghi file JSON
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Đã lưu contours thành công vào file {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu contours ra file JSON: {e}")
            return False
            
    def load_from_json(self, input_file: str) -> bool:
        """
        Nạp thông tin contours từ file JSON.
        
        Args:
            input_file: Đường dẫn file JSON đầu vào
            
        Returns:
            bool: True nếu nạp thành công, False nếu có lỗi
        """
        import json
        
        try:
            # Đọc file JSON
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Kiểm tra phiên bản
            version = data.get("version", "1.0")
            if version != "1.0":
                self.logger.warning(f"Phiên bản file ({version}) có thể không tương thích")
                
            # Nạp thông tin cơ bản
            self.patient_info = data.get("patient_info", {})
            self.reference_frame_uid = data.get("reference_frame_uid", None)
            self.isocenter = data.get("isocenter", None)
            
            # Nạp thông tin các cấu trúc
            structures_data = data.get("structures", {})
            for name, struct_info in structures_data.items():
                # Thêm cấu trúc
                color = struct_info.get("color", [1.0, 0.0, 0.0])
                self.add_structure(name, tuple(color))
                
                # Nạp các contours
                contours_data = struct_info.get("contours", {})
                for slice_idx_str, points_list in contours_data.items():
                    slice_idx = int(slice_idx_str)
                    for points in points_list:
                        # Chuyển đổi danh sách điểm sang numpy array
                        np_points = np.array(points)
                        self.contours.setdefault(name, {}).setdefault(slice_idx, []).append(np_points)
                
                logger.info(f"Đã nạp contours thành công từ file {input_file}")
                self.modified = True
                return True
            
        except Exception as e:
            logger.error(f"Lỗi khi nạp contours từ file JSON: {e}")
            return False
            
    def export_to_csv(self, output_dir: str) -> bool:
        """
        Xuất contours ra các file CSV.
        
        Args:
            output_dir: Thư mục đầu ra
            
        Returns:
            bool: True nếu xuất thành công, False nếu có lỗi
        """
        import os
        import csv
        
        try:
            # Tạo thư mục đầu ra nếu chưa tồn tại
            os.makedirs(output_dir, exist_ok=True)
            
            # Xuất từng cấu trúc ra file CSV riêng
            for name, contours in self.contours.items():
                # Tạo tên file an toàn
                safe_name = "".join(c if c.isalnum() else "_" for c in name)
                output_file = os.path.join(output_dir, f"{safe_name}.csv")
                
                # Ghi file CSV
                with open(output_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    # Ghi header
                    writer.writerow(["SliceIndex", "PointIndex", "X", "Y"])
                    
                    # Ghi dữ liệu
                    for slice_idx, points_list in contours.items():
                        for point_set_idx, points in enumerate(points_list):
                            for i, point in enumerate(points):
                                writer.writerow([slice_idx, point_set_idx, point[0], point[1]])
                                
            self.logger.info(f"Đã xuất contours thành công vào thư mục {output_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"Lỗi khi xuất contours ra file CSV: {e}")
            return False
