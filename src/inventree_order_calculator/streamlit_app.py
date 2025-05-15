import streamlit as st
import pandas as pd
from typing import Dict, Any, Tuple, Optional, List
from urllib.parse import quote
import logging
from pathlib import Path
import uuid # For generating unique IDs for monitoring task parts in UI state

# Project Module Imports
try:
    from inventree_order_calculator.config import Config as AppConfig, ConfigError, get_config # Renamed to Config
    from inventree_order_calculator.api_client import InvenTreeAPIClient as ApiClient # Alias for consistency
    from inventree_order_calculator.calculator import OrderCalculator
    from inventree_order_calculator.models import OutputTables, InputPart, CalculatedPart, PartInputLine
    from inventree_order_calculator.presets_manager import (
        PresetsManager, # Use the class
        Preset,
        PresetItem,
        MonitoringList,
        MonitoringPartItem,
        # DEFAULT_PRESETS_FILE_PATH # Path will come from Config
    )
    # For "Run Manually" - this implies Streamlit might need to trigger something in the service
    # or simulate its action. For now, we'll assume a direct call if possible.
    from inventree_order_calculator.monitoring_service import TaskExecutor as MonitoringTaskExecutor 
    import inventree_order_calculator.monitoring_service as monitoring_service_globals # To set globals for run
except ImportError as e:
    st.error(f"Error importing project modules: {e}. "
             "Ensure the script is run from the project root using "
             "`uv run streamlit run src/inventree_order_calculator/streamlit_app.py` "
             "or adjust Python path.")
    st.stop()

# --- Logging Setup ---
logger = logging.getLogger(__name__)
# Logging level will be set after config is loaded

# --- Constants ---
TARGET_CATEGORY_ID = 191 # As specified in the requirements

# --- Helper Functions (some existing, some new/modified) ---

def initialize_app_state():
    """Initializes all necessary session state variables."""
    default_states = {
        'config': None, 'config_error': None, 'api_client': None,
        'category_parts': None, 'target_category_name': None, 'parts_fetch_error': None,
        'calculation_results': None, 'calculation_error': None,
        'input_rows': [{'id': 0, 'selected_part_name': None, 'selected_part_id': None, 'quantity': 1}],
        'next_row_id': 1,
        'show_consumables_toggle_widget': False, # For calculator display
        'show_haip_parts_toggle': False, # For calculator display
        'presets_manager': None, # Will hold PresetsManager instance
        'new_preset_name': "",
        'selected_preset_to_load': None, # For loading preset
        'selected_preset_to_delete': None, # For deleting preset
        # Monitoring Task UI State
        'show_monitoring_form': False,
        'editing_task_id': None, # None for new, task_id for editing
        'monitor_form_data': {}, # Holds current form data for add/edit monitor task
        'monitor_form_part_rows': [{'ui_id': str(uuid.uuid4()), 'name_or_ipn': '', 'quantity': 1, 'version': ''}],
        # 'next_monitor_part_row_ui_id': 0, # ui_id is uuid, not sequential int
        'manual_run_feedback': None,
    }
    for key, value in default_states.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    # Initialize PresetsManager after config is potentially loaded
    if 'presets_manager' not in st.session_state or st.session_state.presets_manager is None:
        if st.session_state.get('config'): 
             try:
                st.session_state.presets_manager = PresetsManager(Path(st.session_state.config.PRESETS_FILE_PATH))
                logger.info(f"PresetsManager initialized with path: {st.session_state.config.PRESETS_FILE_PATH}")
             except Exception as e: # Catch errors if config path is bad or PresetsManager fails
                logger.error(f"Failed to initialize PresetsManager: {e}")
                st.session_state.config_error = (st.session_state.config_error or "") + f"; Failed to init PresetsManager: {e}"


def setup_logging(log_level_str: str):
    level = getattr(logging, log_level_str.upper(), logging.INFO)
    logging.basicConfig(level=level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S', force=True)
    logger.info(f"Logging level set to: {log_level_str.upper()}")


def convert_input_rows_to_preset_items(input_rows_state: List[Dict[str, Any]]) -> Tuple[List[PresetItem], List[str]]:
    preset_items: List[PresetItem] = []
    errors: List[str] = []
    if not input_rows_state:
        errors.append("No input rows to save as preset.")
        return preset_items, errors
    for i, row_data in enumerate(input_rows_state):
        part_id = row_data.get('selected_part_id')
        quantity = row_data.get('quantity')
        part_name = row_data.get('selected_part_name', f"Row {i+1}")
        if part_id is not None:
            if quantity is None: errors.append(f"'{part_name}': Quantity not provided.")
            else:
                try:
                    qty_int = int(quantity)
                    if qty_int <= 0: errors.append(f"'{part_name}': Quantity must be positive (got {qty_int}).")
                    else: preset_items.append(PresetItem(part_id=part_id, quantity=qty_int))
                except (ValueError, TypeError): errors.append(f"'{part_name}': Invalid quantity '{quantity}'. Must be a whole number.")
    if not preset_items and not errors and any(r.get('selected_part_id') is None for r in input_rows_state) and input_rows_state:
        if any(r.get('selected_part_id') is not None for r in input_rows_state): pass # Some rows have parts, but they might have errors
        elif input_rows_state : errors.append("No parts selected in any input row to save.")
    return preset_items, errors

def populate_input_rows_from_preset_items(
    items: List[PresetItem], current_next_row_id: int
) -> Tuple[List[Dict[str, Any]], int, List[str]]:
    new_input_rows: List[Dict[str, Any]] = []
    warnings: List[str] = []
    next_row_id = current_next_row_id
    # Ensure category_parts is available and is a dict
    category_parts_local = st.session_state.get('category_parts', {})
    if not isinstance(category_parts_local, dict): category_parts_local = {}
    
    category_parts_name_lookup = {v: k for k, v in category_parts_local.items()}

    if not items: 
        new_input_rows.append({'id': next_row_id, 'selected_part_name': None, 'selected_part_id': None, 'quantity': 1})
        next_row_id +=1
        return new_input_rows, next_row_id, warnings

    for item in items:
        part_id_to_check = item.part_id
        part_name_found = category_parts_name_lookup.get(part_id_to_check)
        if not part_name_found and isinstance(part_id_to_check, str): 
            try: part_name_found = category_parts_name_lookup.get(int(part_id_to_check))
            except (ValueError, TypeError): pass # Keep part_name_found as None
        
        if part_name_found:
            new_input_rows.append({
                'id': next_row_id, 'selected_part_name': part_name_found,
                'selected_part_id': item.part_id, 'quantity': item.quantity
            })
        else:
            warnings.append(f"Part ID '{item.part_id}' from preset not found in current category parts. Skipping.")
        next_row_id += 1
    
    if not new_input_rows: 
        new_input_rows.append({'id': next_row_id, 'selected_part_name': None, 'selected_part_id': None, 'quantity': 1})
        next_row_id +=1
        if not warnings: warnings.append("No items from preset could be loaded as they are not in current category parts list.")
    return new_input_rows, next_row_id, warnings


def parse_dynamic_inputs(input_rows_state: List[Dict[str, Any]]) -> Tuple[List[InputPart], bool, List[str]]:
    input_parts_for_calc: List[InputPart] = []
    is_valid = True
    errors: List[str] = []
    if not input_rows_state:
        is_valid = False; errors.append("No input rows provided.")
        return input_parts_for_calc, is_valid, errors
    
    temp_parts_dict: Dict[Any, float] = {} 

    for i, row_data in enumerate(input_rows_state):
        part_id_from_state = row_data.get('selected_part_id')
        quantity = row_data.get('quantity')
        part_name = row_data.get('selected_part_name')
        display_name_for_error = part_name if part_name else f"Input Row {i+1}"

        if part_id_from_state is not None:
            try:
                qty_float = float(quantity) 
                if qty_float <= 0:
                    is_valid = False; errors.append(f"'{display_name_for_error}': Quantity must be positive.")
                else:
                    current_qty = temp_parts_dict.get(part_id_from_state, 0.0)
                    temp_parts_dict[part_id_from_state] = current_qty + qty_float
            except (ValueError, TypeError):
                is_valid = False; errors.append(f"'{display_name_for_error}': Invalid quantity '{quantity}'.")
    
    if not temp_parts_dict and is_valid and input_rows_state and any(r.get('selected_part_id') for r in input_rows_state):
        is_valid = False; errors.append("No valid parts selected or quantities provided, though rows exist.")
    elif not temp_parts_dict and is_valid and not any(r.get('selected_part_id') for r in input_rows_state) and input_rows_state:
        is_valid = False; errors.append("No parts selected in any input row.")


    if is_valid: 
        for pid, qty in temp_parts_dict.items():
            input_parts_for_calc.append(InputPart(part_identifier=str(pid), quantity_to_build=qty))
            
    return input_parts_for_calc, is_valid, errors


def fetch_category_parts(api_client: ApiClient, category_id: int) -> Tuple[Optional[Dict[str, int]], Optional[str]]:
    if not isinstance(api_client, ApiClient):
        logger.error(f"fetch_category_parts received invalid api_client type: {type(api_client)}")
        return None, "Internal Error: Invalid API client."
    try:
        parts_data_list, api_warnings = api_client.get_parts_by_category(category_id=category_id)
        error_messages = [str(w) for w in api_warnings] if api_warnings else []

        if parts_data_list is None:
            msg = f"No data from API for category {category_id}."
            logger.warning(msg); error_messages.append(msg)
            return None, "; ".join(error_messages) if error_messages else "Failed to fetch parts."
        if not isinstance(parts_data_list, list):
            msg = f"API returned unexpected data type for category {category_id}: {type(parts_data_list)}."
            logger.error(msg); error_messages.append(msg)
            return None, "; ".join(error_messages)

        valid_parts_data = [p for p in parts_data_list if isinstance(p, dict) and 'pk' in p and 'name' in p]
        formatted_parts = {part['name']: part['pk'] for part in sorted(valid_parts_data, key=lambda x: x.get('name', ''))}
        
        if len(valid_parts_data) != len(parts_data_list):
            logger.warning(f"Some part data was invalid for category {category_id}")
            
        return formatted_parts, "; ".join(error_messages) if error_messages else None
    except Exception as e:
        logger.error(f"Error in fetch_category_parts for category {category_id}: {e}", exc_info=True)
        return None, f"Error fetching parts: {str(e)}"

def format_parts_to_order_for_display(parts: List[CalculatedPart], app_config: Optional[AppConfig], show_consumables: bool, show_haip: bool) -> pd.DataFrame:
    if not parts: return pd.DataFrame()
    filtered_parts = [p for p in parts if show_consumables or not getattr(p.part_data, 'consumable', False)]
    if not show_haip:
        filtered_parts = [p for p in filtered_parts if "HAIP Solutions GmbH" not in getattr(p.part_data, 'supplier_names', [])] # Assuming supplier_names on part_data
    if not filtered_parts: return pd.DataFrame()
    
    data = []
    instance_url = app_config.INVENTREE_INSTANCE_URL if app_config and app_config.INVENTREE_INSTANCE_URL else None
    for part_calc in filtered_parts:
        pd = part_calc.part_data
        part_url = f"{instance_url.rstrip('/')}/part/{pd.pk}/" if instance_url and pd.pk else None
        data.append({
            "Part ID": pd.pk, "Part_URL": part_url, "Part Name": pd.name, # Added Part Name for LinkColumn
            "Needed": part_calc.total_required, "Total In Stock": pd.total_in_stock,
            "Required for Build Orders": pd.required_for_build_orders,
            "Required for Sales Orders": pd.required_for_sales_orders,
            "Available": part_calc.available, "To Order": part_calc.to_order, "On Order": pd.ordering,
            "Belongs to": ", ".join(sorted(list(part_calc.belongs_to_top_parts))),
        })
    df = pd.DataFrame(data)
    return df.reindex(columns=["Part ID", "Part Name", "Part_URL", "Needed", "Total In Stock", "Required for Build Orders", "Required for Sales Orders", "Available", "To Order", "On Order", "Belongs to"])

def format_assemblies_to_build_for_display(assemblies: List[CalculatedPart], app_config: Optional[AppConfig], show_consumables: bool, show_haip: bool) -> pd.DataFrame:
    if not assemblies: return pd.DataFrame()
    filtered_assemblies = [a for a in assemblies if show_consumables or not getattr(a.part_data, 'consumable', False)]
    if not show_haip:
        filtered_assemblies = [a for a in filtered_assemblies if "HAIP Solutions GmbH" not in getattr(a.part_data, 'supplier_names', [])]
    if not filtered_assemblies: return pd.DataFrame()

    data = []
    instance_url = app_config.INVENTREE_INSTANCE_URL if app_config and app_config.INVENTREE_INSTANCE_URL else None
    for asm_calc in filtered_assemblies:
        pd = asm_calc.part_data
        part_url = f"{instance_url.rstrip('/')}/part/{pd.pk}/" if instance_url and pd.pk else None
        data.append({
            "Part ID": pd.pk, "Part_URL": part_url, "Part Name": pd.name,
            "Needed": asm_calc.total_required, "Total In Stock": pd.total_in_stock,
            "Required for Build Orders": pd.required_for_build_orders,
            "Required for Sales Orders": pd.required_for_sales_orders,
            "Available": asm_calc.available, "In Production": pd.building, "To Build": asm_calc.to_build,
            "Belongs to": ", ".join(sorted(list(asm_calc.belongs_to_top_parts))),
        })
    df = pd.DataFrame(data)
    return df.reindex(columns=["Part ID", "Part Name", "Part_URL", "Needed", "Total In Stock", "Required for Build Orders", "Required for Sales Orders", "Available", "In Production", "To Build", "Belongs to"])


# --- Streamlit App ---
st.set_page_config(layout="wide", page_title="Inventree Order Calculator")
initialize_app_state() # Initialize/ensure all session state keys

# --- Configuration and API Client Loading ---
if st.session_state.config is None and st.session_state.config_error is None:
    try:
        config_obj = get_config()
        st.session_state.config = config_obj
        setup_logging(config_obj.LOG_LEVEL)
        logger.info(f"AppConfig loaded: URL='{config_obj.INVENTREE_API_URL}'")
        st.session_state.api_client = ApiClient(
            base_url=config_obj.INVENTREE_API_URL,
            api_token=config_obj.INVENTREE_API_TOKEN,
            timeout=config_obj.API_TIMEOUT
        )
        # Re-initialize PresetsManager here if it depends on config path that might change or was not available before
        st.session_state.presets_manager = PresetsManager(Path(config_obj.PRESETS_FILE_PATH))
        logger.info("ApiClient and PresetsManager instantiated.")
    except ConfigError as e:
        logger.error(f"Configuration Error: {e}", exc_info=True)
        st.session_state.config_error = f"Configuration Error: {e}"
    except Exception as e:
        logger.error(f"Initialization Error: {e}", exc_info=True)
        st.session_state.config_error = f"Initialization Error: {e}"

if st.session_state.config_error: st.error(st.session_state.config_error); st.stop()
if not all(st.session_state.get(k) for k in ['config', 'api_client', 'presets_manager']):
    st.warning("Initializing application components..."); st.stop()


# --- Fetch Category Parts ---
if st.session_state.category_parts is None and st.session_state.parts_fetch_error is None:
    with st.spinner(f"Fetching parts for category {TARGET_CATEGORY_ID}..."):
        try:
            cat_details, _ = st.session_state.api_client.get_category_details(TARGET_CATEGORY_ID)
            st.session_state.target_category_name = cat_details.get('name', str(TARGET_CATEGORY_ID)) if cat_details else str(TARGET_CATEGORY_ID)
            parts_dict, error_str = fetch_category_parts(st.session_state.api_client, TARGET_CATEGORY_ID)
            if error_str: st.session_state.parts_fetch_error = error_str
            else: st.session_state.category_parts = parts_dict if parts_dict else {}
            if not st.session_state.category_parts and not error_str: logger.warning(f"No parts in category {TARGET_CATEGORY_ID}")
        except Exception as e:
            logger.error(f"Critical error fetching category/parts: {e}", exc_info=True)
            st.session_state.parts_fetch_error = f"Critical fetch error: {e}"
        st.rerun()

if st.session_state.parts_fetch_error: st.error(f"Failed to fetch parts: {st.session_state.parts_fetch_error}"); st.stop()
if st.session_state.category_parts is None: st.info("Loading parts..."); st.stop()


# --- Sidebar ---
st.sidebar.title("Navigation")
app_mode = st.sidebar.radio("Choose Mode", ["Order Calculator", "Monitoring Tasks"], key="app_mode_selector")
st.sidebar.markdown("---")

if app_mode == "Order Calculator":
    st.sidebar.subheader("Calculation Presets")
    preset_names = [p.name for p in st.session_state.presets_manager.get_presets()]
    load_options = ["-- Select Preset --"] + preset_names
    
    selected_preset_to_load = st.sidebar.selectbox("Load Preset", options=load_options, key="sb_load_calc_preset")
    if st.sidebar.button("Load Selected Preset", disabled=(selected_preset_to_load == "-- Select Preset --"), key="btn_load_calc_preset"):
        preset = st.session_state.presets_manager.get_preset_by_name(selected_preset_to_load)
        if preset and st.session_state.category_parts is not None:
            st.session_state.input_rows, st.session_state.next_row_id, warnings = populate_input_rows_from_preset_items(preset.items, 0) # Reset next_row_id from preset
            if warnings: st.sidebar.warning("; ".join(warnings))
            else: st.sidebar.success(f"Preset '{preset.name}' loaded.")
            st.rerun()
        elif not preset: st.sidebar.error(f"Preset '{selected_preset_to_load}' not found.")

    new_preset_name_input = st.sidebar.text_input("Save Current as Preset", key="ti_new_calc_preset_name").strip()
    if st.sidebar.button("Save Preset", key="btn_save_calc_preset"):
        if new_preset_name_input:
            preset_items, errors = convert_input_rows_to_preset_items(st.session_state.input_rows)
            if errors: st.sidebar.error("; ".join(errors))
            elif not preset_items: st.sidebar.warning("No valid parts/quantities to save.")
            else:
                if st.session_state.presets_manager.add_or_update_preset(Preset(name=new_preset_name_input, items=preset_items)):
                    st.sidebar.success(f"Preset '{new_preset_name_input}' saved.")
                else: st.sidebar.error(f"Failed to save preset '{new_preset_name_input}'.")
                st.rerun()
        else: st.sidebar.warning("Enter a name for the preset.")

    delete_options = ["-- Select Preset to Delete --"] + preset_names
    selected_preset_to_delete = st.sidebar.selectbox("Delete Preset", options=delete_options, key="sb_delete_calc_preset")
    if st.sidebar.button("Delete Selected Preset", type="primary", disabled=(selected_preset_to_delete == "-- Select Preset to Delete --"), key="btn_delete_calc_preset"):
        if st.session_state.presets_manager.delete_preset_by_name(selected_preset_to_delete):
            st.sidebar.success(f"Preset '{selected_preset_to_delete}' deleted.")
        else: st.sidebar.error(f"Failed to delete '{selected_preset_to_delete}'.")
        st.rerun()

# --- Main Page Content ---
if app_mode == "Order Calculator":
    st.header("Order Calculator")
    # ... (Order Calculator UI logic - largely similar to original, ensure it uses updated state keys)
    # For brevity, this detailed UI part is condensed. Key elements:
    # - Dynamic input rows for parts
    # - Calculate button
    # - Display options (consumables, HAIP parts)
    # - Results display in tabs
    
    # Dynamic Input Rows for Calculator
    input_container = st.container()
    with input_container:
        st.subheader(f"Input Parts (Category: {st.session_state.target_category_name or TARGET_CATEGORY_ID})")
        if not st.session_state.category_parts:
            st.warning(f"Part list for category '{st.session_state.target_category_name}' is empty or not loaded.")
        else:
            part_names_options = ["-- Select Part --"] + list(st.session_state.category_parts.keys())
            indices_to_remove = []
            for i, row_state in enumerate(st.session_state.input_rows):
                row_key_base = f"calc_row_{row_state['id']}"
                cols_calc = st.columns([3,1,1])
                with cols_calc[0]:
                    current_selection_idx = 0
                    if row_state['selected_part_name'] and row_state['selected_part_name'] in part_names_options:
                        current_selection_idx = part_names_options.index(row_state['selected_part_name'])
                    selected_name = st.selectbox(f"Part##{row_key_base}", options=part_names_options, index=current_selection_idx, label_visibility="collapsed", key=f"sel_{row_key_base}")
                    if selected_name != row_state['selected_part_name']:
                        st.session_state.input_rows[i]['selected_part_name'] = selected_name
                        st.session_state.input_rows[i]['selected_part_id'] = st.session_state.category_parts.get(selected_name) if selected_name != "-- Select Part --" else None
                        st.rerun()
                with cols_calc[1]:
                    qty = st.number_input(f"Qty##{row_key_base}", min_value=1, value=int(row_state['quantity'] or 1), step=1, label_visibility="collapsed", key=f"qty_{row_key_base}")
                    if qty != row_state['quantity']: st.session_state.input_rows[i]['quantity'] = qty
                with cols_calc[2]:
                    if len(st.session_state.input_rows) > 1:
                        if st.button(f"➖##{row_key_base}", key=f"rem_calc_{row_state['id']}"): indices_to_remove.append(i)
            if indices_to_remove:
                for index in sorted(indices_to_remove, reverse=True): del st.session_state.input_rows[index]
                st.rerun()
            if st.button("➕ Add Part Row", key="add_calc_part_row_main"):
                st.session_state.input_rows.append({'id': st.session_state.next_row_id, 'selected_part_name': None, 'selected_part_id': None, 'quantity': 1})
                st.session_state.next_row_id += 1
                st.rerun()

    if st.button("Calculate Order", type="primary", key="btn_calculate_order_main"):
        st.session_state.calculation_results = None; st.session_state.calculation_error = None
        parsed_input_parts, is_valid, errors = parse_dynamic_inputs(st.session_state.input_rows)
        if not is_valid: st.session_state.calculation_error = "Input Error(s):\n" + "\n".join(errors)
        elif not parsed_input_parts: st.session_state.calculation_error = "No valid parts selected."
        else:
            with st.spinner("Calculating..."):
                try:
                    calculator = OrderCalculator(st.session_state.api_client)
                    results = calculator.calculate_orders(parsed_input_parts)
                    st.session_state.calculation_results = results
                    st.success("Calculation complete!")
                except Exception as e:
                    logger.error(f"Calculation failed: {e}", exc_info=True)
                    st.session_state.calculation_error = f"Calculation failed: {str(e)}"
        st.rerun()

    if st.session_state.calculation_error: st.error(st.session_state.calculation_error)
    if st.session_state.calculation_results:
        st.markdown("---"); st.subheader("Calculation Results Display Options")
        st.session_state.show_consumables_toggle_widget = st.checkbox("Show Consumable Parts", value=st.session_state.show_consumables_toggle_widget, key="cb_show_consumables_calc_main")
        st.session_state.show_haip_parts_toggle = st.checkbox("Show Parts from HAIP Solutions GmbH", value=st.session_state.show_haip_parts_toggle, key="cb_show_haip_calc_main")
        
        parts_df = format_parts_to_order_for_display(st.session_state.calculation_results.parts_to_order, st.session_state.config, st.session_state.show_consumables_toggle_widget, st.session_state.show_haip_parts_toggle)
        assemblies_df = format_assemblies_to_build_for_display(st.session_state.calculation_results.subassemblies_to_build, st.session_state.config, st.session_state.show_consumables_toggle_widget, st.session_state.show_haip_parts_toggle)
        
        tab_parts, tab_asm = st.tabs(["Parts to Order", "Subassemblies to Build"])
        with tab_parts:
            if not parts_df.empty: st.dataframe(parts_df, use_container_width=True, column_config={"Part_URL": st.column_config.LinkColumn("Part Name", display_text="🔗", help="Open part in InvenTree")})
            else: st.info("No external parts need to be ordered based on current filters.")
        with tab_asm:
            if not assemblies_df.empty: st.dataframe(assemblies_df, use_container_width=True, column_config={"Part_URL": st.column_config.LinkColumn("Part Name", display_text="🔗", help="Open part in InvenTree")})
            else: st.info("No subassemblies need to be built based on current filters.")

elif app_mode == "Monitoring Tasks":
    st.header("Monitoring Task Management")
    pm: PresetsManager = st.session_state.presets_manager

    if st.button("➕ Add New Monitoring Task", key="btn_add_new_monitor_task_page"):
        st.session_state.show_monitoring_form = True
        st.session_state.editing_task_id = None 
        st.session_state.monitor_form_data = {"name": "", "cron_schedule": "0 9 * * *", "recipients": "", "notify_condition": "on_change", "active": True, "misfire_grace_time": 3600}
        st.session_state.monitor_form_part_rows = [{'ui_id': str(uuid.uuid4()), 'name_or_ipn': '', 'quantity': 1, 'version': ''}]
        st.rerun()

    if st.session_state.show_monitoring_form:
        form_title = "Edit Monitoring Task" if st.session_state.editing_task_id else "Add New Monitoring Task"
        with st.form(key="monitoring_task_form_main", clear_on_submit=False): # clear_on_submit False to handle errors
            st.subheader(form_title)
            form_data = st.session_state.monitor_form_data
            
            form_data["name"] = st.text_input("Task Name", value=form_data.get("name", ""), key="mf_name_main")
            form_data["cron_schedule"] = st.text_input("Cron Schedule", value=form_data.get("cron_schedule", "0 9 * * *"), placeholder="e.g., 0 0 * * *", key="mf_cron_main")
            form_data["recipients"] = st.text_area("Recipients (comma-separated)", value=form_data.get("recipients", ""), placeholder="user1@example.com, user2@example.com", key="mf_recipients_main")
            form_data["notify_condition"] = st.selectbox("Notify On", ["on_change", "always"], index=["on_change", "always"].index(form_data.get("notify_condition", "on_change")), key="mf_notify_main")
            form_data["active"] = st.checkbox("Active", value=form_data.get("active", True), key="mf_active_main")
            form_data["misfire_grace_time"] = st.number_input("Misfire Grace Time (s)", min_value=60, value=form_data.get("misfire_grace_time", 3600), step=60, key="mf_misfire_main")

            st.markdown("**Parts to Monitor:**")
            part_indices_to_remove_monitor = []
            for i, part_row_state in enumerate(st.session_state.monitor_form_part_rows):
                part_row_key = part_row_state['ui_id']
                cols_mon_part = st.columns([3,1,1,1])
                with cols_mon_part[0]: part_row_state['name_or_ipn'] = st.text_input(f"Part Name/IPN##{part_row_key}", value=part_row_state.get('name_or_ipn',''), key=f"mfp_name_ui_{part_row_key}", label_visibility="collapsed", placeholder="Part Name or IPN")
                with cols_mon_part[1]: part_row_state['quantity'] = st.number_input(f"Qty##{part_row_key}", min_value=1, value=int(part_row_state.get('quantity',1)), step=1, key=f"mfp_qty_ui_{part_row_key}", label_visibility="collapsed")
                with cols_mon_part[2]: part_row_state['version'] = st.text_input(f"Version##{part_row_key}", value=part_row_state.get('version',''), key=f"mfp_ver_ui_{part_row_key}", label_visibility="collapsed", placeholder="Version (opt.)")
                with cols_mon_part[3]: 
                    if len(st.session_state.monitor_form_part_rows) > 1:
                        if st.button(f"➖##mfp_rem_ui_{part_row_key}", key=f"mfp_rem_ui_{part_row_key}"): part_indices_to_remove_monitor.append(i)
            if part_indices_to_remove_monitor:
                for index in sorted(part_indices_to_remove_monitor, reverse=True): del st.session_state.monitor_form_part_rows[index]
                st.rerun()
            if st.button("➕ Add Part to Monitor", key="mf_add_part_row_main"):
                st.session_state.monitor_form_part_rows.append({'ui_id': str(uuid.uuid4()), 'name_or_ipn': '', 'quantity': 1, 'version': ''})
                st.rerun()

            submitted = st.form_submit_button("💾 Save Task")
            if submitted:
                parsed_monitoring_parts: List[MonitoringPartItem] = []
                valid_form = True
                for prow_idx, prow in enumerate(st.session_state.monitor_form_part_rows):
                    if not prow['name_or_ipn'].strip() or int(prow['quantity']) <=0:
                        st.error(f"Part row {prow_idx+1}: Name/IPN cannot be empty and quantity must be positive."); valid_form = False; break
                    parsed_monitoring_parts.append(MonitoringPartItem(name_or_ipn=prow['name_or_ipn'], quantity=int(prow['quantity']), version=prow['version'] or None))
                if not form_data["name"].strip(): st.error("Task Name is required."); valid_form = False
                if not form_data["cron_schedule"].strip(): st.error("Cron Schedule is required."); valid_form = False
                if not form_data["recipients"].strip(): st.error("Recipients are required."); valid_form = False
                if not parsed_monitoring_parts and valid_form: st.error("At least one part must be added."); valid_form = False
                
                if valid_form:
                    try:
                        task_data_for_model = {
                            "name": form_data["name"], "parts": parsed_monitoring_parts, "active": form_data["active"],
                            "cron_schedule": form_data["cron_schedule"], 
                            "recipients": [e.strip() for e in form_data["recipients"].split(',') if e.strip()],
                            "notify_condition": form_data["notify_condition"], "misfire_grace_time": form_data["misfire_grace_time"]
                        }
                        if st.session_state.editing_task_id:
                            task_data_for_model["id"] = st.session_state.editing_task_id
                            existing = pm.get_monitoring_list_by_id(st.session_state.editing_task_id)
                            task_data_for_model["last_hash"] = existing.last_hash if existing else None
                            task_to_save = MonitoringList(**task_data_for_model)
                            if pm.update_monitoring_list(st.session_state.editing_task_id, task_to_save): st.success(f"Task '{task_to_save.name}' updated.")
                            else: st.error("Failed to update task.")
                        else:
                            task_to_save = MonitoringList(**task_data_for_model)
                            if pm.add_monitoring_list(task_to_save): st.success(f"Task '{task_to_save.name}' added.")
                            else: st.error("Failed to add task. ID might conflict.")
                        st.session_state.show_monitoring_form = False; st.session_state.editing_task_id = None; st.rerun()
                    except ValidationError as ve: st.error(f"Validation Error: {ve}")
                    except Exception as ex: st.error(f"Error saving task: {ex}")
        
        if st.button("Cancel", key="mf_cancel_btn"):
             st.session_state.show_monitoring_form = False; st.session_state.editing_task_id = None; st.rerun()


    st.markdown("---"); st.subheader("Configured Monitoring Tasks")
    monitoring_tasks = pm.get_monitoring_lists()
    if not monitoring_tasks: st.info("No monitoring tasks configured yet.")
    else:
        task_cols_headers = ["ID", "Name", "Active", "Schedule", "Recipients", "Notify", "Actions"]
        header_cols = st.columns([1, 3, 1, 2, 3, 1, 2])
        for col, h_text in zip(header_cols, task_cols_headers): col.markdown(f"**{h_text}**")

        for task in monitoring_tasks:
            task_row_cols = st.columns([1, 3, 1, 2, 3, 1, 2])
            task_row_cols[0].text(task.id[:8] + "...")
            task_row_cols[1].text(task.name)
            active_label = "✅" if task.active else "❌"
            if task_row_cols[2].button(active_label, key=f"toggle_active_ui_{task.id}", help="Toggle Active State", use_container_width=True):
                if pm.update_monitoring_list(task.id, task.model_copy(update={"active": not task.active})): st.toast(f"Task '{task.name}' toggled.")
                else: st.error(f"Failed to toggle {task.name}")
                st.rerun()
            task_row_cols[3].text(task.cron_schedule)
            task_row_cols[4].caption(", ".join(task.recipients) if task.recipients else "-")
            task_row_cols[5].text(task.notify_condition)
            
            action_buttons_cols = task_row_cols[6].columns(3)
            if action_buttons_cols[0].button("✏️", key=f"edit_ui_{task.id}", help="Edit Task"):
                st.session_state.editing_task_id = task.id
                form_load_data = task.model_dump()
                form_load_data["recipients"] = ", ".join(task.recipients) # Convert list to string for textarea
                st.session_state.monitor_form_data = form_load_data
                st.session_state.monitor_form_part_rows = [{'ui_id': str(uuid.uuid4()), **p.model_dump()} for p in task.parts]
                st.session_state.show_monitoring_form = True; st.rerun()
            if action_buttons_cols[1].button("🗑️", key=f"delete_ui_{task.id}", help="Delete Task"):
                if pm.delete_monitoring_list(task.id): st.toast(f"Task '{task.name}' deleted.")
                else: st.error(f"Failed to delete {task.name}")
                st.rerun()
            if action_buttons_cols[2].button("▶️", key=f"run_ui_{task.id}", help="Run Task Manually"):
                with st.spinner(f"Manually running '{task.name}'..."):
                    try:
                        monitoring_service_globals._config_instance = st.session_state.config
                        monitoring_service_globals._presets_manager_instance = pm
                        monitoring_service_globals._api_client_instance = st.session_state.api_client
                        if monitoring_service_globals._order_calculator_instance is None and st.session_state.api_client:
                             monitoring_service_globals._order_calculator_instance = OrderCalculator(st.session_state.api_client)
                        MonitoringTaskExecutor.run_monitoring_task(task.id)
                        st.toast(f"Task '{task.name}' triggered manually.")
                    except Exception as e:
                        logger.error(f"Error manually running {task.id}: {e}", exc_info=True)
                        st.error(f"Error running task '{task.name}': {e}")
                # No rerun here, toast is sufficient feedback for a background action.

logger.info("Streamlit app script execution finished for this run.")