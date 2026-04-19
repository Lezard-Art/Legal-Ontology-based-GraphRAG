from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url_corpus: str = "sqlite:///./corpus.db"
    database_url_parsed: str = "sqlite:///./parsed.db"
    blob_store_root: str = "./data/raw"
    log_level: str = "INFO"


settings = Settings()
