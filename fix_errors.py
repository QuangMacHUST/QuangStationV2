#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script sua loi tu dong cho du an QuangStation V2
"""

import os
import re
import sys

def fix_e_in_except_blocks(file_path):
    """Sua loi bien e khong duoc dinh nghia trong khoi except"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Tim tat ca cac khoi except Exception as e:
        pattern = r'except\s+Exception\s+as\s+e:'
        matches = re.findall(pattern, content)
        
        if not matches:
            return 0
        
        # Thay the e bang error
        fixed_content = re.sub(pattern, 'except Exception as error:', content)
        
        # Thay the cac su dung cua e trong khoi except
        fixed_content = re.sub(r'(\{str\()e(\)\})', r'\1error\2', fixed_content)
        fixed_content = re.sub(r'str\(e\)', 'str(error)', fixed_content)
        
        # Luu lai file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        return len(matches)
    except Exception as error:
        print(f"Loi khi sua bien e trong file {file_path}: {str(error)}")
        return 0

def fix_missing_attributes(file_path):
    """Sua loi cac thuoc tinh thieu trong lop"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        fixed = 0
        
        # Tim va sua loi self.image_metadata
        pattern_metadata = r'self\.image_metadata'
        if re.search(pattern_metadata, content):
            content = re.sub(pattern_metadata, 'getattr(self, "image_metadata", {})', content)
            fixed += 1
        
        # Tim va sua loi self.structure_colors
        pattern_colors = r'self\.structure_colors'
        if re.search(pattern_colors, content):
            content = re.sub(pattern_colors, 'getattr(self, "structure_colors", {})', content)
            fixed += 1
        
        # Tim va sua loi self.beams - su dung cach tiep can khac de tranh loi look-behind
        lines = content.split('\n')
        new_lines = []
        beams_fixed = False
        
        for line in lines:
            # Bo qua cac dong dinh nghia self.beams
            if 'self.beams' in line and ('=' in line or 'def ' in line):
                new_lines.append(line)
            # Thay the cac truong hop su dung self.beams
            elif 'self.beams' in line:
                new_line = line.replace('self.beams', 'getattr(self, "beams", {})')
                new_lines.append(new_line)
                beams_fixed = True
            else:
                new_lines.append(line)
        
        if beams_fixed:
            content = '\n'.join(new_lines)
            fixed += 1
        
        # Luu lai file neu co sua doi
        if fixed > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return fixed
    except Exception as error:
        print(f"Loi khi sua thuoc tinh trong file {file_path}: {str(error)}")
        return 0

def fix_import_errors(file_path):
    """Sua loi import thieu hoac sai cach"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        fixed = 0
        
        # Them import datetime neu co su dung datetime.now()
        if 'datetime.now()' in content and 'from datetime import ' not in content and 'import datetime' not in content:
            if '#!/usr/bin/env python' in content:
                content = content.replace('#!/usr/bin/env python\n', '#!/usr/bin/env python\nimport datetime\n')
            else:
                content = 'import datetime\n' + content
            fixed += 1
        
        # Luu lai file neu co sua doi
        if fixed > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return fixed
    except Exception as error:
        print(f"Loi khi sua import trong file {file_path}: {str(error)}")
        return 0

def fix_errors_in_directory(directory):
    """Sua loi trong toan bo thu muc"""
    fixed_files = 0
    
    print(f"Dang kiem tra va sua loi trong thu muc {directory}...")
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                fixed = 0
                
                # Sua loi except blocks
                except_fixed = fix_e_in_except_blocks(file_path)
                fixed += except_fixed
                
                # Sua loi missing attributes
                attr_fixed = fix_missing_attributes(file_path)
                fixed += attr_fixed
                
                # Sua loi import
                import_fixed = fix_import_errors(file_path)
                fixed += import_fixed
                
                if fixed > 0:
                    fixed_files += 1
                    print(f'- Da sua {fixed} loi trong file {file_path}:')
                    if except_fixed > 0:
                        print(f'  + {except_fixed} loi bien trong khoi except')
                    if attr_fixed > 0:
                        print(f'  + {attr_fixed} loi thuoc tinh khong ton tai')
                    if import_fixed > 0:
                        print(f'  + {import_fixed} loi import')
    
    return fixed_files

def main():
    """Ham chinh"""
    # Lay thu muc cua script hien tai
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = 'quangstation'
    
    # Kiem tra xem thu muc co ton tai khong
    if not os.path.exists(directory):
        print(f"Thu muc {directory} khong ton tai")
        return
    
    print("=== BAT DAU SUA LOI TU DONG ===")
    
    # Sua loi trong thu muc
    fixed_files = fix_errors_in_directory(directory)
    
    print("=== KET QUA SUA LOI ===")
    print(f"Tong cong da sua loi trong {fixed_files} tep.")
    print("Qua trinh sua loi da hoan tat!")

if __name__ == "__main__":
    main() 