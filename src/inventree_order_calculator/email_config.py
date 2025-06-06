# Module: src/inventree_order_calculator/email_config.py
# Description: Email configuration models and management for automated notifications

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path
import json
import logging
from enum import Enum
from pydantic import BaseModel, EmailStr, field_validator, Field

logger = logging.getLogger(__name__)

class ScheduleFrequency(str, Enum):
    """Enumeration for schedule frequency options"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class EmailSecurityType(str, Enum):
    """Enumeration for email security types"""
    NONE = "none"
    TLS = "tls"
    SSL = "ssl"

class SMTPConfig(BaseModel):
    """SMTP server configuration"""
    host: str = Field(..., description="SMTP server hostname")
    port: int = Field(587, description="SMTP server port", ge=1, le=65535)
    username: str = Field(..., description="SMTP username")
    password: str = Field(..., description="SMTP password")
    security: EmailSecurityType = Field(EmailSecurityType.TLS, description="Security type")
    timeout: int = Field(30, description="Connection timeout in seconds", ge=1, le=300)

    @field_validator('port')
    @classmethod
    def validate_port(cls, v):
        """Validate common SMTP ports"""
        common_ports = [25, 465, 587, 993, 995]
        if v not in common_ports:
            logger.warning(f"Port {v} is not a common SMTP port. Common ports: {common_ports}")
        return v

class EmailRecipients(BaseModel):
    """Email recipients configuration"""
    to: List[EmailStr] = Field(..., description="Primary recipients", min_length=1)
    cc: List[EmailStr] = Field(default_factory=list, description="CC recipients")
    bcc: List[EmailStr] = Field(default_factory=list, description="BCC recipients")

    @field_validator('to', 'cc', 'bcc')
    @classmethod
    def validate_unique_emails(cls, v):
        """Ensure no duplicate email addresses"""
        if len(v) != len(set(v)):
            raise ValueError("Duplicate email addresses are not allowed")
        return v

class ScheduleConfig(BaseModel):
    """Schedule configuration for automated emails"""
    enabled: bool = Field(False, description="Whether scheduling is enabled")
    frequency: ScheduleFrequency = Field(ScheduleFrequency.DAILY, description="Schedule frequency")
    time_of_day: str = Field("09:00", description="Time of day in HH:MM format")
    timezone: str = Field("UTC", description="Timezone for scheduling")
    preset_name: Optional[str] = Field(None, description="Preset to use for automated runs")

    @field_validator('time_of_day')
    @classmethod
    def validate_time_format(cls, v):
        """Validate time format HH:MM"""
        try:
            hour, minute = map(int, v.split(':'))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("Invalid time range")
            return f"{hour:02d}:{minute:02d}"
        except (ValueError, AttributeError):
            raise ValueError("Time must be in HH:MM format")

class EmailConfig(BaseModel):
    """Complete email configuration"""
    smtp: SMTPConfig
    sender_email: EmailStr = Field(..., description="Sender email address")
    sender_name: str = Field("InvenTree Order Calculator", description="Sender display name")
    recipients: EmailRecipients
    subject_template: str = Field(
        "InvenTree Order Report - {{date}}",
        description="Email subject template"
    )
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    
    # Email content settings
    include_parts_table: bool = Field(True, description="Include parts to order table")
    include_assemblies_table: bool = Field(True, description="Include assemblies to build table")
    include_summary: bool = Field(True, description="Include summary statistics")

class EmailConfigManager:
    """Manager for email configuration persistence"""
    
    def __init__(self, config_file: Path = Path("email_config.json")):
        self.config_file = config_file
        self._config: Optional[EmailConfig] = None

    def load_config(self) -> Optional[EmailConfig]:
        """Load email configuration from file"""
        if not self.config_file.exists():
            logger.info(f"Email config file not found at {self.config_file}")
            return None
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._config = EmailConfig(**data)
            logger.info(f"Email configuration loaded from {self.config_file}")
            return self._config
        
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error loading email config from {self.config_file}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error loading email config: {e}")
            return None

    def save_config(self, config: EmailConfig) -> bool:
        """Save email configuration to file"""
        try:
            # Ensure parent directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to dict and save
            config_dict = config.model_dump()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, default=str)
            
            self._config = config
            logger.info(f"Email configuration saved to {self.config_file}")
            return True
        
        except Exception as e:
            logger.error(f"Error saving email config to {self.config_file}: {e}")
            return False

    def get_config(self) -> Optional[EmailConfig]:
        """Get current configuration, loading if necessary"""
        if self._config is None:
            self._config = self.load_config()
        return self._config

    def is_configured(self) -> bool:
        """Check if email is properly configured"""
        config = self.get_config()
        if config is None:
            return False
        
        # Basic validation - check if required fields are present
        try:
            return (
                bool(config.smtp.host) and
                bool(config.smtp.username) and
                bool(config.smtp.password) and
                bool(config.sender_email) and
                len(config.recipients.to) > 0
            )
        except Exception:
            return False

    def validate_config(self, config: EmailConfig) -> List[str]:
        """Validate email configuration and return list of errors"""
        errors = []
        
        try:
            # Validate SMTP settings
            if not config.smtp.host.strip():
                errors.append("SMTP host is required")
            
            if not config.smtp.username.strip():
                errors.append("SMTP username is required")
            
            if not config.smtp.password.strip():
                errors.append("SMTP password is required")
            
            # Validate sender
            if not config.sender_email:
                errors.append("Sender email is required")
            
            # Validate recipients
            if not config.recipients.to:
                errors.append("At least one recipient email is required")
            
            # Validate schedule if enabled
            if config.schedule.enabled:
                if not config.schedule.preset_name or not config.schedule.preset_name.strip():
                    errors.append("Preset name is required when scheduling is enabled")
        
        except Exception as e:
            errors.append(f"Configuration validation error: {e}")
        
        return errors

# Default email configuration file path
DEFAULT_EMAIL_CONFIG_PATH = Path("email_config.json")

# Global email config manager instance
email_config_manager = EmailConfigManager(DEFAULT_EMAIL_CONFIG_PATH)
