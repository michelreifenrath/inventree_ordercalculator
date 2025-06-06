# Tests for email scheduling functionality

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, time
import pytz

from src.inventree_order_calculator.email_scheduler import EmailScheduler, EmailSchedulerManager
from src.inventree_order_calculator.models import OutputTables, CalculatedPart, InputPart
from src.inventree_order_calculator.email_config import (
    EmailConfig, SMTPConfig, EmailRecipients, ScheduleConfig,
    ScheduleFrequency, EmailSecurityType
)
from src.inventree_order_calculator.presets_manager import Preset, PresetItem, PresetsFile

class TestEmailScheduler:
    """Test email scheduler functionality"""
    
    @pytest.fixture
    def sample_config(self):
        """Create sample email configuration with scheduling"""
        smtp = SMTPConfig(
            host="smtp.test.com",
            port=587,
            username="test@test.com",
            password="testpass",
            security=EmailSecurityType.TLS
        )
        
        recipients = EmailRecipients(
            to=["recipient@test.com"]
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
            recipients=recipients,
            schedule=schedule
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
    def calculation_callback(self, sample_results):
        """Create mock calculation callback"""
        def callback(preset_name):
            return sample_results
        return callback
    
    @pytest.fixture
    def email_scheduler(self, calculation_callback):
        """Create email scheduler instance"""
        return EmailScheduler(calculation_callback)
    
    def test_scheduler_initialization(self, email_scheduler):
        """Test scheduler initialization"""
        assert email_scheduler.calculation_callback is not None
        assert email_scheduler.scheduler is not None
        assert not email_scheduler.scheduler.running
    
    def test_start_scheduler(self, email_scheduler):
        """Test starting the scheduler"""
        result = email_scheduler.start()
        assert result is True
        assert email_scheduler.scheduler.running
        
        # Stop for cleanup
        email_scheduler.stop()
    
    def test_stop_scheduler(self, email_scheduler):
        """Test stopping the scheduler"""
        # Start first
        email_scheduler.start()
        assert email_scheduler.scheduler.running
        
        # Stop
        result = email_scheduler.stop()
        assert result is True
        assert not email_scheduler.scheduler.running
    
    def test_schedule_email_daily(self, email_scheduler, sample_config):
        """Test scheduling daily email"""
        email_scheduler.start()
        
        result = email_scheduler.schedule_email(sample_config)
        assert result is True
        assert email_scheduler.is_scheduled()
        
        # Check job details
        job_info = email_scheduler.get_schedule_info()
        assert job_info is not None
        assert "test_preset" in job_info['name']
        
        email_scheduler.stop()
    
    def test_schedule_email_weekly(self, email_scheduler, sample_config):
        """Test scheduling weekly email"""
        sample_config.schedule.frequency = ScheduleFrequency.WEEKLY
        
        email_scheduler.start()
        result = email_scheduler.schedule_email(sample_config)
        assert result is True
        assert email_scheduler.is_scheduled()
        
        email_scheduler.stop()
    
    def test_schedule_email_monthly(self, email_scheduler, sample_config):
        """Test scheduling monthly email"""
        sample_config.schedule.frequency = ScheduleFrequency.MONTHLY
        
        email_scheduler.start()
        result = email_scheduler.schedule_email(sample_config)
        assert result is True
        assert email_scheduler.is_scheduled()
        
        email_scheduler.stop()
    
    def test_schedule_email_disabled(self, email_scheduler, sample_config):
        """Test scheduling when disabled"""
        sample_config.schedule.enabled = False
        
        email_scheduler.start()
        result = email_scheduler.schedule_email(sample_config)
        assert result is True
        assert not email_scheduler.is_scheduled()
        
        email_scheduler.stop()
    
    def test_schedule_email_no_preset(self, email_scheduler, sample_config):
        """Test scheduling without preset name"""
        sample_config.schedule.preset_name = None
        
        email_scheduler.start()
        result = email_scheduler.schedule_email(sample_config)
        assert result is False
        assert not email_scheduler.is_scheduled()
        
        email_scheduler.stop()
    
    def test_unschedule_email(self, email_scheduler, sample_config):
        """Test unscheduling email"""
        email_scheduler.start()
        
        # Schedule first
        email_scheduler.schedule_email(sample_config)
        assert email_scheduler.is_scheduled()
        
        # Unschedule
        result = email_scheduler.unschedule_email()
        assert result is True
        assert not email_scheduler.is_scheduled()
        
        email_scheduler.stop()
    
    def test_get_next_run_time(self, email_scheduler, sample_config):
        """Test getting next run time"""
        email_scheduler.start()
        
        # No schedule initially
        next_run = email_scheduler.get_next_run_time()
        assert next_run is None
        
        # Schedule email
        email_scheduler.schedule_email(sample_config)
        next_run = email_scheduler.get_next_run_time()
        assert next_run is not None
        assert isinstance(next_run, datetime)
        
        email_scheduler.stop()
    
    def test_create_trigger_daily(self, email_scheduler):
        """Test creating daily trigger"""
        trigger = email_scheduler._create_trigger(
            ScheduleFrequency.DAILY, 9, 30, pytz.UTC
        )

        # Just verify trigger is created successfully
        assert trigger is not None
        assert str(trigger).find('9') != -1  # Hour should be in string representation
        assert str(trigger).find('30') != -1  # Minute should be in string representation
    
    def test_create_trigger_weekly(self, email_scheduler):
        """Test creating weekly trigger"""
        trigger = email_scheduler._create_trigger(
            ScheduleFrequency.WEEKLY, 9, 30, pytz.UTC
        )

        # Just verify trigger is created successfully
        assert trigger is not None
        assert str(trigger).find('9') != -1  # Hour should be in string representation
        assert str(trigger).find('30') != -1  # Minute should be in string representation
        assert str(trigger).find('mon') != -1  # Monday should be in string representation
    
    def test_create_trigger_monthly(self, email_scheduler):
        """Test creating monthly trigger"""
        trigger = email_scheduler._create_trigger(
            ScheduleFrequency.MONTHLY, 9, 30, pytz.UTC
        )

        # Just verify trigger is created successfully
        assert trigger is not None
        assert str(trigger).find('9') != -1  # Hour should be in string representation
        assert str(trigger).find('30') != -1  # Minute should be in string representation
    
    def test_create_trigger_invalid_frequency(self, email_scheduler):
        """Test creating trigger with invalid frequency"""
        with pytest.raises(ValueError):
            email_scheduler._create_trigger(
                "invalid", 9, 30, pytz.UTC
            )
    
    @patch('src.inventree_order_calculator.email_scheduler.EmailSender')
    def test_execute_scheduled_email_success(self, mock_email_sender, email_scheduler, sample_config, sample_results):
        """Test successful execution of scheduled email"""
        # Mock email sender
        mock_sender_instance = Mock()
        mock_sender_instance.send_report.return_value = True
        mock_email_sender.return_value = mock_sender_instance
        
        # Execute scheduled email
        email_scheduler._execute_scheduled_email(sample_config)
        
        # Verify email sender was called
        mock_email_sender.assert_called_once_with(sample_config)
        mock_sender_instance.send_report.assert_called_once_with(
            results=sample_results,
            preset_name="test_preset",
            test_mode=False
        )
    
    @patch('src.inventree_order_calculator.email_scheduler.EmailSender')
    def test_execute_scheduled_email_failure(self, mock_email_sender, email_scheduler, sample_config):
        """Test execution of scheduled email with failure"""
        # Mock email sender to return False
        mock_sender_instance = Mock()
        mock_sender_instance.send_report.return_value = False
        mock_email_sender.return_value = mock_sender_instance
        
        # Execute scheduled email (should not raise exception)
        email_scheduler._execute_scheduled_email(sample_config)
        
        # Verify email sender was called
        mock_email_sender.assert_called_once_with(sample_config)

class TestEmailSchedulerManager:
    """Test email scheduler manager functionality"""
    
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
    
    @pytest.fixture
    def mock_api_client(self):
        """Create mock API client"""
        return Mock()
    
    @pytest.fixture
    def scheduler_manager(self, mock_api_client, sample_presets_data):
        """Create scheduler manager instance"""
        return EmailSchedulerManager(mock_api_client, sample_presets_data)
    
    def test_scheduler_manager_initialization(self, scheduler_manager):
        """Test scheduler manager initialization"""
        assert scheduler_manager.api_client is not None
        assert scheduler_manager.presets_data is not None
        assert scheduler_manager.scheduler is not None
    
    def test_start_stop_scheduler(self, scheduler_manager):
        """Test starting and stopping scheduler"""
        # Start
        result = scheduler_manager.start_scheduler()
        assert result is True
        
        status = scheduler_manager.get_status()
        assert status['running'] is True
        
        # Stop
        result = scheduler_manager.stop_scheduler()
        assert result is True
        
        status = scheduler_manager.get_status()
        assert status['running'] is False
    
    def test_calculate_from_preset_success(self, scheduler_manager, sample_presets_data):
        """Test successful calculation from preset"""
        with patch('src.inventree_order_calculator.calculator.OrderCalculator') as mock_calculator_class:
            # Mock calculator
            mock_calculator = Mock()
            mock_results = OutputTables(parts_to_order=[], subassemblies_to_build=[], warnings=[])
            mock_calculator.calculate_orders.return_value = mock_results
            mock_calculator_class.return_value = mock_calculator

            # Calculate from preset
            results = scheduler_manager._calculate_from_preset("test_preset")

            # Verify results
            assert results == mock_results
            mock_calculator_class.assert_called_once_with(scheduler_manager.api_client)
            mock_calculator.calculate_orders.assert_called_once()

            # Verify input parts
            call_args = mock_calculator.calculate_orders.call_args[0][0]
            assert len(call_args) == 2  # Two preset items
            assert all(isinstance(part, InputPart) for part in call_args)
    
    def test_calculate_from_preset_not_found(self, scheduler_manager):
        """Test calculation from non-existent preset"""
        results = scheduler_manager._calculate_from_preset("nonexistent_preset")
        assert results is None
    
    def test_calculate_from_preset_error(self, scheduler_manager):
        """Test calculation from preset with error"""
        with patch('src.inventree_order_calculator.calculator.OrderCalculator') as mock_calculator_class:
            # Mock calculator to raise exception
            mock_calculator_class.side_effect = Exception("Calculation error")

            results = scheduler_manager._calculate_from_preset("test_preset")
            assert results is None
    
    def test_get_status(self, scheduler_manager):
        """Test getting scheduler status"""
        status = scheduler_manager.get_status()
        
        assert 'running' in status
        assert 'scheduled' in status
        assert 'next_run' in status
        assert 'schedule_info' in status
        
        assert isinstance(status['running'], bool)
        assert isinstance(status['scheduled'], bool)
