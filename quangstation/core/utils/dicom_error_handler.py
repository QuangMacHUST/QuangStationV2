#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module chứa các tiện ích xử lý lỗi DICOM cho QuangStation V2.
"""

import os
import traceback
from typing import Dict, List, Tuple, Any, Optional, Callable

from quangstation.core.utils.logging import get_logger

logger = get_logger(__name__)

# Định nghĩa các mã lỗi DICOM
class DICOMErrorCodes:
    NO_ERROR = 0
    FILE_NOT_FOUND = 1
    INVALID_DICOM = 2
    PARSING_ERROR = 3
    MISSING_TAG = 4
    INCONSISTENT_DATA = 5
    MISSING_SLICE = 6
    UNSUPPORTED_TRANSFER_SYNTAX = 7
    MEMORY_ERROR = 8
    UNKNOWN_ERROR = 999

class DICOMError(Exception):
    """Lớp lỗi DICOM tùy chỉnh"""
    
    def __init__(self, message: str, error_code: int = DICOMErrorCodes.UNKNOWN_ERROR, 
                details: Dict[str, Any] = None):
        """
        Khởi tạo lỗi DICOM
        
        Args:
            message: Thông báo lỗi
            error_code: Mã lỗi từ DICOMErrorCodes
            details: Thông tin chi tiết về lỗi
        """
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
        
    def __str__(self):
        return f"[Mã lỗi {self.error_code}] {self.message}"

def handle_dicom_error(func: Callable) -> Callable:
    """
    Decorator để xử lý các lỗi DICOM
    
    Args:
        func: Hàm cần wrap
        
    Returns:
        Callable: Hàm đã được wrap
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except DICOMError as e:
            # Ghi log lỗi DICOM
            logger.error(f"Lỗi DICOM [{e.error_code}]: {e.message}")
            if e.details:
                logger.debug(f"Chi tiết lỗi: {e.details}")
            raise
        except Exception as e:
            # Wrap các lỗi khác vào DICOMError
            error_message = str(e)
            error_code = DICOMErrorCodes.UNKNOWN_ERROR
            error_details = {"traceback": traceback.format_exc()}
            
            if "No such file" in error_message or "FileNotFoundError" in error_message:
                error_code = DICOMErrorCodes.FILE_NOT_FOUND
            elif "Invalid DICOM file" in error_message:
                error_code = DICOMErrorCodes.INVALID_DICOM
            elif "Memory" in error_message:
                error_code = DICOMErrorCodes.MEMORY_ERROR
            elif "Tag" in error_message and "missing" in error_message:
                error_code = DICOMErrorCodes.MISSING_TAG
            
            logger.error(f"Lỗi không xác định khi xử lý DICOM: {error_message}")
            logger.debug(traceback.format_exc())
            
            dicom_error = DICOMError(error_message, error_code, error_details)
            raise dicom_error
    
    return wrapper

def validate_dicom_directory(directory_path: str) -> Tuple[bool, List[str]]:
    """
    Kiểm tra tính hợp lệ của thư mục DICOM
    
    Args:
        directory_path: Đường dẫn đến thư mục cần kiểm tra
        
    Returns:
        Tuple[bool, List[str]]: (thư mục hợp lệ, danh sách lỗi)
    """
    errors = []
    
    # Kiểm tra thư mục tồn tại
    if not os.path.exists(directory_path):
        errors.append(f"Thư mục '{directory_path}' không tồn tại")
        return False, errors
    
    # Kiểm tra thư mục có thể truy cập
    if not os.path.isdir(directory_path):
        errors.append(f"'{directory_path}' không phải là thư mục")
        return False, errors
    
    # Kiểm tra quyền đọc
    if not os.access(directory_path, os.R_OK):
        errors.append(f"Không có quyền đọc thư mục '{directory_path}'")
        return False, errors
    
    # Kiểm tra xem thư mục có trống không
    if not os.listdir(directory_path):
        errors.append(f"Thư mục '{directory_path}' trống")
        return False, errors
    
    return True, errors

def get_error_message(error_code: int) -> str:
    """
    Lấy thông báo lỗi dựa vào mã lỗi
    
    Args:
        error_code: Mã lỗi từ DICOMErrorCodes
        
    Returns:
        str: Thông báo lỗi
    """
    error_messages = {
        DICOMErrorCodes.NO_ERROR: "Không có lỗi",
        DICOMErrorCodes.FILE_NOT_FOUND: "Không tìm thấy file DICOM",
        DICOMErrorCodes.INVALID_DICOM: "File DICOM không hợp lệ",
        DICOMErrorCodes.PARSING_ERROR: "Lỗi khi phân tích file DICOM",
        DICOMErrorCodes.MISSING_TAG: "Thiếu tag DICOM bắt buộc",
        DICOMErrorCodes.INCONSISTENT_DATA: "Dữ liệu DICOM không nhất quán",
        DICOMErrorCodes.MISSING_SLICE: "Thiếu lát cắt trong chuỗi hình ảnh DICOM",
        DICOMErrorCodes.UNSUPPORTED_TRANSFER_SYNTAX: "Cú pháp truyền dữ liệu không được hỗ trợ",
        DICOMErrorCodes.MEMORY_ERROR: "Lỗi bộ nhớ khi xử lý DICOM",
        DICOMErrorCodes.UNKNOWN_ERROR: "Lỗi không xác định"
    }
    
    return error_messages.get(error_code, "Lỗi không xác định") 