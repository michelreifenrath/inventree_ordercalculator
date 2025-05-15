# 2. Methodology

This section outlines the methodology employed to conduct the deep research for the "Automated Parts List Monitoring and Email Notification" feature of the InvenTree Order Calculator project.

## Research Objectives

The primary objective of this research was to gather, analyze, and synthesize information to provide well-founded recommendations and implementation strategies for the new feature. The research aimed to cover best practices in Python for:

*   Job scheduling
*   Email generation and sending
*   Change detection in data structures
*   Error handling and logging
*   Task management via CLI and UI
*   Overall system architecture and integration
*   Relevant security considerations

The output was intended to be a structured research documentation system that could directly inform subsequent pseudocode development and implementation phases.

## Scope Definition

The scope of the research was defined by the user's initial request and the detailed functional and technical specifications provided in [`docs/feature_specs/automated_monitoring_spec.md`](./../../docs/feature_specs/automated_monitoring_spec.md). Key areas of focus were explicitly listed in the request and further refined in `research/01_initial_queries/01_scope_definition.md`.

## Information Sources

A multi-faceted approach to information gathering was planned, as detailed in `research/01_initial_queries/03_information_sources.md`. The primary sources utilized were:

1.  **Perplexity AI Searches:** The `github.com/pashpashpash/perplexity-mcp` server, specifically its `search` tool, was used to perform targeted queries for each of the seven key research areas. These queries were designed to elicit detailed information on Python libraries, best practices, design patterns, and security considerations.
2.  **Project-Specific Documents:** The existing [`docs/feature_specs/automated_monitoring_spec.md`](./../../docs/feature_specs/automated_monitoring_spec.md) served as the foundational document for requirements and constraints.
3.  **General Knowledge Base:** The AI's underlying knowledge base on Python development, software architecture, and common libraries also contributed to the analysis and synthesis of information retrieved from Perplexity.

While secondary sources like technical blogs, official documentation of specific libraries (e.g., APScheduler, Jinja2, Typer), and community forums were planned, the direct outputs from Perplexity AI formed the bulk of the "raw data" for this research iteration. The Perplexity outputs often summarized information that would typically be found in such secondary sources.

## Research Phases

The research followed a structured, recursive self-learning approach, broken down into five distinct phases:

1.  **Phase 1: Initial Queries (`research/01_initial_queries/`)**
    *   **Scope Definition:** Clarifying the boundaries and goals of the research.
    *   **Key Questions:** Formulating specific questions to guide data collection for each research topic.
    *   **Information Sources:** Identifying potential sources of information.

2.  **Phase 2: Data Collection (`research/02_data_collection/`)**
    *   Executing targeted searches using the Perplexity AI MCP tool for each of the seven key research areas.
    *   Storing the raw and processed findings in `01_primary_findings.md`, organized by research topic and referencing the Perplexity AI outputs.

3.  **Phase 3: Analysis (`research/03_analysis/`)**
    *   **Patterns Identified:** Reviewing the collected data to identify recurring themes, common best practices, and recommended technologies.
    *   **Contradictions:** Examining findings for any conflicting information or recommendations, and attempting to resolve or contextualize them.
    *   **Knowledge Gaps:** Identifying areas where information might be insufficient for project-specific needs or where further clarification might be beneficial.

4.  **Phase 4: Synthesis (`research/04_synthesis/`)**
    *   **Integrated Model:** Developing a conceptual framework showing how different components and practices fit together for the proposed feature.
    *   **Key Insights and Recommendations:** Distilling the most critical, actionable advice from the analysis.
    *   **Practical Applications:** Outlining concrete implementation strategies based on the synthesized knowledge.

5.  **Phase 5: Report Generation (`research/05_final_report/`)**
    *   Consolidating all research artifacts into a final structured report, including this methodology, executive summary, detailed findings, analysis, recommendations, and references.

## Tools Used

*   **Perplexity AI MCP Server:** Accessed via the `use_mcp_tool` with `server_name: github.com/pashpashpash/perplexity-mcp` and `tool_name: search`. This was the primary tool for external information gathering.
*   **Internal File Management Tools:** `write_to_file` and `insert_content` were used to create and update the markdown documentation within the defined research structure.