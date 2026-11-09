# Cấu Trúc Dự Án Kiểm Thử Hiệu Năng SATREPS FEDEGAN

Dự án kiểm thử tải được cấu trúc lại theo tiêu chuẩn **Enterprise Performance Engineering**, module hóa toàn bộ thành các package độc lập, dễ bảo trì, dễ mở rộng và tích hợp đầy đủ **20 Kịch Bản Thao Tác Theo Từng Role** cùng các kịch bản tải hệ thống chuẩn.

---

## 📁 Sơ đồ Cây Thư Mục (Architecture)

```
py/
├── config/                     # Cấu hình môi trường & Dữ liệu mẫu (Seed Data)
│   ├── __init__.py
│   ├── settings.py             # Biến môi trường (SCENARIO, LOG_FAILURES, HOST)
│   └── seed_data.py            # Danh sách DIN, Fallback Certificate UUIDs, Org IDs
│
├── core/                       # Thành phần lõi (Core Engine)
│   ├── __init__.py
│   ├── auth.py                 # Single Login Cache (JWT), Traced Headers Generator
│   ├── state.py                # Bộ nhớ đệm động (DYNAMIC_DATA), Semaphore 20, Locks
│   └── base_user.py            # BaseSatrepsUser (Giả lập IP phân tán X-Forwarded-For)
│
├── users/                      # Các lớp Persona theo các Phân hệ kỹ thuật
│   ├── __init__.py
│   ├── traceability.py         # [App 1] ManualTraceabilityUser (SQL Heavy JOINs)
│   ├── inspector.py            # [App 2A] GrassFedInspectorUser (40% trọng số tải)
│   ├── slaughterhouse.py       # [App 2B] GrassFedSlaughterhouseUser (30% + Semaphore 20)
│   ├── rancher.py              # [App 2C] GrassFedRancherUser (30% tải, GIS Polygon)
│   ├── admin.py                # [App 2D] FedeganAdminUser (Tác vụ quản trị trung tâm)
│   ├── visitor.py              # [App 2E] GrassFedVisitorUser (Người tiêu dùng / Khách)
│   ├── output2_growth.py       # [App 5] Output2GrowthAnalysisUser (Mô hình tăng trưởng)
│   └── output3_biomass.py      # [App 6] Output 3 GeoForraje & Biomass ML Model
│
├── scenarios/                  # Bộ điều khiển kịch bản (Shapes & Role Scenarios)
│   ├── __init__.py
│   ├── role_scenarios.py       # 🌟 20 Kịch bản thao tác người dùng theo từng Role
│   └── shapes.py               # FEDEGANLoadTestShape (Điều phối hình thái tải theo thời gian)
│
├── hooks/                      # Trình lắng nghe sự kiện (Locust Lifecycle Hooks)
│   ├── __init__.py
│   └── listeners.py            # Logging lỗi chi tiết, Tổng kết sau test, Tự động dọn dẹp DB
│
├── run_test.sh                 # Script chạy nhanh 20 kịch bản theo role & tải hệ thống
├── locustfile_integrated.py    # Entry point chính (nhập và liên kết toàn bộ module)
└── requirements.txt            # Thư viện phụ thuộc (locust, requests)
```

---

## 📋 Danh Sách 20 Kịch Bản Thao Tác Người Dùng Theo Từng Role

| STT | Mã Kịch Bản | Role Người Dùng | Chuỗi Thao Tác Nghiệp Vụ Thực Tế | Tải Khuyến Nghị |
| :---: | :--- | :--- | :--- | :---: |
| **1** | `inspector_audit` | Thanh tra viên (Inspector) | Xem danh sách chờ duyệt ➔ Xem chi tiết chứng chỉ ➔ Tra cứu lịch sử sự kiện ➔ **Lập biên bản kiểm tra thực địa (`POST /api/events/create`)** | 100 users |
| **2** | `inspector_schedule` | Thanh tra viên (Inspector) | Xem lịch hẹn thẩm định theo ngày ➔ **Đặt lịch kiểm tra trang trại với nông hộ (`POST /api/schedule/set-schedules`)** ➔ Xem thông báo inbox | 100 users |
| **3** | `inspector_cert` | Thanh tra viên (Inspector) | Tra cứu hồ sơ thẩm định công khai ➔ **Xem thông tin tổ chức thanh tra (`GET /api/organizations/get`)** ➔ Đăng ký thiết bị nhận thông báo đẩy FCM | 100 users |
| **4** | `slaughter_lote` | Nhà máy giết mổ (Slaughterhouse) | Xem danh sách lô mổ ➔ **Upload danh sách gia súc & Tạo mới lô mổ hàng loạt (`POST /api/lote/add-list`)** | 50 users |
| **5** | `slaughter_audit` | Nhà máy giết mổ (Slaughterhouse) | Xem chi tiết lô mổ & danh sách thẻ tai DIN (Heavy JOIN) ➔ Xem nhật ký vận hành ➔ **Xem chi tiết kết quả quét barcode từng DIN** | 50 users |
| **6** | `slaughter_external` | Nhà máy giết mổ (Slaughterhouse) | Thống kê gia súc theo dải ngày ➔ **Gọi dịch vụ tra cứu ngoài (External Information Service với Semaphore $\le 20$)** | 50 users |
| **7** | `rancher_manage` | Chủ trang trại (Rancher) | Xem danh sách trang trại ➔ Xem thông tin chi tiết trang trại ➔ Xem thống kê chứng chỉ ➔ Tra cứu danh sách nhân sự nông dân | 500 users |
| **8** | `rancher_create` | Chủ trang trại (Rancher) | **Đăng ký mới trang trại thử nghiệm với mã STRESS_* (`POST /api/ranches/create`)** ➔ Đăng ký thiết bị nhận thông báo đẩy | 200 users |
| **9** | `rancher_gis` | Chủ trang trại (Rancher) | Chọn trang trại ➔ **Vẽ & Cập nhật ranh giới không gian địa lý GIS Polygon (`PUT /api/ranches/save-geo-points`)** ➔ Đọc inbox | 300 users |
| **10** | `admin_dashboard` | Quản trị FEDEGAN (Admin) | Dashboard thống kê chứng chỉ toàn quốc ➔ Dashboard thống kê người dùng ➔ **Phân trang danh sách người dùng toàn hệ sinh thái** | 50 users |
| **11** | `admin_approval` | Quản trị FEDEGAN (Admin) | Xem chi tiết hồ sơ thẩm định & checklist đánh giá ➔ **Phê duyệt cấp chứng chỉ bò ăn cỏ (`POST /api/fedegan/approve-certification`)** | 50 users |
| **12** | `traceability_timeline` | Truy xuất nguồn gốc (Traceability) | Xác thực Auth ➔ **Tra cứu dòng đời gia súc SQL Heavy JOIN qua 4 bảng** ➔ Tra cứu mã thẻ tai không định dạng ➔ Đọc config web | 100 users |
| **13** | `admin_reject` | Quản trị FEDEGAN (Admin) | Danh sách hồ sơ chờ xử lý ➔ Xem biên bản vi phạm ➔ **Từ chối cấp chứng chỉ bò ăn cỏ (`POST /api/fedegan/reject-certification`)** | 50 users |
| **14** | `output2_growth` | Phân hệ Tăng trưởng (Output 2) | Tải tài nguyên web SPA ➔ **Tải tham số cấu hình mô hình Gompertz tăng trưởng (`GET /api/system-configs?target=output2`)** | 100 users |
| **15** | `output3_biomass` | Phân hệ Viễn thám AI (Output 3) | Tải tham số GeoForraje ➔ Kiểm tra health BPS FastAPI ➔ **Chạy mô hình AI Sentinel-2 ước tính sinh khối đồng cỏ (`POST /api/v1/biomass`)** | 50 users |
| **16** | `rancher_request_cert` | Chủ trang trại (Rancher) | Danh sách trang trại ➔ Trạng thái chứng nhận ➔ **Nộp hồ sơ xin cấp chứng chỉ bò ăn cỏ (`POST /api/events/create`)** ➔ Xem chi tiết | 200 users |
| **17** | `admin_assign_inspector` | Quản trị FEDEGAN (Admin) | Danh sách tổ chức ➔ Danh sách thanh tra viên ➔ **Phân công thanh tra viên cho hồ sơ trang trại (`POST /api/fedegan/assign-inspector`)** | 50 users |
| **18** | `admin_clarification` | Quản trị FEDEGAN (Admin) | Danh sách hồ sơ cần xét duyệt ➔ Chi tiết tiêu chí ➔ **Gửi yêu cầu giải trình & bổ sung hồ sơ (`POST /api/fedegan/request-clarification`)** | 50 users |
| **19** | `rancher_member_manage` | Chủ trang trại (Rancher) | Danh sách công nhân nông trại ➔ **Mời / đăng ký nông dân phụ trách đồng cỏ (`POST /api/farmer/create`)** ➔ Kiểm tra thiết bị | 200 users |
| **20** | `slaughter_plant_network` | Nhà máy giết mổ / Chuỗi | Mạng lưới cơ sở liên kết ➔ Chi tiết lô mổ nguồn ➔ **Truy vết timeline chuyển dịch gia súc (`GET /api/animals/timeline`)** ➔ Xem hồ sơ DIN | 100 users |

---

## 🚀 Cách Thực Thi Kiểm Thử

### Cách 1: Chạy 20 Kịch Bản Thao Tác Theo Role Qua `run_test.sh`

```bash
# Xem danh sách và hướng dẫn đầy đủ
./run_test.sh help

# 1. Chạy kịch bản Thanh tra viên thẩm định & lập biên bản
./run_test.sh inspector_audit

# 2. Chạy kịch bản Lò mổ tiếp nhận & tạo lô mới
./run_test.sh slaughter_lote

# 3. Chạy kịch bản Chủ trại nộp đơn xin cấp chứng chỉ Grass Fed
./run_test.sh rancher_request_cert

# 4. Chạy kịch bản Quản trị viên phân công thanh tra viên
./run_test.sh admin_assign_inspector

# 5. Chạy kịch bản Quản trị viên yêu cầu giải trình hồ sơ
./run_test.sh admin_clarification

# 6. Chạy kịch bản Quản trị viên từ chối cấp chứng nhận không đạt
./run_test.sh admin_reject

# 7. Chạy kịch bản Chủ trại quản lý nhân sự & nông dân
./run_test.sh rancher_member_manage

# 8. Chạy kịch bản Mạng lưới chuỗi cung ứng & Timeline gia súc
./run_test.sh slaughter_plant_network

# Tùy biến số Users và thời gian chạy linh hoạt:
USERS=300 DURATION=300 ./run_test.sh rancher_request_cert
```

### Cách 2: Chạy Theo Nhóm Toàn Bộ Role (Role Aggregation)

```bash
./run_test.sh role_inspector       # Chạy đồng thời 3 kịch bản của Thanh tra viên (Kịch bản 1, 2, 3)
./run_test.sh role_slaughterhouse  # Chạy đồng thời 4 kịch bản của Lò mổ (Kịch bản 4, 5, 6, 20)
./run_test.sh role_rancher         # Chạy đồng thời 5 kịch bản của Chủ trại (Kịch bản 7, 8, 9, 16, 19)
./run_test.sh role_admin           # Chạy đồng thời 5 kịch bản của Quản trị viên (Kịch bản 10, 11, 13, 17, 18)
```

### Cách 3: Chạy Kịch Bản Tải Hệ Thống (System Load Shapes)

```bash
./run_test.sh baseline        # Baseline chuẩn 700 Users (Mục 6.1 doc.txt)
./run_test.sh peak            # Tải đỉnh 15.000 Users (Mục 6.2 doc.txt)
./run_test.sh stress          # Vượt đỉnh 25.000 Users đo phục hồi (Mục 6.3 doc.txt)
./run_test.sh spike           # Sốc tải đột biến (Flash Crowd)
./run_test.sh step            # Tăng bậc thang tuyến tính
./run_test.sh bottleneck      # Dò tìm điểm nghẽn 5 phút
./run_test.sh breakingpoint   # Tăng liên tục tìm Điểm gãy tự ngắt
./run_test.sh soak            # Ngâm tải dài hạn 1 giờ
./run_test.sh doublespike     # Sốc tải kép 2 đỉnh
./run_test.sh interactive     # Mở giao diện Web UI Locust tại http://0.0.0.0:8089
```

---

## 🛡️ Cơ Chế Tự Động Dọn Dẹp Dữ Liệu Rác (Auto Cleanup)

Trong các kịch bản tạo mới trang trại (`rancher_create`) hoặc đăng ký thiết bị (`register-device`):
1. Dữ liệu thử nghiệm được gắn mã định danh `STRESS*` và lưu trữ trong `core.state.CREATED_TEST_IDS`.
2. Khi dừng bài test (hoặc test hoàn tất), hook `on_test_stop_cleanup_leftovers` tự động kích hoạt **30 luồng song song** (`ThreadPoolExecutor`) để dọn sạch 100% dữ liệu thử nghiệm trong DB, không để lại bất kỳ dữ liệu rác nào.
