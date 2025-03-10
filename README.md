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
python launcher.py
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
├── launcher.py                # Script khởi chạy ứng dụng
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
- **Tiến độ**: 45%
- **Dự kiến phát hành chính thức**: tháng 6/2024

## 🌟 Hỗ trợ
Nếu bạn thấy dự án hữu ích, hãy cho chúng tôi một sao ⭐ trên GitHub!

## �� Cập nhật gần đây
- Triển khai tính năng tối ưu hóa dựa trên kiến thức (KBP - Knowledge-Based Planning)
- Cải tiến tính năng tính toán liều với phương pháp Monte Carlo
- Cải thiện cấu trúc dự án
- Sửa lỗi xóa bệnh nhân
- Thêm xử lý ngoại lệ tốt hơn
- Cải thiện giao diện người dùng
- Tối ưu hóa hiệu suất
- Thêm các dialog mới: PatientDialog, DoseDialog
- Cải thiện quản lý phiên làm việc và kế hoạch
- Sửa lỗi trong lưu/đọc metadata kế hoạch
- Tối ưu hóa hiển thị hình ảnh y tế
- Thêm widget ImageViewer nâng cao

## 📱 Triển khai tiếp theo
- Hoàn thiện tính năng tối ưu hóa kế hoạch
- Cải thiện tính năng tự động phân đoạn với AI
- Phát triển chức năng báo cáo chi tiết
- Hỗ trợ đa ngôn ngữ
- Tích hợp với hệ thống PACS/HIS

## 📊 Dữ liệu chuẩn cần thiết
Để hệ thống hoạt động tối ưu, cần các dữ liệu chuẩn sau:

### 1. Dữ liệu huấn luyện cho KBP
- Bộ dữ liệu kế hoạch xạ trị đã được phê duyệt (tối thiểu 50 kế hoạch cho mỗi vị trí điều trị)
- Dữ liệu DVH của các cơ quan nguy cấp (OAR) và thể tích điều trị (PTV)
- Thông tin về các ràng buộc liều đã sử dụng trong các kế hoạch chất lượng cao

### 2. Dữ liệu vật lý cho tính toán liều
- Dữ liệu đặc tính chùm tia (beam data) cho các máy gia tốc
- Dữ liệu đo đạc phantom cho kiểm định thuật toán
- Dữ liệu hiệu chỉnh không đồng nhất (heterogeneity correction)
- Dữ liệu đo đạc MLC (Multi-Leaf Collimator)

### 3. Dữ liệu CT và cấu trúc
- Bộ dữ liệu CT chuẩn với các cấu trúc đã được vẽ
- Bộ dữ liệu atlas cho phân đoạn tự động
- Dữ liệu chuyển đổi HU sang mật độ electron và thông số vật liệu

### 4. Dữ liệu đánh giá kế hoạch
- Các ràng buộc liều chuẩn theo QUANTEC, RTOG và các hướng dẫn lâm sàng mới nhất
- Dữ liệu tham chiếu cho các chỉ số đánh giá kế hoạch (CI, HI, GI, v.v.)
- Dữ liệu tham chiếu cho các mô hình hiệu quả sinh học (TCP, NTCP)

Các dữ liệu này có thể được thu thập từ:
1. Cơ sở dữ liệu nội bộ của bệnh viện
2. Cơ sở dữ liệu công khai như TCIA (The Cancer Imaging Archive)
3. Dữ liệu từ các thử nghiệm lâm sàng
4. Dữ liệu đo đạc commissioning của máy gia tốc

## 🔬 Kiểm định và đảm bảo chất lượng
Hệ thống cần được kiểm định theo các tiêu chuẩn:
- AAPM TG-53: Đảm bảo chất lượng hệ thống lập kế hoạch xạ trị
- AAPM TG-119: Kiểm định IMRT
- IAEA TRS-430: Commissioning và QA hệ thống lập kế hoạch xạ trị
- MPPG 5.a: Commissioning hệ thống lập kế hoạch xạ trị

