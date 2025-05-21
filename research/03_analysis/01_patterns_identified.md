# Patterns Identified: Testing Streamlit Applications

Based on the primary and secondary findings, the following patterns and recommended practices emerge for testing Streamlit applications:

1.  **Primacy of `streamlit.testing.v1.AppTest`:** The most consistent pattern is the recommendation and use of Streamlit's native `AppTest` framework. It's designed specifically to handle Streamlit's reactive execution model and provides APIs to simulate user interactions programmatically without a browser.

2.  **`pytest` as the Standard Runner:** `pytest` is the universally recommended test runner for organizing, executing, and enhancing Streamlit tests (e.g., using fixtures, plugins like `pytest-mock`, `pytest-cov`).

3.  **Combined Unit and Integration Testing:**
    *   **Unit Tests:** Pure Python logic (helper functions, data processing classes like `OrderCalculator`, `ApiClient` methods if separable) should be unit tested using standard `pytest` techniques, independent of Streamlit and `AppTest`.
    *   **Integration Tests (`AppTest`):** `AppTest` is primarily used for integration testing of the Streamlit layer – verifying how UI components interact, how state changes affect the UI, and how Streamlit code orchestrates calls to backend logic (which should be mocked at this level).

4.  **Focus on State and Output Assertion:** Tests using `AppTest` typically follow a pattern:
    *   Initialize `AppTest` (optionally setting initial `session_state`).
    *   Run the app (`at.run()`).
    *   Simulate user interactions (`at.widget(...).action().run()`).
    *   Assert the final state of UI elements (`at.widget.value`, `at.markdown[0].value`) and/or `session_state` (`at.session_state.key`).

5.  **Standard Mocking Techniques:** Python's standard mocking libraries (`unittest.mock`, `pytest-mock`) are used to isolate the Streamlit application from external dependencies (APIs, databases, complex calculations) during `AppTest` runs. Mocks are typically applied using `pytest` fixtures like `monkeypatch`.

6.  **Component Isolation:** Testing smaller, self-contained parts of the UI (custom components or sections loaded from separate files) using `AppTest.from_file("component_script.py")` is a recommended pattern for manageability.

7.  **CI/CD Integration:** Automating test execution (`pytest tests/`) within CI pipelines (e.g., GitHub Actions) is a standard practice mentioned in the context of Streamlit testing.