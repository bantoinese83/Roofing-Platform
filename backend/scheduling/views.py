from django.shortcuts import get_object_or_404
from django.db.models import Q, Prefetch
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from datetime import datetime, timedelta

from .models import JobSchedule, CalendarEvent, SchedulingSettings
from .serializers import (
    JobScheduleSerializer, JobScheduleUpdateSerializer,
    CalendarEventSerializer, SchedulingSettingsSerializer,
    CalendarDataSerializer
)


class JobScheduleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing job schedules.
    """
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination

    def get_queryset(self):
        queryset = JobSchedule.objects.select_related(
            'job', 'job__customer', 'assigned_crew', 'assigned_technician', 'scheduled_by'
        ).prefetch_related(
            'job__job_items'
        )

        # Filter by date range if provided
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if start_date:
            queryset = queryset.filter(scheduled_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(scheduled_date__lte=end_date)

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by priority
        priority_filter = self.request.query_params.get('priority')
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)

        # Filter by crew
        crew_filter = self.request.query_params.get('crew')
        if crew_filter:
            queryset = queryset.filter(assigned_crew_id=crew_filter)

        # Filter by technician
        technician_filter = self.request.query_params.get('technician')
        if technician_filter:
            queryset = queryset.filter(assigned_technician_id=technician_filter)

        # Search by job number or customer name
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(job__job_number__icontains=search) |
                Q(job__customer__full_name__icontains=search) |
                Q(job__title__icontains=search)
            )

        return queryset.order_by('scheduled_date', 'scheduled_time')

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return JobScheduleUpdateSerializer
        return JobScheduleSerializer

    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get overdue scheduled jobs."""
        now = timezone.now()
        overdue_jobs = self.get_queryset().filter(
            Q(scheduled_date__lt=now.date()) |
            Q(scheduled_date=now.date(), scheduled_time__lt=now.time()),
            status__in=['scheduled', 'confirmed']
        )
        serializer = self.get_serializer(overdue_jobs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get jobs scheduled for today."""
        today = timezone.now().date()
        today_jobs = self.get_queryset().filter(scheduled_date=today)
        serializer = self.get_serializer(today_jobs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def week(self, request):
        """Get jobs scheduled for this week."""
        today = timezone.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        week_jobs = self.get_queryset().filter(
            scheduled_date__gte=start_of_week,
            scheduled_date__lte=end_of_week
        )
        serializer = self.get_serializer(week_jobs, many=True)
        return Response(serializer.data)


class CalendarEventViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing calendar events.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = CalendarEventSerializer
    pagination_class = PageNumberPagination

    def get_queryset(self):
        queryset = CalendarEvent.objects.select_related('created_by').prefetch_related(
            'assigned_to', 'assigned_crews'
        )

        # Filter by date range if provided
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if start_date:
            queryset = queryset.filter(start_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(start_date__lte=end_date)

        # Filter by event type
        event_type = self.request.query_params.get('event_type')
        if event_type:
            queryset = queryset.filter(event_type=event_type)

        # Search by title or description
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )

        return queryset.order_by('start_date', 'start_time')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class SchedulingSettingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing scheduling settings.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SchedulingSettingsSerializer

    def get_queryset(self):
        return SchedulingSettings.objects.all()

    def get_object(self):
        """Return the singleton settings object."""
        return SchedulingSettings.get_settings()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def calendar_data(request):
    """
    Get combined calendar data (jobs and events) for a specific date range.
    """
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')

    if not start_date or not end_date:
        return Response(
            {'error': 'start_date and end_date parameters are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        return Response(
            {'error': 'Invalid date format. Use YYYY-MM-DD'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Get all dates in the range
    current_date = start
    calendar_data = []

    while current_date <= end:
        # Get jobs for this date
        jobs = JobSchedule.objects.select_related(
            'job', 'job__customer', 'assigned_crew', 'assigned_technician'
        ).filter(scheduled_date=current_date)

        # Get events for this date
        events = CalendarEvent.objects.prefetch_related(
            'assigned_to', 'assigned_crews'
        ).filter(
            Q(start_date=current_date) |
            Q(start_date__lte=current_date, end_date__gte=current_date)
        )

        if jobs.exists() or events.exists():
            calendar_data.append({
                'date': current_date.isoformat(),
                'jobs': JobScheduleSerializer(jobs, many=True).data,
                'events': CalendarEventSerializer(events, many=True).data
            })

        current_date += timedelta(days=1)

    return Response(calendar_data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_schedule_update(request):
    """
    Bulk update job schedules (for drag-and-drop operations).
    """
    updates = request.data.get('updates', [])

    if not updates:
        return Response(
            {'error': 'No updates provided'},
            status=status.HTTP_400_BAD_REQUEST
        )

    updated_schedules = []
    errors = []

    for update_data in updates:
        schedule_id = update_data.get('id')
        if not schedule_id:
            errors.append({'error': 'Schedule ID is required'})
            continue

        try:
            schedule = JobSchedule.objects.get(id=schedule_id)
            serializer = JobScheduleUpdateSerializer(
                schedule, data=update_data, partial=True
            )

            if serializer.is_valid():
                serializer.save()
                updated_schedules.append(serializer.data)
            else:
                errors.append({
                    'id': schedule_id,
                    'errors': serializer.errors
                })
        except JobSchedule.DoesNotExist:
            errors.append({
                'id': schedule_id,
                'error': 'Schedule not found'
            })

    return Response({
        'updated': updated_schedules,
        'errors': errors
    })
