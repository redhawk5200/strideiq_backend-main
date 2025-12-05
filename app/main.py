import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
from app.exceptions.handlers import (
    application_exception_handler,
    http_exception_handler,
    generic_exception_handler
)
from app.exceptions.errors import ApplicationException
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError
from app.database.base import Base
from app.database.connection import engine

# Import mobile app routes
from app.api.v1.routes import user_router, health_router, webhook_router, vo2_router, onboarding_router, recommendations_router, coaching_chat_router, progress_router
from app.middlewares.clerk_auth import ClerkAuthMiddleware, whitelisted_routes
from app.utils.agent_instance import initialize_agent

from app.core.logger import get_logger
import os

logger = get_logger("strideiq-backend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 FastAPI app is starting...")
    try:
        # Create database tables (async version)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Application database tables ensured.")

        # Initialize AI agent
        initialize_agent()

    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise e

    yield

    logger.info("🛑 FastAPI app is shutting down...")

# Development mode detection
IS_DEVELOPMENT = os.getenv("ENVIRONMENT", "development") == "development"

# Enhanced Swagger configuration for development
swagger_ui_parameters = {
    "deepLinking": True,
    "displayRequestDuration": True,
    "tryItOutEnabled": True,
    "filter": True,
    "syntaxHighlight.theme": "arta",
}

if IS_DEVELOPMENT:
    swagger_ui_parameters["persistAuthorization"] = True

# Create FastAPI app with enhanced authentication scheme
app = FastAPI(
    title="StrideIQ Backend", 
    version="1.0.0", 
    lifespan=lifespan,
    description="""
    StrideIQ Backend API for mobile application.
    
    ## Authentication
    
    **Development Mode**: Authentication is currently bypassed for development. All endpoints will work without authentication.
    
    **Production Mode**: Uses Clerk JWT tokens. Include your JWT token in the Authorization header:
    ```
    Authorization: Bearer <your-jwt-token>
    ```
    
    ## Testing Endpoints
    
    In development mode, you can test all endpoints directly from this Swagger interface without authentication.
    """,
    swagger_ui_parameters=swagger_ui_parameters,
    openapi_components={
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Enter your JWT token from Clerk authentication (Not required in development mode)"
            },
            "DevelopmentMode": {
                "type": "apiKey",
                "in": "header",
                "name": "X-Development-Mode",
                "description": "Development mode override (set to 'true' for testing)"
            }
        }
    },
    # Remove global security requirement in development
    openapi_security=[] if IS_DEVELOPMENT else [{"BearerAuth": []}]
)

# CORS configuration
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",  # Add Swagger UI origin
    "http://127.0.0.1:8000",
    "https://your-frontend-domain.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    ClerkAuthMiddleware,
    whitelisted_routes=whitelisted_routes
)

# Include API routers
app.include_router(user_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")
app.include_router(webhook_router, prefix="/api/v1")
app.include_router(vo2_router, prefix="/api/v1")
app.include_router(onboarding_router, prefix="/api/v1")
app.include_router(recommendations_router, prefix="/api/v1")
app.include_router(coaching_chat_router, prefix="/api/v1")
app.include_router(progress_router, prefix="/api/v1")

# Development info endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint with development information."""
    return {
        "message": "StrideIQ Backend API",
        "docs": "/docs",
        "development_mode": IS_DEVELOPMENT,
        "version": "1.0.0"
    }

# 404 middleware
@app.middleware("http")
async def catch_all_404_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        if response.status_code == 404:
            return JSONResponse(
                status_code=404, 
                content={"error": "Route not found", "path": str(request.url.path)}
            )
        return response
    except Exception as e:
        raise e

# Custom validation error handler for debugging
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error on {request.url.path}: {exc.errors()}")
    logger.error(f"Request method: {request.method}")
    logger.error(f"Request headers: {dict(request.headers)}")
    
    # Convert validation errors to JSON-serializable format
    errors = []
    for error in exc.errors():
        error_dict = {
            "type": error.get("type"),
            "loc": error.get("loc"),
            "msg": error.get("msg"),
            "input": str(error.get("input")) if error.get("input") is not None else None
        }
        errors.append(error_dict)
    
    error_detail = {
        "detail": errors,
        "url": str(request.url),
        "method": request.method
    }
    
    return JSONResponse(
        status_code=422,
        content=error_detail
    )

# Exception handlers
app.add_exception_handler(ApplicationException, application_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,  # This matches your current setup
        reload=True,
        limit_concurrency=20,
        timeout_keep_alive=30,
        limit_max_requests=1000,
        timeout_graceful_shutdown=30
    )