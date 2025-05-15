# Pseudocode: presets_manager.py

This document outlines the pseudocode for managing presets, including loading, saving, adding, updating, and deleting presets.

## 1. Imports and Pydantic Models

```pseudocode
IMPORT Path FROM pathlib
IMPORT List, Optional, Union, Dict FROM typing
IMPORT json
IMPORT logging // For error logging
IMPORT uuid // For generating unique IDs for monitoring lists

// Assume Pydantic models are defined (e.g., in models.py or presets_models.py)
// from .models import PresetItem, Preset, MonitoringPartItem, MonitoringList, PresetsFile

// Pydantic Model Definitions (as per architecture/presets_feature_architecture.md and automated_monitoring_spec.md)
CLASS PresetItem: // For regular calculation presets
    part_id: Union[int, str] // Can be InvenTree part ID or name for lookup
    quantity: int

CLASS Preset: // For regular calculation presets
    name: str // Must not be empty, unique identifier for the preset
    items: List[PresetItem]

CLASS MonitoringPartItem: // For parts within a monitoring list
    name: str // Part name as known in InvenTree
    quantity: int
    version: Optional[str] = None // Optional specific version of the part

CLASS MonitoringList:
    id: str // Eindeutige ID für die Aufgabe (e.g., UUID)
    name: str // Benutzerdefinierter Name
    parts: List[MonitoringPartItem]
    active: bool = True // Default to active
    cron_schedule: str // Cron-Ausdruck
    recipients: List[str] // List of email addresses
    notify_condition: str = "on_change" // "always" or "on_change"
    last_hash: Optional[str] = None // MD5 hash of last significant result for "on_change"
    // TEST: monitoring_list_schema_validation_passes_for_valid_data (Implicitly tested by Pydantic)
    // TEST: monitoring_list_schema_validation_fails_for_invalid_data (Implicitly tested by Pydantic)

CLASS PresetsFile:
    presets: List[Preset] = [] // Defaults to an empty list for regular presets
    monitoring_lists: List[MonitoringList] = [] // Defaults to an empty list for monitoring tasks
```

## 2. Preset Management Functions

### Function: `load_presets_from_file(filepath: Path) -> PresetsFile`

```pseudocode
FUNCTION load_presets_from_file(filepath: Path) -> PresetsFile:
    // TDD: Test loading from a non-existent file (should return empty PresetsFile)
    IF NOT filepath.exists():
        RETURN PresetsFile(presets=[], monitoring_lists=[]) // Return default empty PresetsFile

    TRY:
        WITH open(filepath, "r", encoding="utf-8") AS f:
            raw_data = json.load(f)
        
        // TDD: Test loading a file with invalid JSON structure (should log error, return empty PresetsFile)
        // TDD: Test loading a file with valid JSON but data not matching PresetsFile schema (Pydantic validation error)
        // TDD: Test loading a file with empty presets list
        // TDD: Test loading a file with valid presets
        // TDD: Test loading a file with empty monitoring_lists
        // TDD: Test loading a file with valid monitoring_lists
        // TEST: presets_manager_can_load_monitoring_lists (Covered by successful load)
        loaded_presets_file = PresetsFile(**raw_data) // Pydantic will validate both presets and monitoring_lists
        RETURN loaded_presets_file
    CATCH json.JSONDecodeError AS e:
        logging.error(f"JSON decode error loading presets from {filepath}: {e}")
        RETURN PresetsFile(presets=[], monitoring_lists=[])
    CATCH ValidationError AS e: // Pydantic's validation error
        logging.error(f"Data validation error loading presets from {filepath}: {e}")
        RETURN PresetsFile(presets=[], monitoring_lists=[])
    CATCH Exception AS e: // Catch any other unexpected errors
        logging.error(f"Unexpected error loading presets from {filepath}: {e}")
        RETURN PresetsFile(presets=[], monitoring_lists=[])
ENDFUNCTION
```

### Function: `save_presets_to_file(filepath: Path, presets_data: PresetsFile) -> bool`

```pseudocode
FUNCTION save_presets_to_file(filepath: Path, presets_data: PresetsFile) -> bool:
    // TDD: Test saving presets to a new file
    // TDD: Test saving presets, overwriting an existing file
    // TDD: Test saving an empty PresetsFile
    TRY:
        // Ensure parent directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)

        WITH open(filepath, "w", encoding="utf-8") AS f:
            json_data = presets_data.model_dump(mode="json") // Use Pydantic's method
            json.dump(json_data, f, indent=2)
        RETURN True
    CATCH IOError AS e:
        // TDD: Test saving to a read-only location or disk full (simulate IOError)
        logging.error(f"IOError saving presets to {filepath}: {e}")
        RETURN False
    CATCH Exception AS e: // Catch any other unexpected errors
        logging.error(f"Unexpected error saving presets to {filepath}: {e}")
        RETURN False
ENDFUNCTION
```

### Function: `add_or_update_preset(presets_data: PresetsFile, new_preset: Preset) -> PresetsFile`

```pseudocode
FUNCTION add_or_update_preset(presets_data: PresetsFile, new_preset: Preset) -> PresetsFile:
    // TDD: Test adding a new preset to an empty list
    // TDD: Test adding a new preset to an existing list
    // TDD: Test updating an existing preset by name
    // TDD: Test that preset names are case-sensitive if that's the design (or insensitive if not)

    existing_preset_index = -1
    FOR i, preset IN enumerate(presets_data.presets):
        IF preset.name == new_preset.name:
            existing_preset_index = i
            BREAK
    
    updated_presets_list = list(presets_data.presets) // Create a mutable copy

    IF existing_preset_index != -1:
        updated_presets_list[existing_preset_index] = new_preset // Update
    ELSE:
        updated_presets_list.append(new_preset) // Add
    
    RETURN PresetsFile(presets=updated_presets_list)
ENDFUNCTION
```

### Function: `delete_preset_by_name(presets_data: PresetsFile, preset_name: str) -> PresetsFile`

```pseudocode
FUNCTION delete_preset_by_name(presets_data: PresetsFile, preset_name: str) -> PresetsFile:
    // TDD: Test deleting an existing preset
    // TDD: Test deleting a non-existent preset (should return data unchanged)
    // TDD: Test deleting from an empty list of presets
    // TDD: Test deleting the only preset in the list

    updated_presets_list = [
        preset FOR preset IN presets_data.presets IF preset.name != preset_name
    ]
    
    RETURN PresetsFile(presets=updated_presets_list)
ENDFUNCTION
```

### Function: `get_preset_names(presets_data: PresetsFile) -> List[str]`

```pseudocode
FUNCTION get_preset_names(presets_data: PresetsFile) -> List[str]:
    // TDD: Test getting names from an empty PresetsFile (should return empty list)
    // TDD: Test getting names from a PresetsFile with multiple presets
    RETURN [preset.name FOR preset IN presets_data.presets]
ENDFUNCTION
```

### Function: `get_preset_by_name(presets_data: PresetsFile, name: str) -> Optional[Preset]`

```pseudocode
FUNCTION get_preset_by_name(presets_data: PresetsFile, name: str) -> Optional[Preset]:
    // TDD: Test getting an existing preset by name
    // TDD: Test getting a non-existent preset by name (should return None)
    // TDD: Test getting from an empty PresetsFile
    FOR preset IN presets_data.presets:
        IF preset.name == name:
            RETURN preset
    RETURN None
ENDFUNCTION

## 3. Monitoring List Management Functions

### Function: `get_monitoring_lists(presets_data: PresetsFile) -> List[MonitoringList]`
```pseudocode
FUNCTION get_monitoring_lists(presets_data: PresetsFile) -> List[MonitoringList]:
    // TEST: get_monitoring_lists_returns_empty_list_if_none_exist
    // TEST: get_monitoring_lists_returns_all_lists
    RETURN presets_data.monitoring_lists
ENDFUNCTION
```

### Function: `get_monitoring_list_by_id(presets_data: PresetsFile, list_id: str) -> Optional[MonitoringList]`
```pseudocode
FUNCTION get_monitoring_list_by_id(presets_data: PresetsFile, list_id: str) -> Optional[MonitoringList]:
    // TEST: get_monitoring_list_by_id_returns_list_if_exists
    // TEST: get_monitoring_list_by_id_returns_none_if_not_exists
    FOR m_list IN presets_data.monitoring_lists:
        IF m_list.id == list_id:
            RETURN m_list
        ENDIF
    ENDFOR
    RETURN None
ENDFUNCTION
```

### Function: `add_monitoring_list(presets_data: PresetsFile, new_monitoring_list_data: Dict) -> PresetsFile`
```pseudocode
// new_monitoring_list_data is a Dict to allow for partial creation before Pydantic model, or pass a MonitoringList object directly
FUNCTION add_monitoring_list(presets_data: PresetsFile, new_monitoring_list_data: Union[MonitoringList, Dict]) -> PresetsFile:
    // TEST: presets_manager_can_save_new_monitoring_list (Covers adding to empty and existing)
    // TEST: add_monitoring_list_generates_uuid_if_id_not_provided
    // TEST: add_monitoring_list_initializes_last_hash_to_none
    // TEST: add_monitoring_list_rejects_duplicate_id (or PresetsFile validation should catch this if ID must be unique)

    IF TYPEOF(new_monitoring_list_data) IS Dict:
        IF 'id' NOT IN new_monitoring_list_data OR new_monitoring_list_data['id'] IS NONE:
            new_monitoring_list_data['id'] = str(uuid.uuid4())
        IF 'last_hash' NOT IN new_monitoring_list_data: // Ensure last_hash is initialized if not provided
            new_monitoring_list_data['last_hash'] = None
        IF 'active' NOT IN new_monitoring_list_data: // Ensure active is initialized if not provided
            new_monitoring_list_data['active'] = True
        IF 'notify_condition' NOT IN new_monitoring_list_data: // Ensure notify_condition is initialized if not provided
            new_monitoring_list_data['notify_condition'] = "on_change"

        // Validate that no existing list has this ID
        FOR m_list IN presets_data.monitoring_lists:
            IF m_list.id == new_monitoring_list_data['id']:
                logging.error(f"Monitoring list with ID {new_monitoring_list_data['id']} already exists.")
                // Depending on desired behavior, could raise error or return presets_data unchanged
                RAISE ValueError(f"Duplicate monitoring list ID: {new_monitoring_list_data['id']}")
        ENDIF
        
        // Attempt to create the MonitoringList object from dict, Pydantic will validate
        TRY
            new_list_obj = MonitoringList(**new_monitoring_list_data)
        CATCH ValidationError AS e:
            logging.error(f"Validation error creating new monitoring list: {e}")
            RAISE // Re-raise to be handled by caller
        ENDTRY
    ELSE: // Assumes new_monitoring_list_data is already a MonitoringList object
        new_list_obj = new_monitoring_list_data
        IF new_list_obj.id IS NONE OR new_list_obj.id == "": // Should be caught by Pydantic if id is mandatory
            new_list_obj.id = str(uuid.uuid4())
        // Ensure no duplicate ID
        FOR m_list IN presets_data.monitoring_lists:
            IF m_list.id == new_list_obj.id:
                logging.error(f"Monitoring list with ID {new_list_obj.id} already exists.")
                RAISE ValueError(f"Duplicate monitoring list ID: {new_list_obj.id}")
        ENDIF
    ENDIF

    updated_monitoring_lists = list(presets_data.monitoring_lists) // Create mutable copy
    updated_monitoring_lists.append(new_list_obj)
    
    RETURN PresetsFile(presets=list(presets_data.presets), monitoring_lists=updated_monitoring_lists)
ENDFUNCTION
```

### Function: `update_monitoring_list(presets_data: PresetsFile, list_id: str, updated_data: Dict) -> PresetsFile`
```pseudocode
FUNCTION update_monitoring_list(presets_data: PresetsFile, list_id: str, updated_data_dict: Dict) -> PresetsFile:
    // TEST: presets_manager_can_update_existing_monitoring_list
    // TEST: update_monitoring_list_fails_if_id_not_found
    // TEST: update_monitoring_list_correctly_modifies_fields
    // Note: updated_data_dict contains only the fields to be changed.

    found_index = -1
    FOR i, m_list IN enumerate(presets_data.monitoring_lists):
        IF m_list.id == list_id:
            found_index = i
            BREAK
        ENDIF
    ENDFOR

    IF found_index == -1:
        logging.warning(f"Monitoring list with ID {list_id} not found for update.")
        RETURN presets_data // Or raise error: RAISE ValueError(f"Monitoring list ID {list_id} not found")

    updated_monitoring_lists = list(presets_data.monitoring_lists)
    existing_list_dict = updated_monitoring_lists[found_index].model_dump() // Convert existing model to dict

    // Merge updates
    FOR key, value IN updated_data_dict.items():
        existing_list_dict[key] = value
    ENDFOR
    
    // Re-create the MonitoringList object with updated data, Pydantic validates
    TRY
        updated_list_obj = MonitoringList(**existing_list_dict)
        updated_monitoring_lists[found_index] = updated_list_obj
    CATCH ValidationError AS e:
        logging.error(f"Validation error updating monitoring list {list_id}: {e}")
        RAISE // Re-raise to be handled by caller
    ENDTRY
    
    RETURN PresetsFile(presets=list(presets_data.presets), monitoring_lists=updated_monitoring_lists)
ENDFUNCTION
```

### Function: `delete_monitoring_list(presets_data: PresetsFile, list_id: str) -> PresetsFile`
```pseudocode
FUNCTION delete_monitoring_list(presets_data: PresetsFile, list_id: str) -> PresetsFile:
    // TEST: presets_manager_can_delete_monitoring_list
    // TEST: delete_monitoring_list_does_nothing_if_id_not_found
    
    initial_count = len(presets_data.monitoring_lists)
    updated_monitoring_lists = [
        m_list FOR m_list IN presets_data.monitoring_lists IF m_list.id != list_id
    ]

    IF len(updated_monitoring_lists) == initial_count:
        logging.warning(f"Monitoring list with ID {list_id} not found for deletion.")
        // No change, return original data
        RETURN presets_data
    
    RETURN PresetsFile(presets=list(presets_data.presets), monitoring_lists=updated_monitoring_lists)
ENDFUNCTION
```