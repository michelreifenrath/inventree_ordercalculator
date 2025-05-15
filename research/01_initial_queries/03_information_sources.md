# Information Sources

To answer the key research questions and gather comprehensive information for the "Automated Parts List Monitoring & Email Notification" feature, the following types of information sources will be leveraged:

## 1. Primary Information Sources (Direct Research & Analysis)

*   **Perplexity AI Searches:**
    *   Utilize the `github.com/pashpashpash/perplexity-mcp` server and its `search` and `chat_perplexity` tools for targeted queries related to each research question.
    *   Focus on Python libraries, best practices, design patterns, security considerations, and common pitfalls for each topic (scheduling, email, hashing, error handling, etc.).
    *   Example query types:
        *   "Best Python libraries for cron-like scheduling with robust error handling"
        *   "Secure SMTP configuration in Python using environment variables"
        *   "Python HTML email generation with Jinja2 and premailer"
        *   "Efficient hashing of complex Python objects for change detection"
        *   "Python `tenacity` library for retry mechanisms best practices"
        *   "Streamlit best practices for CRUD interfaces with background tasks"
        *   "Architectural patterns for integrating background services in a Python application"
        *   "Security risks of user-supplied cron strings in Python"
*   **Official Documentation of Libraries/Tools:**
    *   `APScheduler`: For scheduling mechanisms, cron parsing, job management, and error handling.
    *   Python's `smtplib`, `email.mime`: For low-level email construction and sending.
    *   `Jinja2`: For HTML/text email templating.
    *   `premailer`: For inlining CSS in HTML emails.
    *   `python-dotenv`: For managing environment variables.
    *   `Typer` / `Click`: For CLI design patterns.
    *   `Streamlit`: For UI design patterns and component capabilities.
    *   Relevant Python standard library modules (e.g., `hashlib`, `logging`).
    *   `tenacity` (or similar retry libraries).
*   **Project-Specific Documents:**
    *   [`docs/feature_specs/automated_monitoring_spec.md`](docs/feature_specs/automated_monitoring_spec.md:1): The primary source for feature requirements and constraints.
    *   Existing codebase (`src/inventree_order_calculator/`) for understanding current architecture and components (`Calculator`, `PresetsManager`, `Config`).

## 2. Secondary Information Sources (Broader Context & Best Practices)

*   **Technical Blogs and Articles:**
    *   Search for articles on platforms like Real Python, Medium (towards Data Science, Python in Plain English), official company engineering blogs (e.g., Netflix, Dropbox, if relevant examples exist), and individual developer blogs.
    *   Focus on practical implementation guides, tutorials, and experience reports related to the technologies and problems being addressed.
*   **Books and E-books:**
    *   Relevant sections from books on Python development, software architecture, and specific technologies (if applicable and accessible).
*   **Community Forums and Q&A Sites:**
    *   Stack Overflow: For specific technical questions, common problems, and solutions related to libraries and implementation techniques.
    *   Reddit (e.g., r/Python, r/learnpython): For discussions, opinions, and alternative perspectives.
*   **Open Source Project Codebases:**
    *   Examine well-regarded open-source Python projects that implement similar features (e.g., background task scheduling, email notifications, CLI/web interfaces for task management) to identify common patterns and best practices. This requires careful selection and time commitment.

## 3. Validation and Cross-Referencing

*   Information gathered from one source will be cross-referenced with others to ensure accuracy, identify consensus, and note any contradictions or differing opinions.
*   Priority will be given to official documentation and reputable technical sources.
*   Community opinions will be considered but weighed against established best practices.

## 4. Iterative Refinement

*   The list of information sources may be expanded or refined as the research progresses and new avenues of inquiry emerge.
*   Findings from initial Perplexity searches will often lead to more specific documentation or articles.