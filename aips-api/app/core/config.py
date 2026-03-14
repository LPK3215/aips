import json
from pathlib import Path


AIPS_API_DIR = Path(__file__).resolve().parents[2]
AIPS_ROOT_DIR = AIPS_API_DIR.parent
APP_DIR = AIPS_API_DIR / "app"
STORAGE_DIR = AIPS_API_DIR / "storage"
UPLOADS_DIR = STORAGE_DIR / "uploads"
RESULTS_DIR = STORAGE_DIR / "results"
TASKS_DIR = STORAGE_DIR / "tasks"
TEMP_DIR = STORAGE_DIR / "temp"
PRESETS_FILE = APP_DIR / "data" / "presets.json"
RUNTIME_SETTINGS_FILE = AIPS_ROOT_DIR / "aips.settings.json"
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

_DEFAULT_RUNTIME_SETTINGS = {
    "backend": {"host": "127.0.0.1", "port": 8000},
    "frontend": {"host": "127.0.0.1", "port": 5173},
    "launcher": {"open_browser": True},
}


def _load_runtime_settings() -> dict:
    if not RUNTIME_SETTINGS_FILE.exists():
        return _DEFAULT_RUNTIME_SETTINGS

    try:
        loaded = json.loads(RUNTIME_SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _DEFAULT_RUNTIME_SETTINGS

    if not isinstance(loaded, dict):
        return _DEFAULT_RUNTIME_SETTINGS

    merged = {
        "backend": {**_DEFAULT_RUNTIME_SETTINGS["backend"], **(loaded.get("backend") or {})},
        "frontend": {**_DEFAULT_RUNTIME_SETTINGS["frontend"], **(loaded.get("frontend") or {})},
        "launcher": {**_DEFAULT_RUNTIME_SETTINGS["launcher"], **(loaded.get("launcher") or {})},
    }
    return merged


RUNTIME_SETTINGS = _load_runtime_settings()
DEV_BACKEND_HOST = str(RUNTIME_SETTINGS["backend"]["host"])
DEV_BACKEND_PORT = int(RUNTIME_SETTINGS["backend"]["port"])
DEV_FRONTEND_HOST = str(RUNTIME_SETTINGS["frontend"]["host"])
DEV_FRONTEND_PORT = int(RUNTIME_SETTINGS["frontend"]["port"])


def _build_dev_cors_origins() -> list[str]:
    candidates = [f"http://{DEV_FRONTEND_HOST}:{DEV_FRONTEND_PORT}"]
    if DEV_FRONTEND_HOST == "127.0.0.1":
        candidates.append(f"http://localhost:{DEV_FRONTEND_PORT}")
    elif DEV_FRONTEND_HOST == "localhost":
        candidates.append(f"http://127.0.0.1:{DEV_FRONTEND_PORT}")
    return list(dict.fromkeys(candidates))


DEV_CORS_ORIGINS = [
    url
    for url in _build_dev_cors_origins()
    if url
]


def ensure_storage_dirs() -> None:
    for path in (UPLOADS_DIR, RESULTS_DIR, TASKS_DIR, TEMP_DIR):
        path.mkdir(parents=True, exist_ok=True)
