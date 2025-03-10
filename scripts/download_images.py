#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script tải hình ảnh cho QuangStation V2
Tải các hình ảnh từ web và lưu vào thư mục resources/images
"""

import os
import sys
import requests
from pathlib import Path
from PIL import Image
from io import BytesIO
import time
import random

# Thêm thư mục gốc vào đường dẫn Python
root_dir = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, root_dir)

# Thiết lập đường dẫn lưu hình ảnh
IMAGES_DIR = os.path.join(root_dir, 'resources', 'images')
os.makedirs(IMAGES_DIR, exist_ok=True)

# Danh sách hình ảnh cần tải
IMAGES = [
    {
        "name": "splash_background.jpg",
        "url": "https://img.freepik.com/free-vector/gradient-network-connection-background_23-2148865393.jpg",
        "description": "Hình nền cho splash screen"
    },
    {
        "name": "welcome_background.jpg",
        "url": "https://img.freepik.com/free-vector/abstract-medical-wallpaper-template-design_53876-61802.jpg",
        "description": "Hình nền cho welcome screen"
    },
    {
        "name": "radiation_therapy.jpg",
        "url": "https://img.freepik.com/free-photo/modern-medical-equipment-room-with-radiation-therapy-treatment-generated-by-ai_188544-15283.jpg",
        "description": "Hình ảnh xạ trị"
    },
    {
        "name": "patient_care.jpg",
        "url": "https://img.freepik.com/free-photo/doctor-checking-patient-vitals-hospital-room-generated-by-ai_188544-38087.jpg",
        "description": "Hình ảnh chăm sóc bệnh nhân"
    },
    {
        "name": "doctor_planning.jpg",
        "url": "https://img.freepik.com/free-photo/doctor-analyzing-medical-results-with-technology-advancement-generated-by-ai_188544-32593.jpg",
        "description": "Bác sĩ lập kế hoạch"
    },
    {
        "name": "medical_team.jpg",
        "url": "https://img.freepik.com/free-photo/frontview-medical-team-hospital_23-2150711480.jpg",
        "description": "Đội ngũ y tế"
    },
    {
        "name": "rt_machine.jpg",
        "url": "https://img.freepik.com/free-photo/radiation-therapy-equipment-hospital-generated-by-ai_188544-21473.jpg",
        "description": "Máy xạ trị"
    },
    {
        "name": "mlc_visualization.jpg",
        "url": "https://www.researchgate.net/publication/349650252/figure/fig2/AS:995757207465991@1614606882540/A-multileaf-collimator-MLC-design-installed-in-a-LINAC-head-left-and-a-patient-CT.png",
        "description": "Minh họa MLC"
    }
]

def download_image(image_info):
    """Tải hình ảnh từ URL và lưu vào thư mục"""
    try:
        name = image_info["name"]
        url = image_info["url"]
        description = image_info["description"]
        
        output_path = os.path.join(IMAGES_DIR, name)
        
        # Kiểm tra nếu hình ảnh đã tồn tại
        if os.path.exists(output_path):
            print(f"Hình ảnh {name} đã tồn tại, bỏ qua.")
            return True
            
        print(f"Đang tải {name}: {description}")
        
        # Tải hình ảnh
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()
        
        # Lưu hình ảnh
        img = Image.open(BytesIO(response.content))
        img.save(output_path)
        
        print(f"Đã lưu {name} vào {output_path}")
        
        # Tạm dừng ngẫu nhiên để tránh bị chặn
        time.sleep(random.uniform(0.5, 2.0))
        
        return True
    except Exception as e:
        print(f"Lỗi khi tải {image_info['name']}: {str(e)}")
        return False

def main():
    """Hàm chính để tải tất cả hình ảnh"""
    print(f"Bắt đầu tải {len(IMAGES)} hình ảnh vào {IMAGES_DIR}")
    
    success_count = 0
    for image_info in IMAGES:
        if download_image(image_info):
            success_count += 1
    
    print(f"Hoàn thành: {success_count}/{len(IMAGES)} hình ảnh đã tải thành công")

if __name__ == "__main__":
    main() 