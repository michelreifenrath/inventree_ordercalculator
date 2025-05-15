# 1. Executive Summary

## Overview of the Research

This report details the findings of comprehensive research conducted to determine best practices and optimal implementation strategies for an "Automated Parts List Monitoring and Email Notification" feature for the InvenTree Order Calculator project. The research was guided by the detailed functional and technical specifications provided in [`docs/feature_specs/automated_monitoring_spec.md`](./../../docs/feature_specs/automated_monitoring_spec.md).

The investigation covered seven key areas:
1.  **Scheduling Mechanisms** for cron-like job execution.
2.  **Email Generation and Sending** practices.
3.  **Change Detection (`on_change` logic)** for monitoring results.
4.  **Error Handling and Logging** strategies.
5.  **Task Management (CLI/UI)** patterns.
6.  **Overall System Architecture** for new and existing components.
7.  **Security Considerations** for credentials and data.

The research leveraged Perplexity AI for targeted queries and drew upon established Python best practices and library documentation.

## Key Findings and Insights

The research confirmed the suitability of many technologies and approaches outlined in the initial specification while providing deeper insights and alternative considerations:

*   **Scheduling:** `APScheduler` is appropriate for initial in-process scheduling, with `Celery` as a viable path for future scalability. Robust cron string validation (`croniter`) is essential.
*   **Email:** A combination of `Jinja2` for templating, `premailer` for CSS inlining, and `smtplib` for secure SMTP communication (via environment variables for credentials) is recommended. Deliverability (SPF, DKIM, DMARC) is crucial.
*   **Change Detection:** Canonical JSON serialization (`json.dumps` with `sort_keys=True`) of relevant calculation results, followed by SHA256 hashing, is effective for the `on_change` logic.
*   **Error Handling & Logging:** Structured logging (`logging` module + `structlog`), along with `tenacity` for retry mechanisms (exponential backoff), forms a resilient error handling strategy. Admin notifications for persistent issues are critical.
*   **Task Management:** `Typer` for CLI and Streamlit for UI can provide consistent task management by interacting with a central `PresetsManager`.
*   **Architecture:** A modular design using Dependency Injection, and patterns like Observer (for notifications) and Strategy (for flexible logic), will enhance maintainability and testability.
*   **Security:** Secure credential management (environment variables, vaults for production), input validation (cron strings, user data for emails), and output escaping (HTML emails) are paramount.

## Core Recommendations

The report strongly recommends:

1.  **Adopting `APScheduler` initially** for scheduling, with `croniter` for validation.
2.  Implementing a robust **`EmailService`** using `Jinja2`, `premailer`, and secure `smtplib` practices.
3.  Using **SHA256 hashing of canonically serialized JSON** for change detection.
4.  Establishing **comprehensive structured logging** and using `tenacity` for retries.
5.  Developing **CLI (`Typer`) and Streamlit UI** interfaces that interact with `PresetsManager` and a new `MonitoringService`.
6.  Designing the **`MonitoringService` and `EmailService` with clear separation of concerns**, using Dependency Injection and the Observer pattern for notifications.
7.  Prioritizing **security best practices** for credentials, cron strings, and email content.

## Conclusion

The research provides a solid foundation of best practices and actionable strategies for developing the automated monitoring and notification feature. By implementing the recommendations outlined, the InvenTree Order Calculator can gain a valuable, robust, and secure enhancement that meets the specified requirements and allows for future scalability. The subsequent phases of detailed design and pseudocode development should be well-informed by these findings.