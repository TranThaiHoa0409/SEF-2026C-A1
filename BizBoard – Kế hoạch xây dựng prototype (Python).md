# BizBoard – Kế hoạch xây dựng prototype (Python)

Nov 9, 2026 · @Trần Thái Hòa

## 1. Mục tiêu và phạm vi

Mục tiêu là dựng một prototype BizBoard bằng Python và SQLite chạy trên máy cá nhân, đủ 6 nhóm chức năng trong Group Work Guide, dùng dữ liệu mẫu GreenLeaf Coffee (160 ngày, 12,876 đơn). Prototype dùng để kiểm chứng yêu cầu và lấy ảnh minh họa cho SRS, không phải sản phẩm triển khai thật.

**Làm:**

- Responsive web, thiết kế mobile first, chạy được từ màn hình 360px.
- 8 KPI đúng tên trong Guide, tính từ `orders`, `customers`, `app_sessions`.
- Dashboard, analytics, báo cáo PDF, cảnh báo theo ngưỡng, nhóm, ghi chú, trang System Administrator, upload CSV.
- Số liệu đối chiếu được với các ví dụ tính tay trong README dataset.

**Không làm (theo Guide):**

- Kết nối dữ liệu live qua API.
- Phát hiện bất thường tự động bằng AI.
- Market intelligence.
- App mobile native.
- Gửi email thật (prototype ghi vào hộp thư giả).
- Push notification.
- Gộp nhiều điều kiện trong một rule, nhiều bộ lọc cùng lúc, lời mời vào nhóm cần chấp nhận.

## 2. Công nghệ và kiến trúc

Prototype là một ứng dụng FastAPI duy nhất, vừa phục vụ API vừa phục vụ trang web, lưu dữ liệu trong một file SQLite và không cần dịch vụ bên ngoài.

&#91;embedded content: kiến trúc prototype · trình duyệt, backend, SQLite, CSV\]

Mọi màn hình gọi cùng một module KPI nên số liệu không lệch nhau; tác vụ nền cũng dùng chính module này để kiểm tra rule cảnh báo.

| Lớp | Lựa chọn đề xuất | Lý do |
| --- | --- | --- |
| Ngôn ngữ | Python 3.11 trở lên, môi trường `venv` | Đúng lựa chọn của bạn |
| Backend | FastAPI + Uvicorn | API JSON, tự sinh trang `/docs` để thử từng endpoint |
| Dữ liệu | SQLite (module `sqlite3` có sẵn) | Một file, đủ cho khoảng 13 nghìn đơn và 46 nghìn phiên |
| Giao diện | HTML + JavaScript thuần, FastAPI phục vụ file tĩnh | Không cần Node; dễ viết mobile first |
| Biểu đồ và kéo thả | Chart.js; SortableJS | SortableJS hỗ trợ nhấn giữ để kéo trên điện thoại |
| PDF | ReportLab | Cài bằng `pip`, không cần thư viện hệ thống nên chạy tốt trên Windows |
| Tác vụ nền | APScheduler | Chạy chu kỳ 5 phút và báo cáo định kỳ trong cùng tiến trình |
| Kiểm thử | pytest | Đối chiếu số liệu theo mục 7 |

**Cấu trúc thư mục dự kiến:**

```text
bizboard/
  app/
    main.py        # khởi tạo FastAPI, phục vụ file tĩnh
    db.py          # kết nối SQLite, tạo bảng
    auth.py        # chọn tài khoản mẫu, phiên 30 phút, kiểm tra quyền
    kpi.py         # 8 KPI, kỳ, bộ lọc
    importer.py    # nạp CSV, kiểm tra file upload
    scheduler.py   # tác vụ 5 phút: refresh, alert, email giả, báo cáo định kỳ
    pdf.py         # tạo PDF báo cáo
    routers/       # dashboard, analytics, reports, alerts, groups, admin
  static/          # HTML, JS, CSS, Chart.js
  data/            # CSV mẫu và upload_*.csv
  tests/           # pytest đối chiếu với mục 7
  requirements.txt
```

## 3. Database SQLite

Database có 3 bảng dữ liệu kinh doanh nạp từ CSV và khoảng 12 bảng cho người dùng, chia sẻ và thông báo. Mọi thứ người dùng chọn (widget, bố cục, kỳ) lưu trong DB theo tài khoản, đúng yêu cầu "thấy cùng lựa chọn trên mọi thiết bị".

| Bảng | Cột chính | Dùng cho |
| --- | --- | --- |
| `orders` | order\_id, order\_datetime, customer\_id, region, city, product\_category, product\_name, sales\_channel, device, payment\_method, discount\_code, unit\_price, quantity, discount\_amount, order\_value, status | Total Sales, Total Revenue, Average Order Value, Revenue Growth, Customer Retention Rate, lọc, drill-down |
| `customers` | customer\_id, full\_name, email, signup\_date, region, city, segment, acquisition\_source | New Customers |
| `app_sessions` | session\_id, session\_datetime, user\_id, platform, duration\_seconds, pages\_viewed, converted | Active Users, Conversion Rate |
| `upload_batches` | id, filename, uploaded\_by (Admin), uploaded\_at, status, row\_count, skipped\_rows\_json, error\_summary | Lịch sử upload, refresh ngay sau upload hợp lệ |
| `users` | id, name, email (có thể trống), system\_role, is\_active | Đăng nhập, phân quyền, Bao không có email |
| `groups`, `group_members` | group\_id, name, owner\_id; group\_id, user\_id, role (Owner/Member) | Nhóm và quyền trong nhóm |
| `dashboard_prefs` | user\_id, widget\_ids theo thứ tự, period\_key | Lựa chọn, bố cục, kỳ đã lưu |
| `snapshots` | id, owner\_id, name, period\_start, period\_end, captured\_at, data\_json | Chụp dashboard, không đổi khi dữ liệu refresh |
| `reports` | id, owner\_id, name, kpis\_json, period\_start, period\_end, generated\_at, pdf\_path | Báo cáo PDF là bản chụp tại thời điểm tạo |
| `report_schedules` | id, owner\_id, kpis\_json, period\_key, frequency, next\_run, active | Báo cáo định kỳ |
| `shares` | item\_type (report/snapshot), item\_id, target\_type (user/group), target\_id, created\_at | Chia sẻ cho cá nhân và nhóm, thu hồi quyền |
| `notes` | id, report\_id, author\_id, body, created\_at, updated\_at | Ghi chú dưới báo cáo (không có cho snapshot) |
| `alert_rules` | id, user\_id, kpi, condition (above/below), threshold, is\_active, is\_triggered | Rule ngưỡng, nhớ trạng thái đang vượt ngưỡng |
| `alerts` | id, rule\_id, user\_id, kpi, condition, threshold, value, created\_at, is\_read, email\_status | Thông báo trong app, "email not delivered" |
| `notification_settings` | user\_id, email\_on\_alert, email\_on\_share | Hai công tắc email, mặc định bật |
| `mailbox` | id, to\_user\_id, subject, body, attempt, status, sent\_at | Hộp thư giả thay cho email thật, có thể mô phỏng lỗi để thử retry |
| `activity_log` | id, actor\_id, action, target, created\_at | Admin xem ai thêm/xóa thành viên |

**Quy ước quan trọng:** mọi truy vấn KPI chỉ lấy `status = 'completed'`. Thời gian lưu dạng `YYYY-MM-DD HH:MM:SS`. Những widget không lưu trong DB vì danh mục giống nhau cho mọi người, định nghĩa ngay trong code.

## 4. Công thức 8 KPI

Tất cả KPI viết trong một module Python duy nhất nhận (khoảng thời gian, bộ lọc) và trả về giá trị hoặc `None` khi không có dữ liệu. Dashboard, analytics, báo cáo và cảnh báo đều gọi module này để số liệu không bao giờ lệch nhau.

| KPI | Cách tính trong một period | Nguồn | Khi nào là no data |
| --- | --- | --- | --- |
| Total Sales | Số đơn `completed` có `order_datetime` trong period | orders | Không có đơn nào trong period (kể cả trước 01 Jun 2026) |
| Total Revenue | Tổng `order_value` của đơn `completed` | orders | Như Total Sales |
| Average Order Value | Total Revenue chia Total Sales | orders | Total Sales = 0 |
| Revenue Growth | (Revenue kỳ này trừ Revenue kỳ trước) chia Revenue kỳ trước; hai kỳ cùng độ dài | orders | Kỳ trước không có doanh thu |
| New Customers | Số khách có `signup_date` trong period | customers | Không có khách đăng ký trong period |
| Customer Retention Rate | Trong số khách có đơn `completed` ở kỳ liền trước cùng độ dài, tỉ lệ khách mua lại trong kỳ này | orders | Kỳ trước không có khách mua |
| Active Users | Số `user_id` khác nhau có ít nhất 1 session trong period | app\_sessions | Không có session (ví dụ 20 đến 22 Sep) |
| Conversion Rate | Số user có session `converted = 1` chia Active Users | app\_sessions | Active Users = 0 |

**Quy tắc dùng chung**

- Đơn `cancelled` và `refunded` không tính vào KPI nhưng vẫn có trong file và hiện ở drill-down. Danh sách drill-down phải có cột `status` để người dùng hiểu vì sao tổng không bằng số dòng.
- Bộ lọc chỉ áp dụng được cho các KPI có cột tương ứng. `region`, `city` có trong `orders` và `customers`; `product_*`, `sales_channel`, `device`, `payment_method` chỉ có trong `orders`. Khi lọc theo cột mà bảng của KPI không có (ví dụ Active Users lọc theo `product_name`), prototype hiển thị "bộ lọc không áp dụng cho KPI này" thay vì trả số sai.
- Retention và Conversion phụ thuộc độ dài period, vì vậy hai kỳ so sánh luôn cùng số ngày (đã là quy tắc của period comparison).
- Total Sales đếm số đơn (đã chốt).

## 5. Danh sách API

Backend FastAPI trả JSON; mọi endpoint trừ đăng nhập đều kiểm tra phiên và quyền trước khi xử lý, vì vậy truy cập thiếu quyền luôn trả một thông báo "no access" thống nhất (403).

| Bước | Endpoint | Mục đích |
| --- | --- | --- |
| 1 | `GET /api/kpis?period=&start=&end=&filter=` | Giá trị 8 KPI cho một kỳ |
| 1 | `POST /api/uploads` | Chỉ Admin: upload CSV, bỏ dòng lỗi, ghi đè theo order\_id, refresh ngay |
| 2 | `GET /api/widgets` | Danh mục widget, đánh dấu đã thêm và no data |
| 2 | `GET /api/dashboard`, `PUT /api/dashboard/selection` | Đọc dashboard; lưu lựa chọn khi bấm Save |
| 2 | `PUT /api/dashboard/layout`, `POST /api/dashboard/reset` | Lưu bố cục tự động; về mặc định |
| 2 | `PUT /api/dashboard/period` | Lưu kỳ đã chọn |
| 2 | `POST /api/snapshots`, `GET /api/snapshots`, `DELETE /api/snapshots/{id}` | Chụp, liệt kê, xóa snapshot |
| 3 | `GET /api/analytics/trend` | Chuỗi thời gian của một KPI theo giờ/ngày/tuần |
| 3 | `GET /api/analytics/compare` | Hai kỳ cùng độ dài, chênh lệch số và phần trăm |
| 3 | `GET /api/analytics/filters` | Danh mục và giá trị có thật trong dữ liệu |
| 3 | `GET /api/analytics/drilldown` | Các đơn tạo nên một điểm trên biểu đồ |
| 4 | `POST /api/reports`, `GET /api/reports`, `GET /api/reports/{id}/pdf`, `DELETE /api/reports/{id}` | Tạo, liệt kê, tải, xóa báo cáo |
| 4 | `POST/PUT/DELETE /api/schedules` | Báo cáo định kỳ |
| 4 | `POST/DELETE /api/shares` | Chia sẻ, thu hồi quyền |
| 4 | `GET/POST/PUT/DELETE /api/alert-rules` | Rule cảnh báo |
| 4 | `GET /api/alerts`, `POST /api/alerts/{id}/read` | Danh sách thông báo trong app |
| 4 | `GET/PUT /api/notification-settings` | Hai công tắc email |
| 5 | `GET/POST/PUT/DELETE /api/groups`, `POST/DELETE /api/groups/{id}/members` | Nhóm và thành viên |
| 5 | `GET/POST/PUT/DELETE /api/reports/{id}/notes` | Ghi chú dưới báo cáo |
| 5 | `GET/PUT/DELETE /api/admin/...` | Admin: nhóm, chủ nhóm, tài khoản, ghi chú, activity log, danh sách file upload |
| 6 | `GET /api/dev/mailbox` | Xem email giả (chỉ dùng khi demo) |

**Tiến trình nền (không phải endpoint):** một tác vụ chạy mỗi 5 phút làm mới dữ liệu, kiểm tra rule cảnh báo, gửi email giả và chạy các báo cáo đến lịch.

## 6. Kế hoạch 6 bước

Mỗi bước kết thúc bằng một bản chạy được và một phép kiểm tra cụ thể, nên có thể dừng ở bất kỳ bước nào mà vẫn có sản phẩm dùng được. Nếu chỉ cần ảnh minh họa cho báo cáo, dừng sau bước 3.

| Bước | Việc làm | Xong khi |
| --- | --- | --- |
| 1. Nền tảng và dữ liệu | Tạo dự án FastAPI + SQLite. Nạp `orders`, `customers`, `app_sessions`, `users`, `groups`, `group_members`, `alert_rules` từ CSV. Viết module KPI. Đăng nhập đơn giản bằng chọn tài khoản mẫu (Admin An, Hoa, Len, Phu, Yuki, Mai, Bao; Nam đã bị deactivate nên bị chặn). Tiến trình nền 5 phút. Upload CSV (chỉ Admin): bỏ dòng lỗi và báo rõ dòng nào, ghi đè theo `order_id`. | `GET /api/kpis` cho 1–7 Nov trả đúng 421 đơn, $15,641.04, 37.15, 112, 1,240, 29.4%. `upload_01` được nhận nhưng số liệu không đổi (trùng y hệt dữ liệu có sẵn); `upload_08` làm ngày 5 Nov đổi ngay từ 79 đơn, $2,985.05 thành 88 đơn, $3,326.19; upload\_02 và upload\_05 bị từ chối cả file; upload\_03, upload\_06 và upload\_07 chỉ bị bỏ dòng lỗi và báo số dòng; upload\_04 giữ dòng cuối cho mỗi order\_id. |
| 2. Dashboard | Danh mục widget (nhóm theo Sales, Revenue, Customers, App usage; tìm theo tên; ô tick; widget no data vẫn hiện). Lưu lựa chọn khi bấm Save, bộ mặc định cho người mới, reset. Kéo thả bố cục tự lưu (giữ chạm trên điện thoại). Chọn kỳ (Today, Last 7 days, Last 30 days, This month) và hiện ngày cụ thể. Chụp snapshot, danh sách cá nhân và Shared with me. | Đăng nhập bằng hai tài khoản khác nhau thấy hai dashboard độc lập. Đóng trình duyệt mở lại vẫn giữ đúng lựa chọn, bố cục, kỳ. Snapshot không đổi khi dữ liệu refresh. |
| 3. Analytics | Trend theo giờ/ngày/tuần tùy kỳ. So sánh hai kỳ cùng độ dài (không trùng nhau, điền sẵn ngày kết thúc). Một bộ lọc một lúc, hiện bộ lọc đang dùng, xóa bằng một thao tác. Drill-down từ điểm trên biểu đồ. Thông báo no-data nêu rõ kỳ và bộ lọc, có nút đổi kỳ hoặc xóa lọc ngay. | So sánh 1–7 Nov với 15–21 Sep ra $15,641.04 so với $21,116.56 (−5,475.52, −25.9%). Region: North cho 147 đơn, $4,929.98, 384 Active Users. Drill-down ngày 3 Nov liệt kê 16 dòng, 15 dòng `completed` cộng lại $662.50. Region: Central trong 9–13 Oct và kỳ 20–26 May hiện "No data". |
| 4. Báo cáo và thông báo | Tạo PDF (chọn KPI, kỳ, tên mặc định), danh sách báo cáo, xóa. Xử lý thiếu input: không chọn KPI, kỳ sai, KPI no data (hộp xác nhận "Generate without them"), lỗi tạo PDF. Báo cáo định kỳ. Chia sẻ cá nhân và nhóm, thu hồi quyền. Rule ngưỡng, kiểm tra sau mỗi lần refresh, nhớ trạng thái đang vượt ngưỡng, bỏ qua khi KPI không có dữ liệu. Giao: lưu trong app, email giả trong 1 phút, thử lại 3 lần cách nhau 1 phút, đánh dấu "email not delivered". Hai công tắc email. | Rule R01 (Total Revenue dưới 1,000) tạo đúng 2 alert: 3 Nov (4 Nov không tạo thêm) và 7 Nov. Rule R04 đang tắt không tạo alert. Bao không email nên chỉ nhận in-app. Mô phỏng lỗi mail thấy 3 lần thử rồi đánh dấu lỗi. Báo cáo 20–22 Sep có KPI app usage trống thì hiện hộp xác nhận. |
| 5. Nhóm, ghi chú, admin | Tạo nhóm (người tạo thành Group Owner), thêm/xóa thành viên ngay không cần lời mời, rời nhóm, chuyển quyền chủ nhóm trước khi rời. Ghi chú: nhận qua nhóm thì được viết, nhận cá nhân thì chỉ đọc; tác giả sửa/xóa ghi chú của mình, chủ báo cáo và Admin xóa bất kỳ ghi chú. Trang Admin: xem và sửa mọi nhóm, deactivate user, activity log, danh sách file upload (tên file, giờ upload, số dòng nạp, số dòng bị bỏ). Thiếu quyền → thông báo "no access". | Phu chia sẻ cho Sales Team: Len và Mai xem và viết được ghi chú; chia sẻ riêng cho Hoa thì Hoa chỉ đọc. Phu không chia sẻ được cho nhóm Marketing nhưng chia cá nhân cho Yuki được. Mai rời Sales Team thì mất quyền xem báo cáo và ghi chú. |
| 6. Hoàn thiện | Rà soát NFR-01 đến NFR-14 (tốc độ dashboard dưới 3 giây, PDF dưới 10 giây, phiên hết sau 30 phút, nút tối thiểu 44px, 360px). Làm bộ kiểm thử tự động cho các số trong mục 7. Chụp ảnh màn hình cho SRS. | Tất cả test đạt; có bộ ảnh màn hình để đưa vào báo cáo. |

**Lưu ý cho bước 4:** README ghi R01 tạo alert lần 1 vào 3–4 Nov (một alert, vì 4 Nov vẫn dưới ngưỡng) và alert thứ hai vào 7 Nov, sau khi 5–6 Nov đã về bình thường. Kiểm tra đầu ra của prototype với đúng chuỗi ngày này.

## 7. Kiểm thử đối chiếu

Các con số trong README dataset là đáp án để viết test tự động (pytest). File `kpi_daily_answer_key.csv` dùng để đối chiếu toàn bộ 160 ngày, chỉ dùng trong test, không phải nguồn dữ liệu của app.

| Test | Kỳ / điều kiện | Kết quả mong đợi |
| --- | --- | --- |
| Dashboard Last 7 days | 1–7 Nov | Total Sales 421; Average Order Value $37.15; Total Revenue $15,641.04; New Customers 112; Customer Retention Rate 8.2%; Active Users 1,240; Conversion Rate 29.4% |
| So sánh hai kỳ | A = 1–7 Nov, B = 15–21 Sep | Total Revenue $15,641.04 so với $21,116.56 (−$5,475.52, −25.9%); Total Sales 421 so với 589 (−168, −28.5%); Active Users 1,240 so với 1,237 (+3, +0.2%) |
| Bộ lọc | Region: North, 1–7 Nov | Total Sales 147; Total Revenue $4,929.98; Active Users 384 |
| Drill-down | Ngày 3 Nov | 16 dòng, 15 dòng `completed` tổng $662.50 |
| No data app usage | 20–22 Sep | Active Users và Conversion Rate là no data; 253 đơn, $9,078.17 |
| Bộ lọc rỗng | Region: Central, 9–13 Oct | "No data", trong khi New Customers vẫn 26 |
| Kỳ trước dữ liệu | 1–7 Nov so với 20–26 May | Chỉ hiện kỳ có dữ liệu, nêu rõ kỳ còn lại không có |
| Alert R01 | Total Revenue dưới 1,000 | Đúng 2 alert: lần đầu khi cắt ngưỡng (3 Nov), lần hai ngày 7 Nov; 4 Nov không tạo thêm |
| Alert R03, R04 | R03 dưới 20% Conversion Rate; R04 đang tắt | Không tạo alert nào |
| Đơn không tính | 20–24 Oct | Đơn `refunded` không vào doanh thu, nhưng còn trong drill-down |
| Upload hợp lệ, trùng dữ liệu | `upload_01_valid_orders.csv` | 40 dòng được nạp, giờ refresh cập nhật; ngày 5 Nov vẫn 79 đơn, $2,985.05 (không tính đôi) |
| Upload hợp lệ, có thay đổi | `upload_08_new_and_changed_orders.csv` | 12 đơn mới, 3 đơn đổi sang `refunded`; ngày 5 Nov thành 88 đơn, $3,326.19; kỳ 1–7 Nov thành 430 đơn, $15,982.18 |
| Upload lỗi | `upload_02` đến `upload_07` | upload\_02 và upload\_05 bị từ chối cả file; upload\_03, upload\_06 và upload\_07 bỏ dòng lỗi (ngày tương lai là dòng lỗi) và báo số dòng; upload\_04 giữ dòng cuối cho mỗi order\_id, không tính đôi doanh thu |
| Phân quyền | Các tình huống mục 5 của README | Đúng theo bảng ở bước 5 của kế hoạch |

Lưu ý: README ghi "hôm nay" là 08 Nov 2026 để Last 7 days bằng 1–7 Nov, vì vậy prototype cần một hằng ngày giả lập (đặt ngày hiện tại = 2026-11-08) thay vì lấy ngày hệ thống, nếu không các con số trên sẽ lệch.

## 8. Giả định, rủi ro và quyết định đã chốt

**Giả định đang dùng (có thể đổi):**

- Ngày hiện tại cố định là 2026-11-08 để khớp README.
- Đăng nhập bằng cách chọn tài khoản mẫu, không có mật khẩu thật. NFR-06 (hết phiên sau 30 phút) vẫn làm được; NFR-07 (HTTPS) và NFR-08 (hash mật khẩu) chỉ được nêu trong tài liệu, không được làm trong prototype.
- Email là hộp thư giả trong DB. "Trong 1 phút" và "thử lại cách nhau 1 phút" dùng bộ hẹn giờ có thể đổi nhanh khi demo.
- Custom range là tùy chọn trong Guide, nên bỏ qua trừ khi còn thời gian.

**Rủi ro:**

| Rủi ro | Cách xử lý |
| --- | --- |
| Hiệu năng khi tính KPI trên 46k phiên và 12.9k đơn | Tạo chỉ mục theo ngày, việc này đủ cho SQLite; đo lại theo NFR-01 |
| Retention và Conversion sai khi lọc hoặc khi kỳ khác độ dài | Một module KPI duy nhất, test đối chiếu với answer key |
| Upload dữ liệu lỗi làm hỏng DB | Kiểm tra toàn bộ file trước, ghi trong một giao dịch, lỗi thì hủy |
| Phân quyền nằm rải rác, dễ sót | Một hàm kiểm tra quyền dùng chung cho mọi endpoint |
| Prototype lệch SRS | Khi đổi yêu cầu, sửa SRS và code cùng lúc; đừng thêm tính năng ngoài phạm vi |

**Quyết định đã chốt:**

- Total Sales đếm số đơn, không đếm số món.
- Bộ lọc giữ nguyên danh sách hiện tại: `region`, `city`, `product_category`, `product_name`, `sales_channel`, `device`, `payment_method`.
- File upload có dòng lỗi: bỏ dòng lỗi, nạp phần còn lại và báo rõ dòng nào bị bỏ.
- Upload ghi đè theo `order_id`: đơn trùng được thay bằng bản trong file, đơn mới được thêm, các đơn khác giữ nguyên.
- Chỉ Admin được upload; Admin có trang riêng để quản lý danh sách file upload.
- Xóa nhóm: snapshot đã chia sẻ cho nhóm đó mất quyền xem, giống báo cáo.
- File thiếu cột hoặc chỉ có dòng tiêu đề (`upload_02`, `upload_05`): từ chối cả file.
- `order_id` lặp ngay trong cùng một file (`upload_04`): giữ dòng cuối.
- Ngày ở tương lai (`upload_07`): coi là dòng lỗi và bỏ.
- Trang quản lý file upload chỉ xem lịch sử, Admin không xóa hay hoàn tác một lần upload.
