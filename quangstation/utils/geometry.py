#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module cung cấp các hàm tính toán hình học cho kế hoạch xạ trị.
"""

import numpy as np
from typing import Tuple, List, Optional, Union, Dict, Any

def calculate_beam_plane(volume_data: np.ndarray, gantry_angle: float, 
                       couch_angle: float, isocenter: List[float]) -> np.ndarray:
    """
    Tính toán mặt phẳng theo hướng chùm tia (Beam's Eye View).
    
    Args:
        volume_data: Dữ liệu khối 3D (numpy array)
        gantry_angle: Góc gantry (độ)
        couch_angle: Góc bàn (độ)
        isocenter: Tọa độ tâm điều trị [x, y, z]
        
    Returns:
        Mặt phẳng 2D theo hướng chùm tia
    """
    # Chuyển đổi góc sang radian
    gantry_rad = np.radians(gantry_angle)
    couch_rad = np.radians(couch_angle)
    
    # Tính hướng chùm tia
    # Công thức tính hướng chùm tia dựa trên góc gantry và góc bàn
    # Hướng chùm tia là vector từ nguồn tới tâm điều trị
    beam_dir = np.array([
        np.sin(gantry_rad) * np.cos(couch_rad),
        np.cos(gantry_rad) * np.cos(couch_rad),
        np.sin(couch_rad)
    ])
    
    # Chuẩn hóa vector
    beam_dir = beam_dir / np.linalg.norm(beam_dir)
    
    # Tìm hai vector vuông góc với beam_dir để tạo mặt phẳng
    # Sử dụng phương pháp Gram-Schmidt để tạo hệ trực chuẩn
    if np.abs(beam_dir[2]) < 0.9:
        # Nếu chùm tia không quá gần với trục Z
        v1 = np.array([0, 0, 1])
    else:
        # Nếu chùm tia gần trục Z, chọn vector khác
        v1 = np.array([1, 0, 0])
    
    # Vector thứ nhất vuông góc với beam_dir
    u1 = v1 - np.dot(v1, beam_dir) * beam_dir
    u1 = u1 / np.linalg.norm(u1)
    
    # Vector thứ hai vuông góc với cả beam_dir và u1
    u2 = np.cross(beam_dir, u1)
    
    # Kích thước của khối dữ liệu
    depth, height, width = volume_data.shape
    
    # Xác định kích thước của mặt phẳng
    # Sử dụng kích thước lớn nhất của khối dữ liệu để đảm bảo bao phủ hết
    max_dim = max(depth, height, width)
    plane_size = int(np.sqrt(2) * max_dim)
    
    # Tạo mặt phẳng trống
    plane = np.zeros((plane_size, plane_size), dtype=np.float32)
    
    # Tọa độ tâm của khối dữ liệu
    center = np.array([depth/2, height/2, width/2])
    
    # Nếu có tọa độ tâm điều trị, sử dụng nó thay vì tâm khối
    if isocenter is not None and len(isocenter) == 3:
        center = np.array(isocenter)
        
    # Tạo lưới tọa độ cho mặt phẳng
    # Khoảng -plane_size/2 đến plane_size/2 tính từ tâm
    grid_1d = np.arange(-(plane_size//2), plane_size//2)
    grid_x, grid_y = np.meshgrid(grid_1d, grid_1d)
    
    # Tính toán tọa độ trong không gian 3D cho mỗi điểm trên mặt phẳng
    for i in range(plane_size):
        for j in range(plane_size):
            # Vị trí tương đối so với tâm trên mặt phẳng
            du = grid_x[i, j]
            dv = grid_y[i, j]
            
            # Tính tọa độ 3D
            pos = center + du * u1 + dv * u2
            
            # Kiểm tra nếu tọa độ nằm trong khối dữ liệu
            x, y, z = int(pos[0]), int(pos[1]), int(pos[2])
            if 0 <= x < depth and 0 <= y < height and 0 <= z < width:
                plane[i, j] = volume_data[x, y, z]
    
    return plane

def calculate_isocenter(structure_mask: np.ndarray, spacing: List[float]) -> List[float]:
    """
    Tính toán tâm điều trị tối ưu dựa trên cấu trúc đích (PTV).
    
    Args:
        structure_mask: Mask 3D của cấu trúc đích
        spacing: Khoảng cách giữa các pixel [dx, dy, dz]
        
    Returns:
        Tọa độ tâm điều trị [x, y, z]
    """
    # Kiểm tra xem mask có dữ liệu không
    if not np.any(structure_mask):
        return [0, 0, 0]
    
    # Tìm các vị trí có giá trị khác 0 trong mask
    positions = np.where(structure_mask > 0)
    
    # Tính tọa độ trung bình (trọng tâm)
    center = np.array([
        np.mean(positions[0]),
        np.mean(positions[1]),
        np.mean(positions[2])
    ])
    
    # Đổi sang tọa độ thực (mm) bằng cách nhân với spacing
    center_mm = center * np.array(spacing)
    
    return center_mm.tolist()

def calculate_distance(point1: List[float], point2: List[float]) -> float:
    """
    Tính khoảng cách giữa hai điểm trong không gian 3D.
    
    Args:
        point1: Tọa độ điểm thứ nhất [x, y, z]
        point2: Tọa độ điểm thứ hai [x, y, z]
        
    Returns:
        Khoảng cách Euclid giữa hai điểm
    """
    p1 = np.array(point1)
    p2 = np.array(point2)
    return np.sqrt(np.sum((p1 - p2) ** 2))

def calculate_angle(p1: List[float], p2: List[float], p3: List[float]) -> float:
    """
    Tính góc tạo bởi ba điểm trong không gian, với p2 là đỉnh.
    
    Args:
        p1: Tọa độ điểm thứ nhất [x, y, z]
        p2: Tọa độ điểm thứ hai (đỉnh) [x, y, z]
        p3: Tọa độ điểm thứ ba [x, y, z]
        
    Returns:
        Góc (độ) tạo bởi ba điểm
    """
    # Tính hai vector
    v1 = np.array(p1) - np.array(p2)
    v2 = np.array(p3) - np.array(p2)
    
    # Chuẩn hóa vector
    v1 = v1 / np.linalg.norm(v1)
    v2 = v2 / np.linalg.norm(v2)
    
    # Tính góc (radian)
    dot_product = np.clip(np.dot(v1, v2), -1.0, 1.0)
    angle_rad = np.arccos(dot_product)
    
    # Chuyển sang độ
    angle_deg = np.degrees(angle_rad)
    
    return angle_deg

def rotate_point(point: List[float], axis: List[float], angle_deg: float) -> List[float]:
    """
    Xoay một điểm quanh một trục xác định.
    
    Args:
        point: Tọa độ điểm cần xoay [x, y, z]
        axis: Vector chỉ phương của trục xoay [ax, ay, az]
        angle_deg: Góc xoay (độ)
        
    Returns:
        Tọa độ mới của điểm sau khi xoay
    """
    # Chuyển sang radian
    angle_rad = np.radians(angle_deg)
    
    # Chuẩn hóa trục xoay
    axis = np.array(axis)
    axis = axis / np.linalg.norm(axis)
    
    # Công thức xoay Rodrigues
    p = np.array(point)
    cos_ang = np.cos(angle_rad)
    sin_ang = np.sin(angle_rad)
    
    p_rot = (p * cos_ang + 
            np.cross(axis, p) * sin_ang + 
            axis * np.dot(axis, p) * (1 - cos_ang))
    
    return p_rot.tolist()

def project_point_to_plane(point: List[float], plane_point: List[float], plane_normal: List[float]) -> List[float]:
    """
    Chiếu một điểm lên một mặt phẳng.
    
    Args:
        point: Tọa độ điểm cần chiếu [x, y, z]
        plane_point: Một điểm nằm trên mặt phẳng [x, y, z]
        plane_normal: Vector pháp tuyến của mặt phẳng [nx, ny, nz]
        
    Returns:
        Tọa độ điểm chiếu [x, y, z]
    """
    # Chuẩn hóa vector pháp tuyến
    normal = np.array(plane_normal)
    normal = normal / np.linalg.norm(normal)
    
    # Tính khoảng cách từ điểm đến mặt phẳng
    p = np.array(point)
    p0 = np.array(plane_point)
    d = np.dot(p - p0, normal)
    
    # Tính điểm chiếu
    projected = p - d * normal
    
    return projected.tolist()

def interpolate_3d(volume_data: np.ndarray, point: List[float]) -> float:
    """
    Nội suy tuyến tính giá trị tại một điểm bất kỳ trong không gian 3D.
    
    Args:
        volume_data: Dữ liệu khối 3D (numpy array)
        point: Tọa độ điểm cần nội suy [x, y, z]
        
    Returns:
        Giá trị nội suy tại điểm đó
    """
    # Kích thước của khối dữ liệu
    depth, height, width = volume_data.shape
    
    # Tọa độ điểm
    x, y, z = point
    
    # Kiểm tra xem điểm có nằm trong khối dữ liệu không
    if (x < 0 or x >= depth-1 or 
        y < 0 or y >= height-1 or 
        z < 0 or z >= width-1):
        return 0.0
    
    # Tính toạ độ nguyên và phần dư
    x0, y0, z0 = int(x), int(y), int(z)
    dx, dy, dz = x - x0, y - y0, z - z0
    
    # Nội suy tuyến tính 3D
    c00 = volume_data[x0, y0, z0] * (1 - dx) + volume_data[x0+1, y0, z0] * dx
    c01 = volume_data[x0, y0, z0+1] * (1 - dx) + volume_data[x0+1, y0, z0+1] * dx
    c10 = volume_data[x0, y0+1, z0] * (1 - dx) + volume_data[x0+1, y0+1, z0] * dx
    c11 = volume_data[x0, y0+1, z0+1] * (1 - dx) + volume_data[x0+1, y0+1, z0+1] * dx
    
    c0 = c00 * (1 - dy) + c10 * dy
    c1 = c01 * (1 - dy) + c11 * dy
    
    value = c0 * (1 - dz) + c1 * dz
    
    return value 