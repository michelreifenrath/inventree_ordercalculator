import typer
from rich.console import Console
from rich.table import Table
from typing import List, Dict, Optional
from typing_extensions import Annotated # Use typing_extensions for older Python versions if needed
from decimal import Decimal

# --- Dependencies (will be mocked in tests) ---
# Assume these modules/classes exist and are importable
# In a real scenario, ensure they are correctly implemented and tested elsewhere.
try:
    from .config import AppConfig, ConfigError
    from .api_client import ApiClient
    from .calculator import OrderCalculator
    # Import models if needed for type hinting
    from .models import InputPart # Import InputPart
except ImportError:
    # Define dummy classes if imports fail (e.g., during isolated testing setup)
    # This helps basic script parsing but won't work for actual execution.
    class ConfigError(Exception): pass
    class AppConfig:
        def __init__(self, inventree_url, inventree_api_token): pass
        @classmethod
        def load(cls): return cls("dummy_url", "dummy_token")
    class ApiClient:
        def __init__(self, config): pass
    class OrderCalculator:
        def __init__(self, client): pass
        def calculate_order(self, parts: Dict[str, int]):
            return {"required_parts": [], "total_cost": Decimal("0.00")}
# --- End Dependencies ---


app = typer.Typer(help="Inventree Order Calculator CLI")
console = Console()

def parse_parts_input(parts_list: List[str]) -> List[InputPart]:
    """Parses the list of 'PART:QUANTITY' strings into a list of InputPart objects."""
    parsed_parts: List[InputPart] = []
    for part_str in parts_list:
        part_num = "" # Initialize part_num here
        quantity_str = "" # Initialize quantity_str here
        if ":" not in part_str:
            console.print(f"[bold red]Error:[/bold red] Invalid format for part '{part_str}'. Expected format: PART_IDENTIFIER:QUANTITY")
            raise typer.Exit(code=1)
        try:
            part_num, quantity_str = part_str.split(":", 1)
            quantity = float(quantity_str) # Convert to float for InputPart
            if quantity <= 0:
                 console.print(f"[bold red]Error:[/bold red] Quantity for part '{part_num}' must be positive.")
                 raise typer.Exit(code=1)
            # Create InputPart object and add to list
            parsed_parts.append(InputPart(part_identifier=part_num.strip(), quantity_to_build=quantity))
        except ValueError:
            # Ensure part_num is defined even if split fails before quantity conversion
            if ":" in part_str:
                part_num, _ = part_str.split(":", 1)
            console.print(f"[bold red]Error:[/bold red] Invalid quantity for part '{part_num}'. '{quantity_str}' is not a valid number.")
            raise typer.Exit(code=1)
        except Exception as e: # Catch other potential split errors etc.
             console.print(f"[bold red]Error:[/bold red] Could not parse '{part_str}': {e}")
             raise typer.Exit(code=1)
    return parsed_parts

@app.command()
def main(
    parts: Annotated[List[str], typer.Argument(help="List of parts to order in format PART_IDENTIFIER:QUANTITY")],
    hide_consumables: Annotated[bool, typer.Option("--hide-consumables", help="Hide consumable parts from the output tables.")] = False,
    hide_haip_parts: Annotated[bool, typer.Option("--hide-haip-parts", help="Hide parts supplied by HAIP Solutions GmbH.")] = False,
):
    """
    Calculates the required components and total cost for a list of top-level parts based on Inventree BOMs.
    """
    console.print("[bold blue]Inventree Order Calculator[/bold blue]")

    try:
        input_parts_list = parse_parts_input(parts) # Renamed variable
        if not input_parts_list:
             console.print("[bold yellow]Warning:[/bold yellow] No valid parts provided.")
             raise typer.Exit()

        console.print("Loading configuration...")
        # --- Dependency Injection / Setup ---
        # In a real app, you'd load config and instantiate real objects here.
        # Tests mock these out.
        config = AppConfig.load() # Mocked in tests
        api_client = ApiClient(url=config.inventree_url, token=config.inventree_api_token) # Mocked in tests
        calculator = OrderCalculator(api_client) # Mocked in tests
        # --- End Setup ---

        # Update print statement to use the list of InputPart objects
        console.print(f"Calculating order for: {', '.join(f'{ip.part_identifier}:{ip.quantity_to_build}' for ip in input_parts_list)}")
        result = calculator.calculate_orders(input_parts_list) # Pass the list of InputPart objects

        if hide_consumables:
            console.print("[italic]Hiding consumable parts from output.[/italic]")
            result.parts_to_order = [p for p in result.parts_to_order if not p.is_consumable]
            result.subassemblies_to_build = [a for a in result.subassemblies_to_build if not a.is_consumable]

        if hide_haip_parts:
            console.print("[italic]Hiding parts supplied by HAIP Solutions GmbH from output.[/italic]")
            result.parts_to_order = [p for p in result.parts_to_order if "HAIP Solutions GmbH" not in p.supplier_names]
            # For assemblies, the supplier is of the assembly itself, not its components.
            # If an assembly part itself is supplied by HAIP, it should be hidden.
            result.subassemblies_to_build = [a for a in result.subassemblies_to_build if "HAIP Solutions GmbH" not in a.supplier_names]

        # --- Output Formatting ---
        # Access the lists directly from the OutputTables object
        parts_to_order = result.parts_to_order
        subassemblies_to_build = result.subassemblies_to_build # Get the list

        # --- Parts to Order Table ---
        if not parts_to_order:
            console.print("[yellow]No parts need to be ordered based on calculation.[/yellow]")
        else:
            parts_table = Table(title="Parts to Order", show_header=True, header_style="bold magenta")
            parts_table.add_column("Part ID", justify="right")
            parts_table.add_column("Optional", justify="center", style="dim")
            parts_table.add_column("Part Name", style="dim", width=30)
            parts_table.add_column("Needed", justify="right")
            parts_table.add_column("Total In Stock", justify="right")
            # Reordered columns: Moved 'On Order' after 'Available'
            parts_table.add_column("Required for Build Orders", justify="right")
            parts_table.add_column("Required for Sales Orders", justify="right")
            parts_table.add_column("Available", justify="right")
            # Moved 'To Order' before 'On Order'
            parts_table.add_column("To Order", justify="right", style="bold red")
            parts_table.add_column("On Order", justify="right") # 'ordering' field
            parts_table.add_column("Gehört zu", style="dim", width=25) # New column

            for item in parts_to_order:
                # Access attributes directly from the CalculatedPart object (item)
                part_pk = getattr(item, 'pk', None)
                part_name = getattr(item, 'name', 'N/A')
                total_in_stock = getattr(item, 'total_in_stock', 0.0)
                ordering = getattr(item, 'ordering', 0.0)
                req_build = getattr(item, 'required_for_build_orders', 0.0)
                req_sales = getattr(item, 'required_for_sales_orders', 0.0)
                total_required = getattr(item, 'total_required', 0.0)

                display_name = part_name
                if config.inventree_instance_url and part_pk is not None:
                    link_url = f"{config.inventree_instance_url.rstrip('/')}/part/{part_pk}/"
                    display_name = f"[link={link_url}]{part_name}[/link]"

                # Get optional status and format as ✓/✗
                optional_status = "✓" if getattr(item, 'is_optional', False) else "✗"

                parts_table.add_row(
                    str(part_pk) if part_pk is not None else 'N/A',
                    optional_status,
                    display_name,
                    f"{total_required:.2f}",
                    f"{total_in_stock:.2f}",
                    # Reordered data to match new column order
                    f"{req_build:.2f}",
                    f"{req_sales:.2f}",
                    f"{getattr(item, 'available', 0.0):.2f}",
                    # Moved 'to_order' data before 'ordering' data
                    f"{getattr(item, 'to_order', 0.0):.2f}",
                    f"{ordering:.2f}",
                    ", ".join(sorted(list(getattr(item, 'belongs_to_top_parts', set())))), # Populate new column
                )
            console.print(parts_table)

        # --- Subassemblies to Build Table ---
        if not subassemblies_to_build:
            console.print("[yellow]No subassemblies need to be built based on calculation.[/yellow]")
        else:
            build_table = Table(title="Subassemblies to Build", show_header=True, header_style="bold cyan")
            # Define columns in the new order
            build_table.add_column("Part ID", justify="right")
            build_table.add_column("Optional", justify="center", style="dim")
            build_table.add_column("Part Name", style="dim", width=30)
            build_table.add_column("Needed", justify="right")
            build_table.add_column("Total In Stock", justify="right")
            build_table.add_column("Required for Build Orders", justify="right")
            build_table.add_column("Required for Sales Orders", justify="right")
            build_table.add_column("Available", justify="right")
            build_table.add_column("In Production", justify="right") # 'building' field
            build_table.add_column("To Build", justify="right", style="bold blue")
            build_table.add_column("Gehört zu", style="dim", width=25) # New column

            for item in subassemblies_to_build:
                 # Access attributes directly from the CalculatedPart object (item)
                part_pk = getattr(item, 'pk', None)
                part_name = getattr(item, 'name', 'N/A')
                total_in_stock = getattr(item, 'total_in_stock', 0.0)
                building = getattr(item, 'building', 0.0) # Use 'building' here
                req_build = getattr(item, 'required_for_build_orders', 0.0)
                req_sales = getattr(item, 'required_for_sales_orders', 0.0)
                available = getattr(item, 'available', 0.0)
                to_build = getattr(item, 'to_build', 0.0)
                total_required = getattr(item, 'total_required', 0.0)

                display_name = part_name
                if config.inventree_instance_url and part_pk is not None:
                    link_url = f"{config.inventree_instance_url.rstrip('/')}/part/{part_pk}/"
                    display_name = f"[link={link_url}]{part_name}[/link]"

                # Get optional status and format as ✓/✗
                optional_status = "✓" if getattr(item, 'is_optional', False) else "✗"

                # Add row data in the new order
                build_table.add_row(
                    str(part_pk) if part_pk is not None else 'N/A',
                    optional_status,
                    display_name,
                    f"{total_required:.2f}",
                    f"{total_in_stock:.2f}",
                    f"{req_build:.2f}",
                    f"{req_sales:.2f}",
                    f"{available:.2f}",
                    f"{building:.2f}", # In Production data
                    f"{to_build:.2f}", # To Build data
                    ", ".join(sorted(list(getattr(item, 'belongs_to_top_parts', set())))), # Populate new column
                )
            console.print(build_table)

    except ConfigError as e:
        console.print(f"[bold red]Configuration Error:[/bold red] {e}")
        raise typer.Exit(code=1)
    except ValueError as e: # Catch calculation errors propagated
        console.print(f"[bold red]Error during calculation:[/bold red] {e}")
        raise typer.Exit(code=1)
    except Exception as e: # Catch unexpected errors
        console.print(f"[bold red]An unexpected error occurred:[/bold red] {e}")
        # Consider logging the full traceback here for debugging
        # import traceback
        # console.print(traceback.format_exc())
        raise typer.Exit(code=1)


# Allow running the script directly for basic checks (though tests are better)
# if __name__ == "__main__":
#     app()