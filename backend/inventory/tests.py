from django.test import TestCase
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from .models import (
    InventoryCategory, Supplier, InventoryItem, ItemSupplier,
    StockTransaction, PurchaseOrder, PurchaseOrderItem
)


class InventoryCategoryTestCase(TestCase):
    """Test cases for InventoryCategory model"""

    def test_category_creation(self):
        """Test inventory category creation"""
        category = InventoryCategory.objects.create(
            name='Roofing Materials',
            description='Materials for roofing projects'
        )

        self.assertEqual(category.name, 'Roofing Materials')
        self.assertTrue(category.is_active)

    def test_category_hierarchy(self):
        """Test category hierarchy"""
        parent = InventoryCategory.objects.create(
            name='Materials',
            description='All materials'
        )

        child = InventoryCategory.objects.create(
            name='Roofing',
            description='Roofing materials',
            parent_category=parent
        )

        self.assertEqual(child.parent_category, parent)
        self.assertEqual(str(child), 'Materials > Roofing')


class SupplierTestCase(TestCase):
    """Test cases for Supplier model"""

    def test_supplier_creation(self):
        """Test supplier creation"""
        supplier = Supplier.objects.create(
            name='Test Supplier',
            contact_person='John Doe',
            email='john@testsupplier.com',
            phone='555-0123'
        )

        self.assertEqual(supplier.name, 'Test Supplier')
        self.assertTrue(supplier.is_active)


class InventoryItemTestCase(TestCase):
    """Test cases for InventoryItem model"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', first_name='Test', last_name='User', 
            email='test@example.com',
            password='testpass123',
            role='manager'
        )
        self.category = InventoryCategory.objects.create(
            name='Test Category'
        )

    def test_item_creation(self):
        """Test inventory item creation"""
        item = InventoryItem.objects.create(
            name='Test Item',
            sku='TEST-001',
            category=self.category,
            unit='each',
            current_stock=Decimal('100.00'),
            unit_cost=Decimal('10.00'),
            selling_price=Decimal('15.00'),
            created_by=self.user
        )

        self.assertEqual(item.name, 'Test Item')
        self.assertEqual(item.sku, 'TEST-001')
        self.assertEqual(item.stock_status, 'normal')
        self.assertEqual(item.stock_value, Decimal('1000.00'))  # 100 * 10

    def test_auto_sku_generation(self):
        """Test automatic SKU generation"""
        item = InventoryItem.objects.create(
            name='Auto SKU Item',
            category=self.category,
            unit='each',
            created_by=self.user
        )

        self.assertIsNotNone(item.sku)
        self.assertTrue(len(item.sku) >= 8)

    def test_stock_status_calculation(self):
        """Test stock status calculation"""
        item = InventoryItem.objects.create(
            name='Stock Test',
            sku='STOCK-001',
            category=self.category,
            unit='each',
            minimum_stock=Decimal('10.00'),
            reorder_point=Decimal('25.00'),
            current_stock=Decimal('50.00'),
            created_by=self.user
        )

        # Normal stock
        self.assertEqual(item.stock_status, 'normal')

        # Low stock
        item.current_stock = Decimal('20.00')
        item.save()
        self.assertEqual(item.stock_status, 'low_stock')

        # Out of stock
        item.current_stock = Decimal('0.00')
        item.save()
        self.assertEqual(item.stock_status, 'out_of_stock')

    def test_stock_update(self):
        """Test stock update functionality"""
        item = InventoryItem.objects.create(
            name='Update Test',
            sku='UPDATE-001',
            category=self.category,
            unit='each',
            current_stock=Decimal('50.00'),
            created_by=self.user
        )

        old_stock = item.current_stock
        quantity_change = Decimal('10.00')

        new_stock = item.update_stock(
            quantity_change,
            reason='Test adjustment',
            reference='TEST-001',
            user=self.user
        )

        self.assertEqual(new_stock, old_stock + quantity_change)
        item.refresh_from_db()
        self.assertEqual(item.current_stock, old_stock + quantity_change)

        # Check transaction was created
        transaction = StockTransaction.objects.filter(item=item).latest('created_at')
        self.assertEqual(transaction.quantity_change, quantity_change)
        self.assertEqual(transaction.reason, 'Test adjustment')


class StockTransactionTestCase(TestCase):
    """Test cases for StockTransaction model"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', first_name='Test', last_name='User', 
            email='test@example.com',
            password='testpass123',
            role='manager'
        )
        self.category = InventoryCategory.objects.create(name='Test')
        self.item = InventoryItem.objects.create(
            name='Transaction Test',
            sku='TRANS-001',
            category=self.category,
            created_by=self.user
        )

    def test_transaction_creation(self):
        """Test stock transaction creation"""
        transaction = StockTransaction.objects.create(
            item=self.item,
            transaction_type='adjustment',
            quantity_change=Decimal('10.00'),
            new_quantity=Decimal('10.00'),
            reason='Test transaction',
            performed_by=self.user
        )

        self.assertEqual(transaction.quantity_change, Decimal('10.00'))
        self.assertEqual(transaction.transaction_type, 'adjustment')
        self.assertEqual(str(transaction), f"{self.item.name} - Adjustment (10.00)")


class PurchaseOrderTestCase(TestCase):
    """Test cases for PurchaseOrder model"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', first_name='Test', last_name='User', 
            email='test@example.com',
            password='testpass123',
            role='manager'
        )
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            email='supplier@test.com'
        )

    def test_purchase_order_creation(self):
        """Test purchase order creation"""
        po = PurchaseOrder.objects.create(
            supplier=self.supplier,
            created_by=self.user
        )

        self.assertIsNotNone(po.po_number)
        self.assertTrue(po.po_number.startswith('PO-'))
        self.assertEqual(po.status, 'draft')

    def test_purchase_order_calculations(self):
        """Test purchase order calculations"""
        po = PurchaseOrder.objects.create(
            supplier=self.supplier,
            subtotal=Decimal('100.00'),
            tax_amount=Decimal('8.25'),
            shipping_cost=Decimal('10.00'),
            created_by=self.user
        )

        expected_total = Decimal('118.25')  # 100 + 8.25 + 10
        self.assertEqual(po.total_amount, expected_total)


class PurchaseOrderItemTestCase(TestCase):
    """Test cases for PurchaseOrderItem model"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', first_name='Test', last_name='User', 
            email='test@example.com',
            password='testpass123',
            role='manager'
        )
        self.supplier = Supplier.objects.create(name='Test Supplier')
        self.category = InventoryCategory.objects.create(name='Test')
        self.item = InventoryItem.objects.create(
            name='PO Item Test',
            sku='PO-001',
            category=self.category,
            created_by=self.user
        )
        self.po = PurchaseOrder.objects.create(
            supplier=self.supplier,
            created_by=self.user
        )

    def test_purchase_order_item_creation(self):
        """Test purchase order item creation"""
        po_item = PurchaseOrderItem.objects.create(
            purchase_order=self.po,
            inventory_item=self.item,
            quantity_ordered=Decimal('20.00'),
            unit_price=Decimal('10.00')
        )

        self.assertEqual(po_item.line_total, Decimal('200.00'))  # 20 * 10
        self.assertEqual(po_item.quantity_remaining, Decimal('20.00'))
        self.assertFalse(po_item.is_fully_received)

    def test_partial_receipt(self):
        """Test partial receipt of items"""
        po_item = PurchaseOrderItem.objects.create(
            purchase_order=self.po,
            inventory_item=self.item,
            quantity_ordered=Decimal('20.00'),
            unit_price=Decimal('10.00')
        )

        po_item.quantity_received = Decimal('15.00')
        po_item.save()

        self.assertEqual(po_item.quantity_remaining, Decimal('5.00'))
        self.assertFalse(po_item.is_fully_received)

    def test_full_receipt(self):
        """Test full receipt of items"""
        po_item = PurchaseOrderItem.objects.create(
            purchase_order=self.po,
            inventory_item=self.item,
            quantity_ordered=Decimal('20.00'),
            unit_price=Decimal('10.00')
        )

        po_item.quantity_received = Decimal('20.00')
        po_item.save()

        self.assertEqual(po_item.quantity_remaining, Decimal('0.00'))
        self.assertTrue(po_item.is_fully_received)


class InventoryAPITestCase(APITestCase):
    """Test cases for Inventory API endpoints"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', first_name='Test', last_name='User', 
            email='test@example.com',
            password='testpass123',
            role='manager'
        )
        self.client.force_authenticate(user=self.user)
        self.category = InventoryCategory.objects.create(name='Test Category')

    def test_inventory_item_list(self):
        """Test inventory item list API"""
        item = InventoryItem.objects.create(
            name='API Test Item',
            sku='API-001',
            category=self.category,
            created_by=self.user
        )

        response = self.client.get('/api/inventory/items/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_inventory_item_creation(self):
        """Test inventory item creation via API"""
        data = {
            'name': 'API Created Item',
            'category': self.category.id,
            'unit': 'each',
            'current_stock': 50,
            'unit_cost': 10.00,
            'selling_price': 15.00
        }

        response = self.client.post('/api/inventory/items/', data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(InventoryItem.objects.count(), 1)

    def test_stock_update_api(self):
        """Test stock update via API"""
        item = InventoryItem.objects.create(
            name='Stock Update Test',
            sku='STOCK-API-001',
            category=self.category,
            current_stock=Decimal('100.00'),
            created_by=self.user
        )

        data = {
            'item_id': item.id,
            'quantity_change': 25,
            'reason': 'API Test',
            'reference': 'API-REF-001'
        }

        response = self.client.post('/api/inventory/items/stock_update/', data, format='json')
        self.assertEqual(response.status_code, 200)

        item.refresh_from_db()
        self.assertEqual(item.current_stock, Decimal('125.00'))

    def test_low_stock_api(self):
        """Test low stock items API"""
        # Create item with low stock
        InventoryItem.objects.create(
            name='Low Stock Item',
            sku='LOW-001',
            category=self.category,
            current_stock=Decimal('5.00'),
            reorder_point=Decimal('10.00'),
            created_by=self.user
        )

        response = self.client.get('/api/inventory/items/low_stock/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_inventory_reports(self):
        """Test inventory reports API"""
        InventoryItem.objects.create(
            name='Report Test Item',
            sku='REPORT-001',
            category=self.category,
            current_stock=Decimal('100.00'),
            unit_cost=Decimal('10.00'),
            created_by=self.user
        )

        response = self.client.get('/api/inventory/reports/summary/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('total_items', response.data)
        self.assertIn('total_value', response.data)