import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
import models
from routes import auth, visitor, admin, receivers

# Initialize Database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MCET Smart Visitor Live Tracking System API",
    description="Backend services for real-time visitor GPS & BLE tracking inside campus.",
    version="1.0.0"
)

# Configure CORS for Frontend React access.
# Set ALLOWED_ORIGINS to a comma-separated list of your deployed frontend
# origin(s), e.g. "https://track-in-frontend.vercel.app,http://localhost:5173".
# Auth here uses a Bearer token (not cookies), so allow_credentials can stay
# False - that's what lets us safely support multiple explicit origins.
_origins_env = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = [
    origin.strip().strip("\"'").rstrip("/")
    for origin in _origins_env.split(",")
    if origin.strip().strip("\"'").rstrip("/")
] or ["*"]

app.include_router(auth.router)
app.include_router(visitor.router)
app.include_router(admin.router)
app.include_router(receivers.router)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "system": "MCET Smart Visitor Live Tracking System",
        "api_docs": "/docs"
    }

# Wrap the complete ASGI application so CORS headers are also applied to
# unhandled error responses (for example, a database schema mismatch).
app = CORSMiddleware(
    app,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
