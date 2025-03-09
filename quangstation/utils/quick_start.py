#!/usr/bin/env python
"""
Script khởi động nhanh cho QuangStation V2.
Giúp người dùng mới thiết lập môi trường và chạy ứng dụng dễ dàng.
"""

import os
import sys
import subprocess
import argparse
import platform
import shutil
import json
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, filedialog

CONFIG_DIR = os.path.expanduser("~/.quangstation")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
DEFAULT_WORKSPACE = os.path.join(os.path.expanduser("~"), "QuangStation_Workspace")

def check_dependencies():
    """Kiểm tra các thư viện phụ thuộc đã được cài đặt chưa."""
    required_packages = [
        "numpy", "matplotlib", "pydicom", "SimpleITK", "vtk", "opencv-python",
        "scipy", "scikit-image", "pandas", "tqdm", "pillow", "reportlab",
        "psutil", "pyqt5"
    ]
    
    optional_packages = [
        "torch", "torchvision", "scikit-learn", "pylinac", "dicompyler-core",
        "nibabel", "pytest", "sphinx"
    ]
    
    missing_required = []
    missing_optional = []
    
    print("Đang kiểm tra các thư viện phụ thuộc...")
    
    # Kiểm tra các gói bắt buộc
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✓ {package}")
        except ImportError:
            missing_required.append(package)
            print(f"✗ {package} (bắt buộc)")
    
    # Kiểm tra các gói tùy chọn
    for package in optional_packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            missing_optional.append(package)
            print(f"? {package} (tùy chọn)")
    
    return missing_required, missing_optional

def install_dependencies(missing_required, missing_optional, install_optional=False):
    """Cài đặt các thư viện còn thiếu."""
    if not missing_required and not (missing_optional and install_optional):
        print("Tất cả các thư viện cần thiết đã được cài đặt.")
        return True
    
    print("\nĐang cài đặt các thư viện còn thiếu...")
    
    packages_to_install = missing_required.copy()
    if install_optional:
        packages_to_install.extend(missing_optional)
    
    if not packages_to_install:
        return True
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + packages_to_install)
        print("Cài đặt thư viện thành công!")
        return True
    except subprocess.CalledProcessError:
        print("Lỗi khi cài đặt thư viện. Vui lòng cài đặt thủ công.")
        return False

def create_config(workspace_dir=None):
    """Tạo file cấu hình mặc định."""
    if workspace_dir is None:
        workspace_dir = DEFAULT_WORKSPACE
    
    # Tạo thư mục cấu hình nếu chưa tồn tại
    os.makedirs(CONFIG_DIR, exist_ok=True)
    
    # Tạo thư mục làm việc nếu chưa tồn tại
    os.makedirs(workspace_dir, exist_ok=True)
    
    # Cấu hình mặc định
    config = {
        "workspace_dir": workspace_dir,
        "logging": {
            "level": "INFO",
            "file": os.path.join(CONFIG_DIR, "quangstation.log"),
            "max_size_mb": 10,
            "backup_count": 3
        },
        "dose_calculation": {
            "default_algorithm": "collapsed_cone",
            "resolution_mm": 3.0,
            "monte_carlo": {
                "num_particles": 1000000,
                "num_threads": 4
            }
        },
        "ui": {
            "theme": "light",
            "language": "vi",
            "window_size": [1200, 800],
            "default_colormap": "jet",
            "auto_save_minutes": 10
        },
        "dicom": {
            "anonymize": False,
            "default_import_dir": "",
            "default_export_dir": ""
        },
        "reporting": {
            "logo_path": "",
            "institution_name": "Bệnh viện Mẫu",
            "report_template": "standard"
        }
    }
    
    # Lưu cấu hình
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    
    print(f"Đã tạo file cấu hình tại: {CONFIG_FILE}")
    return config

def load_config():
    """Đọc file cấu hình."""
    if not os.path.exists(CONFIG_FILE):
        return create_config()
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except Exception as error:
        print(f"Lỗi khi đọc file cấu hình: {e}")
        return create_config()

def create_sample_data(workspace_dir):
    """Tạo dữ liệu mẫu cho người dùng mới."""
    sample_dir = os.path.join(workspace_dir, "samples")
    os.makedirs(sample_dir, exist_ok=True)
    
    # Tạo cấu trúc thư mục mẫu
    patient_dirs = [
        os.path.join(sample_dir, "patient001"),
        os.path.join(sample_dir, "patient002")
    ]
    
    for patient_dir in patient_dirs:
        os.makedirs(patient_dir, exist_ok=True)
        os.makedirs(os.path.join(patient_dir, "ct"), exist_ok=True)
        os.makedirs(os.path.join(patient_dir, "structures"), exist_ok=True)
        os.makedirs(os.path.join(patient_dir, "plans"), exist_ok=True)
        os.makedirs(os.path.join(patient_dir, "dose"), exist_ok=True)
    
    # Tạo file README.txt
    readme_path = os.path.join(sample_dir, "README.txt")
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write("""QUANGSTATION V2 - DỮ LIỆU MẪU

Thư mục này chứa cấu trúc dữ liệu mẫu cho QuangStation V2.
Để bắt đầu sử dụng, bạn có thể:

1. Nhập dữ liệu DICOM vào thư mục patient001/ct
2. Sử dụng tính năng "Nhập DICOM" trong ứng dụng
3. Tạo contour và kế hoạch xạ trị mới

Tham khảo tài liệu hướng dẫn để biết thêm chi tiết.
""")
    
    print(f"Đã tạo cấu trúc dữ liệu mẫu tại: {sample_dir}")

def run_application():
    """Khởi chạy ứng dụng QuangStation."""
    try:
        import quangstation.main
        quangstation.main.main()
        return True
    except ImportError:
        print("Không thể nhập module quangstation.main. Đảm bảo QuangStation đã được cài đặt đúng cách.")
        return False
    except Exception as error:
        print(f"Lỗi khi khởi chạy ứng dụng: {e}")
        return False

def setup_gui():
    """Hiển thị giao diện đồ họa để thiết lập QuangStation."""
    root = tk.Tk()
    root.title("QuangStation V2 - Thiết lập nhanh")
    root.geometry("600x500")
    root.resizable(True, True)
    
    # Tạo style
    root.configure(bg="#f0f0f0")
    title_font = ("Arial", 16, "bold")
    header_font = ("Arial", 12, "bold")
    normal_font = ("Arial", 10)
    
    # Tiêu đề
    tk.Label(root, text="QuangStation V2 - Thiết lập nhanh", font=title_font, bg="#f0f0f0", pady=10).pack()
    
    # Frame chính
    main_frame = tk.Frame(root, bg="#f0f0f0", padx=20, pady=10)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Kiểm tra thư viện
    tk.Label(main_frame, text="1. Kiểm tra thư viện phụ thuộc", font=header_font, bg="#f0f0f0", anchor="w").pack(fill=tk.X, pady=(10, 5))
    
    deps_frame = tk.Frame(main_frame, bg="#f0f0f0")
    deps_frame.pack(fill=tk.X, padx=10)
    
    deps_text = tk.Text(deps_frame, height=6, width=60, font=normal_font)
    deps_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    scrollbar = tk.Scrollbar(deps_frame, command=deps_text.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    deps_text.config(yscrollcommand=scrollbar.set)
    
    # Thư mục làm việc
    tk.Label(main_frame, text="2. Chọn thư mục làm việc", font=header_font, bg="#f0f0f0", anchor="w").pack(fill=tk.X, pady=(15, 5))
    
    workspace_frame = tk.Frame(main_frame, bg="#f0f0f0")
    workspace_frame.pack(fill=tk.X, padx=10, pady=5)
    
    workspace_var = tk.StringVar(value=DEFAULT_WORKSPACE)
    workspace_entry = tk.Entry(workspace_frame, textvariable=workspace_var, width=50, font=normal_font)
    workspace_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
    
    def browse_workspace():
        directory = filedialog.askdirectory(initialdir=os.path.expanduser("~"))
        if directory:
            workspace_var.set(directory)
    
    browse_button = tk.Button(workspace_frame, text="Duyệt...", command=browse_workspace, font=normal_font)
    browse_button.pack(side=tk.RIGHT)
    
    # Tùy chọn
    tk.Label(main_frame, text="3. Tùy chọn", font=header_font, bg="#f0f0f0", anchor="w").pack(fill=tk.X, pady=(15, 5))
    
    options_frame = tk.Frame(main_frame, bg="#f0f0f0", padx=10)
    options_frame.pack(fill=tk.X)
    
    install_optional_var = tk.BooleanVar(value=False)
    create_sample_var = tk.BooleanVar(value=True)
    launch_app_var = tk.BooleanVar(value=True)
    
    tk.Checkbutton(options_frame, text="Cài đặt các thư viện tùy chọn", variable=install_optional_var, 
                  bg="#f0f0f0", font=normal_font).pack(anchor="w")
    tk.Checkbutton(options_frame, text="Tạo dữ liệu mẫu", variable=create_sample_var, 
                  bg="#f0f0f0", font=normal_font).pack(anchor="w")
    tk.Checkbutton(options_frame, text="Khởi chạy ứng dụng sau khi thiết lập", variable=launch_app_var, 
                  bg="#f0f0f0", font=normal_font).pack(anchor="w")
    
    # Trạng thái
    status_var = tk.StringVar(value="Sẵn sàng thiết lập...")
    status_label = tk.Label(main_frame, textvariable=status_var, bg="#f0f0f0", fg="blue", font=normal_font)
    status_label.pack(fill=tk.X, pady=10)
    
    # Nút điều khiển
    control_frame = tk.Frame(main_frame, bg="#f0f0f0")
    control_frame.pack(fill=tk.X, pady=10)
    
    def start_setup():
        # Vô hiệu hóa nút
        setup_button.config(state=tk.DISABLED)
        
        # Cập nhật trạng thái
        status_var.set("Đang kiểm tra thư viện phụ thuộc...")
        root.update()
        
        # Kiểm tra thư viện
        deps_text.delete(1.0, tk.END)
        missing_required, missing_optional = check_dependencies()
        
        for pkg in missing_required:
            deps_text.insert(tk.END, f"✗ {pkg} (bắt buộc)\n")
        
        for pkg in missing_optional:
            deps_text.insert(tk.END, f"? {pkg} (tùy chọn)\n")
        
        if not missing_required and not missing_optional:
            deps_text.insert(tk.END, "✓ Tất cả thư viện đã được cài đặt!\n")
        
        # Cài đặt thư viện
        if missing_required or (missing_optional and install_optional_var.get()):
            status_var.set("Đang cài đặt thư viện còn thiếu...")
            root.update()
            
            success = install_dependencies(missing_required, missing_optional, install_optional_var.get())
            if not success:
                status_var.set("Lỗi khi cài đặt thư viện. Vui lòng cài đặt thủ công.")
                setup_button.config(state=tk.NORMAL)
                return
        
        # Tạo cấu hình
        status_var.set("Đang tạo cấu hình...")
        root.update()
        
        workspace_dir = workspace_var.get()
        config = create_config(workspace_dir)
        
        # Tạo dữ liệu mẫu
        if create_sample_var.get():
            status_var.set("Đang tạo dữ liệu mẫu...")
            root.update()
            create_sample_data(workspace_dir)
        
        # Hoàn thành
        status_var.set("Thiết lập hoàn tất!")
        messagebox.showinfo("QuangStation V2", "Thiết lập hoàn tất! QuangStation V2 đã sẵn sàng sử dụng.")
        
        # Khởi chạy ứng dụng
        if launch_app_var.get():
            status_var.set("Đang khởi chạy ứng dụng...")
            root.update()
            root.destroy()  # Đóng cửa sổ thiết lập
            run_application()
        else:
            setup_button.config(state=tk.NORMAL)
    
    setup_button = tk.Button(control_frame, text="Bắt đầu thiết lập", command=start_setup, 
                           font=("Arial", 12), bg="#4CAF50", fg="white", padx=10, pady=5)
    setup_button.pack(side=tk.RIGHT, padx=5)
    
    exit_button = tk.Button(control_frame, text="Thoát", command=root.destroy, 
                          font=("Arial", 12), bg="#f44336", fg="white", padx=10, pady=5)
    exit_button.pack(side=tk.RIGHT, padx=5)
    
    # Hiển thị thông tin thư viện ban đầu
    missing_required, missing_optional = check_dependencies()
    
    if not missing_required and not missing_optional:
        deps_text.insert(tk.END, "✓ Tất cả thư viện đã được cài đặt!\n")
    else:
        for pkg in missing_required:
            deps_text.insert(tk.END, f"✗ {pkg} (bắt buộc)\n")
        
        for pkg in missing_optional:
            deps_text.insert(tk.END, f"? {pkg} (tùy chọn)\n")
    
    root.mainloop()

def main():
    """Hàm chính của script khởi động nhanh."""
    parser = argparse.ArgumentParser(description="QuangStation V2 - Script khởi động nhanh")
    parser.add_argument("--gui", action="store_true", help="Sử dụng giao diện đồ họa để thiết lập")
    parser.add_argument("--workspace", type=str, help="Đường dẫn thư mục làm việc")
    parser.add_argument("--check-only", action="store_true", help="Chỉ kiểm tra thư viện phụ thuộc")
    parser.add_argument("--install-deps", action="store_true", help="Cài đặt thư viện còn thiếu")
    parser.add_argument("--create-sample", action="store_true", help="Tạo dữ liệu mẫu")
    parser.add_argument("--run", action="store_true", help="Khởi chạy ứng dụng sau khi thiết lập")
    
    args = parser.parse_args()
    
    # Sử dụng GUI nếu được chỉ định
    if args.gui:
        setup_gui()
        return
    
    # Kiểm tra thư viện
    missing_required, missing_optional = check_dependencies()
    
    # Chỉ kiểm tra
    if args.check_only:
        return
    
    # Cài đặt thư viện
    if args.install_deps:
        install_dependencies(missing_required, missing_optional, True)
    
    # Tạo cấu hình
    workspace_dir = args.workspace if args.workspace else DEFAULT_WORKSPACE
    config = load_config()
    
    if args.workspace:
        config["workspace_dir"] = workspace_dir
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    
    # Tạo dữ liệu mẫu
    if args.create_sample:
        create_sample_data(config["workspace_dir"])
    
    # Khởi chạy ứng dụng
    if args.run:
        run_application()

if __name__ == "__main__":
    main() 