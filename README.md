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
- 🤖 Phân đoạn tự động với AI
- 🔬 Tính toán hiệu quả sinh học (BED, EQD2)
- 🔄 So sánh kế hoạch
- 🎲 Tính toán liều Monte Carlo

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

# Cài đặt trong chế độ phát triển
pip install -e .

# Khởi chạy ứng dụng
python -m quangstation.main
```

## 🔧 Cấu hình

QuangStation V2 cung cấp cấu hình linh hoạt thông qua file `config.json`:
- Tùy chỉnh đường dẫn làm việc
- Cài đặt ghi log
- Cấu hình thuật toán tính liều
- Tùy chọn giao diện người dùng

File cấu hình được tạo tự động trong thư mục `~/.quangstation/config.json` khi khởi động lần đầu.

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

## 💡 Xử lý lỗi
Nếu bạn gặp vấn đề khi sử dụng QuangStation, hãy tham khảo [Hướng dẫn khắc phục sự cố](docs/TROUBLESHOOTING.md) của chúng tôi.

## 📂 Cấu trúc Dự án
```
QuangStationV2/
├── quangstation/              # Package Python chính
│   ├── contouring/            # Công cụ contour
│   ├── data_management/       # Quản lý dữ liệu
│   ├── dose_calculation/      # Tính toán liều
│   ├── gui/                   # Giao diện người dùng
│   ├── image_processing/      # Xử lý hình ảnh
│   ├── optimization/          # Tối ưu hóa
│   ├── plan_evaluation/       # Đánh giá kế hoạch
│   ├── planning/              # Lập kế hoạch
│   ├── quality_assurance/     # Đảm bảo chất lượng
│   ├── reporting/             # Tạo báo cáo
│   └── utils/                 # Công cụ hỗ trợ
├── resources/                 # Tài nguyên ứng dụng
├── docs/                      # Tài liệu
├── tests/                     # Kiểm thử
├── scripts/                   # Script hỗ trợ
├── setup.py                   # Script cài đặt
└── requirements.txt           # Phụ thuộc
```

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
- **Dự kiến phát hành chính thức**: tháng 6/2024

## 🌟 Hỗ trợ
Nếu bạn thấy dự án hữu ích, hãy cho chúng tôi một sao ⭐ trên GitHub!

