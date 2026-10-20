from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env from the project root (demoa_fullstack/.env),
# regardless of which directory the process is launched from.
_ENV_FILE = Path(__file__).resolve().parents[3] / '.env'


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding='utf-8',
        extra='ignore',
    )

    app_name: str = 'Student Course Insight Chatbot'
    secret_key: str = 'demo-b-secret-change-in-production'
    algorithm: str = 'HS256'
    access_token_expire_minutes: int = 60
    privacy_min_sample_size: int = 10

    database_url: str = 'postgresql://insight:insight_pass@localhost:5432/insight_db'
    openai_api_key: str = ''

    # Optional overrides for any OpenAI-compatible provider.
    # Leave blank to use api.openai.com. The chat and embedding endpoints can
    # point at different providers (e.g. a free chat model + a cheap embedding model).
    llm_api_key: str = ''
    llm_base_url: str = ''
    embedding_api_key: str = ''
    embedding_base_url: str = ''

    embedding_model: str = 'text-embedding-3-small'
    embedding_dimensions: int = 1536
    embedding_batch_size: int = 200
    chat_model: str = 'gpt-4o-mini'


settings = Settings()
