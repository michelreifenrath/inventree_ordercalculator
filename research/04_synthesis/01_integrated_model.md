# Integrated Model: Testing Streamlit Applications

This model synthesizes the findings into a recommended approach for applying Test-Driven Development (TDD) principles to Streamlit applications, addressing its unique reactive nature.

**Challenge:** Streamlit's automatic script rerun on interaction makes traditional testing difficult.

**Solution:** A layered testing strategy centered around Streamlit's native `AppTest` framework, orchestrated by `pytest`, and isolated using standard mocking techniques.

---

**Core Components:**

1.  **`pytest` (Test Runner & Framework):**
    *   Orchestrates test discovery and execution.
    *   Provides fixtures for setup/teardown (e.g., initializing mocks).
    *   Integrates plugins (`pytest-mock`, `pytest-cov`) for enhanced functionality.

2.  **`streamlit.testing.v1.AppTest` (Streamlit Integration Layer):**
    *   The primary tool for testing the Streamlit UI layer.
    *   Simulates the Streamlit runtime environment and script reruns *without* a browser.
    *   Provides methods to:
        *   Load app scripts (`AppTest.from_file(...)`).
        *   Simulate user interactions (`.button(...).click()`, `.text_input(...).input(...)`).
        *   Manipulate and inspect `st.session_state`.
        *   Access and assert the state/value of rendered UI elements (`.dataframe`, `.markdown`, `.button`, etc.).

3.  **Mocking Libraries (`unittest.mock` / `pytest-mock`):**
    *   Used to isolate the Streamlit application from external dependencies (APIs, databases, complex calculations) during tests.
    *   Ensures tests focus on the Streamlit logic and UI behavior, not the dependencies.

---

**Testing Layers:**

1.  **Unit Testing (Standard `pytest`):**
    *   **Target:** Pure Python functions, classes, or modules (e.g., data processing, API client logic, calculation functions) that *do not* directly involve `st.` calls.
    *   **Tools:** `pytest`, `unittest.mock`.
    *   **Goal:** Verify the correctness of individual logic units in isolation.

2.  **Integration Testing (`AppTest` + `pytest`):**
    *   **Target:** The Streamlit application script (`app.py`) or individual component scripts. Tests how UI elements interact, how state changes affect the UI, and how Streamlit code calls backend logic (mocked).
    *   **Tools:** `AppTest`, `pytest`, Mocking libraries.
    *   **Goal:** Verify the integration between UI elements, state management, and (mocked) backend logic within the Streamlit execution context. This is the primary focus for TDD of the Streamlit part.

3.  **End-to-End (E2E) Testing (Optional, Separate Tools):**
    *   **Target:** The fully deployed or locally running application in a real browser.
    *   **Tools:** Selenium, Playwright, Cypress.
    *   **Goal:** Verify complete user flows through the actual rendered UI. (Generally considered outside the scope of TDD focused on `AppTest`).

---

**Conceptual Workflow (`AppTest` Integration Tests):**

```
1. Write Test (Fail)  <---------------------------------------+
   - Define test case using `pytest`.                         |
   - Use `AppTest` to target app/component script.            | Refactor
   - Simulate interaction(s) (`at.widget.action().run()`).    |
   - Assert expected UI state or `session_state` (will fail). |
           |                                                  |
           v                                                  |
2. Write Code (Pass)                                          |
   - Implement minimal Streamlit code (`app.py`) to make      |
     the assertion pass (e.g., add widget, update state).     |
           |                                                  |
           v                                                  |
3. Refactor (Optional)----------------------------------------+
   - Improve Streamlit code structure or test clarity
     while ensuring tests still pass.
```

---

**Key Patterns in the Model:**

*   **State-Based Assertions:** Focus tests on the *result* (UI element values, `session_state`) after interactions, letting `AppTest` handle the implicit reruns.
*   **Component Isolation:** Use `AppTest.from_file()` to test smaller UI parts independently before integrating.
*   **Mocking Boundaries:** Clearly separate Streamlit UI logic from backend/external logic using mocks during integration tests.
*   **CI Automation:** Integrate `pytest` execution into CI pipelines for continuous validation.

This integrated model provides a robust framework for developing and maintaining testable Streamlit applications.