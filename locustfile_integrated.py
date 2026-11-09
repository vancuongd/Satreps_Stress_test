"""
==============================================================================
HỆ THỐNG KIỂM THỬ HIỆU NĂNG TÍCH HỢP SATREPS FEDEGAN (LOCUST 2.46.7)
Theo Đặc tả Kỹ thuật: "Technical Specification: Stress Testing Services for SATREPS systems"
Hỗ trợ đầy đủ 15 Kịch bản thao tác người dùng theo từng Role & Kịch bản tải hệ thống
==============================================================================
Cấu trúc module hóa:
  - config/    : Cấu hình biến môi trường, kịch bản tải, seed data
  - core/      : Quản lý xác thực (JWT), bộ nhớ đệm state, BaseUser (Distributed IP)
  - users/     : Các User Persona theo 4 phân hệ kỹ thuật (Traceability, Inspector, Slaughterhouse, Rancher, Admin, Visitor, Output2, Output3)
  - scenarios/ : Bộ điều khiển LoadTestShape (Baseline, Spike, BreakingPoint,...) & 15 Kịch bản thao tác theo Role
  - hooks/     : Trình lắng nghe sự kiện Locust (Logging lỗi, Tổng kết, Tự động dọn dẹp dữ liệu DB)
==============================================================================
"""

import sys
import os

# Đảm bảo đường dẫn module hiện tại nằm trong PYTHONPATH
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from config.settings import TEST_SCENARIO
from core.base_user import BaseSatrepsUser
from core.state import (
    DYNAMIC_DATA,
    CREATED_TEST_IDS,
    CLEANUP_LOCK,
    EXTERNAL_API_SEMAPHORE,
)
from core.auth import AUTH_TOKENS, create_traced_headers

# 1. Nhập các lớp User Persona chính của hệ sinh thái
from users.traceability import ManualTraceabilityUser
from users.inspector import GrassFedInspectorUser
from users.slaughterhouse import GrassFedSlaughterhouseUser
from users.rancher import GrassFedRancherUser
from users.admin import FedeganAdminUser
from users.output2_growth import Output2GrowthAnalysisUser
# Phân hệ Output 3 tạm thời comment out theo yêu cầu
# from users.output3_biomass import (
#     Output3GeospatialBiomassUser,
#     Output3BiomassAnalyticalModelUser,
# )

# 2. Nhập 20 Kịch bản thao tác người dùng theo từng Role
from scenarios.role_scenarios import (
    ROLE_SCENARIOS_MAP,
    Scenario1_InspectorAuditUser,
    Scenario2_InspectorScheduleUser,
    Scenario3_InspectorCertUser,
    Scenario4_SlaughterLoteUser,
    Scenario5_SlaughterAuditUser,
    Scenario6_SlaughterExternalUser,
    Scenario7_RancherManageUser,
    Scenario8_RancherCreateUser,
    Scenario9_RancherGisUser,
    Scenario10_AdminDashboardUser,
    Scenario11_AdminApprovalUser,
    Scenario12_TraceabilityTimelineUser,
    Scenario13_AdminRejectUser,
    Scenario14_Output2GrowthUser,
    # Scenario15_Output3BiomassUser,
    Scenario16_RancherRequestCertUser,
    Scenario17_AdminAssignInspectorUser,
    Scenario18_AdminClarificationUser,
    Scenario19_RancherMemberManageUser,
    Scenario20_SlaughterPlantNetworkUser,
)

# 3. Nhập và kích hoạt các Trình lắng nghe sự kiện (Event Hooks)
import hooks.listeners

# 4. Nhập Bộ điều phối tải theo kịch bản (Load Test Shapes)
from scenarios.shapes import SCENARIO_LIST

# Danh sách đầy đủ các lớp có thể chạy
ALL_AVAILABLE_USERS = [
    ManualTraceabilityUser,
    GrassFedInspectorUser,
    GrassFedSlaughterhouseUser,
    GrassFedRancherUser,
    FedeganAdminUser,
    Output2GrowthAnalysisUser,
    # Output3GeospatialBiomassUser,
    # Output3BiomassAnalyticalModelUser,
    Scenario1_InspectorAuditUser,
    Scenario2_InspectorScheduleUser,
    Scenario3_InspectorCertUser,
    Scenario4_SlaughterLoteUser,
    Scenario5_SlaughterAuditUser,
    Scenario6_SlaughterExternalUser,
    Scenario7_RancherManageUser,
    Scenario8_RancherCreateUser,
    Scenario9_RancherGisUser,
    Scenario10_AdminDashboardUser,
    Scenario11_AdminApprovalUser,
    Scenario12_TraceabilityTimelineUser,
    Scenario13_AdminRejectUser,
    Scenario14_Output2GrowthUser,
    # Scenario15_Output3BiomassUser,
    Scenario16_RancherRequestCertUser,
    Scenario17_AdminAssignInspectorUser,
    Scenario18_AdminClarificationUser,
    Scenario19_RancherMemberManageUser,
    Scenario20_SlaughterPlantNetworkUser,
]

# Tự động chọn tập User chạy theo biến môi trường SCENARIO
if TEST_SCENARIO in ROLE_SCENARIOS_MAP:
    # Nếu chạy 1 trong 20 kịch bản thao tác hoặc nhóm Role chuyên biệt
    selected_classes = ROLE_SCENARIOS_MAP[TEST_SCENARIO]
    __all__ = ["BaseSatrepsUser"] + [cls.__name__ for cls in selected_classes]
else:
    # Mặc định (Baseline, Peak, Stress, Interactive, ...): Chạy tải tích hợp toàn bộ các phân hệ chính
    __all__ = [
        "BaseSatrepsUser",
        "ManualTraceabilityUser",
        "GrassFedInspectorUser",
        "GrassFedSlaughterhouseUser",
        "GrassFedRancherUser",
        "FedeganAdminUser",
        "Output2GrowthAnalysisUser",
    ]

# Kích hoạt LoadTestShape khi chạy kịch bản tự động theo biến môi trường SCENARIO
if TEST_SCENARIO in SCENARIO_LIST:
    from scenarios.shapes import FEDEGANLoadTestShape
    __all__.append("FEDEGANLoadTestShape")
