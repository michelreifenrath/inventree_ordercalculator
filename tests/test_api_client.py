import pytest
from unittest.mock import patch, MagicMock

from unittest.mock import patch, MagicMock

from requests.exceptions import HTTPError # Added import
from inventree_order_calculator.api_client import ApiClient
from inventree_order_calculator.models import PartData, BomItemData # Import PartData and BomItemData

# Mock configuration data (replace with actual config loading later)
MOCK_INVENTREE_URL = "http://mock-inventree.local"
MOCK_INVENTREE_TOKEN = "mock_token_123"

# Placeholder class removed, using actual import now
# Fixture to provide a mocked ApiClient instance
@pytest.fixture
def mock_api_client(monkeypatch):
    """Provides an ApiClient instance with mocked InvenTreeAPI."""
    # Mock the InvenTreeAPI class within the api_client module
    mock_inventree_api_class = MagicMock(name="MockInvenTreeAPIClass")
    mock_api_instance = mock_inventree_api_class.return_value
    monkeypatch.setattr('inventree_order_calculator.api_client.InvenTreeAPI', mock_inventree_api_class)

    # Instantiate the client - its __init__ will now use the mocked class
    client = ApiClient(MOCK_INVENTREE_URL, MOCK_INVENTREE_TOKEN)

    # Return the client and the mock instance for assertions in tests
    # Yielding allows teardown if needed later
    yield client, mock_api_instance, mock_inventree_api_class

# --- Test Cases ---

def test_api_client_initialization(mock_api_client):
    """Test that ApiClient initializes InvenTreeAPI correctly using fixture."""
    client, mock_api_instance, mock_inventree_api_class = mock_api_client
    # Check that the mocked class was called correctly during ApiClient init
    mock_inventree_api_class.assert_called_once_with(host=MOCK_INVENTREE_URL, token=MOCK_INVENTREE_TOKEN, connect=False)
    # Check that the client holds the instance returned by the mocked class
    assert client.api == mock_api_instance

@patch('inventree_order_calculator.api_client.Company')
@patch('inventree_order_calculator.api_client.SupplierPart')
@patch('inventree_order_calculator.api_client.Part')
def test_get_part_data_success(MockPart, MockSupplierPart, MockCompany, mock_api_client):
    """Test fetching part data successfully, including supplier names."""
    client, mock_api_instance, _ = mock_api_client
    mock_part_instance = MockPart.return_value
    mock_raw_data = {
        'pk': 1, 'name': 'Test Part', 'purchaseable': True, 'assembly': False,
        'total_in_stock': 100.5, 'required_for_build_orders': 10.0,
        'required_for_sales_orders': 5.0, 'ordering': 20.0, 'building': 0.0,
        'consumable': True
    }
    mock_part_instance._data = mock_raw_data

    # Mock SupplierPart.list
    mock_sp1 = MagicMock()
    mock_sp1.supplier = 101 # Supplier PK
    mock_sp2 = MagicMock()
    mock_sp2.supplier = 102
    MockSupplierPart.list.return_value = [mock_sp1, mock_sp2]

    # Mock Company instantiation
    mock_company1 = MagicMock()
    mock_company1.name = "Supplier Alpha"
    mock_company2 = MagicMock()
    mock_company2.name = "Supplier Beta"

    # Configure MockCompany to return different instances based on pk
    def company_side_effect(api, pk):
        if pk == 101:
            return mock_company1
        elif pk == 102:
            return mock_company2
        return MagicMock() # Default mock if pk doesn't match
    MockCompany.side_effect = company_side_effect

    part_data, warnings = client.get_part_data(1)

    MockPart.assert_called_once_with(mock_api_instance, pk=1)
    MockSupplierPart.list.assert_called_once_with(mock_api_instance, part=1)
    MockCompany.assert_any_call(mock_api_instance, pk=101)
    assert not warnings, "Expected no warnings for a successful call"
    MockCompany.assert_any_call(mock_api_instance, pk=102)

    assert isinstance(part_data, PartData)
    assert part_data.pk == 1
    assert part_data.name == 'Test Part'
    assert part_data.is_purchaseable is True
    assert part_data.is_assembly is False
    assert part_data.total_in_stock == 100.5
    assert part_data.required_for_build_orders == 10.0
    assert part_data.required_for_sales_orders == 5.0
    assert part_data.ordering == 20.0
    assert part_data.building == 0.0
    assert part_data.is_consumable is True
    assert part_data.supplier_names == ["Supplier Alpha", "Supplier Beta"]

@patch('inventree_order_calculator.api_client.SupplierPart') # Patch SupplierPart for this test too
@patch('inventree_order_calculator.api_client.Part')
def test_get_part_data_not_found(MockPart, MockSupplierPart, mock_api_client): # Added MockSupplierPart
    """Test fetching part data when the part is not found using fixture."""
    client, mock_api_instance, _ = mock_api_client
    MockPart.side_effect = Exception("Part not found simulation")

    part_data, warnings = client.get_part_data(999)

    MockPart.assert_called_once_with(mock_api_instance, pk=999)
    # SupplierPart.list should not be called if Part fetching fails
    MockSupplierPart.list.assert_not_called()
    assert part_data is None
    assert len(warnings) >= 1 # Expect some warning/error message
    # The exact message depends on how Part(pk=...) failure is converted to a warning by ApiClient
    # For now, just check that warnings list is not empty.
    # A more specific check could be:
    # assert any("Part not found" in w.lower() or "error fetching part" in w.lower() for w in warnings)

@patch('inventree_order_calculator.api_client.Company')
@patch('inventree_order_calculator.api_client.SupplierPart')
@patch('inventree_order_calculator.api_client.Part')
def test_get_part_data_no_supplier_parts(MockPart, MockSupplierPart, MockCompany, mock_api_client):
    """Test fetching part data when a part has no supplier parts."""
    client, mock_api_instance, _ = mock_api_client
    mock_part_instance = MockPart.return_value
    mock_raw_data = {'pk': 2, 'name': 'Part No Suppliers', 'purchaseable': True, 'assembly': False, 'total_in_stock': 10.0, 'consumable': False}
    mock_part_instance._data = mock_raw_data

    MockSupplierPart.list.return_value = [] # No supplier parts

    part_data, warnings = client.get_part_data(2)

    MockPart.assert_called_once_with(mock_api_instance, pk=2)
    MockSupplierPart.list.assert_called_once_with(mock_api_instance, part=2)
    MockCompany.assert_not_called() # Company should not be called if no supplier parts

    assert isinstance(part_data, PartData)
    assert part_data.pk == 2
    assert part_data.supplier_names == []
    assert not warnings, f"Expected no warnings, got: {warnings}"

@patch('inventree_order_calculator.api_client.Company')
@patch('inventree_order_calculator.api_client.SupplierPart')
@patch('inventree_order_calculator.api_client.Part')
def test_get_part_data_supplier_part_list_fails(MockPart, MockSupplierPart, MockCompany, mock_api_client, caplog): # Added caplog
    """Test fetching part data when SupplierPart.list call fails."""
    client, mock_api_instance, _ = mock_api_client
    caplog.set_level("WARNING") # Capture warning logs
    mock_part_instance = MockPart.return_value
    mock_raw_data = {'pk': 3, 'name': 'Part Supplier Fail', 'purchaseable': True, 'assembly': False, 'total_in_stock': 10.0, 'consumable': False}
    mock_part_instance._data = mock_raw_data

    mock_exception = Exception("Failed to list supplier parts")
    MockSupplierPart.list.side_effect = mock_exception

    part_data, warnings = client.get_part_data(3)

    MockPart.assert_called_once_with(mock_api_instance, pk=3)
    MockSupplierPart.list.assert_called_once_with(mock_api_instance, part=3)
    MockCompany.assert_not_called()

    assert isinstance(part_data, PartData) # PartData is still returned
    assert part_data.pk == 3
    assert part_data.supplier_names == [] # Supplier names list is empty due to the error
    assert not warnings, f"Expected no returned warnings, got: {warnings}" # Changed assertion
    assert len(caplog.records) == 1
    log_record = caplog.records[0]
    assert log_record.levelname == "WARNING"
    assert f"An unexpected error occurred while trying to process supplier parts for part 3: {mock_exception}" in log_record.message # Adjusted message to match new logging

@patch('inventree_order_calculator.api_client.Company')
@patch('inventree_order_calculator.api_client.SupplierPart')
@patch('inventree_order_calculator.api_client.Part')
def test_get_part_data_company_fetch_fails(MockPart, MockSupplierPart, MockCompany, mock_api_client, caplog): # Added caplog
    """Test fetching part data when Company call fails for one supplier."""
    client, mock_api_instance, _ = mock_api_client
    caplog.set_level("WARNING") # Capture warning logs
    mock_part_instance = MockPart.return_value
    mock_raw_data = {'pk': 4, 'name': 'Part Company Fail', 'purchaseable': True, 'assembly': False, 'total_in_stock': 10.0, 'consumable': False}
    mock_part_instance._data = mock_raw_data

    mock_sp1 = MagicMock()
    mock_sp1.supplier = 201
    mock_sp2 = MagicMock() # This one will cause Company to fail
    mock_sp2.supplier = 202
    MockSupplierPart.list.return_value = [mock_sp1, mock_sp2]

    mock_company1 = MagicMock()
    mock_company1.name = "Good Supplier"
    mock_company_exception = Exception("Failed to fetch company 202")

    def company_side_effect(api, pk):
        if pk == 201:
            return mock_company1
        elif pk == 202:
            raise mock_company_exception
        return MagicMock()
    MockCompany.side_effect = company_side_effect

    part_data, warnings = client.get_part_data(4)

    MockPart.assert_called_once_with(mock_api_instance, pk=4)
    MockSupplierPart.list.assert_called_once_with(mock_api_instance, part=4)
    MockCompany.assert_any_call(mock_api_instance, pk=201)
    MockCompany.assert_any_call(mock_api_instance, pk=202)

    assert isinstance(part_data, PartData)
    assert part_data.pk == 4
    assert part_data.supplier_names == ["Good Supplier"] # Only the successful one
    assert not warnings, f"Expected no returned warnings, got: {warnings}" # Changed assertion
    
    assert len(caplog.records) == 1
    log_record = caplog.records[0]
    assert log_record.levelname == "WARNING"
    # Adjusted message to match new logging for company fetch failures
    assert f"Could not fetch company name for supplier ID 202 of part 4: {mock_company_exception}" in log_record.message

@patch('inventree_order_calculator.api_client.Company')
@patch('inventree_order_calculator.api_client.SupplierPart')
@patch('inventree_order_calculator.api_client.Part')
def test_get_part_data_supplier_part_missing_supplier_id(MockPart, MockSupplierPart, MockCompany, mock_api_client):
    """Test fetching part data when a SupplierPart object is missing the .supplier attribute."""
    client, mock_api_instance, _ = mock_api_client
    mock_part_instance = MockPart.return_value
    mock_raw_data = {'pk': 5, 'name': 'Part Missing Supplier ID', 'purchaseable': True, 'assembly': False, 'total_in_stock': 10.0, 'consumable': False}
    mock_part_instance._data = mock_raw_data

    mock_sp1 = MagicMock()
    mock_sp1.supplier = 301 # Valid supplier PK
    mock_sp2 = MagicMock()
    mock_sp2.supplier = None # Simulate supplier ID missing but attribute exists
    mock_sp3 = MagicMock() # Another valid one to ensure processing continues
    mock_sp3.supplier = 303


    MockSupplierPart.list.return_value = [mock_sp1, mock_sp2, mock_sp3]

    mock_company1 = MagicMock()
    mock_company1.name = "Supplier Gamma"
    mock_company3 = MagicMock()
    mock_company3.name = "Supplier Delta"


    def company_side_effect(api, pk):
        if pk == 301:
            return mock_company1
        if pk == 303:
            return mock_company3
        return MagicMock()
    MockCompany.side_effect = company_side_effect

    part_data, warnings = client.get_part_data(5)

    MockPart.assert_called_once_with(mock_api_instance, pk=5)
    MockSupplierPart.list.assert_called_once_with(mock_api_instance, part=5)
    MockCompany.assert_any_call(mock_api_instance, pk=301)
    MockCompany.assert_any_call(mock_api_instance, pk=303)
    # MockCompany should not be called for the supplier part with None supplier ID

    assert isinstance(part_data, PartData)
    assert part_data.pk == 5
    assert part_data.supplier_names == ["Supplier Gamma", "Supplier Delta"]
    # Based on current ApiClient, warnings for individual supplier issues like None PK are logged but not added to the *returned* list.
    assert not warnings, f"Expected no returned warnings for this scenario, got: {warnings}"

@patch('inventree_order_calculator.api_client.Company') # Mock Company as it might be called if SupplierPart.list doesn't fail first
@patch('inventree_order_calculator.api_client.SupplierPart')
@patch('inventree_order_calculator.api_client.Part')
def test_get_part_data_supplier_part_specific_400_error(MockPart, MockSupplierPart, MockCompany, mock_api_client, caplog):
    """
    Test get_part_data when SupplierPart.list raises a specific HTTPError
    (status 400, "Select a valid choice...") indicating no supplier parts.
    This should be logged as debug and not result in a warning in the returned list.
    """
    client, mock_api_instance, _ = mock_api_client
    caplog.set_level("DEBUG") # Capture debug logs

    mock_part_instance = MockPart.return_value
    mock_raw_data = {'pk': 6, 'name': 'Part Specific 400 Error', 'purchaseable': True, 'assembly': False, 'total_in_stock': 5.0, 'consumable': False}
    mock_part_instance._data = mock_raw_data

    # Simulate the specific HTTPError
    mock_response = MagicMock()
    mock_response.status_code = 400
    response_json_data = {"part": ["Select a valid choice. That choice is not one of the available choices."]}
    mock_response.json.return_value = response_json_data
    mock_response.text = str(response_json_data) # Or a more realistic JSON string

    http_error = HTTPError(response=mock_response)
    # To make str(http_error) more realistic if needed, though api_client uses response attributes directly
    # http_error.args = (f"400 Client Error: Bad Request for url",)

    MockSupplierPart.list.side_effect = http_error

    part_data, warnings = client.get_part_data(6)

    MockPart.assert_called_once_with(mock_api_instance, pk=6)
    MockSupplierPart.list.assert_called_once_with(mock_api_instance, part=6)
    MockCompany.assert_not_called() # Should not be called if SupplierPart.list fails

    assert isinstance(part_data, PartData)
    assert part_data.pk == 6
    assert part_data.supplier_names == [] # No suppliers found
    assert not warnings, f"Expected no warnings in the returned list, got: {warnings}"

    # Check logs
    assert len(caplog.records) == 1
    log_record = caplog.records[0]
    assert log_record.levelname == "DEBUG"
    assert "Part 6 has no supplier parts listed (API 400 'Select a valid choice'). Proceeding without supplier names." in log_record.message # Adjusted message

@patch('inventree_order_calculator.api_client.Company')
@patch('inventree_order_calculator.api_client.SupplierPart')
@patch('inventree_order_calculator.api_client.Part')
def test_get_part_data_supplier_part_other_api_error(MockPart, MockSupplierPart, MockCompany, mock_api_client, caplog):
    """
    Test get_part_data when SupplierPart.list raises a different HTTPError
    (e.g., status 500 or 400 with a different message).
    This should be logged as a warning but NOT added to the returned warnings list.
    """
    client, mock_api_instance, _ = mock_api_client
    caplog.set_level("WARNING")

    mock_part_instance = MockPart.return_value
    mock_raw_data = {'pk': 7, 'name': 'Part Other API Error', 'purchaseable': True, 'assembly': False, 'total_in_stock': 3.0, 'consumable': False}
    mock_part_instance._data = mock_raw_data

    mock_response = MagicMock()
    mock_response.status_code = 500
    response_json_data = {"detail": "Internal server error"}
    mock_response.json.return_value = response_json_data # Though api_client might not get here if json() fails for text
    mock_response.text = '{"detail": "Internal server error"}' # More realistic text

    http_error = HTTPError(response=mock_response)
    # http_error.args = (f"500 Server Error: Internal Server Error for url",)
    MockSupplierPart.list.side_effect = http_error

    part_data, warnings = client.get_part_data(7)

    MockPart.assert_called_once_with(mock_api_instance, pk=7)
    MockSupplierPart.list.assert_called_once_with(mock_api_instance, part=7)
    MockCompany.assert_not_called()

    assert isinstance(part_data, PartData)
    assert part_data.pk == 7
    assert part_data.supplier_names == []
    assert not warnings, f"Expected no returned warnings, got: {warnings}" # Changed assertion

    assert len(caplog.records) == 1
    log_record = caplog.records[0]
    assert log_record.levelname == "WARNING"
    expected_log_message = f"Could not fetch supplier parts for part 7 due to an HTTP error: 500 - {mock_response.text}" # Message format is correct based on new api_client
    assert expected_log_message in log_record.message


@patch('inventree_order_calculator.api_client.Part')
def test_get_bom_data_success(MockPart, mock_api_client):
    """Test fetching BOM data successfully using fixture."""
    client, mock_api_instance, _ = mock_api_client
    mock_assembly_part = MockPart.return_value
    mock_bom_item1 = MagicMock()
    # Ensure quantity is float if needed by BomItemData
    mock_bom_item1._data = {'pk': 10, 'sub_part': 2, 'quantity': 5.0, 'consumable': True} # Added consumable
    mock_bom_item2 = MagicMock()
    mock_bom_item2._data = {'pk': 11, 'sub_part': 3, 'quantity': 2.0, 'consumable': False} # Added consumable
    mock_assembly_part.getBomItems.return_value = [mock_bom_item1, mock_bom_item2]
    # Simulate the assembly part having 'assembly': True in its data
    mock_assembly_part._data = {'pk': 1, 'name': 'Assembly Part', 'assembly': True}

    bom_data, warnings = client.get_bom_data(1) # Assuming part ID 1 is the assembly

    MockPart.assert_called_once_with(mock_api_instance, pk=1)
    mock_assembly_part.getBomItems.assert_called_once_with()

    # Assert the return type and structure
    assert isinstance(bom_data, list)
    assert len(bom_data) == 2
    assert all(isinstance(item, BomItemData) for item in bom_data)
    assert not warnings, f"Expected no warnings for successful BOM fetch, got: {warnings}"

    # Assert the content of the BomItemData objects
    assert bom_data[0].sub_part == 2
    assert bom_data[0].quantity == 5.0
    assert bom_data[0].is_consumable is True # Added assertion
    assert bom_data[1].sub_part == 3
    assert bom_data[1].quantity == 2.0
    assert bom_data[1].is_consumable is False # Added assertion

@patch('inventree_order_calculator.api_client.Part')
def test_get_bom_data_not_assembly(MockPart, mock_api_client):
    """Test fetching BOM data for a part that is not an assembly using fixture."""
    client, mock_api_instance, _ = mock_api_client
    mock_non_assembly_part = MockPart.return_value
    # Simulate the non-assembly part having 'assembly': False
    mock_non_assembly_part._data = {'pk': 5, 'name': 'Non-Assembly Part', 'assembly': False}

    bom_data, warnings = client.get_bom_data(5) # Assuming part ID 5 is not an assembly

    MockPart.assert_called_once_with(mock_api_instance, pk=5)
    # getBomItems should NOT be called if assembly is False
    mock_non_assembly_part.getBomItems.assert_not_called()
    assert bom_data == []
    assert len(warnings) == 1
    assert f"Part ID 5 ('Non-Assembly Part') is not an assembly. Cannot fetch BOM." in warnings[0]

@patch('inventree_order_calculator.api_client.Part')
def test_get_bom_data_part_not_found(MockPart, mock_api_client):
    """Test fetching BOM data when the part itself is not found using fixture."""
    client, mock_api_instance, _ = mock_api_client
    # Simulate Part instantiation failing
    MockPart.side_effect = Exception("Part not found")

    bom_data, warnings = client.get_bom_data(999)

    MockPart.assert_called_once_with(mock_api_instance, pk=999)
    assert bom_data is None
    assert len(warnings) >= 1 # Expect some warning/error message
    # Example: assert any("part not found" in w.lower() or "error fetching bom" in w.lower() for w in warnings)

@patch('inventree_order_calculator.api_client.Part')
def test_get_bom_data_extracts_optional_field_true(MockPart, mock_api_client):
    """Test that get_bom_data extracts optional=True field from BOM item responses."""
    client, mock_api_instance, _ = mock_api_client
    mock_assembly_part = MockPart.return_value
    mock_bom_item = MagicMock()
    # Mock BOM item with optional=True
    mock_bom_item._data = {
        'pk': 10,
        'sub_part': 123,
        'quantity': 2.0,
        'consumable': False,
        'optional': True  # This should be extracted
    }
    mock_assembly_part.getBomItems.return_value = [mock_bom_item]
    mock_assembly_part._data = {'pk': 1, 'name': 'Assembly Part', 'assembly': True}

    bom_data, warnings = client.get_bom_data(1)

    assert len(bom_data) == 1
    assert bom_data[0].sub_part == 123
    assert bom_data[0].quantity == 2.0
    assert bom_data[0].is_consumable is False
    assert bom_data[0].is_optional is True  # Should extract optional=True

@patch('inventree_order_calculator.api_client.Part')
def test_get_bom_data_extracts_optional_field_false(MockPart, mock_api_client):
    """Test that get_bom_data extracts optional=False field from BOM item responses."""
    client, mock_api_instance, _ = mock_api_client
    mock_assembly_part = MockPart.return_value
    mock_bom_item = MagicMock()
    # Mock BOM item with optional=False
    mock_bom_item._data = {
        'pk': 11,
        'sub_part': 456,
        'quantity': 1.5,
        'consumable': True,
        'optional': False  # This should be extracted
    }
    mock_assembly_part.getBomItems.return_value = [mock_bom_item]
    mock_assembly_part._data = {'pk': 2, 'name': 'Assembly Part', 'assembly': True}

    bom_data, warnings = client.get_bom_data(2)

    assert len(bom_data) == 1
    assert bom_data[0].sub_part == 456
    assert bom_data[0].quantity == 1.5
    assert bom_data[0].is_consumable is True
    assert bom_data[0].is_optional is False  # Should extract optional=False

@patch('inventree_order_calculator.api_client.Part')
def test_get_bom_data_handles_missing_optional_field(MockPart, mock_api_client):
    """Test that get_bom_data defaults to False when optional field is missing."""
    client, mock_api_instance, _ = mock_api_client
    mock_assembly_part = MockPart.return_value
    mock_bom_item = MagicMock()
    # Mock BOM item without optional field (older InvenTree version)
    mock_bom_item._data = {
        'pk': 12,
        'sub_part': 789,
        'quantity': 3.0,
        'consumable': False
        # No 'optional' field - should default to False
    }
    mock_assembly_part.getBomItems.return_value = [mock_bom_item]
    mock_assembly_part._data = {'pk': 3, 'name': 'Assembly Part', 'assembly': True}

    bom_data, warnings = client.get_bom_data(3)

    assert len(bom_data) == 1
    assert bom_data[0].sub_part == 789
    assert bom_data[0].quantity == 3.0
    assert bom_data[0].is_consumable is False
    assert bom_data[0].is_optional is False  # Should default to False when missing

@patch('inventree_order_calculator.api_client.Part')
def test_get_bom_data_handles_optional_field_none(MockPart, mock_api_client):
    """Test that get_bom_data defaults to False when optional field is None."""
    client, mock_api_instance, _ = mock_api_client
    mock_assembly_part = MockPart.return_value
    mock_bom_item = MagicMock()
    # Mock BOM item with optional=None
    mock_bom_item._data = {
        'pk': 13,
        'sub_part': 101,
        'quantity': 0.5,
        'consumable': True,
        'optional': None  # Should be treated as False
    }
    mock_assembly_part.getBomItems.return_value = [mock_bom_item]
    mock_assembly_part._data = {'pk': 4, 'name': 'Assembly Part', 'assembly': True}

    bom_data, warnings = client.get_bom_data(4)

    assert len(bom_data) == 1
    assert bom_data[0].sub_part == 101
    assert bom_data[0].quantity == 0.5
    assert bom_data[0].is_consumable is True
    assert bom_data[0].is_optional is False  # Should default to False when None

@patch('inventree_order_calculator.api_client.Part')
def test_get_bom_data_mixed_optional_required_items(MockPart, mock_api_client):
    """Test that get_bom_data correctly handles mixed optional and required BOM items."""
    client, mock_api_instance, _ = mock_api_client
    mock_assembly_part = MockPart.return_value

    # Create multiple BOM items with different optional values
    mock_bom_item1 = MagicMock()
    mock_bom_item1._data = {
        'pk': 14,
        'sub_part': 111,
        'quantity': 1.0,
        'consumable': False,
        'optional': False  # Required item
    }

    mock_bom_item2 = MagicMock()
    mock_bom_item2._data = {
        'pk': 15,
        'sub_part': 222,
        'quantity': 2.0,
        'consumable': True,
        'optional': True  # Optional item
    }

    mock_bom_item3 = MagicMock()
    mock_bom_item3._data = {
        'pk': 16,
        'sub_part': 333,
        'quantity': 1.5,
        'consumable': False
        # Missing optional field - should default to False
    }

    mock_assembly_part.getBomItems.return_value = [mock_bom_item1, mock_bom_item2, mock_bom_item3]
    mock_assembly_part._data = {'pk': 5, 'name': 'Mixed Assembly', 'assembly': True}

    bom_data, warnings = client.get_bom_data(5)

    assert len(bom_data) == 3

    # Check first item (required)
    assert bom_data[0].sub_part == 111
    assert bom_data[0].is_optional is False

    # Check second item (optional)
    assert bom_data[1].sub_part == 222
    assert bom_data[1].is_optional is True

    # Check third item (missing optional field)
    assert bom_data[2].sub_part == 333
    assert bom_data[2].is_optional is False

@patch('inventree_order_calculator.api_client.Part')
def test_get_parts_by_category_success(MockPart, mock_api_client):
    """Test fetching parts by category successfully."""
    client, mock_api_instance, _ = mock_api_client
    category_id = 191

    # Mock Part objects that Part.list would return
    mock_part_obj_A = MagicMock()
    mock_part_obj_A._data = {'pk': 1, 'name': 'Part A', 'category': category_id}
    mock_part_obj_B = MagicMock()
    mock_part_obj_B._data = {'pk': 2, 'name': 'Part B', 'category': category_id}
    
    mock_parts_list_sdk = [mock_part_obj_A, mock_part_obj_B]
    
    # Expected list of dictionaries
    expected_parts_data = [
        {'pk': 1, 'name': 'Part A', 'category': category_id},
        {'pk': 2, 'name': 'Part B', 'category': category_id},
    ]
    
    MockPart.list.return_value = mock_parts_list_sdk

    parts_data, warnings = client.get_parts_by_category(category_id)

    MockPart.list.assert_called_once_with(mock_api_instance, category=category_id)
    assert parts_data == expected_parts_data
    assert isinstance(parts_data, list)
    assert len(parts_data) == 2
    assert parts_data[0]['name'] == 'Part A'
    assert not warnings, f"Expected no warnings, got: {warnings}"

@patch('inventree_order_calculator.api_client.Part')
def test_get_parts_by_category_api_error(MockPart, mock_api_client):
    """Test fetching parts by category when the API call raises an exception."""
    client, mock_api_instance, _ = mock_api_client
    category_id = 191
    # Simulate an API error
    MockPart.list.side_effect = Exception("API connection failed")

    parts_data, warnings = client.get_parts_by_category(category_id)

    MockPart.list.assert_called_once_with(mock_api_instance, category=category_id)
    assert parts_data is None
    assert len(warnings) == 1
    assert "API connection failed" in warnings[0] # Or more specific error from ApiClient

@patch('inventree_order_calculator.api_client.Part')
def test_get_parts_by_category_no_parts_found(MockPart, mock_api_client):
    """Test fetching parts by category when no parts are found (API returns empty list)."""
    client, mock_api_instance, _ = mock_api_client
    category_id = 191
    # Simulate API returning an empty list of Part objects
    MockPart.list.return_value = [] # Part.list returns list of Part instances

    parts_data, warnings = client.get_parts_by_category(category_id)

    MockPart.list.assert_called_once_with(mock_api_instance, category=category_id)
    assert parts_data == [] # Expect empty list of dicts after processing
    # ApiClient currently logs "No parts found" as info, not a returned warning.
    assert not warnings, f"Expected no warnings for empty category, got: {warnings}"

@patch('inventree_order_calculator.api_client.Part')
def test_get_parts_by_category_api_returns_none(MockPart, mock_api_client):
    """Test fetching parts by category when the API unexpectedly returns None."""
    client, mock_api_instance, _ = mock_api_client
    category_id = 191
    # Simulate Part.list returning None
    MockPart.list.return_value = None

    parts_data, warnings = client.get_parts_by_category(category_id)

    MockPart.list.assert_called_once_with(mock_api_instance, category=category_id)
    assert parts_data is None # ApiClient returns None if Part.list returns None
    assert len(warnings) == 1
    assert "Part.list returned None for category 191" in warnings[0]
@patch('inventree_order_calculator.api_client.PartCategory')
def test_get_category_details_success(MockPartCategory, mock_api_client):
    """Test fetching category details successfully."""
    client, mock_api_instance, _ = mock_api_client
    category_id = 10
    expected_category_data = {'pk': category_id, 'name': 'Test Category', 'pathstring': 'Electronics/Capacitors'}
    mock_category_instance = MockPartCategory.return_value
    mock_category_instance._data = expected_category_data

    category_data, warnings = client.get_category_details(category_id)

    MockPartCategory.assert_called_once_with(mock_api_instance, pk=category_id)
    assert category_data == expected_category_data
    assert not warnings, f"Expected no warnings, got: {warnings}"

@patch('inventree_order_calculator.api_client.PartCategory')
def test_get_category_details_not_found(MockPartCategory, mock_api_client):
    """Test fetching category details when the category is not found."""
    client, mock_api_instance, _ = mock_api_client
    category_id = 99
    # Simulate PartCategory returning an object without _data or with empty _data
    mock_category_instance = MockPartCategory.return_value
    mock_category_instance._data = {} 

    category_data, warnings = client.get_category_details(category_id)

    MockPartCategory.assert_called_once_with(mock_api_instance, pk=category_id)
    assert category_data is None
    assert len(warnings) == 1
    assert f"Category data not found for ID: {category_id}" in warnings[0]

@patch('inventree_order_calculator.api_client.PartCategory')
def test_get_category_details_api_error(MockPartCategory, mock_api_client):
    """Test fetching category details when the API call raises an exception."""
    client, mock_api_instance, _ = mock_api_client
    category_id = 77
    MockPartCategory.side_effect = Exception("API Error for category")

    category_data, warnings = client.get_category_details(category_id)

    MockPartCategory.assert_called_once_with(mock_api_instance, pk=category_id)
    assert category_data is None
    assert len(warnings) == 1
    assert "API Error for category" in warnings[0]