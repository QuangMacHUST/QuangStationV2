{{ ... }}
        def start_backup():
            # Kiểm tra thư mục đích
            if not dest_path.get():
                messagebox.showerror("Lỗi", "Vui lòng chọn thư mục đích để sao lưu")
                return
            
            # Hiển thị tiến trình
            progress_window = tk.Toplevel(dialog)
            progress_window.title("Đang sao lưu...")
            progress_window.geometry("400x150")
            progress_window.resizable(False, False)
            progress_window.transient(dialog)
            progress_window.grab_set()
            
            progress_frame = ttk.Frame(progress_window, padding=20)
            progress_frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(progress_frame, text="Đang sao lưu dữ liệu, vui lòng đợi...").pack(pady=(0, 10))
            
            progress_var = tk.DoubleVar()
            progress_bar = ttk.Progressbar(progress_frame, variable=progress_var, maximum=100)
            progress_bar.pack(fill=tk.X, pady=10)
            
            status_var = tk.StringVar(value="Đang chuẩn bị sao lưu...")
            status_label = ttk.Label(progress_frame, textvariable=status_var)
            status_label.pack(anchor=tk.W, pady=5)
            
            # Đường dẫn đích
            backup_path = dest_path.get()
            
            # Tạo thư mục sao lưu với timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_folder = os.path.join(backup_path, f"quangstation_backup_{timestamp}")
            
            # Danh sách các thư mục cần sao lưu
            backup_items = []
            
            # Thêm các mục sao lưu tùy theo lựa chọn của người dùng
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
            
            if backup_patients.get():
                backup_items.append({
                    'source': os.path.join(data_dir, 'patients'),
                    'dest': os.path.join(backup_folder, 'patients'),
                    'type': 'patient'
                })
                
            if backup_plans.get():
                backup_items.append({
                    'source': os.path.join(data_dir, 'plans'),
                    'dest': os.path.join(backup_folder, 'plans'),
                    'type': 'plan'
                })
                
            if backup_images.get():
                backup_items.append({
                    'source': os.path.join(data_dir, 'images'),
                    'dest': os.path.join(backup_folder, 'images'),
                    'type': 'image'
                })
            
            # Thông tin sao lưu
            backup_info = {
                'timestamp': timestamp,
                'datetime': datetime.now().isoformat(),
                'items': [item['type'] for item in backup_items],
                'compressed': compress_data.get()
            }
            
            def perform_backup():
                try:
                    # Tạo thư mục sao lưu
                    if not os.path.exists(backup_folder):
                        os.makedirs(backup_folder)
                    
                    # Sao lưu từng mục
                    total_items = len(backup_items)
                    for i, item in enumerate(backup_items):
                        progress_percent = (i / total_items) * 80
                        status_var.set(f"Đang sao lưu {item['type']}...")
                        progress_var.set(progress_percent)
                        
                        if os.path.exists(item['source']):
                            # Sao chép thư mục
                            shutil.copytree(item['source'], item['dest'])
                        
                    # Lưu thông tin sao lưu
                    with open(os.path.join(backup_folder, 'backup_info.json'), 'w') as f:
                        json.dump(backup_info, f, indent=4)
                    
                    # Nén file nếu cần
                    if compress_data.get():
                        status_var.set("Đang nén dữ liệu...")
                        progress_var.set(90)
                        
                        # Tạo file zip
                        zip_path = f"{backup_folder}.zip"
                        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                            for root, dirs, files in os.walk(backup_folder):
                                for file in files:
                                    file_path = os.path.join(root, file)
                                    arcname = os.path.relpath(file_path, os.path.dirname(backup_folder))
                                    zipf.write(file_path, arcname)
                        
                        # Xóa thư mục tạm
                        shutil.rmtree(backup_folder)
                        backup_folder_final = zip_path
                    else:
                        backup_folder_final = backup_folder
                    
                    # Cập nhật tiến trình và trạng thái
                    progress_var.set(100)
                    status_var.set("Sao lưu hoàn tất!")
                    
                    # Lưu vào lịch sử sao lưu
                    backup_size = "0 KB"
                    if os.path.exists(backup_folder_final):
                        size_bytes = os.path.getsize(backup_folder_final) if os.path.isfile(backup_folder_final) else sum(
                            os.path.getsize(os.path.join(dirpath, filename))
                            for dirpath, _, filenames in os.walk(backup_folder_final)
                            for filename in filenames
                        )
                        
                        if size_bytes < 1024:
                            backup_size = f"{size_bytes} B"
                        elif size_bytes < 1024 * 1024:
                            backup_size = f"{size_bytes/1024:.1f} KB"
                        else:
                            backup_size = f"{size_bytes/(1024*1024):.1f} MB"
                    
                    # Thêm vào lịch sử
                    backup_date = datetime.now().strftime("%d/%m/%Y")
                    backup_time = datetime.now().strftime("%H:%M")
                    history_tree.insert("", 0, values=(backup_date, backup_time, backup_size, "Thành công"))
                    
                    # Hiển thị thông báo thành công
                    messagebox.showinfo("Sao lưu hoàn tất", 
                                      f"Đã sao lưu dữ liệu thành công tại:\n{backup_folder_final}")
                    
                    # Đóng cửa sổ tiến trình
                    progress_window.destroy()
                    dialog.destroy()
                    
                except Exception as e:
                    self.logger.error(f"Lỗi sao lưu dữ liệu: {str(e)}")
                    status_var.set(f"Lỗi: {str(e)}")
                    messagebox.showerror("Lỗi sao lưu", f"Đã xảy ra lỗi khi sao lưu: {str(e)}")
                    progress_window.destroy()
            
            # Chạy sao lưu trong thread riêng để không làm treo giao diện
            threading_import = __import__('threading')
            backup_thread = threading_import.Thread(target=perform_backup)
            backup_thread.daemon = True
            backup_thread.start()
{{ ... }}
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys
import shutil
import zipfile
import json
from datetime import datetime
import webbrowser
from PIL import Image, ImageTk
from quangstation.core.utils.logging import get_logger
from quangstation.core.utils.config import get_config
import time
from quangstation.gui.views.import_view import ImportView
"""
Module này tạo giao diện chính cho QuangStation V2
"""

class MainWindow:
    """Cửa sổ chính của ứng dụng QuangStation"""
    
    def __init__(self, root):
        """
        Khởi tạo cửa sổ chính
        
        Args:
            root: Cửa sổ Tkinter gốc
        """
        self.logger = get_logger("MainWindow")
        self.root = root
        self.root.title("QuangStation V2 - Hệ thống lập kế hoạch xạ trị")
        
        # Thiết lập biểu tượng
        self._load_icons()
        
        # Lấy cấu hình giao diện từ config
        self.theme = get_config("ui.theme", "light")
        self.font_size = get_config("ui.font_size", 10)
        window_size = get_config("ui.window_size", [1280, 800])
        maximize = get_config("ui.maximize_on_startup", False)
        
        # Thiết lập kích thước cửa sổ
        self.root.geometry(f"{window_size[0]}x{window_size[1]}")
        
        if maximize:
            self.root.state('zoomed')
        
        self.root.minsize(800, 600)
        
        # Khởi tạo biến theo dõi trạng thái
        self.current_patient = None
        self.current_plan = None
        self.sidebar_visible = True
        
        # Thiết lập biến điều khiển UI
        self.time_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Sẵn sàng")
        
        # Khởi tạo giao diện
        self.setup_styles()
        self.create_menu()
        self.create_widgets()
        self.center_window()
        self.setup_events()
        
        # Cập nhật thởi gian
        self.update_time()
        
        # Dữ liệu ứng dụng
        self.patients = {}          # Dict lưu trữ dữ liệu bệnh nhân
        self.plans = {}             # Dict lưu trữ các kế hoạch
        
        # Khởi động ứng dụng
        self.start_application()

    def _load_icons(self):
        """Tải các biểu tượng cho ứng dụng"""
        self.icons = {}
        
        # Biểu tượng ứng dụng
        try:
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                    'resources', 'icons', 'app_icon.ico')
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
                self.logger.info(f"Đã tải biểu tượng ứng dụng từ {icon_path}")
        except Exception as e:
            self.logger.warning(f"Không thể tải biểu tượng ứng dụng: {str(e)}")
        
        # Thư mục chứa các biểu tượng
        icons_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                              'resources', 'icons')
        
        # Tải các biểu tượng thanh công cụ
        toolbar_dir = os.path.join(icons_dir, 'toolbar')
        if os.path.exists(toolbar_dir):
            self.icons['toolbar'] = {}
            for icon_file in os.listdir(toolbar_dir):
                if icon_file.endswith('.png'):
                    name = os.path.splitext(icon_file)[0]
                    try:
                        img = Image.open(os.path.join(toolbar_dir, icon_file))
                        icon = ImageTk.PhotoImage(img)
                        self.icons['toolbar'][name] = icon
                        self.logger.debug(f"Đã tải biểu tượng toolbar: {name}")
                    except Exception as e:
                        self.logger.warning(f"Không thể tải biểu tượng toolbar {name}: {str(e)}")
        
        # Tải các biểu tượng menu
        menu_dir = os.path.join(icons_dir, 'menu')
        if os.path.exists(menu_dir):
            self.icons['menu'] = {}
            for icon_file in os.listdir(menu_dir):
                if icon_file.endswith('.png'):
                    name = os.path.splitext(icon_file)[0]
                    try:
                        img = Image.open(os.path.join(menu_dir, icon_file))
                        img = img.resize((20, 20), Image.LANCZOS)  # Điều chỉnh kích thước cho menu
                        icon = ImageTk.PhotoImage(img)
                        self.icons['menu'][name] = icon
                        self.logger.debug(f"Đã tải biểu tượng menu: {name}")
                    except Exception as e:
                        self.logger.warning(f"Không thể tải biểu tượng menu {name}: {str(e)}")
        
        # Tải các biểu tượng nút
        buttons_dir = os.path.join(icons_dir, 'buttons')
        if os.path.exists(buttons_dir):
            self.icons['buttons'] = {}
            for icon_file in os.listdir(buttons_dir):
                if icon_file.endswith('.png'):
                    name = os.path.splitext(icon_file)[0]
                    try:
                        img = Image.open(os.path.join(buttons_dir, icon_file))
                        img = img.resize((24, 24), Image.LANCZOS)  # Điều chỉnh kích thước cho nút
                        icon = ImageTk.PhotoImage(img)
                        self.icons['buttons'][name] = icon
                        self.logger.debug(f"Đã tải biểu tượng nút: {name}")
                    except Exception as e:
                        self.logger.warning(f"Không thể tải biểu tượng nút {name}: {str(e)}")

    def setup_styles(self):
        """Thiết lập style cho giao diện"""
        style = ttk.Style()
        
        # Cấu hình theme hiện đại
        available_themes = style.theme_names()
        if 'clam' in available_themes:
            style.theme_use('clam')
        
        # Custom styles
        style.configure('TLabel', font=('Helvetica', self.font_size))
        style.configure('TButton', font=('Helvetica', self.font_size), padding=5)
        style.configure('Heading.TLabel', 
                      font=('Helvetica', 14, 'bold'), 
                      foreground="#0066CC",
                      background="#f0f0f0")
        style.configure('Title.TLabel', font=('Helvetica', 20, 'bold'))
        style.configure('Sidebar.TFrame', background='#2c3e50')
        style.configure('Sidebar.TButton', background='#2c3e50', foreground='white', borderwidth=0)
        
        # Progress bar style
        style.configure("Blue.Horizontal.TProgressbar", background='#3498db')

    def center_window(self):
        """Căn giữa cửa sổ trên màn hình"""
        self.root.update_idletasks()
        
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        
        self.root.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        
    def update_time(self):
        """Cập nhật thởi gian hiển thị"""
        current_time = time.strftime("%H:%M:%S - %d/%m/%Y")
        self.time_var.set(current_time)
        
        # Gọi lại sau 1 giây
        self.root.after(1000, self.update_time)
        
    def setup_events(self):
        """Thiết lập các sự kiện"""
        # Sự kiện khi đóng cửa sổ
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)
        
    def on_exit(self):
        """Xử lý sự kiện khi thoát chương trình"""
        if messagebox.askokcancel("Thoát", "Bạn có chắc muốn thoát không?"):
            self.root.destroy()
            
    def toggle_sidebar(self):
        """Ẩn/hiện thanh sidebar"""
        if self.sidebar_visible:
            self.sidebar.pack_forget()
            self.sidebar_visible = False
        else:
            self.sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=0, pady=0)
            self.sidebar_visible = True
            
    def start_application(self):
        """Khởi động ứng dụng"""
        # Kiểm tra cấu hình, khởi tạo cơ sở dữ liệu, v.v.
        self.logger.info("Khởi động ứng dụng...")
        
        # Thiết lập giao diện chính
        self.create_main_interface()
        
    def create_main_interface(self):
        """Thiết lập giao diện chính của ứng dụng"""
        # Thực hiện các thao tác thiết lập giao diện chính
        self.status_var.set("Đã sẵn sàng")

    def create_menu(self):
        """Tạo menu chính cho ứng dụng"""
        # Menu chính
        menubar = tk.Menu(self.root)
        
        # Menu File
        file_menu = tk.Menu(menubar, tearoff=0)
        if 'menu' in self.icons and 'new' in self.icons['menu']:
            file_menu.add_command(label="Bệnh nhân mới", image=self.icons['menu']['new'], 
                                compound='left', command=self.add_new_patient)
        else:
            file_menu.add_command(label="Bệnh nhân mới", command=self.add_new_patient)
            
        if 'menu' in self.icons and 'open' in self.icons['menu']:
            file_menu.add_command(label="Mở bệnh nhân", image=self.icons['menu']['open'], 
                                compound='left', command=self.open_patient)
        else:
            file_menu.add_command(label="Mở bệnh nhân", command=self.open_patient)
            
        file_menu.add_separator()
        
        if 'menu' in self.icons and 'open' in self.icons['menu']:
            file_menu.add_command(label="Nhập DICOM", image=self.icons['menu']['open'], 
                                compound='left', command=self.import_dicom)
        else:
            file_menu.add_command(label="Nhập DICOM", command=self.import_dicom)
            
        if 'menu' in self.icons and 'save' in self.icons['menu']:
            file_menu.add_command(label="Xuất kế hoạch", image=self.icons['menu']['save'], 
                                compound='left', command=self.export_plan)
        else:
            file_menu.add_command(label="Xuất kế hoạch", command=self.export_plan)
            
        file_menu.add_separator()
        
        if 'menu' in self.icons and 'exit' in self.icons['menu']:
            file_menu.add_command(label="Thoát", image=self.icons['menu']['exit'], 
                                compound='left', command=self.on_exit)
        else:
            file_menu.add_command(label="Thoát", command=self.on_exit)
            
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Menu Plan
        plan_menu = tk.Menu(menubar, tearoff=0)
        plan_menu.add_command(label="Tạo kế hoạch mới", command=self.create_new_plan)
        plan_menu.add_command(label="Sao chép kế hoạch", command=self.copy_plan)
        plan_menu.add_command(label="Xóa kế hoạch", command=self.delete_plan)
        plan_menu.add_separator()
        plan_menu.add_command(label="Tạo contour tự động", command=self.auto_contour)
        plan_menu.add_command(label="Tính toán liều", command=self.calculate_dose)
        plan_menu.add_command(label="Tối ưu hóa kế hoạch", command=self.optimize_plan)
        plan_menu.add_command(label="Hiển thị DVH", command=self.show_dvh)
        plan_menu.add_separator()
        plan_menu.add_command(label="Tối ưu KBP", command=self.kbp_optimize)
        plan_menu.add_command(label="Công cụ huấn luyện KBP", command=self.open_kbp_trainer)
        menubar.add_cascade(label="Kế hoạch", menu=plan_menu)
        
        # Menu Tools
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Kiểm tra chất lượng kế hoạch", command=self.check_plan_qa)
        tools_menu.add_command(label="Sao lưu dữ liệu", command=self.backup_data, accelerator="Ctrl+B")
        tools_menu.add_separator()
        tools_menu.add_command(label="Tạo báo cáo", command=self.create_report)
        menubar.add_cascade(label="Công cụ", menu=tools_menu)
        
        # Menu Help
        help_menu = tk.Menu(menubar, tearoff=0)
        if 'menu' in self.icons and 'help' in self.icons['menu']:
            help_menu.add_command(label="Hướng dẫn sử dụng", image=self.icons['menu']['help'], 
                                 compound='left', command=self.show_help)
        else:
            help_menu.add_command(label="Hướng dẫn sử dụng", command=self.show_help)
            
        help_menu.add_command(label="Kiểm tra cập nhật", command=self.check_updates)
        
        if 'menu' in self.icons and 'about' in self.icons['menu']:
            help_menu.add_command(label="Giới thiệu", image=self.icons['menu']['about'], 
                                 compound='left', command=self.show_about)
        else:
            help_menu.add_command(label="Giới thiệu", command=self.show_about)
            
        menubar.add_cascade(label="Trợ giúp", menu=help_menu)
        
        # Đặt menu vào cửa sổ
        self.root.config(menu=menubar)

    def create_widgets(self):
        """Tạo các widget cho giao diện chính"""
        # Tạo main frame chứa các widget chính
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tạo thanh công cụ
        self.create_toolbar()
        
        # Tạo frame nội dung (chứa sidebar và content)
        self.content_container = ttk.Frame(self.main_frame)
        self.content_container.pack(fill=tk.BOTH, expand=True)
        
        # Tạo sidebar bên trái
        self.create_sidebar()
        
        # Tạo frame nội dung chính
        self.content_frame = ttk.Frame(self.content_container)
        self.content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Hiển thị màn hình chào mừng
        self.create_welcome_screen()
        
        # Tạo thanh trạng thái
        self.create_statusbar()

    def create_toolbar(self):
        """Tạo thanh công cụ với các biểu tượng"""
        # Frame chứa toolbar
        self.toolbar_frame = ttk.Frame(self.main_frame, style='Toolbar.TFrame')
        self.toolbar_frame.pack(side=tk.TOP, fill=tk.X)
        
        # Tạo các nút trên toolbar
        toolbar_buttons = [
            {"name": "patient", "text": "Bệnh nhân", "command": self.add_new_patient, "tooltip": "Tạo bệnh nhân mới"},
            {"name": "plan", "text": "Kế hoạch", "command": self.create_new_plan, "tooltip": "Tạo kế hoạch mới"},
            {"name": "beam", "text": "Chùm tia", "command": self.open_patient, "tooltip": "Chỉnh sửa chùm tia"},
            {"name": "dose", "text": "Liều", "command": self.calculate_dose, "tooltip": "Tính toán liều"},
            {"name": "contour", "text": "Contour", "command": self.auto_contour, "tooltip": "Tạo contour tự động"},
            {"name": "optimize", "text": "Tối ưu", "command": self.optimize_plan, "tooltip": "Tối ưu hóa kế hoạch"},
            {"name": "report", "text": "Báo cáo", "command": self.create_report, "tooltip": "Tạo báo cáo"},
            {"name": "export", "text": "Xuất", "command": self.export_plan, "tooltip": "Xuất kế hoạch"},
            {"name": "settings", "text": "Cài đặt", "command": self.show_settings, "tooltip": "Cài đặt hệ thống"}
        ]
        
        # Frame chứa nút
        buttons_frame = ttk.Frame(self.toolbar_frame)
        buttons_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)
        
        # Tạo các nút
        for i, btn_info in enumerate(toolbar_buttons):
            btn = ttk.Button(
                buttons_frame, 
                text=btn_info["text"],
                command=btn_info["command"],
                style='Toolbar.TButton'
            )
            
            # Thêm biểu tượng nếu có
            if 'toolbar' in self.icons and btn_info["name"] in self.icons['toolbar']:
                btn.configure(image=self.icons['toolbar'][btn_info["name"]], compound=tk.TOP)
            
            btn.pack(side=tk.LEFT, padx=5, pady=2)
            
            # Tạo tooltip
            self._create_tooltip(btn, btn_info["tooltip"])
            
        # Thêm frame khoảng cách
        ttk.Frame(self.toolbar_frame).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Thêm nút trợ giúp bên phải
        help_frame = ttk.Frame(self.toolbar_frame)
        help_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=2)
        
        help_btn = ttk.Button(help_frame, text="Trợ giúp", command=self.show_help)
        help_btn.pack(side=tk.RIGHT, padx=5)
        
        # Thêm biểu tượng nếu có
        if 'menu' in self.icons and 'help' in self.icons['menu']:
            help_btn.configure(image=self.icons['menu']['help'], compound=tk.LEFT)
        
        # Thêm đường phân cách
        separator = ttk.Separator(self.toolbar_frame, orient=tk.HORIZONTAL)
        separator.pack(fill=tk.X, pady=2)

    def _create_tooltip(self, widget, text):
        """Tạo tooltip cho widget"""
        def enter(event):
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25
            
            # Tạo cửa sổ tooltip
            self.tooltip = tk.Toplevel(widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            
            label = ttk.Label(self.tooltip, text=text, background="#ffffe0", relief="solid", borderwidth=1)
            label.pack()
            
        def leave(event):
            if hasattr(self, 'tooltip'):
                self.tooltip.destroy()
                
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    def create_welcome_screen(self):
        """Tạo màn hình chào mừng hiện đại với nhiều thẻ và hình ảnh"""
        # Xóa nội dung cũ của content_frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        # Lưu tham chiếu đến welcome_frame
        self.welcome_frame = ttk.Frame(self.content_frame)
        self.welcome_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tạo style cho các phần tử của welcome screen
        welcome_style = ttk.Style()
        welcome_style.configure("Welcome.TFrame", background="#f0f0f0")
        welcome_style.configure("WelcomeHeader.TLabel", 
                              font=('Helvetica', 24, 'bold'), 
                              foreground="#0066CC",
                              background="#f0f0f0")
        welcome_style.configure("WelcomeDesc.TLabel", 
                              font=('Helvetica', 12), 
                              foreground="#333333",
                              background="#f0f0f0")
        welcome_style.configure("CardTitle.TLabel", 
                              font=('Helvetica', 14, 'bold'), 
                              foreground="#0066CC")
        welcome_style.configure("CardDesc.TLabel", 
                              font=('Helvetica', 10), 
                              foreground="#333333")
        welcome_style.configure("Welcome.TButton", 
                              font=('Helvetica', 11))
        
        # Frame chính có background
        main_frame = ttk.Frame(self.welcome_frame, style="Welcome.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Nạp hình nền
        bg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                            'resources', 'images', 'welcome_background.jpg')
        
        if os.path.exists(bg_path):
            try:
                from PIL import Image, ImageTk, ImageFilter, ImageEnhance
                
                # Lấy kích thước của content_frame
                self.content_frame.update()
                width = self.content_frame.winfo_width() or 1200
                height = self.content_frame.winfo_height() or 800
                
                # Nạp và xử lý hình nền
                bg_img = Image.open(bg_path)
                bg_img = bg_img.resize((width, height), Image.LANCZOS)
                
                # Làm mờ nhẹ hình nền và điều chỉnh độ sáng
                bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=1))
                enhancer = ImageEnhance.Brightness(bg_img)
                bg_img = enhancer.enhance(1.2)
                
                # Chuyển đổi thành PhotoImage
                self.bg_photo = ImageTk.PhotoImage(bg_img)
                
                # Tạo canvas để hiển thị hình nền
                self.bg_canvas = tk.Canvas(main_frame, width=width, height=height, 
                                          highlightthickness=0)
                self.bg_canvas.pack(fill=tk.BOTH, expand=True)
                self.bg_canvas.create_image(0, 0, anchor=tk.NW, image=self.bg_photo)
                
                # Tạo overlay bán trong suốt
                self.bg_canvas.create_rectangle(0, 0, width, height, 
                                              fill='white', stipple='gray50')
                
                # Container cho nội dung
                content_container = ttk.Frame(self.bg_canvas)
                self.bg_canvas.create_window(width//2, height//2, window=content_container)
                
            except Exception as e:
                self.logger.warning(f"Không thể tải hình nền: {str(e)}")
                content_container = ttk.Frame(main_frame, style="Welcome.TFrame")
                content_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        else:
            content_container = ttk.Frame(main_frame, style="Welcome.TFrame")
            content_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Frame tiêu đề
        header_frame = ttk.Frame(content_container, style="Welcome.TFrame")
        header_frame.pack(fill=tk.X, pady=(20, 30))
        
        # Tiêu đề chào mừng
        welcome_label = ttk.Label(
            header_frame, 
            text="Chào mừng đến với QuangStation V2", 
            style="WelcomeHeader.TLabel"
        )
        welcome_label.pack(anchor=tk.CENTER)
        
        # Mô tả ngắn
        desc_label = ttk.Label(
            header_frame, 
            text="Hệ thống lập kế hoạch xạ trị mã nguồn mở tiên tiến cho y học hiện đại", 
            style="WelcomeDesc.TLabel"
        )
        desc_label.pack(anchor=tk.CENTER, pady=(5, 0))
        
        # Tạo notebook để chứa các thẻ
        notebook = ttk.Notebook(content_container)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # ===== Thẻ 1: Chức năng chính =====
        functions_tab = ttk.Frame(notebook, style="Welcome.TFrame")
        notebook.add(functions_tab, text="Chức năng chính")
        
        # Container cho các card
        cards_frame = ttk.Frame(functions_tab, style="Welcome.TFrame")
        cards_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Danh sách chức năng
        functions = [
            {
                "icon": "patient", 
                "title": "Quản lý bệnh nhân", 
                "desc": "Tạo và quản lý hồ sơ bệnh nhân, nhập dữ liệu DICOM", 
                "command": self.add_new_patient,
                "image": "patient_care.jpg"
            },
            {
                "icon": "plan", 
                "title": "Thiết kế kế hoạch", 
                "desc": "Tạo kế hoạch xạ trị với nhiều kỹ thuật khác nhau", 
                "command": self.create_new_plan,
                "image": "doctor_planning.jpg"
            },
            {
                "icon": "dose", 
                "title": "Tính toán liều", 
                "desc": "Tính toán phân bố liều với nhiều thuật toán", 
                "command": self.calculate_dose,
                "image": "radiation_therapy.jpg"
            },
            {
                "icon": "contour", 
                "title": "Tự động phân đoạn", 
                "desc": "Phân đoạn cấu trúc tự động với AI", 
                "command": self.auto_contour,
                "image": None
            },
            {
                "icon": "optimize", 
                "title": "Tối ưu hóa kế hoạch", 
                "desc": "Tối ưu hóa kế hoạch xạ trị theo các tiêu chí", 
                "command": self.optimize_plan,
                "image": None
            },
            {
                "icon": "report", 
                "title": "Đánh giá kế hoạch", 
                "desc": "Phân tích DVH và đánh giá kế hoạch", 
                "command": self.create_report,
                "image": None
            }
        ]
        
        # Tạo các card chức năng dạng lưới (3x2)
        for i, func in enumerate(functions):
            row = i // 3
            col = i % 3
            
            # Frame cho mỗi card
            card_frame = ttk.Frame(cards_frame, style="Welcome.TFrame")
            card_frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            
            # Tạo border với màu sắc
            card_border = ttk.Frame(card_frame, style="Welcome.TFrame")
            card_border.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
            
            # Card nội dung với viền và bóng
            card = ttk.Frame(card_border, style="Welcome.TFrame")
            card.pack(fill=tk.BOTH, expand=True)
            
            # Chiều cao cố định cho mỗi card
            card_height = 200
            
            # Thêm hình ảnh nếu có
            image_path = None
            if func["image"]:
                image_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                     'resources', 'images', func["image"])
            
            if image_path and os.path.exists(image_path):
                try:
                    # Nạp và căn chỉnh hình ảnh
                    img = Image.open(image_path)
                    img = img.resize((240, 120), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    
                    # Lưu tham chiếu để tránh garbage collection
                    func["photo"] = photo
                    
                    # Hiển thị hình ảnh
                    img_label = ttk.Label(card, image=photo)
                    img_label.pack(fill=tk.X, padx=5, pady=5)
                except Exception as e:
                    self.logger.warning(f"Không thể tải hình ảnh cho {func['title']}: {str(e)}")
            
            # Container cho nội dung
            content_frame = ttk.Frame(card, style="Welcome.TFrame")
            content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))
            
            # Tiêu đề chức năng
            title_label = ttk.Label(
                content_frame, 
                text=func["title"],
                style="CardTitle.TLabel"
            )
            title_label.pack(anchor=tk.W)
            
            # Mô tả chức năng
            desc_label = ttk.Label(
                content_frame, 
                text=func["desc"],
                style="CardDesc.TLabel",
                wraplength=220
            )
            desc_label.pack(anchor=tk.W, pady=(5, 10))
            
            # Nút hành động
            btn = ttk.Button(
                content_frame,
                text="Mở",
                command=func["command"],
                style="Welcome.TButton"
            )
            
            # Thêm icon nếu có
            if 'toolbar' in self.icons and func["icon"] in self.icons['toolbar']:
                btn.configure(image=self.icons['toolbar'][func["icon"]], compound=tk.LEFT)
                
            btn.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # Đảm bảo các cột có kích thước bằng nhau
        for i in range(3):
            cards_frame.columnconfigure(i, weight=1)
        
        # ===== Thẻ 2: Tiện ích =====
        tools_tab = ttk.Frame(notebook, style="Welcome.TFrame")
        notebook.add(tools_tab, text="Tiện ích")
        
        # Danh sách tiện ích
        tools = [
            {"title": "So sánh kế hoạch", "desc": "So sánh nhiều kế hoạch xạ trị", "command": self.compare_plans},
            {"title": "Tính toán BED/EQD2", "desc": "Tính toán hiệu quả sinh học", "command": self.calculate_bed},
            {"title": "Xuất báo cáo", "desc": "Tạo báo cáo điều trị chi tiết", "command": self.export_plan},
            {"title": "Đảm bảo chất lượng", "desc": "Kiểm tra và đảm bảo chất lượng", "command": self.check_plan_qa},
            {"title": "Nhập/Xuất DICOM", "desc": "Quản lý dữ liệu DICOM", "command": self.import_dicom},
            {"title": "Sao lưu dữ liệu", "desc": "Sao lưu và phục hồi dữ liệu", "command": self.backup_data}
        ]
        
        # Container cho các tiện ích
        tools_frame = ttk.Frame(tools_tab, style="Welcome.TFrame")
        tools_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tạo các card tiện ích
        for i, tool in enumerate(tools):
            row = i // 3
            col = i % 3
            
            tool_card = ttk.Frame(tools_frame, style="Welcome.TFrame")
            tool_card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            
            title_label = ttk.Label(
                tool_card, 
                text=tool["title"],
                style="CardTitle.TLabel"
            )
            title_label.pack(anchor=tk.W, pady=(5, 2))
            
            desc_label = ttk.Label(
                tool_card, 
                text=tool["desc"],
                style="CardDesc.TLabel"
            )
            desc_label.pack(anchor=tk.W, pady=(0, 5))
            
            btn = ttk.Button(
                tool_card,
                text="Mở",
                command=tool["command"],
                style="Welcome.TButton"
            )
            btn.pack(anchor=tk.W, pady=5)
        
        # Đảm bảo các cột có kích thước bằng nhau
        for i in range(3):
            tools_frame.columnconfigure(i, weight=1)
        
        # ===== Thẻ 3: Tài nguyên =====
        resources_tab = ttk.Frame(notebook, style="Welcome.TFrame")
        notebook.add(resources_tab, text="Tài nguyên")
        
        resources_frame = ttk.Frame(resources_tab, style="Welcome.TFrame")
        resources_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        resources_title = ttk.Label(
            resources_frame, 
            text="Tài nguyên hữu ích",
            style="WelcomeHeader.TLabel"
        )
        resources_title.pack(anchor=tk.W, pady=(0, 10))
        
        resources_desc = ttk.Label(
            resources_frame, 
            text="Các tài nguyên sau đây sẽ giúp bạn sử dụng QuangStation V2 hiệu quả hơn.",
            style="WelcomeDesc.TLabel"
        )
        resources_desc.pack(anchor=tk.W, pady=(0, 20))
        
        # Danh sách tài nguyên
        resources_list = [
            {"text": "Hướng dẫn sử dụng", "command": lambda: self.open_documentation("user_manual")},
            {"text": "Hướng dẫn cho nhà phát triển", "command": lambda: self.open_documentation("developer_guide")},
            {"text": "Tài liệu API", "command": lambda: self.open_documentation("api")},
            {"text": "Khắc phục sự cố", "command": lambda: self.open_documentation("troubleshooting")},
            {"text": "Trang web chính thức", "command": lambda: self.open_url("https://quangstation.com")}
        ]
        
        for res in resources_list:
            btn = ttk.Button(
                resources_frame,
                text=res["text"],
                command=res["command"],
                width=30,
                style="Welcome.TButton"
            )
            btn.pack(anchor=tk.W, pady=5)
        
        # Phần thông tin phiên bản
        version_frame = ttk.Frame(resources_frame, style="Welcome.TFrame")
        version_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 0))
        
        version_label = ttk.Label(
            version_frame, 
            text="QuangStation V2 - Phiên bản 2.0.0-beta",
            font=('Helvetica', 10, 'italic'),
            foreground="#666666",
            background="#f0f0f0"
        )
        version_label.pack(side=tk.LEFT)
        
        # Nút trợ giúp và hướng dẫn
        help_button = ttk.Button(
            version_frame,
            text="Trợ giúp",
            command=self.show_help,
            style="Welcome.TButton"
        )
        
        # Thêm icon nếu có
        if 'menu' in self.icons and 'help' in self.icons['menu']:
            help_button.configure(image=self.icons['menu']['help'], compound=tk.LEFT)
            
        help_button.pack(side=tk.RIGHT, padx=5)
        
        # Chọn thẻ mặc định
        notebook.select(0)
        
    def open_documentation(self, doc_type):
        """Mở tài liệu hướng dẫn"""
        doc_paths = {
            "user_manual": os.path.join("docs", "user_manual", "index.html"),
            "developer_guide": os.path.join("docs", "developer_guide", "index.html"),
            "api": os.path.join("docs", "api", "index.html"),
            "troubleshooting": os.path.join("docs", "TROUBLESHOOTING.md")
        }
        
        if doc_type in doc_paths:
            doc_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                doc_paths[doc_type])
            
            if os.path.exists(doc_path):
                # Sử dụng trình duyệt mặc định để mở file
                import webbrowser
                webbrowser.open(doc_path)
            else:
                messagebox.showinfo("Thông báo", 
                                  f"Tài liệu {doc_type} chưa được cài đặt. Vui lòng tải về từ trang web chính thức.")
    
    def open_url(self, url):
        """Mở URL trong trình duyệt mặc định"""
        import webbrowser
        webbrowser.open(url)
        
    def compare_plans(self):
        """Mở công cụ so sánh kế hoạch"""
        messagebox.showinfo("Thông báo", "Chức năng đang được phát triển")
        
    def calculate_bed(self):
        """Mở công cụ tính toán BED/EQD2"""
        messagebox.showinfo("Thông báo", "Chức năng đang được phát triển")
        
    def check_plan_qa(self):
        """Mở công cụ kiểm tra chất lượng kế hoạch"""
        messagebox.showinfo("Thông báo", "Chức năng đang được phát triển")
        
    def import_dicom(self):
        """Mở công cụ nhập/xuất DICOM"""
        # Tạo cửa sổ dialog để hiển thị giao diện nhập DICOM
        dialog = tk.Toplevel(self.root)
        dialog.title("Nhập dữ liệu DICOM - QuangStation V2")
        dialog.geometry("800x600")
        dialog.minsize(800, 600)
        
        # Thiết lập icon nếu có
        try:
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                   'resources', 'icons', 'app_icon.ico')
            if os.path.exists(icon_path):
                dialog.iconbitmap(icon_path)
        except Exception as e:
            self.logger.warning(f"Không thể tải biểu tượng cho cửa sổ nhập DICOM: {str(e)}")
        
        # Callback khi nhập hoàn tất
        def on_import_complete(result):
            if result:
                self.logger.info("Đã nhập dữ liệu DICOM thành công")
                # Cập nhật danh sách bệnh nhân nếu cần
                # TODO: Cập nhật danh sách bệnh nhân từ kết quả nhập
                
                # Đóng cửa sổ nhập DICOM
                dialog.destroy()
        
        # Tạo và hiển thị giao diện nhập DICOM
        import_view = ImportView(dialog, on_import_complete=on_import_complete)
        import_view.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Thiết lập focus và đợi cửa sổ đóng
        dialog.transient(self.root)
        dialog.grab_set()
        self.root.wait_window(dialog)

    def show_dvh(self):
        """Hiển thị biểu đồ DVH"""
        if hasattr(self, 'current_plan_window') and self.current_plan_window:
            self.current_plan_window.show_dvh()
        else:
            messagebox.showinfo("Thông báo", "Vui lòng mở cửa sổ thiết kế kế hoạch trước.")
    
    def kbp_optimize(self):
        """Mở chức năng tối ưu hóa dựa trên kiến thức (KBP)"""
        if hasattr(self, 'current_plan_window') and self.current_plan_window:
            self.current_plan_window.kbp_optimize()
        else:
            messagebox.showinfo("Thông báo", "Vui lòng mở cửa sổ thiết kế kế hoạch trước.")
    
    def open_kbp_trainer(self):
        """Mở công cụ huấn luyện mô hình KBP"""
        try:
            from quangstation.gui.dialogs.kbp_trainer_dialog import KBPTrainerDialog
            from quangstation.optimization.kbp_optimizer import KnowledgeBasedPlanningOptimizer
            
            # Khởi tạo optimizer
            optimizer = KnowledgeBasedPlanningOptimizer()
            
            # Tạo và hiển thị dialog
            dialog = KBPTrainerDialog(self.root, optimizer)
            
        except Exception as e:
            self.logger.error(f"Lỗi khi mở công cụ huấn luyện KBP: {str(e)}")
            messagebox.showerror("Lỗi", f"Không thể mở công cụ huấn luyện KBP: {str(e)}")

    def create_report(self):
        """Tạo báo cáo kế hoạch xạ trị"""
        messagebox.showinfo("Thông báo", "Chức năng đang được phát triển")

    def backup_data(self):
        """Mở công cụ sao lưu dữ liệu"""
        # Tạo cửa sổ dialog cho sao lưu dữ liệu
        dialog = tk.Toplevel(self.root)
        dialog.title("Sao lưu dữ liệu - QuangStation V2")
        dialog.geometry("600x400")
        dialog.minsize(600, 400)
        
        # Thiết lập icon nếu có
        try:
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                   'resources', 'icons', 'app_icon.ico')
            if os.path.exists(icon_path):
                dialog.iconbitmap(icon_path)
        except Exception as e:
            self.logger.warning(f"Không thể tải biểu tượng cho cửa sổ sao lưu: {str(e)}")
        
        # Tạo giao diện
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tiêu đề
        title_label = ttk.Label(main_frame, text="Sao lưu dữ liệu bệnh nhân và kế hoạch", 
                              style="Heading.TLabel")
        title_label.pack(pady=(0, 10))
        
        # Tạo tab control
        tab_control = ttk.Notebook(main_frame)
        tab_control.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Sao lưu thủ công
        tab1 = ttk.Frame(tab_control, padding=10)
        tab_control.add(tab1, text="Sao lưu thủ công")
        
        # Chọn thư mục đích
        dest_frame = ttk.LabelFrame(tab1, text="Thư mục đích", padding=10)
        dest_frame.pack(fill=tk.X, pady=5)
        
        dest_path = tk.StringVar()
        dest_entry = ttk.Entry(dest_frame, textvariable=dest_path, width=50)
        dest_entry.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
        
        def browse_dest():
            folder = filedialog.askdirectory(title="Chọn thư mục lưu trữ dữ liệu")
            if folder:
                dest_path.set(folder)
        
        browse_button = ttk.Button(dest_frame, text="Duyệt...", command=browse_dest)
        browse_button.pack(side=tk.RIGHT)
        
        # Tùy chọn sao lưu
        options_frame = ttk.LabelFrame(tab1, text="Tùy chọn sao lưu", padding=10)
        options_frame.pack(fill=tk.X, pady=10)
        
        backup_patients = tk.BooleanVar(value=True)
        patient_check = ttk.Checkbutton(options_frame, text="Sao lưu dữ liệu bệnh nhân", 
                                      variable=backup_patients)
        patient_check.pack(anchor=tk.W, pady=2)
        
        backup_plans = tk.BooleanVar(value=True)
        plan_check = ttk.Checkbutton(options_frame, text="Sao lưu kế hoạch xạ trị", 
                                   variable=backup_plans)
        plan_check.pack(anchor=tk.W, pady=2)
        
        backup_images = tk.BooleanVar(value=True)
        image_check = ttk.Checkbutton(options_frame, text="Sao lưu dữ liệu hình ảnh", 
                                    variable=backup_images)
        image_check.pack(anchor=tk.W, pady=2)
        
        compress_data = tk.BooleanVar(value=True)
        compress_check = ttk.Checkbutton(options_frame, text="Nén dữ liệu (giảm dung lượng)", 
                                       variable=compress_data)
        compress_check.pack(anchor=tk.W, pady=2)
        
        # Tab 2: Lịch sử sao lưu tự động
        tab2 = ttk.Frame(tab_control, padding=10)
        tab_control.add(tab2, text="Sao lưu tự động")
        
        auto_frame = ttk.LabelFrame(tab2, text="Thiết lập sao lưu tự động", padding=10)
        auto_frame.pack(fill=tk.X, pady=5)
        
        enable_auto = tk.BooleanVar(value=False)
        auto_check = ttk.Checkbutton(auto_frame, text="Bật sao lưu tự động", 
                                   variable=enable_auto)
        auto_check.pack(anchor=tk.W, pady=2)
        
        interval_frame = ttk.Frame(auto_frame)
        interval_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(interval_frame, text="Tần suất sao lưu:").pack(side=tk.LEFT, padx=(0, 5))
        
        interval_options = ["Hàng ngày", "Hàng tuần", "Hàng tháng"]
        interval = tk.StringVar(value=interval_options[0])
        interval_combo = ttk.Combobox(interval_frame, textvariable=interval, 
                                    values=interval_options, state="readonly", width=15)
        interval_combo.pack(side=tk.LEFT)
        
        # Khung hiển thị lịch sử sao lưu
        history_frame = ttk.LabelFrame(tab2, text="Lịch sử sao lưu", padding=10)
        history_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        columns = ("date", "time", "size", "status")
        history_tree = ttk.Treeview(history_frame, columns=columns, show="headings", height=5)
        
        history_tree.heading("date", text="Ngày")
        history_tree.heading("time", text="Thời gian")
        history_tree.heading("size", text="Kích thước")
        history_tree.heading("status", text="Trạng thái")
        
        history_tree.column("date", width=100)
        history_tree.column("time", width=80)
        history_tree.column("size", width=80)
        history_tree.column("status", width=100)
        
        # Thêm dummy data cho ví dụ
        history_tree.insert("", "end", values=("12/03/2025", "08:30", "25.4 MB", "Thành công"))
        history_tree.insert("", "end", values=("05/03/2025", "09:15", "24.8 MB", "Thành công"))
        
        history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=history_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        history_tree.configure(yscrollcommand=scrollbar.set)
        
        # Buttons cho cả hai tab
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        def start_backup():
            # Kiểm tra thư mục đích
            if not dest_path.get():
                messagebox.showerror("Lỗi", "Vui lòng chọn thư mục đích để sao lưu")
                return
            
            messagebox.showinfo("Thông báo", "Đã bắt đầu quá trình sao lưu dữ liệu")
            # TODO: Thực hiện sao lưu dữ liệu thực tế
            
            # Đóng dialog
            dialog.destroy()
        
        backup_button = ttk.Button(button_frame, text="Bắt đầu sao lưu", command=start_backup)
        backup_button.pack(side=tk.RIGHT, padx=5)
        
        cancel_button = ttk.Button(button_frame, text="Hủy", command=dialog.destroy)
        cancel_button.pack(side=tk.RIGHT, padx=5)
        
        # Thiết lập focus và đợi cửa sổ đóng
        dialog.transient(self.root)
        dialog.grab_set()
        self.root.wait_window(dialog)

if __name__ == "__main__":
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()
