import time
import uuid
import random
import datetime
# pyrefly: ignore [missing-import]
from locust import task, between
from core.base_user import BaseSatrepsUser
from core.auth import AUTH_TOKENS, create_traced_headers
from core.state import DYNAMIC_DATA, CLEANUP_LOCK, CREATED_TEST_IDS, EXTERNAL_API_SEMAPHORE
from config.seed_data import SAMPLE_DINS, SLAUGHTERHOUSE_ORG_ID

# ==============================================================================
# PHÂN HỆ 2B: GRASS-FED CERTIFICATION - LÒ MỔ (MỤC 5.2: 30% TỔNG TẢI)
# Profile: Slaughterhouse (Ràng buộc: External API <= 20 users)
# ==============================================================================

class GrassFedSlaughterhouseUser(BaseSatrepsUser):
    """
    Phân hệ Chứng nhận Bò ăn cỏ - Nhà máy giết mổ (Slaughterhouse):
    Tỷ lệ khuyến nghị trong doc.txt: 30% tổng tải giao dịch.
    Nghiệp vụ: Quản lý lô gia súc, thống kê số lượng, nhật ký xử lý thịt.
    ⚠️ Ràng buộc nghiêm ngặt theo mục 5.2 & 6.1: Dịch vụ ngoài (External API)
    phải bị giới hạn tối đa <= 20 concurrent users và đo lường độc lập.
    """
    weight = 3
    wait_time = between(1.5, 3.5)

    @task(4)
    def test_slaughterhouse_lote_list(self):
        """Xem danh sách lô giết mổ"""
        token = AUTH_TOKENS.get("slaughterhouse")
        if not token:
            return

        headers = create_traced_headers(token)
        page = random.choice([1, 2])
        with self.client.get(
            f"/api/slaughterhouse/lote/get-list-by-slaughterhouse?org_id={SLAUGHTERHOUSE_ORG_ID}&pageNumber={page}&pageSize=10",
            headers=headers,
            name="[App 3: Grass-Fed Slaughterhouse] GET /api/lote/get-list",
            catch_response=True,
        ) as res:
            if res.status_code == 200:
                res.success()
                try:
                    items = res.json().get("result", {}).get("items", [])
                    new_lotes = [item["id"] for item in items if "id" in item]
                    if new_lotes:
                        DYNAMIC_DATA["lotes"] = list(set(DYNAMIC_DATA["lotes"] + new_lotes[:5]))
                except Exception:
                    pass

    @task(3)
    def test_slaughterhouse_lote_detail(self):
        """[Mức 1] Xem chi tiết lô giết mổ và danh sách gia súc trong lô (Heavy JOIN Query)"""
        token = AUTH_TOKENS.get("slaughterhouse")
        if not token or not DYNAMIC_DATA["lotes"]:
            return

        lote_id = random.choice(DYNAMIC_DATA["lotes"])
        headers = create_traced_headers(token)
        with self.client.get(
            f"/api/slaughterhouse/lote/detail?lote_id={lote_id}&org_id={SLAUGHTERHOUSE_ORG_ID}&pageNumber=1&pageSize=10",
            headers=headers,
            name="[App 3: Grass-Fed Slaughterhouse] GET /api/lote/detail",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 404]:
                res.success()
            elif res.status_code == 429:
                res.failure("Throttled (429)")
            elif res.status_code >= 500:
                res.failure(f"Lote Detail 500: {res.status_code}")

    @task(3)
    def test_slaughterhouse_statistics(self):
        """Thống kê tổng số gia súc xử lý tại lò mổ"""
        token = AUTH_TOKENS.get("slaughterhouse")
        if token:
            headers = create_traced_headers(token)
            self.client.get(
                f"/api/slaughterhouse/lote/statistics-animals?org_id={SLAUGHTERHOUSE_ORG_ID}",
                headers=headers,
                name="[App 3: Grass-Fed Slaughterhouse] GET /api/lote/statistics-animals",
            )

    @task(2)
    def test_slaughterhouse_animal_statistics_range(self):
        """Thống kê chi tiết động vật giết mổ theo dải ngày (Grass-fed ratio & Volume Analysis)"""
        token = AUTH_TOKENS.get("slaughterhouse")
        if not token:
            return

        headers = create_traced_headers(token)
        end_date = datetime.date.today().strftime("%Y-%m-%d")
        start_date = (datetime.date.today() - datetime.timedelta(days=random.randint(15, 60))).strftime("%Y-%m-%d")
        with self.client.get(
            f"/api/slaughterhouse/lote/statistics-animals?org_id={SLAUGHTERHOUSE_ORG_ID}&startDate={start_date}&endDate={end_date}",
            headers=headers,
            name="[App 3: Grass-Fed Slaughterhouse] GET /api/lote/statistics-animals (Date Range)",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 404]:
                res.success()
            elif res.status_code == 429:
                res.failure("Animal Stats Range Throttled (429)")
            elif res.status_code >= 500:
                res.failure(f"Animal Stats Range 500: {res.text[:100]}")

    @task(2)
    def test_slaughterhouse_logs(self):
        """Nhật ký vận hành lò mổ và cập nhật logId vào dynamic pool"""
        token = AUTH_TOKENS.get("slaughterhouse")
        if not token:
            return

        headers = create_traced_headers(token)
        with self.client.get(
            "/api/slaughterhouse/lote/logs",
            headers=headers,
            name="[App 3: Grass-Fed Slaughterhouse] GET /api/lote/logs",
            catch_response=True,
        ) as res:
            if res.status_code == 200:
                res.success()
                try:
                    items = res.json()
                    if isinstance(items, list):
                        ids = [item["id"] for item in items if "id" in item]
                        if ids:
                            DYNAMIC_DATA["lote_logs"] = list(set(DYNAMIC_DATA["lote_logs"] + ids[:5]))
                except Exception:
                    pass
            elif res.status_code == 429:
                res.failure("Throttled (429)")

    @task(2)
    def test_slaughterhouse_log_detail(self):
        """[Mức 2] Xem chi tiết log upload lô mổ và kết quả xử lý từng DIN"""
        token = AUTH_TOKENS.get("slaughterhouse")
        if not token or not DYNAMIC_DATA.get("lote_logs"):
            return

        log_id = random.choice(DYNAMIC_DATA["lote_logs"])
        headers = create_traced_headers(token)
        with self.client.get(
            f"/api/slaughterhouse/lote/logs/detail?logId={log_id}",
            headers=headers,
            name="[App 3: Grass-Fed Slaughterhouse] GET /api/lote/logs/detail",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 404]:
                res.success()
            elif res.status_code == 429:
                res.failure("Throttled (429)")

    @task(2)
    def test_slaughterhouse_notifications_inbox(self):
        """[Mức 1] Tải danh sách thông báo hộp thư (Notification Inbox) của lò mổ"""
        token = AUTH_TOKENS.get("slaughterhouse")
        if not token:
            return

        headers = create_traced_headers(token)
        with self.client.get(
            "/api/notifications/get-by-user",
            headers=headers,
            name="[App 3: Grass-Fed Slaughterhouse] GET /api/notifications/get-by-user",
            catch_response=True,
        ) as res:
            if res.status_code == 200:
                res.success()
            elif res.status_code == 429:
                res.failure("Throttled (429)")

    @task(1)
    def test_slaughterhouse_external_animal_check(self):
        """
        Dịch vụ tra cứu kiểm tra vật nuôi bên ngoài (External Animal Check API):
        - Theo mục 2.2 & 5.1 doc.txt: Giới hạn đồng thời <= 20 connections.
        - Giả lập (Mock) gọi dịch vụ ngoài với kết quả Thành Công (100% Success) 
          và thời gian trễ ~80-220ms mà không gửi request thật ra mạng ngoài.
        """
        acquired = EXTERNAL_API_SEMAPHORE.acquire(blocking=False)
        if not acquired:
            return

        try:
            start_time = time.time()
            # Giả lập thời gian phản hồi mạng của dịch vụ ngoài (80ms - 220ms)
            time.sleep(random.uniform(0.08, 0.22))
            total_time = (time.time() - start_time) * 1000

            # Ghi nhận giao dịch thành công vào báo cáo Locust
            self.environment.events.request.fire(
                request_type="EXTERNAL_MOCK",
                name="[App 3: Slaughterhouse External API] External Animal Check (<= 20 Mocked)",
                response_time=total_time,
                response_length=512,
                response=None,
                context={},
                exception=None,
            )
        finally:
            EXTERNAL_API_SEMAPHORE.release()

    @task(1)
    def test_slaughterhouse_add_lote(self):
        """[Mức 2] Kịch bản GHI (POST): Upload danh sách gia súc cho lô mổ mới"""
        token = AUTH_TOKENS.get("slaughterhouse")
        if not token:
            return

        headers = create_traced_headers(token)
        din_sample = random.choice(SAMPLE_DINS).replace(" ", "")
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payload = {
            "org_id": SLAUGHTERHOUSE_ORG_ID,
            "fileName": f"stress_import_{uuid.uuid4().hex[:6]}.xlsx",
            "animals": [
                {
                    "din": din_sample,
                    "hacienda": "HACIENDA STRESS TEST",
                    "fecha": now_str,
                    "ciudadProcedencia": "MONTERIA",
                    "tipoArete": "FDX",
                    "maquilador": "STRESS TEST S.A",
                }
            ],
        }
        with self.client.post(
            "/api/slaughterhouse/lote/add-list-by-slaughterhouse",
            json=payload,
            headers=headers,
            name="[App 3: Grass-Fed Slaughterhouse] POST /api/lote/add-list (Write Batch)",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 201, 400, 404]:
                res.success()
            elif res.status_code == 429:
                res.failure("Add Lote Throttled (429)")
            elif res.status_code >= 500:
                res.failure(f"Add Lote 500: {res.status_code}")

    @task(1)
    def test_slaughterhouse_register_device(self):
        """
        Kịch bản GHI (POST): Đăng ký thiết bị nhận thông báo lò mổ.
        Dữ liệu rác (device_token) được ghi nhận và tự động xóa sạch khi DỪNG TEST.
        """
        token = AUTH_TOKENS.get("slaughterhouse")
        if not token:
            return

        headers = create_traced_headers(token)
        device_token = f"stress_fcm_slaughter_{uuid.uuid4().hex}"

        with self.client.post(
            "/api/notifications/register-device",
            json={"token": device_token, "platform": "web"},
            headers=headers,
            name="[App 3: Grass-Fed Slaughterhouse] POST /api/notifications/register-device",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 201]:
                res.success()
                with CLEANUP_LOCK:
                    CREATED_TEST_IDS["devices"].add(device_token)
            elif res.status_code == 429:
                res.failure("Slaughterhouse Register Device Throttled (429)")
