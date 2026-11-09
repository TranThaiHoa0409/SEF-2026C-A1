# BizBoard prototype

Prototype web app cho Assignment 1 (SEF). Mục đích: kiểm chứng yêu cầu và lấy ảnh minh họa cho SRS, không phải sản phẩm thật.

## Đọc trước khi làm
1. `BizBoard_prototype_plan.md`: kế hoạch, kiến trúc, database, API, 6 bước, bảng kiểm thử.
2. `BizBoard_Group_Work_Guide.md`: nguồn nghiệp vụ chi tiết và 14 NFR. Nếu hai file lệch nhau, Guide đúng.
3. `data/README.md`: cách tính KPI, tình huống dữ liệu cài sẵn, ví dụ tính tay.

## Công nghệ
- Python 3.11+, FastAPI + Uvicorn, SQLite (`sqlite3`), APScheduler, ReportLab, pytest.
- Giao diện: HTML + JavaScript thuần, Chart.js, SortableJS. Không dùng Node.
- Mobile first, chạy được từ màn hình 360px, nút bấm tối thiểu 44x44px.
- Chạy trên Windows.

## Quy tắc không được phá
- Mọi KPI nằm trong một module duy nhất (`app/kpi.py`). Dashboard, analytics, báo cáo, cảnh báo đều gọi module này.
- Tên 8 KPI giữ đúng: Total Sales, Average Order Value, Total Revenue, Revenue Growth, New Customers, Customer Retention Rate, Active Users, Conversion Rate.
- Chỉ đơn `status = 'completed'` được tính vào KPI. Đơn `cancelled`, `refunded` vẫn hiện trong drill-down (có cột `status`).
- Total Sales đếm số đơn, không đếm số món.
- "Hôm nay" cố định là 2026-11-08 (hằng số cấu hình), để "Last 7 days" = 1 đến 7 Nov.
- Hai kỳ so sánh luôn cùng độ dài, không trùng nhau. Không so sánh Retention hoặc Conversion giữa hai kỳ khác độ dài.
- Khi không có dữ liệu: trả `None` và hiện thông báo no-data nêu rõ kỳ và bộ lọc. Không để màn hình trống, không coi là lỗi.
- Một bộ lọc một lúc. Danh sách lọc: `region`, `city`, `product_category`, `product_name`, `sales_channel`, `device`, `payment_method`. Bộ lọc không áp dụng được cho KPI thì báo rõ, không trả số sai.

## Quyết định đã chốt về upload
- Chỉ System Administrator được upload. Admin có trang riêng xem lịch sử các lần upload (tên file, giờ, số dòng nạp, số dòng bị bỏ). Chỉ xem, không xóa hay hoàn tác.
- File thiếu cột hoặc chỉ có dòng tiêu đề (`upload_02`, `upload_05`): từ chối cả file.
- File có dòng lỗi (`upload_03`, `upload_06`) và ngày ở tương lai (`upload_07`): bỏ dòng lỗi, nạp phần còn lại, báo rõ dòng nào bị bỏ.
- `order_id` lặp trong cùng một file (`upload_04`): giữ dòng cuối.
- Ghi đè theo `order_id`: đơn trùng trong DB được thay bằng bản trong file, đơn mới được thêm, các đơn khác giữ nguyên.
- Upload hợp lệ làm dữ liệu refresh ngay.

## Quy tắc khác đã chốt
- Dữ liệu refresh mỗi 5 phút. Alert chỉ tạo khi KPI vừa cắt ngưỡng, không tạo lại khi vẫn đang vượt. Email giả (bảng `mailbox`) trong 1 phút, lỗi thì thử lại 3 lần cách nhau 1 phút.
- Xóa nhóm thì báo cáo và snapshot đã chia sẻ cho nhóm đó mất quyền xem, không bị xóa.
- Snapshot chỉ xem, không có ghi chú. Ghi chú chỉ có ở báo cáo.
- Phiên đăng nhập hết sau 30 phút không hoạt động. Đăng nhập bằng cách chọn tài khoản mẫu từ `users.csv`.
- Thiếu quyền thì luôn trả thông báo "no access" (403), dùng một hàm kiểm tra quyền chung.

## Thứ tự làm (mỗi bước chạy được và có test trước khi sang bước sau)
1. Nền tảng và dữ liệu: nạp CSV, module KPI, đăng nhập mẫu, tác vụ nền, upload.
2. Dashboard: danh mục widget, lưu lựa chọn, bố cục kéo thả, kỳ, snapshot.
3. Analytics: trend, so sánh hai kỳ, bộ lọc, drill-down.
4. Báo cáo PDF và thông báo: báo cáo, lịch, chia sẻ, rule cảnh báo, email giả.
5. Nhóm, ghi chú, trang Admin.
6. Hoàn thiện: rà NFR, bộ test tự động, ảnh màn hình.

## Kiểm thử
- Viết test pytest đối chiếu với các con số trong `data/README.md` và bảng ở mục 7 của file kế hoạch (ví dụ 1 đến 7 Nov: 421 đơn, $15,641.04, 112 khách mới, 1,240 Active Users, 29.4% Conversion Rate).
- `kpi_daily_answer_key.csv` chỉ dùng trong test, không phải nguồn dữ liệu của app.

## Ngoài phạm vi (không làm)
Kết nối dữ liệu live qua API, phát hiện bất thường bằng AI, market intelligence, app mobile native, gửi email thật, push notification, nhiều điều kiện trong một rule, nhiều bộ lọc cùng lúc, lời mời vào nhóm cần chấp nhận. Custom range chỉ làm nếu còn thời gian.

## Cách làm việc
- Sửa file trực tiếp để mình xem diff, không dán toàn bộ file vào chat.
- Nếu yêu cầu mơ hồ hoặc hiểu được theo nhiều cách, hỏi lại trước khi làm, không tự đoán.
- Không thêm tính năng ngoài Guide. Khi đổi yêu cầu, nói rõ để sửa cả SRS.