"""Initialize local .env files from templates.

This repo keeps user-specific `.env` files out of version control (see `.gitignore`).
Run this script once after cloning to generate:

- aips-api/.env   from aips-api/.env.example
- aips-web/.env   from aips-web/.env.example
"""

from __future__ import annotations

import argparse
from pathlib import Path
from shutil import copyfile


ROOT_DIR = Path(__file__).resolve().parent
ENV_PAIRS = (
    (ROOT_DIR / "aips-api" / ".env.example", ROOT_DIR / "aips-api" / ".env"),
    (ROOT_DIR / "aips-web" / ".env.example", ROOT_DIR / "aips-web" / ".env"),
)


def ensure_env(example_file: Path, env_file: Path, *, force: bool) -> str:
    if env_file.exists() and not force:
        return "exists"

    if not example_file.exists():
        return "missing-template"

    try:
        env_file.parent.mkdir(parents=True, exist_ok=True)
        copyfile(example_file, env_file)
    except OSError:
        return "error"

    return "created" if not force else "overwritten"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate local .env files from .env.example templates.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing .env files.",
    )
    args = parser.parse_args()

    created: list[str] = []
    skipped: list[str] = []
    missing: list[str] = []
    errors: list[str] = []

    for example_file, env_file in ENV_PAIRS:
        status = ensure_env(example_file, env_file, force=args.force)
        rel_env = env_file.relative_to(ROOT_DIR).as_posix()
        rel_example = example_file.relative_to(ROOT_DIR).as_posix()

        if status in {"created", "overwritten"}:
            created.append(f"{rel_env} <= {rel_example}")
        elif status == "exists":
            skipped.append(rel_env)
        elif status == "missing-template":
            missing.append(rel_example)
        else:
            errors.append(rel_env)

    if created:
        print("已生成：")
        for item in created:
            print(f"- {item}")

    if skipped:
        print("已存在，跳过：")
        for item in skipped:
            print(f"- {item}")

    if missing:
        print("缺少模板文件：")
        for item in missing:
            print(f"- {item}")

    if errors:
        print("生成失败：")
        for item in errors:
            print(f"- {item}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

