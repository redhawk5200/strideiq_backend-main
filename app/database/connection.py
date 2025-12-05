from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool
from sqlalchemy import text
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("database")

# Determine SSL requirement based on environment
ssl_config = {} if settings.ENVIRONMENT == "development" else {"ssl": "require"}

# OPTIMIZED engine configuration with connection pooling for sub-second responses
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Disable SQL logging for production performance
    connect_args={
        **ssl_config,
        "server_settings": {
            "application_name": "strideiq_backend",
            "jit": "off",
        },
        "command_timeout": 30,
        "prepared_statement_cache_size": 500,
    },
    # Connection pool configuration - THIS IS THE FIX
    poolclass=AsyncAdaptedQueuePool,
    pool_size=10,            # Keep 10 connections ready
    max_overflow=20,         # Allow 20 additional connections under load
    pool_timeout=30,         # Wait up to 30s for a connection
    pool_recycle=1800,       # Recycle connections every 30 minutes
    pool_pre_ping=True,      # Verify connections are alive before using
    query_cache_size=1000,
    future=True
)

# Ultra-optimized session configuration
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,         # Disable autoflush for maximum speed
    autocommit=False
)

async def get_db():
    """Dependency for getting database session - OPTIMIZED."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

@asynccontextmanager
async def async_session():
    """Context manager for database session - OPTIMIZED."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Keep only basic admin stats query - remove complex performance monitoring
class DatabaseQueries:
    
    @staticmethod
    async def get_admin_stats(db: AsyncSession):
        """Get basic admin dashboard stats"""
        stats_query = text("""
        SELECT 
            (SELECT COUNT(*) FROM users WHERE is_active = true) as active_users,
            (SELECT COUNT(*) FROM users) as total_users,
            (SELECT COUNT(*) FROM devices) as total_devices,
            (SELECT COUNT(*) FROM heart_rate_samples) as total_hr_samples,
            (SELECT COUNT(*) FROM sleep_sessions) as total_sleep_sessions
        """)
        
        result = await db.execute(stats_query)
        row = result.first()
        
        return {
            'active_users': row.active_users or 0,
            'total_users': row.total_users or 0,
            'total_devices': row.total_devices or 0,
            'total_hr_samples': row.total_hr_samples or 0,
            'total_sleep_sessions': row.total_sleep_sessions or 0,
        }

# Create global instance
db_queries = DatabaseQueries()
