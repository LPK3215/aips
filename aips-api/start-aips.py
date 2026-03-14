"""启动 aips-api 后端服务。"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
ENV_FILE = BACKEND_DIR / ".env"
PYTHON_EXE = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"


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


def main() -> None:
    load_env(ENV_FILE)

    python = str(PYTHON_EXE) if PYTHON_EXE.exists() else sys.executable

    subprocess.run(
        [python, "-m", "app.run_dev"],
        cwd=str(BACKEND_DIR),
        check=False,
    )


if __name__ == "__main__":
    main()
