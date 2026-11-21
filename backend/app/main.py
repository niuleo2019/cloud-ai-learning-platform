from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from pathlib import Path

from app.infrastructure.database import close_connection_pool, init_connection_pool
from app.interfaces.exceptions import AppException
from app.interfaces.http.response import (
    app_exception_handler,
    http_exception_handler,
    success_response,
    validation_exception_handler,
)
from app.interfaces.http.routes import auth_routes, dictionary_routes, pdf_roots_routes, review_routes, vision_routes, word_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_connection_pool()
    try:
        yield
    finally:
        close_connection_pool()


app = FastAPI(title="Vocab App API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return success_response(
        {
            "api": "/api/health",
            "docs": "/docs",
            "frontend": "http://localhost:5173",
        },
        "Vocab App backend is running",
    )


@app.get("/api/health")
def health_check():
    return success_response({"status": "ok"}, "API is healthy")


app.include_router(auth_routes.router, prefix="/api/auth", tags=["auth"])
app.include_router(dictionary_routes.router, prefix="/api/dictionary", tags=["dictionary"])
app.include_router(word_routes.router, prefix="/api/words", tags=["words"])
app.include_router(review_routes.router, prefix="/api/reviews", tags=["reviews"])
app.include_router(pdf_roots_routes.router, prefix="/api/pdf-roots", tags=["pdf-roots"])
app.include_router(vision_routes.router, prefix="/api/vision", tags=["vision"])

PDF_ROOT_IMAGES_DIR = Path(__file__).resolve().parents[1] / "data" / "pdf-root-images"
PDF_ROOT_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/api/pdf-root-images", StaticFiles(directory=PDF_ROOT_IMAGES_DIR), name="pdf-root-images")

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
