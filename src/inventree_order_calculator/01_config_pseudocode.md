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

    // Email Configuration Attributes
    ATTRIBUTE email_smtp_server: STRING | NONE = NONE
    ATTRIBUTE email_smtp_port: INTEGER | NONE = NONE
    ATTRIBUTE email_use_tls: BOOLEAN = FALSE
    ATTRIBUTE email_use_ssl: BOOLEAN = FALSE
    ATTRIBUTE email_username: STRING | NONE = NONE
    ATTRIBUTE email_password: STRING | NONE = NONE // Sensitive
    ATTRIBUTE email_sender_address: STRING | NONE = NONE
    ATTRIBUTE admin_email_recipients: LIST[STRING] = []

    // Global Notification Switch
    ATTRIBUTE global_email_notifications_enabled: BOOLEAN = TRUE


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

        // Validate that required InvenTree configuration values are present
        IF self.inventree_api_url IS NONE:
            RAISE ConfigurationError("Environment variable 'INVENTREE_API_URL' is not set.")
            // TEST: Error handling when INVENTREE_API_URL is missing
        ENDIF

        IF self.inventree_api_token IS NONE:
            RAISE ConfigurationError("Environment variable 'INVENTREE_API_TOKEN' is not set.")
            // TEST: Error handling when INVENTREE_API_TOKEN is missing
        ENDIF

        // Load Email Configuration
        self.email_smtp_server = os.getenv('EMAIL_SMTP_SERVER')
        // TEST: email_config_loads_EMAIL_SMTP_SERVER

        port_str = os.getenv('EMAIL_SMTP_PORT')
        IF port_str IS NOT NONE AND port_str.isdigit():
            self.email_smtp_port = INTEGER(port_str)
        ELSE IF port_str IS NOT NONE:
            LOG_WARNING("Invalid EMAIL_SMTP_PORT value: " + port_str + ". Expected an integer.")
            self.email_smtp_port = NONE // Or a default, or raise error if mandatory
        // TEST: email_config_loads_EMAIL_SMTP_PORT
        // TEST: email_config_handles_invalid_EMAIL_SMTP_PORT

        self.email_use_tls = os.getenv('EMAIL_USE_TLS', 'false').lower() == 'true'
        // TEST: email_config_loads_EMAIL_USE_TLS

        self.email_use_ssl = os.getenv('EMAIL_USE_SSL', 'false').lower() == 'true'
        // TEST: email_config_loads_EMAIL_USE_SSL

        self.email_username = os.getenv('EMAIL_USERNAME')
        // TEST: email_config_loads_EMAIL_USERNAME

        self.email_password = os.getenv('EMAIL_PASSWORD') // Sensitive, handle with care
        // TEST: email_config_loads_EMAIL_PASSWORD

        self.email_sender_address = os.getenv('EMAIL_SENDER_ADDRESS')
        // TEST: email_config_loads_EMAIL_SENDER_ADDRESS

        admin_recipients_str = os.getenv('ADMIN_EMAIL_RECIPIENTS', '')
        IF admin_recipients_str:
            self.admin_email_recipients = [email.strip() FOR email IN admin_recipients_str.split(',') IF email.strip()]
        ELSE:
            self.admin_email_recipients = []
        // TEST: email_config_loads_ADMIN_EMAIL_RECIPIENTS_comma_separated
        // TEST: email_config_handles_empty_ADMIN_EMAIL_RECIPIENTS

        // Load Global Notification Switch
        self.global_email_notifications_enabled = os.getenv('GLOBAL_EMAIL_NOTIFICATIONS_ENABLED', 'true').lower() == 'true'
        // TEST: config_loads_GLOBAL_EMAIL_NOTIFICATIONS_ENABLED_true
        // TEST: config_loads_GLOBAL_EMAIL_NOTIFICATIONS_ENABLED_false
        // TEST: config_defaults_GLOBAL_EMAIL_NOTIFICATIONS_ENABLED_to_true_if_not_set

        // Optional: Validate required email configuration if email notifications are globally enabled
        // This depends on whether email is a "must-have" or "optional" feature part.
        // For now, assume individual services will check for necessary configs.
        // Example validation (if SMTP server is always required for the feature to be considered 'on'):
        // IF self.global_email_notifications_enabled AND self.email_smtp_server IS NONE:
        //     RAISE ConfigurationError("Email notifications are enabled, but 'EMAIL_SMTP_SERVER' is not set.")
        // ENDIF


    // Constructor to automatically load config on instantiation
    CONSTRUCTOR __init__():
        CALL self.load_config()

// Function to get a configuration instance (singleton pattern might be useful)
// Ensure this returns the SAME instance if called multiple times.
PRIVATE static_config_instance: Configuration | NONE = NONE

FUNCTION get_config(): Configuration
    IF static_config_instance IS NONE:
        static_config_instance = Configuration()
    ENDIF
    RETURN static_config_instance

// Define custom exception for configuration errors
CLASS ConfigurationError(Exception):
    PASS