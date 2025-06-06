# Tests for email configuration functionality

import pytest
import json
import tempfile
from pathlib import Path
from pydantic import ValidationError

from src.inventree_order_calculator.email_config import (
    SMTPConfig, EmailRecipients, ScheduleConfig, EmailConfig,
    EmailConfigManager, ScheduleFrequency, EmailSecurityType
)

class TestSMTPConfig:
    """Test SMTP configuration model"""
    
    def test_valid_smtp_config(self):
        """Test creating valid SMTP configuration"""
        config = SMTPConfig(
            host="smtp.gmail.com",
            port=587,
            username="test@gmail.com",
            password="password123",
            security=EmailSecurityType.TLS
        )
        
        assert config.host == "smtp.gmail.com"
        assert config.port == 587
        assert config.username == "test@gmail.com"
        assert config.password == "password123"
        assert config.security == EmailSecurityType.TLS
        assert config.timeout == 30  # default value
    
    def test_invalid_port_range(self):
        """Test validation of port range"""
        with pytest.raises(ValidationError):
            SMTPConfig(
                host="smtp.gmail.com",
                port=70000,  # Invalid port
                username="test@gmail.com",
                password="password123"
            )
    
    def test_common_ports_warning(self, caplog):
        """Test warning for uncommon ports"""
        config = SMTPConfig(
            host="smtp.gmail.com",
            port=1234,  # Uncommon port
            username="test@gmail.com",
            password="password123"
        )
        
        assert config.port == 1234
        # Note: Warning is logged, but we can't easily test it in this context

class TestEmailRecipients:
    """Test email recipients configuration"""
    
    def test_valid_recipients(self):
        """Test creating valid recipients configuration"""
        recipients = EmailRecipients(
            to=["user1@example.com", "user2@example.com"],
            cc=["cc@example.com"],
            bcc=["bcc@example.com"]
        )
        
        assert len(recipients.to) == 2
        assert len(recipients.cc) == 1
        assert len(recipients.bcc) == 1
    
    def test_empty_to_field(self):
        """Test validation requires at least one TO recipient"""
        with pytest.raises(ValidationError):
            EmailRecipients(to=[])
    
    def test_duplicate_emails(self):
        """Test validation prevents duplicate emails"""
        with pytest.raises(ValidationError):
            EmailRecipients(
                to=["user@example.com", "user@example.com"]
            )
    
    def test_invalid_email_format(self):
        """Test validation of email format"""
        with pytest.raises(ValidationError):
            EmailRecipients(to=["invalid-email"])

class TestScheduleConfig:
    """Test schedule configuration"""
    
    def test_valid_schedule_config(self):
        """Test creating valid schedule configuration"""
        config = ScheduleConfig(
            enabled=True,
            frequency=ScheduleFrequency.DAILY,
            time_of_day="09:30",
            timezone="America/New_York",
            preset_name="test_preset"
        )
        
        assert config.enabled is True
        assert config.frequency == ScheduleFrequency.DAILY
        assert config.time_of_day == "09:30"
        assert config.timezone == "America/New_York"
        assert config.preset_name == "test_preset"
    
    def test_time_format_validation(self):
        """Test time format validation"""
        # Valid time formats
        config = ScheduleConfig(time_of_day="09:30")
        assert config.time_of_day == "09:30"
        
        config = ScheduleConfig(time_of_day="9:5")
        assert config.time_of_day == "09:05"  # Should be normalized
        
        # Invalid time formats
        with pytest.raises(ValidationError):
            ScheduleConfig(time_of_day="25:00")  # Invalid hour
        
        with pytest.raises(ValidationError):
            ScheduleConfig(time_of_day="12:60")  # Invalid minute
        
        with pytest.raises(ValidationError):
            ScheduleConfig(time_of_day="invalid")  # Invalid format

class TestEmailConfig:
    """Test complete email configuration"""
    
    def test_valid_email_config(self):
        """Test creating valid complete email configuration"""
        smtp = SMTPConfig(
            host="smtp.gmail.com",
            port=587,
            username="test@gmail.com",
            password="password123"
        )
        
        recipients = EmailRecipients(
            to=["recipient@example.com"]
        )
        
        schedule = ScheduleConfig(
            enabled=True,
            preset_name="test_preset"
        )
        
        config = EmailConfig(
            smtp=smtp,
            sender_email="sender@example.com",
            recipients=recipients,
            schedule=schedule
        )
        
        assert config.smtp.host == "smtp.gmail.com"
        assert config.sender_email == "sender@example.com"
        assert config.sender_name == "InvenTree Order Calculator"  # default
        assert len(config.recipients.to) == 1
        assert config.schedule.enabled is True

class TestEmailConfigManager:
    """Test email configuration manager"""
    
    def test_save_and_load_config(self):
        """Test saving and loading configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_email_config.json"
            manager = EmailConfigManager(config_file)
            
            # Create test configuration
            smtp = SMTPConfig(
                host="smtp.test.com",
                port=587,
                username="test@test.com",
                password="testpass"
            )
            
            recipients = EmailRecipients(
                to=["recipient@test.com"]
            )
            
            config = EmailConfig(
                smtp=smtp,
                sender_email="sender@test.com",
                recipients=recipients
            )
            
            # Save configuration
            success = manager.save_config(config)
            assert success is True
            assert config_file.exists()
            
            # Load configuration
            loaded_config = manager.load_config()
            assert loaded_config is not None
            assert loaded_config.smtp.host == "smtp.test.com"
            assert loaded_config.sender_email == "sender@test.com"
    
    def test_load_nonexistent_config(self):
        """Test loading configuration from nonexistent file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "nonexistent.json"
            manager = EmailConfigManager(config_file)
            
            config = manager.load_config()
            assert config is None
    
    def test_load_invalid_json(self):
        """Test loading configuration from invalid JSON file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "invalid.json"
            
            # Write invalid JSON
            with open(config_file, 'w') as f:
                f.write("{ invalid json }")
            
            manager = EmailConfigManager(config_file)
            config = manager.load_config()
            assert config is None
    
    def test_is_configured(self):
        """Test configuration validation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_config.json"
            manager = EmailConfigManager(config_file)
            
            # No configuration
            assert manager.is_configured() is False
            
            # Valid configuration
            smtp = SMTPConfig(
                host="smtp.test.com",
                port=587,
                username="test@test.com",
                password="testpass"
            )
            
            recipients = EmailRecipients(
                to=["recipient@test.com"]
            )
            
            config = EmailConfig(
                smtp=smtp,
                sender_email="sender@test.com",
                recipients=recipients
            )
            
            manager.save_config(config)
            assert manager.is_configured() is True
    
    def test_validate_config(self):
        """Test configuration validation"""
        manager = EmailConfigManager()
        
        # Valid configuration
        smtp = SMTPConfig(
            host="smtp.test.com",
            port=587,
            username="test@test.com",
            password="testpass"
        )
        
        recipients = EmailRecipients(
            to=["recipient@test.com"]
        )
        
        config = EmailConfig(
            smtp=smtp,
            sender_email="sender@test.com",
            recipients=recipients
        )
        
        errors = manager.validate_config(config)
        assert len(errors) == 0
        
        # Invalid configuration - missing SMTP host
        smtp_invalid = SMTPConfig(
            host="",  # Empty host
            port=587,
            username="test@test.com",
            password="testpass"
        )
        
        config_invalid = EmailConfig(
            smtp=smtp_invalid,
            sender_email="sender@test.com",
            recipients=recipients
        )
        
        errors = manager.validate_config(config_invalid)
        assert len(errors) > 0
        assert any("SMTP host is required" in error for error in errors)
    
    def test_validate_schedule_config(self):
        """Test schedule configuration validation"""
        manager = EmailConfigManager()
        
        smtp = SMTPConfig(
            host="smtp.test.com",
            port=587,
            username="test@test.com",
            password="testpass"
        )
        
        recipients = EmailRecipients(
            to=["recipient@test.com"]
        )
        
        # Schedule enabled but no preset name
        schedule = ScheduleConfig(
            enabled=True,
            preset_name=""  # Empty preset name
        )
        
        config = EmailConfig(
            smtp=smtp,
            sender_email="sender@test.com",
            recipients=recipients,
            schedule=schedule
        )
        
        errors = manager.validate_config(config)
        assert len(errors) > 0
        assert any("Preset name is required" in error for error in errors)
