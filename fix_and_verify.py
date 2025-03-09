#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script tong hop de chay ca hai script (sua loi va kiem tra) cung mot luc
"""

import os
import sys
import subprocess
import time

def run_script(script_name, directory=None):
    """Chay mot script Python voi tham so tuy chon"""
    cmd = [sys.executable, script_name]
    if directory:
        cmd.append(directory)
    
    print(f"Dang chay {script_name}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print(f"Loi: {result.stderr}")
    
    return result.returncode == 0

def main():
    """Ham chinh"""
    # Lay thu muc tu tham so dong lenh hoac su dung mac dinh
    directory = None
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    
    print("=" * 80)
    print("CONG CU SUA LOI VA KIEM TRA TU DONG CHO QUANGSTATION V2")
    print("=" * 80)
    
    # Kiem tra xem cac script can thiet co ton tai khong
    if not os.path.exists("fix_errors.py"):
        print("Loi: Khong tim thay file fix_errors.py")
        return
    
    if not os.path.exists("verify_fixes.py"):
        print("Loi: Khong tim thay file verify_fixes.py")
        return
    
    # Chay script sua loi
    print("\n=== BUOC 1: SUA LOI TU DONG ===\n")
    fix_success = run_script("fix_errors.py", directory)
    
    if not fix_success:
        print("Canh bao: Script sua loi co the da gap van de.")
    
    # Tam dung de nguoi dung co the doc ket qua
    print("\nDa hoan thanh buoc sua loi. Dang chuyen sang buoc kiem tra...")
    time.sleep(2)
    
    # Chay script kiem tra
    print("\n=== BUOC 2: KIEM TRA KET QUA ===\n")
    verify_success = run_script("verify_fixes.py", directory)
    
    if not verify_success:
        print("Canh bao: Script kiem tra co the da gap van de.")
    
    print("\n=== KET LUAN ===")
    print("Qua trinh sua loi va kiem tra da hoan tat.")
    print("Vui long kiem tra cac file log de biet them chi tiet.")
    print("Neu van con loi, ban co the chay lai script nay hoac sua thu cong.")

if __name__ == "__main__":
    main() 