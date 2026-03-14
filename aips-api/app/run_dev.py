from __future__ import annotations

import uvicorn

from app.core.config import API_HOST, API_PORT


def main() -> None:
    uvicorn.run(
        "app.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
    )


if __name__ == "__main__":
    main()
