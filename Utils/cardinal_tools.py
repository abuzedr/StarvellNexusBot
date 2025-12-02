import os
import shutil
import time
import json
import hashlib
from typing import List, Dict, Any, Optional

def create_directories(directories: List[str]):
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)

def backup_file(file_path: str, backup_dir: str = "backups"):
    if not os.path.exists(file_path):
        return False
    
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    filename = os.path.basename(file_path)
    timestamp = int(time.time())
    backup_path = os.path.join(backup_dir, f"{filename}.{timestamp}")
    
    try:
        shutil.copy2(file_path, backup_path)
        return True
    except Exception:
        return False

def format_time(seconds: int) -> str:
    if seconds < 60:
        return f"{int(seconds)} сек"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        return f"{minutes} мин"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours} ч {minutes} мин"
    else:
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        return f"{days} д {hours} ч"

def safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    try:
        return data.get(key, default)
    except (KeyError, TypeError):
        return default

def is_valid_email(email: str) -> bool:
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def clean_filename(filename: str) -> str:
    import re
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = filename.strip()
    if len(filename) > 255:
        filename = filename[:255]
    return filename

def calculate_file_hash(file_path: str) -> str:
    try:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return ""

def save_json(data: Dict[str, Any], file_path: str) -> bool:
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def load_json(file_path: str) -> Optional[Dict[str, Any]]:
    try:
        if not os.path.exists(file_path):
            return None
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

def format_price(price: float, currency: str = "RUB") -> str:
    if currency == "RUB":
        return f"{price:.2f} ₽"
    elif currency == "USD":
        return f"${price:.2f}"
    elif currency == "EUR":
        return f"€{price:.2f}"
    else:
        return f"{price:.2f} {currency}"

def parse_price(price_str: str) -> float:
    import re
    cleaned = re.sub(r'[^\d.,]', '', price_str)
    cleaned = cleaned.replace(',', '.')
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

def get_timestamp() -> int:
    return int(time.time())

def format_datetime(timestamp: int) -> str:
    import datetime
    return datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

def truncate_text(text: str, max_length: int = 100) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def is_valid_url(url: str) -> bool:
    import re
    pattern = r'^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$'
    return re.match(pattern, url) is not None

def get_file_size(file_path: str) -> int:
    try:
        return os.path.getsize(file_path)
    except Exception:
        return 0

def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes/(1024**2):.1f} MB"
    else:
        return f"{size_bytes/(1024**3):.1f} GB"

def create_pid_file(pid_file_path: str) -> bool:
    try:
        with open(pid_file_path, 'w') as f:
            f.write(str(os.getpid()))
        return True
    except Exception:
        return False

def remove_pid_file(pid_file_path: str) -> bool:
    try:
        if os.path.exists(pid_file_path):
            os.remove(pid_file_path)
        return True
    except Exception:
        return False

def check_pid_file(pid_file_path: str) -> bool:
    try:
        if not os.path.exists(pid_file_path):
            return False
        
        with open(pid_file_path, 'r') as f:
            pid = int(f.read().strip())
        
        import psutil
        return psutil.pid_exists(pid)
    except Exception:
        return False