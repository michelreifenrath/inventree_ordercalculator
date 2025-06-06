import streamlit as st
import pandas as pd
from typing import Dict, Any, Tuple, Optional, List
from urllib.parse import quote
import logging
from pathlib import Path

# Assuming these modules are structured correctly relative to the execution path
# If running with `uv run streamlit run src/inventree_order_calculator/streamlit_app.py`
# from the project root, these imports should work.
try:
    # Use absolute imports based on the package name
    from inventree_order_calculator.config import AppConfig, ConfigError
    from inventree_order_calculator.api_client import ApiClient
    from inventree_order_calculator.calculator import OrderCalculator
    from inventree_order_calculator.models import OutputTables, InputPart, BuildingCalculationMethod # Add BuildingCalculationMethod import
    from inventree_order_calculator.presets_manager import (
        load_presets_from_file,
        save_presets_to_file,
        add_or_update_preset,
        delete_preset_by_name,
        get_preset_names,
        get_preset_by_name,
        Preset,
        PresetItem,
        PresetsFile,
        PRESETS_FILE_PATH as DEFAULT_PRESETS_FILE_PATH
    )
except ImportError as e:
    st.error(f"Error importing project modules: {e}. "
             "Ensure the script is run from the project root using "
             "`uv run streamlit run src/inventree_order_calculator/streamlit_app.py` "
             "or adjust Python path.")
    st.stop()

# --- Logging Setup ---
# Configure logging level and format
logging.basicConfig(
    level=logging.WARNING, # Set default level to WARNING
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
logger.info("Streamlit app script started/reloaded.")


# --- Constants ---
TARGET_CATEGORY_ID = 191 # As specified in the requirements
PRESETS_FILE_PATH = DEFAULT_PRESETS_FILE_PATH # Use the path from presets_manager

# --- Helper Functions ---

def convert_input_rows_to_preset_items(input_rows_state: List[Dict[str, Any]]) -> Tuple[List[PresetItem], List[str]]:
    """Converts the app's input_rows state to a list of PresetItem objects."""
    preset_items: List[PresetItem] = []
    errors: List[str] = []

    if not input_rows_state:
        errors.append("No input rows to save as preset.")
        return preset_items, errors

    for i, row_data in enumerate(input_rows_state):
        part_id = row_data.get('selected_part_id')
        quantity = row_data.get('quantity')
        part_name = row_data.get('selected_part_name', f"Row {i+1}") # Default name for error

        if part_id is not None: # A part has been selected
            if quantity is None:
                errors.append(f"'{part_name}': Quantity not provided.")
                continue
            try:
                qty_int = int(quantity)
                if qty_int <= 0:
                    errors.append(f"'{part_name}': Quantity must be positive (got {qty_int}).")
                else:
                    # Ensure part_id is stored as it is (could be int or str from selectbox)
                    preset_items.append(PresetItem(part_id=part_id, quantity=qty_int))
            except ValueError:
                errors.append(f"'{part_name}': Invalid quantity '{quantity}'. Must be a whole number.")
            except TypeError:
                errors.append(f"'{part_name}': Invalid quantity type '{type(quantity)}'. Must be a whole number.")
        # Silently skip rows where no part is selected, as they are not part of the "set"
    
    if not preset_items and not errors: 
        if any(row.get('selected_part_id') is not None for row in input_rows_state): 
             pass 
        elif input_rows_state: 
            errors.append("No parts selected in any input row to save.")


    return preset_items, errors

def populate_input_rows_from_preset_items(
    items: List[PresetItem], 
    category_parts_lookup: Dict[Any, str], # {id: name} or {str_id: name}
    current_next_row_id: int
) -> Tuple[List[Dict[str, Any]], int, List[str]]:
    """
    Converts a list of PresetItem objects to the app's input_rows state.
    category_parts_lookup: A dictionary mapping part_id (int or str) to part_name.
    Returns the new input_rows list, the next_row_id, and any warnings.
    """
    new_input_rows: List[Dict[str, Any]] = []
    warnings: List[str] = []
    next_row_id = current_next_row_id

    if not items:
        new_input_rows.append({
            'id': next_row_id,
            'selected_part_name': None,
            'selected_part_id': None,
            'quantity': 1
        })
        next_row_id +=1
        return new_input_rows, next_row_id, warnings

    for item in items:
        # PresetItem.part_id can be int or str. category_parts_lookup keys are part_names (str), values are part_ids (int).
        # We need to find the name for a given ID.
        part_name_found = None
        # category_parts (from session state) is {name: id}
        # We need to iterate to find the name for the item.part_id
        for name, cat_part_id in st.session_state.category_parts.items():
            if cat_part_id == item.part_id: # item.part_id could be int or str, cat_part_id is likely int
                part_name_found = name
                break
            # Fallback for string comparison if part_id was stored as string in preset
            elif str(cat_part_id) == str(item.part_id):
                part_name_found = name
                break
        
        if part_name_found:
            new_input_rows.append({
                'id': next_row_id,
                'selected_part_name': part_name_found,
                'selected_part_id': item.part_id, 
                'quantity': item.quantity
            })
        else:
            warnings.append(f"Part ID '{item.part_id}' from preset not found in current category parts. Skipping.")
        next_row_id += 1
    
    if not new_input_rows:
        new_input_rows.append({
            'id': next_row_id,
            'selected_part_name': None,
            'selected_part_id': None,
            'quantity': 1
        })
        next_row_id +=1
        if not warnings: 
            warnings.append("No items from the preset could be loaded as they are not in the current category parts list.")

    return new_input_rows, next_row_id, warnings


def parse_dynamic_inputs(input_rows_state: List[Dict[str, Any]]) -> Tuple[Dict[int, int], bool, List[str]]:
    """ Parses the part selections and quantities from Streamlit state """
    parts_to_calculate: Dict[int, int] = {} # part_id here should be int for calculator
    is_valid = True
    errors: List[str] = []

    if not input_rows_state:
        is_valid = False
        errors.append("No input rows provided.")
        return parts_to_calculate, is_valid, errors

    for i, row_data in enumerate(input_rows_state):
        part_id_from_state = row_data.get('selected_part_id') # This can be int or str
        quantity = row_data.get('quantity')
        part_name = row_data.get('selected_part_name') 

        if part_id_from_state is not None: 
            display_name_for_error = part_name if part_name else f"Input Row {i+1} (Part ID: {part_id_from_state})"
            
            # Convert part_id_from_state to int for the calculator dictionary
            try:
                actual_part_id = int(part_id_from_state)
            except ValueError:
                is_valid = False
                errors.append(f"'{display_name_for_error}': Invalid Part ID format '{part_id_from_state}'. Must be convertible to an integer.")
                continue

            if quantity is None: 
                is_valid = False
                errors.append(f"'{display_name_for_error}': Quantity not provided.")
                continue 

            try:
                qty_int = int(quantity)
                if qty_int <= 0:
                    is_valid = False
                    errors.append(f"'{display_name_for_error}': Quantity must be positive (got {qty_int}).")
                else:
                    parts_to_calculate[actual_part_id] = parts_to_calculate.get(actual_part_id, 0) + qty_int
            except ValueError:
                is_valid = False
                errors.append(f"'{display_name_for_error}': Invalid quantity '{quantity}'. Must be a whole number.")
            except TypeError:
                 is_valid = False
                 errors.append(f"'{display_name_for_error}': Invalid quantity type '{type(quantity)}'. Must be a whole number.")

    if not parts_to_calculate and is_valid: 
         is_valid = False
         errors.append("No valid parts selected or quantities provided.")


    return parts_to_calculate, is_valid, errors

def fetch_category_parts(api_client: ApiClient, category_id: int) -> Tuple[Optional[Dict[str, int]], Optional[str]]:
    """ Fetches parts from a specific category using the ApiClient """
    if not isinstance(api_client, ApiClient):
        logger.error(f"fetch_category_parts received invalid api_client type: {type(api_client)}")
        return None, f"Internal Error: Invalid API client provided to fetch_category_parts."

    try:
        parts_data_list, api_warnings = api_client.get_parts_by_category(category_id=category_id)
        error_messages = []
        if api_warnings:
            for warn_msg in api_warnings:
                logger.warning(f"API warning while fetching parts for category {category_id}: {warn_msg}")
                error_messages.append(warn_msg)

        if parts_data_list is None:
            msg = f"Received no data (None) from API for category {category_id} using get_parts_by_category."
            logger.warning(msg)
            error_messages.append(msg)
            return None, "; ".join(error_messages) if error_messages else "Failed to fetch parts and no specific API warnings."

        if not isinstance(parts_data_list, list):
            msg = f"API returned unexpected data type for category {category_id}. Expected list, got {type(parts_data_list)}."
            logger.error(msg)
            error_messages.append(msg)
            return None, "; ".join(error_messages)

        formatted_parts: Dict[str, int] = {}
        valid_parts_data = []
        for part_dict in parts_data_list:
            if isinstance(part_dict, dict) and 'pk' in part_dict and 'name' in part_dict:
                valid_parts_data.append(part_dict)
            else:
                logger.warning(f"Skipping part data due to missing 'pk' or 'name': {part_dict} for category {category_id}")
        
        formatted_parts = {part['name']: part['pk'] for part in sorted(valid_parts_data, key=lambda x: x.get('name', ''))}
        
        if error_messages:
             return None, "; ".join(error_messages)

        return formatted_parts, None 
    except Exception as e:
        logger.error(f"Error in fetch_category_parts for category {category_id}: {e}", exc_info=True)
        return None, f"Error fetching parts for category {category_id}: {str(e)}"

# --- Helper Functions --- (Continued)

def format_parts_to_order_for_display(parts: List['CalculatedPart'], app_config: Optional[AppConfig], show_consumables: bool, show_optional_parts: bool = True) -> pd.DataFrame:
    """ Formats the list of parts to order into a DataFrame for Streamlit display. """
    if not parts:
        return pd.DataFrame()

    filtered_parts = parts
    if not show_consumables:
        filtered_parts = [p for p in parts if not getattr(p, 'is_consumable', False)]

    if not filtered_parts:
        return pd.DataFrame()

    if not st.session_state.get("show_haip_parts_toggle", True):
        filtered_parts = [
            p for p in filtered_parts
            if "HAIP Solutions GmbH" not in getattr(p, 'supplier_names', [])
        ]

    if not filtered_parts:
        return pd.DataFrame()

    if not show_optional_parts:
        filtered_parts = [p for p in filtered_parts if not getattr(p, 'is_optional', False)]

    if not filtered_parts:
        return pd.DataFrame()

    data = []
    instance_url = app_config.inventree_instance_url if app_config else None

    for part in filtered_parts: 
        part_pk = getattr(part, 'pk', None)
        part_name = getattr(part, 'name', 'N/A')
        part_url = None
        if instance_url and part_pk is not None:
            part_url = f"{instance_url.rstrip('/')}/part/{part_pk}/#name={quote(part_name)}" if instance_url and part_pk else None

        data.append({
            "Part ID": part_pk,
            "Optional": getattr(part, 'is_optional', False),
            "Part_URL": part_url,
            "Needed": getattr(part, 'total_required', 0.0),
            "Total In Stock": getattr(part, 'total_in_stock', 0.0),
            "Required for Build Orders": getattr(part, 'required_for_build_orders', 0.0),
            "Required for Sales Orders": getattr(part, 'required_for_sales_orders', 0.0),
            "Available": getattr(part, 'available', 0.0),
            "To Order": getattr(part, 'to_order', 0.0),
            "On Order": getattr(part, 'ordering', 0.0),
            "Belongs to": ", ".join(sorted(list(getattr(part, 'belongs_to_top_parts', set())))),
        })

    columns_order = [
        "Part ID", "Optional", "Part_URL", "Needed", "Total In Stock",
        "Required for Build Orders", "Required for Sales Orders",
        "Available", "To Order", "On Order", "Belongs to"
    ]
    df = pd.DataFrame(data)
    df = df.reindex(columns=columns_order)
    return df

def format_assemblies_to_build_for_display(assemblies: List['CalculatedPart'], app_config: Optional[AppConfig], show_consumables: bool, show_optional_parts: bool = True) -> pd.DataFrame:
    """ Formats the list of assemblies to build into a DataFrame for Streamlit display. """
    if not assemblies:
        return pd.DataFrame()

    filtered_assemblies = assemblies
    if not show_consumables:
        filtered_assemblies = [a for a in assemblies if not getattr(a, 'is_consumable', False)]

    if not filtered_assemblies:
        return pd.DataFrame()

    if not st.session_state.get("show_haip_parts_toggle", True):
        filtered_assemblies = [
            a for a in filtered_assemblies
            if "HAIP Solutions GmbH" not in getattr(a, 'supplier_names', [])
        ]

    if not filtered_assemblies:
        return pd.DataFrame()

    if not show_optional_parts:
        filtered_assemblies = [a for a in filtered_assemblies if not getattr(a, 'is_optional', False)]

    if not filtered_assemblies:
        return pd.DataFrame()

    data = []
    instance_url = app_config.inventree_instance_url if app_config else None

    for asm in filtered_assemblies: 
        part_pk = getattr(asm, 'pk', None)
        part_name = getattr(asm, 'name', 'N/A')
        part_url = None
        if instance_url and part_pk is not None:
            part_url = f"{instance_url.rstrip('/')}/part/{part_pk}/#name={quote(part_name)}" if instance_url and part_pk else None

        data.append({
            "Part ID": part_pk,
            "Optional": getattr(asm, 'is_optional', False),
            "Part_URL": part_url,
            "Needed": getattr(asm, 'total_required', 0.0),
            "Total In Stock": getattr(asm, 'total_in_stock', 0.0),
            "Required for Build Orders": getattr(asm, 'required_for_build_orders', 0.0),
            "Required for Sales Orders": getattr(asm, 'required_for_sales_orders', 0.0),
            "Available": getattr(asm, 'available', 0.0),
            "In Production": getattr(asm, 'building', 0.0),
            "To Build": getattr(asm, 'to_build', 0.0),
            "Belongs to": ", ".join(sorted(list(getattr(asm, 'belongs_to_top_parts', set())))),
        })

    columns_order = [
        "Part ID", "Optional", "Part_URL", "Needed", "Total In Stock",
        "Required for Build Orders", "Required for Sales Orders",
        "Available", "In Production", "To Build", "Belongs to"
    ]
    df = pd.DataFrame(data)
    df = df.reindex(columns=columns_order)
    return df


# --- Streamlit App ---

st.set_page_config(layout="wide") 
st.title("Inventree Order Calculator")

# --- Initialization and State ---
if 'config' not in st.session_state:
    st.session_state.config = None
if 'config_error' not in st.session_state:
    st.session_state.config_error = None
if 'api_client' not in st.session_state:
    st.session_state.api_client = None
if 'category_parts' not in st.session_state: 
    st.session_state.category_parts = None
if 'target_category_name' not in st.session_state: 
    st.session_state.target_category_name = None
if 'parts_fetch_error' not in st.session_state:
    st.session_state.parts_fetch_error = None
if 'calculation_results' not in st.session_state: 
    st.session_state.calculation_results = None
if 'calculation_error' not in st.session_state:
    st.session_state.calculation_error = None
if 'input_rows' not in st.session_state:
    st.session_state.input_rows = [{'id': 0, 'selected_part_name': None, 'selected_part_id': None, 'quantity': 1}]
if 'next_row_id' not in st.session_state:
    st.session_state.next_row_id = 1
if 'show_consumables_toggle_widget' not in st.session_state: 
    st.session_state.show_consumables_toggle_widget = False 
if 'show_haip_parts_toggle' not in st.session_state:
    st.session_state.show_haip_parts_toggle = False
if 'show_optional_parts_toggle' not in st.session_state:
    st.session_state.show_optional_parts_toggle = True
if 'building_calculation_method' not in st.session_state:
    st.session_state.building_calculation_method = BuildingCalculationMethod.OLD_GUI

# --- Preset Session State Initialization ---
if 'presets_data' not in st.session_state:
    st.session_state.presets_data = load_presets_from_file(PRESETS_FILE_PATH)
if 'preset_names' not in st.session_state:
    st.session_state.preset_names = get_preset_names(st.session_state.presets_data)
if 'new_preset_name' not in st.session_state:
    st.session_state.new_preset_name = ""
if 'selected_preset_name' not in st.session_state:
    st.session_state.selected_preset_name = st.session_state.preset_names[0] if st.session_state.preset_names else None


# --- Configuration Loading ---
if st.session_state.config is None and st.session_state.config_error is None:
    try:
        config = AppConfig.load() 
        st.session_state.config = config
        logger.info(f"AppConfig loaded in Streamlit: URL='{st.session_state.config.inventree_url}', Token is {'SET' if st.session_state.config.inventree_api_token else 'NOT SET'}")

        url = config.inventree_url
        token = config.inventree_api_token

        if url is None or not isinstance(url, str) or url.strip() == "":
            logger.error("INVENTREE_URL is missing or invalid after loading config.")
            raise ConfigError("INVENTREE_URL is missing or invalid in the .env file or environment variables.")
        if token is None or not isinstance(token, str) or token.strip() == "":
             logger.error("INVENTREE_API_TOKEN is missing or invalid after loading config.")
             raise ConfigError("INVENTREE_API_TOKEN is missing or invalid in the .env file or environment variables.")

        url_variable_used = url.strip()
        token_variable_used = token.strip()
        logger.info(f"Attempting to instantiate ApiClient with URL: {url_variable_used}, Token: {'SET' if token_variable_used else 'NOT SET'}")

        st.session_state.api_client = ApiClient(
            url=url_variable_used, 
            token=token_variable_used 
        )
        logger.info("ApiClient instantiated and stored in st.session_state.api_client")

        st.success("Configuration loaded successfully from .env.")
        st.info(f"Using InvenTree URL: {config.inventree_url}")
    except ConfigError as e:
        logger.error(f"Configuration Error during initial load: {e}", exc_info=True)
        st.session_state.config_error = f"Configuration Error: {e}"
        st.error(st.session_state.config_error)
    except Exception as e:
        logger.error(f"Failed to load configuration or initialize API client: {e}", exc_info=True)
        st.session_state.config_error = f"Failed to load configuration or initialize API client: {e}"
        st.error(st.session_state.config_error)

if st.session_state.config_error:
    st.stop()
    logger.warning("Stopping execution due to configuration error.")
    st.stop()
if st.session_state.config is None or st.session_state.api_client is None:
     logger.warning("Config or api_client is still None, stopping.")
     st.warning("Waiting for configuration and API client initialization...")
     st.stop()


# --- Fetch Category Parts ---
if st.session_state.api_client and st.session_state.category_parts is None and st.session_state.parts_fetch_error is None:
    with st.spinner(f"Fetching data for category {TARGET_CATEGORY_ID}..."):
        if st.session_state.target_category_name is None:
            try:
                category_details, cat_api_warnings = st.session_state.api_client.get_category_details(TARGET_CATEGORY_ID)
                combined_cat_errors = []
                if cat_api_warnings:
                    for warn_msg in cat_api_warnings:
                        logger.warning(f"API warning fetching category details for ID {TARGET_CATEGORY_ID}: {warn_msg}")
                        combined_cat_errors.append(warn_msg)

                if category_details and 'name' in category_details:
                    st.session_state.target_category_name = category_details['name']
                    logger.info(f"Fetched category name: {st.session_state.target_category_name} for ID {TARGET_CATEGORY_ID}")
                else:
                    err_msg = f"Could not fetch category name for ID {TARGET_CATEGORY_ID}."
                    if category_details is None and not combined_cat_errors: 
                        combined_cat_errors.append(err_msg + " API returned no data.")
                    elif category_details is not None and 'name' not in category_details :
                         combined_cat_errors.append(err_msg + " 'name' field missing in response.")
                    logger.warning(f"{err_msg} Details: {category_details}, Warnings: {combined_cat_errors}")
                    st.session_state.target_category_name = str(TARGET_CATEGORY_ID) 
                    if combined_cat_errors: 
                         st.session_state.parts_fetch_error = (st.session_state.parts_fetch_error + "; " if st.session_state.parts_fetch_error else "") + "; ".join(combined_cat_errors)

            except Exception as e:
                logger.error(f"Error in Streamlit app calling get_category_details for ID {TARGET_CATEGORY_ID}: {e}", exc_info=True)
                st.session_state.parts_fetch_error = (st.session_state.parts_fetch_error + "; " if st.session_state.parts_fetch_error else "") + f"Error fetching category details: {str(e)}"
                st.session_state.target_category_name = str(TARGET_CATEGORY_ID) 

        parts_dict, error = fetch_category_parts(st.session_state.api_client, TARGET_CATEGORY_ID)
        if error:
            st.session_state.parts_fetch_error = error
        else:
            st.session_state.category_parts = parts_dict if parts_dict is not None else {}
            if not st.session_state.category_parts:
                 logger.warning(f"No parts found in category {TARGET_CATEGORY_ID} ({st.session_state.target_category_name}).")
        
        if error or parts_dict is not None or st.session_state.target_category_name is not None:
            st.rerun()

if st.session_state.parts_fetch_error:
    st.error(st.session_state.parts_fetch_error)
    logger.warning(f"Stopping execution due to parts/category fetch error: {st.session_state.parts_fetch_error}")
    st.stop()

if st.session_state.category_parts is None or st.session_state.target_category_name is None:
     logger.warning("category_parts or target_category_name is still None, stopping.")
     st.warning("Waiting for category and parts list to load...")
     st.stop()


# --- Dynamic Input Section ---
category_display_name = st.session_state.target_category_name if st.session_state.target_category_name else str(TARGET_CATEGORY_ID)
st.subheader(f"Input Parts (Category: {category_display_name})")

if not st.session_state.category_parts:
    st.warning(f"Cannot add parts: No parts found in category {category_display_name}.")
else:
    part_names_list = list(st.session_state.category_parts.keys()) 

    input_container = st.container()

    with input_container:
        indices_to_remove = []
        for i, row in enumerate(st.session_state.input_rows):
            row_key_base = f"row_{row['id']}"
            cols = st.columns([4, 1, 1]) 

            with cols[0]:
                current_selection_in_state = st.session_state.input_rows[i]['selected_part_name']
                
                select_box_index = None
                if current_selection_in_state is not None:
                    try:
                        select_box_index = part_names_list.index(current_selection_in_state)
                    except ValueError:
                        logger.warning(f"Previously selected part '{current_selection_in_state}' for row {row['id']} not in current options. Resetting selection.")
                        st.session_state.input_rows[i]['selected_part_name'] = None
                        st.session_state.input_rows[i]['selected_part_id'] = None
                
                selected_name_from_widget = st.selectbox(
                    label="Part",
                    options=part_names_list,
                    index=select_box_index, 
                    placeholder="-- Select Part --",
                    key=f"part_select_{row_key_base}",
                    label_visibility="collapsed"
                )
                
                if selected_name_from_widget != current_selection_in_state:
                    st.session_state.input_rows[i]['selected_part_name'] = selected_name_from_widget
                    if selected_name_from_widget is None: 
                         st.session_state.input_rows[i]['selected_part_id'] = None
                    else:
                         st.session_state.input_rows[i]['selected_part_id'] = st.session_state.category_parts[selected_name_from_widget]

            with cols[1]:
                quantity = st.number_input(
                    label="Quantity", 
                    min_value=1,
                    value=st.session_state.input_rows[i]['quantity'],
                    step=1,
                    key=f"quantity_input_{row_key_base}", 
                    label_visibility="collapsed" 
                )
                st.session_state.input_rows[i]['quantity'] = quantity

            with cols[2]:
                 if len(st.session_state.input_rows) > 1:
                     if st.button("➖", key=f"remove_{row_key_base}", help="Remove this row"): 
                         indices_to_remove.append(i)
                 else:
                      st.write("") 

        if indices_to_remove:
            for index in sorted(indices_to_remove, reverse=True):
                del st.session_state.input_rows[index]
            st.rerun() 

    col_btn1, col_btn2 = st.columns([1, 5]) 
    with col_btn1:
        if st.button("➕ Add Part", help="Add another part row"):
            new_row_id = st.session_state.next_row_id
            st.session_state.input_rows.append({
                'id': new_row_id,
                'selected_part_name': None, 
                'selected_part_id': None,
                'quantity': 1
            })
            st.session_state.next_row_id += 1
            st.rerun()

    with col_btn2:
        if st.button("⚙️ Calculate Orders", type="primary", help="Calculate required parts and assemblies"):
            st.session_state.calculation_results = None 
            st.session_state.calculation_error = None   

            logger.info("Calculate Orders button clicked.")
            parts_to_calc, is_valid, errors = parse_dynamic_inputs(st.session_state.input_rows)

            if not is_valid:
                error_message = "Input Error(s):\n" + "\n".join(errors)
                logger.warning(f"Input validation failed: {error_message}")
                st.session_state.calculation_error = error_message
            else:
                logger.info("Input valid, proceeding with calculation.")
                with st.spinner("Calculating required orders..."):
                    try:
                        api_client_instance = st.session_state.get('api_client')

                        if not isinstance(api_client_instance, ApiClient):
                            logger.error(f"Invalid type for api_client in session state. Expected ApiClient, got {type(api_client_instance)}. Value: {api_client_instance!r}")
                            logger.error(f"The ApiClient class object used for isinstance check: {ApiClient!r} (id: {id(ApiClient)})")
                            if api_client_instance is not None:
                                logger.error(f"The class object of the instance in session state: {type(api_client_instance)!r} (id: {id(type(api_client_instance))})")
                            st.session_state.calculation_error = f"Internal Error: Invalid API client state. Expected ApiClient, got {type(api_client_instance)}."
                            raise Exception(st.session_state.calculation_error) 

                        calculator = OrderCalculator(api_client_instance, building_method=st.session_state.building_calculation_method)

                        logger.info(f"Preparing input for calculator. Original parts_to_calc: {parts_to_calc}")
                        input_parts_list = [
                            InputPart(part_identifier=str(pk), quantity_to_build=qty) # Ensure part_identifier is string
                            for pk, qty in parts_to_calc.items()
                        ]
                        
                        # Call the correct method name as per calculator.py
                        output_data = calculator.calculate_orders(input_parts_list) # Returns a single OutputTables object
                        
                        # Access results and warnings from the OutputTables object
                        # OutputTables model currently only has a 'warnings' field for messages.
                        st.session_state.calculation_results = output_data
                        calc_messages = output_data.warnings # This list contains both errors and warnings from calculator
                        
                        # For Streamlit display, we'll treat these messages seriously.
                        # We can't distinguish errors from warnings solely based on OutputTables structure.
                        # The st.session_state.calculation_error will store these.
                        st.session_state.calculation_error = "; ".join(calc_messages) if calc_messages else None
                        
                        if calc_messages: # Display all messages from calculator
                            for msg in calc_messages:
                                # Heuristic: if "error" or "invalid" is in message, display as error, else warning
                                if "error" in msg.lower() or "invalid" in msg.lower() or "failed" in msg.lower() or "not found" in msg.lower():
                                    st.error(f"Calculation Message: {msg}")
                                    logger.error(f"Calculator Message (treated as error): {msg}")
                                else:
                                    st.warning(f"Calculation Message: {msg}")
                                    logger.warning(f"Calculator Message (treated as warning): {msg}")
                        
                        # Determine success based on whether critical messages (now in calculation_error) were logged.
                        # A more robust solution would be for calculator to return distinct error/warning lists.
                        if output_data and not st.session_state.calculation_error:
                             st.success("Calculation complete!")
                             logger.info(f"Calculation successful. Results stored. Parts to order: {len(output_data.parts_to_order)}, Assemblies to build: {len(output_data.subassemblies_to_build)}")
                        elif not st.session_state.calculation_error and (not output_data.parts_to_order and not output_data.subassemblies_to_build):
                            st.info("Calculation complete. No parts need to be ordered and no subassemblies need to be built based on current stock and demands.")
                            logger.info("Calculation complete, no orders/builds required.")
                        elif st.session_state.calculation_error:
                            # Error already displayed by the loop above.
                            # Ensure no success message is shown.
                            pass

                    except ConfigError as e:
                         logger.error(f"Configuration Error during calculation: {e}", exc_info=True)
                         st.session_state.calculation_error = f"Configuration Error during calculation: {e}"
                    except ConnectionError as e: 
                         logger.error(f"API Connection Error during calculation: {e}", exc_info=True)
                         st.session_state.calculation_error = f"API Connection Error during calculation: {e}"
                    except ValueError as e: 
                         logger.error(f"Data Error during calculation: {e}", exc_info=True)
                         st.session_state.calculation_error = f"Data Error during calculation: {e}"
                    except TypeError as e: 
                         logger.error(f"Type Error during calculation: {e}", exc_info=True)
                         st.session_state.calculation_error = f"Type Error during calculation: {e}"
                    except Exception as e: 
                        logger.error(f"An unexpected error occurred during calculation: {e}", exc_info=True)
                        st.session_state.calculation_error = f"An unexpected error occurred during calculation: {e}"
            st.rerun()


# --- Sidebar Content ---
st.sidebar.title("Options & Presets")

# --- Display Toggles in Sidebar ---
# --- Preset Management UI in Sidebar ---
st.sidebar.subheader("Preset Management")

st.session_state.new_preset_name = st.sidebar.text_input(
    "New Preset Name:",
    value=st.session_state.new_preset_name,
    key="new_preset_name_input"
)

if st.sidebar.button("Save Current Set", key="save_preset_button"):
    preset_name_to_save = st.session_state.new_preset_name.strip()
    if not preset_name_to_save:
        st.sidebar.warning("Please enter a name for the preset.")
    else:
        preset_items, conversion_errors = convert_input_rows_to_preset_items(st.session_state.input_rows)
        if conversion_errors:
            for err in conversion_errors:
                st.sidebar.error(err)
        if not preset_items: 
            if not conversion_errors: 
                 st.sidebar.warning("No valid items to save. Ensure parts are selected and quantities are valid.")
        else:
            try:
                new_preset_obj = Preset(name=preset_name_to_save, items=preset_items)
                st.session_state.presets_data = add_or_update_preset(
                    st.session_state.presets_data,
                    new_preset_obj
                )
                save_success = save_presets_to_file(st.session_state.presets_data, PRESETS_FILE_PATH)
                if save_success:
                    st.sidebar.success(f"Preset '{preset_name_to_save}' saved!")
                    st.session_state.preset_names = get_preset_names(st.session_state.presets_data)
                    st.session_state.new_preset_name = "" 
                    st.session_state.selected_preset_name = preset_name_to_save
                    st.rerun()
                else:
                    st.sidebar.error("Failed to save preset to file.")
            except Exception as e:
                st.sidebar.error(f"Error creating or saving preset: {e}")

# Selectbox for loading/deleting presets
if not st.session_state.preset_names:
    st.sidebar.caption("No presets saved yet.")
    if st.session_state.selected_preset_name is not None: # If a preset was selected but list is now empty
        st.session_state.selected_preset_name = None
else:
    current_selection = st.session_state.get('selected_preset_name')
    selectbox_options = ["-- Select a preset --"] + st.session_state.preset_names
    
    idx = 0 
    if current_selection and current_selection in st.session_state.preset_names:
        idx = selectbox_options.index(current_selection)

    selected_option_from_widget = st.sidebar.selectbox(
        "Manage Presets:",
        options=selectbox_options,
        index=idx, 
        key="manage_presets_selectbox"
    )

    if selected_option_from_widget == "-- Select a preset --":
        if st.session_state.selected_preset_name is not None: 
            st.session_state.selected_preset_name = None
            st.rerun() # Rerun if selection changes to placeholder to hide load/delete
    elif selected_option_from_widget != st.session_state.selected_preset_name:
        st.session_state.selected_preset_name = selected_option_from_widget
        st.rerun() # Rerun if selection changes to a valid preset
        
# Load and Delete buttons - only show if a valid preset is selected
if st.session_state.selected_preset_name and st.session_state.selected_preset_name != "-- Select a preset --":
    col_load, col_delete = st.sidebar.columns(2)
    with col_load:
        if st.button("Load Set", key="load_preset_button", help=f"Load '{st.session_state.selected_preset_name}'"):
            preset_to_load = get_preset_by_name(
                st.session_state.presets_data,
                st.session_state.selected_preset_name
            )
            if preset_to_load:
                # category_parts is {name: id}. We need {id: name} for lookup.
                category_parts_id_to_name_lookup: Dict[Any, str] = {}
                if st.session_state.category_parts: 
                    for pname, pid_val in st.session_state.category_parts.items():
                        category_parts_id_to_name_lookup[pid_val] = pname # pid_val is int
                        category_parts_id_to_name_lookup[str(pid_val)] = pname # also add string version for safety
                
                new_rows, next_id, load_warnings = populate_input_rows_from_preset_items(
                    preset_to_load.items,
                    category_parts_id_to_name_lookup, # This is {id: name}
                    st.session_state.next_row_id 
                )
                st.session_state.input_rows = new_rows
                st.session_state.next_row_id = next_id 

                st.sidebar.success(f"Preset '{st.session_state.selected_preset_name}' loaded!")
                for warning in load_warnings:
                    st.sidebar.warning(warning)
                st.rerun()
            else:
                st.sidebar.error(f"Could not find preset '{st.session_state.selected_preset_name}' to load.")
                st.session_state.presets_data = load_presets_from_file(PRESETS_FILE_PATH)
                st.session_state.preset_names = get_preset_names(st.session_state.presets_data)
                st.rerun()
    
    with col_delete:
        if st.button("Delete Set", key="delete_preset_button", type="secondary", help=f"Delete '{st.session_state.selected_preset_name}'"):
            name_to_delete = st.session_state.selected_preset_name
            st.session_state.presets_data = delete_preset_by_name(
                st.session_state.presets_data,
                name_to_delete
            )
            # Corrected argument order: (presets_data, filepath)
            save_success = save_presets_to_file(st.session_state.presets_data, PRESETS_FILE_PATH)
            if save_success:
                st.sidebar.success(f"Preset '{name_to_delete}' deleted!")
                st.session_state.preset_names = get_preset_names(st.session_state.presets_data)
                
                st.session_state.selected_preset_name = None 
                st.rerun()
            else:
                st.sidebar.error(f"Failed to save changes after deleting '{name_to_delete}'.")
                st.session_state.presets_data = load_presets_from_file(PRESETS_FILE_PATH) 
                st.session_state.preset_names = get_preset_names(st.session_state.presets_data)
                st.rerun()

# --- Display Errors / Results ---
st.divider()

with st.expander("Display Options", expanded=True):
    # Building Calculation Method Selection
    st.subheader("Building Calculation Method")
    building_method_options = {
        "New Method (like Old GUI)": BuildingCalculationMethod.OLD_GUI,
        "Old Method (like New GUI)": BuildingCalculationMethod.NEW_GUI
    }

    current_method_label = next(
        (label for label, method in building_method_options.items()
         if method == st.session_state.building_calculation_method),
        "New Method (like Old GUI)"
    )

    selected_method_label = st.selectbox(
        "Choose building calculation method:",
        options=list(building_method_options.keys()),
        index=list(building_method_options.keys()).index(current_method_label),
        key="building_method_selectbox",
        help="""
        **New Method (like Old GUI)**: Uses StockItem.list(api, part=part_id, is_building=True) approach.
        Building quantity decreases immediately when individual build outputs are completed.
        Prevents double counting of completed items. **Recommended for accurate calculations.**

        **Old Method (like New GUI)**: Uses standard InvenTree API building field.
        Shows full build order quantities until entire order is completed.
        May cause double counting if completed items are still marked as building.
        """
    )

    st.session_state.building_calculation_method = building_method_options[selected_method_label]

    # Display current method info
    if st.session_state.building_calculation_method == BuildingCalculationMethod.OLD_GUI:
        st.info("🔧 Using New Method (like Old GUI) - prevents double counting of completed build outputs")
    else:
        st.warning("⚠️ Using Old Method (like New GUI) - may include completed items in building quantities")

    st.divider()

    # Display toggles
    st.subheader("Display Filters")
    st.session_state.show_consumables_toggle_widget = st.toggle(
        "Show Consumable Parts",
        value=st.session_state.show_consumables_toggle_widget,
        key="show_consumables_key_main",  # Changed key to avoid conflict if old one lingers
        help="Include parts marked as 'consumable' in the results."
    )
    st.session_state.show_haip_parts_toggle = st.toggle(
        "Show HAIP Solutions GmbH Parts",
        value=st.session_state.show_haip_parts_toggle,
        key="show_haip_parts_key_main", # Changed key to avoid conflict
        help="Include parts primarily supplied by HAIP Solutions GmbH."
    )
    st.session_state.show_optional_parts_toggle = st.toggle(
        "Show Optional Parts",
        value=st.session_state.show_optional_parts_toggle,
        key="show_optional_parts_key_main",
        help="Include parts marked as 'optional' in the BOM results."
    )

# Display calculation error if it occurred (moved from below results)
# The individual calculation messages (errors/warnings) are displayed
# during the calculation logic itself (around line 630-640).
# So, st.session_state.calculation_error (which is a join of those messages)
# doesn't need to be displayed again here as a single block.

# Display warnings from calculation_results.warnings if they exist
# This was the original intent for this expander.
# Note: The loop during calculation (around line 630) already displays these.
# This expander might be redundant if all messages are shown above.
# For now, let's keep it but ensure it only shows actual warnings if distinct from errors.
# However, current `OutputTables` only has `warnings`.
# The logic around line 630 already iterates `output_data.warnings`.
# This expander is therefore duplicative of what's shown above.
# We can remove this expander or ensure it shows something different.
# Given the user feedback, let's remove this redundant display of warnings as well.
# The primary display of calculation messages (errors/warnings) happens after calculation.

# if st.session_state.calculation_results and st.session_state.calculation_results.warnings:
#     with st.expander("⚠️ Calculation Messages", expanded=True):
#         for msg in st.session_state.calculation_results.warnings:
#             # This is duplicative of the display logic after calculation.
#             # st.info(msg) # Or st.warning(msg)
#             pass # Messages are shown after calculation step.
            
# Display results if available and no error occurred during the *last* calculation attempt
if st.session_state.calculation_results is not None: # Display tables if results object exists
    results = st.session_state.calculation_results
    st.subheader("Results") # Moved subheader here

    tab1, tab2 = st.tabs(["Parts to Order", "Assemblies to Build"])

    with tab1:
        df_parts = format_parts_to_order_for_display(
            results.parts_to_order,
            st.session_state.config,
            st.session_state.show_consumables_toggle_widget,
            st.session_state.show_optional_parts_toggle
        )
        if not df_parts.empty:
            st.info(f"Found {len(df_parts)} distinct parts to order.")
            st.dataframe(
                df_parts,
                column_config={
                    "Part_URL": st.column_config.LinkColumn(
                        "Part Name",
                        help="Click to open part in InvenTree (Name extracted from URL)",
                        display_text="^.+/part/\\d+/#name=(.+)$", # Use regex for display_text
                        validate="^.+/part/\\d+/#name=(.+)$"
                    ),
                     "Part ID": st.column_config.NumberColumn(format="%d"),
                     "Optional": st.column_config.CheckboxColumn(
                        "Optional",
                        help="Indicates if this part is optional for the assembly (from InvenTree BOM)",
                        default=False
                     ),
                     "Needed": st.column_config.NumberColumn(format="%.2f"),
                     "Total In Stock": st.column_config.NumberColumn(format="%.2f"),
                     "Required for Build Orders": st.column_config.NumberColumn(format="%.2f"),
                     "Required for Sales Orders": st.column_config.NumberColumn(format="%.2f"),
                     "Available": st.column_config.NumberColumn(format="%.2f"),
                     "To Order": st.column_config.NumberColumn(format="%.2f"),
                     "On Order": st.column_config.NumberColumn(format="%.2f"),
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.success("No parts need to be ordered based on the current input and stock levels.")

    with tab2:
        df_assemblies = format_assemblies_to_build_for_display(
            results.subassemblies_to_build,
            st.session_state.config,
            st.session_state.show_consumables_toggle_widget,
            st.session_state.show_optional_parts_toggle
        )
        if not df_assemblies.empty:
            st.info(f"Found {len(df_assemblies)} distinct assemblies to build.")
            st.dataframe(
                df_assemblies,
                column_config={
                    "Part_URL": st.column_config.LinkColumn(
                        "Assembly Name",
                        help="Click to open assembly in InvenTree (Name extracted from URL)",
                        display_text="^.+/part/\\d+/#name=(.+)$", # Use regex for display_text
                        validate="^.+/part/\\d+/#name=(.+)$"
                    ),
                    "Part ID": st.column_config.NumberColumn(format="%d"),
                    "Optional": st.column_config.CheckboxColumn(
                        "Optional",
                        help="Indicates if this assembly is optional for the build (from InvenTree BOM)",
                        default=False
                    ),
                    "Needed": st.column_config.NumberColumn(format="%.2f"),
                    "Total In Stock": st.column_config.NumberColumn(format="%.2f"),
                    "Required for Build Orders": st.column_config.NumberColumn(format="%.2f"),
                    "Required for Sales Orders": st.column_config.NumberColumn(format="%.2f"),
                    "Available": st.column_config.NumberColumn(format="%.2f"),
                    "In Production": st.column_config.NumberColumn(format="%.2f"),
                    "To Build": st.column_config.NumberColumn(format="%.2f"),
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.success("No assemblies need to be built based on the current input and stock levels.")

elif st.session_state.calculation_error is None and st.session_state.calculation_results is None:
    # Only show this if no calculation has been run yet (results is None) and no error exists
    st.info("Enter parts and quantities above, then click 'Calculate Orders'.")