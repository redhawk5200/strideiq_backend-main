"""
API v1 routes package.
Mobile app backend routes.
"""

from .user_routes import router as user_router
from .health_routes import router as health_router
from .webhook_routes import router as webhook_router
from .vo2_routes import router as vo2_router
from .onboarding_routes import router as onboarding_router
from .recommendations_routes import router as recommendations_router
from .coaching_chat_routes import router as coaching_chat_router
from .progress_routes import router as progress_router

__all__ = [
    "user_router",
    "health_router",
    "webhook_router",
    "vo2_router",
    "onboarding_router",
    "recommendations_router",
    "coaching_chat_router",
    "progress_router"
]
