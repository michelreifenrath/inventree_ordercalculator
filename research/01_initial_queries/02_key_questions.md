# Key Research Questions

Based on the project scope and the feature specifications ([`docs/feature_specs/automated_monitoring_spec.md`](docs/feature_specs/automated_monitoring_spec.md:1)), the following key questions will guide the research:

## 1. Scheduling Mechanisms

*   **Q1.1:** Is `APScheduler` the most suitable Python library for the project's cron-like job scheduling needs, considering robustness, ease of use, cron string parsing capabilities, and error handling? What are its key strengths and weaknesses in this context?
*   **Q1.2:** What are viable alternatives to `APScheduler` (e.g., `schedule`, `Celery` with `Redis`/`RabbitMQ`, `arq`, system cron + script)? Under what circumstances would they be preferable, and what are their trade-offs (complexity, dependencies, features)?
*   **Q1.3:** What are best practices for parsing and validating cron strings within a Python application using `APScheduler` or alternatives? How can common parsing errors be handled gracefully?
*   **Q1.4:** How should the scheduling service handle errors during job execution (e.g., if a scheduled task itself fails)? What are `APScheduler`'s (or alternatives') built-in mechanisms for this, and are they sufficient?

## 2. Email Generation and Sending

*   **Q2.1:** What are the current best-practice Python libraries for generating both HTML (with tables and styling) and plain-text multipart emails? (e.g., `smtplib`, `email.mime`, `Jinja2` for templating, `premailer` for inlining CSS).
*   **Q2.2:** What are secure and reliable methods for configuring SMTP settings (`EMAIL_SMTP_SERVER`, `PORT`, `TLS/SSL`, `USERNAME`, `PASSWORD`, `SENDER_ADDRESS`) in a Python application, particularly when using environment variables and a `.env` file?
*   **Q2.3:** How should sensitive credentials like `EMAIL_PASSWORD` be handled to prevent exposure, both in configuration and in memory during runtime?
*   **Q2.4:** What are robust error handling and retry mechanisms (e.g., exponential backoff) for SMTP connection failures, authentication errors, and sending timeouts? How can `ADMIN_EMAIL_RECIPIENTS` be reliably notified of persistent email system failures?
*   **Q2.5:** What considerations are there for email deliverability (e.g., SPF, DKIM records, avoiding spam filters), and how much of this can be influenced at the application level versus server configuration?

## 3. Change Detection (`on_change` logic)

*   **Q3.1:** What are the most effective and efficient hashing algorithms (e.g., MD5, SHA256) for generating a `last_hash` from complex Python data structures (specifically, the "Fehlmengenliste" and "kritische Teile unter Schwellenwert" derived from calculation results)? What are the trade-offs (collision risk, performance)?
*   **Q3.2:** How can the relevant parts of the calculation result be reliably serialized into a canonical string representation before hashing to ensure consistent hash values for semantically identical results?
*   **Q3.3:** Are there alternative change detection methods to hashing (e.g., deep comparison of data structures) that might be more suitable or offer advantages in terms of accuracy or minimizing false positives/negatives for this specific use case? What are their performance implications?
*   **Q3.4:** How should the `last_hash` be updated in [`presets.json`](presets.json) to ensure atomicity and prevent race conditions if multiple processes or threads could potentially access it (though likely single-threaded in this context initially)?

## 4. Error Handling and Logging

*   **Q4.1:** What are best practices for comprehensive logging in a scheduled task environment? What information should be logged at different levels (DEBUG, INFO, WARNING, ERROR) for API interactions, calculations, email sending, and configuration issues?
*   **Q4.2:** What are effective retry strategies (e.g., fixed interval, exponential backoff with jitter) for transient errors like InvenTree API unavailability or temporary email sending issues? Which Python libraries facilitate this (e.g., `tenacity`)?
*   **Q4.3:** How should persistent errors (after retries) be handled? Specifically, for API unavailability and email sending failures, what is the best way to notify `ADMIN_EMAIL_RECIPIENTS`?
*   **Q4.4:** How should configuration errors (invalid cron, bad email config) be detected at startup or task load, and how should they be reported to admins and handled by the system (e.g., automatic deactivation of the faulty task)?

## 5. Task Management (CLI/UI)

*   **Q5.1:** What are common and user-friendly CLI design patterns for CRUD operations, activation/deactivation, and manual triggering of background tasks (e.g., using Typer/Click)?
*   **Q5.2:** What are effective ways to present and manage these tasks in a Streamlit web UI? How can user input for complex fields like `parts` (list of dicts) and `cron_schedule` be handled gracefully?
*   **Q5.3:** How can the state of tasks (e.g., last run time, next run time, status) be queried and displayed effectively in both CLI and UI?
*   **Q5.4:** What considerations are needed for ensuring consistency between CLI and UI operations, given they both interact with `PresetsManager`?

## 6. Overall Architecture

*   **Q6.1:** What is an optimal way to structure the `MonitoringService` (handling scheduling, task execution, `on_change` logic) and `EmailService` (handling email templating, configuration, sending)? How should they be decoupled?
*   **Q6.2:** How should these new services interact with existing modules like `PresetsManager` (for task definitions), `Calculator` (for running checks), and `Config` (for email and global settings)? What interfaces or patterns (e.g., dependency injection) would be beneficial?
*   **Q6.3:** What design patterns (e.g., Observer, Strategy) could be useful for managing different `notify_condition` behaviors or different types of checks in the future?
*   **Q6.4:** How can the architecture be designed for testability, allowing unit and integration tests for scheduling, calculation, change detection, and email sending logic?
*   **Q6.5:** What are considerations for scalability if the number of monitoring tasks grows significantly? (e.g., moving from in-process `APScheduler` to a distributed task queue).

## 7. Security Considerations

*   **Q7.1:** What are the specific security best practices for storing and accessing `EMAIL_PASSWORD` and any potential InvenTree API keys/tokens when managed via environment variables and `.env` files? (e.g., file permissions for `.env`, avoiding logging credentials).
*   **Q7.2:** Are there risks associated with user-defined cron strings? How can they be validated to prevent potential abuse or system instability?
*   **Q7.3:** What are the security implications of parsing and rendering user-defined data (e.g., part names from `presets.json`) in HTML emails? How can cross-site scripting (XSS) vulnerabilities be prevented (e.g., proper escaping)?
*   **Q7.4:** If InvenTree API interactions require authentication for this feature, what are the best practices for managing those credentials securely within the application?