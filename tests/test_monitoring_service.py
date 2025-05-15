import pytest
import asyncio
from unittest.mock import MagicMock, patch, ANY
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.base import JobLookupError

# Assuming MonitoringTaskConfig and other necessary models will be defined
# For now, create placeholder or mock them as needed.
from inventree_order_calculator.monitoring_service import (
    Scheduler, 
    # TaskExecutor, # Will test later
    # MonitoringTaskManager, # Will test later
    # MonitoringTaskConfig # Placeholder if not yet defined
)
from inventree_order_calculator.presets_manager import MonitoringList # For task config type hint

# Placeholder for MonitoringTaskConfig if not yet fully defined or to simplify tests
class MockMonitoringTaskConfig(MonitoringList):
    id: str = "task_123"
    name: str = "Test Task"
    cron_string: str = "0 0 * * *" # Default cron: daily at midnight
    # Add other fields as necessary for Scheduler interaction, e.g. timezone
    timezone: str = "UTC"

    # Make it behave like a dict for attribute access if needed by scheduler
    def __getitem__(self, key):
        return getattr(self, key)

@pytest.fixture
def mock_apscheduler():
    """Fixture for a mocked AsyncIOScheduler instance."""
    with patch('apscheduler.schedulers.asyncio.AsyncIOScheduler', autospec=True) as mock_scheduler_class:
        mock_instance = mock_scheduler_class.return_value
        mock_instance.add_job = MagicMock()
        mock_instance.remove_job = MagicMock()
        mock_instance.start = MagicMock()
        mock_instance.shutdown = MagicMock()
        mock_instance.get_job = MagicMock()
        yield mock_instance

@pytest.fixture
def scheduler_service(mock_apscheduler):
    """Fixture for the Scheduler service using the mocked APScheduler."""
    # Pass the mocked instance, not the class
    return Scheduler(apscheduler_instance=mock_apscheduler)

# TDD Anchor: Test adding a job to the scheduler
def test_scheduler_add_job(scheduler_service, mock_apscheduler):
    """Test that add_job correctly calls apscheduler.add_job."""
    mock_task_executor_run = MagicMock()
    task_config = MockMonitoringTaskConfig(id="job1", cron_string="* * * * *")

    scheduler_service.add_job(task_config, mock_task_executor_run)

    mock_apscheduler.add_job.assert_called_once_with(
        mock_task_executor_run,
        trigger=ANY, # CronTrigger is complex to match exactly here, check type below
        id="job1",
        name="Test Task", # from MockMonitoringTaskConfig
        replace_existing=True,
        misfire_grace_time=300 # Default from Scheduler class
    )
    # Check that the trigger is a CronTrigger
    call_args = mock_apscheduler.add_job.call_args
    assert isinstance(call_args[1]['trigger'], CronTrigger)
    assert call_args[1]['trigger'].fields_str == task_config.cron_string.split()


# TDD Anchor: Test removing a job
def test_scheduler_remove_job(scheduler_service, mock_apscheduler):
    """Test that remove_job correctly calls apscheduler.remove_job."""
    job_id = "job_to_remove"
    scheduler_service.remove_job(job_id)
    mock_apscheduler.remove_job.assert_called_once_with(job_id)

# TDD Anchor: Test removing a non-existent job
def test_scheduler_remove_non_existent_job(scheduler_service, mock_apscheduler):
    """Test handling of removing a job that doesn't exist."""
    job_id = "non_existent_job"
    mock_apscheduler.remove_job.side_effect = JobLookupError(job_id)
    
    # Expect remove_job to handle JobLookupError gracefully (e.g., log and not raise)
    try:
        scheduler_service.remove_job(job_id)
    except JobLookupError:
        pytest.fail("Scheduler.remove_job should handle JobLookupError gracefully.")
    
    mock_apscheduler.remove_job.assert_called_once_with(job_id)
    # Add assertion for logging if implemented, e.g. mock_logger.warning.assert_called_once()

# TDD Anchor: Test starting the scheduler
def test_scheduler_start(scheduler_service, mock_apscheduler):
    """Test that start correctly calls apscheduler.start."""
    scheduler_service.start()
    mock_apscheduler.start.assert_called_once()

# TDD Anchor: Test stopping the scheduler
def test_scheduler_stop(scheduler_service, mock_apscheduler):
    """Test that stop correctly calls apscheduler.shutdown."""
    scheduler_service.stop()
    mock_apscheduler.shutdown.assert_called_once_with(wait=True) # Default wait=True

# TDD Anchor: Test scheduler initializes with a real APScheduler if none provided
def test_scheduler_initializes_real_apscheduler_if_none_provided():
    """Test that Scheduler creates its own AsyncIOScheduler instance if not given one."""
    with patch('apscheduler.schedulers.asyncio.AsyncIOScheduler', autospec=True) as mock_real_scheduler_class:
        # Prevent the actual scheduler from starting during test
        mock_real_scheduler_class.return_value.start = MagicMock() 
        
        scheduler_instance = Scheduler() # No apscheduler_instance provided
        assert scheduler_instance.scheduler is not None
        assert isinstance(scheduler_instance.scheduler, AsyncIOScheduler)
        mock_real_scheduler_class.assert_called_once()
        # Check if default jobstore 'default' was added as per APScheduler's default behavior
        # This might be too implementation-specific for APScheduler's internals
        # scheduler_instance.scheduler.add_jobstore.assert_called_with('memory', alias='default')

# TDD Anchor: Test job execution (conceptual, relies on APScheduler working)
# This test is more about ensuring the callback is set up correctly.
# A more robust test would involve a real (but controlled) AsyncIOScheduler
# and a callback that sets a flag or appends to a list.
@pytest.mark.asyncio
async def test_scheduler_job_actually_runs_callback(event_loop):
    """
    Test that a job added to a real (but controlled) scheduler runs the callback.
    This is a more complex test and might be closer to an integration test for the Scheduler.
    """
    real_scheduler = AsyncIOScheduler(event_loop=event_loop)
    scheduler_service_real = Scheduler(apscheduler_instance=real_scheduler)
    
    callback_executed = asyncio.Event()
    
    async def mock_job_function():
        nonlocal callback_executed
        print(f"Mock job function called at {datetime.now()}")
        callback_executed.set()

    # Schedule a job to run very soon
    task_config = MockMonitoringTaskConfig(
        id="quick_job", 
        cron_string="* * * * * */1"  # Every second for testing
    ) 
    
    scheduler_service_real.add_job(task_config, mock_job_function)
    scheduler_service_real.start()
    
    try:
        # Wait for the callback to be executed, with a timeout
        await asyncio.wait_for(callback_executed.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        pytest.fail("Scheduled job did not run the callback within the timeout.")
    finally:
        scheduler_service_real.stop()

    assert callback_executed.is_set()

# TDD Anchor: Test adding a job with a specific timezone
def test_scheduler_add_job_with_timezone(scheduler_service, mock_apscheduler):
    """Test adding a job with a specific timezone from task_config."""
    mock_task_executor_run = MagicMock()
    task_config = MockMonitoringTaskConfig(
        id="job_tz", 
        cron_string="0 10 * * *", 
        timezone="America/New_York"
    )

    scheduler_service.add_job(task_config, mock_task_executor_run)

    mock_apscheduler.add_job.assert_called_once()
    call_args = mock_apscheduler.add_job.call_args
    trigger = call_args[1]['trigger']
    assert isinstance(trigger, CronTrigger)
    assert str(trigger.timezone) == "America/New_York"

# TDD Anchor: Test default misfire_grace_time
def test_scheduler_add_job_default_misfire_grace_time(scheduler_service, mock_apscheduler):
    """Test that add_job uses the default misfire_grace_time."""
    mock_task_executor_run = MagicMock()
    task_config = MockMonitoringTaskConfig(id="job_misfire", cron_string="* * * * *")
    
    # Scheduler class has default MISFIRE_GRACE_TIME = 300
    scheduler_service.add_job(task_config, mock_task_executor_run)
    
    mock_apscheduler.add_job.assert_called_once_with(
        mock_task_executor_run,
        trigger=ANY,
        id="job_misfire",
        name=task_config.name,
        replace_existing=True,
        misfire_grace_time=300 # Check default
    )

# TDD Anchor: Test overriding misfire_grace_time
def test_scheduler_add_job_override_misfire_grace_time(scheduler_service, mock_apscheduler):
    """Test that add_job allows overriding misfire_grace_time."""
    mock_task_executor_run = MagicMock()
    task_config = MockMonitoringTaskConfig(id="job_misfire_override", cron_string="* * * * *")
    custom_misfire_time = 600
    
    scheduler_service.add_job(task_config, mock_task_executor_run, misfire_grace_time=custom_misfire_time)
    
    mock_apscheduler.add_job.assert_called_once_with(
        mock_task_executor_run,
        trigger=ANY,
        id="job_misfire_override",
        name=task_config.name,
        replace_existing=True,
        misfire_grace_time=custom_misfire_time # Check override
    )

# TDD Anchor: Test get_job method
def test_scheduler_get_job(scheduler_service, mock_apscheduler):
    """Test that get_job correctly calls apscheduler.get_job."""
    job_id = "job_to_get"
    mock_job_object = MagicMock()
    mock_apscheduler.get_job.return_value = mock_job_object

    returned_job = scheduler_service.get_job(job_id)

    mock_apscheduler.get_job.assert_called_once_with(job_id)
    assert returned_job == mock_job_object

# TDD Anchor: Test get_job for non-existent job
def test_scheduler_get_job_non_existent(scheduler_service, mock_apscheduler):
    """Test get_job returns None for a non-existent job_id."""
    job_id = "non_existent_job_get"
    mock_apscheduler.get_job.return_value = None # APScheduler's get_job returns None if not found

    returned_job = scheduler_service.get_job(job_id)

    mock_apscheduler.get_job.assert_called_once_with(job_id)
    assert returned_job is None
# Placeholder for TaskExecutor and related imports, will be refined
from inventree_order_calculator.monitoring_service import TaskExecutor
from inventree_order_calculator.models import CalculationResult, PartSummaryLine, OrderSummary
from inventree_order_calculator.config import Config as AppConfig # Use the main Config for tests
from inventree_order_calculator.api_client import APIUnreachableError # If used by TaskExecutor
from inventree_order_calculator.monitoring_service import NonRetryableCalculationError # If used

# --- Tests for TaskExecutor ---

@pytest.fixture
def mock_task_config_for_executor():
    """Provides a mock MonitoringList task configuration for TaskExecutor tests."""
    return MockMonitoringTaskConfig( # Using the existing mock for now
        id="exec_task_1",
        name="Executor Test Task",
        cron_string="0 0 * * *", # Not directly used by TaskExecutor methods but part of the model
        parts=[ # Example parts data
            {"part_name": "PART1", "quantity": 10},
            {"part_name": "PART2", "quantity": 5},
        ],
        recipients=["test@example.com"],
        notify_condition="on_change",
        last_hash="initial_hash",
        active=True,
        timezone="UTC"
    )

@pytest.fixture
def mock_app_config():
    """Provides a mock application Config for TaskExecutor tests."""
    # Using a simplified dictionary for patching os.environ effectively
    # The actual Config.load() will pick these up.
    # Ensure all fields required by TaskExecutor._perform_calculation_with_retry are present.
    return AppConfig(
        INVENTREE_API_URL="http://fake-inventree.com",
        INVENTREE_API_TOKEN="fake_token",
        API_MAX_RETRIES=2, # For retry tests
        API_RETRY_DELAY=1,  # seconds, keep low for tests
        API_TIMEOUT=10,
        GLOBAL_EMAIL_NOTIFICATIONS_ENABLED=True,
        ADMIN_EMAIL_RECIPIENTS=["admin@example.com"],
        # Add other fields if TaskExecutor or its dependencies require them
        EMAIL_SENDER_ADDRESS="notify@example.com", # Needed for email_service calls
        EMAIL_SMTP_SERVER="smtp.example.com" # Needed for email_service calls
    )

@pytest.fixture
def mock_order_calculator_instance():
    """Mocks the OrderCalculator instance."""
    mock_calc = MagicMock()
    mock_calc.calculate_bom_cost_and_availability = MagicMock()
    return mock_calc

# --- Tests for TaskExecutor._perform_calculation_with_retry ---

@patch('inventree_order_calculator.monitoring_service._get_order_calculator')
@patch('time.sleep', MagicMock()) # Mock time.sleep to speed up retry tests
def test_perform_calculation_success_first_try(
    mock_get_calc, mock_app_config, mock_task_config_for_executor
):
    """Test _perform_calculation_with_retry succeeds on the first attempt."""
    mock_calculator = mock_get_calc.return_value
    expected_result = CalculationResult(
        summary=OrderSummary(total_parts_requested=2, total_parts_available=2, total_missing_parts=0, overall_availability_percentage=100.0),
        detailed_bom=[], # Simplified for this test
        warnings_or_errors=[]
    )
    mock_calculator.calculate_bom_cost_and_availability.return_value = expected_result

    result = TaskExecutor._perform_calculation_with_retry(
        mock_task_config_for_executor.parts, mock_app_config
    )

    mock_calculator.calculate_bom_cost_and_availability.assert_called_once()
    assert result == expected_result
    assert not getattr(result, 'has_critical_error', False)

@patch('inventree_order_calculator.monitoring_service._get_order_calculator')
@patch('time.sleep', MagicMock())
def test_perform_calculation_success_on_retry(
    mock_get_calc, mock_app_config, mock_task_config_for_executor
):
    """Test _perform_calculation_with_retry succeeds after one retry."""
    mock_calculator = mock_get_calc.return_value
    expected_result = CalculationResult(summary=OrderSummary(total_parts_requested=2, total_parts_available=2, total_missing_parts=0, overall_availability_percentage=100.0), detailed_bom=[])
    
    # Fail first, then succeed
    mock_calculator.calculate_bom_cost_and_availability.side_effect = [
        APIUnreachableError("Simulated API down"),
        expected_result
    ]
    # mock_app_config.API_MAX_RETRIES = 1 # Ensure it retries at least once

    result = TaskExecutor._perform_calculation_with_retry(
        mock_task_config_for_executor.parts, mock_app_config
    )

    assert mock_calculator.calculate_bom_cost_and_availability.call_count == 2
    assert result == expected_result
    assert not getattr(result, 'has_critical_error', False)
    assert time.sleep.call_count == 1 # Called once before the successful retry

@patch('inventree_order_calculator.monitoring_service._get_order_calculator')
@patch('time.sleep', MagicMock())
def test_perform_calculation_failure_after_all_retries(
    mock_get_calc, mock_app_config, mock_task_config_for_executor
):
    """Test _perform_calculation_with_retry fails after all retries."""
    mock_calculator = mock_get_calc.return_value
    mock_app_config.API_MAX_RETRIES = 1 # e.g., 1 retry means 2 attempts total
    
    mock_calculator.calculate_bom_cost_and_availability.side_effect = APIUnreachableError("Consistently down")

    result = TaskExecutor._perform_calculation_with_retry(
        mock_task_config_for_executor.parts, mock_app_config
    )

    assert mock_calculator.calculate_bom_cost_and_availability.call_count == mock_app_config.API_MAX_RETRIES + 1
    assert getattr(result, 'has_critical_error', False) is True
    assert "API unreachable after" in result.summary.get("error", "")
    assert time.sleep.call_count == mock_app_config.API_MAX_RETRIES

@patch('inventree_order_calculator.monitoring_service._get_order_calculator')
@patch('time.sleep', MagicMock())
def test_perform_calculation_non_retryable_error(
    mock_get_calc, mock_app_config, mock_task_config_for_executor
):
    """Test _perform_calculation_with_retry handles NonRetryableCalculationError immediately."""
    mock_calculator = mock_get_calc.return_value
    error_message = "This is a non-retryable error"
    mock_calculator.calculate_bom_cost_and_availability.side_effect = NonRetryableCalculationError(error_message)

    result = TaskExecutor._perform_calculation_with_retry(
        mock_task_config_for_executor.parts, mock_app_config
    )

    mock_calculator.calculate_bom_cost_and_availability.assert_called_once() # Should not retry
    assert getattr(result, 'has_critical_error', False) is True
    assert error_message in result.summary.get("error", "")
    assert time.sleep.call_count == 0 # No retries, so no sleep

# --- Tests for TaskExecutor._generate_significant_result_hash ---

def test_generate_hash_consistent_for_same_data():
    """Test _generate_significant_result_hash is consistent."""
    res1_details = [
        PartSummaryLine(part_id="P1", name="Part 1", quantity_required=5, quantity_available=2, quantity_missing=3),
        PartSummaryLine(part_id="P2", name="Part 2", quantity_required=10, quantity_available=10, quantity_missing=0)
    ]
    calc_result1 = CalculationResult(summary=OrderSummary(), detailed_bom=res1_details)
    
    res2_details = [ # Same data, different order initially
        PartSummaryLine(part_id="P2", name="Part 2", quantity_required=10, quantity_available=10, quantity_missing=0),
        PartSummaryLine(part_id="P1", name="Part 1", quantity_required=5, quantity_available=2, quantity_missing=3)
    ]
    calc_result2 = CalculationResult(summary=OrderSummary(), detailed_bom=res2_details)

    hash1 = TaskExecutor._generate_significant_result_hash(calc_result1)
    hash2 = TaskExecutor._generate_significant_result_hash(calc_result2)
    assert hash1 == hash2

def test_generate_hash_different_for_different_missing_parts():
    """Test _generate_significant_result_hash changes if missing parts change."""
    res1_details = [
        PartSummaryLine(part_id="P1", name="Part 1", quantity_required=5, quantity_available=2, quantity_missing=3)
    ]
    calc_result1 = CalculationResult(summary=OrderSummary(), detailed_bom=res1_details)
    
    res2_details = [
        PartSummaryLine(part_id="P1", name="Part 1", quantity_required=5, quantity_available=1, quantity_missing=4) # Missing qty changed
    ]
    calc_result2 = CalculationResult(summary=OrderSummary(), detailed_bom=res2_details)

    hash1 = TaskExecutor._generate_significant_result_hash(calc_result1)
    hash2 = TaskExecutor._generate_significant_result_hash(calc_result2)
    assert hash1 != hash2

def test_generate_hash_ignores_non_missing_parts_changes():
    """Test _generate_significant_result_hash ignores changes in available parts if not missing."""
    res1_details = [
        PartSummaryLine(part_id="P1", name="Part 1", quantity_required=5, quantity_available=5, quantity_missing=0),
        PartSummaryLine(part_id="P2", name="Part 2", quantity_required=10, quantity_available=10, quantity_missing=0)
    ]
    calc_result1 = CalculationResult(summary=OrderSummary(), detailed_bom=res1_details)
    
    res2_details = [ 
        PartSummaryLine(part_id="P1", name="Part 1", quantity_required=5, quantity_available=6, quantity_missing=0), # Available changed, still not missing
        PartSummaryLine(part_id="P2", name="Part 2", quantity_required=10, quantity_available=10, quantity_missing=0)
    ]
    calc_result2 = CalculationResult(summary=OrderSummary(), detailed_bom=res2_details)

    hash1 = TaskExecutor._generate_significant_result_hash(calc_result1)
    hash2 = TaskExecutor._generate_significant_result_hash(calc_result2)
    assert hash1 == hash2 # Hash should only consider missing parts based on current implementation

def test_generate_hash_empty_bom():
    """Test _generate_significant_result_hash with an empty BOM."""
    calc_result_empty = CalculationResult(summary=OrderSummary(), detailed_bom=[])
    hash_empty = TaskExecutor._generate_significant_result_hash(calc_result_empty)
    assert isinstance(hash_empty, str)
    assert len(hash_empty) == 32 # MD5 hash length

    # Hash of another empty result should be the same
    calc_result_empty2 = CalculationResult(summary=OrderSummary(), detailed_bom=[])
    hash_empty2 = TaskExecutor._generate_significant_result_hash(calc_result_empty2)
    assert hash_empty == hash_empty2

# More tests for run_monitoring_task will be added subsequently.
# --- Tests for TaskExecutor.run_monitoring_task ---

@patch('inventree_order_calculator.monitoring_service.TaskExecutor._perform_calculation_with_retry')
@patch('inventree_order_calculator.monitoring_service.MonitoringTaskManager.get_task_by_id')
@patch('inventree_order_calculator.monitoring_service._get_config')
@patch('inventree_order_calculator.email_service.send_email_with_retry') # Mock the actual email sending
@patch('inventree_order_calculator.email_service.send_admin_notification')
@patch('inventree_order_calculator.monitoring_service.MonitoringTaskManager.update_task_last_hash')
def test_run_monitoring_task_inactive_task(
    mock_update_hash, mock_send_admin, mock_send_email, mock_get_cfg, mock_get_task, mock_perform_calc,
    mock_app_config, mock_task_config_for_executor # Fixtures
):
    """Test run_monitoring_task skips inactive tasks."""
    inactive_task_config = mock_task_config_for_executor.model_copy(update={"active": False})
    mock_get_task.return_value = inactive_task_config
    mock_get_cfg.return_value = mock_app_config

    TaskExecutor.run_monitoring_task("exec_task_1")

    mock_get_task.assert_called_once_with("exec_task_1")
    mock_perform_calc.assert_not_called()
    mock_send_email.assert_not_called()
    mock_send_admin.assert_not_called()
    mock_update_hash.assert_not_called()

@patch('inventree_order_calculator.monitoring_service.TaskExecutor._perform_calculation_with_retry')
@patch('inventree_order_calculator.monitoring_service.MonitoringTaskManager.get_task_by_id')
@patch('inventree_order_calculator.monitoring_service._get_config')
@patch('inventree_order_calculator.email_service.send_email_with_retry')
@patch('inventree_order_calculator.email_service.send_admin_notification')
@patch('inventree_order_calculator.monitoring_service.MonitoringTaskManager.update_task_last_hash')
def test_run_monitoring_task_task_not_found(
    mock_update_hash, mock_send_admin, mock_send_email, mock_get_cfg, mock_get_task, mock_perform_calc,
    mock_app_config
):
    """Test run_monitoring_task skips if task is not found."""
    mock_get_task.return_value = None
    mock_get_cfg.return_value = mock_app_config

    TaskExecutor.run_monitoring_task("non_existent_task")

    mock_get_task.assert_called_once_with("non_existent_task")
    mock_perform_calc.assert_not_called()
    mock_send_email.assert_not_called()

@patch('inventree_order_calculator.monitoring_service.TaskExecutor._perform_calculation_with_retry')
@patch('inventree_order_calculator.monitoring_service.MonitoringTaskManager.get_task_by_id')
@patch('inventree_order_calculator.monitoring_service._get_config')
@patch('inventree_order_calculator.email_service.send_email_with_retry')
@patch('inventree_order_calculator.email_service.send_admin_notification')
@patch('inventree_order_calculator.monitoring_service.MonitoringTaskManager.update_task_last_hash')
def test_run_monitoring_task_global_email_disabled(
    mock_update_hash, mock_send_admin, mock_send_email, mock_get_cfg, mock_get_task, mock_perform_calc,
    mock_app_config, mock_task_config_for_executor
):
    """Test run_monitoring_task skips email if global notifications are disabled."""
    disabled_email_config = mock_app_config.model_copy(update={"GLOBAL_EMAIL_NOTIFICATIONS_ENABLED": False})
    mock_get_cfg.return_value = disabled_email_config
    mock_get_task.return_value = mock_task_config_for_executor
    
    # Mock calculation result (doesn't matter much as email is disabled)
    mock_calc_result = CalculationResult(summary=OrderSummary(), detailed_bom=[])
    mock_perform_calc.return_value = mock_calc_result
    
    TaskExecutor.run_monitoring_task("exec_task_1")

    mock_perform_calc.assert_called_once()
    mock_send_email.assert_not_called()
    mock_send_admin.assert_not_called() # Admin notifications also respect global disable in current TaskExecutor logic
    mock_update_hash.assert_not_called() # Hash update might still happen if notify_condition was 'on_change' and change detected, but email not sent.
                                        # Current TaskExecutor logic updates hash only if email_sent_successfully.

@patch('inventree_order_calculator.monitoring_service.TaskExecutor._perform_calculation_with_retry')
@patch('inventree_order_calculator.monitoring_service.TaskExecutor._generate_significant_result_hash')
@patch('inventree_order_calculator.monitoring_service.MonitoringTaskManager.get_task_by_id')
@patch('inventree_order_calculator.monitoring_service._get_config')
@patch('inventree_order_calculator.email_service.send_email_with_retry')
@patch('inventree_order_calculator.email_service.send_admin_notification')
@patch('inventree_order_calculator.monitoring_service.MonitoringTaskManager.update_task_last_hash')
def test_run_monitoring_task_notify_always(
    mock_update_hash, mock_send_admin, mock_send_email, mock_get_cfg, mock_get_task, mock_gen_hash, mock_perform_calc,
    mock_app_config, mock_task_config_for_executor
):
    """Test 'always' notify condition sends email."""
    always_notify_task = mock_task_config_for_executor.model_copy(update={"notify_condition": "always"})
    mock_get_task.return_value = always_notify_task
    mock_get_cfg.return_value = mock_app_config
    
    mock_calc_result = CalculationResult(summary=OrderSummary(), detailed_bom=[])
    mock_perform_calc.return_value = mock_calc_result
    mock_send_email.return_value = True # Simulate successful email send

    TaskExecutor.run_monitoring_task("exec_task_1")

    mock_perform_calc.assert_called_once()
    mock_gen_hash.assert_not_called() # Hash not needed for 'always'
    mock_send_email.assert_called_once()
    mock_update_hash.assert_not_called() # Hash not updated for 'always'

@patch('inventree_order_calculator.monitoring_service.TaskExecutor._perform_calculation_with_retry')
@patch('inventree_order_calculator.monitoring_service.TaskExecutor._generate_significant_result_hash')
@patch('inventree_order_calculator.monitoring_service.MonitoringTaskManager.get_task_by_id')
@patch('inventree_order_calculator.monitoring_service._get_config')
@patch('inventree_order_calculator.email_service.send_email_with_retry')
@patch('inventree_order_calculator.email_service.send_admin_notification')
@patch('inventree_order_calculator.monitoring_service.MonitoringTaskManager.update_task_last_hash')
def test_run_monitoring_task_notify_on_change_detected(
    mock_update_hash, mock_send_admin, mock_send_email, mock_get_cfg, mock_get_task, mock_gen_hash, mock_perform_calc,
    mock_app_config, mock_task_config_for_executor
):
    """Test 'on_change' sends email and updates hash when change is detected."""
    on_change_task = mock_task_config_for_executor.model_copy(update={
        "notify_condition": "on_change",
        "last_hash": "old_hash"
    })
    mock_get_task.return_value = on_change_task
    mock_get_cfg.return_value = mock_app_config
    
    mock_calc_result = CalculationResult(summary=OrderSummary(), detailed_bom=[]) # Dummy result
    mock_perform_calc.return_value = mock_calc_result
    mock_gen_hash.return_value = "new_hash" # Simulate new hash
    mock_send_email.return_value = True

    TaskExecutor.run_monitoring_task("exec_task_1")

    mock_perform_calc.assert_called_once()
    mock_gen_hash.assert_called_once_with(mock_calc_result)
    mock_send_email.assert_called_once()
    mock_update_hash.assert_called_once_with("exec_task_1", "new_hash")

@patch('inventree_order_calculator.monitoring_service.TaskExecutor._perform_calculation_with_retry')
@patch('inventree_order_calculator.monitoring_service.TaskExecutor._generate_significant_result_hash')
@patch('inventree_order_calculator.monitoring_service.MonitoringTaskManager.get_task_by_id')
@patch('inventree_order_calculator.monitoring_service._get_config')
@patch('inventree_order_calculator.email_service.send_email_with_retry')
@patch('inventree_order_calculator.email_service.send_admin_notification')
@patch('inventree_order_calculator.monitoring_service.MonitoringTaskManager.update_task_last_hash')
def test_run_monitoring_task_notify_on_change_no_change(
    mock_update_hash, mock_send_admin, mock_send_email, mock_get_cfg, mock_get_task, mock_gen_hash, mock_perform_calc,
    mock_app_config, mock_task_config_for_executor
):
    """Test 'on_change' does not send email or update hash if no change."""
    current_hash = "current_identical_hash"
    no_change_task = mock_task_config_for_executor.model_copy(update={
        "notify_condition": "on_change",
        "last_hash": current_hash
    })
    mock_get_task.return_value = no_change_task
    mock_get_cfg.return_value = mock_app_config
    
    mock_calc_result = CalculationResult(summary=OrderSummary(), detailed_bom=[])
    mock_perform_calc.return_value = mock_calc_result
    mock_gen_hash.return_value = current_hash # Simulate same hash

    TaskExecutor.run_monitoring_task("exec_task_1")

    mock_perform_calc.assert_called_once()
    mock_gen_hash.assert_called_once_with(mock_calc_result)
    mock_send_email.assert_not_called()
    mock_update_hash.assert_not_called()

@patch('inventree_order_calculator.monitoring_service.TaskExecutor._perform_calculation_with_retry')
@patch('inventree_order_calculator.monitoring_service.MonitoringTaskManager.get_task_by_id')
@patch('inventree_order_calculator.monitoring_service._get_config')
@patch('inventree_order_calculator.email_service.send_email_with_retry')
@patch('inventree_order_calculator.email_service.send_admin_notification')
@patch('inventree_order_calculator.monitoring_service.MonitoringTaskManager.update_task_last_hash')
def test_run_monitoring_task_critical_error_sends_admin_email(
    mock_update_hash, mock_send_admin, mock_send_email, mock_get_cfg, mock_get_task, mock_perform_calc,
    mock_app_config, mock_task_config_for_executor
):
    """Test critical error during calculation sends admin email."""
    mock_get_task.return_value = mock_task_config_for_executor
    mock_get_cfg.return_value = mock_app_config # Assumes ADMIN_EMAIL_RECIPIENTS is set
    
    error_calc_result = CalculationResult(
        summary=OrderSummary(error="Critical calc error"), 
        detailed_bom=[],
        has_critical_error=True,
        error_message="Detailed critical error message."
    )
    mock_perform_calc.return_value = error_calc_result

    TaskExecutor.run_monitoring_task("exec_task_1")

    mock_perform_calc.assert_called_once()
    mock_send_email.assert_not_called() # Regular email not sent
    mock_send_admin.assert_called_once() # Admin email sent
    # Check some details of admin email
    admin_call_args = mock_send_admin.call_args
    assert admin_call_args[1]['subject'] == f"Monitoring Task Failed: {mock_task_config_for_executor.name}"
    assert "Detailed critical error message." in admin_call_args[1]['text_body_content']
    mock_update_hash.assert_not_called()

@patch('inventree_order_calculator.monitoring_service.TaskExecutor._perform_calculation_with_retry')
@patch('inventree_order_calculator.monitoring_service.TaskExecutor._generate_significant_result_hash')
@patch('inventree_order_calculator.monitoring_service.MonitoringTaskManager.get_task_by_id')
@patch('inventree_order_calculator.monitoring_service._get_config')
@patch('inventree_order_calculator.email_service.send_email_with_retry')
@patch('inventree_order_calculator.email_service.send_admin_notification')
@patch('inventree_order_calculator.monitoring_service.MonitoringTaskManager.update_task_last_hash')
def test_run_monitoring_task_on_change_email_fails_no_hash_update(
    mock_update_hash, mock_send_admin, mock_send_email, mock_get_cfg, mock_get_task, mock_gen_hash, mock_perform_calc,
    mock_app_config, mock_task_config_for_executor
):
    """Test 'on_change', if email send fails, hash is not updated."""
    on_change_task = mock_task_config_for_executor.model_copy(update={
        "notify_condition": "on_change",
        "last_hash": "old_hash"
    })
    mock_get_task.return_value = on_change_task
    mock_get_cfg.return_value = mock_app_config
    
    mock_calc_result = CalculationResult(summary=OrderSummary(), detailed_bom=[])
    mock_perform_calc.return_value = mock_calc_result
    mock_gen_hash.return_value = "new_hash"
    mock_send_email.return_value = False # Simulate failed email send

    TaskExecutor.run_monitoring_task("exec_task_1")

    mock_send_email.assert_called_once()
    mock_update_hash.assert_not_called() # Hash should not be updated if email failed
from inventree_order_calculator.monitoring_service import MonitoringTaskManager
from inventree_order_calculator.presets_manager import PresetsManager # For mocking

# --- Tests for MonitoringTaskManager ---

@pytest.fixture
def mock_presets_manager_instance():
    """Mocks the PresetsManager instance used by MonitoringTaskManager."""
    mock_pm = MagicMock(spec=PresetsManager)
    mock_pm.get_monitoring_lists = MagicMock()
    mock_pm.add_monitoring_list = MagicMock()
    mock_pm.update_monitoring_list = MagicMock()
    mock_pm.delete_monitoring_list = MagicMock()
    return mock_pm

@pytest.fixture
def sample_monitoring_tasks():
    """Provides a list of sample MonitoringList objects for testing."""
    return [
        MockMonitoringTaskConfig(id="task1", name="Task One", active=True, cron_string="0 1 * * *"),
        MockMonitoringTaskConfig(id="task2", name="Task Two", active=False, cron_string="0 2 * * *"),
        MockMonitoringTaskConfig(id="task3", name="Task Three", active=True, cron_string="0 3 * * *"),
    ]

@patch('inventree_order_calculator.monitoring_service._get_presets_manager')
def test_mtm_get_all_monitoring_tasks(mock_get_pm, mock_presets_manager_instance, sample_monitoring_tasks):
    """Test get_all_monitoring_tasks returns all tasks from PresetsManager."""
    mock_get_pm.return_value = mock_presets_manager_instance
    mock_presets_manager_instance.get_monitoring_lists.return_value = sample_monitoring_tasks

    tasks = MonitoringTaskManager.get_all_monitoring_tasks()

    mock_presets_manager_instance.get_monitoring_lists.assert_called_once()
    assert tasks == sample_monitoring_tasks
    assert len(tasks) == 3

@patch('inventree_order_calculator.monitoring_service._get_presets_manager')
def test_mtm_get_all_active_monitoring_tasks(mock_get_pm, mock_presets_manager_instance, sample_monitoring_tasks):
    """Test get_all_active_monitoring_tasks returns only active tasks."""
    mock_get_pm.return_value = mock_presets_manager_instance
    mock_presets_manager_instance.get_monitoring_lists.return_value = sample_monitoring_tasks

    active_tasks = MonitoringTaskManager.get_all_active_monitoring_tasks()

    mock_presets_manager_instance.get_monitoring_lists.assert_called_once()
    assert len(active_tasks) == 2
    assert all(task.active for task in active_tasks)
    assert active_tasks[0].id == "task1"
    assert active_tasks[1].id == "task3"

@patch('inventree_order_calculator.monitoring_service.MonitoringTaskManager.get_all_monitoring_tasks')
def test_mtm_get_task_by_id_found(mock_get_all_tasks, sample_monitoring_tasks):
    """Test get_task_by_id returns the correct task when found."""
    mock_get_all_tasks.return_value = sample_monitoring_tasks
    
    task_id_to_find = "task2"
    found_task = MonitoringTaskManager.get_task_by_id(task_id_to_find)

    mock_get_all_tasks.assert_called_once()
    assert found_task is not None
    assert found_task.id == task_id_to_find
    assert found_task.name == "Task Two"

@patch('inventree_order_calculator.monitoring_service.MonitoringTaskManager.get_all_monitoring_tasks')
def test_mtm_get_task_by_id_not_found(mock_get_all_tasks, sample_monitoring_tasks):
    """Test get_task_by_id returns None when task is not found."""
    mock_get_all_tasks.return_value = sample_monitoring_tasks
    
    task_id_to_find = "non_existent_task_id"
    found_task = MonitoringTaskManager.get_task_by_id(task_id_to_find)

    mock_get_all_tasks.assert_called_once()
    assert found_task is None

# Tests for add_task, update_task, delete_task etc. will follow.
# --- Tests for MonitoringTaskManager modification methods ---

@patch('inventree_order_calculator.monitoring_service._get_presets_manager')
@patch('inventree_order_calculator.monitoring_service._generate_uuid', return_value="new_uuid_123")
@patch('inventree_order_calculator.monitoring_service._scheduler_global_aps_instance') # Mock the global scheduler for now
def test_mtm_add_task_new_id_and_hash(
    mock_scheduler, mock_generate_uuid, mock_get_pm, mock_presets_manager_instance
):
    """Test add_task generates ID if missing, initializes last_hash, and calls PresetsManager."""
    mock_get_pm.return_value = mock_presets_manager_instance
    mock_presets_manager_instance.add_monitoring_list.return_value = True # Simulate success
    
    # Mock the global scheduler's running state for the conceptual check in add_task
    # This part of add_task will be refactored later to use the new Scheduler instance.
    # For now, we test the existing logic.
    if mock_scheduler: # Ensure it's not None if referenced
        mock_scheduler.running = True 
        # We also need to mock the static Scheduler.schedule_task if it's called
        # This highlights the need for refactoring MonitoringTaskManager to use an injected Scheduler instance.
        # For this unit test, we'll focus on PresetsManager interaction.
        # The scheduler interaction part of add_task is more of an integration concern.

    task_data_no_id = {
        "name": "New Task No ID",
        "cron_schedule": "0 0 * * *",
        "parts": [{"part_name": "P1", "quantity": 1}],
        "recipients": ["add@example.com"],
        "notify_condition": "always",
        "active": True
    }
    
    added_task = MonitoringTaskManager.add_task(task_data_no_id.copy()) # Pass a copy

    mock_generate_uuid.assert_called_once()
    mock_presets_manager_instance.add_monitoring_list.assert_called_once()
    
    # Check the argument passed to add_monitoring_list
    call_args = mock_presets_manager_instance.add_monitoring_list.call_args
    assert isinstance(call_args[0][0], MonitoringList)
    added_task_obj_passed = call_args[0][0]
    
    assert added_task_obj_passed.id == "new_uuid_123"
    assert added_task_obj_passed.name == "New Task No ID"
    assert added_task_obj_passed.last_hash == "" # Initialized
    assert added_task is not None
    assert added_task.id == "new_uuid_123"


@patch('inventree_order_calculator.monitoring_service._get_presets_manager')
@patch('inventree_order_calculator.monitoring_service._generate_uuid')
def test_mtm_add_task_with_existing_id(
    mock_generate_uuid, mock_get_pm, mock_presets_manager_instance
):
    """Test add_task uses provided ID and initializes last_hash."""
    mock_get_pm.return_value = mock_presets_manager_instance
    mock_presets_manager_instance.add_monitoring_list.return_value = True

    task_data_with_id = {
        "id": "existing_id_456",
        "name": "New Task With ID",
        "cron_schedule": "0 1 * * *",
        "parts": [{"part_name": "P2", "quantity": 2}],
        "recipients": ["add2@example.com"],
        "notify_condition": "on_change",
        "active": False
    }
    
    added_task = MonitoringTaskManager.add_task(task_data_with_id.copy())

    mock_generate_uuid.assert_not_called() # ID was provided
    mock_presets_manager_instance.add_monitoring_list.assert_called_once()
    
    added_task_obj_passed = mock_presets_manager_instance.add_monitoring_list.call_args[0][0]
    assert added_task_obj_passed.id == "existing_id_456"
    assert added_task_obj_passed.last_hash == "" # Initialized
    assert added_task is not None
    assert added_task.id == "existing_id_456"

@patch('inventree_order_calculator.monitoring_service._get_presets_manager')
def test_mtm_add_task_presets_manager_fails(mock_get_pm, mock_presets_manager_instance):
    """Test add_task returns None if PresetsManager.add_monitoring_list fails."""
    mock_get_pm.return_value = mock_presets_manager_instance
    mock_presets_manager_instance.add_monitoring_list.return_value = False # Simulate failure

    task_data = {"name": "Fail Task", "id": "fail1"}
    added_task = MonitoringTaskManager.add_task(task_data)
    assert added_task is None

@patch('inventree_order_calculator.monitoring_service.MonitoringTaskManager.get_task_by_id')
@patch('inventree_order_calculator.monitoring_service._get_presets_manager')
def test_mtm_update_task_success(
    mock_get_pm, mock_get_task_by_id, mock_presets_manager_instance, sample_monitoring_tasks
):
    """Test update_task successfully updates a task."""
    mock_get_pm.return_value = mock_presets_manager_instance
    existing_task = sample_monitoring_tasks[0] # task1, active=True
    mock_get_task_by_id.return_value = existing_task
    mock_presets_manager_instance.update_monitoring_list.return_value = True

    update_data = {"name": "Task One Updated", "active": False}
    updated_task = MonitoringTaskManager.update_task("task1", update_data)

    mock_get_task_by_id.assert_called_once_with("task1")
    mock_presets_manager_instance.update_monitoring_list.assert_called_once()
    
    updated_task_obj_passed = mock_presets_manager_instance.update_monitoring_list.call_args[0][1]
    assert isinstance(updated_task_obj_passed, MonitoringList)
    assert updated_task_obj_passed.id == "task1"
    assert updated_task_obj_passed.name == "Task One Updated"
    assert updated_task_obj_passed.active is False
    assert updated_task is not None
    assert updated_task.name == "Task One Updated"

@patch('inventree_order_calculator.monitoring_service.MonitoringTaskManager.get_task_by_id')
@patch('inventree_order_calculator.monitoring_service._get_presets_manager')
def test_mtm_update_task_not_found(
    mock_get_pm, mock_get_task_by_id, mock_presets_manager_instance
):
    """Test update_task returns None if task to update is not found."""
    mock_get_pm.return_value = mock_presets_manager_instance
    mock_get_task_by_id.return_value = None # Simulate task not found

    updated_task = MonitoringTaskManager.update_task("ghost_task", {"name": "Ghost"})
    
    mock_get_task_by_id.assert_called_once_with("ghost_task")
    mock_presets_manager_instance.update_monitoring_list.assert_not_called()
    assert updated_task is None

@patch('inventree_order_calculator.monitoring_service._get_presets_manager')
def test_mtm_delete_task_success(mock_get_pm, mock_presets_manager_instance):
    """Test delete_task successfully deletes a task."""
    mock_get_pm.return_value = mock_presets_manager_instance
    mock_presets_manager_instance.delete_monitoring_list.return_value = True
    
    result = MonitoringTaskManager.delete_task("task_to_delete")
    
    mock_presets_manager_instance.delete_monitoring_list.assert_called_once_with("task_to_delete")
    assert result is True

@patch('inventree_order_calculator.monitoring_service._get_presets_manager')
def test_mtm_delete_task_fails(mock_get_pm, mock_presets_manager_instance):
    """Test delete_task returns False if deletion fails."""
    mock_get_pm.return_value = mock_presets_manager_instance
    mock_presets_manager_instance.delete_monitoring_list.return_value = False
    
    result = MonitoringTaskManager.delete_task("task_fail_delete")
    assert result is False

@patch('inventree_order_calculator.monitoring_service.MonitoringTaskManager.update_task')
@patch('inventree_order_calculator.monitoring_service.MonitoringTaskManager.get_task_by_id')
def test_mtm_activate_task(mock_get_task, mock_update_task, sample_monitoring_tasks):
    """Test activate_task activates an inactive task."""
    inactive_task = sample_monitoring_tasks[1] # task2, active=False
    assert not inactive_task.active
    mock_get_task.return_value = inactive_task
    # Simulate update_task returning the updated task object (or a truthy value)
    mock_update_task.return_value = inactive_task.model_copy(update={"active": True}) 

    result = MonitoringTaskManager.activate_task("task2")

    mock_get_task.assert_called_once_with("task2")
    mock_update_task.assert_called_once_with("task2", {"active": True})
    assert result is True

@patch('inventree_order_calculator.monitoring_service.MonitoringTaskManager.update_task')
@patch('inventree_order_calculator.monitoring_service.MonitoringTaskManager.get_task_by_id')
def test_mtm_deactivate_task(mock_get_task, mock_update_task, sample_monitoring_tasks):
    """Test deactivate_task deactivates an active task."""
    active_task = sample_monitoring_tasks[0] # task1, active=True
    assert active_task.active
    mock_get_task.return_value = active_task
    mock_update_task.return_value = active_task.model_copy(update={"active": False})

    result = MonitoringTaskManager.deactivate_task("task1")

    mock_get_task.assert_called_once_with("task1")
    mock_update_task.assert_called_once_with("task1", {"active": False})
    assert result is True

@patch('inventree_order_calculator.monitoring_service.MonitoringTaskManager.update_task')
def test_mtm_update_task_last_hash(mock_update_task):
    """Test update_task_last_hash calls update_task with correct data."""
    mock_update_task.return_value = True # Simulate success
    task_id = "hash_task_1"
    new_hash = "abcdef123456"

    result = MonitoringTaskManager.update_task_last_hash(task_id, new_hash)

    mock_update_task.assert_called_once_with(task_id, {"last_hash": new_hash})
    assert result is True

@patch('inventree_order_calculator.monitoring_service.TaskExecutor.run_monitoring_task')
def test_mtm_run_task_manually(mock_executor_run):
    """Test run_task_manually calls TaskExecutor.run_monitoring_task."""
    task_id_to_run = "manual_run_task"
    MonitoringTaskManager.run_task_manually(task_id_to_run)
    mock_executor_run.assert_called_once_with(task_id_to_run)