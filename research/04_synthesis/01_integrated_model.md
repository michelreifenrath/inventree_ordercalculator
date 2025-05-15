# Synthesis: Integrated Model for Automated Monitoring & Notification

This document presents an integrated conceptual model for the "Automated Parts List Monitoring and Email Notification" feature, synthesizing the findings from the research and analysis phases. It outlines the core components, their interactions, and key architectural considerations.

## I. Core Components and Responsibilities

The system will be built around two new primary services, supported by existing and modified modules:

1.  **`MonitoringService`**:
    *   **Responsibilities**:
        *   Manages the lifecycle of monitoring tasks (defined in [`presets.json`](presets.json)).
        *   Schedules and triggers periodic checks based on individual cron schedules using `APScheduler` (initially, in-process).
        *   For each triggered task:
            *   Retrieves parts list and parameters from `PresetsManager`.
            *   Invokes the `Calculator` to perform the availability check.
            *   Handles the `on_change` notification logic:
                *   Serializes the relevant parts of the `Calculator` result (Fehlmengenliste, kritische Teile) into a canonical JSON string.
                *   Computes a hash (SHA256) of this string.
                *   Compares with `last_hash` stored for the task (via `PresetsManager`).
            *   If a notification is warranted (due to `notify_condition == "always"` or `on_change` with hash mismatch):
                *   Notifies registered observers (e.g., `EmailNotificationObserver`) with the task details and calculation results.
                *   If `on_change` and notified, updates `last_hash` for the task via `PresetsManager`.
        *   Handles errors during task execution (API errors, calculation errors) with retry logic (`tenacity`) and admin notifications for persistent issues.
    *   **Key Dependencies**: `APScheduler`, `PresetsManager`, `Calculator`, `Config`, `NotificationDispatcher` (Observer pattern subject).

2.  **`EmailService`** (or more generally, part of a notification subsystem):
    *   **Responsibilities**:
        *   Receives notification requests (containing task details and calculation results) from the `MonitoringService` (likely via an `EmailNotificationObserver`).
        *   Generates email content:
            *   Uses `Jinja2` templates for both HTML and plain-text versions.
            *   Populates templates with data from the calculation result.
            *   Uses `premailer` to inline CSS for HTML emails.
        *   Sends emails:
            *   Uses `smtplib` for SMTP communication.
            *   Retrieves SMTP configuration (`EMAIL_SMTP_SERVER`, credentials, etc.) from `Config` (sourced from environment variables).
            *   Implements secure connection protocols (TLS/SSL).
            *   Handles email sending errors with retry logic (`tenacity`) and admin notifications for persistent failures.
        *   Checks `GLOBAL_EMAIL_NOTIFICATIONS_ENABLED` flag from `Config` before sending.
    *   **Key Dependencies**: `Jinja2`, `premailer`, `smtplib`, `Config`, `tenacity`.

3.  **`NotificationDispatcher` (Conceptual - Observer Pattern Subject)**:
    *   **Responsibilities**:
        *   Manages a list of observers (e.g., `EmailNotificationObserver`, potentially `SlackNotificationObserver` in the future).
        *   When `MonitoringService` detects a need for notification, it calls `NotificationDispatcher.notify()`.
        *   The dispatcher then calls the `update()` method on all registered observers, passing the necessary data.
    *   This component formalizes the Observer pattern for decoupling `MonitoringService` from specific notification mechanisms.

## II. Supporting Modules (Existing/Modified)

1.  **`PresetsManager`**:
    *   Extended to store and manage `monitoring_lists` within [`presets.json`](presets.json) as per the specification.
    *   Provides CRUD operations for these lists, accessible by both CLI and Streamlit UI.
    *   Handles loading and saving of `last_hash` for each monitoring task.
    *   Ensures reasonably atomic writes to `presets.json`.

2.  **`Calculator`**:
    *   Existing logic is used to perform the parts availability check.
    *   Its output (specifically "Fehlmengenliste" and "kritische Teile") must be clearly defined and consistently structured to enable reliable serialization and hashing for the `on_change` logic.

3.  **`Config`**:
    *   Extended to manage email SMTP configurations and the `GLOBAL_EMAIL_NOTIFICATIONS_ENABLED` flag, loaded from environment variables / `.env` file.
    *   Provides these configurations to `EmailService` and potentially `MonitoringService`.

4.  **CLI Module (e.g., using `Typer`)**:
    *   Extended with `monitor` subcommands (`list`, `add`, `update`, `delete`, `activate`, `deactivate`, `run`) as specified.
    *   Interacts with `PresetsManager` for CRUD and activation.
    *   Interacts with `MonitoringService` (or an interface to it) for manual `run` and potentially for querying dynamic task status.

5.  **Streamlit UI Module**:
    *   New section for managing monitoring tasks, mirroring CLI functionality.
    *   Uses Streamlit forms for input (including cron strings, parts lists, recipients).
    *   Displays task lists and their status (static from `PresetsManager`, dynamic potentially queried from `MonitoringService`).
    *   Relies on `PresetsManager` and potentially an interface to `MonitoringService`.

## III. Key Architectural Principles & Patterns

*   **Dependency Injection**: Core services (`MonitoringService`, `EmailService`) will receive their dependencies (other services, managers, config objects) upon instantiation.
*   **Observer Pattern**: For notifications, decoupling `MonitoringService` (event source) from `EmailService` and other potential notifiers (event listeners).
*   **Strategy Pattern**: Potentially for different calculation types within `Calculator` or different notification channels if complexity grows.
*   **Layered Error Handling**: Each component handles its own errors; `MonitoringService` orchestrates retries and escalations for tasks. `tenacity` will be used for retry logic.
*   **Structured Logging**: `logging` module + `structlog` for comprehensive, machine-readable logs across all components.
*   **Configuration First**: Secure and flexible configuration via environment variables (`python-dotenv`) and `Config` objects.
*   **Security by Design**:
    *   Secure credential management.
    *   Input validation (cron strings, email data).
    *   Output escaping/sanitization for HTML emails (Jinja2 autoescape, `bleach`).

## IV. Data Flow for a Monitoring Check

1.  `APScheduler` (managed by `MonitoringService`) triggers a scheduled job for a specific `task_id`.
2.  `MonitoringService` retrieves the task configuration (parts, recipients, `notify_condition`, `last_hash`) from `PresetsManager`.
3.  `MonitoringService` calls `Calculator` with the task's parts list.
4.  `Calculator` performs the check and returns results (including Fehlmengenliste, kritische Teile).
5.  `MonitoringService` serializes relevant parts of the result and computes a `current_hash`.
6.  **If `notify_condition == "always"` OR (`notify_condition == "on_change"` AND `current_hash != last_hash`):**
    a.  `MonitoringService` calls `NotificationDispatcher.notify(task_details, calculation_results)`.
    b.  `NotificationDispatcher` calls `EmailNotificationObserver.update()`.
    c.  `EmailNotificationObserver` (which holds/gets an `EmailService` instance) instructs `EmailService` to prepare and send the email.
    d.  `EmailService` generates HTML/text content using `Jinja2` and `premailer`.
    e.  `EmailService` sends the email via SMTP, handling retries.
    f.  If email sent successfully and `on_change` was the trigger, `MonitoringService` updates `last_hash` for the task via `PresetsManager`.
7.  Errors at any stage are logged; persistent errors trigger admin notifications (via `EmailService` if possible, or other means).

## V. Scalability Path

*   **Phase 1 (Current Scope):** `MonitoringService` runs `APScheduler` in-process. Suitable for moderate task loads.
*   **Phase 2 (Future):** If needed, transition to `Celery` for distributed task execution.
    *   `MonitoringService` becomes a task producer, submitting jobs to Celery.
    *   `celery beat` handles scheduling.
    *   Celery workers execute the checks.
    *   Requires a message broker (Redis/RabbitMQ).

This integrated model provides a modular, testable, and extensible framework for the automated monitoring feature, aligning with the project's specifications and Python best practices.