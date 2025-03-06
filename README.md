# QuangStation V2

## Giới thiệu
QuangStation V2 là một hệ thống lập kế hoạch xạ trị mã nguồn mở được phát triển bởi Mạc Đăng Quang. Phần mềm này được thiết kế để hỗ trợ các nhà vật lý y tế, bác sĩ xạ trị và kỹ thuật viên trong quá trình lập kế hoạch điều trị xạ trị cho bệnh nhân ung thư.

## Tính năng chính
- Nhập và quản lý dữ liệu DICOM (CT, MRI, RT Structure, RT Dose, RT Plan, RT Image)
- Hiển thị 2D/3D cho dữ liệu hình ảnh và cấu trúc
- Vẽ và chỉnh sửa contour cho cơ quan nguy cấp (OAR) và thể tích mục tiêu (PTV)
- Thiết lập và tối ưu hóa kế hoạch xạ trị
- Tính toán liều xạ trị với nhiều thuật toán (Collapsed Cone Convolution, Pencil Beam)
- Đánh giá kế hoạch điều trị thông qua DVH (Dose Volume Histogram)
- Quản lý phiên làm việc và xuất dữ liệu
- Tạo báo cáo điều trị chi tiết

## Cài đặt
### Yêu cầu hệ thống
- Python 3.8 trở lên
- Các gói thư viện cần thiết được liệt kê trong file `requirements.txt`

### Hướng dẫn cài đặt
1. Clone repository từ GitHub:
```
git clone https://github.com/quangmac/QuangStationV2.git
```

2. Cài đặt các thư viện phụ thuộc:
```
pip install -r requirements.txt
```

3. Khởi chạy ứng dụng:
```
python main.py
```

## Hướng dẫn sử dụng

### Nhập dữ liệu DICOM
1. Chọn "Nhập DICOM" từ menu
2. Chọn thư mục chứa dữ liệu DICOM
3. Lựa chọn loại dữ liệu cần nhập (CT, MRI, RT Structure, v.v.)
4. Xác nhận thông tin bệnh nhân và tiến hành nhập

### Lập kế hoạch điều trị
1. Chọn bệnh nhân từ danh sách
2. Tạo kế hoạch mới hoặc chỉnh sửa kế hoạch hiện có
3. Vẽ contour cho cơ quan nguy cấp và thể tích mục tiêu
4. Thiết lập thông số chùm tia
5. Tính toán liều xạ trị
6. Tối ưu hóa kế hoạch để đạt được phân bố liều tối ưu
7. Xem và đánh giá DVH
8. Xuất kế hoạch điều trị

## Cấu trúc dự án
- `data_management/`: Quản lý dữ liệu bệnh nhân và DICOM
- `image_processing/`: Xử lý và hiển thị hình ảnh
- `contouring/`: Công cụ vẽ và chỉnh sửa contour
- `planning/`: Thiết lập kế hoạch xạ trị
- `dose_calculation/`: Các thuật toán tính toán liều xạ trị
- `optimization/`: Tối ưu hóa kế hoạch điều trị
- `plan_evaluation/`: Đánh giá kế hoạch điều trị
- `reporting/`: Tạo báo cáo điều trị
- `gui/`: Giao diện người dùng
- `utils/`: Công cụ hỗ trợ

## Đóng góp
Dự án này đang trong quá trình phát triển và cần sự đóng góp từ cộng đồng. Nếu bạn muốn đóng góp, vui lòng tạo pull request hoặc liên hệ trực tiếp với tác giả.

## Liên hệ
- **Tác giả**: Mạc Đăng Quang
- **Email**: quanmacdangg@gmail.com
- **Điện thoại**: 0974478238

## Giấy phép
QuangStation V2 được phân phối dưới giấy phép mã nguồn mở MIT License. Xem file LICENSE để biết thêm chi tiết.

## Trạng thái dự án
- Tiến trình hiện tại: 30%
- Dự kiến hoàn thành bản beta: Quý 4/2023

