from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from customers.models import Customer
from .models import Quote, QuoteItem, QuoteTemplate, QuoteSettings


class QuoteModelTestCase(TestCase):
    """Test cases for Quote model"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', first_name='Test', last_name='User', 
            email='test@example.com',
            password='testpass123',
            role='manager'
        )
        self.customer = Customer.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            phone='555-0123'
        )

    def test_quote_creation(self):
        """Test quote creation with auto-generated number"""
        quote = Quote.objects.create(
            customer=self.customer,
            title='Test Quote',
            project_address='123 Test St',
            project_type='repair',
            tax_rate=Decimal('8.25'),
            subtotal=Decimal('1000.00'),
            created_by=self.user
        )

        self.assertIsNotNone(quote.quote_number)
        self.assertTrue(quote.quote_number.startswith('Q-'))
        self.assertEqual(quote.status, 'draft')
        self.assertEqual(quote.total_amount, Decimal('1082.50'))  # 1000 + 8.25% tax

    def test_quote_expiry(self):
        """Test quote expiry functionality"""
        past_date = timezone.now().date() - timezone.timedelta(days=1)
        quote = Quote.objects.create(
            customer=self.customer,
            title='Expired Quote',
            project_address='123 Test St',
            valid_until=past_date,
            created_by=self.user
        )

        self.assertTrue(quote.is_expired)

    def test_quote_status_transitions(self):
        """Test quote status transitions"""
        quote = Quote.objects.create(
            customer=self.customer,
            title='Status Test',
            project_address='123 Test St',
            created_by=self.user
        )

        # Test sending
        quote.status = 'sent'
        quote.save()
        self.assertEqual(quote.status, 'sent')

        # Test acceptance
        quote.accept_quote('Looks good!')
        self.assertEqual(quote.status, 'accepted')
        self.assertIsNotNone(quote.accepted_at)
        self.assertEqual(quote.customer_notes, 'Looks good!')

        # Test decline
        quote.status = 'sent'  # Reset for decline test
        quote.decline_quote('Too expensive')
        self.assertEqual(quote.status, 'declined')
        self.assertIsNotNone(quote.declined_at)
        self.assertEqual(quote.customer_notes, 'Too expensive')


class QuoteItemModelTestCase(TestCase):
    """Test cases for QuoteItem model"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', first_name='Test', last_name='User', 
            email='test@example.com',
            password='testpass123',
            role='manager'
        )
        self.customer = Customer.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@example.com'
        )
        self.quote = Quote.objects.create(
            customer=self.customer,
            title='Test Quote',
            project_address='123 Test St',
            created_by=self.user
        )

    def test_quote_item_creation(self):
        """Test quote item creation with automatic total calculation"""
        item = QuoteItem.objects.create(
            quote=self.quote,
            description='Test Material',
            quantity=Decimal('10.00'),
            unit='sq_ft',
            unit_price=Decimal('5.00')
        )

        self.assertEqual(item.total_price, Decimal('50.00'))  # 10 * 5

    def test_quote_item_categories(self):
        """Test quote item categories"""
        categories = ['labor', 'materials', 'equipment', 'permits', 'disposal', 'other']

        for category in categories:
            item = QuoteItem.objects.create(
                quote=self.quote,
                category=category,
                description=f'{category.title()} Item',
                quantity=Decimal('1.00'),
                unit_price=Decimal('10.00')
            )
            self.assertEqual(item.category, category)


class QuoteTemplateModelTestCase(TestCase):
    """Test cases for QuoteTemplate model"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', first_name='Test', last_name='User', 
            email='test@example.com',
            password='testpass123',
            role='manager'
        )

    def test_template_creation(self):
        """Test quote template creation"""
        template = QuoteTemplate.objects.create(
            name='Standard Repair',
            project_type='repair',
            default_tax_rate=Decimal('8.25'),
            default_validity_days=30,
            created_by=self.user
        )

        self.assertEqual(template.name, 'Standard Repair')
        self.assertEqual(template.usage_count, 0)

    def test_template_usage_tracking(self):
        """Test template usage tracking"""
        template = QuoteTemplate.objects.create(
            name='Usage Test',
            project_type='repair',
            created_by=self.user
        )

        initial_count = template.usage_count
        template.increment_usage()

        template.refresh_from_db()
        self.assertEqual(template.usage_count, initial_count + 1)


class QuoteSettingsModelTestCase(TestCase):
    """Test cases for QuoteSettings model"""

    def test_settings_singleton(self):
        """Test that only one settings instance exists"""
        settings1 = QuoteSettings.get_settings()
        settings2 = QuoteSettings.get_settings()

        self.assertEqual(settings1, settings2)
        self.assertEqual(QuoteSettings.objects.count(), 1)

    def test_default_settings(self):
        """Test default settings values"""
        settings = QuoteSettings.get_settings()

        self.assertEqual(settings.company_name, 'Roofing Platform')
        self.assertEqual(settings.default_tax_rate, Decimal('8.25'))
        self.assertEqual(settings.default_validity_days, 30)
        self.assertTrue(settings.send_quote_emails)


class QuoteAPITestCase(TestCase):
    """Test cases for Quote API endpoints"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', first_name='Test', last_name='User', 
            email='test@example.com',
            password='testpass123',
            role='manager'
        )
        self.client.force_authenticate(user=self.user)

        self.customer = Customer.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@example.com'
        )

    def test_quote_list(self):
        """Test quote list API"""
        Quote.objects.create(
            customer=self.customer,
            title='Test Quote',
            project_address='123 Test St',
            created_by=self.user
        )

        response = self.client.get('/api/quotes/quotes/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_quote_creation(self):
        """Test quote creation via API"""
        data = {
            'customer': self.customer.id,
            'title': 'API Test Quote',
            'project_address': '123 Test St',
            'project_type': 'repair',
            'items': [
                {
                    'description': 'Test Item',
                    'quantity': 10,
                    'unit': 'sq_ft',
                    'unit_price': 5.00
                }
            ]
        }

        response = self.client.post('/api/quotes/quotes/', data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Quote.objects.count(), 1)

    def test_quote_status_update(self):
        """Test quote status update via API"""
        quote = Quote.objects.create(
            customer=self.customer,
            title='Status Test',
            project_address='123 Test St',
            created_by=self.user
        )

        response = self.client.post(f'/api/quotes/quotes/{quote.id}/send_to_customer/')
        self.assertEqual(response.status_code, 200)

        quote.refresh_from_db()
        self.assertEqual(quote.status, 'sent')

    def test_quote_acceptance(self):
        """Test quote acceptance via API"""
        quote = Quote.objects.create(
            customer=self.customer,
            title='Acceptance Test',
            project_address='123 Test St',
            status='sent',
            created_by=self.user
        )

        response = self.client.post(
            f'/api/quotes/quotes/{quote.id}/accept/',
            {'notes': 'Approved!'},
            format='json'
        )
        self.assertEqual(response.status_code, 200)

        quote.refresh_from_db()
        self.assertEqual(quote.status, 'accepted')
        self.assertEqual(quote.customer_notes, 'Approved!')


class QuoteTemplateAPITestCase(TestCase):
    """Test cases for QuoteTemplate API endpoints"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', first_name='Test', last_name='User', 
            email='test@example.com',
            password='testpass123',
            role='manager'
        )
        self.client.force_authenticate(user=self.user)

    def test_template_list(self):
        """Test template list API"""
        QuoteTemplate.objects.create(
            name='Test Template',
            project_type='repair',
            created_by=self.user
        )

        response = self.client.get('/api/quotes/templates/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_template_creation(self):
        """Test template creation via API"""
        data = {
            'name': 'API Template',
            'project_type': 'replacement',
            'default_tax_rate': 8.25,
            'default_validity_days': 30
        }

        response = self.client.post('/api/quotes/templates/', data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(QuoteTemplate.objects.count(), 1)
