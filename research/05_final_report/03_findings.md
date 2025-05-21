# Findings: TDD for Streamlit Applications

This section summarizes the key findings from the research on testing Streamlit applications, focusing on tools, strategies, and specific techniques.

---

### Core Testing Tools: `AppTest` and `pytest`

*   **`streamlit.testing.v1.AppTest`:** This is Streamlit's official, built-in testing framework. It is the cornerstone for testing the Streamlit UI layer.
    *   It simulates the Streamlit runtime environment and script execution without needing a browser.
    *   It provides Python methods to interact with widgets (e.g., `at.button(...).click()`, `at.text_input(...).input(...)`).
    *   It allows inspection and manipulation of `st.session_state`.
    *   It enables asserting the state and content of rendered UI elements (e.g., `at.markdown`, `at.dataframe`).
    *   It handles Streamlit's reactive script reruns implicitly.
*   **`pytest`:** This is the recommended test runner.
    *   It provides test discovery, execution, and reporting.
    *   Its fixture system is useful for setting up test conditions (e.g., initializing mocks).
    *   It integrates well with standard Python tools like mocking libraries and coverage analysis (`pytest-mock`, `pytest-cov`).

---

### Testing Strategies: Layered Approach

A consensus emerged around a layered testing strategy:

1.  **Unit Tests:** Focus on non-Streamlit Python code (helper functions, data processing, API clients, business logic). Use standard `pytest` and mocking, completely independent of `AppTest`.
2.  **Integration Tests:** Focus on the Streamlit script (`app.py` or component scripts). Use `AppTest` combined with `pytest` to test UI interactions, state changes, and the integration between Streamlit code and *mocked* backend logic. This is the primary layer where TDD for the Streamlit part occurs.
3.  **End-to-End (E2E) Tests:** Optional layer using browser automation tools (Selenium, Playwright) to test user flows in a real browser. This is generally separate from the `AppTest`-based TDD workflow.

---

### Handling Streamlit's Reactivity

*   `AppTest` is designed to manage the reactive reruns automatically. When an interaction is simulated (e.g., `at.button(...).click().run()`), `AppTest` handles the script rerun and updates the internal representation of the app's state.
*   Tests should therefore focus on asserting the *final state* after an interaction, rather than trying to predict or track the exact execution path during the rerun.

---

### Mocking Dependencies

*   Standard Python mocking libraries (`unittest.mock`, `pytest-mock`) are used.
*   Dependencies like API calls, database interactions, or complex calculations within the Streamlit script or its callbacks should be mocked during `AppTest` integration tests.
*   `pytest` fixtures like `monkeypatch` are commonly used to apply these mocks before `AppTest` runs the script.

---

### Testing UI Components and State

*   **Interactions:** Use specific `AppTest` methods like `.click()`, `.input("value")`, `.select("option")` on widget objects retrieved via `at.widget_type(key=...)`. Remember to chain `.run()` after actions that trigger reruns.
*   **Assertions:**
    *   Check `st.session_state` directly: `assert at.session_state.my_key == expected_value`.
    *   Check rendered element content: `assert at.markdown[0].value == "Expected Text"`, `assert at.dataframe[0].value == expected_dataframe`.
    *   Check element existence/count: `assert len(at.success) == 1`.

---

### Code Examples

Specific code examples demonstrating testing forms, dataframes, session state, and mocking using `AppTest` and `pytest` were found and documented in [`research/02_data_collection/02_secondary_findings.md`](../02_data_collection/02_secondary_findings.md). These examples illustrate the practical application of the methods described above.