# 🚀 Hướng Dẫn Cài Đặt, Cấu Hình & Chạy Kiểm Thử Tải (Load Testing) Với Locust

Tài liệu này hướng dẫn chi tiết từ cài đặt, thiết lập môi trường, cấu trúc kịch bản kiểm thử, cách thực thi và phân tích kết quả load testing hệ thống **SATREPS** sử dụng **Locust (Python)**.

---

## 📑 Mục lục
1. [Giới thiệu về Locust](#1-giới-thiệu-về-locust)
2. [Yêu cầu môi trường & Cài đặt](#2-yêu-cầu-môi-trường--cài-đặt)
3. [Cấu trúc mã nguồn trong thư mục](#3-cấu-trúc-mã-nguồn-trong-thư-mục)
4. [Các cách chạy kiểm thử tải](#4-các-cách-chạy-kiểm-thử-tải)
   - [Chế độ 1: Giao diện trực quan (Web UI)](#chế-độ-1-giao-diện-trực-quan-web-ui)
   - [Chế độ 2: Dòng lệnh tự động (Headless Mode)](#chế-độ-2-dòng-lệnh-tự-động-headless-mode)
   - [Chế độ 3: Phân tán nhiều máy/worker (Distributed Load)](#chế-độ-3-phân-tán-nhiều-máyworker-distributed-load)
5. [Giải thích các thông số cấu hình](#5-giải-thích-các-thông-số-cấu-hình)
6. [Cấu trúc kịch bản Locustfile](#6-cấu-trúc-kịch-bản-locustfile)
7. [Cách đọc và phân tích báo cáo kết quả](#7-cách-đọc-và-phân-tích-báo-cáo-kết-quả)
8. [Các lỗi thường gặp & Cách khắc phục](#8-các-lỗi-thường-gặp--cách-khắc-phục)
9. [Kỹ thuật Bắt & Bắn Lỗi Chuyên Sâu (Error Handling, Alerting & Logging)](#9-kỹ-thuật-bắt--bắn-lỗi-chuyên-sâu-error-handling-alerting--logging)
   - [9.1. Bắt chi tiết Response Body lỗi ra Console/Log (catch_response)](#91-bắt-chi-tiết-response-body-lỗi-ra-consolelog-catch_response)
   - [9.2. Event Hook toàn cục: Tự động ghi toàn bộ lỗi ra file log](#92-event-hook-toàn-cục-tự-động-ghi-toàn-bộ-lỗi-ra-file-log)
   - [9.3. Bắn thông báo cảnh báo qua Telegram / Slack Webhook](#93-bắn-thông-báo-cảnh-báo-qua-telegram--slack-webhook)
   - [9.4. Tự động ngắt test sớm (Fail-Fast / Circuit Breaker)](#94-tự-động-ngắt-test-sớm-fail-fast--circuit-breaker)
   - [9.5. Bắn Exit Code thất bại cho CI/CD Pipeline & Xuất file CSV](#95-bắn-exit-code-thất-bại-cho-cicd-pipeline--xuất-file-csv)
10. [Các Kỹ Thuật Nâng Cao Sâu Hơn (Advanced Enterprise Patterns)](#10-các-kỹ-thuật-nâng-cao-sâu-hơn-advanced-enterprise-patterns)
   - [10.1. Mô hình tải bậc thang & Sốc tải (LoadTestShape)](#101-mô-hình-tải-bậc-thang--sốc-tải-loadtestshape)
   - [10.2. Chuỗi nghiệp vụ liên hoàn & Nối dữ liệu (SequentialTaskSet)](#102-chuỗi-nghiệp-vụ-liên-hoàn--nối-dữ-liệu-sequentialtaskset)
   - [10.3. Tăng tốc hiệu năng máy test gấp 5 lần (FastHttpUser)](#103-tăng-tốc-hiệu-năng-máy-test-gấp-5-lần-fasthttpuser)
   - [10.4. Gắn Trace ID (X-Request-ID) truy vết tận cùng Server Log](#104-gắn-trace-id-x-request-id-truy-vết-tận-cùng-server-log)
   - [10.5. Kỹ thuật Test API POST không làm rác Database](#105-kỹ-thuật-test-api-post-không-làm-rác-database)
   - [10.6. Cảnh báo sớm Rate Limit (Header Snooping)](#106-cảnh-báo-sớm-rate-limit-header-snooping)

---

## 1. Giới thiệu về Locust

[Locust](https://locust.io/) là một công cụ kiểm thử tải (Load & Performance Testing) mã nguồn mở viết hoàn toàn bằng Python:
* **Hỗ trợ Coroutine (`gevent`):** Có khả năng mô phỏng hàng nghìn người dùng đồng thời (Virtual Users) trên một máy tính thông thường mà tốn rất ít RAM/CPU.
* **Kịch bản bằng code Python chuẩn:** Dễ dàng viết logic phức tạp, xác thực JWT, sinh dữ liệu ngẫu nhiên, nối chuỗi gọi API (workflow).
* **Giao diện Web UI Real-time:** Theo dõi biểu đồ số lượng người dùng, RPS (Request per second), độ trễ (Latency P50, P90, P99) và tỷ lệ lỗi trực tiếp.
* **Hỗ trợ Headless & Xuất báo cáo:** Chạy tự động trong CI/CD pipeline và xuất file HTML/CSV.

---

## 2. Yêu cầu môi trường & Cài đặt

### Bước 2.1: Kiểm tra Python
Yêu cầu máy cài đặt **Python 3.8+** và công cụ quản lý gói **pip**.
```bash
python3 --version
pip3 --version
```

### Bước 2.2: Khởi tạo môi trường ảo (Khuyến nghị)
Nên tạo virtualenv riêng để tránh xung đột thư viện:
```bash
cd /media/vhec-dev/127C4DD37C4DB1F1/VHEC_Project/py

# Tạo môi trường ảo
python3 -m venv venv

# Kích hoạt môi trường ảo
# Trên Linux/macOS:
source venv/bin/activate
# Trên Windows:
# venv\Scripts\activate
```

### Bước 2.3: Cài đặt Locust và các thư viện phụ thuộc
Cài đặt Locust và `requests`:
```bash
pip install --upgrade pip
pip install locust requests
```

Tạo file `requirements.txt` để lưu cấu hình gói:
```txt
locust>=2.40.0
requests>=2.31.0
```
Sau đó có thể cài lại bất cứ lúc nào qua: `pip install -r requirements.txt`.

### Bước 2.4: Tối ưu hệ điều hành Linux (Bắt buộc khi test tải cao)
Mặc định hệ điều hành Linux giới hạn số lượng file socket mở cùng lúc (`ulimit` là 1024), khi chạy hơn 1000 users sẽ bị lỗi `Too many open files`.
Hãy nâng giới hạn trước khi chạy test:
```bash
ulimit -n 65535
```

---

## 3. Cấu trúc mã nguồn trong thư mục

Thư mục hiện tại chứa các kịch bản kiểm thử:

| Tên File | Chức năng chính |
| :--- | :--- |
| `locustfile_integrated.py` | 🌟 **Kịch bản chuẩn đặc tả FEDEGAN (`doc.txt`)**: Tích hợp đồng thời 4 ứng dụng trên cùng hạ tầng dùng chung: Manual Traceability (SQL-heavy), Grass-Fed Inspector (40%), Grass-Fed Slaughterhouse (30% với ràng buộc External API <= 20), Grass-Fed Rancher (30%), Output 2 (Animal Growth), và Output 3 (Geospatial Biomass GeoForraje + Python Analytical Model). Hỗ trợ các kịch bản chuẩn `SCENARIO=baseline`, `SCENARIO=peak`, `SCENARIO=stress`. |
| `locustfile_backend.py` | Kịch bản kiểm thử tải toàn diện **Backend API** (NestJS + PostgreSQL Cloud Run): login lấy token, tra cứu GIS, dòng đời gia súc (JOIN bảng nặng), quản lý lô hàng, kiểm định, rate limiting. |
| `locustfile.py` | Kịch bản kiểm thử cho **Web Client** (SvelteKit SSR): tự sinh session JWT cookie, kiểm tra trang chủ, trang tra cứu công khai, dashboard quản trị. |

---

## 4. Các cách chạy kiểm thử tải

### Chế độ 1: Giao diện trực quan (Web UI)
Phù hợp khi cần theo dõi biểu đồ trực tiếp, điều chỉnh số user linh hoạt theo thời gian thực.

**Lệnh chạy:**
```bash
# 🌟 Kịch bản chuẩn FEDEGAN tích hợp đồng thời 4 phân hệ (Khuyến nghị):
locust -f locustfile_integrated.py --host https://satreps-api-427991251928.us-central1.run.app

# Chạy kịch bản tự động theo các Scenario của FEDEGAN (Mục 6 doc.txt):
# 1. Kịch bản Baseline (Mục 6.1: ~700 users):
SCENARIO=baseline locust -f locustfile_integrated.py --host https://satreps-api-427991251928.us-central1.run.app --headless --html report_baseline.html

# 2. Kịch bản Load & Peak (Mục 6.2: Lũy tiến lên tải đỉnh 45.000 requests):
SCENARIO=peak locust -f locustfile_integrated.py --host https://satreps-api-427991251928.us-central1.run.app --headless --html report_peak.html

# 3. Kịch bản Stress & Recovery (Mục 6.3: Vượt đỉnh tìm breaking point và đo phục hồi):
SCENARIO=stress locust -f locustfile_integrated.py --host https://satreps-api-427991251928.us-central1.run.app --headless --html report_stress.html

# Test Backend API riêng lẻ:
locust -f locustfile_backend.py --host https://satreps-api-427991251928.us-central1.run.app

# Test Frontend Web riêng lẻ:
locust -f locustfile.py --host https://satreps-client-web-427991251928.us-central1.run.app
```

> **⚠️ LƯU Ý QUAN TRỌNG:** Giá trị `--host` chỉ có **MỘT** lần `https://`. Tránh gõ nhầm thành `https://https://...` gây lỗi DNS resolution.

Sau khi chạy lệnh:
1. Mở trình duyệt truy cập: `http://localhost:8089` (hoặc `http://0.0.0.0:8089`).
2. Điền các thông số:
   - **Number of users:** Tổng số user ảo tối đa (ví dụ: `200` hoặc `500`).
   - **Spawn rate:** Số user sinh ra mỗi giây (ramp-up, ví dụ: `5` hoặc `10`).
   - **Host:** Tự động lấy từ cờ `--host` hoặc điền lại nếu cần.
3. Bấm **Start swarming** để bắt đầu test.
4. Có thể tăng/giảm số user bất kỳ lúc nào hoặc bấm **Stop** để dừng.

---

### Chế độ 2: Dòng lệnh tự động (Headless Mode)
Dùng khi chạy tự động trên server CI/CD hoặc muốn xuất báo cáo HTML/CSV hoàn chỉnh mà không cần mở trình duyệt.

```bash
locust -f locustfile_backend.py \
  --host https://satreps-api-427991251928.us-central1.run.app \
  --headless \
  -u 300 \
  -r 10 \
  --run-time 3m \
  --html report_backend.html \
  --csv=result_backend
```

**Các tùy chọn sử dụng:**
* `--headless`: Bật chế độ không giao diện web.
* `-u 300`: Giả lập tối đa 300 virtual users.
* `-r 10`: Mỗi giây khởi tạo thêm 10 users cho đến khi đạt 300 users.
* `--run-time 3m`: Chạy liên tục trong 3 phút rồi tự động kết thúc.
* `--html report_backend.html`: Xuất báo cáo đồ thị trực quan ra file HTML.
* `--csv=result_backend`: Xuất số liệu thống kê chi tiết ra file CSV để vẽ đồ thị Excel/Grafana.

---

### Chế độ 3: Phân tán nhiều máy/worker (Distributed Load)
Khi cần test tải lớn (hàng chục ngàn users vượt quá khả năng 1 lõi CPU Python):

```bash
# Terminal 1: Khởi chạy Master node điều phối
locust -f locustfile_backend.py --master

# Terminal 2, 3, 4: Khởi chạy các Worker node sinh tải
locust -f locustfile_backend.py --worker --master-host=127.0.0.1
```

---

## 5. Giải thích các thông số cấu hình

| Tham số | Dạng rút gọn | Ý nghĩa | Ví dụ khuyến nghị |
| :--- | :--- | :--- | :--- |
| `--locustfile` | `-f` | Đường dẫn file kịch bản Python | `locustfile_backend.py` |
| `--host` | | Địa chỉ domain backend/frontend cần test | `https://satreps-api-xxx.run.app` |
| `--users` | `-u` | Số người dùng ảo chạy đồng thời cùng lúc | `100` -> `500` -> `1000` |
| `--spawn-rate` | `-r` | Tốc độ gia tăng số user mỗi giây | `5` đến `20` users/giây |
| `--run-time` | `-t` | Thời gian chạy kịch bản (s/m/h) | `2m` (2 phút), `10m` |
| `--headless` | | Chạy không cần Web UI qua dòng lệnh | Dùng trong CI/CD |
| `--html` | | Xuất file báo cáo giao diện HTML | `--html report.html` |
| `--csv` | | Tiền tố file CSV lưu log | `--csv=loadtest_results` |

---

## 6. Cấu trúc kịch bản Locustfile

Một kịch bản Locust tiêu chuẩn gồm các phần chính như sau:

```python
import random
from locust import HttpUser, task, between

class BackendApiUser(HttpUser):
    # Thời gian nghỉ ngẫu nhiên giữa các request của mỗi user ảo (từ 1.0 đến 2.5s)
    wait_time = between(1.0, 2.5)

    def on_start(self):
        """Hàm chạy 1 lần duy nhất khi User bắt đầu sinh ra (khởi tạo token, session)"""
        self.headers = {"Authorization": "Bearer <TOKEN>"}

    @task(3)
    def test_heavy_api(self):
        """
        @task(trọng số): Trọng số càng cao thì tỉ lệ thực thi càng lớn.
        Ví dụ: task(3) sẽ được gọi nhiều gấp 3 lần task(1).
        """
        # Sử dụng tham số name="..." để Locust gom nhóm các URL có biến động id
        self.client.get("/api/animals/timeline?din=170010008406013", name="GET /api/animals/timeline")

    @task(1)
    def test_health_check(self):
        self.client.get("/", name="GET / (Health Probe)")
```

### Các kỹ thuật tối ưu kịch bản:
1. **Gom nhóm Endpoint động (`name="..."`):**
   * Nếu URL có chứa path param thay đổi như `/api/certifications/uuid-1/events`, `/api/certifications/uuid-2/events`, cần đặt `name="GET /api/certifications/:id/events"`. Nếu không, báo cáo Locust sẽ bị phân mảnh thành hàng nghìn dòng riêng biệt.
2. **Bộ nhớ đệm Auth Token dùng chung (`fetch_tokens_once`):**
   * Trong [locustfile_backend.py](file:///media/vhec-dev/127C4DD37C4DB1F1/VHEC_Project/py/locustfile_backend.py), không đăng nhập lại trong mỗi request. Đăng nhập 1 lần duy nhất ở cấp module và tái sử dụng token cho toàn bộ user để không bị chặn bởi Rate Limiter (Throttler) của API login.

---

## 7. Cách đọc và phân tích báo cáo kết quả

Khi kết thúc bài kiểm thử, Locust sẽ in ra bảng tổng kết:

### 1. Bảng Request Statistics
* **# reqs:** Tổng số lượt request đã gửi đến endpoint đó.
* **# fails (%):** Số lượng và tỉ lệ request thất bại (mã trạng thái không phải 2xx/3xx).
* **Avg / Min / Max / Med (ms):** Thời gian phản hồi trung bình, nhỏ nhất, lớn nhất và trung vị (miligiây).
* **req/s (RPS):** Thông lượng máy chủ xử lý được trên mỗi giây.

### 2. Bảng Phân vị thời gian phản hồi (Percentiles)
* **50% (Median):** 50% người dùng nhận kết quả nhanh hơn hoặc bằng mốc thời gian này.
* **95% / 99%:** 95% hoặc 99% người dùng nhận kết quả trong khoảng này. Đây là chỉ số quan trọng nhất phản ánh trải nghiệm người dùng thực tế (SLA thông thường yêu cầu P95 < 2000ms).

### 3. Bảng Error Report (Báo cáo lỗi)
* **`HTTPError('429 Too Many Requests')`:** Hệ thống đã chạm ngưỡng bảo vệ Rate Limit (NestJS Throttler). Cần cân nhắc điều chỉnh policy rate limit nếu đây là traffic hợp lệ.
* **`HTTPError('500 Internal Server Error')`:** Xảy ra unhandled exception ở server (quá tải Connection Pool DB, crash process hoặc lỗi truy vấn SQL).
* **`HTTPError('504 Gateway Timeout')`:** Request mất quá nhiều thời gian xử lý khiến Load Balancer / Reverse Proxy ngắt kết nối.

---

## 8. Các lỗi thường gặp & Cách khắc phục

### ❌ Lỗi 1: `Temporary failure in name resolution` / `Failed to resolve 'https'`
* **Nguyên nhân:** Lệnh chạy bị gõ trùng giao thức: `--host https://https://...`.
* **Khắc phục:** Đảm bảo chỉ có một lần `https://`:
  ```bash
  --host https://satreps-api-427991251928.us-central1.run.app
  ```

### ❌ Lỗi 2: `Too many open files` / `OSError: [Errno 24]`
* **Nguyên nhân:** Giới hạn file descriptor mặc định của Linux quá thấp.
* **Khắc phục:** Chạy lệnh sau trong cùng terminal trước khi chạy Locust:
  ```bash
  ulimit -n 65535
  ```

### ❌ Lỗi 3: `Lỗi đăng nhập: Read timed out`
* **Nguyên nhân:** Server đang khởi động lạnh (Cold Start trên Cloud Run) hoặc timeout kết nối quá ngắn.
* **Khắc phục:** Tăng timeout trong hàm login của script từ `10` lên `30` giây (`timeout=30`).

### ❌ Lỗi 4: Xuất hiện hàng loạt lỗi HTTP 429
* **Nguyên nhân:** Backend NestJS bật `@nestjs/throttler` (ví dụ giới hạn 1500 request / 15 phút cho mỗi IP hoặc token).
* **Khắc phục:** Khi kiểm thử tải nội bộ, cần tạm thời nới lỏng cấu hình throttler trên backend hoặc test với rate ramp-up vừa phải (`-r 1` đến `-r 5`).

---

## 9. Kỹ thuật Bắt & Bắn Lỗi Chuyên Sâu (Error Handling, Alerting & Logging)

Mặc định khi gặp lỗi (ví dụ mã 500, 429, 404), Locust chỉ báo generic dạng:
```text
HTTPError('500 Server Error: Internal Server Error for url: /api/organizations/base-organizations')
```
Bạn sẽ **không biết** backend trả về message gì trong response body (do thiếu connection DB, hay validate fail, hay exception nào). Dưới đây là các cơ chế giúp bạn **"bắn" chi tiết lỗi ra** theo nhiều cấp độ:

---

### 9.1. Bắt chi tiết Response Body lỗi ra Console/Log (`catch_response`)

Dùng cú pháp `with self.client.get(..., catch_response=True) as response:` để can thiệp trực tiếp vào kết quả trả về:

```python
with self.client.get(
    "/api/organizations/base-organizations?type=inspectionorg",
    headers=self.inspector_headers,
    name="GET /api/organizations/base-organizations (Inspection Orgs)",
    catch_response=True
) as response:
    if response.status_code == 200:
        response.success()
    else:
        # Bắn chi tiết nội dung lỗi từ backend ra terminal
        error_detail = response.text[:200] # Lấy 200 ký tự đầu của response body
        print(f"\n[❌ LỖI {response.status_code}] URL: {response.url} -> Chi tiết: {error_detail}")
        
        # Đánh dấu thất bại và hiển thị nội dung lỗi tùy chỉnh trên bảng Locust Web UI
        response.failure(f"HTTP {response.status_code}: {error_detail}")
```

---

### 9.2. Event Hook toàn cục: Tự động ghi toàn bộ lỗi ra file log

Nếu bạn không muốn sửa từng `task` trong code, Locust cung cấp **Event Hook toàn cục (`events.request.add_listener`)**. Hook này sẽ tự động lắng nghe **mọi request** bị lỗi trên toàn bộ hệ thống và ghi ra file `failures.log`:

Thêm đoạn sau vào cuối file kịch bản (ví dụ `locustfile_backend.py`):

```python
import datetime
from locust import events

LOG_FILE = "failures.log"

@events.request.add_listener
def log_request_failure(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    """
    Tự động kích hoạt khi có request thất bại (status code >= 400 hoặc crash network)
    """
    if exception or (response and response.status_code >= 400):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = response.status_code if response else "NO_STATUS"
        body = response.text[:300] if response else str(exception)
        
        log_line = f"[{now}] | {request_type} {name} | Status: {status} | Latency: {response_time:.0f}ms | Response: {body}\n"
        
        # Ghi trực tiếp ra file failures.log
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line)
```

👉 Khi chạy test, bạn chỉ cần mở một terminal khác và theo dõi lỗi bắn ra theo thời gian thực:
```bash
tail -f failures.log
```

---

### 9.3. Bắn thông báo cảnh báo qua Telegram / Slack Webhook

Khi kiểm thử tải mà hệ thống server bị crash (lỗi 500 xuất hiện liên tục) hoặc khi kết thúc bài test có tỷ lệ lỗi vượt ngưỡng cho phép, ta có thể tự động **bắn cảnh báo về Telegram Bot** hoặc **Slack Webhook**:

```python
import requests
from locust import events

TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

def send_telegram_alert(message: str):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=5)
    except Exception as e:
        print(f"Không gửi được cảnh báo Telegram: {e}")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Khi bài test kết thúc, tổng hợp và bắn thông báo"""
    stats = environment.stats.total
    fail_ratio = stats.fail_ratio * 100
    
    msg = (
        f"🚨 [BÁO CÁO LOAD TEST SATREPS]\n"
        f"- Tổng số requests: {stats.num_requests}\n"
        f"- Thất bại: {stats.num_failures} ({fail_ratio:.2f}%)\n"
        f"- RPS trung bình: {stats.total_rps:.1f}\n"
        f"- Thời gian phản hồi P95: {stats.get_current_response_time_percentile(0.95)} ms"
    )
    
    if fail_ratio > 1.0: # Nếu tỷ lệ lỗi > 1%
        msg = f"⚠️ CẢNH BÁO: TỶ LỆ LỖI CAO!\n" + msg
        send_telegram_alert(msg)
```

---

### 9.4. Tự động ngắt test sớm (Fail-Fast / Circuit Breaker)

Nếu bạn không muốn tiếp tục bắn tải khi server đã bắt đầu sập (tránh làm tràn ổ cứng, crash DB, hoặc tốn chi phí Cloud Run):

```python
from locust import events

@events.request.add_listener
def check_circuit_breaker(environment, exception, response, **kwargs):
    """Nếu số lượng lỗi 500 vượt quá 50 lần -> Ngắt bài test ngay lập tức"""
    if response and response.status_code == 500:
        # Đếm số lỗi 500
        stats = environment.stats.total
        if stats.num_failures >= 50:
            print("\n🚨 [CIRCUIT BREAKER] Phát hiện quá nhiều lỗi 500 từ Server. Tự động dừng test để bảo vệ hệ thống!")
            environment.runner.quit()
```

---

### 9.5. Bắn Exit Code thất bại cho CI/CD Pipeline & Xuất file CSV

#### 1. Dùng cờ `--exit-code-on-error`:
Khi tích hợp vào GitHub Actions / GitLab CI, bạn muốn bài test tự động đánh dấu là **FAILED** (Exit code = 1) nếu có bất kỳ lỗi nào xảy ra:
```bash
locust -f locustfile_backend.py \
  --host https://satreps-api-427991251928.us-central1.run.app \
  --headless \
  -u 100 -r 10 --run-time 1m \
  --exit-code-on-error 1
```

#### 2. Xuất bảng tổng hợp các loại lỗi ra file CSV:
Thêm cờ `--csv=test_result`:
```bash
locust -f locustfile_backend.py --host https://... --headless -u 100 -r 10 --run-time 1m --csv=test_result
```
Lệnh trên sẽ tự động sinh ra file:
* `test_result_failures.csv`: Danh sách chi tiết tên endpoint bị lỗi, method, loại lỗi (429, 500, Timeout...) và số lần xuất hiện.
* `test_result_stats.csv`: Thống kê RPS và Latency.

---

## 10. Các Kỹ Thuật Nâng Cao Sâu Hơn (Advanced Enterprise Patterns)

Đây là những kỹ thuật chuyên sâu dùng trong môi trường doanh nghiệp để biến bài kiểm thử Locust thành một hệ thống phân tích hiệu năng toàn diện.

---

### 10.1. Mô hình tải bậc thang & Sốc tải (`LoadTestShape`)

Bình thường bạn chỉ tăng user tuyến tính (Linear Ramp-up). Tuy nhiên để **tìm chính xác điểm gãy (Breaking Point)** của Database PostgreSQL hoặc kiểm tra độ trễ Auto-scaling của Google Cloud Run, ta dùng lớp `LoadTestShape`.

Thêm lớp này vào kịch bản (Locust sẽ tự động nhận diện mà không cần cấu hình thêm trên UI):

```python
from locust import LoadTestShape

class StepLoadShape(LoadTestShape):
    """
    Kịch bản tải bậc thang:
    - 0 đến 60s  : Duy trì 50 users  (Làm nóng cache & connection pool)
    - 60 đến 120s : Tăng vọt lên 150 users (Kiểm tra tải trung bình)
    - 120 đến 180s: Đạt đỉnh 300 users (Tìm ngưỡng nghẽn DB)
    - Sau 180s   : Kết thúc bài test
    """
    stages = [
        {"duration": 60,  "users": 50,  "spawn_rate": 10},
        {"duration": 120, "users": 150, "spawn_rate": 20},
        {"duration": 180, "users": 300, "spawn_rate": 30},
    ]

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])
        return None  # Dừng test
```

---

### 10.2. Chuỗi nghiệp vụ liên hoàn & Nối dữ liệu (`SequentialTaskSet`)

Người dùng thật không bấm các nút một cách ngẫu nhiên. Họ đi theo **luồng quy trình (Workflow)** và dữ liệu của bước sau phụ thuộc vào bước trước (Dynamic Chaining):

```python
from locust import HttpUser, SequentialTaskSet, task

class SlaughterhouseWorkflow(SequentialTaskSet):
    """Quy trình tuần tự: Xem danh sách lô -> Chọn 1 lô có thật -> Xem chi tiết động vật trong lô đó"""

    @task
    def step_1_get_lotes(self):
        res = self.client.get(
            "/api/slaughterhouse/lote/get-list-by-slaughterhouse?pageNumber=1&pageSize=5",
            name="Step 1: Get Lotes List"
        )
        if res.status_code == 200:
            lotes = res.json().get("result", {}).get("items", [])
            # Trích xuất ID thật đang có trong Database
            if lotes:
                self.selected_lote_id = lotes[0].get("id")

    @task
    def step_2_get_lote_details(self):
        if hasattr(self, "selected_lote_id") and self.selected_lote_id:
            self.client.get(
                f"/api/slaughterhouse/lote/{self.selected_lote_id}/animals",
                name="Step 2: Get Animals in Lote (Chained ID)"
            )

class EnterpriseUser(HttpUser):
    tasks = [SlaughterhouseWorkflow]
```

---

### 10.3. Tăng tốc hiệu năng máy test gấp 5 lần (`FastHttpUser`)

Mặc định `HttpUser` sử dụng thư viện Python `requests` (viết bằng Python thuần). Khi mô phỏng trên **3,000 – 10,000 người dùng ảo**, CPU máy bạn sẽ bị quá tải (Client-side bottleneck) khiến kết quả đo đạc bị sai lệch.

**Giải pháp:** Đổi sang `FastHttpUser` (sử dụng `geventhttpclient` viết bằng C, tốc độ xử lý nhanh gấp 5 - 6 lần):

```python
# Thay vì: from locust import HttpUser
from locust.contrib.fasthttp import FastHttpUser

class UltraFastBackendUser(FastHttpUser):
    # Cú pháp gọi self.client.get/post hoàn toàn tương thích như cũ
    # Nhưng tiêu tốn cực ít RAM và CPU của máy chạy Locust!
    pass
```

---

### 10.4. Gắn Trace ID (`X-Request-ID`) truy vết tận cùng Server Log

Khi gặp lỗi (ví dụ 500 hoặc 429), việc biết lỗi xảy ra ở dòng code nào trên NestJS Cloud Run là rất quan trọng. Bằng cách gửi kèm mã `x-request-id` (UUID) trong mỗi request:

```python
import uuid

class TracedApiUser(HttpUser):
    def get_traced_headers(self):
        trace_id = str(uuid.uuid4())
        headers = {
            "Content-Type": "application/json",
            "x-request-id": trace_id,  # Trace ID chuẩn OpenTelemetry / Cloud Logging
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers, trace_id

    @task
    def test_traceable_api(self):
        headers, trace_id = self.get_traced_headers()
        with self.client.get("/api/animals/timeline", headers=headers, catch_response=True) as res:
            if res.status_code >= 400:
                print(f"[❌ LỖI] Trace-ID: {trace_id} | Status: {res.status_code} | Body: {res.text}")
                # Ghi trace_id này vào failures.log -> Copy sang Cloud Run log là tìm ra ngay dòng crash!
```

---

### 10.5. Kỹ thuật Test API POST không làm rác Database

Có 3 cách để test các API ghi dữ liệu (`POST`, `PUT`) mà không ô nhiễm database thật:

1. **Test các API POST bản chất là Search/Filter:**
   * Các endpoint nhận filter JSON nặng như `POST /api/animals/search` hoặc `POST /api/users/login`. Máy chủ phải mã hóa bcrypt hoặc chạy query SQL nặng nhưng **không insert thêm dòng nào**.
2. **Kỹ thuật Tạo & Xóa ngay lập tức (Create-Then-Delete):**
   * Trong 1 task: Gửi `POST` tạo bản ghi -> Lấy `id` trả về từ response -> Gửi `DELETE /api/.../{id}` để dọn dẹp ngay. Database chỉ tăng tạm thời trong vài giây rồi sạch sẽ trở lại.
3. **Kỹ thuật Cố tình gửi Payload sai (Validation Stress Test):**
   * Gửi payload vi phạm validation (thiếu trường bắt buộc, sai định dạng email/uuid).
   * Kiểm tra khả năng xử lý của `ValidationPipe` (class-validator tiêu tốn rất nhiều CPU) và bắt buộc server trả về `400 Bad Request`. Bọc `catch_response=True` để tính `400` là thành công!

---

### 10.6. Cảnh báo sớm Rate Limit (Header Snooping)

NestJS Throttler khi trả về response thường kèm các header:
* `X-RateLimit-Limit`: Tổng số lượt cho phép.
* `X-RateLimit-Remaining`: Số lượt còn lại trước khi bị chặn.
* `Retry-After`: Số giây phải đợi.

Locust có thể đọc các header này và ghi log cảnh báo trước khi server thực sự trả về mã `429`:

```python
with self.client.get("/api/animals/timeline", catch_response=True) as res:
    remaining = res.headers.get("x-ratelimit-remaining")
    if remaining and int(remaining) < 5:
        print(f"⚠️ [CẢNH BÁO SẮP CHẠM TRẦN] Endpoint {res.url} chỉ còn {remaining} requests!")
```
