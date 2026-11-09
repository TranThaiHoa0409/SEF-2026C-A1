# BizBoard sample dataset (v2) — GreenLeaf Coffee, dữ liệu bịa

Dataset **giả lập** để cả team hiểu business logic của BizBoard. Không phải dữ liệu thật; tên khách và email đều bịa (`@example.com`). Dùng để minh hoạ trong SRS và để mọi người cùng nhìn một ví dụ khi viết user story / use case / acceptance criteria.

**Công ty giả định:** GreenLeaf Coffee, cửa hàng cà phê online ở Việt Nam bán hạt cà phê, thiết bị pha, đồ lưu niệm và gói subscription. Đơn vị tiền: USD.
**Khoảng thời gian:** 01 Jun 2026 → 07 Nov 2026 (160 ngày). Coi "hôm nay" là 08 Nov 2026, nên "Last 7 days" = **1 to 7 Nov**.

## 1. Các file

| File | Dòng | Nội dung |
| --- | --- | --- |
| `orders.csv` | 12,876 | Mỗi dòng 1 đơn. Có trạng thái đơn, sản phẩm, giảm giá, thanh toán, thiết bị |
| `customers.csv` | 6,012 | Tài khoản khách: tên, email, vùng, thành phố, nhóm khách, nguồn khách |
| `app_sessions.csv` | 45,959 | Mỗi dòng 1 phiên dùng app: nền tảng, thời lượng, số trang, có mua hay không |
| `users.csv`, `groups.csv`, `group_members.csv` | 8 / 3 / 8 | Tài khoản BizBoard, nhóm, vai trò trong nhóm |
| `alert_rules.csv` | 6 | Các rule ngưỡng mẫu |
| `kpi_daily_answer_key.csv` | 160 | KPI tính sẵn theo ngày (đáp án để đối chiếu, **không phải nguồn** của app) |
| `upload_01_...csv` đến `upload_07_...csv` | 7 file | File upload mẫu: 1 file hợp lệ và 6 file lỗi (xem mục 6) |

Hệ thống thật chỉ cần `orders`, `customers`, `app_sessions` (đúng quyết định "sample datasets + uploaded files").

### Từ điển cột

**orders.csv**

| Cột | Ý nghĩa |
| --- | --- |
| `order_id` | Mã đơn, duy nhất |
| `order_datetime` | Thời điểm đặt, `YYYY-MM-DD HH:MM:SS` |
| `customer_id` | Khách đặt (nối với `customers.csv`) |
| `region`, `city` | Vùng (North, Central, South) và thành phố giao hàng |
| `product_category`, `product_name` | Nhóm sản phẩm và tên sản phẩm |
| `sales_channel` | Website, Mobile Web hoặc Marketplace |
| `device`, `payment_method` | Thiết bị đặt hàng và cách thanh toán |
| `discount_code` | Mã giảm giá, để trống nếu không dùng |
| `unit_price`, `quantity`, `discount_amount` | Đơn giá, số lượng, số tiền được giảm |
| `order_value` | Giá trị đơn sau giảm giá = `unit_price × quantity − discount_amount` |
| `status` | `completed`, `cancelled` hoặc `refunded` |

**customers.csv:** `customer_id, full_name, email, signup_date, region, city, segment (Consumer/Business), acquisition_source (Organic, Facebook Ads, Google Ads, Referral, Email)`.
**app_sessions.csv:** `session_id, session_datetime, user_id (= customer_id), platform (iOS/Android/Web), duration_seconds, pages_viewed, converted (1 = có mua trong phiên)`.

## 2. 8 KPI tính từ dữ liệu thế nào

Tên KPI giữ **đúng** như guide của team. **Chỉ đơn `completed` được tính vào KPI.** Đơn `cancelled` và `refunded` có trong file nhưng không tính doanh thu.

| KPI | Cách tính trong một period | Nguồn |
| --- | --- | --- |
| Total Sales | Số đơn `completed` có `order_datetime` trong period | orders |
| Average Order Value | Total Revenue ÷ Total Sales | orders |
| Total Revenue | Tổng `order_value` của đơn `completed` | orders |
| Revenue Growth | (Revenue kỳ này − Revenue kỳ trước) ÷ Revenue kỳ trước, hai kỳ cùng độ dài | orders |
| New Customers | Số khách có `signup_date` trong period | customers |
| Customer Retention Rate | Trong số khách đã mua (đơn `completed`) ở kỳ liền trước cùng độ dài, tỉ lệ khách mua lại trong kỳ này | orders |
| Active Users | Số `user_id` khác nhau có ít nhất 1 session trong period | app_sessions |
| Conversion Rate | Số user có session `converted = 1` ÷ Active Users | app_sessions |

**Team cần chốt (mình tự giả định để dataset chạy được):**
1. *Total Sales* guide ghi "items or orders". Dataset đếm **số đơn**. Muốn đếm số món thì cộng `quantity`.
2. Đơn `cancelled` / `refunded` không tính vào Total Sales và Total Revenue. Nếu team muốn hiện "Refunds" như một KPI riêng thì đó là tính năng mới, ngoài scope hiện tại.
3. *Retention* và *Conversion* tính theo **period**, nên period dài hơn thì số cao hơn (Retention: tuần ≈ 10–25%, tháng ≈ 55–60%). Đừng so sánh hai period khác độ dài.

## 3. Ví dụ tính tay (dùng để viết acceptance criteria)

**Dashboard "Last 7 days: 1 to 7 Nov"**

| KPI | Giá trị |
| --- | --- |
| Total Sales | 421 |
| Average Order Value | $37.15 |
| Total Revenue | $15,641.04 |
| New Customers | 112 |
| Customer Retention Rate | 8.2% (so với 25–31 Oct) |
| Active Users | 1,240 |
| Conversion Rate | 29.4% |

**Period comparison** (Period A = 1–7 Nov, Period B = 15–21 Sep)

| KPI | Period A | Period B | Chênh lệch |
| --- | --- | --- | --- |
| Total Revenue | $15,641.04 | $21,116.56 | -$5,475.52 (-25.9%) → **Revenue Growth** |
| Total Sales | 421 | 589 | -168 (-28.5%) |
| Active Users | 1,240 | 1,237 | +3 (+0.2%) |

**Filter** `Region: North`, 1–7 Nov: Total Sales 147, Total Revenue $4,929.98, Active Users 384.

**Drill-down** ngày 3 Nov: file có 16 đơn, trong đó 15 đơn `completed` tạo nên Total Revenue $662.50. Các đơn `cancelled` / `refunded` của ngày đó nằm trong file nhưng không nằm trong con số. Đây là chỗ để viết quy tắc "danh sách chi tiết phải khớp với con số trên biểu đồ".

## 4. Các tình huống đã cài sẵn trong dữ liệu

| # | Tình huống | Dữ liệu | Dùng cho |
| --- | --- | --- | --- |
| S1 | **Doanh thu tụt** (sự cố cổng thanh toán) | Total Revenue dưới $1,000 vào: 03 Nov ($662), 04 Nov ($516), 07 Nov ($520). Ngày bình thường trung bình ≈ $2,649 | Alert rule `R01` (Total Revenue below 1,000) |
| S2 | **Alert chỉ tạo khi vừa cắt ngưỡng** | 3 và 4 Nov đều dưới 1,000 → 1 alert. 5–6 Nov về bình thường. 7 Nov dưới ngưỡng lại → alert thứ 2 | Alert checking ("remember triggered") |
| S3 | **Khuyến mãi 10.10** | 10–12 Oct doanh thu tăng ~1.7×; 70% đơn dùng mã `1010SALE` (giảm 20%) | Rule `R02` (above 3,500), trend, so sánh kỳ |
| S4 | **Mất dữ liệu app usage** | 20–22 Sep không có session → Active Users và Conversion Rate = no data, nhưng doanh thu vẫn có (253 đơn, $9,078.17) | No-data rule, report "một số KPI không có data" |
| S5 | **Một vùng không có đơn** | Region Central không có đơn 9–13 Oct → filter Region: Central ra "No data", trong khi New Customers vẫn là 26 | Filter rỗng |
| S6 | **Kỳ không có dữ liệu** | Trước 01 Jun 2026 không có đơn nào (ví dụ so 1–7 Nov với 20–26 May) | Period comparison có 1 kỳ no data |
| S7 | **Cuối tuần cao hơn** | Thứ 7, CN cao hơn ngày thường ~30% | Trend theo ngày không phẳng |
| S8 | **Đợt hoàn tiền** | 20–24 Oct, 17% đơn nhóm Equipment bị `refunded` (bình thường 2%) | Đơn refunded không tính vào doanh thu; chênh lệch giữa số đơn trong file và Total Sales |
| S9 | **Marketplace ngừng hoạt động** | 14–15 Sep không có đơn nào qua Marketplace (0 đơn) | Filter theo `sales_channel` (nếu team chọn category này) |
| S10 | **Ra mắt sản phẩm mới** | `Cold Brew Kit` chỉ xuất hiện từ 01 Oct (57 đơn) | Filter theo `product_name`, drill-down |
| S11 | **Tăng giá** | Giá trung bình Arabica Dalat 250g: $14.01 (Oct) → $15.11 (từ 1 Nov, +8%) | Average Order Value thay đổi dù số đơn không đổi |
| S12 | **Mã giảm giá** | Số đơn theo mã: WELCOME 1411, SAVE10 858, 1010SALE 302 | `order_value` đã trừ giảm giá; Revenue không bằng giá niêm yết |

Số đơn theo trạng thái: completed 12,097, cancelled 490, refunded 289.
Rule `R03` (Conversion Rate below 20%) không bao giờ kích hoạt (thấp nhất 24.2%): ví dụ "rule không có alert". Rule `R04` đang tắt nên không tạo alert dù New Customers thấp. Rule `R05` (Total Revenue below 2,500) và `R06` (Active Users above 1,200) để thử nhiều rule trên cùng một KPI / nhiều người dùng.

## 5. Tình huống phân quyền / chia sẻ

| User | Vai trò hệ thống | Nhóm |
| --- | --- | --- |
| Admin An | System Administrator | không thuộc nhóm nào |
| Hoa | Business User | Group Owner của Management |
| Len | Business User | Group Owner của Sales Team; Member của Management |
| Phu | Business User | Member của Sales Team |
| Yuki | Business User | Group Owner của Marketing |
| Mai | Business User | Member của Sales Team **và** Marketing |
| Bao | Business User | Member của Marketing, **không có email** → chỉ nhận in-app |
| Nam | (đã bị deactivate) | không đăng nhập được |

- Phu chia sẻ report cho **Sales Team** → Len, Mai xem được và **được viết note**.
- Phu chia sẻ riêng cho Hoa (cá nhân) → Hoa đọc được note nhưng **không viết note**.
- Phu **không** chia sẻ được cho Marketing vì không thuộc nhóm đó, nhưng vẫn chia sẻ cá nhân cho Yuki được.
- Mai rời Sales Team → mất quyền xem report và note qua nhóm đó.
- Alert cho Bao chỉ hiện in-app vì không có email.

## 6. File upload mẫu (các file `upload_*.csv`)

Dùng để viết alternative flow cho việc **upload file** (nguồn dữ liệu thứ hai ngoài sample dataset). Hành vi mong đợi chỉ là gợi ý, team quyết định thông báo lỗi cụ thể.

| File | Có gì | Hệ thống nên làm gì |
| --- | --- | --- |
| `upload_01_valid_orders.csv` | 40 đơn ngày 5 Nov, đúng cột, đúng định dạng | Nhận file, dữ liệu refresh ngay, dashboard cập nhật |
| `upload_02_missing_column_order_value.csv` | Thiếu cột `order_value` | Từ chối, nêu rõ cột còn thiếu |
| `upload_03_bad_dates.csv` | 3 dòng ngày sai (`05/11/2026 14:20`, `not a date`, để trống) | Từ chối hoặc bỏ dòng lỗi và báo rõ dòng nào |
| `upload_04_duplicate_order_ids.csv` | 5 `order_id` bị lặp | Báo trùng, không tính đôi doanh thu |
| `upload_05_empty_header_only.csv` | Chỉ có dòng tiêu đề | Báo file không có dữ liệu |
| `upload_06_negative_blank_and_text_values.csv` | `order_value` âm / chữ / trống, `customer_id` trống, `quantity` là chữ | Báo từng loại lỗi và dòng lỗi |
| `upload_07_dates_in_the_future.csv` | Ngày năm 2027 | Cảnh báo ngày ở tương lai |

## 7. Giới hạn của dataset

- Dữ liệu sinh ngẫu nhiên có seed cố định: con số "tự nhiên" nhưng không phản ánh doanh nghiệp thật.
- Không có market intelligence và API live (ngoài scope v1).
- Category dùng để filter: `region`, `city`, `product_category`, `product_name`, `sales_channel`, `device`, `payment_method`. Len cần chốt danh sách filter cuối cùng; guide chỉ cho phép một filter tại một thời điểm.
