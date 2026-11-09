# pyrefly: ignore [missing-import]
from locust import task, between
from core.base_user import BaseSatrepsUser
from core.auth import create_traced_headers

# ==============================================================================
# PHÂN HỆ 3: OUTPUT 2 - ANIMAL GROWTH ANALYSIS (MỤC 5.3 TRONG DOC.TXT)
# "Public access ~1,000 unique users/day, calculations, charts and reference data"
# ==============================================================================

class Output2GrowthAnalysisUser(BaseSatrepsUser):
    """
    Phân hệ Output 2: Phân tích đường cong sinh trưởng động vật (Public Web)
    - Lưu lượng người dùng công cộng (~1.000 unique users/ngày).
    - Thao tác: Tải thông số mô hình sinh trưởng, cấu hình tham số, kết quả tính toán.
    """
    weight = 1
    wait_time = between(2.0, 4.0)

    @task(3)
    def test_output2_system_configs(self):
        """Tải tham số cấu hình mô hình Gompertz tăng trưởng từ server (Output 2)"""
        headers = create_traced_headers()
        self.client.get(
            "/api/system-configs?target=output2",
            headers=headers,
            name="[App 5: Output 2 Growth] GET /api/system-configs?target=output2",
        )

    @task(2)
    def test_output2_static_assets(self):
        """Tải ứng dụng và Static Assets (Output 2 Landing & Hub Web)"""
        headers = create_traced_headers()
        self.client.get(
            "/",
            headers=headers,
            name="[App 5: Output 2 Growth] GET / (Static Web Delivery)",
        )
