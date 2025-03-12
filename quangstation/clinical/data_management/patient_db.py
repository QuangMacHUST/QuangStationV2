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
                          'physician', 'notes']:
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
        for key in ['diagnosis', 'diagnosis_date', 'physician', 'notes']:
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
    """Lớp quản lý dữ liệu bệnh nhân"""
    
    def __init__(self, db_path: str = None):
        """
        Khởi tạo cơ sở dữ liệu bệnh nhân
        
        Args:
            db_path: Đường dẫn đến file cơ sở dữ liệu (nếu không cung cấp sẽ sử dụng đường dẫn mặc định)
        """
        # Xác định đường dẫn cơ sở dữ liệu
        self.db_path = db_path or os.path.join(
            get_config().get('data_dir', os.path.expanduser('~/.quangstation/data')),
            'patient_db.sqlite'
        )
        
        # Tạo thư mục chứa cơ sở dữ liệu nếu chưa tồn tại
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Khởi tạo kết nối cơ sở dữ liệu
        self._init_database()
        
        # Đường dẫn thư mục lưu trữ dữ liệu bệnh nhân
        self.patient_data_dir = os.path.join(
            get_config().get('data_dir', os.path.expanduser('~/.quangstation/data')),
            'patients'
        )
        os.makedirs(self.patient_data_dir, exist_ok=True)
        
        # Dữ liệu bệnh nhân đã tải
        self.loaded_patients = {}
        
        logger.info(f"Khởi tạo PatientDatabase tại {self.db_path}")
    
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
            cursor.execute('''
            INSERT OR REPLACE INTO patients (
                patient_id, name, birth_date, gender, address, phone, email,
                diagnosis, diagnosis_date, physician, notes, created_date, modified_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                patient.patient_id,
                patient.demographics.get('name', ''),
                patient.demographics.get('birth_date', ''),
                patient.demographics.get('gender', ''),
                patient.demographics.get('address', ''),
                patient.demographics.get('phone', ''),
                patient.demographics.get('email', ''),
                patient.clinical_info.get('diagnosis', ''),
                patient.clinical_info.get('diagnosis_date', ''),
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
        finally:
            conn.close()
    
    def update_patient(self, patient_id: str, patient_data: Dict[str, Any]) -> bool:
        """
        Cập nhật thông tin bệnh nhân
        
        Args:
            patient_id: ID của bệnh nhân cần cập nhật
            patient_data: Dictionary chứa thông tin cập nhật
            
        Returns:
            bool: True nếu cập nhật thành công, False nếu không tìm thấy bệnh nhân
        """
        # Lấy thông tin bệnh nhân hiện tại
        patient = self.get_patient(patient_id)
        if not patient:
            return False
        
        # Cập nhật thông tin
        if 'name' in patient_data:
            patient.demographics['name'] = patient_data['name']
        if 'birth_date' in patient_data:
            patient.demographics['birth_date'] = patient_data['birth_date']
        if 'gender' in patient_data:
            patient.demographics['gender'] = patient_data['gender']
        if 'address' in patient_data:
            patient.demographics['address'] = patient_data['address']
        if 'phone' in patient_data:
            patient.demographics['phone'] = patient_data['phone']
        if 'email' in patient_data:
            patient.demographics['email'] = patient_data['email']
        if 'diagnosis' in patient_data:
            patient.clinical_info['diagnosis'] = patient_data['diagnosis']
        if 'diagnosis_date' in patient_data:
            patient.clinical_info['diagnosis_date'] = patient_data['diagnosis_date']
        if 'physician' in patient_data:
            patient.clinical_info['physician'] = patient_data['physician']
        if 'notes' in patient_data:
            patient.clinical_info['notes'] = patient_data['notes']
        
        # Cập nhật dữ liệu bổ sung nếu có
        if 'plans' in patient_data:
            patient.plans.update(patient_data['plans'])
        if 'images' in patient_data:
            patient.images.update(patient_data['images'])
        if 'structures' in patient_data:
            patient.structures.update(patient_data['structures'])
        
        # Cập nhật thời gian sửa đổi
        patient.modified_date = datetime.now().isoformat()
        
        # Lưu vào cơ sở dữ liệu
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Cập nhật thông tin trong bảng patients
            cursor.execute('''
            UPDATE patients SET
                name = ?, birth_date = ?, gender = ?, address = ?, phone = ?, email = ?,
                diagnosis = ?, diagnosis_date = ?, physician = ?, notes = ?, modified_date = ?
            WHERE patient_id = ?
            ''', (
                patient.demographics.get('name', ''),
                patient.demographics.get('birth_date', ''),
                patient.demographics.get('gender', ''),
                patient.demographics.get('address', ''),
                patient.demographics.get('phone', ''),
                patient.demographics.get('email', ''),
                patient.clinical_info.get('diagnosis', ''),
                patient.clinical_info.get('diagnosis_date', ''),
                patient.clinical_info.get('physician', ''),
                patient.clinical_info.get('notes', ''),
                patient.modified_date,
                patient_id
            ))
            
            conn.commit()
            
            # Lưu dữ liệu chi tiết vào file JSON
            self._save_patient_data(patient)
            
            # Cập nhật trong danh sách đã tải
            self.loaded_patients[patient_id] = patient
            
            logger.info(f"Đã cập nhật bệnh nhân: {patient}")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Lỗi khi cập nhật bệnh nhân: {str(e)}")
            return False
        finally:
            conn.close()
    
    def delete_patient(self, patient_id: str) -> bool:
        """
        Xóa bệnh nhân khỏi cơ sở dữ liệu
        
        Args:
            patient_id: ID của bệnh nhân cần xóa
            
        Returns:
            bool: True nếu xóa thành công, False nếu không tìm thấy bệnh nhân
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Kiểm tra bệnh nhân có tồn tại không
            cursor.execute("SELECT patient_id FROM patients WHERE patient_id = ?", (patient_id,))
            if not cursor.fetchone():
                return False
            
            # Xóa các dữ liệu liên quan
            cursor.execute("DELETE FROM plans WHERE patient_id = ?", (patient_id,))
            cursor.execute("DELETE FROM images WHERE patient_id = ?", (patient_id,))
            cursor.execute("DELETE FROM structures WHERE patient_id = ?", (patient_id,))
            
            # Xóa bệnh nhân
            cursor.execute("DELETE FROM patients WHERE patient_id = ?", (patient_id,))
            
            conn.commit()
            
            # Xóa thư mục dữ liệu của bệnh nhân
            patient_dir = os.path.join(self.patient_data_dir, patient_id)
            if os.path.exists(patient_dir):
                shutil.rmtree(patient_dir)
            
            # Xóa khỏi danh sách đã tải
            if patient_id in self.loaded_patients:
                del self.loaded_patients[patient_id]
            
            logger.info(f"Đã xóa bệnh nhân: {patient_id}")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Lỗi khi xóa bệnh nhân: {str(e)}")
            raise
        finally:
            conn.close()
    
    def get_patient(self, patient_id: str) -> Optional[Patient]:
        """
        Lấy thông tin bệnh nhân
        
        Args:
            patient_id: ID của bệnh nhân cần lấy
            
        Returns:
            Patient: Đối tượng bệnh nhân, hoặc None nếu không tìm thấy
        """
        # Kiểm tra đã tải chưa
        if patient_id in self.loaded_patients:
            return self.loaded_patients[patient_id]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Lấy thông tin cơ bản từ cơ sở dữ liệu
            cursor.execute('''
            SELECT name, birth_date, gender, address, phone, email,
                   diagnosis, diagnosis_date, physician, notes, created_date, modified_date
            FROM patients
            WHERE patient_id = ?
            ''', (patient_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Tạo đối tượng Patient
            name, birth_date, gender, address, phone, email, diagnosis, diagnosis_date, physician, notes, created_date, modified_date = row
            
            patient = Patient(
                patient_id=patient_id,
                name=name,
                birth_date=birth_date,
                gender=gender,
                address=address,
                phone=phone,
                email=email,
                diagnosis=diagnosis,
                diagnosis_date=diagnosis_date,
                physician=physician,
                notes=notes,
                created_date=created_date,
                modified_date=modified_date
            )
            
            # Tải dữ liệu chi tiết
            self._load_patient_data(patient)
            
            # Lưu vào danh sách đã tải
            self.loaded_patients[patient_id] = patient
            
            return patient
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin bệnh nhân: {str(e)}")
            return None
        finally:
            conn.close()
    
    def get_all_patients(self) -> List[Dict[str, Any]]:
        """
        Lấy danh sách tất cả bệnh nhân (chỉ thông tin cơ bản)
        
        Returns:
            List[Dict]: Danh sách thông tin cơ bản của các bệnh nhân
        """
        conn = sqlite3.connect(self.db_path)
        
        try:
            # Lấy danh sách tất cả bệnh nhân
            query = '''
            SELECT patient_id, name, birth_date, gender, diagnosis, diagnosis_date, physician, created_date, modified_date
            FROM patients
            ORDER BY name
            '''
            
            # Sử dụng pandas để dễ xử lý dữ liệu
            df = pd.read_sql_query(query, conn)
            
            # Chuyển thành list of dicts
            patients = df.to_dict('records')
            
            return patients
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách bệnh nhân: {str(e)}")
            return []
        finally:
            conn.close()
    
    def search_patients(self, query: str) -> List[Dict[str, Any]]:
        """
        Tìm kiếm bệnh nhân theo từ khóa
        
        Args:
            query: Từ khóa tìm kiếm
            
        Returns:
            List[Dict]: Danh sách thông tin cơ bản của các bệnh nhân thỏa mãn
        """
        conn = sqlite3.connect(self.db_path)
        
        try:
            # Tìm kiếm bệnh nhân trong các trường name, diagnosis, physician
            search_query = f"%{query}%"
            sql_query = '''
            SELECT patient_id, name, birth_date, gender, diagnosis, diagnosis_date, physician, created_date, modified_date
            FROM patients
            WHERE name LIKE ? OR diagnosis LIKE ? OR physician LIKE ?
            ORDER BY name
            '''
            
            # Sử dụng pandas để dễ xử lý dữ liệu
            df = pd.read_sql_query(sql_query, conn, params=(search_query, search_query, search_query))
            
            # Chuyển thành list of dicts
            patients = df.to_dict('records')
            
            return patients
            
        except Exception as e:
            logger.error(f"Lỗi khi tìm kiếm bệnh nhân: {str(e)}")
            return []
        finally:
            conn.close()
    
    def _save_patient_data(self, patient: Patient) -> None:
        """
        Lưu dữ liệu chi tiết của bệnh nhân vào file
        
        Args:
            patient: Đối tượng bệnh nhân cần lưu
        """
        # Tạo thư mục cho bệnh nhân
        patient_dir = os.path.join(self.patient_data_dir, patient.patient_id)
        os.makedirs(patient_dir, exist_ok=True)
        
        # Lưu thông tin cơ bản vào file patient_info.json
        patient_info_file = os.path.join(patient_dir, 'patient_info.json')
        with open(patient_info_file, 'w') as f:
            json.dump(patient.to_dict(), f, indent=2)
        
        # Lưu danh sách plan_ids vào file plans.json
        plans_file = os.path.join(patient_dir, 'plans.json')
        with open(plans_file, 'w') as f:
            json.dump(list(patient.plans.keys()), f, indent=2)
        
        # Lưu danh sách image_ids vào file images.json
        images_file = os.path.join(patient_dir, 'images.json')
        with open(images_file, 'w') as f:
            json.dump(list(patient.images.keys()), f, indent=2)
        
        # Lưu danh sách structure_ids vào file structures.json
        structures_file = os.path.join(patient_dir, 'structures.json')
        with open(structures_file, 'w') as f:
            json.dump(list(patient.structures.keys()), f, indent=2)
        
        # Tạo thư mục cho các thành phần
        plans_dir = os.path.join(patient_dir, 'plans')
        os.makedirs(plans_dir, exist_ok=True)
        
        images_dir = os.path.join(patient_dir, 'images')
        os.makedirs(images_dir, exist_ok=True)
        
        structures_dir = os.path.join(patient_dir, 'structures')
        os.makedirs(structures_dir, exist_ok=True)
        
        # Lưu dữ liệu chi tiết từng plan
        for plan_id, plan_data in patient.plans.items():
            plan_file = os.path.join(plans_dir, f'{plan_id}.json')
            with open(plan_file, 'w') as f:
                json.dump(plan_data, f, indent=2)
        
        # Lưu dữ liệu chi tiết từng image (metadata)
        for image_id, image_data in patient.images.items():
            # Lưu metadata vào file JSON
            image_meta_file = os.path.join(images_dir, f'{image_id}_meta.json')
            with open(image_meta_file, 'w') as f:
                # Chỉ lưu metadata, không lưu dữ liệu hình ảnh
                meta_data = {k: v for k, v in image_data.items() if k != 'data'}
                json.dump(meta_data, f, indent=2)
            
            # Dữ liệu hình ảnh (nếu có) sẽ được lưu dưới dạng binary hoặc numpy array
            if 'data' in image_data and image_data['data'] is not None:
                import numpy as np
                image_data_file = os.path.join(images_dir, f'{image_id}_data.npy')
                np.save(image_data_file, image_data['data'])
        
        # Lưu dữ liệu chi tiết từng structure
        for structure_id, structure_data in patient.structures.items():
            # Lưu metadata vào file JSON
            structure_meta_file = os.path.join(structures_dir, f'{structure_id}_meta.json')
            with open(structure_meta_file, 'w') as f:
                # Chỉ lưu metadata, không lưu mask
                meta_data = {k: v for k, v in structure_data.items() if k != 'mask'}
                json.dump(meta_data, f, indent=2)
            
            # Dữ liệu mask (nếu có) sẽ được lưu dưới dạng numpy array
            if 'mask' in structure_data and structure_data['mask'] is not None:
                import numpy as np
                mask_file = os.path.join(structures_dir, f'{structure_id}_mask.npy')
                np.save(mask_file, structure_data['mask'])
    
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
    
    def patient_exists(self, patient_id: str) -> bool:
        """
        Kiểm tra bệnh nhân có tồn tại trong cơ sở dữ liệu không
        
        Args:
            patient_id: ID của bệnh nhân cần kiểm tra
            
        Returns:
            bool: True nếu bệnh nhân tồn tại, False nếu không
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT patient_id FROM patients WHERE patient_id = ?", (patient_id,))
            return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra bệnh nhân: {str(e)}")
            return False
        finally:
            conn.close()

# Tạo instance mặc định
patient_db = PatientDatabase()