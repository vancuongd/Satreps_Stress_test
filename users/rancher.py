import uuid
import random
# pyrefly: ignore [missing-import]
from locust import task, between
from core.base_user import BaseSatrepsUser
from core.auth import AUTH_TOKENS, create_traced_headers
from core.state import DYNAMIC_DATA, CLEANUP_LOCK, CREATED_TEST_IDS

# ==============================================================================
# PHÂN HỆ 2C: GRASS-FED CERTIFICATION - CHỦ TRẠI / NÔNG DÂN (MỤC 5.2: 30% TỔNG TẢI)
# Profile: Rancher (Farmer)
# ==============================================================================

class GrassFedRancherUser(BaseSatrepsUser):
    """
    Phân hệ Chứng nhận Bò ăn cỏ - Chủ trang trại (Rancher / Farmer):
    Tỷ lệ khuyến nghị trong doc.txt: 30% tổng tải giao dịch.
    Nghiệp vụ: Quản lý danh sách trang trại, xem tình trạng chứng nhận, thống kê đàn bò.
    """
    weight = 3
    wait_time = between(1.5, 3.5)

    @task(4)
    def test_rancher_farms_list(self):
        """Chủ trại xem danh sách trang trại và trạng thái chứng chỉ"""
        token = AUTH_TOKENS.get("rancher")
        if not token:
            return

        headers = create_traced_headers(token)
        with self.client.get(
            "/api/ranches/get-by-organization?page=1&length=5",
            headers=headers,
            name="[App 4: Grass-Fed Rancher] GET /api/ranches/get-by-organization",
            catch_response=True,
        ) as res:
            if res.status_code == 200:
                res.success()
                try:
                    data = res.json().get("result", [])
                    ranch_ids = [r["id"] for r in data if "id" in r]
                    if ranch_ids:
                        DYNAMIC_DATA["ranches"] = list(set(DYNAMIC_DATA["ranches"] + ranch_ids[:3]))
                except Exception:
                    pass

    @task(3)
    def test_rancher_farm_statistics(self):
        """Thống kê chứng nhận của chủ trang trại (Đã cấp / Chờ duyệt)"""
        token = AUTH_TOKENS.get("rancher")
        if token:
            headers = create_traced_headers(token)
            self.client.get(
                "/api/ranches/statistics",
                headers=headers,
                name="[App 4: Grass-Fed Rancher] GET /api/ranches/statistics",
            )

    @task(2)
    def test_rancher_review_certification_status(self):
        """Xem chi tiết hồ sơ chứng nhận bò ăn cỏ của trang trại"""
        cert_id = random.choice(DYNAMIC_DATA["certs"])
        headers = create_traced_headers(AUTH_TOKENS.get("rancher"))
        with self.client.get(
            f"/api/certifications/public-info/{cert_id}",
            headers=headers,
            name="[App 4: Grass-Fed Rancher] GET /api/certifications/public-info/:id",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 404]:
                res.success()
            elif res.status_code == 429:
                res.failure("Throttled (429)")
            elif res.status_code >= 500:
                res.failure(f"Rancher Cert 500: {res.status_code}")

    @task(1)
    def test_rancher_create_farm(self):
        """
        Kịch bản GHI (POST): Đăng ký trang trại thử nghiệm với mã định danh STRESS_*
        - Thực thi đầy đủ Database Write Transaction, Validation, Address và Location Mapping.
        - KHÔNG xóa ngay trong lúc test để phản ánh đúng hành vi người dùng thật và không làm biến dạng chỉ số đo.
        - Toàn bộ ranch ID được lưu vào CREATED_TEST_IDS và tự động DỌN DẸP SẠCH 100% KHI DỪNG TEST.
        """
        token = AUTH_TOKENS.get("rancher")
        if not token:
            return

        headers = create_traced_headers(token)
        test_uid = uuid.uuid4().hex[:10].upper()
        sit_code = f"STRESS{test_uid}"
        payload = {
            "name": f"Stress Test Ranch {test_uid}",
            "sitCode": sit_code,
            "personResponsible": "Locust Auto Tester",
            "address": "Calle 100 # 15-20, Bogota",
            "department": {"id": "25", "name": "ARAUCA"},
            "municipality": {"id": "1081", "name": "ARAUCA"},
            "productionSystem": "Grass-Fed",
            "email": f"stresstest_{test_uid.lower()}@fedegan.org.co",
        }

        with self.client.post(
            "/api/ranches/create",
            json=payload,
            headers=headers,
            name="[App 4: Grass-Fed Rancher] POST /api/ranches/create (Write Transaction)",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 201]:
                res.success()
                try:
                    ranch_id = res.json().get("result", {}).get("id")
                    if ranch_id:
                        with CLEANUP_LOCK:
                            CREATED_TEST_IDS["ranches"].add(ranch_id)
                except Exception:
                    pass
            elif res.status_code == 429:
                res.failure("Ranch Create Throttled (429)")
            elif res.status_code >= 500:
                res.failure(f"Ranch Create 500: {res.text[:100]}")

    @task(3)
    def test_rancher_get_farm_detail(self):
        """[Mức 1] Xem thông tin chi tiết một trang trại cụ thể"""
        token = AUTH_TOKENS.get("rancher")
        if not token or not DYNAMIC_DATA["ranches"]:
            return

        ranch_id = random.choice(DYNAMIC_DATA["ranches"])
        headers = create_traced_headers(token)
        with self.client.get(
            f"/api/ranches/get/{ranch_id}",
            headers=headers,
            name="[App 4: Grass-Fed Rancher] GET /api/ranches/get/:id",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 404]:
                res.success()
            elif res.status_code == 429:
                res.failure("Throttled (429)")
            elif res.status_code >= 500:
                res.failure(f"Ranch Detail 500: {res.status_code}")

    @task(2)
    def test_rancher_notifications_inbox(self):
        """[Mức 1] Tải danh sách thông báo hộp thư (Notification Inbox) của chủ trang trại"""
        token = AUTH_TOKENS.get("rancher")
        if not token:
            return

        headers = create_traced_headers(token)
        with self.client.get(
            "/api/notifications/get-by-user",
            headers=headers,
            name="[App 4: Grass-Fed Rancher] GET /api/notifications/get-by-user",
            catch_response=True,
        ) as res:
            if res.status_code == 200:
                res.success()
            elif res.status_code == 429:
                res.failure("Throttled (429)")

    @task(2)
    def test_rancher_farmers_list(self):
        """[Mức 2] Chủ trang trại xem danh sách nhân sự / nông dân thuộc tổ chức"""
        token = AUTH_TOKENS.get("rancher")
        if not token:
            return

        headers = create_traced_headers(token)
        with self.client.get(
            "/api/farmer/get-by-organization?page=1&length=10",
            headers=headers,
            name="[App 4: Grass-Fed Rancher] GET /api/farmer/get-by-organization",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 403]:
                # 403: Hợp lệ nếu user không thuộc tổ chức MultiRanchOrg_LEGAL
                res.success()
            elif res.status_code == 429:
                res.failure("Throttled (429)")

    @task(1)
    def test_rancher_save_geo_points(self):
        """[Mức 2] Kịch bản GHI (PUT): Lưu ranh giới không gian địa lý (GIS GeoPoints Polygon) của trang trại"""
        token = AUTH_TOKENS.get("rancher")
        if not token or not DYNAMIC_DATA["ranches"]:
            return

        ranch_id = random.choice(DYNAMIC_DATA["ranches"])
        headers = create_traced_headers(token)
        lat_base = round(random.uniform(8.30, 8.50), 6)
        lng_base = round(random.uniform(-75.90, -75.70), 6)
        geo_payload = {
            "ranchId": ranch_id,
            "geoPoints": [
                {"lat": lat_base, "lng": lng_base},
                {"lat": round(lat_base + 0.005, 6), "lng": round(lng_base + 0.002, 6)},
                {"lat": round(lat_base + 0.002, 6), "lng": round(lng_base + 0.008, 6)},
            ],
        }
        with self.client.put(
            "/api/ranches/save-geo-points",
            json=geo_payload,
            headers=headers,
            name="[App 4: Grass-Fed Rancher] PUT /api/ranches/save-geo-points (GIS Polygon)",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 201, 404]:
                res.success()
            elif res.status_code == 429:
                res.failure("Save Geo Points Throttled (429)")
            elif res.status_code >= 500:
                res.failure(f"Save Geo Points 500: {res.status_code}")

    @task(1)
    def test_rancher_register_device(self):
        """
        Kịch bản GHI (POST): Đăng ký thiết bị nhận thông báo của nông dân.
        Dữ liệu rác (device_token) được ghi nhận và tự động xóa sạch khi DỪNG TEST.
        """
        token = AUTH_TOKENS.get("rancher")
        if not token:
            return

        headers = create_traced_headers(token)
        device_token = f"stress_fcm_rancher_{uuid.uuid4().hex}"

        with self.client.post(
            "/api/notifications/register-device",
            json={"token": device_token, "platform": "android"},
            headers=headers,
            name="[App 4: Grass-Fed Rancher] POST /api/notifications/register-device",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 201]:
                res.success()
                with CLEANUP_LOCK:
                    CREATED_TEST_IDS["devices"].add(device_token)
            elif res.status_code == 429:
                res.failure("Rancher Register Device Throttled (429)")
