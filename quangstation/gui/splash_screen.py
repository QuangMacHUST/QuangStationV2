#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module cung cấp màn hình splash hiện đại cho QuangStation V2.
"""

import os
import tkinter as tk
from tkinter import ttk
import threading
import time
from PIL import Image, ImageTk, ImageFilter, ImageEnhance
from pathlib import Path
import random

class SplashScreen:
    """
    Màn hình splash hiện đại với hiệu ứng và animation.
    Hiển thị thông tin khởi động và tiến trình tải.
    """
    
    def __init__(self, root, duration=3000):
        """
        Khởi tạo màn hình splash.
        
        Args:
            root: Cửa sổ Tkinter gốc
            duration: Thời gian hiển thị tối thiểu (ms)
        """
        self.root = root
        self.duration = duration
        self.window = None
        self.progress_value = 0
        self.progress_target = 100
        self.message_text = tk.StringVar()
        self.message_text.set("Đang khởi chạy QuangStation V2...")
        self.loading_phrases = [
            "Khởi tạo hệ thống...",
            "Nạp giao diện người dùng...",
            "Khởi động dịch vụ hỗ trợ...",
            "Chuẩn bị hệ thống tính toán liều...",
            "Kiểm tra cơ sở dữ liệu...",
            "Nạp thuật toán tối ưu hóa...",
            "Khởi động công cụ vẽ contour...",
            "Chuẩn bị module phân đoạn...",
            "Nạp dữ liệu mẫu...",
            "Khởi động hệ thống DVH...",
            "Hoàn tất khởi động..."
        ]
        
        # Tạo cửa sổ splash
        self._create_splash_window()
        
        # Bắt đầu cập nhật tiến trình
        self.start_time = time.time()
        self.update_thread = threading.Thread(target=self._update_progress)
        self.update_thread.daemon = True
        self.update_thread.start()
    
    def _create_splash_window(self):
        """Tạo cửa sổ splash với giao diện hiện đại."""
        # Tạo cửa sổ mới không có tiêu đề và viền
        self.window = tk.Toplevel(self.root)
        self.window.overrideredirect(True)  # Không có tiêu đề và viền
        self.window.wm_attributes('-topmost', True)  # Luôn hiển thị phía trên
        
        # Kích thước cửa sổ
        width, height = 800, 500
        self.window.geometry(f"{width}x{height}")
        
        # Căn giữa màn hình
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.window.geometry(f"+{x}+{y}")
        
        # Frame chính
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Nạp hình nền
        image_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                               'resources', 'images', 'splash_background.jpg')
        
        try:
            # Nạp và xử lý hình nền
            img = Image.open(image_path)
            img = img.resize((width, height), Image.LANCZOS)
            
            # Thêm hiệu ứng làm mờ nhẹ và tăng độ sáng
            img = img.filter(ImageFilter.GaussianBlur(radius=1))
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(1.1)
            
            # Chuyển đổi thành PhotoImage
            self.bg_image = ImageTk.PhotoImage(img)
            
            # Tạo canvas để hiển thị hình nền
            self.canvas = tk.Canvas(main_frame, width=width, height=height, 
                                   highlightthickness=0)
            self.canvas.pack(fill=tk.BOTH, expand=True)
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.bg_image)
            
            # Thêm gradient overlay bán trong suốt
            self.canvas.create_rectangle(0, 0, width, height, 
                                        fill='#000033', stipple='gray50')
            
            # Tạo logo hoặc biểu tượng ứng dụng (vẽ hình tròn xanh dương làm placeholder)
            logo_x, logo_y = width // 2, height // 2 - 80
            self.canvas.create_oval(logo_x-60, logo_y-60, logo_x+60, logo_y+60, 
                                   outline='#0099FF', fill='#0066CC', width=5)
            
            # Vẽ chữ QS ở giữa logo
            self.canvas.create_text(logo_x, logo_y, text="QS", 
                                   font=('Helvetica', 50, 'bold'), fill='white')
            
            # Vẽ tên ứng dụng
            self.canvas.create_text(width//2, logo_y+100, text="QuangStation V2", 
                                   font=('Helvetica', 36, 'bold'), fill='white')
            
            # Vẽ slogan
            self.canvas.create_text(width//2, logo_y+140, 
                                   text="Hệ thống Lập kế hoạch Xạ trị Mã nguồn Mở", 
                                   font=('Helvetica', 14), fill='#CCCCCC')
            
            # Vẽ phiên bản
            self.canvas.create_text(width//2, logo_y+170, text="Phiên bản 2.0.0-beta", 
                                   font=('Helvetica', 12, 'italic'), fill='#AAAAAA')
            
            # Tạo vùng hiển thị thông báo tải
            message_y = height - 90
            message_frame = ttk.Frame(self.canvas)
            self.canvas.create_window(width//2, message_y, window=message_frame)
            
            message_label = ttk.Label(message_frame, textvariable=self.message_text, 
                                     font=('Helvetica', 10), foreground='white',
                                     background='#000033')
            message_label.pack()
            
            # Tạo thanh tiến trình
            progress_y = height - 60
            self.progress = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, 
                                           length=width-100, mode='determinate')
            self.canvas.create_window(width//2, progress_y, window=self.progress)
            
            # Vẽ thông tin bản quyền
            self.canvas.create_text(width//2, height-20, 
                                   text="© 2024 Mạc Đăng Quang. Mọi quyền được bảo lưu.", 
                                   font=('Helvetica', 8), fill='#999999')
            
        except Exception as e:
            print(f"Lỗi khi tạo splash screen: {e}")
            # Fallback nếu không tạo được giao diện đồ họa
            label = ttk.Label(main_frame, text="Đang khởi động QuangStation V2...")
            label.pack(padx=20, pady=20)
            self.progress = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, 
                                           length=300, mode='determinate')
            self.progress.pack(padx=20, pady=10)
    
    def _update_progress(self):
        """Cập nhật tiến trình và thông báo tải."""
        # Tính toán tốc độ cập nhật
        total_steps = len(self.loading_phrases)
        step_time = self.duration / total_steps
        
        for i, phrase in enumerate(self.loading_phrases):
            if not self.window:
                break
                
            # Cập nhật thông báo
            self.message_text.set(phrase)
            
            # Cập nhật tiến trình
            target_progress = int((i + 1) * 100 / total_steps)
            
            # Tăng dần tiến trình từ giá trị hiện tại đến target
            start_progress = self.progress_value
            for p in range(start_progress, target_progress + 1):
                if not self.window:
                    break
                self.progress_value = p
                self.progress['value'] = p
                time.sleep(step_time / (target_progress - start_progress) / 1000)
            
            # Thêm độ trễ ngẫu nhiên để tạo cảm giác thực tế
            time.sleep(random.uniform(0.1, 0.3))
        
        # Đảm bảo tiến trình đạt 100%
        self.progress['value'] = 100
        
        # Đảm bảo hiển thị tối thiểu trong thời gian duration
        elapsed = (time.time() - self.start_time) * 1000
        if elapsed < self.duration:
            time.sleep((self.duration - elapsed) / 1000)
    
    def destroy(self):
        """Đóng màn hình splash."""
        if self.window:
            self.window.destroy()
            self.window = None
    
    def is_alive(self):
        """Kiểm tra xem splash screen còn hiển thị không."""
        return self.window is not None


# Hàm tiện ích để sử dụng splash screen
def show_splash(root, callback=None, duration=3000):
    """
    Hiển thị splash screen và chạy callback sau khi hoàn thành.
    
    Args:
        root: Cửa sổ Tkinter gốc
        callback: Hàm gọi lại khi splash screen đóng
        duration: Thời gian tối thiểu hiển thị splash screen (ms)
    """
    splash = SplashScreen(root, duration)
    
    def check_status():
        if not splash.is_alive():
            if callback:
                callback()
            return
            
        if splash.progress_value >= 100:
            splash.destroy()
            if callback:
                callback()
            return
            
        root.after(100, check_status)
    
    root.after(100, check_status)
    return splash 