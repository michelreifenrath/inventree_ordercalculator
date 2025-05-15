# 6. References

This section outlines the primary types of information sources and tools used during the research process for the "Automated Parts List Monitoring and Email Notification" feature. Due to the nature of the Perplexity AI tool, direct, citable URLs for each piece of information are not available in a traditional bibliographic format. Instead, this section describes the methodology of information retrieval.

## Primary Information Sources

1.  **Perplexity AI (via MCP Server `github.com/pashpashpash/perplexity-mcp`)**:
    *   The core of the external research was conducted using the `search` tool provided by this MCP server.
    *   Targeted queries were formulated for each of the seven key research areas (Scheduling, Email, Change Detection, Error Handling/Logging, Task Management, Architecture, Security).
    *   The Perplexity AI responses typically synthesized information from various web sources, documentation, and articles, providing summaries and conceptual code examples. These outputs are referenced in `research/02_data_collection/01_primary_findings.md` by the date of the search and often with bracketed numbers (e.g., "[1]", "[2]") corresponding to distinct points or examples within a given Perplexity output.

2.  **Project-Specific Documentation**:
    *   [`docs/feature_specs/automated_monitoring_spec.md`](./../../docs/feature_specs/automated_monitoring_spec.md): This document provided the foundational requirements and technical specifications that guided the research questions and scope.

3.  **General AI Knowledge Base**:
    *   The underlying knowledge base of the AI model performing this research contributed to the interpretation, analysis, and synthesis of the information retrieved from Perplexity. This includes general best practices in Python software development, common libraries, and architectural patterns.

## Types of Secondary Information Sources Consulted (Implicitly via Perplexity AI)

The Perplexity AI tool, in generating its responses, draws from a wide array of online resources. While direct links are not provided by the tool's output in a citable way for this report, the types of sources it typically consults include:

*   **Official Documentation:** For Python itself, and for relevant libraries such as `APScheduler`, `Celery`, `Jinja2`, `smtplib`, `Typer`, `Click`, `Streamlit`, `Pydantic`, `tenacity`, `structlog`, `premailer`, `python-dotenv`, `croniter`, `DeepDiff`, `bleach`.
*   **Technical Blogs and Articles:** From reputable software engineering blogs, individual developer sites, and platforms like Real Python, Medium, etc.
*   **Community Forums and Q&A Sites:** Such as Stack Overflow, Reddit (e.g., r/Python).
*   **Open Source Project Codebases and Discussions:** GitHub repositories and associated issue trackers or discussions.
*   **Academic Papers and Research Publications:** For more theoretical concepts if applicable (less so for this practical research).

## Tooling

*   **Model Context Protocol (MCP):** The framework enabling interaction with the Perplexity AI server.
*   **Internal File Management Tools:** `write_to_file`, `insert_content` for creating and managing the markdown research documentation.

While a traditional bibliography is not feasible, the structured approach of documenting queries, raw findings (linked to Perplexity outputs), analysis, and synthesis aims to provide a traceable and verifiable research process. The strength of the findings relies on Perplexity AI's ability to synthesize information from authoritative sources effectively.