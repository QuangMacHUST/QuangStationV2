import tkinter as tk
from data_management.import_interface import ImportInterface
from data_management.patient_db import PatientDatabase
from data_management.display import Display

class MainApp:
    def __init__(self, root):
        self.root = root
        self.db = PatientDatabase()
        self.import_interface = ImportInterface(self.root, self.display_data)
    
    def display_data(self, patient_id):
        display = Display(self.root, patient_id, self.db)

if __name__ == "__main__":
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()