from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.template import Template, Context
from django.core.mail import send_mail
from django.utils import timezone


class NotificationTemplate(models.Model):
    """
    Configurable templates for different types of notifications.
    """

    NOTIFICATION_TYPES = [
        ('sms', 'SMS'),
        ('email', 'Email'),
    ]

    TEMPLATE_TYPES = [
        ('appointment_confirmation', 'Appointment Confirmation'),
        ('appointment_reminder', 'Appointment Reminder'),
        ('job_status_update', 'Job Status Update'),
        ('job_assigned', 'Job Assigned to Technician'),
        ('job_completed', 'Job Completed'),
        ('job_cancelled', 'Job Cancelled'),
        ('welcome_customer', 'Welcome New Customer'),
        ('payment_reminder', 'Payment Reminder'),
        ('feedback_request', 'Feedback Request'),
    ]

    name = models.CharField(
        max_length=100,
        help_text='Display name for the template'
    )

    template_type = models.CharField(
        max_length=50,
        choices=TEMPLATE_TYPES,
        help_text='The type of notification this template is for'
    )

    notification_method = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        help_text='SMS or Email'
    )

    subject = models.CharField(
        max_length=200,
        blank=True,
        help_text='Email subject line (ignored for SMS)'
    )

    content = models.TextField(
        help_text='Template content with placeholders like {{customer_name}}, {{job_title}}, etc.'
    )

    is_active = models.BooleanField(
        default=True,
        help_text='Whether this template is active and available for use'
    )

    # Timing configuration for automated notifications
    send_before_hours = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Send notification this many hours before scheduled time (for reminders)'
    )

    # Target audience
    send_to_customer = models.BooleanField(
        default=True,
        help_text='Send to customer'
    )

    send_to_technician = models.BooleanField(
        default=False,
        help_text='Send to assigned technician'
    )

    send_to_office = models.BooleanField(
        default=False,
        help_text='Send to office/managers'
    )

    # Trigger configuration
    trigger_on_job_create = models.BooleanField(
        default=False,
        help_text='Send when job is created'
    )

    trigger_on_job_update = models.BooleanField(
        default=False,
        help_text='Send when job is updated'
    )

    trigger_on_status_change = models.BooleanField(
        default=False,
        help_text='Send when job status changes'
    )

    trigger_statuses = models.JSONField(
        null=True,
        blank=True,
        help_text='Specific statuses that trigger this notification (if trigger_on_status_change is True)'
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_notification_templates',
        help_text='User who created this template'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['template_type', 'notification_method', 'name']
        verbose_name = 'Notification Template'
        verbose_name_plural = 'Notification Templates'
        unique_together = ['template_type', 'notification_method']

    def __str__(self):
        return f"{self.get_template_type_display()} - {self.get_notification_method_display()} - {self.name}"

    def render_content(self, context_data):
        """
        Render the template content with provided context data.
        """
        template = Template(self.content)
        context = Context(context_data)
        return template.render(context)

    def render_subject(self, context_data):
        """
        Render the email subject with provided context data.
        """
        if not self.subject:
            return ""
        template = Template(self.subject)
        context = Context(context_data)
        return template.render(context)

    def get_available_placeholders(self):
        """
        Return a list of available placeholder variables for this template type.
        """
        placeholders = {
            'appointment_confirmation': [
                'customer_name', 'customer_email', 'customer_phone',
                'job_title', 'job_number', 'scheduled_date', 'scheduled_time',
                'job_address', 'company_name', 'contact_phone'
            ],
            'appointment_reminder': [
                'customer_name', 'customer_email', 'customer_phone',
                'job_title', 'job_number', 'scheduled_date', 'scheduled_time',
                'job_address', 'company_name', 'contact_phone', 'hours_until'
            ],
            'job_status_update': [
                'customer_name', 'customer_email', 'customer_phone',
                'job_title', 'job_number', 'old_status', 'new_status',
                'scheduled_date', 'scheduled_time', 'job_address',
                'technician_name', 'technician_phone', 'company_name'
            ],
            'job_assigned': [
                'technician_name', 'technician_email', 'technician_phone',
                'customer_name', 'job_title', 'job_number', 'scheduled_date',
                'scheduled_time', 'job_address', 'company_name'
            ],
            'job_completed': [
                'customer_name', 'customer_email', 'customer_phone',
                'job_title', 'job_number', 'completion_date', 'job_address',
                'technician_name', 'company_name', 'feedback_link'
            ],
            'welcome_customer': [
                'customer_name', 'customer_email', 'company_name',
                'contact_phone', 'website_url'
            ]
        }
        return placeholders.get(self.template_type, [])


class NotificationLog(models.Model):
    """
    Log of all sent notifications for auditing and tracking.
    """

    NOTIFICATION_TYPES = [
        ('sms', 'SMS'),
        ('email', 'Email'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('bounced', 'Bounced'),
    ]

    # Related objects
    job = models.ForeignKey(
        'jobs.Job',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        help_text='Related job (if applicable)'
    )

    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        help_text='Related customer (if applicable)'
    )

    technician = models.ForeignKey(
        'technicians.TechnicianProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        help_text='Related technician (if applicable)'
    )

    # Notification details
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        help_text='Type of notification sent'
    )

    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs',
        help_text='Template used for this notification'
    )

    recipient_email = models.EmailField(
        blank=True,
        help_text='Email address of recipient (for email notifications)'
    )

    recipient_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text='Phone number of recipient (for SMS notifications)'
    )

    subject = models.CharField(
        max_length=200,
        blank=True,
        help_text='Email subject or SMS preview'
    )

    content = models.TextField(
        help_text='Full content of the notification'
    )

    # Status and delivery
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text='Delivery status of the notification'
    )

    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the notification was sent'
    )

    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the notification was delivered (if available)'
    )

    # External service tracking
    external_id = models.CharField(
        max_length=100,
        blank=True,
        help_text='External service ID (Twilio SID, SendGrid message ID, etc.)'
    )

    error_message = models.TextField(
        blank=True,
        help_text='Error message if delivery failed'
    )

    # Retry information
    retry_count = models.PositiveIntegerField(
        default=0,
        help_text='Number of retry attempts'
    )

    max_retries = models.PositiveIntegerField(
        default=3,
        help_text='Maximum number of retry attempts'
    )

    next_retry_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When to attempt the next retry'
    )

    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_notifications',
        help_text='User who triggered this notification'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification Log'
        verbose_name_plural = 'Notification Logs'
        indexes = [
            models.Index(fields=['job', 'created_at']),
            models.Index(fields=['customer', 'created_at']),
            models.Index(fields=['technician', 'created_at']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['notification_type', 'status']),
        ]

    def __str__(self):
        recipient = self.recipient_email or self.recipient_phone
        return f"{self.get_notification_type_display()} to {recipient} - {self.get_status_display()}"

    def can_retry(self):
        """Check if this notification can be retried."""
        return (
            self.status in ['failed', 'bounced'] and
            self.retry_count < self.max_retries and
            (self.next_retry_at is None or self.next_retry_at <= timezone.now())
        )

    def mark_as_sent(self, external_id=None):
        """Mark notification as sent."""
        self.status = 'sent'
        self.sent_at = timezone.now()
        if external_id:
            self.external_id = external_id
        self.save()

    def mark_as_delivered(self):
        """Mark notification as delivered."""
        self.status = 'delivered'
        self.delivered_at = timezone.now()
        self.save()

    def mark_as_failed(self, error_message=None):
        """Mark notification as failed."""
        self.status = 'failed'
        if error_message:
            self.error_message = error_message
        self.retry_count += 1

        # Schedule next retry with exponential backoff
        if self.retry_count < self.max_retries:
            delay_minutes = 2 ** self.retry_count  # 2, 4, 8 minutes
            self.next_retry_at = timezone.now() + timezone.timedelta(minutes=delay_minutes)

        self.save()

    def mark_as_bounced(self, error_message=None):
        """Mark notification as bounced (permanent failure)."""
        self.status = 'bounced'
        if error_message:
            self.error_message = error_message
        self.save()


class NotificationSettings(models.Model):
    """
    Global notification settings and configurations.
    """

    # Service configurations
    twilio_account_sid = models.CharField(
        max_length=100,
        blank=True,
        help_text='Twilio Account SID'
    )

    twilio_auth_token = models.CharField(
        max_length=100,
        blank=True,
        help_text='Twilio Auth Token'
    )

    twilio_phone_number = models.CharField(
        max_length=20,
        blank=True,
        help_text='Twilio phone number for sending SMS'
    )

    sendgrid_api_key = models.CharField(
        max_length=200,
        blank=True,
        help_text='SendGrid API Key'
    )

    sendgrid_from_email = models.EmailField(
        blank=True,
        help_text='Default from email address for SendGrid'
    )

    sendgrid_from_name = models.CharField(
        max_length=100,
        blank=True,
        help_text='Default from name for SendGrid'
    )

    # Global settings
    enable_sms_notifications = models.BooleanField(
        default=True,
        help_text='Enable SMS notifications globally'
    )

    enable_email_notifications = models.BooleanField(
        default=True,
        help_text='Enable email notifications globally'
    )

    default_timezone = models.CharField(
        max_length=50,
        default='America/New_York',
        help_text='Default timezone for scheduling notifications'
    )

    # Business information for templates
    company_name = models.CharField(
        max_length=100,
        default='Roofing Platform',
        help_text='Company name used in notification templates'
    )

    company_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text='Company phone number for notifications'
    )

    company_website = models.URLField(
        blank=True,
        help_text='Company website URL'
    )

    # Feature toggles
    enable_appointment_reminders = models.BooleanField(
        default=True,
        help_text='Enable automatic appointment reminders'
    )

    reminder_hours_before = models.PositiveIntegerField(
        default=24,
        help_text='Send appointment reminders this many hours before'
    )

    enable_job_status_notifications = models.BooleanField(
        default=True,
        help_text='Enable automatic job status notifications'
    )

    enable_technician_notifications = models.BooleanField(
        default=True,
        help_text='Enable notifications to technicians'
    )

    # Maintenance settings
    cleanup_old_logs_days = models.PositiveIntegerField(
        default=90,
        help_text='Delete notification logs older than this many days'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Notification Settings'
        verbose_name_plural = 'Notification Settings'

    def __str__(self):
        return "Global Notification Settings"

    @classmethod
    def get_settings(cls):
        """Get the global notification settings (singleton pattern)."""
        settings_obj, created = cls.objects.get_or_create(
            defaults={
                'company_name': 'Roofing Platform',
                'default_timezone': 'America/New_York',
            }
        )
        return settings_obj
