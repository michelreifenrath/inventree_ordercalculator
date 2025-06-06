# Integration tests for email notification system

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.inventree_order_calculator.email_config import (
    EmailConfig, SMTPConfig, EmailRecipients, ScheduleConfig,
    EmailConfigManager, ScheduleFrequency, EmailSecurityType
)
from src.inventree_order_calculator.email_sender import EmailSender
from src.inventree_order_calculator.email_formatter import EmailFormatter
from src.inventree_order_calculator.email_scheduler import EmailSchedulerManager
from src.inventree_order_calculator.models import OutputTables, CalculatedPart
from src.inventree_order_calculator.presets_manager import Preset, PresetItem, PresetsFile

class TestEmailIntegration:
    """Integration tests for the complete email notification system"""
    
    @pytest.fixture
    def temp_config_file(self):
        """Create temporary config file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_path = Path(f.name)
        yield config_path
        if config_path.exists():
            config_path.unlink()
    
    @pytest.fixture
    def sample_email_config(self):
        """Create complete email configuration"""
        smtp = SMTPConfig(
            host="smtp.test.com",
            port=587,
            username="test@test.com",
            password="testpass",
            security=EmailSecurityType.TLS
        )
        
        recipients = EmailRecipients(
            to=["recipient@test.com"],
            cc=["cc@test.com"]
        )
        
        schedule = ScheduleConfig(
            enabled=True,
            frequency=ScheduleFrequency.DAILY,
            time_of_day="09:00",
            timezone="UTC",
            preset_name="test_preset"
        )
        
        return EmailConfig(
            smtp=smtp,
            sender_email="sender@test.com",
            sender_name="Test Sender",
            recipients=recipients,
            subject_template="Test Report - {{date}}",
            schedule=schedule,
            include_parts_table=True,
            include_assemblies_table=True,
            include_summary=True
        )
    
    @pytest.fixture
    def sample_calculation_results(self):
        """Create sample calculation results"""
        part1 = CalculatedPart(
            pk=1,
            name="Test Part 1",
            is_purchaseable=True,
            is_assembly=False,
            total_required=10.0,
            available=5.0,
            to_order=5.0,
            supplier_names=["Supplier A", "Supplier B"],
            is_optional=False
        )
        
        part2 = CalculatedPart(
            pk=2,
            name="Optional Part",
            is_purchaseable=True,
            is_assembly=False,
            total_required=3.0,
            available=0.0,
            to_order=3.0,
            supplier_names=["Supplier C"],
            is_optional=True
        )
        
        assembly1 = CalculatedPart(
            pk=3,
            name="Test Assembly",
            is_purchaseable=False,
            is_assembly=True,
            total_required=2.0,
            available=0.0,
            to_build=2.0,
            building=1.0,
            is_optional=False
        )
        
        return OutputTables(
            parts_to_order=[part1, part2],
            subassemblies_to_build=[assembly1],
            warnings=["Test warning: Some parts may be out of stock"]
        )
    
    @pytest.fixture
    def sample_presets_data(self):
        """Create sample presets data"""
        preset = Preset(
            name="test_preset",
            items=[
                PresetItem(part_id=1, quantity=10),
                PresetItem(part_id=2, quantity=5)
            ]
        )
        
        return PresetsFile(presets=[preset])
    
    def test_config_save_load_cycle(self, temp_config_file, sample_email_config):
        """Test complete configuration save and load cycle"""
        # Create config manager with temp file
        config_manager = EmailConfigManager(temp_config_file)
        
        # Save configuration
        success = config_manager.save_config(sample_email_config)
        assert success is True
        assert temp_config_file.exists()
        
        # Load configuration
        loaded_config = config_manager.load_config()
        assert loaded_config is not None
        
        # Verify all fields are preserved
        assert loaded_config.smtp.host == sample_email_config.smtp.host
        assert loaded_config.smtp.port == sample_email_config.smtp.port
        assert loaded_config.sender_email == sample_email_config.sender_email
        assert loaded_config.recipients.to == sample_email_config.recipients.to
        assert loaded_config.schedule.enabled == sample_email_config.schedule.enabled
        assert loaded_config.schedule.preset_name == sample_email_config.schedule.preset_name
    
    def test_email_formatting_complete(self, sample_email_config, sample_calculation_results):
        """Test complete email formatting with all components"""
        formatter = EmailFormatter()
        
        # Format email with all options enabled
        content = formatter.format_email(
            results=sample_calculation_results,
            config=sample_email_config,
            preset_name="test_preset"
        )
        
        # Verify both formats are generated
        assert 'html' in content
        assert 'text' in content
        
        html_content = content['html']
        text_content = content['text']
        
        # Verify HTML content includes all components
        assert "test_preset" in html_content
        assert "Test Part 1" in html_content
        assert "Optional Part" in html_content
        assert "Test Assembly" in html_content
        assert "Test warning" in html_content
        assert "Summary" in html_content
        assert "(Optional)" in html_content  # Optional part indicator
        
        # Verify text content includes all components
        assert "test_preset" in text_content
        assert "Test Part 1" in text_content
        assert "Optional Part" in text_content
        assert "Test Assembly" in text_content
        assert "Test warning" in text_content
        assert "SUMMARY" in text_content
        assert "(Opt)" in text_content  # Optional part indicator
        
        # Verify subject formatting
        subject = formatter.format_subject(
            sample_email_config.subject_template,
            "test_preset"
        )
        assert "Test Report" in subject
        assert "2025" in subject or "2024" in subject  # Current year
    
    @patch('src.inventree_order_calculator.email_sender.smtplib.SMTP')
    def test_email_sending_integration(self, mock_smtp, sample_email_config, sample_calculation_results):
        """Test complete email sending integration"""
        # Mock SMTP server
        mock_server = Mock()
        mock_smtp.return_value = mock_server
        
        # Create email sender
        sender = EmailSender(sample_email_config)
        
        # Send email report
        success = sender.send_report(
            results=sample_calculation_results,
            preset_name="test_preset",
            test_mode=False
        )
        
        # Verify success
        assert success is True
        
        # Verify SMTP interactions
        mock_smtp.assert_called_once()
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@test.com", "testpass")
        mock_server.sendmail.assert_called_once()
        mock_server.quit.assert_called_once()
        
        # Verify email content
        call_args = mock_server.sendmail.call_args[0]
        sender_email = call_args[0]
        recipients = call_args[1]
        message_content = call_args[2]
        
        assert sender_email == "sender@test.com"
        assert "recipient@test.com" in recipients
        assert "cc@test.com" in recipients
        assert "Test Part 1" in message_content
        assert "Test Assembly" in message_content
        assert "test_preset" in message_content
    
    def test_scheduler_integration(self, sample_email_config, sample_presets_data):
        """Test scheduler integration with configuration"""
        # Mock API client
        mock_api_client = Mock()
        
        # Create scheduler manager
        scheduler_manager = EmailSchedulerManager(mock_api_client, sample_presets_data)
        
        # Start scheduler
        success = scheduler_manager.start_scheduler()
        assert success is True
        
        # Update schedule
        success = scheduler_manager.update_schedule(sample_email_config)
        assert success is True
        
        # Check status
        status = scheduler_manager.get_status()
        assert status['running'] is True
        assert status['scheduled'] is True
        assert status['next_run'] is not None
        
        # Stop scheduler
        success = scheduler_manager.stop_scheduler()
        assert success is True
        
        status = scheduler_manager.get_status()
        assert status['running'] is False
    
    def test_configuration_validation_integration(self, sample_email_config):
        """Test configuration validation integration"""
        config_manager = EmailConfigManager()
        
        # Valid configuration should pass
        errors = config_manager.validate_config(sample_email_config)
        assert len(errors) == 0
        
        # Invalid configuration should fail
        # Create config with valid structure but invalid content
        invalid_config = EmailConfig(
            smtp=SMTPConfig(
                host="",  # Invalid empty host
                port=587,
                username="test@test.com",
                password="testpass"
            ),
            sender_email="sender@test.com",  # Valid email format for Pydantic
            recipients=EmailRecipients(to=["test@test.com"]),  # Valid for Pydantic
            schedule=ScheduleConfig(
                enabled=True,
                preset_name=""  # Empty preset name
            )
        )

        # Manually set invalid values after creation to bypass Pydantic validation
        invalid_config.smtp.host = ""
        invalid_config.recipients.to = []
        
        errors = config_manager.validate_config(invalid_config)
        assert len(errors) > 0
        assert any("SMTP host is required" in error for error in errors)
        assert any("recipient email is required" in error for error in errors)
        assert any("Preset name is required" in error for error in errors)
    
    @patch('src.inventree_order_calculator.email_sender.smtplib.SMTP')
    def test_test_mode_integration(self, mock_smtp, sample_email_config, sample_calculation_results):
        """Test email sending in test mode"""
        # Mock SMTP server
        mock_server = Mock()
        mock_smtp.return_value = mock_server
        
        # Create email sender
        sender = EmailSender(sample_email_config)
        
        # Send email in test mode
        success = sender.send_report(
            results=sample_calculation_results,
            preset_name="test_preset",
            test_mode=True
        )
        
        # Verify success
        assert success is True
        
        # Verify only first recipient is used in test mode
        call_args = mock_server.sendmail.call_args[0]
        recipients = call_args[1]
        assert len(recipients) == 1
        assert "recipient@test.com" in recipients
        assert "cc@test.com" not in recipients  # CC should be excluded in test mode
    
    def test_selective_content_integration(self, sample_calculation_results):
        """Test email formatting with selective content inclusion"""
        # Create config with only parts table enabled
        smtp = SMTPConfig(
            host="smtp.test.com",
            port=587,
            username="test@test.com",
            password="testpass"
        )
        
        recipients = EmailRecipients(to=["test@test.com"])
        
        config = EmailConfig(
            smtp=smtp,
            sender_email="sender@test.com",
            recipients=recipients,
            include_parts_table=True,
            include_assemblies_table=False,
            include_summary=False
        )
        
        formatter = EmailFormatter()
        content = formatter.format_email(
            results=sample_calculation_results,
            config=config
        )
        
        html_content = content['html']
        text_content = content['text']
        
        # Should include parts but not assemblies or summary
        assert "Test Part 1" in html_content
        assert "Test Assembly" not in html_content
        assert "Summary" not in html_content
        
        assert "Test Part 1" in text_content
        assert "Test Assembly" not in text_content
        assert "SUMMARY" not in text_content
    
    def test_error_handling_integration(self, sample_email_config):
        """Test error handling throughout the system"""
        # Test invalid SMTP configuration
        invalid_smtp_config = EmailConfig(
            smtp=SMTPConfig(
                host="invalid.smtp.server",
                port=587,
                username="test@test.com",
                password="wrongpassword"
            ),
            sender_email="sender@test.com",
            recipients=EmailRecipients(to=["test@test.com"])
        )
        
        sender = EmailSender(invalid_smtp_config)
        
        # Connection test should fail gracefully
        result = sender.test_connection()
        assert result['success'] is False
        assert 'error' in result['message'].lower() or 'failed' in result['message'].lower()
        
        # Test configuration manager with invalid JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json }")
            invalid_config_path = Path(f.name)
        
        try:
            config_manager = EmailConfigManager(invalid_config_path)
            loaded_config = config_manager.load_config()
            assert loaded_config is None  # Should handle invalid JSON gracefully
        finally:
            invalid_config_path.unlink()
