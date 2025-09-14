from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from jobs.models import Job
from customers.models import Customer
from technicians.models import TechnicianProfile
from quotes.models import Quote
from .models import Report, ReportExecution, DashboardMetric
from .services import ReportService


class ReportModelTestCase(TestCase):
    """Test cases for Report model"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', first_name='Test', last_name='User', 
            email='test@example.com',
            password='testpass123',
            role='manager'
        )

    def test_report_creation(self):
        """Test report creation"""
        report = Report.objects.create(
            name='Test Report',
            report_type='job_status',
            description='A test report',
            is_scheduled=True,
            frequency='weekly',
            created_by=self.user
        )

        self.assertEqual(report.name, 'Test Report')
        self.assertEqual(report.report_type, 'job_status')
        self.assertTrue(report.is_scheduled)
        self.assertEqual(report.frequency, 'weekly')
        self.assertFalse(report.is_active)  # Should be False by default

    def test_report_str_method(self):
        """Test report string representation"""
        report = Report.objects.create(
            name='String Test',
            report_type='revenue_tracking',
            created_by=self.user
        )

        expected = f"String Test (Revenue Tracking)"
        self.assertEqual(str(report), expected)


class ReportExecutionModelTestCase(TestCase):
    """Test cases for ReportExecution model"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', first_name='Test', last_name='User', 
            email='test@example.com',
            password='testpass123',
            role='manager'
        )
        self.report = Report.objects.create(
            name='Execution Test',
            report_type='job_status',
            created_by=self.user
        )

    def test_execution_creation(self):
        """Test report execution creation"""
        execution = ReportExecution.objects.create(
            report=self.report,
            executed_by=self.user
        )

        self.assertEqual(execution.status, 'pending')
        self.assertIsNotNone(execution.created_at)

    def test_execution_status_transitions(self):
        """Test execution status transitions"""
        execution = ReportExecution.objects.create(
            report=self.report,
            executed_by=self.user
        )

        # Start execution
        execution.start_execution(self.user)
        self.assertEqual(execution.status, 'running')
        self.assertIsNotNone(execution.started_at)

        # Complete execution
        execution.complete_execution({'test': 'data'})
        self.assertEqual(execution.status, 'completed')
        self.assertIsNotNone(execution.completed_at)
        self.assertEqual(execution.data, {'test': 'data'})

        # Fail execution
        execution.status = 'running'
        execution.fail_execution('Test error')
        self.assertEqual(execution.status, 'failed')
        self.assertEqual(execution.error_message, 'Test error')

    def test_execution_duration(self):
        """Test execution duration calculation"""
        execution = ReportExecution.objects.create(
            report=self.report,
            executed_by=self.user
        )

        # No duration initially
        self.assertIsNone(execution.duration)

        # Set start and complete times
        execution.started_at = timezone.now()
        execution.completed_at = execution.started_at + timezone.timedelta(seconds=30)
        execution.save()

        self.assertEqual(execution.duration, 30.0)


class DashboardMetricModelTestCase(TestCase):
    """Test cases for DashboardMetric model"""

    def test_metric_creation(self):
        """Test dashboard metric creation"""
        metric = DashboardMetric.objects.create(
            name='Test Metric',
            metric_type='total_jobs',
            value=Decimal('150.00'),
            unit='count'
        )

        self.assertEqual(metric.name, 'Test Metric')
        self.assertEqual(metric.metric_type, 'total_jobs')
        self.assertEqual(metric.value, Decimal('150.00'))
        self.assertEqual(metric.unit, 'count')
        self.assertEqual(metric.trend_direction, 'stable')  # Default

    def test_metric_trend_calculation(self):
        """Test metric trend calculation"""
        metric = DashboardMetric.objects.create(
            name='Trend Test',
            metric_type='active_jobs',
            value=Decimal('100.00')
        )

        # No previous value
        self.assertEqual(metric.trend_percentage, 0)

        # Update with higher value
        metric.update_value(Decimal('120.00'))
        self.assertEqual(metric.trend_direction, 'up')
        self.assertEqual(metric.trend_percentage, 20.0)

        # Update with lower value
        metric.update_value(Decimal('80.00'))
        self.assertEqual(metric.trend_direction, 'down')
        self.assertEqual(metric.trend_percentage, -33.33)

    def test_metric_str_method(self):
        """Test metric string representation"""
        metric = DashboardMetric.objects.create(
            name='String Test',
            metric_type='completed_jobs',
            value=Decimal('50.00'),
            unit='jobs'
        )

        expected = "String Test: 50 jobs"
        self.assertEqual(str(metric), expected)


class ReportServiceTestCase(TestCase):
    """Test cases for ReportService"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', first_name='Test', last_name='User', 
            email='test@example.com',
            password='testpass123',
            role='manager'
        )
        self.service = ReportService()

        # Create test data
        self.customer = Customer.objects.create(
            first_name='Test',
            last_name='Customer',
            email='test@example.com'
        )

        self.technician = TechnicianProfile.objects.create(
            user=self.user,
            full_name='Test Technician'
        )

    def test_job_status_report(self):
        """Test job status report generation"""
        # Create test jobs
        Job.objects.create(
            customer=self.customer,
            title='Test Job 1',
            status='completed',
            created_by=self.user
        )
        Job.objects.create(
            customer=self.customer,
            title='Test Job 2',
            status='in_progress',
            created_by=self.user
        )

        start_date = timezone.now().date() - timezone.timedelta(days=30)
        end_date = timezone.now().date()

        parameters = {
            'start_date': start_date,
            'end_date': end_date
        }

        result = self.service._generate_job_status_report(parameters)

        self.assertEqual(result['title'], 'Job Status Distribution Report')
        self.assertIn('status_distribution', result)
        self.assertIn('total_jobs', result)

    def test_completion_rates_report(self):
        """Test completion rates report generation"""
        # Create completed job
        completed_job = Job.objects.create(
            customer=self.customer,
            title='Completed Job',
            status='completed',
            actual_start_time=timezone.now() - timezone.timedelta(hours=2),
            actual_end_time=timezone.now(),
            estimated_duration_hours=2,
            created_by=self.user
        )

        start_date = timezone.now().date() - timezone.timedelta(days=30)
        end_date = timezone.now().date()

        parameters = {
            'start_date': start_date,
            'end_date': end_date
        }

        result = self.service._generate_completion_rates_report(parameters)

        self.assertEqual(result['title'], 'Job Completion Rates Report')
        self.assertIn('overall_completion_rate', result)
        self.assertIn('weekly_trends', result)

    def test_technician_performance_report(self):
        """Test technician performance report generation"""
        # Create job assigned to technician
        job = Job.objects.create(
            customer=self.customer,
            title='Tech Performance Job',
            status='completed',
            scheduled_date=timezone.now().date(),
            created_by=self.user
        )
        job.assigned_technicians.add(self.technician)

        start_date = timezone.now().date() - timezone.timedelta(days=30)
        end_date = timezone.now().date()

        parameters = {
            'start_date': start_date,
            'end_date': end_date
        }

        result = self.service._generate_technician_performance_report(parameters)

        self.assertEqual(result['title'], 'Technician Performance Report')
        self.assertIn('technician_performance', result)
        self.assertEqual(len(result['technician_performance']), 1)

    def test_revenue_tracking_report(self):
        """Test revenue tracking report generation"""
        # Create completed job with revenue
        Job.objects.create(
            customer=self.customer,
            title='Revenue Job',
            status='completed',
            actual_cost=Decimal('1000.00'),
            updated_at=timezone.now(),
            created_by=self.user
        )

        start_date = timezone.now().date() - timezone.timedelta(days=30)
        end_date = timezone.now().date()

        parameters = {
            'start_date': start_date,
            'end_date': end_date
        }

        result = self.service._generate_revenue_tracking_report(parameters)

        self.assertEqual(result['title'], 'Revenue Tracking Report')
        self.assertIn('total_actual_revenue', result)
        self.assertIn('monthly_trends', result)

    def test_customer_satisfaction_report(self):
        """Test customer satisfaction report generation"""
        # Create job with rating
        Job.objects.create(
            customer=self.customer,
            title='Satisfaction Job',
            status='completed',
            quality_rating=5,
            customer_feedback='Excellent work!',
            updated_at=timezone.now(),
            created_by=self.user
        )

        start_date = timezone.now().date() - timezone.timedelta(days=30)
        end_date = timezone.now().date()

        parameters = {
            'start_date': start_date,
            'end_date': end_date
        }

        result = self.service._generate_customer_satisfaction_report(parameters)

        self.assertEqual(result['title'], 'Customer Satisfaction Report')
        self.assertIn('average_rating', result)
        self.assertIn('recent_feedback', result)

    def test_unknown_report_type(self):
        """Test handling of unknown report type"""
        parameters = {'start_date': timezone.now().date(), 'end_date': timezone.now().date()}

        with self.assertRaises(ValueError):
            self.service.generate_report('unknown_type', parameters)


class ReportsAPITestCase(TestCase):
    """Test cases for Reports API endpoints"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', first_name='Test', last_name='User', 
            email='test@example.com',
            password='testpass123',
            role='manager'
        )
        self.client.force_authenticate(user=self.user)

    def test_report_list(self):
        """Test report list API"""
        Report.objects.create(
            name='API Test Report',
            report_type='job_status',
            created_by=self.user
        )

        response = self.client.get('/api/reports/reports/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_report_creation(self):
        """Test report creation via API"""
        data = {
            'name': 'API Created Report',
            'report_type': 'revenue_tracking',
            'description': 'Created via API',
            'is_scheduled': True,
            'frequency': 'monthly'
        }

        response = self.client.post('/api/reports/reports/', data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Report.objects.count(), 1)

    def test_dashboard_data(self):
        """Test dashboard data API"""
        response = self.client.get('/api/reports/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('metrics', response.data)
        self.assertIn('recent_jobs', response.data)
        self.assertIn('alerts', response.data)

    def test_chart_data(self):
        """Test chart data API"""
        response = self.client.get('/api/reports/charts/?type=job_status&days=30')
        self.assertEqual(response.status_code, 200)
        self.assertIn('data', response.data)
        self.assertIn('title', response.data)

    def test_analytics_overview(self):
        """Test analytics overview API"""
        response = self.client.get('/api/reports/analytics/performance_overview/?days=30')
        self.assertEqual(response.status_code, 200)
        self.assertIn('job_performance', response.data)
        self.assertIn('revenue', response.data)

    def test_trend_analysis(self):
        """Test trend analysis API"""
        response = self.client.get('/api/reports/analytics/trend_analysis/?days=30')
        self.assertEqual(response.status_code, 200)
        self.assertIn('daily_trends', response.data)
        self.assertIn('weekly_trends', response.data)
