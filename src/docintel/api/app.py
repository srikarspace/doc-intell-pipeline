"""The FastAPI app. Run it with: uv run uvicorn docintel.api.app:app"""

import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request

from docintel.api.routes import VERSION, router
from docintel.core.logs import setup_logging
from docintel.core.tracing import setup_tracing

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    setup_tracing()
    yield


def not_traced(scope) -> bool:
    """Trace only the extract routes. /health and the sample files would hide them in Phoenix."""
    return not scope["path"].startswith("/v1/extract")


app = FastAPI(
    title="docintel", version=VERSION, lifespan=lifespan, telemetry={"exclude": not_traced}
)
app.include_router(router)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Give every request an id. Every log line and the trace carry it, and so does the answer."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    ms = round((time.perf_counter() - start) * 1000)
    log.info(
        "request", method=request.method, path=request.url.path, status=response.status_code, ms=ms
    )
    return response
