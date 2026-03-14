import os
from pathlib import Path


AIPS_API_DIR = Path(__file__).resolve().parents[2]
APP_DIR = AIPS_API_DIR / "app"
STORAGE_DIR = AIPS_API_DIR / "storage"
UPLOADS_DIR = STORAGE_DIR / "uploads"
RESULTS_DIR = STORAGE_DIR / "results"
TASKS_DIR = STORAGE_DIR / "tasks"
TEMP_DIR = STORAGE_DIR / "temp"
PRESETS_FILE = APP_DIR / "data" / "presets.json"
ENV_FILE = AIPS_API_DIR / ".env"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000
MAX_BATCH_ITEMS = 20
MAX_CONCURRENT_HEAVY_JOBS = 2
STORAGE_TTL_HOURS = 24
CLEANUP_INTERVAL_SECONDS = 600
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
RATE_LIMIT_UPLOAD_REQUESTS = 12
RATE_LIMIT_HEAVY_REQUESTS = 24
RATE_LIMIT_ARCHIVE_REQUESTS = 6
RATE_LIMIT_WINDOW_SECONDS = 60


def _load_env_file() -> None:
    if not ENV_FILE.exists():
        return

    try:
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]

        os.environ.setdefault(key, value)


def _read_env_str(name: str, default: str) -> str:
    value = os.getenv(name, default).strip()
    return value or default


def _read_env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        value = int(raw_value)
    except ValueError:
        return default
    return value if value > 0 else default


def _normalize_origin(value: str) -> str:
    return value.strip().rstrip("/")


_load_env_file()

API_HOST = _read_env_str("AIPS_API_HOST", "127.0.0.1")
API_PORT = _read_env_int("AIPS_API_PORT", 8000)
WEB_HOST = _read_env_str("AIPS_WEB_HOST", "127.0.0.1")
WEB_PORT = _read_env_int("AIPS_WEB_PORT", 5173)


def _build_cors_origins() -> list[str]:
    explicit_origins = _read_env_str("AIPS_CORS_ORIGINS", "")
    if explicit_origins:
        return list(
            dict.fromkeys(
                _normalize_origin(origin)
                for origin in explicit_origins.split(",")
                if origin.strip()
            )
        )

    candidates = [f"http://{WEB_HOST}:{WEB_PORT}"]
    if WEB_HOST == "127.0.0.1":
        candidates.append(f"http://localhost:{WEB_PORT}")
    elif WEB_HOST == "localhost":
        candidates.append(f"http://127.0.0.1:{WEB_PORT}")
    return list(dict.fromkeys(candidates))


CORS_ORIGINS = [
    url
    for url in _build_cors_origins()
    if url
]


def ensure_storage_dirs() -> None:
    for path in (UPLOADS_DIR, RESULTS_DIR, TASKS_DIR, TEMP_DIR):
        path.mkdir(parents=True, exist_ok=True)
