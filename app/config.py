from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url_corpus: str = "sqlite:///./corpus.db"
    database_url_parsed: str = "sqlite:///./parsed.db"
    blob_store_root: str = "./data/raw"
    log_level: str = "INFO"

    # API keys for sources that require authentication.
    # Absent keys cause the corresponding fetcher to raise RuntimeError on use;
    # the source row is still created in the DB with enabled=False.
    congress_api_key: str = ""
    courtlistener_api_key: str = ""
    ny_senate_api_key: str = ""


settings = Settings()
