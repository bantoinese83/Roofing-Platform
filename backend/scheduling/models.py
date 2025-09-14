from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class JobSchedule(models.Model):
    """
    Scheduling information for jobs.
    Links jobs to specific dates, times, and crews.
    """

    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    job = models.OneToOneField(
        'jobs.Job',
        on_delete=models.CASCADE,
        related_name='schedule',
        help_text='Job being scheduled'
    )

    scheduled_date = models.DateField(
        help_text='Date when the job is scheduled'
    )

    scheduled_time = models.TimeField(
        null=True,
        blank=True,
        help_text='Time when the job is scheduled to start'
    )

    estimated_duration_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=2.0,
        help_text='Estimated duration in hours'
    )

    actual_duration_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Actual duration in hours'
    )

    assigned_crew = models.ForeignKey(
        'technicians.Crew',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scheduled_jobs',
        help_text='Crew assigned to this job'
    )

    assigned_technician = models.ForeignKey(
        'technicians.TechnicianProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scheduled_jobs',
        help_text='Primary technician assigned to this job'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled',
        help_text='Current scheduling status'
    )

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        help_text='Job priority level'
    )

    # Location for mapping
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='Job location latitude'
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='Job location longitude'
    )

    # Notes and special instructions
    scheduling_notes = models.TextField(
        blank=True,
        help_text='Special scheduling notes or instructions'
    )

    customer_notes = models.TextField(
        blank=True,
        help_text='Notes from customer about scheduling preferences'
    )

    # Tracking
    scheduled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='scheduled_jobs',
        help_text='User who scheduled this job'
    )

    scheduled_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When this job was scheduled'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text='Last update timestamp'
    )

    class Meta:
        ordering = ['scheduled_date', 'scheduled_time']
        verbose_name = 'Job Schedule'
        verbose_name_plural = 'Job Schedules'
        indexes = [
            models.Index(fields=['scheduled_date', 'status']),
            models.Index(fields=['assigned_crew', 'scheduled_date']),
            models.Index(fields=['assigned_technician', 'scheduled_date']),
            models.Index(fields=['status', 'priority']),
        ]

    def __str__(self):
        return f"{self.job.job_number} - {self.scheduled_date}"

    @property
    def duration_display(self):
        """Return formatted duration display"""
        hours = float(self.estimated_duration_hours)
        if hours == 1:
            return "1 hour"
        elif hours < 1:
            minutes = int(hours * 60)
            return f"{minutes} minutes"
        else:
            return ".1f"

    @property
    def is_overdue(self):
        """Check if this scheduled job is overdue"""
        from django.utils import timezone
        now = timezone.now()

        if self.status in ['completed', 'cancelled']:
            return False

        if self.scheduled_date < now.date():
            return True

        if self.scheduled_date == now.date() and self.scheduled_time:
            if now.time() > self.scheduled_time:
                return True

        return False

    @property
    def status_color(self):
        """Return color class for status"""
        colors = {
            'scheduled': 'bg-blue-100 text-blue-800',
            'confirmed': 'bg-green-100 text-green-800',
            'in_progress': 'bg-yellow-100 text-yellow-800',
            'completed': 'bg-gray-100 text-gray-800',
            'cancelled': 'bg-red-100 text-red-800',
            'no_show': 'bg-purple-100 text-purple-800',
        }
        return colors.get(self.status, 'bg-gray-100 text-gray-800')

    @property
    def priority_color(self):
        """Return color class for priority"""
        colors = {
            'low': 'bg-gray-100 text-gray-800',
            'medium': 'bg-yellow-100 text-yellow-800',
            'high': 'bg-orange-100 text-orange-800',
            'urgent': 'bg-red-100 text-red-800',
        }
        return colors.get(self.priority, 'bg-gray-100 text-gray-800')


class CalendarEvent(models.Model):
    """
    Calendar events that are not directly tied to jobs.
    Includes holidays, training, meetings, etc.
    """

    EVENT_TYPES = [
        ('holiday', 'Holiday'),
        ('training', 'Training'),
        ('meeting', 'Meeting'),
        ('maintenance', 'Maintenance'),
        ('other', 'Other'),
    ]

    title = models.CharField(
        max_length=200,
        help_text='Event title'
    )

    description = models.TextField(
        blank=True,
        help_text='Event description'
    )

    event_type = models.CharField(
        max_length=20,
        choices=EVENT_TYPES,
        default='other',
        help_text='Type of calendar event'
    )

    start_date = models.DateField(
        help_text='Event start date'
    )

    start_time = models.TimeField(
        null=True,
        blank=True,
        help_text='Event start time'
    )

    end_date = models.DateField(
        null=True,
        blank=True,
        help_text='Event end date (if different from start)'
    )

    end_time = models.TimeField(
        null=True,
        blank=True,
        help_text='Event end time'
    )

    is_all_day = models.BooleanField(
        default=False,
        help_text='Whether this is an all-day event'
    )

    # Assignment
    assigned_to = models.ManyToManyField(
        'technicians.TechnicianProfile',
        blank=True,
        related_name='calendar_events',
        help_text='Technicians assigned to this event'
    )

    assigned_crews = models.ManyToManyField(
        'technicians.Crew',
        blank=True,
        related_name='calendar_events',
        help_text='Crews assigned to this event'
    )

    # Location (optional)
    location = models.CharField(
        max_length=200,
        blank=True,
        help_text='Event location'
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='Location latitude'
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='Location longitude'
    )

    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_calendar_events',
        help_text='User who created this event'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_date', 'start_time']
        verbose_name = 'Calendar Event'
        verbose_name_plural = 'Calendar Events'
        indexes = [
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['event_type', 'start_date']),
        ]

    def __str__(self):
        return f"{self.title} - {self.start_date}"

    @property
    def duration_days(self):
        """Calculate event duration in days"""
        if self.end_date:
            return (self.end_date - self.start_date).days + 1
        return 1


class SchedulingSettings(models.Model):
    """
    Global scheduling settings and preferences.
    """

    # Default scheduling settings
    default_job_duration_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=2.0,
        help_text='Default estimated duration for new jobs'
    )

    working_hours_start = models.TimeField(
        default='08:00:00',
        help_text='Default working hours start time'
    )

    working_hours_end = models.TimeField(
        default='17:00:00',
        help_text='Default working hours end time'
    )

    # Buffer settings
    buffer_between_jobs_minutes = models.PositiveIntegerField(
        default=30,
        help_text='Buffer time between jobs in minutes'
    )

    # Auto-scheduling settings
    auto_schedule_new_jobs = models.BooleanField(
        default=False,
        help_text='Automatically schedule new jobs'
    )

    auto_assign_crews = models.BooleanField(
        default=False,
        help_text='Automatically assign crews based on availability'
    )

    # Notification settings
    notify_on_overdue_jobs = models.BooleanField(
        default=True,
        help_text='Send notifications for overdue jobs'
    )

    overdue_notification_hours = models.PositiveIntegerField(
        default=2,
        help_text='Hours before scheduled time to send overdue notifications'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Scheduling Settings'
        verbose_name_plural = 'Scheduling Settings'

    def __str__(self):
        return "Global Scheduling Settings"

    @classmethod
    def get_settings(cls):
        """Get the global scheduling settings (singleton pattern)."""
        settings_obj, created = cls.objects.get_or_create(
            defaults={
                'default_job_duration_hours': 2.0,
                'working_hours_start': '08:00:00',
                'working_hours_end': '17:00:00',
            }
        )
        return settings_obj
