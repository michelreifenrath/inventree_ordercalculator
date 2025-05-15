from pathlib import Path
from typing import List, Optional, Union, Dict # Added Dict
import json
import logging
import uuid # Added for generating monitoring list IDs

from pydantic import BaseModel, ValidationError, field_validator, Field

# Project-specific imports
from src.inventree_order_calculator.config import EmailConfig # Import EmailConfig using absolute path

# --- Pydantic Model Definitions ---
class PresetItem(BaseModel):
    """A single item within a calculation preset."""
    part_id: Union[int, str]  # Can be InvenTree part ID or name/IPN for lookup
    quantity: int

class Preset(BaseModel):
    """A calculation preset with a name and a list of items."""
    name: str = Field(..., min_length=1) # Must not be empty
    items: List[PresetItem]

# New models for Monitoring Lists
class MonitoringPartItem(BaseModel):
    """A part to be monitored within a monitoring list."""
    # Corresponds to PartInputLine in models.py for calculator input
    # For simplicity, directly using fields that calculator.PartInputLine would have
    name_or_ipn: str = Field(..., min_length=1) # Part name or IPN as known in InvenTree
    quantity: int = Field(..., gt=0) # Quantity required for this part in the assembly/list
    version: Optional[str] = None # Optional specific version of the part
    # Optional fields that might be part of PartInputLine:
    # part_id: Optional[int] = None # If resolved
    # allow_substitutes: bool = True
    # notes: Optional[str] = None

class MonitoringList(BaseModel):
    """Configuration for a single automated monitoring task."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1)
    parts: List[MonitoringPartItem] # List of parts to monitor
    active: bool = True
    interval_minutes: int = Field(..., gt=0) # Interval in minutes for interval-based scheduling
    cron_schedule: Optional[str] = None # Optional Cron-ausdruck
    recipients: List[str] = Field(default_factory=list) # List of email addresses
    notify_condition: str = "on_change" # "always" or "on_change" # Consider Enum here too
    email_config_name: Optional[str] = None # Name of the EmailConfig to use
    last_hash: Optional[str] = None # MD5 hash of last significant result for "on_change"
    misfire_grace_time: int = 3600 # Seconds, default 1 hour for APScheduler

    @field_validator('notify_condition')
    @classmethod
    def validate_notify_condition(cls, value: str) -> str:
        if value not in ["always", "on_change"]:
            raise ValueError("notify_condition must be 'always' or 'on_change'")
        return value

    @field_validator('recipients')
    @classmethod
    def validate_recipients_are_emails(cls, value: List[str]) -> List[str]:
        # Basic email format check, can be enhanced
        for email_str in value:
            if "@" not in email_str or "." not in email_str.split("@")[-1]:
                raise ValueError(f"Invalid email format: {email_str}")
        return value
    
    # Add cron schedule validation if APScheduler doesn't handle it sufficiently upstream
    # For now, assume basic string format and let APScheduler validate specifics.

class PresetsFile(BaseModel):
    """Structure of the JSON file storing all presets and monitoring lists."""
    presets: List[Preset] = Field(default_factory=list)
    monitoring_lists: List[MonitoringList] = Field(default_factory=list)
    email_configs: List[EmailConfig] = Field(default_factory=list) # Added EmailConfig list
    # filepath: Optional[Path] = None # No longer storing filepath inside the model data

# --- Global Variables & Logging ---
logger = logging.getLogger(__name__)
# Default path, can be overridden by passing config to PresetsManager instance
DEFAULT_PRESETS_FILE_PATH = Path("presets.json")


# --- PresetsManager Class ---
class PresetsManager:
    """
    Manages loading, saving, and modifying presets and monitoring lists
    from a JSON file.
    """
    def __init__(self, config_path: Optional[Path] = None):
        self.filepath = config_path if config_path is not None else DEFAULT_PRESETS_FILE_PATH
        self.data: PresetsFile = self._load_from_file()
        logger.info(f"PresetsManager initialized with file: {self.filepath.resolve()}")

    def _load_from_file(self) -> PresetsFile:
        """Loads data from the JSON file."""
        if not self.filepath.exists():
            logger.info(f"Presets file not found at {self.filepath}. Returning empty data structure.")
            return PresetsFile()

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                content = f.read()
                if not content.strip():
                    logger.info(f"Presets file at {self.filepath} is empty. Returning empty data structure.")
                    return PresetsFile()
                raw_data = json.loads(content)
            
            loaded_data = PresetsFile(**raw_data)
            logger.info(f"Successfully loaded data from {self.filepath}.")
            return loaded_data
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error loading from {self.filepath}: {e}. Returning empty data structure.")
            return PresetsFile()
        except ValidationError as e:
            logger.error(f"Data validation error loading from {self.filepath}: {e}. Returning empty data structure.")
            return PresetsFile()
        except Exception as e:
            logger.error(f"Unexpected error loading from {self.filepath}: {e}. Returning empty data structure.")
            return PresetsFile()

    def _save_to_file(self) -> bool:
        """Saves the current data to the JSON file."""
        try:
            if not self.filepath.parent.exists():
                self.filepath.parent.mkdir(parents=True, exist_ok=True)
            
            json_string = self.data.model_dump_json(indent=2)
            self.filepath.write_text(json_string, encoding="utf-8")
            logger.info(f"Data saved to {self.filepath}")
            return True
        except IOError as e:
            logger.error(f"IOError saving data to {self.filepath}: {e}")
            return False # Keep consistent return type, though monitoring_service might not check it directly
        except Exception as e:
            logger.error(f"Unexpected error saving data to {self.filepath}: {e}")
            return False

    # --- Regular Preset Management ---
    def get_presets(self) -> List[Preset]:
        return list(self.data.presets)

    def get_preset_by_name(self, name: str) -> Optional[Preset]:
        if not name.strip():
            logger.warning("Attempted to get preset with empty name.")
            return None
        for preset in self.data.presets:
            if preset.name == name:
                return preset
        logger.debug(f"Preset '{name}' not found.")
        return None

    def add_or_update_preset(self, preset_obj: Preset) -> bool:
        if not preset_obj.name.strip():
            logger.warning("Preset name cannot be empty. Operation skipped.")
            return False
        
        existing_idx = next((i for i, p in enumerate(self.data.presets) if p.name == preset_obj.name), -1)
        
        if existing_idx != -1:
            self.data.presets[existing_idx] = preset_obj
            logger.info(f"Updated existing preset: '{preset_obj.name}'.")
        else:
            self.data.presets.append(preset_obj)
            logger.info(f"Added new preset: '{preset_obj.name}'.")
        return self._save_to_file()

    def delete_preset_by_name(self, preset_name: str) -> bool:
        if not preset_name.strip():
            logger.warning("Attempted to delete preset with empty name. Operation skipped.")
            return False
        initial_count = len(self.data.presets)
        self.data.presets = [p for p in self.data.presets if p.name != preset_name]
        if len(self.data.presets) < initial_count:
            logger.info(f"Deleted preset: '{preset_name}'.")
            return self._save_to_file()
        else:
            logger.info(f"Preset '{preset_name}' not found for deletion.")
            return False # No change, no save needed, but indicate "failure" to delete

    def get_preset_names(self) -> List[str]:
        return [p.name for p in self.data.presets]

    # --- Monitoring List Management ---
    def get_monitoring_lists(self) -> List[MonitoringList]:
        """Returns a copy of all monitoring lists."""
        return list(self.data.monitoring_lists) # Return a copy

    def get_monitoring_list_by_id(self, list_id: str) -> Optional[MonitoringList]:
        """Retrieves a monitoring list by its ID."""
        if not list_id: return None
        for m_list in self.data.monitoring_lists:
            if m_list.id == list_id:
                return m_list
        logger.debug(f"Monitoring list with ID '{list_id}' not found.")
        return None

    def add_monitoring_list(self, monitoring_list_obj: MonitoringList) -> bool:
        """Adds a new monitoring list. Ensures ID is unique."""
        if not isinstance(monitoring_list_obj, MonitoringList):
            logger.error("Invalid object type passed to add_monitoring_list. Expected MonitoringList.")
            return False # Or raise TypeError

        if not monitoring_list_obj.id: # Should be handled by Pydantic default_factory
             monitoring_list_obj.id = str(uuid.uuid4())
             logger.warning(f"Monitoring list '{monitoring_list_obj.name}' was missing an ID, generated: {monitoring_list_obj.id}")

        if self.get_monitoring_list_by_id(monitoring_list_obj.id):
            logger.error(f"Monitoring list with ID '{monitoring_list_obj.id}' already exists. Cannot add duplicate.")
            # Consider raising a custom exception like DuplicateIdError
            return False 
        
        self.data.monitoring_lists.append(monitoring_list_obj)
        logger.info(f"Added new monitoring list: '{monitoring_list_obj.name}' (ID: {monitoring_list_obj.id}).")
        return self._save_to_file()

    def update_monitoring_list(self, list_id: str, updated_list_obj: MonitoringList) -> bool:
        """Updates an existing monitoring list identified by list_id."""
        if not isinstance(updated_list_obj, MonitoringList):
            logger.error("Invalid object type passed to update_monitoring_list. Expected MonitoringList.")
            return False

        if list_id != updated_list_obj.id:
            logger.error(f"Mismatch between list_id parameter ('{list_id}') and ID in updated_list_obj ('{updated_list_obj.id}'). Update aborted.")
            return False

        found_index = -1
        for i, m_list in enumerate(self.data.monitoring_lists):
            if m_list.id == list_id:
                found_index = i
                break
        
        if found_index == -1:
            logger.warning(f"Monitoring list with ID '{list_id}' not found for update.")
            return False
            
        self.data.monitoring_lists[found_index] = updated_list_obj
        logger.info(f"Updated monitoring list: '{updated_list_obj.name}' (ID: {list_id}).")
        return self._save_to_file()

    def delete_monitoring_list(self, list_id: str) -> bool:
        """Deletes a monitoring list by its ID."""
        if not list_id:
            logger.warning("Attempted to delete monitoring list with empty ID.")
            return False

        initial_count = len(self.data.monitoring_lists)
        self.data.monitoring_lists = [
            m_list for m_list in self.data.monitoring_lists if m_list.id != list_id
        ]

        if len(self.data.monitoring_lists) < initial_count:
            logger.info(f"Deleted monitoring list with ID: '{list_id}'.")
            return self._save_to_file()
        else:
            logger.warning(f"Monitoring list with ID '{list_id}' not found for deletion.")
            return False # No change, no save needed
# --- EmailConfig Management ---
    def get_email_configs(self) -> List[EmailConfig]:
        """Returns a copy of all email configurations."""
        return list(self.data.email_configs)

    def get_email_config_by_name(self, name: str) -> Optional[EmailConfig]:
        """Retrieves an email configuration by its name."""
        if not name or not name.strip():
            logger.warning("Attempted to get email config with empty name.")
            return None
        for ec in self.data.email_configs:
            if ec.name == name:
                return ec
        logger.debug(f"Email config '{name}' not found.")
        return None

    def add_or_update_email_config(self, email_config_obj: EmailConfig) -> bool:
        """Adds a new email configuration or updates an existing one by name."""
        if not isinstance(email_config_obj, EmailConfig):
            logger.error("Invalid object type passed to add_or_update_email_config. Expected EmailConfig.")
            return False
        
        if not email_config_obj.name or not email_config_obj.name.strip():
            logger.warning("EmailConfig name cannot be empty. Operation skipped.")
            return False

        existing_idx = next((i for i, ec in enumerate(self.data.email_configs) if ec.name == email_config_obj.name), -1)

        if existing_idx != -1:
            self.data.email_configs[existing_idx] = email_config_obj
            logger.info(f"Updated existing email config: '{email_config_obj.name}'.")
        else:
            self.data.email_configs.append(email_config_obj)
            logger.info(f"Added new email config: '{email_config_obj.name}'.")
        return self._save_to_file()

    def delete_email_config_by_name(self, name: str) -> bool:
        """Deletes an email configuration by its name."""
        if not name or not name.strip():
            logger.warning("Attempted to delete email config with empty name. Operation skipped.")
            return False
        
        initial_count = len(self.data.email_configs)
        self.data.email_configs = [ec for ec in self.data.email_configs if ec.name != name]

        if len(self.data.email_configs) < initial_count:
            logger.info(f"Deleted email config: '{name}'.")
            return self._save_to_file()
        else:
            logger.info(f"Email config '{name}' not found for deletion.")
            return False # No change, no save needed

    def get_email_config_names(self) -> List[str]:
        """Returns a list of all email configuration names."""
        return [ec.name for ec in self.data.email_configs if ec.name]

# --- Standalone Functions (Legacy or for direct use if PresetsManager instance is not preferred everywhere) ---
# These are now mostly superseded by methods in the PresetsManager class.
# Consider deprecating or refactoring CLI/UI to use PresetsManager instance.

def load_presets_from_file(filepath: Path = DEFAULT_PRESETS_FILE_PATH) -> PresetsFile:
    """Loads presets from a JSON file. (Standalone version)"""
    # This function is kept for potential direct use, but PresetsManager._load_from_file is preferred.
    manager = PresetsManager(config_path=filepath)
    return manager.data # Access the loaded data

def save_presets_to_file(presets_data: PresetsFile, filepath: Path = DEFAULT_PRESETS_FILE_PATH) -> bool:
    """Saves the given PresetsFile data to a JSON file. (Standalone version)"""
    # This function is kept for potential direct use, but PresetsManager._save_to_file is preferred.
    manager = PresetsManager(config_path=filepath)
    manager.data = presets_data # Overwrite its internal data
    return manager._save_to_file()


if __name__ == '__main__':
    # Example Usage and Basic Test for PresetsManager class
    logging.basicConfig(level=logging.DEBUG) # More verbose for __main__
    
    # Use a temporary file for testing to not overwrite actual presets.json
    test_file_path = Path("test_presets_manager_data.json")
    if test_file_path.exists():
        test_file_path.unlink()

    manager = PresetsManager(config_path=test_file_path)
    print(f"Using presets file: {manager.filepath.resolve()}")

    # 1. Initial state
    print(f"Initial presets: {manager.get_presets()}")
    print(f"Initial monitoring lists: {manager.get_monitoring_lists()}")

    # 2. Add a regular preset
    preset1_items = [PresetItem(part_id=101, quantity=10), PresetItem(part_id="SKU-002", quantity=5)]
    preset1 = Preset(name="My First Calculation Preset", items=preset1_items)
    if manager.add_or_update_preset(preset1):
        print(f"Added preset: {preset1.name}")
    
    # 3. Add a monitoring list
    monitor_parts1 = [MonitoringPartItem(name_or_ipn="Resistor 10k", quantity=100, version="R01")]
    monitor_list1 = MonitoringList(
        name="Critical Resistors Check",
        parts=monitor_parts1,
        cron_schedule="0 9 * * 1-5", # At 09:00 on Monday to Friday
        recipients=["test@example.com", "admin@example.com"],
        notify_condition="on_change"
    )
    if manager.add_monitoring_list(monitor_list1):
         print(f"Added monitoring list: {monitor_list1.name} (ID: {monitor_list1.id})")

    monitor_parts2 = [MonitoringPartItem(name_or_ipn="Capacitor 10uF", quantity=50)]
    monitor_list2 = MonitoringList(
        name="Capacitor Stock Alert",
        parts=monitor_parts2,
        cron_schedule="0 0 * * *", # Daily at midnight
        recipients=["inventory@example.com"],
        notify_condition="always",
        active=False # Start as inactive
    )
    if manager.add_monitoring_list(monitor_list2):
        print(f"Added monitoring list: {monitor_list2.name} (ID: {monitor_list2.id})")

    print(f"Current monitoring lists: {len(manager.get_monitoring_lists())}")
    retrieved_ml1 = manager.get_monitoring_list_by_id(monitor_list1.id)
    print(f"Retrieved ML1 by ID: {retrieved_ml1.name if retrieved_ml1 else 'Not found'}")

    # 4. Update a monitoring list
    if retrieved_ml1:
        updated_ml1_data = retrieved_ml1.model_copy(update={"active": False, "recipients": ["new_admin@example.com"]})
        if manager.update_monitoring_list(retrieved_ml1.id, updated_ml1_data):
            print(f"Updated monitoring list: {retrieved_ml1.name}")
    
    re_retrieved_ml1 = manager.get_monitoring_list_by_id(monitor_list1.id)
    if re_retrieved_ml1:
        print(f"ML1 active status after update: {re_retrieved_ml1.active}")
        print(f"ML1 recipients after update: {re_retrieved_ml1.recipients}")

    # 5. Delete a monitoring list
    if manager.delete_monitoring_list(monitor_list2.id):
        print(f"Deleted monitoring list: {monitor_list2.name}")
    
    print(f"Monitoring lists after deletion: {len(manager.get_monitoring_lists())}")

    # Clean up test file
    if test_file_path.exists():
        test_file_path.unlink()
        print(f"Cleaned up test file: {test_file_path}")