import threading
from config.seed_data import FALLBACK_CERTS, CERTIFIED_RANCH_IDS

# ==============================================================================
# RÀNG BUỘC KỸ THUẬT & TRẠNG THÁI CHIA SẺ THỜI GIAN THỰC (GLOBAL STATE)
# ==============================================================================

# Ràng buộc kỹ thuật: External API <= 20 concurrent users (Mục 5.2 & 6.1 doc.txt)
EXTERNAL_API_SEMAPHORE = threading.Semaphore(20)

# Bộ nhớ đệm ID động (Chaining Data từ database thật sau các truy vấn)
DYNAMIC_DATA = {
    "certs": list(FALLBACK_CERTS),
    "lotes": [],
    "lote_logs": [],
    "ranches": list(CERTIFIED_RANCH_IDS),
    # Danh sách các trang trại đã có hồ sơ chứng nhận Grass-Fed (đảm bảo tính nhất quán trước - sau khi đặt lịch)
    "certified_ranches": list(CERTIFIED_RANCH_IDS),
    # Danh sách các trang trại đã được phân công thanh tra viên
    "assigned_ranches": list(CERTIFIED_RANCH_IDS),
    "inspectors": [],
}

# Quản lý dữ liệu tạo bởi kịch bản GHI (POST/PUT) để dọn dẹp sạch khi dừng test
CLEANUP_LOCK = threading.Lock()
CREATED_TEST_IDS = {
    "ranches": set(),  # Danh sách ID trang trại test tạo bởi POST /api/ranches/create
    "devices": set(),  # Danh sách FCM tokens test tạo bởi POST /api/notifications/register-device
}

# Tham chiếu Locust Environment dùng cho kịch bản tự động dừng (Breaking Point Auto-stop)
GLOBAL_LOCUST_ENV = None

