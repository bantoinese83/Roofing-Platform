from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db.models import Count, Avg, Sum, Q, F, ExpressionWrapper, fields, Case, When
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal
from .models import Report, ReportExecution, DashboardMetric
from .serializers import (
    ReportSerializer, ReportExecutionSerializer, DashboardMetricSerializer,
    DashboardDataSerializer, ChartDataSerializer
)
from accounts.permissions import ManagerAndAbove
from jobs.models import Job
from customers.models import Customer
from technicians.models import TechnicianProfile
from quotes.models import Quote
from inventory.models import InventoryItem, StockTransaction


class ReportViewSet(viewsets.ModelViewSet):
    """ViewSet for managing reports"""
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated, ManagerAndAbove]

    def get_queryset(self):
        return Report.objects.filter(is_active=True)

    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """Generate a report"""
        report = self.get_object()

        try:
            execution = ReportExecution.objects.create(
                report=report,
                executed_by=request.user
            )

            execution.start_execution(request.user)

            # Generate the report data
            data = report.generate_report_data()

            execution.complete_execution(data)

            return Response({
                'execution_id': execution.id,
                'data': data,
                'generated_at': execution.completed_at
            })

        except Exception as e:
            if 'execution' in locals():
                execution.fail_execution(str(e))
            return Response(
                {'error': f'Failed to generate report: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def executions(self, request, pk=None):
        """Get execution history for a report"""
        report = self.get_object()
        executions = report.executions.order_by('-created_at')

        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        start = (page - 1) * page_size
        end = start + page_size

        serializer = ReportExecutionSerializer(executions[start:end], many=True)
        return Response({
            'executions': serializer.data,
            'total': executions.count(),
            'page': page,
            'page_size': page_size
        })


class ReportExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing report executions"""
    queryset = ReportExecution.objects.all()
    serializer_class = ReportExecutionSerializer
    permission_classes = [IsAuthenticated, ManagerAndAbove]

    def get_queryset(self):
        queryset = ReportExecution.objects.select_related('report', 'executed_by')

        # Filter by report
        report = self.request.query_params.get('report', None)
        if report:
            queryset = queryset.filter(report_id=report)

        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset


class DashboardMetricViewSet(viewsets.ModelViewSet):
    """ViewSet for managing dashboard metrics"""
    queryset = DashboardMetric.objects.all()
    serializer_class = DashboardMetricSerializer
    permission_classes = [IsAuthenticated, ManagerAndAbove]

    def get_queryset(self):
        return DashboardMetric.objects.filter(is_active=True)

    @action(detail=False, methods=['post'])
    def refresh_all(self, request):
        """Refresh all dashboard metrics"""
        try:
            from .services import ReportService
            service = ReportService()
            service.update_dashboard_metrics()

            return Response({'message': 'Dashboard metrics refreshed successfully'})
        except Exception as e:
            return Response(
                {'error': f'Failed to refresh metrics: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AnalyticsViewSet(viewsets.ViewSet):
    """ViewSet for advanced analytics"""
    permission_classes = [IsAuthenticated, ManagerAndAbove]

    @action(detail=False, methods=['get'])
    def performance_overview(self, request):
        """Get comprehensive performance overview"""
        # Date range
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        # Job performance
        jobs = Job.objects.filter(created_at__date__gte=start_date)
        total_jobs = jobs.count()
        completed_jobs = jobs.filter(status='completed').count()
        completion_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0

        # Revenue metrics
        completed_jobs_queryset = jobs.filter(status='completed')
        total_revenue = completed_jobs_queryset.aggregate(
            total=Sum('actual_cost')
        )['total'] or 0

        # Customer metrics
        new_customers = Customer.objects.filter(
            created_at__date__gte=start_date
        ).count()

        # Technician utilization
        technicians = TechnicianProfile.objects.all()
        total_technicians = technicians.count()
        active_technicians = technicians.filter(is_available=True).count()
        utilization_rate = (active_technicians / total_technicians * 100) if total_technicians > 0 else 0

        return Response({
            'period': f"{start_date} to {end_date}",
            'job_performance': {
                'total_jobs': total_jobs,
                'completed_jobs': completed_jobs,
                'completion_rate': round(completion_rate, 1),
            },
            'revenue': {
                'total_revenue': float(total_revenue),
                'average_job_value': float(total_revenue / completed_jobs) if completed_jobs > 0 else 0,
            },
            'customers': {
                'new_customers': new_customers,
            },
            'technicians': {
                'total_technicians': total_technicians,
                'active_technicians': active_technicians,
                'utilization_rate': round(utilization_rate, 1),
            }
        })

    @action(detail=False, methods=['get'])
    def trend_analysis(self, request):
        """Get trend analysis data"""
        days = int(request.query_params.get('days', 90))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        # Daily job completion trends
        daily_data = []
        current_date = start_date
        while current_date <= end_date:
            jobs_completed = Job.objects.filter(
                status='completed',
                updated_at__date=current_date
            ).count()

            revenue = Job.objects.filter(
                status='completed',
                updated_at__date=current_date
            ).aggregate(total=Sum('actual_cost'))['total'] or 0

            daily_data.append({
                'date': current_date.isoformat(),
                'jobs_completed': jobs_completed,
                'revenue': float(revenue),
            })
            current_date += timedelta(days=1)

        # Weekly trends
        weekly_data = []
        current_week = start_date
        while current_week <= end_date:
            week_end = min(current_week + timedelta(days=6), end_date)
            week_jobs = Job.objects.filter(
                status='completed',
                updated_at__date__gte=current_week,
                updated_at__date__lte=week_end
            )
            week_revenue = week_jobs.aggregate(total=Sum('actual_cost'))['total'] or 0

            weekly_data.append({
                'week': f"{current_week} - {week_end}",
                'jobs_completed': week_jobs.count(),
                'revenue': float(week_revenue),
            })
            current_week = week_end + timedelta(days=1)

        return Response({
            'daily_trends': daily_data,
            'weekly_trends': weekly_data,
            'period': f"{start_date} to {end_date}",
        })


class DashboardView(APIView):
    """API view for dashboard data"""
    permission_classes = [IsAuthenticated, ManagerAndAbove]

    def get(self, request):
        """Get dashboard data"""
        # Get all active metrics
        metrics = DashboardMetric.objects.filter(is_active=True)
        metrics_data = DashboardMetricSerializer(metrics, many=True).data

        # Get recent activities
        recent_jobs = Job.objects.select_related('customer').order_by('-updated_at')[:5]
        recent_quotes = Quote.objects.select_related('customer').order_by('-updated_at')[:5]

        # Get alerts/warnings
        alerts = []

        # Overdue jobs
        overdue_jobs = Job.objects.filter(
            status__in=['scheduled', 'dispatched', 'in_progress'],
            scheduled_date__lt=timezone.now().date()
        ).count()
        if overdue_jobs > 0:
            alerts.append({
                'type': 'warning',
                'message': f"{overdue_jobs} jobs are overdue",
                'count': overdue_jobs
            })

        # Low stock items
        low_stock_items = InventoryItem.objects.filter(
            current_stock__lte=F('reorder_point'),
            current_stock__gt=0,
            is_active=True
        ).count()
        if low_stock_items > 0:
            alerts.append({
                'type': 'warning',
                'message': f"{low_stock_items} items are low on stock",
                'count': low_stock_items
            })

        # Expiring quotes
        expiring_quotes = Quote.objects.filter(
            status__in=['sent', 'viewed'],
            valid_until__lte=timezone.now().date() + timedelta(days=7),
            valid_until__gte=timezone.now().date()
        ).count()
        if expiring_quotes > 0:
            alerts.append({
                'type': 'info',
                'message': f"{expiring_quotes} quotes are expiring soon",
                'count': expiring_quotes
            })

        return Response({
            'metrics': metrics_data,
            'recent_jobs': [
                {
                    'id': job.id,
                    'job_number': job.job_number,
                    'customer_name': job.customer.get_full_name(),
                    'status': job.status,
                    'scheduled_date': job.scheduled_date,
                    'updated_at': job.updated_at,
                } for job in recent_jobs
            ],
            'recent_quotes': [
                {
                    'id': quote.id,
                    'quote_number': quote.quote_number,
                    'customer_name': quote.customer.get_full_name(),
                    'status': quote.status,
                    'total_amount': float(quote.total_amount),
                    'updated_at': quote.updated_at,
                } for quote in recent_quotes
            ],
            'alerts': alerts,
            'last_updated': timezone.now(),
        })


class ChartsView(APIView):
    """API view for chart data"""
    permission_classes = [IsAuthenticated, ManagerAndAbove]

    def get(self, request):
        """Get chart data"""
        chart_type = request.query_params.get('type', 'job_status')
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        if chart_type == 'job_status':
            return self._get_job_status_chart(start_date, end_date)
        elif chart_type == 'revenue_trends':
            return self._get_revenue_trends_chart(start_date, end_date)
        elif chart_type == 'technician_performance':
            return self._get_technician_performance_chart(start_date, end_date)
        elif chart_type == 'quote_conversion':
            return self._get_quote_conversion_chart(start_date, end_date)
        elif chart_type == 'inventory_status':
            return self._get_inventory_status_chart()
        else:
            return Response(
                {'error': f'Unknown chart type: {chart_type}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    def _get_job_status_chart(self, start_date, end_date):
        """Get job status distribution chart data"""
        jobs = Job.objects.filter(created_at__date__gte=start_date)

        status_counts = jobs.values('status').annotate(
            count=Count('id')
        ).order_by('-count')

        return Response({
            'title': 'Job Status Distribution',
            'type': 'pie',
            'data': [
                {
                    'label': item['status'].replace('_', ' ').title(),
                    'value': item['count'],
                    'percentage': round((item['count'] / jobs.count() * 100), 1) if jobs.count() > 0 else 0
                } for item in status_counts
            ],
            'period': f"{start_date} to {end_date}",
        })

    def _get_revenue_trends_chart(self, start_date, end_date):
        """Get revenue trends chart data"""
        # Monthly revenue data
        monthly_data = Job.objects.filter(
            status='completed',
            updated_at__date__gte=start_date,
            updated_at__date__lte=end_date
        ).annotate(
            month=TruncMonth('updated_at')
        ).values('month').annotate(
            revenue=Sum('actual_cost'),
            job_count=Count('id')
        ).order_by('month')

        return Response({
            'title': 'Monthly Revenue Trends',
            'type': 'line',
            'data': [
                {
                    'month': item['month'].strftime('%Y-%m'),
                    'revenue': float(item['revenue'] or 0),
                    'job_count': item['job_count']
                } for item in monthly_data
            ],
            'period': f"{start_date} to {end_date}",
        })

    def _get_technician_performance_chart(self, start_date, end_date):
        """Get technician performance chart data"""
        technicians = TechnicianProfile.objects.all()

        performance_data = []
        for tech in technicians:
            tech_jobs = Job.objects.filter(
                Q(assigned_technicians=tech) | Q(assigned_crew__members=tech),
                scheduled_date__gte=start_date,
                scheduled_date__lte=end_date
            ).distinct()

            completed_jobs = tech_jobs.filter(status='completed').count()
            total_jobs = tech_jobs.count()

            if total_jobs > 0:
                performance_data.append({
                    'technician': tech.full_name,
                    'total_jobs': total_jobs,
                    'completed_jobs': completed_jobs,
                    'completion_rate': round((completed_jobs / total_jobs * 100), 1)
                })

        # Sort by completion rate
        performance_data.sort(key=lambda x: x['completion_rate'], reverse=True)

        return Response({
            'title': 'Technician Performance',
            'type': 'bar',
            'data': performance_data,
            'period': f"{start_date} to {end_date}",
        })

    def _get_quote_conversion_chart(self, start_date, end_date):
        """Get quote conversion chart data"""
        quotes = Quote.objects.filter(created_at__date__gte=start_date)

        status_counts = quotes.values('status').annotate(
            count=Count('id')
        ).order_by('status')

        # Calculate conversion rates
        total_quotes = quotes.count()
        accepted_quotes = quotes.filter(status='accepted').count()
        converted_quotes = quotes.filter(status='converted').count()

        conversion_data = [
            {
                'status': item['status'].replace('_', ' ').title(),
                'count': item['count'],
                'percentage': round((item['count'] / total_quotes * 100), 1) if total_quotes > 0 else 0
            } for item in status_counts
        ]

        return Response({
            'title': 'Quote Conversion Funnel',
            'type': 'funnel',
            'data': conversion_data,
            'conversion_rate': round((accepted_quotes / total_quotes * 100), 1) if total_quotes > 0 else 0,
            'period': f"{start_date} to {end_date}",
        })

    def _get_inventory_status_chart(self):
        """Get inventory status chart data"""
        items = InventoryItem.objects.filter(is_active=True)

        status_counts = {
            'normal': items.filter(
                current_stock__gt=F('reorder_point'),
                current_stock__lte=F('maximum_stock')
            ).count(),
            'low_stock': items.filter(
                current_stock__lte=F('reorder_point'),
                current_stock__gt=0
            ).count(),
            'out_of_stock': items.filter(current_stock__lte=0).count(),
            'overstock': items.filter(current_stock__gt=F('maximum_stock')).count(),
        }

        return Response({
            'title': 'Inventory Status',
            'type': 'pie',
            'data': [
                {
                    'label': status.replace('_', ' ').title(),
                    'value': count,
                    'percentage': round((count / items.count() * 100), 1) if items.count() > 0 else 0
                } for status, count in status_counts.items()
            ],
            'total_items': items.count(),
        })
