"""The FastAPI app. Run it with: uv run uvicorn docintel.api.app:app"""

from fastapi import FastAPI

from docintel.api.routes import VERSION, router

app = FastAPI(title="docintel", version=VERSION)
app.include_router(router)
