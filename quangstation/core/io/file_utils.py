#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tiện ích xử lý file trong hệ thống QuangStation

Module này cung cấp các hàm tiện ích để xử lý file, bao gồm:
- Đọc/ghi file với các định dạng khác nhau (CSV, Excel, JSON, v.v.)
- Xử lý đường dẫn file
- Tạo và quản lý thư mục tạm
- Nén và giải nén file
- Kiểm tra loại file và dung lượng
"""

import os
import shutil
import tempfile
import json
import csv
import zipfile
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Union, Optional, Tuple

# Thiết lập logging
logger = logging.getLogger(__name__)

# Constants
SUPPORTED_IMAGE_EXTENSIONS = ('.dcm', '.dicom', '.ima', '.png', '.jpg', '.jpeg', '.tiff', '.tif')
SUPPORTED_DOCUMENT_EXTENSIONS = ('.pdf', '.docx', '.doc', '.rtf', '.txt')
SUPPORTED_DATA_EXTENSIONS = ('.csv', '.xlsx', '.xls', '.json', '.xml')
TEMP_DIR = tempfile.gettempdir() / Path('quangstation')


def ensure_directory_exists(directory_path: Union[str, Path]) -> Path:
    """
    Đảm bảo thư mục tồn tại, tạo nếu cần
    
    Args:
        directory_path: Đường dẫn thư mục cần đảm bảo tồn tại
        
    Returns:
        Path: Đối tượng Path đến thư mục
    """
    directory = Path(directory_path)
    if not directory.exists():
        directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"Đã tạo thư mục: {directory}")
    return directory


def get_temp_directory() -> Path:
    """
    Lấy đường dẫn đến thư mục tạm của ứng dụng
    
    Returns:
        Path: Đường dẫn đến thư mục tạm
    """
    return ensure_directory_exists(TEMP_DIR)


def create_temp_file(suffix: str = None, prefix: str = "quangstation_", directory: Path = None) -> Path:
    """
    Tạo file tạm thời
    
    Args:
        suffix: Hậu tố (extension) của file
        prefix: Tiền tố của tên file
        directory: Thư mục chứa file, mặc định là thư mục tạm của ứng dụng
        
    Returns:
        Path: Đường dẫn đến file tạm
    """
    if directory is None:
        directory = get_temp_directory()
    else:
        directory = ensure_directory_exists(directory)
    
    fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=directory)
    os.close(fd)  # Đóng file descriptor để tránh rò rỉ tài nguyên
    
    logger.debug(f"Đã tạo file tạm: {temp_path}")
    return Path(temp_path)


def clean_temp_files(max_age_days: float = 7.0) -> int:
    """
    Dọn dẹp các file tạm quá hạn
    
    Args:
        max_age_days: Tuổi tối đa của file tính bằng ngày
        
    Returns:
        int: Số lượng file đã xóa
    """
    temp_dir = get_temp_directory()
    now = datetime.now()
    deleted_count = 0
    
    for item in temp_dir.glob("quangstation_*"):
        if item.is_file():
            file_age = now - datetime.fromtimestamp(item.stat().st_mtime)
            if file_age.days >= max_age_days:
                try:
                    item.unlink()
                    deleted_count += 1
                    logger.debug(f"Đã xóa file tạm cũ: {item}")
                except OSError as e:
                    logger.warning(f"Không thể xóa file tạm {item}: {e}")
    
    logger.info(f"Đã xóa {deleted_count} file tạm cũ")
    return deleted_count


def get_file_size(file_path: Union[str, Path], human_readable: bool = False) -> Union[int, str]:
    """
    Lấy kích thước file
    
    Args:
        file_path: Đường dẫn đến file
        human_readable: Nếu True, trả về kích thước dạng đọc được (KB, MB, GB)
        
    Returns:
        Union[int, str]: Kích thước file dạng bytes hoặc chuỗi đọc được
    """
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"File không tồn tại hoặc không phải là file: {path}")
    
    size_bytes = path.stat().st_size
    
    if not human_readable:
        return size_bytes
    
    # Chuyển đổi sang đơn vị đọc được
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = size_bytes
    unit_index = 0
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.2f} {units[unit_index]}"


def is_valid_extension(file_path: Union[str, Path], allowed_extensions: Tuple[str, ...]) -> bool:
    """
    Kiểm tra xem file có phần mở rộng hợp lệ hay không
    
    Args:
        file_path: Đường dẫn đến file
        allowed_extensions: Danh sách các phần mở rộng được cho phép
        
    Returns:
        bool: True nếu file có phần mở rộng hợp lệ, False nếu không
    """
    path = Path(file_path)
    extension = path.suffix.lower()
    return extension in allowed_extensions


def is_image_file(file_path: Union[str, Path]) -> bool:
    """
    Kiểm tra xem file có phải là file hình ảnh hợp lệ hay không
    
    Args:
        file_path: Đường dẫn đến file
        
    Returns:
        bool: True nếu file là file hình ảnh, False nếu không
    """
    return is_valid_extension(file_path, SUPPORTED_IMAGE_EXTENSIONS)


def is_document_file(file_path: Union[str, Path]) -> bool:
    """
    Kiểm tra xem file có phải là file tài liệu hợp lệ hay không
    
    Args:
        file_path: Đường dẫn đến file
        
    Returns:
        bool: True nếu file là file tài liệu, False nếu không
    """
    return is_valid_extension(file_path, SUPPORTED_DOCUMENT_EXTENSIONS)


def is_data_file(file_path: Union[str, Path]) -> bool:
    """
    Kiểm tra xem file có phải là file dữ liệu hợp lệ hay không
    
    Args:
        file_path: Đường dẫn đến file
        
    Returns:
        bool: True nếu file là file dữ liệu, False nếu không
    """
    return is_valid_extension(file_path, SUPPORTED_DATA_EXTENSIONS)


def load_json(file_path: Union[str, Path]) -> Any:
    """
    Đọc dữ liệu từ file JSON
    
    Args:
        file_path: Đường dẫn đến file JSON
        
    Returns:
        Any: Dữ liệu đọc được từ file JSON
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File không tồn tại: {path}")
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Lỗi đọc file JSON {path}: {e}")
        raise


def save_json(data: Any, file_path: Union[str, Path], indent: int = 4) -> None:
    """
    Lưu dữ liệu vào file JSON
    
    Args:
        data: Dữ liệu cần lưu
        file_path: Đường dẫn đến file JSON
        indent: Số khoảng trắng để thụt lề, mặc định là 4
    """
    path = Path(file_path)
    ensure_directory_exists(path.parent)
    
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        logger.debug(f"Đã lưu dữ liệu vào file JSON: {path}")
    except Exception as e:
        logger.error(f"Lỗi lưu file JSON {path}: {e}")
        raise


def load_csv(file_path: Union[str, Path], has_header: bool = True, delimiter: str = ',') -> List[Dict[str, str]]:
    """
    Đọc dữ liệu từ file CSV
    
    Args:
        file_path: Đường dẫn đến file CSV
        has_header: Nếu True, dòng đầu tiên được xem là tiêu đề
        delimiter: Ký tự phân cách các cột
        
    Returns:
        List[Dict[str, str]]: Danh sách các dòng, mỗi dòng là một từ điển với key là tên cột
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File không tồn tại: {path}")
    
    try:
        with open(path, 'r', encoding='utf-8', newline='') as f:
            reader = csv.reader(f, delimiter=delimiter)
            
            if has_header:
                header = next(reader)
                data = [dict(zip(header, row)) for row in reader]
            else:
                data = [row for row in reader]
        
        logger.debug(f"Đã đọc {len(data)} dòng từ file CSV: {path}")
        return data
    except Exception as e:
        logger.error(f"Lỗi đọc file CSV {path}: {e}")
        raise


def save_csv(data: List[Dict[str, Any]], file_path: Union[str, Path], delimiter: str = ',') -> None:
    """
    Lưu dữ liệu vào file CSV
    
    Args:
        data: Danh sách các dòng, mỗi dòng là một từ điển với key là tên cột
        file_path: Đường dẫn đến file CSV
        delimiter: Ký tự phân cách các cột
    """
    path = Path(file_path)
    ensure_directory_exists(path.parent)
    
    try:
        # Lấy tất cả các key có thể có trong bất kỳ dòng nào
        all_keys = set()
        for row in data:
            all_keys.update(row.keys())
        
        with open(path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(all_keys), delimiter=delimiter)
            writer.writeheader()
            writer.writerows(data)
        
        logger.debug(f"Đã lưu {len(data)} dòng vào file CSV: {path}")
    except Exception as e:
        logger.error(f"Lỗi lưu file CSV {path}: {e}")
        raise


def compress_files(files: List[Union[str, Path]], output_zip: Union[str, Path]) -> Path:
    """
    Nén danh sách các file vào một file ZIP
    
    Args:
        files: Danh sách các đường dẫn đến file cần nén
        output_zip: Đường dẫn đến file ZIP đầu ra
        
    Returns:
        Path: Đường dẫn đến file ZIP đã tạo
    """
    output_path = Path(output_zip)
    ensure_directory_exists(output_path.parent)
    
    try:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file in files:
                file_path = Path(file)
                if file_path.exists() and file_path.is_file():
                    zip_file.write(file_path, file_path.name)
                    logger.debug(f"Đã thêm file vào ZIP: {file_path}")
                else:
                    logger.warning(f"Bỏ qua file không tồn tại: {file_path}")
        
        logger.info(f"Đã nén {len(files)} file vào: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Lỗi nén file {output_path}: {e}")
        raise


def extract_zip(zip_file: Union[str, Path], output_dir: Union[str, Path] = None) -> Path:
    """
    Giải nén file ZIP
    
    Args:
        zip_file: Đường dẫn đến file ZIP
        output_dir: Thư mục đầu ra, mặc định là thư mục cùng cấp với file ZIP
        
    Returns:
        Path: Đường dẫn đến thư mục đã giải nén
    """
    zip_path = Path(zip_file)
    if not zip_path.exists():
        raise FileNotFoundError(f"File ZIP không tồn tại: {zip_path}")
    
    if output_dir is None:
        output_dir = zip_path.parent / zip_path.stem
    
    output_path = Path(output_dir)
    ensure_directory_exists(output_path)
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(output_path)
        
        logger.info(f"Đã giải nén {zip_path} vào: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Lỗi giải nén file {zip_path}: {e}")
        raise


def copy_file(source: Union[str, Path], destination: Union[str, Path], overwrite: bool = False) -> Path:
    """
    Sao chép file từ nguồn đến đích
    
    Args:
        source: Đường dẫn file nguồn
        destination: Đường dẫn file đích
        overwrite: Nếu True, ghi đè lên file đích nếu đã tồn tại
        
    Returns:
        Path: Đường dẫn đến file đích
    """
    source_path = Path(source)
    dest_path = Path(destination)
    
    if not source_path.exists():
        raise FileNotFoundError(f"File nguồn không tồn tại: {source_path}")
    
    if dest_path.exists() and not overwrite:
        logger.warning(f"File đích đã tồn tại và không ghi đè: {dest_path}")
        return dest_path
    
    ensure_directory_exists(dest_path.parent)
    
    try:
        shutil.copy2(source_path, dest_path)
        logger.debug(f"Đã sao chép file từ {source_path} đến {dest_path}")
        return dest_path
    except Exception as e:
        logger.error(f"Lỗi sao chép file từ {source_path} đến {dest_path}: {e}")
        raise


def safe_delete(path: Union[str, Path], confirm: bool = True) -> bool:
    """
    Xóa file/thư mục một cách an toàn
    
    Args:
        path: Đường dẫn đến file/thư mục cần xóa
        confirm: Nếu True, hỏi xác nhận trước khi xóa
        
    Returns:
        bool: True nếu xóa thành công, False nếu không
    """
    file_path = Path(path)
    
    if not file_path.exists():
        logger.warning(f"File/thư mục không tồn tại: {file_path}")
        return False
    
    if confirm:
        response = input(f"Bạn có chắc chắn muốn xóa '{file_path}'? (y/n): ")
        if response.lower() not in ['y', 'yes']:
            logger.info(f"Đã hủy xóa file/thư mục: {file_path}")
            return False
    
    try:
        if file_path.is_file():
            file_path.unlink()
        else:
            shutil.rmtree(file_path)
        
        logger.info(f"Đã xóa file/thư mục: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Lỗi xóa file/thư mục {file_path}: {e}")
        return False


def get_file_info(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Lấy thông tin về file
    
    Args:
        file_path: Đường dẫn đến file
        
    Returns:
        Dict[str, Any]: Thông tin về file
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"File không tồn tại: {path}")
    
    stat = path.stat()
    
    return {
        'name': path.name,
        'extension': path.suffix,
        'size_bytes': stat.st_size,
        'size_human': get_file_size(path, human_readable=True),
        'created_time': datetime.fromtimestamp(stat.st_ctime),
        'modified_time': datetime.fromtimestamp(stat.st_mtime),
        'is_file': path.is_file(),
        'is_directory': path.is_dir(),
        'absolute_path': str(path.absolute()),
        'parent_directory': str(path.parent)
    }


# Hàm tiện ích chuyên dụng cho QuangStation

def get_patient_directory(patient_id: str, base_dir: Union[str, Path] = None) -> Path:
    """
    Lấy đường dẫn đến thư mục của bệnh nhân
    
    Args:
        patient_id: ID của bệnh nhân
        base_dir: Thư mục cơ sở, mặc định là thư mục dữ liệu của ứng dụng
        
    Returns:
        Path: Đường dẫn đến thư mục của bệnh nhân
    """
    if base_dir is None:
        from quangstation.core.utils.config import get_config
        base_dir = get_config().get('data_directory', 'data')
    
    patient_dir = Path(base_dir) / f"patient_{patient_id}"
    return ensure_directory_exists(patient_dir)


def get_plan_directory(patient_id: str, plan_id: str, base_dir: Union[str, Path] = None) -> Path:
    """
    Lấy đường dẫn đến thư mục của kế hoạch
    
    Args:
        patient_id: ID của bệnh nhân
        plan_id: ID của kế hoạch
        base_dir: Thư mục cơ sở, mặc định là thư mục dữ liệu của ứng dụng
        
    Returns:
        Path: Đường dẫn đến thư mục của kế hoạch
    """
    patient_dir = get_patient_directory(patient_id, base_dir)
    plan_dir = patient_dir / f"plan_{plan_id}"
    return ensure_directory_exists(plan_dir)


def get_backup_directory() -> Path:
    """
    Lấy đường dẫn đến thư mục sao lưu
    
    Returns:
        Path: Đường dẫn đến thư mục sao lưu
    """
    from quangstation.core.utils.config import get_config
    backup_dir = Path(get_config().get('backup_directory', 'backups'))
    return ensure_directory_exists(backup_dir)


def create_backup(source_dir: Union[str, Path], backup_name: str = None) -> Path:
    """
    Tạo bản sao lưu của thư mục
    
    Args:
        source_dir: Thư mục cần sao lưu
        backup_name: Tên của bản sao lưu, mặc định là timestamp
        
    Returns:
        Path: Đường dẫn đến file sao lưu
    """
    source_path = Path(source_dir)
    
    if not source_path.exists():
        raise FileNotFoundError(f"Thư mục nguồn không tồn tại: {source_path}")
    
    if backup_name is None:
        now = datetime.now()
        backup_name = f"{source_path.name}_{now.strftime('%Y%m%d_%H%M%S')}"
    
    backup_dir = get_backup_directory()
    backup_file = backup_dir / f"{backup_name}.zip"
    
    # Danh sách các file cần sao lưu
    files_to_backup = []
    for file_path in source_path.rglob('*'):
        if file_path.is_file():
            files_to_backup.append(file_path)
    
    # Nén các file vào file sao lưu
    compress_files(files_to_backup, backup_file)
    
    logger.info(f"Đã tạo bản sao lưu: {backup_file}")
    return backup_file


def restore_backup(backup_file: Union[str, Path], destination: Union[str, Path] = None) -> Path:
    """
    Khôi phục từ bản sao lưu
    
    Args:
        backup_file: File sao lưu
        destination: Thư mục đích, mặc định là thư mục gốc của ứng dụng
        
    Returns:
        Path: Đường dẫn đến thư mục đã khôi phục
    """
    backup_path = Path(backup_file)
    
    if not backup_path.exists():
        raise FileNotFoundError(f"File sao lưu không tồn tại: {backup_path}")
    
    if destination is None:
        from quangstation.core.utils.config import get_config
        destination = get_config().get('data_directory', 'data')
    
    dest_path = Path(destination)
    
    # Giải nén file sao lưu
    extract_zip(backup_path, dest_path)
    
    logger.info(f"Đã khôi phục từ bản sao lưu {backup_path} vào {dest_path}")
    return dest_path
