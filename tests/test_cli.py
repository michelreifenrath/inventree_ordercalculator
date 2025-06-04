from typing import List
import pytest
from typer.testing import CliRunner
from unittest import mock
from decimal import Decimal
from rich.table import Table # Import Table for type checking
from rich.text import Text # Import Text for type checking

from inventree_order_calculator.models import InputPart # Import InputPart

# Mock objects needed for testing the CLI in isolation
# We assume these classes exist and work as expected based on other tests
# or will be implemented later.

# Mock for nested PartData within CalculatedPart
class MockPartData:
    def __init__(self, total_in_stock=0.0, ordering=0.0, building=0.0, required_for_build_orders=0.0, required_for_sales_orders=0.0):
        self.total_in_stock = float(total_in_stock)
        self.ordering = float(ordering)
        self.building = float(building)
        self.required_for_build_orders = float(required_for_build_orders)
        self.required_for_sales_orders = float(required_for_sales_orders)

# Mock for CalculatedPart structure including PartData
class MockCalculatedPart:
    def __init__(self, pk, name, available, total_required=0.0, to_order=0.0, to_build=0.0, part_data=None, is_purchaseable=True, is_assembly=False, belongs_to_top_parts=None, is_consumable=False, supplier_names=None): # Add supplier_names
        # Ensure part_data is an instance of MockPartData
        actual_part_data = part_data if part_data else MockPartData()

        # Copy attributes from PartData onto self to mimic inheritance
        self.pk = pk
        self.name = name
        self.is_purchaseable = is_purchaseable
        self.is_assembly = is_assembly
        self.total_in_stock = actual_part_data.total_in_stock
        self.required_for_build_orders = actual_part_data.required_for_build_orders
        self.required_for_sales_orders = actual_part_data.required_for_sales_orders
        self.ordering = actual_part_data.ordering
        self.building = actual_part_data.building

        # Add CalculatedPart specific fields
        self.available = float(available)
        self.total_required = float(total_required) # Added total_required
        self.to_order = float(to_order)
        self.to_build = float(to_build)
        # Add belongs_to_top_parts attribute
        self.belongs_to_top_parts = belongs_to_top_parts if belongs_to_top_parts is not None else set()
        self.is_consumable = is_consumable # Store is_consumable
        self.supplier_names = supplier_names if supplier_names is not None else [] # Store supplier_names

# Mock for OutputTables structure
class MockOutputTables:
    def __init__(self):
        self.parts_to_order: List[MockCalculatedPart] = []
        self.subassemblies_to_build: List[MockCalculatedPart] = []

class MockOrderCalculator:
    def __init__(self, api_client):
        self.api_client = api_client

    def calculate_orders(self, input_parts: List[InputPart]) -> MockOutputTables:
        parts_dict = {part.part_identifier: part.quantity_to_build for part in input_parts}
        output = MockOutputTables()

        # Simulate calculation result based on input for testing
        if parts_dict == {"100": 10.0, "200": 5.0, "300": 2.0}: # Input for test_cli_success
            # Parts to Order
            output.parts_to_order = [
                MockCalculatedPart(
                    pk=100, name="Resistor 1k", available=5.0, total_required=12.0, to_order=10.0,
                    part_data=MockPartData(total_in_stock=15.0, ordering=2.0, required_for_build_orders=10.0, required_for_sales_orders=2.0),
                    is_purchaseable=True, is_assembly=False, is_consumable=False, supplier_names=["Other Supplier"],
                    belongs_to_top_parts={"100"}
                ),
                MockCalculatedPart(
                    pk=200, name="Capacitor 10uF", available=3.0, total_required=6.0, to_order=5.0,
                    part_data=MockPartData(total_in_stock=8.0, ordering=1.0, required_for_build_orders=5.0, required_for_sales_orders=1.0),
                    is_purchaseable=True, is_assembly=False, is_consumable=False, supplier_names=["HAIP Solutions GmbH"], # Kept as non-consumable for this original test case
                    belongs_to_top_parts={"200"}
                ),
            ]
            # Subassemblies to Build
            output.subassemblies_to_build = [
                 MockCalculatedPart(
                    pk=300, name="Subassembly A", available=1.0, total_required=5.0, to_build=4.0,
                    part_data=MockPartData(total_in_stock=5.0, building=1.0, required_for_build_orders=4.0, required_for_sales_orders=1.0),
                    is_purchaseable=False, is_assembly=True, is_consumable=False, supplier_names=["Internal Build"],
                    belongs_to_top_parts={"300"}
                ),
                # Removed the consumable assembly PK 400 from this specific input case
            ]

        elif parts_dict == {"100": 10.0, "200": 5.0, "300": 2.0, "400": 1.0}: # Input for --hide-consumables and default show tests
            # This specific input will be used to test the --hide-consumables flag
            output.parts_to_order = [
                MockCalculatedPart(pk=100, name="Resistor 1k", available=5.0, total_required=12.0, to_order=10.0, is_consumable=False, belongs_to_top_parts={"100"}, supplier_names=["Other Supplier"]),
                MockCalculatedPart(pk=200, name="Capacitor 10uF", available=3.0, total_required=6.0, to_order=5.0, is_consumable=True, belongs_to_top_parts={"200"}, supplier_names=["HAIP Solutions GmbH"]),
            ]
            output.subassemblies_to_build = [
                MockCalculatedPart(pk=300, name="Subassembly A", available=1.0, total_required=5.0, to_build=4.0, is_consumable=False, belongs_to_top_parts={"300"}, supplier_names=["Internal Build"]),
                MockCalculatedPart(pk=400, name="Consumable Assembly B", available=0.0, total_required=2.0, to_build=2.0, is_consumable=True, belongs_to_top_parts={"400"}, supplier_names=["HAIP Solutions GmbH"]),
            ]
        
        elif parts_dict == {"500": 1.0, "501": 1.0, "502": 1.0, "503": 1.0}: # Input for --hide-haip-parts test
            output.parts_to_order = [
                MockCalculatedPart(pk=500, name="HAIP Part Alpha", available=0, total_required=1, to_order=1, is_consumable=False, belongs_to_top_parts={"500"}, supplier_names=["HAIP Solutions GmbH"]),
                MockCalculatedPart(pk=501, name="Non-HAIP Part Beta", available=0, total_required=1, to_order=1, is_consumable=False, belongs_to_top_parts={"501"}, supplier_names=["Another Corp"]),
            ]
            output.subassemblies_to_build = [
                MockCalculatedPart(pk=502, name="HAIP Assembly Gamma", available=0, total_required=1, to_build=1, is_consumable=False, is_assembly=True, belongs_to_top_parts={"502"}, supplier_names=["HAIP Solutions GmbH"]),
                MockCalculatedPart(pk=503, name="Non-HAIP Assembly Delta", available=0, total_required=1, to_build=1, is_consumable=False, is_assembly=True, belongs_to_top_parts={"503"}, supplier_names=["Internal Assembly Line"]),
            ]

        elif parts_dict == {"999": 1.0}: # Input designed to result in no orders/builds
             output.parts_to_order = []
             output.subassemblies_to_build = []
        elif parts_dict == {"PN_ERROR": 1.0}: # Input designed to trigger error
             raise ValueError("Simulated calculation error")
        else:
             output.parts_to_order = []
             output.subassemblies_to_build = []

        return output

captured_tables_for_test_cli_success = []

def mock_console_print_side_effect(item):
    """Captures rich.Table objects passed to console.print."""
    if isinstance(item, Table):
        captured_tables_for_test_cli_success.append(item)
    # To still see output during test, could use a real console print here too
    # print(item) # Or use original console.print if that's easy to get

# Patch the actual dependencies of the cli module
@mock.patch('inventree_order_calculator.cli.AppConfig')
@mock.patch('inventree_order_calculator.cli.ApiClient')
@mock.patch('inventree_order_calculator.cli.OrderCalculator', new=MockOrderCalculator)
@mock.patch('inventree_order_calculator.cli.Console.print', side_effect=mock_console_print_side_effect)
def test_cli_success(MockConsolePrint, MockApiClient, MockAppConfig): # Added MockConsolePrint
    """Test successful CLI execution with valid arguments."""
    from inventree_order_calculator.cli import app # cli.Console is now patched
    runner = CliRunner()
    captured_tables_for_test_cli_success.clear() # Clear for each test run

    # Mock config loading
    mock_config_instance = mock.Mock()
    mock_config_instance.inventree_url = "mock_url"
    mock_config_instance.inventree_api_token = "mock_token"
    mock_config_instance.inventree_instance_url = "http://test.inventree.local" # Mock instance URL
    MockAppConfig.load.return_value = mock_config_instance

    # Mock ApiClient instantiation
    mock_api_client_instance = mock.Mock()
    MockApiClient.return_value = mock_api_client_instance

    # Use PKs as identifiers matching the mock logic, including assembly
    result = runner.invoke(app, ["100:10", "200:5", "300:2"])

    assert result.exit_code == 0
    assert MockConsolePrint.call_count >= 2

    assert len(captured_tables_for_test_cli_success) == 2
    
    parts_order_table = None
    subassemblies_build_table = None

    for tbl in captured_tables_for_test_cli_success:
        current_table_title_plain = None
        if tbl.title:
            if isinstance(tbl.title, Text):
                current_table_title_plain = tbl.title.plain
            elif isinstance(tbl.title, str):
                current_table_title_plain = tbl.title
        
        if current_table_title_plain == "Parts to Order":
            parts_order_table = tbl
        elif current_table_title_plain == "Subassemblies to Build":
            subassemblies_build_table = tbl
            
    assert parts_order_table is not None, "Parts to Order table not captured"
    assert subassemblies_build_table is not None, "Subassemblies to Build table not captured"

    # --- Check Parts to Order Table ---
    expected_parts_headers = ["Part ID", "Optional", "Part Name", "Needed", "Total In Stock", "Required for Build Orders", "Required for Sales Orders", "Available", "To Order", "On Order", "Gehört zu"]
    assert [col.header for col in parts_order_table.columns] == expected_parts_headers
    assert len(parts_order_table.rows) == 2

    # Expected link format
    link_base = mock_config_instance.inventree_instance_url
    expected_part_100_name_cell = f"[link={link_base}/part/100/]Resistor 1k[/link]"
    expected_part_200_name_cell = f"[link={link_base}/part/200/]Capacitor 10uF[/link]"

    # Row 0 (Part 100) - Added Optional column with ✗ (default False)
    assert [list(col.cells)[0] for col in parts_order_table.columns] == ['100', '✗', expected_part_100_name_cell, '12.00', '15.00', '10.00', '2.00', '5.00', '10.00', '2.00', '100']
    # Row 1 (Part 200) - Added Optional column with ✗ (default False)
    assert [list(col.cells)[1] for col in parts_order_table.columns] == ['200', '✗', expected_part_200_name_cell, '6.00', '8.00', '5.00', '1.00', '3.00', '5.00', '1.00', '200']

    # --- Check Subassemblies to Build Table ---
    expected_build_headers = ["Part ID", "Optional", "Part Name", "Needed", "Total In Stock", "Required for Build Orders", "Required for Sales Orders", "Available", "In Production", "To Build", "Gehört zu"]
    assert [col.header for col in subassemblies_build_table.columns] == expected_build_headers
    assert len(subassemblies_build_table.rows) == 1
    
    expected_subassembly_300_name_cell = f"[link={link_base}/part/300/]Subassembly A[/link]"
    # Row 0 (Part 300) - Added Optional column with ✗ (default False)
    assert [list(col.cells)[0] for col in subassemblies_build_table.columns] == ['300', '✗', expected_subassembly_300_name_cell, '5.00', '5.00', '4.00', '1.00', '1.00', '1.00', '4.00', '300']
    
    assert "Total Estimated Cost:" not in result.stdout
    # Check that titles are still in stdout
    # stdout checks are removed as the mock now captures Table objects directly
    # and doesn't pass through prints to the runner's captured stdout.
    # The core logic is tested by inspecting the captured Table objects.


@mock.patch('inventree_order_calculator.cli.AppConfig')
@mock.patch('inventree_order_calculator.cli.ApiClient')
@mock.patch('inventree_order_calculator.cli.OrderCalculator', new=MockOrderCalculator)
def test_cli_invalid_part_format(MockApiClient, MockAppConfig):
    """Test CLI with invalid part:quantity format."""
    from inventree_order_calculator.cli import app
    runner = CliRunner()
    result = runner.invoke(app, ["PN100:10", "PN200INVALID"]) # Invalid format

    assert result.exit_code != 0 # Expecting an error exit code
    # Check relevant parts of the output string directly for robustness
    assert "Error: Invalid format for part" in result.stdout
    assert "PN200INVALID" in result.stdout
    # Check that both key parts of the format message exist somewhere in the output
    assert "Expected format:" in result.stdout
    assert "PART_IDENTIFIER:QUANTITY" in result.stdout # Updated expected format string

@mock.patch('inventree_order_calculator.cli.AppConfig')
@mock.patch('inventree_order_calculator.cli.ApiClient')
@mock.patch('inventree_order_calculator.cli.OrderCalculator', new=MockOrderCalculator)
def test_cli_invalid_quantity(MockApiClient, MockAppConfig):
    """Test CLI with non-integer quantity."""
    from inventree_order_calculator.cli import app
    runner = CliRunner()
    result = runner.invoke(app, ["PN100:TEN"]) # Invalid quantity

    assert result.exit_code != 0
    assert "Error: Invalid quantity for part" in result.stdout
    assert "PN100" in result.stdout
    assert "'TEN' is not a valid number" in result.stdout # Updated error message check


@mock.patch('inventree_order_calculator.cli.AppConfig')
@mock.patch('inventree_order_calculator.cli.ApiClient')
@mock.patch('inventree_order_calculator.cli.OrderCalculator', new=MockOrderCalculator)
def test_cli_calculation_error(MockApiClient, MockAppConfig):
    """Test CLI when OrderCalculator raises an error."""
    from inventree_order_calculator.cli import app
    runner = CliRunner()
    result = runner.invoke(app, ["PN_ERROR:1"]) # Input designed to trigger error in mock

    assert result.exit_code != 0
    # Check for the specific error message raised by the calculator
    assert "Simulated calculation error" in result.stdout
    # Optionally check that the generic "Error during calculation:" prefix is also present
    assert "Error during calculation:" in result.stdout


@mock.patch('inventree_order_calculator.cli.AppConfig')
@mock.patch('inventree_order_calculator.cli.ApiClient')
@mock.patch('inventree_order_calculator.cli.OrderCalculator', new=MockOrderCalculator)
def test_cli_no_parts_to_order(MockApiClient, MockAppConfig):
    """Test CLI when calculation results in no parts needing to be ordered."""
    from inventree_order_calculator.cli import app
    runner = CliRunner()

    # Mock config loading
    mock_config_instance = mock.Mock()
    mock_config_instance.inventree_url = "mock_url"
    mock_config_instance.inventree_api_token = "mock_token"
    MockAppConfig.load.return_value = mock_config_instance

    # Mock ApiClient instantiation
    mock_api_client_instance = mock.Mock()
    MockApiClient.return_value = mock_api_client_instance

    # Use input designed to return empty list in mock
    result = runner.invoke(app, ["999:1"])

    print(f"CLI Output (No Parts):\n{result.stdout}") # Debug output

    assert result.exit_code == 0
    assert "No parts need to be ordered based on calculation." in result.stdout
    assert "No subassemblies need to be built based on calculation." in result.stdout
    assert "Parts to Order" not in result.stdout # Ensure table title is not printed
    assert "Subassemblies to Build" not in result.stdout # Ensure table title is not printed


def test_cli_missing_arguments():
    """Test CLI when required arguments are missing."""
    # Need to import here as mocks aren't needed for typer's built-in handling
    # However, the module itself might fail to import if dependencies aren't met
    # We'll create a dummy app object just for this test if direct import fails
    try:
        from inventree_order_calculator.cli import app
        runner = CliRunner()
        result = runner.invoke(app, []) # No arguments
        assert result.exit_code != 0
        assert "Missing argument 'PARTS...'" in result.stdout # Typer's default error
    except ImportError:
         pytest.skip("Skipping missing arguments test as CLI module has unmet dependencies")
    except Exception as e:
         pytest.fail(f"CLI import failed unexpectedly: {e}")

# Test case for when instance URL is not provided
@mock.patch('inventree_order_calculator.cli.AppConfig')
@mock.patch('inventree_order_calculator.cli.ApiClient')
@mock.patch('inventree_order_calculator.cli.OrderCalculator', new=MockOrderCalculator)
@mock.patch('inventree_order_calculator.cli.Console.print', side_effect=mock_console_print_side_effect)
def test_cli_success_no_instance_url(MockConsolePrint, MockApiClient, MockAppConfig):
    """Test successful CLI execution when INVENTREE_INSTANCE_URL is not set."""
    from inventree_order_calculator.cli import app
    runner = CliRunner()
    captured_tables_for_test_cli_success.clear()

    # Mock config loading without instance_url
    mock_config_instance_no_url = mock.Mock()
    mock_config_instance_no_url.inventree_url = "mock_url"
    mock_config_instance_no_url.inventree_api_token = "mock_token"
    mock_config_instance_no_url.inventree_instance_url = None # Explicitly None
    MockAppConfig.load.return_value = mock_config_instance_no_url

    mock_api_client_instance = mock.Mock()
    MockApiClient.return_value = mock_api_client_instance

    result = runner.invoke(app, ["100:10", "200:5", "300:2"])

    assert result.exit_code == 0
    assert len(captured_tables_for_test_cli_success) == 2
    
    parts_order_table = None
    subassemblies_build_table = None

    for tbl in captured_tables_for_test_cli_success:
        current_table_title_plain = None
        if tbl.title: # Check if title exists
            if isinstance(tbl.title, Text): # Check if title is Text
                current_table_title_plain = tbl.title.plain
            elif isinstance(tbl.title, str): # Fallback for string title
                current_table_title_plain = tbl.title
        
        if current_table_title_plain == "Parts to Order":
            parts_order_table = tbl
        elif current_table_title_plain == "Subassemblies to Build":
            subassemblies_build_table = tbl
            
    assert parts_order_table is not None, "Parts to Order table not captured (no instance URL)"
    assert subassemblies_build_table is not None, "Subassemblies to Build table not captured (no instance URL)"

    # Check Part Name column for plain text (now at index 2 due to Optional column)
    # Row 0 (Part 100) - Name should be plain
    assert list(list(parts_order_table.columns)[2].cells)[0] == 'Resistor 1k'
    # Row 1 (Part 200) - Name should be plain
    assert list(list(parts_order_table.columns)[2].cells)[1] == 'Capacitor 10uF'
    # Subassembly Row 0 (Part 300) - Name should be plain
    assert list(list(subassemblies_build_table.columns)[2].cells)[0] == 'Subassembly A'
@mock.patch('inventree_order_calculator.cli.AppConfig')
@mock.patch('inventree_order_calculator.cli.ApiClient')
@mock.patch('inventree_order_calculator.cli.OrderCalculator', new=MockOrderCalculator)
@mock.patch('inventree_order_calculator.cli.Console.print', side_effect=mock_console_print_side_effect)
def test_cli_hide_consumables_flag(MockConsolePrint, MockApiClient, MockAppConfig):
    """Test CLI with --hide-consumables flag."""
    from inventree_order_calculator.cli import app
    runner = CliRunner()
    captured_tables_for_test_cli_success.clear()

    mock_config_instance = mock.Mock()
    mock_config_instance.inventree_url = "mock_url"
    mock_config_instance.inventree_api_token = "mock_token"
    mock_config_instance.inventree_instance_url = "http://test.inventree.local"
    MockAppConfig.load.return_value = mock_config_instance

    mock_api_client_instance = mock.Mock()
    MockApiClient.return_value = mock_api_client_instance

    # This input corresponds to the specific case in MockOrderCalculator
    # where parts 200 (order) and 400 (build) are consumable.
    result = runner.invoke(app, ["100:10", "200:5", "300:2", "400:1", "--hide-consumables"])

    assert result.exit_code == 0
    assert len(captured_tables_for_test_cli_success) == 2

    parts_order_table = None
    subassemblies_build_table = None
    for tbl in captured_tables_for_test_cli_success:
        headers = [col.header for col in tbl.columns]
        if "To Order" in headers and "On Order" in headers:
            parts_order_table = tbl
        elif "In Production" in headers and "To Build" in headers:
            subassemblies_build_table = tbl

    assert parts_order_table is not None, "Parts to Order table not captured with --hide-consumables"
    assert subassemblies_build_table is not None, "Subassemblies to Build table not captured with --hide-consumables"

    # Check Parts to Order Table (should only have non-consumable PK 100)
    assert len(parts_order_table.rows) == 1
    assert list(list(parts_order_table.columns)[0].cells)[0] == '100' # Check PK of the first row

    # Check Subassemblies to Build Table (should only have non-consumable PK 300)
    assert len(subassemblies_build_table.rows) == 1
    assert list(list(subassemblies_build_table.columns)[0].cells)[0] == '300' # Check PK of the first row

@mock.patch('inventree_order_calculator.cli.AppConfig')
@mock.patch('inventree_order_calculator.cli.ApiClient')
@mock.patch('inventree_order_calculator.cli.OrderCalculator', new=MockOrderCalculator)
@mock.patch('inventree_order_calculator.cli.Console.print', side_effect=mock_console_print_side_effect)
def test_cli_show_consumables_default(MockConsolePrint, MockApiClient, MockAppConfig):
    """Test CLI shows consumables by default (no flag)."""
    from inventree_order_calculator.cli import app
    runner = CliRunner()
    captured_tables_for_test_cli_success.clear()

    mock_config_instance = mock.Mock()
    mock_config_instance.inventree_url = "mock_url"
    mock_config_instance.inventree_api_token = "mock_token"
    mock_config_instance.inventree_instance_url = "http://test.inventree.local"
    MockAppConfig.load.return_value = mock_config_instance

    mock_api_client_instance = mock.Mock()
    MockApiClient.return_value = mock_api_client_instance

    # This input corresponds to the specific case in MockOrderCalculator
    result = runner.invoke(app, ["100:10", "200:5", "300:2", "400:1"])

    assert result.exit_code == 0
    assert len(captured_tables_for_test_cli_success) == 2

    parts_order_table = None
    subassemblies_build_table = None
    for tbl in captured_tables_for_test_cli_success:
        headers = [col.header for col in tbl.columns]
        if "To Order" in headers and "On Order" in headers:
            parts_order_table = tbl
        elif "In Production" in headers and "To Build" in headers:
            subassemblies_build_table = tbl

    assert parts_order_table is not None, "Parts to Order table not captured (default)"
    assert subassemblies_build_table is not None, "Subassemblies to Build table not captured (default)"

    # Check Parts to Order Table (should have PK 100 and 200)
    assert len(parts_order_table.rows) == 2
    part_ids_in_order_table = {list(col.cells)[idx] for idx in range(len(parts_order_table.rows)) for col_idx, col in enumerate(parts_order_table.columns) if col_idx == 0}
    assert "100" in part_ids_in_order_table
    assert "200" in part_ids_in_order_table


    # Check Subassemblies to Build Table (should have PK 300 and 400)
    assert len(subassemblies_build_table.rows) == 2
    assembly_ids_in_build_table = {list(col.cells)[idx] for idx in range(len(subassemblies_build_table.rows)) for col_idx, col in enumerate(subassemblies_build_table.columns) if col_idx == 0}
    assert "300" in assembly_ids_in_build_table
    assert "400" in assembly_ids_in_build_table


def test_cli_optional_column_display():
    """Test that CLI displays Optional column with correct ✓/✗ symbols."""
    from inventree_order_calculator.cli import app
    from inventree_order_calculator.models import CalculatedPart, OutputTables

    # Create test data with mixed optional/required parts
    required_part = CalculatedPart(
        pk=100, name="Required Part", is_purchaseable=True, is_assembly=False,
        total_required=10.0, to_order=5.0, is_optional=False
    )

    optional_part = CalculatedPart(
        pk=200, name="Optional Part", is_purchaseable=True, is_assembly=False,
        total_required=5.0, to_order=3.0, is_optional=True
    )

    required_assembly = CalculatedPart(
        pk=300, name="Required Assembly", is_purchaseable=False, is_assembly=True,
        total_required=2.0, to_build=1.0, is_optional=False
    )

    optional_assembly = CalculatedPart(
        pk=400, name="Optional Assembly", is_purchaseable=False, is_assembly=True,
        total_required=1.0, to_build=1.0, is_optional=True
    )

    # Create mock result
    mock_result = OutputTables(
        parts_to_order=[required_part, optional_part],
        subassemblies_to_build=[required_assembly, optional_assembly]
    )

    # Mock the OrderCalculator to return our test data
    class MockOrderCalculatorOptional:
        def __init__(self, api_client):
            pass

        def calculate_orders(self, input_parts):
            return mock_result

    runner = CliRunner()

    with mock.patch('inventree_order_calculator.cli.AppConfig') as MockAppConfig, \
         mock.patch('inventree_order_calculator.cli.ApiClient') as MockApiClient, \
         mock.patch('inventree_order_calculator.cli.OrderCalculator', new=MockOrderCalculatorOptional), \
         mock.patch('inventree_order_calculator.cli.Console.print', side_effect=mock_console_print_side_effect):

        # Clear captured tables for this test
        captured_tables_for_test_cli_success.clear()

        # Configure mocks
        mock_config_instance = MockAppConfig.return_value
        mock_config_instance.inventree_instance_url = "https://test.inventree.com"

        # Run CLI
        result = runner.invoke(app, ["100:1"])

        # Verify command succeeded
        assert result.exit_code == 0

        # Get captured tables
        parts_order_table = None
        subassemblies_build_table = None

        for tbl in captured_tables_for_test_cli_success:
            current_table_title_plain = None
            if tbl.title:
                if isinstance(tbl.title, Text):
                    current_table_title_plain = tbl.title.plain
                elif isinstance(tbl.title, str):
                    current_table_title_plain = tbl.title

            if current_table_title_plain == "Parts to Order":
                parts_order_table = tbl
            elif current_table_title_plain == "Subassemblies to Build":
                subassemblies_build_table = tbl

        assert parts_order_table is not None, "Parts to Order table not captured"
        assert subassemblies_build_table is not None, "Subassemblies to Build table not captured"

        # Check Parts to Order table has Optional column
        assert "Optional" in [col.header for col in parts_order_table.columns]

        # Check Optional column values for parts
        optional_col_index = [col.header for col in parts_order_table.columns].index("Optional")
        part_100_optional = list(parts_order_table.columns[optional_col_index].cells)[0]
        part_200_optional = list(parts_order_table.columns[optional_col_index].cells)[1]

        assert part_100_optional == "✗"  # Required part should show ✗
        assert part_200_optional == "✓"  # Optional part should show ✓

        # Check Subassemblies to Build table has Optional column
        assert "Optional" in [col.header for col in subassemblies_build_table.columns]

        # Check Optional column values for assemblies
        optional_col_index = [col.header for col in subassemblies_build_table.columns].index("Optional")
        assembly_300_optional = list(subassemblies_build_table.columns[optional_col_index].cells)[0]
        assembly_400_optional = list(subassemblies_build_table.columns[optional_col_index].cells)[1]

        assert assembly_300_optional == "✗"  # Required assembly should show ✗
        assert assembly_400_optional == "✓"  # Optional assembly should show ✓