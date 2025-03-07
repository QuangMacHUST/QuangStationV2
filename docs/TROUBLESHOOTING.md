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

## Liên hệ hỗ trợ
Nếu bạn vẫn gặp vấn đề, hãy liên hệ:
- Email: quangmacdang@gmail.com
- Điện thoại: 0974478238 