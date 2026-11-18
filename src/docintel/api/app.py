"""The FastAPI app. Run it with: uv run uvicorn docintel.api.app:app"""

import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from docintel.api.routes import VERSION, router
from docintel.core.logs import setup_logging
from docintel.core.tracing import setup_tracing

log = structlog.get_logger()
WEB_DIST = Path("web/dist")  # the built UI, from `make app`; relative to the repo, like data/


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

# The UI, at the same address as the API, so the browser needs no CORS. Added after the routes, so
# /v1/... and /health still go to the API. Only there after `make app` builds it.
if WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")


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
