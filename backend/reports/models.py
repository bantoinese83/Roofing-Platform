from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Report(models.Model):
    """
    Saved reports with configurable parameters.
    """

    REPORT_TYPES = [
        ('job_status', 'Job Status Distribution'),
        ('completion_rates', 'Job Completion Rates'),
        ('technician_performance', 'Technician Performance'),
        ('revenue_tracking', 'Revenue Tracking'),
        ('customer_satisfaction', 'Customer Satisfaction'),
        ('time_off_summary', 'Time Off Summary'),
        ('schedule_efficiency', 'Schedule Efficiency'),
        ('custom', 'Custom Report'),
    ]

    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annually', 'Annually'),
        ('manual', 'Manual Only'),
    ]

    name = models.CharField(
        max_length=200,
        help_text='Name of the report'
    )

    report_type = models.CharField(
        max_length=30,
        choices=REPORT_TYPES,
        help_text='Type of report'
    )

    description = models.TextField(
        blank=True,
        help_text='Description of what this report shows'
    )

    # Report parameters
    date_range_start = models.DateField(
        null=True,
        blank=True,
        help_text='Start date for the report data'
    )

    date_range_end = models.DateField(
        null=True,
        blank=True,
        help_text='End date for the report data'
    )

    parameters = models.JSONField(
        default=dict,
        help_text='Additional parameters specific to the report type'
    )

    # Scheduling
    is_scheduled = models.BooleanField(
        default=False,
        help_text='Whether this report runs automatically'
    )

    frequency = models.CharField(
        max_length=20,
        choices=FREQUENCY_CHOICES,
        default='manual',
        help_text='How often the report runs automatically'
    )

    # Recipients
    recipients = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='report_subscriptions',
        help_text='Users who should receive this report automatically'
    )

    email_recipients = models.JSONField(
        default=list,
        help_text='Additional email addresses to receive the report'
    )

    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_reports',
        help_text='User who created this report'
    )

    is_active = models.BooleanField(
        default=True,
        help_text='Whether this report is active'
    )

    last_run_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When this report was last generated'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Report'
        verbose_name_plural = 'Reports'

    def __str__(self):
        return f"{self.name} ({self.get_report_type_display()})"

    def generate_report_data(self):
        """
        Generate the actual report data based on type and parameters.
        """
        from .services import ReportService
        service = ReportService()
        return service.generate_report(self.report_type, self.parameters)


class ReportExecution(models.Model):
    """
    Record of report executions and their results.
    """

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name='executions',
        help_text='The report that was executed'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text='Execution status'
    )

    # Execution details
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When execution started'
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When execution completed'
    )

    # Results
    data = models.JSONField(
        null=True,
        blank=True,
        help_text='The generated report data'
    )

    file_path = models.FileField(
        upload_to='reports/',
        blank=True,
        null=True,
        help_text='Path to generated report file (PDF, Excel, etc.)'
    )

    # Error handling
    error_message = models.TextField(
        blank=True,
        help_text='Error message if execution failed'
    )

    # Metadata
    executed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='report_executions',
        help_text='User who triggered this execution'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Report Execution'
        verbose_name_plural = 'Report Executions'
        indexes = [
            models.Index(fields=['report', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"{self.report.name} - {self.get_status_display()} ({self.created_at.date()})"

    @property
    def duration(self):
        """Calculate execution duration"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def start_execution(self, executed_by=None):
        """Mark execution as started"""
        from django.utils import timezone
        self.status = 'running'
        self.started_at = timezone.now()
        self.executed_by = executed_by
        self.save()

    def complete_execution(self, data=None, file_path=None):
        """Mark execution as completed"""
        from django.utils import timezone
        self.status = 'completed'
        self.completed_at = timezone.now()
        if data is not None:
            self.data = data
        if file_path:
            self.file_path = file_path
        self.save()

    def fail_execution(self, error_message):
        """Mark execution as failed"""
        from django.utils import timezone
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.save()


class DashboardMetric(models.Model):
    """
    Real-time dashboard metrics for quick insights.
    """

    METRIC_TYPES = [
        ('total_jobs', 'Total Jobs'),
        ('active_jobs', 'Active Jobs'),
        ('completed_jobs', 'Completed Jobs'),
        ('overdue_jobs', 'Overdue Jobs'),
        ('available_technicians', 'Available Technicians'),
        ('pending_time_off', 'Pending Time Off Requests'),
        ('today_jobs', 'Jobs Scheduled Today'),
        ('weekly_completion_rate', 'Weekly Completion Rate'),
        ('average_job_duration', 'Average Job Duration'),
        ('customer_satisfaction', 'Customer Satisfaction Score'),
        ('revenue_this_month', 'Revenue This Month'),
        ('utilization_rate', 'Technician Utilization Rate'),
    ]

    name = models.CharField(
        max_length=100,
        help_text='Display name for the metric'
    )

    metric_type = models.CharField(
        max_length=50,
        choices=METRIC_TYPES,
        unique=True,
        help_text='Type of metric'
    )

    value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Current value of the metric'
    )

    value_text = models.CharField(
        max_length=100,
        blank=True,
        help_text='Text representation of the value (for non-numeric metrics)'
    )

    unit = models.CharField(
        max_length=20,
        blank=True,
        help_text='Unit of measurement (%, $, hours, etc.)'
    )

    # Trend information
    previous_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Previous value for trend calculation'
    )

    trend_direction = models.CharField(
        max_length=10,
        choices=[('up', 'Up'), ('down', 'Down'), ('stable', 'Stable')],
        default='stable',
        help_text='Trend direction compared to previous period'
    )

    # Refresh settings
    refresh_interval_minutes = models.PositiveIntegerField(
        default=60,
        help_text='How often to refresh this metric (in minutes)'
    )

    last_updated = models.DateTimeField(
        auto_now=True,
        help_text='When this metric was last updated'
    )

    # Display settings
    is_active = models.BooleanField(
        default=True,
        help_text='Whether to display this metric'
    )

    display_order = models.PositiveIntegerField(
        default=0,
        help_text='Order in which to display metrics'
    )

    color_code = models.CharField(
        max_length=20,
        default='blue',
        help_text='Color theme for the metric display'
    )

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = 'Dashboard Metric'
        verbose_name_plural = 'Dashboard Metrics'

    def __str__(self):
        return f"{self.name}: {self.value or self.value_text} {self.unit}"

    @property
    def trend_percentage(self):
        """Calculate trend percentage"""
        if self.previous_value and self.previous_value != 0 and self.value is not None:
            return ((self.value - self.previous_value) / self.previous_value) * 100
        return 0

    def update_value(self, new_value, new_value_text=''):
        """Update the metric value and calculate trend"""
        from django.utils import timezone

        if self.value is not None:
            self.previous_value = self.value

            if new_value > self.value:
                self.trend_direction = 'up'
            elif new_value < self.value:
                self.trend_direction = 'down'
            else:
                self.trend_direction = 'stable'

        self.value = new_value
        if new_value_text:
            self.value_text = new_value_text

        self.last_updated = timezone.now()
        self.save()
