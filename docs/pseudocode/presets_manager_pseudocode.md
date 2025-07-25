# Pseudocode: presets_manager.py

This document outlines the pseudocode for managing presets, including loading, saving, adding, updating, and deleting presets.

## 1. Imports and Pydantic Models

```pseudocode
IMPORT Path FROM pathlib
IMPORT List, Optional, Union FROM typing
IMPORT json
IMPORT logging // For error logging

// Assume Pydantic models are defined (e.g., in models.py or presets_models.py)
// from .models import PresetItem, Preset, PresetsFile

// Pydantic Model Definitions (as per architecture/presets_feature_architecture.md)
CLASS PresetItem:
    part_id: Union[int, str]
    quantity: int

CLASS Preset:
    name: str // Must not be empty
    items: List[PresetItem]

CLASS PresetsFile:
    presets: List[Preset] = [] // Defaults to an empty list
```

## 2. Preset Management Functions

### Function: `load_presets_from_file(filepath: Path) -> PresetsFile`

```pseudocode
FUNCTION load_presets_from_file(filepath: Path) -> PresetsFile:
    // TDD: Test loading from a non-existent file (should return empty PresetsFile)
    IF NOT filepath.exists():
        RETURN PresetsFile(presets=[]) // Return default empty PresetsFile

    TRY:
        WITH open(filepath, "r", encoding="utf-8") AS f:
            raw_data = json.load(f)
        
        // TDD: Test loading a file with invalid JSON structure (should log error, return empty PresetsFile)
        // TDD: Test loading a file with valid JSON but data not matching PresetsFile schema (Pydantic validation error)
        // TDD: Test loading a file with empty presets list
        // TDD: Test loading a file with valid presets
        loaded_presets_file = PresetsFile(**raw_data) // Pydantic will validate
        RETURN loaded_presets_file
    CATCH json.JSONDecodeError AS e:
        logging.error(f"JSON decode error loading presets from {filepath}: {e}")
        RETURN PresetsFile(presets=[])
    CATCH ValidationError AS e: // Pydantic's validation error
        logging.error(f"Data validation error loading presets from {filepath}: {e}")
        RETURN PresetsFile(presets=[])
    CATCH Exception AS e: // Catch any other unexpected errors
        logging.error(f"Unexpected error loading presets from {filepath}: {e}")
        RETURN PresetsFile(presets=[])
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