# app/middlewares/upload_limit.py

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.exceptions import HTTPException
from app.core.logger import get_logger

logger = get_logger("upload_limit_middleware")

class LimitUploadSizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_upload_size: int):
        super().__init__(app)
        self.max_upload_size = max_upload_size

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            size = int(content_length)
            logger.debug(f"[LimitUploadSize] Content-Length={size} bytes, Max={self.max_upload_size} bytes")
            if size > self.max_upload_size:
                # 413 Payload Too Large
                raise HTTPException(status_code=413, detail="File too large")
        return await call_next(request)
