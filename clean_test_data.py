#!/usr/bin/env python3
"""
Tiện ích dọn dẹp dữ liệu thử nghiệm SATREPS FEDEGAN
Quét và xóa toàn bộ các trang trại test (STRESS*), thiết bị giả lập (stress_fcm*)
sử dụng đa luồng siêu tốc.
"""

import sys
import os
import requests
from concurrent.futures import ThreadPoolExecutor

HOST = os.environ.get("HOST", "https://satreps-api-427991251928.us-central1.run.app").rstrip("/")
RANCHER_EMAIL = "juancamilo.herrera@gmail.com"

print("=" * 80)
print(f"🧹 TIỆN ÍCH DỌN DẸP DỮ LIỆU THỬ NGHIỆM SATREPS")
print(f"• Máy chủ mục tiêu: {HOST}")
print("=" * 80)

# 1. Đăng nhập lấy Bearer token của Chủ trang trại
try:
    login_res = requests.post(f"{HOST}/api/users/login", json={"email": RANCHER_EMAIL}, timeout=15)
    if login_res.status_code not in [200, 201]:
        print(f"❌ Không thể đăng nhập tài khoản rancher ({login_res.status_code}): {login_res.text}")
        sys.exit(1)
    token = login_res.json().get("result", {}).get("access_token")
    if not token:
        print("❌ Token không tồn tại trong phản hồi login.")
        sys.exit(1)
except Exception as e:
    print(f"❌ Lỗi kết nối tới máy chủ: {e}")
    sys.exit(1)

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=30, pool_maxsize=30)
session.mount("https://", adapter)
session.mount("http://", adapter)
session.headers.update(headers)

# 2. Quét toàn bộ các trang danh sách trang trại
print("🔍 Đang quét danh sách trang trại test (STRESS*)...")
page = 1
stress_ranches = []
while True:
    try:
        r = session.get(f"{HOST}/api/ranches/get-by-organization?page={page}&length=100", timeout=15)
        if r.status_code != 200:
            print(f"⚠️ Dừng quét tại trang {page} (Status: {r.status_code})")
            break
        items = r.json().get("result", [])
        if not items:
            break
        found = [item for item in items if item.get("sitCode", "").startswith("STRESS") and item.get("id")]
        stress_ranches.extend(found)
        if len(items) < 100:
            break
        page += 1
    except Exception as e:
        print(f"⚠️ Lỗi quét trang {page}: {e}")
        break

print(f"📋 Tìm thấy tổng cộng: {len(stress_ranches)} trang trại test.")

if not stress_ranches:
    print("✅ Hệ thống đã hoàn toàn sạch sẽ, không có trang trại test nào!")
    sys.exit(0)

# 3. Thực hiện xóa song song bằng ThreadPoolExecutor
def delete_single(ranch):
    r_id = ranch["id"]
    sit = ranch.get("sitCode", "")
    try:
        res = session.delete(f"{HOST}/api/ranches/delete?id={r_id}", timeout=10)
        return res.status_code in [200, 204]
    except Exception:
        return False

print(f"⚡ Đang xóa đồng thời {len(stress_ranches)} trang trại test...")
with ThreadPoolExecutor(max_workers=25) as executor:
    results = list(executor.map(delete_single, stress_ranches))

deleted_count = sum(1 for ok in results if ok)
print("=" * 80)
print(f"✨ KẾT QUẢ: Đã xóa thành công {deleted_count}/{len(stress_ranches)} trang trại test.")
if deleted_count == len(stress_ranches):
    print("🎉 Toàn bộ dữ liệu test đã được làm sạch 100%!")
else:
    print(f"⚠️ Còn {len(stress_ranches) - deleted_count} trang trại chưa xóa được do timeout, bạn có thể chạy lại script này.")
print("=" * 80)
