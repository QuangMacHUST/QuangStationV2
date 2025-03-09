#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script kiem tra xem cac loi da duoc sua chua dung cach chua
"""

import os
import re
import sys
import time

def check_except_blocks(file_path):
    """Kiem tra cac khoi except Exception as e:"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Tim tat ca cac khoi except Exception as e:
        pattern = r'except\s+Exception\s+as\s+e:'
        matches = re.findall(pattern, content)
        
        if matches:
            print(f"[CANH BAO] File {file_path} van con {len(matches)} khoi except Exception as e:")
            return len(matches)
        
        return 0
    except Exception as error:
        print(f"Loi khi kiem tra file {file_path}: {str(error)}")
        return 0

def check_attribute_access(file_path):
    """Kiem tra cac truy cap thuoc tinh truc tiep"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        issues = 0
        
        # Kiem tra self.image_metadata
        pattern_metadata = r'self\.image_metadata'
        metadata_matches = re.findall(pattern_metadata, content)
        if metadata_matches:
            print(f"[CANH BAO] File {file_path} van con {len(metadata_matches)} truy cap truc tiep den self.image_metadata")
            issues += len(metadata_matches)
        
        # Kiem tra self.structure_colors
        pattern_colors = r'self\.structure_colors'
        colors_matches = re.findall(pattern_colors, content)
        if colors_matches:
            print(f"[CANH BAO] File {file_path} van con {len(colors_matches)} truy cap truc tiep den self.structure_colors")
            issues += len(colors_matches)
        
        # Kiem tra self.beams (phuc tap hon, can loai tru cac dinh nghia)
        lines = content.split('\n')
        beams_issues = 0
        
        for line in lines:
            if 'self.beams' in line and not ('=' in line or 'def ' in line):
                if 'getattr(self, "beams"' not in line:
                    beams_issues += 1
        
        if beams_issues > 0:
            print(f"[CANH BAO] File {file_path} van con {beams_issues} truy cap truc tiep den self.beams")
            issues += beams_issues
        
        return issues
    except Exception as error:
        print(f"Loi khi kiem tra thuoc tinh trong file {file_path}: {str(error)}")
        return 0

def check_directory(directory):
    """Kiem tra tat ca cac file trong thu muc"""
    total_issues = 0
    files_with_issues = 0
    all_files = 0
    
    print(f"Dang kiem tra cac file trong thu muc {directory}...")
    
    # Tao file log
    log_file = f"verify_results_{time.strftime('%Y%m%d_%H%M%S')}.log"
    with open(log_file, 'w', encoding='utf-8') as log:
        log.write(f"=== KET QUA KIEM TRA {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    all_files += 1
                    file_path = os.path.join(root, file)
                    
                    # Ghi log
                    log.write(f"Kiem tra file: {file_path}\n")
                    
                    # Kiem tra cac khoi except
                    except_issues = check_except_blocks(file_path)
                    
                    # Kiem tra cac truy cap thuoc tinh
                    attr_issues = check_attribute_access(file_path)
                    
                    # Tong hop ket qua
                    issues = except_issues + attr_issues
                    if issues > 0:
                        files_with_issues += 1
                        total_issues += issues
                        log.write(f"  - Tim thay {issues} van de\n")
                    else:
                        log.write(f"  - OK\n")
    
    print(f"Da kiem tra {all_files} tep Python. Chi tiet duoc luu trong file {log_file}")
    return total_issues, files_with_issues, all_files

def main():
    """Ham chinh"""
    # Lay thu muc tu tham so dong lenh hoac su dung mac dinh
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = 'quangstation'
    
    # Kiem tra xem thu muc co ton tai khong
    if not os.path.exists(directory):
        print(f"Thu muc {directory} khong ton tai")
        return
    
    print("=== BAT DAU KIEM TRA ===")
    
    # Kiem tra thu muc
    total_issues, files_with_issues, all_files = check_directory(directory)
    
    print("\n=== KET QUA KIEM TRA ===")
    if total_issues > 0:
        print(f"Tim thay {total_issues} van de trong {files_with_issues}/{all_files} tep.")
        print("Vui long chay lai script sua loi de khac phuc cac van de con lai.")
    else:
        print(f"Khong tim thay van de nao trong {all_files} tep Python. Tat ca cac loi da duoc sua chua!")
    
    print("Qua trinh kiem tra da hoan tat!")

if __name__ == "__main__":
    main() 