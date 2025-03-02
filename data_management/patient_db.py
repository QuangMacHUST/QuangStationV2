import sqlite3
import numpy as np
import pickle

class PatientDatabase:
    def __init__(self, db_file='patients.db'):
        self.conn = sqlite3.connect(db_file)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                id TEXT PRIMARY KEY,
                name TEXT,
                study_date TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS volumes (
                patient_id TEXT,
                modality TEXT,
                depth INTEGER,
                rows INTEGER,
                cols INTEGER,
                volume_data BLOB,
                FOREIGN KEY(patient_id) REFERENCES patients(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rt_structs (
                patient_id TEXT,
                struct_data BLOB,
                FOREIGN KEY(patient_id) REFERENCES patients(id)
            )
        ''')
        # Tạo chỉ mục sau khi tạo bảng
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_modality ON volumes (modality)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_patient_id ON rt_structs (patient_id)')
        self.conn.commit()
    
    def insert_patient(self, patient_info):
        cursor = self.conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO patients (id, name, study_date) VALUES (?, ?, ?)',
                       (patient_info['patient_id'], patient_info['patient_name'], patient_info['study_date']))
        self.conn.commit()

    def insert_volume(self, patient_id, modality, volume_data):
        cursor = self.conn.cursor()
        depth, rows, cols = volume_data.shape
        volume_blob = volume_data.tobytes()
        cursor.execute('INSERT INTO volumes (patient_id, modality, depth, rows, cols, volume_data) VALUES (?, ?, ?, ?, ?, ?)',
                       (patient_id, modality, depth, rows, cols, volume_blob))
        self.conn.commit()

    def insert_rt_struct(self, patient_id, struct_data):
        cursor = self.conn.cursor()
        struct_blob = pickle.dumps(struct_data)
        cursor.execute('INSERT INTO rt_structs (patient_id, struct_data) VALUES (?, ?)',
                       (patient_id, struct_blob))
        self.conn.commit()

    def get_volume(self, patient_id, modality):
        cursor = self.conn.cursor()
        cursor.execute('SELECT depth, rows, cols, volume_data FROM volumes WHERE patient_id = ? AND modality = ?',
                       (patient_id, modality))
        result = cursor.fetchone()
        if result:
            depth, rows, cols, volume_blob = result
            return np.frombuffer(volume_blob, dtype=np.float32).reshape(depth, rows, cols)
        return None

    def get_rt_struct(self, patient_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT struct_data FROM rt_structs WHERE patient_id = ?', (patient_id,))
        result = cursor.fetchone()
        return pickle.loads(result[0]) if result else None