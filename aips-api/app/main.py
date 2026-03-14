import logging
import re
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import CORS_ORIGINS, ensure_storage_dirs
from app.services.cleanup_service import cleanup_service
from app.services.rate_limit_service import RateLimitDecision, rate_limit_service
from app.services.task_queue_service import task_queue_service

logger = logging.getLogger("aips.http")
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def _configure_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        return

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


ensure_storage_dirs()
_configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    cleanup_service.start()
    await task_queue_service.start_worker()
    try:
        yield
    finally:
        await task_queue_service.stop_worker()
        cleanup_service.stop()


app = FastAPI(
    title="aips-api",
    version="0.1.0",
    description="aips-api 是 AIPS（AI ID Photo Studio）的后端接口，提供证件照上传、处理、预览与下载能力。",
    lifespan=lifespan,
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    request_id = _resolve_request_id(request.headers.get("X-Request-ID"))
    request.state.request_id = request_id
    started_at = time.perf_counter()

    rate_limit_bucket = _match_rate_limit_bucket(request.method, request.url.path)
    rate_limit_decision: RateLimitDecision | None = None
    if rate_limit_bucket:
        identifier = _client_identifier(request)
        rate_limit_decision = rate_limit_service.check(rate_limit_bucket, identifier)
        if not rate_limit_decision.allowed:
            response = _build_rate_limited_response(rate_limit_decision, request_id=request_id)
            _log_request(
                request=request,
                status_code=response.status_code,
                started_at=started_at,
                request_id=request_id,
                note=f"bucket={rate_limit_bucket} rate_limited",
            )
            return response

    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "request failed request_id=%s method=%s path=%s client=%s",
            request_id,
            request.method,
            request.url.path,
            _client_identifier(request),
        )
        response = JSONResponse(
            status_code=500,
            content={"detail": "服务器内部错误，请稍后重试。"},
        )

    _apply_common_headers(response, request_id=request_id, cache_control=_cache_control_for_path(request.url.path))

    if rate_limit_decision is not None:
        _apply_rate_limit_headers(response, rate_limit_decision)

    _log_request(
        request=request,
        status_code=response.status_code,
        started_at=started_at,
        request_id=request_id,
        note=f"bucket={rate_limit_bucket}" if rate_limit_bucket else None,
    )
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


def _client_identifier(request) -> str:
    return request.client.host if request.client and request.client.host else "unknown"


def _resolve_request_id(value: str | None) -> str:
    candidate = (value or "").strip()
    if _REQUEST_ID_RE.fullmatch(candidate):
        return candidate
    return uuid4().hex[:16]


def _match_rate_limit_bucket(method: str, path: str) -> str | None:
    if method == "OPTIONS":
        return None

    if method == "POST" and path in {"/api/v1/files/upload", "/api/v1/files/upload-batch"}:
        return "upload"

    if method == "POST" and path == "/api/v1/files/download-zip":
        return "archive"

    if method == "POST" and path in {
        "/api/v1/images/process",
        "/api/v1/images/resize",
        "/api/v1/images/enhance",
        "/api/v1/images/suggest-render",
        "/api/v1/images/process-batch",
        "/api/v1/images/process-batch-auto",
        "/api/v1/images/compose-sheet",
    }:
        return "heavy"

    return None


def _cache_control_for_path(path: str) -> str:
    if path == "/api/v1/presets":
        return "public, max-age=300"
    if path.startswith("/api/v1/"):
        return "no-store"
    return "no-store"


def _apply_common_headers(response, *, request_id: str, cache_control: str) -> None:
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Cache-Control", cache_control)
    response.headers["X-Request-ID"] = request_id


def _apply_rate_limit_headers(response, decision: RateLimitDecision) -> None:
    response.headers["X-RateLimit-Limit"] = str(decision.limit)
    response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
    response.headers["X-RateLimit-Reset"] = str(decision.reset_after_seconds)


def _build_rate_limited_response(decision: RateLimitDecision, *, request_id: str) -> JSONResponse:
    response = JSONResponse(
        status_code=429,
        content={"detail": f"请求过于频繁，请在 {decision.reset_after_seconds} 秒后重试。"},
    )
    response.headers["Retry-After"] = str(decision.reset_after_seconds)
    _apply_common_headers(response, request_id=request_id, cache_control="no-store")
    _apply_rate_limit_headers(response, decision)
    return response


def _log_request(
    *,
    request: Request,
    status_code: int,
    started_at: float,
    request_id: str,
    note: str | None = None,
) -> None:
    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    suffix = f" {note}" if note else ""
    logger.info(
        "request_id=%s client=%s method=%s path=%s status=%s duration_ms=%s%s",
        request_id,
        _client_identifier(request),
        request.method,
        request.url.path,
        status_code,
        duration_ms,
        suffix,
    )
