#!/usr/bin/env python3
"""
MVP End-to-End Testing Script
Tests all core functionality of the Roofing Platform MVP
"""

import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'roof_platform.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from accounts.models import User
from customers.models import Customer, CustomerAddress
from technicians.models import TechnicianProfile, Skill, Crew
from jobs.models import Job
from notifications.models import NotificationTemplate, NotificationLog


class MVPTestSuite(APITestCase):
    """Comprehensive test suite for MVP functionality"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()

        # Create test users
        self.owner_user = User.objects.create_user(
            username='owner@test.com',
            email='owner@test.com',
            password='testpass123',
            first_name='John',
            last_name='Owner',
            role='owner'
        )

        self.manager_user = User.objects.create_user(
            username='manager@test.com',
            email='manager@test.com',
            password='testpass123',
            first_name='Jane',
            last_name='Manager',
            role='manager'
        )

        self.technician_user = User.objects.create_user(
            username='tech@test.com',
            email='tech@test.com',
            password='testpass123',
            first_name='Bob',
            last_name='Technician',
            role='technician'
        )

        # Create technician profile
        self.technician_profile = TechnicianProfile.objects.create(
            user=self.technician_user,
            employee_id='TECH001',
            is_available=True
        )

        # Create skills
        self.roofing_skill = Skill.objects.create(
            name='Roofing',
            category='roofing',
            is_active=True
        )

        # Create crew
        self.crew = Crew.objects.create(
            name='Main Crew',
            leader=self.technician_profile,
            is_active=True,
            primary_skill=self.roofing_skill
        )
        self.crew.members.add(self.technician_profile)

        # Create customer
        self.customer = Customer.objects.create(
            first_name='Alice',
            last_name='Customer',
            email='alice@test.com',
            phone_number='+1234567890',
            is_active=True,
            created_by=self.manager_user
        )

        # Create customer address
        self.customer_address = CustomerAddress.objects.create(
            customer=self.customer,
            street_address='123 Main St',
            city='Anytown',
            state='CA',
            postal_code='12345',
            is_primary=True
        )

        # Create job
        self.job = Job.objects.create(
            customer=self.customer,
            title='Roof Repair',
            description='Fix leaking roof',
            job_type='repair',
            status='scheduled',
            scheduled_date=timezone.now().date() + timedelta(days=1),
            scheduled_time=timezone.now().time(),
            estimated_duration_hours=Decimal('4.0'),
            assigned_crew=self.crew,
            address='123 Main St, Anytown, CA 12345',
            created_by=self.manager_user
        )
        self.job.assigned_technicians.add(self.technician_profile)

    def test_user_authentication(self):
        """Test user authentication and authorization"""
        print("🧪 Testing User Authentication...")

        # Test login
        response = self.client.post('/api/auth/login/', {
            'email': 'owner@test.com',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

        # Test profile access
        access_token = response.data['access']
        self.client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {access_token}'

        response = self.client.get('/api/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'owner@test.com')

        print("✅ User authentication tests passed")

    def test_customer_management(self):
        """Test customer CRUD operations"""
        print("🧪 Testing Customer Management...")

        # Authenticate as manager
        self.client.login(email='manager@test.com', password='testpass123')

        # Create customer
        customer_data = {
            'first_name': 'Test',
            'last_name': 'Customer',
            'email': 'test@example.com',
            'phone_number': '+1987654321',
            'addresses': [{
                'street_address': '456 Test St',
                'city': 'Test City',
                'state': 'TX',
                'postal_code': '67890',
                'is_primary': True
            }]
        }

        response = self.client.post('/api/customers/', customer_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        customer_id = response.data['id']

        # Read customer
        response = self.client.get(f'/api/customers/{customer_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'test@example.com')

        # Update customer
        response = self.client.patch(f'/api/customers/{customer_id}/', {
            'notes': 'Updated notes'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Delete customer
        response = self.client.delete(f'/api/customers/{customer_id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        print("✅ Customer management tests passed")

    def test_technician_management(self):
        """Test technician profile management"""
        print("🧪 Testing Technician Management...")

        # Authenticate as manager
        self.client.login(email='manager@test.com', password='testpass123')

        # Read technician profiles
        response = self.client.get('/api/technicians/technicians/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)

        # Update technician profile
        response = self.client.patch(f'/api/technicians/technicians/{self.technician_profile.id}/', {
            'hourly_rate': '25.00'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test crew management
        response = self.client.get('/api/technicians/crews/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)

        print("✅ Technician management tests passed")

    def test_job_management(self):
        """Test job CRUD operations"""
        print("🧪 Testing Job Management...")

        # Authenticate as manager
        self.client.login(email='manager@test.com', password='testpass123')

        # Create job
        job_data = {
            'title': 'Test Job',
            'description': 'Test job description',
            'customer': self.customer.id,
            'job_type': 'repair',
            'scheduled_date': (timezone.now().date() + timedelta(days=2)).isoformat(),
            'scheduled_time': '10:00:00',
            'estimated_duration_hours': '3.5',
            'assigned_crew': self.crew.id
        }

        response = self.client.post('/api/jobs/', job_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        job_id = response.data['id']

        # Read job
        response = self.client.get(f'/api/jobs/{job_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Test Job')

        # Update job status
        response = self.client.patch(f'/api/jobs/{job_id}/', {
            'status': 'in_progress'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        print("✅ Job management tests passed")

    def test_scheduling_calendar(self):
        """Test scheduling calendar functionality"""
        print("🧪 Testing Scheduling Calendar...")

        # Authenticate as manager
        self.client.login(email='manager@test.com', password='testpass123')

        # Get calendar data
        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=7)

        response = self.client.get(f'/api/jobs/calendar/?start={start_date}&end={end_date}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

        print("✅ Scheduling calendar tests passed")

    def test_notification_system(self):
        """Test notification system"""
        print("🧪 Testing Notification System...")

        # Authenticate as admin
        self.client.login(email='owner@test.com', password='testpass123')

        # Get notification templates
        response = self.client.get('/api/notifications/templates/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Get notification logs
        response = self.client.get('/api/notifications/logs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Get notification stats
        response = self.client.get('/api/notifications/stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        print("✅ Notification system tests passed")

    def test_mobile_technician_interface(self):
        """Test mobile technician interface"""
        print("🧪 Testing Mobile Technician Interface...")

        # Authenticate as technician
        self.client.login(email='tech@test.com', password='testpass123')

        # Get today's jobs
        response = self.client.get('/api/jobs/technician/today/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('todays_jobs', response.data)

        # Update job status (simulated mobile action)
        response = self.client.post(f'/api/jobs/{self.job.id}/status/', {
            'status': 'in_progress',
            'notes': 'Started working on the job'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        print("✅ Mobile technician interface tests passed")

    def test_data_integrity(self):
        """Test data integrity and relationships"""
        print("🧪 Testing Data Integrity...")

        # Verify job-customer relationship
        job = Job.objects.get(id=self.job.id)
        self.assertEqual(job.customer.id, self.customer.id)

        # Verify crew-technician relationship
        crew = Crew.objects.get(id=self.crew.id)
        self.assertIn(self.technician_profile, crew.members.all())

        # Verify job-crew relationship
        self.assertEqual(job.assigned_crew.id, self.crew.id)

        # Verify address relationship
        customer = Customer.objects.get(id=self.customer.id)
        primary_address = customer.primary_address
        self.assertIsNotNone(primary_address)
        self.assertEqual(primary_address.street_address, '123 Main St')

        print("✅ Data integrity tests passed")

    def test_permissions(self):
        """Test role-based permissions"""
        print("🧪 Testing Permissions...")

        # Test technician permissions (limited access)
        self.client.login(email='tech@test.com', password='testpass123')

        # Technician should be able to view their jobs
        response = self.client.get('/api/jobs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Technician should not be able to create users
        response = self.client.post('/api/auth/users/', {
            'email': 'newuser@test.com',
            'username': 'newuser',
            'password': 'testpass123',
            'role': 'technician'
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Test manager permissions
        self.client.login(email='manager@test.com', password='testpass123')

        # Manager should be able to create users
        response = self.client.post('/api/auth/users/', {
            'email': 'newuser@test.com',
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'testpass123',
            'role': 'technician'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        print("✅ Permissions tests passed")

    def run_all_tests(self):
        """Run all MVP tests"""
        print("🚀 Starting MVP End-to-End Testing Suite")
        print("=" * 50)

        try:
            self.test_user_authentication()
            self.test_customer_management()
            self.test_technician_management()
            self.test_job_management()
            self.test_scheduling_calendar()
            self.test_notification_system()
            self.test_mobile_technician_interface()
            self.test_data_integrity()
            self.test_permissions()

            print("=" * 50)
            print("🎉 All MVP tests passed successfully!")
            return True

        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Run the test suite"""
    print("Roofing Platform MVP Testing Suite")
    print("==================================")

    # Create test database and run migrations if needed
    from django.core.management import execute_from_command_line
    try:
        execute_from_command_line(['manage.py', 'migrate', '--run-syncdb'])
    except:
        pass  # Ignore if already migrated

    # Run tests
    test_suite = MVPTestSuite()
    test_suite.setUp()

    success = test_suite.run_all_tests()

    if success:
        print("\n✅ MVP is ready for deployment!")
        sys.exit(0)
    else:
        print("\n❌ MVP has issues that need to be resolved")
        sys.exit(1)


if __name__ == '__main__':
    main()
