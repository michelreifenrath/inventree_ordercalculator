# Analysis: Knowledge Gaps

This document identifies potential knowledge gaps or areas where the initial research (`research/02_data_collection/01_primary_findings.md`) might lack specific, actionable details directly applicable to the InvenTree Order Calculator project, or where assumptions were made by the Perplexity AI during its searches.

## 1. Specifics of "Fehlmengenliste" and "Kritische Teile" for Hashing (Q3.1, Q3.2)

*   **Gap:** While the research covers general techniques for hashing complex data structures and canonical serialization (e.g., using `json.dumps` with `sort_keys=True`), the *exact structure* of the "Fehlmengenliste" (shortages list) and "kritische Teile unter Schwellenwert" (critical parts below threshold) as output by the existing `Calculator` module is not detailed in the research.
*   **Impact:** The optimal serialization strategy for hashing depends on the precise data types and structure of these specific outputs. For example, if they contain `Decimal` types, custom objects, or specific `datetime` formats, `json.dumps` might need a custom encoder.
*   **Resolution:** Before implementation, the exact data structure of these elements needs to be confirmed from the `Calculator`'s output to ensure the chosen serialization and hashing method is robust and consistent.

## 2. InvenTree API Interaction Details for Monitoring (Q7.4, Q4.1)

*   **Gap:** The research provides general advice on secure API credential management. However, it doesn't detail:
    *   If the *current* InvenTree API client (`api_client.py`) and its existing authentication method (likely environment-variable-based token) are sufficient for the *monitoring tasks*.
    *   Specific API endpoints that will be hit by the `Calculator` during a monitoring check and their rate-limiting or performance characteristics from InvenTree's side.
    *   Specific error codes or responses from the InvenTree API that should be treated as transient vs. persistent errors.
*   **Impact:** Assumptions about API interaction (e.g., that existing auth is fine, general retry logic applies) might overlook InvenTree-specific behaviors or requirements.
*   **Resolution:** Review `api_client.py` and InvenTree API documentation in the context of frequent, automated checks. Identify key endpoints and their expected behaviors/error modes.

## 3. Streamlit UI - Dynamic Updates and Task State Display (Q5.2, Q5.3)

*   **Gap:** The research mentions general Streamlit patterns (forms, tables) but lacks depth on:
    *   The best way to display *dynamic* task state (last run, next run, status) that changes in a background `MonitoringService` process. Streamlit's typical execution model might require specific strategies (e.g., `st.experimental_rerun` with a polling mechanism, or a more complex backend communication if the service is truly separate).
    *   User experience for inputting/editing the `parts` list within a Streamlit form, which is a list of dictionaries. The research mentions `st.text_area` or file uploads, but a more integrated solution might be desired.
*   **Impact:** UI implementation might be less smooth or require more trial-and-error.
*   **Resolution:** Further, targeted investigation or prototyping of Streamlit components for dynamic data display from a background service and for handling list-of-dicts input might be needed during the UI design/pseudocode phase.

## 4. `PresetsManager` Atomicity and Concurrency (Q3.4)

*   **Gap:** The research assumes that `PresetsManager` interactions (especially saving `last_hash`) are likely single-threaded in the context of a job. While this is a reasonable assumption for `APScheduler` running jobs serially for a given task ID, the exact guarantees of `PresetsManager` regarding atomic writes to `presets.json` (e.g., write-to-temp-then-rename) are not confirmed by the research.
*   **Impact:** Potential (though low) risk of `presets.json` corruption if an error occurs mid-write, or if, in a future scaled-up scenario, multiple processes could attempt to write.
*   **Resolution:** Review `PresetsManager` implementation to confirm its file-saving strategy. For the current scope, this is likely a minor concern.

## 5. Detailed Structure of `MonitoringService` and `EmailService` Startup/Shutdown

*   **Gap:** While architectural roles are discussed, the specifics of how the `MonitoringService` (especially if it runs `APScheduler` in a background thread) is started, managed (e.g., kept alive), and gracefully shut down within the main application (CLI or Streamlit app context) are not deeply explored. Similarly for the `EmailService` if it maintains any persistent connections or state (though unlikely for a simple SMTP sender).
*   **Impact:** Could lead to issues with resource management or zombie processes if not handled correctly during application lifecycle.
*   **Resolution:** This will need careful consideration during the detailed design and pseudocode phase for these services, ensuring they integrate cleanly with the application's entry points.

## 6. Specifics of "Global Email Notifications Enabled" Flag (Spec 4)

*   **Gap:** The specification mentions a `GLOBAL_EMAIL_NOTIFICATIONS_ENABLED` environment variable. The research on email sending covers loading config from env vars, but the exact interaction point where this global flag is checked (e.g., in `EmailService` before any send attempt, or earlier in `MonitoringService` before even deciding to notify) is a design detail not covered by broad research.
*   **Impact:** Minor, but requires a clear decision during implementation.
*   **Resolution:** To be decided during detailed design of `EmailService` / notification logic.

Most of these "gaps" are not deficiencies in the general research but rather areas requiring project-specific details or decisions that naturally fall into the subsequent design and implementation phases. The current research provides a strong foundation of best practices to inform those decisions. No critical gaps requiring immediate, extensive new Perplexity searches seem apparent before proceeding to synthesis and report generation.