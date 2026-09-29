"""
ComicCraft Application Entrypoint
Initializes FastAPI, mounts static directories, and attaches application routers.
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Assets
app.mount("/static", StaticFiles(directory=str(settings.STATIC_DIR)), name="static")

# Include Application Router
app.include_router(router)

@app.get("/health", summary="Health Check")
async def health_check():
    """Returns application status and configuration summary."""
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "gemini_api_configured": bool(settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("your_")),
        "hf_api_configured": bool(settings.HF_API_KEY and not settings.HF_API_KEY.startswith("your_"))
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=settings.DEBUG)
