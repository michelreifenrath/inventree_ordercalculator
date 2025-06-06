# Tests for email sending functionality

import pytest
from unittest.mock import Mock, patch, MagicMock
import smtplib
from email.mime.multipart import MIMEMultipart

from src.inventree_order_calculator.email_sender import EmailSender, EmailSendError
from src.inventree_order_calculator.models import OutputTables, CalculatedPart
from src.inventree_order_calculator.email_config import (
    EmailConfig, SMTPConfig, EmailRecipients, ScheduleConfig,
    EmailSecurityType
)

class TestEmailSender:
    """Test email sending functionality"""
    
    @pytest.fixture
    def sample_config(self):
        """Create sample email configuration"""
        smtp = SMTPConfig(
            host="smtp.test.com",
            port=587,
            username="test@test.com",
            password="testpass",
            security=EmailSecurityType.TLS
        )
        
        recipients = EmailRecipients(
            to=["recipient1@test.com", "recipient2@test.com"],
            cc=["cc@test.com"],
            bcc=["bcc@test.com"]
        )
        
        return EmailConfig(
            smtp=smtp,
            sender_email="sender@test.com",
            sender_name="Test Sender",
            recipients=recipients,
            subject_template="Test Report - {{date}}",
            include_parts_table=True,
            include_assemblies_table=True,
            include_summary=True
        )
    
    @pytest.fixture
    def sample_results(self):
        """Create sample calculation results"""
        part1 = CalculatedPart(
            pk=1,
            name="Test Part 1",
            is_purchaseable=True,
            is_assembly=False,
            total_required=10.0,
            available=5.0,
            to_order=5.0,
            supplier_names=["Supplier A"],
            is_optional=False
        )
        
        return OutputTables(
            parts_to_order=[part1],
            subassemblies_to_build=[],
            warnings=[]
        )
    
    @pytest.fixture
    def email_sender(self, sample_config):
        """Create email sender instance"""
        return EmailSender(sample_config)
    
    def test_email_sender_initialization(self, sample_config):
        """Test email sender initialization"""
        sender = EmailSender(sample_config)
        assert sender.config == sample_config
        assert sender.formatter is not None
    
    @patch('src.inventree_order_calculator.email_sender.smtplib.SMTP')
    def test_send_report_success(self, mock_smtp, email_sender, sample_results):
        """Test successful email report sending"""
        # Mock SMTP server
        mock_server = Mock()
        mock_smtp.return_value = mock_server
        
        # Send report
        result = email_sender.send_report(sample_results, "Test Preset")
        
        # Verify SMTP calls
        mock_smtp.assert_called_once()
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@test.com", "testpass")
        mock_server.sendmail.assert_called_once()
        mock_server.quit.assert_called_once()
        
        assert result is True
    
    @patch('src.inventree_order_calculator.email_sender.smtplib.SMTP')
    def test_send_report_test_mode(self, mock_smtp, email_sender, sample_results):
        """Test email report sending in test mode"""
        # Mock SMTP server
        mock_server = Mock()
        mock_smtp.return_value = mock_server
        
        # Send report in test mode
        result = email_sender.send_report(sample_results, "Test Preset", test_mode=True)
        
        # Verify that sendmail was called with only first recipient
        mock_server.sendmail.assert_called_once()
        call_args = mock_server.sendmail.call_args[0]
        sender_email = call_args[0]
        recipients = call_args[1]
        
        assert sender_email == "sender@test.com"
        assert len(recipients) == 1  # Only first recipient in test mode
        assert "recipient1@test.com" in recipients
        
        assert result is True
    
    @patch('src.inventree_order_calculator.email_sender.smtplib.SMTP')
    def test_send_report_smtp_error(self, mock_smtp, email_sender, sample_results):
        """Test email report sending with SMTP error"""
        # Mock SMTP server to raise exception
        mock_smtp.side_effect = smtplib.SMTPException("SMTP Error")
        
        # Send report should raise EmailSendError
        with pytest.raises(EmailSendError):
            email_sender.send_report(sample_results, "Test Preset")
    
    @patch('src.inventree_order_calculator.email_sender.smtplib.SMTP')
    def test_test_connection_success(self, mock_smtp, email_sender):
        """Test successful SMTP connection test"""
        # Mock SMTP server
        mock_server = Mock()
        mock_smtp.return_value = mock_server
        
        # Test connection
        result = email_sender.test_connection()
        
        # Verify SMTP calls
        mock_smtp.assert_called_once()
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@test.com", "testpass")
        mock_server.quit.assert_called_once()
        
        assert result['success'] is True
        assert "successful" in result['message']
    
    @patch('src.inventree_order_calculator.email_sender.smtplib.SMTP')
    def test_test_connection_auth_error(self, mock_smtp, email_sender):
        """Test SMTP connection test with authentication error"""
        # Mock SMTP server to raise auth error
        mock_server = Mock()
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, "Authentication failed")
        mock_smtp.return_value = mock_server
        
        # Test connection
        result = email_sender.test_connection()
        
        assert result['success'] is False
        assert "Authentication failed" in result['message']
    
    @patch('src.inventree_order_calculator.email_sender.smtplib.SMTP')
    def test_test_connection_connect_error(self, mock_smtp, email_sender):
        """Test SMTP connection test with connection error"""
        # Mock SMTP to raise connection error
        mock_smtp.side_effect = smtplib.SMTPConnectError(421, "Connection failed")
        
        # Test connection
        result = email_sender.test_connection()
        
        assert result['success'] is False
        assert "Connection failed" in result['message']
    
    @patch('src.inventree_order_calculator.email_sender.smtplib.SMTP')
    def test_send_test_email_success(self, mock_smtp, email_sender):
        """Test successful test email sending"""
        # Mock SMTP server
        mock_server = Mock()
        mock_smtp.return_value = mock_server
        
        # Send test email
        result = email_sender.send_test_email("test@example.com")
        
        # Verify SMTP calls
        mock_smtp.assert_called_once()
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@test.com", "testpass")
        mock_server.sendmail.assert_called_once()
        mock_server.quit.assert_called_once()
        
        # Verify test email content
        call_args = mock_server.sendmail.call_args[0]
        sender_email = call_args[0]
        recipients = call_args[1]
        message_content = call_args[2]
        
        assert sender_email == "sender@test.com"
        assert recipients == ["test@example.com"]
        assert "Test Email" in message_content
        assert "smtp.test.com" in message_content  # Config details
        
        assert result is True
    
    @patch('src.inventree_order_calculator.email_sender.smtplib.SMTP')
    def test_send_test_email_error(self, mock_smtp, email_sender):
        """Test test email sending with error"""
        # Mock SMTP server to raise exception
        mock_smtp.side_effect = smtplib.SMTPException("SMTP Error")
        
        # Send test email should raise EmailSendError
        with pytest.raises(EmailSendError):
            email_sender.send_test_email("test@example.com")
    
    def test_get_recipients_normal_mode(self, email_sender):
        """Test recipient list generation in normal mode"""
        recipients = email_sender._get_recipients(test_mode=False)
        
        assert recipients['to'] == ["recipient1@test.com", "recipient2@test.com"]
        assert recipients['cc'] == ["cc@test.com"]
        assert recipients['bcc'] == ["bcc@test.com"]
        assert len(recipients['all']) == 4  # All recipients
    
    def test_get_recipients_test_mode(self, email_sender):
        """Test recipient list generation in test mode"""
        recipients = email_sender._get_recipients(test_mode=True)
        
        assert recipients['to'] == ["recipient1@test.com"]  # Only first recipient
        assert recipients['cc'] == []
        assert recipients['bcc'] == []
        assert len(recipients['all']) == 1  # Only one recipient
    
    def test_create_message(self, email_sender):
        """Test email message creation"""
        recipients = {
            'to': ["to@test.com"],
            'cc': ["cc@test.com"],
            'bcc': ["bcc@test.com"],
            'all': ["to@test.com", "cc@test.com", "bcc@test.com"]
        }
        
        message = email_sender._create_message(
            subject="Test Subject",
            html_content="<h1>Test HTML</h1>",
            text_content="Test Text",
            recipients=recipients
        )
        
        assert isinstance(message, MIMEMultipart)
        assert message["Subject"] == "Test Subject"
        assert message["From"] == "Test Sender <sender@test.com>"
        assert message["To"] == "to@test.com"
        assert message["Cc"] == "cc@test.com"
        assert "Bcc" not in message  # BCC should not be in headers
        
        # Check message parts
        parts = message.get_payload()
        assert len(parts) == 2  # Text and HTML parts
    
    @patch('src.inventree_order_calculator.email_sender.smtplib.SMTP_SSL')
    def test_create_smtp_connection_ssl(self, mock_smtp_ssl, sample_config):
        """Test SMTP connection creation with SSL"""
        # Modify config for SSL
        sample_config.smtp.security = EmailSecurityType.SSL
        sample_config.smtp.port = 465
        
        sender = EmailSender(sample_config)
        
        # Mock SMTP_SSL server
        mock_server = Mock()
        mock_smtp_ssl.return_value = mock_server
        
        # Create connection
        server = sender._create_smtp_connection()
        
        # Verify SSL connection
        mock_smtp_ssl.assert_called_once_with("smtp.test.com", 465, timeout=30)
        mock_server.login.assert_called_once_with("test@test.com", "testpass")
        assert server == mock_server
    
    @patch('src.inventree_order_calculator.email_sender.smtplib.SMTP')
    def test_create_smtp_connection_no_security(self, mock_smtp, sample_config):
        """Test SMTP connection creation without security"""
        # Modify config for no security
        sample_config.smtp.security = EmailSecurityType.NONE
        
        sender = EmailSender(sample_config)
        
        # Mock SMTP server
        mock_server = Mock()
        mock_smtp.return_value = mock_server
        
        # Create connection
        server = sender._create_smtp_connection()
        
        # Verify plain connection (no TLS)
        mock_smtp.assert_called_once_with("smtp.test.com", 587, timeout=30)
        mock_server.starttls.assert_not_called()  # No TLS for NONE security
        mock_server.login.assert_called_once_with("test@test.com", "testpass")
        assert server == mock_server
