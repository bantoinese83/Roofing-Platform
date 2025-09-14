from rest_framework import serializers
from django.utils import timezone
from .models import JobSchedule, CalendarEvent, SchedulingSettings


class JobScheduleSerializer(serializers.ModelSerializer):
    """
    Serializer for JobSchedule model with related job information.
    """

    # Related fields
    job_number = serializers.CharField(source='job.job_number', read_only=True)
    title = serializers.CharField(source='job.title', read_only=True)
    customer_name = serializers.CharField(source='job.customer.full_name', read_only=True)
    crew_name = serializers.CharField(source='assigned_crew.name', read_only=True)
    address = serializers.CharField(source='job.address', read_only=True)

    # Computed fields
    duration_display = serializers.CharField(read_only=True)
    status_color = serializers.CharField(read_only=True)
    priority_color = serializers.CharField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = JobSchedule
        fields = [
            'id', 'job', 'job_number', 'title', 'customer_name', 'crew_name', 'address',
            'scheduled_date', 'scheduled_time', 'estimated_duration_hours',
            'actual_duration_hours', 'assigned_crew', 'assigned_technician',
            'status', 'priority', 'latitude', 'longitude',
            'scheduling_notes', 'customer_notes', 'scheduled_by',
            'scheduled_at', 'updated_at',
            # Computed fields
            'duration_display', 'status_color', 'priority_color', 'is_overdue'
        ]
        read_only_fields = ['scheduled_at', 'updated_at', 'scheduled_by']

    def create(self, validated_data):
        # Set the user who scheduled the job
        validated_data['scheduled_by'] = self.context['request'].user
        return super().create(validated_data)


class JobScheduleUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating job schedules (drag-and-drop functionality).
    """

    class Meta:
        model = JobSchedule
        fields = [
            'scheduled_date', 'scheduled_time', 'assigned_crew', 'assigned_technician',
            'status', 'priority', 'latitude', 'longitude', 'scheduling_notes'
        ]


class CalendarEventSerializer(serializers.ModelSerializer):
    """
    Serializer for CalendarEvent model.
    """

    assigned_to_names = serializers.SerializerMethodField()
    assigned_crews_names = serializers.SerializerMethodField()
    duration_days = serializers.IntegerField(read_only=True)

    class Meta:
        model = CalendarEvent
        fields = [
            'id', 'title', 'description', 'event_type',
            'start_date', 'start_time', 'end_date', 'end_time', 'is_all_day',
            'assigned_to', 'assigned_to_names', 'assigned_crews', 'assigned_crews_names',
            'location', 'latitude', 'longitude', 'created_by',
            'created_at', 'updated_at', 'duration_days'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by']

    def get_assigned_to_names(self, obj):
        """Get names of assigned technicians."""
        return [tech.full_name for tech in obj.assigned_to.all()]

    def get_assigned_crews_names(self, obj):
        """Get names of assigned crews."""
        return [crew.name for crew in obj.assigned_crews.all()]

    def create(self, validated_data):
        # Set the user who created the event
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class SchedulingSettingsSerializer(serializers.ModelSerializer):
    """
    Serializer for SchedulingSettings model.
    """

    class Meta:
        model = SchedulingSettings
        fields = [
            'id', 'default_job_duration_hours', 'working_hours_start', 'working_hours_end',
            'buffer_between_jobs_minutes', 'auto_schedule_new_jobs', 'auto_assign_crews',
            'notify_on_overdue_jobs', 'overdue_notification_hours',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class CalendarDataSerializer(serializers.Serializer):
    """
    Serializer for calendar data (jobs and events combined).
    """

    date = serializers.DateField()
    jobs = JobScheduleSerializer(many=True, read_only=True)
    events = CalendarEventSerializer(many=True, read_only=True)
