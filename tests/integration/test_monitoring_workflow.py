import pytest
from unittest.mock import MagicMock, patch, call
import time

from inventree_order_calculator.monitoring_service import MonitoringTaskManager, TaskExecutor
from inventree_order_calculator.models import MonitoringList, NotifyCondition
from inventree_order_calculator.config import AppConfig

# Placeholder for now, will be expanded
# These tests will initially fail as the implementation details and mocks are not fully set up.

@pytest.fixture
def mock_scheduler():
    """Fixture for a mocked APScheduler."""
    scheduler = MagicMock()
    scheduler.add_job = MagicMock()
    scheduler.remove_job = MagicMock()
    scheduler.pause_job = MagicMock()
    scheduler.resume_job = MagicMock()
    scheduler.get_job = MagicMock()
    return scheduler

@pytest.fixture
def mock_order_calculator():
    """Fixture for a mocked OrderCalculator."""
    calculator = MagicMock()
    calculator.calculate_total_cost_for_part_list.return_value = ({"some_part": {"quantity": 1, "total_price": 10.0}}, 10.0)
    return calculator

@pytest.fixture
def mock_api_client():
    """Fixture for a mocked ApiClient."""
    client = MagicMock()
    # Mock any methods that TaskExecutor might call on ApiClient if necessary
    return client

@pytest.fixture
def mock_email_service():
    """Fixture for a mocked EmailService."""
    service = MagicMock()
    service.send_notification_email = MagicMock()
    return service

@pytest.fixture
def app_config(tmp_path):
    """Fixture for AppConfig using a temporary path for presets."""
    config = AppConfig()
    config.PRESETS_FILE = tmp_path / "temp_presets.json"
    # Ensure other necessary email configs are set if EmailService is initialized
    config.SMTP_HOST = "smtp.example.com"
    config.SMTP_PORT = 587
    config.SMTP_USER = "user"
    config.SMTP_PASSWORD = "password"
    config.SMTP_SENDER_EMAIL = "sender@example.com"
    return config

@pytest.fixture
def task_executor(mock_order_calculator, mock_api_client, mock_email_service, app_config):
    """Fixture for TaskExecutor with mocked dependencies."""
    return TaskExecutor(
        order_calculator=mock_order_calculator,
        api_client=mock_api_client,
        email_service=mock_email_service,
        config=app_config
    )

@pytest.fixture
@patch('inventree_order_calculator.monitoring_service.BackgroundScheduler')
def monitoring_task_manager(MockBackgroundScheduler, task_executor, app_config):
    """Fixture for MonitoringTaskManager with a mocked scheduler and real TaskExecutor."""
    mock_scheduler_instance = mock_scheduler() # Use our more detailed mock
    MockBackgroundScheduler.return_value = mock_scheduler_instance
    
    manager = MonitoringTaskManager(task_executor=task_executor, config=app_config)
    # manager.scheduler is now mock_scheduler_instance
    return manager, mock_scheduler_instance # Return both for easier access in tests

class TestMonitoringWorkflowIntegration:

    def test_add_monitoring_task_schedules_job(self, monitoring_task_manager):
        """
        Test that adding a monitoring task via MonitoringTaskManager
        correctly schedules a job with the Scheduler.
        """
        manager, scheduler_mock = monitoring_task_manager
        
        monitor_list = MonitoringList(
            name="Test Task",
            parts_list_file="path/to/list.csv",
            target_price=100.0,
            schedule="0 0 * * *", # every day at midnight
            active=True,
            notify_on=NotifyCondition.ALWAYS,
            recipient_emails=["test@example.com"]
        )
        
        manager.add_or_update_task(monitor_list)
        
        scheduler_mock.add_job.assert_called_once()
        args, kwargs = scheduler_mock.add_job.call_args
        
        assert kwargs['id'] == monitor_list.name
        assert kwargs['name'] == monitor_list.name
        assert kwargs['trigger'] == 'cron'
        assert kwargs['hour'] == '0'
        assert kwargs['minute'] == '0'
        # Further assertions on func, args for the job can be added
        # For example, assert that args[0] is the task_executor.execute_task
        # and args[1] contains monitor_list.name

    def test_scheduler_calls_task_executor_correctly(self, monitoring_task_manager, task_executor):
        """
        Test that the Scheduler (when a job is triggered) calls the TaskExecutor
        with the correct parameters. This test will be more conceptual as we
        are mocking the scheduler's triggering mechanism.
        We'll simulate the call that scheduler would make.
        """
        manager, scheduler_mock = monitoring_task_manager
        
        monitor_list = MonitoringList(
            name="Executor Test Task",
            parts_list_file="path/to/another_list.csv",
            target_price=200.0,
            schedule="0 1 * * *",
            active=True,
            notify_on=NotifyCondition.ON_CHANGE,
            recipient_emails=["exec@example.com"]
        )
        
        # Add the task to get it into the manager's internal state if needed
        # and to have a job definition for the scheduler mock
        manager.add_or_update_task(monitor_list)
        
        # Simulate the scheduler calling the job function
        # We need to find the function that was passed to add_job
        # For now, let's assume task_executor.execute_task is called directly
        # and we can mock execute_task on the real task_executor instance
        
        with patch.object(task_executor, 'execute_task', wraps=task_executor.execute_task) as mock_execute:
            # This part is tricky: we need to simulate the scheduler's action.
            # One way is to capture the function passed to add_job and call it.
            if scheduler_mock.add_job.call_count > 0:
                job_func = scheduler_mock.add_job.call_args.kwargs.get('func')
                job_args = scheduler_mock.add_job.call_args.kwargs.get('args', [])
                if job_func:
                    job_func(*job_args) # Simulate scheduler running the job
                else:
                    pytest.fail("Job function not captured from scheduler.add_job mock")
            else:
                 pytest.fail("scheduler.add_job was not called, cannot simulate job execution.")

            mock_execute.assert_called_once_with(monitor_list.name)

    @patch('inventree_order_calculator.monitoring_service.TaskExecutor._calculate_and_get_hash')
    @patch('inventree_order_calculator.monitoring_service.TaskExecutor._load_monitoring_list_from_presets')
    def test_task_executor_calculates_compares_hash_and_notifies(
        self, 
        mock_load_presets, 
        mock_calculate_hash, 
        task_executor, 
        mock_email_service,
        monitoring_task_manager # to get app_config easily
    ):
        """
        Test that TaskExecutor performs calculation (mocked), compares hash,
        and calls EmailService under correct conditions (notify on change & hash change).
        """
        manager, _ = monitoring_task_manager # for app_config via task_executor.config
        app_config = task_executor.config

        task_name = "Notify Test Task"
        monitor_list = MonitoringList(
            name=task_name,
            parts_list_file="path/to/notify_list.csv",
            target_price=300.0,
            schedule="0 2 * * *",
            active=True,
            notify_on=NotifyCondition.ON_CHANGE,
            recipient_emails=["notify@example.com"],
            last_hash=None # No previous hash
        )
        mock_load_presets.return_value = monitor_list
        
        # Simulate new calculation result and hash
        new_calculated_data = ({"part_c": {"quantity": 1, "total_price": 25.0}}, 25.0)
        new_hash = "new_hash_value_abc"
        mock_calculate_hash.return_value = (new_calculated_data, new_hash)

        # We also need a PresetsManager mock or a way to save the updated hash
        # For simplicity, let's assume PresetsManager is implicitly used and works.
        # We'll mock its save method if TaskExecutor calls it directly.
        with patch.object(task_executor.presets_manager, 'save_preset') as mock_save_preset:
            task_executor.execute_task(task_name)

            mock_load_presets.assert_called_once_with(task_name)
            mock_calculate_hash.assert_called_once_with(monitor_list)
            
            # Assert email service was called because notify_on=ON_CHANGE and hash changed
            mock_email_service.send_notification_email.assert_called_once()
            email_args, email_kwargs = mock_email_service.send_notification_email.call_args
            assert email_kwargs['recipients'] == monitor_list.recipient_emails
            assert task_name in email_kwargs['subject']
            
            # Assert that the preset was saved with the new hash
            mock_save_preset.assert_called_once()
            saved_list_arg = mock_save_preset.call_args[0][0]
            assert saved_list_arg.name == task_name
            assert saved_list_arg.last_hash == new_hash

    def test_deactivate_task_pauses_job_in_scheduler(self, monitoring_task_manager):
        """Test that deactivating a task pauses the job in the scheduler."""
        manager, scheduler_mock = monitoring_task_manager
        task_name = "Deactivation Test Task"
        monitor_list = MonitoringList(
            name=task_name,
            parts_list_file="path/to/deactivate.csv",
            schedule="* * * * *",
            active=True, # Initially active
            notify_on=NotifyCondition.NEVER,
            recipient_emails=[]
        )
        # Mock get_job to return a mock job object
        mock_job = MagicMock()
        scheduler_mock.get_job.return_value = mock_job

        manager.add_or_update_task(monitor_list) # Add it first
        scheduler_mock.add_job.assert_called_with(
            func=manager.task_executor.execute_task, 
            args=[task_name], 
            trigger='cron', 
            id=task_name, 
            name=task_name, 
            minute='*', hour='*', day='*', month='*', day_of_week='*',
            replace_existing=True
        )
        
        manager.deactivate_task(task_name)
        
        scheduler_mock.get_job.assert_called_with(task_name)
        scheduler_mock.pause_job.assert_called_once_with(task_name)

    def test_activate_task_resumes_or_adds_job_in_scheduler(self, monitoring_task_manager):
        """Test that activating a task resumes a paused job or adds a new one."""
        manager, scheduler_mock = monitoring_task_manager
        task_name = "Activation Test Task"
        monitor_list = MonitoringList(
            name=task_name,
            parts_list_file="path/to/activate.csv",
            schedule="* * * * *",
            active=False, # Initially inactive
            notify_on=NotifyCondition.NEVER,
            recipient_emails=[]
        )
        # Simulate task being known to PresetsManager (e.g., loaded on manager init or added then deactivated)
        # For this test, let's assume it was added then deactivated, so a job might exist.
        
        # Scenario 1: Job exists and is paused
        mock_paused_job = MagicMock()
        scheduler_mock.get_job.return_value = mock_paused_job
        
        # To ensure add_or_update_task is called by activate_task if job doesn't exist
        # we need to make sure it's in manager's presets.
        # This part needs PresetsManager interaction.
        # For now, let's assume activate_task handles this logic.
        # A more robust test would involve mocking PresetsManager.load_preset
        with patch.object(manager.presets_manager, 'load_preset') as mock_load_preset_pm:
            mock_load_preset_pm.return_value = monitor_list # So manager knows about it
            manager.activate_task(task_name)
        
        scheduler_mock.get_job.assert_called_with(task_name)
        scheduler_mock.resume_job.assert_called_once_with(task_name)
        scheduler_mock.add_job.assert_not_called() # Should resume, not add new if exists

        scheduler_mock.reset_mock()

        # Scenario 2: Job does not exist (e.g., task was deactivated and job removed, or never added)
        scheduler_mock.get_job.return_value = None 
        with patch.object(manager.presets_manager, 'load_preset') as mock_load_preset_pm_2:
            monitor_list.active = False # ensure it's seen as inactive before activation
            mock_load_preset_pm_2.return_value = monitor_list
            manager.activate_task(task_name)

        scheduler_mock.get_job.assert_called_with(task_name)
        scheduler_mock.add_job.assert_called_once() # Should add new job
        args, kwargs = scheduler_mock.add_job.call_args
        assert kwargs['id'] == task_name
        scheduler_mock.resume_job.assert_not_called()


    def test_manual_trigger_executes_task_once(self, monitoring_task_manager, task_executor):
        """Test that manually triggering a task executes it once immediately."""
        manager, scheduler_mock = monitoring_task_manager
        task_name = "Manual Trigger Task"
        monitor_list = MonitoringList(
            name=task_name,
            parts_list_file="path/to/manual.csv",
            schedule="0 0 1 1 *", # Some infrequent schedule
            active=True,
            notify_on=NotifyCondition.ALWAYS,
            recipient_emails=["manual@example.com"]
        )

        # Ensure the task is known to the manager (e.g. by adding it)
        # or by mocking presets_manager.load_preset
        with patch.object(manager.presets_manager, 'load_preset') as mock_load_preset_pm:
            mock_load_preset_pm.return_value = monitor_list
            
            with patch.object(task_executor, 'execute_task') as mock_execute:
                manager.trigger_task_manually(task_name)
                mock_execute.assert_called_once_with(task_name)

        # Ensure no new persistent jobs were added or modified for a manual trigger
        # (unless trigger_task_manually is supposed to also schedule if not active,
        #  which is not the typical expectation for a "manual run once" command)
        # For now, assume it only runs it.
        scheduler_mock.add_job.assert_not_called() 
        scheduler_mock.resume_job.assert_not_called()
        scheduler_mock.pause_job.assert_not_called()