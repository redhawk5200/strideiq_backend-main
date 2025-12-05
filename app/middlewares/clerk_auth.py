import os
from typing import List
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from sqlalchemy.future import select
from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions
from httpx import Request as HttpxRequest
from app.database import AsyncSessionLocal
from app.models.user import User
from app.core.logger import get_logger

logger = get_logger("clerk_auth_middleware")

def add_cors_headers(response: JSONResponse) -> JSONResponse:
    """Add CORS headers to response"""
    response.headers["Access-Control-Allow-Origin"] = "http://localhost:3000"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

whitelisted_routes = [
    "/docs", "/openapi.json", "/redoc", "/favicon.ico",
    "/api/v1/webhooks", "/api/v1/webhooks/clerk",
    # Health endpoints now require authentication
    "/api/v1/upload", "/api/v1/chat", "/api/v1/documents",
    "/api/v1/admin", "/api/v1/queue", "/api/v1/users/test",
]

class ClerkAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, whitelisted_routes: List[str] = None):
        super().__init__(app)
        self.clerk_sdk = Clerk(bearer_auth=os.getenv("CLERK_SECRET_KEY"))
        self.whitelisted_routes = whitelisted_routes 
    
    def _is_whitelisted(self, path: str) -> bool:
        """Check if the route is whitelisted (public)"""
        for route in self.whitelisted_routes:
            if path.startswith(route):
                return True
        return False

    async def dispatch(self, request: Request, call_next):
        """Main middleware logic - Verifies Clerk JWT tokens"""

        # Skip authentication for whitelisted routes (public endpoints)
        if self._is_whitelisted(request.url.path):
            logger.debug(f"Whitelisted route: {request.url.path}")
            return await call_next(request)

        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning(f"Missing or invalid Authorization header for: {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing or invalid authorization token"}
            )

        try:
            # Verify the JWT token with Clerk
            # The authenticate_request expects the raw request object
            # Create httpx request from FastAPI request
            httpx_request = HttpxRequest(
                method=request.method,
                url=str(request.url),
                headers=dict(request.headers)
            )

            # Authenticate the request
            request_state = self.clerk_sdk.authenticate_request(
                httpx_request,
                AuthenticateRequestOptions()
            )

            if not request_state.is_signed_in:
                logger.warning(f"Invalid Clerk token: {request_state.reason}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid authentication token"}
                )

            # Extract user_id from the token payload
            clerk_user_id = request_state.payload.get("sub") if request_state.payload else None
            if not clerk_user_id:
                logger.warning("No user_id in token payload")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid token payload"}
                )

            # Get or create user in database
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(User).where(User.clerk_id == clerk_user_id)
                )
                user = result.scalar_one_or_none()

                if not user:
                    # Fetch user details from Clerk
                    clerk_user = self.clerk_sdk.users.get(user_id=clerk_user_id)
                    email = clerk_user.email_addresses[0].email_address if clerk_user.email_addresses else None

                    # Check if user with this email already exists (old Clerk account deleted)
                    if email:
                        email_result = await db.execute(
                            select(User).where(User.email == email)
                        )
                        existing_user = email_result.scalar_one_or_none()

                        if existing_user:
                            # Update the existing user's clerk_id (user re-signed up after deleting Clerk account)
                            existing_user.clerk_id = clerk_user_id
                            existing_user.is_active = True
                            existing_user.is_deleted = False
                            await db.commit()
                            await db.refresh(existing_user)
                            user = existing_user
                            logger.info(f"Updated existing user's Clerk ID: {user.email} (New Clerk ID: {clerk_user_id})")
                        else:
                            # Create new user in database
                            user = User(
                                clerk_id=clerk_user_id,
                                email=email,
                                type="user",
                                is_active=True,
                                is_deleted=False
                            )
                            db.add(user)
                            await db.commit()
                            await db.refresh(user)
                            logger.info(f"Created new user: {user.email} (Clerk ID: {clerk_user_id})")
                    else:
                        # No email, just create the user
                        user = User(
                            clerk_id=clerk_user_id,
                            email=None,
                            type="user",
                            is_active=True,
                            is_deleted=False
                        )
                        db.add(user)
                        await db.commit()
                        await db.refresh(user)
                        logger.info(f"Created new user without email (Clerk ID: {clerk_user_id})")

                # Attach user to request state
                request.state.user = user
                request.state.clerk_user_id = clerk_user_id
                logger.info(f"Authenticated user: {user.email}")

            return await call_next(request)

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Authentication failed"}
            )

# Helper function to get current user from request
def get_current_user_from_request(request: Request) -> User:
    """Extract authenticated user from request state"""
    if not hasattr(request.state, 'user'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    return request.state.user


# Dependency functions for route handlers
async def get_authenticated_user(request: Request) -> User:
    """FastAPI dependency to get authenticated user"""
    return get_current_user_from_request(request)