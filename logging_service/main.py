from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from modules.logs.routers import router as logs_router

app = FastAPI(
    title="Logging & Audit Service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(logs_router)

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": settings.SERVICE_NAME}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True)
