"""
==============================================================================
20 KỊCH BẢN KIỂM THỬ THEO THAO TÁC NGƯỜI DÙNG TỪNG ROLE (SATREPS FEDEGAN)
Tuân thủ đầy đủ nghiệp vụ theo Đặc tả kỹ thuật Doc.txt (Mục 5 & Mục 6)
==============================================================================
Danh sách 20 Kịch bản thao tác phân bổ theo từng vai trò:
  • Nhóm Thanh tra viên (Inspector)      : Kịch bản 1, 2, 3
  • Nhóm Nhà máy giết mổ (Slaughterhouse): Kịch bản 4, 5, 6, 20
  • Nhóm Chủ trang trại (Rancher)        : Kịch bản 7, 8, 9, 16, 19
  • Nhóm Quản trị viên (FEDEGAN Admin)   : Kịch bản 10, 11, 13, 17, 18
  • Nhóm Truy xuất nguồn gốc             : Kịch bản 12
  • Nhóm Output 2: Sinh trưởng           : Kịch bản 14
  • Nhóm Output 3: Viễn thám AI          : Kịch bản 15
==============================================================================
"""

import time
import uuid
import random
import datetime
# pyrefly: ignore [missing-import]
from locust import SequentialTaskSet, task, between

from core.base_user import BaseSatrepsUser
from core.auth import AUTH_TOKENS, create_traced_headers
from core.state import (
    DYNAMIC_DATA,
    CLEANUP_LOCK,
    CREATED_TEST_IDS,
    EXTERNAL_API_SEMAPHORE,
)
from config.seed_data import SAMPLE_DINS, SLAUGHTERHOUSE_ORG_ID
from config.settings import BPS_BACKEND_HOST


# ==============================================================================
# NHÓM 1: ROLE THANH TRA VIÊN (INSPECTOR) - 3 KỊCH BẢN THAO TÁC
# ==============================================================================

class InspectorAuditFlow(SequentialTaskSet):
    """
    Kịch bản 1: Thanh tra viên thẩm định hồ sơ & Lập biên bản kiểm tra thực địa.
    Chuỗi thao tác:
      1. Xem danh sách hồ sơ chứng nhận chờ thẩm định
      2. Xem chi tiết hồ sơ chứng chỉ & checklist thẩm định
      3. Xem lịch sử các sự kiện kiểm định
      4. Lập biên bản sự kiện thực địa (POST /api/events/create)
    """
    @task
    def step1_get_certification_status(self):
        token = AUTH_TOKENS.get("inspector")
        if not token:
            return
        headers = create_traced_headers(token)
        with self.client.get(
            "/api/certifications/get-status-by-inspector",
            headers=headers,
            name="[Scenario 1: Inspector Audit] 1. GET /api/certifications/get-status",
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

    @task
    def step2_get_cert_details(self):
        token = AUTH_TOKENS.get("inspector")
        if not token or not DYNAMIC_DATA["certs"]:
            return
        cert_id = random.choice(DYNAMIC_DATA["certs"])
        headers = create_traced_headers(token)
        with self.client.get(
            f"/api/certifications/details?id={cert_id}",
            headers=headers,
            name="[Scenario 1: Inspector Audit] 2. GET /api/certifications/details",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 403, 404]:
                res.success()
            elif res.status_code >= 500:
                res.failure(f"Cert Detail 500: {res.status_code}")

    @task
    def step3_get_cert_events(self):
        token = AUTH_TOKENS.get("inspector")
        if not token or not DYNAMIC_DATA["certs"]:
            return
        cert_id = random.choice(DYNAMIC_DATA["certs"])
        headers = create_traced_headers(token)
        with self.client.get(
            f"/api/certifications/{cert_id}/events",
            headers=headers,
            name="[Scenario 1: Inspector Audit] 3. GET /api/certifications/:id/events",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 404]:
                res.success()
            elif res.status_code >= 500:
                res.failure(f"Inspector Events 500: {res.status_code}")

    @task
    def step4_create_inspection_event(self):
        token = AUTH_TOKENS.get("inspector")
        if not token or not DYNAMIC_DATA["ranches"]:
            return
        ranch_id = random.choice(DYNAMIC_DATA["ranches"])
        headers = create_traced_headers(token)
        event_payload = {
            "farmId": ranch_id,
            "type": "Certificate",
            "signature": f"sig_flow_{uuid.uuid4().hex[:8]}",
            "fingerprint": f"fp_flow_{uuid.uuid4().hex[:8]}",
            "extra": {"note": "Automated scenario 1 field audit inspection"},
        }
        with self.client.post(
            "/api/events/create",
            json=event_payload,
            headers=headers,
            name="[Scenario 1: Inspector Audit] 4. POST /api/events/create",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 201, 400]:
                res.success()
            elif res.status_code >= 500:
                res.failure(f"Create Event 500: {res.status_code}")


class InspectorScheduleFlow(SequentialTaskSet):
    """
    Kịch bản 2: Thanh tra viên quản lý và đặt lịch kiểm tra trang trại.
    Chuỗi thao tác chuẩn nghiệp vụ (Đảm bảo tính nhất quán dữ liệu trước - sau):
      1. Tải danh sách trang trại được phân công thẩm định (GET /api/ranches/get-by-organization)
      2. Tra cứu lịch hẹn kiểm định thực địa theo ngày (Calendar View)
      3. Thiết lập lịch hẹn kiểm tra trang trại với nông hộ (POST /api/schedule/set-schedules)
         -> Lấy ranchId từ danh sách trang trại đã có hồ sơ chứng nhận thẩm định (assigned/certified ranches)
      4. Đọc danh sách thông báo hộp thư inbox
    """
    @task
    def step1_fetch_assigned_ranches(self):
        token = AUTH_TOKENS.get("inspector")
        if not token:
            return
        headers = create_traced_headers(token)
        with self.client.get(
            "/api/ranches/get-by-organization?page=1&length=10",
            headers=headers,
            name="[Scenario 2: Inspector Schedule] 1. GET /api/ranches/get-by-organization",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 204]:
                res.success()
                try:
                    data = res.json().get("result", [])
                    items = data.get("items", []) if isinstance(data, dict) else data
                    if isinstance(items, list) and items:
                        assigned_ids = [item["id"] for item in items if item.get("id")]
                        if assigned_ids:
                            DYNAMIC_DATA["assigned_ranches"] = list(set(DYNAMIC_DATA.get("assigned_ranches", []) + assigned_ids))
                        # Lọc các trang trại đã có chứng nhận Grass-Fed để tương thích tuyệt đối với backend cũ (tránh lỗi null certId)
                        certified_assigned = [
                            item["id"] for item in items
                            if item.get("id") and item.get("certification")
                        ]
                        if certified_assigned:
                            DYNAMIC_DATA["certified_assigned_ranches"] = list(set(DYNAMIC_DATA.get("certified_assigned_ranches", []) + certified_assigned))
                except Exception:
                    pass

    @task
    def step2_view_schedules(self):
        token = AUTH_TOKENS.get("inspector")
        if not token:
            return
        headers = create_traced_headers(token)
        query_date = (datetime.date.today() + datetime.timedelta(days=random.randint(-2, 5))).strftime("%Y-%m-%d")
        with self.client.get(
            f"/api/schedule/get-schedules?date={query_date}",
            headers=headers,
            name="[Scenario 2: Inspector Schedule] 2. GET /api/schedule/get-schedules",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 404]:
                res.success()

    @task
    def step3_set_schedule(self):
        token = AUTH_TOKENS.get("inspector")
        # Ưu tiên trang trại đã có chứng nhận Grass-Fed để tương thích với backend cũ chưa deploy bản vá
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
        payload = {
            "ranchId": ranch_id,
            "fromDate": f"{start_hour:02d}:{start_min:02d}",
            "toDate": f"{end_hour:02d}:{start_min:02d}",
            "scheduledAt": target_date,
        }
        with self.client.post(
            "/api/schedule/set-schedules",
            json=payload,
            headers=headers,
            name="[Scenario 2: Inspector Schedule] 3. POST /api/schedule/set-schedules",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 201, 400, 404, 409]:
                res.success()
            elif res.status_code >= 500:
                res.failure(f"Set Schedule 500: {res.text[:100]}")

    @task
    def step4_check_inbox(self):
        token = AUTH_TOKENS.get("inspector")
        if not token:
            return
        headers = create_traced_headers(token)
        with self.client.get(
            "/api/notifications/get-by-user",
            headers=headers,
            name="[Scenario 2: Inspector Schedule] 4. GET /api/notifications/get-by-user",
            catch_response=True,
        ) as res:
            if res.status_code == 200:
                res.success()


class InspectorCertFlow(SequentialTaskSet):
    """
    Kịch bản 3: Thanh tra viên tra cứu hồ sơ và đồng bộ thông báo (Profile & Mobile Notifications).
    Chuỗi thao tác theo User Manual (Mục 3.4 & 3.5):
      1. Tra cứu thông tin hồ sơ thẩm định chứng nhận công khai
      2. Xem hồ sơ tổ chức thanh tra / đơn vị kiểm định trực thuộc (My Profile / Organization)
      3. Đăng ký nhận thông báo đẩy qua thiết bị di động (FCM token)
    """
    @task
    def step1_lookup_public_cert(self):
        cert_id = random.choice(DYNAMIC_DATA["certs"])
        headers = create_traced_headers()
        with self.client.get(
            f"/api/certifications/public-info/{cert_id}",
            headers=headers,
            name="[Scenario 3: Inspector Profile] 1. GET /api/certifications/public-info/:id",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 404]:
                res.success()

    @task
    def step2_view_organization_profile(self):
        token = AUTH_TOKENS.get("inspector")
        if not token:
            return
        headers = create_traced_headers(token)
        with self.client.get(
            "/api/organizations/get",
            headers=headers,
            name="[Scenario 3: Inspector Profile] 2. GET /api/organizations/get",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 404]:
                res.success()
            elif res.status_code == 429:
                res.failure("Throttled (429)")
            elif res.status_code >= 500:
                res.failure(f"Inspector Org 500: {res.status_code}")

    @task
    def step3_register_fcm_device(self):
        token = AUTH_TOKENS.get("inspector")
        if not token:
            return
        headers = create_traced_headers(token)
        device_token = f"stress_fcm_insp_sc3_{uuid.uuid4().hex}"
        with self.client.post(
            "/api/notifications/register-device",
            json={"token": device_token, "platform": "android"},
            headers=headers,
            name="[Scenario 3: Inspector Profile] 3. POST /api/notifications/register-device",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 201]:
                res.success()
                with CLEANUP_LOCK:
                    CREATED_TEST_IDS["devices"].add(device_token)


# ==============================================================================
# NHÓM 2: ROLE NHÀ MÁY GIẾT MỔ (SLAUGHTERHOUSE) - 3 KỊCH BẢN THAO TÁC
# ==============================================================================

class SlaughterLoteFlow(SequentialTaskSet):
    """
    Kịch bản 4: Nhà máy giết mổ tiếp nhận lô gia súc & Tạo mới lô mổ hàng loạt.
    Chuỗi thao tác:
      1. Đọc danh sách lô mổ hiện tại của nhà máy
      2. Tạo mới lô gia súc giết mổ với danh sách mã DIN (POST Batch Write)
    """
    @task
    def step1_get_lote_list(self):
        token = AUTH_TOKENS.get("slaughterhouse")
        if not token:
            return
        headers = create_traced_headers(token)
        with self.client.get(
            f"/api/slaughterhouse/lote/get-list-by-slaughterhouse?org_id={SLAUGHTERHOUSE_ORG_ID}&pageNumber=1&pageSize=10",
            headers=headers,
            name="[Scenario 4: Slaughter Lote Batch] 1. GET /api/lote/get-list",
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

    @task
    def step2_add_new_lote(self):
        token = AUTH_TOKENS.get("slaughterhouse")
        if not token:
            return
        headers = create_traced_headers(token)
        din_sample = random.choice(SAMPLE_DINS).replace(" ", "")
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payload = {
            "org_id": SLAUGHTERHOUSE_ORG_ID,
            "fileName": f"scenario4_batch_{uuid.uuid4().hex[:6]}.xlsx",
            "animals": [
                {
                    "din": din_sample,
                    "hacienda": "HACIENDA SCENARIO 4",
                    "fecha": now_str,
                    "ciudadProcedencia": "MONTERIA",
                    "tipoArete": "FDX",
                    "maquilador": "FRIGORIFICO CARIBE",
                }
            ],
        }
        with self.client.post(
            "/api/slaughterhouse/lote/add-list-by-slaughterhouse",
            json=payload,
            headers=headers,
            name="[Scenario 4: Slaughter Lote Batch] 2. POST /api/lote/add-list",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 201, 400, 404]:
                res.success()


class SlaughterAuditFlow(SequentialTaskSet):
    """
    Kịch bản 5: Giám sát chi tiết lô mổ & Thẩm định nhật ký quét mã barcode.
    Chuỗi thao tác:
      1. Xem chi tiết thông tin lô mổ và danh sách vật nuôi trong lô (Heavy SQL JOIN)
      2. Tra cứu danh sách nhật ký xử lý lô mổ (Logs)
      3. Tra cứu chi tiết kết quả quét mã từng con bò trong log (Detail Log)
    """
    @task
    def step1_view_lote_detail(self):
        token = AUTH_TOKENS.get("slaughterhouse")
        if not token or not DYNAMIC_DATA["lotes"]:
            return
        lote_id = random.choice(DYNAMIC_DATA["lotes"])
        headers = create_traced_headers(token)
        with self.client.get(
            f"/api/slaughterhouse/lote/detail?lote_id={lote_id}&org_id={SLAUGHTERHOUSE_ORG_ID}&pageNumber=1&pageSize=10",
            headers=headers,
            name="[Scenario 5: Slaughter Audit] 1. GET /api/lote/detail",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 404]:
                res.success()

    @task
    def step2_view_logs(self):
        token = AUTH_TOKENS.get("slaughterhouse")
        if not token:
            return
        headers = create_traced_headers(token)
        with self.client.get(
            "/api/slaughterhouse/lote/logs",
            headers=headers,
            name="[Scenario 5: Slaughter Audit] 2. GET /api/lote/logs",
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

    @task
    def step3_view_log_detail(self):
        token = AUTH_TOKENS.get("slaughterhouse")
        if not token or not DYNAMIC_DATA["lote_logs"]:
            return
        log_id = random.choice(DYNAMIC_DATA["lote_logs"])
        headers = create_traced_headers(token)
        with self.client.get(
            f"/api/slaughterhouse/lote/logs/detail?logId={log_id}",
            headers=headers,
            name="[Scenario 5: Slaughter Audit] 3. GET /api/lote/logs/detail",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 404]:
                res.success()


class SlaughterExternalFlow(SequentialTaskSet):
    """
    Kịch bản 6: Thống kê động vật & Gọi dịch vụ xác thực ngoài (External API <= 20).
    Chuỗi thao tác:
      1. Thống kê tổng số gia súc xử lý tại lò mổ
      2. Thống kê chi tiết theo dải ngày (Grass-Fed Ratio)
      3. Gọi dịch vụ tra cứu ngoài (External Information Service với Semaphore <= 20)
    """
    @task
    def step1_total_stats(self):
        token = AUTH_TOKENS.get("slaughterhouse")
        if not token:
            return
        headers = create_traced_headers(token)
        with self.client.get(
            f"/api/slaughterhouse/lote/statistics-animals?org_id={SLAUGHTERHOUSE_ORG_ID}",
            headers=headers,
            name="[Scenario 6: Slaughter External] 1. GET /api/lote/statistics-animals",
            catch_response=True,
        ) as res:
            if res.status_code == 200:
                res.success()

    @task
    def step2_range_stats(self):
        token = AUTH_TOKENS.get("slaughterhouse")
        if not token:
            return
        headers = create_traced_headers(token)
        end_date = datetime.date.today().strftime("%Y-%m-%d")
        start_date = (datetime.date.today() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
        with self.client.get(
            f"/api/slaughterhouse/lote/statistics-animals?org_id={SLAUGHTERHOUSE_ORG_ID}&startDate={start_date}&endDate={end_date}",
            headers=headers,
            name="[Scenario 6: Slaughter External] 2. GET /api/lote/statistics-animals (Range)",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 404]:
                res.success()

    @task
    def step3_call_external_service(self):
        acquired = EXTERNAL_API_SEMAPHORE.acquire(blocking=False)
        if not acquired:
            return
        try:
            start_time = time.time()
            time.sleep(random.uniform(0.08, 0.20))
            total_time = (time.time() - start_time) * 1000
            self.user.environment.events.request.fire(
                request_type="EXTERNAL_MOCK",
                name="[Scenario 6: Slaughter External] 3. External Animal Check (<=20 Mocked)",
                response_time=total_time,
                response_length=512,
                response=None,
                context={},
                exception=None,
            )
        finally:
            EXTERNAL_API_SEMAPHORE.release()


# ==============================================================================
# NHÓM 3: ROLE CHỦ TRANG TRẠI (RANCHER / FARMER) - 3 KỊCH BẢN THAO TÁC
# ==============================================================================

class RancherManageFlow(SequentialTaskSet):
    """
    Kịch bản 7: Chủ trang trại quản lý nông trại, xem chứng nhận & nhân sự.
    Chuỗi thao tác:
      1. Xem danh sách trang trại của tổ chức
      2. Xem thông tin chi tiết một trang trại
      3. Xem thống kê chứng nhận của chủ trang trại
      4. Xem danh sách nông dân / nhân sự trực thuộc
    """
    @task
    def step1_farms_list(self):
        token = AUTH_TOKENS.get("rancher")
        if not token:
            return
        headers = create_traced_headers(token)
        with self.client.get(
            "/api/ranches/get-by-organization?page=1&length=5",
            headers=headers,
            name="[Scenario 7: Rancher Manage] 1. GET /api/ranches/get-by-organization",
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

    @task
    def step2_farm_detail(self):
        token = AUTH_TOKENS.get("rancher")
        if not token or not DYNAMIC_DATA["ranches"]:
            return
        ranch_id = random.choice(DYNAMIC_DATA["ranches"])
        headers = create_traced_headers(token)
        with self.client.get(
            f"/api/ranches/get/{ranch_id}",
            headers=headers,
            name="[Scenario 7: Rancher Manage] 2. GET /api/ranches/get/:id",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 404]:
                res.success()

    @task
    def step3_farm_statistics(self):
        token = AUTH_TOKENS.get("rancher")
        if not token:
            return
        headers = create_traced_headers(token)
        with self.client.get(
            "/api/ranches/statistics",
            headers=headers,
            name="[Scenario 7: Rancher Manage] 3. GET /api/ranches/statistics",
            catch_response=True,
        ) as res:
            if res.status_code == 200:
                res.success()

    @task
    def step4_farmers_list(self):
        token = AUTH_TOKENS.get("rancher")
        if not token:
            return
        headers = create_traced_headers(token)
        with self.client.get(
            "/api/farmer/get-by-organization?page=1&length=10",
            headers=headers,
            name="[Scenario 7: Rancher Manage] 4. GET /api/farmer/get-by-organization",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 403]:
                res.success()


class RancherCreateFlow(SequentialTaskSet):
    """
    Kịch bản 8: Chủ trang trại đăng ký mới trang trại (Ghi dữ liệu & Auto Cleanup).
    Chuỗi thao tác:
      1. Đăng ký trang trại thử nghiệm mới với mã STRESS_*
      2. Đăng ký thiết bị nhận thông báo đẩy cho trang trại
    """
    @task
    def step1_create_farm(self):
        token = AUTH_TOKENS.get("rancher")
        if not token:
            return
        headers = create_traced_headers(token)
        test_uid = uuid.uuid4().hex[:10].upper()
        payload = {
            "name": f"Stress Scenario8 Farm {test_uid}",
            "sitCode": f"STRESS{test_uid}",
            "personResponsible": "Locust Scenario 8 Tester",
            "address": "Kilometro 5, Monteria, Cordoba",
            "department": {"id": "23", "name": "CORDOBA"},
            "municipality": {"id": "1001", "name": "MONTERIA"},
            "productionSystem": "Grass-Fed",
            "email": f"scenario8_{test_uid.lower()}@fedegan.org.co",
        }
        with self.client.post(
            "/api/ranches/create",
            json=payload,
            headers=headers,
            name="[Scenario 8: Rancher Create] 1. POST /api/ranches/create",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 201, 409]:
                res.success()
                try:
                    ranch_id = res.json().get("result", {}).get("id")
                    if ranch_id:
                        with CLEANUP_LOCK:
                            CREATED_TEST_IDS["ranches"].add(ranch_id)
                except Exception:
                    pass

    @task
    def step2_register_device(self):
        token = AUTH_TOKENS.get("rancher")
        if not token:
            return
        headers = create_traced_headers(token)
        device_token = f"stress_fcm_ranch_sc8_{uuid.uuid4().hex}"
        with self.client.post(
            "/api/notifications/register-device",
            json={"token": device_token, "platform": "android"},
            headers=headers,
            name="[Scenario 8: Rancher Create] 2. POST /api/notifications/register-device",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 201]:
                res.success()
                with CLEANUP_LOCK:
                    CREATED_TEST_IDS["devices"].add(device_token)


class RancherGisFlow(SequentialTaskSet):
    """
    Kịch bản 9: Cập nhật ranh giới bản đồ GIS đồng cỏ (GIS Polygon Mapping).
    Chuỗi thao tác:
      1. Xem danh sách trang trại của chủ trại
      2. Cập nhật tọa độ polygon ranh giới đồng cỏ (PUT /api/ranches/save-geo-points)
      3. Kiểm tra thông báo hộp thư inbox
    """
    @task
    def step1_select_farm(self):
        token = AUTH_TOKENS.get("rancher")
        if not token:
            return
        headers = create_traced_headers(token)
        with self.client.get(
            "/api/ranches/get-by-organization?page=1&length=5",
            headers=headers,
            name="[Scenario 9: Rancher GIS] 1. GET /api/ranches/get-by-organization",
            catch_response=True,
        ) as res:
            if res.status_code == 200:
                res.success()

    @task
    def step2_save_geo_polygon(self):
        token = AUTH_TOKENS.get("rancher")
        if not token or not DYNAMIC_DATA["ranches"]:
            return
        ranch_id = random.choice(DYNAMIC_DATA["ranches"])
        headers = create_traced_headers(token)
        lat_base = round(random.uniform(8.35, 8.45), 6)
        lng_base = round(random.uniform(-75.85, -75.75), 6)
        geo_payload = {
            "ranchId": ranch_id,
            "geoPoints": [
                {"lat": lat_base, "lng": lng_base},
                {"lat": round(lat_base + 0.004, 6), "lng": round(lng_base + 0.003, 6)},
                {"lat": round(lat_base + 0.001, 6), "lng": round(lng_base + 0.006, 6)},
            ],
        }
        with self.client.put(
            "/api/ranches/save-geo-points",
            json=geo_payload,
            headers=headers,
            name="[Scenario 9: Rancher GIS] 2. PUT /api/ranches/save-geo-points (GIS)",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 201, 404]:
                res.success()

    @task
    def step3_check_inbox(self):
        token = AUTH_TOKENS.get("rancher")
        if not token:
            return
        headers = create_traced_headers(token)
        with self.client.get(
            "/api/notifications/get-by-user",
            headers=headers,
            name="[Scenario 9: Rancher GIS] 3. GET /api/notifications/get-by-user",
            catch_response=True,
        ) as res:
            if res.status_code == 200:
                res.success()


# ==============================================================================
# NHÓM 4: ROLE QUẢN TRỊ VIÊN FEDEGAN (CENTRAL ADMIN) - 2 KỊCH BẢN THAO TÁC
# ==============================================================================

class AdminDashboardFlow(SequentialTaskSet):
    """
    Kịch bản 10: Quản trị viên FEDEGAN theo dõi Dashboard điều hành & Quản lý user.
    Chuỗi thao tác:
      1. Dashboard thống kê chứng chỉ toàn quốc theo trạng thái
      2. Dashboard thống kê tổng quan người dùng toàn hệ sinh thái
      3. Tra cứu và phân trang danh sách người dùng hệ thống
    """
    @task
    def step1_cert_stats(self):
        token = AUTH_TOKENS.get("admin") or AUTH_TOKENS.get("inspector")
        if not token:
            return
        headers = create_traced_headers(token)
        with self.client.get(
            "/api/fedegan/certifications/statistics",
            headers=headers,
            name="[Scenario 10: Admin Dashboard] 1. GET /api/fedegan/certifications/statistics",
            catch_response=True,
        ) as res:
            if res.status_code == 200:
                res.success()

    @task
    def step2_user_stats(self):
        token = AUTH_TOKENS.get("admin") or AUTH_TOKENS.get("inspector")
        if not token:
            return
        headers = create_traced_headers(token)
        with self.client.get(
            "/api/fedegan/users/statistics",
            headers=headers,
            name="[Scenario 10: Admin Dashboard] 2. GET /api/fedegan/users/statistics",
            catch_response=True,
        ) as res:
            if res.status_code == 200:
                res.success()

    @task
    def step3_users_list(self):
        token = AUTH_TOKENS.get("admin") or AUTH_TOKENS.get("inspector")
        if not token:
            return
        headers = create_traced_headers(token)
        page = random.choice([1, 2])
        with self.client.get(
            f"/api/fedegan/users/list?page={page}&length=10&type=INSPECTOR",
            headers=headers,
            name="[Scenario 10: Admin Dashboard] 3. GET /api/fedegan/users/list",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 404]:
                res.success()
            elif res.status_code >= 500:
                res.failure(f"Users List 500: {res.status_code}")


class AdminApprovalFlow(SequentialTaskSet):
    """
    Kịch bản 11: Thẩm định chi tiết hồ sơ & Phê duyệt cấp chứng nhận bò ăn cỏ.
    Chuỗi thao tác:
      1. Xem chi tiết hồ sơ thẩm định và checklist đánh giá chứng nhận
      2. Phê duyệt hồ sơ chứng chỉ (POST /api/fedegan/approve-certification)
    """
    @task
    def step1_review_details(self):
        token = AUTH_TOKENS.get("admin") or AUTH_TOKENS.get("inspector")
        if not token or not DYNAMIC_DATA["certs"]:
            return
        cert_id = random.choice(DYNAMIC_DATA["certs"])
        headers = create_traced_headers(token)
        with self.client.get(
            f"/api/certifications/details?id={cert_id}",
            headers=headers,
            name="[Scenario 11: Admin Approval] 1. GET /api/certifications/details",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 403, 404]:
                res.success()

    @task
    def step2_approve_certification(self):
        token = AUTH_TOKENS.get("admin") or AUTH_TOKENS.get("inspector")
        if not token or not DYNAMIC_DATA["certs"]:
            return
        cert_id = random.choice(DYNAMIC_DATA["certs"])
        headers = create_traced_headers(token)
        with self.client.post(
            "/api/fedegan/approve-certification",
            json={"certificationId": cert_id},
            headers=headers,
            name="[Scenario 11: Admin Approval] 2. POST /api/fedegan/approve-certification",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 201, 400, 404]:
                res.success()


# ==============================================================================
# NHÓM 5: ROLE TRUY XUẤT NGUỒN GỐC (MANUAL TRACEABILITY) - 1 KỊCH BẢN THAO TÁC
# ==============================================================================

class TraceabilityTimelineFlow(SequentialTaskSet):
    """
    Kịch bản 12: Truy vấn dòng đời gia súc & Chịu tải SQL nặng (Heavy JOIN 4 bảng).
    Chuỗi thao tác:
      1. Xác thực đăng nhập hệ thống truy xuất (POST /api/users/login)
      2. Tra cứu timeline dòng đời gia súc theo mã thẻ tai DIN chuẩn (Heavy JOIN)
      3. Tra cứu mã thẻ tai dạng thô không có khoảng trắng
      4. Đọc cấu hình hệ thống web
    """
    @task
    def step1_auth_verification(self):
        headers = create_traced_headers()
        with self.client.post(
            "/api/users/login",
            json={"email": "certicol.andes@colmail.com"},
            headers=headers,
            name="[Scenario 12: Traceability] 1. POST /api/users/login (Auth Verification)",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 201]:
                res.success()

    @task
    def step2_timeline_heavy_join(self):
        din = random.choice(SAMPLE_DINS)
        headers = create_traced_headers()
        with self.client.get(
            f"/api/animals/timeline?din={din}",
            headers=headers,
            name="[Scenario 12: Traceability] 2. GET /api/animals/timeline (Heavy JOIN)",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 404]:
                res.success()
            elif res.status_code >= 500:
                res.failure(f"Timeline DB Error: {res.status_code}")

    @task
    def step3_unformatted_din_search(self):
        din = random.choice(SAMPLE_DINS).replace(" ", "")
        headers = create_traced_headers()
        with self.client.get(
            f"/api/animals/timeline?din={din}",
            headers=headers,
            name="[Scenario 12: Traceability] 3. GET /api/animals/timeline (Unformatted DIN)",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 404]:
                res.success()

    @task
    def step4_system_configs(self):
        headers = create_traced_headers()
        with self.client.get(
            "/api/system-configs?target=web",
            headers=headers,
            name="[Scenario 12: Traceability] 4. GET /api/system-configs?target=web",
            catch_response=True,
        ) as res:
            if res.status_code == 200:
                res.success()


# ==============================================================================
# NHÓM 6: QUẢN TRỊ VIÊN FEDEGAN (TỪ CHỐI CẤP CHỨNG CHỈ) - KỊCH BẢN 13
# Theo Mục 3.2.5 trong SATREPS - APPLICATION USER MANUAL (ADMIN ROLE).docx
# ==============================================================================

class AdminRejectFlow(SequentialTaskSet):
    """
    Kịch bản 13: Quản trị viên FEDEGAN thẩm định & Từ chối cấp chứng chỉ (Reject Certification).
    Theo Mục 3.2.5 trong SATREPS - APPLICATION USER MANUAL (ADMIN ROLE).docx
    Chuỗi thao tác:
      1. Đọc chi tiết hồ sơ chứng chỉ & biên bản không đạt chuẩn (GET /api/certifications/details)
      2. Ra quyết định từ chối cấp chứng chỉ kèm lý do cụ thể (POST /api/fedegan/reject-certification)
      3. Tra cứu lịch sử dòng sự kiện của hồ sơ để xác nhận trạng thái Rejected (GET /api/certifications/:id/events)
    """
    @task
    def step1_view_noncompliant_cert_details(self):
        token = AUTH_TOKENS.get("admin") or AUTH_TOKENS.get("inspector")
        if not token or not DYNAMIC_DATA["certs"]:
            return
        cert_id = random.choice(DYNAMIC_DATA["certs"])
        headers = create_traced_headers(token)
        with self.client.get(
            f"/api/certifications/details?id={cert_id}",
            headers=headers,
            name="[Scenario 13: Admin Reject] 1. GET /api/certifications/details",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 403, 404]:
                res.success()
            elif res.status_code >= 500:
                res.failure(f"Cert Detail 500: {res.status_code}")

    @task
    def step2_reject_certification(self):
        token = AUTH_TOKENS.get("admin") or AUTH_TOKENS.get("inspector")
        if not token or not DYNAMIC_DATA["certs"]:
            return
        cert_id = random.choice(DYNAMIC_DATA["certs"])
        headers = create_traced_headers(token)
        payload = {
            "certificationId": cert_id,
            "reason": "Ho so khong dat tieu chuan chan tha bo an co tu nhien theo quy dinh cua Fedegan.",
        }
        with self.client.post(
            "/api/fedegan/reject-certification",
            json=payload,
            headers=headers,
            name="[Scenario 13: Admin Reject] 2. POST /api/fedegan/reject-certification",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 201, 400, 404]:
                res.success()
            elif res.status_code >= 500:
                res.failure(f"Reject Cert 500: {res.status_code}")

    @task
    def step3_verify_rejected_events(self):
        token = AUTH_TOKENS.get("admin") or AUTH_TOKENS.get("inspector")
        if not token or not DYNAMIC_DATA["certs"]:
            return
        cert_id = random.choice(DYNAMIC_DATA["certs"])
        headers = create_traced_headers(token)
        with self.client.get(
            f"/api/certifications/{cert_id}/events",
            headers=headers,
            name="[Scenario 13: Admin Reject] 3. GET /api/certifications/:id/events",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 404]:
                res.success()
            elif res.status_code >= 500:
                res.failure(f"Verify Events 500: {res.status_code}")


# ==============================================================================
# NHÓM 7: PHÂN HỆ OUTPUT 2 (ANIMAL GROWTH ANALYSIS) - 1 KỊCH BẢN THAO TÁC
# ==============================================================================

class Output2GrowthFlow(SequentialTaskSet):
    """
    Kịch bản 14: Phân tích mô hình đường cong tăng trưởng sinh thái (Output 2).
    Chuỗi thao tác:
      1. Tải tài nguyên giao diện web SPA Output 2
      2. Tải tham số cấu hình mô hình Gompertz tăng trưởng
    """
    @task
    def step1_load_spa_assets(self):
        headers = create_traced_headers()
        with self.client.get(
            "/",
            headers=headers,
            name="[Scenario 14: Output 2 Growth] 1. GET / (Output 2 SPA)",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 304]:
                res.success()

    @task
    def step2_load_gompertz_configs(self):
        headers = create_traced_headers()
        with self.client.get(
            "/api/system-configs?target=output2",
            headers=headers,
            name="[Scenario 14: Output 2 Growth] 2. GET /api/system-configs?target=output2",
            catch_response=True,
        ) as res:
            if res.status_code == 200:
                res.success()


# ==============================================================================
# NHÓM 8: PHÂN HỆ OUTPUT 3 (GEOSPATIAL BIOMASS & ML MODEL) - 1 KỊCH BẢN THAO TÁC
# ==============================================================================

class Output3BiomassFlow(SequentialTaskSet):
    """
    Kịch bản 15: Giám sát sinh khối đồng cỏ & Thực thi mô hình AI Sentinel-2 BPS.
    Chuỗi thao tác:
      1. Đọc tham số vận hành GeoForraje từ satreps_api
      2. Kiểm tra trạng thái Microservice FastAPI BPS (Health Check)
      3. Gửi tọa độ thửa đất GeoJSON chạy mô hình AI ước lượng sinh khối (POST /api/v1/biomass)
      4. Mô phỏng phân tích chuỗi thời gian đa kỳ (Quarter Windows)
    """
    @task
    def step1_geoforraje_configs(self):
        headers = create_traced_headers()
        with self.client.get(
            "/api/system-configs?target=output3",
            headers=headers,
            name="[Scenario 15: Output 3 Biomass] 1. GET /api/system-configs?target=output3",
            catch_response=True,
        ) as res:
            if res.status_code == 200:
                res.success()

    @task
    def step2_bps_health(self):
        url = f"{BPS_BACKEND_HOST}/health" if BPS_BACKEND_HOST else "/health"
        headers = create_traced_headers()
        with self.client.get(
            url,
            headers=headers,
            name="[Scenario 15: Output 3 Biomass] 2. GET /health (BPS Service)",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 204, 404]:
                res.success()

    @task
    def step3_sentinel2_ml_inference(self):
        url = f"{BPS_BACKEND_HOST}/api/v1/biomass" if BPS_BACKEND_HOST else "/api/v1/biomass"
        headers = create_traced_headers()
        headers["Content-Type"] = "application/json"
        payload = {
            "start_date": "2024-01-01",
            "end_date": "2024-01-15",
            "pasture_model": "star_grass",
            "max_cloud_cover_pct": 30.0,
            "paddocks": [
                {
                    "id": f"paddock_sc15_{random.randint(1, 999)}",
                    "coordinates": [
                        [-75.8773, 8.7508],
                        [-75.8750, 8.7508],
                        [-75.8750, 8.7530],
                        [-75.8773, 8.7530],
                        [-75.8773, 8.7508],
                    ],
                }
            ],
        }
        with self.client.post(
            url,
            json=payload,
            headers=headers,
            name="[Scenario 15: Output 3 Biomass] 3. POST /api/v1/biomass (ML Inference)",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 201]:
                res.success()
            elif res.status_code in [404, 422]:
                res.success()
            elif res.status_code >= 500:
                res.failure(f"BPS Model Error 500: {res.status_code}")


# ==============================================================================
# BỔ SUNG 5 KỊCH BẢN NGHIỆP VỤ NÂNG CAO (KỊCH BẢN 16 - 20)
# ==============================================================================

class RancherRequestCertFlow(SequentialTaskSet):
    """
    Kịch bản 16: Chủ trang trại nộp đơn xin cấp chứng nhận bò ăn cỏ (Grass Fed).
    Chuỗi thao tác:
      1. Xem danh sách nông trại của mình để chọn trang trại xin chứng nhận (GET /api/farms/list-farm)
      2. Tra cứu trạng thái các hồ sơ đã nộp của tổ chức (GET /api/certifications/get-status-by-organization)
      3. Gửi hồ sơ đăng ký chứng nhận mới kèm chữ ký số (POST /api/events/create với type: Certificate)
      4. Tra cứu chi tiết hồ sơ chứng nhận vừa tạo (GET /api/certifications/details)
    """
    @task
    def step1_list_rancher_farms(self):
        token = AUTH_TOKENS.get("rancher")
        if not token:
            return
        headers = create_traced_headers(token)
        with self.client.get(
            "/api/ranches/get-by-organization?page=1&length=10",
            headers=headers,
            name="[Scenario 16: Rancher Request Cert] 1. GET /api/ranches/get-by-organization",
            catch_response=True,
        ) as res:
            if res.status_code == 200:
                res.success()
                try:
                    data = res.json().get("result", [])
                    if isinstance(data, list) and data:
                        ranch_ids = [f["id"] for f in data if "id" in f]
                        if ranch_ids:
                            DYNAMIC_DATA["ranches"] = list(set(DYNAMIC_DATA["ranches"] + ranch_ids[:5]))
                except Exception:
                    pass
            elif res.status_code >= 500:
                res.failure(f"List Ranches 500: {res.status_code}")

    @task
    def step2_get_cert_status_by_org(self):
        token = AUTH_TOKENS.get("rancher")
        if not token:
            return
        headers = create_traced_headers(token)
        with self.client.get(
            "/api/certifications/get-status-by-organization",
            headers=headers,
            name="[Scenario 16: Rancher Request Cert] 2. GET /api/certifications/get-status-by-organization",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 404]:
                res.success()
                try:
                    items = res.json().get("result", {}).get("items", [])
                    new_ids = [item["id"] for item in items if "id" in item]
                    if new_ids:
                        DYNAMIC_DATA["certs"] = list(set(DYNAMIC_DATA["certs"] + new_ids[:5]))
                except Exception:
                    pass
            elif res.status_code >= 500:
                res.failure(f"Cert Status Org 500: {res.status_code}")

    @task
    def step3_submit_certificate_event(self):
        token = AUTH_TOKENS.get("rancher")
        if not token:
            return
        headers = create_traced_headers(token)
        farm_id = random.choice(DYNAMIC_DATA["ranches"]) if DYNAMIC_DATA["ranches"] else str(uuid.uuid4())
        payload = {
            "farmId": farm_id,
            "type": "Certificate",
            "signature": f"sig_rancher_{uuid.uuid4().hex[:8]}",
            "fingerprint": f"fp_rancher_{uuid.uuid4().hex[:8]}",
            "extra": {
                "applicationDate": datetime.date.today().isoformat(),
                "grazingStandard": "100% Grass-Fed Pasture",
                "purpose": "Annual Grass Fed certification issuance application",
            },
        }
        with self.client.post(
            "/api/events/create",
            json=payload,
            headers=headers,
            name="[Scenario 16: Rancher Request Cert] 3. POST /api/events/create",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 201, 400, 404]:
                res.success()
                try:
                    cert_id = res.json().get("result", {}).get("certificationId")
                    if cert_id:
                        DYNAMIC_DATA["certs"].append(cert_id)
                        DYNAMIC_DATA.setdefault("certified_ranches", []).append(farm_id)
                        DYNAMIC_DATA.setdefault("assigned_ranches", []).append(farm_id)
                except Exception:
                    pass
            elif res.status_code >= 500:
                res.failure(f"Submit Cert Event 500: {res.status_code}")

    @task
    def step4_view_cert_details(self):
        token = AUTH_TOKENS.get("rancher")
        if not token or not DYNAMIC_DATA["certs"]:
            return
        cert_id = random.choice(DYNAMIC_DATA["certs"])
        headers = create_traced_headers(token)
        with self.client.get(
            f"/api/certifications/details?id={cert_id}",
            headers=headers,
            name="[Scenario 16: Rancher Request Cert] 4. GET /api/certifications/details",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 403, 404]:
                res.success()
            elif res.status_code >= 500:
                res.failure(f"Cert Details 500: {res.status_code}")


class AdminAssignInspectorFlow(SequentialTaskSet):
    """
    Kịch bản 17: Quản trị viên FEDEGAN phân công thanh tra viên thẩm định trang trại.
    Chuỗi thao tác:
      1. Xem danh sách các tổ chức & nông trại thành viên (GET /api/fedegan/organizations)
      2. Tra cứu danh sách tài khoản thanh tra viên trong hệ thống (GET /api/users/list-user)
      3. Thực hiện phân công thanh tra viên cho hồ sơ chứng nhận (POST /api/fedegan/assign-inspector)
      4. Kiểm tra cập nhật phân bổ của tổ chức (GET /api/fedegan/organizations/get)
    """
    @task
    def step1_get_fedegan_organizations(self):
        token = AUTH_TOKENS.get("admin")
        if not token:
            return
        headers = create_traced_headers(token)
        with self.client.get(
            "/api/organizations/base-organizations?page=1&length=10",
            headers=headers,
            name="[Scenario 17: Admin Assign Inspector] 1. GET /api/organizations/base-organizations",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 403]:
                res.success()
            elif res.status_code >= 500:
                res.failure(f"Fedegan Orgs 500: {res.status_code}")

    @task
    def step2_list_inspectors(self):
        token = AUTH_TOKENS.get("admin")
        if not token:
            return
        headers = create_traced_headers(token)
        with self.client.get(
            "/api/fedegan/users/list?page=1&length=20&type=INSPECTOR",
            headers=headers,
            name="[Scenario 17: Admin Assign Inspector] 2. GET /api/fedegan/users/list",
            catch_response=True,
        ) as res:
            if res.status_code == 200:
                res.success()
                try:
                    users = res.json().get("result", [])
                    if isinstance(users, list):
                        u_ids = [u["id"] for u in users if u.get("id")]
                        if u_ids:
                            DYNAMIC_DATA["inspectors"] = list(set(DYNAMIC_DATA.get("inspectors", []) + u_ids[:5]))
                except Exception:
                    pass
            elif res.status_code >= 500:
                res.failure(f"List Users 500: {res.status_code}")

    @task
    def step3_assign_inspector_solicitud(self):
        token = AUTH_TOKENS.get("admin")
        if not token:
            return
        headers = create_traced_headers(token)
        candidate_ranches = DYNAMIC_DATA.get("certified_ranches") or DYNAMIC_DATA["ranches"]
        ranch_id = random.choice(candidate_ranches) if candidate_ranches else str(uuid.uuid4())
        cert_id = random.choice(DYNAMIC_DATA["certs"]) if DYNAMIC_DATA["certs"] else str(uuid.uuid4())
        inspector_id = random.choice(DYNAMIC_DATA["inspectors"]) if DYNAMIC_DATA.get("inspectors") else str(uuid.uuid4())
        payload = {
            "ranchId": ranch_id,
            "inspectorId": inspector_id,
            "certificationId": cert_id,
        }
        with self.client.post(
            "/api/fedegan/assign-inspector",
            json=payload,
            headers=headers,
            name="[Scenario 17: Admin Assign Inspector] 3. POST /api/fedegan/assign-inspector",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 201, 400, 404]:
                res.success()
                if res.status_code in [200, 201]:
                    DYNAMIC_DATA.setdefault("assigned_ranches", []).append(ranch_id)
            elif res.status_code >= 500:
                res.failure(f"Assign Inspector 500: {res.status_code}")

    @task
    def step4_verify_org_assignments(self):
        token = AUTH_TOKENS.get("admin")
        if not token:
            return
        headers = create_traced_headers(token)
        with self.client.get(
            "/api/organizations/get",
            headers=headers,
            name="[Scenario 17: Admin Assign Inspector] 4. GET /api/organizations/get",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 403, 404]:
                res.success()
            elif res.status_code >= 500:
                res.failure(f"Get Org Assignments 500: {res.status_code}")


class AdminClarificationFlow(SequentialTaskSet):
    """
    Kịch bản 18: Quản trị viên FEDEGAN yêu cầu trang trại giải trình & bổ sung hồ sơ chứng nhận.
    Chuỗi thao tác:
      1. Đọc chi tiết tiêu chí đánh giá cần yêu cầu giải trình (GET /api/certifications/details)
      2. Gửi yêu cầu giải trình bổ sung hồ sơ gửi tới chủ trang trại (POST /api/fedegan/request-clarification)
      3. Tra cứu lịch sử dòng sự kiện của hồ sơ chứng nhận (GET /api/certifications/:id/events)
    """
    @task
    def step1_view_solicitud_checklist(self):
        token = AUTH_TOKENS.get("admin") or AUTH_TOKENS.get("inspector")
        if not token or not DYNAMIC_DATA["certs"]:
            return
        cert_id = random.choice(DYNAMIC_DATA["certs"])
        headers = create_traced_headers(token)
        with self.client.get(
            f"/api/certifications/details?id={cert_id}",
            headers=headers,
            name="[Scenario 18: Admin Clarification] 1. GET /api/certifications/details",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 403, 404]:
                res.success()
            elif res.status_code >= 500:
                res.failure(f"View Solicitud 500: {res.status_code}")

    @task
    def step2_request_clarification(self):
        token = AUTH_TOKENS.get("admin") or AUTH_TOKENS.get("inspector")
        if not token or not DYNAMIC_DATA["certs"]:
            return
        cert_id = random.choice(DYNAMIC_DATA["certs"])
        headers = create_traced_headers(token)
        payload = {
            "certificationId": cert_id,
            "request": "Yeu cau bo sung nhat ky chan tha bo an co va ho so thu y 6 thang gan nhat de xet duyet cap chung chi.",
        }
        with self.client.post(
            "/api/fedegan/request-clarification",
            json=payload,
            headers=headers,
            name="[Scenario 18: Admin Clarification] 2. POST /api/fedegan/request-clarification",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 201, 400, 404]:
                res.success()
            elif res.status_code >= 500:
                res.failure(f"Request Clarification 500: {res.status_code}")

    @task
    def step3_verify_clarification_history(self):
        token = AUTH_TOKENS.get("admin") or AUTH_TOKENS.get("inspector")
        if not token or not DYNAMIC_DATA["certs"]:
            return
        cert_id = random.choice(DYNAMIC_DATA["certs"])
        headers = create_traced_headers(token)
        with self.client.get(
            f"/api/certifications/{cert_id}/events",
            headers=headers,
            name="[Scenario 18: Admin Clarification] 3. GET /api/certifications/:id/events",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 404]:
                res.success()
            elif res.status_code >= 500:
                res.failure(f"Verify Events 500: {res.status_code}")


class RancherMemberManageFlow(SequentialTaskSet):
    """
    Kịch bản 19: Chủ trang trại quản lý nhân sự & công nhân nông trại (Farmer Members).
    Chuỗi thao tác:
      1. Xem danh sách thành viên/nông dân thuộc tổ chức (GET /api/farmer/get-by-organization)
      2. Mời/Đăng ký nông dân phụ trách đồng cỏ mới (POST /api/farmer/create)
      3. Kiểm tra danh sách thiết bị định vị cấp cho nhân sự nông trại (GET /api/devices/list)
      4. Tra cứu tổng quan trang trại và phân bổ đồng cỏ (GET /api/farms/list-farm)
    """
    @task
    def step1_list_organization_farmers(self):
        token = AUTH_TOKENS.get("rancher")
        if not token:
            return
        headers = create_traced_headers(token)
        with self.client.get(
            "/api/farmer/get-by-organization?page=1&length=10",
            headers=headers,
            name="[Scenario 19: Rancher Member Manage] 1. GET /api/farmer/get-by-organization",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 403, 404]:
                res.success()
            elif res.status_code >= 500:
                res.failure(f"Farmer List 500: {res.status_code}")

    @task
    def step2_invite_farmer_member(self):
        token = AUTH_TOKENS.get("rancher")
        if not token:
            return
        headers = create_traced_headers(token)
        ranch_id = random.choice(DYNAMIC_DATA["ranches"]) if DYNAMIC_DATA["ranches"] else str(uuid.uuid4())
        unique_email = f"farmer_test_{uuid.uuid4().hex[:6]}@satreps-bench.org"
        payload = {
            "email": unique_email,
            "role": "FARMER",
            "ranchId": ranch_id,
        }
        with self.client.post(
            "/api/farmer/create",
            json=payload,
            headers=headers,
            name="[Scenario 19: Rancher Member Manage] 2. POST /api/farmer/create",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 201, 400, 403, 404]:
                res.success()
            elif res.status_code >= 500:
                res.failure(f"Farmer Create 500: {res.status_code}")

    @task
    def step3_check_farm_ranches(self):
        token = AUTH_TOKENS.get("rancher")
        if not token:
            return
        headers = create_traced_headers(token)
        with self.client.get(
            "/api/ranches/get-by-organization?page=1&length=10",
            headers=headers,
            name="[Scenario 19: Rancher Member Manage] 3. GET /api/ranches/get-by-organization",
            catch_response=True,
        ) as res:
            if res.status_code == 200:
                res.success()
            elif res.status_code >= 500:
                res.failure(f"Farm Ranches 500: {res.status_code}")

    @task
    def step4_list_ranches_statistics(self):
        token = AUTH_TOKENS.get("rancher")
        if not token:
            return
        headers = create_traced_headers(token)
        with self.client.get(
            "/api/ranches/statistics",
            headers=headers,
            name="[Scenario 19: Rancher Member Manage] 4. GET /api/ranches/statistics",
            catch_response=True,
        ) as res:
            if res.status_code == 200:
                res.success()
            elif res.status_code >= 500:
                res.failure(f"Ranches Statistics 500: {res.status_code}")


class SlaughterPlantNetworkFlow(SequentialTaskSet):
    """
    Kịch bản 20: Giám sát mạng lưới chuỗi cung ứng cơ sở & Dòng đời gia súc liên cơ sở.
    Chuỗi thao tác:
      1. Tra cứu mạng lưới các cơ sở, trang trại cung ứng và nhà máy liên kết (GET /api/organizations/base-organizations)
      2. Tra cứu chi tiết thông tin lô mổ liên kết với nông trại nguồn (GET /api/slaughterhouse/lote/detail)
      3. Truy vết dòng thời gian di chuyển của gia súc từ nông trại tới nhà máy (GET /api/animals/timeline)
      4. Tra cứu chi tiết hồ sơ cá thể động vật theo mã định danh DIN (GET /api/animals/get-by-din)
    """
    @task
    def step1_query_base_organizations(self):
        headers = create_traced_headers()
        with self.client.get(
            "/api/organizations/base-organizations?page=1&length=10",
            headers=headers,
            name="[Scenario 20: Slaughter Plant Network] 1. GET /api/organizations/base-organizations",
            catch_response=True,
        ) as res:
            if res.status_code == 200:
                res.success()
            elif res.status_code >= 500:
                res.failure(f"Base Orgs 500: {res.status_code}")

    @task
    def step2_get_lote_source_detail(self):
        token = AUTH_TOKENS.get("slaughterhouse")
        headers = create_traced_headers(token) if token else create_traced_headers()
        lote_id = random.choice(DYNAMIC_DATA["lotes"]) if DYNAMIC_DATA["lotes"] else str(uuid.uuid4())
        with self.client.get(
            f"/api/slaughterhouse/lote/detail?lote_id={lote_id}&org_id={SLAUGHTERHOUSE_ORG_ID}&pageNumber=1&pageSize=10",
            headers=headers,
            name="[Scenario 20: Slaughter Plant Network] 2. GET /api/slaughterhouse/lote/detail",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 400, 404]:
                res.success()
            elif res.status_code >= 500:
                res.failure(f"Lote Detail 500: {res.status_code}")

    @task
    def step3_animal_movement_timeline(self):
        din = random.choice(SAMPLE_DINS)
        headers = create_traced_headers()
        with self.client.get(
            f"/api/animals/timeline?din={din}",
            headers=headers,
            name="[Scenario 20: Slaughter Plant Network] 3. GET /api/animals/timeline",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 404]:
                res.success()
            elif res.status_code >= 500:
                res.failure(f"Animal Timeline 500: {res.status_code}")

    @task
    def step4_query_animal_record(self):
        din = random.choice(SAMPLE_DINS)
        headers = create_traced_headers()
        with self.client.get(
            f"/api/animals/get-by-din?din={din}",
            headers=headers,
            name="[Scenario 20: Slaughter Plant Network] 4. GET /api/animals/get-by-din",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 404]:
                res.success()
            elif res.status_code >= 500:
                res.failure(f"Animal Record 500: {res.status_code}")


# ==============================================================================
# KHỞI TẠO CÁC LỚP USER ĐỘC LẬP CHO TỪNG KỊCH BẢN (20 USER SCENARIOS)
# ==============================================================================

class Scenario1_InspectorAuditUser(BaseSatrepsUser):
    tasks = [InspectorAuditFlow]
    wait_time = between(1.5, 3.5)

class Scenario2_InspectorScheduleUser(BaseSatrepsUser):
    tasks = [InspectorScheduleFlow]
    wait_time = between(1.5, 3.5)

class Scenario3_InspectorCertUser(BaseSatrepsUser):
    tasks = [InspectorCertFlow]
    wait_time = between(1.5, 3.5)

class Scenario4_SlaughterLoteUser(BaseSatrepsUser):
    tasks = [SlaughterLoteFlow]
    wait_time = between(1.5, 3.5)

class Scenario5_SlaughterAuditUser(BaseSatrepsUser):
    tasks = [SlaughterAuditFlow]
    wait_time = between(1.5, 3.5)

class Scenario6_SlaughterExternalUser(BaseSatrepsUser):
    tasks = [SlaughterExternalFlow]
    wait_time = between(1.5, 3.5)

class Scenario7_RancherManageUser(BaseSatrepsUser):
    tasks = [RancherManageFlow]
    wait_time = between(1.5, 3.5)

class Scenario8_RancherCreateUser(BaseSatrepsUser):
    tasks = [RancherCreateFlow]
    wait_time = between(1.5, 3.5)

class Scenario9_RancherGisUser(BaseSatrepsUser):
    tasks = [RancherGisFlow]
    wait_time = between(1.5, 3.5)

class Scenario10_AdminDashboardUser(BaseSatrepsUser):
    tasks = [AdminDashboardFlow]
    wait_time = between(2.0, 4.0)

class Scenario11_AdminApprovalUser(BaseSatrepsUser):
    tasks = [AdminApprovalFlow]
    wait_time = between(2.0, 4.0)

class Scenario12_TraceabilityTimelineUser(BaseSatrepsUser):
    tasks = [TraceabilityTimelineFlow]
    wait_time = between(2.0, 4.5)

class Scenario13_AdminRejectUser(BaseSatrepsUser):
    tasks = [AdminRejectFlow]
    wait_time = between(2.0, 4.0)

class Scenario14_Output2GrowthUser(BaseSatrepsUser):
    tasks = [Output2GrowthFlow]
    wait_time = between(2.0, 4.0)

# class Scenario15_Output3BiomassUser(BaseSatrepsUser):
#     tasks = [Output3BiomassFlow]
#     wait_time = between(3.0, 6.0)

class Scenario16_RancherRequestCertUser(BaseSatrepsUser):
    tasks = [RancherRequestCertFlow]
    wait_time = between(1.5, 3.5)

class Scenario17_AdminAssignInspectorUser(BaseSatrepsUser):
    tasks = [AdminAssignInspectorFlow]
    wait_time = between(2.0, 4.0)

class Scenario18_AdminClarificationUser(BaseSatrepsUser):
    tasks = [AdminClarificationFlow]
    wait_time = between(2.0, 4.0)

class Scenario19_RancherMemberManageUser(BaseSatrepsUser):
    tasks = [RancherMemberManageFlow]
    wait_time = between(1.5, 3.5)

class Scenario20_SlaughterPlantNetworkUser(BaseSatrepsUser):
    tasks = [SlaughterPlantNetworkFlow]
    wait_time = between(1.5, 3.5)


# Dictionary ánh xạ tên kịch bản sang lớp User tương ứng
ROLE_SCENARIOS_MAP = {
    # 1. Nhóm Inspector (Kịch bản 1, 2, 3)
    "inspector_audit": [Scenario1_InspectorAuditUser],
    "inspector_schedule": [Scenario2_InspectorScheduleUser],
    "inspector_cert": [Scenario3_InspectorCertUser],
    "role_inspector": [Scenario1_InspectorAuditUser, Scenario2_InspectorScheduleUser, Scenario3_InspectorCertUser],

    # 2. Nhóm Slaughterhouse (Kịch bản 4, 5, 6, 20)
    "slaughter_lote": [Scenario4_SlaughterLoteUser],
    "slaughter_audit": [Scenario5_SlaughterAuditUser],
    "slaughter_external": [Scenario6_SlaughterExternalUser],
    "slaughter_plant_network": [Scenario20_SlaughterPlantNetworkUser],
    "role_slaughterhouse": [
        Scenario4_SlaughterLoteUser,
        Scenario5_SlaughterAuditUser,
        Scenario6_SlaughterExternalUser,
        Scenario20_SlaughterPlantNetworkUser,
    ],

    # 3. Nhóm Rancher (Kịch bản 7, 8, 9, 16, 19)
    "rancher_manage": [Scenario7_RancherManageUser],
    "rancher_create": [Scenario8_RancherCreateUser],
    "rancher_gis": [Scenario9_RancherGisUser],
    "rancher_request_cert": [Scenario16_RancherRequestCertUser],
    "rancher_member_manage": [Scenario19_RancherMemberManageUser],
    "role_rancher": [
        Scenario7_RancherManageUser,
        Scenario8_RancherCreateUser,
        Scenario9_RancherGisUser,
        Scenario16_RancherRequestCertUser,
        Scenario19_RancherMemberManageUser,
    ],

    # 4. Nhóm Admin (Kịch bản 10, 11, 13, 17, 18)
    "admin_dashboard": [Scenario10_AdminDashboardUser],
    "admin_approval": [Scenario11_AdminApprovalUser],
    "admin_reject": [Scenario13_AdminRejectUser],
    "admin_assign_inspector": [Scenario17_AdminAssignInspectorUser],
    "admin_clarification": [Scenario18_AdminClarificationUser],
    "role_admin": [
        Scenario10_AdminDashboardUser,
        Scenario11_AdminApprovalUser,
        Scenario13_AdminRejectUser,
        Scenario17_AdminAssignInspectorUser,
        Scenario18_AdminClarificationUser,
    ],

    # 5. Nhóm Traceability (Kịch bản 12)
    "traceability_timeline": [Scenario12_TraceabilityTimelineUser],
    "role_traceability": [Scenario12_TraceabilityTimelineUser],

    # 6. Nhóm Output 2 (Kịch bản 14)
    "output2_growth": [Scenario14_Output2GrowthUser],
    "role_output2": [Scenario14_Output2GrowthUser],

    # 7. Nhóm Output 3 (Kịch bản 15) - Tạm thời comment out
    # "output3_biomass": [Scenario15_Output3BiomassUser],
    # "role_output3": [Scenario15_Output3BiomassUser],

    # 8. Toàn bộ các Role cùng lúc (20 Kịch bản thao tác)
    "all_roles": [
        # Nhóm 1: Thanh tra viên (Inspector)
        Scenario1_InspectorAuditUser,
        Scenario2_InspectorScheduleUser,
        Scenario3_InspectorCertUser,
        # Nhóm 2: Nhà máy giết mổ (Slaughterhouse)
        Scenario4_SlaughterLoteUser,
        Scenario5_SlaughterAuditUser,
        Scenario6_SlaughterExternalUser,
        Scenario20_SlaughterPlantNetworkUser,
        # Nhóm 3: Chủ trang trại (Rancher)
        Scenario7_RancherManageUser,
        Scenario8_RancherCreateUser,
        Scenario9_RancherGisUser,
        Scenario16_RancherRequestCertUser,
        Scenario19_RancherMemberManageUser,
        # Nhóm 4: Quản trị viên (FEDEGAN Admin)
        Scenario10_AdminDashboardUser,
        Scenario11_AdminApprovalUser,
        Scenario13_AdminRejectUser,
        Scenario17_AdminAssignInspectorUser,
        Scenario18_AdminClarificationUser,
        # Nhóm 5, 6: Truy xuất nguồn gốc & Output 2
        Scenario12_TraceabilityTimelineUser,
        Scenario14_Output2GrowthUser,
        # Scenario15_Output3BiomassUser,  # Đã comment out phần Output 3
    ],
    "role_all": [
        Scenario1_InspectorAuditUser,
        Scenario2_InspectorScheduleUser,
        Scenario3_InspectorCertUser,
        Scenario4_SlaughterLoteUser,
        Scenario5_SlaughterAuditUser,
        Scenario6_SlaughterExternalUser,
        Scenario20_SlaughterPlantNetworkUser,
        Scenario7_RancherManageUser,
        Scenario8_RancherCreateUser,
        Scenario9_RancherGisUser,
        Scenario16_RancherRequestCertUser,
        Scenario19_RancherMemberManageUser,
        Scenario10_AdminDashboardUser,
        Scenario11_AdminApprovalUser,
        Scenario13_AdminRejectUser,
        Scenario17_AdminAssignInspectorUser,
        Scenario18_AdminClarificationUser,
        Scenario12_TraceabilityTimelineUser,
        Scenario14_Output2GrowthUser,
        # Scenario15_Output3BiomassUser,  # Đã comment out phần Output 3
    ],
}

