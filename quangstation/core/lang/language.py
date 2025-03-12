#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module xử lý đa ngôn ngữ cho QuangStation V2
"""

import os
import json
import logging
from quangstation.core.utils.resource_utils import get_lang_path

logger = logging.getLogger(__name__)

class LanguageManager:
    """
    Quản lý ngôn ngữ và dịch thuật trong ứng dụng
    """
    def __init__(self, default_lang="en"):
        self.current_lang = default_lang
        self.translations = {}
        self.available_langs = self._get_available_languages()
        self.load_language(default_lang)
    
    def _get_available_languages(self):
        """
        Lấy danh sách các ngôn ngữ có sẵn dựa trên các file trong thư mục lang
        
        Returns:
            list: Danh sách các ngôn ngữ có sẵn
        """
        lang_path = get_lang_path()
        langs = {}
        
        if os.path.exists(lang_path):
            for file in os.listdir(lang_path):
                if file.endswith('.json'):
                    lang_code = file.split('.')[0]
                    lang_name = self._get_language_name(lang_code)
                    langs[lang_code] = lang_name
        
        # Đảm bảo luôn có tiếng Anh
        if 'en' not in langs:
            langs['en'] = 'English'
            
        return langs
    
    def _get_language_name(self, lang_code):
        """
        Lấy tên ngôn ngữ dựa trên mã ngôn ngữ
        
        Args:
            lang_code (str): Mã ngôn ngữ (ví dụ: 'en', 'vi')
            
        Returns:
            str: Tên ngôn ngữ
        """
        language_names = {
            'en': 'English',
            'vi': 'Tiếng Việt',
            'fr': 'Français',
            'de': 'Deutsch',
            'es': 'Español',
            'zh': '中文',
            'ja': '日本語',
            'ko': '한국어',
            'ru': 'Русский'
        }
        
        return language_names.get(lang_code, lang_code.upper())
    
    def load_language(self, lang_code):
        """
        Tải file ngôn ngữ dựa trên mã ngôn ngữ
        
        Args:
            lang_code (str): Mã ngôn ngữ (ví dụ: 'en', 'vi')
            
        Returns:
            bool: True nếu tải thành công, False nếu thất bại
        """
        lang_path = get_lang_path()
        file_path = os.path.join(lang_path, f"{lang_code}.json")
        
        # Nếu không tìm thấy file ngôn ngữ, sử dụng tiếng Anh làm mặc định
        if not os.path.exists(file_path):
            logger.warning("Không tìm thấy file ngôn ngữ: %s, sử dụng tiếng Anh làm mặc định", file_path)
            file_path = os.path.join(lang_path, "en.json")
            
            # Nếu vẫn không tìm thấy file tiếng Anh, tạo một file mặc định
            if not os.path.exists(file_path):
                logger.warning("Không tìm thấy file ngôn ngữ tiếng Anh mặc định")
                return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
            
            self.current_lang = lang_code
            logger.info("Đã tải ngôn ngữ: %s", lang_code)
            return True
        except Exception as e:
            logger.error("Lỗi khi tải file ngôn ngữ: %s - %s", file_path, str(e))
            return False
    
    def get_text(self, key, default=None):
        """
        Lấy văn bản dịch dựa trên khóa
        
        Args:
            key (str): Khóa dịch (ví dụ: 'app_name', 'main_menu.file')
            default (str, optional): Giá trị mặc định nếu không tìm thấy khóa
            
        Returns:
            str: Văn bản dịch
        """
        if not key:
            return default or key
        
        # Hỗ trợ khóa phân cấp, ví dụ: main_menu.file
        parts = key.split('.')
        current = self.translations
        
        try:
            for part in parts:
                current = current[part]
            
            return current
        except (KeyError, TypeError):
            return default or key
    
    def get_available_languages(self):
        """
        Lấy danh sách các ngôn ngữ có sẵn
        
        Returns:
            dict: Từ điển với khóa là mã ngôn ngữ và giá trị là tên ngôn ngữ
        """
        return self.available_langs
    
    def get_current_language(self):
        """
        Lấy mã ngôn ngữ hiện tại
        
        Returns:
            str: Mã ngôn ngữ hiện tại
        """
        return self.current_lang

# Tạo một phiên bản singleton để sử dụng trong toàn bộ ứng dụng
_language_manager = None

def init_language_manager(default_lang="en"):
    """
    Khởi tạo language manager
    
    Args:
        default_lang (str, optional): Ngôn ngữ mặc định
        
    Returns:
        LanguageManager: Phiên bản language manager
    """
    global _language_manager
    
    if _language_manager is None:
        _language_manager = LanguageManager(default_lang)
    
    return _language_manager

def get_language_manager():
    """
    Lấy phiên bản language manager hiện tại
    
    Returns:
        LanguageManager: Phiên bản language manager
    """
    global _language_manager
    
    if _language_manager is None:
        _language_manager = LanguageManager()
    
    return _language_manager

def get_text(key, default=None):
    """
    Hàm tiện ích toàn cục để lấy văn bản dịch
    
    Args:
        key (str): Khóa dịch
        default (str, optional): Giá trị mặc định nếu không tìm thấy khóa
        
    Returns:
        str: Văn bản dịch
    """
    lang_manager = get_language_manager()
    return lang_manager.get_text(key, default)

def load_language(lang_code):
    """
    Hàm tiện ích toàn cục để tải ngôn ngữ
    
    Args:
        lang_code (str): Mã ngôn ngữ
        
    Returns:
        bool: True nếu tải thành công, False nếu thất bại
    """
    lang_manager = get_language_manager()
    return lang_manager.load_language(lang_code)

def get_available_languages():
    """
    Hàm tiện ích toàn cục để lấy danh sách các ngôn ngữ có sẵn
    
    Returns:
        dict: Từ điển với khóa là mã ngôn ngữ và giá trị là tên ngôn ngữ
    """
    lang_manager = get_language_manager()
    return lang_manager.get_available_languages()

def get_current_language():
    """
    Hàm tiện ích toàn cục để lấy mã ngôn ngữ hiện tại
    
    Returns:
        str: Mã ngôn ngữ hiện tại
    """
    lang_manager = get_language_manager()
    return lang_manager.get_current_language()
