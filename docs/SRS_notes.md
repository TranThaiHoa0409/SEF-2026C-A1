# Những điểm prototype đã chốt, cần phản ánh vào SRS

Gom lại các quyết định trong lúc làm prototype mà Guide hoặc kế hoạch chưa nói rõ. Mỗi dòng nên được thể hiện trong user story, use case, FR hoặc traceability matrix tương ứng.

## Dữ liệu và upload

- `upload_01_valid_orders.csv` trùng y hệt 40 đơn đã có, nên upload được nhận nhưng số liệu không đổi (ngày 5 Nov vẫn 79 đơn, $2,985.05).
- Thêm `upload_08_new_and_changed_orders.csv` (12 đơn mới, 3 đơn đổi sang `refunded`): ngày 5 Nov thành 88 đơn, $3,326.19; kỳ 1 đến 7 Nov thành 430 đơn, $15,982.18.
- `upload_07` có cả 15 dòng ở năm 2027: file được nhận, nạp 0 dòng, báo lý do từng dòng.

## Dashboard (Hòa)

- Danh mục có 13 widget: 8 widget dạng số (mỗi KPI một) và 5 widget biểu đồ (Total Sales, Average Order Value, Total Revenue, New Customers, Active Users).
- Bộ mặc định cho người mới: Total Revenue, Total Sales, New Customers, Active Users (dạng số).
- Có hai thao tác reset riêng: "Reset to default" (về bộ widget mặc định) và "Reset layout" (về thứ tự trong danh mục).

## Analytics (Len)

- Trend chọn được 6 KPI; Revenue Growth và Customer Retention Rate không có trend.
- Last 3 months là 13 tuần trọn: 9 Aug đến 7 Nov.
- So sánh hai kỳ: độ dài 1, 7 hoặc 30 ngày (không có "1 tháng" vì tháng dài 28 đến 31 ngày).
- Kỳ trước 1 Jun không có đơn và phiên app nhưng vẫn có khách đăng ký (`customers.csv`), nên thông báo "kỳ không có dữ liệu" nêu theo từng KPI.
- Drill-down: KPI đơn hàng liệt kê đơn (mọi trạng thái), New Customers liệt kê khách đăng ký, Active Users và Conversion Rate liệt kê phiên app.

## Báo cáo và thông báo (Phu)

- Rule cảnh báo xét giá trị KPI của ngày đầy đủ gần nhất (7 Nov), không phải kỳ trên dashboard. Đây là cách duy nhất khớp với tình huống R01 (alert ngày 3 và 7 Nov).
- Email lỗi: lần gửi đầu + 3 lần thử lại, cách nhau 1 phút (tổng 4 lần), theo Guide. Kế hoạch ghi "3 lần thử" nên cần sửa cho thống nhất.
- Báo cáo chỉ có 4 kỳ cố định; Custom range chưa làm, nên tình huống báo cáo 20 đến 22 Sep chưa chọn được.
- Danh sách thông báo trong app gồm cảnh báo, chia sẻ báo cáo và báo cáo định kỳ (endpoint `/api/notifications`).
- Báo cáo định kỳ: hằng ngày, hằng tuần, hằng tháng, kèm giờ chạy lần đầu; KPI không có dữ liệu được bỏ qua tự động vì không có ai bấm xác nhận.

## Nhóm, ghi chú, Admin (Yuki)

- Admin đổi Group Owner được chọn cả người ngoài nhóm; người đó được thêm vào nhóm. Group Owner thường chỉ chuyển quyền cho thành viên.
- Activity log ghi thêm: tạo, đổi tên, xóa nhóm, đổi Group Owner, deactivate tài khoản, xóa ghi chú của người khác.
- Chỉ có Deactivate, không có kích hoạt lại tài khoản.
- Ghi chú tối đa 1,000 ký tự.

## Bảo mật

- Thiếu quyền luôn trả cùng thông báo "No access" (403), kể cả khi mục không tồn tại, để không lộ mục nào có thật.
- API không cho trình duyệt lưu đệm (`Cache-Control: no-store`).
