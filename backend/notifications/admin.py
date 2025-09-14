from django.contrib import admin
from .models import NotificationTemplate, NotificationLog, NotificationSettings


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    """
    Admin for NotificationTemplate model.
    """
    list_display = [
        'name', 'template_type', 'notification_method', 'is_active',
        'send_to_customer', 'send_to_technician', 'created_by', 'created_at'
    ]
    list_filter = [
        'template_type', 'notification_method', 'is_active',
        'send_to_customer', 'send_to_technician', 'send_to_office',
        'trigger_on_job_create', 'trigger_on_job_update', 'trigger_on_status_change',
        'created_at'
    ]
    search_fields = ['name', 'subject', 'content', 'created_by__username']
    ordering = ['template_type', 'notification_method', 'name']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'template_type', 'notification_method', 'is_active')
        }),
        ('Content', {
            'fields': ('subject', 'content')
        }),
        ('Timing', {
            'fields': ('send_before_hours',)
        }),
        ('Recipients', {
            'fields': ('send_to_customer', 'send_to_technician', 'send_to_office')
        }),
        ('Triggers', {
            'fields': ('trigger_on_job_create', 'trigger_on_job_update', 'trigger_on_status_change', 'trigger_statuses')
        }),
        ('Metadata', {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at', 'created_by']

    def save_model(self, request, obj, form, change):
        """Set created_by when creating new templates"""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    """
    Admin for NotificationLog model.
    """
    list_display = [
        'id', 'notification_type', 'recipient_info', 'template_name',
        'status', 'sent_at', 'created_at'
    ]
    list_filter = [
        'notification_type', 'status', 'created_at', 'sent_at',
        'template__template_type', 'template__notification_method'
    ]
    search_fields = [
        'recipient_email', 'recipient_phone', 'subject', 'content',
        'job__job_number', 'customer__email', 'technician__user__email'
    ]
    ordering = ['-created_at']
    readonly_fields = [
        'id', 'sent_at', 'delivered_at', 'external_id', 'error_message',
        'retry_count', 'next_retry_at', 'created_at', 'updated_at'
    ]

    fieldsets = (
        ('Notification Details', {
            'fields': ('notification_type', 'template', 'subject', 'content')
        }),
        ('Recipients', {
            'fields': ('recipient_email', 'recipient_phone', 'job', 'customer', 'technician')
        }),
        ('Status & Delivery', {
            'fields': ('status', 'sent_at', 'delivered_at', 'external_id')
        }),
        ('Error Handling', {
            'fields': ('error_message', 'retry_count', 'max_retries', 'next_retry_at'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def recipient_info(self, obj):
        """Display recipient information"""
        if obj.recipient_email:
            return obj.recipient_email
        elif obj.recipient_phone:
            return obj.recipient_phone
        return 'N/A'
    recipient_info.short_description = 'Recipient'

    def template_name(self, obj):
        """Display template name"""
        return obj.template.name if obj.template else 'N/A'
    template_name.short_description = 'Template'

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of notification logs"""
        return False


@admin.register(NotificationSettings)
class NotificationSettingsAdmin(admin.ModelAdmin):
    """
    Admin for NotificationSettings model (singleton).
    """

    def has_add_permission(self, request):
        """Prevent adding multiple settings instances"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of settings"""
        return False

    fieldsets = (
        ('Service Configurations', {
            'fields': ('twilio_account_sid', 'twilio_auth_token', 'twilio_phone_number'),
            'classes': ('collapse',)
        }),
        ('Email Configuration', {
            'fields': ('sendgrid_api_key', 'sendgrid_from_email', 'sendgrid_from_name'),
            'classes': ('collapse',)
        }),
        ('Global Settings', {
            'fields': ('enable_sms_notifications', 'enable_email_notifications', 'default_timezone')
        }),
        ('Business Information', {
            'fields': ('company_name', 'company_phone', 'company_website')
        }),
        ('Notification Preferences', {
            'fields': ('enable_appointment_reminders', 'reminder_hours_before',
                      'enable_job_status_notifications', 'enable_technician_notifications')
        }),
        ('Maintenance', {
            'fields': ('cleanup_old_logs_days',),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at']

    def get_queryset(self, request):
        """Always return the singleton instance"""
        qs = super().get_queryset(request)
        # This will create the instance if it doesn't exist
        NotificationSettings.get_settings()
        return qs
