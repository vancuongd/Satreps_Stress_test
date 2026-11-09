import random
# pyrefly: ignore [missing-import]
from locust import task, between
from core.base_user import BaseSatrepsUser
from core.auth import create_traced_headers
from config.seed_data import SAMPLE_DINS

# ==============================================================================
# PHÂN HỆ 1: MANUAL TRACEABILITY (MỤC 5.1 & 6.4 TRONG DOC.TXT)
# "Low user concurrency (< 100 users), high volume of SQL database operations"
# ==============================================================================

class ManualTraceabilityUser(BaseSatrepsUser):
    """
    Phân hệ Truy xuất nguồn gốc thủ công:
    - User concurrency thấp (< 100 users).
    - Tải cơ sở dữ liệu cực nặng: Heavy JOIN qua 4 bảng (Animal -> Mobilization -> Ranch -> Slaughterhouse).
    """
    weight = 1
    wait_time = between(2.0, 5.0)

    @task(5)
    def test_animal_timeline_heavy_join(self):
        """Truy vấn dòng đời gia súc: Heavy JOIN SQL kiểm định Connection Pool & Lock Contention"""
        din = random.choice(SAMPLE_DINS)
        headers = create_traced_headers()
        with self.client.get(
            f"/api/animals/timeline?din={din}",
            headers=headers,
            name="[App 1: Traceability] GET /api/animals/timeline (Heavy JOIN)",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 404]:
                res.success()
            elif res.status_code == 429:
                res.failure("Traceability Throttled (429)")
            elif res.status_code >= 500:
                res.failure(f"Traceability DB Timeout/500: {res.text[:100]}")

    @task(3)
    def test_animal_verification_and_search(self):
        """Truy vấn tìm kiếm và kiểm tra tính hợp lệ của mã thẻ tai động vật (DIN validation & Timeline)"""
        din = random.choice(SAMPLE_DINS)
        headers = create_traced_headers()
        clean_din = din.replace(" ", "")
        with self.client.get(
            f"/api/animals/timeline?din={clean_din}",
            headers=headers,
            name="[App 1: Traceability] GET /api/animals/timeline (Unformatted DIN)",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 404]:
                res.success()
            elif res.status_code == 429:
                res.failure("Animal Verification Throttled (429)")
            elif res.status_code >= 500:
                res.failure(f"Animal Verification 500: {res.text[:100]}")

    @task(1)
    def test_traceability_system_config(self):
        """Đọc cấu hình hệ thống truy xuất"""
        headers = create_traced_headers()
        self.client.get(
            "/api/system-configs?target=web",
            headers=headers,
            name="[App 1: Traceability] GET /api/system-configs",
        )

    @task(1)
    def test_traceability_auth_verification(self):
        """Kịch bản GHI/POST: Xác thực phiên người dùng truy xuất nguồn gốc (Auth POST)"""
        headers = create_traced_headers()
        with self.client.post(
            "/api/users/login",
            json={"email": "certicol.andes@colmail.com"},
            headers=headers,
            name="[App 1: Traceability] POST /api/users/login (Auth Verification)",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 201]:
                res.success()
            elif res.status_code == 429:
                res.failure("Traceability Auth Throttled (429)")
            elif res.status_code >= 500:
                res.failure(f"Traceability Auth 500: {res.text[:100]}")
