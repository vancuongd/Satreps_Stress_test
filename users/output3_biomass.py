import random
# pyrefly: ignore [missing-import]
from locust import HttpUser, task, between
from core.auth import create_traced_headers
from config.settings import BPS_BACKEND_HOST

# ==============================================================================
# PHÂN HỆ 4: OUTPUT 3 - GEOSPATIAL BIOMASS & ANALYTICAL MODEL (BPS SATELLITE ENGINE)
# Đã chuẩn hóa đầy đủ theo satreps-bps-backend (FastAPI) và satreps-bps-frontend (Svelte 5):
# - satreps_api cung cấp thông số cấu hình: GET /api/system-configs?target=output3
# - satreps-bps-backend thực thi mô hình viễn thám: POST /api/v1/biomass & GET /health & GET /api/v1/models
# ==============================================================================

class Output3GeospatialBiomassUser(HttpUser):
    """
    Phân hệ Output 3: Giám sát sinh khối đồng cỏ bằng không gian địa lý (GeoForraje / BPS Web)
    - Lưu lượng công cộng (~1.000 unique users/ngày theo Mục 5.4 trong doc.txt).
    - Thao tác: Tải cấu hình tham số vệ tinh Sentinel-2, danh sách tiểu vùng Córdoba,
      mô hình cỏ (star_grass, mombasa_grass), kiểm tra trạng thái sức khỏe dịch vụ viễn thám.
    """
    weight = 1
    wait_time = between(2.0, 4.0)

    @task(3)
    def test_geoforraje_operational_configs(self):
        """
        Tải tham số vận hành GeoForraje (Độ che phủ mây Sentinel-2, tọa độ trung tâm tiểu vùng,
        ngưỡng ngày sử dụng đồng cỏ disponible/cautela) từ NestJS API (satreps_api).
        """
        headers = create_traced_headers()
        with self.client.get(
            "/api/system-configs?target=output3",
            headers=headers,
            name="[App 6: Output 3 GeoForraje] GET /api/system-configs?target=output3",
            catch_response=True,
        ) as res:
            if res.status_code == 200:
                res.success()
            elif res.status_code == 429:
                res.failure("Output 3 Configs Throttled (429)")
            elif res.status_code >= 500:
                res.failure(f"Output 3 Configs 500: {res.status_code}")

    @task(1)
    def test_bps_service_health(self):
        """
        Kiểm tra trạng thái sẵn sàng (Health Check) của Python FastAPI BPS Microservice.
        Nếu có BPS_BACKEND_HOST sẽ gọi trực tiếp, nếu không sẽ kiểm tra endpoint /health.
        """
        url = f"{BPS_BACKEND_HOST}/health" if BPS_BACKEND_HOST else "/health"
        headers = create_traced_headers()
        with self.client.get(
            url,
            headers=headers,
            name="[App 6: Output 3 BPS Backend] GET /health",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 204]:
                res.success()
            elif res.status_code == 404:
                if not BPS_BACKEND_HOST:
                    res.success()
                else:
                    res.failure(f"BPS Health 404: {res.text[:80]}")
            elif res.status_code >= 500:
                res.failure(f"BPS Health 500: {res.status_code}")

    @task(1)
    def test_geoforraje_static_assets(self):
        """Kiểm tra độ trễ phân phối nội dung tĩnh cho phân hệ bản đồ Leaflet SPA"""
        headers = create_traced_headers()
        self.client.get(
            "/",
            headers=headers,
            name="[App 6: Output 3 GeoForraje] GET / (Map SPA Delivery)",
        )


class Output3BiomassAnalyticalModelUser(HttpUser):
    """
    Khối tính toán chuyên biệt: Mô hình phân tích ảnh viễn thám Sentinel-2 ước lượng sinh khối (BPS)
    Theo Mục 5.4 & 6.4 trong tài liệu kỹ thuật:
    - Tác vụ tính toán cực nặng (CPU & RAM), xử lý raster TIF viễn thám và mô hình hồi quy Scikit-learn.
    - Được thiết kế thành nhóm giao dịch chuyên biệt (Separate Transaction Group)
      và báo cáo độc lập để đánh giá năng lực chịu tải tối đa, hàng đợi và thời gian phục hồi.
    - Chuẩn tọa độ gửi lên backend: [[lng, lat], ...] (GeoJSON WGS-84), khu vực thực địa ESTRELLA, Córdoba.
    """
    weight = 1
    wait_time = between(4.0, 8.0)

    @task(2)
    def test_biomass_model_parameter_query(self):
        """Đọc tham số cấu hình mô hình toán học GeoForraje trước khi tính toán"""
        headers = create_traced_headers()
        self.client.get(
            "/api/system-configs?target=output3",
            headers=headers,
            name="[Specialized: Output 3 Biomass Model] GET Parameters",
        )

    @task(3)
    def test_biomass_model_single_window_inference(self):
        """
        Kích hoạt tính toán sinh khối vệ tinh đơn kỳ (Single Sentinel-2 Window Inference).
        - Endpoint: POST /api/v1/biomass
        - Model: star_grass (Production pipeline tại ESTRELLA, Colombia)
        - Dữ liệu polygon thửa đất (paddocks): Tọa độ WGS-84 chuẩn [lng, lat]
        """
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
                    "id": f"paddock_estrella_{random.randint(1, 999)}",
                    "coordinates": [
                        [-75.8773, 8.7508],
                        [-75.8750, 8.7508],
                        [-75.8750, 8.7530],
                        [-75.8773, 8.7530],
                        [-75.8773, 8.7508],
                    ],
                },
                {
                    "id": f"paddock_estrella_{random.randint(1000, 1999)}",
                    "coordinates": [
                        [-75.8814, 8.7512],
                        [-75.8790, 8.7512],
                        [-75.8790, 8.7535],
                        [-75.8814, 8.7535],
                        [-75.8814, 8.7512],
                    ],
                },
            ],
        }

        with self.client.post(
            url,
            json=payload,
            headers=headers,
            name="[Specialized: Output 3 Biomass Model] POST /api/v1/biomass (Sentinel-2 ML Inference)",
            catch_response=True,
        ) as res:
            if res.status_code in [200, 201]:
                res.success()
            elif res.status_code == 422:
                res.failure(f"BPS Model 422: {res.text[:100]}")
            elif res.status_code == 404:
                if not BPS_BACKEND_HOST:
                    res.failure("BPS 404 (Đặt biến BPS_BACKEND_HOST=http://localhost:8000 nếu BPS backend chạy ở cổng riêng)")
                else:
                    res.failure(f"BPS 404 Not Found: {res.text[:80]}")
            elif res.status_code == 429:
                res.failure("BPS Model Throttled (429 Queue Full)")
            elif res.status_code >= 500:
                res.failure(f"BPS Model Compute Error 500: {res.text[:100]}")

    @task(1)
    def test_biomass_model_multi_quarter_simulation(self):
        """
        Mô phỏng hành vi người dùng trên satreps-bps-frontend khi chọn phân tích chuỗi thời gian
        (Multiple Quarter Windows) với tính năng gọi đồng thời lên đến 3 kỳ liên tiếp.
        """
        url = f"{BPS_BACKEND_HOST}/api/v1/biomass" if BPS_BACKEND_HOST else "/api/v1/biomass"
        headers = create_traced_headers()
        headers["Content-Type"] = "application/json"

        quarters = [
            ("2024-01-01", "2024-03-31"),
            ("2024-04-01", "2024-06-30"),
        ]

        for start_d, end_d in quarters:
            payload = {
                "start_date": start_d,
                "end_date": end_d,
                "pasture_model": "star_grass",
                "max_cloud_cover_pct": 30.0,
                "paddocks": [
                    {
                        "id": f"paddock_quarter_{random.randint(1, 500)}",
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
                name="[Specialized: Output 3 Biomass Model] POST /api/v1/biomass (Quarter Window)",
                catch_response=True,
            ) as res:
                if res.status_code in [200, 201]:
                    res.success()
                elif res.status_code == 422:
                    res.failure(f"BPS Quarter 422: {res.text[:80]}")
                elif res.status_code == 404:
                    if not BPS_BACKEND_HOST:
                        res.failure("BPS 404 (Set BPS_BACKEND_HOST to target BPS server)")
                    else:
                        res.failure("BPS 404 Not Found")
                elif res.status_code == 429:
                    res.failure("BPS Quarter Throttled (429)")
                elif res.status_code >= 500:
                    res.failure(f"BPS Quarter 500: {res.text[:80]}")
