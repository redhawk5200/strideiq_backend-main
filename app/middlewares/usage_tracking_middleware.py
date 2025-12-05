# app/middlewares/usage_tracking_middleware.py

import time
import asyncio
import tiktoken
from typing import Optional, Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.usage_tracking_service import usage_service
from app.core.logger import get_logger

logger = get_logger("usage_tracking_middleware")

class UsageTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically track AI token usage and API performance"""
    
    def __init__(self, app):
        super().__init__(app)
        # Initialize tokenizer for GPT-4 models
        try:
            self.tokenizer = tiktoken.encoding_for_model("gpt-4")
        except:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    async def dispatch(self, request: Request, call_next):
        # Only track certain endpoints
        if not self._should_track_request(request):
            return await call_next(request)
        
        # Start timing
        start_time = time.time()
        
        # Extract user and workspace context from request
        user_id = getattr(request.state, 'user_id', None)
        workspace_id = getattr(request.state, 'workspace_id', None)
        
        # Process the request
        response = await call_next(request)
        
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Track usage if we have context
        if user_id and workspace_id and self._is_ai_endpoint(request):
            # Run tracking in background to avoid slowing response
            asyncio.create_task(
                self._track_ai_usage_async(
                    request, response, user_id, workspace_id, response_time_ms
                )
            )
        
        # Add performance headers
        response.headers["X-Response-Time"] = str(response_time_ms)
        
        return response
    
    def _should_track_request(self, request: Request) -> bool:
        """Determine if request should be tracked"""
        path = request.url.path
        
        # Track AI endpoints and key API endpoints
        track_patterns = [
            "/api/v1/chat",
            "/api/v1/documents/upload",
            "/api/v1/admin"
        ]
        
        return any(pattern in path for pattern in track_patterns)
    
    def _is_ai_endpoint(self, request: Request) -> bool:
        """Check if endpoint uses AI/tokens"""
        path = request.url.path
        return "/chat" in path
    
    async def _track_ai_usage_async(
        self, 
        request: Request, 
        response: Response, 
        user_id: str, 
        workspace_id: str, 
        response_time_ms: int
    ):
        """Track AI usage asynchronously"""
        try:
            # Get database session
            async for db in get_db():
                # Extract usage information from request/response
                usage_info = await self._extract_usage_info(request, response)
                
                if usage_info:
                    # Log token usage
                    await usage_service.log_token_usage(
                        db=db,
                        workspace_id=workspace_id,
                        user_id=user_id,
                        model_name=usage_info.get('model_name', 'gpt-4o'),
                        input_tokens=usage_info.get('input_tokens', 0),
                        output_tokens=usage_info.get('output_tokens', 0),
                        endpoint=request.url.path,
                        operation_type=usage_info.get('operation_type', 'chat'),
                        session_id=usage_info.get('session_id'),
                        response_time_ms=response_time_ms
                    )
                
                break  # Exit the async generator
                
        except Exception as e:
            logger.error(f"Error tracking AI usage: {e}")
    
    async def _extract_usage_info(self, request: Request, response: Response) -> Optional[Dict[str, Any]]:
        """Extract token usage information from request/response"""
        try:
            # Get request body if available
            if hasattr(request.state, 'body'):
                request_body = request.state.body
            else:
                # Try to read body (this might not work in all cases)
                request_body = await request.body() if hasattr(request, 'body') else b""
            
            # Extract query from request
            query_text = ""
            session_id = None
            
            # For chat endpoints, extract question and session_id
            if "/chat" in request.url.path:
                # Try to get from query parameters first
                query_params = dict(request.query_params)
                query_text = query_params.get('question', '')
                session_id = query_params.get('session_id', '')
                
                # If not in query params, might be in request body (for POST requests)
                if not query_text and request_body:
                    try:
                        import json
                        body_data = json.loads(request_body.decode())
                        query_text = body_data.get('question', '')
                        session_id = body_data.get('session_id', '')
                    except:
                        pass
            
            if not query_text:
                return None
            
            # Estimate input tokens from query
            input_tokens = self._estimate_tokens(query_text)
            
            # Estimate output tokens from response
            output_tokens = 0
            if hasattr(response, 'body'):
                try:
                    # For streaming responses, this might not capture everything
                    # But we can estimate based on average response length
                    output_tokens = max(100, input_tokens // 2)  # Conservative estimate
                except:
                    output_tokens = 150  # Default estimate
            else:
                output_tokens = 150  # Default estimate for streaming responses
            
            return {
                'model_name': 'gpt-4o',  # Default model
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'operation_type': 'chat',
                'session_id': session_id if session_id else None
            }
            
        except Exception as e:
            logger.error(f"Error extracting usage info: {e}")
            return None
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        try:
            if not text:
                return 0
            return len(self.tokenizer.encode(text))
        except Exception as e:
            logger.warning(f"Error estimating tokens: {e}")
            # Fallback: rough estimate (1 token ≈ 4 characters)
            return max(1, len(text) // 4)


class TokenUsageTracker:
    """Helper class for manual token usage tracking"""
    
    def __init__(self):
        try:
            self.tokenizer = tiktoken.encoding_for_model("gpt-4")
        except:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        try:
            return len(self.tokenizer.encode(text))
        except Exception as e:
            logger.warning(f"Error counting tokens: {e}")
            return max(1, len(text) // 4)  # Fallback estimate
    
    async def track_streaming_usage(
        self,
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
        input_text: str,
        output_text: str,
        model_name: str = "gpt-4o",
        endpoint: str = "/chat",
        operation_type: str = "chat",
        session_id: Optional[str] = None,
        response_time_ms: Optional[int] = None
    ):
        """Manually track token usage for streaming responses"""
        
        input_tokens = self.count_tokens(input_text)
        output_tokens = self.count_tokens(output_text)
        
        await usage_service.log_token_usage(
            db=db,
            workspace_id=workspace_id,
            user_id=user_id,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            endpoint=endpoint,
            operation_type=operation_type,
            session_id=session_id,
            response_time_ms=response_time_ms
        )

# Global tracker instance
token_tracker = TokenUsageTracker()