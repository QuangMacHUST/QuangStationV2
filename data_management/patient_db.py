import sqlite3
import numpy as np

class PatientDatabase:
    def __init__(self, db_file='patients.db'):
        self.conn = sqlite3.connect(db_file)
        self.create_tables()
    
    def create_tables(self):
        """Tạo bảng cho bệnh nhân và hình ảnh"""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                id TEXT PRIMARY KEY,
                name TEXT,
                study_date TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS images (
                patient_id TEXT,
                image_data BLOB,
                FOREIGN KEY(patient_id) REFERENCES patients(id)
            )
        ''')
        self.conn.commit()
    
    def insert_patient(self, patient_info):
        """Thêm bệnh nhân"""
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO patients (id, name, study_date) VALUES (?, ?, ?)',
                       (patient_info['patient_id'], patient_info['patient_name'], patient_info['study_date']))
        self.conn.commit()
    
    def insert_image(self, patient_id, image_data):
        """Thêm hình ảnh"""
        cursor = self.conn.cursor()
        image_blob = np.array(image_data).tobytes()
        cursor.execute('INSERT INTO images (patient_id, image_data) VALUES (?, ?)',
                       (patient_id, image_blob))
        self.conn.commit()
    
    def get_patient(self, patient_id):
        """Lấy thông tin bệnh nhân"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM patients WHERE id = ?', (patient_id,))
        return cursor.fetchone()
    
    def get_image(self, patient_id):
        """Lấy hình ảnh"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT image_data FROM images WHERE patient_id = ?', (patient_id,))
        image_blob = cursor.fetchone()[0]
        image_data = np.frombuffer(image_blob, dtype=np.float32).reshape((512, 512))  # Giả sử shape
        return image_data