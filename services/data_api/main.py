"""
FastAPI Data API Service
Provides access to SQL and Vector databases
"""

import os
import sys
import json
import logging
from pathlib import Path
from contextlib import asynccontextmanager

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Import shared modules
from shared.database.connection import init_databases, close_databases

# Import routers
from services.data_api.routers import data_router

# Load environment variables
load_dotenv()

# Logging configuration
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI Lifespan - Initialize and cleanup databases"""
    # Startup
    logger.info("Starting up Data API Service")

    # Initialize databases
    await init_databases()
    logger.info("Databases initialized")

    yield

    # Shutdown
    logger.info("Shutting down Data API Service")
    await close_databases()
    logger.info("Database connections closed")


# Create FastAPI app
app = FastAPI(
    title="Data API Service",
    description="SQL and Vector Database Access Layer",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
cors_origins = json.loads(os.getenv("CORS_ORIGINS", '["http://localhost:3000"]'))
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(data_router, prefix="/api/v1/data")


# Root endpoint
@app.get("/")
async def root():
    """Health check and service info"""
    return {
        "service": "data_api",
        "status": "healthy",
        "version": "1.0.0",
        "endpoints": {
            "sql": "/api/v1/data/sql",
            "vector": "/api/v1/data/vector",
            "hybrid": "/api/v1/data/hybrid",
            "metadata": "/api/v1/data/metadata"
        }
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        # Check database connections
        from shared.database.connection import _engines

        db_status = {}
        for db_name in _engines.keys():
            db_status[db_name] = "connected"

        return {
            "status": "healthy",
            "databases": db_status,
            "service": "data_api"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("DATA_API_HOST", "0.0.0.0"),
        port=int(os.getenv("DATA_API_PORT", 8002)),
        reload=os.getenv("API_RELOAD", "true").lower() == "true"
    )