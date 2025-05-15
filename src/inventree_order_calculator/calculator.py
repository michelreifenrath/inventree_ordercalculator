# Module: src/inventree_order_calculator/calculator.py
# Description: Contains the core logic for BOM explosion and quantity calculations.

import logging
from typing import Union, Optional, List
# Import necessary models
from .models import PartData, BomItemData, InputPart, CalculatedPart, OutputTables # Import more models
# from .api_client import InventreeApiClient, ApiClientError, PartNotFoundError # Not needed yet (mocked)

# Setup logger
logger = logging.getLogger(__name__)

class OrderCalculator:
    """
    Calculates required part quantities based on input assemblies and BOM data.
    """
    # ATTRIBUTE api_client: InventreeApiClient # Dependency will be injected
    # ATTRIBUTE calculated_parts_dict: DICTIONARY[INTEGER, CalculatedPart] # Stores calculated results keyed by part PK
    # Note: Replaces required_parts and processed_parts_cache logic

    def __init__(self, api_client):
        """
        Initializes the OrderCalculator.

        Args:
            api_client: An instance of InventreeApiClient (or a mock).
        """
        self.api_client = api_client
        # self.required_parts = {} # Replaced by calculated_parts_dict logic
        # self.processed_parts_cache = {} # Renamed and stores CalculatedPart
        self.calculated_parts_dict = {} # Initialize dictionary to store CalculatedPart instances

    def _calculate_availability(self, part_data: Union[PartData, CalculatedPart]) -> float: # Accept CalculatedPart too
        """
        Calculates the available quantity for a given part based on its type and stock levels.
        Minimal implementation for the Green phase (handles purchased parts only).
        """
        # Fetch necessary fields from PartData object
        total_in_stock = part_data.total_in_stock
        required_builds = part_data.required_for_build_orders
        required_sales = part_data.required_for_sales_orders
        ordering = part_data.ordering
        building = part_data.building # Now needed for assembly parts

        available: float = 0.0
        committed = required_builds + required_sales

        if part_data.is_purchaseable:
            # Updated calculation: remove '+ ordering'
            available = total_in_stock - committed
            logger.debug(f"Calculated availability for purchased part {part_data.name} (PK: {part_data.pk}): {available}")
        elif part_data.is_assembly:
            # Implement assembly availability calculation
            # stock_base = total_in_stock - committed
            available = total_in_stock - committed # Changed: Removed '+ building'
            logger.debug(f"Calculated availability for assembly part {part_data.name} (PK: {part_data.pk}): {available}")
        else:
             # Handle parts that are neither purchaseable nor assembly
             available = total_in_stock - committed # Default to stock - committed as per pseudocode
             warning_msg = f"Part '{part_data.name}' (PK: {part_data.pk}) is neither purchaseable nor assembly. Calculating availability as stock - commitments."
             logger.warning(warning_msg)
             # This warning is local to _calculate_availability and might not be directly added to output_tables
             # unless output_tables is passed around or this logic is centralized.
             # For now, focusing on warnings in calculate_orders.

        return available

    # Internal recursive function to calculate total required quantities
    def _calculate_required_recursive(self, part_pk: int, quantity_needed_for_parent: float, current_top_level_part_name: str, output_tables_ref: OutputTables):
        """
        Recursively calculates the total required quantity for a part and its sub-components.
        Updates the calculated_parts_dict with results and tracks top-level part association.
        Uses api_client to fetch part data and BOM data.

        Args:
            part_pk: The primary key of the part to calculate requirements for.
            quantity_needed_for_parent: The quantity of this part needed for its direct parent.
            current_top_level_part_name: The name/identifier of the top-level part this requirement originates from.
            output_tables_ref: A reference to the OutputTables instance to append API warnings.
        """
        # --- Get or Create CalculatedPart entry ---
        calculated_part = self.calculated_parts_dict.get(part_pk)
        if not calculated_part:
            # Fetch base PartData if not already processed
            part_data, api_warnings = self.api_client.get_part_data(part_pk)
            if api_warnings:
                output_tables_ref.warnings.extend(api_warnings)
            
            if part_data is None:
                # Warning already added by api_client or a generic one if part_data is None without specific api_warnings
                # Log it here for context within calculator if needed, but primary warning is from api_client
                logger.error(f"Part data for PK {part_pk} not found by API client (see warnings). Cannot process this part or its components further in this branch.")
                return # Cannot proceed without part data

            # Create a new CalculatedPart instance from PartData
            calculated_part = CalculatedPart(
                pk=part_data.pk, name=part_data.name, is_purchaseable=part_data.is_purchaseable,
                is_assembly=part_data.is_assembly, total_in_stock=part_data.total_in_stock,
                required_for_build_orders=part_data.required_for_build_orders,
                required_for_sales_orders=part_data.required_for_sales_orders,
                ordering=part_data.ordering, building=part_data.building,
                is_consumable=part_data.is_consumable, # Propagate is_consumable
                supplier_names=part_data.supplier_names, # Propagate supplier_names
                total_required=0.0, # Initialize calculated fields
                available=0.0,
                to_order=0.0,
                to_build=0.0
                # belongs_to_top_parts is initialized by default_factory=set
            )
            self.calculated_parts_dict[part_pk] = calculated_part
            logger.debug(f"Created CalculatedPart entry for {calculated_part.name} (PK: {part_pk})")

        # --- Update Total Required Quantity and Top-Level Association ---
        calculated_part.total_required += quantity_needed_for_parent
        calculated_part.belongs_to_top_parts.add(current_top_level_part_name)
        logger.debug(f"Updated total_required for {calculated_part.name} (PK: {part_pk}) to {calculated_part.total_required:.2f}. Belongs to: {calculated_part.belongs_to_top_parts}")

        # --- Process BOM if Assembly (Netting Logic) ---
        if calculated_part.is_assembly:
            logger.debug(f"Processing BOM for assembly: {calculated_part.name} (PK: {part_pk})")

            try:
                # --- Netting Logic Start ---
                # Calculate effective availability *before* processing BOM
                effective_availability = (
                    calculated_part.total_in_stock + calculated_part.building -
                    (calculated_part.required_for_build_orders + calculated_part.required_for_sales_orders)
                )
                logger.debug(f"Assembly {part_pk} ({calculated_part.name}): Effective Availability = {effective_availability:.2f} (Stock:{calculated_part.total_in_stock:.2f} + Building:{calculated_part.building:.2f} - ReqBO:{calculated_part.required_for_build_orders:.2f} - ReqSO:{calculated_part.required_for_sales_orders:.2f})")

                # Get the current *accumulated* gross total required for this assembly
                current_gross_total_for_assembly = calculated_part.total_required # Already updated above
                logger.debug(f"Assembly {part_pk} ({calculated_part.name}): Current Accumulated Gross Demand = {current_gross_total_for_assembly:.2f}")

                # Calculate the net demand for this assembly *specific to this path* that needs to be fulfilled by building more
                # Use quantity_needed_for_parent for this specific path, not the accumulated total_required
                net_demand_for_this_path_components = max(0.0, quantity_needed_for_parent - effective_availability)
                logger.debug(f"Assembly {part_pk} ({calculated_part.name}): Net Demand for Components (This Path) = {net_demand_for_this_path_components:.2f} (Max(0, PathDemand:{quantity_needed_for_parent:.2f} - Avail:{effective_availability:.2f}))")
                # --- Netting Logic End ---

                # Fetch BOM items regardless of net_assembly_demand_for_components to ensure all parts are processed
                # for belongs_to_top_parts tracking. The quantity passed down will be zero if net demand is zero.
                bom_items, bom_api_warnings = self.api_client.get_bom_data(part_pk)
                if bom_api_warnings:
                    output_tables_ref.warnings.extend(bom_api_warnings)

                if bom_items is None:
                    # Warning for BOM fetch failure (e.g. API error) should have been added by api_client.
                    logger.error(f"Failed to retrieve BOM for {calculated_part.name} (PK: {part_pk}) (see warnings). Cannot process its subassemblies.")
                    return # Exit BOM processing for this part

                if not bom_items: # Handles empty BOM list (which is valid)
                    # An info/warning about empty BOM might have been added by api_client.get_bom_data
                    # If not, and we want to log it here:
                    # warning_msg = f"Assembly {calculated_part.name} (PK: {part_pk}) has an empty BOM. No sub-components to process."
                    # logger.info(warning_msg) # Or logger.warning
                    # output_tables_ref.warnings.append(warning_msg) # If desired
                    pass # Continue, as empty BOM is not an error stopping processing of the assembly itself

                for item in bom_items:
                    sub_part_pk = item.sub_part
                    quantity_per_assembly = item.quantity
                    bom_item_is_consumable = item.is_consumable # Get from BomItemData

                    if not isinstance(sub_part_pk, int) or not isinstance(quantity_per_assembly, (int, float)):
                        logger.warning(f"BOM item for assembly {part_pk} has invalid sub-part PK ({sub_part_pk}) or quantity ({quantity_per_assembly}). Skipping item.")
                        continue
                    
                    # Ensure sub-part is in calculated_parts_dict before trying to update its consumable flag
                    # This recursive call will create it if it doesn't exist.
                    # We need to handle the consumable flag update *after* the recursive call ensures the sub-part's
                    # CalculatedPart object exists and its own global 'is_consumable' status is initialized.

                    # Calculate quantity needed for this sub-part based on the NET demand of the parent *for this specific path*
                    # If net_demand_for_this_path_components is 0, sub_part_quantity_to_pass_down will be 0.
                    sub_part_quantity_to_pass_down = net_demand_for_this_path_components * quantity_per_assembly
                    logger.debug(f"  Propagating demand to component {sub_part_pk}: {sub_part_quantity_to_pass_down:.2f} (NetParentDemandForPath:{net_demand_for_this_path_components:.2f} * BOMQty:{quantity_per_assembly:.2f}) for top-level {current_top_level_part_name}")

                    # Recursive call for the sub-component, passing the SAME top-level part name.
                    # This ensures the sub-component is added to calculated_parts_dict and its belongs_to_top_parts is updated,
                    # even if the quantity_needed_for_parent (sub_part_quantity_to_pass_down) is zero.
                    self._calculate_required_recursive(sub_part_pk, sub_part_quantity_to_pass_down, current_top_level_part_name, output_tables_ref)

                    # After the recursive call, the sub_part_pk will be in calculated_parts_dict.
                    # Now, update its is_consumable flag if this BOM item marks it as such.
                    if bom_item_is_consumable:
                        if sub_part_pk in self.calculated_parts_dict:
                            # If any BOM line marks it as consumable, the CalculatedPart becomes consumable for filtering.
                            if not self.calculated_parts_dict[sub_part_pk].is_consumable:
                                logger.debug(f"Marking sub-part {sub_part_pk} as consumable due to BOM item in assembly {part_pk}.")
                                self.calculated_parts_dict[sub_part_pk].is_consumable = True
                        else:
                            # This case should ideally not happen if _calculate_required_recursive works correctly
                            logger.error(f"Sub-part PK {sub_part_pk} not found in calculated_parts_dict after recursive call. Cannot update consumable status from BOM item.")
            except Exception as e:
                logger.exception(f"Unexpected error processing BOM for {calculated_part.name} (PK: {part_pk}): {e}")

    # Public method to start the calculation process
    def calculate_orders(self, input_parts: List[InputPart]) -> OutputTables:
        """
        Calculates the required orders and builds based on a list of input parts.
        """
        logger.info("Starting order calculation...")
        output_tables = OutputTables() # Initialize OutputTables early
        self.calculated_parts_dict = {} # Reset dictionary for new calculation

        # 1. Calculate Total Required Quantities via Recursive BOM Explosion
        for input_part in input_parts:
            try:
                # Resolve identifier to PK and get initial PartData
                # Note: In a real scenario, might need api_client.find_part here if identifier is name
                # For now, assume identifier is PK
                part_pk = int(input_part.part_identifier) # Assuming identifier is PK for now

                # Fetch top-level part data to get its name for tracking
                # Check if CalculatedPart for this top-level part already exists (e.g., if it's also a sub-component)
                # If not, fetch its base PartData to create it.
                top_level_name = None
                if part_pk not in self.calculated_parts_dict:
                    top_level_part_data, api_warnings = self.api_client.get_part_data(part_pk)
                    if api_warnings:
                        output_tables.warnings.extend(api_warnings)

                    if top_level_part_data:
                        top_level_name = top_level_part_data.name
                        # Create the CalculatedPart instance for the top-level part now
                        # This ensures it's in the dict before the first recursive call for it.
                        calculated_top_part = CalculatedPart(
                            pk=top_level_part_data.pk, name=top_level_part_data.name,
                            is_purchaseable=top_level_part_data.is_purchaseable, is_assembly=top_level_part_data.is_assembly,
                            total_in_stock=top_level_part_data.total_in_stock,
                            required_for_build_orders=top_level_part_data.required_for_build_orders,
                            required_for_sales_orders=top_level_part_data.required_for_sales_orders,
                            ordering=top_level_part_data.ordering, building=top_level_part_data.building,
                            is_consumable=top_level_part_data.is_consumable, # Propagate is_consumable
                            supplier_names=top_level_part_data.supplier_names, # Propagate supplier_names
                            total_required=0.0, available=0.0, to_order=0.0, to_build=0.0
                        )
                        self.calculated_parts_dict[part_pk] = calculated_top_part
                        logger.debug(f"Primed calculated_parts_dict for top-level part {top_level_name} (PK: {part_pk})")
                    else:
                        # Warning for part not found should have been added by api_client.get_part_data
                        # and collected into output_tables.warnings.
                        # Log here for calculator context if needed.
                        logger.error(f"Top-level part identifier '{input_part.part_identifier}' (PK: {part_pk}) not found by API (see warnings). Skipping this input part.")
                        # output_tables.warnings.append(warning_msg) # Already handled by api_client
                        continue # Skip this input part
                else:
                    # Part already exists in dict, get its name
                    top_level_name = self.calculated_parts_dict[part_pk].name

                if top_level_name is None:
                    warning_msg = f"Could not determine name for top-level part PK {part_pk}. This indicates an issue. Using placeholder."
                    logger.error(warning_msg)
                    output_tables.warnings.append(warning_msg)
                    top_level_name = f"UNKNOWN_PK_{part_pk}"

                logger.info(f"Processing top-level part: {top_level_name} (PK: {part_pk}), Quantity: {input_part.quantity_to_build}")

                # Call recursive function with the top-level part name and output_tables reference
                self._calculate_required_recursive(part_pk, input_part.quantity_to_build, top_level_name, output_tables)

            except ValueError:
                 warning_msg = f"Invalid part identifier '{input_part.part_identifier}'. Must be an integer PK. Skipping."
                 logger.error(warning_msg)
                 output_tables.warnings.append(warning_msg)
            except Exception as e:
                warning_msg = f"Unexpected error processing input '{input_part.part_identifier}': {e}. Skipping."
                logger.exception(warning_msg) # Keep logger.exception for full traceback
                output_tables.warnings.append(warning_msg)

        # 2. Calculate Available, To Order, To Build for each unique part in calculated_parts_dict
        # output_tables is already initialized
        for part_pk, calculated_part in self.calculated_parts_dict.items():
            try:
                # Calculate Available Quantity (using the part itself)
                calculated_part.available = self._calculate_availability(calculated_part)

                # Calculate To Order / To Build
                if calculated_part.is_purchaseable:
                    # Calculate how much needs to be ordered
                    # Available already considers stock, commitments, and ordering/building
                    # We need total_required - (available + on_order)
                    # Simplified: total_required - available (where available includes stock - committed)
                    # Need to factor in 'ordering' quantity here for purchased parts
                    to_order_value = calculated_part.total_required - calculated_part.available
                    calculated_part.to_order = max(0.0, to_order_value)
                    calculated_part.to_build = 0.0 # Purchaseable parts are not built
                    logger.debug(f"Part {part_pk} (Purch): Req={calculated_part.total_required:.2f}, Avail={calculated_part.available:.2f}, Ord={calculated_part.ordering:.2f} -> ToOrder={calculated_part.to_order:.2f}")

                elif calculated_part.is_assembly:
                    # Calculate how much needs to be built
                    # Need to factor in 'building' quantity here for assemblies
                    effective_supply = calculated_part.available + calculated_part.building
                    to_build = calculated_part.total_required - effective_supply
                    calculated_part.to_build = max(0.0, to_build) # Ensure non-negative
                    calculated_part.to_order = 0.0 # Assemblies are built, not ordered
                    logger.debug(f"Part {part_pk} (Asm): Req={calculated_part.total_required:.2f}, Avail={calculated_part.available:.2f}, Build={calculated_part.building:.2f} -> ToBuild={calculated_part.to_build:.2f}")

                else:
                    # Neither purchaseable nor assembly
                    warning_msg = f"Part '{calculated_part.name}' (PK: {part_pk}) is neither purchaseable nor an assembly. Cannot be ordered or built through this process. Setting to_order and to_build to 0."
                    logger.warning(warning_msg)
                    output_tables.warnings.append(warning_msg)
                    calculated_part.to_order = 0.0
                    calculated_part.to_build = 0.0

                if part_pk == 1314:
                    logger.info(f"--- DEBUGGING PART 1314 (PK: {part_pk}) ---")
                    logger.info(f"  Name: {calculated_part.name}")
                    logger.info(f"  Total Required (Needed): {calculated_part.total_required:.2f}")
                    logger.info(f"  Total In Stock: {calculated_part.total_in_stock:.2f}")
                    logger.info(f"  Required for Build Orders: {calculated_part.required_for_build_orders:.2f}")
                    logger.info(f"  Required for Sales Orders: {calculated_part.required_for_sales_orders:.2f}")
                    logger.info(f"  Calculated Available: {calculated_part.available:.2f}")
                    logger.info(f"  Calculated To Order: {calculated_part.to_order:.2f}")
                    logger.info(f"  Calculated To Build: {calculated_part.to_build:.2f}")
                    logger.info(f"  Is Purchaseable: {calculated_part.is_purchaseable}")
                    logger.info(f"  Is Assembly: {calculated_part.is_assembly}")
                    logger.info(f"  Ordering (On Order): {calculated_part.ordering:.2f}")
                    logger.info(f"  Building (WIP): {calculated_part.building:.2f}")
                    logger.info(f"--- END DEBUGGING PART 1314 ---")

                # 3. Add to output tables if needed
                if calculated_part.to_order > 0:
                    output_tables.parts_to_order.append(calculated_part)
                elif calculated_part.is_assembly and \
                     (calculated_part.building > 0 or \
                      calculated_part.to_build > 0):
                    output_tables.subassemblies_to_build.append(calculated_part)

            except Exception as e:
                 warning_msg = f"Unexpected error calculating final quantities for part {calculated_part.name} (PK: {part_pk}): {e}"
                 logger.exception(warning_msg) # Keep logger.exception for full traceback
                 output_tables.warnings.append(warning_msg)

        logger.info(f"Calculation complete. Parts to order: {len(output_tables.parts_to_order)}, Subassemblies to build: {len(output_tables.subassemblies_to_build)}")
        # Sort results for consistent output (optional, but good practice)
        output_tables.parts_to_order.sort(key=lambda p: p.name)
        output_tables.subassemblies_to_build.sort(key=lambda p: p.name)
        return output_tables