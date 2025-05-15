# Module: src/inventree_order_calculator/models.py
# Description: Defines data structures used throughout the application.

from dataclasses import dataclass, field
from typing import Union, Set, List, Optional # Import Union, Set, List, and Optional
from enum import Enum

@dataclass
class PartData:
    """Represents the relevant data for a single part fetched from InvenTree."""
    pk: int
    name: str
    is_purchaseable: bool
    is_assembly: bool
    ipn: Optional[str] = None # Internal Part Number
    revision: Optional[str] = None
    description: Optional[str] = None
    virtual: bool = False
    unit_price: float = 0.0 # Assuming a default, might be fetched or calculated
    total_price: float = 0.0 # Typically calculated (quantity * unit_price)
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

@dataclass
class OutputTables:
    """Holds the final lists of parts to order and build."""
    parts_to_order: list[CalculatedPart] = field(default_factory=list)
    subassemblies_to_build: list[CalculatedPart] = field(default_factory=list)
    total_cost_parts_to_order: float = 0.0
    total_cost_subassemblies: float = 0.0
    overall_total_cost: float = 0.0
    warnings: List[str] = field(default_factory=list)


# Minimal placeholder for BOM Item data structure
# Based on pseudocode line 155-156
@dataclass
class BomItemData:
    """Represents relevant data from a BOM item."""
    sub_part: int # PK of the sub-part
    quantity: float # Quantity of sub-part per assembly
    is_consumable: bool = False # Indicates if this BOM line item is consumable

class NotifyCondition(Enum):
    """Defines conditions under which a notification should be sent."""
    ALWAYS = "always"
    ON_CHANGE = "on_change"
    # Add more conditions like ON_THRESHOLD_MET if needed later

@dataclass
class MonitoringList:
    """Defines a monitoring task configuration."""
    name: str
    parts_list_file: str
    schedule: str # cron-like schedule string
    active: bool = True
    notify_on: NotifyCondition = NotifyCondition.ON_CHANGE
    recipient_emails: List[str] = field(default_factory=list)
    target_price: Optional[float] = None
    last_hash: Optional[str] = None
    last_run_iso: Optional[str] = None # Store as ISO 8601 string
    last_result_summary: Optional[str] = None # Brief summary of the last run
    created_at_iso: Optional[str] = None # Store as ISO 8601 string
    updated_at_iso: Optional[str] = None # Store as ISO 8601 string