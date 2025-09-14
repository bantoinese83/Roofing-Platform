from rest_framework import serializers
from .models import NotificationTemplate, NotificationLog, NotificationSettings


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for NotificationTemplate model.
    """
    available_placeholders = serializers.ReadOnlyField()

    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'name', 'template_type', 'notification_method', 'subject',
            'content', 'is_active', 'send_before_hours', 'send_to_customer',
            'send_to_technician', 'send_to_office', 'trigger_on_job_create',
            'trigger_on_job_update', 'trigger_on_status_change', 'trigger_statuses',
            'available_placeholders', 'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'available_placeholders', 'created_by', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class NotificationTemplateTestSerializer(serializers.Serializer):
    """
    Serializer for testing notification templates.
    """
    template_id = serializers.IntegerField()
    test_data = serializers.JSONField(help_text='Test data for template rendering')
    recipient_email = serializers.EmailField(required=False)
    recipient_phone = serializers.CharField(max_length=20, required=False)


class NotificationLogSerializer(serializers.ModelSerializer):
    """
    Serializer for NotificationLog model.
    """
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    technician_name = serializers.CharField(source='technician.full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)

    class Meta:
        model = NotificationLog
        fields = [
            'id', 'job', 'customer', 'customer_name', 'technician', 'technician_name',
            'notification_type', 'template', 'template_name', 'recipient_email',
            'recipient_phone', 'subject', 'content', 'status', 'sent_at', 'delivered_at',
            'external_id', 'error_message', 'retry_count', 'max_retries',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'customer_name', 'technician_name', 'created_by_name',
            'template_name', 'sent_at', 'delivered_at', 'created_at', 'updated_at'
        ]


class NotificationStatsSerializer(serializers.Serializer):
    """
    Serializer for notification statistics.
    """
    total_sent = serializers.IntegerField()
    total_failed = serializers.IntegerField()
    total_pending = serializers.IntegerField()
    sms_sent_today = serializers.IntegerField()
    email_sent_today = serializers.IntegerField()
    delivery_rate = serializers.FloatField()
    failure_rate = serializers.FloatField()


class NotificationSettingsSerializer(serializers.ModelSerializer):
    """
    Serializer for NotificationSettings model.
    """

    class Meta:
        model = NotificationSettings
        fields = [
            'id', 'twilio_account_sid', 'twilio_auth_token', 'twilio_phone_number',
            'sendgrid_api_key', 'sendgrid_from_email', 'sendgrid_from_name',
            'enable_sms_notifications', 'enable_email_notifications', 'default_timezone',
            'company_name', 'company_phone', 'company_website',
            'enable_appointment_reminders', 'reminder_hours_before',
            'enable_job_status_notifications', 'enable_technician_notifications',
            'cleanup_old_logs_days', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, data):
        """Validate notification settings."""
        # Validate Twilio settings
        twilio_fields = ['twilio_account_sid', 'twilio_auth_token', 'twilio_phone_number']
        twilio_provided = any(data.get(field) for field in twilio_fields)
        twilio_complete = all(data.get(field) for field in twilio_fields)

        if twilio_provided and not twilio_complete:
            raise serializers.ValidationError({
                'twilio': 'All Twilio fields (Account SID, Auth Token, Phone Number) must be provided together.'
            })

        # Validate SendGrid settings
        sendgrid_fields = ['sendgrid_api_key', 'sendgrid_from_email']
        sendgrid_provided = any(data.get(field) for field in sendgrid_fields)
        sendgrid_complete = all(data.get(field) for field in sendgrid_fields)

        if sendgrid_provided and not sendgrid_complete:
            raise serializers.ValidationError({
                'sendgrid': 'Both SendGrid API Key and From Email must be provided.'
            })

        return data


class BulkNotificationSerializer(serializers.Serializer):
    """
    Serializer for sending bulk notifications.
    """
    template_id = serializers.IntegerField()
    job_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text='List of job IDs to send notifications for'
    )
    customer_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text='List of customer IDs to send notifications for'
    )
    technician_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text='List of technician IDs to send notifications for'
    )
    custom_recipients = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text='Custom recipients with email/phone and context data'
    )
    context_overrides = serializers.JSONField(
        required=False,
        help_text='Additional context data to override defaults'
    )

    def validate(self, data):
        """Ensure at least one recipient type is provided."""
        recipient_fields = ['job_ids', 'customer_ids', 'technician_ids', 'custom_recipients']
        has_recipients = any(data.get(field) for field in recipient_fields)

        if not has_recipients:
            raise serializers.ValidationError(
                'At least one recipient type (jobs, customers, technicians, or custom recipients) must be provided.'
            )

        return data
