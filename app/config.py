from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:sobertone123@localhost:5432/sobertone"
    SECRET_KEY: str = "change-this-in-production-use-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Groq — free tier, used for all chat/insight/pattern calls
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-70b-versatile"

    # OpenAI — optional, only needed for vector memory embeddings
    # Leave blank to run without memory (still works great)
    OPENAI_API_KEY: str = ""
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Pinecone — optional, only needed if OPENAI_API_KEY is set
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "sobertone-memory"
    PINECONE_ENVIRONMENT: str = "us-east-1"

    APP_ENV: str = "development"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
