# Practical Applications: Testing Streamlit Applications

The synthesized model and key insights translate into the following practical applications for developers building and testing Streamlit apps, particularly following TDD principles:

1.  **Project Setup:**
    *   Structure projects with a dedicated `tests/` directory alongside the `src/` or app directory.
    *   Use `pytest` as the test runner. Install `pytest`, `pytest-mock`, `pytest-cov`, and `pandas` (often needed for `st.dataframe` tests).
    *   Configure `pytest.ini` or `pyproject.toml` for `pytest` settings if needed.

2.  **TDD Workflow Implementation:**
    *   **Backend Logic (Non-Streamlit):** Apply standard Python TDD. Write `pytest` unit tests first for helper functions, data classes, API clients, calculation logic, etc. Use mocks for external dependencies.
    *   **Streamlit UI Logic:**
        *   **Red:** Write a failing integration test using `AppTest` in a `tests/test_streamlit_app.py` file (or similar). Define the desired interaction (e.g., button click) and assert the expected outcome (e.g., updated text, changed `session_state`).
        *   **Green:** Write the minimal Streamlit code (`st.button`, callback logic, state update) in your `app.py` (or component file) required to make the `AppTest` pass.
        *   **Refactor:** Clean up the Streamlit code or the test code while ensuring the test continues to pass.

3.  **Writing `AppTest` Tests:**
    *   **Isolate Components:** Create separate test files for distinct parts of the UI or components loaded from different scripts (`AppTest.from_file(...)`).
    *   **Simulate Interactions:** Use `at.widget_type(key=...).action()` (e.g., `.click()`, `.input()`, `.select()`) followed by `.run()` to simulate user actions and trigger reruns.
    *   **Assert State:** Check `at.session_state` values and the `.value` or content of relevant `AppTest` elements (`at.markdown`, `at.dataframe`, `at.success`, etc.) after interactions.
    *   **Mock Dependencies:** Use `pytest` fixtures (`monkeypatch`, `mocker`) to replace backend functions called by Streamlit callbacks or within the main script body during tests.

4.  **Handling Specific Scenarios:**
    *   **Forms:** Use `at.form_submit_button(...).click().run()` to test submission logic. Access input values via `at.widget_type(key=...).value` before submission or check `session_state` after.
    *   **Data Display:** Access rendered data via `at.dataframe[0].value` or `at.table[0].value` and use appropriate comparison methods (e.g., `pandas.testing.assert_frame_equal`).
    *   **Session State:** Set initial state via `at.session_state[...] = ...` before `at.run()`. Verify state changes after interactions.

5.  **Continuous Integration:**
    *   Configure CI pipelines (GitHub Actions, GitLab CI, etc.) to automatically run `pytest tests/` on code pushes or pull requests.
    *   Include coverage reporting (`pytest --cov=src`) to monitor test effectiveness.

6.  **Refactoring for Testability:**
    *   Extract complex logic from Streamlit callbacks or the main script body into separate, testable Python functions or classes (unit testable).
    *   Keep Streamlit code focused on UI presentation, state management, and orchestrating calls to the (testable) backend logic.
    *   Use `st.session_state` effectively to manage state explicitly, making it easier to assert in tests.