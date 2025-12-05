from fastapi import APIRouter
from app.api.v1.controllers.health_controller import health_check
from app.api.v1.endpoints import health_sync

router = APIRouter()

router.get("/health", tags=["Health"])(health_check)

# Include health sync endpoints
router.include_router(health_sync.router, prefix="/health", tags=["Health Sync"])