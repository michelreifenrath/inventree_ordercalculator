# Module: src/inventree_order_calculator/models.py
# Description: Defines data structures used throughout the application.

from dataclasses import dataclass, field
from typing import Union, Set, List # Import Union, Set, and List
from enum import Enum

class BuildingCalculationMethod(Enum):
    """Enum for different building quantity calculation methods."""
    NEW_GUI = "new_gui"  # Current behavior (full build order quantities)
    OLD_GUI = "old_gui"  # Legacy behavior (only is_building=True items)

@dataclass
class PartData:
    """Represents the relevant data for a single part fetched from InvenTree."""
    pk: int
    name: str
    is_purchaseable: bool
    is_assembly: bool
    total_in_stock: float = 0.0
    required_for_build_orders: float = 0.0 # Committed stock for builds
    required_for_sales_orders: float = 0.0 # Committed stock for sales
    ordering: float = 0.0 # Quantity on order (for purchaseable parts)
    building: float = 0.0 # Quantity in production (for assemblies)
    is_consumable: bool = False
    supplier_names: List[str] = field(default_factory=list)

    # Add other fields as needed based on pseudocode and API responses

# Placeholder for other models mentioned in pseudocode
@dataclass
class InputPart:
    part_identifier: Union[str, int] # Use Union for Python < 3.10 compatibility
    quantity_to_build: float

@dataclass
class CalculatedPart(PartData):
    """Extends PartData with calculated results."""
    total_required: float = 0.0
    available: float = 0.0
    to_order: float = 0.0
    to_build: float = 0.0
    belongs_to_top_parts: Set[str] = field(default_factory=set) # Tracks which top-level parts this part belongs to
    is_consumable: bool = False
    supplier_names: List[str] = field(default_factory=list)
    is_optional: bool = False # Indicates if this part is optional in the BOM

@dataclass
class OutputTables:
    """Holds the final lists of parts to order and build."""
    parts_to_order: list[CalculatedPart] = field(default_factory=list)
    subassemblies_to_build: list[CalculatedPart] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# Minimal placeholder for BOM Item data structure
# Based on pseudocode line 155-156
@dataclass
class BomItemData:
    """Represents relevant data from a BOM item."""
    sub_part: int # PK of the sub-part
    quantity: float # Quantity of sub-part per assembly
    is_consumable: bool = False # Indicates if this BOM line item is consumable
    is_optional: bool = False # Indicates if this BOM line item is optional