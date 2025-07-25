import pytest
import os
from pathlib import Path
from unittest import mock

from inventree_order_calculator.config import AppConfig, ConfigError

# Expected values for testing
TEST_URL = "http://test.inventree.com"
TEST_TOKEN = "test_api_token_12345"
TEST_INSTANCE_URL = "http://test.instance.inventree.com"

@mock.patch.dict(os.environ, {
    "INVENTREE_URL": TEST_URL,
    "INVENTREE_API_TOKEN": TEST_TOKEN,
    "INVENTREE_INSTANCE_URL": TEST_INSTANCE_URL
})
def test_load_config_success_with_instance_url():
    """Test successful loading of all config variables."""
    config = AppConfig.load()
    assert config.inventree_url == TEST_URL
    assert config.inventree_api_token == TEST_TOKEN
    assert config.inventree_instance_url == TEST_INSTANCE_URL

@mock.patch('inventree_order_calculator.config.load_dotenv')
@mock.patch.dict(os.environ, {"INVENTREE_URL": TEST_URL, "INVENTREE_API_TOKEN": TEST_TOKEN})
def test_load_config_success_without_instance_url(mock_load_dotenv):
    """Test successful loading when optional INVENTREE_INSTANCE_URL is missing."""
    # Ensure INVENTREE_INSTANCE_URL is not in os.environ for this test.
    # The @mock.patch.dict above sets URL and TOKEN.
    # mock_load_dotenv prevents .env file from loading and overriding.
    if "INVENTREE_INSTANCE_URL" in os.environ: # This checks the environ set by the decorator
        del os.environ["INVENTREE_INSTANCE_URL"] # This modifies the dict managed by the mock

    config = AppConfig.load()
    assert config.inventree_url == TEST_URL
    assert config.inventree_api_token == TEST_TOKEN
    assert config.inventree_instance_url is None
    mock_load_dotenv.assert_called_once() # Ensure load_dotenv was called (but did nothing)


@mock.patch('inventree_order_calculator.config.load_dotenv')
@mock.patch.dict(os.environ, {"INVENTREE_API_TOKEN": TEST_TOKEN, "INVENTREE_INSTANCE_URL": TEST_INSTANCE_URL}, clear=True)
def test_load_config_missing_url(mock_load_dotenv): # Add mock argument
    """Test ConfigError is raised if INVENTREE_URL is missing."""
    with pytest.raises(ConfigError) as excinfo:
        AppConfig.load()
    assert "INVENTREE_URL not found in environment variables" in str(excinfo.value)
    # mock_load_dotenv.assert_not_called() # Removed: Mock IS called, but doesn't load vars

@mock.patch('inventree_order_calculator.config.load_dotenv') # Add this patch
@mock.patch.dict(os.environ, {"INVENTREE_URL": TEST_URL}, clear=True)
def test_load_config_missing_token(mock_load_dotenv): # Add mock argument
    """Test ConfigError is raised if INVENTREE_API_TOKEN is missing."""
    with pytest.raises(ConfigError) as excinfo:
        AppConfig.load()
    assert "INVENTREE_API_TOKEN not found in environment variables" in str(excinfo.value)
    # mock_load_dotenv.assert_not_called() # Removed: Mock IS called, but doesn't load vars

@mock.patch('inventree_order_calculator.config.load_dotenv') # Add this patch
@mock.patch.dict(os.environ, {}, clear=True)
def test_load_config_missing_both(mock_load_dotenv): # Add mock argument
    """Test ConfigError is raised if both variables are missing."""
    with pytest.raises(ConfigError) as excinfo:
        AppConfig.load()
    # Check the error message based on current config logic (checks URL first)
    assert "INVENTREE_URL not found" in str(excinfo.value)
    # mock_load_dotenv.assert_not_called() # Removed: Mock IS called, but doesn't load vars

@mock.patch('inventree_order_calculator.config.load_dotenv')
@mock.patch.dict(os.environ, {}, clear=True) # Ensure no env vars initially
def test_load_config_from_dotenv_file(mock_load_dotenv):
    """Test loading config purely from mocked .env file via load_dotenv."""
    # Simulate load_dotenv populating os.environ
    def side_effect(*args, **kwargs): # Accept arbitrary arguments
        os.environ["INVENTREE_URL"] = TEST_URL
        os.environ["INVENTREE_API_TOKEN"] = TEST_TOKEN
        os.environ["INVENTREE_INSTANCE_URL"] = TEST_INSTANCE_URL
    mock_load_dotenv.side_effect = side_effect

    config = AppConfig.load()
    assert config.inventree_url == TEST_URL
    assert config.inventree_api_token == TEST_TOKEN
    assert config.inventree_instance_url == TEST_INSTANCE_URL
    # Construct the expected path to .env in the root directory
    expected_dotenv_path = os.path.join(os.getcwd(), ".env")
    mock_load_dotenv.assert_called_once_with(dotenv_path=expected_dotenv_path, override=False) # Verify load_dotenv was called

@mock.patch('inventree_order_calculator.config.load_dotenv')
@mock.patch.dict(os.environ, {
    "INVENTREE_URL": "env_url",
    "INVENTREE_API_TOKEN": "env_token",
    "INVENTREE_INSTANCE_URL": "env_instance_url"
})
def test_load_config_env_overrides_dotenv(mock_load_dotenv):
    """Test that environment variables override .env values."""
    # Simulate load_dotenv trying to set different values
    def side_effect(*args, **kwargs): # Accept arbitrary arguments
        # These should be ignored because env vars already exist and override=False
        if "INVENTREE_URL" not in os.environ:
             os.environ["INVENTREE_URL"] = "dotenv_url"
        if "INVENTREE_API_TOKEN" not in os.environ:
             os.environ["INVENTREE_API_TOKEN"] = "dotenv_token"
        if "INVENTREE_INSTANCE_URL" not in os.environ:
            os.environ["INVENTREE_INSTANCE_URL"] = "dotenv_instance_url"
    mock_load_dotenv.side_effect = side_effect

    config = AppConfig.load()
    # Assert that the environment variable values took precedence
    assert config.inventree_url == "env_url"
    assert config.inventree_api_token == "env_token"
    assert config.inventree_instance_url == "env_instance_url"
    mock_load_dotenv.assert_called_once()

def test_app_config_attributes_all_present():
    """Test that AppConfig can be instantiated with all attributes."""
    config = AppConfig(
        inventree_url=TEST_URL,
        inventree_api_token=TEST_TOKEN,
        inventree_instance_url=TEST_INSTANCE_URL
    )
    assert config.inventree_url == TEST_URL
    assert config.inventree_api_token == TEST_TOKEN
    assert config.inventree_instance_url == TEST_INSTANCE_URL

def test_app_config_attributes_optional_missing():
    """Test that AppConfig can be instantiated with optional attributes missing."""
    config = AppConfig(inventree_url=TEST_URL, inventree_api_token=TEST_TOKEN)
    assert config.inventree_url == TEST_URL
    assert config.inventree_api_token == TEST_TOKEN
    assert config.inventree_instance_url is None

# TDD: Tests for configurable presets file path functionality
@mock.patch.dict(os.environ, {
    "INVENTREE_URL": TEST_URL,
    "INVENTREE_API_TOKEN": TEST_TOKEN,
    "PRESETS_FILE_PATH": "/app/data/presets.json"
})
def test_load_config_with_custom_presets_path():
    """Test that custom presets file path is loaded from environment."""
    config = AppConfig.load()
    assert config.presets_file_path == Path("/app/data/presets.json")

@mock.patch.dict(os.environ, {
    "INVENTREE_URL": TEST_URL,
    "INVENTREE_API_TOKEN": TEST_TOKEN
})
def test_load_config_with_default_presets_path():
    """Test that default presets file path is used when not specified."""
    config = AppConfig.load()
    assert config.presets_file_path == Path("presets.json")

@mock.patch.dict(os.environ, {
    "INVENTREE_URL": TEST_URL,
    "INVENTREE_API_TOKEN": TEST_TOKEN,
    "PRESETS_FILE_PATH": "custom/path/my_presets.json"
})
def test_load_config_with_relative_presets_path():
    """Test that relative presets file path works correctly."""
    config = AppConfig.load()
    assert config.presets_file_path == Path("custom/path/my_presets.json")

def test_app_config_presets_path_attribute():
    """Test that AppConfig can be instantiated with presets_file_path."""
    config = AppConfig(
        inventree_url=TEST_URL,
        inventree_api_token=TEST_TOKEN,
        presets_file_path=Path("/custom/presets.json")
    )
    assert config.presets_file_path == Path("/custom/presets.json")