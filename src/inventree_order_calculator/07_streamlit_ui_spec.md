# Specification: Streamlit UI for Inventree Order Calculator

This document outlines the specifications for a Streamlit-based web user interface for the Inventree Order Calculator.

## 1. Context and Goals

- **Goal:** Provide a user-friendly graphical interface for the existing Inventree Order Calculator logic.
- **Target Users:** Users who need to calculate required parts and subassemblies based on a list of top-level parts and quantities, interacting with an InvenTree instance.
- **Core Logic:** The UI will leverage the existing `AppConfig`, `ApiClient`, and `OrderCalculator` classes.

## 2. Functional Requirements

1.  **Configuration Loading:**
    *   The application MUST load the InvenTree URL and API Token from a `.env` file using the `AppConfig` class upon startup.
    *   The application MUST display the status of the configuration (e.g., "Configuration loaded from .env" or "Configuration missing, check .env file"). Display the URL, but mask or hide the token itself.
    *   // TEST: Configuration loads correctly from .env
    *   // TEST: Configuration status is displayed correctly
2.  **Part List Fetching:**
    *   On startup (after successful configuration), the application MUST connect to InvenTree using `ApiClient`.
    *   The application MUST fetch all parts belonging to InvenTree category ID 191.
    *   The fetched parts list (ID and Name) MUST be stored for use in the input selection.
    *   Appropriate error messages MUST be displayed if fetching fails (e.g., connection error, category not found).
    *   // TEST: Parts from category 191 are fetched successfully
    *   // TEST: Error handling for part fetching works
3.  **User Input (Dynamic):**
    *   The UI MUST allow users to select one or more parts from the fetched list (category 191).
    *   For each selected part, the user MUST be able to specify a desired quantity (positive integer).
    *   A mechanism MUST be provided to add/remove part-quantity rows dynamically (e.g., an "Add Part" button creating a new row with a dropdown and quantity input).
    *   The UI MUST include a "Calculate" button to trigger the order calculation.
    *   // TEST: Dropdown is populated with correct parts
    *   // TEST: User can add multiple part-quantity rows
    *   // TEST: User can input valid quantities
    *   // TEST: Input validation prevents non-positive quantities
4.  **Calculation Process:**
    *   Upon clicking "Calculate", the application MUST gather the selected Part IDs and quantities into a suitable format (e.g., a dictionary `{part_id: quantity}`).
    *   The application MUST instantiate `ApiClient` and `OrderCalculator` using the loaded `AppConfig`.
    *   The application MUST call the `calculator.calculate_orders()` method with the gathered input parts.
    *   // TEST: Input data is correctly parsed before calculation
    *   // TEST: `calculate_orders` is called with correct arguments
5.  **Output Display:**
    *   If the calculation is successful, the application MUST display the results.
    *   Results MUST be presented in two separate `st.tabs`: "Parts to Order" and "Subassemblies to Build".
    *   Each tab MUST display the corresponding data (from `OutputTables`) in a tabular format (`st.dataframe`), matching the columns of the CLI output.
    *   // TEST: Results are displayed in the correct tabs
    *   // TEST: Dataframes display correct data and columns
6.  **Error Handling:**
    *   The application MUST gracefully handle potential errors during configuration loading, API communication (part fetching, calculation), input parsing, or calculation.
    *   Relevant error messages (e.g., "Connection Error", "Part ID not found during calculation", "Invalid input format", "Calculation failed") MUST be displayed clearly to the user (e.g., using `st.error` or `st.warning`).
    *   // TEST: API connection errors are handled and displayed
    *   // TEST: Calculation errors are handled and displayed
7.  **Status Updates:**
    *   The UI SHOULD provide feedback during potentially long operations (e.g., "Fetching parts...", "Calculating...", "Connecting to InvenTree...").

## 3. Non-Functional Requirements

1.  **Usability:** The interface should be intuitive, especially the dynamic input section.
2.  **Responsiveness:** Provide timely feedback, particularly during API calls.
3.  **Maintainability:** Code should be organized, commented, and leverage existing backend components.
4.  **Security:** API token should not be displayed directly in the UI after loading.

## 4. UI Layout and Components (Conceptual)

```
+-----------------------------------------------------+
| Main Area                                           |
| +-------------------------------------------------+ |
| | **Inventree Order Calculator**                  | |
| |                                                 | |
| | Config Status: [Loaded from .env / Error]       | |
| | InvenTree URL: [URL from .env]                  | |
| |                                                 | |
| | **Input Parts (Category 191):**                 | |
| | +---------------------------------------------+ | |
| | | [ Row 1: [Dropdown Part Select] Qty: [Num Input] ] | |
| | | [ Row 2: [Dropdown Part Select] Qty: [Num Input] ] | |
| | | ...                                         | |
| | +---------------------------------------------+ | |
| | [ Add Part Button ]                             | |
| | [ Calculate Button ]                            | |
| |                                                 | |
| | **Results:**                                    | |
| | +---------------------------------------------+ | |
| | | [ Status/Error Message Area ]               | |
| | +---------------------------------------------+ | |
| | | Tabs: [ Parts to Order | Subassemblies ]     | |
| | | +-----------------------------------------+ | |
| | | | [ st.dataframe for Parts ]              | |
| | | | or                                      | |
| | | | [ st.dataframe for Subassemblies ]      | |
| | | +-----------------------------------------+ | |
| | +---------------------------------------------+ | |
| +-------------------------------------------------+ |
+-----------------------------------------------------+
```

## 5. Workflow

1.  **Initialization:**
    *   App starts.
    *   `AppConfig` attempts to load URL/Token from `.env`.
    *   Display config status. If error, stop.
    *   Instantiate `ApiClient`.
    *   Fetch parts from category 191 using `ApiClient`. Store list (e.g., in `st.session_state`). Display error if fetch fails.
2.  **User Interaction:**
    *   Display initial input row (dropdown with fetched parts, quantity input).
    *   User selects part(s) and quantity(ies), potentially adding more rows via "Add Part".
3.  **Calculation Trigger:**
    *   User clicks "Calculate".
4.  **Backend Call:**
    *   Clear previous results/errors.
    *   Display "Calculating..." status.
    *   Parse selected parts and quantities from UI state.
    *   Validate inputs (e.g., quantities > 0). Display error if invalid.
    *   Instantiate `OrderCalculator` with `ApiClient`.
    *   Call `calculator.calculate_orders(parsed_inputs)`.
    *   Handle exceptions from the call, display errors via `st.error`.
5.  **Display Results:**
    *   If calculation successful:
        *   Store results (e.g., `OutputTables` object) in `st.session_state`.
        *   Display "Calculation Complete" status.
        *   Show the results tabs ("Parts to Order", "Subassemblies to Build").
        *   Render the corresponding dataframes within the tabs using the stored results.

## 6. Pseudocode (`streamlit_app.py`)

```python
import streamlit as st
import pandas as pd
from inventree_order_calculator.config import AppConfig
from inventree_order_calculator.api_client import ApiClient
from inventree_order_calculator.calculator import OrderCalculator
from inventree_order_calculator.models import OutputTables # Assuming models are accessible

# --- Constants ---
TARGET_CATEGORY_ID = 191

# --- Helper Functions ---

# // TEST: test_parse_inputs_valid
# // TEST: test_parse_inputs_invalid_quantity
# // TEST: test_parse_inputs_no_selection
FUNCTION parse_dynamic_inputs(input_rows_state):
    """ Parses the part selections and quantities from Streamlit state """
    parts_to_calculate = {}
    is_valid = True
    errors = []
    FOR row_index, row_data IN enumerate(input_rows_state):
        part_id = row_data['selected_part_id']
        quantity = row_data['quantity']
        IF part_id IS NOT None AND quantity IS NOT None:
            TRY
                qty_int = int(quantity)
                IF qty_int <= 0:
                    is_valid = False
                    errors.append(f"Row {row_index + 1}: Quantity must be positive.")
                ELSE:
                    IF part_id IN parts_to_calculate:
                        # Handle duplicate part selection if necessary (e.g., sum quantities or raise error)
                        parts_to_calculate[part_id] += qty_int # Example: Summing
                    ELSE:
                        parts_to_calculate[part_id] = qty_int
            EXCEPT ValueError:
                is_valid = False
                errors.append(f"Row {row_index + 1}: Invalid quantity '{quantity}'.")
        # Optional: Add validation for rows where only one field is filled
    RETURN parts_to_calculate, is_valid, errors

# // TEST: test_fetch_parts_success (requires mocking ApiClient)
# // TEST: test_fetch_parts_api_error (requires mocking ApiClient)
FUNCTION fetch_category_parts(api_client, category_id):
    """ Fetches parts from a specific category using the ApiClient """
    TRY
        # Assuming ApiClient has a method like get_parts_by_category
        parts_data = api_client.get_parts_by_category(category_id)
        # Format for dropdown: list of tuples or dict {name: id}
        # Example: [(part['name'], part['pk']) for part in parts_data]
        formatted_parts = {part['name']: part['pk'] for part in parts_data} # Name -> ID mapping
        RETURN formatted_parts, None # parts_dict, error
    EXCEPT Exception as e:
        RETURN None, f"Error fetching parts: {e}"

# --- Streamlit App ---

st.title("Inventree Order Calculator")

# --- Initialization and State ---
IF 'config' NOT IN st.session_state:
    st.session_state.config = None
IF 'api_client' NOT IN st.session_state:
    st.session_state.api_client = None
IF 'category_parts' NOT IN st.session_state: # Dict {name: id}
    st.session_state.category_parts = None
IF 'parts_fetch_error' NOT IN st.session_state:
    st.session_state.parts_fetch_error = None
IF 'calculation_results' NOT IN st.session_state: # OutputTables object
    st.session_state.calculation_results = None
IF 'calculation_error' NOT IN st.session_state:
    st.session_state.calculation_error = None
IF 'input_rows' NOT IN st.session_state:
    # List of dictionaries, each representing a row
    # e.g., [{'id': 0, 'selected_part_name': None, 'selected_part_id': None, 'quantity': 1}]
    st.session_state.input_rows = [{'id': 0, 'selected_part_name': None, 'selected_part_id': None, 'quantity': 1}]
IF 'next_row_id' NOT IN st.session_state:
    st.session_state.next_row_id = 1

# --- Configuration Loading ---
IF st.session_state.config IS None:
    TRY:
        st.session_state.config = AppConfig() # Loads from .env
        st.success("Configuration loaded successfully from .env.")
        st.info(f"InvenTree URL: {st.session_state.config.inventree_url}")
        # Don't display token
        st.session_state.api_client = ApiClient(st.session_state.config)
    EXCEPT Exception as e:
        st.error(f"Failed to load configuration from .env: {e}")
        st.stop() # Stop execution if config fails

# --- Fetch Category Parts ---
IF st.session_state.api_client AND st.session_state.category_parts IS None AND st.session_state.parts_fetch_error IS None:
    WITH st.spinner(f"Fetching parts from category {TARGET_CATEGORY_ID}..."):
        parts_dict, error = fetch_category_parts(st.session_state.api_client, TARGET_CATEGORY_ID)
        IF error:
            st.session_state.parts_fetch_error = error
            st.error(error)
        ELSE:
            st.session_state.category_parts = parts_dict
            IF not parts_dict:
                 st.warning(f"No parts found in category {TARGET_CATEGORY_ID}.")
            # Force rerun to update UI now that parts are loaded
            st.rerun()

# --- Display Fetch Error ---
IF st.session_state.parts_fetch_error:
    st.error(st.session_state.parts_fetch_error)
    st.stop() # Stop if parts can't be fetched

# --- Dynamic Input Section ---
st.subheader("Input Parts (Category 191)")

IF st.session_state.category_parts IS NOT None:
    IF not st.session_state.category_parts:
        st.warning(f"Cannot add parts: No parts found in category {TARGET_CATEGORY_ID}.")
    ELSE:
        # Prepare list for dropdown (add a placeholder)
        part_names_list = ["-- Select Part --"] + list(st.session_state.category_parts.keys())

        # Render existing rows
        indices_to_remove = []
        for i, row in enumerate(st.session_state.input_rows):
            cols = st.columns([3, 1, 1]) # Adjust column ratios as needed
            with cols[0]:
                # Use unique key for each widget based on row id
                selected_name = st.selectbox(
                    f"Part##{row['id']}",
                    options=part_names_list,
                    index=part_names_list.index(row['selected_part_name']) if row['selected_part_name'] in part_names_list else 0,
                    label_visibility="collapsed"
                )
                # Update state if selection changed
                if selected_name != row['selected_part_name']:
                    st.session_state.input_rows[i]['selected_part_name'] = selected_name
                    if selected_name == "-- Select Part --":
                         st.session_state.input_rows[i]['selected_part_id'] = None
                    else:
                         st.session_state.input_rows[i]['selected_part_id'] = st.session_state.category_parts[selected_name]
                    st.rerun() # Rerun to reflect potential changes

            with cols[1]:
                quantity = st.number_input(
                    f"Quantity##{row['id']}",
                    min_value=1,
                    value=st.session_state.input_rows[i]['quantity'],
                    step=1,
                    label_visibility="collapsed"
                )
                # Update state if quantity changed
                if quantity != st.session_state.input_rows[i]['quantity']:
                    st.session_state.input_rows[i]['quantity'] = quantity
                    # No rerun needed for number input usually

            with cols[2]:
                 # Add remove button only if more than one row exists
                 if len(st.session_state.input_rows) > 1:
                     if st.button(f"Remove##{row['id']}", key=f"remove_{row['id']}"):
                         indices_to_remove.append(i)


        # Process removals after iterating
        if indices_to_remove:
            # Remove items in reverse order to avoid index shifting issues
            for index in sorted(indices_to_remove, reverse=True):
                del st.session_state.input_rows[index]
            st.rerun()

        # Add "Add Part" button
        if st.button("Add Part"):
            new_row_id = st.session_state.next_row_id
            st.session_state.input_rows.append({
                'id': new_row_id,
                'selected_part_name': None,
                'selected_part_id': None,
                'quantity': 1
            })
            st.session_state.next_row_id += 1
            st.rerun()

        # --- Calculate Button ---
        if st.button("Calculate"):
            st.session_state.calculation_results = None # Clear previous results
            st.session_state.calculation_error = None   # Clear previous errors

            parts_to_calc, is_valid, errors = parse_dynamic_inputs(st.session_state.input_rows)

            if not is_valid:
                st.session_state.calculation_error = "Input Error(s):\n" + "\n".join(errors)
            elif not parts_to_calc:
                 st.session_state.calculation_error = "Input Error: No parts selected or quantities provided."
            else:
                # // TEST: test_calculate_button_success (mock Calculator)
                # // TEST: test_calculate_button_api_error (mock Calculator)
                # // TEST: test_calculate_button_calc_error (mock Calculator)
                WITH st.spinner("Calculating required orders..."):
                    TRY:
                        calculator = OrderCalculator(st.session_state.api_client)
                        results = calculator.calculate_orders(parts_to_calc)
                        st.session_state.calculation_results = results
                        st.success("Calculation complete!")
                    EXCEPT Exception as e:
                        st.session_state.calculation_error = f"Calculation failed: {e}"

            # Rerun to display results or errors
            st.rerun()

ELSE:
    st.info("Waiting for parts list to load...")


# --- Display Errors / Results ---
st.subheader("Results")

# Display calculation error if it occurred
if st.session_state.calculation_error:
    st.error(st.session_state.calculation_error)

# Display results if available
if st.session_state.calculation_results:
    results = st.session_state.calculation_results
    tab1, tab2 = st.tabs(["Parts to Order", "Subassemblies to Build"])

    with tab1:
        st.write("Parts required from suppliers:")
        # // TEST: test_display_parts_dataframe
        IF results.parts_to_order IS NOT None AND NOT results.parts_to_order.empty:
            st.dataframe(results.parts_to_order)
        ELSE:
            st.info("No external parts need to be ordered.")

    with tab2:
        st.write("Subassemblies that need to be built:")
        # // TEST: test_display_subassemblies_dataframe
        IF results.subassemblies_to_build IS NOT None AND NOT results.subassemblies_to_build.empty:
            st.dataframe(results.subassemblies_to_build)
        ELSE:
            st.info("No subassemblies need to be built.")

```

## 7. TDD Anchors (Conceptual & Pseudocode)

Testing Streamlit apps directly can be complex due to their execution model. The focus should be on testing the helper functions and the logic within the main script flow where possible, potentially by mocking Streamlit functions and backend classes.

-   **`parse_dynamic_inputs(input_rows_state)`:**
    -   `// TEST: test_parse_inputs_valid`: Provide sample valid state, check output dict.
    -   `// TEST: test_parse_inputs_invalid_quantity`: Include rows with 0 or negative qty, check `is_valid` is False and errors list.
    -   `// TEST: test_parse_inputs_no_selection`: Provide state with default/unselected parts, check output dict is empty or handles appropriately.
    -   `// TEST: test_parse_inputs_duplicate_parts`: Provide state with same part selected twice, check if quantities are summed (or error raised, depending on desired logic).
-   **`fetch_category_parts(api_client, category_id)`:**
    -   `// TEST: test_fetch_parts_success`: Mock `api_client.get_parts_by_category` to return sample data, verify correct formatting of output dict.
    -   `// TEST: test_fetch_parts_api_error`: Mock `api_client.get_parts_by_category` to raise an exception, verify error string is returned.
-   **Calculation Logic (within "Calculate" button block):**
    -   `// TEST: test_calculate_button_success`: Mock `OrderCalculator`, `parse_dynamic_inputs`. Simulate button click, verify `calculator.calculate_orders` is called with correct args and results are stored in `st.session_state`. Mock `st.success`.
    -   `// TEST: test_calculate_button_api_error`: Mock `OrderCalculator` to raise an API-related exception during `calculate_orders`. Verify error is caught and stored in `st.session_state.calculation_error`. Mock `st.error`.
    -   `// TEST: test_calculate_button_calc_error`: Mock `OrderCalculator` to raise a different exception. Verify error handling.
    -   `// TEST: test_calculate_button_invalid_input`: Simulate invalid input state, verify `parse_dynamic_inputs` catches it and error is displayed without calling calculator.
-   **Display Logic (within Results section):**
    -   `// TEST: test_display_parts_dataframe`: Set `st.session_state.calculation_results` with sample `OutputTables` containing parts data. Mock `st.dataframe`, verify it's called with the correct DataFrame.
    -   `// TEST: test_display_subassemblies_dataframe`: Similar test for subassemblies tab.
    -   `// TEST: test_display_no_results`: Set `st.session_state.calculation_results` with empty DataFrames, verify `st.info` messages are shown.

**Note:** Actual implementation of these tests might involve libraries like `pytest-mock` and potentially Streamlit testing frameworks if available/mature, or structuring the app to further isolate testable logic.

## 8. Monitoring Task Management UI (New Section)

This section details the UI for managing automated monitoring tasks, interacting with `PresetsManager`.

### 8.1. Functional Requirements

1.  **Display Monitoring Tasks:**
    *   A new tab or expandable section titled "Monitoring Tasks" MUST be available.
    *   It MUST display a table of all configured monitoring tasks from `presets.json` (via `PresetsManager.get_monitoring_lists()`).
    *   The table MUST show: ID, Name, Active status, Cron Schedule, Recipients, Notify Condition.
    *   Each row MUST have buttons/icons for "Edit", "Delete", "Activate/Deactivate", and "Run Manually".
    *   // TEST: streamlit_ui_can_display_monitoring_tasks
2.  **Add New Monitoring Task:**
    *   A button "Add New Monitoring Task" MUST be present.
    *   Clicking it SHOULD show a form (e.g., in `st.form` or a modal/expander).
    *   **Form Fields:**
        *   Task Name (text input, required)
        *   Parts (dynamic list of inputs, similar to main calculator but for `MonitoringPartItem`: Part Name (text input), Quantity (number input), Version (text input, optional)).
        *   Cron Schedule (text input, required, with placeholder/example)
        *   Recipients (text input, comma-separated emails, required)
        *   Notify Condition (selectbox: "on_change", "always", default "on_change")
        *   Active (checkbox, default true)
    *   On submission, the new task data MUST be validated.
    *   The new task MUST be saved using `PresetsManager.add_monitoring_list()`.
    *   The task list display MUST refresh.
    *   // TEST: streamlit_ui_can_create_new_monitoring_task_valid_data
    *   // TEST: streamlit_ui_create_task_handles_invalid_cron
    *   // TEST: streamlit_ui_create_task_handles_invalid_email_format (basic client-side or rely on backend)
    *   // TEST: streamlit_ui_create_task_requires_name_parts_schedule_recipients
3.  **Edit Existing Monitoring Task:**
    *   Clicking "Edit" on a task row SHOULD populate a similar form with the existing task's data.
    *   The Task ID SHOULD be displayed but not editable.
    *   On submission, changes MUST be saved using `PresetsManager.update_monitoring_list()`.
    *   The task list display MUST refresh.
    *   // TEST: streamlit_ui_can_edit_monitoring_task_loads_data
    *   // TEST: streamlit_ui_can_edit_monitoring_task_saves_changes
4.  **Delete Monitoring Task:**
    *   Clicking "Delete" on a task row SHOULD prompt for confirmation (e.g., `st.confirm_button` or a modal).
    *   On confirmation, the task MUST be deleted using `PresetsManager.delete_monitoring_list()`.
    *   The task list display MUST refresh.
    *   // TEST: streamlit_ui_can_delete_monitoring_task_with_confirmation
5.  **Activate/Deactivate Monitoring Task:**
    *   A toggle switch or button ("Activate"/"Deactivate") MUST be available for each task.
    *   Clicking it MUST update the `active` status of the task using `PresetsManager.update_monitoring_list()`.
    *   The display of the task's active status MUST refresh.
    *   // TEST: streamlit_ui_can_activate_task
    *   // TEST: streamlit_ui_can_deactivate_task
6.  **Run Monitoring Task Manually:**
    *   Clicking "Run Manually" SHOULD trigger the immediate execution of that specific monitoring task.
    *   This will involve calling a function similar to `MonitoringTaskManager.run_task_manually(task_id)`.
    *   Feedback (e.g., "Task [Name] triggered manually. Check logs/email.") SHOULD be displayed.
    *   // TEST: streamlit_ui_can_trigger_manual_run

### 8.2. UI Layout and Components (Conceptual for Monitoring)

```
+-----------------------------------------------------+
| Sidebar (Optional Navigation)                       |
| [ Calculator ]                                      |
| [ Monitoring Tasks ] <-- New Navigation Item        |
+-----------------------------------------------------+
| Main Area (If "Monitoring Tasks" selected)          |
| +-------------------------------------------------+ |
| | **Monitoring Task Management**                  | |
| |                                                 | |
| | [ Add New Monitoring Task Button ]              | |
| |                                                 | |
| | +---------------------------------------------+ | |
| | | Monitoring Task Table (st.dataframe or custom)| |
| | | | ID | Name | Active | Schedule | Actions   | | |
| | | +--+----+--------+----------+-----------+ | |
| | | |..|....| [Toggle] | ........ | [Edit][Del]| | |
| | | |..|....| [Toggle] | ........ | [Run][Edit]| | |
| | +---------------------------------------------+ | |
| |                                                 | |
| | --- Form for Add/Edit Task (shown conditionally) --- | |
| | | Name: [Text Input]                          | |
| | | Parts:                                      | |
| | |   [ Part Name | Qty | Version (opt) ] [Add] | |
| | |   [ ................................. ]     | |
| | | Cron: [Text Input]                          | |
| | | Recipients: [Text Input (comma-sep)]        | |
| | | Notify: [SelectBox: on_change/always]       | |
| | | Active: [Checkbox]                          | |
| | | [ Save Task Button ] [ Cancel Button ]       | |
| | +---------------------------------------------+ | |
| +-------------------------------------------------+ |
+-----------------------------------------------------+
```

### 8.3. Pseudocode (`streamlit_app.py` - Additions for Monitoring)

```python
# --- Additions to Streamlit App for Monitoring ---

# Import PresetsManager and MonitoringList model (adjust path as needed)
# from inventree_order_calculator.presets_manager import PresetsManager, MonitoringList # Assuming direct class/func access
# from inventree_order_calculator.models import MonitoringPartItem # If not already imported

# --- Add to Initialization and State ---
IF 'monitoring_tasks' NOT IN st.session_state:
    st.session_state.monitoring_tasks = [] # List of MonitoringList objects
IF 'editing_task_id' NOT IN st.session_state: # ID of task being edited, or None for new
    st.session_state.editing_task_id = None
IF 'show_monitoring_form' NOT IN st.session_state:
    st.session_state.show_monitoring_form = False
# Add state for form inputs if managing them directly in session_state
IF 'monitor_form_name' NOT IN st.session_state: st.session_state.monitor_form_name = ""
# ... other form fields ...
IF 'monitor_form_parts' NOT IN st.session_state: st.session_state.monitor_form_parts = [{'name': '', 'quantity': 1, 'version': ''}]


# --- Helper Function to Load Monitoring Tasks ---
# // TEST: test_load_monitoring_tasks_success
# // TEST: test_load_monitoring_tasks_file_not_found (handled by PresetsManager)
FUNCTION load_monitoring_tasks_from_presets():
    TRY:
        # Assumes PresetsManager is set up to load from the correct file
        presets_file = PresetsManager.load_presets_from_file(PresetsManager.get_presets_filepath())
        st.session_state.monitoring_tasks = PresetsManager.get_monitoring_lists(presets_file)
    EXCEPT Exception as e:
        st.error(f"Error loading monitoring tasks: {e}")
        st.session_state.monitoring_tasks = []


# --- Main App Structure Modification ---
# Consider using a sidebar for navigation or top-level tabs if the UI grows.
# For simplicity, could be a separate section on the main page or an expander.

# Example: Adding a new section/page for Monitoring
st.sidebar.title("Navigation")
app_mode = st.sidebar.selectbox("Choose Mode", ["Order Calculator", "Monitoring Tasks"])

IF app_mode == "Order Calculator":
    # ... existing calculator UI code ...
    pass # Placeholder for existing UI

ELIF app_mode == "Monitoring Tasks":
    render_monitoring_ui()


FUNCTION render_monitoring_ui():
    st.title("Monitoring Task Management")

    # Load tasks if not already loaded or if a refresh is needed
    # This might be called more strategically (e.g., after save/delete)
    IF not st.session_state.monitoring_tasks: # Initial load
        load_monitoring_tasks_from_presets()

    # --- Display Add/Edit Form ---
    if st.button("➕ Add New Monitoring Task"):
        st.session_state.editing_task_id = None # Signal new task
        st.session_state.show_monitoring_form = True
        # Reset form fields for new task
        st.session_state.monitor_form_name = ""
        st.session_state.monitor_form_parts = [{'id': 0, 'name': '', 'quantity': 1, 'version': ''}] # Use unique IDs for dynamic rows
        st.session_state.monitor_form_cron = "0 * * * *"
        st.session_state.monitor_form_recipients = ""
        st.session_state.monitor_form_notify_condition = "on_change"
        st.session_state.monitor_form_active = True
        st.rerun()


    IF st.session_state.show_monitoring_form:
        render_monitoring_task_form()

    # --- Display Monitoring Tasks Table ---
    st.subheader("Configured Monitoring Tasks")
    IF not st.session_state.monitoring_tasks:
        st.info("No monitoring tasks configured yet.")
    ELSE:
        # Use st.columns to create a table-like layout or st.dataframe
        # For actions, st.columns within the loop is common.
        header_cols = st.columns([1, 2, 1, 2, 3, 1, 3]) # ID, Name, Active, Cron, Recipients, Notify, Actions
        header_cols[0].write("**ID**")
        header_cols[1].write("**Name**")
        header_cols[2].write("**Active**")
        header_cols[3].write("**Cron Schedule**")
        header_cols[4].write("**Recipients**")
        header_cols[5].write("**Notify**")
        header_cols[6].write("**Actions**")

        FOR task IN st.session_state.monitoring_tasks:
            row_cols = st.columns([1, 2, 1, 2, 3, 1, 3])
            row_cols[0].text(task.id[:8] + "...") # Shortened ID
            row_cols[1].text(task.name)
            
            # Active Toggle
            current_active_status = task.active
            new_active_status = row_cols[2].checkbox(" ", value=current_active_status, key=f"active_{task.id}", label_visibility="collapsed")
            IF new_active_status != current_active_status:
                handle_activate_deactivate_task(task.id, new_active_status)
                # st.rerun() # Handled by handle_activate_deactivate_task

            row_cols[3].text(task.cron_schedule)
            row_cols[4].text(", ".join(task.recipients))
            row_cols[5].text(task.notify_condition)

            action_col = row_cols[6]
            sub_action_cols = action_col.columns(4) # Run, Edit, Delete
            if sub_action_cols[0].button("▶️ Run", key=f"run_{task.id}", help="Run Manually"):
                handle_manual_run_task(task.id)
            if sub_action_cols[1].button("✏️ Edit", key=f"edit_{task.id}"):
                st.session_state.editing_task_id = task.id
                st.session_state.show_monitoring_form = True
                # Populate form fields with task data
                st.session_state.monitor_form_name = task.name
                st.session_state.monitor_form_parts = [{'id': i, 'name': p.name, 'quantity': p.quantity, 'version': p.version or ''} for i, p in enumerate(task.parts)]
                st.session_state.monitor_form_cron = task.cron_schedule
                st.session_state.monitor_form_recipients = ", ".join(task.recipients)
                st.session_state.monitor_form_notify_condition = task.notify_condition
                st.session_state.monitor_form_active = task.active
                st.rerun()
            if sub_action_cols[2].button("🗑️ Delete", key=f"delete_{task.id}"):
                # Confirmation could be added here
                handle_delete_task(task.id)
            # Activate/Deactivate handled by checkbox directly for simplicity here
            # Or could be a separate button:
            # label = "Deactivate" if task.active else "Activate"
            # if sub_action_cols[3].button(label, key=f"toggle_active_{task.id}"):
            #    handle_activate_deactivate_task(task.id, not task.active)


FUNCTION render_monitoring_task_form():
    # // TEST: streamlit_ui_form_populates_for_edit
    # // TEST: streamlit_ui_form_is_blank_for_new
    form_title = "Edit Monitoring Task" if st.session_state.editing_task_id else "Add New Monitoring Task"
    
    with st.expander(form_title, expanded=True): # Or use st.form
      with st.form(key="monitoring_task_form", clear_on_submit=True):
        st.text_input("Task Name", key="monitor_form_name_input", value=st.session_state.monitor_form_name) # Use distinct keys for form inputs
        
        st.subheader("Parts to Monitor")
        # Dynamic part input for monitoring tasks
        # This is a simplified version. A robust implementation would use unique keys for each part row.
        # For each part in st.session_state.monitor_form_parts:
        #   cols = st.columns([2,1,1,1])
        #   cols[0].text_input("Part Name", value=part['name'], key=f"part_name_{part['id']}")
        #   cols[1].number_input("Quantity", value=part['quantity'], min_value=1, key=f"part_qty_{part['id']}")
        #   cols[2].text_input("Version (Optional)", value=part['version'], key=f"part_ver_{part['id']}")
        #   cols[3].button("Remove Part", key=f"remove_part_{part['id']}") # Needs handler
        # st.button("Add Monitoring Part") # Needs handler to append to st.session_state.monitor_form_parts

        # Placeholder for parts input - this needs to be made dynamic like the main calculator's input
        st.text_area("Parts (JSON/CSV format for now - UI needs dynamic rows)",
                      value=convert_parts_to_string(st.session_state.monitor_form_parts),
                      key="monitor_form_parts_text_area",
                      help="Example: [{'name': 'PartA', 'quantity': 10, 'version': 'v1'}, {'name': 'PartB', 'quantity': 5}]")


        st.text_input("Cron Schedule", key="monitor_form_cron_input", value=st.session_state.monitor_form_cron)
        st.text_input("Recipients (comma-separated)", key="monitor_form_recipients_input", value=st.session_state.monitor_form_recipients)
        st.selectbox("Notify Condition", options=["on_change", "always"],
                     index=["on_change", "always"].index(st.session_state.monitor_form_notify_condition),
                     key="monitor_form_notify_condition_select")
        st.checkbox("Active", key="monitor_form_active_checkbox", value=st.session_state.monitor_form_active)

        submitted = st.form_submit_button("Save Task")

        if submitted:
            # Retrieve values from form input keys
            name = st.session_state.monitor_form_name_input # Example, actual keys from st.text_input etc.
            # parts_data = parse_parts_from_string(st.session_state.monitor_form_parts_text_area) # Needs implementation
            parts_data_raw = json.loads(st.session_state.monitor_form_parts_text_area) # Basic parsing for now
            parts_data = [MonitoringPartItem(**p) for p in parts_data_raw]

            cron = st.session_state.monitor_form_cron_input
            recipients = [r.strip() for r in st.session_state.monitor_form_recipients_input.split(',') if r.strip()]
            notify = st.session_state.monitor_form_notify_condition_select
            active = st.session_state.monitor_form_active_checkbox
            
            # Basic Validation
            if not name or not parts_data or not cron or not recipients:
                st.error("Name, Parts, Cron Schedule, and Recipients are required.")
            else:
                task_payload = {
                    "name": name, "parts": parts_data, "cron_schedule": cron,
                    "recipients": recipients, "notify_condition": notify, "active": active
                }
                handle_save_monitoring_task(task_payload)
                st.session_state.show_monitoring_form = False # Close form on save
                st.rerun()
        
      if st.button("Cancel"):
          st.session_state.show_monitoring_form = False
          st.rerun()


FUNCTION convert_parts_to_string(parts_list_of_dicts):
    # Helper to display parts in text area for now
    TRY
        RETURN json.dumps(parts_list_of_dicts, indent=2)
    EXCEPT:
        RETURN "[]"

# --- Handler Functions for Monitoring UI Actions ---
FUNCTION handle_save_monitoring_task(task_data_dict): # task_data_dict has 'name', 'parts' (list of MonitoringPartItem), etc.
    # // TEST: streamlit_ui_save_new_task_calls_presets_manager
    # // TEST: streamlit_ui_save_edited_task_calls_presets_manager
    presets_file = PresetsManager.load_presets_from_file(PresetsManager.get_presets_filepath())
    task_id_to_save = st.session_state.editing_task_id

    # Convert parts from MonitoringPartItem objects to dicts if PresetsManager expects dicts
    task_data_dict["parts"] = [p.model_dump() for p in task_data_dict["parts"]]


    TRY:
        if task_id_to_save: # Update existing
            updated_presets = PresetsManager.update_monitoring_list(presets_file, task_id_to_save, task_data_dict)
        else: # Add new
            # ID is generated by add_monitoring_list if not in task_data_dict
            updated_presets = PresetsManager.add_monitoring_list(presets_file, task_data_dict)
        
        PresetsManager.save_presets_to_file(PresetsManager.get_presets_filepath(), updated_presets)
        st.success(f"Monitoring task '{task_data_dict['name']}' saved successfully.")
        load_monitoring_tasks_from_presets() # Refresh list
        # TODO: Notify backend scheduler if running as separate service
    EXCEPT Exception as e:
        st.error(f"Error saving monitoring task: {e}")
    st.session_state.editing_task_id = None # Reset editing state


FUNCTION handle_delete_task(task_id):
    # // TEST: streamlit_ui_delete_task_calls_presets_manager
    presets_file = PresetsManager.load_presets_from_file(PresetsManager.get_presets_filepath())
    TRY:
        updated_presets = PresetsManager.delete_monitoring_list(presets_file, task_id)
        if updated_presets is not presets_file: # Check if a change was made
            PresetsManager.save_presets_to_file(PresetsManager.get_presets_filepath(), updated_presets)
            st.success(f"Monitoring task {task_id} deleted.")
            load_monitoring_tasks_from_presets() # Refresh list
            # TODO: Notify backend scheduler
            st.rerun()
        else:
            st.warning(f"Task {task_id} not found for deletion.")
    EXCEPT Exception as e:
        st.error(f"Error deleting task {task_id}: {e}")

FUNCTION handle_activate_deactivate_task(task_id, new_active_status):
    # // TEST: streamlit_ui_activate_deactivate_calls_presets_manager
    presets_file = PresetsManager.load_presets_from_file(PresetsManager.get_presets_filepath())
    TRY:
        updated_presets = PresetsManager.update_monitoring_list(presets_file, task_id, {"active": new_active_status})
        if updated_presets is not presets_file:
            PresetsManager.save_presets_to_file(PresetsManager.get_presets_filepath(), updated_presets)
            status_text = "activated" if new_active_status else "deactivated"
            st.success(f"Task {task_id} {status_text}.")
            load_monitoring_tasks_from_presets() # Refresh list
            # TODO: Notify backend scheduler
            st.rerun() # Rerun to reflect change immediately in UI
        else:
            st.warning(f"Task {task_id} not found for activation/deactivation.")
    EXCEPT Exception as e:
        st.error(f"Error updating task {task_id} status: {e}")


FUNCTION handle_manual_run_task(task_id):
    # // TEST: streamlit_ui_manual_run_calls_monitoring_task_manager
    st.info(f"Attempting to manually run task {task_id}...")
    TRY:
        # This assumes MonitoringTaskManager is accessible and initialized
        # This is a simplification for UI spec; actual implementation might differ
        # based on how CLI and service components are structured/shared.
        # MonitoringTaskManager.initialize_if_needed() # Conceptual
        MonitoringTaskManager.run_task_manually(task_id)
        st.success(f"Manual run for task {task_id} initiated. Check logs/email for results.")
    EXCEPT Exception as e:
        st.error(f"Failed to manually run task {task_id}: {e}")

```

### 8.4. TDD Anchors (Conceptual for Monitoring UI)

-   **Loading Tasks:**
    -   `// TEST: streamlit_ui_loads_and_displays_monitoring_tasks`: Mock `PresetsManager.get_monitoring_lists`, verify table/rows rendered.
    -   `// TEST: streamlit_ui_handles_no_monitoring_tasks`: Mock `PresetsManager.get_monitoring_lists` to return empty, verify "No tasks" message.
-   **Form Handling (Add/Edit):**
    -   `// TEST: streamlit_ui_add_task_form_opens_blank`: Check form fields are empty/default when "Add" is clicked.
    -   `// TEST: streamlit_ui_edit_task_form_populates_data`: Mock task data, click "Edit", verify form fields are populated.
    -   `// TEST: streamlit_ui_save_new_task_validates_input`: Test with missing required fields, verify error messages.
    -   `// TEST: streamlit_ui_save_new_task_calls_presets_manager`: Valid input, mock `PresetsManager.add_monitoring_list`, verify it's called.
    -   `// TEST: streamlit_ui_save_edited_task_calls_presets_manager`: Valid input, mock `PresetsManager.update_monitoring_list`, verify.
-   **Actions:**
    -   `// TEST: streamlit_ui_delete_task_shows_confirmation_and_calls_presets_manager`: Mock `PresetsManager.delete_monitoring_list`.
    -   `// TEST: streamlit_ui_activate_deactivate_updates_status_and_calls_presets_manager`: Mock `PresetsManager.update_monitoring_list`.
    -   `// TEST: streamlit_ui_manual_run_shows_feedback_and_calls_task_manager`: Mock `MonitoringTaskManager.run_task_manually`.

**Note:** The dynamic parts input for the monitoring task form is simplified in the pseudocode (using a text area for JSON). A production UI would implement dynamic row addition/removal for parts similar to the main calculator's input section, but tailored for `MonitoringPartItem` fields (Name, Quantity, Version). The TDD anchors assume such a richer implementation.
The interaction with `MonitoringTaskManager.run_task_manually` from Streamlit assumes that the task manager's logic can be invoked from the Streamlit process. If the monitoring service runs as a completely separate daemon, IPC or an API call to the service would be needed.