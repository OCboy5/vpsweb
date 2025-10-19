"""
VPSWeb Repository Settings Configuration v0.3.1

Configuration settings for the repository layer.
"""

from pydantic_settings import BaseSettings


class RepositorySettings(BaseSettings):
    """Repository layer settings"""

    # Database settings
    database_url: str = "sqlite:///./repository_root/repo.db"

    # Repository storage settings
    repo_root: str = "./repository_root"
    storage_path: str = "./repository_root/data"

    # VPSWeb integration settings
    vpsweb_config_path: str = "./config"
    default_workflow_mode: str = "hybrid"

    # Logging settings
    log_level: str = "INFO"

    model_config = {
        "env_file": ".env",
        "env_prefix": "REPO_",
        "extra": "ignore"
    }


# Global settings instance
settings = RepositorySettings()