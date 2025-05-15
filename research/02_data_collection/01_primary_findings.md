# Primary Research Findings

This document consolidates the primary findings from research activities, organized by the key research areas defined in `research/01_initial_queries/02_key_questions.md`.

## 1. Scheduling Mechanisms

This section addresses research questions Q1.1, Q1.2, Q1.3, and Q1.4 related to Python job scheduling libraries, cron parsing, and error handling. The findings are based on a Perplexity AI search conducted on 2025-05-14.

### Q1.1: APScheduler Suitability

**APScheduler** is generally considered suitable for lightweight scheduling in single-node Python applications, aligning well with the project's initial needs as described in [`docs/feature_specs/automated_monitoring_spec.md`](docs/feature_specs/automated_monitoring_spec.md:1).

*   **Strengths:**
    *   **Cron-like Scheduling:** Supports flexible cron expressions via `CronTrigger` (e.g., `* */5 1-3 * mon-fri`). (Perplexity result [2], [5])
    *   **Error Handling:** Facilitates robust error handling through job-specific try-except wrappers and configurable `misfire_grace_time` for jobs. APScheduler also allows attaching event listeners for job errors.
    *   **Storage Options:** Supports in-memory job storage (default) or persistent storage using backends like SQLAlchemy (for SQL databases), MongoDB, or Redis. (Perplexity result [5])
    *   **Integration:** Can be integrated directly into applications, including those with CLI or Streamlit UIs, often using `BackgroundScheduler` for daemon-like execution.
    *   **Dependencies:** Relatively lightweight, primarily requiring `pytz` and `tzlocal`.

*   **Example (Conceptual, based on Perplexity output):**
    ```python
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    import logging

    logger = logging.getLogger(__name__)

    def job_with_error_handling():
        try:
            # Your job logic here
            logger.info("Job executed successfully.")
        except Exception as e:
            logger.error(f"Job failed: {e}", exc_info=True)
            # Potentially notify admin or re-raise for scheduler's listener

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        job_with_error_handling,
        CronTrigger.from_crontab("0 2 * * *") # Example: every day at 2 AM
    )
    # scheduler.start() # Typically started by the main application
    ```

### Q1.2: Alternatives to APScheduler

Several alternatives exist, each with different trade-offs:

| Feature          | APScheduler                               | Celery                                     | Schedule Library                        | ARQ (Asyncio Redis Queue)             | System Cron + Script                     |
|------------------|-------------------------------------------|--------------------------------------------|-----------------------------------------|---------------------------------------|------------------------------------------|
| **Complexity**   | Medium                                    | High                                       | Low                                     | Medium                                | Low (script), Medium (OS config)         |
| **Distributed**  | No (natively)                             | Yes                                        | No                                      | Yes (via Redis)                       | No                                       |
| **Cron Parsing** | Native (`CronTrigger`)                    | Via `celery beat`                          | No native cron; interval-based          | Uses `croniter`                       | Native OS cron syntax                    |
| **Retry Logic**  | Manual implementation (or via listeners)  | Automatic (configurable per task)          | Manual implementation                   | Automatic (configurable)              | Script-dependent; none from cron itself  |
| **Dependencies** | `pytz`, `tzlocal`                         | Message Broker (Redis, RabbitMQ), Backend  | None                                    | Redis, `croniter`                     | OS-dependent                             |
| **Use Case**     | In-process scheduling, single-node apps   | Distributed tasks, complex workflows, scaling | Simple, human-readable interval tasks   | Async tasks, Redis-backed queues      | OS-level script execution, reliability   |
| **UI Integration**| Direct (e.g., control scheduler object)   | Indirect (via message queue, API calls)    | Direct                                  | Indirect (via Redis, API calls)       | External (trigger script, check status)  |

*   **Celery:**
    *   Best for **distributed task queues** requiring horizontal scaling, result tracking (e.g., with Redis or RabbitMQ as a message broker), and complex task workflows (chaining, grouping). (Perplexity result [3], [5])
    *   `celery beat` is its component for periodic task scheduling.
    *   Higher setup and operational complexity compared to APScheduler.
    *   **Example (Conceptual Celery task, from Perplexity):**
        ```python
        from celery import Celery

        # Assumes Celery app is configured
        # app = Celery('tasks', broker='redis://localhost:6379/0')

        # @app.task(bind=True, max_retries=3)
        def example_celery_task(self, data):
            try:
                # Task logic
                pass
            except Exception as e:
                # self.retry(exc=e, countdown=60) # Retry after 60s
                raise # Or re-raise for Celery's error handling
        ```

*   **Schedule library:**
    *   Very simple, human-readable syntax for basic interval-based tasks (e.g., `schedule.every(10).minutes.do(job)`). (Perplexity result [5])
    *   Does not natively support cron expressions.
    *   Suitable for very simple, non-critical scheduling needs within a single process.

*   **ARQ (Asyncio Redis Queue):**
    *   Designed for asynchronous task processing using Python's `asyncio` and Redis as a message broker. (Perplexity result [1], [5])
    *   Supports cron-like scheduling using the `croniter` library.
    *   Good for applications already using `asyncio` and Redis.

*   **System Cron + Script:**
    *   Utilizes the operating system's cron daemon (e.g., on Linux/macOS) to execute a Python script at specified times.
    *   Highly reliable for OS-level tasks.
    *   Lacks direct integration with the Python application's context, making state management and interaction more complex. (Perplexity result [4])
    *   Error handling and logging must be fully implemented within the script.

### Q1.3: Cron String Parsing and Validation

*   **APScheduler:** Natively parses cron expressions through its `CronTrigger.from_crontab()` method or by directly instantiating `CronTrigger` with cron parameters. It handles standard cron syntax.
*   **`croniter` library:**
    *   A widely used Python library for iterating and validating cron expressions.
    *   Can be used independently or by other libraries (like ARQ) for cron functionality.
    *   Useful for validating user-supplied cron strings before passing them to a scheduler.
    *   **Example (from Perplexity):**
        ```python
        from croniter import croniter
        is_valid = croniter.is_valid("*/5 * * * *")  # Returns True or False
        # base_time = datetime.datetime.now()
        # iter = croniter("*/5 * * * *", base_time)
        # next_run = iter.get_next(datetime.datetime)
        ```
*   **Best Practices:**
    *   Always validate user-provided cron strings to prevent errors and potential abuse.
    *   Provide clear feedback to users on valid cron syntax.
    *   Log errors related to invalid cron expressions.

### Q1.4: Error Handling in Scheduling Mechanisms

*   **APScheduler:**
    *   **Job-level:** Individual jobs should implement their own `try-except` blocks to catch and log exceptions, as shown in the Q1.1 example. This prevents a single job failure from crashing the scheduler.
    *   **Scheduler-level:** APScheduler can emit events, including `EVENT_JOB_ERROR`. Event listeners can be attached to react to these events, for example, to log the error globally or notify an administrator.
        *   **Example (Conceptual listener, from Perplexity):**
            ```python
            from apscheduler.events import EVENT_JOB_ERROR
            import logging
            logger = logging.getLogger(__name__)

            def job_error_listener(event):
                if event.exception:
                    logger.error(f"Job {event.job_id} crashed: {event.exception}", exc_info=True)
                    # Notify admin logic here

            # scheduler.add_listener(job_error_listener, EVENT_JOB_ERROR)
            ```
    *   `misfire_grace_time`: Configures a window during which a job can still run if its scheduled time was missed (e.g., due to scheduler downtime).
    *   `max_instances`: Can limit the number of concurrently running instances of a particular job.

*   **Celery:**
    *   Provides built-in support for automatic task retries with configurable policies (e.g., max retries, countdown).
    *   Has mechanisms for error handling and callbacks (e.g., `on_failure`).

*   **General Best Practices:**
    *   Implement comprehensive logging within scheduled jobs.
    *   For critical jobs, consider implementing alerting mechanisms (e.g., email notifications to admins) when jobs fail persistently.
    *   Ensure the scheduler itself is monitored (e.g., that the process is running).

The Perplexity output suggests that for most Python applications requiring scheduled tasks with UI controls (like Streamlit), **APScheduler offers a good balance of flexibility and simplicity**. Celery is preferred for distributed environments or complex task chaining. (Perplexity result [2], [5])

## 2. Email Generation and Sending

This section addresses research questions Q2.1, Q2.2, Q2.3, Q2.4, and Q2.5 related to Python email generation, sending, security, and deliverability. The findings are based on a Perplexity AI search conducted on 2025-05-14.

### Q2.1: Email Generation Libraries and Techniques

*   **Multipart Emails:** For sending emails with both HTML and plain-text versions, Python's built-in `email.mime` module is standard.
    *   `email.mime.multipart.MIMEMultipart("alternative")` is used to create a container for the two versions.
    *   `email.mime.text.MIMEText` is used to create the plain text and HTML parts. (Perplexity result [4])
*   **HTML Templating:** `Jinja2` is a highly recommended library for generating dynamic HTML content for emails. It allows separating presentation logic from application code.
    *   **Example (Conceptual Jinja2 usage, from Perplexity):**
        ```python
        from jinja2 import Environment, FileSystemLoader
        # env = Environment(loader=FileSystemLoader("templates/")) # Assuming 'templates' dir
        # html_template = env.get_template("email_template.html")
        # html_content = html_template.render(user_name="John Doe", ...)
        ```
*   **CSS Inlining:** Email clients have inconsistent support for CSS in `<style>` tags or external stylesheets. Therefore, inlining CSS styles directly into HTML elements is crucial for consistent rendering.
    *   `premailer` is a popular Python library for this purpose. It takes HTML content with `<style>` tags and transforms it into HTML with inlined styles. (Perplexity result, general best practice)
    *   **Example (Conceptual premailer usage, from Perplexity):**
        ```python
        import premailer
        # html_with_styles = "<html><head><style>p {color: blue;}</style></head><body><p>Hello</p></body></html>"
        # inlined_html = premailer.transform(html_with_styles)
        ```

### Q2.2: Secure SMTP Configuration

*   **Environment Variables:** Storing SMTP server details (`EMAIL_SMTP_SERVER`, `EMAIL_SMTP_PORT`, `EMAIL_USE_TLS`, `EMAIL_USE_SSL`, `EMAIL_USERNAME`, `EMAIL_PASSWORD`, `EMAIL_SENDER_ADDRESS`) in environment variables is a security best practice. This avoids hardcoding sensitive information in the codebase.
    *   The `python-dotenv` library can be used to load these variables from a `.env` file during development. The `.env` file should be included in `.gitignore`. (Perplexity result [3], [4])
    *   Access variables in Python using `os.getenv("VARIABLE_NAME")`.
    *   **Example `.env` file structure (from Perplexity):**
        ```
        EMAIL_SMTP_SERVER=smtp.example.com
        EMAIL_SMTP_PORT=587
        EMAIL_USERNAME=user@example.com
        EMAIL_PASSWORD=your_secret_password
        EMAIL_SENDER_ADDRESS=noreply@example.com
        EMAIL_USE_TLS=true
        ```
*   **Secure Connections:** Always use encrypted connections to the SMTP server.
    *   `smtplib.SMTP_SSL()`: For servers that expect an SSL connection from the start (typically on port 465). (Perplexity result)
    *   `smtplib.SMTP()` followed by `server.starttls()`: For servers that start with an unencrypted connection and then upgrade to TLS (typically on port 587).

### Q2.3: Handling Sensitive Credentials

*   **Primary Method:** Use environment variables as described in Q2.2. This is the standard and recommended approach.
*   **Avoid Hardcoding:** Never store passwords or sensitive keys directly in source code.
*   **Logging:** Ensure that sensitive credentials are never logged. Be careful with logging entire SMTP connection objects or debug messages that might inadvertently include them.
*   **Access Control:** If using a `.env` file, ensure its file permissions are restrictive. In production, environment variables are typically managed by the deployment platform or orchestration system.

### Q2.4: Error Handling and Retry Logic for SMTP Failures

*   **Exception Handling:** Python's `smtplib` can raise various exceptions, such as `smtplib.SMTPException` (a base class for many SMTP errors), `smtplib.SMTPAuthenticationError`, `smtplib.SMTPServerDisconnected`, or `TimeoutError` during connection or sending.
*   **Retry Mechanisms:** For transient errors (e.g., temporary network issues, server busy), implement a retry logic, often with an exponential backoff strategy.
    *   **Example (Conceptual retry loop, from Perplexity result [5]):**
        ```python
        import smtplib
        import time
        import logging
        logger = logging.getLogger(__name__)

        # MAX_RETRIES = 3
        # RETRY_DELAY_SECONDS = 30 # Initial delay

        # for attempt in range(MAX_RETRIES):
        #     try:
        #         # server = smtplib.SMTP_SSL(os.getenv("SMTP_SERVER"), int(os.getenv("SMTP_PORT", 465)))
        #         # server.login(os.getenv("SMTP_USERNAME"), os.getenv("SMTP_PASSWORD"))
        #         # server.send_message(msg_object)
        #         # server.quit()
        #         logger.info("Email sent successfully.")
        #         break # Exit loop on success
        #     except (smtplib.SMTPException, TimeoutError) as e:
        #         logger.warning(f"Email sending attempt {attempt + 1} failed: {e}")
        #         if attempt == MAX_RETRIES - 1:
        #             logger.error(f"Failed to send email after {MAX_RETRIES} attempts.")
        #             # Notify admin (e.g., if a separate, more reliable channel exists or log for alerting)
        #             # raise EmailDeliveryError(f"Failed after {MAX_RETRIES} attempts") from e # Custom exception
        #         time.sleep(RETRY_DELAY_SECONDS * (2 ** attempt)) # Exponential backoff
        ```
*   **Admin Notifications:** For persistent failures, the system should notify `ADMIN_EMAIL_RECIPIENTS` as specified in [`docs/feature_specs/automated_monitoring_spec.md`](docs/feature_specs/automated_monitoring_spec.md:1). If the primary email system itself is failing, this might require logging to an external monitoring system or a very basic, separate notification channel if feasible.

### Q2.5: Email Deliverability

Improving email deliverability involves server-side configurations and email content best practices. While some are beyond direct Python code control, awareness is key.

*   **DNS Records (Server-side configuration):**
    *   **SPF (Sender Policy Framework):** A TXT DNS record that specifies which mail servers are authorized to send emails on behalf of your domain. Helps prevent spoofing. (Perplexity result)
        *   Example: `v=spf1 include:_spf.google.com ~all`
    *   **DKIM (DomainKeys Identified Mail):** Adds a digital signature to outgoing emails, allowing the receiving server to verify that the email was sent from an authorized server and hasn't been tampered with. Involves a TXT DNS record with a public key. (Perplexity result)
        *   Example: `v=DKIM1; k=rsa; p=PUBLIC_KEY_STRING...`
    *   **DMARC (Domain-based Message Authentication, Reporting, and Conformance):** A TXT DNS record that tells receiving servers what to do if an email fails SPF or DKIM checks (e.g., quarantine, reject). Also enables reporting. (Perplexity result)
        *   Example: `v=DMARC1; p=quarantine; rua=mailto:dmarc-reports@example.com`
*   **Other Key Considerations (Application and Content level):**
    *   **IP Warm-up:** If sending from a new IP address, gradually increase sending volume to build a positive sender reputation.
    *   **Monitor Bounce Rates and Spam Complaints:** Aim for low bounce rates (e.g., <2%) and spam complaint rates (e.g., <0.1%). High rates damage sender reputation.
    *   **Unsubscribe Links:** Include clear and easy-to-use unsubscribe links/headers (`List-Unsubscribe`).
    *   **Email Validation:** Validate email addresses before sending to reduce bounces (e.g., using third-party services, though this has costs and privacy implications). (Perplexity result [4])
    *   **Content Quality:** Avoid spammy content, excessive capitalization, misleading subject lines, and too many images without text.
    *   **Engagement:** Sending emails that recipients open and interact with positively impacts deliverability.

The Perplexity output also suggests an abstraction like an `EmailClient` class to encapsulate SMTP logic, credential handling, and potentially retry/logging, which aligns with good software design principles.

## 3. Change Detection (`on_change` logic)

This section addresses research questions Q3.1, Q3.2, Q3.3, and Q3.4 related to detecting significant changes in complex data structures for the `on_change` notification condition. The findings are based on a Perplexity AI search conducted on 2025-05-14 (though the initial search timed out, the subsequent one provided general context, and much of this section relies on established best practices). The specification in [`docs/feature_specs/automated_monitoring_spec.md`](docs/feature_specs/automated_monitoring_spec.md:1) indicates that the "Fehlmengenliste" (shortages list) and "kritische Teile unter Schwellenwert" (critical parts below threshold) are key for this.

### Q3.1: Hashing Algorithms

*   **Cryptographic Hashes:** For generating a `last_hash` to detect changes, cryptographic hash functions like MD5 or SHA256 (SHA256 preferred for better collision resistance) are suitable.
    *   **MD5:** Faster but has known collision vulnerabilities (less critical for this use case if only used for change detection, not security).
    *   **SHA256:** More secure, slightly slower, but generally recommended for new implementations.
*   **Process:** The relevant part of the calculation result (e.g., a list of dictionaries representing shortages) needs to be serialized into a consistent string format before being hashed.
    *   **Example (Conceptual, using SHA256):**
        ```python
        import hashlib
        import json

        def calculate_data_hash(data_to_hash):
            # Ensure data_to_hash is the specific, relevant part of the calculation result
            # e.g., shortages_list = [{"part": "A", "short": 5}, {"part": "B", "short": 2}]
            # canonical_representation = json.dumps(data_to_hash, sort_keys=True, separators=(',', ':'))
            # return hashlib.sha256(canonical_representation.encode('utf-8')).hexdigest()
            pass # Placeholder for actual implementation based on Perplexity output
        ```
        (Adapted from Perplexity output on hashing)

### Q3.2: Canonical Serialization for Hashing

To ensure that semantically identical results produce the same hash, the data must be serialized into a canonical (standardized) string representation before hashing.

*   **JSON Serialization:**
    *   `json.dumps()` with `sort_keys=True` is crucial for dictionaries to ensure keys are always in the same order. (Perplexity output)
    *   Using `separators=(',', ':')` removes unnecessary whitespace, contributing to a consistent representation. (Perplexity output)
    *   This handles nested lists and dictionaries well.
    *   **Limitation:** Standard `json.dumps` cannot serialize all Python types (e.g., `datetime` objects, custom objects) without custom encoders. For the specified "Fehlmengenliste" and "kritische Teile," which are likely lists of simple data types or dicts, this should be manageable.
*   **`repr()`:** For simpler structures or when a Python-specific representation is needed and consistent, `repr()` might be considered, but often `json.dumps` is more robust for complex data. Sorting items in dictionaries (`sorted(my_dict.items())`) before `repr` would be necessary. (Perplexity output)
*   **`orjson`:** A faster JSON library for Python that also supports `OPT_SORT_KEYS`. Could be considered if performance with `json.dumps` becomes an issue for very large result sets. (Perplexity output [3] - note: source [3] in Perplexity output was a video, this is a general knowledge point about orjson)
*   **Floating Point Numbers:** If the results include floats, be aware that their string representation can vary. It might be necessary to round them to a consistent number of decimal places or convert them to a fixed-point decimal representation before serialization if exact float equality is not intended.
*   **Type Consistency:** Ensure that types within the data structure are consistent between checks (e.g., an ID is always an `int` or always a `str`).

### Q3.3: Alternative Change Detection Methods

While hashing is efficient for a binary "changed/not changed" decision, other methods can provide more insight or handle specific cases differently.

*   **`DeepDiff` library:**
    *   Performs a deep comparison of two Python objects (lists, dicts, custom objects) and reports detailed differences (e.g., items added, removed, changed values). (Perplexity output)
    *   **Pros:** Provides granular information about *what* changed, can ignore order in lists, handle numeric tolerances (`numeric_epsilon`), and exclude specific paths from comparison.
    *   **Cons:** Significantly more computationally expensive than hashing, especially for large and complex data structures (10-100x slower reported in Perplexity output [4] - note: source [4] in Perplexity output was about time series, this is a general knowledge point about deepdiff performance).
    *   **Use Case:** Could be used *after* a hash mismatch is detected to log the specific changes, or if the definition of "significant change" is too complex for a simple hash.
    *   **Example (Conceptual, from Perplexity output):**
        ```python
        from deepdiff import DeepDiff
        # previous_result = ...
        # current_result = ...
        # diff = DeepDiff(previous_result, current_result, ignore_order=True)
        # if diff:
        #     print("Changes detected:", diff)
        ```
*   **Custom Comparison Logic:** For very specific definitions of "significant change," custom Python code could iterate through the relevant data structures and apply specific rules. This offers maximum flexibility but requires careful implementation and testing.
*   **Hybrid Approach (Recommended by Perplexity output):**
    1.  Perform a quick hash check. If hashes match, assume no significant change.
    2.  If hashes differ, then (optionally, if detailed changes are needed for logging or more complex logic) use a library like `DeepDiff` or custom logic to analyze the differences.

### Q3.4: Updating `last_hash`

*   The `last_hash` field in the `monitoring_lists` object within [`presets.json`](presets.json) should be updated only after a notification has been successfully sent (if `notify_condition` is `on_change` and a change was detected).
*   **Atomicity:** Since [`presets.json`](presets.json) is managed by `PresetsManager`, and interactions are likely to be single-threaded in the context of a scheduled job for a specific monitoring list, file write atomicity is less of a concern than in a highly concurrent system. Standard file write operations (read, modify, write back) should be sufficient.
    *   However, ensure that the `PresetsManager`'s save operation writes the entire updated presets data atomically to avoid corruption if an error occurs mid-write (e.g., by writing to a temporary file then renaming).
*   **Error Handling:** If updating the `last_hash` fails after a notification has been sent, this could lead to repeated notifications for the same change in the next cycle. This scenario should be logged. The risk is relatively low if file writes are generally reliable.

**Minimizing False Positives/Negatives (Summary from Perplexity output and best practices):**

*   **False Positives (detecting a change when none occurred):**
    *   Ensure robust canonical serialization (sorted keys, no random whitespace, consistent type handling).
    *   Handle floating-point comparisons carefully (e.g., rounding or epsilon comparisons if exact values are not critical).
    *   Be mindful of non-significant data that might be part of the hashed structure (e.g., timestamps of data retrieval if not relevant to the change itself). Exclude such volatile fields before hashing.
*   **False Negatives (missing a real change):**
    *   Ensure all relevant fields that define a "significant change" are included in the serialization and hashing process. The spec correctly identifies "Fehlmengenliste" and "kritische Teile" as key.
    *   Use a hash algorithm with good collision resistance (SHA256 is better than MD5).
    *   If the definition of "significant change" is very nuanced, hashing might be too coarse, and a more detailed comparison (like `DeepDiff` or custom logic) might be necessary as the primary check, despite performance costs.

The Perplexity output suggests a balanced approach: a quick hash check first, and if a change is detected, then potentially a more detailed diff for logging or more complex decision-making. This seems appropriate for the specified `on_change` logic.

## 4. Error Handling and Logging

This section addresses research questions Q4.1, Q4.2, Q4.3, and Q4.4 concerning comprehensive error handling and logging strategies for the monitoring service. The findings are based on a Perplexity AI search conducted on 2025-05-14.

### Q4.1: Comprehensive Logging Strategies

Effective logging is crucial for diagnosing issues in background tasks.

*   **Standard Library `logging` Module:**
    *   Python's built-in `logging` module is the foundation. Configure it with appropriate formatters, handlers (e.g., file handler, console handler), and logging levels (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    *   **Example Basic Configuration (from Perplexity result [2]):**
        ```python
        import logging
        # logging.basicConfig(level=logging.INFO, 
        #                     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        #                     handlers=[logging.FileHandler("monitoring.log"), logging.StreamHandler()])
        # logger = logging.getLogger(__name__)
        ```
    *   Use `logger.exception("Error message")` within `except` blocks to automatically include traceback information. (Perplexity result [2])
*   **Structured Logging (e.g., `structlog`):**
    *   `structlog` enhances the standard library by making it easy to produce structured logs (e.g., JSON), which are invaluable for log management systems (like ELK stack, Splunk, Datadog). (Perplexity result)
    *   Allows adding key-value pairs for context, making logs more searchable and analyzable.
    *   **Example (Conceptual `structlog` usage, from Perplexity output):**
        ```python
        import structlog
        # structlog.configure(
        #     processors=[
        #         structlog.stdlib.add_logger_name,
        #         structlog.stdlib.add_log_level,
        #         structlog.processors.StackInfoRenderer(),
        #         structlog.dev.set_exc_info,
        #         structlog.dev.format_exc_info,
        #         structlog.processors.JSONRenderer() # Or structlog.dev.ConsoleRenderer() for development
        #     ],
        #     logger_factory=structlog.stdlib.LoggerFactory(),
        #     wrapper_class=structlog.stdlib.BoundLogger,
        # )
        # logger = structlog.get_logger(__name__)
        # logger.info("task_started", task_id="123", preset_name="MyPreset")
        # try:
        #   # ... task logic ...
        # except Exception as e:
        #   logger.error("task_failed", task_id="123", error=str(e), exc_info=True)
        ```
*   **Contextual Logging:** Include relevant context in log messages, such as the ID or name of the monitoring task being processed, current step, API endpoints called, etc. (Perplexity result [1], [3])
    *   A custom context manager or `structlog`'s `bind` feature can help manage contextual information. (Perplexity result [1])
*   **Log Levels:**
    *   `DEBUG`: Detailed information, typically of interest only when diagnosing problems.
    *   `INFO`: Confirmation that things are working as expected (e.g., task started, email sent).
    *   `WARNING`: An indication that something unexpected happened, or indicative of some problem in the near future (e.g., API slow response, minor configuration issue).
    *   `ERROR`: Due to a more serious problem, the software has not been able to perform some function.
    *   `CRITICAL`: A serious error, indicating that the program itself may be unable to continue running.
*   **HTTP Request Logging:** For API interactions (e.g., with InvenTree), log request details (URL, method, headers if not sensitive, body if small and not sensitive) and response details (status code, relevant parts of response body). (Perplexity result [5])

### Q4.2: Retry Mechanisms for Transient Errors

For operations that can fail due to temporary issues (e.g., network glitches, API rate limits, temporary email server unavailability).

*   **`tenacity` Library:**
    *   A popular and powerful Python library for adding retry logic to functions/methods with minimal code. (Perplexity result)
    *   Supports various waiting strategies (e.g., `wait_exponential` for exponential backoff, `wait_fixed`), stopping conditions (e.g., `stop_after_attempt`, `stop_after_delay`), and specifying which exceptions to retry on.
    *   **Example (Conceptual `tenacity` usage, from Perplexity output):**
        ```python
        from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
        import logging
        logger = logging.getLogger(__name__)

        class TransientAPIError(Exception): pass
        class TransientEmailError(Exception): pass

        def log_retry_attempt(retry_state):
            logger.warning(f"Retrying {retry_state.fn.__name__}, attempt {retry_state.attempt_number}...")

        # @retry(
        #     wait=wait_exponential(multiplier=1, min=4, max=60), # Wait 2^N * 1s, min 4s, max 60s
        #     stop=stop_after_attempt(5),
        #     retry=retry_if_exception_type((TransientAPIError, TransientEmailError)),
        #     before_sleep=log_retry_attempt
        # )
        # def call_inventree_api_with_retry(part_id):
        #     # ... API call logic ...
        #     # if error_is_transient: raise TransientAPIError("API temporarily unavailable")
        #     pass

        # @retry(wait=wait_exponential(), stop=stop_after_attempt(3), retry=retry_if_exception_type(TransientEmailError))
        # def send_email_with_retry(message_details):
        #     # ... email sending logic ...
        #     # if email_error_is_transient: raise TransientEmailError("Email server busy")
        #     pass
        ```
*   **Exponential Backoff with Jitter:** This strategy involves increasing the wait time between retries exponentially and adding a small random amount of time (jitter) to prevent thundering herd problems where many clients retry simultaneously. `tenacity` can be configured for this.
*   **Idempotency:** Ensure that operations being retried are idempotent (i.e., applying them multiple times has the same effect as applying them once). This is crucial for data integrity.

### Q4.3: Handling Persistent Errors (API/Email Failures)

When retries are exhausted for critical operations like InvenTree API access or email sending:

*   **Log Thoroughly:** Log the persistent failure with all available context (error messages, number of retries, relevant data).
*   **Admin Notifications:** Send a notification to `ADMIN_EMAIL_RECIPIENTS` as specified in [`docs/feature_specs/automated_monitoring_spec.md`](docs/feature_specs/automated_monitoring_spec.md:1).
    *   This notification should clearly state the failed operation, the error, and the affected monitoring task.
    *   If the primary email system is the one failing, this notification might need to be sent via an alternative, highly reliable channel if configured, or rely on external log monitoring and alerting systems (e.g., Sentry, Rollbar, Prometheus Alertmanager).
*   **Circuit Breaker Pattern:** For services that are repeatedly failing, consider implementing a circuit breaker pattern. After a certain number of consecutive failures, the circuit "opens," and further calls to the failing service are immediately rejected for a period, preventing the application from overwhelming a struggling service. `tenacity` can also be used to implement basic circuit breaker logic.
*   **Graceful Degradation:** The specific monitoring task that encountered the persistent error might be temporarily skipped or marked as "degraded" rather than halting the entire monitoring service (unless the error is global, like InvenTree being completely down).

### Q4.4: Managing Configuration Errors

Errors in configuration (e.g., invalid cron string, incorrect email server details, malformed `presets.json` entries) should be handled robustly.

*   **Validation at Startup/Load:**
    *   Validate configurations when the monitoring service starts or when monitoring tasks are loaded/reloaded from [`presets.json`](presets.json).
    *   Libraries like `Pydantic` can be used to define configuration models and validate data against them, providing clear error messages. (Perplexity result)
    *   **Example (Conceptual Pydantic usage, from Perplexity output):**
        ```python
        from pydantic import BaseModel, validator, EmailStr
        import logging
        logger = logging.getLogger(__name__)
        
        # class EmailConfig(BaseModel):
        #     smtp_server: str
        #     smtp_port: int = 587
        #     username: EmailStr
        #     # ... other fields

        # class MonitoringTaskConfig(BaseModel):
        #     id: str
        #     name: str
        #     cron_schedule: str
        #     recipients: list[EmailStr]
        #     active: bool = True

        #     @validator('cron_schedule')
        #     def validate_cron(cls, v):
        #         from croniter import croniter # Assuming croniter for validation
        #         if not croniter.is_valid(v):
        #             raise ValueError(f"Invalid cron string: {v}")
        #         return v
        
        # try:
        #     # raw_task_config_from_json = {"id": "task1", ...}
        #     # task_config = MonitoringTaskConfig(**raw_task_config_from_json)
        # except ValidationError as e:
        #     logger.critical("Invalid task configuration", task_id=raw_task_config_from_json.get("id"), errors=e.errors())
        #     # Potentially disable this specific task or prevent service start if critical
        ```
*   **Logging:** Clearly log any configuration errors found, indicating the problematic setting and task.
*   **Admin Notification:** Notify `ADMIN_EMAIL_RECIPIENTS` about critical configuration errors that prevent a task from running or the service from starting correctly.
*   **Task Deactivation (as per spec):** If a specific monitoring task has an invalid configuration (e.g., bad cron string), the specification suggests it could be automatically deactivated. This prevents it from repeatedly failing or causing issues for the scheduler. The admin notification should mention this deactivation. (Perplexity result [1], [3])
*   **Fail Fast / Graceful Degradation:**
    *   For critical global configuration errors (e.g., unable to load main email settings), the service might need to fail fast on startup.
    *   For errors specific to one monitoring task, the service should ideally continue running other valid tasks.

**Async Exception Handling (Perplexity result [4]):**
If parts of the monitoring service use `asyncio` (e.g., for concurrent API calls):
*   Ensure exceptions in async tasks are properly handled and propagated (e.g., using `try-except` within `async def` functions, or `asyncio.gather(*tasks, return_exceptions=True)`).
*   Be mindful of "forgotten" tasks that might raise exceptions silently if not `await`ed or handled.
*   Use `asyncio.create_task` and ensure tasks are properly awaited or have exception handlers attached to prevent issues like memory leaks from unhandled exceptions.

By implementing these strategies, the monitoring service can achieve a higher degree of reliability and maintainability.

## 5. Task Management (CLI/UI)

This section addresses research questions Q5.1, Q5.2, Q5.3, and Q5.4 related to managing monitoring tasks via Command Line Interface (CLI) and a Streamlit Web User Interface (UI). The findings are based on a Perplexity AI search conducted on 2025-05-14.

### Q5.1: CLI Design Patterns (Typer/Click)

Libraries like `Typer` (which is based on `Click`) are excellent for creating user-friendly CLIs in Python. The specification in [`docs/feature_specs/automated_monitoring_spec.md`](docs/feature_specs/automated_monitoring_spec.md:1) outlines specific CLI commands: `monitor list`, `add`, `update`, `delete`, `activate`, `deactivate`, `run`.

*   **CRUD Operations:**
    *   **`add`**: Should take parameters for `name`, `parts` (e.g., as a comma-separated string "PartA:10,PartB:5" or path to a JSON/CSV file), `schedule` (cron string), `recipients` (comma-separated emails), and optionally `notify_condition`.
        *   **Example (Conceptual Typer command, from Perplexity output):**
            ```python
            import typer
            # app = typer.Typer()

            # @app.command()
            # def add_task(name: str, cron_schedule: str, parts_definition: str, recipients: str):
            #     # Logic to parse parts_definition, recipients
            #     # Save to backend (e.g., presets.json via PresetsManager)
            #     typer.echo(f"Task '{name}' added with schedule {cron_schedule}")
            ```
    *   **`list`**: Display tasks, potentially with options for filtering or showing details (e.g., active status, next run time). Output can be formatted as a table.
    *   **`update <task_id>`**: Allow modification of specific fields of an existing task, identified by its unique ID.
    *   **`delete <task_id>`**: Remove a task. Should probably ask for confirmation.
*   **Activation/Deactivation:**
    *   **`activate <task_id>` / `deactivate <task_id>`**: Toggle the `active` flag of a task in [`presets.json`](presets.json).
        *   **Example (Conceptual Typer command, from Perplexity output):**
            ```python
            # @app.command()
            # def toggle_task_status(task_id: str, activate_status: bool):
            #     # Update active flag in backend
            #     typer.echo(f"Task {task_id} {'activated' if activate_status else 'deactivated'}")
            ```
*   **Manual Triggering:**
    *   **`run <task_id>`**: Execute a specific monitoring task immediately, outside its regular schedule. This would involve directly invoking the task's execution logic.
        *   **Example (Conceptual Typer command, from Perplexity output):**
            ```python
            # @app.command()
            # def run_task_now(task_id: str):
            #     # Signal or call the monitoring service to run this task_id
            #     typer.echo(f"Task {task_id} triggered manually.")
            ```
*   **Input Validation:** Use Typer/Click's built-in type checking and validation, or add custom validators for complex inputs like cron strings or part definitions.

### Q5.2: Streamlit UI Patterns for Task Management

Streamlit can provide a user-friendly graphical interface for these operations.

*   **Displaying Tasks:**
    *   Use `st.dataframe` or `st.table` to list monitoring tasks with key information (name, active status, schedule, recipients, last run, next run). (Perplexity output)
    *   Allow sorting and searching/filtering if the number of tasks can grow.
*   **CRUD Forms:**
    *   Use `st.form` for creating and editing tasks.
    *   **Complex Inputs:**
        *   **Cron Schedules:** `st.text_input` for the cron string. Provide examples or a link to a cron syntax helper. Real-time validation feedback using `croniter` would be beneficial. (Perplexity output)
        *   **Parts List:** This is more complex. Options:
            *   `st.text_area` for a simple comma/line-separated format (e.g., "PartA:10, PartB:5"). Requires robust parsing and validation on the backend.
            *   `st.file_uploader` for users to upload a small CSV or JSON file defining the parts and quantities.
            *   A dynamic form using `st.experimental_add_rows` (if suitable for this version of Streamlit) or custom logic to add/remove part-quantity pairs.
            *   For editing, pre-fill the form with existing data.
        *   **Recipients:** `st.text_area` or multiple `st.text_input` fields for email addresses, with validation.
    *   **Activation/Deactivation:** Use `st.checkbox` or `st.toggle` next to each task in the list, or an "Edit" form with an activation toggle.
    *   **Manual Trigger:** A "Run Now" button next to each task.
*   **Status Updates:** The UI should reflect the current state of tasks. This might require the Streamlit app to periodically re-fetch task data or use techniques like `st.experimental_rerun` if the backend can notify of changes (more complex). For simpler cases, a manual refresh button.

### Q5.3: Querying and Displaying Task State

Both CLI and UI need to access and display task state information.

*   **Information to Display:**
    *   `id`: Unique identifier.
    *   `name`: User-defined name.
    *   `active`: Boolean status.
    *   `cron_schedule`: The schedule string.
    *   `recipients`: List of email addresses.
    *   `notify_condition`: "always" or "on_change".
    *   `last_hash` (if `on_change`).
    *   **Dynamic State (from scheduler/logs):**
        *   `last_run_time`: Timestamp of the last execution.
        *   `last_run_status`: Success, failure (with error message snippet).
        *   `next_run_time`: Calculated next execution time based on the cron schedule. (APScheduler jobs have a `next_run_time` attribute).
*   **Accessing State:**
    *   Static configuration (name, schedule, etc.) comes from [`presets.json`](presets.json) via `PresetsManager`.
    *   Dynamic state (last run, next run) would typically come from the `MonitoringService` (which interfaces with `APScheduler`). The scheduler itself often stores job metadata, including `next_run_time`. `last_run_time` and `status` might need to be logged by the tasks and then queried from logs or a simple status store.
    *   Celery provides more built-in tools for inspecting task states if it were used. (Perplexity output [1])

### Q5.4: Consistency Between CLI and UI

This is crucial for a good user experience.

*   **Single Source of Truth:** All task definitions and static configurations must reside in one place (`presets.json`, managed by `PresetsManager`). Both CLI and UI must read from and write to this single source.
*   **Shared Business Logic:** The core logic for adding, updating, deleting, activating, and deactivating tasks should be encapsulated (e.g., in `PresetsManager` and `MonitoringService`). Both CLI commands and UI actions should call this shared logic. This avoids duplicating validation and operational logic.
*   **State Synchronization (for dynamic state):**
    *   If the `MonitoringService` runs as a separate process, the CLI and UI need a way to query it for dynamic task states (e.g., via an API, a shared database/cache if the scheduler updates it, or inter-process communication).
    *   For Streamlit, this might involve periodic polling or a refresh mechanism to update the displayed dynamic task information.
*   **Eventual Consistency:** Be aware that there might be slight delays in UI updates if changes are made via CLI, depending on the refresh/polling strategy.

The Perplexity output mentions that for Celery-based systems, Celery itself provides inspection capabilities (`celery.app.control.Inspect`) which can be leveraged by management interfaces. If using APScheduler, similar introspection capabilities or custom status tracking would be needed for dynamic state. The overall approach should ensure that task decomposition and management (Perplexity result [2]) are handled consistently across interfaces.

## 6. Overall Architecture

This section addresses research questions Q6.1, Q6.2, Q6.3, Q6.4, and Q6.5 concerning the architectural design of the new `MonitoringService` and `EmailService`, their integration with existing modules, and considerations for testability and scalability. The findings are based on a Perplexity AI search conducted on 2025-05-14.

### Q6.1: Structuring `MonitoringService` and `EmailService`

*   **`MonitoringService`:**
    *   **Responsibilities:**
        *   Managing the lifecycle of scheduled monitoring tasks (loading from `PresetsManager`, scheduling with `APScheduler` or a similar library).
        *   Executing the checks for each task (delegating to the `Calculator`).
        *   Implementing the `on_change` logic (hashing results, comparing with `last_hash`).
        *   Coordinating notifications (triggering `EmailService` or other observers).
    *   **Internal Components (Conceptual, based on Perplexity output):**
        *   Scheduler instance (e.g., `APScheduler.BackgroundScheduler`). (Perplexity result [3], [5] - general background task scheduling)
        *   Logic for loading and parsing task definitions from `PresetsManager`.
        *   A mechanism to dispatch tasks to the `Calculator`.
        *   Storage/retrieval for `last_hash` values (likely via `PresetsManager`).
        *   Interaction with observers for notifications (see Observer Pattern below).
    *   **Example (Conceptual Structure, from Perplexity output):**
        ```python
        # class MonitoringService:
        #     def __init__(self, scheduler, calculator, presets_manager, email_service, observers=None):
        #         self.scheduler = scheduler
        #         self.calculator = calculator
        #         self.presets_manager = presets_manager
        #         self.email_service = email_service # Or more general notification dispatcher
        #         self.observers = observers if observers else [] # For Observer pattern
        #         # self.active_jobs = {} # To keep track of scheduled APScheduler jobs

        #     def start(self):
        #         # Load tasks from presets_manager
        #         # Schedule active tasks using self.scheduler
        #         # self.scheduler.start()
        #         pass

        #     def run_check(self, task_id):
        #         # Get task config
        #         # Perform calculation using self.calculator
        #         # Perform on_change logic
        #         # If notification needed, call self.email_service.send_alert(...) or notify observers
        #         pass
        ```

*   **`EmailService`:**
    *   **Responsibilities:**
        *   Generating email content (HTML and plain-text) using templates (e.g., `Jinja2`).
        *   Handling SMTP configuration (loaded from `Config`).
        *   Sending emails via SMTP, including error handling and retries for sending.
    *   **Internal Components (Conceptual, based on Perplexity output):**
        *   Template engine instance (e.g., `Jinja2.Environment`).
        *   SMTP connection management logic.
    *   **Example (Conceptual Structure, from Perplexity output):**
        ```python
        # class EmailService:
        #     def __init__(self, config, template_engine):
        #         self.config = config # For SMTP settings
        #         self.template_engine = template_engine

        #     def send_monitoring_report(self, recipients, subject, calculation_result_data):
        #         # html_body = self.template_engine.render("email_template.html", **calculation_result_data)
        #         # text_body = self.template_engine.render("email_template.txt", **calculation_result_data)
        #         # Connect to SMTP server using self.config
        #         # Send multipart email
        #         pass
        ```

*   **Decoupling:**
    *   `MonitoringService` should not directly know the details of email formatting or sending. It should delegate to `EmailService` or a more general notification dispatcher.
    *   `EmailService` should be configurable and not tied to specific monitoring logic.

### Q6.2: Integration with Existing Modules

*   **`PresetsManager`:**
    *   `MonitoringService` will use `PresetsManager` to load monitoring task definitions (including `cron_schedule`, `parts`, `recipients`, `notify_condition`, `last_hash`) and to save updated `last_hash` values.
    *   This interaction can be achieved via **Dependency Injection**: `PresetsManager` instance is passed to `MonitoringService` upon initialization. (Perplexity output)
*   **`Calculator`:**
    *   `MonitoringService` will use `Calculator` to perform the actual parts list availability check for each monitoring task.
    *   The `Calculator`'s `calculate_part_availability` (or similar method) will be called with the parts list from the monitoring task.
    *   Dependency Injection is also suitable here.
*   **`Config`:**
    *   `EmailService` will use `Config` to retrieve SMTP server settings, sender address, admin email recipients, and the global email enabled flag.
    *   `MonitoringService` might use `Config` for global settings related to its operation (e.g., default retry policies if not task-specific).
    *   Dependency Injection for `Config` instances.

### Q6.3: Design Patterns

*   **Dependency Injection (DI):**
    *   As mentioned, inject dependencies like `PresetsManager`, `Calculator`, `Config`, `scheduler`, `template_engine` into `MonitoringService` and `EmailService`.
    *   This improves modularity, testability (by allowing mock dependencies), and flexibility.
    *   A simple DI container or manual injection can be used. (Perplexity output)
*   **Strategy Pattern:**
    *   If different types of checks or calculation logic are anticipated in the future, the `Calculator`'s role or the check execution within `MonitoringService` could use the Strategy pattern. Different "check strategies" or "calculation strategies" could be implemented. (Perplexity output)
    *   The `EmailService` could also use a strategy pattern for different delivery methods (e.g., SMTP, SendGrid API, LogToFileEmailStrategy for testing).
*   **Observer Pattern:**
    *   Ideal for the `on_change` notification logic. `MonitoringService` (or a dedicated `ChangeDetector` component) acts as the "Subject." When a significant change is detected for a task, it notifies all registered "Observers."
    *   `EmailService` (or a specific `EmailAlertObserver`) would be one such observer. Other observers could be for Slack notifications, logging to a specific system, etc. (Perplexity output)
    *   This decouples the change detection from the specific notification actions.
    *   **Example (Conceptual Observer, from Perplexity output):**
        ```python
        # class ChangeDispatcher: # Subject
        #     def __init__(self):
        #         self._observers = []
        #     def attach(self, observer): self._observers.append(observer)
        #     def detach(self, observer): self._observers.remove(observer)
        #     def notify(self, task_id, changes_data):
        #         for observer in self._observers:
        #             observer.update(task_id, changes_data)

        # class EmailAlertObserver: # Observer
        #     def __init__(self, email_service): self.email_service = email_service
        #     def update(self, task_id, changes_data):
        #         # self.email_service.send_change_notification(task_id, changes_data)
        #         pass
        ```

### Q6.4: Testability

*   **Unit Tests:**
    *   DI makes unit testing easier. Mock dependencies (e.g., `Mock(Calculator)`, `Mock(EmailService)`) to test the logic of `MonitoringService` in isolation.
    *   Test `EmailService` by mocking the `smtplib` interactions or the template engine.
    *   Test `on_change` logic with various data inputs and expected hash/diff results.
*   **Integration Tests:**
    *   Test the interaction between `MonitoringService`, `Calculator`, and `PresetsManager` (perhaps with a temporary `presets.json`).
    *   Test the full flow from scheduling a task to (mocked) email sending.
*   **Mocking External Services:** Use libraries like `unittest.mock` or `pytest-mock` extensively. (Perplexity output)
*   **Component Isolation:** Design services with clear interfaces to facilitate isolated testing. (Perplexity output)

### Q6.5: Scalability Considerations

*   **Initial Phase (In-process `APScheduler`):**
    *   Suitable for a moderate number of tasks and when the application runs as a single process. (Perplexity output)
    *   The `BackgroundScheduler` runs in a thread within the main application process.
*   **Scaling to a Distributed Task Queue (e.g., Celery):**
    *   If the number of tasks grows significantly, or if checks become long-running and resource-intensive, or if high availability is required, moving to a distributed task queue like Celery (with Redis or RabbitMQ as a broker) is a common scaling path. (Perplexity output [2], [3])
    *   **Changes Required:**
        *   `MonitoringService` would schedule tasks by sending messages to the Celery queue instead of directly using `APScheduler`.
        *   `celery beat` would be used for cron-like scheduling of Celery tasks.
        *   The actual check execution logic would be encapsulated in Celery tasks, run by separate worker processes.
        *   This distributes the load and allows scaling workers independently.
    *   **Monitoring Distributed Tasks:** Tools like `Flower` can be used to monitor Celery tasks and workers. (Perplexity output [2])
*   **Database for Task State:** For a more scalable solution, especially with distributed tasks, storing task state (last run, status, `last_hash`) in a database rather than just [`presets.json`](presets.json) might become necessary.
*   **API-based Communication:** If `MonitoringService` becomes a separate microservice, communication with other parts of the application (e.g., for UI updates) might shift to API calls. (Perplexity output [4] - general concept of returning results from background jobs)
*   **Observability Tools:** For larger scale, integrate with distributed tracing (e.g., OpenTelemetry, Jaeger, Zipkin) and monitoring/logging platforms (e.g., Prometheus, Grafana, ELK, SigNoz). (Perplexity output [1], [5])

The architecture should be designed with modularity in mind from the start, using patterns like DI, to make a future transition to a distributed model smoother if needed.

## 7. Security Considerations

This section addresses research questions Q7.1, Q7.2, Q7.3, and Q7.4 concerning security best practices relevant to the automated monitoring feature. The findings are based on a Perplexity AI search conducted on 2025-05-14.

### Q7.1: Handling API Keys and Email Credentials

*   **Environment Variables & `.env` Files:**
    *   Store all sensitive credentials (API keys, email passwords, InvenTree tokens) in environment variables. (Perplexity result)
    *   Use `.env` files for local development (loaded with `python-dotenv`) and ensure `.env` is in `.gitignore`. (Perplexity result)
    *   **Example (from Perplexity output):**
        ```python
        import os
        # from dotenv import load_dotenv
        # load_dotenv() # Load .env file
        # api_key = os.getenv("EXTERNAL_API_KEY")
        # email_password = os.getenv("EMAIL_PASSWORD")
        ```
*   **Vault Solutions:** For production environments, especially with more complex secret management needs, consider using dedicated vault solutions like HashiCorp Vault or cloud provider services (e.g., AWS Secrets Manager, Azure Key Vault). (Perplexity result [2], [3])
*   **Secure Key Generation:** If generating keys or secrets within the application, use Python's `secrets` module for cryptographically strong random numbers, not the `random` module. (Perplexity result [3])
    *   Example: `secrets.token_urlsafe(32)`
*   **Key Rotation:** Implement regular rotation of API keys and credentials (e.g., quarterly). Automate this process where possible. (Perplexity result [3], [5])
*   **Principle of Least Privilege:** Ensure API keys and credentials have only the minimum necessary permissions.
*   **Secure Transmission (TLS/HTTPS):** Always transmit credentials over encrypted channels (HTTPS for API calls, SMTP with TLS/SSL for email). Enforce certificate verification. (Perplexity result [3])
*   **Avoid Client-Side Exposure:** Never embed API keys or sensitive credentials in client-side code (e.g., Streamlit frontend if it makes direct calls, though it typically runs server-side Python).
*   **Logging:** Ensure credentials are never logged.

### Q7.2: Validating User-Defined Cron Strings

User-supplied cron strings can pose a risk if not handled carefully (e.g., overly frequent schedules causing denial-of-service).

*   **Syntax Validation:** Use a library like `croniter` to validate the syntax of cron strings. (Perplexity result)
    *   **Example (from Perplexity output):**
        ```python
        from croniter import croniter
        # def is_valid_cron(cron_str):
        #     return croniter.is_valid(cron_str)
        ```
*   **Frequency Restrictions:** Implement business logic to restrict the frequency of scheduled tasks. For example, do not allow tasks to run more frequently than every 15 minutes or every hour, depending on resource impact. (Perplexity result)
    *   This can be checked by expanding the cron string for a given period and analyzing the intervals.
*   **Resource Limits:** Consider overall limits on the number of active tasks per user or globally to prevent system overload.
*   **Input Sanitization/Whitelisting:** While `croniter` handles syntax, ensure no command injection is possible if cron strings were ever used to construct shell commands (not the case here, as it's for an internal scheduler, but a general principle).
*   **Logging and Monitoring:** Log the creation and modification of cron schedules, and monitor job execution frequencies.

### Q7.3: Preventing XSS in HTML Emails from User Data

If user-defined data (e.g., part names, monitoring list names from `presets.json`) is included in HTML emails, Cross-Site Scripting (XSS) is a risk.

*   **HTML Escaping/Sanitization:**
    *   **Jinja2 Autoescaping:** When using Jinja2 for HTML email templates, ensure autoescaping is enabled (it is by default). This will escape special HTML characters from variables inserted into the template. (Perplexity result)
        *   Example: `{{ user_provided_name | e }}` or simply `{{ user_provided_name }}` if autoescape is on.
    *   **`bleach` Library:** For cases where you need to allow some HTML from users but want to sanitize it, use `bleach`. It can strip disallowed tags and attributes. (Perplexity result)
        *   **Example (from Perplexity output):**
            ```python
            from bleach import clean
            # allowed_tags = ['b', 'i', 'p', 'br']
            # allowed_attributes = {'a': ['href', 'title']} # Example
            # safe_html_from_user = clean(user_input, tags=allowed_tags, attributes=allowed_attributes, strip=True)
            ```
*   **Context-Aware Escaping:** Be mindful of the context where data is inserted (HTML body, HTML attributes, JavaScript, CSS). Different contexts require different escaping strategies. Jinja2's autoescaping is generally good for HTML body content.
*   **Content Security Policy (CSP):** While CSP support in email clients is limited, consider setting a restrictive CSP header for emails if possible, to limit what resources can be loaded or executed.
*   **Validate URLs:** If including user-provided URLs in emails, validate them to ensure they point to expected protocols (e.g., `http`, `https`) and domains if necessary.

### Q7.4: Secure InvenTree API Credential Management

If the monitoring feature requires specific InvenTree API credentials beyond what the existing `api_client.py` handles (which seems to use environment variables for server/token):

*   **Token-Based Authentication:** InvenTree uses token-based authentication. These tokens should be treated as sensitive credentials.
*   **Storage:** Store InvenTree API tokens securely using the same methods as other API keys/passwords (environment variables, vault solutions). (Perplexity result)
*   **Transmission:** Always use HTTPS when communicating with the InvenTree API.
*   **Scope/Permissions:** If InvenTree supports scoped tokens or user roles with specific permissions, ensure the token used by the monitoring service has only the necessary read permissions for parts, stock, BOMs, etc. It should not have write permissions unless absolutely required for a feature (not indicated in current specs).
*   **Token Rotation:** If InvenTree supports programmatic token rotation or if tokens have an expiry, implement a mechanism to refresh or rotate them. (Perplexity result)
*   **Audit Logging:** Monitor InvenTree's audit logs (if available) for API access patterns from the monitoring service to detect any anomalous behavior.

By adhering to these security best practices, the application can significantly reduce its vulnerability to common threats. Regular security reviews and keeping dependencies updated (e.g., using `pip-audit` or GitHub Dependabot) are also crucial. (Perplexity result [1], [3], [5])