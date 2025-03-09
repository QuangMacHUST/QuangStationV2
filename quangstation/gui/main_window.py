import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
from datetime import datetime
import webbrowser

class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("QuangStation V2 - Hệ thống Lập kế hoạch Xạ trị")
        self.root.geometry("1200x800")  # Kích thước mặc định
        
        # Thiết lập style
        self.setup_styles()
        
        # Biến lưu trữ trạng thái
        self.current_patient = None
        self.current_plan = None
        self.language = "vi"  # Ngôn ngữ mặc định
        
        # Tạo menu
        self.create_menu()
        
        # Tạo widgets
        self.create_widgets()
        
        # Thiết lập statusbar
        self.create_statusbar()
        
        # Tạo thanh bên
        self.create_sidebar()
        
        # Center the window
        self.center_window()
        
        # Thiết lập sự kiện
        self.setup_events()

    def setup_styles(self):
        """Thiết lập style cho giao diện"""
        style = ttk.Style()
        
        # Cấu hình theme hiện đại
        available_themes = style.theme_names()
        if 'clam' in available_themes:
            style.theme_use('clam')
        
        # Custom styles
        style.configure('TLabel', font=('Helvetica', 11))
        style.configure('TButton', font=('Helvetica', 11), padding=5)
        style.configure('Heading.TLabel', font=('Helvetica', 14, 'bold'))
        style.configure('Title.TLabel', font=('Helvetica', 20, 'bold'))
        style.configure('Sidebar.TFrame', background='#2c3e50')
        style.configure('Sidebar.TButton', background='#2c3e50', foreground='white', borderwidth=0)
        
        # Progress bar style
        style.configure("Blue.Horizontal.TProgressbar", background='#3498db')

    def center_window(self):
        """Đặt cửa sổ vào giữa màn hình"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry('{}x{}+{}+{}'.format(width, height, x, y))

    def create_menu(self):
        """Tạo menu chính cho ứng dụng"""
        self.menu_bar = tk.Menu(self.root)
        
        # Menu File
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="Bệnh nhân mới", command=self.add_new_patient)
        file_menu.add_command(label="Mở bệnh nhân", command=self.open_patient)
        file_menu.add_separator()
        file_menu.add_command(label="Nhập DICOM", command=self.import_dicom)
        file_menu.add_command(label="Xuất kế hoạch", command=self.export_plan)
        file_menu.add_separator()
        file_menu.add_command(label="Thoát", command=self.on_exit)
        self.menu_bar.add_cascade(label="Tệp", menu=file_menu)
        
        # Menu Plan
        plan_menu = tk.Menu(self.menu_bar, tearoff=0)
        plan_menu.add_command(label="Tạo kế hoạch mới", command=self.create_new_plan)
        plan_menu.add_command(label="Sao chép kế hoạch", command=self.copy_plan)
        plan_menu.add_command(label="Xóa kế hoạch", command=self.delete_plan)
        self.menu_bar.add_cascade(label="Kế hoạch", menu=plan_menu)
        
        # Menu Công cụ
        tools_menu = tk.Menu(self.menu_bar, tearoff=0)
        tools_menu.add_command(label="Contour tự động", command=self.auto_contour)
        tools_menu.add_command(label="Tính toán liều", command=self.calculate_dose)
        tools_menu.add_command(label="Tối ưu hóa kế hoạch", command=self.optimize_plan)
        tools_menu.add_command(label="Hiển thị DVH", command=self.show_dvh)
        tools_menu.add_separator()
        tools_menu.add_command(label="Kiểm tra chất lượng", command=self.check_plan_qa)
        tools_menu.add_command(label="Cài đặt", command=self.show_settings)
        self.menu_bar.add_cascade(label="Công cụ", menu=tools_menu)
        
        # Menu Báo cáo
        report_menu = tk.Menu(self.menu_bar, tearoff=0)
        report_menu.add_command(label="Tạo báo cáo", command=self.create_report)
        report_menu.add_command(label="Xuất PDF", command=lambda: self.create_report("pdf"))
        report_menu.add_command(label="Xuất DOCX", command=lambda: self.create_report("docx"))
        report_menu.add_command(label="Xuất HTML", command=lambda: self.create_report("html"))
        self.menu_bar.add_cascade(label="Báo cáo", menu=report_menu)
        
        # Menu Trợ giúp
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        help_menu.add_command(label="Hướng dẫn sử dụng", command=self.show_help)
        help_menu.add_command(label="Kiểm tra cập nhật", command=self.check_updates)
        help_menu.add_separator()
        help_menu.add_command(label="Thông tin phần mềm", command=self.show_about)
        self.menu_bar.add_cascade(label="Trợ giúp", menu=help_menu)
        
        # Menu Ngôn ngữ
        lang_menu = tk.Menu(self.menu_bar, tearoff=0)
        lang_menu.add_command(label="Tiếng Việt", command=lambda: self.change_language("vi"))
        lang_menu.add_command(label="English", command=lambda: self.change_language("en"))
        self.menu_bar.add_cascade(label="Ngôn ngữ", menu=lang_menu)
        
        self.root.config(menu=self.menu_bar)

    def create_widgets(self):
        """Tạo giao diện chính cho ứng dụng"""
        # Frame chính
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tạo layout cơ bản
        self.create_welcome_screen()

    def create_welcome_screen(self):
        """Tạo màn hình chào mừng"""
        # Frame chứa nội dung chào mừng
        welcome_frame = ttk.Frame(self.main_frame, padding="20")
        welcome_frame.pack(fill=tk.BOTH, expand=True)
        
        # Logo hoặc banner (có thể thay bằng hình ảnh logo thực tế)
        logo_label = ttk.Label(welcome_frame, text="QuangStation V2", style="Title.TLabel")
        logo_label.pack(pady=(30, 10))
        
        # Tiêu đề phụ
        subtitle_label = ttk.Label(welcome_frame, text="Hệ thống Lập kế hoạch Xạ trị Hiện đại", style="Heading.TLabel")
        subtitle_label.pack(pady=(0, 30))
        
        # Khung chứa các nút
        button_frame = ttk.Frame(welcome_frame)
        button_frame.pack(pady=20)
        
        # Các nút chức năng chính
        new_patient_btn = ttk.Button(button_frame, text="Bệnh nhân mới", command=self.add_new_patient, width=20)
        new_patient_btn.grid(row=0, column=0, padx=10, pady=10)
        
        open_patient_btn = ttk.Button(button_frame, text="Mở bệnh nhân", command=self.open_patient, width=20)
        open_patient_btn.grid(row=0, column=1, padx=10, pady=10)
        
        import_dicom_btn = ttk.Button(button_frame, text="Nhập DICOM", command=self.import_dicom, width=20)
        import_dicom_btn.grid(row=1, column=0, padx=10, pady=10)
        
        plan_design_btn = ttk.Button(button_frame, text="Lập kế hoạch", command=self.create_new_plan, width=20)
        plan_design_btn.grid(row=1, column=1, padx=10, pady=10)
        
        # Thông tin phiên bản
        version_label = ttk.Label(welcome_frame, text="Phiên bản 2.0.0 - Bản quyền © 2023")
        version_label.pack(side=tk.BOTTOM, pady=20)
        
        # Hiển thị thời gian hiện tại
        self.time_label = ttk.Label(welcome_frame, text="")
        self.time_label.pack(side=tk.BOTTOM, pady=5)
        self.update_time()
        
        # Hiển thị tin tức hoặc thông báo mới
        news_frame = ttk.LabelFrame(welcome_frame, text="Tin tức & Cập nhật", padding=10)
        news_frame.pack(fill=tk.X, pady=20, padx=50)
        
        news_text = "• Phiên bản mới nhất: 2.0.0 - Cập nhật ngày 15/07/2023\n"
        news_text += "• Thêm các tính năng tối ưu hóa kế hoạch theo nhiều mục tiêu\n"
        news_text += "• Cải thiện hiệu suất và độ chính xác của thuật toán tính liều\n"
        news_text += "• Hỗ trợ xuất báo cáo theo nhiều định dạng: PDF, DOCX, HTML"
        
        news_label = ttk.Label(news_frame, text=news_text, wraplength=600)
        news_label.pack(pady=5)

    def create_statusbar(self):
        """Tạo thanh trạng thái ở phía dưới"""
        self.status_frame = ttk.Frame(self.root, relief=tk.SUNKEN, padding=2)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Nội dung của thanh trạng thái
        self.status_label = ttk.Label(self.status_frame, text="Sẵn sàng")
        self.status_label.pack(side=tk.LEFT)
        
        # Thông tin phiên bản và phiên làm việc
        self.session_label = ttk.Label(self.status_frame, text="Phiên: " + datetime.now().strftime("%Y%m%d_%H%M"))
        self.session_label.pack(side=tk.RIGHT, padx=10)

    def create_sidebar(self):
        """Tạo thanh bên với các chức năng chính"""
        # Frame thanh bên
        self.sidebar_frame = ttk.Frame(self.root, style="Sidebar.TFrame", width=200)
        self.sidebar_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        # Logo hoặc banner
        sidebar_title = ttk.Label(self.sidebar_frame, text="QuangStation", foreground="white", background="#2c3e50", font=("Helvetica", 14, "bold"))
        sidebar_title.pack(pady=20, padx=10)
        
        # Các nút chức năng
        patient_btn = tk.Button(self.sidebar_frame, text="Bệnh nhân", bg="#2c3e50", fg="white", bd=0, padx=10, pady=5, font=("Helvetica", 11),
                               activebackground="#34495e", activeforeground="white", width=15, anchor="w")
        patient_btn.pack(fill=tk.X, padx=5, pady=2)
        
        plan_btn = tk.Button(self.sidebar_frame, text="Kế hoạch", bg="#2c3e50", fg="white", bd=0, padx=10, pady=5, font=("Helvetica", 11),
                           activebackground="#34495e", activeforeground="white", width=15, anchor="w")
        plan_btn.pack(fill=tk.X, padx=5, pady=2)
        
        contour_btn = tk.Button(self.sidebar_frame, text="Contour", bg="#2c3e50", fg="white", bd=0, padx=10, pady=5, font=("Helvetica", 11),
                              activebackground="#34495e", activeforeground="white", width=15, anchor="w")
        contour_btn.pack(fill=tk.X, padx=5, pady=2)
        
        dose_btn = tk.Button(self.sidebar_frame, text="Tính liều", bg="#2c3e50", fg="white", bd=0, padx=10, pady=5, font=("Helvetica", 11),
                           activebackground="#34495e", activeforeground="white", width=15, anchor="w")
        dose_btn.pack(fill=tk.X, padx=5, pady=2)
        
        optimize_btn = tk.Button(self.sidebar_frame, text="Tối ưu hóa", bg="#2c3e50", fg="white", bd=0, padx=10, pady=5, font=("Helvetica", 11),
                               activebackground="#34495e", activeforeground="white", width=15, anchor="w")
        optimize_btn.pack(fill=tk.X, padx=5, pady=2)
        
        report_btn = tk.Button(self.sidebar_frame, text="Báo cáo", bg="#2c3e50", fg="white", bd=0, padx=10, pady=5, font=("Helvetica", 11),
                             activebackground="#34495e", activeforeground="white", width=15, anchor="w")
        report_btn.pack(fill=tk.X, padx=5, pady=2)
        
        # Thông tin bệnh nhân hiện tại
        ttk.Separator(self.sidebar_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=20)
        
        patient_info_label = ttk.Label(self.sidebar_frame, text="Bệnh nhân hiện tại:", foreground="white", background="#2c3e50")
        patient_info_label.pack(anchor="w", padx=10, pady=5)
        
        self.current_patient_label = ttk.Label(self.sidebar_frame, text="Chưa chọn", foreground="white", background="#2c3e50")
        self.current_patient_label.pack(anchor="w", padx=10)
        
        plan_info_label = ttk.Label(self.sidebar_frame, text="Kế hoạch hiện tại:", foreground="white", background="#2c3e50")
        plan_info_label.pack(anchor="w", padx=10, pady=5)
        
        self.current_plan_label = ttk.Label(self.sidebar_frame, text="Chưa chọn", foreground="white", background="#2c3e50")
        self.current_plan_label.pack(anchor="w", padx=10)
        
        # Nút đóng/mở thanh bên
        ttk.Separator(self.sidebar_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=20)
        
        toggle_btn = tk.Button(self.sidebar_frame, text="<<", bg="#2c3e50", fg="white", bd=0, 
                             activebackground="#34495e", activeforeground="white", command=self.toggle_sidebar)
        toggle_btn.pack(side=tk.BOTTOM, pady=10)
        
        # Khởi tạo trạng thái thanh bên
        self.sidebar_visible = True

    def toggle_sidebar(self):
        """Đóng/mở thanh bên"""
        if self.sidebar_visible:
            self.sidebar_frame.pack_forget()
            self.sidebar_visible = False
        else:
            self.sidebar_frame.pack(side=tk.LEFT, fill=tk.Y)
            self.sidebar_visible = True

    def update_time(self):
        """Cập nhật thời gian hiện tại"""
        current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.time_label.config(text=current_time)
        self.root.after(1000, self.update_time)

    def setup_events(self):
        """Thiết lập các sự kiện"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)
        
    def on_exit(self):
        """Xử lý sự kiện khi đóng ứng dụng"""
        if messagebox.askokcancel("Thoát", "Bạn có chắc muốn thoát khỏi ứng dụng?"):
            # Thực hiện lưu trạng thái và dọn dẹp tài nguyên nếu cần
            self.root.destroy()
            sys.exit()

    def start_application(self):
        """Bắt đầu ứng dụng"""
        # Ẩn màn hình chào mừng
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        # Hiển thị giao diện chính
        self.create_main_interface()

    def create_main_interface(self):
        """Tạo giao diện chính sau khi đã bắt đầu ứng dụng"""
        pass
    
    def add_new_patient(self):
        """Thêm bệnh nhân mới"""
        # Chức năng sẽ được triển khai
        self.status_label.config(text="Thêm bệnh nhân mới...")
        
    def open_patient(self):
        """Mở thông tin bệnh nhân"""
        # Chức năng sẽ được triển khai
        self.status_label.config(text="Mở thông tin bệnh nhân...")
        
    def import_dicom(self):
        """Nhập dữ liệu DICOM"""
        # Chức năng sẽ được triển khai
        self.status_label.config(text="Nhập dữ liệu DICOM...")
        
    def export_plan(self):
        """Xuất kế hoạch điều trị"""
        # Chức năng sẽ được triển khai
        self.status_label.config(text="Xuất kế hoạch điều trị...")
        
    def create_new_plan(self):
        """Tạo kế hoạch mới"""
        # Chức năng sẽ được triển khai
        self.status_label.config(text="Tạo kế hoạch điều trị mới...")
        
    def copy_plan(self):
        """Sao chép kế hoạch"""
        # Chức năng sẽ được triển khai
        self.status_label.config(text="Sao chép kế hoạch...")
        
    def delete_plan(self):
        """Xóa kế hoạch"""
        # Chức năng sẽ được triển khai
        self.status_label.config(text="Xóa kế hoạch...")
        
    def auto_contour(self):
        """Tự động phân đoạn"""
        # Chức năng sẽ được triển khai
        self.status_label.config(text="Đang thực hiện contour tự động...")
        
    def calculate_dose(self):
        """Tính toán liều"""
        # Chức năng sẽ được triển khai
        self.status_label.config(text="Đang tính toán liều...")
        
    def optimize_plan(self):
        """Tối ưu hóa kế hoạch"""
        # Chức năng sẽ được triển khai
        self.status_label.config(text="Đang tối ưu hóa kế hoạch...")
        
    def show_dvh(self):
        """Hiển thị DVH"""
        # Chức năng sẽ được triển khai
        self.status_label.config(text="Hiển thị biểu đồ DVH...")
        
    def check_plan_qa(self):
        """Kiểm tra QA kế hoạch"""
        # Chức năng sẽ được triển khai
        self.status_label.config(text="Kiểm tra chất lượng kế hoạch...")
        
    def show_settings(self):
        """Hiển thị cài đặt"""
        # Chức năng sẽ được triển khai
        self.status_label.config(text="Hiển thị cài đặt hệ thống...")
        
    def create_report(self, format="pdf"):
        """Tạo báo cáo"""
        # Chức năng sẽ được triển khai
        self.status_label.config(text=f"Đang tạo báo cáo {format.upper()}...")
        
    def show_help(self):
        """Hiển thị hướng dẫn sử dụng"""
        # Mở tài liệu hướng dẫn (có thể là trang web hoặc PDF)
        webbrowser.open("https://quangstation.com/help")
        self.status_label.config(text="Mở hướng dẫn sử dụng...")
        
    def check_updates(self):
        """Kiểm tra cập nhật"""
        # Chức năng sẽ được triển khai
        self.status_label.config(text="Đang kiểm tra cập nhật...")
        
    def show_about(self):
        """Hiển thị thông tin về phần mềm"""
        about_window = tk.Toplevel(self.root)
        about_window.title("Thông tin về QuangStation V2")
        about_window.geometry("500x400")
        about_window.resizable(False, False)
        
        # Logo
        logo_label = ttk.Label(about_window, text="QuangStation V2", style="Title.TLabel")
        logo_label.pack(pady=20)
        
        # Thông tin
        info_text = "Hệ thống Lập kế hoạch Xạ trị\n\n"
        info_text += "Phiên bản: 2.0.0\n"
        info_text += "Ngày phát hành: 15/07/2023\n\n"
        info_text += "© 2023 QuangStation Team\n"
        info_text += "Tất cả các quyền được bảo lưu."
        
        info_label = ttk.Label(about_window, text=info_text, justify=tk.CENTER)
        info_label.pack(pady=20)
        
        # Nút đóng
        close_button = ttk.Button(about_window, text="Đóng", command=about_window.destroy)
        close_button.pack(pady=20)
        
    def change_language(self, lang_code):
        """Thay đổi ngôn ngữ ứng dụng"""
        self.language = lang_code
        # Cập nhật giao diện với ngôn ngữ mới
        self.status_label.config(text=f"Đã chuyển sang ngôn ngữ: {lang_code}")
        # Cần triển khai hệ thống đa ngôn ngữ

if __name__ == "__main__":
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()
