"""
VPSWeb Web UI Configuration v0.3.1

Configuration settings for the FastAPI web interface.
"""

from pydantic_settings import BaseSettings


class WebUISettings(BaseSettings):
    """Web UI application settings"""

    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = True
    log_level: str = "INFO"

    model_config = {
        "env_file": ".env",
        "env_prefix": "WEBUI_",
        "extra": "ignore"
    }


# Global settings instance
settings = WebUISettings()