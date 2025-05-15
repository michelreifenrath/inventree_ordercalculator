# Module: src/inventree_order_calculator/__main__.py (or similar entry point)
# Description: Main entry point for the application.

# Dependencies: cli module

// Import the Typer application instance from the cli module
IMPORT app from .cli

// Define the main execution block
FUNCTION run_app():
    // Run the Typer application
    app()

// Standard Python entry point check
IF __name__ == "__main__":
    CALL run_app()