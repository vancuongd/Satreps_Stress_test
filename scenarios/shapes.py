import os
# pyrefly: ignore [missing-import]
from locust import LoadTestShape
from config.settings import TEST_SCENARIO
import core.state as state

# ==============================================================================
# ĐIỀU PHỐI KỊCH BẢN TẢI THEO MỤC 6 TRONG DOC.TXT (LOAD TEST SHAPE)
# Kích hoạt tự động khi đặt biến môi trường: SCENARIO=baseline | peak | stress | bottleneck | breakingpoint
# Mặc định khi không đặt SCENARIO: Dùng chế độ Interactive (Web UI slider hoặc cờ CLI -u/-r)
# ==============================================================================

SCENARIO_LIST = [
    # Kịch bản tải hệ thống chung (General Load Shapes)
    "baseline", "peak", "stress", "bottleneck", "rampup",
    "breakingpoint", "continuous", "autostop",
    "spike", "shock", "flashcrowd", "step", "gradual", "ladder",
    "soak", "endurance", "doublespike", "dualspike", "twospike",

    # 20 Kịch bản thao tác người dùng theo từng Role (Role-based Operational Scenarios)
    "inspector_audit", "inspector_schedule", "inspector_cert", "role_inspector",
    "slaughter_lote", "slaughter_audit", "slaughter_external", "slaughter_plant_network", "role_slaughterhouse",
    "rancher_manage", "rancher_create", "rancher_gis", "rancher_request_cert", "rancher_member_manage", "role_rancher",
    "admin_dashboard", "admin_approval", "admin_reject", "admin_assign_inspector", "admin_clarification", "role_admin",
    "traceability_timeline", "role_traceability",
    "output2_growth", "role_output2",
    "output3_biomass", "role_output3",
    "all_roles", "role_all"
]


class FEDEGANLoadTestShape(LoadTestShape):
    """
    Bộ điều khiển hình dạng tải (Load Shape) theo Mục 6 của tài liệu kỹ thuật & 20 Kịch bản theo Role:
    - 20 Kịch bản thao tác theo Role:
        1. inspector_audit         : Thanh tra viên thẩm định & lập biên bản kiểm tra hiện trường
        2. inspector_schedule      : Thanh tra viên quản lý & đặt lịch thanh tra trang trại
        3. inspector_cert          : Thanh tra viên tra cứu & thẩm định hồ sơ chứng chỉ
        4. slaughter_lote          : Nhà máy giết mổ tiếp nhận & tạo lô mổ mới (Batch write)
        5. slaughter_audit         : Nhà máy giết mổ tra cứu chi tiết lô & nhật ký quét barcode
        6. slaughter_external      : Nhà máy giết mổ thống kê & gọi API ngoài (<= 20 connections)
        7. rancher_manage          : Chủ trang trại quản lý nông trại, xem chứng nhận & nhân sự
        8. rancher_create          : Chủ trang trại đăng ký mới trang trại (DB write transaction)
        9. rancher_gis             : Chủ trang trại cập nhật tọa độ ranh giới đất GIS Polygon
        10. admin_dashboard        : Quản trị FEDEGAN theo dõi Dashboard & quản lý người dùng
        11. admin_approval         : Quản trị FEDEGAN thẩm định hồ sơ & phê duyệt chứng chỉ
        12. traceability_timeline  : Người dùng truy xuất dòng đời gia súc SQL Heavy JOIN
        13. admin_reject           : Quản trị FEDEGAN thẩm định & từ chối cấp chứng chỉ (Rejected)
        14. output2_growth         : Người dùng công cộng phân tích mô hình tăng trưởng gia súc
        15. output3_biomass        : Người dùng phân tích ảnh viễn thám AI Sentinel-2 BPS sinh khối
        16. rancher_request_cert   : Chủ trang trại nộp đơn xin cấp chứng nhận bò ăn cỏ Grass Fed
        17. admin_assign_inspector : Quản trị FEDEGAN phân công thanh tra viên cho hồ sơ trang trại
        18. admin_clarification    : Quản trị FEDEGAN yêu cầu trang trại giải trình & bổ sung hồ sơ
        19. rancher_member_manage  : Chủ trang trại quản lý nhân sự, công nhân nông trại (Farmers)
        20. slaughter_plant_network: Giám sát chuỗi cung ứng cơ sở & Dòng đời gia súc liên cơ sở
    - Kịch bản tải hệ thống:
        baseline, peak, stress, bottleneck, breakingpoint, spike, step, soak, doublespike
    """
    _role_users = int(os.getenv("USERS", "100"))
    _role_spawn = int(os.getenv("SPAWN_RATE", "20"))
    _role_duration = int(os.getenv("DURATION", "180"))

    # 1. Kịch bản Spike (Bắn lớn ngay từ đầu): Cấu hình qua USERS (mặc định 800) và DURATION (mặc định 180s)
    _spike_users = int(os.getenv("USERS", os.getenv("SPIKE_USERS", "800")))
    _spike_spawn = int(os.getenv("SPAWN_RATE", "200"))
    _spike_duration = int(os.getenv("DURATION", "180"))
    spike_stages = [
        {"duration": max(30, _spike_duration - 20), "users": _spike_users, "spawn_rate": _spike_spawn},
        {"duration": _spike_duration, "users": 0, "spawn_rate": 50},
    ]

    # 2. Kịch bản Step / Gradual (Tăng từ từ từng bậc thang): Bắt đầu 50 users
    step_stages = [
        {"duration": 40,  "users": 50,   "spawn_rate": 5},   # Bậc 1 (0-40s): 50 users (rất nhẹ)
        {"duration": 80,  "users": 150,  "spawn_rate": 10},  # Bậc 2 (40-80s): 150 users
        {"duration": 120, "users": 300,  "spawn_rate": 15},  # Bậc 3 (80-120s): 300 users
        {"duration": 160, "users": 500,  "spawn_rate": 20},  # Bậc 4 (120-160s): 500 users
        {"duration": 200, "users": 750,  "spawn_rate": 25},  # Bậc 5 (160-200s): 750 users
        {"duration": 240, "users": 1000, "spawn_rate": 30},  # Bậc 6 (200-240s): 1.000 users
        {"duration": 270, "users": 0,    "spawn_rate": 50},  # Cooldown (240-270s): Hạ tải về 0
    ]

    # 3. Kịch bản 5 phút tăng từ từ lên 2.000 Users tìm điểm nghẽn cổ chai (Bottleneck Discovery)
    bottleneck_stages = [
        {"duration": 60, "users": 200, "spawn_rate": 10},    # Phút 1 (0-60s): 200 users khởi động
        {"duration": 120, "users": 500, "spawn_rate": 15},   # Phút 2 (60-120s): 500 users tải trung bình
        {"duration": 180, "users": 1000, "spawn_rate": 20},  # Phút 3 (120-180s): 1.000 users tiệm cận ngưỡng nghẽn
        {"duration": 240, "users": 1500, "spawn_rate": 25},  # Phút 4 (180-240s): 1.500 users ép tải mạnh
        {"duration": 300, "users": 2000, "spawn_rate": 30},  # Phút 5 (240-300s): Đỉnh 2.000 users kiểm tra Breaking Point
    ]

    # 4. Kịch bản 6.1 Baseline: 700 concurrent users trong 10 phút
    baseline_stages = [
        {"duration": 120, "users": 350, "spawn_rate": 10},
        {"duration": 480, "users": 700, "spawn_rate": 15},
        {"duration": 600, "users": 0, "spawn_rate": 20},
    ]

    # 5. Kịch bản 6.2 Peak Load: Tăng tốc lũy tiến lên mốc tải đỉnh
    peak_stages = [
        {"duration": 180, "users": 2000, "spawn_rate": 50},
        {"duration": 420, "users": 8000, "spawn_rate": 100},
        {"duration": 720, "users": 15000, "spawn_rate": 150},
        {"duration": 900, "users": 0, "spawn_rate": 100},
    ]

    # 6. Kịch bản 6.3 Stress & Recovery: Đẩy vượt ngưỡng để tìm Breaking Point rồi hạ tải
    stress_stages = [
        {"duration": 180, "users": 3000, "spawn_rate": 50},
        {"duration": 420, "users": 10000, "spawn_rate": 100},
        {"duration": 720, "users": 25000, "spawn_rate": 200},  # Vượt đỉnh tìm điểm gãy
        {"duration": 900, "users": 700, "spawn_rate": 100},    # Hạ tải về Baseline đo phục hồi
        {"duration": 1080, "users": 0, "spawn_rate": 50},
    ]

    # 7. Kịch bản Soak / Endurance Test: Ngâm tải dài hạn phát hiện Memory Leak & DB Pool Exhaustion
    _soak_users = int(os.getenv("USERS", os.getenv("SOAK_USERS", "350")))
    _soak_duration = int(os.getenv("DURATION", os.getenv("SOAK_DURATION", "3600")))
    _soak_spawn = int(os.getenv("SPAWN_RATE", os.getenv("SOAK_SPAWN_RATE", "15")))
    _soak_ramp = min(300, max(60, int(_soak_duration * 0.08)))
    _soak_cool = min(120, max(30, int(_soak_duration * 0.05)))
    soak_stages = [
        {"duration": _soak_ramp, "users": _soak_users, "spawn_rate": _soak_spawn},
        {"duration": max(_soak_ramp + 30, _soak_duration - _soak_cool), "users": _soak_users, "spawn_rate": _soak_spawn},
        {"duration": _soak_duration, "users": 0, "spawn_rate": 30},
    ]

    # 8. Kịch bản Double-Spike / Dual-Peak: Sốc tải kép mô phỏng 2 đỉnh giờ cao điểm (Morning & Afternoon Peak)
    _d_spike1 = int(os.getenv("SPIKE1_USERS", "900"))
    _d_spike2 = int(os.getenv("SPIKE2_USERS", "1200"))
    _d_base = int(os.getenv("BASE_USERS", "100"))
    doublespike_stages = [
        {"duration": 60,  "users": _d_base,   "spawn_rate": 20},   # Giai đoạn 1: Khởi động với tải nền nhẹ
        {"duration": 180, "users": _d_spike1, "spawn_rate": 150},  # Giai đoạn 2: Cú sốc 1 (Morning Peak)
        {"duration": 300, "users": _d_base,   "spawn_rate": 50},   # Giai đoạn 3: Hạ tải kiểm tra phục hồi (Recovery Phase)
        {"duration": 450, "users": _d_spike2, "spawn_rate": 200},  # Giai đoạn 4: Cú sốc 2 (Afternoon Peak vượt ngưỡng trước)
        {"duration": 510, "users": 0,         "spawn_rate": 50},   # Giai đoạn 5: Cooldown hạ tải về 0 an toàn
    ]

    def get_continuous_target(self, run_time):
        """Hàm tính toán tăng tải liên tục: Cứ mỗi 15 giây tăng thêm 250 users"""
        step = int(run_time // 15)
        target = 500 + (step * 250)
        spawn_rate = min(20 + (step * 5), 100)
        return target, spawn_rate

    def tick(self):
        run_time = self.get_run_time()

        # Nếu không đặt SCENARIO hoặc SCENARIO không nằm trong danh sách điều phối tự động: bỏ qua để dùng interactive
        if TEST_SCENARIO not in SCENARIO_LIST:
            return None

        # KỊCH BẢN TĂNG LIÊN TỤC TỚI KHI NGHẼN (AUTO-STOP BREAKING POINT SEARCH)
        if TEST_SCENARIO in ["breakingpoint", "continuous", "autostop"]:
            if run_time > 25 and state.GLOBAL_LOCUST_ENV and state.GLOBAL_LOCUST_ENV.stats:
                stats = state.GLOBAL_LOCUST_ENV.stats.total
                if stats.num_requests >= 300:
                    fail_ratio = stats.fail_ratio
                    p95 = stats.get_current_response_time_percentile(0.95) or 0
                    current_rps = stats.total_rps

                    if fail_ratio >= 0.05 or p95 >= 15000:
                        current_users = self.get_current_user_count()
                        reason = (
                            f"Tỷ lệ lỗi tăng vọt {fail_ratio * 100:.2f}% (>= 5.0% - Server quá tải)"
                            if fail_ratio >= 0.05
                            else f"Độ trễ P95 chạm ngưỡng {p95:.0f} ms (>= 15.0s - Quá giới hạn 10s)"
                        )
                        print("\n" + "=" * 90)
                        print(f"🚨 PHÁT HIỆN ĐIỂM NGHẼN CỔ CHAI / BREAKING POINT TẠI MỐC: {current_users} USERS!")
                        print(f"   • Dấu hiệu nghẽn                 : {reason}")
                        print(f"   • Thời gian chịu đựng trước nghẽn: {int(run_time)} giây (~{run_time/60:.1f} phút)")
                        print(f"   • Tỷ lệ lỗi tại điểm gãy         : {fail_ratio * 100:.2f}%")
                        print(f"   • Độ trễ P95 tại điểm gãy        : {p95:.0f} ms")
                        print(f"   • Thông lượng đạt được           : {current_rps:.2f} req/s")
                        print(f"🛑 Tự động DỪNG TEST ngay lập tức để bảo vệ server và kích hoạt Cleanup...")
                        print("=" * 90 + "\n")
                        return None

            target, rate = self.get_continuous_target(run_time)
            return target, rate

        if TEST_SCENARIO in ["spike", "shock", "flashcrowd"]:
            stages = self.spike_stages
        elif TEST_SCENARIO in ["step", "gradual", "ladder"]:
            stages = self.step_stages
        elif TEST_SCENARIO in ["bottleneck", "rampup"]:
            stages = self.bottleneck_stages
        elif TEST_SCENARIO == "baseline":
            stages = self.baseline_stages
        elif TEST_SCENARIO == "stress":
            stages = self.stress_stages
        elif TEST_SCENARIO in ["soak", "endurance"]:
            stages = self.soak_stages
        elif TEST_SCENARIO in ["doublespike", "dualspike", "twospike"]:
            stages = self.doublespike_stages
        elif TEST_SCENARIO in ["inspector_audit", "inspector_schedule", "inspector_cert", "role_inspector"]:
            u = int(os.getenv("USERS", "100"))
            d = int(os.getenv("DURATION", "180"))
            s = int(os.getenv("SPAWN_RATE", "15"))
            stages = [{"duration": d, "users": u, "spawn_rate": s}]
        elif TEST_SCENARIO in ["slaughter_lote", "slaughter_audit", "slaughter_external", "slaughter_plant_network", "role_slaughterhouse"]:
            u = int(os.getenv("USERS", "50"))
            d = int(os.getenv("DURATION", "180"))
            s = int(os.getenv("SPAWN_RATE", "10"))
            stages = [{"duration": d, "users": u, "spawn_rate": s}]
        elif TEST_SCENARIO in ["rancher_manage", "rancher_create", "rancher_gis", "rancher_request_cert", "rancher_member_manage", "role_rancher"]:
            u = int(os.getenv("USERS", "500"))
            d = int(os.getenv("DURATION", "180"))
            s = int(os.getenv("SPAWN_RATE", "25"))
            stages = [{"duration": d, "users": u, "spawn_rate": s}]
        elif TEST_SCENARIO in ["admin_dashboard", "admin_approval", "admin_reject", "admin_assign_inspector", "admin_clarification", "role_admin"]:
            u = int(os.getenv("USERS", "50"))
            d = int(os.getenv("DURATION", "180"))
            s = int(os.getenv("SPAWN_RATE", "10"))
            stages = [{"duration": d, "users": u, "spawn_rate": s}]
        elif TEST_SCENARIO in ["traceability_timeline", "role_traceability"]:
            u = int(os.getenv("USERS", "100"))
            d = int(os.getenv("DURATION", "180"))
            s = int(os.getenv("SPAWN_RATE", "15"))
            stages = [{"duration": d, "users": u, "spawn_rate": s}]
        elif TEST_SCENARIO in ["output2_growth", "role_output2"]:
            u = int(os.getenv("USERS", "100"))
            d = int(os.getenv("DURATION", "180"))
            s = int(os.getenv("SPAWN_RATE", "20"))
            stages = [{"duration": d, "users": u, "spawn_rate": s}]
        elif TEST_SCENARIO in ["output3_biomass", "role_output3"]:
            u = int(os.getenv("USERS", "50"))
            d = int(os.getenv("DURATION", "180"))
            s = int(os.getenv("SPAWN_RATE", "10"))
            stages = [{"duration": d, "users": u, "spawn_rate": s}]
        elif TEST_SCENARIO in ["all_roles", "role_all"]:
            u = int(os.getenv("USERS", "100"))
            d = int(os.getenv("DURATION", "180"))
            s = int(os.getenv("SPAWN_RATE", "20"))
            stages = [{"duration": d, "users": u, "spawn_rate": s}]
        else:
            stages = self.peak_stages

        for stage in stages:
            if run_time < stage["duration"]:
                return stage["users"], stage["spawn_rate"]

        return None

