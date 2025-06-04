import pytest
from unittest.mock import Mock, patch # Import patch

# Import actual classes from the source modules
from src.inventree_order_calculator.models import PartData, BomItemData, InputPart, OutputTables, CalculatedPart # Import more models
from src.inventree_order_calculator.calculator import OrderCalculator


# --- Fixtures ---

@pytest.fixture
def mock_api_client():
    """Provides a mock API client instance."""
    return Mock()

@pytest.fixture
def calculator(mock_api_client):
    """Provides an OrderCalculator instance with a mocked API client."""
    return OrderCalculator(api_client=mock_api_client)


# --- Test Cases ---

# --- Tests for _calculate_availability ---

def test_calculate_availability_purchased_part_simple(calculator): # Use fixture
    """
    Tests availability calculation for a purchased part with stock, commitments, and incoming orders.
    Formula: available = total_in_stock - (required_builds + required_sales) + ordering
    """
    # Arrange
    # calculator instance is provided by the fixture

    # Create part data instance for a purchased item
    part_data = PartData(
        pk=1,
        name="Test Resistor",
        is_purchaseable=True,
        is_assembly=False,
        total_in_stock=100.0,
        required_for_build_orders=10.0, # Corrected keyword argument
        required_for_sales_orders=5.0,  # Corrected keyword argument
        ordering=20.0,
        building=0.0
    )
    # Updated calculation: remove '+ ordering'
    expected_availability = 100.0 - (10.0 + 5.0) # 85.0

    # Act
    actual_availability = calculator._calculate_availability(part_data)

    # Assert
    assert actual_availability == expected_availability, \
        f"Expected availability {expected_availability}, but got {actual_availability}"


# --- Tests for _calculate_required_recursive ---

# Remove the patch decorator, we will configure the injected mock_api_client instead
def test_calculate_required_recursive_base_case(calculator, mock_api_client):
    """
    Tests the base case for recursive calculation: a single, non-assembly part.
    It should create/update the part in calculated_parts_dict with the required quantity
    and the correct top-level part association.
    """
    # Arrange
    part_pk = 10
    quantity_needed = 5.0
    top_level_part_name = "TOP_LEVEL_PART_A"

    mock_part_data = PartData(
        pk=part_pk, name="Leaf Part", is_purchaseable=True, is_assembly=False,
        total_in_stock=10, required_for_build_orders=1, required_for_sales_orders=1, ordering=2, building=0,
        is_consumable=True, supplier_names=["Supplier X"] # Added for testing
    )
    # Update mock to return tuple: (data, warnings_list)
    mock_api_client.get_part_data.return_value = (mock_part_data, [])
    mock_api_client.get_bom_data.return_value = ([], []) # Should not be called, but match signature

    # Expected state after call: A CalculatedPart object in the dictionary
    expected_calculated_part = CalculatedPart(
        pk=part_pk, name="Leaf Part", is_purchaseable=True, is_assembly=False,
        total_in_stock=10, required_for_build_orders=1, required_for_sales_orders=1, ordering=2, building=0,
        is_consumable=True, supplier_names=["Supplier X"], # Added for testing
        total_required=quantity_needed, # Initial requirement
        available=0.0, # Will be calculated later
        to_order=0.0,  # Will be calculated later
        to_build=0.0,  # Will be calculated later
        belongs_to_top_parts={top_level_part_name} # Should contain the top-level name
    )

    # Act
    output_tables_instance = OutputTables() # Create instance to pass
    calculator._calculate_required_recursive(part_pk, quantity_needed, top_level_part_name, output_tables_instance)

    # Assert
    assert part_pk in calculator.calculated_parts_dict, "Part PK not found in calculated_parts_dict"
    actual_calculated_part = calculator.calculated_parts_dict[part_pk]

    # Compare relevant fields (ignore available, to_order, to_build as they are calculated later)
    assert actual_calculated_part.pk == expected_calculated_part.pk
    assert actual_calculated_part.name == expected_calculated_part.name
    assert actual_calculated_part.total_required == expected_calculated_part.total_required
    assert actual_calculated_part.belongs_to_top_parts == expected_calculated_part.belongs_to_top_parts
    assert actual_calculated_part.is_consumable == expected_calculated_part.is_consumable # Added assertion
    assert actual_calculated_part.supplier_names == expected_calculated_part.supplier_names # Added assertion
    assert not output_tables_instance.warnings, "Expected no warnings from this base case"

    # Verify mocks
    mock_api_client.get_part_data.assert_called_once_with(part_pk)
    mock_api_client.get_bom_data.assert_not_called() # BOM data should not be fetched for a non-assembly


def test_calculate_required_recursive_simple_assembly(calculator, mock_api_client):
    """
    Tests the recursive step for a simple assembly with one sub-part.
    It should update calculated_parts_dict for the assembly AND the sub-part,
    propagating the top-level part name. Assumes zero stock/availability for simplicity.
    """
    # Arrange
    assembly_pk = 20
    sub_part_pk = 21
    quantity_needed_assembly = 2.0
    quantity_per_assembly = 3.0 # 3 sub-parts needed per assembly
    top_level_part_name = "TOP_LEVEL_PART_B"

    # --- Mock PartData ---
    assembly_part_data = PartData(
        pk=assembly_pk, name="Assembly", is_purchaseable=False, is_assembly=True,
        total_in_stock=0, required_for_build_orders=0, required_for_sales_orders=0, ordering=0, building=0,
        is_consumable=False, supplier_names=["Supplier Assembly Co"] # Assembly itself is not consumable
    )
    sub_part_data = PartData(
        pk=sub_part_pk, name="SubPart", is_purchaseable=True, is_assembly=False,
        total_in_stock=0, required_for_build_orders=0, required_for_sales_orders=0, ordering=0, building=0,
        is_consumable=False, supplier_names=["Supplier Sub Inc"] # Sub-part is globally not consumable
    )

    # --- Configure Mock api_client.get_part_data ---
    def get_part_side_effect(part_pk_arg):
        if part_pk_arg == assembly_pk: return (assembly_part_data, [])
        elif part_pk_arg == sub_part_pk: return (sub_part_data, [])
        pytest.fail(f"Unexpected part PK requested: {part_pk_arg}")
        return (None, [])
    mock_api_client.get_part_data.side_effect = get_part_side_effect

    # --- Configure Mock api_client.get_bom_data ---
    # Sub-part is marked as consumable on this BOM line
    mock_bom_item = BomItemData(sub_part=sub_part_pk, quantity=quantity_per_assembly, is_consumable=True)
    mock_api_client.get_bom_data.return_value = ([mock_bom_item], []) # Return (data, warnings_list)

    # Expected state after call
    expected_assembly_calc = CalculatedPart(
        pk=assembly_pk, name="Assembly", is_purchaseable=False, is_assembly=True,
        total_in_stock=0, required_for_build_orders=0, required_for_sales_orders=0, ordering=0, building=0,
        is_consumable=False, supplier_names=["Supplier Assembly Co"], # Assembly itself is not consumable
        total_required=quantity_needed_assembly, # 2.0
        available=0.0, to_order=0.0, to_build=0.0, # Ignored for this assertion
        belongs_to_top_parts={top_level_part_name}
    )
    expected_subpart_calc = CalculatedPart(
        pk=sub_part_pk, name="SubPart", is_purchaseable=True, is_assembly=False,
        total_in_stock=0, required_for_build_orders=0, required_for_sales_orders=0, ordering=0, building=0,
        is_consumable=True, supplier_names=["Supplier Sub Inc"], # Should be true because BOM item was consumable
        total_required=quantity_needed_assembly * quantity_per_assembly, # 2.0 * 3.0 = 6.0
        available=0.0, to_order=0.0, to_build=0.0, # Ignored for this assertion
        belongs_to_top_parts={top_level_part_name} # Inherited from parent call
    )

    # Act
    output_tables_instance = OutputTables()
    calculator._calculate_required_recursive(assembly_pk, quantity_needed_assembly, top_level_part_name, output_tables_instance)

    # Assert
    assert assembly_pk in calculator.calculated_parts_dict
    assert sub_part_pk in calculator.calculated_parts_dict
    actual_assembly = calculator.calculated_parts_dict[assembly_pk]
    actual_subpart = calculator.calculated_parts_dict[sub_part_pk]

    # Compare relevant fields
    assert actual_assembly.total_required == expected_assembly_calc.total_required
    assert actual_assembly.belongs_to_top_parts == expected_assembly_calc.belongs_to_top_parts
    assert actual_assembly.is_consumable == expected_assembly_calc.is_consumable
    assert not output_tables_instance.warnings, "Expected no warnings from this simple assembly case"
    assert actual_assembly.supplier_names == expected_assembly_calc.supplier_names
    assert actual_subpart.total_required == expected_subpart_calc.total_required
    assert actual_subpart.supplier_names == expected_subpart_calc.supplier_names
def test_calculate_required_recursive_subpart_globally_consumable(calculator, mock_api_client):
    """
    Tests that if a sub-part is globally marked as consumable, its CalculatedPart.is_consumable
    is True, even if the BOM item itself doesn't explicitly mark it as consumable.
    """
    # Arrange
    assembly_pk = 30
    sub_part_pk = 31
    quantity_needed_assembly = 1.0
    quantity_per_assembly = 1.0
    top_level_part_name = "TOP_LEVEL_PART_C"

    assembly_part_data = PartData(
        pk=assembly_pk, name="Assembly For Global Consumable Test", is_purchaseable=False, is_assembly=True,
        total_in_stock=0, required_for_build_orders=0, required_for_sales_orders=0, ordering=0, building=0,
        is_consumable=False
    )
    # Sub-part IS globally consumable
    sub_part_data = PartData(
        pk=sub_part_pk, name="Globally Consumable SubPart", is_purchaseable=True, is_assembly=False,
        total_in_stock=0, required_for_build_orders=0, required_for_sales_orders=0, ordering=0, building=0,
        is_consumable=True
    )

    def get_part_side_effect(part_pk_arg):
        if part_pk_arg == assembly_pk: return (assembly_part_data, [])
        elif part_pk_arg == sub_part_pk: return (sub_part_data, [])
        return (None, [])
    mock_api_client.get_part_data.side_effect = get_part_side_effect

    # BOM item does NOT mark it as consumable, but sub-part's global flag should take precedence
    mock_bom_item = BomItemData(sub_part=sub_part_pk, quantity=quantity_per_assembly, is_consumable=False)
    mock_api_client.get_bom_data.return_value = ([mock_bom_item], [])

    # Act
    output_tables_instance = OutputTables()
    calculator._calculate_required_recursive(assembly_pk, quantity_needed_assembly, top_level_part_name, output_tables_instance)

    # Assert
    assert sub_part_pk in calculator.calculated_parts_dict
    actual_subpart = calculator.calculated_parts_dict[sub_part_pk]
    assert actual_subpart.is_consumable is True # Should be true due to global part flag
    assert not output_tables_instance.warnings

def test_calculate_required_recursive_subpart_not_consumable_anywhere(calculator, mock_api_client):
    """
    Tests that if a sub-part is not globally consumable and not marked as consumable
    on the BOM item, its CalculatedPart.is_consumable remains False.
    """
    # Arrange
    assembly_pk = 40
    sub_part_pk = 41
    quantity_needed_assembly = 1.0
    quantity_per_assembly = 1.0
    top_level_part_name = "TOP_LEVEL_PART_D"

    assembly_part_data = PartData(
        pk=assembly_pk, name="Assembly For Non-Consumable Test", is_purchaseable=False, is_assembly=True,
        total_in_stock=0, required_for_build_orders=0, required_for_sales_orders=0, ordering=0, building=0,
        is_consumable=False
    )
    # Sub-part is NOT globally consumable
    sub_part_data = PartData(
        pk=sub_part_pk, name="Non-Consumable SubPart", is_purchaseable=True, is_assembly=False,
        total_in_stock=0, required_for_build_orders=0, required_for_sales_orders=0, ordering=0, building=0,
        is_consumable=False
    )

    def get_part_side_effect(part_pk_arg):
        if part_pk_arg == assembly_pk: return (assembly_part_data, [])
        elif part_pk_arg == sub_part_pk: return (sub_part_data, [])
        return (None, [])
    mock_api_client.get_part_data.side_effect = get_part_side_effect

    # BOM item also does NOT mark it as consumable
    mock_bom_item = BomItemData(sub_part=sub_part_pk, quantity=quantity_per_assembly, is_consumable=False)
    mock_api_client.get_bom_data.return_value = ([mock_bom_item], [])

    # Act
    output_tables_instance = OutputTables()
    calculator._calculate_required_recursive(assembly_pk, quantity_needed_assembly, top_level_part_name, output_tables_instance)

    # Assert
    assert sub_part_pk in calculator.calculated_parts_dict
    actual_subpart = calculator.calculated_parts_dict[sub_part_pk]
    assert actual_subpart.is_consumable is False # Should be False
    assert actual_subpart.belongs_to_top_parts == {top_level_part_name}
    assert not output_tables_instance.warnings

def test_calculate_required_recursive_propagates_optional_status_true(mock_api_client):
    """Test that optional status is propagated from BOM items to CalculatedPart objects when optional=True."""
    # Arrange
    calculator = OrderCalculator(mock_api_client)
    assembly_pk = 100
    sub_part_pk = 200
    quantity_needed_assembly = 5.0
    quantity_per_assembly = 2.0
    top_level_part_name = "Test Assembly"

    # Mock assembly part data
    assembly_part_data = PartData(
        pk=assembly_pk, name="Assembly Part", is_purchaseable=False, is_assembly=True,
        total_in_stock=0.0, is_consumable=False
    )

    # Mock sub-part data
    sub_part_data = PartData(
        pk=sub_part_pk, name="Sub Part", is_purchaseable=True, is_assembly=False,
        total_in_stock=0.0, is_consumable=False
    )

    # Configure mock API client
    mock_api_client.get_part_data.side_effect = lambda pk: (assembly_part_data, []) if pk == assembly_pk else (sub_part_data, [])

    # BOM item with optional=True
    mock_bom_item = BomItemData(
        sub_part=sub_part_pk,
        quantity=quantity_per_assembly,
        is_consumable=False,
        is_optional=True  # This should be propagated
    )
    mock_api_client.get_bom_data.return_value = ([mock_bom_item], [])

    # Act
    output_tables_instance = OutputTables()
    calculator._calculate_required_recursive(assembly_pk, quantity_needed_assembly, top_level_part_name, output_tables_instance)

    # Assert
    assert sub_part_pk in calculator.calculated_parts_dict
    actual_subpart = calculator.calculated_parts_dict[sub_part_pk]
    assert actual_subpart.is_optional is True  # Should be propagated from BOM item
    assert actual_subpart.belongs_to_top_parts == {top_level_part_name}
    assert not output_tables_instance.warnings

def test_calculate_required_recursive_propagates_optional_status_false(mock_api_client):
    """Test that optional status is propagated from BOM items to CalculatedPart objects when optional=False."""
    # Arrange
    calculator = OrderCalculator(mock_api_client)
    assembly_pk = 101
    sub_part_pk = 201
    quantity_needed_assembly = 3.0
    quantity_per_assembly = 1.0
    top_level_part_name = "Required Assembly"

    # Mock assembly part data
    assembly_part_data = PartData(
        pk=assembly_pk, name="Assembly Part", is_purchaseable=False, is_assembly=True,
        total_in_stock=0.0, is_consumable=False
    )

    # Mock sub-part data
    sub_part_data = PartData(
        pk=sub_part_pk, name="Required Sub Part", is_purchaseable=True, is_assembly=False,
        total_in_stock=0.0, is_consumable=False
    )

    # Configure mock API client
    mock_api_client.get_part_data.side_effect = lambda pk: (assembly_part_data, []) if pk == assembly_pk else (sub_part_data, [])

    # BOM item with optional=False
    mock_bom_item = BomItemData(
        sub_part=sub_part_pk,
        quantity=quantity_per_assembly,
        is_consumable=False,
        is_optional=False  # This should be propagated
    )
    mock_api_client.get_bom_data.return_value = ([mock_bom_item], [])

    # Act
    output_tables_instance = OutputTables()
    calculator._calculate_required_recursive(assembly_pk, quantity_needed_assembly, top_level_part_name, output_tables_instance)

    # Assert
    assert sub_part_pk in calculator.calculated_parts_dict
    actual_subpart = calculator.calculated_parts_dict[sub_part_pk]
    assert actual_subpart.is_optional is False  # Should be propagated from BOM item
    assert actual_subpart.belongs_to_top_parts == {top_level_part_name}
    assert not output_tables_instance.warnings

def test_calculate_required_recursive_mixed_optional_required_parts(mock_api_client):
    """Test that calculator correctly handles mixed optional and required BOM items."""
    # Arrange
    calculator = OrderCalculator(mock_api_client)
    assembly_pk = 102
    required_part_pk = 202
    optional_part_pk = 203
    quantity_needed_assembly = 2.0
    top_level_part_name = "Mixed Assembly"

    # Mock assembly part data
    assembly_part_data = PartData(
        pk=assembly_pk, name="Mixed Assembly", is_purchaseable=False, is_assembly=True,
        total_in_stock=0.0, is_consumable=False
    )

    # Mock sub-part data
    required_part_data = PartData(
        pk=required_part_pk, name="Required Part", is_purchaseable=True, is_assembly=False,
        total_in_stock=0.0, is_consumable=False
    )

    optional_part_data = PartData(
        pk=optional_part_pk, name="Optional Part", is_purchaseable=True, is_assembly=False,
        total_in_stock=0.0, is_consumable=False
    )

    # Configure mock API client
    def get_part_data_side_effect(pk):
        if pk == assembly_pk:
            return (assembly_part_data, [])
        elif pk == required_part_pk:
            return (required_part_data, [])
        elif pk == optional_part_pk:
            return (optional_part_data, [])
        return (None, [])

    mock_api_client.get_part_data.side_effect = get_part_data_side_effect

    # BOM items with mixed optional status
    required_bom_item = BomItemData(
        sub_part=required_part_pk,
        quantity=1.0,
        is_consumable=False,
        is_optional=False  # Required
    )

    optional_bom_item = BomItemData(
        sub_part=optional_part_pk,
        quantity=1.0,
        is_consumable=False,
        is_optional=True  # Optional
    )

    mock_api_client.get_bom_data.return_value = ([required_bom_item, optional_bom_item], [])

    # Act
    output_tables_instance = OutputTables()
    calculator._calculate_required_recursive(assembly_pk, quantity_needed_assembly, top_level_part_name, output_tables_instance)

    # Assert
    assert required_part_pk in calculator.calculated_parts_dict
    assert optional_part_pk in calculator.calculated_parts_dict

    required_part = calculator.calculated_parts_dict[required_part_pk]
    optional_part = calculator.calculated_parts_dict[optional_part_pk]

    assert required_part.is_optional is False  # Should be required
    assert optional_part.is_optional is True   # Should be optional
    assert not output_tables_instance.warnings

    # Verify mock calls
    assert mock_api_client.get_part_data.call_count >= 3  # Assembly + 2 sub-parts
    mock_api_client.get_part_data.assert_any_call(assembly_pk)
    mock_api_client.get_part_data.assert_any_call(required_part_pk)
    mock_api_client.get_part_data.assert_any_call(optional_part_pk)
    mock_api_client.get_bom_data.assert_called_once_with(assembly_pk)


def test_calculate_required_recursive_netting_covers_demand(calculator, mock_api_client):
    """
    Tests netting: Assembly is needed, effective availability covers the gross demand.
    Demand propagated to components should be zero, but both parts should be in the dict.
    """
    # Arrange
    assembly_pk = 100
    component_pk = 101
    quantity_needed_assembly = 10.0
    top_level_part_name = "TOP_LEVEL_PART_C"

    assembly_part_data = PartData(
        pk=assembly_pk, name="Assembly Fully Stocked", is_purchaseable=False, is_assembly=True,
        total_in_stock=5.0, building=5.0, # Effective availability = 10.0
        required_for_build_orders=0.0, required_for_sales_orders=0.0, ordering=0.0
    )
    component_part_data = PartData(
        pk=component_pk, name="Component A", is_purchaseable=True, is_assembly=False,
        total_in_stock=0, required_for_build_orders=0, required_for_sales_orders=0, ordering=0, building=0
    )

    def get_part_side_effect(part_pk_arg):
        if part_pk_arg == assembly_pk: return (assembly_part_data, [])
        elif part_pk_arg == component_pk: return (component_part_data, [])
        pytest.fail(f"Unexpected part PK requested: {part_pk_arg}")
        return (None, [])
    mock_api_client.get_part_data.side_effect = get_part_side_effect

    mock_bom_item = BomItemData(sub_part=component_pk, quantity=2.0)
    mock_api_client.get_bom_data.return_value = ([mock_bom_item], [])

    # Expected:
    # Assembly gross demand = 10.0
    # Assembly effective availability = 10.0
    # Net demand for components = max(0, 10.0 - 10.0) = 0.0
    # Demand propagated to component = 0.0 * 2.0 = 0.0
    # Component's total_required should be 0.0

    # Act
    output_tables_instance = OutputTables()
    calculator._calculate_required_recursive(assembly_pk, quantity_needed_assembly, top_level_part_name, output_tables_instance)

    # Assert
    assert assembly_pk in calculator.calculated_parts_dict
    assert component_pk in calculator.calculated_parts_dict # Component should still be added

    actual_assembly = calculator.calculated_parts_dict[assembly_pk]
    actual_component = calculator.calculated_parts_dict[component_pk]

    assert actual_assembly.total_required == quantity_needed_assembly
    assert actual_assembly.belongs_to_top_parts == {top_level_part_name}
    assert actual_component.total_required == 0.0 # Net demand propagated was zero
    assert actual_component.belongs_to_top_parts == {top_level_part_name} # Still associated
    assert not output_tables_instance.warnings

    # Verify mocks: Part data for both, BOM for assembly should still be fetched
    # because net demand calculation happens before deciding whether to recurse.
    mock_api_client.get_part_data.assert_any_call(assembly_pk)
    mock_api_client.get_part_data.assert_any_call(component_pk)
    assert mock_api_client.get_part_data.call_count == 2
    # BOM is fetched, but recursion doesn't happen if net demand is zero
    mock_api_client.get_bom_data.assert_called_once_with(assembly_pk)
def test_calculate_required_recursive_netting_partial_coverage(calculator, mock_api_client):
    """
    Tests netting: Assembly is needed, effective availability partially covers the gross demand.
    Demand propagated to components should be based on the remaining net demand.
    """
    # Arrange
    assembly_pk = 200
    component_pk = 201
    quantity_needed_assembly = 10.0
    component_qty_per_assembly = 2.0
    top_level_part_name = "TOP_LEVEL_PART_D"

    assembly_part_data = PartData(
        pk=assembly_pk, name="Assembly Partial Stock", is_purchaseable=False, is_assembly=True,
        total_in_stock=3.0, building=2.0, # Effective availability = 5.0
        required_for_build_orders=0.0, required_for_sales_orders=0.0, ordering=0.0
    )
    component_part_data = PartData(
        pk=component_pk, name="Component B", is_purchaseable=True, is_assembly=False,
        total_in_stock=0, required_for_build_orders=0, required_for_sales_orders=0, ordering=0, building=0
    )

    def get_part_side_effect(part_pk_arg):
        if part_pk_arg == assembly_pk: return (assembly_part_data, [])
        elif part_pk_arg == component_pk: return (component_part_data, [])
        pytest.fail(f"Unexpected part PK requested: {part_pk_arg}")
        return (None, [])
    mock_api_client.get_part_data.side_effect = get_part_side_effect

    mock_bom_item = BomItemData(sub_part=component_pk, quantity=component_qty_per_assembly)
    mock_api_client.get_bom_data.return_value = ([mock_bom_item], [])

    # Expected:
    # Assembly gross demand = 10.0
    # Assembly effective availability = 5.0
    # Net demand for components = max(0, 10.0 - 5.0) = 5.0
    # Demand propagated to component = 5.0 * 2.0 = 10.0

    # Act
    output_tables_instance = OutputTables()
    calculator._calculate_required_recursive(assembly_pk, quantity_needed_assembly, top_level_part_name, output_tables_instance)

    # Assert
    assert assembly_pk in calculator.calculated_parts_dict
    assert component_pk in calculator.calculated_parts_dict

    actual_assembly = calculator.calculated_parts_dict[assembly_pk]
    actual_component = calculator.calculated_parts_dict[component_pk]

    assert actual_assembly.total_required == quantity_needed_assembly
    assert actual_assembly.belongs_to_top_parts == {top_level_part_name}
    assert actual_component.total_required == 10.0 # Net demand propagated
    assert actual_component.belongs_to_top_parts == {top_level_part_name}
    assert not output_tables_instance.warnings

    # Verify mocks
    assert mock_api_client.get_part_data.call_count == 2
    mock_api_client.get_part_data.assert_any_call(assembly_pk)
    mock_api_client.get_part_data.assert_any_call(component_pk)
    mock_api_client.get_bom_data.assert_called_once_with(assembly_pk)


def test_calculate_required_recursive_netting_multi_level(calculator, mock_api_client):
    """
    Tests netting: An assembly (SA1) is used by two top-level assemblies (TLA1, TLA2).
    The total gross demand for SA1 is accumulated. The demand propagated to SA1's
    components (C3) should be based on the *net* demand calculated using the
    *accumulated* gross demand for SA1 and SA1's availability.
    Also tests that belongs_to_top_parts accumulates correctly.
    """
    # Arrange
    tla1_pk, tla2_pk = 300, 301
    sa1_pk = 302 # Sub-assembly
    c3_pk = 303  # Component of SA1
    tla1_name = "TLA1_NAME"
    tla2_name = "TLA2_NAME"

    qty_tla1_needed = 5.0
    qty_tla2_needed = 10.0
    qty_sa1_per_tla = 1.0
    qty_c3_per_sa1 = 4.0

    tla1_data = PartData(pk=tla1_pk, name=tla1_name, is_purchaseable=False, is_assembly=True, total_in_stock=0, building=0, required_for_build_orders=0, required_for_sales_orders=0, ordering=0)
    tla2_data = PartData(pk=tla2_pk, name=tla2_name, is_purchaseable=False, is_assembly=True, total_in_stock=0, building=0, required_for_build_orders=0, required_for_sales_orders=0, ordering=0)
    sa1_data = PartData(
        pk=sa1_pk, name="SA1", is_purchaseable=False, is_assembly=True,
        total_in_stock=3.0, building=2.0, # Effective availability = 5.0
        required_for_build_orders=0.0, required_for_sales_orders=0.0, ordering=0.0
    )
    c3_data = PartData(pk=c3_pk, name="C3", is_purchaseable=True, is_assembly=False, total_in_stock=0, building=0, required_for_build_orders=0, required_for_sales_orders=0, ordering=0)

    part_data_map = {
        tla1_pk: tla1_data, tla2_pk: tla2_data, sa1_pk: sa1_data, c3_pk: c3_data
    }
    mock_api_client.get_part_data.side_effect = lambda pk: (part_data_map.get(pk), [])

    bom_map = {
        tla1_pk: [BomItemData(sub_part=sa1_pk, quantity=qty_sa1_per_tla)],
        tla2_pk: [BomItemData(sub_part=sa1_pk, quantity=qty_sa1_per_tla)],
        sa1_pk: [BomItemData(sub_part=c3_pk, quantity=qty_c3_per_sa1)],
        c3_pk: []
    }
    mock_api_client.get_bom_data.side_effect = lambda pk: (bom_map.get(pk), [])

    # Expected Calculation Steps:
    # Process TLA1 (needs 5.0, name=tla1_name):
    #   - TLA1 total_req = 5.0, belongs_to = {tla1_name}
    #   - Recurse SA1 (needs 5.0, top_level=tla1_name):
    #     - SA1 total_req = 5.0, belongs_to = {tla1_name}
    #     - SA1 avail = 5.0, net_demand = max(0, 5.0 - 5.0) = 0.0
    #     - Recurse C3 (needs 0.0, top_level=tla1_name):
    #       - C3 total_req = 0.0, belongs_to = {tla1_name}
    # Process TLA2 (needs 10.0, name=tla2_name):
    #   - TLA2 total_req = 10.0, belongs_to = {tla2_name}
    #   - Recurse SA1 (needs 10.0, top_level=tla2_name):
    #     - SA1 total_req = 5.0 + 10.0 = 15.0, belongs_to = {tla1_name, tla2_name}
    #     - SA1 avail = 5.0, net_demand = max(0, 15.0 - 5.0) = 10.0
    #     - Recurse C3 (needs 10.0 * 4.0 = 40.0, top_level=tla2_name):
    #       - C3 total_req = 0.0 + 40.0 = 40.0, belongs_to = {tla1_name, tla2_name}

    # Act
    output_tables_instance = OutputTables()
    calculator._calculate_required_recursive(tla1_pk, qty_tla1_needed, tla1_name, output_tables_instance)
    # For the second call, it will use the same output_tables_instance, accumulating warnings if any.
    calculator._calculate_required_recursive(tla2_pk, qty_tla2_needed, tla2_name, output_tables_instance)

    # Assert
    assert tla1_pk in calculator.calculated_parts_dict
    assert tla2_pk in calculator.calculated_parts_dict
    assert sa1_pk in calculator.calculated_parts_dict
    assert c3_pk in calculator.calculated_parts_dict

    actual_tla1 = calculator.calculated_parts_dict[tla1_pk]
    actual_tla2 = calculator.calculated_parts_dict[tla2_pk]
    actual_sa1 = calculator.calculated_parts_dict[sa1_pk]
    actual_c3 = calculator.calculated_parts_dict[c3_pk]

    assert actual_tla1.total_required == qty_tla1_needed
    assert actual_tla1.belongs_to_top_parts == {tla1_name}
    assert actual_tla2.total_required == qty_tla2_needed
    assert actual_tla2.belongs_to_top_parts == {tla2_name}
    assert actual_sa1.total_required == 15.0 # Accumulated gross
    assert actual_sa1.belongs_to_top_parts == {tla1_name, tla2_name} # Accumulated names
    assert actual_c3.total_required == 20.0 # Net propagated only from the second path (10 * 4.0)
    assert actual_c3.belongs_to_top_parts == {tla1_name, tla2_name} # Accumulated names
    assert not output_tables_instance.warnings

    # Verify calls (simplified) - BOM for SA1 might be called twice due to structure
    assert mock_api_client.get_part_data.called
    assert mock_api_client.get_bom_data.called
    mock_api_client.get_bom_data.assert_any_call(tla1_pk)
    mock_api_client.get_bom_data.assert_any_call(tla2_pk)
    mock_api_client.get_bom_data.assert_any_call(sa1_pk)
    calls_to_get_bom_data = [call_args[0][0] for call_args in mock_api_client.get_bom_data.call_args_list]
    assert c3_pk not in calls_to_get_bom_data
# --- Tests for calculate_orders ---

def test_calculate_orders_simple_purchase(calculator, mock_api_client):
    """
    Tests the main calculate_orders method for a simple case:
    ordering a single purchased part that is out of stock.
    Checks the final OutputTables, belongs_to_top_parts, and warnings.
    """
    # Arrange
    input_pk = 1314 # Simulating Part 1314
    input_name = "Part 1314"
    quantity_to_build = 2.0 # Needed = 2
    stock_available = 0.0   # Available = 0 (total_in_stock - commitments)
    on_order = 106.0        # OnOrder = 106
    # Commitments (required_for_build_orders, required_for_sales_orders) are 0 for simplicity to make available = total_in_stock

    # InputPart uses identifier (string PK here) and quantity
    input_list = [InputPart(part_identifier=str(input_pk), quantity_to_build=quantity_to_build)]

    # Mock PartData for the purchased part
    purchased_part_data = PartData(
        pk=input_pk, name=input_name, is_purchaseable=True, is_assembly=False,
        total_in_stock=stock_available, # 0
        required_for_build_orders=0,    # 0
        required_for_sales_orders=0,    # 0
        ordering=on_order,              # 106
        building=0
    )
    # With new logic:
    # Availability = total_in_stock - (required_for_build_orders + required_for_sales_orders)
    # Availability = 0.0 - (0 + 0) = 0.0
    # Required = 2.0
    # To Order = total_required - available
    # To Order = 2.0 - 0.0 = 2.0

    mock_api_client.get_part_data.return_value = (purchased_part_data, []) # Return tuple
    mock_api_client.get_bom_data.return_value = ([], []) # Return tuple, not called for non-assembly

    # Expected Output
    expected_part_to_order = CalculatedPart(
        pk=input_pk, name=input_name, is_purchaseable=True, is_assembly=False,
        total_in_stock=stock_available, required_for_build_orders=0, required_for_sales_orders=0,
        ordering=on_order, building=0,
        total_required=quantity_to_build, # 2.0
        available=0.0, # Calculated availability (0.0)
        to_order=2.0,  # Calculated to_order (2.0)
        to_build=0.0,
        belongs_to_top_parts={input_name} # Should belong to itself (the input part name)
    )
    # expected_output = OutputTables( # Not needed for direct comparison of parts_to_order
    #     parts_to_order=[expected_part_to_order],
    #     subassemblies_to_build=[]
    # )

    # Act
    actual_output = calculator.calculate_orders(input_list)

    # Assert
    # Compare OutputTables content
    assert len(actual_output.parts_to_order) == 1
    assert len(actual_output.subassemblies_to_build) == 0
    assert actual_output.parts_to_order[0] == expected_part_to_order # Relies on dataclass __eq__
    assert not actual_output.warnings, f"Expected no warnings, but got: {actual_output.warnings}"


    # Verify mocks
    # get_part_data called once in calculate_orders to get name, then _calculate_required_recursive creates CalculatedPart
    mock_api_client.get_part_data.assert_called_once_with(input_pk)
    mock_api_client.get_bom_data.assert_not_called()

def test_calculate_orders_top_level_part_not_found_warning(calculator, mock_api_client):
    """
    Tests that a warning is generated if a top-level input part is not found.
    """
    # Arrange
    non_existent_pk = 9999
    input_list = [InputPart(part_identifier=str(non_existent_pk), quantity_to_build=1.0)]

    # Simulate part not found - API client returns (None, [warning_message])
    api_warning_message = f"API: Part not found in InvenTree (ID: {non_existent_pk}). Status: 404."
    mock_api_client.get_part_data.return_value = (None, [api_warning_message])

    # Act
    actual_output = calculator.calculate_orders(input_list)

    # Assert
    assert not actual_output.parts_to_order
    assert not actual_output.subassemblies_to_build
    assert len(actual_output.warnings) == 1 # Expecting the warning from ApiClient
    # The calculator itself also logs an error but the warning comes from ApiClient
    assert actual_output.warnings[0] == api_warning_message
    mock_api_client.get_part_data.assert_called_once_with(non_existent_pk)

def test_calculate_orders_part_neither_purchaseable_nor_assembly_warning(calculator, mock_api_client):
    """
    Tests that a warning is generated if a part is neither purchaseable nor an assembly
    during the final calculation phase.
    """
    # Arrange
    part_pk = 777
    part_name = "Neither Part"
    input_list = [InputPart(part_identifier=str(part_pk), quantity_to_build=1.0)]

    # Mock PartData for a part that is neither purchaseable nor assembly
    part_data = PartData(
        pk=part_pk, name=part_name, is_purchaseable=False, is_assembly=False,
        total_in_stock=10.0, required_for_build_orders=0, required_for_sales_orders=0,
        ordering=0, building=0
    )
    mock_api_client.get_part_data.return_value = (part_data, []) # Return tuple
    mock_api_client.get_bom_data.return_value = ([], []) # Return tuple, though not called

    # Act
    actual_output = calculator.calculate_orders(input_list)

    # Assert
    assert not actual_output.parts_to_order
    assert not actual_output.subassemblies_to_build
    assert len(actual_output.warnings) == 1
    expected_warning_msg = f"Part '{part_name}' (PK: {part_pk}) is neither purchaseable nor an assembly. Cannot be ordered or built through this process. Setting to_order and to_build to 0."
    assert actual_output.warnings[0] == expected_warning_msg
    mock_api_client.get_part_data.assert_called_once_with(part_pk)
    mock_api_client.get_bom_data.assert_not_called() # Not an assembly

def test_calculate_orders_invalid_input_identifier_warning(calculator, mock_api_client):
    """
    Tests that a warning is generated if an input part identifier is invalid (e.g., not an int).
    """
    # Arrange
    invalid_identifier = "abc"
    input_list = [InputPart(part_identifier=invalid_identifier, quantity_to_build=1.0)]

    # Act
    actual_output = calculator.calculate_orders(input_list)

    # Assert
    assert not actual_output.parts_to_order
    assert not actual_output.subassemblies_to_build
    assert len(actual_output.warnings) == 1
    expected_warning_msg = f"Invalid part identifier '{invalid_identifier}'. Must be an integer PK. Skipping."
    assert actual_output.warnings[0] == expected_warning_msg
    mock_api_client.get_part_data.assert_not_called() # Should not be called due to ValueError
    """
    Tests availability calculation for an assembly part with stock, commitments, and in-production units.
    Formula: available = total_in_stock - (required_builds + required_sales) # Changed: removed '+ building'
    """
    # Arrange
    # calculator instance is provided by the fixture

    # Create part data instance for an assembly item
    part_data = PartData(
        pk=2,
        name="Test Subassembly",
        is_purchaseable=False,
        is_assembly=True,
        total_in_stock=50.0,
        required_for_build_orders=5.0,
        required_for_sales_orders=2.0,
        ordering=0.0, # Not relevant for assembly
        building=10.0 # Units currently in production
    )
    # Expected: 50 - (5 + 2) = 43.0
    expected_availability = 50.0 - (5.0 + 2.0) # Changed: Removed '+ 10.0'

    # Act
    actual_availability = calculator._calculate_availability(part_data)

    # Assert
    assert actual_availability == expected_availability, \
        f"Expected availability {expected_availability}, but got {actual_availability}"
def test_calculate_orders_simple_assembly_build(calculator, mock_api_client):
    """
    Tests the main calculate_orders method for a simple case:
    ordering a single assembly part that needs to be built.
    Checks the final OutputTables and belongs_to_top_parts.
    """
    # Arrange
    assembly_pk = 40
    assembly_name = "Assembly To Build"
    quantity_to_build = 10.0
    stock_available = 5.0
    in_production = 2.0
    req_build = 1.0
    req_sales = 1.0

    input_list = [InputPart(part_identifier=str(assembly_pk), quantity_to_build=quantity_to_build)]

    # Mock PartData for the assembly part
    assembly_part_data = PartData(
        pk=assembly_pk, name=assembly_name, is_purchaseable=False, is_assembly=True,
        total_in_stock=stock_available, # 5
        required_for_build_orders=req_build, # 1
        required_for_sales_orders=req_sales, # 1
        ordering=0,
        building=in_production # 2
    )
    # Availability = stock - (req_build + req_sales) = 5 - (1 + 1) = 3.0
    # Required = 10.0
    # Effective Supply = Available + In Production = 3.0 + 2.0 = 5.0
    # To Build = Required - Effective Supply = 10.0 - 5.0 = 5.0

    mock_api_client.get_part_data.return_value = (assembly_part_data, []) # Return tuple
    mock_api_client.get_bom_data.return_value = ([], []) # Return tuple for empty BOM

    # Expected Output
    expected_assembly_to_build = CalculatedPart(
        pk=assembly_pk, name=assembly_name, is_purchaseable=False, is_assembly=True,
        total_in_stock=stock_available, required_for_build_orders=req_build, required_for_sales_orders=req_sales,
        ordering=0, building=in_production,
        total_required=quantity_to_build, # 10.0
        available=3.0, # Calculated availability
        to_order=0.0,
        to_build=5.0, # Calculated to_build
        belongs_to_top_parts={assembly_name} # Belongs to itself (input part name)
    )
    expected_output = OutputTables(
        parts_to_order=[],
        subassemblies_to_build=[expected_assembly_to_build]
    )

    # Act
    actual_output = calculator.calculate_orders(input_list)

    # Assert
    assert len(actual_output.parts_to_order) == 0
    assert len(actual_output.subassemblies_to_build) == 1
    assert actual_output.subassemblies_to_build[0] == expected_assembly_to_build
    assert not actual_output.warnings, f"Expected no warnings, got: {actual_output.warnings}"

    # Verify mocks
    mock_api_client.get_part_data.assert_called_once_with(assembly_pk)
    # BOM is fetched in _calculate_required_recursive if net demand > 0 (which it is here)
    mock_api_client.get_bom_data.assert_called_once_with(assembly_pk)


# --- New Tests for Specific Netting Scenarios ---

def test_netting_component_needed_elsewhere_and_final_calculation(calculator, mock_api_client):
    """
    Complex scenario checking final calculation and belongs_to:
    - Input: Assembly A (needs 10), Assembly B (needs 5)
    - Assembly A BOM: 2x Component C
    - Assembly B BOM: 3x Component C
    - Assembly A: Stock=10 (covers demand)
    - Assembly B: Stock=0
    - Component C: Stock=1, OnOrder=0, Purchaseable=True
    Expected: Build 5 B, Order 14 C. B belongs to "Assembly B", C belongs to {"Assembly A", "Assembly B"}.
    """
    # Arrange
    a_pk, b_pk, c_pk = 400, 401, 402
    a_name = "Assembly A (Stocked)"
    b_name = "Assembly B (No Stock)"
    c_name = "Component C"
    qty_a_needed = 10.0
    qty_b_needed = 5.0
    qty_c_per_a = 2.0
    qty_c_per_b = 3.0

    input_list = [
        InputPart(part_identifier=str(a_pk), quantity_to_build=qty_a_needed),
        InputPart(part_identifier=str(b_pk), quantity_to_build=qty_b_needed)
    ]

    # --- Part Data ---
    part_a_data = PartData(pk=a_pk, name=a_name, is_purchaseable=False, is_assembly=True, total_in_stock=10.0, building=0.0, required_for_build_orders=0.0, required_for_sales_orders=0.0, ordering=0.0) # Avail=10
    part_b_data = PartData(pk=b_pk, name=b_name, is_purchaseable=False, is_assembly=True, total_in_stock=0.0, building=0.0, required_for_build_orders=0.0, required_for_sales_orders=0.0, ordering=0.0) # Avail=0
    part_c_data = PartData(pk=c_pk, name=c_name, is_purchaseable=True, is_assembly=False, total_in_stock=1.0, building=0.0, ordering=0.0, required_for_build_orders=0.0, required_for_sales_orders=0.0) # Avail=1

    part_data_map = {a_pk: part_a_data, b_pk: part_b_data, c_pk: part_c_data}
    # Update side_effect to return tuple (data, warnings_list)
    mock_api_client.get_part_data.side_effect = lambda pk: (part_data_map.get(pk), [])

    # --- BOM Data ---
    bom_map = {
        a_pk: [BomItemData(sub_part=c_pk, quantity=qty_c_per_a)],
        b_pk: [BomItemData(sub_part=c_pk, quantity=qty_c_per_b)],
        c_pk: [],
    }
    # Update side_effect to return tuple (data, warnings_list)
    mock_api_client.get_bom_data.side_effect = lambda pk: (bom_map.get(pk), [])

    # --- Expected Calculation Steps ---
    # Process A (needs 10, name=a_name):
    #   - A total_req=10, belongs={a_name}
    #   - A avail=10, net_demand=max(0, 10-10)=0
    #   - Recurse C (needs 0, top_level=a_name):
    #     - C total_req=0, belongs={a_name}
    # Process B (needs 5, name=b_name):
    #   - B total_req=5, belongs={b_name}
    #   - B avail=0, net_demand=max(0, 5-0)=5
    #   - Recurse C (needs 5*3=15, top_level=b_name):
    #     - C total_req=0+15=15, belongs={a_name, b_name}

    # --- Expected Final Output ---
    # Part A: req=10, avail=10, build=0 -> eff_supply=10 -> to_build=max(0, 10-10)=0
    # Part B: req=5, avail=0, build=0 -> eff_supply=0 -> to_build=max(0, 5-0)=5
    # Part C: req=15, avail=1, order=0 -> eff_supply=1 -> to_order=max(0, 15-1)=14

    expected_order_c = CalculatedPart(
        pk=c_pk, name=c_name, is_purchaseable=True, is_assembly=False,
        total_in_stock=1.0, required_for_build_orders=0.0, required_for_sales_orders=0.0,
        ordering=0.0, building=0.0,
        total_required=15.0, available=1.0, to_order=14.0, to_build=0.0,
        belongs_to_top_parts={a_name, b_name} # Should belong to both
    )
    expected_build_b = CalculatedPart(
        pk=b_pk, name=b_name, is_purchaseable=False, is_assembly=True,
        total_in_stock=0.0, required_for_build_orders=0.0, required_for_sales_orders=0.0,
        ordering=0.0, building=0.0,
        total_required=5.0, available=0.0, to_order=0.0, to_build=5.0,
        belongs_to_top_parts={b_name} # Only belongs to B
    )
    # Part A is not in the final output tables as to_build/to_order is 0
    expected_output = OutputTables(
        parts_to_order=[expected_order_c],
        subassemblies_to_build=[expected_build_b]
    )

    # Act
    actual_output = calculator.calculate_orders(input_list)

    # Assert Final Output
    actual_output.parts_to_order.sort(key=lambda p: p.pk)
    expected_output.parts_to_order.sort(key=lambda p: p.pk)
    actual_output.subassemblies_to_build.sort(key=lambda p: p.pk)
    expected_output.subassemblies_to_build.sort(key=lambda p: p.pk)

    assert actual_output == expected_output, \
        f"Final output object mismatch. Expected {expected_output}, got {actual_output}"
    assert not actual_output.warnings, f"Expected no warnings, got: {actual_output.warnings}"

    # Assert Intermediate State (Optional: Check calculated_parts_dict)
    assert a_pk in calculator.calculated_parts_dict
    assert b_pk in calculator.calculated_parts_dict
    assert c_pk in calculator.calculated_parts_dict
    assert calculator.calculated_parts_dict[a_pk].total_required == 10.0
    assert calculator.calculated_parts_dict[a_pk].belongs_to_top_parts == {a_name}
    assert calculator.calculated_parts_dict[b_pk].total_required == 5.0
    assert calculator.calculated_parts_dict[b_pk].belongs_to_top_parts == {b_name}
    assert calculator.calculated_parts_dict[c_pk].total_required == 15.0
    assert calculator.calculated_parts_dict[c_pk].belongs_to_top_parts == {a_name, b_name}

    # Verify mocks
    assert mock_api_client.get_part_data.call_count == 3 # A, B, C
    mock_api_client.get_part_data.assert_any_call(a_pk)
    mock_api_client.get_part_data.assert_any_call(b_pk)
    mock_api_client.get_part_data.assert_any_call(c_pk)
    assert mock_api_client.get_bom_data.call_count == 2 # A, B
    mock_api_client.get_bom_data.assert_any_call(a_pk)
    mock_api_client.get_bom_data.assert_any_call(b_pk)
    calls_to_get_bom_data = [call_args[0][0] for call_args in mock_api_client.get_bom_data.call_args_list]
    assert c_pk not in calls_to_get_bom_data


def test_calculate_orders_multi_level_with_shared_component(calculator, mock_api_client):
    """
    Tests multi-level BOM with shared component and checks belongs_to_top_parts.
    Input: Top Assembly (TA, needs 1)
    TA BOM: 2x SA1, 1x SA2
    SA1 BOM: 3x CC
    SA2 BOM: 4x CC
    Expected: Build 1 TA, 2 SA1, 1 SA2. Order 10 CC. All belong to "Top Assembly".
    """
def test_calculate_orders_assembly_shown_if_building_even_if_not_needed(calculator, mock_api_client):
    """
    Tests that an assembly is included in the subassemblies_to_build list
    if it has a non-zero 'building' quantity, even if 'total_required' is 0
    and 'to_build' calculates to 0.
    """
    # Arrange
    assembly_pk = 50
    assembly_name = "Assembly In Production Not Needed"
    stock_val = 10.0
    building_val = 5.0 # Key: This assembly is being built

    # Input this assembly with a demand of 0
    input_list = [InputPart(part_identifier=str(assembly_pk), quantity_to_build=0.0)]

    assembly_part_data = PartData(
        pk=assembly_pk,
        name=assembly_name,
        is_purchaseable=False,
        is_assembly=True,
        total_in_stock=stock_val,
        required_for_build_orders=0.0,
        required_for_sales_orders=0.0,
        ordering=0.0,
        building=building_val
    )

    mock_api_client.get_part_data.return_value = (assembly_part_data, []) # Return tuple
    mock_api_client.get_bom_data.return_value = ([], []) # Return tuple, no sub-components for simplicity

    # Expected calculations for this assembly:
    # total_required = 0.0 (from input_list)
    # available = total_in_stock - (req_build_orders + req_sales_orders)
    #           = 10.0 - (0.0 + 0.0) = 10.0
    # to_build = max(0, total_required - (available + building))
    #          = max(0, 0.0 - (10.0 + 5.0)) = max(0, -15.0) = 0.0

    expected_calculated_part = CalculatedPart(
        pk=assembly_pk,
        name=assembly_name,
        is_purchaseable=False,
        is_assembly=True,
        total_in_stock=stock_val,
        required_for_build_orders=0.0,
        required_for_sales_orders=0.0,
        ordering=0.0,
        building=building_val,
        total_required=0.0, # As per input
        available=10.0,     # Calculated
        to_order=0.0,
        to_build=0.0,       # Calculated
        belongs_to_top_parts={assembly_name}
    )

    # Act
    actual_output = calculator.calculate_orders(input_list)

    # Assert
    assert len(actual_output.parts_to_order) == 0, "No parts should be ordered"
    assert len(actual_output.subassemblies_to_build) == 1, "Assembly should be in the build list"
    assert not actual_output.warnings, f"Expected no warnings, got: {actual_output.warnings}"
    
    output_assembly = actual_output.subassemblies_to_build[0]
    assert output_assembly.pk == expected_calculated_part.pk
    assert output_assembly.name == expected_calculated_part.name
    assert output_assembly.is_assembly == expected_calculated_part.is_assembly
    assert output_assembly.total_in_stock == expected_calculated_part.total_in_stock
    assert output_assembly.building == expected_calculated_part.building
    assert output_assembly.total_required == expected_calculated_part.total_required
    assert output_assembly.available == expected_calculated_part.available
    assert output_assembly.to_build == expected_calculated_part.to_build
    assert output_assembly.belongs_to_top_parts == expected_calculated_part.belongs_to_top_parts

    # Verify mocks
    mock_api_client.get_part_data.assert_called_once_with(assembly_pk)
    # BOM data might be called if is_assembly is true, even if net demand is zero,
    # to ensure all parts are processed for belongs_to_top_parts tracking.
    # However, in this specific case, the path through _calculate_required_recursive
    # for the top-level part itself (assembly_pk) with quantity_needed_for_parent = 0
    # and effective_availability > 0 means net_demand_for_this_path_components will be 0.
    # The BOM fetch happens after this.
    mock_api_client.get_bom_data.assert_called_once_with(assembly_pk)