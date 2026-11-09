import random
# pyrefly: ignore [missing-import]
from locust import task, between
from core.base_user import BaseSatrepsUser
from core.auth import create_traced_headers
from core.state import DYNAMIC_DATA

# ==============================================================================
# PHÂN HỆ 2E: GRASS-FED CERTIFICATION - KHÁCH THĂM QUAN / CÔNG CHÚNG (MỤC 5.2 DOC.TXT)
# Profile: Visitor / Public Consumer
# Primary activities: Tra cứu thông tin chứng nhận công khai, xem thông tin trang trại
# ==============================================================================

class GrassFedVisitorUser(BaseSatrepsUser):
    """
    Phân hệ Khách thăm quan / Người tiêu dùng công cộng (Visitor):
    Nghiệp vụ: Quét mã QR tem nhãn, tra cứu thông tin chứng nhận thịt bò ăn cỏ,
    xem hồ sơ công khai của trang trại liên kết.
    """
    weight = 2
    wait_time = between(1.5, 4.0)

    @task(4)
    def test_visitor_public_certification_lookup(self):
        """Khách / Người tiêu dùng quét QR tra cứu chứng nhận công khai"""
        cert_id = random.choice(DYNAMIC_DATA["certs"])
        headers = create_traced_headers()
        with self.client.get(
            f"/api/certifications/public-info/{cert_id}",
            headers=headers,
            name="[App 2: Visitor] GET /api/certifications/public-info/:id",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 404]:
                res.success()
            elif res.status_code == 429:
                res.failure("Visitor Throttled (429)")
            elif res.status_code >= 500:
                res.failure(f"Visitor Public Cert 500: {res.status_code}")

    @task(2)
    def test_visitor_view_farm_public(self):
        """Xem thông tin trang trại liên kết với chứng nhận công khai"""
        if not DYNAMIC_DATA["ranches"]:
            return

        ranch_id = random.choice(DYNAMIC_DATA["ranches"])
        headers = create_traced_headers()
        with self.client.get(
            f"/api/ranches/get/{ranch_id}",
            headers=headers,
            name="[App 2: Visitor] GET /api/ranches/get/:id (Public Farm View)",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 404]:
                res.success()
            elif res.status_code == 429:
                res.failure("Visitor Throttled (429)")

    @task(1)
    def test_visitor_landing_page(self):
        """Tải trang chủ xác thực nguồn gốc chứng nhận"""
        headers = create_traced_headers()
        self.client.get(
            "/",
            headers=headers,
            name="[App 2: Visitor] GET / (Public Landing)",
        )
