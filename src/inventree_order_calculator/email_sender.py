# Module: src/inventree_order_calculator/email_sender.py
# Description: Email sending functionality for order calculator notifications

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional
from .email_config import EmailConfig, EmailSecurityType
from .email_formatter import EmailFormatter
from .models import OutputTables

logger = logging.getLogger(__name__)

class EmailSendError(Exception):
    """Custom exception for email sending errors"""
    pass

class EmailSender:
    """Handles sending of formatted email reports"""
    
    def __init__(self, config: EmailConfig):
        self.config = config
        self.formatter = EmailFormatter()
    
    def send_report(
        self, 
        results: OutputTables, 
        preset_name: Optional[str] = None,
        test_mode: bool = False
    ) -> bool:
        """
        Send email report with calculation results
        
        Args:
            results: OutputTables containing calculation results
            preset_name: Name of preset used for calculation
            test_mode: If True, only sends to first recipient for testing
            
        Returns:
            True if email sent successfully, False otherwise
            
        Raises:
            EmailSendError: If email sending fails
        """
        try:
            # Format email content
            content = self.formatter.format_email(results, self.config, preset_name)
            
            # Format subject
            subject = self.formatter.format_subject(
                self.config.subject_template, 
                preset_name
            )
            
            # Determine recipients based on test mode
            recipients = self._get_recipients(test_mode)
            
            # Create and send email
            message = self._create_message(
                subject=subject,
                html_content=content['html'],
                text_content=content['text'],
                recipients=recipients
            )
            
            self._send_message(message, recipients['all'])

            recipient_count = len(recipients['all'])
            logger.info(f"Email report sent successfully to {recipient_count} recipients")
            if test_mode:
                logger.info("Email sent in test mode (limited recipients)")

            return True
            
        except Exception as e:
            error_msg = f"Failed to send email report: {e}"
            logger.error(error_msg)
            raise EmailSendError(error_msg) from e
    
    def test_connection(self) -> Dict[str, any]:
        """
        Test SMTP connection and authentication
        
        Returns:
            Dict with 'success' boolean and 'message' string
        """
        try:
            server = self._create_smtp_connection()
            server.quit()
            
            return {
                'success': True,
                'message': 'SMTP connection successful'
            }
            
        except smtplib.SMTPAuthenticationError as e:
            return {
                'success': False,
                'message': f'Authentication failed: {e}'
            }
        except smtplib.SMTPConnectError as e:
            return {
                'success': False,
                'message': f'Connection failed: {e}'
            }
        except smtplib.SMTPException as e:
            return {
                'success': False,
                'message': f'SMTP error: {e}'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Unexpected error: {e}'
            }
    
    def send_test_email(self, test_recipient: str) -> bool:
        """
        Send a simple test email to verify configuration
        
        Args:
            test_recipient: Email address to send test to
            
        Returns:
            True if test email sent successfully
        """
        try:
            # Create simple test message
            message = MIMEMultipart("alternative")
            message["Subject"] = "InvenTree Order Calculator - Test Email"
            message["From"] = f"{self.config.sender_name} <{self.config.sender_email}>"
            message["To"] = test_recipient
            
            # Create test content
            text_content = f"""
This is a test email from InvenTree Order Calculator.

If you received this email, your email configuration is working correctly.

Configuration Details:
- SMTP Server: {self.config.smtp.host}:{self.config.smtp.port}
- Security: {self.config.smtp.security.value}
- Sender: {self.config.sender_email}

This is an automated test message.
            """
            
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Test Email</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; color: #333; }}
        .header {{ background-color: #27ae60; color: white; padding: 20px; border-radius: 5px; }}
        .content {{ padding: 20px; }}
        .config {{ background-color: #ecf0f1; padding: 15px; margin: 20px 0; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>✅ Test Email Successful</h1>
        <p>InvenTree Order Calculator</p>
    </div>

    <div class="content">
        <p>If you received this email, your email configuration is working correctly.</p>

        <div class="config">
            <h3>Configuration Details:</h3>
            <ul>
                <li><strong>SMTP Server:</strong> {self.config.smtp.host}:{self.config.smtp.port}</li>
                <li><strong>Security:</strong> {self.config.smtp.security.value}</li>
                <li><strong>Sender:</strong> {self.config.sender_email}</li>
            </ul>
        </div>

        <p><em>This is an automated test message.</em></p>
    </div>
</body>
</html>
            """
            
            # Attach content
            text_part = MIMEText(text_content, "plain")
            html_part = MIMEText(html_content, "html")
            message.attach(text_part)
            message.attach(html_part)
            
            # Send test email
            self._send_message(message, [test_recipient])

            logger.info(f"Test email sent successfully to {test_recipient}")

            return True
            
        except Exception as e:
            logger.error(f"Failed to send test email: {e}")
            raise EmailSendError(f"Test email failed: {e}") from e
    
    def _get_recipients(self, test_mode: bool) -> Dict[str, List[str]]:
        """Get recipient lists based on mode"""
        if test_mode:
            # In test mode, only send to first recipient
            to_list = [self.config.recipients.to[0]]
            cc_list = []
            bcc_list = []
        else:
            to_list = list(self.config.recipients.to)
            cc_list = list(self.config.recipients.cc)
            bcc_list = list(self.config.recipients.bcc)
        
        all_recipients = to_list + cc_list + bcc_list
        
        return {
            'to': to_list,
            'cc': cc_list,
            'bcc': bcc_list,
            'all': all_recipients
        }
    
    def _create_message(
        self, 
        subject: str, 
        html_content: str, 
        text_content: str,
        recipients: Dict[str, List[str]]
    ) -> MIMEMultipart:
        """Create email message with content"""
        
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{self.config.sender_name} <{self.config.sender_email}>"
        message["To"] = ", ".join(recipients['to'])
        
        if recipients['cc']:
            message["Cc"] = ", ".join(recipients['cc'])
        
        # Note: BCC recipients are not added to headers for privacy
        
        # Attach content (text first, then HTML for proper fallback)
        text_part = MIMEText(text_content, "plain")
        html_part = MIMEText(html_content, "html")
        
        message.attach(text_part)
        message.attach(html_part)
        
        return message
    
    def _create_smtp_connection(self) -> smtplib.SMTP:
        """Create and configure SMTP connection"""
        
        # Create SMTP connection
        if self.config.smtp.security == EmailSecurityType.SSL:
            server = smtplib.SMTP_SSL(
                self.config.smtp.host, 
                self.config.smtp.port,
                timeout=self.config.smtp.timeout
            )
        else:
            server = smtplib.SMTP(
                self.config.smtp.host, 
                self.config.smtp.port,
                timeout=self.config.smtp.timeout
            )
            
            # Start TLS if required
            if self.config.smtp.security == EmailSecurityType.TLS:
                server.starttls()
        
        # Authenticate
        server.login(self.config.smtp.username, self.config.smtp.password)
        
        return server
    
    def _send_message(self, message: MIMEMultipart, recipients: List[str]) -> bool:
        """Send email message via SMTP"""
        
        try:
            server = self._create_smtp_connection()
            
            # Send email
            server.sendmail(
                self.config.sender_email,
                recipients,
                message.as_string()
            )
            
            server.quit()
            return True
            
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email: {e}")
            raise EmailSendError(f"SMTP error: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
            raise EmailSendError(f"Unexpected error: {e}") from e
