# Potential Information Sources

This document lists potential sources for researching TDD practices for Streamlit applications.

**Primary Sources:**

*   **Streamlit Official Documentation:**
    *   Testing section (if available)
    *   Session State documentation
    *   Advanced features or guides that might touch upon testability.
*   **Streamlit GitHub Repository:**
    *   Issues related to testing.
    *   Discussions or examples within the codebase or community contributions.
*   **Streamlit Community Forum:**
    *   Threads discussing testing strategies, challenges, and solutions.

**Secondary Sources:**

*   **Blog Posts & Articles:** Search for articles by developers sharing their experiences testing Streamlit apps (e.g., on Medium, personal blogs, company engineering blogs).
*   **Pytest Documentation & Plugins:**
    *   Core `pytest` features (`fixtures`, `mocking` with `pytest-mock`).
    *   Search for any `pytest` plugins specifically designed for Streamlit.
*   **Testing Libraries:**
    *   `unittest.mock` documentation (for standard mocking).
    *   Potentially relevant UI testing libraries (though direct browser automation might be E2E).
*   **GitHub Repositories:** Search for open-source Streamlit projects to see how they implement testing (if they do). Look for projects using libraries like `streamlit-testing` or similar names.
*   **Stack Overflow:** Questions tagged with `streamlit` and `testing`.

**Specific Libraries/Tools to Investigate:**

*   `streamlit-testing` (if it exists and is maintained)
*   `pytest`
*   `pytest-mock`
*   `unittest.mock`
*   Potentially E2E tools like `Selenium` or `Playwright` (for E2E perspective, though focus is TDD/unit/integration).

**Search Queries (Examples):**

*   "test streamlit application pytest"
*   "streamlit unit testing"
*   "mocking streamlit session state"
*   "streamlit integration testing"
*   "test streamlit widgets"
*   "streamlit-testing library"
*   "streamlit tdd best practices"