"""
Mã hoá / giải mã API key của user trước khi lưu vào DB.

ENCRYPTION_KEY phải là Fernet key hợp lệ (32 byte, base64 url-safe → 44 ký tự).
Tạo bằng:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import os

# Module này có thể được import trực tiếp (seed.py, script test) mà không qua
# app.database — nạp .env ở đây để không phụ thuộc thứ tự import.
load_dotenv()

_raw_key = os.getenv("ENCRYPTION_KEY", "").strip()

if not _raw_key:
    raise RuntimeError(
        "Thiếu biến môi trường ENCRYPTION_KEY. API key của user sẽ không được mã hoá an toàn.\n"
        'Tạo key: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
    )

try:
    # Fernet tự validate độ dài và định dạng base64
    _fernet = Fernet(_raw_key.encode())
except Exception as exc:
    # Trước đây key sai định dạng bị "vá" bằng _raw_key.ljust(32)[:32], nên
    # ENCRYPTION_KEY rỗng sẽ tạo ra khoá là 32 dấu cách — ai cũng giải mã được.
    # Giờ fail-fast thay vì âm thầm dùng khoá yếu.
    raise RuntimeError(
        f"ENCRYPTION_KEY không phải Fernet key hợp lệ ({exc}). "
        "Cần chuỗi base64 url-safe dài 44 ký tự.\n"
        'Tạo key: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
    ) from exc


def encrypt(plaintext: str) -> str:
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return _fernet.decrypt(ciphertext.encode()).decode()
