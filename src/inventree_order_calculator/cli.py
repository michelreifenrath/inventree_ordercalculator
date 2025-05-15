import typer
from rich.console import Console
from rich.table import Table
from typing import List, Dict, Optional # Keep Dict for updates
from typing_extensions import Annotated
from decimal import Decimal
import logging # Added for explicit logger setup
import sys # Added for sys.exit
from pathlib import Path # Added for PresetsManager config_path
import click # Import click
import uuid # Added for generating task IDs
from pydantic import ValidationError # Moved import here

# --- Project Dependencies ---
try:
    from src.inventree_order_calculator.config import Config, ConfigError, get_config # Use get_config
    from src.inventree_order_calculator.api_client import ApiClient, ApiClientError, ApiAuthenticationError, ApiConnectionError, PartNotFoundError # Changed InvenTreeAPIClient to ApiClient
    from src.inventree_order_calculator.calculator import OrderCalculator
    from src.inventree_order_calculator.models import InputPart, OutputTables, CalculatedPart # Removed PartInputLine
    from src.inventree_order_calculator.presets_manager import PresetsManager, Preset, PresetItem, MonitoringList, MonitoringPartItem
    # Import monitoring service components for 'run' and potentially for scheduler interaction
    from src.inventree_order_calculator.monitoring_service import MonitoringTaskManager, Scheduler, start_monitoring_service_new, stop_monitoring_service_new, TaskExecutor # Renamed functions
except ImportError as e:
    # Fallback for basic script parsing if run in an environment where full package isn't set up
    # This is primarily for development convenience and won't support full functionality.
    print(f"Warning: CLI running with dummy imports due to: {e}", file=sys.stderr)
    # raise e # Re-raise the import error to make it fail loudly in tests - REMOVED
    class ConfigError(Exception): pass
    class Config:
        INVENTREE_API_URL: str = "dummy_url"
        INVENTREE_API_TOKEN: str = "dummy_token"
        INVENTREE_INSTANCE_URL: Optional[str] = None
        PRESETS_FILE_PATH: str = "presets.json" # Add for PresetsManager
        LOG_LEVEL: str = "INFO"
        API_TIMEOUT: int = 30 # Add for InvenTreeAPIClient
        # Add other essential defaults if needed by CLI functions directly
        @classmethod
        def load(cls): return cls()
    def get_config(): return Config.load()

    class ApiClientError(Exception): pass
    class ApiAuthenticationError(ApiClientError): pass
    class ApiConnectionError(ApiClientError): pass
    class PartNotFoundError(ApiClientError): pass
    class InvenTreeAPIClient:
        def __init__(self, base_url, api_token, timeout=30): pass
    class OrderCalculator:
        def __init__(self, client): pass
        def calculate_orders(self, parts: List['InputPart']) -> 'OutputTables': # Forward reference InputPart
            return OutputTables(parts_to_order=[], subassemblies_to_build=[]) # Ensure OutputTables is defined
    
    # Dummy BaseModel if pydantic is not available in this fallback
    try: from pydantic import BaseModel
    except ImportError:
        class BaseModel: # Dummy BaseModel if pydantic is not available
            pass

    class InputPart(BaseModel):
        part_identifier: str
        quantity_to_build: float
    class PartInputLine(BaseModel):
        name_or_ipn: str
        quantity: int
        version: Optional[str] = None
    class CalculatedPart(BaseModel): # Dummy for type hint
        part_data: dict = {}
        total_required: float = 0.0
        available: float = 0.0
        to_order: float = 0.0
        to_build: float = 0.0
        belongs_to_top_parts: list = []

    class OutputTables(BaseModel):
        parts_to_order: List[CalculatedPart] = []
        subassemblies_to_build: List[CalculatedPart] = []

    class PresetItem(BaseModel): pass
    class Preset(BaseModel): pass
    class MonitoringPartItem(BaseModel):
        name_or_ipn: str
        quantity: int
        version: Optional[str] = None
    class MonitoringList(BaseModel):
        id: str
        name: str
        parts: List[MonitoringPartItem]
        active: bool
        cron_schedule: str
        recipients: List[str]
        notify_condition: str
        last_hash: Optional[str] = None
        misfire_grace_time: int = 3600
    class PresetsManager:
        def __init__(self, config_path=None): self.config_path = config_path
        def get_monitoring_lists(self) -> List[MonitoringList]: return []
        def add_monitoring_list(self, data: MonitoringList) -> bool: return True
        def update_monitoring_list(self, list_id: str, data: MonitoringList) -> bool: return True
        def delete_monitoring_list(self, list_id: str) -> bool: return True
        def get_monitoring_list_by_id(self, list_id: str) -> Optional[MonitoringList]: return None
    class MonitoringTaskManager: # Dummy class
        @staticmethod
        def get_task_by_id(task_id: str): return None
        @staticmethod
        def run_task_manually(task_id: str): print(f"Dummy run task {task_id}")
        # Add dummy methods that mirror the ones used in CLI
        @staticmethod
        def add_task(task_data: dict): return MonitoringList(**task_data) if isinstance(task_data.get("parts")[0], dict) else None
        @staticmethod
        def update_task(task_id: str, updated_data: dict): return MonitoringList(**updated_data) if task_id else None
        @staticmethod
        def delete_task(task_id: str): return True if task_id else False
        @staticmethod
        def activate_task(task_id: str): return True if task_id else False
        @staticmethod
        def deactivate_task(task_id: str): return True if task_id else False

    class Scheduler: # Dummy class
        @staticmethod
        def get_scheduled_jobs_info(): return []
    class TaskExecutor: # Dummy class
        @staticmethod
        def run_monitoring_task(task_id: str): pass


# --- Typer App Initialization ---
app = typer.Typer(help="Inventree Order Calculator CLI")
monitor_app = typer.Typer(name="monitor", help="Manage monitoring tasks.")
app.add_typer(monitor_app, name="monitor") 

console = Console()
logger = logging.getLogger(__name__) 

# --- Global instances (initialized in _ensure_services_initialized or specific commands) ---
_config: Optional[Config] = None
_presets_manager: Optional[PresetsManager] = None
_api_client: Optional[ApiClient] = None # Corrected type hint
_calculator: Optional[OrderCalculator] = None
_monitoring_task_manager: Optional[MonitoringTaskManager] = None # Added global instance
# _email_service: Optional[EmailService] = None # Placeholder for future use

def _setup_logging(log_level_str: str):
    level = getattr(logging, log_level_str.upper(), logging.INFO)
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s', force=True)
    # logger.info(f"Logging level set to: {log_level_str.upper()}") # Avoid logging before Typer output

def _ensure_services_initialized(for_calculation: bool = False, for_monitoring_run: bool = False, for_monitoring_management: bool = False): # Added for_monitoring_management
    global _config, _presets_manager, _api_client, _calculator, _monitoring_task_manager # Added _monitoring_task_manager
    if _config is None:
        try:
            _config = get_config()
            _setup_logging(_config.LOG_LEVEL) 
        except ConfigError as e:
            console.print(f"[bold red]Configuration Error:[/bold red] {e}")
            raise typer.Exit(code=1)
    
    if _presets_manager is None: # Always needed for monitor commands
        _presets_manager = PresetsManager(config_path=Path(_config.PRESETS_FILE_PATH))
    
    if for_monitoring_management or for_monitoring_run: # MonitoringTaskManager needed for management and run
        if _monitoring_task_manager is None:
            # Ensure monitoring_service globals are set up for MTM initialization
            import src.inventree_order_calculator.monitoring_service as ms
            if ms._config_instance is None: ms._config_instance = _config
            if ms._presets_manager_instance is None: ms._presets_manager_instance = _presets_manager
            # MTM might need other services like EmailService in the future
            _monitoring_task_manager = MonitoringTaskManager() # Initialize it

    if for_calculation or for_monitoring_run: # Calculation engine needed for both
        if _api_client is None:
            try:
                _api_client = InvenTreeAPIClient(
                    base_url=_config.INVENTREE_API_URL,
                    api_token=_config.INVENTREE_API_TOKEN,
                    timeout=_config.API_TIMEOUT
                )
            except (ApiAuthenticationError, ApiConnectionError) as e:
                console.print(f"[bold red]API Client Initialization Error:[/bold red] {e}")
                raise typer.Exit(code=1)
        if _calculator is None:
            _calculator = OrderCalculator(_api_client)
    
    if for_monitoring_run:
        # For CLI 'run', ensure monitoring_service's globals are set up
        # This is a simplified approach for CLI; a real service would manage its own state.
        import src.inventree_order_calculator.monitoring_service as ms
        if ms._config_instance is None: ms._config_instance = _config
        if ms._presets_manager_instance is None: ms._presets_manager_instance = _presets_manager
        if ms._api_client_instance is None: ms._api_client_instance = _api_client # Also needed by MTM via TaskExecutor
        if ms._order_calculator_instance is None: ms._order_calculator_instance = _calculator # Also needed by MTM via TaskExecutor
        # If EmailService becomes a direct dependency of MTM or TaskExecutor, initialize it here too.


def parse_parts_input_for_calc(parts_list: List[str]) -> List[InputPart]:
    parsed_parts: List[InputPart] = []
    for part_str in parts_list:
        part_num_str = "" 
        quantity_str = ""
        if ":" not in part_str:
            console.print(f"[bold red]Error:[/bold red] Invalid format for part '{part_str}'. Expected format: PART_IDENTIFIER:QUANTITY")
            raise typer.Exit(code=1)
        try:
            part_num_str, quantity_str = part_str.split(":", 1)
            quantity = float(quantity_str) 
            if quantity <= 0:
                 console.print(f"[bold red]Error:[/bold red] Quantity for part '{part_num_str}' must be positive.")
                 raise typer.Exit(code=1)
            parsed_parts.append(InputPart(part_identifier=part_num_str.strip(), quantity_to_build=quantity))
        except ValueError:
            if ":" in part_str: part_num_str, _ = part_str.split(":", 1) 
            console.print(f"[bold red]Error:[/bold red] Invalid quantity for part '{part_num_str}'. '{quantity_str}' is not a valid number.")
            raise typer.Exit(code=1)
        except Exception as e:
             console.print(f"[bold red]Error:[/bold red] Could not parse '{part_str}': {e}")
             raise typer.Exit(code=1)
    return parsed_parts


@app.command(name="calculate", help="Calculates required components and total cost for a list of top-level parts.")
def calculate_order_command(
    parts_to_build: Annotated[List[str], typer.Argument(help="List of parts to build, format: PART_ID_OR_NAME:QUANTITY")],
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable detailed logging.")] = False
):
    if verbose: _setup_logging("DEBUG") 
    else: _setup_logging(get_config().LOG_LEVEL if _config else "INFO") # Ensure logging is set up
    
    _ensure_services_initialized(for_calculation=True)
    assert _config and _calculator 

    console.print("[bold blue]Inventree Order Calculator[/bold blue]")
    
    input_parts_list = parse_parts_input_for_calc(parts_to_build)
    if not input_parts_list:
        console.print("[bold yellow]Warning:[/bold yellow] No valid parts provided for calculation.")
        raise typer.Exit()

    logger.info(f"Calculating order for: {', '.join(f'{ip.part_identifier}:{ip.quantity_to_build}' for ip in input_parts_list)}")
    
    try:
        results: OutputTables = _calculator.calculate_orders(input_parts_list)
        _generate_output_tables(results, _config) 
    except PartNotFoundError as e:
        console.print(f"[bold red]Part Not Found Error:[/bold red] {e}")
        raise typer.Exit(code=1)
    except ApiClientError as e:
        console.print(f"[bold red]API Error during calculation:[/bold red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.exception("An unexpected error occurred during calculation.")
        console.print(f"[bold red]Unexpected Error:[/bold red] {e}")
        raise typer.Exit(code=1)
    
    console.print("\n[bold green]Calculation finished successfully.[/bold green]")


def _generate_output_tables(results: OutputTables, config: Config):
    # --- Parts to Order Table ---
    if results.parts_to_order:
        table_order = Table(title="[bold blue]Parts to Order[/bold blue]", show_header=True, header_style="bold magenta")
        table_order.add_column("Part ID", style="dim", width=12)
        table_order.add_column("Part Name", width=30)
        table_order.add_column("Needed", justify="right")
        table_order.add_column("In Stock", justify="right")
        table_order.add_column("Req. Builds", justify="right")
        table_order.add_column("Req. Sales", justify="right")
        table_order.add_column("Available", justify="right")
        table_order.add_column("To Order", justify="right", style="bold red")
        table_order.add_column("On Order", justify="right")
        table_order.add_column("Belongs To", width=25, overflow="fold")

        for item in results.parts_to_order: 
            pd = item.part_data 
            display_name = pd.name
            if config.INVENTREE_INSTANCE_URL and pd.pk is not None:
                link_url = f"{config.INVENTREE_INSTANCE_URL.rstrip('/')}/part/{pd.pk}/"
                display_name = f"[link={link_url}]{pd.name}[/link]"

            table_order.add_row(
                str(pd.pk) if pd.pk else "N/A",
                display_name,
                f"{item.total_required:.2f}",
                f"{pd.total_in_stock:.2f}",
                f"{pd.required_for_build_orders:.2f}",
                f"{pd.required_for_sales_orders:.2f}",
                f"{item.available:.2f}",
                f"{item.to_order:.2f}",
                f"{pd.ordering:.2f}",
                ", ".join(sorted(list(item.belongs_to_top_parts)))
            )
        console.print(table_order)
    else:
        console.print("[bold blue]Parts to Order:[/bold blue] None required.")

    # --- Subassemblies to Build Table ---
    if results.subassemblies_to_build:
        table_build = Table(title="[bold blue]Subassemblies to Build[/bold blue]", show_header=True, header_style="bold magenta")
        table_build.add_column("Part ID", style="dim", width=12)
        table_build.add_column("Part Name", width=30)
        table_build.add_column("Needed", justify="right")
        table_build.add_column("In Stock", justify="right")
        table_build.add_column("Req. Builds", justify="right")
        table_build.add_column("Req. Sales", justify="right")
        table_build.add_column("Available", justify="right")
        table_build.add_column("In Prod.", justify="right") 
        table_build.add_column("To Build", justify="right", style="bold blue")
        table_build.add_column("Belongs To", width=25, overflow="fold")

        for item in results.subassemblies_to_build: 
            pd = item.part_data
            display_name = pd.name
            if config.INVENTREE_INSTANCE_URL and pd.pk is not None:
                link_url = f"{config.INVENTREE_INSTANCE_URL.rstrip('/')}/part/{pd.pk}/"
                display_name = f"[link={link_url}]{pd.name}[/link]"

            table_build.add_row(
                str(pd.pk) if pd.pk else "N/A",
                display_name,
                f"{item.total_required:.2f}",
                f"{pd.total_in_stock:.2f}",
                f"{pd.required_for_build_orders:.2f}",
                f"{pd.required_for_sales_orders:.2f}",
                f"{item.available:.2f}",
                f"{pd.building:.2f}", 
                f"{item.to_build:.2f}",
                ", ".join(sorted(list(item.belongs_to_top_parts)))
            )
        console.print(table_build)
    else:
        console.print("[bold blue]Subassemblies to Build:[/bold blue] None required.")


# --- Monitoring Subcommands ---
@monitor_app.callback(invoke_without_command=True) # invoke_without_command for verbose on monitor itself
def monitor_callback(
    ctx: typer.Context, # Added context
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable detailed logging for monitor commands.")] = False
):
    """Manage monitoring tasks."""
    # Setup logging based on the global verbose flag or command-specific one
    log_level = "DEBUG" if verbose else (get_config().LOG_LEVEL if _config else "INFO")
    _setup_logging(log_level)
    if ctx.invoked_subcommand is None: # If just 'monitor' is called, print help
        console.print(ctx.get_help())
        return
    _ensure_services_initialized(for_monitoring_management=True) # Ensures MTM is also available for monitor subcommands


def _parse_monitoring_parts(parts_str: str) -> List[MonitoringPartItem]:
    parsed_parts: List[MonitoringPartItem] = []
    if not parts_str: return parsed_parts
    try:
        for p_item_str in parts_str.split(','):
            segments = p_item_str.strip().split(':')
            if not segments or not segments[0].strip(): continue 

            part_name_or_ipn = segments[0].strip()
            if len(segments) < 2: raise ValueError(f"Missing quantity for part '{part_name_or_ipn}'")
            
            quantity = int(segments[1].strip())
            version = segments[2].strip() if len(segments) > 2 and segments[2].strip() else None
            if quantity <= 0: raise ValueError("Quantity must be positive.")
            parsed_parts.append(MonitoringPartItem(name_or_ipn=part_name_or_ipn, quantity=quantity, version=version))
    except ValueError as e:
        console.print(f"[bold red]Error parsing parts string: '{parts_str}'. {e}. Expected format 'Name1:Qty1[:Version1],Name2:Qty2'.[/bold red]")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error parsing parts string '{parts_str}': {e}[/bold red]")
        raise typer.Exit(code=1)
    if not parsed_parts and parts_str.strip(): 
        console.print(f"[bold red]No valid parts could be parsed from: '{parts_str}'[/bold red]")
        raise typer.Exit(code=1)
    return parsed_parts

@monitor_app.command("list")
def monitor_list_tasks():
    """Lists all configured monitoring tasks."""
    assert _presets_manager 
    monitoring_lists = _presets_manager.get_monitoring_lists()

    if not monitoring_lists:
        console.print("No monitoring tasks configured.")
        return

    table = Table(title="[bold green]Monitoring Tasks[/bold green]")
    table.add_column("ID", style="dim", overflow="fold")
    table.add_column("Name")
    table.add_column("Active", justify="center")
    table.add_column("Schedule (Cron)")
    table.add_column("Recipients", overflow="fold")
    table.add_column("Notify Condition")
    table.add_column("Last Hash", style="dim", overflow="fold")
    table.add_column("Parts Count", justify="right")

    for task in monitoring_lists:
        table.add_row(
            task.id,
            task.name,
            "[green]Yes[/green]" if task.active else "[red]No[/red]",
            task.cron_schedule,
            ", ".join(task.recipients) if task.recipients else "-",
            task.notify_condition,
            task.last_hash if task.last_hash else "-",
            str(len(task.parts))
        )
    console.print(table)

@monitor_app.command("add")
def monitor_add_task(
    name: Annotated[str, typer.Option(..., "--name", help="User-defined name for the monitoring task.")],
    parts_str: Annotated[str, typer.Option(..., "--parts", help="Comma-separated list of parts, format: 'PartNameOrIPN1:Qty1[:Version1],PartNameOrIPN2:Qty2'.")],
    schedule: Annotated[str, typer.Option(..., "--schedule", help="Cron expression for the check cycle (e.g., '0 * * * *').")],
    recipients_str: Annotated[str, typer.Option(..., "--recipients", help="Comma-separated list of email recipients.")],
    email_config_name: Annotated[str, typer.Option(..., "--email-config-name", help="Name of the email configuration to use for notifications.")],
    notify_condition: Annotated[str, typer.Option("--notify-condition", help="Notify 'always' or 'on_change'. Valid values: always, on_change.")] = "on_change",
    misfire_grace_time: Annotated[int, typer.Option("--misfire-grace-time", help="APScheduler misfire_grace_time in seconds.")] = 3600,
    active: Annotated[bool, typer.Option("--active/--inactive", help="Set task active or inactive on creation. Defaults to active.")] = True
):
    """Adds a new monitoring task."""
    assert _presets_manager 
    
    parsed_parts = _parse_monitoring_parts(parts_str)
    if not parsed_parts: 
        console.print(f"[bold red]No parts provided for the monitoring task.[/bold red]")
        raise typer.Exit(code=1)

    recipients_list = [email.strip() for email in recipients_str.split(',') if email.strip()]
    if not recipients_list:
        console.print(f"[bold red]No recipients provided for the monitoring task.[/bold red]")
        raise typer.Exit(code=1)

    try:
        new_task = MonitoringList(
            id=str(uuid.uuid4()), # Generate ID for new task
            name=name,
            parts=parsed_parts,
            active=active,
            cron_schedule=schedule,
            interval_minutes=60, # Provide a default as CLI doesn't take this yet
            recipients=recipients_list,
            notify_condition=notify_condition,
            email_config_name=email_config_name,
            misfire_grace_time=misfire_grace_time
        )
    except ValidationError as e:
        console.print(f"[bold red]Validation error creating new monitoring task:\n{e}[/bold red]")
        raise typer.Exit(code=1)

    if _presets_manager.add_monitoring_list(new_task):
        console.print(f"[green]Monitoring task '{name}' (ID: {new_task.id}) added successfully.[/green]")
    else:
        console.print(f"[bold red]Failed to add monitoring task '{name}'. It might already exist or there was a save error.[/bold red]")
        raise typer.Exit(code=1)


@monitor_app.command("update")
def monitor_update_task(
    task_id: Annotated[str, typer.Argument(help="ID of the task to update.")],
    name: Annotated[Optional[str], typer.Option(help="New name for the task.")] = None,
    parts_str: Annotated[Optional[str], typer.Option(help="New parts list string. Replaces existing parts.")] = None,
    schedule: Annotated[Optional[str], typer.Option(help="New cron schedule.")] = None,
    recipients_str: Annotated[Optional[str], typer.Option(help="New recipients list string. Replaces existing.")] = None,
    active: Annotated[Optional[bool], typer.Option("--active/--inactive", help="Set task active or inactive. If not provided, status is unchanged.")] = None,
    notify_condition: Annotated[Optional[str], typer.Option(help="New notify condition ('always' or 'on_change').")] = None,
    misfire_grace_time: Annotated[Optional[int], typer.Option(help="New misfire_grace_time in seconds.")] = None
):
    """Updates an existing monitoring task."""
    assert _presets_manager 
    
    existing_task = _presets_manager.get_monitoring_list_by_id(task_id)
    if not existing_task:
        console.print(f"[bold red]Monitoring task with ID '{task_id}' not found.[/bold red]")
        raise typer.Exit(code=1)

    update_data_dict = {}
    if name is not None: update_data_dict["name"] = name
    if schedule is not None: update_data_dict["cron_schedule"] = schedule
    if active is not None: update_data_dict["active"] = active
    if notify_condition is not None: update_data_dict["notify_condition"] = notify_condition
    if misfire_grace_time is not None: update_data_dict["misfire_grace_time"] = misfire_grace_time

    if parts_str is not None:
        parsed_parts = _parse_monitoring_parts(parts_str)
        # Allow empty parts list if parts_str is explicitly empty, otherwise require valid parts if string is non-empty
        if not parsed_parts and parts_str.strip(): 
             console.print(f"[bold red]Invalid parts string provided for update: '{parts_str}'[/bold red]")
             raise typer.Exit(code=1)
        update_data_dict["parts"] = parsed_parts 
    
    if recipients_str is not None:
        recipients_list = [email.strip() for email in recipients_str.split(',') if email.strip()]
        # Allow empty recipients list if recipients_str is explicitly empty
        if not recipients_list and recipients_str.strip():
             console.print(f"[bold red]Invalid recipients string provided for update: '{recipients_str}'[/bold red]")
             raise typer.Exit(code=1)
        update_data_dict["recipients"] = recipients_list
        
    if not update_data_dict:
        console.print("No update parameters provided.")
        return

    try:
        updated_task_obj = existing_task.model_copy(update=update_data_dict)
    except ValidationError as e:
        console.print(f"[bold red]Validation error preparing task update for ID '{task_id}':\n{e}[/bold red]")
        raise typer.Exit(code=1)

    if _presets_manager.update_monitoring_list(task_id, updated_task_obj):
        console.print(f"[green]Monitoring task '{task_id}' updated successfully.[/green]")
    else:
        console.print(f"[bold red]Failed to update monitoring task '{task_id}'.[/bold red]")
        raise typer.Exit(code=1)


@monitor_app.command("delete")
def monitor_delete_task(task_id: Annotated[str, typer.Argument(help="ID of the task to delete.")]):
    """Deletes a monitoring task from presets and the scheduler."""
    assert _presets_manager
    assert _monitoring_task_manager # Ensure it's initialized

    # Attempt to remove from scheduler first.
    removed_from_scheduler = False
    try:
        if _monitoring_task_manager.remove_task(task_id):
            logger.info(f"Task '{task_id}' removed from scheduler by CLI delete command.")
            removed_from_scheduler = True
        else:
            logger.info(f"Task '{task_id}' not found in scheduler or remove_task returned False during CLI delete.")
    except Exception as e:
        logger.error(f"Error removing task '{task_id}' from scheduler during CLI delete: {e}", exc_info=True)
        console.print(f"[yellow]Warning: Encountered an issue removing task '{task_id}' from the scheduler. It will still be attempted for removal from presets.[/yellow]")

    # Then remove from presets
    if _presets_manager.delete_monitoring_list(task_id):
        console.print(f"[green]Monitoring task '{task_id}' deleted successfully from presets.[/green]")
        if not removed_from_scheduler:
             console.print(f"[yellow]Note: Task '{task_id}' was not found or not active in the scheduler, but was removed from presets.[/yellow]")
    else:
        console.print(f"[bold red]Monitoring task with ID '{task_id}' not found in presets or could not be deleted from presets.[/bold red]")
        # If it wasn't in presets, but we tried to remove from scheduler, that's okay.
        # If it was in scheduler but not presets, that's an inconsistency, but delete_monitoring_list handles the "not found".
        raise typer.Exit(code=1)

@monitor_app.command("activate")
def monitor_activate_task(task_id: Annotated[str, typer.Argument(help="ID of the task to activate.")]):
    """Activates a monitoring task."""
    assert _presets_manager
    task = _presets_manager.get_monitoring_list_by_id(task_id)
    if not task:
        console.print(f"[bold red]Task with ID '{task_id}' not found.[/bold red]")
        raise typer.Exit(code=1)
    if task.active:
        console.print(f"Task '{task.name}' (ID: {task_id}) is already active.")
        return
    
    try:
        updated_task = task.model_copy(update={"active": True})
    except ValidationError as e: # Should not happen if only 'active' is changed
        console.print(f"[bold red]Error preparing activation for task '{task_id}': {e}[/bold red]")
        raise typer.Exit(code=1)

    if _presets_manager.update_monitoring_list(task_id, updated_task):
        assert _monitoring_task_manager # Should be initialized
        try:
            if _monitoring_task_manager.activate_task(task_id):
                console.print(f"[green]Monitoring task '{task.name}' (ID: {task_id}) activated and scheduler updated.[/green]")
            else:
                # This might mean the task wasn't found in the scheduler, or MTM.activate_task had an issue
                console.print(f"[yellow]Warning: Task '{task.name}' (ID: {task_id}) activated in presets, but scheduler interaction failed or task not found in scheduler.[/yellow]")
        except Exception as e:
            logger.error(f"Error activating task {task_id} in scheduler: {e}", exc_info=True)
            console.print(f"[yellow]Warning: Task '{task.name}' (ID: {task_id}) activated in presets, but an error occurred updating the scheduler: {e}[/yellow]")
    else:
        console.print(f"[bold red]Failed to activate task '{task_id}' in presets.[/bold red]")
        raise typer.Exit(code=1)


@monitor_app.command("deactivate")
def monitor_deactivate_task(task_id: Annotated[str, typer.Argument(help="ID of the task to deactivate.")]):
    """Deactivates a monitoring task."""
    assert _presets_manager
    task = _presets_manager.get_monitoring_list_by_id(task_id)
    if not task:
        console.print(f"[bold red]Task with ID '{task_id}' not found.[/bold red]")
        raise typer.Exit(code=1)
    if not task.active:
        console.print(f"Task '{task.name}' (ID: {task_id}) is already inactive.")
        return
    try:
        updated_task = task.model_copy(update={"active": False})
    except ValidationError as e:
        console.print(f"[bold red]Error preparing deactivation for task '{task_id}': {e}[/bold red]")
        raise typer.Exit(code=1)

    if _presets_manager.update_monitoring_list(task_id, updated_task):
        assert _monitoring_task_manager # Should be initialized
        try:
            if _monitoring_task_manager.deactivate_task(task_id):
                console.print(f"[green]Monitoring task '{task.name}' (ID: {task_id}) deactivated and scheduler updated.[/green]")
            else:
                console.print(f"[yellow]Warning: Task '{task.name}' (ID: {task_id}) deactivated in presets, but scheduler interaction failed or task not found in scheduler.[/yellow]")
        except Exception as e:
            logger.error(f"Error deactivating task {task_id} in scheduler: {e}", exc_info=True)
            console.print(f"[yellow]Warning: Task '{task.name}' (ID: {task_id}) deactivated in presets, but an error occurred updating the scheduler: {e}[/yellow]")
    else:
        console.print(f"[bold red]Failed to deactivate task '{task_id}' in presets.[/bold red]")
        raise typer.Exit(code=1)


@monitor_app.command("run")
def monitor_run_task_manually(task_id: Annotated[str, typer.Argument(help="ID of the task to run manually.")]):
    """Runs a specific monitoring task manually, outside of its schedule."""
    _ensure_services_initialized(for_calculation=True, for_monitoring_run=True, for_monitoring_management=True) # Ensure MTM is available
    assert _monitoring_task_manager is not None
    assert _presets_manager is not None # Needed to get task name for message

    task = _presets_manager.get_monitoring_list_by_id(task_id)
    if not task:
        console.print(f"[bold red]Task with ID '{task_id}' not found.[/bold red]")
        raise typer.Exit(code=1)

    console.print(f"Attempting to trigger manual run for task '{task.name}' (ID: {task_id})...")
    try:
        _monitoring_task_manager.run_task_manually(task_id)
        console.print(f"[green]Manual run for task '{task.name}' (ID: {task_id}) triggered.[/green]")
    except Exception as e:
        logger.exception(f"Error during manual run of task {task_id}") # logger.exception includes traceback
        console.print(f"[bold red]Error triggering manual run for task '{task.name}' (ID: {task_id}): {e}[/bold red]")
        raise typer.Exit(code=1)

# --- Main entry point for CLI ---
if __name__ == "__main__":
    app()