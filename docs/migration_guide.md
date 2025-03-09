# Hướng dẫn chuyển đổi mã nguồn QuangStation V2

## Tổng quan

Chúng tôi đã thực hiện tái cấu trúc các module xạ trị trong QuangStation V2 để cải thiện khả năng bảo trì và mở rộng. Tài liệu này sẽ hướng dẫn bạn cách cập nhật mã nguồn hiện có để sử dụng cấu trúc mới.

## Thay đổi lớn

1. Module `rt_techniques.py` đã được chia thành nhiều file nhỏ hơn và di chuyển vào thư mục mới `techniques`
2. Các lớp kỹ thuật xạ trị (RTTechnique, Conventional3DCRT, IMRT, ...) đã được di chuyển vào các file riêng biệt
3. Thêm hàm tiện ích `create_technique()` để dễ dàng khởi tạo các đối tượng kỹ thuật xạ trị

## Hướng dẫn chuyển đổi mã nguồn

### 1. Thay đổi các phát biểu import

#### Trước đây:

```python
from quangstation.planning.rt_techniques import RTTechnique, Conventional3DCRT, IMRT
```

#### Bây giờ:

```python
# Cách 1: Import từ module kế hoạch (Khuyến nghị)
from quangstation.planning import RTTechnique, Conventional3DCRT, IMRT

# Cách 2: Import trực tiếp từ package techniques
from quangstation.planning.techniques import RTTechnique, Conventional3DCRT, IMRT
```

> **Lưu ý quan trọng**: Module `rt_techniques.py` đã bị loại bỏ hoàn toàn. Tất cả các import phải được cập nhật theo một trong hai cách trên.

### 2. Sử dụng hàm tiện ích create_technique

#### Trước đây:

```python
technique = Conventional3DCRT()
technique.beam_energy = 10.0
technique.set_beam_angles([0, 90, 180, 270])
```

#### Bây giờ:

```python
# Cách 1: Tạo đối tượng với các tham số mặc định và cấu hình sau
from quangstation.planning import create_technique
technique = create_technique("3DCRT")
technique.beam_energy = 10.0
technique.set_beam_angles([0, 90, 180, 270])

# Cách 2: Tạo đối tượng với các tham số đã được cấu hình sẵn
technique = create_technique("3DCRT", beam_energy=10.0, beam_angles=[0, 90, 180, 270])
```

### 3. Sử dụng logging mới

#### Trước đây:

```python
from quangstation.utils.logging import get_logger
logger = get_logger(__name__)
logger.log_info("Thông báo")
logger.log_error("Lỗi xảy ra")
```

#### Bây giờ:

```python
from quangstation.utils.logging import get_logger
logger = get_logger(__name__)
logger.info("Thông báo")
logger.error("Lỗi xảy ra")
```

## Các lớp đã được tái cấu trúc

Module `rt_techniques.py` đã được chia thành các file sau:

- `techniques/base.py`: Chứa lớp cơ sở `RTTechnique`
- `techniques/conventional.py`: Chứa lớp `Conventional3DCRT`
- `techniques/fif.py`: Chứa lớp `FieldInField`
- `techniques/imrt.py`: Chứa lớp `IMRT`
- `techniques/vmat.py`: Chứa lớp `VMAT`

Trong tương lai, các lớp bổ sung sẽ được thêm vào thư mục `techniques`.

## Lợi ích của cấu trúc mới

- **Dễ bảo trì**: Mã nguồn được tổ chức thành các module nhỏ hơn, dễ quản lý
- **Dễ mở rộng**: Thêm các kỹ thuật xạ trị mới không làm ảnh hưởng đến mã nguồn hiện có
- **Dễ hiểu**: Mã nguồn được tổ chức theo tính năng, dễ dàng tìm thấy và hiểu
- **Hiệu suất tốt hơn**: Chỉ tải các module thực sự cần thiết
- **Tránh trùng lặp mã nguồn**: Cấu trúc mới loại bỏ các đoạn mã trùng lặp

## Câu hỏi thường gặp

### Làm thế nào để tìm hiểu các tham số có sẵn cho hàm create_technique?

Bạn có thể sử dụng hàm `help()` trong Python:

```python
from quangstation.planning import create_technique
help(create_technique)
```

### Làm thế nào để tìm hiểu các phương thức và thuộc tính của một kỹ thuật xạ trị?

Sử dụng hàm `dir()` hoặc `help()`:

```python
from quangstation.planning import create_technique
technique = create_technique("3DCRT")
help(technique)  # Hiển thị thông tin chi tiết
dir(technique)   # Liệt kê tất cả các thuộc tính và phương thức
```

### Tôi vẫn cần hỗ trợ cách chuyển đổi mã nguồn của mình. Tôi nên làm gì?

Vui lòng liên hệ đội phát triển QuangStation để được hỗ trợ thêm. 