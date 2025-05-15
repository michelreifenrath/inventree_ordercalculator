import pytest
import os
from unittest import mock

from inventree_order_calculator.config import Config, ConfigError, EmailConfig # Updated import

# Expected values for testing
TEST_URL = "http://test.inventree.com"
TEST_TOKEN = "test_api_token_12345"
TEST_INSTANCE_URL = "http://test.instance.inventree.com"
TEST_DEFAULT_RECIPIENT = "default_recipient@example.com"
TEST_SMTP_SERVER = "mail.example.com"
TEST_SENDER_EMAIL = "sender@example.com"


@mock.patch.dict(os.environ, {
    "INVENTREE_API_URL": TEST_URL, # Changed from INVENTREE_URL
    "INVENTREE_API_TOKEN": TEST_TOKEN,
    "INVENTREE_INSTANCE_URL": TEST_INSTANCE_URL,
    "DEFAULT_RECIPIENT_EMAIL": TEST_DEFAULT_RECIPIENT,
    "EMAIL_SMTP_SERVER": TEST_SMTP_SERVER,
    "EMAIL_SENDER_ADDRESS": TEST_SENDER_EMAIL,
    # Add other necessary email fields for EmailConfig instantiation if defaults are not sufficient
    "EMAIL_SMTP_PORT": "587",
    "EMAIL_USE_TLS": "true",
    "EMAIL_USE_SSL": "false",
    "EMAIL_USERNAME": "user",
    "EMAIL_PASSWORD": "password",
    "EMAIL_SMTP_TIMEOUT": "30",
})
def test_load_config_success_with_all_values():
    """Test successful loading of all config variables including new email ones."""
    config = Config.load()
    assert config.INVENTREE_API_URL == TEST_URL
    assert config.INVENTREE_API_TOKEN == TEST_TOKEN
    assert config.INVENTREE_INSTANCE_URL == TEST_INSTANCE_URL
    assert config.DEFAULT_RECIPIENT_EMAIL == TEST_DEFAULT_RECIPIENT
    assert config.EMAIL_SMTP_SERVER == TEST_SMTP_SERVER # Check one email specific var

@mock.patch('inventree_order_calculator.config.load_dotenv')
@mock.patch.dict(os.environ, {"INVENTREE_API_URL": TEST_URL, "INVENTREE_API_TOKEN": TEST_TOKEN})
def test_load_config_success_without_optional_urls(mock_load_dotenv):
    """Test successful loading when optional INVENTREE_INSTANCE_URL and DEFAULT_RECIPIENT_EMAIL are missing."""
    if "INVENTREE_INSTANCE_URL" in os.environ:
        del os.environ["INVENTREE_INSTANCE_URL"]
    if "DEFAULT_RECIPIENT_EMAIL" in os.environ:
        del os.environ["DEFAULT_RECIPIENT_EMAIL"]

    config = Config.load()
    assert config.INVENTREE_API_URL == TEST_URL
    assert config.INVENTREE_API_TOKEN == TEST_TOKEN
    assert config.INVENTREE_INSTANCE_URL is None
    assert config.DEFAULT_RECIPIENT_EMAIL is None # Should be None if not set
    mock_load_dotenv.assert_called_once()


@mock.patch('inventree_order_calculator.config.load_dotenv')
@mock.patch.dict(os.environ, {"INVENTREE_API_TOKEN": TEST_TOKEN, "INVENTREE_INSTANCE_URL": TEST_INSTANCE_URL}, clear=True)
def test_load_config_missing_url(mock_load_dotenv):
    """Test ConfigError is raised if INVENTREE_API_URL is missing."""
    with pytest.raises(ConfigError) as excinfo:
        Config.load()
    assert "INVENTREE_API_URL not found in environment variables" in str(excinfo.value)

@mock.patch('inventree_order_calculator.config.load_dotenv')
@mock.patch.dict(os.environ, {"INVENTREE_API_URL": TEST_URL}, clear=True)
def test_load_config_missing_token(mock_load_dotenv):
    """Test ConfigError is raised if INVENTREE_API_TOKEN is missing."""
    with pytest.raises(ConfigError) as excinfo:
        Config.load()
    assert "INVENTREE_API_TOKEN not found in environment variables" in str(excinfo.value)

@mock.patch('inventree_order_calculator.config.load_dotenv')
@mock.patch.dict(os.environ, {}, clear=True)
def test_load_config_missing_both_core_vars(mock_load_dotenv):
    """Test ConfigError is raised if both core InvenTree variables are missing."""
    with pytest.raises(ConfigError) as excinfo:
        Config.load()
    assert "INVENTREE_API_URL not found" in str(excinfo.value)

@mock.patch('inventree_order_calculator.config.load_dotenv')
@mock.patch.dict(os.environ, {}, clear=True)
def test_load_config_from_dotenv_file(mock_load_dotenv):
    """Test loading config purely from mocked .env file via load_dotenv."""
    def side_effect(*args, **kwargs):
        os.environ["INVENTREE_API_URL"] = TEST_URL
        os.environ["INVENTREE_API_TOKEN"] = TEST_TOKEN
        os.environ["INVENTREE_INSTANCE_URL"] = TEST_INSTANCE_URL
        os.environ["DEFAULT_RECIPIENT_EMAIL"] = TEST_DEFAULT_RECIPIENT
        os.environ["EMAIL_SMTP_SERVER"] = TEST_SMTP_SERVER
        os.environ["EMAIL_SENDER_ADDRESS"] = TEST_SENDER_EMAIL
    mock_load_dotenv.side_effect = side_effect

    config = Config.load()
    assert config.INVENTREE_API_URL == TEST_URL
    assert config.INVENTREE_API_TOKEN == TEST_TOKEN
    assert config.INVENTREE_INSTANCE_URL == TEST_INSTANCE_URL
    assert config.DEFAULT_RECIPIENT_EMAIL == TEST_DEFAULT_RECIPIENT
    expected_dotenv_path = os.path.join(os.getcwd(), ".env") # Assumes .env is in cwd for find_dotenv(usecwd=True)
    mock_load_dotenv.assert_called_once_with(dotenv_path=expected_dotenv_path, override=False)

@mock.patch('inventree_order_calculator.config.load_dotenv')
@mock.patch.dict(os.environ, {
    "INVENTREE_API_URL": "env_url",
    "INVENTREE_API_TOKEN": "env_token",
    "INVENTREE_INSTANCE_URL": "env_instance_url",
    "DEFAULT_RECIPIENT_EMAIL": "env_default@example.com"
})
def test_load_config_env_overrides_dotenv(mock_load_dotenv):
    """Test that environment variables override .env values."""
    def side_effect(*args, **kwargs):
        if "INVENTREE_API_URL" not in os.environ:
             os.environ["INVENTREE_API_URL"] = "dotenv_url"
        # ... (similar for other vars, not strictly needed if override=False is tested)
    mock_load_dotenv.side_effect = side_effect

    config = Config.load()
    assert config.INVENTREE_API_URL == "env_url"
    assert config.INVENTREE_API_TOKEN == "env_token"
    assert config.INVENTREE_INSTANCE_URL == "env_instance_url"
    assert config.DEFAULT_RECIPIENT_EMAIL == "env_default@example.com"
    mock_load_dotenv.assert_called_once()

def test_config_instantiation_all_present():
    """Test that Config can be instantiated with all attributes."""
    # This test is more about the dataclass definition itself
    config = Config(
        INVENTREE_API_URL=TEST_URL,
        INVENTREE_API_TOKEN=TEST_TOKEN,
        INVENTREE_INSTANCE_URL=TEST_INSTANCE_URL,
        DEFAULT_RECIPIENT_EMAIL=TEST_DEFAULT_RECIPIENT,
        EMAIL_SMTP_SERVER=TEST_SMTP_SERVER,
        EMAIL_SENDER_ADDRESS=TEST_SENDER_EMAIL
        # Add other required fields or ensure defaults are handled
    )
    assert config.INVENTREE_API_URL == TEST_URL
    assert config.DEFAULT_RECIPIENT_EMAIL == TEST_DEFAULT_RECIPIENT

def test_config_instantiation_optional_missing():
    """Test that Config can be instantiated with optional attributes missing."""
    config = Config(INVENTREE_API_URL=TEST_URL, INVENTREE_API_TOKEN=TEST_TOKEN)
    assert config.INVENTREE_API_URL == TEST_URL
    assert config.INVENTREE_API_TOKEN == TEST_TOKEN
    assert config.INVENTREE_INSTANCE_URL is None
    assert config.DEFAULT_RECIPIENT_EMAIL is None
    assert config.EMAIL_SMTP_SERVER is None # Example of another optional field

# --- New tests for EmailConfig and get_email_config ---

@mock.patch.dict(os.environ, {
    "INVENTREE_API_URL": "dummy_url", # Required by Config.load()
    "INVENTREE_API_TOKEN": "dummy_token", # Required by Config.load()
    "EMAIL_SMTP_SERVER": "smtp.example.com",
    "EMAIL_SMTP_PORT": "123",
    "EMAIL_USERNAME": "testuser",
    "EMAIL_PASSWORD": "testpassword",
    "EMAIL_SENDER_ADDRESS": "sender@example.com",
    "EMAIL_USE_TLS": "false",
    "EMAIL_USE_SSL": "true",
    "DEFAULT_RECIPIENT_EMAIL": "default@example.com",
    "EMAIL_SMTP_TIMEOUT": "45"
})
def test_get_email_config_method():
    """Test the get_email_config method on the Config class."""
    main_config = Config.load()
    email_config = main_config.get_email_config()

    assert isinstance(email_config, EmailConfig)
    assert email_config.smtp_server == "smtp.example.com"
    assert email_config.smtp_port == 123
    assert email_config.smtp_user == "testuser"
    assert email_config.smtp_password == "testpassword"
    assert email_config.sender_email == "sender@example.com"
    assert email_config.use_tls is False
    assert email_config.use_ssl is True
    assert email_config.default_recipient_email == "default@example.com"
    assert email_config.smtp_timeout == 45

@mock.patch.dict(os.environ, {
    "INVENTREE_API_URL": "dummy_url",
    "INVENTREE_API_TOKEN": "dummy_token",
    # Minimal email settings, relying on EmailConfig defaults
    "EMAIL_SENDER_ADDRESS": "minimal@example.com", # Required by EmailConfig if not None
    "DEFAULT_RECIPIENT_EMAIL": "minimal_default@example.com" # Required by EmailConfig if not None
})
def test_get_email_config_with_defaults():
    """Test get_email_config when many email settings use Pydantic defaults."""
    main_config = Config.load() # Loads DEFAULT_RECIPIENT_EMAIL from env
    
    # Override some main_config fields to test EmailConfig defaults more directly
    main_config.EMAIL_SMTP_SERVER = None
    main_config.EMAIL_SMTP_PORT = 587 # Default from Config dataclass
    main_config.EMAIL_USE_TLS = True  # Default from Config dataclass
    main_config.EMAIL_USE_SSL = False # Default from Config dataclass
    main_config.EMAIL_SMTP_TIMEOUT = 30 # Default from Config dataclass
    # DEFAULT_RECIPIENT_EMAIL is already set from env by Config.load()

    email_config = main_config.get_email_config()

    assert email_config.smtp_server is None # Pydantic default is None
    assert email_config.smtp_port == 587    # Pydantic default is 587
    assert email_config.smtp_user is None   # Pydantic default is None
    assert email_config.use_tls is True     # Pydantic default is True
    assert email_config.use_ssl is False    # Pydantic default is False
    assert email_config.sender_email == "minimal@example.com" # This came from main_config
    assert email_config.default_recipient_email == "minimal_default@example.com" # This came from main_config
    assert email_config.smtp_timeout == 30  # Pydantic default is 30

def test_email_config_model_validation():
    """Test Pydantic EmailConfig model validation for email fields."""
    # Valid
    EmailConfig(sender_email="test@example.com", default_recipient_email="test2@example.com")
    # Invalid
    with pytest.raises(ValueError): # Pydantic raises ValueError for validation errors
        EmailConfig(sender_email="invalid-email")
    with pytest.raises(ValueError):
        EmailConfig(default_recipient_email="another-invalid")
    # Port validation (Pydantic converts to int, so type error if not convertible)
    with pytest.raises(ValueError):
        EmailConfig(smtp_port="not-a-port")