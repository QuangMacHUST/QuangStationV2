# Hướng dẫn sử dụng tính năng Tối ưu hóa dựa trên Kiến thức (KBP)

## Giới thiệu

Tối ưu hóa dựa trên kiến thức (Knowledge-Based Planning - KBP) là một phương pháp tiên tiến trong lập kế hoạch xạ trị, sử dụng dữ liệu từ các kế hoạch trước đó để dự đoán các ràng buộc tối ưu cho kế hoạch mới. QuangStation V2 đã tích hợp tính năng KBP để giúp các nhà lập kế hoạch tạo ra các kế hoạch xạ trị chất lượng cao một cách nhanh chóng và nhất quán.

## Nguyên lý hoạt động

KBP trong QuangStation V2 hoạt động dựa trên các nguyên lý sau:

1. **Thu thập dữ liệu**: Hệ thống thu thập dữ liệu từ các kế hoạch xạ trị đã được phê duyệt trước đó.
2. **Trích xuất đặc trưng**: Các đặc trưng hình học và liều lượng được trích xuất từ dữ liệu.
3. **Huấn luyện mô hình**: Mô hình học máy được huấn luyện để dự đoán các ràng buộc tối ưu.
4. **Dự đoán**: Khi có một kế hoạch mới, mô hình sẽ dự đoán các ràng buộc tối ưu dựa trên đặc trưng của kế hoạch đó.
5. **Áp dụng**: Các ràng buộc được đề xuất sẽ được áp dụng vào quá trình tối ưu hóa.

## Chuẩn bị dữ liệu

Để sử dụng tính năng KBP hiệu quả, bạn cần chuẩn bị dữ liệu huấn luyện:

1. **Thu thập kế hoạch**: Thu thập ít nhất 50 kế hoạch xạ trị chất lượng cao cho mỗi vị trí điều trị (ví dụ: đầu cổ, phổi, tiền liệt tuyến, v.v.).
2. **Đảm bảo chất lượng**: Các kế hoạch phải được phê duyệt bởi bác sĩ và đáp ứng các tiêu chuẩn lâm sàng.
3. **Chuẩn hóa dữ liệu**: Đảm bảo các cấu trúc được đặt tên nhất quán và tuân theo các quy ước đặt tên.
4. **Nhập dữ liệu**: Nhập các kế hoạch vào hệ thống QuangStation V2.

## Huấn luyện mô hình KBP

### Bước 1: Truy cập công cụ huấn luyện KBP

1. Mở QuangStation V2.
2. Chọn "Công cụ" > "Huấn luyện KBP" từ menu chính.

### Bước 2: Chọn dữ liệu huấn luyện

1. Chọn vị trí điều trị (ví dụ: đầu cổ, phổi, tiền liệt tuyến).
2. Chọn các kế hoạch sẽ được sử dụng để huấn luyện.
3. Xác định các cơ quan nguy cấp (OAR) cần được dự đoán.

### Bước 3: Cấu hình tham số huấn luyện

1. Chọn các đặc trưng sẽ được sử dụng (mặc định: thể tích, khoảng cách đến PTV, chồng lấp với PTV).
2. Chọn các chỉ số liều cần dự đoán (ví dụ: Dmean, D1cc, D2%, v.v.).
3. Cấu hình tham số mô hình (số cây quyết định, độ sâu tối đa, v.v.).

### Bước 4: Huấn luyện và đánh giá

1. Nhấn "Huấn luyện" để bắt đầu quá trình huấn luyện.
2. Xem kết quả đánh giá (MAE, RMSE, R²) để đánh giá chất lượng mô hình.
3. Lưu mô hình nếu kết quả đánh giá đạt yêu cầu.

## Sử dụng KBP trong lập kế hoạch

### Bước 1: Tạo kế hoạch mới

1. Tạo một kế hoạch xạ trị mới hoặc mở kế hoạch hiện có.
2. Đảm bảo đã có các cấu trúc cần thiết (PTV, OARs).

### Bước 2: Sử dụng KBP

1. Trong cửa sổ thiết kế kế hoạch, nhấn nút "KBP Optimize" trên thanh công cụ.
2. Chọn các cơ quan cần tối ưu hóa.
3. Cấu hình các tùy chọn:
   - Tự động áp dụng các ràng buộc đề xuất
   - Hiển thị chi tiết các ràng buộc đề xuất
4. Nhấn "Tối ưu hóa" để bắt đầu quá trình.

### Bước 3: Xem và điều chỉnh kết quả

1. Xem danh sách các ràng buộc được đề xuất.
2. Điều chỉnh các ràng buộc nếu cần thiết.
3. Nhấn "Áp dụng" để áp dụng các ràng buộc vào quá trình tối ưu hóa.

### Bước 4: Tối ưu hóa kế hoạch

1. Sau khi áp dụng các ràng buộc KBP, nhấn "Tối ưu hóa" để bắt đầu quá trình tối ưu hóa kế hoạch.
2. Đánh giá kết quả tối ưu hóa và điều chỉnh nếu cần thiết.

## Mẹo và thủ thuật

1. **Chuẩn hóa đặt tên cấu trúc**: Đảm bảo các cấu trúc được đặt tên nhất quán để KBP có thể nhận dạng chính xác.
2. **Kiểm tra chất lượng dữ liệu**: Loại bỏ các kế hoạch có chất lượng kém khỏi dữ liệu huấn luyện.
3. **Huấn luyện theo vị trí điều trị**: Tạo các mô hình riêng cho từng vị trí điều trị để cải thiện độ chính xác.
4. **Cập nhật mô hình định kỳ**: Huấn luyện lại mô hình khi có thêm dữ liệu mới để cải thiện hiệu suất.
5. **Kết hợp với MCO**: Kết hợp KBP với tối ưu hóa đa tiêu chí (MCO) để có kết quả tốt nhất.

## Xử lý sự cố

### Vấn đề: Không tìm thấy mô hình phù hợp

**Giải pháp**: 
- Kiểm tra xem đã huấn luyện mô hình cho vị trí điều trị cụ thể chưa.
- Đảm bảo các cấu trúc được đặt tên đúng quy ước.
- Sử dụng tùy chọn "Tìm mô hình tương tự" trong cài đặt KBP.

### Vấn đề: Các ràng buộc đề xuất không hợp lý

**Giải pháp**:
- Kiểm tra chất lượng dữ liệu huấn luyện.
- Điều chỉnh thủ công các ràng buộc trước khi áp dụng.
- Huấn luyện lại mô hình với dữ liệu chất lượng cao hơn.

### Vấn đề: Quá trình tối ưu hóa không hội tụ

**Giải pháp**:
- Kiểm tra xem các ràng buộc có mâu thuẫn không.
- Điều chỉnh trọng số của các ràng buộc.
- Thử sử dụng thuật toán tối ưu hóa khác.

## Tài liệu tham khảo

1. Anchineyan, P., Amalraj, J., Krishnan, B. T., Ananthalakshmi, M. C., Jayaraman, P., & Krishnasamy, R. (2022). Assessment of Knowledge-Based Planning Model in Combination with Multi-Criteria Optimization in Head-and-Neck Cancers. Journal of Medical Physics, 47(2), 119-125. [PubMed](https://pubmed.ncbi.nlm.nih.gov/36212210/)

2. Müller, B. S., Shih, H. A., Efstathiou, J. A., Bortfeld, T., & Craft, D. (2017). Multicriteria plan optimization in the hands of physicians: A pilot study in prostate cancer and brain tumors. Radiation Oncology, 12, 168.

3. Voet, P. W., Dirkx, M. L., Breedveld, S., Fransen, D., Levendag, P. C., & Heijmen, B. J. (2013). Toward fully automated multicriterial plan generation: A prospective clinical study. International Journal of Radiation Oncology, Biology, Physics, 85, 866-872.

4. McNutt, T., Wu, B., Moore, J., Petit, S., Kazhdan, M., & Taylor, R. (2012). Automated Treatment Planning Using a Database of Prior Patient Treatment Plans. Medical Physics, 39, 4008.

5. Craft, D. L., Hong, T. S., Shih, H. A., & Bortfeld, T. R. (2012). Improved planning time and plan quality through multicriteria optimization for intensity-modulated radiotherapy. International Journal of Radiation Oncology, Biology, Physics, 82, e83-90. 