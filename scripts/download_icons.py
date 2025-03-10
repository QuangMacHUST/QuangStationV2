#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script để tải xuống các biểu tượng mẫu cho QuangStation V2
Sử dụng các icon từ các nguồn miễn phí
"""

import os
import requests
from urllib.parse import urlparse
from pathlib import Path
import base64
import io
from PIL import Image

# Đường dẫn đến thư mục resources/icons
ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'resources', 'icons')

# Danh sách các biểu tượng cần tải xuống
ICONS = {
    'app_icon': 'https://img.icons8.com/fluency/96/null/radiation.png',
    'toolbar': {
        'patient': 'https://img.icons8.com/fluency/48/null/hospital-bed.png',
        'plan': 'https://img.icons8.com/fluency/48/null/treatment-plan.png',
        'beam': 'https://img.icons8.com/fluency/48/null/ray.png',
        'dose': 'https://img.icons8.com/fluency/48/null/chart.png',
        'contour': 'https://img.icons8.com/fluency/48/null/polygon.png',
        'optimize': 'https://img.icons8.com/fluency/48/null/process.png',
        'report': 'https://img.icons8.com/fluency/48/null/report-card.png',
        'export': 'https://img.icons8.com/fluency/48/null/export.png',
        'settings': 'https://img.icons8.com/fluency/48/null/settings.png',
    },
    'menu': {
        'new': 'https://img.icons8.com/fluency/48/null/new-file.png',
        'open': 'https://img.icons8.com/fluency/48/null/opened-folder.png',
        'save': 'https://img.icons8.com/fluency/48/null/save.png',
        'exit': 'https://img.icons8.com/fluency/48/null/exit.png',
        'help': 'https://img.icons8.com/fluency/48/null/help.png',
        'about': 'https://img.icons8.com/fluency/48/null/about.png',
    },
    'buttons': {
        'add': 'https://img.icons8.com/fluency/48/null/plus-math.png',
        'delete': 'https://img.icons8.com/fluency/48/null/delete-forever.png',
        'edit': 'https://img.icons8.com/fluency/48/null/edit.png',
        'calculate': 'https://img.icons8.com/fluency/48/null/calculator.png',
        'view': 'https://img.icons8.com/fluency/48/null/visible.png',
        'refresh': 'https://img.icons8.com/fluency/48/null/refresh.png',
    }
}

# Tạo định dạng ICO từ PNG
def png_to_ico(png_data, output_path):
    img = Image.open(io.BytesIO(png_data))
    img.save(output_path, format='ICO', sizes=[(32, 32)])

def download_icons():
    """Tải xuống các biểu tượng và lưu vào thư mục resources/icons"""
    
    print(f"Đang tải xuống các biểu tượng vào {ICON_DIR}...")
    
    # Tạo thư mục nếu chưa tồn tại
    os.makedirs(ICON_DIR, exist_ok=True)
    
    # Tải xuống app_icon
    response = requests.get(ICONS['app_icon'])
    if response.status_code == 200:
        # Lưu dưới dạng PNG
        png_path = os.path.join(ICON_DIR, 'app_icon.png')
        with open(png_path, 'wb') as f:
            f.write(response.content)
        print(f"Đã tải xuống: app_icon.png")
        
        # Chuyển đổi sang ICO
        ico_path = os.path.join(ICON_DIR, 'app_icon.ico')
        png_to_ico(response.content, ico_path)
        print(f"Đã tạo: app_icon.ico")
    
    # Tải xuống các biểu tượng toolbar
    toolbar_dir = os.path.join(ICON_DIR, 'toolbar')
    os.makedirs(toolbar_dir, exist_ok=True)
    
    for name, url in ICONS['toolbar'].items():
        response = requests.get(url)
        if response.status_code == 200:
            output_path = os.path.join(toolbar_dir, f"{name}.png")
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"Đã tải xuống: toolbar/{name}.png")
    
    # Tải xuống các biểu tượng menu
    menu_dir = os.path.join(ICON_DIR, 'menu')
    os.makedirs(menu_dir, exist_ok=True)
    
    for name, url in ICONS['menu'].items():
        response = requests.get(url)
        if response.status_code == 200:
            output_path = os.path.join(menu_dir, f"{name}.png")
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"Đã tải xuống: menu/{name}.png")
    
    # Tải xuống các biểu tượng buttons
    buttons_dir = os.path.join(ICON_DIR, 'buttons')
    os.makedirs(buttons_dir, exist_ok=True)
    
    for name, url in ICONS['buttons'].items():
        response = requests.get(url)
        if response.status_code == 200:
            output_path = os.path.join(buttons_dir, f"{name}.png")
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"Đã tải xuống: buttons/{name}.png")
    
    print("Hoàn tất tải xuống các biểu tượng!")

if __name__ == "__main__":
    download_icons() 