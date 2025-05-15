"""
Main entry point for the Inventree Order Calculator application.

This script initializes the application components (config, API client, calculator)
and launches the command-line interface (CLI) defined using Typer.
"""
import logging

# --- Logging Setup ---
# Configure logging level and format for the CLI application
logging.basicConfig(
    level=logging.INFO, # Set default level to INFO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
logger.debug("CLI __main__ script started.") # Debug message to confirm logger works

# Import the Typer application object from the cli module
# The cli module itself handles loading config, creating clients/calculators
# when its main command is invoked. This entry point just needs to run the app.
from .cli import app

def run():
    """Runs the Typer CLI application."""
    # Typer handles the rest: argument parsing, command execution,
    # error handling (based on the implementation in cli.py)
    app()

if __name__ == "__main__":
    run()