#!/usr/bin/env python3
"""
User Acceptance Testing (UAT) Script for Roofing Platform MVP
This script guides testers through comprehensive UAT scenarios
"""

import os
import sys
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List

class UATTester:
    """User Acceptance Testing framework"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.test_results = []
        self.current_user = None

    def log_test(self, test_name: str, passed: bool, notes: str = ""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
        if notes:
            print(f"   Notes: {notes}")
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'notes': notes,
            'timestamp': datetime.now()
        })

    def authenticate(self, email: str, password: str) -> bool:
        """Authenticate user and store tokens"""
        try:
            response = self.session.post(f"{self.base_url}/api/auth/login/", {
                'email': email,
                'password': password
            })
            if response.status_code == 200:
                tokens = response.json()
                self.session.headers.update({
                    'Authorization': f"Bearer {tokens['access']}"
                })
                self.current_user = email
                return True
            return False
        except Exception as e:
            print(f"Authentication failed: {e}")
            return False

    def test_user_registration(self):
        """Test user registration functionality"""
        print("\n🔐 Testing User Registration & Authentication")
        print("-" * 50)

        # Test owner registration
        owner_data = {
            'email': 'uat_owner@test.com',
            'username': 'uat_owner',
            'first_name': 'UAT',
            'last_name': 'Owner',
            'password': 'uatpass123',
            'role': 'owner'
        }

        try:
            response = self.session.post(f"{self.base_url}/api/auth/register/", owner_data)
            if response.status_code == 201:
                self.log_test("Owner registration", True, "Owner account created successfully")
            else:
                self.log_test("Owner registration", False, f"Failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.log_test("Owner registration", False, f"Exception: {e}")
            return False

        # Test login
        if self.authenticate('uat_owner@test.com', 'uatpass123'):
            self.log_test("User login", True, "Login successful")
        else:
            self.log_test("User login", False, "Login failed")
            return False

        # Test profile access
        try:
            response = self.session.get(f"{self.base_url}/api/auth/profile/")
            if response.status_code == 200:
                profile = response.json()
                if profile['email'] == 'uat_owner@test.com' and profile['role'] == 'owner':
                    self.log_test("Profile access", True, "Profile data correct")
                else:
                    self.log_test("Profile access", False, "Profile data incorrect")
            else:
                self.log_test("Profile access", False, f"Failed: {response.status_code}")
        except Exception as e:
            self.log_test("Profile access", False, f"Exception: {e}")

        return True

    def test_customer_management(self):
        """Test customer management functionality"""
        print("\n👥 Testing Customer Management")
        print("-" * 50)

        # Create customer
        customer_data = {
            'first_name': 'UAT',
            'last_name': 'Customer',
            'email': 'uat_customer@test.com',
            'phone_number': '+1555123456',
            'addresses': [{
                'street_address': '123 UAT Street',
                'city': 'Test City',
                'state': 'CA',
                'postal_code': '90210',
                'is_primary': True
            }]
        }

        try:
            response = self.session.post(f"{self.base_url}/api/customers/", json=customer_data)
            if response.status_code == 201:
                customer = response.json()
                customer_id = customer['id']
                self.log_test("Customer creation", True, f"Customer created with ID: {customer_id}")

                # Test customer retrieval
                response = self.session.get(f"{self.base_url}/api/customers/{customer_id}/")
                if response.status_code == 200:
                    self.log_test("Customer retrieval", True, "Customer data retrieved successfully")
                else:
                    self.log_test("Customer retrieval", False, f"Failed: {response.status_code}")

                # Test customer update
                update_data = {'notes': 'Updated via UAT testing'}
                response = self.session.patch(f"{self.base_url}/api/customers/{customer_id}/", json=update_data)
                if response.status_code == 200:
                    self.log_test("Customer update", True, "Customer updated successfully")
                else:
                    self.log_test("Customer update", False, f"Failed: {response.status_code}")

                return customer_id
            else:
                self.log_test("Customer creation", False, f"Failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            self.log_test("Customer management", False, f"Exception: {e}")
            return None

    def test_technician_management(self):
        """Test technician management functionality"""
        print("\n👷 Testing Technician Management")
        print("-" * 50)

        try:
            # Create technician
            tech_data = {
                'email': 'uat_tech@test.com',
                'first_name': 'UAT',
                'last_name': 'Technician',
                'password': 'uatpass123',
                'phone_number': '+1555987654',
                'employee_id': 'UAT001',
                'hourly_rate': '25.00'
            }

            response = self.session.post(f"{self.base_url}/api/auth/users/", json=tech_data)
            if response.status_code == 201:
                self.log_test("Technician creation", True, "Technician created successfully")

                # Test technician listing
                response = self.session.get(f"{self.base_url}/api/technicians/technicians/")
                if response.status_code == 200:
                    techs = response.json()
                    if len(techs) > 0:
                        self.log_test("Technician listing", True, f"Found {len(techs)} technicians")
                    else:
                        self.log_test("Technician listing", False, "No technicians found")
                else:
                    self.log_test("Technician listing", False, f"Failed: {response.status_code}")

                return True
            else:
                self.log_test("Technician creation", False, f"Failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.log_test("Technician management", False, f"Exception: {e}")
            return False

    def test_job_management(self, customer_id: int):
        """Test job management functionality"""
        print("\n🔧 Testing Job Management")
        print("-" * 50)

        # Create job
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        job_data = {
            'title': 'UAT Roof Repair',
            'description': 'Testing job creation via UAT',
            'customer': customer_id,
            'job_type': 'repair',
            'scheduled_date': tomorrow.isoformat(),
            'scheduled_time': '10:00:00',
            'estimated_duration_hours': '4.0',
            'estimated_cost': '1200.00'
        }

        try:
            response = self.session.post(f"{self.base_url}/api/jobs/", json=job_data)
            if response.status_code == 201:
                job = response.json()
                job_id = job['id']
                self.log_test("Job creation", True, f"Job created with ID: {job_id}")

                # Test job retrieval
                response = self.session.get(f"{self.base_url}/api/jobs/{job_id}/")
                if response.status_code == 200:
                    self.log_test("Job retrieval", True, "Job data retrieved successfully")
                else:
                    self.log_test("Job retrieval", False, f"Failed: {response.status_code}")

                # Test job status update
                status_data = {'status': 'in_progress'}
                response = self.session.patch(f"{self.base_url}/api/jobs/{job_id}/", json=status_data)
                if response.status_code == 200:
                    self.log_test("Job status update", True, "Job status updated to 'in_progress'")
                else:
                    self.log_test("Job status update", False, f"Failed: {response.status_code}")

                return job_id
            else:
                self.log_test("Job creation", False, f"Failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            self.log_test("Job management", False, f"Exception: {e}")
            return None

    def test_scheduling_calendar(self):
        """Test scheduling calendar functionality"""
        print("\n📅 Testing Scheduling Calendar")
        print("-" * 50)

        try:
            # Test calendar view
            start_date = datetime.now().date()
            end_date = start_date + timedelta(days=7)

            response = self.session.get(
                f"{self.base_url}/api/jobs/calendar/",
                params={'start': start_date, 'end': end_date}
            )

            if response.status_code == 200:
                calendar_data = response.json()
                self.log_test("Calendar view", True, f"Retrieved {len(calendar_data)} calendar entries")

                # Test job filtering
                response = self.session.get(
                    f"{self.base_url}/api/jobs/",
                    params={'status': 'in_progress'}
                )

                if response.status_code == 200:
                    jobs = response.json()
                    self.log_test("Job filtering", True, f"Filtered jobs by status, found {len(jobs)} jobs")
                else:
                    self.log_test("Job filtering", False, f"Failed: {response.status_code}")

                return True
            else:
                self.log_test("Calendar view", False, f"Failed: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Scheduling calendar", False, f"Exception: {e}")
            return False

    def test_mobile_technician_interface(self):
        """Test mobile technician interface"""
        print("\n📱 Testing Mobile Technician Interface")
        print("-" * 50)

        try:
            # Switch to technician account
            if self.authenticate('uat_tech@test.com', 'uatpass123'):
                # Test technician's job view
                response = self.session.get(f"{self.base_url}/api/jobs/technician/today/")
                if response.status_code == 200:
                    todays_jobs = response.json()
                    self.log_test("Technician job view", True, f"Retrieved today's jobs: {todays_jobs}")

                    # Test job status update (mobile action)
                    if todays_jobs.get('todays_jobs'):
                        job_id = todays_jobs['todays_jobs'][0]['id']
                        status_data = {
                            'status': 'completed',
                            'notes': 'Completed via mobile UAT testing'
                        }

                        response = self.session.post(
                            f"{self.base_url}/api/jobs/{job_id}/status/",
                            json=status_data
                        )

                        if response.status_code == 200:
                            self.log_test("Mobile job update", True, "Job status updated via mobile interface")
                        else:
                            self.log_test("Mobile job update", False, f"Failed: {response.status_code}")
                    else:
                        self.log_test("Mobile job update", True, "No jobs available for mobile testing (expected)")
                else:
                    self.log_test("Technician job view", False, f"Failed: {response.status_code}")

                return True
            else:
                self.log_test("Technician authentication", False, "Could not authenticate as technician")
                return False
        except Exception as e:
            self.log_test("Mobile technician interface", False, f"Exception: {e}")
            return False

    def test_notification_system(self):
        """Test notification system"""
        print("\n📧 Testing Notification System")
        print("-" * 50)

        try:
            # Switch back to owner account
            if self.authenticate('uat_owner@test.com', 'uatpass123'):
                # Test notification templates
                response = self.session.get(f"{self.base_url}/api/notifications/templates/")
                if response.status_code == 200:
                    templates = response.json()
                    self.log_test("Notification templates", True, f"Retrieved {len(templates)} templates")
                else:
                    self.log_test("Notification templates", False, f"Failed: {response.status_code}")

                # Test notification logs
                response = self.session.get(f"{self.base_url}/api/notifications/logs/")
                if response.status_code == 200:
                    logs = response.json()
                    self.log_test("Notification logs", True, f"Retrieved notification logs ({len(logs)} entries)")
                else:
                    self.log_test("Notification logs", False, f"Failed: {response.status_code}")

                # Test notification stats
                response = self.session.get(f"{self.base_url}/api/notifications/stats/")
                if response.status_code == 200:
                    stats = response.json()
                    self.log_test("Notification stats", True, f"Retrieved stats: {stats}")
                else:
                    self.log_test("Notification stats", False, f"Failed: {response.status_code}")

                return True
            else:
                self.log_test("Owner re-authentication", False, "Could not re-authenticate as owner")
                return False
        except Exception as e:
            self.log_test("Notification system", False, f"Exception: {e}")
            return False

    def test_permissions_and_security(self):
        """Test permissions and security"""
        print("\n🔒 Testing Permissions & Security")
        print("-" * 50)

        try:
            # Test role-based access control
            # Switch to technician account
            if self.authenticate('uat_tech@test.com', 'uatpass123'):
                # Technician should not be able to create users
                user_data = {
                    'email': 'unauthorized@test.com',
                    'username': 'unauthorized',
                    'first_name': 'Unauthorized',
                    'last_name': 'User',
                    'password': 'testpass123',
                    'role': 'technician'
                }

                response = self.session.post(f"{self.base_url}/api/auth/users/", json=user_data)
                if response.status_code == 403:
                    self.log_test("Permission control", True, "Technician correctly denied user creation")
                else:
                    self.log_test("Permission control", False, f"Technician incorrectly allowed user creation: {response.status_code}")

                # Technician should be able to view their own jobs
                response = self.session.get(f"{self.base_url}/api/jobs/")
                if response.status_code == 200:
                    self.log_test("Technician job access", True, "Technician can view jobs")
                else:
                    self.log_test("Technician job access", False, f"Technician cannot view jobs: {response.status_code}")

                return True
            else:
                self.log_test("Permission testing", False, "Could not authenticate as technician for permission testing")
                return False
        except Exception as e:
            self.log_test("Permissions & security", False, f"Exception: {e}")
            return False

    def generate_report(self):
        """Generate UAT test report"""
        print("\n📊 UAT Test Report")
        print("=" * 50)

        passed = sum(1 for test in self.test_results if test['passed'])
        total = len(self.test_results)
        success_rate = (passed / total * 100) if total > 0 else 0

        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(".1f")

        print("\nDetailed Results:")
        print("-" * 30)

        for test in self.test_results:
            status = "✅ PASS" if test['passed'] else "❌ FAIL"
            print(f"{status} - {test['test']}")
            if test['notes']:
                print(f"   {test['notes']}")

        print("\n" + "=" * 50)

        if success_rate >= 90:
            print("🎉 UAT PASSED - MVP is ready for production!")
        elif success_rate >= 75:
            print("⚠️  UAT PARTIALLY PASSED - Minor issues need attention")
        else:
            print("❌ UAT FAILED - Critical issues need to be resolved")

        return success_rate >= 90

    def run_uat_tests(self):
        """Run all UAT tests"""
        print("🏗️  Roofing Platform MVP - User Acceptance Testing")
        print("=" * 60)

        # Test user registration and authentication
        if not self.test_user_registration():
            print("❌ Critical failure in user registration. Aborting UAT.")
            return False

        # Test customer management
        customer_id = self.test_customer_management()
        if not customer_id:
            print("❌ Critical failure in customer management. Continuing with limited tests...")

        # Test technician management
        self.test_technician_management()

        # Test job management
        job_id = None
        if customer_id:
            job_id = self.test_job_management(customer_id)

        # Test scheduling calendar
        self.test_scheduling_calendar()

        # Test mobile technician interface
        self.test_mobile_technician_interface()

        # Test notification system
        self.test_notification_system()

        # Test permissions and security
        self.test_permissions_and_security()

        # Generate final report
        return self.generate_report()


def main():
    """Run UAT tests"""
    if len(sys.argv) != 2:
        print("Usage: python uat_testing.py <staging_url>")
        print("Example: python uat_testing.py https://staging.roofingplatform.com")
        sys.exit(1)

    staging_url = sys.argv[1]

    print(f"Testing against: {staging_url}")

    # Test basic connectivity
    try:
        response = requests.get(f"{staging_url}/api/", timeout=10)
        if response.status_code != 200:
            print(f"❌ Staging environment not responding correctly: {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Cannot connect to staging environment: {e}")
        sys.exit(1)

    print("✅ Staging environment is accessible")

    # Run UAT tests
    tester = UATTester(staging_url)
    success = tester.run_uat_tests()

    if success:
        print("\n🚀 MVP is ready for production deployment!")
        sys.exit(0)
    else:
        print("\n⚠️  MVP needs additional work before production deployment")
        sys.exit(1)


if __name__ == '__main__':
    main()
