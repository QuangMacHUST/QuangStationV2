# QuangStation V2: Hệ thống Lập kế hoạch Xạ trị Mã nguồn Mở

## 🏥 Giới thiệu
QuangStation V2 là một hệ thống lập kế hoạch xạ trị mã nguồn mở tiên tiến, được phát triển bởi Mạc Đăng Quang. Phần mềm được thiết kế để hỗ trợ các chuyên gia y tế trong quá trình lập kế hoạch điều trị ung thư chính xác và hiệu quả, kết hợp các công nghệ tiên tiến và thuật toán vật lý phức tạp.

## ✨ Tính năng Chính
### 📋 Quản lý Dữ liệu
- **Quản lý toàn diện dữ liệu DICOM**
  - Hỗ trợ đầy đủ CT, MRI, RT Structure, RT Dose, RT Plan, RT Image
  - Nhập/xuất DICOM theo chuẩn DICOM RT
  - Sao lưu và phục hồi dữ liệu
- **Quản lý bệnh nhân và kế hoạch**
  - Lưu trữ và quản lý thông tin bệnh nhân
  - Quản lý nhiều kế hoạch xạ trị cho một bệnh nhân
  - Hệ thống phiên làm việc an toàn với khôi phục tự động

### 🖼️ Hiển thị và Xử lý Hình ảnh
- **Hiển thị hình ảnh 2D/3D tiên tiến**
  - Hiển thị đa mặt phẳng (MPR) với Axial, Sagittal, Coronal
  - Rendering 3D với khả năng xoay, phóng to/thu nhỏ
  - Điều chỉnh độ tương phản, độ sáng và các bộ lọc hình ảnh
- **Công cụ điều khiển hình ảnh**
  - Đo khoảng cách, góc và diện tích trên hình ảnh
  - Hiển thị giá trị HU tại điểm quan tâm
  - Chức năng thay đổi độ trong suốt và màu sắc hiển thị

### 🔍 Phân đoạn và Contour
- **Công cụ vẽ và chỉnh sửa Contour chuyên nghiệp**
  - Vẽ contour thủ công với nhiều công cụ vẽ khác nhau
  - Chỉnh sửa contour với các công cụ push/pull, smooth, interpolate
  - Tạo cấu trúc từ phép toán boolean (union, intersection, subtraction)
  - Tạo margin tự động (expansion, contraction)
- **Phân đoạn tự động với AI**
  - Phân đoạn tự động các cơ quan nguy cấp (OAR) sử dụng mạng U-Net
  - Hỗ trợ tải và sử dụng nhiều mô hình đã huấn luyện
  - Tự động điều chỉnh và tinh chỉnh kết quả phân đoạn

### 📊 Tính toán và Mô phỏng Liều
- **Đa dạng thuật toán tính toán liều xạ trị**
  - Collapsed Cone Convolution (CCC)
  - Pencil Beam
  - Analytical Anisotropic Algorithm (AAA)
  - Acuros XB
  - Convolution Superposition
  - Monte Carlo
- **Mô hình vật lý nâng cao**
  - Tính toán TERMA (Total Energy Released per unit MAss)
  - Mô hình hóa đầy đủ tương tác chùm tia-vật chất
  - Hiệu chỉnh không đồng nhất (heterogeneity correction)
  - Mô phỏng các hiệu ứng tán xạ và hấp thụ

### 🎛️ Kỹ thuật Xạ trị Tiên tiến
- **Hỗ trợ nhiều kỹ thuật xạ trị**
  - 3D-CRT (Conformal Radiation Therapy)
  - IMRT (Intensity Modulated Radiation Therapy)
  - VMAT (Volumetric Modulated Arc Therapy)
  - SRS/SBRT (Stereotactic Radiosurgery/Stereotactic Body Radiation Therapy)
  - Proton Therapy
  - Adaptive Radiation Therapy
- **Quản lý MLC (Multi-Leaf Collimator)**
  - Hiển thị và điều chỉnh MLC trong Beam's Eye View (BEV)
  - Tự động điều chỉnh lá MLC dựa trên hình dạng cấu trúc
  - Mô phỏng chuyển động của MLC trong kỹ thuật VMAT

### 🧩 Tối ưu hóa Kế hoạch
- **Tối ưu hóa liều xạ trị**
  - Tối ưu hóa dựa trên ràng buộc (Constraint-based optimization)
  - Tối ưu hóa dựa trên mục tiêu (Objective-based optimization)
  - Tối ưu hóa MCO (Multi-Criteria Optimization)
  - Tự động điều chỉnh trọng số tối ưu
- **Tối ưu hóa dựa trên kiến thức (KBP - Knowledge-Based Planning)**
  - Dự đoán DVH tối ưu dựa trên dữ liệu lịch sử
  - Tối ưu hóa tự động dựa trên kế hoạch tương tự
  - Tạo mục tiêu tối ưu dựa trên dữ liệu học máy

### 📈 Đánh giá Kế hoạch
- **Đánh giá kế hoạch qua Biểu đồ Liều-Thể tích (DVH)**
  - Hiển thị DVH tương tác với nhiều tùy chọn hiển thị
  - Phân tích thống kê DVH với các chỉ số Dmin, Dmax, Dmean, Vx, Dx
  - Xuất dữ liệu DVH sang nhiều định dạng
- **Chỉ số đánh giá kế hoạch**
  - Chỉ số đồng dạng (Conformity Index - CI)
  - Chỉ số đồng nhất (Homogeneity Index - HI)
  - Chỉ số gradient (Gradient Index - GI)
  - Phân tích liều điểm nóng (Hotspot Analysis)
- **Tính toán hiệu quả sinh học**
  - Tính BED (Biologically Effective Dose)
  - Tính EQD2 (Equivalent Dose in 2Gy fractions)
  - Mô hình TCP (Tumor Control Probability)
  - Mô hình NTCP (Normal Tissue Complication Probability)

### 📑 Báo cáo và Xuất dữ liệu
- **Tạo báo cáo điều trị chi tiết**
  - Báo cáo kế hoạch điều trị với hình ảnh và đồ thị
  - Báo cáo QA (Quality Assurance)
  - Báo cáo so sánh kế hoạch
  - Báo cáo theo dõi điều trị
- **Xuất dữ liệu đa dạng**
  - Xuất DICOM RT theo chuẩn
  - Xuất báo cáo dạng PDF, DOCX
  - Xuất dữ liệu phân tích dạng CSV, Excel
  - Xuất hình ảnh và đồ thị dạng PNG, JPEG, SVG

### 🔄 Tính năng Nâng cao
- **So sánh kế hoạch**
  - So sánh trực quan nhiều kế hoạch xạ trị
  - Phân tích sự khác biệt giữa các kế hoạch
  - Đánh giá kết quả trước và sau tối ưu
- **Đảm bảo chất lượng (Quality Assurance)**
  - Tính toán Gamma Index
  - Phân tích sự khác biệt giữa liều tính toán và đo đạc
  - Kiểm tra tính nhất quán của kế hoạch
- **Giao diện người dùng thân thiện**
  - Thiết kế hiện đại với hỗ trợ giao diện sáng/tối
  - Thanh công cụ tùy chỉnh với biểu tượng trực quan
  - Hệ thống thông báo và trợ giúp tích hợp

## 🖥️ Yêu cầu Hệ thống
- **Python**: 3.8 trở lên
- **Hệ điều hành**: Windows 10+, macOS, Linux
- **Phần cứng**: 
  - CPU: 4 nhân trở lên
  - RAM: 8GB trở lên (khuyến nghị 16GB cho dữ liệu lớn)
  - Không gian đĩa: 10GB trống
  - Khuyến nghị: GPU hỗ trợ CUDA (cho tính toán Monte Carlo và AI)

## 🚀 Cài đặt Nhanh

### Cài đặt từ PyPI
```bash
pip install quangstation
```

### Cài đặt từ Mã nguồn
```bash
# Clone repository
git clone https://github.com/QuangMacHust/QuangStationV2.git
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
- **Cài đặt chung**:
  - Tùy chỉnh đường dẫn làm việc
  - Cài đặt ngôn ngữ và múi giờ
  - Thiết lập đơn vị đo lường
- **Cài đặt hệ thống**:
  - Cấu hình ghi log và mức độ chi tiết
  - Quản lý bộ nhớ cache và tạm thời
  - Thiết lập số luồng xử lý cho tính toán
- **Cài đặt thuật toán**:
  - Cấu hình thuật toán tính liều mặc định
  - Thiết lập độ phân giải tính toán
  - Cấu hình mô hình vật lý và tham số
- **Giao diện người dùng**:
  - Tùy chọn giao diện sáng/tối
  - Cấu hình bố cục và kích thước cửa sổ
  - Tùy chỉnh phím tắt và thanh công cụ

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
3. Vẽ contour hoặc sử dụng phân đoạn tự động
4. Thiết lập chùm tia và kỹ thuật xạ trị
5. Tính toán liều ban đầu
6. Tối ưu hóa kế hoạch
7. Đánh giá kế hoạch qua DVH và các chỉ số
8. Tinh chỉnh nếu cần
9. Duyệt và xuất báo cáo

## 💡 Xử lý lỗi
Nếu bạn gặp vấn đề khi sử dụng QuangStation, hãy tham khảo [Hướng dẫn khắc phục sự cố](docs/TROUBLESHOOTING.md) của chúng tôi. Hệ thống còn được trang bị tính năng tự chẩn đoán và gợi ý sửa lỗi thông minh.

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
│   ├── icons/                 # Biểu tượng giao diện
│   ├── templates/             # Mẫu báo cáo
│   ├── models/                # Mô hình AI đã huấn luyện
│   └── data/                  # Dữ liệu tham chiếu
├── docs/                      # Tài liệu
│   ├── user_manual/           # Hướng dẫn người dùng
│   ├── developer_guide/       # Hướng dẫn phát triển
│   └── api/                   # Tài liệu API
├── tests/                     # Kiểm thử
├── scripts/                   # Script hỗ trợ
├── launcher.py                # Script khởi chạy ứng dụng
├── setup.py                   # Script cài đặt
└── requirements.txt           # Phụ thuộc
```

## 🤝 Đóng góp
Chúng tôi rất hoan nghênh các đóng góp! Vui lòng xem [CONTRIBUTING.md](CONTRIBUTING.md) để biết thêm thông tin về cách tham gia phát triển dự án.

## 📞 Liên hệ
- **Tác giả**: Mạc Đăng Quang
- **Email**: quangmacdang@gmail.com
- **Điện thoại**: 0974478238
- **Website**: [quangstation.com](https://quangstation.com)

## 📄 Giấy phép
Dự án được phân phối dưới Giấy phép MIT. Xem [LICENSE](LICENSE) để biết chi tiết.

## 🚧 Trạng thái Dự án
- **Phiên bản**: 2.0.0-beta
- **Tiến độ**: 65%
- **Dự kiến phát hành chính thức**: tháng 6/2024

## 🌟 Hỗ trợ
Nếu bạn thấy dự án hữu ích, hãy cho chúng tôi một sao ⭐ trên GitHub!

## 🔄 Cập nhật gần đây
- Triển khai tính toán TERMA (Total Energy Released per unit MAss) trong thuật toán Convolution Superposition
- Cải tiến tiền xử lý hình ảnh cho phân đoạn tự động với AI
- Triển khai phương thức tạo kế hoạch cơ bản cho các kỹ thuật xạ trị
- Cải thiện tính toán liều với thuật toán nâng cao
- Hỗ trợ mô-đun C++ cho tính toán liều nhanh
- Hoàn thiện giao diện người dùng với xử lý sự kiện đầy đủ
- Thêm tính năng hiển thị MLC trong Beam's Eye View
- Triển khai tính năng hiển thị mục tiêu (target) trong BEV
- Thêm biểu tượng và cải thiện trải nghiệm người dùng
- Tối ưu hóa dựa trên kiến thức (KBP) với mô hình học máy
- Cải tiến tính toán Monte Carlo cho độ chính xác cao
- Thêm tính năng báo cáo chi tiết với thông tin bệnh nhân và kế hoạch
- Triển khai và cải thiện công cụ đánh giá kế hoạch

## 📱 Triển khai tiếp theo
- Cải thiện giao diện người dùng với thiết kế đáp ứng
- Tích hợp hệ thống đám mây để lưu trữ và tính toán từ xa
- Phát triển phiên bản web cho truy cập từ mọi nơi
- Hỗ trợ đa ngôn ngữ toàn diện
- Tích hợp sâu hơn với hệ thống PACS/HIS
- Mở rộng hỗ trợ cho các kỹ thuật xạ trị mới nhất

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

