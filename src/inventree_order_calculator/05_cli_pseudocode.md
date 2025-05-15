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
IMPORT InputPart, CalculatedPart, OutputTables, MonitoringList, MonitoringPartItem from .models // Added Monitoring models
IMPORT PresetsManager // Assuming PresetsManager is a class or has static methods
IMPORT MonitoringTaskManager // From 08_monitoring_service_pseudocode.md
IMPORT uuid // For generating IDs if needed, though PresetsManager might handle it
FROM typing import List, Optional // Ensure List and Optional are imported for type hints

// Create Typer application instance
app = typer.Typer()
monitor_app = typer.Typer(name="monitor", help="Manage monitoring tasks.")
app.add_typer(monitor_app)

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

// --- Monitoring Subcommands ---

// Utility function to load presets file for monitor commands
FUNCTION _load_presets_for_monitoring():
    TRY:
        // Assuming PresetsManager is initialized and provides access to loaded data
        // This might involve calling a PresetsManager.load() or similar if not auto-loaded
        // For pseudocode, let's assume a global or accessible PresetsManager instance
        // that handles the presets.json file.
        // This is a simplification; actual implementation will need robust PresetsManager access.
        presets_file_data = PresetsManager.load_presets_from_file(PresetsManager.get_presets_filepath())
        RETURN presets_file_data
    CATCH Exception as e:
        console.print(f"[bold red]Error loading presets file for monitoring: {e}[/bold red]")
        sys.exit(1)

FUNCTION _save_presets_for_monitoring(presets_data):
    TRY:
        success = PresetsManager.save_presets_to_file(PresetsManager.get_presets_filepath(), presets_data)
        IF NOT success:
            console.print(f"[bold red]Error saving presets file after monitoring operation.[/bold red]")
            sys.exit(1)
    CATCH Exception as e:
        console.print(f"[bold red]Error saving presets file: {e}[/bold red]")
        sys.exit(1)


@monitor_app.command("list")
FUNCTION monitor_list_tasks():
    """Lists all configured monitoring tasks."""
    // TEST: cli_monitor_list_displays_tasks
    presets_data = _load_presets_for_monitoring()
    monitoring_lists = PresetsManager.get_monitoring_lists(presets_data)

    IF NOT monitoring_lists:
        console.print("No monitoring tasks configured.")
        RETURN

    table = Table(title="[bold green]Monitoring Tasks[/bold green]")
    table.add_column("ID", style="dim")
    table.add_column("Name")
    table.add_column("Active", justify="center")
    table.add_column("Schedule (Cron)")
    table.add_column("Recipients")
    table.add_column("Notify Condition")
    table.add_column("Last Hash", style="dim")

    FOR task IN monitoring_lists:
        table.add_row(
            task.id,
            task.name,
            "[green]Yes[/green]" IF task.active ELSE "[red]No[/red]",
            task.cron_schedule,
            ", ".join(task.recipients),
            task.notify_condition,
            task.last_hash IF task.last_hash ELSE "-"
        )
    console.print(table)

@monitor_app.command("add")
FUNCTION monitor_add_task(
    name: str = typer.Option(..., "--name", help="User-defined name for the monitoring list."),
    parts_str: str = typer.Option(..., "--parts", help="Comma-separated list of parts, format: 'PartName1:Qty1,PartName2:Qty2[:Version2]'."),
    schedule: str = typer.Option(..., "--schedule", help="Cron expression for the check cycle (e.g., '0 * * * *')."),
    recipients_str: str = typer.Option(..., "--recipients", help="Comma-separated list of email recipients."),
    notify_condition: str = typer.Option("on_change", "--notify-condition", help="Notify 'always' or 'on_change'.")
):
    """Adds a new monitoring task."""
    // TEST: cli_monitor_add_creates_new_task_in_presets
    presets_data = _load_presets_for_monitoring()

    parsed_parts: List[MonitoringPartItem] = []
    TRY:
        for p_item_str IN parts_str.split(','):
            segments = p_item_str.strip().split(':')
            part_name = segments[0].strip()
            quantity = int(segments[1].strip())
            version = segments[2].strip() IF len(segments) > 2 ELSE None
            IF quantity <= 0: RAISE ValueError("Quantity must be positive.")
            parsed_parts.append(MonitoringPartItem(name=part_name, quantity=quantity, version=version))
    CATCH Exception as e:
        console.print(f"[bold red]Error parsing parts string: {e}. Expected format 'Name1:Qty1[:Version1],Name2:Qty2'.[/bold red]")
        sys.exit(1)

    IF not parsed_parts:
        console.print(f"[bold red]No parts provided for the monitoring task.[/bold red]")
        sys.exit(1)

    recipients_list = [email.strip() for email in recipients_str.split(',') if email.strip()]
    IF not recipients_list:
        console.print(f"[bold red]No recipients provided for the monitoring task.[/bold red]")
        sys.exit(1)

    IF notify_condition NOT IN ["always", "on_change"]:
        console.print(f"[bold red]Invalid notify condition: {notify_condition}. Must be 'always' or 'on_change'.[/bold red]")
        sys.exit(1)

    # ID will be generated by PresetsManager.add_monitoring_list if not provided or if it's a dict
    new_task_data = {
        "name": name,
        "parts": parsed_parts, # This should be list of dicts if Pydantic model is used in presets_manager
                               # Or PresetsManager.add_monitoring_list should handle MonitoringPartItem objects
        "active": True, # Default new tasks to active
        "cron_schedule": schedule,
        "recipients": recipients_list,
        "notify_condition": notify_condition,
        # id and last_hash will be handled by add_monitoring_list
    }
    
    # Convert parts to dicts if PresetsManager.add_monitoring_list expects dicts for Pydantic creation
    new_task_data_for_pm = {
        "id": str(uuid.uuid4()), # Generate ID here or let PresetsManager do it
        "name": name,
        "parts": [part.model_dump() for part in parsed_parts], # Convert to dicts
        "active": True,
        "cron_schedule": schedule,
        "recipients": recipients_list,
        "notify_condition": notify_condition,
        "last_hash": None
    }

    TRY
        updated_presets_data = PresetsManager.add_monitoring_list(presets_data, new_task_data_for_pm)
        _save_presets_for_monitoring(updated_presets_data)
        console.print(f"[green]Monitoring task '{name}' (ID: {new_task_data_for_pm['id']}) added successfully.[/green]")
        // TODO: Inform MonitoringService/Scheduler about the new task if it's running
        // This might involve IPC or a shared mechanism if CLI and service are separate processes.
        // For now, assume service reloads on its own schedule or on restart.
    CATCH ValueError as e: // Catch duplicate ID or validation errors from PresetsManager
        console.print(f"[bold red]Error adding monitoring task: {e}[/bold red]")
        sys.exit(1)


@monitor_app.command("update")
FUNCTION monitor_update_task(
    task_id: str = typer.Argument(..., help="ID of the task to update."),
    name: Optional[str] = typer.Option(None, "--name", help="New name for the task."),
    parts_str: Optional[str] = typer.Option(None, "--parts", help="New parts list string."),
    schedule: Optional[str] = typer.Option(None, "--schedule", help="New cron schedule."),
    recipients_str: Optional[str] = typer.Option(None, "--recipients", help="New recipients list string."),
    active: Optional[bool] = typer.Option(None, "--active/--inactive", help="Set task active or inactive."),
    notify_condition: Optional[str] = typer.Option(None, "--notify-condition", help="New notify condition ('always' or 'on_change').")
):
    """Updates an existing monitoring task."""
    // TEST: cli_monitor_update_modifies_existing_task
    presets_data = _load_presets_for_monitoring()
    
    updates: Dict[str, any] = {}
    if name is not None: updates["name"] = name
    if schedule is not None: updates["cron_schedule"] = schedule
    if active is not None: updates["active"] = active
    if notify_condition is not None:
        if notify_condition not in ["always", "on_change"]:
            console.print(f"[bold red]Invalid notify condition: {notify_condition}. Must be 'always' or 'on_change'.[/bold red]")
            sys.exit(1)
        updates["notify_condition"] = notify_condition

    if parts_str is not None:
        parsed_parts: List[MonitoringPartItem] = []
        try:
            for p_item_str in parts_str.split(','):
                segments = p_item_str.strip().split(':')
                part_name = segments[0].strip()
                quantity = int(segments[1].strip())
                version = segments[2].strip() if len(segments) > 2 else None
                if quantity <= 0: raise ValueError("Quantity must be positive.")
                parsed_parts.append(MonitoringPartItem(name=part_name, quantity=quantity, version=version))
            updates["parts"] = [part.model_dump() for part in parsed_parts] # Convert to dicts
        except Exception as e:
            console.print(f"[bold red]Error parsing parts string for update: {e}[/bold red]")
            sys.exit(1)
        if not updates["parts"]:
             console.print(f"[bold red]Cannot update parts to an empty list.[/bold red]")
             sys.exit(1)


    if recipients_str is not None:
        recipients_list = [email.strip() for email in recipients_str.split(',') if email.strip()]
        if not recipients_list:
            console.print(f"[bold red]Cannot update recipients to an empty list.[/bold red]")
            sys.exit(1)
        updates["recipients"] = recipients_list
        
    if not updates:
        console.print("No update parameters provided.")
        return

    TRY
        updated_presets_data = PresetsManager.update_monitoring_list(presets_data, task_id, updates)
        if updated_presets_data is presets_data: // Indicates task_id not found by PresetsManager if it returns original
             console.print(f"[bold red]Monitoring task with ID '{task_id}' not found.[/bold red]")
             sys.exit(1)
        _save_presets_for_monitoring(updated_presets_data)
        console.print(f"[green]Monitoring task '{task_id}' updated successfully.[/green]")
        // TODO: Inform MonitoringService/Scheduler about the updated task
    CATCH ValueError as e: // Catch ID not found or validation errors
        console.print(f"[bold red]Error updating monitoring task: {e}[/bold red]")
        sys.exit(1)

@monitor_app.command("delete")
FUNCTION monitor_delete_task(task_id: str = typer.Argument(..., help="ID of the task to delete.")):
    """Deletes a monitoring task."""
    // TEST: cli_monitor_delete_removes_task_from_presets
    presets_data = _load_presets_for_monitoring()
    updated_presets_data = PresetsManager.delete_monitoring_list(presets_data, task_id)

    if updated_presets_data is presets_data : # No change means task was not found
        console.print(f"[bold red]Monitoring task with ID '{task_id}' not found for deletion.[/bold red]")
        sys.exit(1)
    
    _save_presets_for_monitoring(updated_presets_data)
    console.print(f"[green]Monitoring task '{task_id}' deleted successfully.[/green]")
    // TODO: Inform MonitoringService/Scheduler to remove the task

@monitor_app.command("activate")
FUNCTION monitor_activate_task(task_id: str = typer.Argument(..., help="ID of the task to activate.")):
    """Activates a monitoring task."""
    // TEST: cli_monitor_activate_sets_task_active_flag_true
    presets_data = _load_presets_for_monitoring()
    # PresetsManager.update_monitoring_list can be used for this
    updated_presets_data = PresetsManager.update_monitoring_list(presets_data, task_id, {"active": True})
    if updated_presets_data is presets_data:
         console.print(f"[bold red]Monitoring task with ID '{task_id}' not found or no change made.[/bold red]")
         sys.exit(1)
    _save_presets_for_monitoring(updated_presets_data)
    console.print(f"[green]Monitoring task '{task_id}' activated.[/green]")
    // TODO: Inform MonitoringService/Scheduler

@monitor_app.command("deactivate")
FUNCTION monitor_deactivate_task(task_id: str = typer.Argument(..., help="ID of the task to deactivate.")):
    """Deactivates a monitoring task."""
    // TEST: cli_monitor_deactivate_sets_task_active_flag_false
    presets_data = _load_presets_for_monitoring()
    updated_presets_data = PresetsManager.update_monitoring_list(presets_data, task_id, {"active": False})
    if updated_presets_data is presets_data:
         console.print(f"[bold red]Monitoring task with ID '{task_id}' not found or no change made.[/bold red]")
         sys.exit(1)
    _save_presets_for_monitoring(updated_presets_data)
    console.print(f"[green]Monitoring task '{task_id}' deactivated.[/green]")
    // TODO: Inform MonitoringService/Scheduler

@monitor_app.command("run")
FUNCTION monitor_run_task_manually(task_id: str = typer.Argument(..., help="ID of the task to run manually.")):
    """Runs a specific monitoring task manually, outside of its schedule."""
    // TEST: cli_monitor_run_executes_task_once
    console.print(f"Attempting to manually run task '{task_id}'...")
    // This requires the MonitoringTaskManager from 08_monitoring_service_pseudocode.md
    // It assumes that the MonitoringTaskManager can be initialized and used here.
    // This might be complex if the CLI and the service are separate processes.
    // For a monolithic app, this is more straightforward.
    TRY
        // Initialize necessary components for a single run
        config = get_config() // Load full app config
        // PresetsManager.initialize() // Ensure presets are loaded
        // MonitoringTaskManager.initialize(config, PresetsManager) // Conceptual initialization

        task_config = MonitoringTaskManager.get_task_by_id(task_id) // Using the manager from service pseudocode
        IF task_config IS NULL:
            console.print(f"[bold red]Task with ID '{task_id}' not found.[/bold red]")
            sys.exit(1)
        
        IF NOT task_config.active:
            console.print(f"[yellow]Warning: Task '{task_id}' is currently inactive. Running it manually anyway.[/yellow]")

        MonitoringTaskManager.run_task_manually(task_id) // Calls TaskExecutor.run_monitoring_task
        console.print(f"[green]Manual run of task '{task_id}' completed. Check logs and email (if configured).[/green]")
    CATCH Exception as e:
        logger.exception(f"Error during manual run of task {task_id}")
        console.print(f"[bold red]Error during manual run of task '{task_id}': {e}[/bold red]")
        sys.exit(1)


// Entry point for running the Typer app (if this file is executed directly)
// Usually, a separate main.py or __main__.py handles this.
// IF __name__ == "__main__":
//     app()