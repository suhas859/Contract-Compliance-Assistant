from fastapi import FastAPI
from backend.api.ingestion_api import router as ingestion_router

app = FastAPI(
    title="Contract Compliance Assistant API",
    version="1.0.0"
)

app.include_router(
    ingestion_router,
    prefix="/api",
    tags=["Ingestion"]
)


@app.get("/")
def root():
    return {
        "message": "Backend is running successfully"
    }