# app/services/queue_scheduler.py

import asyncio
from app.core.logger import get_logger

logger = get_logger("queue_scheduler")

# Global variable to track scheduler state
_scheduler_task = None
_scheduler_running = False

async def start_queue_scheduler():
    """Start queue scheduler - simplified since document processing was removed"""
    global _scheduler_running
    _scheduler_running = True
    logger.info("Queue scheduler started (simplified - no document processing)")

async def stop_queue_scheduler():
    """Stop queue scheduler"""
    global _scheduler_task, _scheduler_running
    _scheduler_running = False
    
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
    
    logger.info("Queue scheduler stopped successfully")

def is_scheduler_running() -> bool:
    """Check if scheduler is running"""
    return _scheduler_running
