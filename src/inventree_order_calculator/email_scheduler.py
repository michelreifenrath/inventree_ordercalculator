# Module: src/inventree_order_calculator/email_scheduler.py
# Description: Scheduling functionality for automated email notifications

import logging
from datetime import datetime, time
from typing import Optional, Callable, Dict, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
import pytz

from .email_config import EmailConfig, ScheduleFrequency
from .email_sender import EmailSender, EmailSendError
from .models import OutputTables, InputPart
from .presets_manager import get_preset_by_name, PresetsFile

logger = logging.getLogger(__name__)

class EmailScheduler:
    """Manages scheduled email notifications for order calculator"""
    
    def __init__(self, calculation_callback: Callable[[str], OutputTables]):
        """
        Initialize email scheduler
        
        Args:
            calculation_callback: Function that takes preset name and returns OutputTables
        """
        self.calculation_callback = calculation_callback
        self.scheduler: Optional[BackgroundScheduler] = None
        self._job_id = "email_notification_job"
        
        # Configure scheduler
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': ThreadPoolExecutor(max_workers=1)
        }
        job_defaults = {
            'coalesce': True,  # Combine multiple pending executions into one
            'max_instances': 1,  # Only one instance of job can run at a time
            'misfire_grace_time': 300  # 5 minutes grace time for missed jobs
        }
        
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=pytz.UTC
        )
    
    def start(self) -> bool:
        """Start the scheduler"""
        try:
            if not self.scheduler.running:
                self.scheduler.start()
                logger.info("Email scheduler started")
                return True
            else:
                logger.warning("Email scheduler is already running")
                return True
        except Exception as e:
            logger.error(f"Failed to start email scheduler: {e}")
            return False
    
    def stop(self) -> bool:
        """Stop the scheduler"""
        try:
            if self.scheduler and self.scheduler.running:
                self.scheduler.shutdown(wait=True)
                logger.info("Email scheduler stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop email scheduler: {e}")
            return False
    
    def schedule_email(self, config: EmailConfig) -> bool:
        """
        Schedule email notifications based on configuration
        
        Args:
            config: EmailConfig with schedule settings
            
        Returns:
            True if scheduling successful
        """
        try:
            # Remove existing job if present
            self.unschedule_email()
            
            if not config.schedule.enabled:
                logger.info("Email scheduling is disabled")
                return True
            
            if not config.schedule.preset_name:
                logger.error("Cannot schedule email: no preset specified")
                return False
            
            # Parse time
            hour, minute = map(int, config.schedule.time_of_day.split(':'))
            
            # Create timezone object
            try:
                tz = pytz.timezone(config.schedule.timezone)
            except pytz.UnknownTimeZoneError:
                logger.warning(f"Unknown timezone {config.schedule.timezone}, using UTC")
                tz = pytz.UTC
            
            # Create trigger based on frequency
            trigger = self._create_trigger(config.schedule.frequency, hour, minute, tz)
            
            # Add job to scheduler
            self.scheduler.add_job(
                func=self._execute_scheduled_email,
                trigger=trigger,
                id=self._job_id,
                args=[config],
                name=f"Email notification for preset: {config.schedule.preset_name}",
                replace_existing=True
            )
            
            next_run = self.scheduler.get_job(self._job_id).next_run_time
            logger.info(f"Email scheduled for preset '{config.schedule.preset_name}' "
                       f"at {config.schedule.time_of_day} {config.schedule.frequency}. "
                       f"Next run: {next_run}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to schedule email: {e}")
            return False
    
    def unschedule_email(self) -> bool:
        """Remove scheduled email job"""
        try:
            if self.scheduler.get_job(self._job_id):
                self.scheduler.remove_job(self._job_id)
                logger.info("Email scheduling removed")
            return True
        except Exception as e:
            logger.error(f"Failed to unschedule email: {e}")
            return False
    
    def get_next_run_time(self) -> Optional[datetime]:
        """Get next scheduled run time"""
        try:
            job = self.scheduler.get_job(self._job_id)
            return job.next_run_time if job else None
        except Exception:
            return None
    
    def is_scheduled(self) -> bool:
        """Check if email is currently scheduled"""
        try:
            return self.scheduler.get_job(self._job_id) is not None
        except Exception:
            return False
    
    def get_schedule_info(self) -> Optional[Dict[str, Any]]:
        """Get information about current schedule"""
        try:
            job = self.scheduler.get_job(self._job_id)
            if not job:
                return None
            
            return {
                'job_id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time,
                'trigger': str(job.trigger),
                'args': job.args[0] if job.args else None  # EmailConfig
            }
        except Exception as e:
            logger.error(f"Failed to get schedule info: {e}")
            return None
    
    def _create_trigger(
        self, 
        frequency: ScheduleFrequency, 
        hour: int, 
        minute: int, 
        timezone: pytz.BaseTzInfo
    ) -> CronTrigger:
        """Create appropriate trigger based on frequency"""
        
        if frequency == ScheduleFrequency.DAILY:
            return CronTrigger(
                hour=hour,
                minute=minute,
                timezone=timezone
            )
        elif frequency == ScheduleFrequency.WEEKLY:
            # Run every Monday
            return CronTrigger(
                day_of_week='mon',
                hour=hour,
                minute=minute,
                timezone=timezone
            )
        elif frequency == ScheduleFrequency.MONTHLY:
            # Run on first day of month
            return CronTrigger(
                day=1,
                hour=hour,
                minute=minute,
                timezone=timezone
            )
        else:
            raise ValueError(f"Unsupported frequency: {frequency}")
    
    def _execute_scheduled_email(self, config: EmailConfig) -> None:
        """Execute scheduled email notification"""
        try:
            logger.info(f"Executing scheduled email for preset: {config.schedule.preset_name}")
            
            # Get calculation results using callback
            results = self.calculation_callback(config.schedule.preset_name)
            
            if not results:
                logger.error("Failed to get calculation results for scheduled email")
                return
            
            # Send email
            sender = EmailSender(config)
            success = sender.send_report(
                results=results,
                preset_name=config.schedule.preset_name,
                test_mode=False
            )
            
            if success:
                logger.info(f"Scheduled email sent successfully for preset: {config.schedule.preset_name}")
            else:
                logger.error(f"Failed to send scheduled email for preset: {config.schedule.preset_name}")
                
        except EmailSendError as e:
            logger.error(f"Email sending error in scheduled job: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in scheduled email job: {e}")

class EmailSchedulerManager:
    """High-level manager for email scheduling functionality"""
    
    def __init__(self, api_client, presets_data: PresetsFile):
        """
        Initialize scheduler manager
        
        Args:
            api_client: ApiClient instance for calculations
            presets_data: PresetsFile containing available presets
        """
        self.api_client = api_client
        self.presets_data = presets_data
        self.scheduler = EmailScheduler(self._calculate_from_preset)
    
    def start_scheduler(self) -> bool:
        """Start the email scheduler"""
        return self.scheduler.start()
    
    def stop_scheduler(self) -> bool:
        """Stop the email scheduler"""
        return self.scheduler.stop()
    
    def update_schedule(self, config: EmailConfig) -> bool:
        """Update email schedule with new configuration"""
        return self.scheduler.schedule_email(config)
    
    def remove_schedule(self) -> bool:
        """Remove current email schedule"""
        return self.scheduler.unschedule_email()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status"""
        return {
            'running': self.scheduler.scheduler.running if self.scheduler.scheduler else False,
            'scheduled': self.scheduler.is_scheduled(),
            'next_run': self.scheduler.get_next_run_time(),
            'schedule_info': self.scheduler.get_schedule_info()
        }
    
    def _calculate_from_preset(self, preset_name: str) -> Optional[OutputTables]:
        """
        Calculate orders from preset name
        
        Args:
            preset_name: Name of preset to use for calculation
            
        Returns:
            OutputTables with calculation results or None if failed
        """
        try:
            from .calculator import OrderCalculator
            
            # Get preset
            preset = get_preset_by_name(self.presets_data, preset_name)
            if not preset:
                logger.error(f"Preset '{preset_name}' not found for scheduled calculation")
                return None
            
            # Convert preset items to InputPart list
            input_parts = [
                InputPart(
                    part_identifier=str(item.part_id),
                    quantity_to_build=float(item.quantity)
                )
                for item in preset.items
            ]
            
            # Perform calculation
            calculator = OrderCalculator(self.api_client)
            results = calculator.calculate_orders(input_parts)
            
            logger.info(f"Calculation completed for preset '{preset_name}': "
                       f"{len(results.parts_to_order)} parts, "
                       f"{len(results.subassemblies_to_build)} assemblies")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to calculate from preset '{preset_name}': {e}")
            return None
