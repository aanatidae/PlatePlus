"""FastAPI entry point for the local ALPR prototype."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.webcam import router as webcam_router

app = FastAPI(title="AI-Powered ALPR Dynamic Toll Prototype")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(webcam_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
