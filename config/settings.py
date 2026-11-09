import os

# ==============================================================================
# CẤU HÌNH BIẾN MÔI TRƯỜNG & THIẾT LẬP KIỂM THỬ
# ==============================================================================

LOG_FAILURES_TO_FILE = os.getenv("LOG_FAILURES_TO_FILE", "true").lower() == "true"
FAILURES_LOG_PATH = os.getenv("FAILURES_LOG_PATH", "failures_integrated.log")
TEST_SCENARIO = os.getenv("SCENARIO", "interactive").lower()
ENABLE_DIGITAL_CERT_TEST = os.getenv("ENABLE_DIGITAL_CERT_TEST", "false").lower() == "true"
BPS_BACKEND_HOST = os.getenv("BPS_BACKEND_HOST", "").rstrip("/")
