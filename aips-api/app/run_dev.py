from __future__ import annotations

import uvicorn

from app.core.config import DEV_BACKEND_HOST, DEV_BACKEND_PORT


def main() -> None:
    uvicorn.run(
        "app.main:app",
        host=DEV_BACKEND_HOST,
        port=DEV_BACKEND_PORT,
        reload=True,
    )


if __name__ == "__main__":
    main()
