# Pseudocode: Email Service (`09_email_service_pseudocode.md`)

This document outlines the pseudocode for the Email Service, responsible for generating and sending emails.

## 1. Core Components

*   **Email Config Loader:** Loads SMTP and sender configuration from environment variables.
*   **Email Content Generator:** Creates HTML and plain-text versions of the monitoring report.
*   **Email Sender:** Connects to the SMTP server and sends emails, including retry logic.

## 2. Configuration (Loaded by `Config` module, accessed here)

```pseudocode
// These are assumed to be loaded into a global Config object or similar structure
// by a dedicated Config module (e.g., 01_config_pseudocode.md)
// EMAIL_SMTP_SERVER
// EMAIL_SMTP_PORT
// EMAIL_USE_TLS
// EMAIL_USE_SSL
// EMAIL_USERNAME
// EMAIL_PASSWORD
// EMAIL_SENDER_ADDRESS
// ADMIN_EMAIL_RECIPIENTS (list of strings)
// GLOBAL_EMAIL_NOTIFICATIONS_ENABLED (boolean)
```

## 3. Email Service Module

```pseudocode
MODULE EmailService

  // Assumes email configuration is loaded globally or passed appropriately.
  // For simplicity, direct access to Config.EMAIL_... is shown.

  FUNCTION generate_html_email_content(task_config, calculation_result):
    // TEST: email_generator_creates_html_output_from_calculation_result
    // TEST: email_content_includes_all_required_tables_and_summary
    // TEST: part_not_found_is_reported_in_email_not_as_system_error (Content generation part)

    html_body = "<html><body>"
    html_body += "<h1>Inventree Order Report: " + task_config.name + "</h1>"
    html_body += "<p>Report generated on: " + current_datetime_string() + "</p>"

    // Summary Section (Example)
    html_body += "<h2>Summary</h2>"
    html_body += "<p>Total Parts Requested: " + calculation_result.summary.total_parts_requested + "</p>"
    html_body += "<p>Total Parts Available: " + calculation_result.summary.total_parts_available + "</p>"
    html_body += "<p>Total Missing Parts: " + calculation_result.summary.total_missing_parts + "</p>"
    // ... other summary fields

    // Detailed BOM Table (Example)
    html_body += "<h2>Detailed Bill of Materials</h2>"
    html_body += "<table border='1'><tr><th>Part Name</th><th>Version</th><th>Required</th><th>Available</th><th>Missing</th><th>Notes</th></tr>"
    FOR EACH part_row IN calculation_result.detailed_bom:
      html_body += "<tr>"
      html_body += "<td>" + part_row.name + "</td>"
      html_body += "<td>" + (part_row.version IF part_row.version ELSE "-") + "</td>"
      html_body += "<td>" + part_row.quantity_required + "</td>"
      html_body += "<td>" + part_row.quantity_available + "</td>"
      html_body += "<td>" + part_row.quantity_missing + "</td>"
      html_body += "<td>" + (part_row.notes IF part_row.notes ELSE "") + "</td>" // e.g., "Part not found", "Alternative used"
      html_body += "</tr>"
    ENDFOR
    html_body += "</table>"

    // Alternative Parts Section (if applicable)
    IF calculation_result.has_alternatives_info:
      html_body += "<h2>Alternative Parts Used</h2>"
      // ... table for alternatives
    ENDIF

    // Errors/Warnings during calculation (e.g., part not found is a note, but API sub-errors could be listed)
    IF calculation_result.has_calculation_warnings_or_errors:
        html_body += "<h2>Calculation Warnings/Errors</h2><ul>"
        FOR EACH error_msg IN calculation_result.warnings_or_errors:
            html_body += "<li>" + error_msg + "</li>"
        ENDFOR
        html_body += "</ul>"
    ENDIF

    html_body += "</body></html>"
    RETURN html_body

  FUNCTION generate_text_email_content(task_config, calculation_result):
    // TEST: email_generator_creates_plaintext_output_from_calculation_result
    text_body = "Inventree Order Report: " + task_config.name + "\n"
    text_body += "Report generated on: " + current_datetime_string() + "\n\n"

    // Summary
    text_body += "== Summary ==\n"
    text_body += "Total Parts Requested: " + calculation_result.summary.total_parts_requested + "\n"
    // ... other summary fields
    text_body += "\n"

    // Detailed BOM
    text_body += "== Detailed Bill of Materials ==\n"
    text_body += "Part Name | Version | Required | Available | Missing | Notes\n"
    text_body += "-----------------------------------------------------------------\n"
    FOR EACH part_row IN calculation_result.detailed_bom:
      text_body += part_row.name + " | "
      text_body += (part_row.version IF part_row.version ELSE "-") + " | "
      text_body += part_row.quantity_required + " | "
      text_body += part_row.quantity_available + " | "
      text_body += part_row.quantity_missing + " | "
      text_body += (part_row.notes IF part_row.notes ELSE "") + "\n"
    ENDFOR
    text_body += "\n"

    // ... similar sections for alternatives, errors/warnings
    RETURN text_body

  FUNCTION send_email(recipients, subject, html_body, text_body, is_admin_notification = FALSE):
    // TEST: email_sender_connects_to_smtp_server_with_tls
    // TEST: email_sender_connects_to_smtp_server_with_ssl
    // TEST: email_sender_authenticates_successfully
    // TEST: email_sender_fails_gracefully_on_auth_failure
    // TEST: email_config_loads_parameters_from_env_variables (Tested in Config module)

    IF NOT Config.GLOBAL_EMAIL_NOTIFICATIONS_ENABLED:
      LOG_INFO "Global email notifications disabled. Suppressing email: " + subject
      RETURN TRUE // Pretend success as per spec for global disable

    // If it's a regular notification and the primary recipients list is empty, log and return.
    // Admin notifications should always try to send to ADMIN_EMAIL_RECIPIENTS.
    IF NOT is_admin_notification AND (recipients IS NULL OR recipients.length == 0):
        LOG_WARNING "No recipients specified for email: " + subject + ". Email not sent."
        RETURN FALSE // Indicate failure to send to specific recipients.

    actual_recipients = recipients
    if is_admin_notification:
        actual_recipients = Config.ADMIN_EMAIL_RECIPIENTS
        if actual_recipients IS NULL OR actual_recipients.length == 0:
            LOG_ERROR "Admin email requested but ADMIN_EMAIL_RECIPIENTS is not set. Cannot send: " + subject
            RETURN FALSE

    TRY
      smtp_connection = create_smtp_connection() // Uses Config.EMAIL_... vars
      
      message = create_mime_message(
        sender=Config.EMAIL_SENDER_ADDRESS,
        recipients=actual_recipients,
        subject=subject,
        html_content=html_body,
        text_content=text_body
      )
      
      smtp_connection.sendmail(Config.EMAIL_SENDER_ADDRESS, actual_recipients, message.as_string())
      smtp_connection.quit()
      LOG_INFO "Email sent successfully to " + actual_recipients.join(", ") + ". Subject: " + subject
      RETURN TRUE
    CATCH SMTPAuthenticationError as e:
      LOG_ERROR "SMTP Authentication failed: " + e.message
      // TEST: email_sender_fails_gracefully_on_auth_failure (Covered here)
      RETURN FALSE
    CATCH SMTPException as e: // Catches other SMTP errors (connection, send, etc.)
      LOG_ERROR "SMTP Error occurred: " + e.message
      RETURN FALSE
    CATCH Exception as e:
      LOG_ERROR "Generic error during email sending: " + e.message
      RETURN FALSE
    ENDTRY

  FUNCTION send_email_with_retry(recipients, subject, html_body, text_body):
    // TEST: error_handler_logs_email_send_failure (within this function)
    // TEST: error_handler_initiates_retry_for_email_send_failure (within this function)
    // TEST: error_handler_sends_admin_notification_for_persistent_email_failure (within this function)

    max_retries = 2 // As per spec, "one or more" - let's define it as 2 for a total of 3 attempts
    retry_delay_base = 10 // seconds

    FOR attempt = 0 TO max_retries: // 0 is the first attempt, 1 and 2 are retries
      success = send_email(recipients, subject, html_body, text_body)
      IF success:
        RETURN TRUE
      
      LOG_ERROR "Email send attempt " + (attempt + 1) + " failed for subject: " + subject
      IF attempt < max_retries:
        sleep_duration = retry_delay_base * (2 ** attempt) // Exponential backoff
        LOG_INFO "Retrying email send in " + sleep_duration + " seconds..."
        sleep(sleep_duration)
      ENDIF
    ENDFOR

    LOG_ERROR "Failed to send email after " + (max_retries + 1) + " attempts. Subject: " + subject
    // Send notification to admin about persistent email failure
    IF Config.GLOBAL_EMAIL_NOTIFICATIONS_ENABLED AND Config.ADMIN_EMAIL_RECIPIENTS AND Config.ADMIN_EMAIL_RECIPIENTS.length > 0:
      admin_subject = "CRITICAL: Email System Failure - Could not send report"
      admin_body_text = "The email system failed to send the following report after multiple retries:\n\n"
      admin_body_text += "Original Subject: " + subject + "\n"
      admin_body_text += "Original Recipients: " + recipients.join(", ") + "\n\n"
      admin_body_text += "Please check the SMTP server configuration and logs."
      
      // Send admin email with no retry, as this is the fallback notification.
      // If this also fails, it will be logged by the inner send_email call.
      send_email(
          recipients=Config.ADMIN_EMAIL_RECIPIENTS, // Will be overridden by is_admin_notification
          subject=admin_subject,
          html_body=admin_body_text, // Simple text for admin alert
          text_body=admin_body_text,
          is_admin_notification=TRUE
      )
    RETURN FALSE

  FUNCTION send_admin_notification(subject, text_body_content):
    // Simplified sender for admin-only critical notifications
    LOG_INFO "Attempting to send admin notification. Subject: " + subject
    IF NOT Config.GLOBAL_EMAIL_NOTIFICATIONS_ENABLED:
      LOG_INFO "Global email notifications disabled. Suppressing admin email: " + subject
      RETURN TRUE // Pretend success

    IF Config.ADMIN_EMAIL_RECIPIENTS IS NULL OR Config.ADMIN_EMAIL_RECIPIENTS.length == 0:
      LOG_ERROR "Cannot send admin notification: ADMIN_EMAIL_RECIPIENTS not set. Subject: " + subject
      RETURN FALSE
    
    // Admin notifications are critical, try once. If it fails, it's logged by send_email.
    // No complex HTML, just plain text.
    RETURN send_email(
        recipients=Config.ADMIN_EMAIL_RECIPIENTS, // Will be overridden by is_admin_notification
        subject="[Inventree Monitor Admin] " + subject,
        html_body=text_body_content.replace("\n", "<br>"), // Basic HTML for readability
        text_body=text_body_content,
        is_admin_notification=TRUE
    )

  PRIVATE FUNCTION create_smtp_connection():
    // Helper to establish SMTP connection based on Config
    // This would use a standard library like `smtplib` in Python.
    // Handles TLS/SSL.
    // Example (conceptual):
    // IF Config.EMAIL_USE_SSL:
    //   connection = smtplib.SMTP_SSL(Config.EMAIL_SMTP_SERVER, Config.EMAIL_SMTP_PORT)
    // ELSE:
    //   connection = smtplib.SMTP(Config.EMAIL_SMTP_SERVER, Config.EMAIL_SMTP_PORT)
    //   IF Config.EMAIL_USE_TLS:
    //     connection.starttls()
    // ENDIF
    // connection.login(Config.EMAIL_USERNAME, Config.EMAIL_PASSWORD)
    // RETURN connection
    // Placeholder:
    LOG_DEBUG "Creating SMTP connection to " + Config.EMAIL_SMTP_SERVER + ":" + Config.EMAIL_SMTP_PORT
    // ... actual SMTP library calls ...
    IF Config.EMAIL_USERNAME == "fail_auth": // For testing auth failure
        THROW new SMTPAuthenticationError("Simulated authentication failure")
    ENDIF
    RETURN new MockSMTPConnection() // Placeholder for actual connection object

  PRIVATE FUNCTION create_mime_message(sender, recipients, subject, html_content, text_content):
    // Helper to construct a multipart MIME email message.
    // This would use a library like `email.mime` in Python.
    // Example (conceptual):
    // msg = MIMEMultipart('alternative')
    // msg['Subject'] = subject
    // msg['From'] = sender
    // msg['To'] = ", ".join(recipients)
    // part1 = MIMEText(text_content, 'plain')
    // part2 = MIMEText(html_content, 'html')
    // msg.attach(part1)
    // msg.attach(part2)
    // RETURN msg
    // Placeholder:
    LOG_DEBUG "Creating MIME message. Subject: " + subject
    RETURN new MockMIMEMessage(subject, text_content, html_content) // Placeholder

END MODULE EmailService
```

## 4. Helper/Placeholder Objects (for pseudocode clarity)

```pseudocode
CLASS MockSMTPConnection:
  FUNCTION sendmail(from_addr, to_addrs, msg_string):
    LOG_DEBUG "MockSMTPConnection: Sending email..."
    IF from_addr == "simulate_send_fail@example.com": // For testing send failure
        THROW new SMTPException("Simulated SMTP send failure")
    ENDIF
  FUNCTION quit():
    LOG_DEBUG "MockSMTPConnection: Quitting."
END CLASS

CLASS MockMIMEMessage:
  CONSTRUCTOR(subject, text_content, html_content):
    this.subject = subject
    this.text_content = text_content
    this.html_content = html_content
  FUNCTION as_string():
    RETURN "Subject: " + this.subject + "\n\n" + this.text_content
END CLASS

// Custom Exception for testing
CLASS SMTPAuthenticationError EXTENDS Error {}
CLASS SMTPException EXTENDS Error {}

FUNCTION current_datetime_string():
  RETURN "YYYY-MM-DD HH:MM:SS" // Placeholder