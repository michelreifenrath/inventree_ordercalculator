# Key Research Questions

1.  **Reactive Model:** How can tests effectively handle Streamlit's top-to-bottom script rerun mechanism triggered by user interactions? Are there patterns to isolate testable logic from this reactivity?
2.  **UI Component Testing:** What are the most effective ways to test the behavior and state changes of Streamlit widgets (`st.button`, `st.text_input`, `st.selectbox`, etc.) and forms (`st.form`)? How can we assert the content displayed by elements like `st.table`, `st.dataframe`, or `st.write`?
3.  **Mocking:** What are the standard practices for mocking external dependencies (APIs like `ApiClient`, complex logic like `OrderCalculator`, database connections) when testing Streamlit UI logic? How does this integrate with Streamlit's execution model?
4.  **Tooling:** Are there dedicated Streamlit testing libraries or `pytest` plugins available? How mature and well-maintained are they? What are the pros and cons compared to using standard Python testing tools (`pytest`, `unittest.mock`) directly?
5.  **Testing Levels:** What is the recommended balance between unit tests (for helper functions, isolated logic), integration tests (testing interactions between UI and backend mocks), and E2E tests (testing the full application flow, potentially using browser automation)?
6.  **State Management:** How can tests reliably manipulate and assert the contents of `st.session_state`? Are there specific patterns or helpers needed to manage state across simulated reruns?
7.  **Test Structure:** What are best practices for organizing Streamlit test files and fixtures?
8.  **Limitations:** What are the inherent limitations or difficulties when testing Streamlit applications compared to traditional web frameworks?