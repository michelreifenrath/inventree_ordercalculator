# 3. Detailed Findings

This section presents the detailed findings of the research, organized by the seven key areas investigated for the "Automated Parts List Monitoring and Email Notification" feature. The comprehensive compilation of these findings, including summaries of Perplexity AI search results and conceptual code examples, is located in:

*   **[`research/02_data_collection/01_primary_findings.md`](./../02_data_collection/01_primary_findings.md)**

Below is a summary of the topics covered within that document, with direct links to each subsection for easy navigation.

## 3.1. Scheduling Mechanisms

Covers the suitability of `APScheduler`, alternatives like `Celery`, `schedule`, and `ARQ`, best practices for cron string parsing and validation (using `croniter`), and error handling within scheduling mechanisms.

*   [Link to Detailed Findings on Scheduling Mechanisms](./../02_data_collection/01_primary_findings.md#1-scheduling-mechanisms)

## 3.2. Email Generation and Sending

Details best practices for generating multipart HTML and plain-text emails (`smtplib`, `email.mime`, `Jinja2` for templating, `premailer` for CSS inlining), secure SMTP configuration using environment variables, handling of sensitive credentials, error/retry logic for SMTP failures, and considerations for email deliverability (SPF, DKIM, DMARC).

*   [Link to Detailed Findings on Email Generation and Sending](./../02_data_collection/01_primary_findings.md#2-email-generation-and-sending)

## 3.3. Change Detection (`on_change` logic)

Explores effective methods for hashing (MD5, SHA256) complex data structures (like calculation results), the importance of canonical serialization (e.g., `json.dumps` with `sort_keys=True`), strategies for minimizing false positives/negatives, and alternative change detection methods like `DeepDiff`.

*   [Link to Detailed Findings on Change Detection](./../02_data_collection/01_primary_findings.md#3-change-detection-on_change-logic)

## 3.4. Error Handling and Logging

Outlines comprehensive strategies for logging (`logging` module, `structlog`), implementing retry mechanisms (`tenacity` library with exponential backoff) for transient errors (API unavailability, email sending failures), handling persistent errors including admin notifications, and managing configuration errors (validation, task deactivation).

*   [Link to Detailed Findings on Error Handling and Logging](./../02_data_collection/01_primary_findings.md#4-error-handling-and-logging)

## 3.5. Task Management (CLI/UI)

Discusses common patterns for managing background tasks (CRUD operations, activation/deactivation, manual triggering) via both Command Line Interfaces (using `Typer`/`Click`) and web UIs (specifically `Streamlit`). It also covers querying task state (last run, next run, status) and ensuring consistency between CLI and UI.

*   [Link to Detailed Findings on Task Management (CLI/UI)](./../02_data_collection/01_primary_findings.md#5-task-management-cliui)

## 3.6. Overall Architecture

Focuses on structuring the new `MonitoringService` and `EmailService` components, their integration with existing project modules (`PresetsManager`, `Calculator`, `Config`), the application of relevant design patterns (Dependency Injection, Observer, Strategy), and considerations for testability and scalability (e.g., evolving from in-process `APScheduler` to a distributed task queue like `Celery`).

*   [Link to Detailed Findings on Overall Architecture](./../02_data_collection/01_primary_findings.md#6-overall-architecture)

## 3.7. Security Considerations

Addresses specific security best practices for handling API keys and email credentials (via environment variables, `.env` files, and vault solutions), validating user-defined cron strings to prevent abuse, preventing Cross-Site Scripting (XSS) in HTML emails generated from user data, and securely managing InvenTree API credentials.

*   [Link to Detailed Findings on Security Considerations](./../02_data_collection/01_primary_findings.md#7-security-considerations)

Please refer to the linked `01_primary_findings.md` file for the complete details gathered during the data collection phase.