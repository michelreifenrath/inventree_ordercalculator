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