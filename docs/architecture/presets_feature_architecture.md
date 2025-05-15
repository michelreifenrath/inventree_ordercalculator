# Preset Management Feature Architecture

This document outlines the architecture for the "Save/Load Presets" feature in the Streamlit GUI.

## 1. Overview

The feature will allow users to save their current input configurations as named presets, load previously saved presets, and optionally delete them. Presets will be stored locally in a `presets.json` file.

## 2. Data Models

We will define Pydantic models to ensure data consistency for presets. These models can be placed in `src/inventree_order_calculator/models.py` or a new `src/inventree_order_calculator/presets_models.py` if preferred.

```python
from typing import List, Dict, Union
from pydantic import BaseModel, Field

class PresetItem(BaseModel):
    """Represents a single item within a preset."""
    part_id: Union[int, str]  # Part ID can be int or a string (e.g., IPN)
    quantity: int

class Preset(BaseModel):
    """Represents a single preset configuration."""
    name: str = Field(..., min_length=1) # Preset name, must not be empty
    items: List[PresetItem]

class PresetsFile(BaseModel):
    """Represents the structure of the presets.json file."""
    presets: List[Preset] = []
```

## 3. Storage

-   **File:** `presets.json`
-   **Location:** In the user's application data directory or a configurable path. For simplicity, we can start with it in the root of the project or a `data/` subfolder.
-   **Format:** A JSON object containing a single key "presets", which is a list of `Preset` objects.

**Example `presets.json`:**
```json
{
  "presets": [
    {
      "name": "My Standard Kit",
      "items": [
        {"part_id": "PN001", "quantity": 10},
        {"part_id": 123, "quantity": 5}
      ]
    },
    {
      "name": "Beginner Pack",
      "items": [
        {"part_id": "PN002", "quantity": 2},
        {"part_id": "PN003", "quantity": 3}
      ]
    }
  ]
}
```

## 4. File I/O Functions

These functions will handle reading from and writing to `presets.json`. They should include error handling for file operations and JSON parsing. These functions would ideally reside in a new module, e.g., `src/inventree_order_calculator/presets_manager.py`.

```python
# In src/inventree_order_calculator/presets_manager.py
import json
from pathlib import Path
from typing import List, Optional
# Assuming Preset and PresetsFile models are accessible, e.g., from .models
# from .models import Preset, PresetsFile (or appropriate import path)

PRESETS_FILE_PATH = Path("presets.json") # Or a more robust path resolution

def load_presets_from_file() -> List[Preset]:
    """Loads presets from the presets.json file."""
    if not PRESETS_FILE_PATH.exists():
        return []
    try:
        with open(PRESETS_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Validate data with Pydantic model
            presets_file_data = PresetsFile(**data)
            return presets_file_data.presets
    except json.JSONDecodeError:
        # Log error or notify user
        print(f"Error: Could not decode JSON from {PRESETS_FILE_PATH}")
        return [] # Or raise an exception
    except FileNotFoundError:
        # This case is handled by the initial check, but good for robustness
        return []
    except Exception as e: # Catch other potential errors like Pydantic validation
        print(f"Error loading presets: {e}")
        return []


def save_presets_to_file(presets_data: List[Preset]) -> bool:
    """Saves the list of presets to the presets.json file."""
    try:
        presets_file_obj = PresetsFile(presets=presets_data)
        with open(PRESETS_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(presets_file_obj.model_dump(mode="json"), f, indent=2)
        return True
    except IOError as e:
        # Log error or notify user
        print(f"Error: Could not write to {PRESETS_FILE_PATH}: {e}")
        return False
    except Exception as e: # Catch other potential errors
        print(f"Error saving presets: {e}")
        return False

# Helper functions for preset management (add, update, delete)

def add_or_update_preset(name: str, items: List[PresetItem]) -> bool:
    """Adds a new preset or updates an existing one by name."""
    presets = load_presets_from_file()
    existing_preset_index = -1
    for i, p in enumerate(presets):
        if p.name == name:
            existing_preset_index = i
            break

    new_preset = Preset(name=name, items=items)
    if existing_preset_index != -1:
        presets[existing_preset_index] = new_preset # Update
    else:
        presets.append(new_preset) # Add
    
    return save_presets_to_file(presets)

def delete_preset_by_name(name: str) -> bool:
    """Deletes a preset by its name."""
    presets = load_presets_from_file()
    updated_presets = [p for p in presets if p.name != name]
    
    if len(updated_presets) < len(presets): # Check if a preset was actually removed
        return save_presets_to_file(updated_presets)
    return False # Preset not found or no change
```

## 5. Streamlit UI Interaction Flow (`src/inventree_order_calculator/streamlit_app.py`)

### 5.1. State Management with `st.session_state`

Initialize and manage the following in `st.session_state`:

-   `st.session_state.preset_name_input`: Stores the current value of the preset name input field.
-   `st.session_state.selected_preset_for_load`: Stores the name of the preset selected from the load selectbox.
-   `st.session_state.selected_preset_for_delete`: (If delete functionality is separate) Stores the name of the preset selected for deletion.
-   `st.session_state.available_presets`: A list of `Preset` objects, loaded from `presets.json`. This is used to populate the selectbox.
-   `st.session_state.parts_input_text`: The main text area for part inputs (already existing, will be updated by "Load Preset").

**Initialization (typically at the start of the Streamlit app script):**
```python
# In streamlit_app.py
# from .presets_manager import load_presets_from_file, add_or_update_preset, delete_preset_by_name
# from .models import PresetItem # or appropriate import path

if 'available_presets' not in st.session_state:
    st.session_state.available_presets = load_presets_from_file() # Load initial presets

if 'preset_name_input' not in st.session_state:
    st.session_state.preset_name_input = ""

if 'selected_preset_for_load' not in st.session_state:
    st.session_state.selected_preset_for_load = None

# Initialize parts_input_text if not already done
if 'parts_input_text' not in st.session_state:
    st.session_state.parts_input_text = ""
```

### 5.2. UI Elements and Logic

```python
# In streamlit_app.py, within the main app function

# --- Preset Management UI Section ---
st.sidebar.subheader("Preset Management")

# Input for preset name
st.session_state.preset_name_input = st.sidebar.text_input(
    "Preset Name", 
    value=st.session_state.get('preset_name_input', "") # Persist value
)

# Button "Save Current Set"
if st.sidebar.button("Save Current Set"):
    if st.session_state.preset_name_input:
        # 1. Parse current main input (st.session_state.parts_input_text)
        # This requires a parser function, similar to how the main app processes input.
        # Let's assume a function `parse_input_to_preset_items(text_input: str) -> List[PresetItem]` exists.
        # This parser needs to convert "PN001 10\nPN002 5" into PresetItem objects.
        
        # Example of how items might be parsed (simplified - needs robust parsing)
        current_items_text = st.session_state.parts_input_text
        parsed_items: List[PresetItem] = []
        try:
            # This parsing logic needs to be robust and handle various formats/errors
            # It should be similar to the main input parsing logic of the calculator
            for line in current_items_text.strip().split('\n'):
                if not line.strip():
                    continue
                parts = line.strip().split()
                if len(parts) >= 2:
                    part_id_str = parts[0]
                    quantity_str = parts[-1] # Take the last part as quantity
                    # Attempt to convert part_id to int if possible, else keep as str
                    try:
                        part_id = int(part_id_str)
                    except ValueError:
                        part_id = part_id_str
                    
                    parsed_items.append(PresetItem(part_id=part_id, quantity=int(quantity_str)))
                else:
                    st.sidebar.warning(f"Skipping invalid line for preset: '{line}'")
            
            if parsed_items:
                if add_or_update_preset(st.session_state.preset_name_input, parsed_items):
                    st.sidebar.success(f"Preset '{st.session_state.preset_name_input}' saved!")
                    st.session_state.available_presets = load_presets_from_file() # Refresh list
                    st.session_state.preset_name_input = "" # Clear input field
                    st.experimental_rerun() # To update selectbox immediately
                else:
                    st.sidebar.error("Failed to save preset.")
            else:
                st.sidebar.warning("No items to save in the preset. Input is empty or invalid.")

        except ValueError as e:
            st.sidebar.error(f"Invalid quantity in input: {e}. Preset not saved.")
        except Exception as e:
            st.sidebar.error(f"Error parsing input for preset: {e}")
            
    else:
        st.sidebar.warning("Please enter a name for the preset.")

# Selectbox to list/choose saved presets
preset_names = [p.name for p in st.session_state.available_presets]
if not preset_names:
    st.sidebar.caption("No presets saved yet.")
    st.session_state.selected_preset_for_load = None # Ensure it's None if no presets
else:
    # Ensure selected_preset_for_load is valid or default to first if it becomes invalid
    current_selection = st.session_state.get('selected_preset_for_load')
    if current_selection not in preset_names and preset_names:
        current_selection = preset_names[0] # Default to first if previous selection is gone
    
    st.session_state.selected_preset_for_load = st.sidebar.selectbox(
        "Load Preset",
        options=preset_names,
        index=preset_names.index(current_selection) if current_selection in preset_names else 0,
        key="load_preset_selector" # Unique key for selectbox
    )

    # Button "Load Selected Set"
    if st.sidebar.button("Load Selected Set"):
        if st.session_state.selected_preset_for_load:
            selected_preset_name = st.session_state.selected_preset_for_load
            preset_to_load = next((p for p in st.session_state.available_presets if p.name == selected_preset_name), None)
            
            if preset_to_load:
                # Populate main input text area
                # This requires a formatter function: `format_preset_items_to_text(items: List[PresetItem]) -> str`
                # Example: Convert PresetItem objects back to "PN001 10\nPN002 5"
                formatted_text = ""
                for item in preset_to_load.items:
                    formatted_text += f"{item.part_id} {item.quantity}\n"
                
                st.session_state.parts_input_text = formatted_text.strip()
                st.sidebar.success(f"Preset '{selected_preset_name}' loaded!")
                # Trigger rerun to update the main text_area widget if it's not automatically doing so
                # due to direct session_state modification.
                st.experimental_rerun() 
            else:
                st.sidebar.error(f"Could not find preset '{selected_preset_name}' to load.")
        else:
            st.sidebar.warning("No preset selected to load.")

    # Button "Delete Selected Set"
    if st.sidebar.button("Delete Selected Set", key="delete_preset_button"):
        if st.session_state.selected_preset_for_load: # Assuming we use the same selectbox for deletion target
            preset_name_to_delete = st.session_state.selected_preset_for_load
            if delete_preset_by_name(preset_name_to_delete):
                st.sidebar.success(f"Preset '{preset_name_to_delete}' deleted!")
                st.session_state.available_presets = load_presets_from_file() # Refresh list
                # If the deleted preset was the one selected, reset selection
                if st.session_state.selected_preset_for_load == preset_name_to_delete:
                    st.session_state.selected_preset_for_load = None 
                st.experimental_rerun() # To update selectbox and UI
            else:
                st.sidebar.error(f"Failed to delete preset '{preset_name_to_delete}'. It might not exist.")
        else:
            st.sidebar.warning("No preset selected to delete.")

# The main parts input text area (ensure it uses session state)
# st.session_state.parts_input_text = st.text_area(
#     "Enter Part ID and Quantity (one per line, e.g., 'PART_SKU 10')",
#     value=st.session_state.get('parts_input_text', ""), # Use .get for safety
#     height=200,
#     key="main_parts_input" # Ensure a key for reliable state
# )
```

### 5.3. Populating and Updating Preset List for Selectbox

-   **Initial Population:** `st.session_state.available_presets` is loaded from `presets.json` via `load_presets_from_file()` when the session state variable is first initialized.
-   **Updates:** After a successful "Save" or "Delete" operation, `st.session_state.available_presets` is reloaded from the file by calling `load_presets_from_file()` again. `st.experimental_rerun()` is called to ensure the UI (specifically the selectbox) reflects these changes immediately.
-   The `options` for `st.selectbox` are derived directly from `[p.name for p in st.session_state.available_presets]`.

### 5.4. Updating Main Input Text Area (`st.session_state.parts_input_text`)

-   When "Load Selected Set" is clicked:
    1.  The `Preset` object corresponding to `st.session_state.selected_preset_for_load` is retrieved from `st.session_state.available_presets`.
    2.  Its `items` (a list of `PresetItem` objects) are formatted back into a multi-line string (e.g., "PART_ID1 QTY1\nPART_ID2 QTY2").
    3.  This string is assigned to `st.session_state.parts_input_text`.
    4.  `st.experimental_rerun()` ensures the `st.text_area` widget, which should be bound to `st.session_state.parts_input_text`, updates its displayed content.

### 5.5. Constructing New Presets from Main Input

-   When "Save Current Set" is clicked:
    1.  The content of `st.session_state.parts_input_text` is read.
    2.  A parser function (e.g., `parse_input_to_preset_items`) converts this string into a list of `PresetItem` objects. This parser needs to be robust, handling potential errors in formatting, non-numeric quantities, etc. It should ideally mirror the logic used by the main application to parse this input for calculations.
    3.  The `st.session_state.preset_name_input` provides the name for the new `Preset`.
    4.  A new `Preset` object is created.
    5.  The `add_or_update_preset` function is called to save it to `presets.json`.

## 6. Modularity

It is highly recommended to organize the new preset-related logic into a separate Python module.

-   **New File:** `src/inventree_order_calculator/presets_manager.py`
    -   This file would contain:
        -   `PRESETS_FILE_PATH` constant.
        -   `load_presets_from_file()`
        -   `save_presets_to_file(presets_data)`
        -   `add_or_update_preset(name, items)`
        -   `delete_preset_by_name(name)`
        -   Potentially helper functions for parsing input to `PresetItem` list and formatting `PresetItem` list to string, if these are complex enough and distinct from main app parsing.

-   **Models:** `PresetItem`, `Preset`, and `PresetsFile` Pydantic models can reside in `src/inventree_order_calculator/models.py` or a dedicated `src/inventree_order_calculator/presets_models.py`.

-   **Streamlit App (`streamlit_app.py`):**
    -   Imports functions from `presets_manager.py` and models.
    -   Handles UI elements and interaction logic as described in section 5.
    -   Manages `st.session_state` for preset-related data.

This separation keeps `streamlit_app.py` focused on UI presentation and event handling, while `presets_manager.py` encapsulates the business logic and data persistence for presets.

## 7. Error Handling and User Feedback

-   **File I/O:** `load_presets_from_file` and `save_presets_to_file` should catch `FileNotFoundError`, `json.JSONDecodeError`, `IOError`, and Pydantic `ValidationError`, providing feedback to the user via `st.error` or `st.warning` in the Streamlit app, or logging errors.
-   **Input Parsing (for Save):** The logic converting `st.session_state.parts_input_text` to `List[PresetItem]` must handle malformed lines, non-numeric quantities, etc., and inform the user via `st.warning` or `st.error` without crashing.
-   **Empty Preset Name:** Prevent saving a preset with an empty name.
-   **No Preset Selected:** Provide feedback if "Load" or "Delete" is clicked without a preset selected.
-   **Successful Operations:** Use `st.success` to confirm successful save, load, or delete operations.

## 8. Future Considerations / Enhancements

-   **Path Configuration:** Allow configuration of `PRESETS_FILE_PATH` (e.g., via environment variable or a settings section).
-   **Backup/Restore:** Functionality to backup and restore `presets.json`.
-   **Cloud Sync:** (Advanced) Sync presets with a cloud storage service.
-   **More Robust Parsing:** The functions `parse_input_to_preset_items` and `format_preset_items_to_text` need to be carefully implemented to match the main application's input/output format precisely. Consider centralizing parsing logic if it's shared.
-   **Confirmation for Delete:** Add a confirmation dialog before deleting a preset.
-   **Unique Preset Names:** Enforce unique preset names during save, or clarify update behavior. The current `add_or_update_preset` updates if the name exists.