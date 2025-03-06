# QuangStation V2: Hệ thống Lập kế hoạch Xạ trị Mã nguồn Mở

## 🏥 Giới thiệu
QuangStation V2 là một hệ thống lập kế hoạch xạ trị mã nguồn mở tiên tiến, được phát triển bởi Mạc Đăng Quang. Phần mềm được thiết kế để hỗ trợ các chuyên gia y tế trong quá trình lập kế hoạch điều trị ung thư chính xác và hiệu quả.

## ✨ Tính năng Chính
- 📋 Quản lý toàn diện dữ liệu DICOM
  - Hỗ trợ CT, MRI, RT Structure, RT Dose, RT Plan, RT Image
- 🖼️ Hiển thị hình ảnh 2D/3D tiên tiến
- 🔍 Công cụ vẽ và chỉnh sửa Contour chuyên nghiệp
- 📊 Tính toán và tối ưu hóa liều xạ trị
- 📈 Đánh giá kế hoạch qua Biểu đồ Liều-Thể tích (DVH)
- 📝 Tạo báo cáo điều trị chi tiết
- 🔒 Quản lý phiên làm việc an toàn

## 🖥️ Yêu cầu Hệ thống
- **Python**: 3.8 trở lên
- **Hệ điều hành**: Windows 10+, macOS, Linux
- **Phần cứng**: 
  - RAM: 8GB trở lên
  - Không gian đĩa: 10GB trống
  - Khuyến nghị: GPU hỗ trợ CUDA

## 🚀 Cài đặt Nhanh

### Cài đặt từ PyPI
```bash
pip install quangstation
```

### Cài đặt từ Mã nguồn
```bash
# Clone repository
git clone https://github.com/quangmac/QuangStationV2.git
cd QuangStationV2

# Cài đặt các phụ thuộc
pip install -r requirements.txt

# Khởi chạy ứng dụng
python main.py
```

## 🔧 Cấu hình

QuangStation V2 cung cấp cấu hình linh hoạt thông qua file `config.json`:
- Tùy chỉnh đường dẫn làm việc
- Cài đặt ghi log
- Cấu hình thuật toán tính liều
- Tùy chọn giao diện người dùng

## 📘 Hướng dẫn Sử dụng

### Nhập dữ liệu DICOM
1. Chọn "Nhập DICOM" từ menu
2. Chọn thư mục chứa dữ liệu
3. Lựa chọn loại dữ liệu
4. Xác nhận và nhập

### Lập kế hoạch Xạ trị
1. Chọn bệnh nhân
2. Tạo kế hoạch mới
3. Vẽ contour
4. Thiết lập chùm tia
5. Tính toán liều
6. Tối ưu hóa kế hoạch
7. Đánh giá DVH
8. Xuất báo cáo

## 📂 Cấu trúc Dự án
- `data_management/`: Quản lý dữ liệu
- `image_processing/`: Xử lý hình ảnh
- `contouring/`: Công cụ contour
- `planning/`: Lập kế hoạch
- `dose_calculation/`: Tính toán liều
- `optimization/`: Tối ưu hóa
- `plan_evaluation/`: Đánh giá kế hoạch
- `reporting/`: Tạo báo cáo
- `gui/`: Giao diện người dùng
- `utils/`: Công cụ hỗ trợ

## 🤝 Đóng góp
Chúng tôi rất hoan nghênh các đóng góp! Vui lòng xem [CONTRIBUTING.md](CONTRIBUTING.md)

## 📞 Liên hệ
- **Tác giả**: Mạc Đăng Quang
- **Email**: quangmacdang@gmail.com
- **Điện thoại**: 0974478238

## 📄 Giấy phép
Dự án được phân phối dưới Giấy phép MIT. Xem [LICENSE](LICENSE) để biết chi tiết.

## 🚧 Trạng thái Dự án
- **Phiên bản**: 2.0.0-beta
- **Tiến độ**: 40%
- **Dự kiến phát hành chính thức**: Quý 2/2024

## 🌟 Hỗ trợ
Nếu bạn thấy dự án hữu ích, hãy cho chúng tôi một sao ⭐ trên GitHub!

