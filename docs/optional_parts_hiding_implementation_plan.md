# Optional BOM Parts Hiding Implementation Plan

## Executive Summary

This document outlines the implementation plan for adding the ability to hide optional BOM parts from the display in the InvenTree Order Calculator app, similar to the existing consumable parts hiding functionality.

**Current Status**: The optional BOM parts feature is already fully implemented with data extraction, propagation, and display. This plan focuses on adding the **hiding/filtering functionality** for optional parts.

## 1. Analysis Phase

### 1.1 Current Consumable Hiding Mechanism

**Existing Implementation Pattern:**

<augment_code_snippet path="src/inventree_order_calculator/streamlit_app.py" mode="EXCERPT">
````python
# Session state initialization
if 'show_consumables_toggle_widget' not in st.session_state: 
    st.session_state.show_consumables_toggle_widget = False 

# UI Toggle Control
st.session_state.show_consumables_toggle_widget = st.toggle(
    "Show Consumable Parts",
    value=st.session_state.show_consumables_toggle_widget,
    key="show_consumables_key_main",
    help="Include parts marked as 'consumable' in the results."
)

# Filtering Logic in format functions
if not show_consumables:
    filtered_parts = [p for p in parts if not getattr(p, 'is_consumable', False)]
````
</augment_code_snippet>

**CLI Implementation:**

<augment_code_snippet path="src/inventree_order_calculator/cli.py" mode="EXCERPT">
````python
hide_consumables: Annotated[bool, typer.Option("--hide-consumables", help="Hide consumable parts from the output tables.")] = False

if hide_consumables:
    console.print("[italic]Hiding consumable parts from output.[/italic]")
    result.parts_to_order = [p for p in result.parts_to_order if not p.is_consumable]
    result.subassemblies_to_build = [a for a in result.subassemblies_to_build if not a.is_consumable]
````
</augment_code_snippet>

### 1.2 Optional BOM Item Data Availability

**Data Source**: InvenTree API native `optional` field support is already implemented:

<augment_code_snippet path="src/inventree_order_calculator/api_client.py" mode="EXCERPT">
````python
is_optional = data.get('optional', False)  # Extract optional field, default to False
bom_data_list.append(
    BomItemData(
        sub_part=int(sub_part_pk),
        quantity=float(quantity),
        is_consumable=bool(is_consumable),
        is_optional=bool(is_optional)  # Already implemented
    )
)
````
</augment_code_snippet>

**Data Models**: Already support optional status:

<augment_code_snippet path="src/inventree_order_calculator/models.py" mode="EXCERPT">
````python
@dataclass
class BomItemData:
    sub_part: int
    quantity: float
    is_consumable: bool = False
    is_optional: bool = False  # ✅ Already implemented

@dataclass
class CalculatedPart(PartData):
    # ... existing fields ...
    is_optional: bool = False  # ✅ Already implemented
````
</augment_code_snippet>

### 1.3 UI Components Analysis

**Current Display**: Optional column is already displayed in both interfaces:

- **Streamlit**: Checkbox column with tooltip
- **CLI**: ✓/✗ symbols in "Optional" column

**Missing**: Toggle controls to hide optional parts from display

## 2. Implementation Plan

### 2.1 Files Requiring Modifications

**Primary Files:**

1. **`src/inventree_order_calculator/streamlit_app.py`**
   - Add session state for optional parts toggle
   - Add UI toggle control in Display Options
   - Update filtering logic in format functions
   - Pass optional toggle state to format functions

2. **`src/inventree_order_calculator/cli.py`**
   - Add `--hide-optional-parts` command line option
   - Add filtering logic for optional parts
   - Add console message for optional parts hiding

**Secondary Files (Testing):**

3. **`tests/test_streamlit_app.py`**
   - Add tests for optional parts filtering logic
   - Test toggle state management
   - Test format function with optional filtering

4. **`tests/test_cli.py`**
   - Add tests for `--hide-optional-parts` option
   - Test filtering behavior
   - Test combined filtering (consumables + optional + HAIP)

### 2.2 Data Flow Design

**Updated Data Flow:**
```
CalculatedPart.is_optional (already available) →
UI Toggle State (show_optional_parts) →
Filtering Logic (filter optional parts) →
Display Tables (filtered results)
```

**Filtering Logic Pattern:**
```python
# Follow existing consumable filtering pattern
if not show_optional_parts:
    filtered_parts = [p for p in filtered_parts if not getattr(p, 'is_optional', False)]
```

### 2.3 UI Implementation Strategy

**Streamlit Interface:**

1. **Session State Initialization:**
   ```python
   if 'show_optional_parts_toggle' not in st.session_state: 
       st.session_state.show_optional_parts_toggle = True  # Default: show optional parts
   ```

2. **Toggle Control (in Display Options expander):**
   ```python
   st.session_state.show_optional_parts_toggle = st.toggle(
       "Show Optional Parts",
       value=st.session_state.show_optional_parts_toggle,
       key="show_optional_parts_key_main",
       help="Include parts marked as 'optional' in the BOM results."
   )
   ```

3. **Function Signature Updates:**
   ```python
   def format_parts_to_order_for_display(
       parts: List['CalculatedPart'], 
       app_config: Optional[AppConfig], 
       show_consumables: bool,
       show_optional_parts: bool  # New parameter
   ) -> pd.DataFrame:
   ```

**CLI Interface:**

1. **Command Line Option:**
   ```python
   hide_optional_parts: Annotated[bool, typer.Option(
       "--hide-optional-parts", 
       help="Hide parts marked as optional in the BOM from the output tables."
   )] = False
   ```

2. **Filtering Logic:**
   ```python
   if hide_optional_parts:
       console.print("[italic]Hiding optional parts from output.[/italic]")
       result.parts_to_order = [p for p in result.parts_to_order if not getattr(p, 'is_optional', False)]
       result.subassemblies_to_build = [a for a in result.subassemblies_to_build if not getattr(a, 'is_optional', False)]
   ```

### 2.4 Technical Requirements

**Consistency with Existing Patterns:**
- Follow exact same pattern as consumable hiding
- Maintain backward compatibility
- Use same naming conventions (`show_*` for Streamlit, `hide_*` for CLI)

**State Management:**
- Default to showing optional parts (user choice to hide)
- Persist toggle state in session
- Apply filtering after consumable and HAIP filtering

**User Experience:**
- Clear toggle labels and help text
- Consistent behavior across interfaces
- Logical filtering order (consumables → HAIP → optional)

## 3. Testing Strategy

### 3.1 Unit Tests

**Test Cases for Filtering Logic:**

1. **`test_format_parts_with_optional_filtering()`**
   - Test filtering out optional parts when `show_optional_parts=False`
   - Test showing optional parts when `show_optional_parts=True`
   - Test mixed scenarios (some optional, some required)

2. **`test_format_assemblies_with_optional_filtering()`**
   - Same tests for assemblies table

3. **`test_combined_filtering()`**
   - Test filtering consumables + optional parts together
   - Test filtering consumables + HAIP + optional parts together
   - Verify filtering order and precedence

**Test Cases for CLI:**

1. **`test_cli_hide_optional_parts_option()`**
   - Test `--hide-optional-parts` flag functionality
   - Test combined flags (`--hide-consumables --hide-optional-parts`)
   - Test console output messages

### 3.2 Integration Tests

**Streamlit UI Tests:**

1. **`test_optional_parts_toggle_state()`**
   - Test session state initialization
   - Test toggle state persistence
   - Test toggle interaction with filtering

2. **`test_display_options_expander()`**
   - Test all three toggles work together
   - Test UI layout and positioning

### 3.3 User Acceptance Criteria

**Functional Requirements:**

✅ **FR1**: User can toggle optional parts visibility in Streamlit interface  
✅ **FR2**: User can hide optional parts via CLI `--hide-optional-parts` flag  
✅ **FR3**: Optional parts filtering works independently of consumable filtering  
✅ **FR4**: Combined filtering (consumables + optional + HAIP) works correctly  
✅ **FR5**: Default behavior shows optional parts (user must explicitly hide)  
✅ **FR6**: Filtering preserves all other data and calculations  
✅ **FR7**: UI provides clear feedback about filtering state  

**Non-Functional Requirements:**

✅ **NFR1**: Performance impact is minimal (simple list comprehension)  
✅ **NFR2**: Implementation follows existing code patterns  
✅ **NFR3**: Backward compatibility is maintained  
✅ **NFR4**: Code is well-documented and testable  

## 4. Implementation Sequence

### Phase 1: Streamlit Implementation (Priority: High)
1. Add session state initialization for optional parts toggle
2. Add toggle control to Display Options expander
3. Update `format_parts_to_order_for_display()` function signature and logic
4. Update `format_assemblies_to_build_for_display()` function signature and logic
5. Update function calls to pass optional toggle state

### Phase 2: CLI Implementation (Priority: High)
1. Add `--hide-optional-parts` command line option
2. Add filtering logic in main() function
3. Add console output message for optional parts hiding

### Phase 3: Testing (Priority: High)
1. Write unit tests for filtering logic
2. Write integration tests for UI components
3. Write CLI tests for new option
4. Test combined filtering scenarios

### Phase 4: Documentation Updates (Priority: Medium)
1. Update README.md with optional parts filtering documentation
2. Update help text and docstrings
3. Update specification if needed

## 5. Risk Assessment

**Low Risk Implementation:**
- Following established patterns reduces implementation risk
- Simple filtering logic with minimal complexity
- No changes to data models or API client required
- Extensive existing test coverage for similar functionality

**Potential Issues:**
- **UI Layout**: Adding third toggle might affect Display Options layout
- **Performance**: Multiple filtering passes (minimal impact expected)
- **User Confusion**: Three similar toggles might be confusing

**Mitigation Strategies:**
- Test UI layout changes carefully
- Consider grouping toggles with clear labels
- Provide comprehensive help text for each toggle
- Document filtering behavior clearly

## 6. Success Metrics

**Implementation Success:**
- All tests pass
- Feature works as specified in both interfaces
- No regression in existing functionality
- Code review approval

**User Success:**
- Users can effectively hide optional parts when needed
- Filtering behavior is intuitive and predictable
- Performance remains acceptable
- Documentation is clear and helpful
