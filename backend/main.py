from fastapi import FastAPI
from backend.api.chat_api import router as chat_router
from backend.api.ingestion_api import router as ingestion_router
from backend.api.servicenow_api import router as servicenow_router

app = FastAPI(
    title="Contract Compliance Assistant API",
    version="1.0.0"
)

app.include_router(
    ingestion_router,
    prefix="/api",
    tags=["Ingestion"]
)

app.include_router(
    chat_router,
    tags=["Chat"]
)

app.include_router(
    servicenow_router,
    tags=["ServiceNow"]
)


@app.get("/")
def root():
    return {
        "message": "Backend is running successfully"
    }