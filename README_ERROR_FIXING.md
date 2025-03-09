# Công cụ sửa lỗi tự động cho QuangStation V2

Thư mục này chứa các công cụ để tự động sửa lỗi và kiểm tra mã nguồn trong dự án QuangStation V2.

## Các công cụ có sẵn

### 1. Script sửa lỗi tự động (`fix_errors.py`)

Script này tự động quét và sửa các lỗi phổ biến trong mã nguồn Python của dự án QuangStation V2.

**Các lỗi được sửa:**

- **Biến không được định nghĩa trong khối except**: Thay thế `except Exception as e:` bằng `except Exception as error:` và cập nhật các tham chiếu đến biến `e` trong khối except.
- **Thuộc tính không tồn tại**: Thay thế truy cập trực tiếp đến các thuộc tính như `self.image_metadata`, `self.structure_colors`, và `self.beams` bằng `getattr(self, "attribute_name", {})` để tránh lỗi AttributeError.
- **Lỗi import**: Thêm các import thiếu như `import datetime` khi cần thiết.

**Cách sử dụng:**

```bash
python fix_errors.py [thư_mục]
```

Nếu không chỉ định thư mục, script sẽ mặc định sửa lỗi trong thư mục `quangstation`.

### 2. Script kiểm tra lỗi (`verify_fixes.py`)

Script này kiểm tra xem các lỗi đã được sửa chữa đúng cách chưa.

**Các kiểm tra được thực hiện:**

- Tìm kiếm các khối `except Exception as e:` còn sót lại.
- Tìm kiếm các truy cập trực tiếp đến các thuộc tính có thể gây lỗi như `self.image_metadata`, `self.structure_colors`, và `self.beams`.

**Cách sử dụng:**

```bash
python verify_fixes.py [thư_mục]
```

Nếu không chỉ định thư mục, script sẽ mặc định kiểm tra thư mục `quangstation`.

Script sẽ tạo một tệp log chi tiết với định dạng `verify_results_YYYYMMDD_HHMMSS.log` chứa kết quả kiểm tra cho từng tệp.

### 3. Script tổng hợp (`fix_and_verify.py`)

Script này chạy cả hai script (sửa lỗi và kiểm tra) cùng một lúc, giúp đơn giản hóa quá trình sửa lỗi.

**Cách sử dụng:**

```bash
python fix_and_verify.py [thư_mục]
```

Nếu không chỉ định thư mục, script sẽ mặc định làm việc với thư mục `quangstation`.

## Quy trình sửa lỗi

1. Chạy script tổng hợp:
   ```bash
   python fix_and_verify.py
   ```

   Hoặc chạy từng script riêng lẻ:

   a. Chạy script sửa lỗi tự động:
   ```bash
   python fix_errors.py
   ```

   b. Kiểm tra xem các lỗi đã được sửa chữa đúng cách chưa:
   ```bash
   python verify_fixes.py
   ```

2. Nếu vẫn còn lỗi, chạy lại script sửa lỗi hoặc sửa thủ công các lỗi còn lại.

## Lưu ý

- Các script này chỉ sửa các lỗi cú pháp và lỗi tiềm ẩn phổ biến. Chúng không thể sửa các lỗi logic hoặc lỗi thiết kế.
- Luôn sao lưu mã nguồn trước khi chạy các script sửa lỗi tự động.
- Kiểm tra kỹ kết quả sau khi sửa lỗi để đảm bảo không có tác dụng phụ không mong muốn.
- Các script đã được thiết kế để hoạt động tốt trên Windows và không sử dụng các ký tự đặc biệt để tránh lỗi mã hóa.

## Tác giả

Các công cụ này được phát triển như một phần của dự án QuangStation V2 - Hệ thống Lập kế hoạch Xạ trị Mã nguồn Mở. 