import pytest
from unittest.mock import patch, MagicMock

from inventree_order_calculator.email_service import EmailService
from inventree_order_calculator.config import EmailConfig

# TDD Anchor: Test basic email sending functionality (mocking SMTP)
# Test Goal: Verify that EmailService.send_email attempts to connect to SMTP,
# login, send mail, and quit.

@pytest.fixture
def email_config():
    """Provides a basic EmailConfig for testing."""
    return EmailConfig(
        smtp_server="smtp.example.com",
        smtp_port=587,
        smtp_user="user@example.com",
        smtp_password="password",
        sender_email="sender@example.com",
        use_tls=True,
        use_ssl=False,
        default_recipient_email="recipient@example.com"
    )

@pytest.fixture
def email_service(email_config):
    """Provides an EmailService instance with mocked config."""
    return EmailService(config=email_config)

def test_send_email_attempts_smtp_connection_and_send(email_service, email_config):
    """
    Tests that send_email attempts to connect, login, send, and quit SMTP server.
    This is a failing test initially.
    """
    subject = "Test Subject"
    body = "Test Body"
    recipient = "test_recipient@example.com"

    with patch("smtplib.SMTP") as mock_smtp_constructor:
        mock_smtp_instance = MagicMock()
        mock_smtp_constructor.return_value.__enter__.return_value = mock_smtp_instance

        email_service.send_email(subject, body, recipient)

        mock_smtp_constructor.assert_called_once_with(email_config.smtp_server, email_config.smtp_port, timeout=30)
        mock_smtp_instance.ehlo.assert_called_once()
        mock_smtp_instance.starttls.assert_called_once() # Assuming use_tls=True
        mock_smtp_instance.login.assert_called_once_with(email_config.smtp_user, email_config.smtp_password)
        
        # We need to check the arguments to sendmail more carefully
        # For now, just check it was called.
        # Actual message content check will be a separate test or refinement.
        assert mock_smtp_instance.sendmail.called
        
        # Check that the correct from_addr, to_addrs are used
        args, kwargs = mock_smtp_instance.sendmail.call_args
        assert args[0] == email_config.sender_email
        assert args[1] == [recipient]
        # args[2] is the message, will test its content later

        mock_smtp_instance.quit.assert_called_once()

# TDD Anchor: Test email sending with SSL
def test_send_email_with_ssl(email_config):
    """Tests email sending when use_ssl is True."""
    email_config.use_tls = False
    email_config.use_ssl = True
    service_ssl = EmailService(config=email_config)
    subject = "SSL Test"
    body = "SSL Body"
    recipient = "ssl_recipient@example.com"

    with patch("smtplib.SMTP_SSL") as mock_smtp_ssl_constructor:
        mock_smtp_instance = MagicMock()
        mock_smtp_ssl_constructor.return_value.__enter__.return_value = mock_smtp_instance

        service_ssl.send_email(subject, body, recipient)

        mock_smtp_ssl_constructor.assert_called_once_with(email_config.smtp_server, email_config.smtp_port, timeout=30)
        mock_smtp_instance.ehlo.assert_called_once() # SMTP_SSL might not need ehlo before login if not using starttls
        mock_smtp_instance.login.assert_called_once_with(email_config.smtp_user, email_config.smtp_password)
        assert mock_smtp_instance.sendmail.called
        mock_smtp_instance.quit.assert_called_once()

# TDD Anchor: Test correct email message formatting (MIMEText)
def test_send_email_formats_message_correctly(email_service, email_config):
    """Tests that the email message is formatted correctly using MIMEText."""
    subject = "Formatted Subject"
    body = "Formatted Body Content"
    recipient = "format_recipient@example.com"

    with patch("smtplib.SMTP") as mock_smtp_constructor:
        mock_smtp_instance = MagicMock()
        mock_smtp_constructor.return_value.__enter__.return_value = mock_smtp_instance

        email_service.send_email(subject, body, recipient)

        assert mock_smtp_instance.sendmail.called
        args, _ = mock_smtp_instance.sendmail.call_args
        sent_message = args[2] # The msg string

        assert f"Subject: {subject}" in sent_message
        assert f"From: {email_config.sender_email}" in sent_message
        assert f"To: {recipient}" in sent_message
        assert "\n\n" + body in sent_message # Ensure body is separated from headers

# TDD Anchor: Test SMTP connection error handling
def test_send_email_handles_smtp_connection_error(email_service, email_config):
    """Tests that SMTP connection errors are handled (e.g., logged)."""
    subject = "Connection Error Test"
    body = "Body"
    recipient = "error_recipient@example.com"

    with patch("smtplib.SMTP") as mock_smtp_constructor:
        mock_smtp_constructor.side_effect = ConnectionRefusedError("Test connection error")
        
        with pytest.raises(ConnectionRefusedError): # Or a custom exception if EmailService wraps it
             email_service.send_email(subject, body, recipient)
        # Add assertion for logging if implemented, e.g., mock logger.error.assert_called_once()

# TDD Anchor: Test SMTP authentication error handling
def test_send_email_handles_smtp_authentication_error(email_service, email_config):
    """Tests that SMTP authentication errors are handled."""
    subject = "Auth Error Test"
    body = "Body"
    recipient = "auth_error@example.com"

    with patch("smtplib.SMTP") as mock_smtp_constructor:
        mock_smtp_instance = MagicMock()
        mock_smtp_constructor.return_value.__enter__.return_value = mock_smtp_instance
        mock_smtp_instance.login.side_effect = smtplib.SMTPAuthenticationError(535, "Authentication credentials invalid")

        with pytest.raises(smtplib.SMTPAuthenticationError): # Or a custom exception
            email_service.send_email(subject, body, recipient)
        # Add assertion for logging

# TDD Anchor: Test sending to default recipient if none provided
def test_send_email_uses_default_recipient_if_none_provided(email_service, email_config):
    """Tests that the default recipient is used if no recipient is specified."""
    subject = "Default Recipient Test"
    body = "This should go to the default recipient."
    
    with patch("smtplib.SMTP") as mock_smtp_constructor:
        mock_smtp_instance = MagicMock()
        mock_smtp_constructor.return_value.__enter__.return_value = mock_smtp_instance

        email_service.send_email(subject, body) # No recipient provided

        mock_smtp_instance.sendmail.assert_called_once()
        args, _ = mock_smtp_instance.sendmail.call_args
        assert args[1] == [email_config.default_recipient_email]

# TDD Anchor: Test sending without TLS/SSL if configured
def test_send_email_without_tls_ssl(email_config):
    """Tests email sending when both use_tls and use_ssl are False."""
    email_config.use_tls = False
    email_config.use_ssl = False
    service_no_secure = EmailService(config=email_config)
    subject = "No TLS/SSL Test"
    body = "Plain text body"
    recipient = "plain_recipient@example.com"

    with patch("smtplib.SMTP") as mock_smtp_constructor:
        mock_smtp_instance = MagicMock()
        mock_smtp_constructor.return_value.__enter__.return_value = mock_smtp_instance

        service_no_secure.send_email(subject, body, recipient)

        mock_smtp_constructor.assert_called_once_with(email_config.smtp_server, email_config.smtp_port, timeout=30)
        mock_smtp_instance.ehlo.assert_called_once()
        mock_smtp_instance.starttls.assert_not_called()
        mock_smtp_instance.login.assert_called_once_with(email_config.smtp_user, email_config.smtp_password)
        assert mock_smtp_instance.sendmail.called
        mock_smtp_instance.quit.assert_called_once()