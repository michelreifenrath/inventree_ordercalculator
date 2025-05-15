# Secondary Findings: Specific `AppTest` Code Examples

This document details specific code examples for common Streamlit testing scenarios using `streamlit.testing.v1.AppTest` and `pytest`, based on targeted research.

---

### 1. Testing `st.form` Submission and Input Values

*   **Concept:** Use `AppTest` to simulate filling form inputs and clicking the submit button, then assert the resulting state or UI elements.
*   **Example (`test_forms.py`):**

```python
# Assumes app.py contains a form with key "my_form",
# a text_input with key "name", and a submit button.
# On submission, it might display st.success and update session_state.

from streamlit.testing.v1 import AppTest

def test_form_submission():
    at = AppTest.from_file("app.py").run() # Initial run

    # Interact with the form
    name_input = at.text_input(key="name")
    name_input.input("Alice")
    # Note: Interactions within a form often don't require .run() until submission
    # unless they trigger immediate changes outside the form.

    submit_button = at.form_submit_button("Submit") # Find the submit button by label
    submit_button.click().run() # Click and trigger rerun

    # Assertions after submission
    assert len(at.success) > 0, "Success message should be displayed"
    assert at.success[0].value == "Received: Alice" # Check message content
    assert at.session_state.get("form_data") == {"name": "Alice"} # Check state update
```

*   **Key `AppTest` Methods:**
    *   `at.text_input(key="...")`: Selects the widget.
    *   `.input("value")`: Sets the widget's value.
    *   `at.form_submit_button("label")`: Selects the submit button.
    *   `.click().run()`: Simulates the click and the subsequent script rerun.
    *   `at.success`: Accesses displayed success messages.
    *   `at.session_state`: Accesses the session state dictionary.

---

### 2. Asserting Data Displayed in `st.dataframe` or `st.table`

*   **Concept:** Run the app to the point where data is displayed, then access the corresponding `AppTest` element (`.dataframe` or `.table`) and assert its `value`.
*   **Example (`test_data_outputs.py`):**

```python
# Assumes app.py displays a pandas DataFrame stored in
# session_state['source_data'] using st.dataframe()

import pandas as pd
from streamlit.testing.v1 import AppTest

def test_dataframe_output():
    # Prepare test data
    expected_df = pd.DataFrame({"col1": [1, 2], "col2": ["A", "B"]})

    at = AppTest.from_file("app.py")
    # Set up initial state if needed
    at.session_state["source_data"] = expected_df
    at.run()

    # Assertions
    assert len(at.dataframe) == 1, "A dataframe should be displayed"
    displayed_df = at.dataframe[0].value
    pd.testing.assert_frame_equal(displayed_df, expected_df) # Use pandas testing utility
```

*   **Key `AppTest` Methods:**
    *   `at.dataframe`: Returns a list of rendered dataframe elements.
    *   `.value`: Accesses the data (typically a pandas DataFrame) within the element.

---

### 3. Manipulating and Asserting `st.session_state`

*   **Concept:** Set initial `session_state` values directly on the `AppTest` object before `.run()`. Simulate interactions that modify the state, then assert the final state values.
*   **Example (`test_session_state.py`):**

```python
# Assumes app.py has a button that increments session_state['count']
# and displays the count using st.markdown.

from streamlit.testing.v1 import AppTest

def test_session_state_manipulation():
    at = AppTest.from_file("app.py")

    # Set initial state
    at.session_state["count"] = 10
    at.run() # Run with initial state

    # Verify initial display
    assert "Count: 10" in at.markdown[0].value

    # Simulate interaction modifying state
    at.button(key="increment_button").click().run() # Assume button has key="increment_button"

    # Assert final state and display
    assert at.session_state.count == 11
    assert "Count: 11" in at.markdown[0].value # Check updated display
```

*   **Key `AppTest` Methods:**
    *   `at.session_state["key"] = value`: Set state before running.
    *   `at.button(key="...").click().run()`: Trigger state change via interaction.
    *   `assert at.session_state.key == expected_value`: Verify final state.

---

### 4. Mocking Functions Called by Callbacks/Interactions

*   **Concept:** Use `pytest`'s mocking capabilities (like `monkeypatch` or `pytest-mock`'s `mocker` fixture) to replace functions *before* running the `AppTest`.
*   **Example (`test_mocking.py`):**

```python
# Assumes app.py calls a function 'utils.fetch_data(param)'
# when a button is clicked.

import pytest
from unittest.mock import Mock # Can use unittest.mock or pytest-mock
from streamlit.testing.v1 import AppTest
# Assume 'utils.py' exists with 'fetch_data' function

def test_mocked_callback(monkeypatch):
    # Create a mock object
    mock_fetch = Mock(return_value="Mocked Data")

    # Replace the actual function with the mock
    # Ensure the path string is correct for where 'fetch_data' is *imported* or defined in app.py
    monkeypatch.setattr("app.utils.fetch_data", mock_fetch) # Or "utils.fetch_data" if imported directly

    at = AppTest.from_file("app.py").run()

    # Simulate interaction triggering the mocked function
    at.button(key="load_data_button").click().run()

    # Assertions
    mock_fetch.assert_called_once() # Check if the mock was called
    # mock_fetch.assert_called_once_with(expected_param) # Check call arguments if needed
    assert "Data: Mocked Data" in at.markdown[0].value # Check UI update based on mock return
```

*   **Key Concepts:**
    *   `monkeypatch.setattr("module.function_name", mock_object)`: Replaces the target function.
    *   `Mock(return_value=...)`: Defines the mock's behavior.
    *   `mock_object.assert_called_once()`: Verifies the mock was triggered.

---
*These examples illustrate common patterns. Specific implementation details depend on the application's structure.*