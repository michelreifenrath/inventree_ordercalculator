# Pseudocode: Monitoring Service (`08_monitoring_service_pseudocode.md`)

This document outlines the pseudocode for the automated monitoring service.

## 1. Core Components

*   **Scheduler:** Manages and triggers monitoring tasks based on their cron schedules. (Uses APScheduler)
*   **Task Executor:** Executes a single monitoring task, including fetching data, calculation, and initiating notification.
*   **Monitoring Task Manager:** Interfaces with `PresetsManager` to load and manage monitoring task configurations.

## 2. Global Variables / Configuration

```pseudocode
GLOBAL_EMAIL_NOTIFICATIONS_ENABLED // boolean, loaded from environment variable
ADMIN_EMAIL_RECIPIENTS // list of strings, loaded from environment variable
```

## 3. Scheduler Module

```pseudocode
MODULE Scheduler

  PRIVATE scheduler_instance // APScheduler instance

  FUNCTION initialize_scheduler():
    // TEST: scheduler_initializes_apscheduler_instance
    SET scheduler_instance = new APScheduler()
    load_and_schedule_all_active_tasks()
    scheduler_instance.start()
    LOG "Scheduler initialized and started."

  FUNCTION load_and_schedule_all_active_tasks():
    // TEST: scheduler_loads_and_schedules_active_tasks_on_startup
    tasks = MonitoringTaskManager.get_all_active_monitoring_tasks()
    FOR EACH task IN tasks:
      schedule_task(task)
    ENDFOR

  FUNCTION schedule_task(task_config):
    // TEST: scheduler_adds_new_task_correctly
    // TEST: scheduler_updates_existing_task_schedule
    // TEST: scheduler_rejects_task_with_invalid_cron_schedule (handled by validation before this point)
    IF task_config.active IS TRUE:
      TRY
        scheduler_instance.add_job(
          TaskExecutor.run_monitoring_task,
          trigger='cron',
          args=[task_config.id],
          id=task_config.id,
          name=task_config.name,
          replace_existing=TRUE,
          // Cron parsing from task_config.cron_schedule
          // e.g., minute=cron_parts[0], hour=cron_parts[1], ...
          // This needs robust parsing of the cron string.
          // APScheduler handles cron parsing directly if provided as a string.
          cron_schedule_to_apscheduler_format(task_config.cron_schedule)
        )
        LOG "Scheduled task: " + task_config.name + " with ID: " + task_config.id
      CATCH InvalidCronExpressionError as e:
        LOG_ERROR "Invalid cron schedule for task " + task_config.id + ": " + task_config.cron_schedule + ". Error: " + e.message
        // Optionally, notify admin or mark task as invalid
        MonitoringTaskManager.deactivate_task(task_config.id) // Example of handling
        EmailService.send_admin_notification("Invalid Cron Schedule", "Task " + task_config.name + " (" + task_config.id + ") deactivated due to invalid cron: " + task_config.cron_schedule)
      ENDTRY
    ELSE:
      remove_task(task_config.id) // Ensure inactive tasks are not scheduled
    ENDIF

  FUNCTION remove_task(task_id):
    // TEST: scheduler_removes_task_correctly
    TRY
      scheduler_instance.remove_job(task_id)
      LOG "Removed task from scheduler: " + task_id
    CATCH JobLookupError:
      LOG_WARNING "Task " + task_id + " not found in scheduler for removal, might have already been removed or never scheduled."
    ENDTRY

  FUNCTION shutdown_scheduler():
    // TEST: scheduler_shuts_down_cleanly
    IF scheduler_instance AND scheduler_instance.running:
      scheduler_instance.shutdown()
      LOG "Scheduler shut down."
    ENDIF

  FUNCTION get_scheduled_jobs_info():
    // TEST: scheduler_can_list_scheduled_jobs
    IF scheduler_instance:
      RETURN scheduler_instance.get_jobs() // Returns list of job objects
    ELSE:
      RETURN []
    ENDIF

  PRIVATE FUNCTION cron_schedule_to_apscheduler_format(cron_string):
    // This function might not be strictly necessary if APScheduler can take the string directly.
    // However, it's good to acknowledge the need for correct format.
    // Example: "0 * * * *" -> {minute: '0', hour: '*', day: '*', month: '*', day_of_week: '*'}
    // APScheduler's CronTrigger can often parse standard cron strings.
    // TEST: scheduler_correctly_parses_valid_cron_schedule (Covered by APScheduler's capabilities)
    // TEST: scheduler_rejects_invalid_cron_schedule (Covered by APScheduler's capabilities)
    RETURN cron_string // Assuming APScheduler handles it
  END FUNCTION

END MODULE Scheduler
```

## 4. Task Executor Module

```pseudocode
MODULE TaskExecutor

  FUNCTION run_monitoring_task(task_id):
    // TEST: task_executor_retrieves_task_config_by_id
    LOG "Starting monitoring task: " + task_id
    task_config = MonitoringTaskManager.get_task_by_id(task_id)

    IF task_config IS NULL OR task_config.active IS FALSE:
      LOG_WARNING "Task " + task_id + " not found or inactive. Skipping execution."
      Scheduler.remove_task(task_id) // Clean up if task was removed/deactivated elsewhere
      RETURN

    // TEST: task_executor_handles_api_unreachable_with_retry
    // TEST: task_executor_sends_admin_notification_for_persistent_api_error
    calculation_result = perform_calculation_with_retry(task_config.parts)

    IF calculation_result.has_critical_error: // e.g., API unreachable after retries
      LOG_ERROR "Critical error during calculation for task " + task_id + ": " + calculation_result.error_message
      IF GLOBAL_EMAIL_NOTIFICATIONS_ENABLED:
        EmailService.send_admin_notification(
          "Monitoring Task Failed: " + task_config.name,
          "Task ID: " + task_id + "\nError: " + calculation_result.error_message
        )
      RETURN // Stop further processing for this task run

    // TEST: task_executor_handles_part_not_found_as_part_of_result
    // (This is inherent in how calculation_result is structured)

    // Notification Logic
    // TEST: task_executor_checks_global_email_enabled_flag
    IF NOT GLOBAL_EMAIL_NOTIFICATIONS_ENABLED:
      LOG "Global email notifications are disabled. Skipping email for task " + task_id
      RETURN

    should_notify = FALSE
    current_result_hash = ""

    IF task_config.notify_condition == "always":
      // TEST: notification_logic_sends_email_if_condition_is_always
      should_notify = TRUE
    ELSE IF task_config.notify_condition == "on_change":
      // TEST: notification_logic_calculates_result_hash_correctly
      current_result_hash = generate_significant_result_hash(calculation_result)
      IF current_result_hash != task_config.last_hash:
        // TEST: notification_logic_sends_email_if_condition_is_on_change_and_hash_differs
        should_notify = TRUE
      ELSE:
        // TEST: notification_logic_does_not_send_email_if_condition_is_on_change_and_hash_is_same
        LOG "No significant changes for task " + task_id + ". Skipping notification."
      ENDIF
    ENDIF

    IF should_notify:
      // TEST: email_generator_creates_html_output_from_calculation_result (Responsibility of EmailService)
      // TEST: email_generator_creates_plaintext_output_from_calculation_result (Responsibility of EmailService)
      // TEST: email_content_includes_all_required_tables_and_summary (Responsibility of EmailService)
      email_subject = "Inventree Order Report: " + task_config.name
      email_content_html = EmailService.generate_html_email_content(task_config, calculation_result)
      email_content_text = EmailService.generate_text_email_content(task_config, calculation_result)

      // TEST: task_executor_handles_email_send_failure_with_retry
      // TEST: task_executor_sends_admin_notification_for_persistent_email_failure
      email_sent_successfully = EmailService.send_email_with_retry(
        recipients=task_config.recipients,
        subject=email_subject,
        html_body=email_content_html,
        text_body=email_content_text
      )

      IF email_sent_successfully AND task_config.notify_condition == "on_change":
        // TEST: notification_logic_updates_last_hash_after_sending_on_change_email
        MonitoringTaskManager.update_task_last_hash(task_id, current_result_hash)
      ELSE IF NOT email_sent_successfully:
         LOG_ERROR "Failed to send notification email for task " + task_id + " after retries."
         // Admin notification for persistent email failure is handled within EmailService.send_email_with_retry
    ENDIF
    LOG "Finished monitoring task: " + task_id

  PRIVATE FUNCTION perform_calculation_with_retry(parts_list):
    // This function encapsulates the logic from the existing calculator,
    // including InvenTree API calls.
    // TEST: error_handler_logs_api_unreachable_error (within this function)
    // TEST: error_handler_initiates_retry_for_api_error (within this function)
    // TEST: error_handler_sends_admin_notification_for_persistent_api_error (if retries fail)

    max_retries = 3
    retry_delay_base = 5 // seconds

    FOR attempt = 1 TO max_retries:
      TRY
        // Assume Calculator.calculate_bom_cost_and_availability(parts_list) exists
        // and returns a structured result object including any errors like "part not found".
        // This result object should have a flag like `has_critical_error` and `error_message`.
        calculation_result = Calculator.calculate_bom_cost_and_availability(parts_list) // Placeholder for actual call
        
        // Check for specific API errors that warrant a retry vs. data errors (part not found)
        IF calculation_result.is_api_error AND calculation_result.is_retryable: // Example properties
            THROW new APIUnreachableError(calculation_result.error_message)

        LOG "Calculation successful for parts list on attempt " + attempt
        RETURN calculation_result // Contains data, warnings, non-critical errors
      CATCH APIUnreachableError as e:
        LOG_ERROR "API Unreachable on attempt " + attempt + " for task. Error: " + e.message
        IF attempt == max_retries:
          LOG_ERROR "API still unreachable after " + max_retries + " attempts."
          RETURN { has_critical_error: TRUE, error_message: "InvenTree API unreachable after " + max_retries + " attempts. Last error: " + e.message, is_api_error: TRUE }
        ENDIF
        sleep(retry_delay_base * (2 ** (attempt - 1))) // Exponential backoff
      CATCH OtherCalculationError as e: // For non-retryable calculation errors
        LOG_ERROR "Non-retryable calculation error: " + e.message
        RETURN { has_critical_error: TRUE, error_message: "Calculation error: " + e.message, is_api_error: FALSE }
      ENDTRY
    ENDFOR
    // Should not be reached if logic is correct, but as a fallback:
    RETURN { has_critical_error: TRUE, error_message: "Unknown error in perform_calculation_with_retry", is_api_error: FALSE }


  PRIVATE FUNCTION generate_significant_result_hash(calculation_result):
    // TEST: notification_logic_calculates_result_hash_correctly
    // Based on spec: "Fehlmengenliste" und "kritische Teile unter Schwellenwert"
    // This needs a stable serialization of the relevant parts of calculation_result.
    // For example, convert the relevant data to a JSON string and then hash it.
    significant_data = {
      "missing_parts": calculation_result.get_missing_parts_summary(), // Needs definition
      "critical_threshold_parts": calculation_result.get_critical_threshold_parts_summary() // Needs definition
    }
    serialized_data = json_stable_stringify(significant_data) // Ensure keys are sorted for consistent hash
    RETURN md5_hash(serialized_data)

END MODULE TaskExecutor
```

## 5. Monitoring Task Manager Module (Adapter for PresetsManager)

```pseudocode
MODULE MonitoringTaskManager

  // This module primarily acts as an interface/adapter to the existing PresetsManager
  // to fetch and update monitoring task configurations.

  FUNCTION get_all_monitoring_tasks():
    // TEST: presets_manager_can_load_monitoring_lists (Covered by PresetsManager tests)
    RETURN PresetsManager.get_monitoring_lists()

  FUNCTION get_all_active_monitoring_tasks():
    // TEST: task_manager_retrieves_only_active_tasks
    all_tasks = PresetsManager.get_monitoring_lists()
    active_tasks = []
    FOR EACH task IN all_tasks:
      IF task.active IS TRUE:
        ADD task TO active_tasks
      ENDIF
    ENDFOR
    RETURN active_tasks

  FUNCTION get_task_by_id(task_id):
    // TEST: task_manager_retrieves_specific_task_by_id
    all_tasks = PresetsManager.get_monitoring_lists()
    FOR EACH task IN all_tasks:
      IF task.id == task_id:
        RETURN task
      ENDIF
    ENDFOR
    RETURN NULL

  FUNCTION add_task(task_data):
    // TEST: presets_manager_can_save_new_monitoring_list (Covered by PresetsManager tests)
    // Validation of task_data (e.g., cron string) should happen before calling this,
    // or PresetsManager should handle it.
    // Generate UUID for task_data.id if not present
    IF task_data.id IS NULL OR task_data.id == "":
        task_data.id = generate_uuid()
    ENDIF
    IF task_data.last_hash IS NULL: // Initialize last_hash
        task_data.last_hash = ""
    ENDIF
    success = PresetsManager.add_monitoring_list(task_data)
    IF success:
      Scheduler.schedule_task(task_data) // Add to scheduler if successful
    RETURN success

  FUNCTION update_task(task_id, updated_data):
    // TEST: presets_manager_can_update_existing_monitoring_list (Covered by PresetsManager tests)
    // updated_data is a dictionary of fields to change
    task_config = get_task_by_id(task_id)
    IF task_config IS NULL:
        RETURN FALSE // Task not found

    // Merge updated_data into task_config
    FOR key, value IN updated_data:
        task_config[key] = value
    ENDFOR

    success = PresetsManager.update_monitoring_list(task_id, task_config)
    IF success:
      // Reschedule with potentially new cron or active status
      Scheduler.schedule_task(task_config)
    RETURN success

  FUNCTION delete_task(task_id):
    // TEST: presets_manager_can_delete_monitoring_list (Covered by PresetsManager tests)
    success = PresetsManager.delete_monitoring_list(task_id)
    IF success:
      Scheduler.remove_task(task_id)
    RETURN success

  FUNCTION activate_task(task_id):
    // TEST: cli_monitor_activate_sets_task_active_flag_true (Higher level test)
    // TEST: task_manager_can_activate_task
    task_config = get_task_by_id(task_id)
    IF task_config AND task_config.active IS FALSE:
      task_config.active = TRUE
      success = PresetsManager.update_monitoring_list(task_id, task_config)
      IF success:
        Scheduler.schedule_task(task_config)
      RETURN success
    ENDIF
    RETURN FALSE

  FUNCTION deactivate_task(task_id):
    // TEST: cli_monitor_deactivate_sets_task_active_flag_false (Higher level test)
    // TEST: task_manager_can_deactivate_task
    task_config = get_task_by_id(task_id)
    IF task_config AND task_config.active IS TRUE:
      task_config.active = FALSE
      success = PresetsManager.update_monitoring_list(task_id, task_config)
      IF success:
        Scheduler.remove_task(task_id)
      RETURN success
    ENDIF
    RETURN FALSE

  FUNCTION update_task_last_hash(task_id, new_hash):
    // TEST: task_manager_updates_last_hash_for_task
    task_config = get_task_by_id(task_id)
    IF task_config:
      task_config.last_hash = new_hash
      RETURN PresetsManager.update_monitoring_list(task_id, task_config)
    ENDIF
    RETURN FALSE

  FUNCTION run_task_manually(task_id):
    // TEST: cli_monitor_run_executes_task_once (Higher level test)
    // TEST: task_manager_can_trigger_manual_run
    LOG "Manually triggering task: " + task_id
    TaskExecutor.run_monitoring_task(task_id)
    LOG "Manual run finished for task: " + task_id

END MODULE MonitoringTaskManager
```

## 6. Main Application Flow (Conceptual)

```pseudocode
FUNCTION main_monitoring_application_startup():
  load_environment_variables() // For email config, global flags
  Config.load_email_configuration() // Loads EMAIL_SMTP_SERVER etc.
  PresetsManager.initialize() // Load presets.json including monitoring_lists

  Scheduler.initialize_scheduler()

  // Keep the application running (e.g., in a loop with sleep, or if APScheduler runs in a background thread)
  // Handle graceful shutdown (e.g., on SIGINT/SIGTERM)
  TRY
    WHILE TRUE:
      sleep(3600) // Or some other mechanism to keep main thread alive if scheduler is daemonized
    ENDWHILE
  CATCH KeyboardInterrupt:
    LOG "Shutdown signal received."
  FINALLY
    Scheduler.shutdown_scheduler()
    LOG "Monitoring application stopped."
  ENDTRY

END FUNCTION
```

## 7. Helper Functions (Assumed to exist or be implemented elsewhere)

```pseudocode
FUNCTION generate_uuid(): // Returns a new UUID string
FUNCTION md5_hash(string_data): // Returns MD5 hash of the input string
FUNCTION json_stable_stringify(object_data): // Converts object to JSON string with sorted keys
FUNCTION LOG(message):
FUNCTION LOG_ERROR(message):
FUNCTION LOG_WARNING(message):
FUNCTION sleep(seconds):