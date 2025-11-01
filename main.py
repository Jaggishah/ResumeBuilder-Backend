from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pathlib import Path
import asyncio
import subprocess
import sys
from contextlib import asynccontextmanager


# Import routes
from routes import resume_routes, ai_routes, auth_routes, feedback_routes
from database.models import init_database

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    await init_database()
    print("ResumeBuilder API started successfully")
    yield
    # Shutdown
    print("Shutting down ResumeBuilder API")

app = FastAPI(title="ResumeBuilder API", version="0.1.0", lifespan=lifespan)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(resume_routes.router)
app.include_router(ai_routes.router)
app.include_router(auth_routes.router)
app.include_router(feedback_routes.router)

@app.get("/")
async def root():
    return {"ok": True, "message": "ResumeBuilder API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)