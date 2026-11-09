#!/usr/bin/env bash
# ==============================================================================
# TIỆN ÍCH CHẠY KIỂM THỬ TẢI SATREPS FEDEGAN (LOCUST RUNNER)
# Hỗ trợ đầy đủ 15 Kịch bản thao tác người dùng theo từng Role & Kịch bản tải hệ thống
# ==============================================================================

set -e

HOST="${HOST:-https://satreps-api-427991251928.us-central1.run.app}"
SCENARIO="${1:-help}"
HTML_REPORT="kq/report_${SCENARIO}.html"

mkdir -p kq

if [ "$SCENARIO" = "help" ] || [ "$SCENARIO" = "--help" ] || [ "$SCENARIO" = "-h" ] || [ "$SCENARIO" = "list" ]; then
  echo "=============================================================================="
  echo "📋 DANH SÁCH 20 KỊCH BẢN THAO TÁC THEO TỪNG ROLE (SATREPS FEDEGAN)"
  echo "=============================================================================="
  echo "Cú pháp: ./run_test.sh <tên_kịch_bản>"
  echo "Tùy biến tham số (tùy chọn): USERS=... DURATION=... ./run_test.sh <tên_kịch_bản>"
  echo ""
  echo "📍 NHÓM 1: ROLE THANH TRA VIÊN (INSPECTOR)"
  echo "  1.  inspector_audit       : Thẩm định hồ sơ & Lập biên bản kiểm tra thực địa"
  echo "  2.  inspector_schedule    : Tra cứu lịch & Đặt lịch kiểm định trang trại"
  echo "  3.  inspector_cert        : Thẩm định hồ sơ chứng chỉ & Lấy danh sách tổ chức"
  echo ""
  echo "📍 NHÓM 2: ROLE NHÀ MÁY GIẾT MỔ (SLAUGHTERHOUSE)"
  echo "  4.  slaughter_lote        : Tiếp nhận lô gia súc & Tạo mới lô mổ hàng loạt"
  echo "  5.  slaughter_audit       : Giám sát chi tiết lô mổ & Nhật ký quét mã Barcode"
  echo "  6.  slaughter_external    : Thống kê động vật & Gọi dịch vụ ngoài (External API <= 20)"
  echo "  20. slaughter_plant_network: Giám sát chuỗi cung ứng cơ sở & Dòng đời gia súc liên cơ sở"
  echo ""
  echo "📍 NHÓM 3: ROLE CHỦ TRANG TRẠI (RANCHER / FARMER)"
  echo "  7.  rancher_manage        : Quản lý nông trại, xem chứng nhận & danh sách nông dân"
  echo "  8.  rancher_create        : Đăng ký mới trang trại thử nghiệm (DB Write + Auto Cleanup)"
  echo "  9.  rancher_gis           : Cập nhật ranh giới bản đồ GIS đồng cỏ (GIS Polygon PUT)"
  echo "  16. rancher_request_cert  : Nộp đơn xin cấp chứng nhận bò ăn cỏ Grass Fed (POST /api/events/create)"
  echo "  19. rancher_member_manage : Quản lý nhân sự, mời công nhân nông trại (GET/POST /api/farmer/*)"
  echo ""
  echo "📍 NHÓM 4: ROLE QUẢN TRỊ VIÊN FEDEGAN (CENTRAL ADMIN)"
  echo "  10. admin_dashboard       : Dashboard điều hành toàn quốc & Quản lý danh sách User"
  echo "  11. admin_approval        : Thẩm định chi tiết hồ sơ & Phê duyệt cấp chứng chỉ bò ăn cỏ"
  echo "  13. admin_reject          : Thẩm định hồ sơ & Từ chối cấp chứng chỉ (POST /api/fedegan/reject-certification)"
  echo "  17. admin_assign_inspector: Phân công thanh tra viên cho hồ sơ trang trại (POST /api/fedegan/assign-inspector)"
  echo "  18. admin_clarification   : Yêu cầu trang trại giải trình & bổ sung hồ sơ (POST /api/fedegan/request-clarification)"
  echo ""
  echo "📍 NHÓM 5: ROLE TRUY XUẤT NGUỒN GỐC (MANUAL TRACEABILITY)"
  echo "  12. traceability_timeline : Tra cứu dòng đời gia súc SQL Heavy JOIN 4 bảng"
  echo ""
  echo "📍 NHÓM 6: PHÂN HỆ OUTPUT 2 (ANIMAL GROWTH ANALYSIS)"
  echo "  14. output2_growth        : Mô hình phân tích đường cong tăng trưởng sinh thái"
  echo ""
  echo "📍 NHÓM 7: PHÂN HỆ OUTPUT 3 (GEOSPATIAL BIOMASS & ML MODEL)"
  echo "  15. output3_biomass       : Giám sát đồng cỏ & Thực thi mô hình AI Sentinel-2 BPS"
  echo ""
  echo "=============================================================================="
  echo "👥 CÁC LỆNH CHẠY TỔNG HỢP THEO ROLE"
  echo "  • role_inspector         : Chạy kết hợp Kịch bản 1, 2, 3"
  echo "  • role_slaughterhouse    : Chạy kết hợp Kịch bản 4, 5, 6, 20"
  echo "  • role_rancher           : Chạy kết hợp Kịch bản 7, 8, 9, 16, 19"
  echo "  • role_admin             : Chạy kết hợp Kịch bản 10, 11, 13, 17, 18"
  echo "  • all_roles              : Chạy đồng thời TẤT CẢ các Role (Toàn bộ 20 kịch bản cùng lúc)"
  echo ""
  echo "=============================================================================="
  echo "🌐 KỊCH BẢN TẢI HỆ THỐNG TOÀN DIỆN (SYSTEM LOAD SHAPES)"
  echo "  • baseline       : Tải chuẩn 700 Users trong 10 phút (Mục 6.1 doc.txt)"
  echo "  • peak           : Tải đỉnh lũy tiến lên 15.000 Users (Mục 6.2 doc.txt)"
  echo "  • stress         : Vượt đỉnh 25.000 Users đo phục hồi (Mục 6.3 doc.txt)"
  echo "  • bottleneck     : Tăng 5 giai đoạn 200 -> 2.000 Users tìm điểm nghẽn"
  echo "  • breakingpoint  : Tăng liên tục tìm Điểm gãy tự động dừng"
  echo "  • spike          : Sốc tải tức thì (Flash Crowd 800-1.200 Users)"
  echo "  • step           : Tăng từng bậc thang nhỏ (Step Ramp 50 -> 1.000 Users)"
  echo "  • soak           : Ngâm tải dài hạn 1 giờ (Soak Test 350 Users)"
  echo "  • doublespike    : Sốc tải kép 2 đỉnh sáng & chiều (900 -> 1.200 Users)"
  echo "  • interactive    : Mở giao diện Web UI Locust tại http://0.0.0.0:8089"
  echo "=============================================================================="
  exit 0
fi

echo "=============================================================================="
echo "🚀 KHỞI ĐỘNG KIỂM THỬ HIỆU NĂNG SATREPS"
echo "• Host mục tiêu  : $HOST"
echo "• Kịch bản chạy  : $SCENARIO"
echo "• Báo cáo đầu ra : $HTML_REPORT"
echo "=============================================================================="

case "$SCENARIO" in
  interactive)
    echo "🌐 Đang mở Locust Web UI tại http://0.0.0.0:8089 ..."
    ./venv/bin/locust -f locustfile_integrated.py -H "$HOST"
    ;;
  
  # --- 15 KỊCH BẢN THAO TÁC THEO TỪNG ROLE ---
  inspector_audit)
    echo "📋 Đang chạy Kịch bản 1: Thanh tra viên thẩm định & Lập biên bản hiện trường..."
    SCENARIO=inspector_audit LOCUST_USER_CLASSES=Scenario1_InspectorAuditUser USERS="${USERS:-100}" DURATION="${DURATION:-180}" ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --html "$HTML_REPORT"
    ;;
  inspector_schedule)
    echo "📅 Đang chạy Kịch bản 2: Thanh tra viên tra cứu & Đặt lịch kiểm định..."
    SCENARIO=inspector_schedule LOCUST_USER_CLASSES=Scenario2_InspectorScheduleUser USERS="${USERS:-100}" DURATION="${DURATION:-180}" ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --html "$HTML_REPORT"
    ;;
  inspector_cert)
    echo "📜 Đang chạy Kịch bản 3: Thanh tra viên thẩm định & Tải chứng chỉ số..."
    SCENARIO=inspector_cert LOCUST_USER_CLASSES=Scenario3_InspectorCertUser USERS="${USERS:-100}" DURATION="${DURATION:-180}" ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --html "$HTML_REPORT"
    ;;
  slaughter_lote)
    echo "🥩 Đang chạy Kịch bản 4: Lò mổ tiếp nhận & Tạo lô gia súc mới (Batch write)..."
    SCENARIO=slaughter_lote LOCUST_USER_CLASSES=Scenario4_SlaughterLoteUser USERS="${USERS:-50}" DURATION="${DURATION:-180}" ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --html "$HTML_REPORT"
    ;;
  slaughter_audit)
    echo "🔍 Đang chạy Kịch bản 5: Lò mổ tra cứu chi tiết lô mổ & Nhật ký barcode..."
    SCENARIO=slaughter_audit LOCUST_USER_CLASSES=Scenario5_SlaughterAuditUser USERS="${USERS:-50}" DURATION="${DURATION:-180}" ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --html "$HTML_REPORT"
    ;;
  slaughter_external)
    echo "🌐 Đang chạy Kịch bản 6: Lò mổ thống kê & Gọi dịch vụ ngoài (External API <= 20)..."
    SCENARIO=slaughter_external LOCUST_USER_CLASSES=Scenario6_SlaughterExternalUser USERS="${USERS:-50}" DURATION="${DURATION:-180}" ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --html "$HTML_REPORT"
    ;;
  rancher_manage)
    echo "🏡 Đang chạy Kịch bản 7: Chủ trại quản lý nông trại, xem chứng nhận & nhân sự..."
    SCENARIO=rancher_manage LOCUST_USER_CLASSES=Scenario7_RancherManageUser USERS="${USERS:-500}" DURATION="${DURATION:-180}" ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --html "$HTML_REPORT"
    ;;
  rancher_create)
    echo "📝 Đang chạy Kịch bản 8: Chủ trại đăng ký mới trang trại (DB write transaction)..."
    SCENARIO=rancher_create LOCUST_USER_CLASSES=Scenario8_RancherCreateUser USERS="${USERS:-200}" DURATION="${DURATION:-180}" ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --html "$HTML_REPORT"
    ;;
  rancher_gis)
    echo "🗺️ Đang chạy Kịch bản 9: Chủ trại cập nhật ranh giới đất GIS Polygon..."
    SCENARIO=rancher_gis LOCUST_USER_CLASSES=Scenario9_RancherGisUser USERS="${USERS:-300}" DURATION="${DURATION:-180}" ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --html "$HTML_REPORT"
    ;;
  admin_dashboard)
    echo "📊 Đang chạy Kịch bản 10: Quản trị FEDEGAN theo dõi Dashboard & Quản lý User..."
    SCENARIO=admin_dashboard LOCUST_USER_CLASSES=Scenario10_AdminDashboardUser USERS="${USERS:-50}" DURATION="${DURATION:-180}" ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --html "$HTML_REPORT"
    ;;
  admin_approval)
    echo "✅ Đang chạy Kịch bản 11: Quản trị FEDEGAN thẩm định & Phê duyệt chứng chỉ..."
    SCENARIO=admin_approval LOCUST_USER_CLASSES=Scenario11_AdminApprovalUser USERS="${USERS:-50}" DURATION="${DURATION:-180}" ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --html "$HTML_REPORT"
    ;;
  traceability_timeline)
    echo "⛓️ Đang chạy Kịch bản 12: Truy xuất nguồn gốc SQL Heavy JOIN qua 4 bảng..."
    SCENARIO=traceability_timeline LOCUST_USER_CLASSES=Scenario12_TraceabilityTimelineUser USERS="${USERS:-100}" DURATION="${DURATION:-180}" ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --html "$HTML_REPORT"
    ;;
  admin_reject)
    echo "❌ Đang chạy Kịch bản 13: Quản trị viên thẩm định & Từ chối cấp chứng chỉ..."
    SCENARIO=admin_reject LOCUST_USER_CLASSES=Scenario13_AdminRejectUser USERS="${USERS:-50}" DURATION="${DURATION:-180}" ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --html "$HTML_REPORT"
    ;;
  output2_growth)
    echo "📈 Đang chạy Kịch bản 14: Mô hình dự báo đường cong tăng trưởng động vật (Output 2)..."
    SCENARIO=output2_growth LOCUST_USER_CLASSES=Scenario14_Output2GrowthUser USERS="${USERS:-100}" DURATION="${DURATION:-180}" ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --html "$HTML_REPORT"
    ;;
  output3_biomass)
    echo "🛰️ [THÔNG BÁO] Kịch bản 15 (Output 3: Giám sát đồng cỏ & Mô hình AI Sentinel-2 BPS) hiện đã được comment out."
    # SCENARIO=output3_biomass LOCUST_USER_CLASSES=Scenario15_Output3BiomassUser USERS="${USERS:-50}" DURATION="${DURATION:-180}" ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --html "$HTML_REPORT"
    ;;
  rancher_request_cert)
    echo "📋 Đang chạy Kịch bản 16: Chủ trại nộp đơn xin cấp chứng nhận bò ăn cỏ Grass Fed..."
    SCENARIO=rancher_request_cert LOCUST_USER_CLASSES=Scenario16_RancherRequestCertUser USERS="${USERS:-200}" DURATION="${DURATION:-180}" ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --html "$HTML_REPORT"
    ;;
  admin_assign_inspector)
    echo "🧑‍⚖️ Đang chạy Kịch bản 17: Quản trị viên phân công thanh tra viên cho trang trại..."
    SCENARIO=admin_assign_inspector LOCUST_USER_CLASSES=Scenario17_AdminAssignInspectorUser USERS="${USERS:-50}" DURATION="${DURATION:-180}" ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --html "$HTML_REPORT"
    ;;
  admin_clarification)
    echo "📨 Đang chạy Kịch bản 18: Quản trị viên yêu cầu trang trại giải trình hồ sơ..."
    SCENARIO=admin_clarification LOCUST_USER_CLASSES=Scenario18_AdminClarificationUser USERS="${USERS:-50}" DURATION="${DURATION:-180}" ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --html "$HTML_REPORT"
    ;;
  rancher_member_manage)
    echo "👥 Đang chạy Kịch bản 19: Chủ trại quản lý nhân sự & nông dân (Farmers)..."
    SCENARIO=rancher_member_manage LOCUST_USER_CLASSES=Scenario19_RancherMemberManageUser USERS="${USERS:-200}" DURATION="${DURATION:-180}" ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --html "$HTML_REPORT"
    ;;
  slaughter_plant_network)
    echo "🏭 Đang chạy Kịch bản 20: Giám sát chuỗi cung ứng cơ sở & Dòng đời gia súc liên cơ sở..."
    SCENARIO=slaughter_plant_network LOCUST_USER_CLASSES=Scenario20_SlaughterPlantNetworkUser USERS="${USERS:-100}" DURATION="${DURATION:-180}" ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --html "$HTML_REPORT"
    ;;

  # --- CÁC NHÓM ROLE TỔNG HỢP ---
  role_inspector)
    echo "🧑‍💼 Đang chạy tổng hợp Role: Thanh tra viên (Inspector - 3 kịch bản)..."
    SCENARIO=role_inspector LOCUST_USER_CLASSES="Scenario1_InspectorAuditUser Scenario2_InspectorScheduleUser Scenario3_InspectorCertUser" USERS="${USERS:-100}" DURATION="${DURATION:-180}" ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --run-time "${DURATION:-180}s" --html "$HTML_REPORT"
    ;;
  role_slaughterhouse)
    echo "🏭 Đang chạy tổng hợp Role: Nhà máy giết mổ (Slaughterhouse - 4 kịch bản)..."
    SCENARIO=role_slaughterhouse LOCUST_USER_CLASSES="Scenario4_SlaughterLoteUser Scenario5_SlaughterAuditUser Scenario6_SlaughterExternalUser Scenario20_SlaughterPlantNetworkUser" USERS="${USERS:-50}" DURATION="${DURATION:-180}" ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --run-time "${DURATION:-180}s" --html "$HTML_REPORT"
    ;;
  role_rancher)
    echo "🚜 Đang chạy tổng hợp Role: Chủ trang trại (Rancher - 5 kịch bản)..."
    SCENARIO=role_rancher LOCUST_USER_CLASSES="Scenario7_RancherManageUser Scenario8_RancherCreateUser Scenario9_RancherGisUser Scenario16_RancherRequestCertUser Scenario19_RancherMemberManageUser" USERS="${USERS:-500}" DURATION="${DURATION:-180}" ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --run-time "${DURATION:-180}s" --html "$HTML_REPORT"
    ;;
  role_admin)
    echo "👑 Đang chạy tổng hợp Role: Quản trị viên FEDEGAN (Admin - 5 kịch bản)..."
    SCENARIO=role_admin LOCUST_USER_CLASSES="Scenario10_AdminDashboardUser Scenario11_AdminApprovalUser Scenario13_AdminRejectUser Scenario17_AdminAssignInspectorUser Scenario18_AdminClarificationUser" USERS="${USERS:-50}" DURATION="${DURATION:-180}" ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --run-time "${DURATION:-180}s" --html "$HTML_REPORT"
    ;;
  all_roles|role_all)
    echo "🌐 Đang chạy TẤT CẢ CÁC ROLE CÙNG LÚC (20 Kịch bản thao tác người dùng)..."
    SCENARIO=all_roles USERS="${USERS:-100}" DURATION="${DURATION:-180}" SPAWN_RATE="${SPAWN_RATE:-20}" ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" -u "${USERS:-100}" -r "${SPAWN_RATE:-20}" --run-time "${DURATION:-180}s" --html "$HTML_REPORT"
    ;;


  # --- KỊCH BẢN TẢI HỆ THỐNG CHUẨN ---
  baseline)
    echo "📊 Đang chạy Kịch bản Baseline chuẩn 700 Users (Mục 6.1)..."
    SCENARIO=baseline ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --html "$HTML_REPORT"
    ;;
  peak)
    echo "🚀 Đang chạy Kịch bản Tải đỉnh lũy tiến lên 15.000 Users (Mục 6.2)..."
    SCENARIO=peak ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --html "$HTML_REPORT"
    ;;
  stress)
    echo "🔥 Đang chạy Kịch bản Vượt ngưỡng Stress 25.000 Users đo phục hồi (Mục 6.3)..."
    SCENARIO=stress ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --html "$HTML_REPORT"
    ;;
  spike)
    echo "⚡ Đang chạy Kịch bản Sốc tải tức thì (Spike / Shock Test)..."
    SCENARIO=spike SPIKE_USERS="${USERS:-800}" DURATION="${DURATION:-180}" ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --html "$HTML_REPORT"
    ;;
  step)
    echo "📈 Đang chạy Kịch bản Tăng tuyến tính bậc thang (Step-Ramp 50 -> 1.000 Users)..."
    SCENARIO=step ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --html "$HTML_REPORT"
    ;;
  bottleneck)
    echo "🔍 Đang chạy Kịch bản Dò tìm điểm nghẽn 5 phút (200 -> 2.000 Users)..."
    SCENARIO=bottleneck ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --html "$HTML_REPORT"
    ;;
  breakingpoint)
    echo "💥 Đang chạy Kịch bản Tăng liên tục tìm Điểm gãy tự ngắt..."
    SCENARIO=breakingpoint ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --html "$HTML_REPORT"
    ;;
  soak)
    echo "⏱️ Đang chạy Kịch bản Ngâm tải dài hạn 1 giờ (Soak Test 350 Users)..."
    SCENARIO=soak SOAK_USERS="${USERS:-350}" SOAK_DURATION="${DURATION:-3600}" ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --html "$HTML_REPORT"
    ;;
  doublespike)
    echo "🌊 Đang chạy Kịch bản Sốc tải kép 2 đỉnh (Double-Spike 900 -> 1.200 Users)..."
    SCENARIO=doublespike SPIKE1_USERS="${SPIKE1_USERS:-900}" SPIKE2_USERS="${SPIKE2_USERS:-1200}" ./venv/bin/locust -f locustfile_integrated.py --headless -H "$HOST" --html "$HTML_REPORT"
    ;;
  *)
    echo "❌ Kịch bản '$SCENARIO' không tồn tại!"
    echo "Gõ './run_test.sh help' để xem danh sách 15 kịch bản theo role và các kịch bản tải hệ thống."
    exit 1
    ;;
esac
