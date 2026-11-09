import uuid
import threading
import requests

# ==============================================================================
# QUẢN LÝ XÁC THỰC DÙNG CHUNG (SINGLE LOGIN CACHE & HEADER FACTORY)
# ==============================================================================

# Bộ nhớ đệm Token chia sẻ toàn hệ thống cho 4 vai trò chính
AUTH_TOKENS = {
    "inspector": None,
    "slaughterhouse": None,
    "rancher": None,
    "admin": None,
}

AUTH_LOCK = threading.Lock()


import time

def _login_single_role(clean_base_url: str, email: str, role_name: str, max_retries: int = 3, timeout: int = 45) -> str:
    """Đăng nhập kèm cơ chế tự động thử lại (Auto-Retry) phòng ngừa Cloud Run Cold Start"""
    json_headers = {"Content-Type": "application/json"}
    for attempt in range(1, max_retries + 1):
        try:
            r = requests.post(
                f"{clean_base_url}/api/users/login",
                json={"email": email},
                headers=json_headers,
                timeout=timeout,
            )
            if r.status_code in [200, 201]:
                token = r.json().get("result", {}).get("access_token")
                if token:
                    return token
            elif r.status_code in [502, 503, 504]:
                time.sleep(1.5 * attempt)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if attempt < max_retries:
                time.sleep(2 * attempt)
            else:
                print(f"[Warn] Login {role_name} timeout sau {max_retries} lần thử: {e}")
        except Exception as e:
            print(f"[Warn] Login {role_name} gặp lỗi: {e}")
            break
    return None


def fetch_tokens_once(base_url: str):
    """
    Đăng nhập lấy Token 1 lần duy nhất cho toàn bộ các vai trò để tránh bão login (Login Storm).
    Được gọi tự động trong on_start() của BaseSatrepsUser.
    """
    if all(AUTH_TOKENS.values()):
        return

    with AUTH_LOCK:
        if all(AUTH_TOKENS.values()):
            return

        clean_base_url = base_url.rstrip("/")

        # 1. Login Inspector
        if not AUTH_TOKENS["inspector"]:
            AUTH_TOKENS["inspector"] = _login_single_role(
                clean_base_url, "certicol.andes@colmail.com", "Inspector"
            )

        # 2. Login Slaughterhouse
        if not AUTH_TOKENS["slaughterhouse"]:
            AUTH_TOKENS["slaughterhouse"] = _login_single_role(
                clean_base_url, "frigorifico.caribe@correo.com", "Slaughterhouse"
            )

        # 3. Login Rancher / Farmer
        if not AUTH_TOKENS["rancher"]:
            AUTH_TOKENS["rancher"] = _login_single_role(
                clean_base_url, "juancamilo.herrera@gmail.com", "Rancher"
            )

        # 4. Login FEDEGAN Admin (Sử dụng token quản trị viên hệ thống)
        if not AUTH_TOKENS["admin"]:
            AUTH_TOKENS["admin"] = AUTH_TOKENS.get("inspector")


def create_traced_headers(token: str = None) -> dict:
    """Sinh Header chứa Trace-ID để truy vết server logs và Cloud Trace"""
    headers = {
        "Content-Type": "application/json",
        "x-request-id": uuid.uuid4().hex[:12],
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers
