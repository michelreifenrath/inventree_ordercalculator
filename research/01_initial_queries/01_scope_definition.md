# Research Scope Definition: Automated Parts List Monitoring & Email Notification

## 1. Project Goal

To conduct deep research on best practices and optimal implementation strategies for an "automated parts list monitoring and email notification" feature within the InvenTree Order Calculator project. The research aims to provide actionable recommendations to guide the subsequent pseudocode and implementation phases.

## 2. Feature Overview (Based on Provided Specifications)

The core functionality involves:
*   Users defining specific parts lists with quantities to be monitored.
*   Persistent storage of these monitoring lists, including configuration for scheduling, recipients, and notification conditions (always vs. on_change).
*   Automated, scheduled checks of these lists using the existing calculation logic.
*   Generation and sending of email notifications (HTML and plain-text) containing the check results.
*   Robust error handling, logging, and admin notifications for system issues.
*   Management of monitoring tasks via CLI and a Streamlit web UI.

## 3. Key Research Areas (as per user request and specifications)

The research will focus on the following seven key areas:

1.  **Scheduling Mechanisms:**
    *   Evaluation of Python libraries for cron-like job scheduling (confirming `APScheduler` or suggesting alternatives).
    *   Robust parsing of cron strings.
    *   Error handling within the scheduling mechanism.
2.  **Email Generation and Sending:**
    *   Best practices for generating HTML and plain-text emails in Python.
    *   Secure and reliable SMTP configuration and sending.
    *   Handling of sensitive credentials (e.g., `EMAIL_PASSWORD`).
    *   Error/retry logic for email sending.
3.  **Change Detection (`on_change` logic):**
    *   Effective methods for hashing or comparing complex data structures (calculation results, specifically "Fehlmengenliste" and "kritische Teile unter Schwellenwert" as per spec) to detect significant changes.
    *   Minimizing false positives/negatives.
4.  **Error Handling and Logging:**
    *   Comprehensive strategies for logging and handling errors (API unavailability, calculation issues, email failures, configuration problems).
    *   Retry mechanisms (e.g., exponential backoff).
    *   Admin notifications for critical system errors.
5.  **Task Management (CLI/UI):**
    *   Common patterns for managing background tasks (CRUD, activation/deactivation, manual triggering).
    *   Specific considerations for CLI (Typer/Click) and web UI (Streamlit) integration.
6.  **Overall Architecture:**
    *   Structuring new components (`MonitoringService`, `EmailService`).
    *   Integration with existing modules (`PresetsManager`, `Calculator`, `Config`).
    *   Ensuring maintainability, testability, and scalability.
7.  **Security Considerations:**
    *   Handling API keys for InvenTree (if required for this feature beyond current scope).
    *   Secure storage and access of email credentials.
    *   Protection of user-defined data in `presets.json`.

## 4. Deliverables

The primary deliverable will be a structured research report organized into the predefined `research/` folder structure, culminating in a `05_final_report/` containing:
*   Executive Summary
*   Methodology
*   Detailed Findings for each research area
*   Analysis of findings
*   Actionable Recommendations
*   References/Citations

## 5. Constraints and Considerations

*   The solution must be implemented in Python.
*   The existing project structure and components (Streamlit UI, `PresetsManager`, `Calculator`, `Config`) should be leveraged.
*   The solution should adhere to the non-functional requirements outlined in the specification (performance, security, scalability, reliability, maintainability).
*   The specification already suggests `APScheduler` and a hashing mechanism for `on_change` logic; the research should validate these choices or propose justified alternatives.