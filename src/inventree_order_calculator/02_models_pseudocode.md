# Module: src/inventree_order_calculator/models.py
# Description: Defines data structures/models used in the application.

# Dependencies: (Potentially Pydantic for actual implementation)

// Define a structure for the input provided by the user
CLASS InputPart:
    ATTRIBUTE part_identifier: STRING // Could be Part ID (PK) or Part Number (IPN/MPN)
    ATTRIBUTE quantity_to_build: INTEGER

// Define a structure to hold detailed data fetched from InvenTree for a part
CLASS PartData:
    ATTRIBUTE pk: INTEGER                 // Primary Key in InvenTree
    ATTRIBUTE ipn: STRING | NONE          // Internal Part Number
    ATTRIBUTE name: STRING
    ATTRIBUTE description: STRING | NONE
    ATTRIBUTE is_purchaseable: BOOLEAN    // Indicates if it's typically bought
    ATTRIBUTE is_assembly: BOOLEAN        // Indicates if it can be built (has a BOM)

    // Stock and Order Information (fetched from API)
    ATTRIBUTE total_in_stock: FLOAT = 0.0
    ATTRIBUTE ordering: FLOAT = 0.0         // Quantity on purchase orders
    ATTRIBUTE building: FLOAT = 0.0         // Quantity on build orders (being built)
    ATTRIBUTE required_for_build_orders: FLOAT = 0.0 // Allocated to other builds
    ATTRIBUTE required_for_sales_orders: FLOAT = 0.0 // Allocated to sales orders

    // Method to initialize with default values (optional, depends on implementation)
    CONSTRUCTOR __init__(pk, ipn, name, description, is_purchaseable, is_assembly, ...):
        // Assign values...
        // Ensure numerical fields default to 0.0 if API returns null/None
        self.total_in_stock = IF total_in_stock IS NOT NONE THEN total_in_stock ELSE 0.0
        // ... similar checks for other numerical fields ...
        // TEST: Handling of null/missing numerical values from API for stock/order fields

// Define a structure to hold calculated results for a part
CLASS CalculatedPart:
    ATTRIBUTE part_data: PartData         // The original data from InvenTree
    ATTRIBUTE total_required: FLOAT = 0.0 // Total quantity needed for the top-level builds
    ATTRIBUTE available: FLOAT = 0.0      // Calculated available quantity
    ATTRIBUTE to_order: FLOAT = 0.0       // Calculated quantity to order (for purchaseable parts)
    ATTRIBUTE to_build: FLOAT = 0.0       // Calculated quantity to build (for assemblies)

    CONSTRUCTOR __init__(part_data: PartData):
        self.part_data = part_data
        // Initialize other fields to 0.0

// Define a structure to hold the final output tables
CLASS OutputTables:
    ATTRIBUTE parts_to_order: LIST[CalculatedPart] = []
    ATTRIBUTE subassemblies_to_build: LIST[CalculatedPart] = []