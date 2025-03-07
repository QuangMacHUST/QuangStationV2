# Hướng dẫn khắc phục sự cố cho QuangStation V2

## Lỗi import module
Nếu bạn gặp lỗi import như `ModuleNotFoundError: No module named 'quangstation'`, hãy thử các cách sau:

### Giải pháp 1: Cài đặt package
```bash
# Cài đặt ở chế độ development
pip install -e .
```

### Giải pháp 2: Thêm thư mục gốc vào PYTHONPATH
```python
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
```

## Lỗi tkinter
Nếu bạn gặp lỗi liên quan đến tkinter, hãy đảm bảo bạn đã cài đặt gói python-tk:

### Ubuntu/Debian
```bash
sudo apt-get install python3-tk
```

### CentOS/RHEL
```bash
sudo yum install python3-tkinter
```

### Windows
Tkinter thường được cài đặt sẵn với Python trên Windows. Nếu không, hãy cài đặt lại Python và chọn tùy chọn "tcl/tk and IDLE".

## Lỗi PyTorch
Nếu bạn gặp lỗi khi sử dụng các tính năng liên quan đến AI (như contour tự động), có thể là do không có PyTorch:

```bash
# Cài đặt PyTorch
pip install torch torchvision
```

Lưu ý: PyTorch không bắt buộc để vận hành QuangStation. Các tính năng AI sẽ tự động vô hiệu hóa nếu không tìm thấy PyTorch.

## Lỗi về DICOM
Nếu bạn gặp lỗi khi đọc file DICOM:

1. Hãy đảm bảo bạn đã cài đặt pydicom:
```bash
pip install pydicom
```

2. Kiểm tra xem file DICOM có bị hỏng không
3. Kiểm tra xem file có phải là định dạng DICOM chuẩn không

## Lỗi database
Nếu bạn gặp lỗi liên quan đến cơ sở dữ liệu:

1. Kiểm tra quyền ghi file trong thư mục làm việc
2. Xóa file database và để hệ thống tạo lại
3. Kiểm tra cấu hình trong `~/.quangstation/config.json`

## Lỗi hiển thị 3D
Nếu bạn gặp lỗi khi hiển thị 3D:

1. Đảm bảo VTK đã được cài đặt đúng:
```bash
pip install vtk
```

2. Kiểm tra driver card đồ họa
3. Giảm độ phân giải hiển thị 3D trong phần cấu hình

## Lỗi trong dose_engine.cpp
Nếu bạn gặp lỗi liên quan đến tính toán liều lượng trong file C++:

1. Lỗi "expression must have pointer-to-object type":
   - Đây là lỗi khi truy cập phần tử trong mảng 3D
   - Đảm bảo rằng bạn đang truy cập đúng kiểu dữ liệu
   - Sử dụng phương pháp truy cập an toàn với kiểm tra kích thước

2. Lỗi biên dịch C++:
   - Đảm bảo bạn có trình biên dịch C++ phù hợp (GCC 7+ hoặc MSVC 2019+)
   - Cài đặt các thư viện phát triển cần thiết:
     ```bash
     # Ubuntu/Debian
     sudo apt-get install build-essential
     
     # Windows
     # Cài đặt Visual Studio với C++ workload
     ```

3. Lỗi khi gọi hàm C++ từ Python:
   - Kiểm tra xem module pybind11 đã được cài đặt chưa
   - Đảm bảo rằng thư viện động (.so/.dll) đã được biên dịch đúng cách
   - Kiểm tra đường dẫn tới thư viện động trong biến môi trường (PATH/LD_LIBRARY_PATH)

## Lỗi OpenCV
Nếu bạn gặp lỗi liên quan đến OpenCV như "Module 'cv2' has no member":

1. Cài đặt lại OpenCV:
```bash
pip uninstall opencv-python
pip install opencv-python
```

2. Nếu vẫn gặp lỗi với linter, thêm comment `# type: ignore` sau dòng import:
```python
import cv2  # type: ignore
```

## Lỗi ReportLab
Nếu bạn gặp lỗi khi tạo báo cáo PDF:

1. Cài đặt ReportLab:
```bash
pip install reportlab
```

2. Nếu gặp lỗi về font, hãy đảm bảo các font cần thiết đã được cài đặt trong hệ thống
3. Nếu gặp lỗi về quyền truy cập file, kiểm tra quyền ghi trong thư mục đầu ra

## Lỗi Monte Carlo
Nếu bạn gặp lỗi khi sử dụng thuật toán Monte Carlo:

1. Lỗi "numpy.random has no member RandomState":
   - Cập nhật cách sử dụng numpy.random theo phiên bản mới nhất:
   ```python
   # Thay vì
   rng = numpy.random.RandomState(seed)
   
   # Sử dụng
   rng = numpy.random.default_rng(seed)
   ```

2. Lỗi hiệu suất:
   - Tăng số luồng trong cấu hình Monte Carlo
   - Giảm số hạt nếu bộ nhớ bị giới hạn
   - Sử dụng GPU nếu có thể (yêu cầu CUDA và CuPy)

## Lỗi khi cài đặt từ nguồn
Nếu bạn gặp lỗi khi cài đặt QuangStation từ mã nguồn:

1. Đảm bảo bạn có đủ các công cụ phát triển:
```bash
# Ubuntu/Debian
sudo apt-get install python3-dev

# Windows
# Cài đặt Visual C++ Build Tools
```

2. Cài đặt các phụ thuộc trước:
```bash
pip install -r requirements.txt
```

3. Sử dụng môi trường ảo:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

## Sử dụng script khởi động nhanh
Để tránh nhiều vấn đề cài đặt, bạn có thể sử dụng script khởi động nhanh:

```bash
python -m quangstation.utils.quick_start --gui
```

Script này sẽ:
- Kiểm tra và cài đặt các thư viện phụ thuộc
- Tạo cấu hình mặc định
- Thiết lập thư mục làm việc
- Tạo dữ liệu mẫu (tùy chọn)
- Khởi chạy ứng dụng

## Liên hệ hỗ trợ
Nếu bạn vẫn gặp vấn đề, hãy liên hệ:
- Email: quangmacdang@gmail.com
- Điện thoại: 0974478238 
- GitHub: Tạo issue tại [repository chính thức](https://github.com/quangmacdang/QuangStationV2) 