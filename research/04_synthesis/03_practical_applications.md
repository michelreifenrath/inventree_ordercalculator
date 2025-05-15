# Synthesis: Practical Applications and Implementation Strategies

This document outlines practical applications of the research findings and suggests concrete implementation strategies for the "Automated Parts List Monitoring and Email Notification" feature. It builds upon the integrated model and key recommendations.

## I. Core Service Implementation Strategy

1.  **`MonitoringService` Implementation:**
    *   **Initialization:** Instantiate with `APScheduler.BackgroundScheduler`, and injected instances of `PresetsManager`, `Calculator`, `Config`, and a `NotificationDispatcher`.
    *   **Startup (`start()` method):**
        *   Load all monitoring task configurations from `PresetsManager`.
        *   For each active task, parse its `cron_schedule` (validate with `croniter`).
        *   Add a job to `APScheduler` for each valid, active task. The job should call a method like `MonitoringService._execute_check(task_id)`. Store references to `APScheduler` job objects if needed for dynamic management (e.g., pausing, resuming, though `PresetsManager`'s `active` flag is primary).
        *   Start the `APScheduler` instance.
    *   **Check Execution (`_execute_check(task_id)` method):**
        *   Retrieve full task details from `PresetsManager` using `task_id`.
        *   Invoke `self.calculator.calculate_availability(task_config['parts'])` (or similar). Wrap in `try-except` for calculation errors.
        *   Implement `on_change` logic:
            *   Serialize relevant calculation results (Fehlmengenliste, kritische Teile) to a canonical JSON string.
            *   Compute SHA256 hash (`current_hash`).
            *   Compare with `task_config['last_hash']`.
        *   If notification is needed: `self.notification_dispatcher.notify(task_config, calc_results, current_hash)`.
    *   **Error Handling:** Use `tenacity` decorators for retrying InvenTree API calls within the `Calculator` if it doesn't already have such logic, or within `_execute_check` if API calls are made directly. Log all errors extensively.

2.  **`EmailService` Implementation:**
    *   **Initialization:** Instantiate with `Config` (for SMTP settings) and a `Jinja2.Environment` (configured to load templates from a `templates/` directory).
    *   **Email Generation (`generate_report_email` method):**
        *   Accepts `task_config`, `calculation_results`.
        *   Renders HTML (`email_report.html`) and plain-text (`email_report.txt`) templates using Jinja2.
        *   Uses `premailer` on the HTML output.
        *   Constructs a `MIMEMultipart("alternative")` email message with both parts.
    *   **Sending (`send_email` method):**
        *   Accepts recipient list, subject, and the `MIMEMultipart` message.
        *   Checks `GLOBAL_EMAIL_NOTIFICATIONS_ENABLED` from `Config`.
        *   Connects to SMTP server using `smtplib` (handling TLS/SSL based on `Config`).
        *   Authenticates and sends the email.
        *   Wrap sending logic with `tenacity` for retries.
        *   Log success/failure. If persistent failure, notify admins (this might involve calling itself with admin recipients and a different template, or a simpler text-only alert if the primary templating/sending is failing).

3.  **`NotificationDispatcher` and Observers:**
    *   Implement a simple `NotificationDispatcher` class with `attach(observer)` and `notify(task_config, calc_results, current_hash)` methods.
    *   Create an `EmailNotificationObserver` class:
        *   Takes an `EmailService` instance in its constructor.
        *   Its `update(task_config, calc_results, current_hash)` method will:
            *   Call `email_service.generate_report_email(...)` and then `email_service.send_email(...)`.
            *   If the email is sent successfully due to an `on_change` condition, it should then instruct `PresetsManager` (perhaps via a callback or by returning a status to `MonitoringService`) to update `last_hash` for the `task_config['id']` with `current_hash`.

## II. Integration with Existing Modules

1.  **`PresetsManager` Enhancements:**
    *   Add methods to load, save, update, and delete `monitoring_lists` objects in `presets.json`.
    *   Ensure schema validation (perhaps using `Pydantic` models internally) when loading/saving monitoring list data.
    *   Method to update `last_hash` for a specific task ID.
    *   Ensure file writes are atomic (e.g., write to temp file, then rename).
2.  **`Calculator` Interface:**
    *   Confirm the `Calculator` provides a clear method to get the "Fehlmengenliste" and "kritische Teile" in a consistent, serializable format. If not, refactor or add a specific method for this.

3.  **`Config` Enhancements:**
    *   Add new environment variables and corresponding attributes in `Config` for: `EMAIL_SMTP_SERVER`, `EMAIL_SMTP_PORT`, `EMAIL_USE_TLS`, `EMAIL_USE_SSL`, `EMAIL_USERNAME`, `EMAIL_PASSWORD`, `EMAIL_SENDER_ADDRESS`, `ADMIN_EMAIL_RECIPIENTS`, `GLOBAL_EMAIL_NOTIFICATIONS_ENABLED`.

## III. CLI and UI Implementation Strategy

1.  **CLI (`Typer`):**
    *   Create a new subcommand group, e.g., `app.add_typer(monitor_app, name="monitor")`.
    *   Implement each command (`list`, `add`, `update`, etc.) as specified in [`docs/feature_specs/automated_monitoring_spec.md`](docs/feature_specs/automated_monitoring_spec.md:1).
    *   CLI commands for CRUD and activation/deactivation will primarily call methods on an instance of `PresetsManager`.
    *   The `monitor run <task_id>` command will need to interface with a running `MonitoringService` instance or trigger a one-off execution path that uses the same core logic. (This interaction needs careful design: e.g., if `MonitoringService` runs in a daemon, CLI might use IPC or an API. If it's part of the CLI process itself for `run`, it instantiates necessary components).

2.  **Streamlit UI:**
    *   Create a new page/section in the Streamlit app for "Monitoring Tasks."
    *   **Display:** Use `st.dataframe` to show tasks from `PresetsManager.load_monitoring_lists()`. Include columns for status, and buttons for "Edit," "Delete," "Run Now."
    *   **Forms (`st.form`):**
        *   For adding/editing tasks.
        *   `st.text_input` for name, cron schedule (with `croniter` validation on submit).
        *   `st.multiselect` or `st.text_area` for recipients.
        *   `st.radio` for `notify_condition`.
        *   `st.checkbox` for `active` status.
        *   **Parts List Input:** Start with `st.text_area` expecting a simple format (e.g., `PartName1:Qty1, PartName2:Qty2`). Parse and validate this string on form submission. A `st.file_uploader` for CSV/JSON is a good alternative for more complex lists.
    *   **Actions:** Buttons in the UI will call corresponding `PresetsManager` methods. "Run Now" would need to interact with the `MonitoringService` similar to the CLI.
    *   **Dynamic Status:** For `last_run_time`, `next_run_time`, initially, these might only update on a full page refresh or via a manual "Refresh Status" button that queries the `MonitoringService` (if accessible).

## IV. Startup and Service Management

*   **Main Application Entry Point (e.g., `main.py` or `streamlit_app.py`):**
    *   If the `MonitoringService` is to run continuously in the background when the main application (e.g., Streamlit app or a dedicated daemon mode for CLI) starts:
        *   Instantiate `Config`, `PresetsManager`, `Calculator`, `EmailService`, `NotificationDispatcher`, and then `MonitoringService`.
        *   Call `monitoring_service.start()`.
        *   Ensure graceful shutdown: when the main application exits, `monitoring_service.scheduler.shutdown()` should be called.
*   **CLI `monitor run`:** This command might instantiate a temporary `MonitoringService` (or just the core check logic) to execute a single task without starting the full scheduler.

## V. Logging and Error Handling Implementation

*   Configure `logging` (and `structlog`) early in the application startup. Define handlers (file, console) and formatters.
*   Apply `tenacity` decorators to relevant functions in `EmailService` (sending) and `Calculator` or `MonitoringService` (API calls).
*   Implement a central admin notification function that `EmailService` can use to alert `ADMIN_EMAIL_RECIPIENTS` about critical system errors (e.g., persistent email failure, critical config error).

## VI. Security Implementation

*   Ensure `.env` is in `.gitignore`.
*   Use `os.getenv()` for all credential access.
*   Implement `croniter` validation for all cron string inputs.
*   Use Jinja2's default autoescaping for HTML emails. If any user-generated HTML were to be included (not in current spec), use `bleach.clean()`.

This phased implementation, starting with core services and gradually building CLI/UI and robust error handling, should lead to a successful feature deployment. Prioritize clear interfaces between components.