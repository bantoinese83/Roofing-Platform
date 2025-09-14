from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from .models import Job, JobPhoto, JobDocument
from .serializers import (
    JobListSerializer,
    JobDetailSerializer,
    JobCreateSerializer,
    JobUpdateSerializer,
    JobCalendarSerializer,
    JobPhotoSerializer,
    JobDocumentSerializer
)
from accounts.permissions import TechnicianAndAbove, ManagerAndAbove


class JobListCreateView(generics.ListCreateAPIView):
    """
    List all jobs or create a new job.
    """
    permission_classes = [TechnicianAndAbove]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return JobCreateSerializer
        return JobListSerializer

    def get_queryset(self):
        """Filter jobs based on user permissions"""
        queryset = Job.objects.select_related('customer', 'assigned_crew', 'created_by')

        # Search functionality
        search_query = self.request.query_params.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(job_number__icontains=search_query) |
                Q(title__icontains=search_query) |
                Q(customer__first_name__icontains=search_query) |
                Q(customer__last_name__icontains=search_query)
            )

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by('-scheduled_date', '-created_at')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class JobDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a job.
    """
    queryset = Job.objects.select_related('customer', 'assigned_crew', 'created_by')
    permission_classes = [TechnicianAndAbove]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return JobUpdateSerializer
        return JobDetailSerializer


class JobCalendarView(APIView):
    """
    API for calendar views - returns jobs in a date range.
    """
    permission_classes = [TechnicianAndAbove]

    def get(self, request):
        """Get jobs for calendar view"""
        start_date = request.query_params.get('start')
        end_date = request.query_params.get('end')

        if not start_date or not end_date:
            return Response(
                {'error': 'start and end dates are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        queryset = Job.objects.filter(
            scheduled_date__gte=start_date,
            scheduled_date__lte=end_date
        ).select_related('customer', 'assigned_crew')

        serializer = JobCalendarSerializer(queryset, many=True)
        return Response(serializer.data)


class JobPhotoListCreateView(generics.ListCreateAPIView):
    """
    List photos for a job or upload new photos.
    """
    serializer_class = JobPhotoSerializer
    permission_classes = [TechnicianAndAbove]

    def get_queryset(self):
        """Filter photos by job"""
        job_id = self.kwargs.get('job_id')
        return JobPhoto.objects.filter(job_id=job_id)

    def perform_create(self, serializer):
        """Set job and uploaded_by"""
        job_id = self.kwargs.get('job_id')
        job = get_object_or_404(Job, id=job_id)
        serializer.save(job=job, uploaded_by=self.request.user)


class JobDocumentListCreateView(generics.ListCreateAPIView):
    """
    List documents for a job or upload new documents.
    """
    serializer_class = JobDocumentSerializer
    permission_classes = [TechnicianAndAbove]

    def get_queryset(self):
        """Filter documents by job"""
        job_id = self.kwargs.get('job_id')
        return JobDocument.objects.filter(job_id=job_id)

    def perform_create(self, serializer):
        """Set job and uploaded_by"""
        job_id = self.kwargs.get('job_id')
        job = get_object_or_404(Job, id=job_id)
        serializer.save(job=job, uploaded_by=self.request.user)


class TechnicianJobsView(APIView):
    """
    Get jobs assigned to current technician (for mobile app).
    """
    permission_classes = [TechnicianAndAbove]

    def get(self, request):
        """Get technician's assigned jobs"""
        user = request.user

        if not user.is_technician:
            return Response({'error': 'Only technicians can access this endpoint'}, status=403)

        try:
            tech_profile = user.technician_profile
        except:
            return Response({'error': 'Technician profile not found'}, status=404)

        # Get today's jobs
        today = timezone.now().date()
        todays_jobs = Job.objects.filter(
            Q(assigned_crew__members=tech_profile) | Q(assigned_technicians=tech_profile),
            scheduled_date=today,
            status__in=['scheduled', 'dispatched', 'in_progress']
        ).distinct().select_related('customer', 'assigned_crew')

        return Response({
            'todays_jobs': JobListSerializer(todays_jobs, many=True).data
        })


class JobStatusUpdateView(APIView):
    """
    Update job status (for technicians).
    """
    permission_classes = [TechnicianAndAbove]

    def post(self, request, job_id):
        """Update job status"""
        job = get_object_or_404(Job, id=job_id)
        new_status = request.data.get('status')
        notes = request.data.get('notes', '')

        if not new_status:
            return Response({'error': 'Status is required'}, status=400)

        # Validate user can update this job
        user = request.user
        can_update = False

        if user.is_admin or user.is_manager or user.is_owner:
            can_update = True
        elif user.is_technician:
            try:
                tech_profile = user.technician_profile
                can_update = (
                    job.assigned_crew and tech_profile in job.assigned_crew.members.all()
                ) or (
                    tech_profile in job.assigned_technicians.all()
                )
            except:
                can_update = False

        if not can_update:
            return Response({'error': 'You do not have permission to update this job'}, status=403)

        # Update job status
        old_status = job.status
        job.status = new_status

        # Set timestamps based on status
        if new_status == 'in_progress' and not job.actual_start_time:
            job.actual_start_time = timezone.now()
        elif new_status == 'completed' and not job.actual_end_time:
            job.actual_end_time = timezone.now()

        job.save()

        return Response({'message': 'Job status updated successfully'})
