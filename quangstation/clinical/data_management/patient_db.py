#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module quản lý dữ liệu bệnh nhân cho QuangStation V2
"""

import os
import json
import sqlite3
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import logging
import uuid
import shutil

from quangstation.core.utils.logging import get_logger
from quangstation.core.utils.config import get_config

"""
Module quản lý dữ liệu bệnh nhân cho QuangStation V2
"""

logger = get_logger(__name__)
    
class Patient:
    """Lớp đại diện cho thông tin bệnh nhân"""
    
    def __init__(self, patient_id: str = None, **kwargs):
        """
        Khởi tạo đối tượng bệnh nhân
        
        Args:
            patient_id: ID bệnh nhân (nếu không cung cấp sẽ tạo tự động)
            **kwargs: Thông tin khác về bệnh nhân (họ tên, ngày sinh, giới tính, chẩn đoán,...)
        """
        self.patient_id = patient_id or str(uuid.uuid4())
        self.created_date = kwargs.get('created_date', datetime.now().isoformat())
        self.modified_date = kwargs.get('modified_date', datetime.now().isoformat())
        self.demographics = {
            'name': kwargs.get('name', ''),
            'birth_date': kwargs.get('birth_date', ''),
            'gender': kwargs.get('gender', ''),
            'address': kwargs.get('address', ''),
            'phone': kwargs.get('phone', ''),
            'email': kwargs.get('email', '')
        }
        self.clinical_info = {
            'diagnosis': kwargs.get('diagnosis', ''),
            'diagnosis_date': kwargs.get('diagnosis_date', ''),
            'cancer_type': kwargs.get('cancer_type', ''),
            'stage': kwargs.get('stage', ''),
            'physician': kwargs.get('physician', ''),
            'notes': kwargs.get('notes', '')
        }
        self.plans = {}  # Các kế hoạch của bệnh nhân
        self.structures = {}  # Các cấu trúc/contour của bệnh nhân
        self.images = {}  # Các hình ảnh của bệnh nhân (CT, MRI,...)
        
        # Tải thêm thông tin từ kwargs
        for key, value in kwargs.items():
            if key not in ['patient_id', 'created_date', 'modified_date', 'name', 'birth_date', 
                          'gender', 'address', 'phone', 'email', 'diagnosis', 'diagnosis_date', 
                          'cancer_type', 'stage', 'physician', 'notes']:
                setattr(self, key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi thông tin bệnh nhân thành dictionary"""
        result = {
            'patient_id': self.patient_id,
            'created_date': self.created_date,
            'modified_date': self.modified_date,
            'demographics': self.demographics,
            'clinical_info': self.clinical_info
        }
        
        # Không bao gồm các dữ liệu lớn như plans, structures, images
        # vì chúng sẽ được lưu riêng
        
        return result
    
    def update(self, **kwargs) -> None:
        """
        Cập nhật thông tin bệnh nhân
        
        Args:
            **kwargs: Thông tin cần cập nhật
        """
        # Cập nhật thông tin demographics
        for key in ['name', 'birth_date', 'gender', 'address', 'phone', 'email']:
            if key in kwargs:
                self.demographics[key] = kwargs[key]
        
        # Cập nhật thông tin clinical_info
        for key in ['diagnosis', 'diagnosis_date', 'cancer_type', 'stage', 'physician', 'notes']:
            if key in kwargs:
                self.clinical_info[key] = kwargs[key]
        
        # Cập nhật các thông tin khác
        for key, value in kwargs.items():
            if key not in ['patient_id', 'created_date', 'demographics', 'clinical_info']:
                setattr(self, key, value)
        
        # Cập nhật ngày sửa đổi
        self.modified_date = datetime.now().isoformat()
    
    def add_plan(self, plan_id: str, plan_data: Dict[str, Any]) -> None:
        """
        Thêm hoặc cập nhật kế hoạch cho bệnh nhân
        
        Args:
            plan_id: ID của kế hoạch
            plan_data: Dữ liệu kế hoạch
        """
        self.plans[plan_id] = plan_data
        self.modified_date = datetime.now().isoformat()
    
    def remove_plan(self, plan_id: str) -> bool:
        """
        Xóa kế hoạch của bệnh nhân
        
        Args:
            plan_id: ID của kế hoạch cần xóa
            
        Returns:
            bool: True nếu xóa thành công, False nếu không tìm thấy kế hoạch
        """
        if plan_id in self.plans:
            del self.plans[plan_id]
            self.modified_date = datetime.now().isoformat()
            return True
        return False
    
    def add_structure(self, structure_id: str, structure_data: Dict[str, Any]) -> None:
        """
        Thêm hoặc cập nhật cấu trúc/contour cho bệnh nhân
        
        Args:
            structure_id: ID của cấu trúc
            structure_data: Dữ liệu cấu trúc
        """
        self.structures[structure_id] = structure_data
        self.modified_date = datetime.now().isoformat()
    
    def remove_structure(self, structure_id: str) -> bool:
        """
        Xóa cấu trúc của bệnh nhân
        
        Args:
            structure_id: ID của cấu trúc cần xóa
            
        Returns:
            bool: True nếu xóa thành công, False nếu không tìm thấy cấu trúc
        """
        if structure_id in self.structures:
            del self.structures[structure_id]
            self.modified_date = datetime.now().isoformat()
            return True
        return False
    
    def add_image(self, image_id: str, image_data: Dict[str, Any]) -> None:
        """
        Thêm hoặc cập nhật hình ảnh cho bệnh nhân
        
        Args:
            image_id: ID của hình ảnh
            image_data: Dữ liệu hình ảnh
        """
        self.images[image_id] = image_data
        self.modified_date = datetime.now().isoformat()
    
    def remove_image(self, image_id: str) -> bool:
        """
        Xóa hình ảnh của bệnh nhân
        
        Args:
            image_id: ID của hình ảnh cần xóa
            
        Returns:
            bool: True nếu xóa thành công, False nếu không tìm thấy hình ảnh
        """
        if image_id in self.images:
            del self.images[image_id]
            self.modified_date = datetime.now().isoformat()
            return True
        return False
    
    def __str__(self) -> str:
        """Biểu diễn chuỗi của đối tượng bệnh nhân"""
        return f"Patient: {self.demographics.get('name', '')} (ID: {self.patient_id})"


class PatientDatabase:
    """Lớp quản lý cơ sở dữ liệu bệnh nhân"""
    
    def __init__(self, db_path: str = None):
        """
        Khởi tạo cơ sở dữ liệu bệnh nhân
        
        Args:
            db_path: Đường dẫn tới file cơ sở dữ liệu (nếu None, sử dụng đường dẫn mặc định từ cấu hình)
        """
        # Lấy đường dẫn cơ sở dữ liệu từ cấu hình nếu không được cung cấp
        config = get_config()
        self.db_path = db_path or config.get("database.path")
        self.data_dir = os.path.join(config.get("workspace.root_dir"), "patients")
        
        # Đảm bảo thư mục dữ liệu tồn tại
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Khởi tạo cơ sở dữ liệu nếu chưa tồn tại
        self._init_database()
        
        # Chuẩn bị câu lệnh SQL
        self._prepare_statements()
        self.loaded_patients = {}
        self.patient_data_dir = self.data_dir
    
    def _init_database(self) -> None:
        """Khởi tạo cấu trúc cơ sở dữ liệu nếu chưa tồn tại"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tạo bảng patients nếu chưa tồn tại
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            patient_id TEXT PRIMARY KEY,
            name TEXT,
            birth_date TEXT,
            gender TEXT,
            address TEXT,
            phone TEXT,
            email TEXT,
            diagnosis TEXT,
            diagnosis_date TEXT,
            cancer_type TEXT,
            stage TEXT,
            physician TEXT,
            notes TEXT,
            created_date TEXT,
            modified_date TEXT
        )
        ''')
        
        # Tạo bảng plans nếu chưa tồn tại
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS plans (
            plan_id TEXT PRIMARY KEY,
            patient_id TEXT,
            name TEXT,
            description TEXT,
            status TEXT,
            created_date TEXT,
            modified_date TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
        )
        ''')
        
        # Tạo bảng images nếu chưa tồn tại
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS images (
            image_id TEXT PRIMARY KEY,
            patient_id TEXT,
            modality TEXT,
            description TEXT,
            created_date TEXT,
            metadata TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
        )
        ''')
        
        # Tạo bảng structures nếu chưa tồn tại
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS structures (
            structure_id TEXT PRIMARY KEY,
            patient_id TEXT,
            name TEXT,
            type TEXT,
            color TEXT,
            created_date TEXT,
            modified_date TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def _prepare_statements(self) -> None:
        """Chuẩn bị các câu lệnh SQL thường dùng"""
        self.insert_patient_stmt = '''
        INSERT OR REPLACE INTO patients (
            patient_id, name, birth_date, gender, address, phone, email,
            diagnosis, diagnosis_date, cancer_type, stage, physician, notes, created_date, modified_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        self.update_patient_stmt = '''
        UPDATE patients SET
            name = ?, birth_date = ?, gender = ?, address = ?, phone = ?, email = ?,
            diagnosis = ?, diagnosis_date = ?, cancer_type = ?, stage = ?, physician = ?, notes = ?,
            modified_date = ?
        WHERE patient_id = ?
        '''
        
        self.insert_plan_stmt = '''
        INSERT OR REPLACE INTO plans (
            plan_id, patient_id, name, description, status, created_date, modified_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        '''
        
        self.insert_image_stmt = '''
        INSERT OR REPLACE INTO images (
            image_id, patient_id, modality, description, created_date, metadata
        ) VALUES (?, ?, ?, ?, ?, ?)
        '''
        
        self.insert_structure_stmt = '''
        INSERT OR REPLACE INTO structures (
            structure_id, patient_id, name, type, color, created_date, modified_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        '''
    
    def add_patient(self, patient: Patient) -> str:
        """
        Thêm bệnh nhân vào cơ sở dữ liệu
        
        Args:
            patient: Đối tượng bệnh nhân cần thêm
            
        Returns:
            str: ID của bệnh nhân đã thêm
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Thêm vào bảng patients
            cursor.execute(self.insert_patient_stmt, (
                patient.patient_id,
                patient.demographics.get('name', ''),
                patient.demographics.get('birth_date', ''),
                patient.demographics.get('gender', ''),
                patient.demographics.get('address', ''),
                patient.demographics.get('phone', ''),
                patient.demographics.get('email', ''),
                patient.clinical_info.get('diagnosis', ''),
                patient.clinical_info.get('diagnosis_date', ''),
                patient.clinical_info.get('cancer_type', ''),
                patient.clinical_info.get('stage', ''),
                patient.clinical_info.get('physician', ''),
                patient.clinical_info.get('notes', ''),
                patient.created_date,
                patient.modified_date
            ))
            
            conn.commit()
            
            # Lưu dữ liệu chi tiết vào file JSON
            self._save_patient_data(patient)
            
            # Thêm vào danh sách đã tải
            self.loaded_patients[patient.patient_id] = patient
            
            logger.info(f"Đã thêm bệnh nhân: {patient}")
            return patient.patient_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Lỗi khi thêm bệnh nhân: {str(e)}")
            raise
    
    def _save_patient_data(self, patient: Patient) -> None:
        """
        Lưu dữ liệu chi tiết của bệnh nhân vào file JSON
        
        Args:
            patient: Đối tượng bệnh nhân
        """
        patient_dir = os.path.join(self.data_dir, patient.patient_id)
        os.makedirs(patient_dir, exist_ok=True)
        
        # Lưu thông tin chung
        with open(os.path.join(patient_dir, 'info.json'), 'w', encoding='utf-8') as f:
            json.dump(patient.to_dict(), f, indent=4)
        
        # Lưu các dữ liệu lớn
        for data_type, data in [('plans', patient.plans), ('structures', patient.structures), ('images', patient.images)]:
            data_dir = os.path.join(patient_dir, data_type)
            os.makedirs(data_dir, exist_ok=True)
            
            for key, value in data.items():
                with open(os.path.join(data_dir, f'{key}.json'), 'w', encoding='utf-8') as f:
                    json.dump(value, f, indent=4)
    
    def get_patient(self, patient_id: str):
        """Trả về đối tượng Patient từ loaded_patients nếu tồn tại, ngược lại trả về None"""
        return self.loaded_patients.get(patient_id)
    
    def patient_exists(self, patient_id: str) -> bool:
        """
        Kiểm tra xem bệnh nhân có tồn tại trong cơ sở dữ liệu hay không
        
        Args:
            patient_id: ID của bệnh nhân
            
        Returns:
            bool: True nếu bệnh nhân tồn tại, False nếu không
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM patients WHERE patient_id = ?", (patient_id,))
        return cursor.fetchone() is not None
    
    def update_patient(self, patient: Patient) -> bool:
        """
        Cập nhật thông tin bệnh nhân
        
        Args:
            patient: Đối tượng Patient cần cập nhật
            
        Returns:
            True nếu cập nhật thành công, False nếu thất bại
        """
        try:
            # Kiểm tra xem bệnh nhân có tồn tại không
            if not self.patient_exists(patient.patient_id):
                logger.error(f"Không thể cập nhật: Bệnh nhân {patient.patient_id} không tồn tại")
                return False
            
            # Cập nhật ngày sửa đổi
            patient.modified_date = datetime.now().isoformat()
            
            # Cập nhật bệnh nhân trong cơ sở dữ liệu
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Lấy dữ liệu bệnh nhân để chuẩn bị câu lệnh cập nhật
            patient_data = patient.to_dict()
            
            # Lấy thông tin cơ bản
            patient_id = patient_data.pop('patient_id')
            created_date = patient_data.pop('created_date', None)
            modified_date = patient_data.pop('modified_date')
            
            # Lấy các thông tin khác
            demographics = patient_data.get('demographics', {})
            clinical_info = patient_data.get('clinical_info', {})
            
            # Thực hiện cập nhật
            cursor.execute(
                """
                UPDATE patients 
                SET modified_date = ?,
                    name = ?,
                    birth_date = ?,
                    gender = ?,
                    address = ?,
                    phone = ?,
                    email = ?,
                    diagnosis = ?,
                    diagnosis_date = ?
                WHERE patient_id = ?
                """,
                (
                    modified_date,
                    demographics.get('name', ''),
                    demographics.get('birth_date', ''),
                    demographics.get('gender', ''),
                    demographics.get('address', ''),
                    demographics.get('phone', ''),
                    demographics.get('email', ''),
                    clinical_info.get('diagnosis', ''),
                    clinical_info.get('diagnosis_date', ''),
                    patient_id
                )
            )
            
            conn.commit()
            conn.close()
            
            # Lưu dữ liệu chi tiết của bệnh nhân
            self._save_patient_data(patient)
            
            logger.info(f"Đã cập nhật thông tin bệnh nhân {patient_id}")
            
            return True
        except Exception as error:
            logger.error(f"Lỗi khi cập nhật bệnh nhân: {error}")
            return False
    
    def insert_volume(self, patient_id: str, modality: str, volume_data: Any, metadata: Dict[str, Any]) -> str:
        """
        Chèn dữ liệu khối vào cơ sở dữ liệu
        
        Args:
            patient_id: ID của bệnh nhân
            modality: Loại hình ảnh (CT, MRI, PET,...)
            volume_data: Dữ liệu khối (numpy array)
            metadata: Metadata của khối
            
        Returns:
            ID của khối đã chèn
        """
        try:
            # Tạo ID khối
            volume_id = f"{modality.lower()}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Đảm bảo thư mục bệnh nhân tồn tại
            patient_dir = os.path.join(self.data_dir, patient_id)
            os.makedirs(patient_dir, exist_ok=True)
            
            # Thư mục lưu trữ khối
            volume_dir = os.path.join(patient_dir, "volumes")
            os.makedirs(volume_dir, exist_ok=True)
            
            # Lưu metadata
            metadata_path = os.path.join(volume_dir, f"{volume_id}_metadata.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=4)
            
            # Lưu dữ liệu khối (sử dụng numpy để lưu)
            import numpy as np
            volume_path = os.path.join(volume_dir, f"{volume_id}_data.npy")
            np.save(volume_path, volume_data)
            
            # Cập nhật cơ sở dữ liệu
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Chèn metadata cơ bản vào bảng volumes
            cursor.execute(
                "INSERT INTO volumes (volume_id, patient_id, modality, create_date, metadata_path, data_path) VALUES (?, ?, ?, ?, ?, ?)",
                (volume_id, patient_id, modality, datetime.now().isoformat(), metadata_path, volume_path)
            )
            
            conn.commit()
            conn.close()
            
            logger.info(f"Đã lưu khối {modality} cho bệnh nhân {patient_id}")
            
            return volume_id
        except Exception as error:
            logger.error(f"Lỗi khi lưu khối {modality}: {error}")
            raise
    
    def insert_rt_struct(self, patient_id: str, structures_data: Dict[str, Any]) -> str:
        """
        Chèn dữ liệu cấu trúc RT vào cơ sở dữ liệu
        
        Args:
            patient_id: ID của bệnh nhân
            structures_data: Dữ liệu cấu trúc RT
            
        Returns:
            ID của cấu trúc RT đã chèn
        """
        try:
            # Tạo ID cấu trúc
            struct_id = f"rtstruct_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Đảm bảo thư mục bệnh nhân tồn tại
            patient_dir = os.path.join(self.data_dir, patient_id)
            os.makedirs(patient_dir, exist_ok=True)
            
            # Thư mục lưu trữ cấu trúc
            struct_dir = os.path.join(patient_dir, "structures")
            os.makedirs(struct_dir, exist_ok=True)
            
            # Lưu dữ liệu cấu trúc
            struct_path = os.path.join(struct_dir, f"{struct_id}.json")
            with open(struct_path, 'w', encoding='utf-8') as f:
                json.dump(structures_data, f, indent=4)
            
            # Cập nhật cơ sở dữ liệu
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Chèn metadata cơ bản vào bảng structures
            cursor.execute(
                "INSERT INTO structures (structure_id, patient_id, create_date, data_path) VALUES (?, ?, ?, ?)",
                (struct_id, patient_id, datetime.now().isoformat(), struct_path)
            )
            
            # Thêm thông tin chi tiết cho từng cấu trúc
            for struct_name, struct_info in structures_data.items():
                if isinstance(struct_info, dict) and 'type' in struct_info:
                    cursor.execute(
                        "INSERT INTO structure_details (structure_id, name, type, color) VALUES (?, ?, ?, ?)",
                        (struct_id, struct_name, struct_info.get('type', 'UNKNOWN'), struct_info.get('color', '#FFFFFF'))
                    )
            
            conn.commit()
            conn.close()
            
            logger.info(f"Đã lưu cấu trúc RT cho bệnh nhân {patient_id}")
            
            return struct_id
        except Exception as error:
            logger.error(f"Lỗi khi lưu cấu trúc RT: {error}")
            raise
    
    def insert_rt_plan(self, patient_id: str, plan_data: Dict[str, Any]) -> str:
        """
        Chèn dữ liệu kế hoạch RT vào cơ sở dữ liệu
        
        Args:
            patient_id: ID của bệnh nhân
            plan_data: Dữ liệu kế hoạch RT
            
        Returns:
            ID của kế hoạch RT đã chèn
        """
        try:
            # Tạo ID kế hoạch
            plan_id = f"rtplan_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Đảm bảo thư mục bệnh nhân tồn tại
            patient_dir = os.path.join(self.data_dir, patient_id)
            os.makedirs(patient_dir, exist_ok=True)
            
            # Thư mục lưu trữ kế hoạch
            plan_dir = os.path.join(patient_dir, "plans")
            os.makedirs(plan_dir, exist_ok=True)
            
            # Lưu dữ liệu kế hoạch
            plan_path = os.path.join(plan_dir, f"{plan_id}.json")
            with open(plan_path, 'w', encoding='utf-8') as f:
                json.dump(plan_data, f, indent=4)
            
            # Cập nhật cơ sở dữ liệu
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Lấy tên kế hoạch nếu có
            plan_name = plan_data.get('label', 'Không có tên')
            
            # Chèn metadata cơ bản vào bảng plans
            cursor.execute(
                "INSERT INTO plans (plan_id, patient_id, plan_name, create_date, data_path) VALUES (?, ?, ?, ?, ?)",
                (plan_id, patient_id, plan_name, datetime.now().isoformat(), plan_path)
            )
            
            conn.commit()
            conn.close()
            
            logger.info(f"Đã lưu kế hoạch RT cho bệnh nhân {patient_id}")
            
            return plan_id
        except Exception as error:
            logger.error(f"Lỗi khi lưu kế hoạch RT: {error}")
            raise
    
    def insert_rt_dose(self, patient_id: str, dose_data: Any, dose_metadata: Dict[str, Any]) -> str:
        """
        Chèn dữ liệu liều RT vào cơ sở dữ liệu
        
        Args:
            patient_id: ID của bệnh nhân
            dose_data: Dữ liệu liều RT (numpy array)
            dose_metadata: Metadata của liều RT
            
        Returns:
            ID của liều RT đã chèn
        """
        try:
            # Tạo ID liều
            dose_id = f"rtdose_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Đảm bảo thư mục bệnh nhân tồn tại
            patient_dir = os.path.join(self.data_dir, patient_id)
            os.makedirs(patient_dir, exist_ok=True)
            
            # Thư mục lưu trữ liều
            dose_dir = os.path.join(patient_dir, "doses")
            os.makedirs(dose_dir, exist_ok=True)
            
            # Lưu metadata
            metadata_path = os.path.join(dose_dir, f"{dose_id}_metadata.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(dose_metadata, f, indent=4)
            
            # Lưu dữ liệu liều (sử dụng numpy để lưu)
            import numpy as np
            dose_path = os.path.join(dose_dir, f"{dose_id}_data.npy")
            np.save(dose_path, dose_data)
            
            # Cập nhật cơ sở dữ liệu
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Chèn metadata cơ bản vào bảng doses
            cursor.execute(
                "INSERT INTO doses (dose_id, patient_id, create_date, metadata_path, data_path) VALUES (?, ?, ?, ?, ?)",
                (dose_id, patient_id, datetime.now().isoformat(), metadata_path, dose_path)
            )
            
            conn.commit()
            conn.close()
            
            logger.info(f"Đã lưu liều RT cho bệnh nhân {patient_id}")
            
            return dose_id
        except Exception as error:
            logger.error(f"Lỗi khi lưu liều RT: {error}")
            raise
        finally:
            conn.close()
    
    def _load_patient_data(self, patient: Patient) -> None:
        """
        Tải dữ liệu chi tiết của bệnh nhân từ file
        
        Args:
            patient: Đối tượng bệnh nhân cần tải dữ liệu
        """
        patient_dir = os.path.join(self.patient_data_dir, patient.patient_id)
        
        # Kiểm tra thư mục có tồn tại không
        if not os.path.exists(patient_dir):
            logger.warning(f"Không tìm thấy thư mục dữ liệu của bệnh nhân: {patient.patient_id}")
            return
        
        # Tải danh sách plan_ids
        plans_file = os.path.join(patient_dir, 'plans.json')
        if os.path.exists(plans_file):
            with open(plans_file, 'r') as f:
                plan_ids = json.load(f)
                
                # Tải dữ liệu từng plan
                plans_dir = os.path.join(patient_dir, 'plans')
                for plan_id in plan_ids:
                    plan_file = os.path.join(plans_dir, f'{plan_id}.json')
                    if os.path.exists(plan_file):
                        with open(plan_file, 'r') as pf:
                            patient.plans[plan_id] = json.load(pf)
        
        # Tải danh sách image_ids
        images_file = os.path.join(patient_dir, 'images.json')
        if os.path.exists(images_file):
            with open(images_file, 'r') as f:
                image_ids = json.load(f)
                
                # Tải dữ liệu từng image
                images_dir = os.path.join(patient_dir, 'images')
                for image_id in image_ids:
                    # Tải metadata
                    image_meta_file = os.path.join(images_dir, f'{image_id}_meta.json')
                    if os.path.exists(image_meta_file):
                        with open(image_meta_file, 'r') as imf:
                            image_data = json.load(imf)
                            
                            # Tải dữ liệu hình ảnh (nếu có)
                            image_data_file = os.path.join(images_dir, f'{image_id}_data.npy')
                            if os.path.exists(image_data_file):
                                import numpy as np
                                image_data['data'] = np.load(image_data_file)
                            
                            patient.images[image_id] = image_data
        
        # Tải danh sách structure_ids
        structures_file = os.path.join(patient_dir, 'structures.json')
        if os.path.exists(structures_file):
            with open(structures_file, 'r') as f:
                structure_ids = json.load(f)
                
                # Tải dữ liệu từng structure
                structures_dir = os.path.join(patient_dir, 'structures')
                for structure_id in structure_ids:
                    # Tải metadata
                    structure_meta_file = os.path.join(structures_dir, f'{structure_id}_meta.json')
                    if os.path.exists(structure_meta_file):
                        with open(structure_meta_file, 'r') as smf:
                            structure_data = json.load(smf)
                            
                            # Tải mask (nếu có)
                            mask_file = os.path.join(structures_dir, f'{structure_id}_mask.npy')
                            if os.path.exists(mask_file):
                                import numpy as np
                                structure_data['mask'] = np.load(mask_file)
                            
                            patient.structures[structure_id] = structure_data

    def get_patient_plans(self, patient_id: str) -> List[Dict[str, Any]]:
        """
        Lấy danh sách kế hoạch của bệnh nhân
        
        Args:
            patient_id: ID bệnh nhân
            
        Returns:
            List[Dict]: Danh sách thông tin cơ bản của các kế hoạch
        """
        # Tải bệnh nhân
        patient = self.get_patient(patient_id)
        if not patient:
            return []
        
        # Lấy danh sách plan_ids
        plans = []
        for plan_id, plan_data in patient.plans.items():
            # Bổ sung plan_id vào plan_data nếu chưa có
            if 'id' not in plan_data:
                plan_data['id'] = plan_id
            plans.append(plan_data)
        
        # Sắp xếp theo ngày sửa đổi (mới nhất lên đầu)
        plans.sort(key=lambda x: x.get('modified_date', ''), reverse=True)
        
        return plans
        
    def get_plan_structures(self, plan_id: str) -> Dict[str, Any]:
        """
        Lấy danh sách cấu trúc của kế hoạch
        
        Args:
            plan_id: ID kế hoạch
            
        Returns:
            Dict[str, Any]: Dictionary các cấu trúc
        """
        # Tìm plan trong tất cả bệnh nhân
        for patient_id in self.loaded_patients.keys():
            patient = self.loaded_patients[patient_id]
            if plan_id in patient.plans:
                # Nếu tìm thấy plan, lấy cấu trúc của bệnh nhân
                return patient.structures
        
        # Nếu không tìm thấy, trả về dict rỗng
        return {}
    
    def insert_patient(self, patient_data: Dict[str, Any]) -> str:
        """
        Thêm bệnh nhân mới vào cơ sở dữ liệu
        
        Args:
            patient_data: Dictionary chứa thông tin bệnh nhân
            
        Returns:
            str: ID của bệnh nhân đã thêm
        """
        # Tạo đối tượng Patient từ dữ liệu
        patient_id = patient_data.get('patient_id', str(uuid.uuid4()))
        
        patient = Patient(
            patient_id=patient_id,
            name=patient_data.get('name', ''),
            birth_date=patient_data.get('birth_date', ''),
            gender=patient_data.get('gender', ''),
            address=patient_data.get('address', ''),
            phone=patient_data.get('phone', ''),
            email=patient_data.get('email', ''),
            diagnosis=patient_data.get('diagnosis', ''),
            diagnosis_date=patient_data.get('diagnosis_date', ''),
            cancer_type=patient_data.get('cancer_type', ''),
            stage=patient_data.get('stage', ''),
            physician=patient_data.get('physician', ''),
            notes=patient_data.get('notes', '')
        )
        
        # Thêm dữ liệu bổ sung nếu có
        if 'plans' in patient_data:
            patient.plans = patient_data['plans']
        if 'images' in patient_data:
            patient.images = patient_data['images']
        if 'structures' in patient_data:
            patient.structures = patient_data['structures']
        
        # Thêm vào cơ sở dữ liệu
        return self.add_patient(patient)
    
    def get_patient_details(self, patient_id: str) -> Dict[str, Any]:
        """
        Lấy thông tin chi tiết của bệnh nhân
        
        Args:
            patient_id: ID của bệnh nhân
            
        Returns:
            Dict[str, Any]: Thông tin chi tiết của bệnh nhân, hoặc dict rỗng nếu không tìm thấy
        """
        patient = self.get_patient(patient_id)
        if not patient:
            return {}
        
        return patient.to_dict()
    
    def get_patient_folder(self, patient_id: str) -> str:
        """
        Lấy đường dẫn đến thư mục dữ liệu của bệnh nhân
        
        Args:
            patient_id: ID của bệnh nhân
            
        Returns:
            str: Đường dẫn đến thư mục dữ liệu của bệnh nhân
        """
        patient_dir = os.path.join(self.patient_data_dir, patient_id)
        os.makedirs(patient_dir, exist_ok=True)
        return patient_dir

# Tạo instance mặc định
patient_db = PatientDatabase()