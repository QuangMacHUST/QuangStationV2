import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Dict, Any, List, Callable, Optional
import datetime
import uuid

from quangstation.data_management.patient_db import PatientDatabase, Patient
from quangstation.utils.logging_config import get_logger

class PatientManagerGUI:
    """
    Giao diện quản lý bệnh nhân trong QuangStation V2
    """
    def __init__(self, root: tk.Toplevel, callback: Optional[Callable] = None):
        """
        Khởi tạo giao diện quản lý bệnh nhân
        
        Args:
            root: Cửa sổ gốc Tkinter
            callback: Hàm gọi lại khi chọn bệnh nhân
        """
        self.root = root
        self.root.title("Quản lý bệnh nhân - QuangStation V2")
        self.callback = callback
        self.db = PatientDatabase()
        self.logger = get_logger("PatientManagerGUI")
        
        # Biến lưu trữ
        self.patients = []
        self.selected_patient_id = None
        
        # Tạo giao diện
        self.create_widgets()
        
        # Tải danh sách bệnh nhân
        self.load_patients()
    
    def create_widgets(self):
        """Tạo các thành phần giao diện"""
        
        # Frame chính
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame tìm kiếm
        search_frame = ttk.LabelFrame(main_frame, text="Tìm kiếm", padding="5")
        search_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(search_frame, text="Từ khóa:").grid(row=0, column=0, padx=5, pady=5)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.grid(row=0, column=1, padx=5, pady=5)
        
        search_button = ttk.Button(search_frame, text="Tìm kiếm", command=self.search_patients)
        search_button.grid(row=0, column=2, padx=5, pady=5)
        
        reset_button = ttk.Button(search_frame, text="Làm mới", command=self.load_patients)
        reset_button.grid(row=0, column=3, padx=5, pady=5)
        
        # Frame danh sách bệnh nhân
        list_frame = ttk.LabelFrame(main_frame, text="Danh sách bệnh nhân", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Tạo Treeview để hiển thị danh sách bệnh nhân
        columns = ("id", "name", "birth_date", "gender", "diagnosis", "physician")
        self.patient_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        # Đặt tiêu đề cho các cột
        self.patient_tree.heading("id", text="ID")
        self.patient_tree.heading("name", text="Họ tên")
        self.patient_tree.heading("birth_date", text="Ngày sinh")
        self.patient_tree.heading("gender", text="Giới tính")
        self.patient_tree.heading("diagnosis", text="Chẩn đoán")
        self.patient_tree.heading("physician", text="Bác sĩ phụ trách")
        
        # Đặt độ rộng cho các cột
        self.patient_tree.column("id", width=50)
        self.patient_tree.column("name", width=150)
        self.patient_tree.column("birth_date", width=100)
        self.patient_tree.column("gender", width=70)
        self.patient_tree.column("diagnosis", width=200)
        self.patient_tree.column("physician", width=150)
        
        # Thêm thanh cuộn
        tree_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.patient_tree.yview)
        self.patient_tree.configure(yscrollcommand=tree_scroll.set)
        
        # Bố trí các thành phần
        self.patient_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Thêm sự kiện cho Treeview
        self.patient_tree.bind("<Double-1>", self.on_patient_selected)
        self.patient_tree.bind("<Button-3>", self.show_context_menu)
        
        # Frame nút điều khiển
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        add_button = ttk.Button(button_frame, text="Thêm mới", command=self.add_patient)
        add_button.pack(side=tk.LEFT, padx=5)
        
        edit_button = ttk.Button(button_frame, text="Chỉnh sửa", command=self.edit_patient)
        edit_button.pack(side=tk.LEFT, padx=5)
        
        delete_button = ttk.Button(button_frame, text="Xóa", command=self.delete_patient)
        delete_button.pack(side=tk.LEFT, padx=5)
        
        select_button = ttk.Button(button_frame, text="Chọn", command=self.select_patient)
        select_button.pack(side=tk.LEFT, padx=5)
        
        close_button = ttk.Button(button_frame, text="Đóng", command=self.root.destroy)
        close_button.pack(side=tk.RIGHT, padx=5)
        
        # Menu ngữ cảnh
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Chọn", command=self.select_patient)
        self.context_menu.add_command(label="Chỉnh sửa", command=self.edit_patient)
        self.context_menu.add_command(label="Xóa", command=self.delete_patient)
    
    def load_patients(self):
        """Tải danh sách bệnh nhân từ cơ sở dữ liệu"""
        # Xóa dữ liệu cũ
        for item in self.patient_tree.get_children():
            self.patient_tree.delete(item)
        
        # Lấy danh sách bệnh nhân từ cơ sở dữ liệu
        self.patients = self.db.get_all_patients()
        
        # Hiển thị danh sách bệnh nhân
        for patient in self.patients:
            values = (
                patient.get("patient_id", ""),
                patient.get("name", ""),
                patient.get("birth_date", ""),
                patient.get("gender", ""),
                patient.get("diagnosis", ""),
                patient.get("physician", "")
            )
            self.patient_tree.insert("", tk.END, values=values)
    
    def search_patients(self):
        """Tìm kiếm bệnh nhân theo từ khóa"""
        # Lấy từ khóa tìm kiếm
        query = self.search_var.get().strip()
        if not query:
            self.load_patients()
            return
        
        # Tìm kiếm bệnh nhân
        self.patients = self.db.search_patients(query)
        
        # Xóa dữ liệu cũ
        for item in self.patient_tree.get_children():
            self.patient_tree.delete(item)
        
        # Hiển thị kết quả tìm kiếm
        for patient in self.patients:
            values = (
                patient.get("patient_id", ""),
                patient.get("name", ""),
                patient.get("birth_date", ""),
                patient.get("gender", ""),
                patient.get("diagnosis", ""),
                patient.get("physician", "")
            )
            self.patient_tree.insert("", tk.END, values=values)
    
    def add_patient(self):
        """Thêm bệnh nhân mới"""
        # Tạo cửa sổ thêm bệnh nhân
        add_window = tk.Toplevel(self.root)
        add_window.title("Thêm bệnh nhân mới")
        add_window.geometry("500x500")
        add_window.transient(self.root)
        add_window.grab_set()
        
        # Tạo giao diện nhập thông tin
        main_frame = ttk.Frame(add_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame thông tin nhân khẩu học
        demo_frame = ttk.LabelFrame(main_frame, text="Thông tin nhân khẩu học", padding="5")
        demo_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(demo_frame, text="Họ tên:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        name_var = tk.StringVar()
        ttk.Entry(demo_frame, textvariable=name_var, width=30).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(demo_frame, text="Ngày sinh:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        birth_date_var = tk.StringVar()
        ttk.Entry(demo_frame, textvariable=birth_date_var, width=30).grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(demo_frame, text="(YYYY-MM-DD)").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(demo_frame, text="Giới tính:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        gender_var = tk.StringVar()
        ttk.Combobox(demo_frame, textvariable=gender_var, values=["Nam", "Nữ", "Khác"], width=10).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(demo_frame, text="Địa chỉ:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        address_var = tk.StringVar()
        ttk.Entry(demo_frame, textvariable=address_var, width=30).grid(row=3, column=1, padx=5, pady=5)
        
        ttk.Label(demo_frame, text="Điện thoại:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        phone_var = tk.StringVar()
        ttk.Entry(demo_frame, textvariable=phone_var, width=30).grid(row=4, column=1, padx=5, pady=5)
        
        ttk.Label(demo_frame, text="Email:").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        email_var = tk.StringVar()
        ttk.Entry(demo_frame, textvariable=email_var, width=30).grid(row=5, column=1, padx=5, pady=5)
        
        # Frame thông tin lâm sàng
        clinical_frame = ttk.LabelFrame(main_frame, text="Thông tin lâm sàng", padding="5")
        clinical_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(clinical_frame, text="Chẩn đoán:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        diagnosis_var = tk.StringVar()
        ttk.Entry(clinical_frame, textvariable=diagnosis_var, width=30).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(clinical_frame, text="Ngày chẩn đoán:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        diagnosis_date_var = tk.StringVar()
        ttk.Entry(clinical_frame, textvariable=diagnosis_date_var, width=30).grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(clinical_frame, text="(YYYY-MM-DD)").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(clinical_frame, text="Bác sĩ phụ trách:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        physician_var = tk.StringVar()
        ttk.Entry(clinical_frame, textvariable=physician_var, width=30).grid(row=2, column=1, padx=5, pady=5)
        
        ttk.Label(clinical_frame, text="Ghi chú:").grid(row=3, column=0, sticky=tk.NW, padx=5, pady=5)
        notes_var = tk.StringVar()
        notes_text = tk.Text(clinical_frame, width=30, height=4)
        notes_text.grid(row=3, column=1, padx=5, pady=5)
        
        # Frame nút điều khiển
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        def save_patient():
            # Kiểm tra dữ liệu
            if not name_var.get().strip():
                messagebox.showwarning("Cảnh báo", "Vui lòng nhập họ tên bệnh nhân")
                return
            
            # Tạo đối tượng Patient mới
            patient_id = str(uuid.uuid4())
            patient = Patient(patient_id=patient_id)
            
            # Cập nhật thông tin nhân khẩu học
            patient.demographics.update({
                'name': name_var.get().strip(),
                'birth_date': birth_date_var.get().strip(),
                'gender': gender_var.get(),
                'address': address_var.get().strip(),
                'phone': phone_var.get().strip(),
                'email': email_var.get().strip()
            })
            
            # Cập nhật thông tin lâm sàng
            patient.clinical_info.update({
                'diagnosis': diagnosis_var.get().strip(),
                'diagnosis_date': diagnosis_date_var.get().strip(),
                'physician': physician_var.get().strip(),
                'notes': notes_text.get("1.0", tk.END).strip()
            })
            
            try:
                # Lưu vào database
                self.db.add_patient(patient)
                messagebox.showinfo("Thông báo", "Thêm bệnh nhân thành công")
                add_window.destroy()
                self.load_patients()
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể thêm bệnh nhân: {str(e)}")
        
        save_button = ttk.Button(button_frame, text="Lưu", command=save_patient)
        save_button.pack(side=tk.RIGHT, padx=5)
        
        cancel_button = ttk.Button(button_frame, text="Hủy", command=add_window.destroy)
        cancel_button.pack(side=tk.RIGHT, padx=5)
    
    def edit_patient(self):
        """Chỉnh sửa thông tin bệnh nhân"""
        # Kiểm tra đã chọn bệnh nhân chưa
        selection = self.patient_tree.selection()
        if not selection:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn bệnh nhân cần chỉnh sửa")
            return
        
        # Lấy ID bệnh nhân đã chọn
        item = self.patient_tree.item(selection[0])
        patient_id = item["values"][0]
        
        # Lấy thông tin bệnh nhân
        patient = self.db.get_patient(patient_id)
        if not patient:
            messagebox.showerror("Lỗi", "Không thể tải thông tin bệnh nhân")
            return
        
        # Tạo cửa sổ chỉnh sửa
        edit_window = tk.Toplevel(self.root)
        edit_window.title("Chỉnh sửa thông tin bệnh nhân")
        edit_window.geometry("500x500")
        edit_window.transient(self.root)
        edit_window.grab_set()
        
        # Tạo giao diện nhập thông tin
        main_frame = ttk.Frame(edit_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame thông tin nhân khẩu học
        demo_frame = ttk.LabelFrame(main_frame, text="Thông tin nhân khẩu học", padding="5")
        demo_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(demo_frame, text="Họ tên:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        name_var = tk.StringVar(value=patient.demographics.get("name", ""))
        ttk.Entry(demo_frame, textvariable=name_var, width=30).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(demo_frame, text="Ngày sinh:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        birth_date_var = tk.StringVar(value=patient.demographics.get("birth_date", ""))
        ttk.Entry(demo_frame, textvariable=birth_date_var, width=30).grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(demo_frame, text="(YYYY-MM-DD)").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(demo_frame, text="Giới tính:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        gender_var = tk.StringVar(value=patient.demographics.get("gender", ""))
        ttk.Combobox(demo_frame, textvariable=gender_var, values=["Nam", "Nữ", "Khác"], width=10).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(demo_frame, text="Địa chỉ:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        address_var = tk.StringVar(value=patient.demographics.get("address", ""))
        ttk.Entry(demo_frame, textvariable=address_var, width=30).grid(row=3, column=1, padx=5, pady=5)
        
        ttk.Label(demo_frame, text="Điện thoại:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        phone_var = tk.StringVar(value=patient.demographics.get("phone", ""))
        ttk.Entry(demo_frame, textvariable=phone_var, width=30).grid(row=4, column=1, padx=5, pady=5)
        
        ttk.Label(demo_frame, text="Email:").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        email_var = tk.StringVar(value=patient.demographics.get("email", ""))
        ttk.Entry(demo_frame, textvariable=email_var, width=30).grid(row=5, column=1, padx=5, pady=5)
        
        # Frame thông tin lâm sàng
        clinical_frame = ttk.LabelFrame(main_frame, text="Thông tin lâm sàng", padding="5")
        clinical_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(clinical_frame, text="Chẩn đoán:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        diagnosis_var = tk.StringVar(value=patient.clinical_info.get("diagnosis", ""))
        ttk.Entry(clinical_frame, textvariable=diagnosis_var, width=30).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(clinical_frame, text="Ngày chẩn đoán:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        diagnosis_date_var = tk.StringVar(value=patient.clinical_info.get("diagnosis_date", ""))
        ttk.Entry(clinical_frame, textvariable=diagnosis_date_var, width=30).grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(clinical_frame, text="(YYYY-MM-DD)").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(clinical_frame, text="Bác sĩ phụ trách:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        physician_var = tk.StringVar(value=patient.clinical_info.get("physician", ""))
        ttk.Entry(clinical_frame, textvariable=physician_var, width=30).grid(row=2, column=1, padx=5, pady=5)
        
        ttk.Label(clinical_frame, text="Ghi chú:").grid(row=3, column=0, sticky=tk.NW, padx=5, pady=5)
        notes_text = tk.Text(clinical_frame, width=30, height=4)
        notes_text.grid(row=3, column=1, padx=5, pady=5)
        notes_text.insert("1.0", patient.clinical_info.get("notes", ""))
        
        # Frame nút điều khiển
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        def save_changes():
            # Kiểm tra dữ liệu
            if not name_var.get().strip():
                messagebox.showwarning("Cảnh báo", "Vui lòng nhập họ tên bệnh nhân")
                return
            
            # Cập nhật thông tin nhân khẩu học
            patient.demographics.update({
                'name': name_var.get().strip(),
                'birth_date': birth_date_var.get().strip(),
                'gender': gender_var.get(),
                'address': address_var.get().strip(),
                'phone': phone_var.get().strip(),
                'email': email_var.get().strip()
            })
            
            # Cập nhật thông tin lâm sàng
            patient.clinical_info.update({
                'diagnosis': diagnosis_var.get().strip(),
                'diagnosis_date': diagnosis_date_var.get().strip(),
                'physician': physician_var.get().strip(),
                'notes': notes_text.get("1.0", tk.END).strip()
            })
            
            try:
                # Lưu vào database
                patient.modified_date = datetime.datetime.now().isoformat()
                self.db.update_patient(patient)
                messagebox.showinfo("Thông báo", "Cập nhật thông tin bệnh nhân thành công")
                edit_window.destroy()
                self.load_patients()
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể cập nhật thông tin bệnh nhân: {str(e)}")
        
        save_button = ttk.Button(button_frame, text="Lưu", command=save_changes)
        save_button.pack(side=tk.RIGHT, padx=5)
        
        cancel_button = ttk.Button(button_frame, text="Hủy", command=edit_window.destroy)
        cancel_button.pack(side=tk.RIGHT, padx=5)
    
    def delete_patient(self):
        """Xóa bệnh nhân"""
        # Kiểm tra đã chọn bệnh nhân chưa
        selection = self.patient_tree.selection()
        if not selection:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn bệnh nhân cần xóa")
            return
        
        # Lấy ID bệnh nhân đã chọn
        item = self.patient_tree.item(selection[0])
        patient_id = item["values"][0]
        patient_name = item["values"][1]
        
        # Xác nhận xóa
        if not messagebox.askyesno("Xác nhận", f"Bạn có chắc chắn muốn xóa bệnh nhân '{patient_name}' không?"):
            return
        
        try:
            # Xóa bệnh nhân
            success = self.db.delete_patient(patient_id)
            if success:
                messagebox.showinfo("Thông báo", "Xóa bệnh nhân thành công")
                self.load_patients()
            else:
                messagebox.showerror("Lỗi", "Không thể xóa bệnh nhân")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi xóa bệnh nhân: {str(e)}")
    
    def select_patient(self):
        """Chọn bệnh nhân và gọi hàm callback"""
        # Kiểm tra đã chọn bệnh nhân chưa
        selection = self.patient_tree.selection()
        if not selection:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một bệnh nhân")
            return
        
        # Lấy ID bệnh nhân đã chọn
        item = self.patient_tree.item(selection[0])
        patient_id = item["values"][0]
        
        # Gọi hàm callback
        if self.callback:
            self.callback(patient_id)
            self.root.destroy()
    
    def on_patient_selected(self, event):
        """Xử lý sự kiện khi nhấp đúp vào bệnh nhân"""
        self.select_patient()
    
    def show_context_menu(self, event):
        """Hiển thị menu ngữ cảnh khi nhấp chuột phải"""
        # Kiểm tra vị trí nhấp chuột
        item = self.patient_tree.identify("item", event.x, event.y)
        if item:
            # Chọn dòng được nhấp
            self.patient_tree.selection_set(item)
            # Hiển thị menu
            self.context_menu.post(event.x_root, event.y_root)

def show_patient_manager(parent, callback=None):
    """
    Hiển thị cửa sổ quản lý bệnh nhân
    
    Args:
        parent: Widget cha
        callback: Hàm gọi lại khi chọn bệnh nhân
    """
    # Tạo cửa sổ mới
    window = tk.Toplevel(parent)
    window.geometry("800x600")
    
    # Tạo giao diện quản lý bệnh nhân
    patient_manager = PatientManagerGUI(window, callback)
    
    # Chờ cửa sổ đóng
    window.wait_window()

if __name__ == "__main__":
    # Chạy thử
    root = tk.Tk()
    root.withdraw()
    show_patient_manager(root, lambda patient_id: print(f"Đã chọn bệnh nhân: {patient_id}"))
    root.destroy()
