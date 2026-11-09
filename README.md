# Tôi tự học

Trang đọc "Tôi tự học" (Thu Giang Nguyễn Duy Cần, Khai Trí, 1971) trên điện thoại, kèm bản PDF đã dàn trang lại cho hết lỗi font.

## Đọc sách

Bản chính chạy trên Vercel (project `toi-tu-hoc`), có khoá Vercel Authentication cho mọi địa chỉ: phải đăng nhập tài khoản Vercel của chủ repo mới đọc được. Mỗi lần push lên nhánh `main`, Vercel tự deploy thư mục `site/` theo `vercel.json`.

Khi đọc:

- Vuốt ngang ở giữa màn hình để sang chương sau hoặc chương trước. Trên máy tính dùng phím mũi tên trái/phải.
- Mỗi chương nhớ chỗ đang đọc. Đọc tới cuối chương thì mục lục ghi "đã đọc", dòng "Đọc tiếp" chỉ sang chương chưa đọc kế tiếp. Tất cả lưu trong `localStorage` của trình duyệt.
- Các chương đã mở (và chương kế tiếp) được lưu lại bằng service worker, mất mạng vẫn đọc được. Phần này chỉ chạy trên HTTPS hoặc localhost.

Chạy thử trên máy tính:

```
python -m http.server 8000 -d site
```

rồi mở http://localhost:8000.

Trên điện thoại (điện thoại và máy tính cùng một mạng Wi-Fi):

```
python -m http.server 8000 -d site --bind 0.0.0.0
```

rồi mở `http://<IP của máy tính>:8000` trên điện thoại. Xem IP bằng lệnh `ipconfig` (dòng IPv4 Address).

Bản PDF: `Tôi Tự Học (bản sửa font).pdf`, khổ A5, có mục lục bấm được ở thanh bên của trình đọc PDF.

## Bản gốc bị lỗi gì

File PDF gốc được xuất từ Word, trộn font Times New Roman nhúng sẵn với font không nhúng. Máy nào không có đúng font đó thì chữ có dấu bị tách ra ("nh ững", "đ ể"). Bản này lấy lại chữ từ lớp văn bản của PDF và dàn trang lại bằng font Literata nhúng đầy đủ.

Ngoài ra đã sửa 38 lỗi gõ có sẵn trong bản ebook, phần lớn là chữ bị chèn khoảng trắng ("sác h", "kh ông"). Danh sách nằm trong `tools/fixes.json`.

## Dựng lại từ PDF gốc

```
pip install pymupdf
python tools/extract.py "<đường dẫn tới PDF gốc>"
python tools/build.py
python tools/print_pdf.py
```

- `extract.py` đọc PDF, ghép lại dòng và đoạn, tách chương, chú thích, áp `fixes.json`, ghi ra `data/book.json`.
- `build.py` sinh trang web vào `site/` và bản in vào `print/sach.html`.
- `print_pdf.py` dùng Chrome hoặc Edge để in `print/sach.html` ra PDF.

## Bản quyền

Sách vẫn còn trong thời hạn bảo hộ (tác giả mất năm 1998). Repo này để riêng tư, chỉ dùng để đọc cá nhân. Đừng chuyển repo sang công khai, và giữ Deployment Protection của project Vercel ở chế độ "All Deployments".
