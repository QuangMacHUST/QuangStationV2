"""
Module cung cấp các công cụ đo hiệu năng và tối ưu hóa.
"""

import os
import time
import psutil
import threading
import numpy as np
from typing import Dict, Any, Optional, Callable, Tuple, List, Union
import tempfile
import logging

from quangstation.utils.logging import get_logger

logger = get_logger(__name__)

# Số thread mặc định sử dụng cho xử lý song song
DEFAULT_NUM_THREADS = max(1, os.cpu_count() - 1)

# Lớp bộ nhớ đệm toàn cục
class MemoryCache:
    """Lớp quản lý bộ nhớ đệm cho dữ liệu tính toán."""
    
    def __init__(self, max_size_mb: int = 1024):
        """
        Khởi tạo bộ nhớ đệm với kích thước tối đa.
        
        Args:
            max_size_mb: Kích thước tối đa của bộ nhớ đệm (MB).
        """
        self.max_size = max_size_mb * 1024 * 1024  # Chuyển đổi sang byte
        self.current_size = 0
        self.cache = {}
        logger.debug(f"Đã khởi tạo MemoryCache với kích thước tối đa {max_size_mb} MB")
    
    def get(self, key: str):
        """Lấy giá trị từ bộ nhớ đệm."""
        return self.cache.get(key)
    
    def set(self, key: str, value, size: int = None):
        """Lưu giá trị vào bộ nhớ đệm."""
        if key in self.cache:
            self.remove(key)
        
        # Ước tính kích thước nếu không được cung cấp
        if size is None:
            if hasattr(value, 'nbytes'):
                size = value.nbytes
            else:
                # Ước tính kích thước
                import sys
                size = sys.getsizeof(value)
        
        # Kiểm tra xem có đủ dung lượng không
        if size > self.max_size:
            logger.warning(f"Không thể lưu cache: kích thước giá trị ({size} bytes) lớn hơn kích thước tối đa của cache")
            return False
        
        # Giải phóng không gian nếu cần
        while self.current_size + size > self.max_size and self.cache:
            # Xóa mục cũ nhất
            oldest_key = next(iter(self.cache))
            self.remove(oldest_key)
        
        # Lưu giá trị mới
        self.cache[key] = {'value': value, 'size': size, 'timestamp': time.time()}
        self.current_size += size
        return True
    
    def remove(self, key: str):
        """Xóa mục khỏi bộ nhớ đệm."""
        if key in self.cache:
            self.current_size -= self.cache[key]['size']
            del self.cache[key]
    
    def clear(self):
        """Xóa toàn bộ bộ nhớ đệm."""
        self.cache.clear()
        self.current_size = 0
    
    def get_stats(self):
        """Lấy thống kê về bộ nhớ đệm."""
        return {
            'size': self.current_size,
            'max_size': self.max_size,
            'usage_percent': (self.current_size / self.max_size) * 100 if self.max_size > 0 else 0,
            'items': len(self.cache)
        }

# Tạo singleton instance
_global_memory_cache = None

def get_memory_cache(max_size_mb: int = 1024) -> MemoryCache:
    """Lấy singleton instance của MemoryCache."""
    global _global_memory_cache
    
    if _global_memory_cache is None:
        _global_memory_cache = MemoryCache(max_size_mb)
        
    return _global_memory_cache

# ------------------------ Hàm theo dõi hiệu năng ------------------------
def get_system_info() -> Dict[str, Any]:
    """Lấy thông tin về tài nguyên hệ thống."""
    try:
        # Thông tin CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count(logical=True)
        cpu_physical = psutil.cpu_count(logical=False)
        
        # Thông tin bộ nhớ
        memory = psutil.virtual_memory()
        memory_total = memory.total / (1024 * 1024 * 1024)  # GB
        memory_available = memory.available / (1024 * 1024 * 1024)  # GB
        memory_used = memory.used / (1024 * 1024 * 1024)  # GB
        memory_percent = memory.percent
        
        # Thông tin đĩa
        disk = psutil.disk_usage('/')
        disk_total = disk.total / (1024 * 1024 * 1024)  # GB
        disk_free = disk.free / (1024 * 1024 * 1024)  # GB
        disk_used = disk.used / (1024 * 1024 * 1024)  # GB
        disk_percent = disk.percent
        
        # Thông tin về tiến trình hiện tại
        process = psutil.Process(os.getpid())
        process_memory = process.memory_info().rss / (1024 * 1024)  # MB
        process_cpu = process.cpu_percent(interval=0.1)
        process_threads = process.num_threads()
        process_create_time = process.create_time()
        process_running_time = time.time() - process_create_time
        
        return {
            'timestamp': time.time(),
            'cpu': {
                'percent': cpu_percent,
                'count': cpu_count,
                'physical_count': cpu_physical
            },
            'memory': {
                'total_gb': memory_total,
                'available_gb': memory_available,
                'used_gb': memory_used,
                'percent': memory_percent
            },
            'disk': {
                'total_gb': disk_total,
                'free_gb': disk_free,
                'used_gb': disk_used,
                'percent': disk_percent
            },
            'process': {
                'memory_mb': process_memory,
                'cpu_percent': process_cpu,
                'threads': process_threads,
                'running_time_sec': process_running_time
            }
        }
    except Exception as error:
        logger.log_error(f"Lỗi khi lấy thông tin hệ thống: {str(error)}")
        return {}

def monitor_performance(interval: float = 10.0, callback: Optional[Callable] = None):
    """
    Giám sát hiệu năng hệ thống trong một luồng riêng biệt.
    
    Args:
        interval: Khoảng thời gian giữa các lần kiểm tra (giây)
        callback: Hàm callback để xử lý thông tin hiệu năng
    """
    stop_event = threading.Event()
    
    def monitor_thread():
        while not stop_event.is_set():
            try:
                # Lấy thông tin hệ thống
                info = get_system_info()
                
                # Ghi log thông tin
                logger.log_debug(f"CPU: {info['cpu']['percent']}%, "
                               f"Bộ nhớ: {info['memory']['percent']}%, "
                               f"Tiến trình: {info['process']['memory_mb']:.1f}MB")
                
                # Gọi callback nếu có
                if callback is not None:
                    callback(info)
                    
                # Kiểm tra ngưỡng cảnh báo
                if info['memory']['percent'] > 90:
                    logger.log_warning(f"Cảnh báo: Bộ nhớ hệ thống đạt ngưỡng cao ({info['memory']['percent']}%)")
                if info['process']['memory_mb'] > 1024:  # Quá 1GB
                    logger.log_warning(f"Cảnh báo: Tiến trình đang sử dụng nhiều bộ nhớ ({info['process']['memory_mb']:.1f}MB)")
                    
            except Exception as error:
                logger.log_error(f"Lỗi trong luồng giám sát hiệu năng: {str(error)}")
                
            # Chờ đến lần kiểm tra tiếp theo
            stop_event.wait(interval)
    
    # Khởi động luồng giám sát
    monitor_thread = threading.Thread(target=monitor_thread, daemon=True)
    monitor_thread.start()
    
    # Trả về hàm để dừng giám sát
    def stop_monitoring():
        stop_event.set()
        monitor_thread.join(timeout=interval+1)
        
    return stop_monitoring

# ------------------------ Tối ưu hóa numpy/scipy ------------------------
def optimize_numpy():
    """Tối ưu hóa cấu hình NumPy/SciPy."""
    try:
        import numpy as np
        
        # Kiểm tra và cấu hình OpenMP
        threads = DEFAULT_NUM_THREADS
        
        # Thiết lập số luồng cho OpenMP (cho NumPy/SciPy)
        os.environ["OMP_NUM_THREADS"] = str(threads)
        os.environ["OPENBLAS_NUM_THREADS"] = str(threads)
        os.environ["MKL_NUM_THREADS"] = str(threads)
        os.environ["VECLIB_MAXIMUM_THREADS"] = str(threads)
        os.environ["NUMEXPR_NUM_THREADS"] = str(threads)
        
        logger.log_info(f"Đã tối ưu hóa NumPy/SciPy với {threads} luồng")
        
        # Kiểm tra xem NumPy có sử dụng các thư viện tối ưu không
        np_config = np.__config__
        info = str(np_config).lower()
        
        if "mkl" in info or "openblas" in info or "blas" in info:
            logger.log_info("NumPy được xây dựng với thư viện BLAS tối ưu hóa")
        else:
            logger.log_warning("NumPy có thể không được tối ưu hoá - không tìm thấy BLAS")
            
        return True
    except Exception as error:
        logger.log_error(f"Lỗi khi tối ưu hóa NumPy: {str(error)}")
        return False

# ------------------------ Quản lý dữ liệu lớn ------------------------
def create_memory_mapped_array(shape: Tuple[int, ...], dtype: np.dtype = np.float32, 
                              filename: Optional[str] = None, mode: str = 'w+') -> np.ndarray:
    """
    Tạo mảng memory-mapped để xử lý dữ liệu lớn.
    
    Args:
        shape: Kích thước mảng
        dtype: Kiểu dữ liệu
        filename: Tên file để lưu dữ liệu (None để tạo file tạm)
        mode: Chế độ mở file ('r' chỉ đọc, 'w+' đọc/ghi, 'c' copy-on-write)
        
    Returns:
        Mảng numpy memory-mapped
    """
    try:
        import tempfile
        
        # Tạo file tạm nếu không có tên file
        if filename is None:
            # Tạo thư mục tạm nếu cần
            temp_dir = os.path.join(tempfile.gettempdir(), "quangstation")
            os.makedirs(temp_dir, exist_ok=True)
            
            # Tạo file tạm
            fd, filename = tempfile.mkstemp(suffix='.dat', prefix='array_', dir=temp_dir)
            os.close(fd)
            
            # Đăng ký hàm dọn dẹp khi thoát
            import atexit
            atexit.register(lambda: os.unlink(filename) if os.path.exists(filename) else None)
        
        # Tạo mảng memory-mapped
        mm_array = np.memmap(filename, dtype=dtype, mode=mode, shape=shape)
        
        logger.log_info(f"Đã tạo mảng memory-mapped kích thước {shape}, "
                      f"kiểu {dtype}, file: {filename}")
        
        return mm_array
    except Exception as error:
        logger.log_error(f"Lỗi khi tạo mảng memory-mapped: {str(error)}")
        # Trả về mảng thông thường nếu có lỗi
        return np.zeros(shape, dtype=dtype)

# Cải thiện hàm parallel_process_3d_array để đảm bảo an toàn bộ nhớ
def parallel_process_3d_array(func: Callable, array: np.ndarray, axis: int = 0, 
                             num_threads: int = None, use_processes: bool = False,
                             *args, **kwargs) -> np.ndarray:
    """
    Xử lý song song một mảng 3D theo một trục cụ thể.
    
    Args:
        func: Hàm xử lý một lát cắt 2D
        array: Mảng 3D cần xử lý
        axis: Trục để chia lát cắt (0, 1 hoặc 2)
        num_threads: Số lượng luồng/tiến trình (mặc định: tự động)
        use_processes: True để sử dụng tiến trình (chỉ hỗ trợ trên Windows)
        *args, **kwargs: Các tham số khác của hàm xử lý
        
    Returns:
        Mảng 3D đã xử lý
    """
    try:
        import multiprocessing
        
        # Kiểm tra và đảm bảo các tham số hợp lệ
        if axis not in [0, 1, 2]:
            raise ValueError("Trục phải là 0, 1 hoặc 2")
        if num_threads is None:
            num_threads = multiprocessing.cpu_count()
        if use_processes and not os.name == 'nt':
            raise ValueError("Sử dụng tiến trình chỉ hỗ trợ trên Windows")
        
        # Tạo hàm xử lý cho mỗi lát cắt
        def process_slice(slice_index):
            slice_array = array[slice_index]
            return func(slice_array, *args, **kwargs)
        
        # Tạo các luồng/tiến trình
        with multiprocessing.Pool(num_threads) as pool:
            results = pool.map(process_slice, range(array.shape[axis]))
        
        # Ghép các lát cắt lại thành mảng 3D
        result_array = np.zeros(array.shape, dtype=results[0].dtype)
        for slice_index, result in enumerate(results):
            result_array[slice_index] = result
        
        return result_array
    except Exception as error:
        logger.log_error(f"Lỗi khi xử lý song song mảng 3D: {str(error)}")
        return array
        
    except Exception as error:
        logger.log_error(f"Lỗi khi xử lý song song mảng 3D: {str(error)}")
        return array 