from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from django.core.validators import MinValueValidator


class InventoryCategory(models.Model):
    """
    Categories for organizing inventory items.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text='Category name'
    )
    description = models.TextField(
        blank=True,
        help_text='Category description'
    )
    parent_category = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subcategories',
        help_text='Parent category for hierarchical organization'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this category is active'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Inventory Category'
        verbose_name_plural = 'Inventory Categories'

    def __str__(self):
        if self.parent_category:
            return f"{self.parent_category.name} > {self.name}"
        return self.name


class Supplier(models.Model):
    """
    Suppliers/vendors for inventory items.
    """
    name = models.CharField(
        max_length=200,
        help_text='Supplier company name'
    )
    contact_person = models.CharField(
        max_length=100,
        blank=True,
        help_text='Primary contact person'
    )
    email = models.EmailField(
        blank=True,
        help_text='Supplier email'
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        help_text='Supplier phone number'
    )
    address = models.TextField(
        blank=True,
        help_text='Supplier address'
    )
    website = models.URLField(
        blank=True,
        help_text='Supplier website'
    )
    notes = models.TextField(
        blank=True,
        help_text='Additional notes about supplier'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this supplier is active'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Supplier'
        verbose_name_plural = 'Suppliers'

    def __str__(self):
        return self.name


class InventoryItem(models.Model):
    """
    Individual inventory items/materials.
    """
    UNIT_CHOICES = [
        ('each', 'Each'),
        ('sq_ft', 'Square Feet'),
        ('linear_ft', 'Linear Feet'),
        ('lb', 'Pounds'),
        ('kg', 'Kilograms'),
        ('gal', 'Gallons'),
        ('liter', 'Liters'),
        ('box', 'Box'),
        ('roll', 'Roll'),
        ('bundle', 'Bundle'),
        ('sheet', 'Sheet'),
        ('panel', 'Panel'),
        ('bag', 'Bag'),
        ('can', 'Can'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('discontinued', 'Discontinued'),
        ('out_of_stock', 'Out of Stock'),
    ]

    # Basic information
    name = models.CharField(
        max_length=200,
        help_text='Item name/description'
    )
    sku = models.CharField(
        max_length=100,
        unique=True,
        help_text='Stock Keeping Unit - unique identifier'
    )
    description = models.TextField(
        blank=True,
        help_text='Detailed description'
    )

    # Categorization
    category = models.ForeignKey(
        InventoryCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='items',
        help_text='Item category'
    )

    # Suppliers and pricing
    suppliers = models.ManyToManyField(
        Supplier,
        through='ItemSupplier',
        related_name='supplied_items',
        help_text='Suppliers for this item'
    )

    # Stock information
    unit = models.CharField(
        max_length=20,
        choices=UNIT_CHOICES,
        default='each',
        help_text='Unit of measurement'
    )

    current_stock = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Current stock quantity'
    )

    minimum_stock = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Minimum stock level before reorder'
    )

    maximum_stock = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Maximum stock level'
    )

    reorder_point = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Point at which to reorder'
    )

    # Cost and pricing
    unit_cost = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Cost per unit'
    )

    selling_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Selling price per unit'
    )

    # Status and tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        help_text='Item status'
    )

    is_active = models.BooleanField(
        default=True,
        help_text='Whether this item is active'
    )

    # Location and storage
    location = models.CharField(
        max_length=200,
        blank=True,
        help_text='Storage location'
    )

    barcode = models.CharField(
        max_length=100,
        blank=True,
        help_text='Barcode for item'
    )

    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_inventory_items',
        help_text='User who created this item'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Inventory Item'
        verbose_name_plural = 'Inventory Items'
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['is_active', 'current_stock']),
        ]

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def save(self, *args, **kwargs):
        # Auto-generate SKU if not provided
        if not self.sku:
            import uuid
            self.sku = str(uuid.uuid4())[:8].upper()
        super().save(*args, **kwargs)

    @property
    def stock_status(self):
        """Determine stock status based on current levels"""
        if self.current_stock <= 0:
            return 'out_of_stock'
        elif self.current_stock <= self.reorder_point:
            return 'low_stock'
        elif self.current_stock >= self.maximum_stock:
            return 'overstock'
        else:
            return 'normal'

    @property
    def stock_value(self):
        """Calculate total value of current stock"""
        return self.current_stock * self.unit_cost

    @property
    def needs_reorder(self):
        """Check if item needs to be reordered"""
        return self.current_stock <= self.reorder_point

    def update_stock(self, quantity_change, reason='', reference='', user=None):
        """
        Update stock quantity with audit trail.
        """
        old_quantity = self.current_stock
        self.current_stock += quantity_change
        self.save()

        # Create stock transaction record
        StockTransaction.objects.create(
            item=self,
            transaction_type='adjustment' if quantity_change != 0 else 'count',
            quantity_change=quantity_change,
            new_quantity=self.current_stock,
            reason=reason,
            reference=reference,
            performed_by=user
        )

        return self.current_stock


class ItemSupplier(models.Model):
    """
    Through model for item-supplier relationships with pricing.
    """
    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name='supplier_relationships'
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name='item_relationships'
    )

    supplier_sku = models.CharField(
        max_length=100,
        blank=True,
        help_text='SKU used by this supplier'
    )

    supplier_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Price from this supplier'
    )

    minimum_order_quantity = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Minimum quantity to order from this supplier'
    )

    lead_time_days = models.PositiveIntegerField(
        default=7,
        help_text='Lead time in days for delivery'
    )

    is_preferred = models.BooleanField(
        default=False,
        help_text='Whether this is the preferred supplier'
    )

    notes = models.TextField(
        blank=True,
        help_text='Notes about this supplier relationship'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['item', 'supplier']
        ordering = ['-is_preferred', 'supplier_price']
        verbose_name = 'Item Supplier'
        verbose_name_plural = 'Item Suppliers'

    def __str__(self):
        return f"{self.item.name} - {self.supplier.name}"


class StockTransaction(models.Model):
    """
    Audit trail for all stock movements.
    """
    TRANSACTION_TYPES = [
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
        ('adjustment', 'Adjustment'),
        ('transfer', 'Transfer'),
        ('return', 'Return'),
        ('count', 'Stock Count'),
        ('waste', 'Waste/Damage'),
    ]

    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name='transactions',
        help_text='Item involved in transaction'
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES,
        help_text='Type of transaction'
    )

    quantity_change = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text='Change in quantity (positive for increase, negative for decrease)'
    )

    new_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Stock quantity after this transaction'
    )

    # Related entities
    related_job = models.ForeignKey(
        'jobs.Job',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_transactions',
        help_text='Related job if applicable'
    )

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        help_text='Related supplier if applicable'
    )

    # Details
    reason = models.CharField(
        max_length=200,
        blank=True,
        help_text='Reason for transaction'
    )

    reference = models.CharField(
        max_length=100,
        blank=True,
        help_text='Reference number (PO, invoice, etc.)'
    )

    notes = models.TextField(
        blank=True,
        help_text='Additional notes'
    )

    # Audit
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='inventory_transactions',
        help_text='User who performed this transaction'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Stock Transaction'
        verbose_name_plural = 'Stock Transactions'
        indexes = [
            models.Index(fields=['item', 'created_at']),
            models.Index(fields=['transaction_type', 'created_at']),
            models.Index(fields=['performed_by', 'created_at']),
        ]

    def __str__(self):
        return f"{self.item.name} - {self.get_transaction_type_display()} ({self.quantity_change})"


class PurchaseOrder(models.Model):
    """
    Purchase orders for inventory replenishment.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent to Supplier'),
        ('confirmed', 'Confirmed'),
        ('partially_received', 'Partially Received'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    ]

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name='purchase_orders',
        help_text='Supplier for this purchase order'
    )

    po_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        help_text='Purchase order number'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        help_text='Purchase order status'
    )

    order_date = models.DateField(
        auto_now_add=True,
        help_text='Date order was placed'
    )

    expected_delivery_date = models.DateField(
        null=True,
        blank=True,
        help_text='Expected delivery date'
    )

    actual_delivery_date = models.DateField(
        null=True,
        blank=True,
        help_text='Actual delivery date'
    )

    # Financial details
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Subtotal before tax'
    )

    tax_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Tax amount'
    )

    shipping_cost = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Shipping/freight cost'
    )

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Total order amount'
    )

    # Notes and tracking
    notes = models.TextField(
        blank=True,
        help_text='Order notes'
    )

    tracking_number = models.CharField(
        max_length=100,
        blank=True,
        help_text='Shipping tracking number'
    )

    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_purchase_orders',
        help_text='User who created this order'
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_purchase_orders',
        help_text='User who approved this order'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Purchase Order'
        verbose_name_plural = 'Purchase Orders'
        indexes = [
            models.Index(fields=['supplier', 'status']),
            models.Index(fields=['po_number']),
            models.Index(fields=['order_date']),
        ]

    def __str__(self):
        return f"PO {self.po_number} - {self.supplier.name}"

    def save(self, *args, **kwargs):
        # Auto-generate PO number if not set
        if not self.po_number:
            import datetime
            today = datetime.date.today()
            date_str = today.strftime('%Y%m%d')

            # Find the next number for today
            today_pos = PurchaseOrder.objects.filter(
                po_number__startswith=f'PO-{date_str}',
                created_at__date=today
            ).count()

            self.po_number = f'PO-{date_str}-{str(today_pos + 1).zfill(3)}'

        # Calculate total
        self.total_amount = self.subtotal + self.tax_amount + self.shipping_cost

        super().save(*args, **kwargs)


class PurchaseOrderItem(models.Model):
    """
    Individual items in a purchase order.
    """
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name='items',
        help_text='Purchase order this item belongs to'
    )

    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name='purchase_order_items',
        help_text='Inventory item being ordered'
    )

    quantity_ordered = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Quantity ordered'
    )

    quantity_received = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Quantity actually received'
    )

    unit_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Unit price'
    )

    line_total = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text='Total for this line item'
    )

    notes = models.TextField(
        blank=True,
        help_text='Notes for this item'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['purchase_order', 'inventory_item']
        ordering = ['created_at']
        verbose_name = 'Purchase Order Item'
        verbose_name_plural = 'Purchase Order Items'

    def __str__(self):
        return f"{self.purchase_order.po_number} - {self.inventory_item.name}"

    def save(self, *args, **kwargs):
        # Calculate line total
        self.line_total = self.quantity_ordered * self.unit_price
        super().save(*args, **kwargs)

    @property
    def quantity_remaining(self):
        """Quantity still to be received"""
        return self.quantity_ordered - self.quantity_received

    @property
    def is_fully_received(self):
        """Check if item has been fully received"""
        return self.quantity_received >= self.quantity_ordered
