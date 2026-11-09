import random
# pyrefly: ignore [missing-import]
from locust import task, between
from core.base_user import BaseSatrepsUser
from core.auth import AUTH_TOKENS, create_traced_headers
from core.state import DYNAMIC_DATA

# ==============================================================================
# PHÂN HỆ 2D: FEDEGAN ADMINISTRATOR (MỤC 5.2 - KỊCH BẢN QUẢN TRỊ TRUNG TÂM)
# Profile: FEDEGAN Central Administrator
# ==============================================================================

class FedeganAdminUser(BaseSatrepsUser):
    """
    [Mức 3] Phân hệ Quản trị FEDEGAN Trung tâm (Module 2D theo Mục 5.2 doc.txt):
    - Quản lý và giám sát chứng nhận bò ăn cỏ toàn quốc.
    - Nghiệp vụ:
      1. Dashboard thống kê chứng chỉ toàn quốc (GET /api/fedegan/certifications/statistics)
      2. Thống kê người dùng toàn hệ thống (GET /api/fedegan/users/statistics)
      3. Danh sách người dùng & phân quyền (GET /api/fedegan/users/list)
      4. Xem chi tiết hồ sơ chứng nhận FEDEGAN (GET /api/certifications/details)
      5. Duyệt hồ sơ chứng nhận (POST /api/fedegan/approve-certification)
    """
    weight = 1
    wait_time = between(2.0, 4.0)

    @task(3)
    def test_admin_certification_statistics(self):
        """[Mức 3] Dashboard thống kê chứng nhận toàn quốc theo các trạng thái"""
        token = AUTH_TOKENS.get("admin") or AUTH_TOKENS.get("inspector")
        if not token:
            return

        headers = create_traced_headers(token)
        with self.client.get(
            "/api/fedegan/certifications/statistics",
            headers=headers,
            name="[App 2: FEDEGAN Admin] GET /api/fedegan/certifications/statistics",
            catch_response=True,
        ) as res:
            if res.status_code == 200:
                res.success()
            elif res.status_code == 429:
                res.failure("Throttled (429)")

    @task(3)
    def test_admin_user_statistics(self):
        """[Mức 3] Dashboard thống kê tổng quan người dùng toàn hệ sinh thái"""
        token = AUTH_TOKENS.get("admin") or AUTH_TOKENS.get("inspector")
        if not token:
            return

        headers = create_traced_headers(token)
        with self.client.get(
            "/api/fedegan/users/statistics",
            headers=headers,
            name="[App 2: FEDEGAN Admin] GET /api/fedegan/users/statistics",
            catch_response=True,
        ) as res:
            if res.status_code == 200:
                res.success()
            elif res.status_code == 429:
                res.failure("Throttled (429)")

    @task(2)
    def test_admin_users_list(self):
        """[Mức 3] Xem và phân trang danh sách người dùng hệ thống"""
        token = AUTH_TOKENS.get("admin") or AUTH_TOKENS.get("inspector")
        if not token:
            return

        headers = create_traced_headers(token)
        page = random.choice([1, 2])
        with self.client.get(
            f"/api/fedegan/users/list?page={page}&length=10",
            headers=headers,
            name="[App 2: FEDEGAN Admin] GET /api/fedegan/users/list",
            catch_response=True,
        ) as res:
            if res.status_code == 200:
                res.success()
            elif res.status_code == 429:
                res.failure("Throttled (429)")

    @task(2)
    def test_admin_certification_details(self):
        """[Mức 1 & 3] Xem chi tiết đầy đủ hồ sơ thẩm định và checklist đánh giá của chứng nhận"""
        token = AUTH_TOKENS.get("admin") or AUTH_TOKENS.get("inspector")
        if not token or not DYNAMIC_DATA["certs"]:
            return

        cert_id = random.choice(DYNAMIC_DATA["certs"])
        headers = create_traced_headers(token)
        with self.client.get(
            f"/api/certifications/details?id={cert_id}",
            headers=headers,
            name="[App 2: FEDEGAN Admin] GET /api/certifications/details",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 403, 404]:
                # 403: Cần role Fedegan (chấp nhận nếu token là role khác), 404: cert_id không tồn tại
                res.success()
            elif res.status_code == 429:
                res.failure("Throttled (429)")

    @task(1)
    def test_admin_approve_certification(self):
        """[Mức 3] Kịch bản GHI (POST): Admin phê duyệt hồ sơ chứng chỉ bò ăn cỏ"""
        token = AUTH_TOKENS.get("admin") or AUTH_TOKENS.get("inspector")
        if not token or not DYNAMIC_DATA["certs"]:
            return

        cert_id = random.choice(DYNAMIC_DATA["certs"])
        headers = create_traced_headers(token)
        with self.client.post(
            "/api/fedegan/approve-certification",
            json={"certificationId": cert_id},
            headers=headers,
            name="[App 2: FEDEGAN Admin] POST /api/fedegan/approve-certification",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 201, 400, 404]:
                res.success()
            elif res.status_code == 429:
                res.failure("Throttled (429)")
