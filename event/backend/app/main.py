from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import (
    admin_routes,
    auth_routes,
    master_data_routes,
    parsing_routes,
    regulation_routes,
    review_routes,
)
from .config import get_settings
from .database import SessionLocal
from .seed import seed_demo_data

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.bootstrap_demo_data:
        with SessionLocal() as db:
            seed_demo_data(db)
    yield


app = FastAPI(title=settings.app_name, version="0.4.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": f"HTTP_{exc.status_code}", "message": exc.detail}},
    )


@app.get("/health")
def health():
    return {"status": "ok", "milestone": "M4"}


app.include_router(auth_routes.router, prefix=settings.api_prefix)
app.include_router(master_data_routes.router, prefix=settings.api_prefix)
app.include_router(regulation_routes.router, prefix=settings.api_prefix)
app.include_router(parsing_routes.router, prefix=settings.api_prefix)
app.include_router(review_routes.router, prefix=settings.api_prefix)
app.include_router(admin_routes.router, prefix=settings.api_prefix)
