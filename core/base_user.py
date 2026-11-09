import random
# pyrefly: ignore [missing-import]
from locust import HttpUser
from core.auth import fetch_tokens_once

# ==============================================================================
# LỚP CƠ SỞ (BASE USER) - GIẢ LẬP MẠNG PHÂN TÁN CHO TỪNG VIRTUAL USER
# ==============================================================================

class BaseSatrepsUser(HttpUser):
    """
    Lớp cơ sở cho toàn bộ người dùng ảo:
    1. Đăng nhập lấy JWT dùng chung 1 lần duy nhất lúc bắt đầu (Single Login Cache).
    2. Cấp phát 1 địa chỉ IP phân tán thực tế (Colombia Subnets: 190.24.x.x, 181.128.x.x, 186.28.x.x)
       được gắn vào header 'X-Forwarded-For' cho từng User ảo trong suốt phiên làm việc.
       Điều này phản ánh chính xác các người dùng thật từ các vùng miền khác nhau,
       đồng thời giúp bypass bộ lọc rate-limit 429 khi chạy dồn dập từ 1 máy test.
    """
    abstract = True

    def on_start(self):
        fetch_tokens_once(self.host)
        # Giả lập IP ngẫu nhiên từ các nhà mạng Colombia (Claro, Tigo, Movistar, ETB)
        subnet = random.choice(["190.24", "181.128", "186.28", "200.118", "190.157", "181.48"])
        self.simulated_ip = f"{subnet}.{random.randint(1, 254)}.{random.randint(1, 254)}"
        self.client.headers.update({
            "X-Forwarded-For": self.simulated_ip,
            "x-user-agent": "SATREPS-Locust-Distributed-Agent",
        })
        # Thiết lập timeout mặc định (30s) chống treo greenlet khi Cloud Run/DB nghẽn
        orig_request = self.client.request
        def timeout_request(*args, **kwargs):
            kwargs.setdefault("timeout", 30.0)
            return orig_request(*args, **kwargs)
        self.client.request = timeout_request
