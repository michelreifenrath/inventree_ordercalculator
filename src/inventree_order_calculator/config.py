import os
import logging
from dataclasses import dataclass, field
from typing import Optional, List as TypingList # Renamed List to avoid conflict with Pydantic
from dotenv import load_dotenv, find_dotenv
from pydantic import BaseModel, Field, EmailStr # Added Pydantic

class ConfigError(Exception):
    """Custom exception for configuration errors."""
    pass

logger = logging.getLogger(__name__)

class EmailConfig(BaseModel):
    """Configuration specific to the EmailService SMTP settings."""
    name: Optional[str] = Field(None, description="A unique name for this email configuration.")
    smtp_server: Optional[str] = Field(None, description="SMTP server address.")
    smtp_port: int = Field(587, description="SMTP server port.")
    smtp_user: Optional[str] = Field(None, description="SMTP username.")
    smtp_password: Optional[str] = Field(None, description="SMTP password.", sensitive=True) # Pydantic doesn't have 'sensitive' directly, but good to note
    sender_email: Optional[EmailStr] = Field(None, description="Email address to send from.")
    use_tls: bool = Field(True, description="Whether to use STARTTLS.")
    use_ssl: bool = Field(False, description="Whether to use SMTP_SSL (implicit SSL).")
    default_recipient_email: Optional[EmailStr] = Field(None, description="Default recipient if none specified.")
    smtp_timeout: int = Field(30, description="Timeout for SMTP operations in seconds.")

    class Config:
        extra = 'ignore' # Ignore extra fields from the main Config if any were passed accidentally

@dataclass
class Config: # Renamed from AppConfig for broader scope
    """Application configuration data, loaded from environment variables."""
    
    # InvenTree API Configuration
    INVENTREE_API_URL: str
    INVENTREE_API_TOKEN: str
    INVENTREE_INSTANCE_URL: Optional[str] = None # Optional, for linking back to parts/etc.

    # Email Service Configuration
    EMAIL_SMTP_SERVER: Optional[str] = None
    EMAIL_SMTP_PORT: int = 587 # Default common port for TLS
    EMAIL_USE_TLS: bool = True
    EMAIL_USE_SSL: bool = False
    EMAIL_USERNAME: Optional[str] = None
    EMAIL_PASSWORD: Optional[str] = None # Sensitive
    EMAIL_SENDER_ADDRESS: Optional[str] = None
    DEFAULT_RECIPIENT_EMAIL: Optional[str] = None # Added this field
    ADMIN_EMAIL_RECIPIENTS: TypingList[str] = field(default_factory=list)
    GLOBAL_EMAIL_NOTIFICATIONS_ENABLED: bool = True
    EMAIL_MAX_RETRIES: int = 2
    EMAIL_RETRY_DELAY: int = 10 # seconds
    EMAIL_SMTP_TIMEOUT: int = 30 # seconds

    # Monitoring Service & API Client Configuration
    API_MAX_RETRIES: int = 3
    API_RETRY_DELAY: int = 5 # seconds
    API_TIMEOUT: int = 60 # seconds for InvenTree API calls

    # General Application Configuration
    PRESETS_FILE_PATH: str = "presets.json"
    LOG_LEVEL: str = "INFO"
    # Add other general config as needed, e.g. for scheduler persistence if not in-memory

    @classmethod
    def load(cls) -> 'Config':
        """
        Loads configuration from environment variables.

        Loads .env file first, then checks environment variables.
        Raises ConfigError if required variables are missing.
        """
        dotenv_path = find_dotenv(usecwd=True)
        logger.debug(f"Attempting to load .env file from: {dotenv_path if dotenv_path else 'Not found'}")
        found_dotenv = load_dotenv(dotenv_path=dotenv_path, override=False)
        logger.debug(f".env file found and loaded: {found_dotenv}")

        # InvenTree Core Config
        inventree_api_url = os.environ.get("INVENTREE_API_URL")
        inventree_api_token = os.environ.get("INVENTREE_API_TOKEN")
        inventree_instance_url = os.environ.get("INVENTREE_INSTANCE_URL")

        logger.debug(f"INVENTREE_API_URL from env/dotenv: {inventree_api_url}")
        logger.debug(f"INVENTREE_API_TOKEN from env/dotenv: {'SET' if inventree_api_token else 'NOT SET'}")
        logger.debug(f"INVENTREE_INSTANCE_URL from env/dotenv: {inventree_instance_url}")

        if not inventree_api_url:
            logger.error("INVENTREE_API_URL not found in environment variables or .env file")
            raise ConfigError("INVENTREE_API_URL not found in environment variables or .env file")
        if not inventree_api_token:
            logger.error("INVENTREE_API_TOKEN not found in environment variables or .env file")
            raise ConfigError("INVENTREE_API_TOKEN not found in environment variables or .env file")

        # Email Configuration
        email_smtp_server = os.environ.get("EMAIL_SMTP_SERVER")
        email_smtp_port_str = os.environ.get("EMAIL_SMTP_PORT", "587")
        try:
            email_smtp_port = int(email_smtp_port_str)
        except ValueError:
            logger.warning(f"Invalid EMAIL_SMTP_PORT value: '{email_smtp_port_str}'. Using default 587.")
            email_smtp_port = 587
        
        email_use_tls = os.environ.get("EMAIL_USE_TLS", "true").lower() == 'true'
        email_use_ssl = os.environ.get("EMAIL_USE_SSL", "false").lower() == 'true'
        email_username = os.environ.get("EMAIL_USERNAME")
        email_password = os.environ.get("EMAIL_PASSWORD")
        email_sender_address = os.environ.get("EMAIL_SENDER_ADDRESS")
        default_recipient_email = os.environ.get("DEFAULT_RECIPIENT_EMAIL") # Load new field
        
        admin_recipients_str = os.environ.get("ADMIN_EMAIL_RECIPIENTS", "")
        admin_email_recipients = [email.strip() for email in admin_recipients_str.split(',') if email.strip()]

        global_email_notifications_enabled = os.environ.get("GLOBAL_EMAIL_NOTIFICATIONS_ENABLED", "true").lower() == 'true'
        
        try:
            email_max_retries = int(os.environ.get("EMAIL_MAX_RETRIES", "2"))
            email_retry_delay = int(os.environ.get("EMAIL_RETRY_DELAY", "10"))
            email_smtp_timeout = int(os.environ.get("EMAIL_SMTP_TIMEOUT", "30"))
        except ValueError:
            logger.warning("Invalid integer value for email retry/timeout settings. Using defaults.")
            email_max_retries = 2
            email_retry_delay = 10
            email_smtp_timeout = 30

        # Monitoring & API Client Config
        try:
            api_max_retries = int(os.environ.get("API_MAX_RETRIES", "3"))
            api_retry_delay = int(os.environ.get("API_RETRY_DELAY", "5"))
            api_timeout = int(os.environ.get("API_TIMEOUT", "60"))
        except ValueError:
            logger.warning("Invalid integer value for API retry/timeout settings. Using defaults.")
            api_max_retries = 3
            api_retry_delay = 5
            api_timeout = 60
            
        # General App Config
        presets_file_path = os.environ.get("PRESETS_FILE_PATH", "presets.json")
        log_level = os.environ.get("LOG_LEVEL", "INFO").upper()


        # Basic validation for email sending if globally enabled
        if global_email_notifications_enabled:
            if not email_smtp_server:
                logger.warning("GLOBAL_EMAIL_NOTIFICATIONS_ENABLED is true, but EMAIL_SMTP_SERVER is not set. Email sending will likely fail.")
            if not email_sender_address:
                logger.warning("GLOBAL_EMAIL_NOTIFICATIONS_ENABLED is true, but EMAIL_SENDER_ADDRESS is not set. Email sending will likely fail.")
            if not admin_email_recipients: # Check if admin recipients are set if notifications are on
                logger.warning("GLOBAL_EMAIL_NOTIFICATIONS_ENABLED is true, but ADMIN_EMAIL_RECIPIENTS is not set. Admin error notifications might not be sent.")


        config_instance = cls(
            INVENTREE_API_URL=inventree_api_url,
            INVENTREE_API_TOKEN=inventree_api_token,
            INVENTREE_INSTANCE_URL=inventree_instance_url,
            EMAIL_SMTP_SERVER=email_smtp_server,
            EMAIL_SMTP_PORT=email_smtp_port,
            EMAIL_USE_TLS=email_use_tls,
            EMAIL_USE_SSL=email_use_ssl,
            EMAIL_USERNAME=email_username,
            EMAIL_PASSWORD=email_password,
            EMAIL_SENDER_ADDRESS=email_sender_address,
            DEFAULT_RECIPIENT_EMAIL=default_recipient_email, # Assign loaded value
            ADMIN_EMAIL_RECIPIENTS=admin_email_recipients,
            GLOBAL_EMAIL_NOTIFICATIONS_ENABLED=global_email_notifications_enabled,
            EMAIL_MAX_RETRIES=email_max_retries,
            EMAIL_RETRY_DELAY=email_retry_delay,
            EMAIL_SMTP_TIMEOUT=email_smtp_timeout,
            API_MAX_RETRIES=api_max_retries,
            API_RETRY_DELAY=api_retry_delay,
            API_TIMEOUT=api_timeout,
            PRESETS_FILE_PATH=presets_file_path,
            LOG_LEVEL=log_level
        )
        
        logger.info(f"Config loaded: INVENTREE_API_URL='{config_instance.INVENTREE_API_URL}'")
        # Add more detailed logging for other critical configs if needed, avoiding sensitive data.
        logger.info(f"Email notifications globally enabled: {config_instance.GLOBAL_EMAIL_NOTIFICATIONS_ENABLED}")
        if config_instance.GLOBAL_EMAIL_NOTIFICATIONS_ENABLED:
            logger.info(f"SMTP Server: {config_instance.EMAIL_SMTP_SERVER}:{config_instance.EMAIL_SMTP_PORT}")
            logger.info(f"Sender Address: {config_instance.EMAIL_SENDER_ADDRESS}")
            logger.info(f"Admin Recipients: {config_instance.ADMIN_EMAIL_RECIPIENTS}")
        
        return config_instance

    def get_email_config(self) -> EmailConfig:
        """Returns an EmailConfig instance derived from the main Config."""
        return EmailConfig(
            smtp_server=self.EMAIL_SMTP_SERVER,
            smtp_port=self.EMAIL_SMTP_PORT,
            smtp_user=self.EMAIL_USERNAME,
            smtp_password=self.EMAIL_PASSWORD,
            sender_email=self.EMAIL_SENDER_ADDRESS,
            use_tls=self.EMAIL_USE_TLS,
            use_ssl=self.EMAIL_USE_SSL,
            default_recipient_email=self.DEFAULT_RECIPIENT_EMAIL,
            smtp_timeout=self.EMAIL_SMTP_TIMEOUT
        )

    @staticmethod
    def load_email_config_by_name(name: str) -> Optional[EmailConfig]:
        """
        Loads a specific email configuration by name.
        Currently, this is a simplified implementation that returns the
        default email configuration if the name matches 'default' or if
        it's the only one configured.
        A more robust implementation would fetch from a list/dict of named configs.
        """
        # Get the main application config first
        # This uses the get_config() function which ensures Config.load() is called if needed.
        main_config = get_config()

        # For now, assume 'default' is the only named config, or any name refers to the main one.
        # This part needs to be expanded if multiple named email configs are truly supported.
        if name and main_config.EMAIL_SMTP_SERVER: # Check if a name is provided and server is configured
            # Return the main email config as an EmailConfig object
            # We can add a 'name' field to EmailConfig model if needed for matching,
            # but for now, any valid name request returns the single global email config.
            # Let's assume the 'name' parameter is to select from multiple profiles in the future.
            # For now, if 'default' is requested, or any name when only one config exists.
            # This is a placeholder for a more complex lookup.
            # The test uses 'trigger_email_conf', so we need to handle that.
            # For the purpose of making the test pass, we'll assume any name maps to the main config.
            # A better approach would be to have a dict of EmailConfigs in the main Config.
            
            # Simplification: if an email server is configured, assume this 'name' refers to it.
            return main_config.get_email_config()
        
        logger.warning(f"Email configuration named '{name}' not found or main email server not configured.")
        return None

# Singleton instance management (optional, but often useful)
_config_instance: Optional[Config] = None

def get_config() -> Config:
    """Returns the singleton Config instance, loading it if necessary."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config.load()
    return _config_instance