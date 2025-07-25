# Module: src/inventree_order_calculator/config.py
# Description: Handles loading configuration from environment variables.

# Dependencies: python-dotenv, os

// Import necessary libraries
IMPORT load_dotenv from dotenv
IMPORT os

// Define a class or functions to hold configuration settings
CLASS Configuration:
    // Attributes to store configuration values
    ATTRIBUTE inventree_api_url: STRING | NONE = NONE
    ATTRIBUTE inventree_api_token: STRING | NONE = NONE

    // Method to load configuration from environment variables
    FUNCTION load_config():
        // Load environment variables from a .env file if it exists
        // This is useful for local development
        load_dotenv()

        // Read InvenTree API URL from environment variable 'INVENTREE_API_URL'
        self.inventree_api_url = os.getenv('INVENTREE_API_URL')
        // TEST: Loading INVENTREE_API_URL from environment

        // Read InvenTree API Token from environment variable 'INVENTREE_API_TOKEN'
        self.inventree_api_token = os.getenv('INVENTREE_API_TOKEN')
        // TEST: Loading INVENTREE_API_TOKEN from environment

        // Validate that required configuration values are present
        IF self.inventree_api_url IS NONE:
            RAISE ConfigurationError("Environment variable 'INVENTREE_API_URL' is not set.")
            // TEST: Error handling when INVENTREE_API_URL is missing
        ENDIF

        IF self.inventree_api_token IS NONE:
            RAISE ConfigurationError("Environment variable 'INVENTREE_API_TOKEN' is not set.")
            // TEST: Error handling when INVENTREE_API_TOKEN is missing
        ENDIF

    // Constructor to automatically load config on instantiation
    CONSTRUCTOR __init__():
        CALL self.load_config()

// Function to get a configuration instance (singleton pattern might be useful)
FUNCTION get_config(): Configuration
    // Create and return a Configuration instance
    RETURN Configuration()

// Define custom exception for configuration errors
CLASS ConfigurationError(Exception):
    PASS