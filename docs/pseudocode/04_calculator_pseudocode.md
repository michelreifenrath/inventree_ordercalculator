# Module: src/inventree_order_calculator/calculator.py
# Description: Contains the core logic for BOM explosion and quantity calculations.

# Dependencies: api_client module, models module, logging

// Import necessary modules and classes
IMPORT InventreeApiClient from .api_client
IMPORT ApiClientError, PartNotFoundError from .api_client
IMPORT InputPart, PartData, CalculatedPart, OutputTables from .models
IMPORT logging

// Setup logger
logger = logging.getLogger(__name__)

// Define the main calculator class
CLASS OrderCalculator:
    ATTRIBUTE api_client: InventreeApiClient
    ATTRIBUTE required_parts: DICTIONARY[INTEGER, FLOAT] // Key: Part PK, Value: Total Required Quantity
    ATTRIBUTE processed_parts_cache: DICTIONARY[INTEGER, PartData] // Cache fetched part data

    CONSTRUCTOR __init__(api_client: InventreeApiClient):
        self.api_client = api_client
        self.required_parts = {}
        self.processed_parts_cache = {}

    // Public method to start the calculation process
    FUNCTION calculate_orders(input_parts: LIST[InputPart]) -> OutputTables:
        logger.info("Starting order calculation...")
        self.required_parts = {} // Reset for new calculation
        self.processed_parts_cache = {} // Reset cache

        // 1. Calculate Total Required Quantities via Recursive BOM Explosion
        FOR input_part IN input_parts:
            TRY
                // Fetch top-level part data first to get its PK
                top_level_part_data = self._get_part_data_cached(input_part.part_identifier)
                IF top_level_part_data IS NONE:
                    // Error already logged in _get_part_data_cached if PartNotFoundError
                    CONTINUE // Skip this input part if not found

                logger.info(f"Processing top-level part: {top_level_part_data.name} (PK: {top_level_part_data.pk}), Quantity: {input_part.quantity_to_build}")
                CALL self._calculate_required_recursive(top_level_part_data.pk, input_part.quantity_to_build)

            CATCH PartNotFoundError as e:
                logger.error(f"Skipping input '{input_part.part_identifier}': {e}")
                // AC8: Handles invalid input part numbers gracefully (logs error, skips part)
            CATCH ApiClientError as e:
                logger.error(f"API error processing '{input_part.part_identifier}': {e}. Aborting calculation for this part.")
                // Handle API errors during initial part fetch if necessary
            CATCH Exception as e:
                logger.exception(f"Unexpected error processing input '{input_part.part_identifier}': {e}")

        // 2. Calculate Available, To Order, To Build for each unique required part
        calculated_results = []
        FOR part_pk, total_required IN self.required_parts.items():
            TRY
                part_data = self.processed_parts_cache.get(part_pk)
                IF part_data IS NONE:
                    // This shouldn't happen if _calculate_required_recursive worked correctly
                    logger.error(f"Internal error: Part data for PK {part_pk} not found in cache.")
                    CONTINUE

                calculated_part = CalculatedPart(part_data)
                calculated_part.total_required = total_required

                // Calculate Available Quantity
                calculated_part.available = self._calculate_availability(part_data)
                // TEST: Calculation of available quantity (covered by specific part type tests below)

                // Calculate To Order / To Build using the final (potentially netted) total_required
                IF part_data.is_purchaseable:
                    // To Order = Needed - Available (Physical Stock - Commitments)
                    // 'ordering' is informational, not subtracted here per updated spec
                    to_order = total_required - calculated_part.available
                    calculated_part.to_order = max(0.0, to_order)
                    // TEST: Calculation of 'To Order' when required exceeds available
                    // TEST: Calculation of 'To Order' when available meets or exceeds required
                ELSE IF part_data.is_assembly:
                     // To Build = Needed - (Available + In Production)
                    to_build = total_required - (calculated_part.available + part_data.building)
                    calculated_part.to_build = max(0.0, to_build)
                    // TEST: Calculation of 'To Build' when required exceeds available + in_production
                    // TEST: Calculation of 'To Build' when available + in_production meets or exceeds required
                ELSE:
                    // Part is neither purchaseable nor assembly? Log warning.
                    logger.warning(f"Part '{part_data.name}' (PK: {part_pk}) is neither purchaseable nor an assembly. Cannot calculate 'To Order' or 'To Build'.")


                calculated_results.append(calculated_part)

            CATCH Exception as e:
                 logger.exception(f"Unexpected error calculating final quantities for part PK {part_pk}: {e}")


        // 3. Separate results into two lists for output
        output_tables = OutputTables()
        FOR result IN calculated_results:
            IF result.is_purchaseable AND result.to_order > 0:
                output_tables.parts_to_order.append(result)
            ELSE IF result.is_assembly AND (result.to_build > 0 OR result.part_data.building > 0):
                output_tables.subassemblies_to_build.append(result)

        logger.info(f"Calculation complete. Parts to order: {len(output_tables.parts_to_order)}, Subassemblies to build: {len(output_tables.subassemblies_to_build)}")
        RETURN output_tables

    // Internal helper to get part data, using cache
    FUNCTION _get_part_data_cached(part_identifier: STRING | INTEGER) -> PartData | NONE:
        // Check cache first (assuming identifier is PK if integer, else IPN/Name)
        // Simple cache check by identifier string/int might not be robust if mixing types.
        // Better: Always resolve identifier to PK via API first if not already PK.
        // For pseudocode simplicity, assume identifier is unique and cacheable.

        // If identifier is PK and in cache:
        IF isinstance(part_identifier, INTEGER) AND part_identifier IN self.processed_parts_cache:
             RETURN self.processed_parts_cache[part_identifier]

        // If not in cache or identifier is not PK, fetch from API
        TRY
            part_data = self.api_client.get_part_data(part_identifier)
            IF part_data IS NOT NONE:
                self.processed_parts_cache[part_data.pk] = part_data // Cache by PK
            RETURN part_data
        CATCH PartNotFoundError as e:
             logger.warning(f"{e}") // Log warning here, let caller handle skipping/error
             RAISE e // Re-raise to allow caller to handle
        CATCH ApiClientError as e:
             logger.error(f"API Client error fetching part '{part_identifier}': {e}")
             RAISE e // Re-raise


    // Internal recursive function to calculate total required quantities
    # Internal recursive function to calculate total required quantities, incorporating netting
    FUNCTION _calculate_required_recursive(part_pk: INTEGER, quantity_needed: FLOAT):
        # TEST: Calculation of total required quantity for a simple BOM (base case)
        # TEST: Calculation of total required quantity for a multi-level BOM (recursive step)
        # TEST: Netting logic correctly reduces component demand when assembly is available

        # Fetch part data (use cache)
        part_data = self._get_part_data_cached(part_pk)
        IF part_data IS NONE:
            # Error already logged by _get_part_data_cached
            RETURN # Cannot proceed without part data

        # Add to total required quantity for this part
        # This stores the *gross* requirement before considering this part's own availability
        # or the availability of parent assemblies (netting happens before recursive call)
        current_total = self.required_parts.get(part_pk, 0.0)
        self.required_parts[part_pk] = current_total + quantity_needed
        logger.debug(f"Gross required quantity for {part_data.name} (PK: {part_pk}): {self.required_parts[part_pk]}")


        # If the part is an assembly, process its BOM and apply netting
        IF part_data.is_assembly:
            logger.debug(f"Processing BOM for assembly: {part_data.name} (PK: {part_pk})")

            # --- Netting Logic Start ---
            # Calculate effective availability of this assembly
            assembly_available = self._calculate_availability(part_data) # Stock - Commitments
            assembly_effective_availability = assembly_available + part_data.building # Include In Production

            # Calculate how much of the current demand can be met by this assembly's effective stock
            demand_covered_by_assembly = min(quantity_needed, max(0.0, assembly_effective_availability))

            # Calculate the remaining demand that needs to be fulfilled by components
            net_assembly_demand_for_components = quantity_needed - demand_covered_by_assembly
            logger.debug(f"Assembly {part_data.name}: Needed={quantity_needed}, EffectiveAvail={assembly_effective_availability}, Covered={demand_covered_by_assembly}, NetDemandForComponents={net_assembly_demand_for_components}")
            # --- Netting Logic End ---

            TRY
                bom_items = self.api_client.get_bom_items(part_pk)
                # TEST: Handling of a part missing an expected BOM (get_bom_items returns empty list)

                FOR item IN bom_items:
                    # Get sub-part PK and quantity per assembly from BOM item
                    sub_part_pk = item.sub_part # Assuming sub_part is the PK
                    quantity_per_assembly = item.quantity

                    IF sub_part_pk IS NONE OR quantity_per_assembly IS NONE:
                         logger.warning(f"BOM item for assembly {part_pk} has missing sub-part PK or quantity. Skipping item.")
                         CONTINUE

                    # Calculate quantity needed for this sub-part BASED ON NET DEMAND for the assembly
                    # Even if net_assembly_demand_for_components is 0, we still recurse to capture the part itself
                    # and allow its own stock levels to be checked later.
                    sub_part_quantity_needed = net_assembly_demand_for_components * quantity_per_assembly

                    # Recursively call for the sub-part with the potentially reduced (netted) quantity
                    CALL self._calculate_required_recursive(sub_part_pk, sub_part_quantity_needed)

            CATCH ApiClientError as e:
                logger.error(f"API error fetching BOM for {part_data.name} (PK: {part_pk}): {e}. Cannot process subassemblies.")
                # Decide: Halt? Or just skip subassembly processing for this part? Skipping for now.
            CATCH Exception as e:
                 logger.exception(f"Unexpected error processing BOM for {part_data.name} (PK: {part_pk}): {e}")
        ELSE:
             # If it's a purchased part, no BOM processing needed at this level.
             logger.debug(f"Part {part_data.name} (PK: {part_pk}) is not an assembly, stopping recursion branch.")


    // Internal function to calculate available quantity based on part type
    FUNCTION _calculate_availability(part_data: PartData) -> FLOAT:
        // Fetch necessary fields (already in PartData object)
        total_in_stock = part_data.total_in_stock
        required_builds = part_data.required_for_build_orders
        required_sales = part_data.required_for_sales_orders
        ordering = part_data.ordering
        building = part_data.building

        available: FLOAT = 0.0

        // Apply formula based on updated Specification.md Section 6
        // Available = Stock on hand minus immediate commitments (Build/Sales Orders)
        // This value does NOT include 'ordering' or 'building' yet.
        committed = required_builds + required_sales
        available = total_in_stock - committed

        // The 'available' calculation is now the same regardless of type,
        // representing physical stock minus commitments.
        // 'ordering' and 'building' are factored in later when calculating 'to_order'/'to_build'.
        // TEST: Calculation of available quantity (stock - commitments)

        logger.debug(f"Calculated availability for {part_data.name} (PK: {part_data.pk}): {available}")
        RETURN available