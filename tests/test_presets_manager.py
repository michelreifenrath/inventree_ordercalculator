import pytest
import json
from pathlib import Path
from unittest.mock import patch, mock_open
from pydantic import ValidationError # Added import

from src.inventree_order_calculator.presets_manager import (
    PresetsManager,
    MonitoringPartItem,
    MonitoringList,
    # EmailConfig and PresetsFile are used internally or via PresetsManager
)
from src.inventree_order_calculator.config import EmailConfig # Corrected import for EmailConfig
from src.inventree_order_calculator.presets_manager import PresetsFile # For direct comparison in some tests

# Obsolete tests for old preset system (Preset, PresetItem, PresetsFile)
# and standalone functions have been removed.
# The PresetsManager now handles MonitoringList and EmailConfig.
# Tests for the new PresetsManager start further down.

# --- Tests for MonitoringList and MonitoringPartItem Pydantic Models ---

def test_monitoring_part_item_valid():
    """Test valid MonitoringPartItem creation."""
    item = MonitoringPartItem(name_or_ipn="Resistor10K", quantity=100, version="R02")
    assert item.name_or_ipn == "Resistor10K"
    assert item.quantity == 100
    assert item.version == "R02"

def test_monitoring_part_item_invalid_quantity():
    """Test MonitoringPartItem raises ValueError for quantity <= 0."""
    with pytest.raises(ValidationError):
        MonitoringPartItem(name_or_ipn="Capacitor", quantity=0)
    with pytest.raises(ValidationError):
        MonitoringPartItem(name_or_ipn="Inductor", quantity=-5)

def test_monitoring_part_item_missing_name():
    """Test MonitoringPartItem raises ValueError for missing name_or_ipn."""
    with pytest.raises(ValidationError):
        MonitoringPartItem(quantity=10) # name_or_ipn is required

def test_monitoring_list_valid_basic():
    """Test valid MonitoringList creation with minimal required fields."""
    parts = [MonitoringPartItem(name_or_ipn="PART-A", quantity=10)]
    ml = MonitoringList(
        name="Test Monitor",
        parts=parts,
        interval_minutes=60, # Added required field
        cron_schedule="0 * * * *", # Every hour
        recipients=["test@example.com"]
    )
    assert ml.name == "Test Monitor"
    assert ml.parts == parts
    assert ml.cron_schedule == "0 * * * *"
    assert ml.recipients == ["test@example.com"]
    assert ml.active is True # Default
    assert ml.notify_condition == "on_change" # Default
    assert ml.last_hash is None # Default
    assert ml.misfire_grace_time == 3600 # Default
    assert isinstance(ml.id, str) # Default factory for id

def test_monitoring_list_valid_all_fields():
    """Test valid MonitoringList creation with all fields specified."""
    parts = [MonitoringPartItem(name_or_ipn="PART-B", quantity=5)]
    ml = MonitoringList(
        id="custom_id_123",
        name="Full Monitor Task",
        parts=parts,
        active=False,
        interval_minutes=30, # Added missing required field
        cron_schedule="*/5 * * * *", # Every 5 minutes
        recipients=["notify1@example.com", "notify2@example.org"],
        notify_condition="always",
        last_hash="previous_hash_abc",
        misfire_grace_time=600
    )
    assert ml.id == "custom_id_123"
    assert ml.active is False
    assert ml.notify_condition == "always"
    assert ml.last_hash == "previous_hash_abc"
    assert ml.misfire_grace_time == 600

def test_monitoring_list_invalid_notify_condition():
    """Test MonitoringList raises ValueError for invalid notify_condition."""
    with pytest.raises(ValidationError) as excinfo:
        MonitoringList(
            name="Notify Test",
            parts=[MonitoringPartItem(name_or_ipn="P", quantity=1)],
            cron_schedule="* * * * *",
            notify_condition="sometimes" # Invalid
        )
    assert "notify_condition must be 'always' or 'on_change'" in str(excinfo.value)

def test_monitoring_list_invalid_recipient_email():
    """Test MonitoringList raises ValueError for invalid email in recipients."""
    with pytest.raises(ValidationError) as excinfo:
        MonitoringList(
            name="Email Test",
            parts=[MonitoringPartItem(name_or_ipn="P", quantity=1)],
            cron_schedule="* * * * *",
            recipients=["valid@example.com", "invalid-email"]
        )
    assert "Invalid email format: invalid-email" in str(excinfo.value)

def test_monitoring_list_empty_recipients_valid():
    """Test MonitoringList is valid with an empty recipients list (uses default_factory)."""
    ml = MonitoringList(
        name="No Recipients",
        parts=[MonitoringPartItem(name_or_ipn="P", quantity=1)],
        interval_minutes=60, # Added required field
        cron_schedule="* * * * *"
    )
    assert ml.recipients == []

def test_monitoring_list_missing_required_fields():
    """Test MonitoringList raises ValidationError for missing required fields."""
    with pytest.raises(ValidationError): # Missing name
        MonitoringList(
            parts=[MonitoringPartItem(name_or_ipn="P", quantity=1)],
            interval_minutes=60, # Added required field
            cron_schedule="* * * * *"
        )
    with pytest.raises(ValidationError): # Missing parts
        MonitoringList(name="No Parts", interval_minutes=60, cron_schedule="* * * * *")
    with pytest.raises(ValidationError): # Missing interval_minutes (and cron_schedule)
        MonitoringList(name="No Cron Or Interval", parts=[MonitoringPartItem(name_or_ipn="P", quantity=1)])

# --- Tests for PresetsManager with MonitoringList CRUD operations ---
# We need to import the PresetsManager class itself for these tests
from src.inventree_order_calculator.presets_manager import PresetsManager

@pytest.fixture
def temp_presets_file(tmp_path):
    """Provides a temporary file path for PresetsManager tests."""
    return tmp_path / "test_manager_presets.json"

@pytest.fixture
def manager_instance(temp_presets_file):
    """Provides a PresetsManager instance with a temporary file."""
    # Ensure the file is clean before each test that uses this manager
    if temp_presets_file.exists():
        temp_presets_file.unlink()
    return PresetsManager(config_path=temp_presets_file)

def test_pm_add_monitoring_list_success(manager_instance):
    """Test adding a new monitoring list successfully."""
    ml_data = MonitoringList(
        name="Monitor Alpha",
        parts=[MonitoringPartItem(name_or_ipn="ALPHA01", quantity=10)],
        interval_minutes=60, # Added required field
        cron_schedule="0 0 * * 0", # Weekly on Sunday
        recipients=["alpha_user@example.com"]
    )
    with patch.object(manager_instance, '_save_to_file', return_value=True) as mock_save:
        success = manager_instance.add_monitoring_list(ml_data)
    
    assert success is True
    mock_save.assert_called_once()
    assert len(manager_instance.data.monitoring_lists) == 1
    assert manager_instance.data.monitoring_lists[0].name == "Monitor Alpha"
    assert manager_instance.data.monitoring_lists[0].id == ml_data.id # ID should be preserved

def test_pm_add_monitoring_list_duplicate_id(manager_instance):
    """Test adding a monitoring list with a duplicate ID fails."""
    ml1 = MonitoringList(id="dup_id_1", name="First", parts=[], interval_minutes=60, cron_schedule="* * * * *")
    ml2 = MonitoringList(id="dup_id_1", name="Second", parts=[], interval_minutes=30, cron_schedule="0 * * * *") # Same ID
    
    with patch.object(manager_instance, '_save_to_file', return_value=True) as mock_save_initial:
        assert manager_instance.add_monitoring_list(ml1) is True
    mock_save_initial.assert_called_once()
    
    with patch.object(manager_instance, '_save_to_file') as mock_save_duplicate:
        success_dup = manager_instance.add_monitoring_list(ml2) # Attempt to add duplicate
    
    assert success_dup is False
    mock_save_duplicate.assert_not_called() # Save should not be called on failure
    assert len(manager_instance.data.monitoring_lists) == 1 # Only the first one should be there

def test_pm_get_monitoring_lists(manager_instance):
    """Test retrieving all monitoring lists."""
    ml1 = MonitoringList(name="ML1", parts=[], interval_minutes=60, cron_schedule="* * * * *")
    ml2 = MonitoringList(name="ML2", parts=[], interval_minutes=30, cron_schedule="0 * * * *")
    manager_instance.data.monitoring_lists = [ml1, ml2] # Directly set for test

    lists = manager_instance.get_monitoring_lists()
    assert len(lists) == 2
    assert lists[0].name == "ML1"
    assert lists[1].name == "ML2"
    # Ensure it returns a copy
    lists.append(MonitoringList(name="ML3", parts=[], interval_minutes=10, cron_schedule="1 * * * *"))
    assert len(manager_instance.data.monitoring_lists) == 2


def test_pm_get_monitoring_list_by_id(manager_instance):
    """Test retrieving a specific monitoring list by ID."""
    ml1 = MonitoringList(id="find_me_id", name="Findable", parts=[], interval_minutes=60, cron_schedule="* * * * *")
    manager_instance.data.monitoring_lists = [ml1]

    found = manager_instance.get_monitoring_list_by_id("find_me_id")
    assert found is not None
    assert found.name == "Findable"

    not_found = manager_instance.get_monitoring_list_by_id("id_does_not_exist")
    assert not_found is None

def test_pm_update_monitoring_list_success(manager_instance):
    """Test updating an existing monitoring list."""
    original_id = "update_id_1"
    ml_orig = MonitoringList(id=original_id, name="Original Name", parts=[], interval_minutes=60, cron_schedule="* * * * *")
    manager_instance.data.monitoring_lists = [ml_orig]

    ml_updated_data = MonitoringList(id=original_id, name="Updated Name", parts=[], interval_minutes=30, cron_schedule="0 0 * * *", active=False)
    
    with patch.object(manager_instance, '_save_to_file', return_value=True) as mock_save:
        success = manager_instance.update_monitoring_list(original_id, ml_updated_data)
    
    assert success is True
    mock_save.assert_called_once()
    assert len(manager_instance.data.monitoring_lists) == 1
    updated_in_manager = manager_instance.data.monitoring_lists[0]
    assert updated_in_manager.name == "Updated Name"
    assert updated_in_manager.active is False

def test_pm_update_monitoring_list_id_mismatch(manager_instance):
    """Test update fails if list_id param and object's ID mismatch."""
    ml = MonitoringList(id="id1", name="Name1", parts=[], interval_minutes=60, cron_schedule="* * * * *")
    manager_instance.data.monitoring_lists = [ml]
    ml_wrong_id_in_obj = MonitoringList(id="id2_wrong", name="Name2", parts=[], interval_minutes=30, cron_schedule="0 * * * *")

    with patch.object(manager_instance, '_save_to_file') as mock_save:
        success = manager_instance.update_monitoring_list("id1", ml_wrong_id_in_obj)
    
    assert success is False
    mock_save.assert_not_called()

def test_pm_update_monitoring_list_not_found(manager_instance):
    """Test update fails if list_id to update is not found."""
    ml_update_data = MonitoringList(id="non_existent", name="NonExistent", parts=[], interval_minutes=60, cron_schedule="* * * * *")
    with patch.object(manager_instance, '_save_to_file') as mock_save:
        success = manager_instance.update_monitoring_list("non_existent", ml_update_data)
    
    assert success is False
    mock_save.assert_not_called()

def test_pm_delete_monitoring_list_success(manager_instance):
    """Test deleting an existing monitoring list."""
    ml_to_delete = MonitoringList(id="delete_me", name="ToDelete", parts=[], interval_minutes=60, cron_schedule="* * * * *")
    ml_to_keep = MonitoringList(id="keep_me", name="ToKeep", parts=[], interval_minutes=30, cron_schedule="0 * * * *")
    manager_instance.data.monitoring_lists = [ml_to_delete, ml_to_keep]

    with patch.object(manager_instance, '_save_to_file', return_value=True) as mock_save:
        success = manager_instance.delete_monitoring_list("delete_me")
        
    assert success is True
    mock_save.assert_called_once()
    assert len(manager_instance.data.monitoring_lists) == 1
    assert manager_instance.data.monitoring_lists[0].id == "keep_me"

def test_pm_delete_monitoring_list_not_found(manager_instance):
    """Test deleting a non-existent monitoring list."""
    ml = MonitoringList(id="id1", name="Name1", parts=[], interval_minutes=60, cron_schedule="* * * * *")
    manager_instance.data.monitoring_lists = [ml]
    
    with patch.object(manager_instance, '_save_to_file') as mock_save:
        success = manager_instance.delete_monitoring_list("non_existent_delete_id")
    assert success is False # Ensure it's False as per previous similar tests
    mock_save.assert_not_called()


# --- Test PresetsManager MonitoringList CRUD with File Interaction ---

def test_pm_add_monitoring_list_persists(manager_instance, temp_presets_file):
    """Test that adding a monitoring list correctly persists it to the file."""
    ml_data = MonitoringList(
        name="Persistent Monitor Task",
        parts=[MonitoringPartItem(name_or_ipn="MONITOR_PART_001", quantity=5)],
        interval_minutes=30, # Required field
        recipients=["persist@example.com"],
        email_config_name="persist_email_conf"
    )
    
    assert manager_instance.add_monitoring_list(ml_data) is True
    
    # Verify by creating a new manager instance that loads from the same file
    new_manager = PresetsManager(config_path=temp_presets_file)
    loaded_lists = new_manager.get_monitoring_lists()
    
    assert len(loaded_lists) == 1
    persisted_ml = loaded_lists[0]
    assert persisted_ml.name == "Persistent Monitor Task"
    assert persisted_ml.id == ml_data.id # ID is auto-generated by model if not provided
    assert len(persisted_ml.parts) == 1
    assert persisted_ml.parts[0].name_or_ipn == "MONITOR_PART_001"
    assert persisted_ml.recipients == ["persist@example.com"]
    assert persisted_ml.interval_minutes == 30
    assert persisted_ml.email_config_name == "persist_email_conf"

def test_pm_update_monitoring_list_persists(manager_instance, temp_presets_file):
    """Test that updating a monitoring list correctly persists changes to the file."""
    ml_initial_id = "update_persist_id"
    ml_initial = MonitoringList(
        id=ml_initial_id,
        name="Initial Update Task",
        parts=[MonitoringPartItem(name_or_ipn="PART_U1", quantity=1)],
        interval_minutes=60,
        active=True
    )
    manager_instance.add_monitoring_list(ml_initial)

    # Create updated data
    ml_updated_payload = ml_initial.model_copy(update={
        "name": "Updated Task Name Persisted",
        "active": False,
        "recipients": ["updated_persist@example.com"],
        "interval_minutes": 120
    })

    assert manager_instance.update_monitoring_list(ml_initial_id, ml_updated_payload) is True

    # Verify by loading with a new manager
    new_manager = PresetsManager(config_path=temp_presets_file)
    loaded_ml = new_manager.get_monitoring_list_by_id(ml_initial_id)
    
    assert loaded_ml is not None
    assert loaded_ml.name == "Updated Task Name Persisted"
    assert loaded_ml.active is False
    assert loaded_ml.recipients == ["updated_persist@example.com"]
    assert loaded_ml.interval_minutes == 120

def test_pm_delete_monitoring_list_persists(manager_instance, temp_presets_file):
    """Test that deleting a monitoring list correctly removes it from the file."""
    ml1_id = "delete_persist_1"
    ml1 = MonitoringList(id=ml1_id, name="Delete Me Persist", parts=[], interval_minutes=10)
    ml2_id = "delete_persist_2"
    ml2 = MonitoringList(id=ml2_id, name="Keep Me Persist", parts=[], interval_minutes=20)
    
    manager_instance.add_monitoring_list(ml1)
    manager_instance.add_monitoring_list(ml2)

    assert manager_instance.delete_monitoring_list(ml1_id) is True

    # Verify by loading
    new_manager = PresetsManager(config_path=temp_presets_file)
    assert new_manager.get_monitoring_list_by_id(ml1_id) is None
    assert new_manager.get_monitoring_list_by_id(ml2_id) is not None
    assert len(new_manager.get_monitoring_lists()) == 1
    assert new_manager.get_monitoring_lists()[0].id == ml2_id
    
# --- Tests for PresetsManager EmailConfig CRUD operations ---

def test_pm_add_email_config_success(manager_instance):
    """Test adding a new email config successfully."""
    ec_data = EmailConfig(name="Default SMTP", smtp_server="smtp.example.com", smtp_port=587, username="user", password="password")
    with patch.object(manager_instance, '_save_to_file', return_value=True) as mock_save:
        success = manager_instance.add_or_update_email_config(ec_data)
    
    assert success is True
    mock_save.assert_called_once()
    assert len(manager_instance.data.email_configs) == 1
    assert manager_instance.data.email_configs[0].name == "Default SMTP"

def test_pm_add_email_config_duplicate_name_updates(manager_instance):
    """Test adding an email config with a duplicate name updates the existing one."""
    ec1 = EmailConfig(name="Default SMTP", smtp_server="smtp.example.com", smtp_port=587)
    ec2 = EmailConfig(name="Default SMTP", smtp_server="mail.example.org", smtp_port=465, use_tls=False) # Same name, different host
    
    with patch.object(manager_instance, '_save_to_file', return_value=True) as mock_save1:
        assert manager_instance.add_or_update_email_config(ec1) is True
    mock_save1.assert_called_once()
    
    with patch.object(manager_instance, '_save_to_file', return_value=True) as mock_save2:
        assert manager_instance.add_or_update_email_config(ec2) is True # Should update
    mock_save2.assert_called_once()
    
    assert len(manager_instance.data.email_configs) == 1
    assert manager_instance.data.email_configs[0].smtp_server == "mail.example.org"
    assert manager_instance.data.email_configs[0].smtp_port == 465

def test_pm_get_email_configs(manager_instance):
    """Test retrieving all email configs."""
    ec1 = EmailConfig(name="EC1", smtp_server="h1", smtp_port=1)
    ec2 = EmailConfig(name="EC2", smtp_server="h2", smtp_port=2)
    manager_instance.data.email_configs = [ec1, ec2]

    configs = manager_instance.get_email_configs()
    assert len(configs) == 2
    assert configs[0].name == "EC1"
    assert configs[1].name == "EC2"
    # Ensure it returns a copy
    configs.append(EmailConfig(name="EC3", smtp_server="h3", smtp_port=3))
    assert len(manager_instance.data.email_configs) == 2

def test_pm_get_email_config_by_name_success(manager_instance):
    """Test retrieving an existing email config by name."""
    ec1 = EmailConfig(name="find_me_ec", smtp_server="h1", smtp_port=1)
    manager_instance.data.email_configs = [ec1]

    found = manager_instance.get_email_config_by_name("find_me_ec")
    assert found is not None
    assert found.name == "find_me_ec"

def test_pm_get_email_config_by_name_not_found(manager_instance):
    """Test retrieving a non-existent email config returns None."""
    assert manager_instance.get_email_config_by_name("ec_does_not_exist") is None

def test_pm_update_email_config_success_renaming(manager_instance):
    """Test updating an existing email config, including renaming via payload."""
    original_name = "OriginalEC"
    ec_orig = EmailConfig(name=original_name, smtp_server="original.host", smtp_port=123)
    manager_instance.data.email_configs = [ec_orig]

    # The add_or_update_email_config function updates based on the name *in the payload*.
    # So, to "update" 'OriginalEC', we pass new data with the same name if we don't want to rename,
    # or a new name in the payload if we intend to rename.
    # The current PresetsManager.add_or_update_email_config replaces based on the name in the new config.
    # Let's test updating an existing one by providing the same name with different fields.
    ec_updated_data_same_name = EmailConfig(name=original_name, smtp_server="updated.host", smtp_port=456, use_tls=True)
    
    with patch.object(manager_instance, '_save_to_file', return_value=True) as mock_save:
        success = manager_instance.add_or_update_email_config(ec_updated_data_same_name)
    
    assert success is True
    mock_save.assert_called_once()
    assert len(manager_instance.data.email_configs) == 1
    updated_in_manager = manager_instance.data.email_configs[0]
    assert updated_in_manager.name == original_name # Name remains the same
    assert updated_in_manager.smtp_server == "updated.host"
    assert updated_in_manager.smtp_port == 456
    assert updated_in_manager.use_tls is True

    # Test renaming: add_or_update_email_config with a new name effectively adds a new one
    # if the old name is different. If we want to "rename" `OriginalEC` to `NewECName`,
    # we'd add `NewECName` and delete `OriginalEC`.
    # The current `add_or_update_email_config` will simply add `NewECName` if it's different.
    # If the intention is to replace "OriginalEC" with "NewECName" data,
    # the manager's `update_email_config(old_name, new_config_data)` would be more appropriate.
    # Since we only have `add_or_update_email_config`, it finds by `email_config_data.name`.
    # So, "updating" means the name in the payload matches an existing one.

def test_pm_update_email_config_actually_adds_if_name_different(manager_instance):
    """Test that add_or_update_email_config adds a new config if the name in payload is different."""
    ec_orig = EmailConfig(name="OriginalEC", smtp_server="original.host", smtp_port=123)
    manager_instance.add_or_update_email_config(ec_orig) # Saved once

    ec_new_name_data = EmailConfig(name="NewNameEC", smtp_server="new.host", smtp_port=789)
    
    with patch.object(manager_instance, '_save_to_file', return_value=True) as mock_save_new:
        success = manager_instance.add_or_update_email_config(ec_new_name_data)

    assert success is True
    mock_save_new.assert_called_once() # Saved again
    assert len(manager_instance.data.email_configs) == 2
    assert manager_instance.get_email_config_by_name("OriginalEC") is not None
    assert manager_instance.get_email_config_by_name("NewNameEC") is not None


def test_pm_delete_email_config_success(manager_instance):
    """Test deleting an existing email config."""
    ec_to_delete = EmailConfig(name="delete_ec_me", smtp_server="h", smtp_port=1)
    ec_to_keep = EmailConfig(name="keep_ec_me", smtp_server="h2", smtp_port=2)
    manager_instance.data.email_configs = [ec_to_delete, ec_to_keep]

    with patch.object(manager_instance, '_save_to_file', return_value=True) as mock_save:
        success = manager_instance.delete_email_config_by_name("delete_ec_me")
        
    assert success is True
    mock_save.assert_called_once()
    assert len(manager_instance.data.email_configs) == 1
    assert manager_instance.data.email_configs[0].name == "keep_ec_me"

def test_pm_delete_email_config_not_found(manager_instance):
    """Test deleting a non-existent email config."""
    ec = EmailConfig(name="ec1", smtp_server="h", smtp_port=1)
    manager_instance.data.email_configs = [ec]
    
    with patch.object(manager_instance, '_save_to_file') as mock_save:
        success = manager_instance.delete_email_config_by_name("non_existent_ec_id")
    assert success is False
    mock_save.assert_not_called()

def test_pm_get_email_config_names(manager_instance):
    """Test retrieving all email config names."""
    ec1 = EmailConfig(name="SMTP Main", smtp_server="h1", smtp_port=1)
    ec2 = EmailConfig(name="Backup Mail", smtp_server="h2", smtp_port=2)
    manager_instance.data.email_configs = [ec1, ec2]

    names = manager_instance.get_email_config_names()
    assert len(names) == 2
    assert "SMTP Main" in names
    assert "Backup Mail" in names

# --- Test PresetsManager EmailConfig CRUD with File Interaction ---

def test_pm_add_email_config_persists(manager_instance, temp_presets_file):
    """Test that adding an email config correctly persists it to the file."""
    ec_data = EmailConfig(name="Persistent Email", smtp_server="persist.smtp.com", smtp_port=555, smtp_user="persist_user")
    
    assert manager_instance.add_or_update_email_config(ec_data) is True
    
    new_manager = PresetsManager(config_path=temp_presets_file)
    loaded_ec = new_manager.get_email_config_by_name("Persistent Email")
    
    assert loaded_ec is not None
    assert loaded_ec.smtp_server == "persist.smtp.com"
    assert loaded_ec.smtp_port == 555
    assert loaded_ec.smtp_user == "persist_user"

def test_pm_update_email_config_persists(manager_instance, temp_presets_file):
    """Test that updating an email config correctly persists changes."""
    ec_initial_name = "UpdatePersistEC"
    ec_initial = EmailConfig(name=ec_initial_name, smtp_server="initial.host", smtp_port=111)
    manager_instance.add_or_update_email_config(ec_initial)

    ec_updated_payload = EmailConfig(name=ec_initial_name, smtp_server="updated.persist.host", smtp_port=222, use_tls=True)
    
    assert manager_instance.add_or_update_email_config(ec_updated_payload) is True

    new_manager = PresetsManager(config_path=temp_presets_file)
    loaded_ec = new_manager.get_email_config_by_name(ec_initial_name)
    
    assert loaded_ec is not None
    assert loaded_ec.smtp_server == "updated.persist.host"
    assert loaded_ec.smtp_port == 222
    assert loaded_ec.use_tls is True

def test_pm_delete_email_config_persists(manager_instance, temp_presets_file):
    """Test that deleting an email config correctly removes it from the file."""
    ec1_name = "delete_persist_ec1"
    ec1 = EmailConfig(name=ec1_name, smtp_server="h1", smtp_port=1)
    ec2_name = "keep_persist_ec2"
    ec2 = EmailConfig(name=ec2_name, smtp_server="h2", smtp_port=2)
    
    manager_instance.add_or_update_email_config(ec1)
    manager_instance.add_or_update_email_config(ec2)

    assert manager_instance.delete_email_config_by_name(ec1_name) is True

    new_manager = PresetsManager(config_path=temp_presets_file)
    assert new_manager.get_email_config_by_name(ec1_name) is None
    assert new_manager.get_email_config_by_name(ec2_name) is not None
    assert len(new_manager.get_email_configs()) == 1
    assert new_manager.get_email_configs()[0].name == ec2_name