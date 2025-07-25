# Pseudocode: Streamlit UI for Preset Management

This document outlines the pseudocode for the Streamlit UI components and logic for managing presets, interacting with the `presets_manager`.

## 1. Imports and Constants

```pseudocode
IMPORT streamlit AS st
IMPORT Path FROM pathlib // For PRESETS_FILE_PATH

// Functions from presets_manager
// IMPORT load_presets_from_file FROM presets_manager
// IMPORT save_presets_to_file FROM presets_manager
// IMPORT add_or_update_preset FROM presets_manager
// IMPORT delete_preset_by_name FROM presets_manager
// IMPORT get_preset_names FROM presets_manager
// IMPORT get_preset_by_name FROM presets_manager

// Pydantic Models (assuming they are accessible)
// IMPORT Preset, PresetItem, PresetsFile FROM models 

// Constants
PRESETS_FILE_PATH = Path("presets.json") // Or a more robust path from config
```

## 2. Helper Functions (Streamlit specific)

### Function: `parse_input_text_to_preset_items(input_text: str) -> List[PresetItem]`

```pseudocode
FUNCTION parse_input_text_to_preset_items(input_text: str) -> List[PresetItem]:
    // This function converts the main parts input text (e.g., "ID1 QTY1\nID2 QTY2")
    // into a list of PresetItem objects.
    // It needs to be robust and handle various formats/errors.
    // TDD: Test parsing valid input with multiple lines
    // TDD: Test parsing input with extra spaces
    // TDD: Test parsing input with mixed int/str part_ids
    // TDD: Test parsing input with non-numeric quantity (should raise error or return empty/partial)
    // TDD: Test parsing empty input string (should return empty list)
    // TDD: Test parsing input with lines that don't have two parts (ID and quantity)

    parsed_items: List[PresetItem] = []
    lines = input_text.strip().split('\n')
    FOR line IN lines:
        IF NOT line.strip():
            CONTINUE // Skip empty lines
        
        parts = line.strip().split() // Simple split, might need more robust parsing
        IF length(parts) >= 2:
            part_id_str = parts[0]
            quantity_str = parts[-1] // Assume last part is quantity

            TRY:
                quantity = int(quantity_str)
                // Attempt to convert part_id to int if possible, else keep as str
                TRY:
                    part_id = int(part_id_str)
                CATCH ValueError:
                    part_id = part_id_str
                
                parsed_items.append(PresetItem(part_id=part_id, quantity=quantity))
            CATCH ValueError:
                // Log error or notify: "Invalid quantity for line: {line}"
                // Depending on strictness, either skip or raise an error
                st.warning(f"Skipping line with invalid quantity: '{line}'") 
                CONTINUE 
        ELSE:
            // Log error or notify: "Skipping invalid line format: {line}"
            st.warning(f"Skipping line with invalid format: '{line}'")
            CONTINUE
    RETURN parsed_items
ENDFUNCTION
```

### Function: `format_preset_items_to_text(items: List[PresetItem]) -> str`

```pseudocode
FUNCTION format_preset_items_to_text(items: List[PresetItem]) -> str:
    // Converts a list of PresetItem objects back to a string for the text_area.
    // Format: "PART_ID1 QUANTITY1\nPART_ID2 QUANTITY2"
    // TDD: Test formatting an empty list of items (should return empty string)
    // TDD: Test formatting a list with one item
    // TDD: Test formatting a list with multiple items
    
    lines: List[str] = []
    FOR item IN items:
        lines.append(f"{item.part_id} {item.quantity}")
    RETURN "\n".join(lines)
ENDFUNCTION
```

## 3. Streamlit App Logic

```pseudocode
FUNCTION run_streamlit_app(): // Or within your main Streamlit app function

    // --- Initialization of Session State for Presets ---
    // TDD: Test initial load when presets file doesn't exist
    // TDD: Test initial load when presets file exists and is valid
    // TDD: Test initial load when presets file is empty or invalid JSON
    IF 'presets_data' NOT IN st.session_state:
        st.session_state.presets_data = load_presets_from_file(PRESETS_FILE_PATH)
    
    IF 'preset_names' NOT IN st.session_state:
        st.session_state.preset_names = get_preset_names(st.session_state.presets_data)

    IF 'new_preset_name' NOT IN st.session_state:
        st.session_state.new_preset_name = "" // For the text input

    IF 'selected_preset_name' NOT IN st.session_state:
        // Initialize with the first preset name if available, else None
        st.session_state.selected_preset_name = st.session_state.preset_names[0] IF st.session_state.preset_names ELSE None

    // Ensure parts_input_text is initialized (likely already exists in the app)
    IF 'parts_input_text' NOT IN st.session_state:
        st.session_state.parts_input_text = ""


    // --- UI Elements for Preset Management (e.g., in sidebar) ---
    st.sidebar.subheader("Preset Management")

    // 1. Input for new preset name
    st.session_state.new_preset_name = st.sidebar.text_input(
        "New Preset Name:",
        value=st.session_state.new_preset_name 
    )

    // 2. Save Current Set Button
    IF st.sidebar.button("Save Current Set"):
        // TDD: Test saving with empty preset name (should show warning)
        // TDD: Test saving with valid name and valid items (should succeed)
        // TDD: Test saving with valid name but empty/invalid items from parts_input_text (should show warning/error)
        // TDD: Test saving an existing preset name (should update)
        
        current_parts_text = st.session_state.parts_input_text
        preset_name_to_save = st.session_state.new_preset_name.strip()

        IF NOT preset_name_to_save:
            st.sidebar.warning("Please enter a name for the preset.")
        ELSE:
            TRY:
                preset_items = parse_input_text_to_preset_items(current_parts_text)
                // TDD: Test parse_input_text_to_preset_items thoroughly (covered in its own TDDs)
                
                IF NOT preset_items:
                    st.sidebar.warning("No valid items to save. Check input format (ID Quantity per line).")
                ELSE:
                    new_preset_obj = Preset(name=preset_name_to_save, items=preset_items)
                    
                    // Update internal data structure
                    st.session_state.presets_data = add_or_update_preset(
                        st.session_state.presets_data, 
                        new_preset_obj
                    )
                    
                    // Save to file
                    save_success = save_presets_to_file(PRESETS_FILE_PATH, st.session_state.presets_data)
                    
                    IF save_success:
                        st.sidebar.success(f"Preset '{preset_name_to_save}' saved!")
                        // Update preset names for selectbox
                        st.session_state.preset_names = get_preset_names(st.session_state.presets_data)
                        // Clear the input field
                        st.session_state.new_preset_name = "" 
                        // Potentially update selected_preset_name if the new one should be selected
                        st.session_state.selected_preset_name = preset_name_to_save 
                        st.experimental_rerun() // To refresh UI elements like selectbox and clear input
                    ELSE:
                        st.sidebar.error("Failed to save preset to file.")
                        // Potentially revert st.session_state.presets_data if save failed critically
                        // For now, assume presets_data is updated in memory but file save failed.
            CATCH Exception AS e: // Catch errors from parsing or Preset creation
                st.sidebar.error(f"Error creating preset: {e}")

    // 3. Selectbox for loading/deleting presets
    IF NOT st.session_state.preset_names:
        st.sidebar.caption("No presets saved yet.")
        // Ensure selected_preset_name is None if list is empty
        IF st.session_state.selected_preset_name IS NOT None:
             st.session_state.selected_preset_name = None
             st.experimental_rerun() // if it was just emptied
    ELSE:
        // Ensure selected_preset_name is valid or default to first if it becomes invalid
        current_selection = st.session_state.get('selected_preset_name')
        IF current_selection NOT IN st.session_state.preset_names:
            st.session_state.selected_preset_name = st.session_state.preset_names[0]
            // No rerun needed here, selectbox will handle index based on this new value
        
        st.session_state.selected_preset_name = st.sidebar.selectbox(
            "Manage Presets:",
            options=st.session_state.preset_names,
            index=(st.session_state.preset_names.index(st.session_state.selected_preset_name) 
                   IF st.session_state.selected_preset_name IN st.session_state.preset_names 
                   ELSE 0)
        )

    // 4. Load Selected Set Button
    // Display button only if there are presets and one is selected
    IF st.session_state.selected_preset_name AND st.session_state.preset_names:
        IF st.sidebar.button("Load Selected Set"):
            // TDD: Test loading a valid selected preset
            // TDD: Test loading when selected_preset_name is somehow invalid (should not happen with proper selectbox setup)
            
            preset_to_load = get_preset_by_name(
                st.session_state.presets_data, 
                st.session_state.selected_preset_name
            )
            
            IF preset_to_load:
                st.session_state.parts_input_text = format_preset_items_to_text(preset_to_load.items)
                // TDD: Test format_preset_items_to_text (covered in its own TDDs)
                st.sidebar.success(f"Preset '{st.session_state.selected_preset_name}' loaded!")
                st.experimental_rerun() // To update the main text_area
            ELSE:
                st.sidebar.error(f"Could not find preset '{st.session_state.selected_preset_name}' to load. It may have been deleted elsewhere.")
                // Refresh preset list in case of inconsistency
                st.session_state.presets_data = load_presets_from_file(PRESETS_FILE_PATH)
                st.session_state.preset_names = get_preset_names(st.session_state.presets_data)
                st.experimental_rerun()


    // 5. Delete Selected Set Button
    // Display button only if there are presets and one is selected
    IF st.session_state.selected_preset_name AND st.session_state.preset_names:
        IF st.sidebar.button("Delete Selected Set", type="secondary"): // Or use a more prominent warning color/type
            // TDD: Test deleting a valid selected preset
            // TDD: Test deleting when selected_preset_name is somehow invalid
            // TDD: Test UI update after deletion (selectbox, selection reset)

            name_to_delete = st.session_state.selected_preset_name
            
            st.session_state.presets_data = delete_preset_by_name(
                st.session_state.presets_data,
                name_to_delete
            )
            
            save_success = save_presets_to_file(PRESETS_FILE_PATH, st.session_state.presets_data)
            
            IF save_success:
                st.sidebar.success(f"Preset '{name_to_delete}' deleted!")
                old_preset_names = list(st.session_state.preset_names) // Copy before update
                st.session_state.preset_names = get_preset_names(st.session_state.presets_data)
                
                // If the deleted preset was the one selected, reset selection to first or None
                IF name_to_delete IN old_preset_names: // Check against old list
                    IF st.session_state.preset_names: // If there are remaining presets
                        st.session_state.selected_preset_name = st.session_state.preset_names[0]
                    ELSE: // No presets left
                        st.session_state.selected_preset_name = None
                
                st.experimental_rerun() // To update UI
            ELSE:
                st.sidebar.error(f"Failed to save changes after deleting '{name_to_delete}'.")
                // Potentially reload presets_data from file to revert in-memory delete
                st.session_state.presets_data = load_presets_from_file(PRESETS_FILE_PATH)
                st.session_state.preset_names = get_preset_names(st.session_state.presets_data)
                st.experimental_rerun()


    // --- Main parts input text area (ensure it uses session state) ---
    // This is likely already part of your app. Ensure its 'value' and 'key' are tied to session state.
    // st.session_state.parts_input_text = st.text_area(
    //     "Enter Part ID and Quantity...",
    //     value=st.session_state.parts_input_text,
    //     key="parts_input_text_area", // Ensure a unique key
    //     height=300
    // )

ENDFUNCTION