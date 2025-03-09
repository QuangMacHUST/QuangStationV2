import pickle
import json
import os
import sqlite3
from datetime import datetime
import numpy as np

class PatientDatabase:
    def __init__(self, db_file='patients.db'):
        self.conn = sqlite3.connect(db_file)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        # Bảng thông tin bệnh nhân
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                id TEXT PRIMARY KEY,
                name TEXT,
                birth_date TEXT,
                sex TEXT,
                study_date TEXT,
                study_description TEXT,
                institution_name TEXT,
                last_modified TEXT
            )
        ''')
        # Bảng dữ liệu khối ảnh
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS volumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT,
                modality TEXT,
                depth INTEGER,
                rows INTEGER,
                cols INTEGER,
                volume_data BLOB,
                metadata BLOB,
                import_date TEXT,
                FOREIGN KEY(patient_id) REFERENCES patients(id)
            )
        ''')
        # Bảng cấu trúc RT Structure
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rt_structs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT,
                struct_data BLOB,
                import_date TEXT,
                FOREIGN KEY(patient_id) REFERENCES patients(id)
            )
        ''')
        # Bảng dữ liệu liều RT Dose
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rt_doses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT,
                dose_data BLOB,
                metadata BLOB,
                import_date TEXT,
                FOREIGN KEY(patient_id) REFERENCES patients(id)
            )
        ''')
        # Bảng kế hoạch RT Plan
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rt_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT,
                plan_data BLOB,
                import_date TEXT,
                FOREIGN KEY(patient_id) REFERENCES patients(id)
            )
        ''')
        # Bảng contours (tạo bởi người dùng)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contours (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT,
                structure_name TEXT,
                color TEXT,
                contour_data BLOB,
                creation_date TEXT,
                FOREIGN KEY(patient_id) REFERENCES patients(id)
            )
        ''')
        # Tạo chỉ mục để tăng tốc truy vấn
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_volumes_patient_modality ON volumes (patient_id, modality)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rt_structs_patient ON rt_structs (patient_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rt_doses_patient ON rt_doses (patient_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rt_plans_patient ON rt_plans (patient_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_contours_patient ON contours (patient_id)')
        self.conn.commit()
    
    def insert_patient(self, patient_info):
        """Thêm hoặc cập nhật thông tin bệnh nhân"""
        cursor = self.conn.cursor()
        current_time = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT OR REPLACE INTO patients 
            (id, name, birth_date, sex, study_date, study_description, institution_name, last_modified) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            patient_info['patient_id'],
            patient_info['patient_name'],
            patient_info.get('birth_date', ''),
            patient_info.get('sex', ''),
            patient_info.get('study_date', ''),
            patient_info.get('study_description', ''),
            patient_info.get('institution_name', ''),
            current_time
        ))
        self.conn.commit()
        return patient_info['patient_id']

    def insert_volume(self, patient_id, modality, volume_data, metadata=None):
        """Thêm dữ liệu khối ảnh"""
        cursor = self.conn.cursor()
        depth, rows, cols = volume_data.shape
        volume_blob = volume_data.tobytes()
        metadata_blob = pickle.dumps(metadata) if metadata else None
        current_time = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO volumes 
            (patient_id, modality, depth, rows, cols, volume_data, metadata, import_date) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            patient_id,
            modality,
            depth,
            rows,
            cols,
            volume_blob,
            metadata_blob,
            current_time
        ))
        self.conn.commit()
        return cursor.lastrowid

    def insert_rt_struct(self, patient_id, struct_data):
        """Thêm dữ liệu RT Structure"""
        cursor = self.conn.cursor()
        struct_blob = pickle.dumps(struct_data)
        current_time = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO rt_structs 
            (patient_id, struct_data, import_date) 
            VALUES (?, ?, ?)
        ''', (
            patient_id,
            struct_blob,
            current_time
        ))
        self.conn.commit()
        return cursor.lastrowid

    def insert_rt_dose(self, patient_id, dose_data, metadata=None):
        """Thêm dữ liệu RT Dose"""
        cursor = self.conn.cursor()
        dose_blob = dose_data.tobytes()
        metadata_blob = pickle.dumps(metadata) if metadata else None
        current_time = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO rt_doses 
            (patient_id, dose_data, metadata, import_date) 
            VALUES (?, ?, ?, ?)
        ''', (
            patient_id,
            dose_blob,
            metadata_blob,
            current_time
        ))
        self.conn.commit()
        return cursor.lastrowid

    def insert_rt_plan(self, patient_id, plan_data):
        """Thêm dữ liệu RT Plan"""
        cursor = self.conn.cursor()
        plan_blob = pickle.dumps(plan_data)
        current_time = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO rt_plans 
            (patient_id, plan_data, import_date) 
            VALUES (?, ?, ?)
        ''', (
            patient_id,
            plan_blob,
            current_time
        ))
        self.conn.commit()
        return cursor.lastrowid

    def insert_contour(self, patient_id, structure_name, contour_data, color='#FF0000'):
        """Thêm dữ liệu contour tạo bởi người dùng"""
        cursor = self.conn.cursor()
        contour_blob = pickle.dumps(contour_data)
        current_time = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO contours 
            (patient_id, structure_name, color, contour_data, creation_date) 
            VALUES (?, ?, ?, ?, ?)
        ''', (
            patient_id,
            structure_name,
            color,
            contour_blob,
            current_time
        ))
        self.conn.commit()
        return cursor.lastrowid

    def get_all_patients(self):
        """Lấy danh sách tất cả bệnh nhân"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, name, study_date, last_modified FROM patients ORDER BY last_modified DESC')
        return cursor.fetchall()

    def get_patient_info(self, patient_id):
        """Lấy thông tin chi tiết của bệnh nhân"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM patients WHERE id = ?', (patient_id,))
        result = cursor.fetchone()
        if result:
            columns = [col[0] for col in cursor.description]
            return dict(zip(columns, result))
        return None

    def get_volume(self, patient_id, modality):
        """Lấy dữ liệu khối ảnh"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT depth, rows, cols, volume_data, metadata 
            FROM volumes 
            WHERE patient_id = ? AND modality = ?
            ORDER BY import_date DESC
            LIMIT 1
        ''', (patient_id, modality))
        result = cursor.fetchone()
        if result:
            depth, rows, cols, volume_blob, metadata_blob = result
            volume = np.frombuffer(volume_blob, dtype=np.float32).reshape(depth, rows, cols)
            metadata = pickle.loads(metadata_blob) if metadata_blob else None
            return volume, metadata
        return None, None

    def get_rt_struct(self, patient_id):
        """Lấy dữ liệu RT Structure"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT struct_data 
            FROM rt_structs 
            WHERE patient_id = ?
            ORDER BY import_date DESC
            LIMIT 1
        ''', (patient_id,))
        result = cursor.fetchone()
        if result:
            return pickle.loads(result[0])
        return None

    def get_rt_dose(self, patient_id):
        """Lấy dữ liệu RT Dose"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT dose_data, metadata 
            FROM rt_doses 
            WHERE patient_id = ?
            ORDER BY import_date DESC
            LIMIT 1
        ''', (patient_id,))
        result = cursor.fetchone()
        if result:
            dose_blob, metadata_blob = result
            dose = np.frombuffer(dose_blob, dtype=np.float32)
            metadata = pickle.loads(metadata_blob) if metadata_blob else None
            if metadata and 'shape' in metadata:
                dose = dose.reshape(metadata['shape'])
            return dose, metadata
        return None, None

    def get_rt_plan(self, patient_id):
        """Lấy dữ liệu RT Plan"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT plan_data 
            FROM rt_plans 
            WHERE patient_id = ?
            ORDER BY import_date DESC
            LIMIT 1
        ''', (patient_id,))
        result = cursor.fetchone()
        if result:
            return pickle.loads(result[0])
        return None

    def get_contours(self, patient_id):
        """Lấy tất cả contours của bệnh nhân"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, structure_name, color, contour_data, creation_date 
            FROM contours 
            WHERE patient_id = ?
            ORDER BY creation_date DESC
        ''', (patient_id,))
        results = cursor.fetchall()
        contours = []
        for result in results:
            contour_id, structure_name, color, contour_blob, creation_date = result
            contour_data = pickle.loads(contour_blob)
            contours.append({
                'id': contour_id,
                'structure_name': structure_name,
                'color': color,
                'contour_data': contour_data,
                'creation_date': creation_date
            })
        return contours

    def update_contour(self, contour_id, contour_data=None, structure_name=None, color=None):
        """Cập nhật dữ liệu contour"""
        cursor = self.conn.cursor()
        current_time = datetime.now().isoformat()
        updates = []
        params = []
        
        if contour_data is not None:
            updates.append("contour_data = ?")
            params.append(pickle.dumps(contour_data))
        
        if structure_name is not None:
            updates.append("structure_name = ?")
            params.append(structure_name)
        
        if color is not None:
            updates.append("color = ?")
            params.append(color)
        
        if not updates:
            return False
        
        updates.append("creation_date = ?")
        params.append(current_time)
        params.append(contour_id)
        
        query = f"UPDATE contours SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_contour(self, contour_id):
        """Xóa contour"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM contours WHERE id = ?", (contour_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_patient(self, patient_id: str) -> bool:
        """
        Xóa bệnh nhân và tất cả dữ liệu liên quan
        
        Args:
            patient_id: ID của bệnh nhân cần xóa
            
        Returns:
            bool: True nếu xóa thành công, False nếu không
        """
        try:
            cursor = self.conn.cursor()
            # Bắt đầu transaction
            self.conn.execute('BEGIN TRANSACTION')
            
            # Xóa dữ liệu từ các bảng phụ thuộc trước
            cursor.execute('DELETE FROM contours WHERE patient_id = ?', (patient_id,))
            cursor.execute('DELETE FROM rt_plans WHERE patient_id = ?', (patient_id,))
            cursor.execute('DELETE FROM rt_doses WHERE patient_id = ?', (patient_id,))
            cursor.execute('DELETE FROM rt_structs WHERE patient_id = ?', (patient_id,))
            cursor.execute('DELETE FROM volumes WHERE patient_id = ?', (patient_id,))
            
            # Cuối cùng xóa bệnh nhân
            cursor.execute('DELETE FROM patients WHERE id = ?', (patient_id,))
            
            # Commit transaction
            self.conn.commit()
            return True
        except Exception as error:
            # Rollback transaction khi có lỗi
            self.conn.rollback()
            print(f"Lỗi khi xóa bệnh nhân: {e}")
            return False

    def close(self):
        """Đóng kết nối database"""
        if self.conn:
            self.conn.close()

    def update_patient(self, patient_id: str, update_data: dict) -> bool:
        """
        Cập nhật thông tin bệnh nhân
        
        Args:
            patient_id: ID bệnh nhân
            update_data: Dữ liệu cập nhật
            
        Returns:
            True nếu thành công, False nếu thất bại
        """
        try:
            cursor = self.conn.cursor()
            
            # Tạo chuỗi cập nhật SQL
            update_fields = []
            update_values = []
            
            for key, value in update_data.items():
                if key != 'patient_id':  # Không cập nhật patient_id
                    update_fields.append(f"{key} = ?")
                    update_values.append(value)
            
            if not update_fields:
                return False
                
            update_sql = f"UPDATE patients SET {', '.join(update_fields)} WHERE patient_id = ?"
            update_values.append(patient_id)
            
            cursor.execute(update_sql, update_values)
            self.conn.commit()
            
            return True
        except Exception as error:
            print(f"Lỗi cập nhật bệnh nhân: {e}")
            return False

    def get_patient_details(self, patient_id: str) -> dict:
        """
        Lấy chi tiết thông tin bệnh nhân
        
        Args:
            patient_id: ID bệnh nhân
            
        Returns:
            Dictionary chứa thông tin bệnh nhân
        """
        try:
            # Lưu lại row_factory hiện tại
            old_row_factory = self.conn.row_factory
            self.conn.row_factory = sqlite3.Row
            cursor = self.conn.cursor()
            
            cursor.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,))
            row = cursor.fetchone()
            
            result = {}
            if row:
                # Chuyển từ sqlite3.Row sang dict
                patient_info = {key: row[key] for key in row.keys()}
                
                # Lấy thêm danh sách nghiên cứu
                cursor.execute("SELECT * FROM studies WHERE patient_id = ?", (patient_id,))
                studies = []
                for study_row in cursor.fetchall():
                    study_dict = {key: study_row[key] for key in study_row.keys()}
                    studies.append(study_dict)
                
                patient_info['studies'] = studies
                result = patient_info
            
            # Khôi phục row_factory
            self.conn.row_factory = old_row_factory
            return result
        except Exception as error:
            print(f"Lỗi lấy thông tin bệnh nhân: {e}")
            return {}

    def search_patients(self, **kwargs) -> list:
        """
        Tìm kiếm bệnh nhân theo tiêu chí
        
        Args:
            **kwargs: Các tiêu chí tìm kiếm (name, id, etc.)
            
        Returns:
            Danh sách bệnh nhân thỏa mãn
        """
        try:
            # Lưu lại row_factory hiện tại
            old_row_factory = self.conn.row_factory
            self.conn.row_factory = sqlite3.Row
            cursor = self.conn.cursor()
            
            query = "SELECT * FROM patients WHERE 1=1"
            params = []
            
            # Xây dựng truy vấn từ các tiêu chí
            for key, value in kwargs.items():
                if value:
                    if isinstance(value, str) and '%' in value:
                        # Tìm kiếm mờ
                        query += f" AND {key} LIKE ?"
                        params.append(value)
                    else:
                        # Tìm kiếm chính xác
                        query += f" AND {key} = ?"
                        params.append(value)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                # Chuyển từ sqlite3.Row sang dict
                patient_dict = {key: row[key] for key in row.keys()}
                results.append(patient_dict)
            
            # Khôi phục row_factory
            self.conn.row_factory = old_row_factory
            return results
        except Exception as error:
            print(f"Lỗi tìm kiếm bệnh nhân: {e}")
            return []