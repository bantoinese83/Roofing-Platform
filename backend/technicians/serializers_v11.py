from rest_framework import serializers
from .models import TechnicianProfile, TimeOffRequest, TechnicianSchedule


# Version 1.1 Serializers
class TechnicianAvailabilitySerializer(serializers.ModelSerializer):
    """Serializer for technician availability management"""

    class Meta:
        model = TechnicianProfile
        fields = [
            'id', 'user', 'timezone', 'working_days', 'default_start_time',
            'default_end_time', 'break_duration_minutes', 'is_available'
        ]
        read_only_fields = ['id', 'user']


class TimeOffRequestSerializer(serializers.ModelSerializer):
    """Serializer for time-off requests"""

    technician_name = serializers.CharField(source='technician.full_name', read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    duration_days = serializers.ReadOnlyField()
    conflicts_with_jobs = serializers.ReadOnlyField()

    class Meta:
        model = TimeOffRequest
        fields = [
            'id', 'technician', 'technician_name', 'request_type', 'start_date', 'end_date',
            'start_time', 'end_time', 'reason', 'status', 'requested_by', 'requested_by_name',
            'approved_by', 'approved_by_name', 'approval_notes', 'duration_days',
            'conflicts_with_jobs', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'technician_name', 'requested_by_name', 'approved_by_name',
            'duration_days', 'conflicts_with_jobs', 'created_at', 'updated_at'
        ]

    def create(self, validated_data):
        """Set requested_by to current user"""
        validated_data['requested_by'] = self.context['request'].user
        return super().create(validated_data)


class TimeOffRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating time-off requests"""

    class Meta:
        model = TimeOffRequest
        fields = [
            'request_type', 'start_date', 'end_date', 'start_time', 'end_time', 'reason'
        ]


class TechnicianScheduleSerializer(serializers.ModelSerializer):
    """Serializer for technician schedule overrides"""

    technician_name = serializers.CharField(source='technician.full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = TechnicianSchedule
        fields = [
            'id', 'technician', 'technician_name', 'schedule_type', 'title',
            'start_date', 'end_date', 'start_time', 'end_time', 'is_all_day',
            'notes', 'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'technician_name', 'created_by_name', 'created_at', 'updated_at'
        ]

    def create(self, validated_data):
        """Set created_by to current user"""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)
