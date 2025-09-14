from rest_framework import serializers
from django.utils import timezone
from .models import Job, JobPhoto, JobDocument, JobStatusUpdate
from customers.serializers import CustomerListSerializer
from technicians.serializers import CrewSerializer, TechnicianProfileSerializer


class JobPhotoSerializer(serializers.ModelSerializer):
    """
    Serializer for JobPhoto model.
    """
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = JobPhoto
        fields = [
            'id', 'job', 'image', 'image_url', 'photo_type', 'caption',
            'uploaded_by', 'uploaded_by_name', 'uploaded_at',
            'latitude', 'longitude'
        ]
        read_only_fields = ['id', 'uploaded_by', 'uploaded_at']

    def get_image_url(self, obj):
        """Get the full URL for the image"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class JobDocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for JobDocument model.
    """
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    document_url = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()

    class Meta:
        model = JobDocument
        fields = [
            'id', 'job', 'document', 'document_url', 'document_type', 'title',
            'description', 'uploaded_by', 'uploaded_by_name', 'uploaded_at', 'file_size'
        ]
        read_only_fields = ['id', 'uploaded_by', 'uploaded_at', 'file_size']

    def get_document_url(self, obj):
        """Get the full URL for the document"""
        if obj.document:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.document.url)
            return obj.document.url
        return None

    def get_file_size(self, obj):
        """Get human-readable file size"""
        if obj.document and obj.document.size:
            size = obj.document.size
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return ".1f"
                size /= 1024.0
            return ".1f"
        return "Unknown"


class JobStatusUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for JobStatusUpdate model.
    """
    updated_by_name = serializers.CharField(source='updated_by.get_full_name', read_only=True)

    class Meta:
        model = JobStatusUpdate
        fields = [
            'id', 'job', 'old_status', 'new_status', 'notes',
            'updated_by', 'updated_by_name', 'updated_at',
            'latitude', 'longitude'
        ]
        read_only_fields = ['id', 'updated_by', 'updated_at']


class JobListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for job lists and calendar views.
    """
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    assigned_crew_name = serializers.CharField(source='assigned_crew.name', read_only=True)
    duration_display = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    status_color = serializers.SerializerMethodField()
    priority_color = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            'id', 'job_number', 'title', 'status', 'priority', 'scheduled_date',
            'scheduled_time', 'estimated_duration_hours', 'duration_display',
            'customer', 'customer_name', 'customer_email', 'assigned_crew',
            'assigned_crew_name', 'address', 'latitude', 'longitude',
            'is_overdue', 'status_color', 'priority_color', 'created_at'
        ]
        read_only_fields = ['id', 'job_number', 'duration_display', 'is_overdue', 'status_color', 'priority_color', 'created_at']

    def get_status_color(self, obj):
        return obj.get_status_color()

    def get_priority_color(self, obj):
        return obj.get_priority_color()


class JobDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for individual job view.
    """
    customer = CustomerListSerializer(read_only=True)
    assigned_crew = CrewSerializer(read_only=True)
    assigned_technicians = TechnicianProfileSerializer(many=True, read_only=True)
    photos = JobPhotoSerializer(many=True, read_only=True, context={'request': None})
    documents = JobDocumentSerializer(many=True, read_only=True, context={'request': None})
    status_updates = JobStatusUpdateSerializer(many=True, read_only=True)
    duration_display = serializers.ReadOnlyField()
    actual_duration = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    status_color = serializers.SerializerMethodField()
    priority_color = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            'id', 'job_number', 'title', 'description', 'job_type', 'status', 'priority',
            'scheduled_date', 'scheduled_time', 'estimated_duration_hours', 'duration_display',
            'actual_start_time', 'actual_end_time', 'actual_duration',
            'customer', 'assigned_crew', 'assigned_technicians',
            'address', 'latitude', 'longitude',
            'required_materials', 'special_instructions', 'customer_notes', 'internal_notes',
            'estimated_cost', 'actual_cost', 'progress_percentage',
            'quality_rating', 'customer_feedback',
            'photos', 'documents', 'status_updates',
            'is_overdue', 'status_color', 'priority_color',
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'job_number', 'actual_duration', 'duration_display', 'is_overdue',
            'status_color', 'priority_color', 'photos', 'documents', 'status_updates',
            'created_at', 'updated_at'
        ]

    def get_status_color(self, obj):
        return obj.get_status_color()

    def get_priority_color(self, obj):
        return obj.get_priority_color()


class JobCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new jobs.
    """
    class Meta:
        model = Job
        fields = [
            'title', 'description', 'job_type', 'priority', 'scheduled_date', 'scheduled_time',
            'estimated_duration_hours', 'customer', 'assigned_crew', 'assigned_technicians',
            'address', 'required_materials', 'special_instructions', 'customer_notes',
            'internal_notes', 'estimated_cost'
        ]

    def create(self, validated_data):
        # Set created_by to current user
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

    def validate(self, data):
        """Validate job data and check for conflicts"""
        # Check if assigned crew is available on the scheduled date
        assigned_crew = data.get('assigned_crew')
        scheduled_date = data.get('scheduled_date')

        if assigned_crew and scheduled_date:
            # Check if crew already has jobs on this date
            existing_jobs = Job.objects.filter(
                assigned_crew=assigned_crew,
                scheduled_date=scheduled_date,
                status__in=['scheduled', 'dispatched', 'in_progress']
            ).exclude(pk=getattr(self.instance, 'pk', None))

            if existing_jobs.exists():
                raise serializers.ValidationError({
                    'assigned_crew': f'Crew "{assigned_crew.name}" is already assigned to jobs on {scheduled_date}.'
                })

        return data


class JobUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating jobs with conflict detection.
    """
    class Meta:
        model = Job
        fields = [
            'title', 'description', 'job_type', 'status', 'priority', 'scheduled_date', 'scheduled_time',
            'estimated_duration_hours', 'assigned_crew', 'assigned_technicians',
            'address', 'latitude', 'longitude', 'required_materials', 'special_instructions',
            'customer_notes', 'internal_notes', 'estimated_cost', 'actual_cost',
            'progress_percentage', 'quality_rating', 'customer_feedback'
        ]

    def update(self, instance, validated_data):
        # Track status changes
        old_status = instance.status
        new_status = validated_data.get('status', old_status)

        if old_status != new_status:
            # Create status update record
            JobStatusUpdate.objects.create(
                job=instance,
                old_status=old_status,
                new_status=new_status,
                notes=validated_data.get('notes', ''),
                updated_by=self.context['request'].user
            )

        # Handle status-specific updates
        if new_status == 'in_progress' and not instance.actual_start_time:
            validated_data['actual_start_time'] = timezone.now()
        elif new_status == 'completed' and not instance.actual_end_time:
            validated_data['actual_end_time'] = timezone.now()

        return super().update(instance, validated_data)

    def validate(self, data):
        """Validate job data and check for conflicts"""
        instance = self.instance
        assigned_crew = data.get('assigned_crew', instance.assigned_crew if instance else None)
        scheduled_date = data.get('scheduled_date', instance.scheduled_date if instance else None)

        if assigned_crew and scheduled_date:
            # Check if crew already has jobs on this date
            existing_jobs = Job.objects.filter(
                assigned_crew=assigned_crew,
                scheduled_date=scheduled_date,
                status__in=['scheduled', 'dispatched', 'in_progress']
            ).exclude(pk=instance.pk if instance else None)

            if existing_jobs.exists():
                raise serializers.ValidationError({
                    'assigned_crew': f'Crew "{assigned_crew.name}" is already assigned to jobs on {scheduled_date}.'
                })

        return data


class JobCalendarSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for calendar views.
    """
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    crew_name = serializers.CharField(source='assigned_crew.name', read_only=True)
    duration_display = serializers.ReadOnlyField()

    class Meta:
        model = Job
        fields = [
            'id', 'job_number', 'title', 'status', 'priority', 'scheduled_date',
            'scheduled_time', 'estimated_duration_hours', 'duration_display',
            'customer_name', 'crew_name', 'address'
        ]


class JobConflictSerializer(serializers.Serializer):
    """
    Serializer for job conflict detection.
    """
    job_id = serializers.IntegerField()
    job_number = serializers.CharField()
    title = serializers.CharField()
    conflict_type = serializers.CharField()
    conflict_message = serializers.CharField()
    severity = serializers.ChoiceField(choices=[('warning', 'Warning'), ('error', 'Error')])
