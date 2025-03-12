#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module cung cấp các công cụ xử lý lỗi DICOM
"""

import os
import glob
import functools
import traceback
from enum import Enum, auto
from typing import List, Tuple, Dict, Any, Optional, Callable
from quangstation.core.utils.logging import get_logger

logger = get_logger(__name__)

class DICOMErrorCodes(Enum):
    """
    Mã lỗi DICOM tiêu chuẩn
    """
    FILE_NOT_FOUND = auto()
    INVALID_DICOM = auto()
    PARSING_ERROR = auto()
    UNKNOWN_MODALITY = auto()
    NO_PATIENT_INFO = auto()
    NO_IMAGE_DATA = auto()
    INSUFFICIENT_DATA = auto()
    MISSING_SLICE = auto()
    MISSING_FIELD = auto()
    INVALID_FORMAT = auto()
    INVALID_DIRECTORY = auto()
    PERMISSION_DENIED = auto()
    DISK_FULL = auto()
    IO_ERROR = auto()
    MEMORY_ERROR = auto()
    NETWORK_ERROR = auto()
    UNKNOWN_ERROR = auto()

class DICOMError(Exception):
    """
    Lớp ngoại lệ tùy chỉnh cho các lỗi DICOM
    """
    
    def __init__(self, message: str, error_code: DICOMErrorCodes, additional_info: Dict[str, Any] = None):
        """
        Khởi tạo ngoại lệ DICOM
        
        Args:
            message: Thông báo lỗi
            error_code: Mã lỗi từ DICOMErrorCodes
            additional_info: Thông tin bổ sung về lỗi
        """
        self.message = message
        self.error_code = error_code
        self.additional_info = additional_info or {}
        super().__init__(self.message)
    
    def __str__(self):
        """Biểu diễn chuỗi của lỗi DICOM"""
        return f"DICOMError[{self.error_code.name}]: {self.message}"

def handle_dicom_error(func):
    """
    Decorator để xử lý các lỗi DICOM một cách nhất quán
    
    Args:
        func: Hàm cần xử lý lỗi
    
    Returns:
        Wrapper function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except DICOMError as dicom_error:
            # Ghi log lỗi DICOM
            logger.error(f"Lỗi DICOM: {dicom_error}")
            
            # Thêm thông tin traceback nếu chưa có
            if 'traceback' not in dicom_error.additional_info:
                dicom_error.additional_info['traceback'] = traceback.format_exc()
            
            # Chuyển tiếp ngoại lệ DICOM
            raise
        except PermissionError as error:
            # Chuyển đổi lỗi quyền truy cập thành DICOMError
            logger.error(f"Lỗi quyền truy cập: {str(error)}")
            raise DICOMError(
                f"Không có quyền truy cập: {str(error)}",
                DICOMErrorCodes.PERMISSION_DENIED,
                {'traceback': traceback.format_exc(), 'original_error': str(error)}
            )
        except FileNotFoundError as error:
            # Chuyển đổi lỗi không tìm thấy file thành DICOMError
            logger.error(f"Không tìm thấy file: {str(error)}")
            raise DICOMError(
                f"Không tìm thấy file: {str(error)}",
                DICOMErrorCodes.FILE_NOT_FOUND,
                {'traceback': traceback.format_exc(), 'original_error': str(error)}
            )
        except MemoryError as error:
            # Chuyển đổi lỗi bộ nhớ thành DICOMError
            logger.error(f"Lỗi bộ nhớ: {str(error)}")
            raise DICOMError(
                f"Không đủ bộ nhớ để xử lý: {str(error)}",
                DICOMErrorCodes.MEMORY_ERROR,
                {'traceback': traceback.format_exc(), 'original_error': str(error)}
            )
        except Exception as error:
            # Chuyển đổi các lỗi khác thành DICOMError
            logger.error(f"Lỗi không xác định: {str(error)}")
            raise DICOMError(
                f"Lỗi không xác định khi xử lý DICOM: {str(error)}",
                DICOMErrorCodes.UNKNOWN_ERROR,
                {'traceback': traceback.format_exc(), 'original_error': str(error)}
            )
    
    return wrapper

def validate_dicom_directory(directory: str) -> Tuple[bool, List[str]]:
    """
    Kiểm tra tính hợp lệ của thư mục DICOM
    
    Args:
        directory: Đường dẫn đến thư mục cần kiểm tra
        
    Returns:
        Tuple[bool, List[str]]: (có hợp lệ không, danh sách lỗi nếu có)
    """
    errors = []
    
    # Kiểm tra thư mục tồn tại
    if not os.path.exists(directory):
        errors.append(f"Thư mục không tồn tại: {directory}")
        return False, errors
    
    # Kiểm tra đó là thư mục (không phải file)
    if not os.path.isdir(directory):
        errors.append(f"{directory} không phải là thư mục")
        return False, errors
    
    # Kiểm tra quyền truy cập
    if not os.access(directory, os.R_OK):
        errors.append(f"Không có quyền đọc thư mục: {directory}")
        return False, errors
    
    # Kiểm tra thư mục có file
    files = os.listdir(directory)
    if not files:
        errors.append(f"Thư mục trống: {directory}")
        return False, errors
    
    # Kiểm tra có file DICOM hay không
    dicom_files = glob.glob(os.path.join(directory, "*.dcm"))
    if not dicom_files:
        # Kiểm tra các file không có phần mở rộng
        has_potential_dicom = False
        for file in files:
            full_path = os.path.join(directory, file)
            if os.path.isfile(full_path) and not os.path.splitext(file)[1]:
                has_potential_dicom = True
                break
        
        if not has_potential_dicom:
            errors.append("Không tìm thấy file DICOM trong thư mục")
            return False, errors
    
    # Nếu không có lỗi, thư mục hợp lệ
    return len(errors) == 0, errors

def get_error_message(error_code: DICOMErrorCodes) -> str:
    """
    Lấy thông báo lỗi người dùng dựa trên mã lỗi
    
    Args:
        error_code: Mã lỗi DICOM
        
    Returns:
        str: Thông báo lỗi người dùng
    """
    error_messages = {
        DICOMErrorCodes.FILE_NOT_FOUND: "Không tìm thấy file DICOM",
        DICOMErrorCodes.INVALID_DICOM: "File DICOM không hợp lệ",
        DICOMErrorCodes.PARSING_ERROR: "Lỗi khi phân tích dữ liệu DICOM",
        DICOMErrorCodes.UNKNOWN_MODALITY: "Loại dữ liệu DICOM không được hỗ trợ",
        DICOMErrorCodes.NO_PATIENT_INFO: "Không tìm thấy thông tin bệnh nhân",
        DICOMErrorCodes.NO_IMAGE_DATA: "Không tìm thấy dữ liệu hình ảnh",
        DICOMErrorCodes.INSUFFICIENT_DATA: "Dữ liệu DICOM không đầy đủ",
        DICOMErrorCodes.MISSING_SLICE: "Thiếu lát cắt trong dữ liệu CT/MR",
        DICOMErrorCodes.MISSING_FIELD: "Thiếu trường dữ liệu bắt buộc trong DICOM",
        DICOMErrorCodes.INVALID_FORMAT: "Định dạng DICOM không được hỗ trợ",
        DICOMErrorCodes.INVALID_DIRECTORY: "Thư mục DICOM không hợp lệ",
        DICOMErrorCodes.PERMISSION_DENIED: "Không có quyền truy cập file/thư mục",
        DICOMErrorCodes.DISK_FULL: "Đĩa đầy, không thể lưu dữ liệu",
        DICOMErrorCodes.IO_ERROR: "Lỗi nhập/xuất dữ liệu",
        DICOMErrorCodes.MEMORY_ERROR: "Không đủ bộ nhớ để xử lý dữ liệu",
        DICOMErrorCodes.NETWORK_ERROR: "Lỗi kết nối mạng khi truy cập DICOM",
        DICOMErrorCodes.UNKNOWN_ERROR: "Lỗi không xác định khi xử lý DICOM"
    }
    
    return error_messages.get(error_code, "Lỗi không xác định") 