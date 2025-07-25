# Inventree Order Calculator Specification

## 1. Introduction

This document outlines the specifications for the Inventree Order Calculator, a tool designed to determine required parts and subassemblies for manufacturing based on input orders and current InvenTree stock levels.

## 2. Objectives

*   To accurately calculate the total number of individual components and subassemblies required to fulfill a given set of top-level assembly orders.
*   To compare required quantities against current stock levels in InvenTree, considering existing build orders, sales orders, and parts/subassemblies already on order or in production.
*   To generate clear, actionable lists of:
    *   Parts that need to be ordered.
    *   Subassemblies that need tobe built.
*   To provide a command-line interface (CLI) for ease of use.

## 3. Scope

### 3.1. In Scope

*   Input: A list of top-level part numbers and the quantity to be built for each.
*   Processing:
    *   Recursive Bill of Materials (BOM) explosion for all specified top-level parts and their subassemblies down to the lowest level.
    *   Fetching relevant stock and order data from an InvenTree instance via its API. This includes:
        *   `total_in_stock`
        *   `ordering` (for purchased parts)
        *   `building` (for subassemblies)
        *   `required_for_build_orders`
        *   `required_for_sales_orders`
        *   `consumable` (boolean indicating if the part is a consumable)
        *   `supplier_names` (list of strings, names of suppliers for the part)
    *   Calculation of 'Available' quantities based on the logic defined in section 6.
    *   Calculation of 'To Order' (for purchased parts) and 'To Build' (for subassemblies).
    *   Filtering of consumable parts from output tables based on UI/CLI options.
    *   Filtering of parts from "HAIP Solutions GmbH" based on UI/CLI options.
*   Output:
    *   Two separate markdown-formatted tables:
        1.  **Parts to Order:** Details for components that need to be purchased.
        2.  **Subassemblies to Build:** Details for subassemblies that need to be manufactured internally.
*   Configuration:
    *   InvenTree API URL and authentication token will be configurable via environment variables or a configuration file (not hard-coded).

### 3.2. Out of Scope

*   Directly placing purchase orders or build orders in InvenTree.
*   User interface beyond a command-line tool.
*   Real-time stock updates (calculations are based on a snapshot at the time of execution).
*   Handling multiple InvenTree instances simultaneously.
*   Complex supplier management or cost calculation.

## 4. Inputs

### 4.1. Primary Input

*   A list of part numbers and their corresponding quantities to be built.
    *   Format: Direct command-line arguments like `PART_IDENTIFIER:QUANTITY PART_IDENTIFIER:QUANTITY ...`.
*   Optional CLI flags:
    *   `--hide-consumables`: If present, consumable parts will be excluded from the output tables.
    *   `--hide-haip-parts`: If present, parts supplied by "HAIP Solutions GmbH" will be excluded.
    *   `--hide-optional-parts`: If present, parts marked as optional in the BOM will be excluded from the output tables.

### 4.2. Configuration Input

*   InvenTree API URL (e.g., `INVENTREE_API_URL` environment variable).
*   InvenTree API Token (e.g., `INVENTREE_API_TOKEN` environment variable).

## 5. Outputs

### 5.1. Parts to Order Table (Markdown)

| Part ID | Optional | Part Name | Needed | Total In Stock | Required for Build Orders | Required for Sales Orders | Available | To Order | On Order |
|---|---|---|---|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

### 5.2. Subassemblies to Build Table (Markdown)

| Part ID | Optional | Part Name | Needed | Total In Stock | Required for Build Orders | Required for Sales Orders | Available | In Production | To Build |
|---|---|---|---|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

### 5.3. Log Output

*   The tool should provide informative log messages, including:
    *   Progress of BOM explosion.
    *   Parts being processed.
    *   Any errors encountered (e.g., API connection issues, invalid part numbers).
    *   Warnings generated during calculation (e.g., part not found, empty BOM, part neither purchaseable nor assembly) will also be displayed in the Streamlit UI if applicable.

### 5.4. Table Entry Criteria

*   **Parts to Order Table:** A purchasable part will appear in the "Parts to Order" list if its calculated `To Order` quantity is greater than 0.
*   **Subassemblies to Build Table:** A subassembly will appear in the "Subassemblies to Build" list if its calculated `To Build` quantity is greater than 0, OR if its `In Production` quantity (`building`) is greater than 0 (even if the `Total Required` ("Needed") for the current calculation run is 0). This ensures visibility of ongoing production efforts.
### 6.1. Data Models

The core internal data structures used by the calculator include:

*   **`PartData`**: Represents data fetched directly from InvenTree for a part.
    *   `pk: int` - Primary key of the part.
    *   `name: str` - Name of the part.
    *   `is_purchaseable: bool` - True if the part can be purchased.
    *   `is_assembly: bool` - True if the part is an assembly (has a BOM).
    *   `is_consumable: bool` - True if the part is a consumable.
    *   `total_in_stock: float` - Total quantity currently in stock.
    *   `required_for_build_orders: float` - Stock committed to existing build orders.
    *   `required_for_sales_orders: float` - Stock committed to existing sales orders.
    *   `ordering: float` - Quantity currently on order (for purchaseable parts).
    *   `building: float` - Quantity currently in production (for assemblies).
    *   `supplier_names: List[str]` - List of supplier names for the part.

*   **`CalculatedPart`**: Extends `PartData` with calculated values during the BOM explosion and final calculation.
    *   Inherits all fields from `PartData`.
    *   `is_consumable: bool` - Propagated from `PartData`.
    *   `supplier_names: List[str]` - Propagated from `PartData`.
    *   `total_required: float` - Total gross quantity of this part needed for the input top-level assemblies, *after* netting logic from parent assemblies.
    *   `available: float` - Calculated available stock (see formula below).
    *   `to_order: float` - Calculated quantity to order (for purchaseable parts).
    *   `to_build: float` - Calculated quantity to build (for assemblies).
    *   `belongs_to_top_parts: Set[str]` - A set of names of the top-level input parts that this part contributes to.
## 6. Core Logic & Calculations

1.  **Total Required (Benötigt):** For each component/subassembly, sum the total quantity needed to produce the defined number of desired top-level products. This involves traversing the BOMs recursively.
    *   `// TEST: Calculation of total required quantity for a simple BOM`
    *   `// TEST: Calculation of total required quantity for a multi-level BOM`
    *   **Netting Logic:** The `Total Required` (Needed / "Ben. f. Eingabe") for a component is calculated *after* considering the effective availability of its parent assembly. If a parent assembly has sufficient effective stock (considering its own stock, commitments, and incoming production/orders) to cover the demand for it, the `Total Required` passed down to its components is reduced proportionally or to zero. However, *all* components are still processed individually later in the `calculate_orders` step to determine their final `To Order` or `To Build` status based on their *own* stock, commitments, and the (potentially netted) `Total Required`.

2.  **Available (Verfügbar) - For Parts & Subassemblies (Used in Final Tables):**
    `Available = total_in_stock - (required_for_build_orders + required_for_sales_orders)`
    *   *Note:* This 'Available' value represents the stock physically on hand minus immediate commitments (Build Orders, Sales Orders). It is primarily used for display in the final output tables and as an input for the `To Order` / `To Build` calculations below. It does *not* directly account for incoming stock (`ordering` or `building`) or the netting logic applied during the recursive requirement calculation.
    *   `// TEST: Calculation of available quantity for a part/subassembly with positive stock and no commitments`
    *   `// TEST: Calculation of available quantity for a part/subassembly with commitments`

3.  **To Order (Zu Bestellen) - For Purchased Parts:**
    `To_Order = max(0, Total_Required - Available)`
    *   *Note:* The `To_Order` calculation uses the final `Total_Required` (which has already been adjusted by the netting logic during recursion) and compares it against the part's own `Available` stock (stock minus commitments). The `ordering` quantity (parts already on order) is displayed for information but *not* subtracted here; the goal is to show how much is needed *now* compared to current available stock, regardless of incoming orders.
    *   `// TEST: Calculation of 'To Order' when required exceeds available`
    *   `// TEST: Calculation of 'To Order' when available meets or exceeds required`

4.  **To Build (Zu Bauen) - For Subassemblies:**
    `To_Build = max(0, Total_Required - (Available + building))`
    *   *Note:* The `To_Build` calculation uses the final `Total_Required` (adjusted by netting) and compares it against the subassembly's `Available` stock *plus* any quantity already `In Production` (`building`). We only need to initiate builds for the quantity required beyond what's available or already underway. This matches the formula: `max(0, Total_Required - ((total_in_stock - (required_for_build_orders + required_for_sales_orders)) + building))`
    *   `// TEST: Calculation of 'To Build' when required exceeds available`
    *   `// TEST: Calculation of 'To Build' when available meets or exceeds required`

## 7. Constraints & Assumptions

### 7.1. Constraints

*   The tool requires network access to the specified InvenTree API endpoint.
*   Valid API credentials (token) with sufficient read permissions for parts, BOMs, stock, and orders are necessary.
*   The InvenTree instance must have parts correctly configured with BOMs where applicable.

### 7.2. Assumptions

*   The InvenTree API version is compatible with the tool's API calls. (Specify version if known, e.g., InvenTree API vX.Y.Z).
*   The definitions of `total_in_stock`, `ordering`, `building`, `required_for_build_orders`, and `required_for_sales_orders` in InvenTree align with their use in the calculation logic.
*   Part numbers provided as input exist in the InvenTree database.

## 8. Error Handling

*   **Invalid Part Number:** If an input part number is not found in InvenTree, log an error and:
    *   Option A: Skip that part and continue processing others.
    *   Option B: Halt execution and report the error.
    *   *Decision Point:* Choose an error handling strategy. Option A is generally preferred for batch processing.
    *   `// TEST: Handling of a single invalid part number in input`
*   **API Connection Issues:** If the InvenTree API is unreachable or returns an error (e.g., 401 Unauthorized, 500 Server Error):
    *   Log the error clearly.
    *   Retry mechanism (e.g., up to 3 retries with exponential backoff).
    *   If retries fail, terminate gracefully with an informative error message.
    *   `// TEST: Handling of API unavailability`
    *   `// TEST: Handling of API authentication failure`
*   **Missing BOM:** If a part is expected to have a BOM (e.g., it's an assembly) but doesn't, log a warning and treat it as a part with no sub-components for calculation purposes (or halt, TBD).
    *   `// TEST: Handling of a part missing an expected BOM`
*   **Data Inconsistencies:** Handle potential `null` or unexpected values from API responses gracefully (e.g., by treating `null` as 0 for numerical fields involved in calculations, with a warning).
    *   `// TEST: Handling of null/missing numerical values from API for stock/order fields`

## 9. Acceptance Criteria

*   **AC1:** Given a list of top-level assemblies and quantities, the tool correctly identifies all unique sub-components and their total required quantities by recursively exploding BOMs.
*   **AC2:** The tool accurately fetches `total_in_stock`, `ordering`, `building`, `required_for_build_orders`, and `required_for_sales_orders` from InvenTree for all relevant parts.
*   **AC3:** The 'Available' quantity for each part and subassembly is calculated correctly according to the defined logic.
*   **AC4:** The 'To Order' quantity for purchased parts is calculated correctly, showing 0 if available stock meets or exceeds demand.
*   **AC5:** The 'To Build' quantity for subassemblies is calculated correctly, showing 0 if available stock meets or exceeds demand.
*   **AC6:** The tool generates two markdown tables: "Parts to Order" and "Subassemblies to Build", with all specified columns correctly populated.
*   **AC7:** The tool accepts InvenTree API URL and Token via configuration (environment variables or config file) and successfully connects to the InvenTree API.
*   **AC8:** The tool handles invalid input part numbers gracefully as per the chosen strategy (e.g., logs error, skips part).
*   **AC9:** The tool handles InvenTree API connection errors and authentication failures gracefully (e.g., logs error, retries, terminates with message).
*   **AC10:** Log output is clear and provides sufficient information about the tool's progress and any issues encountered.

## 10. Non-Functional Requirements

*   **Performance:** The tool should process BOMs of considerable depth and breadth within a reasonable timeframe (e.g., X seconds for a BOM with Y total lines). Specific benchmarks to be defined if performance becomes a concern.
*   **Usability:** The CLI should be straightforward to use with clear instructions for input and configuration.
*   **Maintainability:** Code should be well-structured, commented, and include unit tests for core logic.
*   **Security:** API tokens must not be hard-coded or logged.

## 11. Future Enhancements (Optional)

*   Support for different input formats (e.g., GUI for file selection).
*   Option to output in other formats (e.g., CSV, Excel).
*   More sophisticated error reporting.
*   Caching of InvenTree data for repeated runs with same/similar inputs.