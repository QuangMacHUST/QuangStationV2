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

## 📂 Cấu trúc Dự án Mới

QuangStation V2 đã được tái cấu trúc thành một dự án có tổ chức theo nguyên tắc phân chia trách nhiệm rõ ràng. Dưới đây là chi tiết về cấu trúc thư mục mới:

```
QuangStationV2/
├── quangstation/              # Package chính
│   ├── core/                  # Module cốt lõi
│   │   ├── data_models/       # Các mô hình dữ liệu 
│   │   ├── io/                # Đọc/ghi dữ liệu
│   │   └── utils/             # Công cụ tiện ích
│   │
│   ├── clinical/              # Module lâm sàng
│   │   ├── data_management/   # Quản lý dữ liệu bệnh nhân, kế hoạch
│   │   ├── contouring/        # Phân đoạn và contour
│   │   ├── planning/          # Lập kế hoạch điều trị
│   │   │   └── techniques/    # Các kỹ thuật điều trị
│   │   ├── dose_calculation/  # Tính toán liều lượng
│   │   ├── optimization/      # Tối ưu hóa kế hoạch
│   │   └── plan_evaluation/   # Đánh giá kế hoạch
│   │
│   ├── gui/                   # Giao diện người dùng
│   │   ├── widgets/           # Các widget tùy chỉnh
│   │   ├── views/             # Các màn hình chính
│   │   └── dialogs/           # Hộp thoại
│   │
│   ├── quality/               # Đảm bảo chất lượng & báo cáo
│   │   ├── quality_assurance/ # Kiểm tra chất lượng
│   │   └── reporting/         # Tạo báo cáo
│   │
│   ├── services/              # Dịch vụ hỗ trợ
│   │   ├── image_processing/  # Xử lý hình ảnh
│   │   └── integration/       # Tích hợp hệ thống
│   │
│   ├── __init__.py            # Khởi tạo package
│   └── __main__.py            # Điểm vào chính
│
├── resources/                 # Tài nguyên ứng dụng
│   ├── icons/                 # Biểu tượng giao diện
│   ├── templates/             # Mẫu báo cáo
│   ├── models/                # Mô hình AI đã huấn luyện
│   └── data/                  # Dữ liệu tham chiếu
│
├── docs/                      # Tài liệu
│   ├── user_manual/           # Hướng dẫn người dùng
│   ├── developer_guide/       # Hướng dẫn phát triển
│   └── api/                   # Tài liệu API
│
├── tests/                     # Kiểm thử
├── scripts/                   # Script hỗ trợ
├── launcher.py                # Script khởi chạy ứng dụng
├── setup.py                   # Script cài đặt
└── requirements.txt           # Phụ thuộc
```

### Mô tả Chi tiết các Module

#### 1. core/ - Module Cốt lõi
- **data_models/**: Định nghĩa các cấu trúc dữ liệu cơ bản
  - `image_data.py`: Mô hình dữ liệu hình ảnh y tế (CT, MRI, PET)
  - `structure_data.py`: Mô hình dữ liệu cấu trúc giải phẫu
  - `plan_data.py`: Mô hình dữ liệu kế hoạch xạ trị
  - `dose_data.py`: Mô hình dữ liệu liều xạ trị
  - `patient_data.py`: Mô hình dữ liệu bệnh nhân
  - `beam_data.py`: Mô hình dữ liệu chùm tia

- **io/**: Xử lý nhập/xuất dữ liệu
  - `dicom_parser.py`: Phân tích dữ liệu DICOM
  - `dicom_import.py`: Nhập dữ liệu từ DICOM
  - `dicom_export.py`: Xuất dữ liệu sang DICOM
  - `dicom_export_rt.py`: Xuất dữ liệu xạ trị sang DICOM RT
  - `dicom_constants.py`: Các hằng số DICOM
  - `file_utils.py`: Tiện ích xử lý file

- **utils/**: Các công cụ tiện ích
  - `logging.py`: Hệ thống ghi log
  - `config.py`: Quản lý cấu hình
  - `external_integration.py`: Tích hợp thư viện bên ngoài
  - `geometry.py`: Các hàm hình học không gian
  - `data_validation.py`: Kiểm tra tính hợp lệ của dữ liệu
  - `performance.py`: Đo lường và tối ưu hiệu suất

#### 2. clinical/ - Module Lâm sàng
- **data_management/**: Quản lý dữ liệu lâm sàng
  - `patient_db.py`: Cơ sở dữ liệu bệnh nhân
  - `session_management.py`: Quản lý phiên làm việc
  - `plan_manager.py`: Quản lý kế hoạch xạ trị
  - `import_interface.py`: Giao diện nhập dữ liệu

- **contouring/**: Công cụ phân đoạn và vẽ contour
  - `contour_tools.py`: Công cụ vẽ contour
  - `auto_segmentation.py`: Phân đoạn tự động với AI
  - `organ_library.py`: Thư viện cơ quan giải phẫu

- **planning/**: Lập kế hoạch điều trị
  - `plan_config.py`: Cấu hình kế hoạch
  - `beam_management.py`: Quản lý chùm tia
  - `mlc_manager.py`: Quản lý MLC (Multi-Leaf Collimator)
  - `bolus_manager.py`: Quản lý bolus
  - `techniques/`: Thư mục chứa các kỹ thuật xạ trị
    - `base.py`: Lớp cơ sở cho các kỹ thuật
    - `conventional.py`: 3D-CRT
    - `imrt.py`: IMRT (Intensity Modulated Radiation Therapy)
    - `vmat.py`: VMAT (Volumetric Modulated Arc Therapy)
    - `stereotactic.py`: SRS/SBRT (Stereotactic)
    - `proton_therapy.py`: Proton Therapy
    - `adaptive_rt.py`: Adaptive Radiation Therapy
    - `fif.py`: Field-in-Field technique

- **dose_calculation/**: Tính toán liều lượng
  - `dose_engine_wrapper.py`: Wrapper cho các thuật toán tính liều
  - `advanced_algorithms.py`: Các thuật toán tính liều nâng cao
  - `monte_carlo.py`: Thuật toán Monte Carlo
  - `dose_engine.cpp`: Module C++ tính liều hiệu suất cao

- **optimization/**: Tối ưu hóa kế hoạch
  - `goal_optimizer.py`: Tối ưu hóa dựa trên mục tiêu
  - `plan_optimizer.py`: Tối ưu hóa kế hoạch
  - `optimizer_wrapper.py`: Wrapper cho các thuật toán tối ưu
  - `kbp_optimizer.py`: Tối ưu hóa dựa trên kiến thức (KBP)
  - `optimizer.cpp`: Module C++ tối ưu hóa hiệu suất cao

- **plan_evaluation/**: Đánh giá kế hoạch
  - `dvh.py`: Tính toán Dose Volume Histogram
  - `plan_metrics.py`: Các chỉ số đánh giá kế hoạch
  - `biological_effects.py`: Mô hình hiệu ứng sinh học
  - `biological_metrics.py`: Chỉ số đánh giá sinh học
  - `plan_comparison.py`: So sánh kế hoạch
  - `plan_qa.py`: QA (Quality Assurance) kế hoạch

#### 3. gui/ - Giao diện người dùng
- **widgets/**: Các widget tùy chỉnh
  - `mpr_viewer.py`: Viewer hình ảnh đa mặt phẳng
  - `dvh_viewer.py`: Viewer Dose Volume Histogram
  - `viewer_3d.py`: Viewer 3D

- **views/**: Các màn hình chính
  - `main_view.py`: Màn hình chính
  - `patient_view.py`: Màn hình quản lý bệnh nhân
  - `plan_view.py`: Màn hình lập kế hoạch
  - `contour_view.py`: Màn hình contour
  - `dose_view.py`: Màn hình hiển thị liều
  - `evaluation_view.py`: Màn hình đánh giá kế hoạch

- **dialogs/**: Hộp thoại
  - `import_dialog.py`: Hộp thoại nhập dữ liệu
  - `export_dialog.py`: Hộp thoại xuất dữ liệu
  - `kbp_trainer_dialog.py`: Hộp thoại huấn luyện KBP
  - `goal_optimizer_dialog.py`: Hộp thoại tối ưu mục tiêu

- `splash_screen.py`: Màn hình chào đón
- `struct_panel.py`: Panel quản lý cấu trúc
- `mlc_animation.py`: Hiển thị chuyển động MLC
- `main_window.py`: Cửa sổ chính ứng dụng
- `patient_manager.py`: Quản lý bệnh nhân
- `plan_design.py`: Thiết kế kế hoạch (cần tách thành các file nhỏ hơn)

#### 4. quality/ - Đảm bảo chất lượng & báo cáo
- **quality_assurance/**: Kiểm tra chất lượng
  - `qa_tools.py`: Công cụ QA
  - `advanced_qa.py`: Công cụ QA nâng cao

- **reporting/**: Tạo báo cáo
  - `report_gen.py`: Tạo báo cáo cơ bản
  - `pdf_report.py`: Tạo báo cáo PDF
  - `qa_report.py`: Báo cáo QA
  - `comprehensive_report.py`: Báo cáo toàn diện
  - `enhanced_report.py`: Báo cáo nâng cao

#### 5. services/ - Dịch vụ hỗ trợ
- **image_processing/**: Xử lý hình ảnh
  - `image_loader.py`: Đọc và xử lý hình ảnh
  - `segmentation.py`: Thuật toán phân đoạn hình ảnh

- **integration/**: Tích hợp hệ thống
  - `integration.py`: Tích hợp với các hệ thống bên ngoài

## 🔄 Hướng dẫn Triển khai Cấu trúc Mới

Để triển khai cấu trúc thư mục mới, bạn cần thực hiện các bước sau:

### 1. Tạo cấu trúc thư mục mới

```bash
# Tạo thư mục chính
mkdir -p quangstation/{core,clinical,gui,quality,services}

# Tạo các thư mục con trong core
mkdir -p quangstation/core/{data_models,io,utils}

# Tạo các thư mục con trong clinical
mkdir -p quangstation/clinical/{data_management,contouring,planning/techniques,dose_calculation,optimization,plan_evaluation}

# Tạo các thư mục con trong gui
mkdir -p quangstation/gui/{widgets,views,dialogs}

# Tạo các thư mục con trong quality
mkdir -p quangstation/quality/{quality_assurance,reporting}

# Tạo các thư mục con trong services
mkdir -p quangstation/services/{image_processing,integration}
```

### 2. Di chuyển các file vào thư mục mới

Ví dụ di chuyển các file mô hình dữ liệu:

```bash
# Di chuyển các file data_models
cp quangstation/data_models/*.py quangstation/core/data_models/

# Di chuyển các file io
cp quangstation/io/*.py quangstation/core/io/

# Di chuyển các file utils
cp quangstation/utils/*.py quangstation/core/utils/

# Tương tự cho các module khác...
```

### 3. Cập nhật các import trong mỗi file

Sau khi di chuyển các file, bạn cần cập nhật tất cả các import trong các file để phản ánh cấu trúc thư mục mới. Ví dụ:

- Thay đổi từ `from quangstation.data_models import image_data` thành `from quangstation.core.data_models import image_data`
- Thay đổi từ `from quangstation.io import dicom_parser` thành `from quangstation.core.io import dicom_parser`
- v.v.

Thao tác này có thể thực hiện thủ công hoặc sử dụng script để tự động thay thế.

### 4. Cập nhật file setup.py

Cập nhật file setup.py để phản ánh cấu trúc thư mục mới:

```python
from setuptools import setup, find_packages

setup(
    name="quangstation",
    version="2.0.0",
    packages=find_packages(),
    # ...
)
```

### 5. Kiểm tra và sửa lỗi

Sau khi triển khai cấu trúc mới, chạy các kiểm tra để đảm bảo mọi thứ hoạt động bình thường:

```bash
# Kiểm tra cài đặt
pip install -e .

# Chạy ứng dụng
python launcher.py
```

## 🛠️ Tái cấu trúc Mã Nguồn

Một số file trong dự án hiện tại có kích thước rất lớn và nên được tách thành các file nhỏ hơn:

### File plan_design.py (4636 dòng)
File này nên được tách thành nhiều file nhỏ hơn, mỗi file đại diện cho một chức năng cụ thể:
- `gui/views/plan_design_view.py`: Cấu trúc chính của màn hình
- `gui/views/beam_setup_view.py`: Thiết lập chùm tia
- `gui/views/dose_view.py`: Hiển thị liều
- `gui/views/structure_view.py`: Quản lý cấu trúc
- `gui/views/optimization_view.py`: Giao diện tối ưu hóa

### File __main__.py (2992 dòng)
File này nên được tách thành các module khác nhau theo chức năng:
- `core/app.py`: Khởi tạo ứng dụng
- `core/session.py`: Quản lý phiên làm việc
- `gui/main_application.py`: Điểm vào giao diện
- `services/app_service.py`: Dịch vụ ứng dụng

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

