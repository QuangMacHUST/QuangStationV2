#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module data_bridge.py
---------------------
Module này cung cấp các lớp cầu nối giữa các module khác nhau trong hệ thống,
đảm bảo tính toàn vẹn dữ liệu khi chuyển từ module này sang module khác.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any, TypeVar, Generic, Protocol, runtime_checkable
import os
import json
from abc import ABC, abstractmethod
import logging

from quangstation.utils.logging import get_logger
from quangstation.utils.data_validation import validate_data_flow, DataType
from quangstation.planning.plan_config import PlanConfig

# Khởi tạo logger
logger = get_logger("DataBridge")

T = TypeVar('T')
U = TypeVar('U')

class DataBridge(Generic[T, U]):
    """
    Lớp cầu nối dữ liệu giữa các module.
    Đảm bảo dữ liệu được truyền đúng định dạng và được xác thực.
    """
    
    def __init__(self, source_module: str, target_module: str, data_type: DataType):
        """
        Khởi tạo cầu nối dữ liệu.
        
        Args:
            source_module: Tên module nguồn
            target_module: Tên module đích
            data_type: Loại dữ liệu sẽ truyền qua cầu nối
        """
        self.source_module = source_module
        self.target_module = target_module
        self.data_type = data_type
        self.transformers = []  # Danh sách các hàm biến đổi dữ liệu
        
        logger.info(f"Đã khởi tạo cầu nối dữ liệu từ {source_module} đến {target_module} cho dữ liệu {data_type.value}")
    
    def add_transformer(self, transformer_func):
        """
        Thêm hàm biến đổi dữ liệu vào cầu nối.
        
        Args:
            transformer_func: Hàm biến đổi dữ liệu, nhận đầu vào là dữ liệu gốc
                             và trả về dữ liệu đã biến đổi
        """
        self.transformers.append(transformer_func)
        logger.debug(f"Đã thêm transformer cho cầu nối {self.source_module} -> {self.target_module}")
    
    def transfer(self, data: T) -> Optional[U]:
        """
        Chuyển dữ liệu từ module nguồn sang module đích.
        
        Args:
            data: Dữ liệu cần chuyển
            
        Returns:
            Dữ liệu đã được biến đổi và xác thực, None nếu dữ liệu không hợp lệ
        """
        # Xác thực dữ liệu đầu vào
        validation_result = validate_data_flow(data, self.target_module, self.data_type)
        if not validation_result.valid:
            logger.error(f"Dữ liệu từ {self.source_module} không hợp lệ cho {self.target_module}: {validation_result.message}")
            return None
        
        # Áp dụng các biến đổi
        transformed_data = data
        for transformer in self.transformers:
            try:
                transformed_data = transformer(transformed_data)
            except Exception as error:
                logger.error(f"Lỗi khi biến đổi dữ liệu: {str(error)}")
                return None
        
        logger.info(f"Đã chuyển dữ liệu từ {self.source_module} đến {self.target_module}")
        return transformed_data

class ImageDataBridge(DataBridge[np.ndarray, np.ndarray]):
    """
    Cầu nối dữ liệu hình ảnh.
    Chuyên biệt hóa cho việc chuyển dữ liệu hình ảnh giữa các module.
    """
    
    def __init__(self, source_module: str, target_module: str):
        """
        Khởi tạo cầu nối dữ liệu hình ảnh.
        
        Args:
            source_module: Tên module nguồn
            target_module: Tên module đích
        """
        super().__init__(source_module, target_module, DataType.CT_IMAGE)
        self.spacing = None
        self.origin = None
        self.orientation = None
    
    def set_image_metadata(self, spacing: List[float], origin: List[float], orientation: Optional[List[float]] = None):
        """
        Thiết lập metadata cho hình ảnh.
        
        Args:
            spacing: Khoảng cách giữa các voxel [x, y, z]
            origin: Tọa độ gốc [x, y, z]
            orientation: Vector định hướng (6 phần tử)
        """
        self.spacing = spacing
        self.origin = origin
        self.orientation = orientation
    
    def transfer(self, image_data: np.ndarray) -> Optional[np.ndarray]:
        """
        Chuyển dữ liệu hình ảnh từ module nguồn sang module đích.
        
        Args:
            image_data: Dữ liệu hình ảnh cần chuyển
            
        Returns:
            Dữ liệu hình ảnh đã được biến đổi, None nếu không hợp lệ
        """
        # Kiểm tra nếu spacing và origin đã được thiết lập
        if self.spacing is None or self.origin is None:
            logger.warning(f"Spacing hoặc origin chưa được thiết lập cho cầu nối {self.source_module} -> {self.target_module}")
            
        # Gọi phương thức của lớp cha
        return super().transfer(image_data)

class StructureDataBridge(DataBridge[Dict[str, np.ndarray], Dict[str, np.ndarray]]):
    """
    Cầu nối dữ liệu cấu trúc.
    Chuyên biệt hóa cho việc chuyển dữ liệu cấu trúc giữa các module.
    """
    
    def __init__(self, source_module: str, target_module: str):
        """
        Khởi tạo cầu nối dữ liệu cấu trúc.
        
        Args:
            source_module: Tên module nguồn
            target_module: Tên module đích
        """
        super().__init__(source_module, target_module, DataType.STRUCTURE_MASK)
        self.image_data = None
    
    def set_reference_image(self, image_data: np.ndarray):
        """
        Thiết lập hình ảnh tham chiếu.
        
        Args:
            image_data: Dữ liệu hình ảnh tham chiếu
        """
        self.image_data = image_data
    
    def transfer(self, structures: Dict[str, np.ndarray]) -> Optional[Dict[str, np.ndarray]]:
        """
        Chuyển dữ liệu cấu trúc từ module nguồn sang module đích.
        
        Args:
            structures: Dictionary chứa các cấu trúc {tên: mask}
            
        Returns:
            Dictionary chứa các cấu trúc đã được biến đổi, None nếu không hợp lệ
        """
        if not structures:
            logger.warning(f"Không có cấu trúc nào để chuyển từ {self.source_module} đến {self.target_module}")
            return {}
        
        # Xác thực từng cấu trúc
        valid_structures = {}
        for name, mask in structures.items():
            result = validate_data_flow(mask, self.target_module, DataType.STRUCTURE_MASK)
            if result.valid:
                valid_structures[name] = mask
            else:
                logger.warning(f"Cấu trúc '{name}' không hợp lệ: {result.message}")
        
        # Áp dụng các biến đổi cho từng cấu trúc
        transformed_structures = {}
        for name, mask in valid_structures.items():
            transformed_mask = mask
            for transformer in self.transformers:
                try:
                    transformed_mask = transformer(transformed_mask)
                except Exception as error:
                    logger.error(f"Lỗi khi biến đổi cấu trúc '{name}': {str(error)}")
                    continue
            
            transformed_structures[name] = transformed_mask
        
        logger.info(f"Đã chuyển {len(transformed_structures)} cấu trúc từ {self.source_module} đến {self.target_module}")
        return transformed_structures

class PlanDataBridge(DataBridge[PlanConfig, PlanConfig]):
    """
    Cầu nối dữ liệu kế hoạch.
    Chuyên biệt hóa cho việc chuyển dữ liệu kế hoạch giữa các module.
    """
    
    def __init__(self, source_module: str, target_module: str):
        """
        Khởi tạo cầu nối dữ liệu kế hoạch.
        
        Args:
            source_module: Tên module nguồn
            target_module: Tên module đích
        """
        super().__init__(source_module, target_module, DataType.PLAN_CONFIG)
    
    def transfer(self, plan_config: PlanConfig) -> Optional[PlanConfig]:
        """
        Chuyển dữ liệu kế hoạch từ module nguồn sang module đích.
        
        Args:
            plan_config: Đối tượng cấu hình kế hoạch
            
        Returns:
            Đối tượng cấu hình kế hoạch đã được biến đổi, None nếu không hợp lệ
        """
        # Chuyển đổi sang dictionary để xác thực
        plan_dict = plan_config.to_dict()
        validation_result = validate_data_flow(plan_dict, self.target_module, self.data_type)
        
        if not validation_result.valid:
            logger.error(f"Cấu hình kế hoạch không hợp lệ cho {self.target_module}: {validation_result.message}")
            return None
        
        # Ghi log các cảnh báo
        for warning in validation_result.warnings:
            logger.warning(f"Cảnh báo khi chuyển kế hoạch từ {self.source_module} đến {self.target_module}: {warning}")
        
        # Áp dụng các biến đổi
        transformed_plan = plan_config
        for transformer in self.transformers:
            try:
                transformed_plan = transformer(transformed_plan)
            except Exception as error:
                logger.error(f"Lỗi khi biến đổi kế hoạch: {str(error)}")
                return None
        
        logger.info(f"Đã chuyển kế hoạch từ {self.source_module} đến {self.target_module}")
        return transformed_plan

class DoseDataBridge(DataBridge[np.ndarray, np.ndarray]):
    """
    Cầu nối dữ liệu liều.
    Chuyên biệt hóa cho việc chuyển dữ liệu liều giữa các module.
    """
    
    def __init__(self, source_module: str, target_module: str):
        """
        Khởi tạo cầu nối dữ liệu liều.
        
        Args:
            source_module: Tên module nguồn
            target_module: Tên module đích
        """
        super().__init__(source_module, target_module, DataType.DOSE_MATRIX)
        self.dose_grid_scaling = 1.0
        self.image_data = None
    
    def set_dose_grid_scaling(self, dose_grid_scaling: float):
        """
        Thiết lập hệ số liều.
        
        Args:
            dose_grid_scaling: Hệ số nhân liều (Gy)
        """
        self.dose_grid_scaling = dose_grid_scaling
    
    def set_reference_image(self, image_data: np.ndarray):
        """
        Thiết lập hình ảnh tham chiếu.
        
        Args:
            image_data: Dữ liệu hình ảnh tham chiếu
        """
        self.image_data = image_data
    
    def transfer(self, dose_data: np.ndarray) -> Optional[np.ndarray]:
        """
        Chuyển dữ liệu liều từ module nguồn sang module đích.
        
        Args:
            dose_data: Dữ liệu liều cần chuyển
            
        Returns:
            Dữ liệu liều đã được biến đổi, None nếu không hợp lệ
        """
        # Xác thực với hình ảnh tham chiếu nếu có
        validation_result = validate_data_flow(dose_data, self.target_module, self.data_type)
        
        if not validation_result.valid:
            logger.error(f"Dữ liệu liều không hợp lệ cho {self.target_module}: {validation_result.message}")
            return None
        
        # Ghi log các cảnh báo
        for warning in validation_result.warnings:
            logger.warning(f"Cảnh báo khi chuyển liều từ {self.source_module} đến {self.target_module}: {warning}")
        
        # Áp dụng các biến đổi
        transformed_dose = dose_data
        for transformer in self.transformers:
            try:
                transformed_dose = transformer(transformed_dose)
            except Exception as error:
                logger.error(f"Lỗi khi biến đổi liều: {str(error)}")
                return None
        
        logger.info(f"Đã chuyển dữ liệu liều từ {self.source_module} đến {self.target_module}")
        return transformed_dose

# Factory method để tạo các cầu nối phù hợp
def create_data_bridge(source_module: str, target_module: str, data_type: DataType) -> DataBridge:
    """
    Tạo cầu nối dữ liệu phù hợp với loại dữ liệu.
    
    Args:
        source_module: Tên module nguồn
        target_module: Tên module đích
        data_type: Loại dữ liệu
        
    Returns:
        Đối tượng cầu nối dữ liệu phù hợp
    """
    if data_type == DataType.CT_IMAGE:
        return ImageDataBridge(source_module, target_module)
    elif data_type == DataType.STRUCTURE_MASK:
        return StructureDataBridge(source_module, target_module)
    elif data_type == DataType.PLAN_CONFIG:
        return PlanDataBridge(source_module, target_module)
    elif data_type == DataType.DOSE_MATRIX:
        return DoseDataBridge(source_module, target_module)
    else:
        return DataBridge(source_module, target_module, data_type) 