#!/usr/bin/env python
"""
Comprehensive System Integration Testing Suite
Tests all modules and their interactions for the Roofing Contractor Platform
"""

import os
import sys
import django
from django.test import TestCase, TransactionTestCase
from django.test.client import Client
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test.utils import override_settings
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import json
import tempfile
import shutil

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'roof_platform.settings')
django.setup()

from customers.models import Customer
from jobs.models import Job
from technicians.models import TechnicianProfile
from quotes.models import Quote, QuoteItem
from inventory.models import InventoryItem, StockTransaction
from reports.models import Report, DashboardMetric


class SystemIntegrationTestSuite(TransactionTestCase):
    """
    Comprehensive integration tests covering all platform modules
    """

    def setUp(self):
        """Set up test data for all modules"""
        self.client = Client()

        # Create test users
        self.owner = get_user_model().objects.create_user(
            username='testuser',
            email='owner@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Owner',
            role='owner'
        )

        self.manager = get_user_model().objects.create_user(
            username='testmanager',
            email='manager@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Manager',
            role='manager'
        )

        self.technician = get_user_model().objects.create_user(
            username='testtechnician',
            email='tech@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Technician',
            role='technician'
        )

        # Create test data
        self.customer = Customer.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@test.com',
            phone='555-0123',
            address='123 Test St'
        )

        self.tech_profile = TechnicianProfile.objects.create(
            user=self.technician,
            full_name='Test Technician',
            phone='555-0456'
        )

    def test_user_authentication_flow(self):
        """Test complete user authentication flow"""
        # Test user registration
        response = self.client.post('/api/auth/register/', {
            'email': 'newuser@test.com',
            'password': 'securepass123',
            'first_name': 'New',
            'last_name': 'User',
            'role': 'technician'
        }, content_type='application/json')
        self.assertEqual(response.status_code, 201)

        # Test user login
        response = self.client.post('/api/auth/login/', {
            'email': 'newuser@test.com',
            'password': 'securepass123'
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.json())
        self.assertIn('refresh', response.json())

        # Test token refresh
        refresh_token = response.json()['refresh']
        response = self.client.post('/api/auth/token/refresh/', {
            'refresh': refresh_token
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200)

    def test_customer_job_workflow(self):
        """Test complete customer to job workflow"""
        # 1. Create customer
        customer_data = {
            'first_name': 'Alice',
            'last_name': 'Smith',
            'email': 'alice@test.com',
            'phone': '555-0789',
            'address': '456 Oak Ave'
        }

        self.client.force_authenticate(user=self.manager)
        response = self.client.post('/api/customers/customers/',
                                  customer_data,
                                  content_type='application/json')
        self.assertEqual(response.status_code, 201)
        customer_id = response.json()['id']

        # 2. Create quote for customer
        quote_data = {
            'customer': customer_id,
            'title': 'Roof Replacement Quote',
            'project_address': '456 Oak Ave',
            'project_type': 'replacement',
            'subtotal': 5000.00,
            'tax_rate': 8.25,
            'items': [
                {
                    'description': 'Roof Replacement',
                    'quantity': 1,
                    'unit': 'job',
                    'unit_price': 5000.00
                }
            ]
        }

        response = self.client.post('/api/quotes/quotes/',
                                  quote_data,
                                  content_type='application/json')
        self.assertEqual(response.status_code, 201)
        quote_id = response.json()['id']

        # 3. Accept quote and convert to job
        response = self.client.post(f'/api/quotes/quotes/{quote_id}/accept/',
                                  {'notes': 'Approved'},
                                  content_type='application/json')
        self.assertEqual(response.status_code, 200)

        response = self.client.post(f'/api/quotes/quotes/{quote_id}/convert_to_job/',
                                  {},
                                  content_type='application/json')
        self.assertEqual(response.status_code, 201)
        job_id = response.json()['id']

        # 4. Assign technician to job
        job_data = {
            'assigned_technicians': [self.tech_profile.id],
            'scheduled_date': '2024-09-15',
            'scheduled_time': '09:00:00'
        }

        response = self.client.patch(f'/api/jobs/jobs/{job_id}/',
                                   job_data,
                                   content_type='application/json')
        self.assertEqual(response.status_code, 200)

        # 5. Start job
        response = self.client.post(f'/api/jobs/jobs/{job_id}/start/',
                                  {},
                                  content_type='application/json')
        self.assertEqual(response.status_code, 200)

        # 6. Complete job
        completion_data = {
            'actual_cost': 4800.00,
            'quality_rating': 5,
            'customer_feedback': 'Excellent work!'
        }

        response = self.client.post(f'/api/jobs/jobs/{job_id}/complete/',
                                  completion_data,
                                  content_type='application/json')
        self.assertEqual(response.status_code, 200)

    def test_inventory_quote_integration(self):
        """Test inventory and quote integration"""
        # 1. Create inventory items
        self.client.force_authenticate(user=self.manager)

        item_data = {
            'name': 'Asphalt Shingles',
            'sku': 'SHINGLE-001',
            'unit': 'sq_ft',
            'current_stock': 1000.00,
            'unit_cost': 2.50,
            'selling_price': 4.00
        }

        response = self.client.post('/api/inventory/items/',
                                  item_data,
                                  content_type='application/json')
        self.assertEqual(response.status_code, 201)
        item_id = response.json()['id']

        # 2. Create quote with inventory items
        quote_data = {
            'customer': self.customer.id,
            'title': 'Roof Repair with Materials',
            'project_address': '123 Test St',
            'project_type': 'repair',
            'items': [
                {
                    'description': 'Asphalt Shingles',
                    'quantity': 500,
                    'unit': 'sq_ft',
                    'unit_price': 4.00,
                    'inventory_item': item_id
                }
            ]
        }

        response = self.client.post('/api/quotes/quotes/',
                                  quote_data,
                                  content_type='application/json')
        self.assertEqual(response.status_code, 201)

        # 3. Verify inventory integration
        response = self.client.get(f'/api/inventory/items/{item_id}/')
        self.assertEqual(response.status_code, 200)
        item = response.json()
        self.assertEqual(item['current_stock'], 1000.00)  # Should not change until job completion

    def test_reporting_dashboard_integration(self):
        """Test reporting and dashboard integration"""
        # Create test data for reports
        Job.objects.create(
            customer=self.customer,
            title='Report Test Job',
            status='completed',
            actual_cost=1000.00,
            created_by=self.manager
        )

        Quote.objects.create(
            customer=self.customer,
            title='Report Test Quote',
            status='accepted',
            subtotal=1200.00,
            created_by=self.manager
        )

        # Test dashboard metrics
        self.client.force_authenticate(user=self.manager)
        response = self.client.get('/api/reports/dashboard/')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn('metrics', data)
        self.assertIn('recent_jobs', data)
        self.assertIn('recent_quotes', data)

        # Test specific reports
        response = self.client.get('/api/reports/charts/?type=job_status&days=30')
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/api/reports/analytics/performance_overview/?days=30')
        self.assertEqual(response.status_code, 200)

    def test_role_based_access_control(self):
        """Test role-based access control across all modules"""
        # Test owner access
        self.client.force_authenticate(user=self.owner)

        # Owner should have access to all endpoints
        response = self.client.get('/api/customers/customers/')
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/api/reports/dashboard/')
        self.assertEqual(response.status_code, 200)

        # Test manager access
        self.client.force_authenticate(user=self.manager)

        response = self.client.get('/api/customers/customers/')
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/api/reports/dashboard/')
        self.assertEqual(response.status_code, 200)

        # Test technician access (limited)
        self.client.force_authenticate(user=self.technician)

        # Technician should have access to their own data
        response = self.client.get('/api/technicians/profile/')
        self.assertEqual(response.status_code, 200)

        # But limited access to sensitive data
        response = self.client.get('/api/reports/dashboard/')
        self.assertEqual(response.status_code, 403)  # Should be forbidden

    def test_notification_system_integration(self):
        """Test notification system integration"""
        # Create a job that should trigger notifications
        job = Job.objects.create(
            customer=self.customer,
            title='Notification Test Job',
            status='scheduled',
            scheduled_date=timezone.now().date(),
            created_by=self.manager
        )

        # Test notification creation through job assignment
        self.client.force_authenticate(user=self.manager)

        job_data = {
            'assigned_technicians': [self.tech_profile.id]
        }

        response = self.client.patch(f'/api/jobs/jobs/{job.id}/',
                                   job_data,
                                   content_type='application/json')
        self.assertEqual(response.status_code, 200)

        # Verify notifications were created (would need notification models)
        # This would test the notification system integration

    def test_error_handling_and_validation(self):
        """Test comprehensive error handling and validation"""
        self.client.force_authenticate(user=self.manager)

        # Test invalid customer data
        invalid_customer = {
            'first_name': '',  # Invalid: empty
            'email': 'invalid-email',  # Invalid: not email format
        }

        response = self.client.post('/api/customers/customers/',
                                  invalid_customer,
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('first_name', response.json())
        self.assertIn('email', response.json())

        # Test invalid quote data
        invalid_quote = {
            'customer': 99999,  # Invalid: non-existent customer
            'title': '',  # Invalid: empty
            'subtotal': -100,  # Invalid: negative
        }

        response = self.client.post('/api/quotes/quotes/',
                                  invalid_quote,
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)

        # Test unauthorized access
        self.client.logout()
        response = self.client.get('/api/customers/customers/')
        self.assertEqual(response.status_code, 401)

    def test_concurrent_operations(self):
        """Test concurrent operations and race conditions"""
        from concurrent.futures import ThreadPoolExecutor
        import threading

        results = []

        def create_customer(index):
            """Create customer in separate thread"""
            try:
                customer_data = {
                    'first_name': f'Concurrent',
                    'last_name': f'User{index}',
                    'email': f'concurrent{index}@test.com',
                    'phone': f'555-0{index:03d}'
                }

                self.client.force_authenticate(user=self.manager)
                response = self.client.post('/api/customers/customers/',
                                          customer_data,
                                          content_type='application/json')
                results.append(response.status_code)
            except Exception as e:
                results.append(str(e))

        # Run concurrent operations
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_customer, i) for i in range(10)]
            for future in futures:
                future.result()

        # Verify all operations succeeded
        success_count = sum(1 for r in results if r == 201)
        self.assertEqual(success_count, 10)

        # Verify no duplicate emails were created
        unique_emails = set()
        for customer in Customer.objects.filter(email__startswith='concurrent'):
            if customer.email in unique_emails:
                self.fail(f"Duplicate email found: {customer.email}")
            unique_emails.add(customer.email)

    def test_data_integrity_and_constraints(self):
        """Test data integrity and database constraints"""
        # Test foreign key constraints
        invalid_quote = {
            'customer': 99999,  # Non-existent customer
            'title': 'Invalid Quote',
            'project_address': '123 Test St'
        }

        self.client.force_authenticate(user=self.manager)
        response = self.client.post('/api/quotes/quotes/',
                                  invalid_quote,
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)

        # Test unique constraints
        Customer.objects.create(
            first_name='Unique',
            last_name='Test',
            email='unique@test.com'
        )

        duplicate_customer = {
            'first_name': 'Duplicate',
            'last_name': 'Test',
            'email': 'unique@test.com'  # Duplicate email
        }

        response = self.client.post('/api/customers/customers/',
                                  duplicate_customer,
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)

        # Test cascade delete behavior
        quote = Quote.objects.create(
            customer=self.customer,
            title='Cascade Test',
            project_address='123 Test St',
            created_by=self.manager
        )

        QuoteItem.objects.create(
            quote=quote,
            description='Test Item',
            quantity=1,
            unit_price=100.00
        )

        # Delete customer and verify cascade
        self.customer.delete()

        # Quote should be deleted due to CASCADE
        with self.assertRaises(Quote.DoesNotExist):
            Quote.objects.get(id=quote.id)

    def test_performance_under_load(self):
        """Test system performance under load"""
        import time

        self.client.force_authenticate(user=self.manager)

        # Create bulk test data
        customers = []
        for i in range(50):
            customer = Customer.objects.create(
                first_name=f'Bulk{i}',
                last_name='Test',
                email=f'bulk{i}@test.com',
                phone=f'555-{i:04d}'
            )
            customers.append(customer)

        # Test bulk quote creation performance
        start_time = time.time()

        for customer in customers[:20]:  # Test with 20 quotes
            quote_data = {
                'customer': customer.id,
                'title': f'Performance Test Quote {customer.id}',
                'project_address': '123 Test St',
                'project_type': 'repair',
                'subtotal': 1000.00,
                'tax_rate': 8.25
            }

            response = self.client.post('/api/quotes/quotes/',
                                      quote_data,
                                      content_type='application/json')
            self.assertEqual(response.status_code, 201)

        end_time = time.time()
        duration = end_time - start_time

        # Performance assertion (should complete within reasonable time)
        self.assertLess(duration, 30.0, f"Bulk operations took too long: {duration}s")

    def test_third_party_integration_simulation(self):
        """Test third-party integration simulation"""
        # This would test integrations with:
        # - Email services (SendGrid)
        # - SMS services (Twilio)
        # - Payment services (Stripe)
        # - Mapping services (Google Maps)
        # - File storage (AWS S3)

        # For now, test the framework is in place
        self.client.force_authenticate(user=self.manager)

        # Test quote email sending (would integrate with SendGrid)
        quote = Quote.objects.create(
            customer=self.customer,
            title='Email Test Quote',
            project_address='123 Test St',
            created_by=self.manager
        )

        response = self.client.post(f'/api/quotes/quotes/{quote.id}/send_to_customer/',
                                  {},
                                  content_type='application/json')
        self.assertEqual(response.status_code, 200)

        # Verify quote status changed
        quote.refresh_from_db()
        self.assertEqual(quote.status, 'sent')


if __name__ == '__main__':
    # Run the integration tests
    import unittest

    # Load test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(SystemIntegrationTestSuite)

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print(f"\n{'='*50}")
    print("INTEGRATION TEST SUMMARY")
    print(f"{'='*50}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.failures:
        print(f"\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")

    if result.errors:
        print(f"\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")

    if result.wasSuccessful():
        print("\n✅ All integration tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some integration tests failed!")
        sys.exit(1)
