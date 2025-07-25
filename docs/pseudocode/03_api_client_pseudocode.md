# Module: src/inventree_order_calculator/api_client.py
# Description: Handles interaction with the InvenTree API using the inventree SDK.

# Dependencies: inventree (SDK), config module, models module, time (for retries), logging

// Import necessary libraries and modules
IMPORT InventreeAPI from inventree.api
IMPORT Part from inventree.part // Assuming Part class exists for type hinting
IMPORT BomItem from inventree.bom // Assuming BomItem class exists
IMPORT get_config from .config
IMPORT ConfigurationError from .config
IMPORT PartData from .models
IMPORT logging
IMPORT time

// Define constants for retries
CONSTANT MAX_RETRIES = 3
CONSTANT RETRY_DELAY_SECONDS = 2 // Initial delay, could use exponential backoff

// Setup logger
logger = logging.getLogger(__name__)

// Define custom exceptions for API errors
CLASS ApiClientError(Exception): PASS
CLASS PartNotFoundError(ApiClientError): PASS
CLASS ApiConnectionError(ApiClientError): PASS
CLASS ApiAuthenticationError(ApiClientError): PASS

CLASS InventreeApiClient:
    ATTRIBUTE api: InventreeAPI | NONE = NONE
    ATTRIBUTE config: Configuration

    CONSTRUCTOR __init__(config: Configuration):
        self.config = config
        CALL self.connect()

    // Method to establish connection to the InvenTree API
    FUNCTION connect():
        TRY
            logger.info(f"Connecting to InvenTree API at {self.config.inventree_api_url}")
            self.api = InventreeAPI(self.config.inventree_api_url, token=self.config.inventree_api_token)
            // Perform a simple check to verify connection and authentication
            // Example: Fetch categories or perform a similar lightweight request
            // self.api.listCategories() // Or similar SDK call
            logger.info("Successfully connected to InvenTree API.")
            // TEST: Successful API connection and authentication
        CATCH AuthenticationError as e: // Assuming SDK raises specific auth error
            logger.error(f"Authentication failed: {e}")
            RAISE ApiAuthenticationError(f"Authentication failed for InvenTree API at {self.config.inventree_api_url}")
            // TEST: Handling of API authentication failure
        CATCH ConnectionError as e: // Assuming SDK raises specific connection error
            logger.error(f"Connection failed: {e}")
            RAISE ApiConnectionError(f"Could not connect to InvenTree API at {self.config.inventree_api_url}")
            // TEST: Handling of API unavailability (initial connection)
        CATCH Exception as e: // Catch other potential SDK errors during connection
            logger.error(f"An unexpected error occurred during API connection: {e}")
            RAISE ApiClientError(f"An unexpected error occurred connecting to InvenTree API: {e}")

    // Method to fetch part data with retries
    FUNCTION get_part_data(part_identifier: STRING) -> PartData | NONE:
        // Attempt to find the part by PK (if integer) or IPN/Name (if string)
        // The SDK might have specific methods like Part.list(IPN=...) or Part.retrieve(pk=...)
        // This pseudocode assumes a generic find_part function for simplicity.

        FOR attempt FROM 1 TO MAX_RETRIES:
            TRY
                logger.debug(f"Attempt {attempt}: Fetching data for part '{part_identifier}'...")
                // --- SDK Interaction ---
                // Example: Find part by IPN or PK. Adjust based on actual SDK capabilities.
                part_list = Part.list(self.api, IPN=part_identifier) // Or search by name/PK
                IF NOT part_list:
                    part_list = Part.list(self.api, name=part_identifier) // Try by name if IPN fails
                // Add logic here if identifier could be PK (integer) -> Part.retrieve(self.api, pk=...)

                IF NOT part_list:
                    logger.warning(f"Part '{part_identifier}' not found in InvenTree.")
                    RAISE PartNotFoundError(f"Part '{part_identifier}' not found.")
                    // TEST: Handling of a single invalid part number in input

                // Assuming the first match is the correct one if multiple found by name
                inventree_part = part_list[0]
                logger.debug(f"Found part PK: {inventree_part.pk}")

                // Fetch detailed stock information - SDK might bundle this or require separate calls
                // Example: inventree_part.getStockData() or access attributes directly
                // Ensure all required fields from Specification.md (Section 3.1) are fetched.
                // Handle potential None values from API, defaulting to 0.0
                total_in_stock = inventree_part.total_stock OR 0.0 // Use actual SDK attribute names
                ordering = inventree_part.on_order OR 0.0
                building = inventree_part.building OR 0.0 // Check SDK for correct field name
                required_for_builds = inventree_part.allocated_to_build_orders OR 0.0 // Check SDK name
                required_for_sales = inventree_part.allocated_to_sales_orders OR 0.0 // Check SDK name

                // Create and return PartData object
                part_data = PartData(
                    pk=inventree_part.pk,
                    ipn=inventree_part.IPN,
                    name=inventree_part.name,
                    description=inventree_part.description,
                    is_purchaseable=inventree_part.purchaseable,
                    is_assembly=inventree_part.assembly,
                    total_in_stock=total_in_stock,
                    ordering=ordering,
                    building=building,
                    required_for_build_orders=required_for_builds,
                    required_for_sales_orders=required_for_sales
                )
                // TEST: Handling of null/missing numerical values from API for stock/order fields (covered in PartData model init)
                // TEST: Successful fetching of part data including stock/order info
                RETURN part_data

            CATCH PartNotFoundError as e: // Catch specific error if raised internally
                RAISE e // Re-raise immediately, no retry needed for 'not found'
            CATCH ApiAuthenticationError | ApiConnectionError as e: // Catch errors that might resolve on retry
                logger.warning(f"API error on attempt {attempt} for part '{part_identifier}': {e}. Retrying in {RETRY_DELAY_SECONDS}s...")
                time.sleep(RETRY_DELAY_SECONDS * (2**(attempt-1))) // Exponential backoff
            CATCH Exception as e: // Catch other unexpected SDK errors
                logger.error(f"Unexpected SDK error on attempt {attempt} for part '{part_identifier}': {e}")
                time.sleep(RETRY_DELAY_SECONDS * (2**(attempt-1))) // Exponential backoff
        ENDFOR

        // If all retries fail
        logger.error(f"Failed to fetch data for part '{part_identifier}' after {MAX_RETRIES} attempts.")
        RAISE ApiClientError(f"Failed to fetch data for part '{part_identifier}' after multiple retries.")
        // TEST: Handling of API unavailability after retries

    // Method to fetch BOM items for a given part PK with retries
    FUNCTION get_bom_items(part_pk: INTEGER) -> LIST[BomItem]:
        FOR attempt FROM 1 TO MAX_RETRIES:
            TRY
                logger.debug(f"Attempt {attempt}: Fetching BOM for part PK {part_pk}...")
                // --- SDK Interaction ---
                // Use the SDK to get the BOM for the part PK
                // Example: BomItem.list(self.api, assembly=part_pk)
                part = Part.retrieve(self.api, pk=part_pk) // Need the Part object first?
                IF NOT part.assembly:
                    logger.debug(f"Part PK {part_pk} is not an assembly, returning empty BOM.")
                    RETURN [] // Not an assembly, return empty list

                bom_items = part.getBomItems() // Or BomItem.list(self.api, assembly=part_pk)
                IF bom_items IS NONE: // Check if SDK returns None for empty BOM
                   bom_items = []

                logger.debug(f"Found {len(bom_items)} BOM items for part PK {part_pk}.")
                // TEST: Successful fetching of BOM items
                // TEST: Handling of a part missing an expected BOM (returns empty list)
                RETURN bom_items // Return the list of BOM items (SDK objects)

            CATCH ApiAuthenticationError | ApiConnectionError as e:
                logger.warning(f"API error on attempt {attempt} fetching BOM for PK {part_pk}: {e}. Retrying...")
                time.sleep(RETRY_DELAY_SECONDS * (2**(attempt-1)))
            CATCH Exception as e:
                logger.error(f"Unexpected SDK error on attempt {attempt} fetching BOM for PK {part_pk}: {e}")
                time.sleep(RETRY_DELAY_SECONDS * (2**(attempt-1)))
        ENDFOR

        logger.error(f"Failed to fetch BOM for part PK {part_pk} after {MAX_RETRIES} attempts.")
        RAISE ApiClientError(f"Failed to fetch BOM for part PK {part_pk} after multiple retries.")
        // TEST: Handling API errors during BOM fetching after retries