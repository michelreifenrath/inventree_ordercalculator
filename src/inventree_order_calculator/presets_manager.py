from pathlib import Path
from typing import List, Optional, Union
import json
import logging
import shutil

from pydantic import BaseModel, ValidationError

# Pydantic Model Definitions (as per architecture/presets_feature_architecture.md and pseudocode)
class PresetItem(BaseModel):
    part_id: Union[int, str]  # Can be int or string if part IDs are sometimes non-numeric
    quantity: int

class Preset(BaseModel):
    name: str
    items: List[PresetItem]

class PresetsFile(BaseModel):
    presets: List[Preset] = []
    filepath: Optional[Path] = None

# Define PRESETS_FILE_PATH (can be overridden in streamlit_app.py if needed)
PRESETS_FILE_PATH = Path("presets.json")

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_presets_from_file(filepath: Path = PRESETS_FILE_PATH) -> PresetsFile:
    """
    Loads presets from a JSON file.
    If the file doesn't exist, is empty, or contains invalid JSON/data,
    it returns an empty PresetsFile object and logs an error.
    """
    if not filepath.exists():
        logging.info(f"Presets file not found at {filepath}. Returning empty presets.")
        return PresetsFile(presets=[], filepath=filepath)

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            # Handle empty file case
            content = f.read()
            if not content.strip():
                logging.info(f"Presets file at {filepath} is empty. Returning empty presets.")
                return PresetsFile(presets=[], filepath=filepath)
            
            raw_data = json.loads(content) # Use content instead of f after reading
        
        # Remove 'filepath' from raw_data if it exists to avoid conflict
        # as we are explicitly setting it.
        raw_data.pop('filepath', None)
        loaded_presets_file = PresetsFile(**raw_data, filepath=filepath)
        logging.info(f"Successfully loaded presets from {filepath}.")
        return loaded_presets_file
    except json.JSONDecodeError as e:
        logging.error(f"JSON decode error loading presets from {filepath}: {e}. Returning empty presets.")
        return PresetsFile(presets=[], filepath=filepath)
    except ValidationError as e: # Pydantic's validation error
        logging.error(f"Data validation error loading presets from {filepath}: {e}. Returning empty presets.")
        return PresetsFile(presets=[], filepath=filepath)
    except Exception as e: # Catch any other unexpected errors
        logging.error(f"Unexpected error loading presets from {filepath}: {e}. Returning empty presets.")
        return PresetsFile(presets=[], filepath=filepath)

def save_presets_to_file(presets_data: PresetsFile, filepath: Path = PRESETS_FILE_PATH) -> bool:
    """
    Saves the given PresetsFile data to a JSON file.
    Returns True on success, False on failure.
    """
    try:
        # Ensure parent directory exists
        if not filepath.parent.exists():
            filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Assuming PresetsFile is a Pydantic model
        json_string = presets_data.model_dump_json(indent=2)
        filepath.write_text(json_string, encoding="utf-8")
        logging.info(f"Presets saved to {filepath}")
        return True
    except IOError as e:
        logging.error(f"IOError saving presets to {filepath}: {e}")
        raise  # Re-raise the IOError for the test to catch
    except Exception as e:
        logging.error(f"Unexpected error saving presets to {filepath}: {e}")
        return False

def add_or_update_preset(presets_data: PresetsFile, new_preset: Preset) -> PresetsFile:
    """
    Adds a new preset to the PresetsFile or updates an existing one if the name matches.
    Returns the updated PresetsFile object.
    """
    if not new_preset.name.strip():
        logging.warning("Attempted to add/update preset with empty name. Operation skipped.")
        return presets_data # Or raise ValueError("Preset name cannot be empty")

    existing_preset_index = -1
    for i, preset in enumerate(presets_data.presets):
        if preset.name == new_preset.name:
            existing_preset_index = i
            break
    
    updated_presets_list = list(presets_data.presets) # Create a mutable copy

    if existing_preset_index != -1:
        updated_presets_list[existing_preset_index] = new_preset # Update
        logging.info(f"Updated existing preset: '{new_preset.name}'.")
    else:
        updated_presets_list.append(new_preset) # Add
        logging.info(f"Added new preset: '{new_preset.name}'.")
    
    return PresetsFile(presets=updated_presets_list, filepath=presets_data.filepath)

def delete_preset_by_name(presets_data: PresetsFile, preset_name: str) -> PresetsFile:
    """
    Deletes a preset by its name from the PresetsFile.
    Returns the updated PresetsFile object. If preset_name not found, returns original data.
    """
    if not preset_name.strip():
        logging.warning("Attempted to delete preset with empty name. Operation skipped.")
        return presets_data

    initial_count = len(presets_data.presets)
    updated_presets_list = [
        preset for preset in presets_data.presets if preset.name != preset_name
    ]
    
    if len(updated_presets_list) < initial_count:
        logging.info(f"Deleted preset: '{preset_name}'.")
    else:
        logging.info(f"Preset '{preset_name}' not found for deletion.")
        
    return PresetsFile(presets=updated_presets_list, filepath=presets_data.filepath)

def get_preset_names(presets_data: PresetsFile) -> List[str]:
    """
    Returns a list of names of all presets in the PresetsFile.
    """
    if not presets_data or not presets_data.presets:
        return []
    return [preset.name for preset in presets_data.presets]

def get_preset_by_name(presets_data: PresetsFile, name: str) -> Optional[Preset]:
    """
    Retrieves a preset by its name from the PresetsFile.
    Returns the Preset object if found, otherwise None.
    """
    if not name.strip():
        logging.warning("Attempted to get preset with empty name.")
        return None
        
    for preset in presets_data.presets:
        if preset.name == name:
            return preset
    logging.info(f"Preset '{name}' not found.")
    return None

def get_presets_file_path(custom_path: Optional[Path] = None, config=None) -> Path:
    """
    Get the presets file path from configuration or use default.
    
    Args:
        custom_path: Direct path override
        config: AppConfig object with presets_file_path attribute
        
    Returns:
        Path object for presets file
    """
    if custom_path is not None:
        return custom_path
    
    if config is not None and hasattr(config, 'presets_file_path'):
        return config.presets_file_path
    
    return Path("presets.json")

def migrate_presets_if_needed(old_path: Path, new_path: Path) -> bool:
    """
    Migrate presets from old location to new location if needed.
    
    Args:
        old_path: Path to old presets file
        new_path: Path to new presets file location
        
    Returns:
        True if migration was performed, False otherwise
    """
    # Don't migrate if old file doesn't exist
    if not old_path.exists():
        return False
    
    # Don't migrate if new file already exists
    if new_path.exists():
        return False
    
    try:
        # Ensure the new directory exists
        new_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy the old file to new location
        shutil.copy2(old_path, new_path)
        
        # Remove the old file after successful copy
        old_path.unlink()
        
        logging.info(f"Successfully migrated presets from {old_path} to {new_path}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to migrate presets from {old_path} to {new_path}: {e}")
        return False

if __name__ == '__main__':
    # Example Usage and Basic Test
    print(f"Using presets file: {PRESETS_FILE_PATH.resolve()}")

    # 1. Load initial (likely empty or non-existent)
    current_presets = load_presets_from_file()
    print(f"Initial loaded presets: {current_presets}")
    print(f"Initial preset names: {get_preset_names(current_presets)}")

    # 2. Add a new preset
    preset1_items = [PresetItem(part_id=101, quantity=10), PresetItem(part_id="SKU-002", quantity=5)]
    preset1 = Preset(name="My First Preset", items=preset1_items)
    current_presets = add_or_update_preset(current_presets, preset1)
    print(f"After adding '{preset1.name}': {current_presets}")

    # 3. Add another preset
    preset2_items = [PresetItem(part_id=202, quantity=2), PresetItem(part_id=303, quantity=3)]
    preset2 = Preset(name="Office Setup", items=preset2_items)
    current_presets = add_or_update_preset(current_presets, preset2)
    print(f"After adding '{preset2.name}': {current_presets}")
    print(f"Preset names: {get_preset_names(current_presets)}")

    # 4. Save to file
    if save_presets_to_file(current_presets):
        print(f"Presets saved to {PRESETS_FILE_PATH}")
    else:
        print(f"Failed to save presets to {PRESETS_FILE_PATH}")

    # 5. Load from file again
    loaded_again = load_presets_from_file()
    print(f"Loaded again from file: {loaded_again}")
    print(f"Preset names from loaded file: {get_preset_names(loaded_again)}")

    # 6. Get a specific preset
    retrieved_preset = get_preset_by_name(loaded_again, "My First Preset")
    if retrieved_preset:
        print(f"Retrieved preset 'My First Preset': {retrieved_preset}")
    else:
        print("Could not retrieve 'My First Preset'")
    
    retrieved_non_existent = get_preset_by_name(loaded_again, "Non Existent Preset")
    print(f"Attempt to retrieve non-existent preset: {retrieved_non_existent}")


    # 7. Update an existing preset
    preset1_updated_items = [PresetItem(part_id=101, quantity=15), PresetItem(part_id="SKU-002", quantity=7), PresetItem(part_id="NEW-003", quantity=1)]
    preset1_updated = Preset(name="My First Preset", items=preset1_updated_items)
    current_presets = add_or_update_preset(loaded_again, preset1_updated)
    print(f"After updating '{preset1_updated.name}': {current_presets}")
    save_presets_to_file(current_presets)

    # 8. Delete a preset
    current_presets = delete_preset_by_name(current_presets, "Office Setup")
    print(f"After deleting 'Office Setup': {current_presets}")
    print(f"Preset names after deletion: {get_preset_names(current_presets)}")

    # 9. Delete a non-existent preset
    current_presets = delete_preset_by_name(current_presets, "Imaginary Preset")
    print(f"After attempting to delete 'Imaginary Preset': {current_presets}")

    # 10. Save final changes
    if save_presets_to_file(current_presets):
        print(f"Final presets saved to {PRESETS_FILE_PATH}")

    # Test empty file scenario
    # To test this, manually create an empty presets.json or delete it
    # empty_presets_path = Path("empty_presets.json")
    # if empty_presets_path.exists():
    #     empty_presets_path.unlink()
    # with open(empty_presets_path, "w") as f:
    #     pass # create empty file
    # print(f"Loading from empty file ({empty_presets_path}): {load_presets_from_file(empty_presets_path)}")
    # if empty_presets_path.exists():
    #    empty_presets_path.unlink()

    # Test invalid JSON
    # invalid_json_path = Path("invalid_presets.json")
    # with open(invalid_json_path, "w") as f:
    #    f.write("{invalid_json_syntax,,")
    # print(f"Loading from invalid JSON file ({invalid_json_path}): {load_presets_from_file(invalid_json_path)}")
    # if invalid_json_path.exists():
    #    invalid_json_path.unlink()