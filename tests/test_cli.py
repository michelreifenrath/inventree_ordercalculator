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
    expected_parts_headers = ["Part ID", "Part Name", "Needed", "Total In Stock", "Required for Build Orders", "Required for Sales Orders", "Available", "To Order", "On Order", "Gehört zu"]
    assert [col.header for col in parts_order_table.columns] == expected_parts_headers
    assert len(parts_order_table.rows) == 2

    # Expected link format
    link_base = mock_config_instance.inventree_instance_url
    expected_part_100_name_cell = f"[link={link_base}/part/100/]Resistor 1k[/link]"
    expected_part_200_name_cell = f"[link={link_base}/part/200/]Capacitor 10uF[/link]"

    # Row 0 (Part 100)
    assert [list(col.cells)[0] for col in parts_order_table.columns] == ['100', expected_part_100_name_cell, '12.00', '15.00', '10.00', '2.00', '5.00', '10.00', '2.00', '100']
    # Row 1 (Part 200)
    assert [list(col.cells)[1] for col in parts_order_table.columns] == ['200', expected_part_200_name_cell, '6.00', '8.00', '5.00', '1.00', '3.00', '5.00', '1.00', '200']

    # --- Check Subassemblies to Build Table ---
    expected_build_headers = ["Part ID", "Part Name", "Needed", "Total In Stock", "Required for Build Orders", "Required for Sales Orders", "Available", "In Production", "To Build", "Gehört zu"]
    assert [col.header for col in subassemblies_build_table.columns] == expected_build_headers
    assert len(subassemblies_build_table.rows) == 1
    
    expected_subassembly_300_name_cell = f"[link={link_base}/part/300/]Subassembly A[/link]"
    # Row 0 (Part 300)
    assert [list(col.cells)[0] for col in subassemblies_build_table.columns] == ['300', expected_subassembly_300_name_cell, '5.00', '5.00', '4.00', '1.00', '1.00', '1.00', '4.00', '300']
    
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

    # Check Part Name column for plain text
    # Row 0 (Part 100) - Name should be plain
    assert list(list(parts_order_table.columns)[1].cells)[0] == 'Resistor 1k'
    # Row 1 (Part 200) - Name should be plain
    assert list(list(parts_order_table.columns)[1].cells)[1] == 'Capacitor 10uF'
    # Subassembly Row 0 (Part 300) - Name should be plain
    assert list(list(subassemblies_build_table.columns)[1].cells)[0] == 'Subassembly A'
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
# --- Tests for CLI 'monitor' subcommands ---

# Mock MonitoringList for CLI tests to avoid direct dependency on presets_manager.MonitoringList structure in tests
class MockCliMonitoringList:
    def __init__(self, id, name, active, cron_schedule, recipients, notify_condition, last_hash, parts_count):
        self.id = id
        self.name = name
        self.active = active
        self.cron_schedule = cron_schedule
        self.recipients = recipients
        self.notify_condition = notify_condition
        self.last_hash = last_hash
        self.parts = [None] * parts_count # Just to have a .parts attribute with a length

    def model_dump(self): # For compatibility if any part of CLI tries to dump it
        return self.__dict__

@pytest.fixture
def mock_cli_presets_manager():
    """Mocks the PresetsManager instance used by CLI monitor commands."""
    with patch('inventree_order_calculator.cli._presets_manager', autospec=True) as mock_pm:
        # Setup common methods used by monitor CLI commands
        mock_pm.get_monitoring_lists = mock.MagicMock(return_value=[])
        mock_pm.add_monitoring_list = mock.MagicMock(return_value=True)
        mock_pm.update_monitoring_list = mock.MagicMock(return_value=True)
        mock_pm.delete_monitoring_list = mock.MagicMock(return_value=True)
        mock_pm.get_monitoring_list_by_id = mock.MagicMock(return_value=None)
        yield mock_pm

@pytest.fixture
def mock_cli_monitoring_task_manager():
    """Mocks MonitoringTaskManager static methods used by CLI."""
    with patch('inventree_order_calculator.cli.MonitoringTaskManager', autospec=True) as mock_mtm:
        mock_mtm.add_task = mock.MagicMock(return_value=None) # Will be set by tests
        mock_mtm.update_task = mock.MagicMock(return_value=None)
        mock_mtm.delete_task = mock.MagicMock(return_value=True)
        mock_mtm.activate_task = mock.MagicMock(return_value=True)
        mock_mtm.deactivate_task = mock.MagicMock(return_value=True)
        mock_mtm.run_task_manually = mock.MagicMock()
        mock_mtm.get_task_by_id = mock.MagicMock(return_value=None)
        yield mock_mtm

@pytest.fixture(autouse=True)
def ensure_cli_services_mocked(mock_cli_presets_manager):
    """Ensure _ensure_services_initialized uses the mocked presets_manager for monitor commands."""
    # This helps simplify individual test setups by ensuring _presets_manager is always mocked
    # when _ensure_services_initialized is called by the CLI commands.
    # We also need to mock Config loading for these specific CLI tests if not done globally.
    with patch('inventree_order_calculator.cli.get_config') as mock_get_cfg:
        mock_cfg_instance = mock.Mock(spec=Config)
        mock_cfg_instance.LOG_LEVEL = "INFO"
        mock_cfg_instance.PRESETS_FILE_PATH = "dummy_presets.json"
        # Add other fields if _ensure_services_initialized or commands need them
        mock_get_cfg.return_value = mock_cfg_instance
        yield mock_get_cfg


def test_monitor_list_no_tasks(mock_cli_presets_manager):
    """Test 'monitor list' when no tasks are configured."""
    from inventree_order_calculator.cli import app
    runner = CliRunner()
    mock_cli_presets_manager.get_monitoring_lists.return_value = []
    
    result = runner.invoke(app, ["monitor", "list"])
    
    assert result.exit_code == 0
    assert "No monitoring tasks configured." in result.stdout
    mock_cli_presets_manager.get_monitoring_lists.assert_called_once()

def test_monitor_list_with_tasks(mock_cli_presets_manager):
    """Test 'monitor list' displays tasks in a table."""
    from inventree_order_calculator.cli import app
    runner = CliRunner()
    
    # Use the MockCliMonitoringList for data consistency with table rendering
    mock_tasks_data = [
        MockCliMonitoringList(id="id1", name="Task Alpha", active=True, cron_schedule="0 0 * * *", recipients=["a@example.com"], notify_condition="on_change", last_hash="hash1", parts_count=3),
        MockCliMonitoringList(id="id2-very-long-id-for-testing-fold", name="Task Beta", active=False, cron_schedule="0 12 * * *", recipients=["b@example.com", "c@example.com"], notify_condition="always", last_hash="-", parts_count=5),
    ]
    mock_cli_presets_manager.get_monitoring_lists.return_value = mock_tasks_data
    
    result = runner.invoke(app, ["monitor", "list"])
    
    assert result.exit_code == 0
    assert "Monitoring Tasks" in result.stdout
    assert "Task Alpha" in result.stdout
    assert "id1" in result.stdout
    assert "[green]Yes[/green]" in result.stdout # For active task
    assert "Task Beta" in result.stdout
    assert "id2-very-long-id-for-testing-fold" in result.stdout
    assert "[red]No[/red]" in result.stdout # For inactive task
    assert "b@example.com, c@example.com" in result.stdout
    assert "always" in result.stdout
    assert "3" in result.stdout # Parts count for Task Alpha
    assert "5" in result.stdout # Parts count for Task Beta
    mock_cli_presets_manager.get_monitoring_lists.assert_called_once()

def test_monitor_add_task_success(mock_cli_presets_manager):
    """Test 'monitor add' successfully adds a task."""
    from inventree_order_calculator.cli import app
    from inventree_order_calculator.presets_manager import MonitoringList as RealMonitoringList # For type check
    runner = CliRunner()

    # Mock PresetsManager's add_monitoring_list to return True
    mock_cli_presets_manager.add_monitoring_list.return_value = True
    
    # Capture the object passed to add_monitoring_list
    added_task_capture = mock.MagicMock()
    def capture_add(task_obj):
        added_task_capture(task_obj)
        return True # Simulate success from presets_manager
    mock_cli_presets_manager.add_monitoring_list.side_effect = capture_add

    result = runner.invoke(app, [
        "monitor", "add",
        "--name", "My New CLI Task",
        "--parts", "PART100:10:V1,PART200:5",
        "--schedule", "0 10 * * *",
        "--recipients", "cli@example.com,another@example.org",
        "--notify-condition", "always",
        "--misfire-grace-time", "600",
        "--active" # Default is True, explicitly setting it
    ])

    print(f"CLI Add Output: {result.stdout}")
    assert result.exit_code == 0
    assert "Monitoring task 'My New CLI Task' added successfully." in result.stdout
    
    mock_cli_presets_manager.add_monitoring_list.assert_called_once()
    
    # Check the MonitoringList object that was passed to presets_manager
    assert added_task_capture.call_count == 1
    passed_task_obj = added_task_capture.call_args[0][0]
    assert isinstance(passed_task_obj, RealMonitoringList)
    assert passed_task_obj.name == "My New CLI Task"
    assert len(passed_task_obj.parts) == 2
    assert passed_task_obj.parts[0].name_or_ipn == "PART100"
    assert passed_task_obj.parts[0].quantity == 10
    assert passed_task_obj.parts[0].version == "V1"
    assert passed_task_obj.parts[1].name_or_ipn == "PART200"
    assert passed_task_obj.parts[1].quantity == 5
    assert passed_task_obj.parts[1].version is None
    assert passed_task_obj.cron_schedule == "0 10 * * *"
    assert passed_task_obj.recipients == ["cli@example.com", "another@example.org"]
    assert passed_task_obj.notify_condition == "always"
    assert passed_task_obj.misfire_grace_time == 600
    assert passed_task_obj.active is True

def test_monitor_add_task_invalid_parts_string(mock_cli_presets_manager):
    """Test 'monitor add' with an invalid parts string."""
    from inventree_order_calculator.cli import app
    runner = CliRunner()
    result = runner.invoke(app, [
        "monitor", "add",
        "--name", "Invalid Parts Task",
        "--parts", "PART100:WRONG,PART200:5", # Invalid quantity
        "--schedule", "0 0 * * *",
        "--recipients", "test@example.com"
    ])
    assert result.exit_code != 0
    assert "Error parsing parts string" in result.stdout
    assert "Invalid quantity for part 'PART100'" not in result.stdout # _parse_monitoring_parts has its own error msg
    mock_cli_presets_manager.add_monitoring_list.assert_not_called()

def test_monitor_add_task_no_recipients(mock_cli_presets_manager):
    """Test 'monitor add' fails if no recipients are provided."""
    from inventree_order_calculator.cli import app
    runner = CliRunner()
    result = runner.invoke(app, [
        "monitor", "add",
        "--name", "No Recipient Task",
        "--parts", "PART1:1",
        "--schedule", "0 0 * * *",
        "--recipients", " " # Empty or whitespace only
    ])
    assert result.exit_code != 0
    assert "No recipients provided" in result.stdout
    mock_cli_presets_manager.add_monitoring_list.assert_not_called()

def test_monitor_add_task_presets_manager_fails(mock_cli_presets_manager):
    """Test 'monitor add' when PresetsManager fails to save."""
    from inventree_order_calculator.cli import app
    runner = CliRunner()
    mock_cli_presets_manager.add_monitoring_list.return_value = False # Simulate failure

    result = runner.invoke(app, [
        "monitor", "add",
        "--name", "Save Fail Task",
        "--parts", "P1:1",
        "--schedule", "0 0 * * *",
        "--recipients", "fail@example.com"
    ])
    assert result.exit_code != 0
    assert "Failed to add monitoring task 'Save Fail Task'" in result.stdout
    mock_cli_presets_manager.add_monitoring_list.assert_called_once()

# Further tests for update, delete, run, activate, deactivate will follow.
# Tests for monitor update
@patch('inventree_order_calculator.cli._presets_manager', autospec=True)
def test_monitor_update_task_success(mock_pm):
    """Test 'monitor update' successfully updates specified fields of a task."""
    from inventree_order_calculator.cli import app, MonitoringList as RealMonitoringList
    runner = CliRunner()

    existing_task_id = "task_to_update_123"
    # Mock the task that get_monitoring_list_by_id will return
    mock_existing_task = RealMonitoringList(
        id=existing_task_id, name="Old Name", parts=[], cron_schedule="0 0 * * *",
        recipients=["old@example.com"], active=True, notify_condition="on_change",
        misfire_grace_time=3600
    )
    mock_pm.get_monitoring_list_by_id.return_value = mock_existing_task
    mock_pm.update_monitoring_list.return_value = True # Simulate successful update in PresetsManager

    # Capture the updated object passed to PresetsManager
    updated_task_capture = mock.MagicMock()
    def capture_update(task_id, task_obj):
        updated_task_capture(task_id, task_obj)
        return True
    mock_pm.update_monitoring_list.side_effect = capture_update
    
    result = runner.invoke(app, [
        "monitor", "update", existing_task_id,
        "--name", "New Updated Name",
        "--schedule", "0 1 * * *",
        "--active", "false" # Test passing boolean flag
    ])

    print(f"CLI Update Output: {result.stdout}")
    assert result.exit_code == 0
    assert f"Monitoring task '{existing_task_id}' updated successfully." in result.stdout
    
    mock_pm.get_monitoring_list_by_id.assert_called_once_with(existing_task_id)
    mock_pm.update_monitoring_list.assert_called_once()
    
    # Check the arguments passed to update_monitoring_list
    assert updated_task_capture.call_count == 1
    passed_id, passed_obj = updated_task_capture.call_args[0]
    assert passed_id == existing_task_id
    assert isinstance(passed_obj, RealMonitoringList)
    assert passed_obj.name == "New Updated Name" # Updated
    assert passed_obj.cron_schedule == "0 1 * * *" # Updated
    assert passed_obj.active is False # Updated
    assert passed_obj.recipients == ["old@example.com"] # Unchanged

@patch('inventree_order_calculator.cli._presets_manager', autospec=True)
def test_monitor_update_task_not_found(mock_pm):
    """Test 'monitor update' when task ID is not found."""
    from inventree_order_calculator.cli import app
    runner = CliRunner()
    mock_pm.get_monitoring_list_by_id.return_value = None # Simulate task not found

    result = runner.invoke(app, ["monitor", "update", "ghost_id_123", "--name", "Ghost Name"])
    
    assert result.exit_code != 0
    assert "Monitoring task with ID 'ghost_id_123' not found." in result.stdout
    mock_pm.update_monitoring_list.assert_not_called()

@patch('inventree_order_calculator.cli._presets_manager', autospec=True)
def test_monitor_update_task_no_options_provided(mock_pm):
    """Test 'monitor update' when no update options are provided."""
    from inventree_order_calculator.cli import app
    runner = CliRunner()
    existing_task_id = "task_no_opts_456"
    mock_pm.get_monitoring_list_by_id.return_value = MockCliMonitoringList(id=existing_task_id, name="No Opts", active=True, cron_schedule="* * * * *", recipients=[], notify_condition="always", last_hash=None, parts_count=0)

    result = runner.invoke(app, ["monitor", "update", existing_task_id])
    
    assert result.exit_code == 0 # Should not error, just print a message
    assert "No update parameters provided." in result.stdout
    mock_pm.update_monitoring_list.assert_not_called()

@patch('inventree_order_calculator.cli._presets_manager', autospec=True)
def test_monitor_update_task_invalid_parts(mock_pm):
    """Test 'monitor update' with invalid parts string."""
    from inventree_order_calculator.cli import app
    runner = CliRunner()
    existing_task_id = "task_invalid_parts_789"
    mock_pm.get_monitoring_list_by_id.return_value = MockCliMonitoringList(id=existing_task_id, name="Invalid Parts Update", active=True, cron_schedule="* * * * *", recipients=[], notify_condition="always", last_hash=None, parts_count=0)

    result = runner.invoke(app, ["monitor", "update", existing_task_id, "--parts", "INVALID:PARTS:STRING"])
    
    assert result.exit_code != 0
    assert "Error parsing parts string" in result.stdout
    mock_pm.update_monitoring_list.assert_not_called()

# Tests for monitor delete
@patch('inventree_order_calculator.cli._presets_manager', autospec=True)
def test_monitor_delete_task_success(mock_pm):
    """Test 'monitor delete' successfully deletes a task."""
    from inventree_order_calculator.cli import app
    runner = CliRunner()
    mock_pm.delete_monitoring_list.return_value = True # Simulate successful deletion

    task_id_to_delete = "del_task_1"
    result = runner.invoke(app, ["monitor", "delete", task_id_to_delete])
    
    assert result.exit_code == 0
    assert f"Monitoring task '{task_id_to_delete}' deleted successfully." in result.stdout
    mock_pm.delete_monitoring_list.assert_called_once_with(task_id_to_delete)

@patch('inventree_order_calculator.cli._presets_manager', autospec=True)
def test_monitor_delete_task_not_found_or_fails(mock_pm):
    """Test 'monitor delete' when task is not found or PresetsManager delete fails."""
    from inventree_order_calculator.cli import app
    runner = CliRunner()
    mock_pm.delete_monitoring_list.return_value = False # Simulate deletion failure

    task_id_fail_delete = "del_task_fail_1"
    result = runner.invoke(app, ["monitor", "delete", task_id_fail_delete])
    
    assert result.exit_code != 0
    assert f"Failed to delete monitoring task '{task_id_fail_delete}'." in result.stdout
    mock_pm.delete_monitoring_list.assert_called_once_with(task_id_fail_delete)
# Tests for monitor activate, deactivate, run

@patch('inventree_order_calculator.cli.MonitoringTaskManager.activate_task', return_value=True)
def test_monitor_activate_task_success(mock_activate_task):
    """Test 'monitor activate' successfully activates a task."""
    from inventree_order_calculator.cli import app
    runner = CliRunner()
    task_id_to_activate = "activate_task_1"
    
    result = runner.invoke(app, ["monitor", "activate", task_id_to_activate])
    
    assert result.exit_code == 0
    assert f"Monitoring task '{task_id_to_activate}' activated successfully." in result.stdout
    mock_activate_task.assert_called_once_with(task_id_to_activate)

@patch('inventree_order_calculator.cli.MonitoringTaskManager.activate_task', return_value=False)
def test_monitor_activate_task_fails(mock_activate_task):
    """Test 'monitor activate' when activation fails (e.g., task not found)."""
    from inventree_order_calculator.cli import app
    runner = CliRunner()
    task_id_fail_activate = "activate_fail_1"
    
    result = runner.invoke(app, ["monitor", "activate", task_id_fail_activate])
    
    assert result.exit_code != 0
    assert f"Failed to activate monitoring task '{task_id_fail_activate}'." in result.stdout
    mock_activate_task.assert_called_once_with(task_id_fail_activate)

@patch('inventree_order_calculator.cli.MonitoringTaskManager.deactivate_task', return_value=True)
def test_monitor_deactivate_task_success(mock_deactivate_task):
    """Test 'monitor deactivate' successfully deactivates a task."""
    from inventree_order_calculator.cli import app
    runner = CliRunner()
    task_id_to_deactivate = "deactivate_task_1"
    
    result = runner.invoke(app, ["monitor", "deactivate", task_id_to_deactivate])
    
    assert result.exit_code == 0
    assert f"Monitoring task '{task_id_to_deactivate}' deactivated successfully." in result.stdout
    mock_deactivate_task.assert_called_once_with(task_id_to_deactivate)

@patch('inventree_order_calculator.cli.MonitoringTaskManager.deactivate_task', return_value=False)
def test_monitor_deactivate_task_fails(mock_deactivate_task):
    """Test 'monitor deactivate' when deactivation fails."""
    from inventree_order_calculator.cli import app
    runner = CliRunner()
    task_id_fail_deactivate = "deactivate_fail_1"
    
    result = runner.invoke(app, ["monitor", "deactivate", task_id_fail_deactivate])
    
    assert result.exit_code != 0
    assert f"Failed to deactivate monitoring task '{task_id_fail_deactivate}'." in result.stdout
    mock_deactivate_task.assert_called_once_with(task_id_fail_deactivate)

@patch('inventree_order_calculator.cli.MonitoringTaskManager.get_task_by_id')
@patch('inventree_order_calculator.cli.TaskExecutor.run_monitoring_task')
@patch('inventree_order_calculator.cli._ensure_services_initialized') # Mock to control its side effects
def test_monitor_run_task_success(mock_ensure_services, mock_executor_run, mock_get_task_by_id_mtm, mock_cli_presets_manager):
    """Test 'monitor run' successfully triggers a task run."""
    from inventree_order_calculator.cli import app
    from inventree_order_calculator.presets_manager import MonitoringList as RealMonitoringList # For type check
    runner = CliRunner()
    task_id_to_run = "run_task_1"

    # Mock that the task exists for the initial check in the CLI command
    # The _ensure_services_initialized in CLI for 'run' also sets up monitoring_service globals.
    # The test for TaskExecutor.run_monitoring_task itself is more detailed.
    # Here, we just check the CLI calls the correct TaskManager/TaskExecutor method.
    # PresetsManager's get_monitoring_list_by_id is used by the CLI command.
    mock_cli_presets_manager.get_monitoring_list_by_id.return_value = RealMonitoringList(
        id=task_id_to_run, name="Test Run Task", parts=[], cron_schedule="* * * * *"
    )
    # MonitoringTaskManager.get_task_by_id is also called by TaskExecutor internally,
    # but for this CLI test, we primarily care about the CLI's direct check.
    # If TaskExecutor.run_monitoring_task is fully mocked, its internal calls don't matter here.

    result = runner.invoke(app, ["monitor", "run", task_id_to_run])
    
    assert result.exit_code == 0
    assert f"Manually triggering monitoring task '{task_id_to_run}'..." in result.stdout
    assert f"Manual run for task '{task_id_to_run}' initiated." in result.stdout # Success message from CLI
    
    mock_cli_presets_manager.get_monitoring_list_by_id.assert_called_once_with(task_id_to_run)
    mock_executor_run.assert_called_once_with(task_id_to_run)
    # Ensure _ensure_services_initialized was called with for_monitoring_run=True
    mock_ensure_services.assert_called_with(for_monitoring_run=True)


@patch('inventree_order_calculator.cli._presets_manager.get_monitoring_list_by_id', return_value=None)
@patch('inventree_order_calculator.cli.TaskExecutor.run_monitoring_task')
def test_monitor_run_task_not_found(mock_executor_run, mock_get_list_by_id_pm):
    """Test 'monitor run' when task ID is not found by PresetsManager."""
    from inventree_order_calculator.cli import app
    runner = CliRunner()
    task_id_not_found = "run_not_found_task"
    
    result = runner.invoke(app, ["monitor", "run", task_id_not_found])
    
    assert result.exit_code != 0
    assert f"Monitoring task with ID '{task_id_not_found}' not found." in result.stdout
    mock_get_list_by_id_pm.assert_called_once_with(task_id_not_found)
    mock_executor_run.assert_not_called()