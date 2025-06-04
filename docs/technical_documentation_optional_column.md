# Technical Documentation: Optional Column Implementation

## Overview

This document provides technical details for the Optional Column feature implementation in the InvenTree Order Calculator. The feature extracts and displays optional part information from InvenTree's native BOM optional field support.

## Architecture

### Data Flow

1. **API Extraction** (`api_client.py`): Extract `optional` field from InvenTree BOM API responses
2. **Data Models** (`models.py`): Store optional status in `BomItemData` and `CalculatedPart` objects
3. **Calculation Logic** (`calculator.py`): Propagate optional status through BOM explosion
4. **UI Display** (`streamlit_app.py`, `cli.py`): Display optional status in output tables

### Key Components

#### 1. API Client (`src/inventree_order_calculator/api_client.py`)

**Method: `get_bom_data(part_pk: int)`**

Extracts the `optional` field from InvenTree BOM item responses:

```python
def get_bom_data(self, part_pk: int) -> Tuple[List[BomItemData], List[str]]:
    """
    Fetch BOM data for a given part.
    
    Extracts optional field from BOM item data:
    - item._data.get('optional', False): Extract optional field with False default
    - Handles missing field gracefully for backward compatibility
    """
    # Implementation extracts 'optional' field from each BOM item
    is_optional = item._data.get('optional', False) or False
    bom_item = BomItemData(
        sub_part=sub_part_pk,
        quantity=quantity,
        is_consumable=is_consumable,
        is_optional=is_optional  # New field
    )
```

**Error Handling:**
- Missing `optional` field: Defaults to `False` (required)
- `optional` field is `None`: Treated as `False`
- Maintains backward compatibility with older InvenTree versions

#### 2. Data Models (`src/inventree_order_calculator/models.py`)

**BomItemData Class:**
```python
@dataclass
class BomItemData:
    sub_part: int
    quantity: float
    is_consumable: bool = False
    is_optional: bool = False  # New field with default False
```

**CalculatedPart Class:**
```python
@dataclass
class CalculatedPart(PartData):
    # ... existing fields ...
    is_optional: bool = False  # New field with default False
```

**Design Decisions:**
- Default value `False` ensures required behavior when field is not set
- Boolean type provides clear True/False semantics
- Inherits from existing data structures for consistency

#### 3. Calculator Logic (`src/inventree_order_calculator/calculator.py`)

**Method: `_calculate_required_recursive()`**

Propagates optional status from BOM items to calculated parts:

```python
def _calculate_required_recursive(self, part_pk: int, quantity_needed: float, 
                                top_level_part_name: str, output_tables: OutputTables):
    """
    Recursive BOM explosion with optional status propagation.
    
    For each BOM item:
    1. Extract is_optional from BomItemData
    2. Create/update CalculatedPart with optional status
    3. Preserve optional status through recursive calls
    """
    # Extract optional status from BOM item
    is_optional = bom_item.is_optional
    
    # Create or update CalculatedPart with optional status
    calculated_part = CalculatedPart(
        pk=sub_part_pk,
        name=sub_part_data.name,
        # ... other fields ...
        is_optional=is_optional  # Propagate optional status
    )
```

**Key Behaviors:**
- Optional status is preserved through all levels of BOM explosion
- Quantity calculations remain unchanged (optional parts still counted)
- Optional status is informational only, doesn't affect ordering logic

#### 4. Streamlit UI (`src/inventree_order_calculator/streamlit_app.py`)

**Display Functions:**

```python
def format_parts_to_order_for_display(parts: List[CalculatedPart], ...):
    """
    Formats parts data for Streamlit display with Optional column.
    
    Column order: Part ID | Optional | Part_URL | Needed | ...
    """
    data.append({
        "Part ID": part_pk,
        "Optional": getattr(part, 'is_optional', False),  # Extract optional status
        "Part_URL": part_url,
        # ... other columns ...
    })
    
    # Column configuration for Streamlit
    column_config = {
        "Optional": st.column_config.CheckboxColumn(
            "Optional",
            help="Indicates if this part is optional for the assembly (from InvenTree BOM)",
            default=False
        ),
        # ... other column configs ...
    }
```

**UI Features:**
- Checkbox column type for clear visual indication
- Positioned after Part ID for prominence
- Tooltip explains optional status source
- Consistent with CLI symbol mapping

#### 5. CLI Interface (`src/inventree_order_calculator/cli.py`)

**Table Display:**

```python
# Add Optional column to table
parts_table.add_column("Optional", justify="center", style="dim")

# Format optional status as symbols
optional_status = "✓" if getattr(item, 'is_optional', False) else "✗"

# Add to table row
parts_table.add_row(
    str(part_pk),
    optional_status,  # Optional column data
    display_name,
    # ... other columns ...
)
```

**Symbol Mapping:**
- `✓` (checkmark): Optional part
- `✗` (X mark): Required part
- Consistent with Streamlit checkbox semantics

## InvenTree API Integration

### BOM API Endpoint

**Endpoint:** `/api/bom/`

**Response Structure:**
```json
{
  "pk": 123,
  "sub_part": 456,
  "quantity": 2.0,
  "consumable": false,
  "optional": true,  // This field is extracted
  // ... other fields ...
}
```

### API Field Extraction

```python
# Extract optional field with fallback
is_optional = item._data.get('optional', False) or False

# Handle various cases:
# - Field missing: False (backward compatibility)
# - Field is None: False (treat as required)
# - Field is True/False: Use actual value
```

### Compatibility Matrix

| InvenTree Version | Optional Field Support | Behavior |
|-------------------|------------------------|----------|
| < 0.13.0 | Not supported | All parts marked as required (✗) |
| >= 0.13.0 | Supported | Actual optional status displayed |
| Any version | Field not set | Defaults to required (✗) |

## Testing Strategy

### Unit Test Coverage

1. **Models Tests** (`tests/test_models.py`):
   - `BomItemData` optional field initialization
   - `CalculatedPart` optional field inheritance
   - Default value behavior (False)
   - Type validation (boolean)

2. **API Client Tests** (`tests/test_api_client.py`):
   - Optional field extraction (`optional=True`)
   - Optional field extraction (`optional=False`)
   - Missing optional field handling
   - `optional=None` handling
   - Mixed optional/required BOM items

3. **Calculator Tests** (`tests/test_calculator.py`):
   - Optional status propagation through BOM explosion
   - Preservation during recursive processing
   - Mixed optional/required parts handling
   - Quantity calculations unaffected by optional status

4. **UI Tests** (`tests/test_streamlit_app.py`, `tests/test_cli.py`):
   - Optional column inclusion in display tables
   - Correct symbol/checkbox formatting
   - Column positioning (after Part ID)
   - Mixed optional/required display

### Test Data Patterns

```python
# Required part
required_part = CalculatedPart(
    pk=123, name="Required Part", is_optional=False
)

# Optional part  
optional_part = CalculatedPart(
    pk=456, name="Optional Part", is_optional=True
)

# BOM item with optional status
bom_item = BomItemData(
    sub_part=789, quantity=2.0, is_optional=True
)
```

## Error Handling

### Graceful Degradation

1. **Missing Optional Field**: Default to `False` (required)
2. **API Errors**: Continue processing, log warnings
3. **Invalid Data Types**: Convert to boolean, default to `False`
4. **Older InvenTree Versions**: Full functionality with all parts marked as required

### Logging

```python
# Log when optional field is missing (debug level)
logger.debug(f"Optional field missing for BOM item {item_pk}, defaulting to False")

# Log when optional field extraction succeeds (debug level)
logger.debug(f"Extracted optional={is_optional} for BOM item {item_pk}")
```

## Performance Considerations

### API Efficiency

- Optional field extraction adds minimal overhead
- No additional API calls required
- Field extracted during existing BOM data fetch
- Backward compatible with existing caching strategies

### Memory Usage

- Single boolean field per BOM item/calculated part
- Negligible memory impact
- No impact on existing data structures

### Processing Speed

- Optional status propagation is O(1) per BOM item
- No impact on BOM explosion algorithm complexity
- UI rendering impact minimal (additional column)

## Future Enhancements

### Potential Features

1. **Optional Part Filtering**: Add toggle to hide/show optional parts
2. **Cost Analysis**: Separate cost calculations for optional vs required parts
3. **Export Options**: Include optional status in CSV/Excel exports
4. **Bulk Operations**: Mark multiple parts as optional/required

### API Extensions

1. **Batch Updates**: Update optional status for multiple BOM items
2. **Search Filters**: Filter parts by optional status
3. **Reporting**: Generate reports based on optional part usage

## Troubleshooting

### Common Issues

1. **All Parts Show as Required (✗)**:
   - Check InvenTree version supports optional field
   - Verify BOM items have optional field set in InvenTree
   - Check API token permissions

2. **Optional Status Not Updating**:
   - Clear any caching mechanisms
   - Verify InvenTree BOM data is updated
   - Check API client connection

3. **Display Issues**:
   - Verify column configuration in UI code
   - Check symbol rendering in terminal/browser
   - Validate data type consistency (boolean)

### Debug Commands

```bash
# Test API connection and optional field support
python -c "
from src.inventree_order_calculator.api_client import ApiClient
from src.inventree_order_calculator.config import AppConfig
config = AppConfig.load()
client = ApiClient(config)
bom_data, warnings = client.get_bom_data(YOUR_PART_ID)
for item in bom_data:
    print(f'Part {item.sub_part}: optional={item.is_optional}')
"
```

## References

- [InvenTree BOM Documentation](https://docs.inventree.org/en/stable/build/bom/)
- [InvenTree API Schema](https://docs.inventree.org/en/latest/api/schema/bom/)
- [InvenTree Python Library](https://github.com/inventree/inventree-python)
