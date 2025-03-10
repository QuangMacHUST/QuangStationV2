# Hướng dẫn sử dụng tính năng Tính toán liều Monte Carlo

## Giới thiệu

Phương pháp Monte Carlo là một trong những phương pháp tính toán liều chính xác nhất trong lập kế hoạch xạ trị. Phương pháp này mô phỏng quá trình lan truyền của các hạt photon trong môi trường vật chất, cho phép tính toán phân bố liều chính xác hơn so với các thuật toán thông thường, đặc biệt trong các trường hợp có sự không đồng nhất về mật độ vật liệu.

QuangStation V2 đã tích hợp tính năng tính toán liều Monte Carlo, giúp các nhà lập kế hoạch có thể tạo ra các kế hoạch xạ trị chính xác hơn, đặc biệt trong các trường hợp phức tạp như ung thư phổi, đầu cổ, hoặc các vùng có cấy ghép kim loại.

## Nguyên lý hoạt động

Phương pháp Monte Carlo trong QuangStation V2 hoạt động dựa trên các nguyên lý sau:

1. **Mô phỏng nguồn bức xạ**: Mô phỏng các hạt photon phát ra từ nguồn bức xạ (máy gia tốc).
2. **Theo dõi hạt**: Theo dõi quá trình di chuyển và tương tác của từng hạt photon trong môi trường vật chất.
3. **Tính toán năng lượng lắng đọng**: Tính toán năng lượng lắng đọng tại mỗi voxel trong cơ thể bệnh nhân.
4. **Tích lũy liều**: Tích lũy liều từ nhiều hạt để tạo ra phân bố liều tổng thể.
5. **Đánh giá độ không đảm bảo**: Tính toán độ không đảm bảo thống kê của kết quả.

## Ưu điểm của phương pháp Monte Carlo

- **Độ chính xác cao**: Mô phỏng chính xác các quá trình vật lý của tương tác bức xạ.
- **Xử lý tốt sự không đồng nhất**: Tính toán chính xác trong các môi trường không đồng nhất như phổi, xương, hoặc cấy ghép kim loại.
- **Mô phỏng chính xác các hiệu ứng biên**: Tính toán chính xác tại các biên giữa các mô có mật độ khác nhau.
- **Độ tin cậy cao**: Cung cấp thông tin về độ không đảm bảo thống kê của kết quả.

## Sử dụng tính năng Monte Carlo

### Bước 1: Tạo kế hoạch xạ trị

1. Tạo một kế hoạch xạ trị mới hoặc mở kế hoạch hiện có.
2. Đảm bảo đã có dữ liệu CT và các cấu trúc cần thiết.
3. Thiết lập các chùm tia và tham số kế hoạch.

### Bước 2: Tính toán liều

1. Trong cửa sổ thiết kế kế hoạch, nhấn nút "Tính liều" trên thanh công cụ.
2. Trong hộp thoại tùy chọn tính liều, chọn thuật toán "Monte Carlo".
3. Cấu hình các tham số Monte Carlo:
   - **Số hạt mỗi lần lặp**: Số lượng hạt photon được mô phỏng trong mỗi lần lặp (mặc định: 100,000).
   - **Độ không đảm bảo mục tiêu**: Độ không đảm bảo thống kê mục tiêu (mặc định: 2%).
   - **Số lần lặp tối đa**: Số lần lặp tối đa để đạt được độ không đảm bảo mục tiêu (mặc định: 10).
4. Cấu hình các tùy chọn chung:
   - **Độ phân giải lưới liều**: Kích thước voxel của lưới liều (mm).
   - **Hiển thị tiến trình**: Hiển thị cửa sổ tiến trình trong quá trình tính toán.
5. Nhấn "Tính toán" để bắt đầu quá trình.

### Bước 3: Theo dõi tiến trình

1. Một cửa sổ tiến trình sẽ hiển thị thông tin về quá trình tính toán.
2. Quá trình tính toán sẽ tiếp tục cho đến khi đạt được độ không đảm bảo mục tiêu hoặc đạt đến số lần lặp tối đa.
3. Sau mỗi lần lặp, độ không đảm bảo hiện tại sẽ được cập nhật.

### Bước 4: Xem kết quả

1. Sau khi tính toán hoàn tất, một thông báo sẽ hiển thị thông tin về kết quả, bao gồm độ không đảm bảo cuối cùng.
2. Phân bố liều sẽ được hiển thị trên các mặt cắt CT.
3. Bạn có thể tiếp tục với các bước tiếp theo như tính DVH, tối ưu hóa, hoặc tạo báo cáo.

## Tùy chỉnh nâng cao

### Cấu hình vật lý

Bạn có thể tùy chỉnh các tham số vật lý của mô phỏng Monte Carlo trong file cấu hình:

1. Mở menu "Công cụ" > "Cài đặt" > "Monte Carlo".
2. Tùy chỉnh các tham số:
   - **Bảng chuyển đổi HU sang mật độ**: Cấu hình bảng chuyển đổi từ giá trị HU sang mật độ electron tương đối.
   - **Hệ số suy giảm tuyến tính**: Cấu hình hệ số suy giảm tuyến tính cho các loại vật liệu.
   - **Tỷ lệ tán xạ Compton**: Cấu hình tỷ lệ tán xạ Compton cho các loại vật liệu.
3. Nhấn "Lưu" để áp dụng các thay đổi.

### Tối ưu hóa hiệu suất

Để tối ưu hóa hiệu suất tính toán Monte Carlo:

1. **Sử dụng mặt nạ tính toán**: Giới hạn vùng tính toán bằng cách sử dụng mặt nạ (chỉ tính trong các vùng quan tâm).
2. **Điều chỉnh số hạt**: Giảm số hạt nếu chỉ cần kết quả sơ bộ, tăng số hạt nếu cần độ chính xác cao.
3. **Sử dụng độ phân giải thích hợp**: Sử dụng độ phân giải thô hơn cho tính toán sơ bộ, độ phân giải mịn hơn cho tính toán cuối cùng.
4. **Tận dụng tính toán song song**: Tăng số luồng tính toán nếu máy tính có nhiều lõi CPU.

## Kiểm định và đảm bảo chất lượng

Để đảm bảo độ chính xác của tính toán Monte Carlo:

1. **So sánh với đo đạc thực tế**: So sánh kết quả tính toán với đo đạc thực tế trên phantom.
2. **Kiểm tra độ hội tụ**: Đảm bảo độ không đảm bảo thống kê đủ thấp (thường < 1% cho các vùng liều cao).
3. **Kiểm tra tính nhất quán**: So sánh kết quả với các thuật toán tính liều khác.
4. **Kiểm tra các trường hợp đặc biệt**: Kiểm tra kỹ lưỡng trong các trường hợp có sự không đồng nhất cao.

## Xử lý sự cố

### Vấn đề: Tính toán quá chậm

**Giải pháp**:
- Giảm số hạt mỗi lần lặp.
- Sử dụng mặt nạ tính toán để giới hạn vùng tính toán.
- Tăng độ không đảm bảo mục tiêu (ví dụ: từ 1% lên 2%).
- Kiểm tra và tăng số luồng tính toán.

### Vấn đề: Độ không đảm bảo không giảm

**Giải pháp**:
- Tăng số hạt mỗi lần lặp.
- Kiểm tra xem có vùng liều thấp chiếm ưu thế không.
- Sử dụng kỹ thuật giảm phương sai (variance reduction).

### Vấn đề: Kết quả không chính xác

**Giải pháp**:
- Kiểm tra dữ liệu đầu vào (CT, cấu trúc, chùm tia).
- Kiểm tra bảng chuyển đổi HU sang mật độ.
- Kiểm tra các tham số vật lý.
- So sánh với thuật toán tính liều khác.

## Tài liệu tham khảo

1. Rogers, D. W. O. (2006). Fifty years of Monte Carlo simulations for medical physics. Physics in Medicine & Biology, 51(13), R287.

2. Chetty, I. J., Curran, B., Cygler, J. E., DeMarco, J. J., Ezzell, G., Faddegon, B. A., ... & Siebers, J. V. (2007). Report of the AAPM Task Group No. 105: Issues associated with clinical implementation of Monte Carlo-based photon and electron external beam treatment planning. Medical physics, 34(12), 4818-4853.

3. Reynaert, N., Van der Marck, S. C., Schaart, D. R., Van der Zee, W., Van Vliet-Vroegindeweij, C., Tomsej, M., ... & Verhaegen, F. (2007). Monte Carlo treatment planning for photon and electron beams. Radiation Physics and Chemistry, 76(4), 643-686.

4. Verhaegen, F., & Seuntjens, J. (2003). Monte Carlo modelling of external radiotherapy photon beams. Physics in Medicine & Biology, 48(21), R107.

5. Ma, C. M., & Jiang, S. B. (1999). Monte Carlo modelling of electron beams from medical accelerators. Physics in Medicine & Biology, 44(12), R157. 