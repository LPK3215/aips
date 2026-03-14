"""启动 aips-api 后端服务。"""
from __future__ import annotations

import os
import subprocess
import sys
from shutil import copyfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
ENV_FILE = BACKEND_DIR / ".env"
ENV_TEMPLATE_FILE = BACKEND_DIR / ".env.example"
VENV_DIR = BACKEND_DIR / ".venv"
VENV_PYTHON_CANDIDATES = (
    VENV_DIR / "Scripts" / "python.exe",
    VENV_DIR / "Scripts" / "python",
    VENV_DIR / "bin" / "python3",
    VENV_DIR / "bin" / "python",
)


def ensure_env_file(env_file: Path, template_file: Path) -> None:
    if env_file.exists():
        return
    if not template_file.exists():
        return
    try:
        copyfile(template_file, env_file)
    except OSError:
        return
    print(f"[aips-api] 已生成配置文件：{env_file.name}（可按需修改）")


def load_env(env_file: Path) -> None:
    if not env_file.exists():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
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


def resolve_python_executable() -> str:
    for candidate in VENV_PYTHON_CANDIDATES:
        if candidate.exists():
            return str(candidate)
    return sys.executable


def main() -> None:
    ensure_env_file(ENV_FILE, ENV_TEMPLATE_FILE)
    load_env(ENV_FILE)

    python = resolve_python_executable()

    result = subprocess.run(
        [python, "-m", "app.run_dev"],
        cwd=str(BACKEND_DIR),
        check=False,
    )
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
