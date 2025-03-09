#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module quản lý tích hợp với các thư viện bên ngoài cho QuangStation V2.
"""

import os
import sys
import importlib
import subprocess
import platform
import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any, Callable

from quangstation.utils.logging import get_logger

logger = get_logger(__name__)

class ExternalLibrary:
    """Lớp xử lý tích hợp với một thư viện bên ngoài"""
    
    def __init__(self, name: str, import_name: str = None, min_version: str = None):
        """
        Khởi tạo đối tượng thư viện bên ngoài.
        
        Args:
            name: Tên thư viện (ví dụ: 'vtk', 'itk')
            import_name: Tên khi import (mặc định là name)
            min_version: Phiên bản tối thiểu yêu cầu
        """
        self.name = name
        self.import_name = import_name or name
        self.min_version = min_version
        self.module = None
        self.version = None
        self.is_available = False
        
        # Kiểm tra và tải thư viện
        self._check_availability()
    
    def _check_availability(self) -> bool:
        """Kiểm tra thư viện có khả dụng hay không"""
        try:
            # Thử import module
            self.module = importlib.import_module(self.import_name)
            
            # Lấy phiên bản
            if hasattr(self.module, '__version__'):
                self.version = self.module.__version__
            elif hasattr(self.module, 'VTK_VERSION'):
                self.version = self.module.VTK_VERSION
            
            # Kiểm tra phiên bản tối thiểu
            if self.min_version and self.version:
                from packaging import version
                if version.parse(self.version) < version.parse(self.min_version):
                    logger.warning(f"Thư viện {self.name} phiên bản {self.version} thấp hơn yêu cầu (>= {self.min_version})")
                    return False
            
            self.is_available = True
            logger.info(f"Đã tải thư viện {self.name} phiên bản {self.version}")
            return True
            
        except ImportError:
            logger.warning(f"Không thể tải thư viện {self.name}")
            self.is_available = False
            return False
    
    def install(self, force: bool = False) -> bool:
        """
        Thử cài đặt thư viện nếu chưa có.
        
        Args:
            force: Cài đặt lại kể cả khi đã có
            
        Returns:
            bool: Thành công hay không
        """
        if self.is_available and not force:
            logger.info(f"Thư viện {self.name} đã được cài đặt rồi")
            return True
        
        try:
            logger.info(f"Đang cài đặt thư viện {self.name}...")
            
            # Cài đặt thông qua pip
            package_name = self.name
            if self.min_version:
                package_name += f">={self.min_version}"
            
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package_name],
                check=True,
                capture_output=True,
                text=True
            )
            
            # Kiểm tra lại sau khi cài đặt
            importlib.invalidate_caches()
            success = self._check_availability()
            
            if success:
                logger.info(f"Đã cài đặt thành công thư viện {self.name}")
                return True
            else:
                logger.error(f"Cài đặt thư viện {self.name} không thành công")
                return False
                
        except subprocess.CalledProcessError as error:
            logger.error(f"Lỗi khi cài đặt thư viện {self.name}: {error.stderr}")
            return False
        except Exception as error:
            logger.error(f"Lỗi khi cài đặt thư viện {self.name}: {str(error)}")
            return False
    
    def get_module(self):
        """Trả về module đã được tải nếu có"""
        return self.module if self.is_available else None


class ExternalIntegration:
    """Lớp quản lý tích hợp với các thư viện bên ngoài"""
    
    # Singleton instance
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Trả về instance singleton"""
        if cls._instance is None:
            cls._instance = ExternalIntegration()
        return cls._instance
    
    def __init__(self):
        """Khởi tạo đối tượng quản lý tích hợp"""
        if ExternalIntegration._instance is not None:
            raise RuntimeError("Singleton class, use get_instance() instead")
        
        # Khởi tạo các thư viện được hỗ trợ
        self.libraries = {
            "vtk": ExternalLibrary("vtk", min_version="9.0.0"),
            "itk": ExternalLibrary("itk", min_version="5.2.0"),
            "pytorch": ExternalLibrary("torch", min_version="1.8.0"),
            "pydicom": ExternalLibrary("pydicom", min_version="2.2.0"),
            "scipy": ExternalLibrary("scipy", min_version="1.6.0"),
            "simpleitk": ExternalLibrary("SimpleITK", import_name="sitk", min_version="2.0.0"),
            "matplotlib": ExternalLibrary("matplotlib", min_version="3.4.0"),
            "skimage": ExternalLibrary("scikit-image", import_name="skimage", min_version="0.18.0"),
            "cuda": None  # Sẽ được kiểm tra riêng
        }
        
        # Kiểm tra CUDA availability
        self._check_cuda()
    
    def _check_cuda(self):
        """Kiểm tra CUDA có khả dụng hay không"""
        try:
            import torch
            cuda_available = torch.cuda.is_available()
            if cuda_available:
                cuda_version = torch.version.cuda
                device_count = torch.cuda.device_count()
                devices = [torch.cuda.get_device_name(i) for i in range(device_count)]
                
                self.libraries["cuda"] = ExternalLibrary("cuda")
                self.libraries["cuda"].is_available = True
                self.libraries["cuda"].version = cuda_version
                
                logger.info(f"Đã phát hiện CUDA {cuda_version} với {device_count} thiết bị: {', '.join(devices)}")
            else:
                self.libraries["cuda"] = ExternalLibrary("cuda")
                self.libraries["cuda"].is_available = False
                logger.info("Không phát hiện được CUDA")
                
        except ImportError:
            logger.warning("Không thể kiểm tra CUDA vì PyTorch chưa được cài đặt")
            self.libraries["cuda"] = ExternalLibrary("cuda")
            self.libraries["cuda"].is_available = False
    
    def get_library(self, name: str) -> Optional[ExternalLibrary]:
        """
        Lấy đối tượng thư viện theo tên.
        
        Args:
            name: Tên thư viện
            
        Returns:
            ExternalLibrary hoặc None nếu không tìm thấy
        """
        return self.libraries.get(name)
    
    def get_module(self, name: str):
        """
        Lấy module từ thư viện.
        
        Args:
            name: Tên thư viện
            
        Returns:
            Module hoặc None nếu không có
        """
        library = self.get_library(name)
        if library:
            return library.get_module()
        return None
    
    def install_library(self, name: str, force: bool = False) -> bool:
        """
        Cài đặt thư viện.
        
        Args:
            name: Tên thư viện
            force: Cài đặt lại kể cả khi đã có
            
        Returns:
            bool: Thành công hay không
        """
        library = self.get_library(name)
        if library:
            return library.install(force)
        else:
            logger.error(f"Không tìm thấy thư viện {name} trong danh sách hỗ trợ")
            return False
    
    def check_requirements(self) -> Dict[str, bool]:
        """
        Kiểm tra tất cả các thư viện yêu cầu.
        
        Returns:
            Dict[str, bool]: Kết quả kiểm tra
        """
        results = {}
        missing_libs = []
        
        for name, lib in self.libraries.items():
            if lib:
                results[name] = lib.is_available
                if not lib.is_available:
                    missing_libs.append(name)
        
        if missing_libs:
            logger.warning(f"Thiếu các thư viện: {', '.join(missing_libs)}")
        
        return results
    
    def install_missing_libraries(self) -> Dict[str, bool]:
        """
        Cài đặt tất cả các thư viện còn thiếu.
        
        Returns:
            Dict[str, bool]: Kết quả cài đặt
        """
        results = {}
        
        for name, lib in self.libraries.items():
            if lib and not lib.is_available:
                logger.info(f"Đang cài đặt thư viện {name}...")
                results[name] = lib.install()
        
        return results
    
    def get_available_modules(self) -> Dict[str, Any]:
        """
        Lấy tất cả các module đã tải thành công.
        
        Returns:
            Dict[str, Any]: Dictionary chứa các module
        """
        modules = {}
        
        for name, lib in self.libraries.items():
            if lib and lib.is_available:
                module = lib.get_module()
                if module:
                    modules[name] = module
        
        return modules
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Lấy thông tin hệ thống và các thư viện.
        
        Returns:
            Dict[str, Any]: Thông tin hệ thống
        """
        info = {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "processor": platform.processor(),
            "python": platform.python_version(),
            "libraries": {}
        }
        
        for name, lib in self.libraries.items():
            if lib:
                info["libraries"][name] = {
                    "available": lib.is_available,
                    "version": lib.version
                }
        
        return info


def get_integration() -> ExternalIntegration:
    """
    Lấy đối tượng quản lý tích hợp.
    
    Returns:
        ExternalIntegration: Đối tượng quản lý tích hợp
    """
    return ExternalIntegration.get_instance()


def get_module(name: str):
    """
    Lấy module từ thư viện bên ngoài.
    
    Args:
        name: Tên thư viện
        
    Returns:
        Module hoặc None nếu không có
    """
    return get_integration().get_module(name)


def check_cuda_available() -> bool:
    """
    Kiểm tra CUDA có khả dụng hay không.
    
    Returns:
        bool: True nếu CUDA khả dụng
    """
    cuda_lib = get_integration().get_library("cuda")
    return cuda_lib.is_available if cuda_lib else False


def get_cuda_devices() -> List[str]:
    """
    Lấy danh sách thiết bị CUDA.
    
    Returns:
        List[str]: Danh sách thiết bị
    """
    try:
        import torch
        if torch.cuda.is_available():
            device_count = torch.cuda.device_count()
            return [torch.cuda.get_device_name(i) for i in range(device_count)]
    except ImportError:
        pass
    
    return [] 