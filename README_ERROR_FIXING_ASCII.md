# Cong cu sua loi tu dong cho QuangStation V2

Thu muc nay chua cac cong cu de tu dong sua loi va kiem tra ma nguon trong du an QuangStation V2.

## Cac cong cu co san

### 1. Script sua loi tu dong (`fix_errors.py`)

Script nay tu dong quet va sua cac loi pho bien trong ma nguon Python cua du an QuangStation V2.

**Cac loi duoc sua:**

- **Bien khong duoc dinh nghia trong khoi except**: Thay the `except Exception as e:` bang `except Exception as error:` va cap nhat cac tham chieu den bien `e` trong khoi except.
- **Thuoc tinh khong ton tai**: Thay the truy cap truc tiep den cac thuoc tinh nhu `self.image_metadata`, `self.structure_colors`, va `self.beams` bang `getattr(self, "attribute_name", {})` de tranh loi AttributeError.
- **Loi import**: Them cac import thieu nhu `import datetime` khi can thiet.

**Cach su dung:**

```bash
python fix_errors.py [thu_muc]
```

Neu khong chi dinh thu muc, script se mac dinh sua loi trong thu muc `quangstation`.

### 2. Script kiem tra loi (`verify_fixes.py`)

Script nay kiem tra xem cac loi da duoc sua chua dung cach chua.

**Cac kiem tra duoc thuc hien:**

- Tim kiem cac khoi `except Exception as e:` con sot lai.
- Tim kiem cac truy cap truc tiep den cac thuoc tinh co the gay loi nhu `self.image_metadata`, `self.structure_colors`, va `self.beams`.

**Cach su dung:**

```bash
python verify_fixes.py [thu_muc]
```

Neu khong chi dinh thu muc, script se mac dinh kiem tra thu muc `quangstation`.

Script se tao mot tep log chi tiet voi dinh dang `verify_results_YYYYMMDD_HHMMSS.log` chua ket qua kiem tra cho tung tep.

### 3. Script tong hop (`fix_and_verify.py`)

Script nay chay ca hai script (sua loi va kiem tra) cung mot luc, giup don gian hoa qua trinh sua loi.

**Cach su dung:**

```bash
python fix_and_verify.py [thu_muc]
```

Neu khong chi dinh thu muc, script se mac dinh lam viec voi thu muc `quangstation`.

## Quy trinh sua loi

1. Chay script tong hop:
   ```bash
   python fix_and_verify.py
   ```

   Hoac chay tung script rieng le:

   a. Chay script sua loi tu dong:
   ```bash
   python fix_errors.py
   ```

   b. Kiem tra xem cac loi da duoc sua chua dung cach chua:
   ```bash
   python verify_fixes.py
   ```

2. Neu van con loi, chay lai script sua loi hoac sua thu cong cac loi con lai.

## Luu y

- Cac script nay chi sua cac loi cu phap va loi tiem an pho bien. Chung khong the sua cac loi logic hoac loi thiet ke.
- Luon sao luu ma nguon truoc khi chay cac script sua loi tu dong.
- Kiem tra ky ket qua sau khi sua loi de dam bao khong co tac dung phu khong mong muon.
- Cac script da duoc thiet ke de hoat dong tot tren Windows va khong su dung cac ky tu dac biet de tranh loi ma hoa.

## Tac gia

Cac cong cu nay duoc phat trien nhu mot phan cua du an QuangStation V2 - He thong Lap ke hoach Xa tri Ma nguon Mo. 