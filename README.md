# 🚀 Hướng Dẫn Kiểm Thử Tải Hệ Sinh Thái SATREPS FEDEGAN (`locustfile_integrated.py`)

Tài liệu hướng dẫn thực thi kịch bản kiểm thử hiệu năng & chịu tải tích hợp (**Integrated Load & Stress Testing**) cho toàn bộ hệ sinh thái số SATREPS FEDEGAN, tuân thủ nghiêm ngặt theo tài liệu đặc tả kỹ thuật:  
`Technical Specification: Stress Testing Services for SATREPS Systems (doc.txt)`.

---

## 📑 Mục lục
1. [Tổng quan hệ thống & Phân bổ tải](#1-tổng-quan-hệ-thống--phân-bổ-tải)
2. [Cài đặt & Chuẩn bị môi trường](#2-cài-đặt--chuẩn-bị-môi-trường)
3. [Các kịch bản kiểm thử (Scenarios)](#3-các-kịch-bản-kiểm-thử-scenarios)
   - [Kịch bản 1: Tăng liên tục tìm điểm gãy & Tự dừng (Breaking Point)](#-kịch-bản-1-tăng-liên-tục-tìm-điểm-gãy--tự-động-dừng-breaking-point---khuyên-dùng)
   - [Kịch bản 2: Dò tìm điểm nghẽn 5 phút (Bottleneck Discovery)](#-kịch-bản-2-dò-tìm-điểm-nghẽn-theo-giai-đoạn-5-phút-bottleneck-ramp-up)
   - [Kịch bản 3: Kịch bản Baseline 700 Users (Mục 6.1)](#-kịch-bản-3-kịch-bản-baseline-chuẩn-700-users-trong-10-phút-mục-61)
   - [Kịch bản 4: Kịch bản Tải đỉnh & Vượt ngưỡng Stress (Mục 6.2 & 6.3)](#-kịch-bản-4-kịch-bản-tải-đỉnh-peak-load--vượt-ngưỡng-stress-mục-62--63)
   - [Kịch bản 5: Chế độ Web UI tương tác (Interactive Mode)](#-kịch-bản-5-chế-độ-giao-diện-web-ui-tương-tác-interactive-mode)
4. [Cơ chế tự động dọn dẹp dữ liệu rác (Auto Cleanup)](#4-cơ-chế-tự-động-dọn-dẹp-dữ-liệu-rác-auto-cleanup)
5. [Bảng tham số biến môi trường (Environment Variables)](#5-bảng-tham-số-biến-môi-trường-environment-variables)
6. [Hướng dẫn đọc và phân tích Báo cáo HTML](#6-hướng-dẫn-đọc-và-phân-tích-báo-cáo-html)

---

## 1. Tổng quan hệ thống & Phân bổ tải

Kịch bản `locustfile_integrated.py` mô phỏng đầy đủ các phân hệ người dùng thật theo đặc tả `doc.txt` (kết hợp kịch bản **ĐỌC**, **GHI** và **DỮ LIỆU ĐỊA LÝ GIS**):

| Phân hệ | Lớp User | Trọng số tải | Nghiệp vụ kiểm thử chính |
| :--- | :--- | :---: | :--- |
| **App 1: Manual Traceability** | `ManualTraceabilityUser` | `1` | Tra cứu dòng đời gia súc (`GET /api/animals/timeline` - SQL Heavy JOIN), đọc cấu hình web, xác thực Auth (`POST /api/users/login`) |
| **App 2A: Grass-Fed Inspector** | `GrassFedInspectorUser` | `4` *(40%)* | Tra cứu danh sách thẩm định, sự kiện, thông tin công khai, **tải chứng chỉ số Digital Certificate**, xem **hộp thư thông báo Inbox**, **lập biên bản sự kiện trang trại (`POST /api/events/create`)**, đặt lịch thẩm định, đăng ký FCM device |
| **App 2B: Grass-Fed Slaughterhouse** | `GrassFedSlaughterhouseUser` | `3` *(30%)* | Danh sách lô giết mổ, **chi tiết lô mổ (`GET /api/lote/detail`)**, thống kê động vật, nhật ký vận hành & **chi tiết log quét mã (`GET /api/lote/logs/detail`)**, **tạo lô mổ mới (`POST /api/lote/add-list`)**, kiểm tra vật nuôi ngoài ($\le$ 20 concurrent) |
| **App 2C: Grass-Fed Rancher** | `GrassFedRancherUser` | `3` *(30%)* | Danh sách nông trại, **chi tiết nông trại (`GET /api/ranches/get/:id`)**, danh sách nhân sự nông dân (`GET /api/farmer/get-by-organization`), thống kê chứng chỉ, **lưu ranh giới thửa đất (`PUT /api/ranches/save-geo-points`)**, tạo mới trang trại (`POST /api/ranches/create`) |
| **App 2D: FEDEGAN Admin** | `FedeganAdminUser` | `1` | Dashboard thống kê chứng chỉ toàn quốc (`GET /api/fedegan/certifications/statistics`), thống kê người dùng (`GET /api/fedegan/users/statistics`), danh sách & phân quyền người dùng, **chi tiết hồ sơ thẩm định FEDEGAN (`GET /api/certifications/details`)**, **duyệt chứng nhận (`POST /api/fedegan/approve-certification`)** |
| **App 2E: Visitor / Public** | `GrassFedVisitorUser` | `2` | Người tiêu dùng quét QR tra cứu chứng chỉ công khai (`GET /api/certifications/public-info/:id`), xem thông tin trang trại và nguồn gốc thịt bò |
| **App 5: Output 2 Animal Growth** | `Output2GrowthAnalysisUser` | `1` | Phân hệ dự báo tăng trưởng gia súc công cộng, tải thông số giống cỏ Gompertz và Static Web Delivery |
| **App 6: Output 3 GeoForraje / BPS** | `Output3BiomassAnalyticalModelUser` | `1` | Giám sát sinh khối đồng cỏ Sentinel-2 & thực thi mô hình AI BPS (`POST /api/v1/biomass`) |


---

## 2. Cài đặt & Chuẩn bị môi trường

Mở terminal tại thư mục dự án `py/`:

```bash
cd /media/vhec-dev/127C4DD37C4DB1F1/VHEC_Project/satreps/py

# Kích hoạt môi trường ảo Python đã cài sẵn Locust
source venv/bin/activate

# (Tùy chọn) Kiểm tra phiên bản Locust
locust --version
```

---

## 3. 🌟 20 Kịch Bản Kiểm Thử Thao Tác Theo Từng Role (User Journey Scenarios)

Hệ thống cung cấp **20 kịch bản độc lập** mô phỏng chính xác chuỗi hành vi thao tác của từng vai trò người dùng trong hệ sinh thái số SATREPS:

| STT | Mã Kịch Bản | Role Người Dùng | Chuỗi Thao Tác Nghiệp Vụ Thực Tế | Lệnh Chạy Nhanh |
| :---: | :--- | :--- | :--- | :--- |
| **1** | `inspector_audit` | Thanh tra viên (Inspector) | Xem danh sách chờ duyệt ➔ Xem chi tiết chứng chỉ ➔ Tra cứu lịch sử sự kiện ➔ **Lập biên bản kiểm tra thực địa (`POST /api/events/create`)** | `./run_test.sh inspector_audit` |
| **2** | `inspector_schedule` | Thanh tra viên (Inspector) | Xem lịch hẹn thẩm định theo ngày ➔ **Đặt lịch kiểm tra trang trại (`POST /api/schedule/set-schedules`)** ➔ Xem thông báo inbox | `./run_test.sh inspector_schedule` |
| **3** | `inspector_cert` | Thanh tra viên (Inspector) | Tra cứu hồ sơ thẩm định công khai ➔ **Xem thông tin tổ chức thanh tra (`GET /api/organizations/get`)** ➔ Đăng ký thiết bị FCM | `./run_test.sh inspector_cert` |
| **4** | `slaughter_lote` | Nhà máy giết mổ (Slaughterhouse) | Xem danh sách lô mổ ➔ **Upload danh sách gia súc & Tạo mới lô mổ hàng loạt (`POST /api/lote/add-list`)** | `./run_test.sh slaughter_lote` |
| **5** | `slaughter_audit` | Nhà máy giết mổ (Slaughterhouse) | Xem chi tiết lô mổ & danh sách thẻ tai DIN ➔ Xem nhật ký vận hành ➔ **Xem chi tiết quét barcode từng DIN** | `./run_test.sh slaughter_audit` |
| **6** | `slaughter_external` | Nhà máy giết mổ (Slaughterhouse) | Thống kê gia súc theo dải ngày ➔ **Gọi dịch vụ tra cứu ngoài (External Information Service $\le 20$ users)** | `./run_test.sh slaughter_external` |
| **7** | `rancher_manage` | Chủ trang trại (Rancher) | Xem danh sách trang trại ➔ Xem thông tin chi tiết trang trại ➔ Xem thống kê chứng chỉ ➔ Tra cứu danh sách nhân sự nông dân | `./run_test.sh rancher_manage` |
| **8** | `rancher_create` | Chủ trang trại (Rancher) | **Đăng ký mới trang trại thử nghiệm với mã STRESS_* (`POST /api/ranches/create`)** ➔ Đăng ký thiết bị nhận thông báo đẩy | `./run_test.sh rancher_create` |
| **9** | `rancher_gis` | Chủ trang trại (Rancher) | Chọn trang trại ➔ **Vẽ & Cập nhật ranh giới không gian địa lý GIS Polygon (`PUT /api/ranches/save-geo-points`)** ➔ Đọc inbox | `./run_test.sh rancher_gis` |
| **10** | `admin_dashboard` | Quản trị FEDEGAN (Admin) | Dashboard thống kê chứng chỉ toàn quốc ➔ Dashboard thống kê người dùng ➔ **Phân trang danh sách người dùng toàn hệ thống** | `./run_test.sh admin_dashboard` |
| **11** | `admin_approval` | Quản trị FEDEGAN (Admin) | Xem chi tiết hồ sơ thẩm định & checklist ➔ **Phê duyệt cấp chứng chỉ bò ăn cỏ (`POST /api/fedegan/approve-certification`)** | `./run_test.sh admin_approval` |
| **12** | `traceability_timeline` | Truy xuất nguồn gốc (Traceability) | Xác thực Auth ➔ **Tra cứu dòng đời gia súc SQL Heavy JOIN qua 4 bảng** ➔ Tra cứu mã thẻ tai không định dạng | `./run_test.sh traceability_timeline` |
| **13** | `admin_reject` | Quản trị FEDEGAN (Admin) | Danh sách hồ sơ chờ xử lý ➔ Xem chi tiết biên bản không đạt ➔ **Từ chối cấp chứng chỉ bò ăn cỏ (`POST /api/fedegan/reject-certification`)** | `./run_test.sh admin_reject` |
| **14** | `output2_growth` | Phân hệ Tăng trưởng (Output 2) | Tải web SPA ➔ **Tải tham số cấu hình mô hình Gompertz tăng trưởng (`GET /api/system-configs?target=output2`)** | `./run_test.sh output2_growth` |
| **15** | `output3_biomass` | Phân hệ Viễn thám AI (Output 3) | Tải tham số GeoForraje ➔ Kiểm tra health BPS ➔ **Chạy mô hình AI Sentinel-2 ước tính sinh khối (`POST /api/v1/biomass`)** | `./run_test.sh output3_biomass` |
| **16** | `rancher_request_cert` | Chủ trang trại (Rancher) | Danh sách trang trại ➔ Trạng thái chứng nhận ➔ **Nộp hồ sơ xin cấp chứng chỉ bò ăn cỏ (`POST /api/events/create`)** | `./run_test.sh rancher_request_cert` |
| **17** | `admin_assign_inspector` | Quản trị FEDEGAN (Admin) | Danh sách tổ chức ➔ Danh sách thanh tra viên ➔ **Phân công thanh tra viên cho trang trại (`POST /api/fedegan/assign-inspector`)** | `./run_test.sh admin_assign_inspector` |
| **18** | `admin_clarification` | Quản trị FEDEGAN (Admin) | Danh sách hồ sơ chờ duyệt ➔ Xem tiêu chí ➔ **Gửi yêu cầu giải trình & bổ sung hồ sơ (`POST /api/fedegan/request-clarification`)** | `./run_test.sh admin_clarification` |
| **19** | `rancher_member_manage` | Chủ trang trại (Rancher) | Danh sách công nhân nông trại ➔ **Mời / đăng ký nông dân phụ trách đồng cỏ (`POST /api/farmer/create`)** | `./run_test.sh rancher_member_manage` |
| **20** | `slaughter_plant_network` | Nhà máy giết mổ / Chuỗi | Mạng lưới cơ sở liên kết ➔ Chi tiết lô mổ nguồn ➔ **Truy vết timeline chuyển dịch gia súc (`GET /api/animals/timeline`)** | `./run_test.sh slaughter_plant_network` |

---

## 4. Các kịch bản tải hệ thống toàn diện (System Load Shapes)

### 🔥 Kịch bản 1: Tăng liên tục tìm điểm gãy & Tự động dừng (Breaking Point) - [KHUYÊN DÙNG]

> **Mục đích:** Bắt đầu từ 500 users, cứ mỗi 15 giây tự động tăng thêm **+250 users**. Khi hệ thống bắt đầu bị nghẽn (Tỷ lệ lỗi $\ge$ 3% hoặc độ trễ P95 $\ge$ 5.0 giây), Locust sẽ **tự động dừng test ngay lập tức** để bảo vệ server và kích hoạt cơ chế dọn dẹp dữ liệu rác.

```bash
SCENARIO=breakingpoint ./venv/bin/locust -f locustfile_integrated.py \
  --headless \
  --host=https://satreps-api-427991251928.us-central1.run.app \
  --html report_breaking_point.html
```

---

### 📈 Kịch bản 2: Dò tìm điểm nghẽn theo giai đoạn 5 phút (Bottleneck Ramp-up)
> **Mục đích:** Tăng tải từ từ theo 5 nấc thời gian để xác định ngưỡng tải ổn định:
> - Phút 1 (0-60s)  : 200 users (Khởi động)
> - Phút 2 (60-120s): 500 users (Tải trung bình)
> - Phút 3 (120-180s): 1.000 users (Tiệm cận ngưỡng cao)
> - Phút 4 (180-240s): 1.500 users (Ép tải mạnh)
> - Phút 5 (240-300s): 2.000 users (Kiểm tra chịu đựng cực hạn)

```bash
SCENARIO=bottleneck ./venv/bin/locust -f locustfile_integrated.py \
  --headless \
  --host=https://satreps-api-427991251928.us-central1.run.app \
  --html report_bottleneck_5m.html
```

---

### 🎯 Kịch bản 3: Kịch bản Baseline chuẩn 700 Users trong 10 phút (Mục 6.1)
> **Mục đích:** Kiểm định nghiệm thu tải tiêu chuẩn theo hợp đồng FEDEGAN SATREPS: 700 người dùng đồng thời chạy liên tục trong 10 phút với mục tiêu P95 < 2.0 giây và tỷ lệ lỗi < 1%.

```bash
SCENARIO=baseline ./venv/bin/locust -f locustfile_integrated.py \
  --headless \
  --host=https://satreps-api-427991251928.us-central1.run.app \
  --html report_baseline.html
```

---

### ⚡ Kịch bản 4: Kịch bản Tải đỉnh (Peak Load) & Vượt ngưỡng Stress (Mục 6.2 & 6.3)
> **Mục đích:** Đẩy tải lên mốc cực đại để đánh giá khả năng co giãn tự động của Cloud Run và đo tốc độ hồi phục sau khi hạ tải.

```bash
# Kịch bản tải đỉnh 15.000 Users (Peak Load)
SCENARIO=peak ./venv/bin/locust -f locustfile_integrated.py \
  --headless \
  --host=https://satreps-api-427991251928.us-central1.run.app \
  --html report_peak.html

# Kịch bản Stress Test & Recovery (25.000 Users sau đó hạ về 700 Users)
SCENARIO=stress ./venv/bin/locust -f locustfile_integrated.py \
  --headless \
  --host=https://satreps-api-427991251928.us-central1.run.app \
  --html report_stress.html
```

---

---

### 💥 Kịch bản 5: Tải đột biến ngay lập tức (Spike Test / Flash Crowd)
> **Mục đích:** Đẩy ngay một lượng lớn người dùng (ví dụ 800 hoặc 1.000 users) ập vào hệ thống ngay trong vài giây đầu tiên để kiểm tra khả năng chịu sốc tải và độ trễ phản ứng auto-scaling của Cloud Run.
> - **Mặc định:** 800 users, tốc độ spawn 200 users/s (chỉ mất 4s để đạt đỉnh 800 users), duy trì trong 3 phút.
> - **Tùy chỉnh linh hoạt:** Có thể truyền thêm `USERS=...`, `SPAWN_RATE=...`, `DURATION=...` (giây).

```bash
# Chạy Spike Test mặc định 800 Users trong 3 phút
SCENARIO=spike ./venv/bin/locust -f locustfile_integrated.py \
  --headless \
  --host=https://satreps-api-427991251928.us-central1.run.app \
  --html report_spike.html

# Hoặc tùy biến: Bắn 1.200 users ngay lập tức trong 2 phút
USERS=1200 SPAWN_RATE=300 DURATION=120 SCENARIO=spike ./venv/bin/locust -f locustfile_integrated.py \
  --headless \
  --host=https://satreps-api-427991251928.us-central1.run.app \
  --html report_spike_1200.html
```

---

### 🪜 Kịch bản 6: Tăng từ từ từng nấc nhỏ (Step / Gradual Ramp-up)
> **Mục đích:** Bắt đầu từ lượng user rất nhỏ và tăng đều đặn qua từng bậc thang để xác định chính xác đường cong hiệu năng và mốc bắt đầu có độ trễ:
> - Nấc 1 (0-40s)  : 50 users (Rất nhẹ nhàng)
> - Nấc 2 (40-80s) : 150 users
> - Nấc 3 (80-120s): 300 users
> - Nấc 4 (120-160s): 500 users
> - Nấc 5 (160-200s): 750 users
> - Nấc 6 (200-240s): 1.000 users
> - Cooldown (240-270s): Hạ tải về 0

```bash
SCENARIO=step ./venv/bin/locust -f locustfile_integrated.py \
  --headless \
  --host=https://satreps-api-427991251928.us-central1.run.app \
  --html report_step_rampup.html
```

---

### 🎛️ Kịch bản 7: Tự do điều khiển qua dòng lệnh CLI thuần túy (Custom CLI Mode)
> **Mục đích:** Tắt toàn bộ các Load Shape tự động để tự do chỉ định bất kỳ số lượng users, spawn-rate và thời gian chạy trực tiếp từ CLI của Locust:

```bash
# Ví dụ A: Bắn ngay 600 users trong 3 giây, chạy 2 phút
SCENARIO=custom ./venv/bin/locust -f locustfile_integrated.py \
  --headless \
  --host=https://satreps-api-427991251928.us-central1.run.app \
  --users 600 \
  --spawn-rate 200 \
  --run-time 2m \
  --html report_custom_spike.html

# Ví dụ B: Tăng thật chậm từ từ (mỗi giây chỉ thêm 2 users) lên 300 users, chạy 5 phút
SCENARIO=custom ./venv/bin/locust -f locustfile_integrated.py \
  --headless \
  --host=https://satreps-api-427991251928.us-central1.run.app \
  --users 300 \
  --spawn-rate 2 \
  --run-time 5m \
  --html report_custom_slow.html
```

---

### 🖥️ Kịch bản 8: Chế độ Giao diện Web UI tương tác (Interactive Mode)
> **Mục đích:** Mở giao diện Web của Locust trên trình duyệt để tự do chỉnh số lượng Users và tốc độ Spawn bằng tay.

```bash
./venv/bin/locust -f locustfile_integrated.py \
  --host=https://satreps-api-427991251928.us-central1.run.app
```
Truy cập trình duyệt: **`http://localhost:8089`**  
Nhập số lượng `Number of users` và `Spawn rate` rồi nhấn **Start swarming**.

---

## 4. Cơ chế tự động dọn dẹp dữ liệu rác (Auto Cleanup)

Trong quá trình stress test, kịch bản tạo ra các giao dịch ghi thật vào cơ sở dữ liệu (`POST /api/ranches/create` và `POST /api/notifications/register-device`).

* **Không xóa ngay trong lúc test:** Để phản ánh chính xác hành vi người dùng thật, không làm sai lệch chỉ số đo lường tải của hệ thống.
* **Tự động xóa 100% khi dừng test (`@events.test_stop`):**
  - Sử dụng hàng đợi song song **30 luồng (`ThreadPoolExecutor`)** kết hợp tái sử dụng HTTP Session.
  - Quét sạch toàn bộ ID trang trại test có tiền tố `STRESS*` và vô hiệu hóa các device token sinh ra.
  - Tốc độ dọn dẹp: Xóa sạch hơn **1.000 trang trại chỉ trong 10 - 15 giây**.
  - Đảm bảo cơ sở dữ liệu PostgreSQL trên môi trường Production/Staging luôn sạch sẽ 100%.

---

## 5. Bảng tham số biến môi trường (Environment Variables)

| Tên biến | Giá trị khả dụng | Mặc định | Ý nghĩa |
| :--- | :--- | :---: | :--- |
| `SCENARIO` | `breakingpoint`, `bottleneck`, `baseline`, `peak`, `stress`, `interactive` | `interactive` | Lựa chọn kịch bản phân bổ hình dạng tải tự động |
| `BPS_BACKEND_HOST` | URL (Ví dụ: `http://localhost:8000`) | Rỗng | Địa chỉ của Python FastAPI BPS backend khi bật kiểm thử phân hệ Output 3 |
| `LOG_FAILURES_TO_FILE`| `true`, `false` | `true` | Ghi chi tiết mã lỗi, Trace-ID và response body vào file `failures_integrated.log` |
| `ALERT_WEBHOOK_URL` | Webhook URL (Slack / Discord / Telegram) | Rỗng | Tự động gửi cảnh báo khi phát hiện Breaking Point |

---

## 6. Hướng dẫn đọc và phân tích Báo cáo HTML

File báo cáo HTML sinh ra (ví dụ: `report_breaking_point.html`) hiển thị đầy đủ biểu đồ trực quan:

1. **Total Requests & RPS (Thông lượng):**
   - Đánh giá khả năng xử lý số lượng yêu cầu mỗi giây của hệ thống (ngưỡng tốt: > 130 - 180 RPS).
2. **Failures (Tỷ lệ lỗi):**
   - Tiêu chuẩn Fedegan chấp nhận: **< 1.0%**.
   - Nếu xuất hiện lỗi `HTTP 500`: Nghẽn Connection Pool trong PostgreSQL (Cloud SQL).
   - Nếu xuất hiện lỗi `HTTP 503`: Container Cloud Run bị quá tải hàng đợi chưa kịp nhân bản instance.
3. **Response Time Percentiles (Độ trễ):**
   - **P50 (Trung vị):** Kỳ vọng `< 300 ms` (trải nghiệm mượt mà).
   - **P95 (Tiêu chuẩn):** Kỳ vọng `< 2.000 ms` (2 giây).
   - **P99 (Tải đỉnh):** Thời gian phản hồi của 1% người dùng gặp tải nặng nhất.
