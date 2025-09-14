from typing import Dict, Any, List
from datetime import datetime, timedelta
from django.db.models import Count, Avg, Sum, Q, F, ExpressionWrapper, fields
from django.utils import timezone
from jobs.models import Job
from customers.models import Customer
from technicians.models import TechnicianProfile, TimeOffRequest
from notifications.models import NotificationLog
from .models import DashboardMetric


class ReportService:
    """
    Service for generating various reports and analytics.
    """

    def generate_report(self, report_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a report based on type and parameters.
        """
        report_methods = {
            'job_status': self._generate_job_status_report,
            'completion_rates': self._generate_completion_rates_report,
            'technician_performance': self._generate_technician_performance_report,
            'revenue_tracking': self._generate_revenue_tracking_report,
            'customer_satisfaction': self._generate_customer_satisfaction_report,
            'time_off_summary': self._generate_time_off_summary_report,
            'schedule_efficiency': self._generate_schedule_efficiency_report,
        }

        if report_type not in report_methods:
            raise ValueError(f"Unknown report type: {report_type}")

        # Set default date range if not provided
        start_date = parameters.get('start_date')
        end_date = parameters.get('end_date')

        if not start_date:
            # Default to last 30 days
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=30)
            parameters['start_date'] = start_date
            parameters['end_date'] = end_date

        return report_methods[report_type](parameters)

    def _generate_job_status_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate job status distribution report"""
        start_date = parameters['start_date']
        end_date = parameters['end_date']

        jobs = Job.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )

        status_counts = jobs.values('status').annotate(
            count=Count('id')
        ).order_by('-count')

        total_jobs = jobs.count()

        # Calculate percentages
        for item in status_counts:
            item['percentage'] = round((item['count'] / total_jobs * 100), 1) if total_jobs > 0 else 0

        # Priority distribution
        priority_counts = jobs.values('priority').annotate(
            count=Count('id')
        ).order_by('-count')

        # Job type distribution
        job_type_counts = jobs.values('job_type').annotate(
            count=Count('id')
        ).order_by('-count')

        return {
            'title': 'Job Status Distribution Report',
            'date_range': f"{start_date} to {end_date}",
            'total_jobs': total_jobs,
            'status_distribution': list(status_counts),
            'priority_distribution': list(priority_counts),
            'job_type_distribution': list(job_type_counts),
            'generated_at': timezone.now(),
        }

    def _generate_completion_rates_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate job completion rates report"""
        start_date = parameters['start_date']
        end_date = parameters['end_date']

        # Get jobs created in the period
        jobs = Job.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )

        total_jobs = jobs.count()
        completed_jobs = jobs.filter(status='completed').count()
        completion_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0

        # Average completion time (for completed jobs)
        completed_jobs_queryset = jobs.filter(
            status='completed',
            actual_start_time__isnull=False,
            actual_end_time__isnull=False
        )

        avg_completion_time = None
        if completed_jobs_queryset.exists():
            durations = []
            for job in completed_jobs_queryset:
                if job.actual_start_time and job.actual_end_time:
                    duration = job.actual_end_time - job.actual_start_time
                    durations.append(duration.total_seconds() / 3600)  # Convert to hours

            if durations:
                avg_completion_time = sum(durations) / len(durations)

        # On-time completion rate (completed within estimated time)
        on_time_completions = 0
        for job in completed_jobs_queryset:
            if job.actual_start_time and job.actual_end_time and job.estimated_duration_hours:
                actual_duration = (job.actual_end_time - job.actual_start_time).total_seconds() / 3600
                if actual_duration <= job.estimated_duration_hours:
                    on_time_completions += 1

        on_time_rate = (on_time_completions / completed_jobs_queryset.count() * 100) if completed_jobs_queryset.count() > 0 else 0

        # Weekly completion trends
        weekly_data = []
        current_date = start_date
        while current_date <= end_date:
            week_end = min(current_date + timedelta(days=6), end_date)
            week_jobs = jobs.filter(
                created_at__date__gte=current_date,
                created_at__date__lte=week_end
            )
            week_completed = week_jobs.filter(status='completed').count()

            weekly_data.append({
                'week': f"{current_date} - {week_end}",
                'total': week_jobs.count(),
                'completed': week_completed,
                'rate': round((week_completed / week_jobs.count() * 100), 1) if week_jobs.count() > 0 else 0
            })

            current_date = week_end + timedelta(days=1)

        return {
            'title': 'Job Completion Rates Report',
            'date_range': f"{start_date} to {end_date}",
            'overall_completion_rate': round(completion_rate, 1),
            'average_completion_time_hours': round(avg_completion_time, 1) if avg_completion_time else None,
            'on_time_completion_rate': round(on_time_rate, 1),
            'weekly_trends': weekly_data,
            'generated_at': timezone.now(),
        }

    def _generate_technician_performance_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate technician performance report"""
        start_date = parameters['start_date']
        end_date = parameters['end_date']

        # Get all technicians
        technicians = TechnicianProfile.objects.select_related('user')

        technician_data = []
        for tech in technicians:
            # Jobs assigned to this technician
            tech_jobs = Job.objects.filter(
                Q(assigned_technicians=tech) | Q(assigned_crew__members=tech),
                scheduled_date__gte=start_date,
                scheduled_date__lte=end_date
            ).distinct()

            completed_jobs = tech_jobs.filter(status='completed').count()
            total_jobs = tech_jobs.count()

            completion_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0

            # Average job duration
            completed_tech_jobs = tech_jobs.filter(
                status='completed',
                actual_start_time__isnull=False,
                actual_end_time__isnull=False
            )

            avg_duration = None
            if completed_tech_jobs.exists():
                durations = []
                for job in completed_tech_jobs:
                    if job.actual_start_time and job.actual_end_time:
                        duration = job.actual_end_time - job.actual_start_time
                        durations.append(duration.total_seconds() / 3600)
                if durations:
                    avg_duration = sum(durations) / len(durations)

            technician_data.append({
                'technician_id': tech.id,
                'technician_name': tech.full_name,
                'total_jobs': total_jobs,
                'completed_jobs': completed_jobs,
                'completion_rate': round(completion_rate, 1),
                'average_job_duration_hours': round(avg_duration, 1) if avg_duration else None,
            })

        # Sort by completion rate (descending)
        technician_data.sort(key=lambda x: x['completion_rate'], reverse=True)

        return {
            'title': 'Technician Performance Report',
            'date_range': f"{start_date} to {end_date}",
            'technician_performance': technician_data,
            'generated_at': timezone.now(),
        }

    def _generate_revenue_tracking_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate revenue tracking report"""
        start_date = parameters['start_date']
        end_date = parameters['end_date']

        jobs = Job.objects.filter(
            status='completed',
            updated_at__date__gte=start_date,
            updated_at__date__lte=end_date
        )

        total_revenue = jobs.aggregate(
            total=Sum('actual_cost')
        )['total'] or 0

        estimated_revenue = jobs.aggregate(
            total=Sum('estimated_cost')
        )['total'] or 0

        # Revenue by job type
        revenue_by_type = jobs.values('job_type').annotate(
            revenue=Sum('actual_cost'),
            count=Count('id')
        ).order_by('-revenue')

        # Monthly revenue trend
        monthly_data = []
        current_date = start_date.replace(day=1)
        while current_date <= end_date:
            month_end = min(
                current_date.replace(day=28) + timedelta(days=4),
                end_date
            ).replace(day=1) - timedelta(days=1)

            month_jobs = jobs.filter(
                updated_at__date__gte=current_date,
                updated_at__date__lte=month_end
            )

            monthly_revenue = month_jobs.aggregate(
                total=Sum('actual_cost')
            )['total'] or 0

            monthly_data.append({
                'month': current_date.strftime('%Y-%m'),
                'revenue': float(monthly_revenue),
                'job_count': month_jobs.count(),
            })

            # Next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1, day=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1, day=1)

        return {
            'title': 'Revenue Tracking Report',
            'date_range': f"{start_date} to {end_date}",
            'total_actual_revenue': float(total_revenue),
            'total_estimated_revenue': float(estimated_revenue),
            'revenue_variance': float(total_revenue - estimated_revenue),
            'revenue_by_job_type': list(revenue_by_type),
            'monthly_trends': monthly_data,
            'generated_at': timezone.now(),
        }

    def _generate_customer_satisfaction_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate customer satisfaction report"""
        start_date = parameters['start_date']
        end_date = parameters['end_date']

        jobs = Job.objects.filter(
            status='completed',
            updated_at__date__gte=start_date,
            updated_at__date__lte=end_date
        ).select_related('customer')

        # Overall satisfaction
        rated_jobs = jobs.exclude(quality_rating__isnull=True)
        avg_rating = rated_jobs.aggregate(
            avg_rating=Avg('quality_rating')
        )['avg_rating'] or 0

        # Rating distribution
        rating_distribution = rated_jobs.values('quality_rating').annotate(
            count=Count('id')
        ).order_by('quality_rating')

        # Customer feedback summary
        feedback_jobs = jobs.exclude(customer_feedback='').exclude(customer_feedback__isnull=True)
        feedback_summary = []
        for job in feedback_jobs[:10]:  # Top 10 recent feedbacks
            feedback_summary.append({
                'customer': job.customer.get_full_name(),
                'job_number': job.job_number,
                'rating': job.quality_rating,
                'feedback': job.customer_feedback,
                'date': job.updated_at.date(),
            })

        return {
            'title': 'Customer Satisfaction Report',
            'date_range': f"{start_date} to {end_date}",
            'total_completed_jobs': jobs.count(),
            'jobs_with_ratings': rated_jobs.count(),
            'average_rating': round(float(avg_rating), 1),
            'rating_distribution': list(rating_distribution),
            'recent_feedback': feedback_summary,
            'generated_at': timezone.now(),
        }

    def _generate_time_off_summary_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate time-off summary report"""
        start_date = parameters['start_date']
        end_date = parameters['end_date']

        # Time-off requests in the period
        requests = TimeOffRequest.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).select_related('technician', 'approved_by', 'requested_by')

        total_requests = requests.count()
        approved_requests = requests.filter(status='approved').count()
        pending_requests = requests.filter(status='pending').count()
        denied_requests = requests.filter(status='denied').count()

        approval_rate = (approved_requests / total_requests * 100) if total_requests > 0 else 0

        # Requests by type
        requests_by_type = requests.values('request_type').annotate(
            count=Count('id'),
            approved=Count('id', filter=Q(status='approved'))
        ).order_by('-count')

        # Requests by technician
        requests_by_technician = requests.values(
            'technician__user__first_name',
            'technician__user__last_name'
        ).annotate(
            total_requests=Count('id'),
            approved_requests=Count('id', filter=Q(status='approved')),
            total_days=Sum('duration_days')
        ).order_by('-total_requests')

        # Format technician names
        for item in requests_by_technician:
            item['technician_name'] = f"{item['technician__user__first_name']} {item['technician__user__last_name']}"

        return {
            'title': 'Time Off Summary Report',
            'date_range': f"{start_date} to {end_date}",
            'total_requests': total_requests,
            'approved_requests': approved_requests,
            'pending_requests': pending_requests,
            'denied_requests': denied_requests,
            'approval_rate': round(approval_rate, 1),
            'requests_by_type': list(requests_by_type),
            'requests_by_technician': list(requests_by_technician),
            'generated_at': timezone.now(),
        }

    def _generate_schedule_efficiency_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate schedule efficiency report"""
        start_date = parameters['start_date']
        end_date = parameters['end_date']

        jobs = Job.objects.filter(
            scheduled_date__gte=start_date,
            scheduled_date__lte=end_date
        )

        total_scheduled_jobs = jobs.count()
        completed_on_time = jobs.filter(
            status='completed',
            scheduled_date__gte=timezone.now().date()  # Only past jobs
        ).count()

        # Technician utilization
        technicians = TechnicianProfile.objects.all()
        utilization_data = []

        for tech in technicians:
            tech_jobs = jobs.filter(
                Q(assigned_technicians=tech) | Q(assigned_crew__members=tech)
            ).distinct()

            scheduled_days = tech_jobs.values('scheduled_date').distinct().count()
            total_days = (end_date - start_date).days + 1

            utilization_rate = (scheduled_days / total_days * 100) if total_days > 0 else 0

            utilization_data.append({
                'technician_name': tech.full_name,
                'scheduled_jobs': tech_jobs.count(),
                'scheduled_days': scheduled_days,
                'total_days_in_period': total_days,
                'utilization_rate': round(utilization_rate, 1),
            })

        # Sort by utilization rate
        utilization_data.sort(key=lambda x: x['utilization_rate'], reverse=True)

        return {
            'title': 'Schedule Efficiency Report',
            'date_range': f"{start_date} to {end_date}",
            'total_scheduled_jobs': total_scheduled_jobs,
            'completed_on_time_jobs': completed_on_time,
            'technician_utilization': utilization_data,
            'generated_at': timezone.now(),
        }

    def update_dashboard_metrics(self):
        """Update all dashboard metrics with current data"""
        today = timezone.now().date()
        thirty_days_ago = today - timedelta(days=30)

        # Total Jobs
        total_jobs = Job.objects.count()
        self._update_metric('total_jobs', total_jobs)

        # Active Jobs
        active_jobs = Job.objects.filter(
            status__in=['scheduled', 'dispatched', 'in_progress']
        ).count()
        self._update_metric('active_jobs', active_jobs)

        # Completed Jobs (last 30 days)
        completed_jobs = Job.objects.filter(
            status='completed',
            updated_at__date__gte=thirty_days_ago
        ).count()
        self._update_metric('completed_jobs', completed_jobs)

        # Overdue Jobs
        overdue_jobs = Job.objects.filter(
            status__in=['scheduled', 'dispatched', 'in_progress'],
            scheduled_date__lt=today
        ).count()
        self._update_metric('overdue_jobs', overdue_jobs)

        # Available Technicians
        available_techs = TechnicianProfile.objects.filter(is_available=True).count()
        self._update_metric('available_technicians', available_techs)

        # Pending Time Off Requests
        pending_time_off = TimeOffRequest.objects.filter(status='pending').count()
        self._update_metric('pending_time_off', pending_time_off)

        # Jobs Scheduled Today
        today_jobs = Job.objects.filter(scheduled_date=today).count()
        self._update_metric('today_jobs', today_jobs)

        # Weekly Completion Rate
        week_ago = today - timedelta(days=7)
        weekly_jobs = Job.objects.filter(
            created_at__date__gte=week_ago,
            created_at__date__lte=today
        )
        weekly_completed = weekly_jobs.filter(status='completed').count()
        weekly_total = weekly_jobs.count()
        weekly_rate = (weekly_completed / weekly_total * 100) if weekly_total > 0 else 0
        self._update_metric('weekly_completion_rate', weekly_rate, '%')

        # Average Job Duration (completed jobs last 30 days)
        completed_jobs_queryset = Job.objects.filter(
            status='completed',
            updated_at__date__gte=thirty_days_ago,
            actual_start_time__isnull=False,
            actual_end_time__isnull=False
        )

        if completed_jobs_queryset.exists():
            durations = []
            for job in completed_jobs_queryset:
                duration = (job.actual_end_time - job.actual_start_time).total_seconds() / 3600
                durations.append(duration)

            avg_duration = sum(durations) / len(durations)
            self._update_metric('average_job_duration', avg_duration, 'hours')

        # Customer Satisfaction Score
        rated_jobs = Job.objects.filter(
            updated_at__date__gte=thirty_days_ago,
            quality_rating__isnull=False
        )
        if rated_jobs.exists():
            avg_rating = rated_jobs.aggregate(avg=Avg('quality_rating'))['avg']
            self._update_metric('customer_satisfaction', avg_rating, '/5')

    def _update_metric(self, metric_type: str, value: float, unit: str = ''):
        """Update a specific dashboard metric"""
        try:
            metric = DashboardMetric.objects.get(metric_type=metric_type)
            metric.update_value(value, unit)
        except DashboardMetric.DoesNotExist:
            # Create metric if it doesn't exist
            DashboardMetric.objects.create(
                name=metric.metric_type.replace('_', ' ').title(),
                metric_type=metric_type,
                value=value,
                unit=unit
            )
