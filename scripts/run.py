#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script khởi động nhanh cho QuangStation V2
"""

import sys
import os

# Thêm thư mục gốc vào PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from quangstation.main import main

if __name__ == "__main__":
    main() 