# Research Report: Table of Contents

## Automated Parts List Monitoring & Email Notification Feature

1.  **[Executive Summary](01_executive_summary.md)**
    *   Overview of the Research
    *   Key Findings and Insights
    *   Core Recommendations
    *   Conclusion

2.  **[Methodology](02_methodology.md)**
    *   Research Objectives
    *   Scope Definition
    *   Information Sources
    *   Research Phases:
        *   Initial Queries
        *   Data Collection
        *   Analysis
        *   Synthesis
        *   Report Generation
    *   Tools Used (Perplexity AI MCP)

3.  **[Detailed Findings](03_findings.md)**
    *   3.1. [Scheduling Mechanisms](./../02_data_collection/01_primary_findings.md#1-scheduling-mechanisms)
        *   APScheduler Suitability
        *   Alternatives to APScheduler
        *   Cron String Parsing and Validation
        *   Error Handling in Scheduling
    *   3.2. [Email Generation and Sending](./../02_data_collection/01_primary_findings.md#2-email-generation-and-sending)
        *   Libraries and Techniques
        *   Secure SMTP Configuration
        *   Handling Sensitive Credentials
        *   Error Handling and Retry Logic
        *   Email Deliverability
    *   3.3. [Change Detection (`on_change` logic)](./../02_data_collection/01_primary_findings.md#3-change-detection-on_change-logic)
        *   Hashing Algorithms
        *   Canonical Serialization
        *   Alternative Change Detection Methods
        *   Updating `last_hash`
        *   Minimizing False Positives/Negatives
    *   3.4. [Error Handling and Logging](./../02_data_collection/01_primary_findings.md#4-error-handling-and-logging)
        *   Comprehensive Logging Strategies
        *   Retry Mechanisms for Transient Errors
        *   Handling Persistent Errors
        *   Managing Configuration Errors
    *   3.5. [Task Management (CLI/UI)](./../02_data_collection/01_primary_findings.md#5-task-management-cliui)
        *   CLI Design Patterns (Typer/Click)
        *   Streamlit UI Patterns
        *   Querying and Displaying Task State
        *   Consistency Between CLI and UI
    *   3.6. [Overall Architecture](./../02_data_collection/01_primary_findings.md#6-overall-architecture)
        *   Structuring `MonitoringService` and `EmailService`
        *   Integration with Existing Modules
        *   Design Patterns (DI, Observer, Strategy)
        *   Testability
        *   Scalability Considerations
    *   3.7. [Security Considerations](./../02_data_collection/01_primary_findings.md#7-security-considerations)
        *   Handling API Keys and Email Credentials
        *   Validating User-Defined Cron Strings
        *   Preventing XSS in HTML Emails
        *   Secure InvenTree API Credential Management

4.  **[Analysis](04_analysis.md)**
    *   4.1. [Patterns Identified](./../03_analysis/01_patterns_identified.md)
    *   4.2. [Contradictions and Conflicting Information](./../03_analysis/02_contradictions.md)
    *   4.3. [Knowledge Gaps](./../03_analysis/03_knowledge_gaps.md)

5.  **[Recommendations and Implementation Strategies](05_recommendations.md)**
    *   5.1. [Integrated Model Overview](./../04_synthesis/01_integrated_model.md)
    *   5.2. [Key Insights and Actionable Recommendations](./../04_synthesis/02_key_insights.md)
    *   5.3. [Practical Applications and Implementation Strategies](./../04_synthesis/03_practical_applications.md)

6.  **[References](06_references.md)**
    *   Primary Information Sources (Perplexity AI, Official Documentation)
    *   Types of Secondary Information Sources Consulted

---

*This Table of Contents provides direct links to the relevant sections within the research documentation structure.*