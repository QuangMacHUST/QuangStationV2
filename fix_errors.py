#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script để tự động sửa các lỗi cú pháp trong mã nguồn của QuangStation V2.
"""

import os
import re
import glob

def fix_except_blocks(directory):
    """
    Tìm và sửa lỗi trong các khối except Exception as error
    nơi biến e được sử dụng thay vì error.
    """
    pattern = r'except\s+Exception\s+as\s+error:.*?\n.*?{e}'
    replacement_pattern = r'{e}'
    replacement = r'{error}'
    
    modified_files = 0
    errors_fixed = 0
    
    # Lấy tất cả các file Python
    for py_file in glob.glob(os.path.join(directory, '**', '*.py'), recursive=True):
        with open(py_file, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Tìm các đoạn khớp với mẫu
        matches = re.findall(pattern, content, re.DOTALL)
        if matches:
            # Thay thế {e} bằng {error}
            new_content = re.sub(replacement_pattern, replacement, content)
            
            # Nếu có thay đổi, ghi lại file
            if new_content != content:
                with open(py_file, 'w', encoding='utf-8') as file:
                    file.write(new_content)
                modified_files += 1
                errors_fixed += len(matches)
                print(f"Đã sửa {len(matches)} lỗi trong file {py_file}")
    
    return modified_files, errors_fixed

def fix_getattr_assignment(directory):
    """
    Tìm và sửa lỗi gán giá trị cho kết quả của hàm getattr.
    """
    pattern = r'getattr\(([^,]+),\s*"([^"]+)",\s*{}\)\s*=\s*'
    
    modified_files = 0
    errors_fixed = 0
    
    # Lấy tất cả các file Python
    for py_file in glob.glob(os.path.join(directory, '**', '*.py'), recursive=True):
        with open(py_file, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Tìm các đoạn khớp với mẫu
        matches = re.findall(pattern, content)
        if matches:
            new_content = content
            for obj, attr in matches:
                # Thay thế getattr(obj, "attr", {}) = value bằng obj.attr = value
                error_pattern = f'getattr\\({obj},\\s*"{attr}",\\s*{{}}\\)\\s*='
                replacement = f'{obj}.{attr} ='
                new_content = re.sub(error_pattern, replacement, new_content)
            
            # Nếu có thay đổi, ghi lại file
            if new_content != content:
                with open(py_file, 'w', encoding='utf-8') as file:
                    file.write(new_content)
                modified_files += 1
                errors_fixed += len(matches)
                print(f"Đã sửa {len(matches)} lỗi getattr trong file {py_file}")
    
    return modified_files, errors_fixed

def fix_variables_before_assignment(directory):
    """
    Tìm và sửa lỗi sử dụng biến trước khi gán giá trị.
    """
    # Các biến thường bị sử dụng trước khi được gán giá trị
    variables_to_check = {
        'structure_mask': 'np.zeros_like(self.volume)',
        'dose_slice': 'np.zeros_like(self.volume[0])',
    }
    
    modified_files = 0
    errors_fixed = 0
    
    for py_file in glob.glob(os.path.join(directory, '**', '*.py'), recursive=True):
        with open(py_file, 'r', encoding='utf-8') as file:
            content = file.read()
        
        changed = False
        for var, default in variables_to_check.items():
            # Tìm tất cả các hàm sử dụng biến này
            functions = re.findall(r'def\s+([^(]+)\([^)]*\):.*?' + var, content, re.DOTALL)
            for func in functions:
                # Tìm vị trí của hàm
                func_pattern = r'def\s+' + func + r'\([^)]*\):'
                func_matches = re.finditer(func_pattern, content)
                for match in func_matches:
                    # Tìm thân hàm
                    func_start = match.end()
                    # Tìm vị trí đầu tiên của biến trong hàm
                    var_pos = content.find(var, func_start)
                    if var_pos > 0:
                        # Tìm vị trí của dòng đầu tiên sau định nghĩa hàm
                        next_line_pos = content.find('\n', func_start) + 1
                        # Thêm phép gán mặc định
                        indent_match = re.search(r'(\s+)', content[next_line_pos:next_line_pos+20])
                        indent = indent_match.group(1) if indent_match else '    '
                        
                        # Kiểm tra xem đã có phép gán cho biến này chưa
                        check_pattern = r'def\s+' + func + r'\([^)]*\):.*?(' + var + r'\s*=)'
                        if not re.search(check_pattern, content[:var_pos], re.DOTALL):
                            # Thêm phép gán mặc định
                            insertion = f'{indent}# Giá trị mặc định để tránh lỗi "biến chưa được khởi tạo"\n{indent}{var} = {default}\n'
                            content = content[:next_line_pos] + insertion + content[next_line_pos:]
                            changed = True
                            errors_fixed += 1
                            
        if changed:
            with open(py_file, 'w', encoding='utf-8') as file:
                file.write(content)
            modified_files += 1
            print(f"Đã sửa lỗi sử dụng biến trước khi gán giá trị trong file {py_file}")
    
    return modified_files, errors_fixed

def fix_pil_image_constants(directory):
    """
    Tìm và sửa lỗi liên quan đến hằng số Image.BILINEAR bị gọi sai.
    """
    bilinear_pattern = r'Image\.BILINEAR'
    
    modified_files = 0
    errors_fixed = 0
    
    # Lấy tất cả các file Python
    for py_file in glob.glob(os.path.join(directory, '**', '*.py'), recursive=True):
        with open(py_file, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Kiểm tra xem tệp có import Image từ PIL không
        if 'from PIL import Image' in content and bilinear_pattern in content:
            # Thay thế Image.BILINEAR bằng Image.BICUBIC
            new_content = re.sub(bilinear_pattern, 'Image.BICUBIC', content)
            
            # Nếu có thay đổi, ghi lại file
            if new_content != content:
                with open(py_file, 'w', encoding='utf-8') as file:
                    file.write(new_content)
                modified_files += 1
                count = content.count('Image.BILINEAR')
                errors_fixed += count
                print(f"Đã sửa {count} lỗi hằng số PIL.Image trong file {py_file}")
    
    return modified_files, errors_fixed

def fix_get_config_calls(directory):
    """
    Tìm và sửa lỗi liên quan đến việc gọi hàm get_config() thiếu tham số.
    """
    pattern = r'get_config\(\s*\)'
    replacement = r'get_config("config")'
    
    modified_files = 0
    errors_fixed = 0
    
    # Lấy tất cả các file Python
    for py_file in glob.glob(os.path.join(directory, '**', '*.py'), recursive=True):
        with open(py_file, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Tìm các đoạn khớp với mẫu
        matches = re.findall(pattern, content)
        if matches:
            # Thay thế get_config() bằng get_config("config")
            new_content = re.sub(pattern, replacement, content)
            
            # Nếu có thay đổi, ghi lại file
            if new_content != content:
                with open(py_file, 'w', encoding='utf-8') as file:
                    file.write(new_content)
                modified_files += 1
                errors_fixed += len(matches)
                print(f"Đã sửa {len(matches)} lỗi gọi hàm get_config() trong file {py_file}")
    
    return modified_files, errors_fixed

def fix_load_rt_image_missing_method(directory):
    """
    Tìm và sửa lỗi liên quan đến việc gọi phương thức load_rt_image không tồn tại.
    """
    pattern = r'(self\.image_loader)\.load_rt_image\('
    replacement = r'\1.load_dicom_series('
    
    modified_files = 0
    errors_fixed = 0
    
    # Lấy tất cả các file Python
    for py_file in glob.glob(os.path.join(directory, '**', '*.py'), recursive=True):
        with open(py_file, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Tìm các đoạn khớp với mẫu
        matches = re.findall(pattern, content)
        if matches:
            # Thay thế .load_rt_image bằng .load_dicom_series
            new_content = re.sub(pattern, replacement, content)
            
            # Nếu có thay đổi, ghi lại file
            if new_content != content:
                with open(py_file, 'w', encoding='utf-8') as file:
                    file.write(new_content)
                modified_files += 1
                errors_fixed += len(matches)
                print(f"Đã sửa {len(matches)} lỗi phương thức load_rt_image không tồn tại trong file {py_file}")
    
    return modified_files, errors_fixed

if __name__ == "__main__":
    directory = "quangstation"
    
    # 1. Sửa khối except
    except_files, except_errors = fix_except_blocks(directory)
    print(f"\nĐã sửa tổng cộng {except_errors} lỗi biến trong khối except trên {except_files} files.")
    
    # 2. Sửa getattr assignment
    getattr_files, getattr_errors = fix_getattr_assignment(directory)
    print(f"Đã sửa tổng cộng {getattr_errors} lỗi gán giá trị cho getattr trên {getattr_files} files.")

    # 3. Sửa lỗi PIL.Image.BILINEAR
    pil_files, pil_errors = fix_pil_image_constants(directory)
    print(f"Đã sửa tổng cộng {pil_errors} lỗi hằng số PIL.Image trên {pil_files} files.")
    
    # 4. Sửa lỗi get_config()
    config_files, config_errors = fix_get_config_calls(directory)
    print(f"Đã sửa tổng cộng {config_errors} lỗi gọi hàm get_config() trên {config_files} files.")
    
    # 5. Sửa lỗi load_rt_image
    rt_image_files, rt_image_errors = fix_load_rt_image_missing_method(directory)
    print(f"Đã sửa tổng cộng {rt_image_errors} lỗi phương thức load_rt_image trên {rt_image_files} files.")
    
    # 6. Sửa lỗi biến sử dụng trước khi gán giá trị
    var_files, var_errors = fix_variables_before_assignment(directory)
    print(f"Đã sửa tổng cộng {var_errors} lỗi sử dụng biến trước khi gán giá trị trên {var_files} files.")
    
    print("\nQuá trình sửa lỗi hoàn tất.") 