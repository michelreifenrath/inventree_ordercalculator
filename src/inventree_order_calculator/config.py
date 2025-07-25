import os
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv, find_dotenv

class ConfigError(Exception):
    """Custom exception for configuration errors."""
    pass

logger = logging.getLogger(__name__)

@dataclass
class AppConfig:
    """Application configuration data."""
    inventree_url: str
    inventree_api_token: str
    inventree_instance_url: Optional[str] = None
    presets_file_path: Path = Path("presets.json")

    @classmethod
    def load(cls) -> 'AppConfig':
        """
        Loads configuration from environment variables.

        Loads .env file first, then checks environment variables.
        Raises ConfigError if required variables are missing.
        """
        dotenv_path = find_dotenv(usecwd=True) # Search in current working directory and upwards
        logger.debug(f"Attempting to load .env file from: {dotenv_path if dotenv_path else 'Not found'}")
        found_dotenv = load_dotenv(dotenv_path=dotenv_path, override=False) # Load .env file if it exists, but don't override existing env vars
        logger.debug(f".env file found: {found_dotenv}")

        url = os.environ.get("INVENTREE_URL")
        token = os.environ.get("INVENTREE_API_TOKEN")
        instance_url = os.environ.get("INVENTREE_INSTANCE_URL")
        presets_path = os.environ.get("PRESETS_FILE_PATH", "presets.json")

        logger.debug(f"INVENTREE_URL from env/dotenv: {url}")
        logger.debug(f"INVENTREE_API_TOKEN from env/dotenv: {'SET' if token else 'NOT SET'}") # Avoid logging the token itself
        logger.debug(f"INVENTREE_INSTANCE_URL from env/dotenv: {instance_url}")
        logger.debug(f"PRESETS_FILE_PATH from env/dotenv: {presets_path}")

        if not url:
            logger.error("INVENTREE_URL not found in environment variables or .env file")
            raise ConfigError("INVENTREE_URL not found in environment variables or .env file")
        if not token:
            logger.error("INVENTREE_API_TOKEN not found in environment variables or .env file")
            raise ConfigError("INVENTREE_API_TOKEN not found in environment variables or .env file")

        config_instance = cls(
            inventree_url=url,
            inventree_api_token=token,
            inventree_instance_url=instance_url,
            presets_file_path=Path(presets_path)
        )
        logger.info(
            f"AppConfig loaded: URL='{config_instance.inventree_url}', "
            f"Token is {'SET' if config_instance.inventree_api_token else 'NOT SET'}, "
            f"Instance URL='{config_instance.inventree_instance_url}', "
            f"Presets path='{config_instance.presets_file_path}'"
        )
        return config_instance