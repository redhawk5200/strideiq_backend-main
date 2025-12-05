import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

class Settings:
    # Environment setting
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

    # OpenAI API KEY
    openai_api_key: str = os.getenv("OPENAI_API_KEY")
    
    # Clerk Configuration
    CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
    CLERK_WEBHOOK_SECRET = os.getenv("CLERK_WEBHOOK_SECRET")
    
    # db creds
    DB_HOST = os.getenv("DB_HOST", "host_db.us-east-1.rds.amazonaws.com")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_NAME = os.getenv("DB_NAME", "postgres")
    DB_PORT = os.getenv("DB_PORT", "5432")
    
    # AWS S3 Configuration
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME", "manual-minds-documents")
    
    # Build URL with SSL requirement based on environment
    def _build_database_url(self):
        base_url = f"postgresql+asyncpg://{self.DB_USER}:{quote_plus(self.DB_PASSWORD)}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        if self.ENVIRONMENT == "development":
            return f"{base_url}?ssl=require"
        else:
            return f"{base_url}?ssl=require"
    
    @property
    def DATABASE_URL(self):
        return self._build_database_url()
    
settings = Settings()
