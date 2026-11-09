import uuid
import random
import datetime
# pyrefly: ignore [missing-import]
from locust import task, between
from core.base_user import BaseSatrepsUser
from core.auth import AUTH_TOKENS, create_traced_headers
from core.state import DYNAMIC_DATA, CLEANUP_LOCK, CREATED_TEST_IDS
# ==============================================================================
# PHÂN HỆ 2A: GRASS-FED CERTIFICATION - THANH TRA VIÊN (MỤC 5.2: 40% TỔNG TẢI)
# Profile: Inspector / Visitor
# ==============================================================================

class GrassFedInspectorUser(BaseSatrepsUser):
    """
    Phân hệ Chứng nhận Bò ăn cỏ - Thanh tra viên (Inspector / Visitor):
    Tỷ lệ khuyến nghị trong doc.txt: 40% tổng tải giao dịch.
    Nghiệp vụ: Tra cứu chứng chỉ, thẩm định hồ sơ, xem nhật ký kiểm tra trang trại.
    """
    weight = 4
    wait_time = between(1.5, 3.5)

    @task(3)
    def test_inspector_certification_status(self):
        """Xem danh sách thẩm định & Cập nhật ID chứng nhận thật vào dynamic pool"""
        token = AUTH_TOKENS.get("inspector")
        if not token:
            return

        headers = create_traced_headers(token)
        with self.client.get(
            "/api/certifications/get-status-by-inspector",
            headers=headers,
            name="[App 2: Grass-Fed Inspector] GET /api/certifications/get-status",
            catch_response=True,
        ) as res:
            if res.status_code == 200:
                res.success()
                try:
                    items = res.json().get("result", {}).get("items", [])
                    new_ids = [item["id"] for item in items if "id" in item]
                    if new_ids:
                        DYNAMIC_DATA["certs"] = list(set(DYNAMIC_DATA["certs"] + new_ids[:5]))
                except Exception:
                    pass
            elif res.status_code == 429:
                res.failure("Throttled (429)")

    @task(3)
    def test_certification_events(self):
        """Xem lịch sử sự kiện kiểm định chứng nhận"""
        token = AUTH_TOKENS.get("inspector")
        if not token:
            return

        cert_id = random.choice(DYNAMIC_DATA["certs"])
        headers = create_traced_headers(token)
        with self.client.get(
            f"/api/certifications/{cert_id}/events",
            headers=headers,
            name="[App 2: Grass-Fed Inspector] GET /api/certifications/:id/events",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 404]:
                res.success()
            elif res.status_code == 429:
                res.failure("Throttled (429)")
            elif res.status_code >= 500:
                res.failure(f"Inspector Events 500: {res.status_code}")

    @task(2)
    def test_public_certification_lookup(self):
        """Visitor tra cứu thông tin chứng nhận công khai"""
        cert_id = random.choice(DYNAMIC_DATA["certs"])
        headers = create_traced_headers()
        with self.client.get(
            f"/api/certifications/public-info/{cert_id}",
            headers=headers,
            name="[App 2: Grass-Fed Inspector] GET /api/certifications/public-info",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 404]:
                res.success()
            elif res.status_code == 429:
                res.failure("Throttled (429)")
            elif res.status_code >= 500:
                res.failure(f"Public Cert 500: {res.status_code}")

    @task(1)
    def test_inspector_organization(self):
        """Xem hồ sơ tổ chức thanh tra"""
        token = AUTH_TOKENS.get("inspector")
        if token:
            headers = create_traced_headers(token)
            self.client.get(
                "/api/organizations/get",
                headers=headers,
                name="[App 2: Grass-Fed Inspector] GET /api/organizations/get",
            )

    @task(1)
    def test_inspector_register_device(self):
        """
        Kịch bản GHI (POST): Đăng ký thiết bị nhận thông báo đẩy FCM (Mobile Inspector App).
        Dữ liệu rác (device_token) được ghi nhận và tự động xóa sạch khi DỪNG TEST.
        """
        token = AUTH_TOKENS.get("inspector")
        if not token:
            return

        headers = create_traced_headers(token)
        device_token = f"stress_fcm_insp_{uuid.uuid4().hex}"

        with self.client.post(
            "/api/notifications/register-device",
            json={"token": device_token, "platform": "android"},
            headers=headers,
            name="[App 2: Grass-Fed Inspector] POST /api/notifications/register-device",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 201]:
                res.success()
                with CLEANUP_LOCK:
                    CREATED_TEST_IDS["devices"].add(device_token)
            elif res.status_code == 429:
                res.failure("Register Device Throttled (429)")


    @task(2)
    def test_inspector_notifications_inbox(self):
        """[Mức 1] Tải danh sách thông báo hộp thư (Notification Inbox) của thanh tra viên"""
        token = AUTH_TOKENS.get("inspector")
        if not token:
            return

        headers = create_traced_headers(token)
        with self.client.get(
            "/api/notifications/get-by-user",
            headers=headers,
            name="[App 2: Grass-Fed Inspector] GET /api/notifications/get-by-user",
            catch_response=True,
        ) as res:
            if res.status_code == 200:
                res.success()
            elif res.status_code == 429:
                res.failure("Throttled (429)")

    @task(1)
    def test_inspector_create_event(self):
        """[Mức 2] Kịch bản GHI (POST): Thanh tra viên lập biên bản kiểm tra sự kiện trang trại"""
        token = AUTH_TOKENS.get("inspector")
        if not token or not DYNAMIC_DATA["ranches"]:
            return

        ranch_id = random.choice(DYNAMIC_DATA["ranches"])
        headers = create_traced_headers(token)
        event_payload = {
            "farmId": ranch_id,
            "type": "Certificate",
            "signature": f"sig_stress_{uuid.uuid4().hex[:8]}",
            "fingerprint": f"fp_stress_{uuid.uuid4().hex[:8]}",
            "extra": {"note": "Automated stress inspection check-in"},
        }
        with self.client.post(
            "/api/events/create",
            json=event_payload,
            headers=headers,
            name="[App 2: Grass-Fed Inspector] POST /api/events/create",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 201, 400]:
                res.success()
            elif res.status_code == 429:
                res.failure("Create Event Throttled (429)")

    @task(2)
    def test_inspector_get_schedules(self):
        """[Mức 1] Xem danh sách lịch hẹn kiểm định nông trại theo ngày (Inspection Calendar)"""
        token = AUTH_TOKENS.get("inspector")
        if not token:
            return

        headers = create_traced_headers(token)
        query_date = (datetime.date.today() + datetime.timedelta(days=random.randint(-3, 7))).strftime("%Y-%m-%d")
        with self.client.get(
            f"/api/schedule/get-schedules?date={query_date}",
            headers=headers,
            name="[App 2: Grass-Fed Inspector] GET /api/schedule/get-schedules",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 404]:
                res.success()
            elif res.status_code == 429:
                res.failure("Get Schedules Throttled (429)")
            elif res.status_code >= 500:
                res.failure(f"Get Schedules 500: {res.text[:100]}")

    @task(1)
    def test_inspector_set_schedule(self):
        """[Mức 2] Kịch bản GHI (POST): Tạo/Cập nhật lịch kiểm tra thực địa nông trại (Schedule Transaction)"""
        token = AUTH_TOKENS.get("inspector")
        candidate_ranches = (
            DYNAMIC_DATA.get("certified_assigned_ranches")
            or DYNAMIC_DATA.get("certified_ranches")
            or DYNAMIC_DATA.get("assigned_ranches")
            or DYNAMIC_DATA["ranches"]
        )
        if not token or not candidate_ranches:
            return

        ranch_id = random.choice(candidate_ranches)
        headers = create_traced_headers(token)
        # Đặt lịch sang NĂM SAU (Next Year) phân tán rộng rãi ngày và khung giờ để tránh xung đột
        next_year = datetime.date.today().year + 1
        random_day = random.randint(1, 360)
        target_date = (datetime.date(next_year, 1, 1) + datetime.timedelta(days=random_day)).strftime("%Y-%m-%d")
        start_hour = random.randint(7, 16)
        start_min = random.choice([0, 15, 30, 45])
        end_hour = start_hour + random.choice([1, 2])
        schedule_payload = {
            "ranchId": ranch_id,
            "fromDate": f"{start_hour:02d}:{start_min:02d}",
            "toDate": f"{end_hour:02d}:{start_min:02d}",
            "scheduledAt": target_date,
        }
        with self.client.post(
            "/api/schedule/set-schedules",
            json=schedule_payload,
            headers=headers,
            name="[App 2: Grass-Fed Inspector] POST /api/schedule/set-schedules",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 201, 400, 404, 409]:
                res.success()
            elif res.status_code == 429:
                res.failure("Set Schedule Throttled (429)")
            elif res.status_code >= 500:
                res.failure(f"Set Schedule 500: {res.text[:100]}")
