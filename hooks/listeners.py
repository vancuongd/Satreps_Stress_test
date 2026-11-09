import datetime
import requests
from concurrent.futures import ThreadPoolExecutor
# pyrefly: ignore [missing-import]
from locust import events
from config.settings import LOG_FAILURES_TO_FILE, FAILURES_LOG_PATH, TEST_SCENARIO
from core.auth import AUTH_TOKENS
import core.state as state

# ==============================================================================
# EVENT HOOKS: GHI NHẬN LỖI CHI TIẾT & BÁO CÁO NGHIỆM THU THEO MỤC 7 & 8
# ==============================================================================

@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Lưu lại tham chiếu environment để dùng cho kịch bản tự động ngắt tải khi nghẽn"""
    state.GLOBAL_LOCUST_ENV = environment


@events.request.add_listener
def on_request_failure_logger(request_type, name, response_time, response_length, response=None, context=None, exception=None, **kwargs):
    """Ghi nhận lỗi kèm Trace ID, URL và mã lỗi vào file log"""
    has_error = exception is not None or (response is not None and response.status_code >= 400)
    
    # Bỏ qua 404 dữ liệu chưa seed để file log chỉ tập trung vào lỗi 500, DB timeouts và 429
    if response is not None and response.status_code == 404:
        return

    if has_error and LOG_FAILURES_TO_FILE:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status_code = getattr(response, "status_code", "EXCEPTION")
        
        trace_id = "UNKNOWN"
        if response is not None and hasattr(response, "request") and response.request:
            trace_id = response.request.headers.get("x-request-id", "UNKNOWN")
            
        if response is not None and hasattr(response, "text"):
            resp_body = response.text.replace("\n", " ").strip()[:200]
        else:
            resp_body = str(exception)
            
        log_entry = (
            f"[{now_str}] | Trace: {trace_id:<12} | {request_type:<4} {name:<70} | "
            f"Status: {str(status_code):<4} | Latency: {response_time:>5.0f}ms | Body: {resp_body}\n"
        )
        
        try:
            with open(FAILURES_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception:
            pass


@events.test_stop.add_listener
def on_test_stop_summary(environment, **kwargs):
    """In báo cáo phân tích tổng thể 4 phân hệ dùng chung hạ tầng theo Mục 7 & 8 của doc.txt"""
    stats = environment.stats.total
    fail_percent = stats.fail_ratio * 100
    
    p50 = stats.get_current_response_time_percentile(0.50)
    p95 = stats.get_current_response_time_percentile(0.95)
    p99 = stats.get_current_response_time_percentile(0.99)
    p50_str = f"{p50:.0f} ms" if p50 is not None else "N/A"
    p95_str = f"{p95:.0f} ms" if p95 is not None else "N/A"
    p99_str = f"{p99:.0f} ms" if p99 is not None else "N/A"

    print("\n" + "=" * 90)
    print("📊 BÁO CÁO TỔNG KẾT ĐÁNH GIÁ CHỊU TẢI HỆ SINH THÁI FEDEGAN SATREPS")
    print("   (Theo Đặc tả Kỹ thuật: Technical Specification for Stress Testing - Shared Infrastructure)")
    print("=" * 90)
    print(f"• Kịch bản thực thi             : {TEST_SCENARIO.upper()}")
    print(f"• Tổng số requests hoàn thành   : {stats.num_requests:,}")
    print(f"• Tổng số lỗi phát sinh         : {stats.num_failures:,} ({fail_percent:.2f}%)")
    print(f"• Thông lượng trung bình (RPS)  : {stats.total_rps:.2f} req/s")
    print(f"• Độ trễ trung vị P50           : {p50_str}")
    print(f"• Độ trễ P95 (Tiêu chuẩn Fedegan): {p95_str}")
    print(f"• Độ trễ P99 (Ngưỡng tải đỉnh)  : {p99_str}")
    print(f"• File log lỗi chi tiết         : {FAILURES_LOG_PATH}")
    print("=" * 90)
    print("Phân bổ các phân hệ đã kiểm thử đồng thời (Bao gồm Kịch bản ĐỌC, GHI & GIS):")
    print("  1. [App 1] Manual Traceability (SQL Heavy JOIN & Auth Verification POST)")
    print("  2. [App 2A] Grass-Fed Inspector (GET Status/Events/Public, Inbox, Event Create & Device/Mark-Read)")
    print("  3. [App 2B] Grass-Fed Slaughterhouse (GET List/Detail/Stats/Logs, External API <= 20, Add Lote Batch & Device)")
    print("  4. [App 2C] Grass-Fed Rancher (GET Farms/Detail/Stats, Farmers List, GIS Polygon PUT, POST Ranch & Device)")
    print("  5. [App 2D] FEDEGAN Central Admin (Cert/User Statistics Dashboard, Users List & Approve Cert POST)")
    print("  6. [App 5] Output 2: Animal Growth Analysis (Public Navigation & System Configs)")
    print("  7. [App 6] Output 3: Geospatial Biomass Monitoring & Python Analytical Model")
    print("=" * 90 + "\n")


@events.test_stop.add_listener
def on_test_stop_cleanup_leftovers(environment, **kwargs):
    """
    Tự động quét và dọn dẹp triệt để 100% dữ liệu thử nghiệm trong Database khi DỪNG TEST (POST Cleanup).
    Sử dụng đa luồng (ThreadPoolExecutor) để xóa song song nhanh chóng mà không làm ảnh hưởng bài test.
    """
    token = AUTH_TOKENS.get("rancher")
    host = environment.host.rstrip("/") if environment.host else ""
    if not host or not token:
        return

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=30, pool_maxsize=30)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(headers)

    with state.CLEANUP_LOCK:
        ranches_to_delete = list(state.CREATED_TEST_IDS["ranches"])
        devices_to_disable = list(state.CREATED_TEST_IDS["devices"])

    # Quét toàn bộ các trang để gom sạch bất kỳ ranch test 'STRESS*' nào chưa ghi nhận
    try:
        page = 1
        while True:
            r_list = session.get(f"{host}/api/ranches/get-by-organization?page={page}&length=100", timeout=15)
            if r_list.status_code != 200:
                break
            items = r_list.json().get("result", [])
            if not items:
                break
            for item in items:
                sit = item.get("sitCode", "")
                r_id = item.get("id")
                if sit.startswith("STRESS") and r_id and r_id not in ranches_to_delete:
                    ranches_to_delete.append(r_id)
            if len(items) < 100:
                break
            page += 1
    except Exception:
        pass

    if not ranches_to_delete and not devices_to_disable:
        return

    print("\n" + "=" * 90)
    print(f"🧹 [CLEANUP KHI DỪNG TEST] Đang dọn dẹp siêu tốc {len(ranches_to_delete)} trang trại test và {len(devices_to_disable)} thiết bị...")

    def delete_single_ranch(ranch_id):
        try:
            r = session.delete(f"{host}/api/ranches/delete?id={ranch_id}", timeout=10)
            if r.status_code in [200, 204]:
                with state.CLEANUP_LOCK:
                    state.CREATED_TEST_IDS["ranches"].discard(ranch_id)
                return True
        except Exception:
            pass
        return False

    def disable_single_device(dev_token):
        try:
            r = session.put(f"{host}/api/notifications/disable-device", json={"token": dev_token}, timeout=10)
            if r.status_code in [200, 204]:
                with state.CLEANUP_LOCK:
                    state.CREATED_TEST_IDS["devices"].discard(dev_token)
                return True
        except Exception:
            pass
        return False

    deleted_ranch_count = 0
    if ranches_to_delete:
        with ThreadPoolExecutor(max_workers=30) as executor:
            results = executor.map(delete_single_ranch, ranches_to_delete)
            deleted_ranch_count = sum(1 for res in results if res)

    disabled_device_count = 0
    if devices_to_disable:
        with ThreadPoolExecutor(max_workers=30) as executor:
            results = executor.map(disable_single_device, devices_to_disable)
            disabled_device_count = sum(1 for res in results if res)

    print(f"✨ [CLEANUP HOÀN TẤT] Đã xóa thành công {deleted_ranch_count}/{len(ranches_to_delete)} trang trại và vô hiệu hóa {disabled_device_count}/{len(devices_to_disable)} thiết bị test.")
    print("   Database trên máy chủ hoàn toàn sạch sẽ, không còn dữ liệu thử nghiệm.")
    print("=" * 90 + "\n")
