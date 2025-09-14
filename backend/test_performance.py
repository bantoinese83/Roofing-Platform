#!/usr/bin/env python
"""
Performance and Scalability Testing Suite
Comprehensive load testing and performance validation for the roofing platform
"""

import os
import sys
import django
import time
import threading
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import statistics
import psutil
import requests
from datetime import datetime, timedelta
import json
import logging

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'roof_platform.settings')
django.setup()

from django.test import TestCase, TransactionTestCase
from django.test.client import Client
from django.contrib.auth import get_user_model
from django.core.management import call_command
from customers.models import Customer
from jobs.models import Job
from quotes.models import Quote
from inventory.models import InventoryItem


class PerformanceTestSuite:
    """
    Comprehensive performance and load testing suite
    """

    def __init__(self, base_url='http://localhost:8000', concurrent_users=50):
        self.base_url = base_url
        self.concurrent_users = concurrent_users
        self.client = Client()
        self.results = {}
        self.logger = self._setup_logger()

        # Performance thresholds
        self.thresholds = {
            'api_response_time': 500,  # ms
            'page_load_time': 2000,   # ms
            'concurrent_users': concurrent_users,
            'error_rate': 0.01,      # 1%
            'memory_usage': 80,      # %
            'cpu_usage': 70          # %
        }

    def _setup_logger(self):
        """Setup performance test logging"""
        logger = logging.getLogger('performance_test')
        logger.setLevel(logging.INFO)

        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)

        # File handler
        fh = logging.FileHandler('logs/performance_test.log')
        fh.setLevel(logging.INFO)

        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        logger.addHandler(fh)
        logger.addHandler(ch)

        return logger

    def create_test_data(self, num_records=1000):
        """Create bulk test data for performance testing"""
        self.logger.info(f"Creating {num_records} test records...")

        # Create test users
        users = []
        for i in range(min(50, num_records // 20)):
            user = get_user_model().objects.create_user(
                email=f'perf_user_{i}@test.com',
                password='testpass123',
                role='technician',
                first_name=f'Perf{i}',
                last_name='User'
            )
            users.append(user)

        # Create customers
        customers = []
        for i in range(num_records):
            customer = Customer.objects.create(
                first_name=f'PerfCustomer{i}',
                last_name='Test',
                email=f'perf_customer_{i}@test.com',
                phone=f'555-{i:06d}',
                address=f'{i} Performance St'
            )
            customers.append(customer)

        # Create inventory items
        items = []
        for i in range(min(100, num_records // 10)):
            item = InventoryItem.objects.create(
                name=f'Perf Item {i}',
                sku=f'PERF-{i:04d}',
                unit='each',
                current_stock=1000.00,
                unit_cost=10.00,
                selling_price=15.00
            )
            items.append(item)

        # Create quotes and jobs
        for i in range(min(500, num_records)):
            customer = customers[i % len(customers)]
            user = users[i % len(users)]

            # Create quote
            quote = Quote.objects.create(
                customer=customer,
                title=f'Performance Quote {i}',
                project_address=customer.address,
                project_type='repair',
                subtotal=1000.00 + (i * 10),
                tax_rate=8.25,
                created_by=user
            )

            # Create job
            job = Job.objects.create(
                customer=customer,
                title=f'Performance Job {i}',
                description=f'Performance test job {i}',
                status=['draft', 'scheduled', 'in_progress', 'completed'][i % 4],
                priority=['low', 'medium', 'high'][i % 3],
                estimated_cost=1000.00 + (i * 10),
                created_by=user
            )

        self.logger.info("Test data creation completed")
        return len(customers), len(users), len(items)

    def api_load_test(self, endpoint, method='GET', data=None, num_requests=100):
        """Test API endpoint performance under load"""
        self.logger.info(f"Testing {endpoint} with {num_requests} concurrent requests")

        def make_request():
            start_time = time.time()
            try:
                if method == 'GET':
                    response = requests.get(f"{self.base_url}{endpoint}")
                elif method == 'POST':
                    response = requests.post(f"{self.base_url}{endpoint}",
                                           json=data,
                                           headers={'Content-Type': 'application/json'})
                else:
                    return None

                response_time = (time.time() - start_time) * 1000  # Convert to ms
                return {
                    'status_code': response.status_code,
                    'response_time': response_time,
                    'success': response.status_code < 400
                }
            except Exception as e:
                return {
                    'status_code': 0,
                    'response_time': (time.time() - start_time) * 1000,
                    'success': False,
                    'error': str(e)
                }

        # Execute concurrent requests
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=min(num_requests, 50)) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        total_time = time.time() - start_time

        # Analyze results
        response_times = [r['response_time'] for r in results if r]
        success_count = sum(1 for r in results if r and r['success'])
        error_count = len(results) - success_count

        analysis = {
            'endpoint': endpoint,
            'total_requests': num_requests,
            'successful_requests': success_count,
            'error_requests': error_count,
            'error_rate': error_count / num_requests if num_requests > 0 else 0,
            'total_time': total_time,
            'requests_per_second': num_requests / total_time if total_time > 0 else 0,
            'avg_response_time': statistics.mean(response_times) if response_times else 0,
            'median_response_time': statistics.median(response_times) if response_times else 0,
            'min_response_time': min(response_times) if response_times else 0,
            'max_response_time': max(response_times) if response_times else 0,
            '95th_percentile': statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times) if response_times else 0,
            '99th_percentile': statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else max(response_times) if response_times else 0
        }

        self.results[endpoint] = analysis
        return analysis

    def concurrent_user_simulation(self, num_users=50, duration_minutes=5):
        """Simulate concurrent users performing typical operations"""
        self.logger.info(f"Simulating {num_users} concurrent users for {duration_minutes} minutes")

        def user_session(user_id):
            """Simulate a user session"""
            session_start = time.time()
            session_actions = 0
            session_errors = 0

            try:
                # Simulate user authentication (if API supports it)
                # For now, just simulate typical user actions

                while time.time() - session_start < (duration_minutes * 60):
                    try:
                        # Simulate various user actions
                        action_start = time.time()

                        # Randomly choose an action
                        actions = [
                            ('/api/customers/customers/', 'GET'),
                            ('/api/jobs/jobs/', 'GET'),
                            ('/api/quotes/quotes/', 'GET'),
                            ('/api/inventory/items/', 'GET'),
                        ]

                        endpoint, method = actions[session_actions % len(actions)]

                        if method == 'GET':
                            response = requests.get(f"{self.base_url}{endpoint}")
                        else:
                            response = requests.post(f"{self.base_url}{endpoint}", json={})

                        action_time = time.time() - action_start
                        session_actions += 1

                        # Add random delay to simulate user think time
                        time.sleep(0.5 + (session_actions % 3))

                    except Exception as e:
                        session_errors += 1
                        self.logger.warning(f"User {user_id} action failed: {e}")

            except Exception as e:
                self.logger.error(f"User {user_id} session failed: {e}")
                session_errors += 1

            return {
                'user_id': user_id,
                'duration': time.time() - session_start,
                'actions_completed': session_actions,
                'errors': session_errors
            }

        # Run concurrent user sessions
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(user_session, i) for i in range(num_users)]
            user_results = [future.result() for future in concurrent.futures.as_completed(futures)]

        total_time = time.time() - start_time

        # Analyze concurrent user test results
        analysis = {
            'total_users': num_users,
            'test_duration': total_time,
            'user_sessions': user_results,
            'avg_session_duration': statistics.mean([r['duration'] for r in user_results]),
            'total_actions': sum([r['actions_completed'] for r in user_results]),
            'total_errors': sum([r['errors'] for r in user_results]),
            'actions_per_second': sum([r['actions_completed'] for r in user_results]) / total_time,
            'error_rate': sum([r['errors'] for r in user_results]) / sum([r['actions_completed'] for r in user_results]) if sum([r['actions_completed'] for r in user_results]) > 0 else 0
        }

        self.results['concurrent_users'] = analysis
        return analysis

    def memory_and_cpu_monitoring(self, duration_seconds=60):
        """Monitor system resources during testing"""
        self.logger.info(f"Monitoring system resources for {duration_seconds} seconds")

        memory_usage = []
        cpu_usage = []

        start_time = time.time()

        while time.time() - start_time < duration_seconds:
            memory_usage.append(psutil.virtual_memory().percent)
            cpu_usage.append(psutil.cpu_percent(interval=1))

        analysis = {
            'monitoring_duration': duration_seconds,
            'avg_memory_usage': statistics.mean(memory_usage),
            'max_memory_usage': max(memory_usage),
            'avg_cpu_usage': statistics.mean(cpu_usage),
            'max_cpu_usage': max(cpu_usage),
            'memory_threshold_exceeded': max(memory_usage) > self.thresholds['memory_usage'],
            'cpu_threshold_exceeded': max(cpu_usage) > self.thresholds['cpu_usage']
        }

        self.results['system_resources'] = analysis
        return analysis

    def database_performance_test(self):
        """Test database performance with complex queries"""
        self.logger.info("Testing database performance with complex queries")

        from django.db import connection

        # Test complex queries
        queries = [
            {
                'name': 'customer_jobs_summary',
                'query': '''
                    SELECT c.id, c.first_name, c.last_name, COUNT(j.id) as job_count,
                           AVG(j.estimated_cost) as avg_job_cost
                    FROM customers_customer c
                    LEFT JOIN jobs_job j ON c.id = j.customer_id
                    GROUP BY c.id, c.first_name, c.last_name
                    ORDER BY job_count DESC
                    LIMIT 100
                '''
            },
            {
                'name': 'quote_status_distribution',
                'query': '''
                    SELECT status, COUNT(*) as count
                    FROM quotes_quote
                    GROUP BY status
                '''
            },
            {
                'name': 'inventory_valuation',
                'query': '''
                    SELECT SUM(current_stock * unit_cost) as total_value,
                           SUM(current_stock * selling_price) as selling_value
                    FROM inventory_inventoryitem
                '''
            }
        ]

        results = {}

        for query_info in queries:
            start_time = time.time()

            with connection.cursor() as cursor:
                cursor.execute(query_info['query'])
                rows = cursor.fetchall()

            execution_time = (time.time() - start_time) * 1000  # Convert to ms

            results[query_info['name']] = {
                'execution_time': execution_time,
                'row_count': len(rows),
                'results': rows[:5] if rows else []  # First 5 results for verification
            }

        self.results['database_performance'] = results
        return results

    def generate_performance_report(self):
        """Generate comprehensive performance report"""
        self.logger.info("Generating performance test report")

        report = {
            'test_timestamp': datetime.now().isoformat(),
            'test_configuration': {
                'base_url': self.base_url,
                'concurrent_users': self.concurrent_users,
                'thresholds': self.thresholds
            },
            'results': self.results,
            'summary': {
                'total_tests': len(self.results),
                'passed_thresholds': 0,
                'failed_thresholds': 0,
                'recommendations': []
            }
        }

        # Analyze results against thresholds
        for test_name, result in self.results.items():
            if test_name == 'api_load_test':
                for endpoint, metrics in result.items():
                    if isinstance(metrics, dict):
                        if 'avg_response_time' in metrics:
                            if metrics['avg_response_time'] > self.thresholds['api_response_time']:
                                report['summary']['failed_thresholds'] += 1
                                report['summary']['recommendations'].append(
                                    f"API {endpoint}: Average response time ({metrics['avg_response_time']:.2f}ms) exceeds threshold ({self.thresholds['api_response_time']}ms)"
                                )
                            else:
                                report['summary']['passed_thresholds'] += 1

                        if 'error_rate' in metrics and metrics['error_rate'] > self.thresholds['error_rate']:
                            report['summary']['failed_thresholds'] += 1
                            report['summary']['recommendations'].append(
                                f"API {endpoint}: Error rate ({metrics['error_rate']:.2%}) exceeds threshold ({self.thresholds['error_rate']:.2%})"
                            )

            elif test_name == 'system_resources':
                if result.get('memory_threshold_exceeded'):
                    report['summary']['failed_thresholds'] += 1
                    report['summary']['recommendations'].append(
                        f"Memory usage ({result['max_memory_usage']:.1f}%) exceeded threshold ({self.thresholds['memory_usage']}%)"
                    )

                if result.get('cpu_threshold_exceeded'):
                    report['summary']['failed_thresholds'] += 1
                    report['summary']['recommendations'].append(
                        f"CPU usage ({result['max_cpu_usage']:.1f}%) exceeded threshold ({self.thresholds['cpu_usage']}%)"
                    )

        # Save report to file
        os.makedirs('reports', exist_ok=True)
        report_file = f"reports/performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        self.logger.info(f"Performance report saved to {report_file}")
        return report

    def run_full_performance_test_suite(self):
        """Run the complete performance test suite"""
        self.logger.info("Starting comprehensive performance test suite")

        try:
            # Step 1: Create test data
            self.create_test_data(1000)

            # Step 2: Monitor system resources in background
            monitor_thread = threading.Thread(
                target=self.memory_and_cpu_monitoring,
                args=(300,)  # 5 minutes
            )
            monitor_thread.start()

            # Step 3: Test key API endpoints
            api_tests = [
                ('/api/customers/customers/', 'GET'),
                ('/api/jobs/jobs/', 'GET'),
                ('/api/quotes/quotes/', 'GET'),
                ('/api/inventory/items/', 'GET'),
                ('/api/reports/dashboard/', 'GET'),
            ]

            api_results = {}
            for endpoint, method in api_tests:
                result = self.api_load_test(endpoint, method, num_requests=100)
                api_results[endpoint] = result

            self.results['api_load_test'] = api_results

            # Step 4: Concurrent user simulation
            concurrent_result = self.concurrent_user_simulation(
                num_users=self.concurrent_users,
                duration_minutes=3
            )

            # Step 5: Database performance test
            db_result = self.database_performance_test()

            # Step 6: Wait for monitoring to complete
            monitor_thread.join()

            # Step 7: Generate report
            report = self.generate_performance_report()

            self.logger.info("Performance test suite completed successfully")
            return report

        except Exception as e:
            self.logger.error(f"Performance test suite failed: {e}")
            raise


def main():
    """Main function to run performance tests"""
    print("🚀 Starting Performance Test Suite")
    print("=" * 50)

    # Initialize test suite
    tester = PerformanceTestSuite(concurrent_users=25)  # Start with moderate load

    try:
        # Run full test suite
        report = tester.run_full_performance_test_suite()

        # Print summary
        print("\n📊 Performance Test Results")
        print("=" * 50)
        print(f"Total Tests: {report['summary']['total_tests']}")
        print(f"Passed Thresholds: {report['summary']['passed_thresholds']}")
        print(f"Failed Thresholds: {report['summary']['failed_thresholds']}")

        if report['summary']['recommendations']:
            print("\n⚠️  Recommendations:")
            for rec in report['summary']['recommendations']:
                print(f"  - {rec}")

        print(f"\n📁 Detailed report saved to: reports/performance_report_*.json")

        if report['summary']['failed_thresholds'] == 0:
            print("\n✅ All performance thresholds met!")
            return 0
        else:
            print(f"\n❌ {report['summary']['failed_thresholds']} performance thresholds failed!")
            return 1

    except Exception as e:
        print(f"\n❌ Performance test suite failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
