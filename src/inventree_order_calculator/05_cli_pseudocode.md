# Module: src/inventree_order_calculator/cli.py
# Description: Defines the command-line interface using Typer and Rich.

# Dependencies: typer, rich, config module, api_client module, calculator module, models module, logging, sys

// Import necessary libraries and modules
IMPORT typer
IMPORT rich
FROM rich.console IMPORT Console
FROM rich.table IMPORT Table
IMPORT logging
IMPORT sys

IMPORT get_config from .config
IMPORT ConfigurationError from .config
IMPORT InventreeApiClient from .api_client
IMPORT ApiClientError, ApiAuthenticationError, ApiConnectionError, PartNotFoundError from .api_client
IMPORT OrderCalculator from .calculator
IMPORT InputPart, CalculatedPart, OutputTables from .models

// Create Typer application instance
app = typer.Typer()

// Create Rich console instance for output
console = Console()

// Setup basic logging configuration
// More sophisticated logging setup could be added (e.g., file logging)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

// Define the main command
@app.command()
FUNCTION main(
    // Define CLI arguments/options using Typer
    // Example: Accept parts as "PART_ID:QUANTITY" strings
    parts_to_build: LIST[STRING] = typer.Argument(..., help="List of parts to build, format: PART_ID:QUANTITY or PART_NAME:QUANTITY"),
    // Example: Option for verbosity
    verbose: BOOLEAN = typer.Option(False, "--verbose", "-v", help="Enable detailed logging.")
    // Add options for config file path if not solely relying on env vars?
):
    """
    Calculates required parts and subassemblies from InvenTree based on input orders.
    """
    IF verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled.")

    TRY
        // 1. Load Configuration
        logger.info("Loading configuration...")
        config = get_config()
        // TEST: Loading configuration successfully

    CATCH ConfigurationError as e:
        console.print(f"[bold red]Configuration Error:[/bold red] {e}")
        // TEST: Handling configuration errors during startup
        sys.exit(1) // Exit with error code

    TRY
        // 2. Initialize API Client
        logger.info("Initializing InvenTree API client...")
        api_client = InventreeApiClient(config)
        // TEST: Successful API client initialization

    CATCH ApiAuthenticationError | ApiConnectionError as e:
        console.print(f"[bold red]API Connection Error:[/bold red] {e}")
        // TEST: Handling API connection/auth errors during startup
        sys.exit(1)
    CATCH ApiClientError as e: // Catch other potential client init errors
        console.print(f"[bold red]API Client Error:[/bold red] {e}")
        sys.exit(1)

    // 3. Parse Input Parts
    logger.info("Parsing input parts...")
    input_parts_list: LIST[InputPart] = []
    FOR part_str IN parts_to_build:
        TRY
            identifier, quantity_str = part_str.split(':')
            quantity = int(quantity_str)
            IF quantity <= 0:
                 RAISE ValueError("Quantity must be positive.")
            input_parts_list.append(InputPart(part_identifier=identifier.strip(), quantity_to_build=quantity))
            // TEST: Parsing valid input strings
        CATCH ValueError as e:
            console.print(f"[bold red]Invalid Input Format:[/bold red] '{part_str}'. Expected format 'PART_ID:QUANTITY' or 'PART_NAME:QUANTITY'. {e}")
            // TEST: Handling invalid input format (e.g., missing ':', non-integer quantity)
            sys.exit(1)

    IF NOT input_parts_list:
        console.print("[bold yellow]Warning:[/bold yellow] No valid input parts provided.")
        sys.exit(0) // Exit gracefully if no input

    // 4. Initialize Calculator
    calculator = OrderCalculator(api_client)

    // 5. Run Calculation
    logger.info("Running calculation...")
    TRY
        results: OutputTables = calculator.calculate_orders(input_parts_list)
        // TEST: Successful execution of the main calculation logic

    CATCH ApiClientError as e: // Catch errors during calculation (e.g., retries failed)
        console.print(f"[bold red]Calculation Error:[/bold red] An API error occurred during calculation: {e}")
        // TEST: Handling API errors during calculation phase
        sys.exit(1)
    CATCH Exception as e: // Catch unexpected errors during calculation
        logger.exception("An unexpected error occurred during calculation.")
        console.print(f"[bold red]Unexpected Error:[/bold red] {e}")
        sys.exit(1)

    // 6. Generate and Print Output Tables using Rich
    logger.info("Generating output tables...")
    CALL generate_output_tables(results)
    // TEST: Successful generation and display of output tables

    console.print("\n[bold green]Calculation finished successfully.[/bold green]")


// Function to generate and print tables using Rich
FUNCTION generate_output_tables(results: OutputTables):
    // TEST: Generating output tables correctly based on calculated results

    // --- Parts to Order Table ---
    IF results.parts_to_order:
        table_order = Table(title="[bold blue]Parts to Order[/bold blue]", show_header=True, header_style="bold magenta")
        // Define columns based on final cli.py implementation
        table_order.add_column("Part ID", style="dim", width=12)
        table_order.add_column("Part Name")
        table_order.add_column("Needed", justify="right") // Added
        table_order.add_column("Total In Stock", justify="right")
        table_order.add_column("Req. Builds", justify="right") // Abbreviated header
        table_order.add_column("Req. Sales", justify="right") // Abbreviated header
        table_order.add_column("Available", justify="right")
        table_order.add_column("To Order", justify="right", style="bold red") // Moved before On Order
        table_order.add_column("On Order", justify="right") // Moved after To Order

        FOR item IN results.parts_to_order:
            pd = item.part_data
            table_order.add_row(
                str(pd.pk),
                pd.name,
                f"{item.total_required:.2f}", // Added Needed data
                f"{pd.total_in_stock:.2f}",
                f"{pd.required_for_build_orders:.2f}",
                f"{pd.required_for_sales_orders:.2f}",
                f"{item.available:.2f}",
                f"{item.to_order:.2f}", // Moved before On Order data
                f"{pd.ordering:.2f}" // Moved after To Order data
            )

        console.print(table_order)
        // TEST: Correct population of 'Parts to Order' table
    ELSE:
        console.print("[bold blue]Parts to Order:[/bold blue] None required.")

    // --- Subassemblies to Build Table ---
    IF results.subassemblies_to_build:
        table_build = Table(title="[bold blue]Subassemblies to Build[/bold blue]", show_header=True, header_style="bold magenta")
        // Define columns based on final cli.py implementation
        table_build.add_column("Part ID", style="dim", width=12)
        table_build.add_column("Part Name")
        table_build.add_column("Needed", justify="right") // Added
        table_build.add_column("Total In Stock", justify="right")
        table_build.add_column("Req. Builds", justify="right")
        table_build.add_column("Req. Sales", justify="right")
        table_build.add_column("Available", justify="right")
        table_build.add_column("In Production", justify="right") // Moved after Available
        table_build.add_column("To Build", justify="right", style="bold blue") // Style updated

        FOR item IN results.subassemblies_to_build:
            pd = item.part_data
            table_build.add_row(
                str(pd.pk),
                pd.name,
                f"{item.total_required:.2f}", // Added Needed data
                f"{pd.total_in_stock:.2f}",
                f"{pd.required_for_build_orders:.2f}",
                f"{pd.required_for_sales_orders:.2f}",
                f"{item.available:.2f}",
                f"{pd.building:.2f}", // Moved after Available data
                f"{item.to_build:.2f}"
            )

        console.print(table_build)
        // TEST: Correct population of 'Subassemblies to Build' table
    ELSE:
        console.print("[bold blue]Subassemblies to Build:[/bold blue] None required.")

// Entry point for running the Typer app (if this file is executed directly)
// Usually, a separate main.py or __main__.py handles this.
// IF __name__ == "__main__":
//     app()