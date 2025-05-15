# src/inventree_order_calculator/email_service.py
import smtplib
import time
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from typing import Optional, List # Added Optional and List
# Assuming config is loaded and accessible.
# For EmailService, we expect an EmailConfig object.
# This will be refined once config.py is updated/reviewed.
from .config import EmailConfig # Expect EmailConfig to be defined in config.py

logger = logging.getLogger(__name__)

# Custom Exceptions for clarity, matching pseudocode intent
# These are kept as they might be raised by smtplib and caught by tests
class SMTPAuthenticationError(smtplib.SMTPAuthenticationError):
    pass

class SMTPServiceUnavailable(smtplib.SMTPException):
    pass

class EmailSendingError(Exception): # General error for the service
    pass


def _current_datetime_string() -> str:
    """Returns the current datetime as a string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# generate_html_email_content and generate_text_email_content are utility functions
# for creating email bodies. They are not part of EmailService's core sending logic
# but can be used by clients of EmailService. They are kept as is for now.
# Their `task_config` argument might need to be a more specific type later.
def generate_html_email_content(task_config, calculation_result) -> str:
    """
    Generates an HTML email body for the monitoring report.

    Args:
        task_config: The configuration object for the monitoring task.
        calculation_result: The result object from the order calculation.

    Returns:
        A string containing the HTML email body.
    """
    html_body = "<html><head><style>"
    html_body += """
        body { font-family: sans-serif; margin: 20px; }
        h1, h2 { color: #333; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .summary p { margin: 5px 0; }
        .errors ul { color: red; }
    """
    html_body += "</style></head><body>"
    html_body += f"<h1>Inventree Order Report: {getattr(task_config, 'name', 'N/A')}</h1>"
    html_body += f"<p>Report generated on: {_current_datetime_string()}</p>"

    # Summary Section
    summary = getattr(calculation_result, 'summary', {})
    html_body += "<div class='summary'><h2>Summary</h2>"
    html_body += f"<p>Total Parts Requested: {summary.get('total_parts_requested', 'N/A')}</p>"
    html_body += f"<p>Total Parts Available: {summary.get('total_parts_available', 'N/A')}</p>"
    html_body += f"<p>Total Missing Parts: {summary.get('total_missing_parts', 'N/A')}</p>"
    html_body += f"<p>Overall Availability: {summary.get('overall_availability_percentage', 'N/A')}%</p>"
    html_body += "</div>"

    # Detailed BOM Table
    detailed_bom = getattr(calculation_result, 'detailed_bom', [])
    if detailed_bom:
        html_body += "<h2>Detailed Bill of Materials</h2>"
        html_body += "<table><tr><th>Part Name</th><th>IPN</th><th>Version</th><th>Required</th><th>Available</th><th>Missing</th><th>Notes</th></tr>"
        for part_row in detailed_bom:
            html_body += "<tr>"
            html_body += f"<td>{part_row.get('name', 'N/A')}</td>"
            html_body += f"<td>{part_row.get('ipn', '-')}</td>"
            html_body += f"<td>{part_row.get('version', '-')}</td>"
            html_body += f"<td>{part_row.get('quantity_required', 'N/A')}</td>"
            html_body += f"<td>{part_row.get('quantity_available', 'N/A')}</td>"
            html_body += f"<td>{part_row.get('quantity_missing', 'N/A')}</td>"
            html_body += f"<td>{part_row.get('notes', '')}</td>"
            html_body += "</tr>"
        html_body += "</table>"
    
    # Alternative Parts Section
    alternatives = getattr(calculation_result, 'alternatives_used', [])
    if alternatives:
        html_body += "<h2>Alternative Parts Used</h2>"
        html_body += "<table><tr><th>Original Part</th><th>Alternative Part</th><th>Quantity Used</th><th>Notes</th></tr>"
        for alt_row in alternatives:
            html_body += "<tr>"
            html_body += f"<td>{alt_row.get('original_part_name', 'N/A')} ({alt_row.get('original_part_ipn', 'N/A')})</td>"
            html_body += f"<td>{alt_row.get('alternative_part_name', 'N/A')} ({alt_row.get('alternative_part_ipn', 'N/A')})</td>"
            html_body += f"<td>{alt_row.get('quantity_used', 'N/A')}</td>"
            html_body += f"<td>{alt_row.get('notes', '')}</td>"
            html_body += "</tr>"
        html_body += "</table>"

    # Errors/Warnings
    warnings_or_errors = getattr(calculation_result, 'warnings_or_errors', [])
    if warnings_or_errors:
        html_body += "<div class='errors'><h2>Calculation Warnings/Errors</h2><ul>"
        for error_msg in warnings_or_errors:
            html_body += f"<li>{error_msg}</li>"
        html_body += "</ul></div>"

    html_body += "</body></html>"
    return html_body

def generate_text_email_content(task_config, calculation_result) -> str:
    """
    Generates a plain-text email body for the monitoring report.

    Args:
        task_config: The configuration object for the monitoring task.
        calculation_result: The result object from the order calculation.

    Returns:
        A string containing the plain-text email body.
    """
    text_body = f"Inventree Order Report: {getattr(task_config, 'name', 'N/A')}\n"
    text_body += f"Report generated on: {_current_datetime_string()}\n\n"

    # Summary
    summary = getattr(calculation_result, 'summary', {})
    text_body += "== Summary ==\n"
    text_body += f"Total Parts Requested: {summary.get('total_parts_requested', 'N/A')}\n"
    text_body += f"Total Parts Available: {summary.get('total_parts_available', 'N/A')}\n"
    text_body += f"Total Missing Parts: {summary.get('total_missing_parts', 'N/A')}\n"
    text_body += f"Overall Availability: {summary.get('overall_availability_percentage', 'N/A')}%\n\n"

    # Detailed BOM
    detailed_bom = getattr(calculation_result, 'detailed_bom', [])
    if detailed_bom:
        text_body += "== Detailed Bill of Materials ==\n"
        text_body += "Part Name | IPN | Version | Required | Available | Missing | Notes\n"
        text_body += "-----------------------------------------------------------------\n"
        for part_row in detailed_bom:
            text_body += f"{part_row.get('name', 'N/A')} | "
            text_body += f"{part_row.get('ipn', '-')} | "
            text_body += f"{part_row.get('version', '-')} | "
            text_body += f"{part_row.get('quantity_required', 'N/A')} | "
            text_body += f"{part_row.get('quantity_available', 'N/A')} | "
            text_body += f"{part_row.get('quantity_missing', 'N/A')} | "
            text_body += f"{part_row.get('notes', '')}\n"
        text_body += "\n"

    # Alternative Parts Section
    alternatives = getattr(calculation_result, 'alternatives_used', [])
    if alternatives:
        text_body += "== Alternative Parts Used ==\n"
        text_body += "Original Part | Alternative Part | Quantity Used | Notes\n"
        text_body += "-----------------------------------------------------------------\n"
        for alt_row in alternatives:
            text_body += f"{alt_row.get('original_part_name', 'N/A')} ({alt_row.get('original_part_ipn', 'N/A')}) | "
            text_body += f"{alt_row.get('alternative_part_name', 'N/A')} ({alt_row.get('alternative_part_ipn', 'N/A')}) | "
            text_body += f"{alt_row.get('quantity_used', 'N/A')} | "
            text_body += f"{alt_row.get('notes', '')}\n"
        text_body += "\n"

    # Errors/Warnings
    warnings_or_errors = getattr(calculation_result, 'warnings_or_errors', [])
    if warnings_or_errors:
        text_body += "== Calculation Warnings/Errors ==\n"
        for error_msg in warnings_or_errors:
            text_body += f"- {error_msg}\n"
        text_body += "\n"
        
    return text_body


class EmailService:
    """Handles sending emails via SMTP."""

    def __init__(self, config: EmailConfig):
        """
        Initializes the EmailService with email configuration.

        Args:
            config: An EmailConfig object containing SMTP server details and credentials.
        """
        self.config = config
        # Ensure logger is accessible if used within methods, or pass it if preferred.
        # For simplicity, class methods will use the module-level logger.

    def _create_mime_message(self, recipients: List[str], subject: str, html_content: str, text_content: str) -> MIMEMultipart:
        """
        Helper to construct a multipart MIME email message.
        """
        if not recipients:
            # This case should ideally be caught before calling _create_mime_message
            logger.error("MIME message creation: Recipients list cannot be empty.")
            raise ValueError("Recipients list cannot be empty for MIME message.")

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.config.sender_email
        msg['To'] = ", ".join(recipients) # Correctly join for display; sendmail takes a list
        
        part1 = MIMEText(text_content, 'plain', 'utf-8')
        part2 = MIMEText(html_content, 'html', 'utf-8')
        
        msg.attach(part1)
        msg.attach(part2)
        
        logger.debug(f"MIME message created. Subject: '{subject}', To: {', '.join(recipients)}")
        return msg

    def _send_over_smtp(self, recipient_email: str, message: MIMEMultipart) -> None:
        """
        Handles the actual SMTP connection and sending.
        This method is private and contains the core SMTP logic.
        """
        smtp_timeout = 30 # As per test expectations

        if self.config.use_ssl:
            logger.debug(f"Creating SMTP_SSL connection to {self.config.smtp_server}:{self.config.smtp_port}")
            with smtplib.SMTP_SSL(self.config.smtp_server, self.config.smtp_port, timeout=smtp_timeout) as server:
                server.ehlo()
                if self.config.smtp_user and self.config.smtp_password:
                    logger.debug(f"Logging in with SSL user: {self.config.smtp_user}")
                    server.login(self.config.smtp_user, self.config.smtp_password)
                server.sendmail(self.config.sender_email, [recipient_email], message.as_string())
                logger.info(f"Email sent successfully via SSL to {recipient_email}. Subject: '{message['Subject']}'")
        else:
            logger.debug(f"Creating SMTP connection to {self.config.smtp_server}:{self.config.smtp_port}")
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port, timeout=smtp_timeout) as server:
                server.ehlo()
                if self.config.use_tls:
                    logger.debug("Starting TLS")
                    server.starttls()
                    server.ehlo()
                if self.config.smtp_user and self.config.smtp_password:
                    logger.debug(f"Logging in with user: {self.config.smtp_user}")
                    server.login(self.config.smtp_user, self.config.smtp_password)
                server.sendmail(self.config.sender_email, [recipient_email], message.as_string())
                logger.info(f"Email sent successfully to {recipient_email}. Subject: '{message['Subject']}'")

    def send_email(self, subject: str, text_body: str, recipient_email: Optional[str] = None, html_body: Optional[str] = None) -> bool:
        """
        Sends an email using the configured SMTP settings.

        Args:
            subject: The subject of the email.
            text_body: The plain text body of the email.
            recipient_email: The primary recipient's email address. If None, uses default_recipient_email from config.
            html_body: Optional HTML body. If None, a simple HTML version of text_body is used.

        Returns:
            True if the email was sent successfully.

        Raises:
            ValueError: If no recipient is specified and no default is configured.
            smtplib.SMTPAuthenticationError: If authentication fails.
            smtplib.SMTPException, ConnectionRefusedError, TimeoutError: For other SMTP related errors.
            EmailSendingError: For unexpected errors during the process.
        """
        actual_recipient = recipient_email if recipient_email else self.config.default_recipient_email
        
        if not actual_recipient:
            logger.error("No recipient specified and no default recipient configured for email.")
            raise ValueError("Email recipient is not specified and no default is configured.")

        effective_html_body = html_body if html_body is not None else text_body.replace("\n", "<br>")
        if not html_body and text_body:
             effective_html_body = f"<p>{effective_html_body}</p>"

        try:
            message = self._create_mime_message(
                recipients=[actual_recipient],
                subject=subject,
                html_content=effective_html_body,
                text_content=text_body
            )
        except ValueError as e:
            logger.error(f"Failed to create MIME message: {e}")
            raise EmailSendingError(f"Failed to create MIME message: {e}") from e

        try:
            self._send_over_smtp(actual_recipient, message)
            return True
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP Authentication error for user '{self.config.smtp_user}': {e.smtp_code} {e.smtp_error}")
            raise
        except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, smtplib.SMTPHeloError, ConnectionRefusedError, TimeoutError) as e:
            logger.error(f"SMTP connection/communication error: {e}")
            raise
        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"SMTP server refused recipients: {e.recipients}. Error: {e.smtp_error}")
            raise EmailSendingError(f"Recipients refused: {e.recipients}") from e
        except smtplib.SMTPSenderRefused as e:
            logger.error(f"SMTP server refused sender: {self.config.sender_email}. Error: {e.smtp_error}")
            raise EmailSendingError(f"Sender refused: {self.config.sender_email}") from e
        except smtplib.SMTPDataError as e:
            logger.error(f"SMTP server refused message data. Error: {e.smtp_error}")
            raise EmailSendingError("Message data refused by server") from e
        except smtplib.SMTPException as e:
            logger.error(f"An unexpected SMTP error occurred: {e}")
            raise EmailSendingError("An unexpected SMTP error occurred") from e
        except Exception as e:
            logger.error(f"A non-SMTP error occurred during email sending: {e}", exc_info=True)
            raise EmailSendingError(f"A non-SMTP error occurred: {e}") from e