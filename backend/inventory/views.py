from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from decimal import Decimal
from .models import (
    InventoryCategory, Supplier, InventoryItem, ItemSupplier,
    StockTransaction, PurchaseOrder, PurchaseOrderItem
)
from .serializers import (
    InventoryCategorySerializer, SupplierSerializer, InventoryItemSerializer,
    ItemSupplierSerializer, StockTransactionSerializer, PurchaseOrderSerializer,
    PurchaseOrderCreateSerializer, StockUpdateSerializer, InventoryReportSerializer
)
from .permissions import IsOwnerOrManager


class InventoryCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing inventory categories"""
    queryset = InventoryCategory.objects.all()
    serializer_class = InventoryCategorySerializer
    permission_classes = [IsAuthenticated, IsOwnerOrManager]

    def get_queryset(self):
        queryset = InventoryCategory.objects.filter(is_active=True)
        parent = self.request.query_params.get('parent', None)
        if parent:
            queryset = queryset.filter(parent_category_id=parent)
        return queryset


class SupplierViewSet(viewsets.ModelViewSet):
    """ViewSet for managing suppliers"""
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrManager]

    def get_queryset(self):
        return Supplier.objects.filter(is_active=True)


class InventoryItemViewSet(viewsets.ModelViewSet):
    """ViewSet for managing inventory items"""
    queryset = InventoryItem.objects.all()
    serializer_class = InventoryItemSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrManager]

    def get_queryset(self):
        queryset = InventoryItem.objects.filter(is_active=True)

        # Filter by category
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category_id=category)

        # Filter by stock status
        stock_status = self.request.query_params.get('stock_status', None)
        if stock_status == 'low_stock':
            queryset = queryset.filter(current_stock__lte=F('reorder_point'))
        elif stock_status == 'out_of_stock':
            queryset = queryset.filter(current_stock__lte=0)
        elif stock_status == 'overstock':
            queryset = queryset.filter(current_stock__gte=F('maximum_stock'))

        # Filter by search term
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(sku__icontains=search) |
                Q(description__icontains=search)
            )

        return queryset

    @action(detail=True, methods=['post'])
    def update_stock(self, request, pk=None):
        """Update stock quantity for an item"""
        item = self.get_object()
        serializer = StockUpdateSerializer(data=request.data)

        if serializer.is_valid():
            quantity_change = serializer.validated_data['quantity_change']
            reason = serializer.validated_data.get('reason', '')
            reference = serializer.validated_data.get('reference', '')

            new_stock = item.update_stock(
                quantity_change,
                reason=reason,
                reference=reference,
                user=request.user
            )

            return Response({
                'message': 'Stock updated successfully',
                'new_stock': new_stock
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get items that are low on stock"""
        items = self.get_queryset().filter(
            current_stock__lte=F('reorder_point'),
            current_stock__gt=0
        )
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def out_of_stock(self, request):
        """Get items that are out of stock"""
        items = self.get_queryset().filter(current_stock__lte=0)
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def needs_reorder(self, request):
        """Get items that need to be reordered"""
        items = self.get_queryset().filter(current_stock__lte=F('reorder_point'))
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)


class ItemSupplierViewSet(viewsets.ModelViewSet):
    """ViewSet for managing item-supplier relationships"""
    queryset = ItemSupplier.objects.all()
    serializer_class = ItemSupplierSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrManager]

    def get_queryset(self):
        queryset = ItemSupplier.objects.all()
        item = self.request.query_params.get('item', None)
        supplier = self.request.query_params.get('supplier', None)

        if item:
            queryset = queryset.filter(item_id=item)
        if supplier:
            queryset = queryset.filter(supplier_id=supplier)

        return queryset


class StockTransactionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing stock transactions"""
    queryset = StockTransaction.objects.all()
    serializer_class = StockTransactionSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrManager]

    def get_queryset(self):
        queryset = StockTransaction.objects.all()

        # Filter by item
        item = self.request.query_params.get('item', None)
        if item:
            queryset = queryset.filter(item_id=item)

        # Filter by transaction type
        transaction_type = self.request.query_params.get('type', None)
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)

        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)

        return queryset


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    """ViewSet for managing purchase orders"""
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrManager]

    def get_serializer_class(self):
        if self.action == 'create':
            return PurchaseOrderCreateSerializer
        return PurchaseOrderSerializer

    def get_queryset(self):
        queryset = PurchaseOrder.objects.all()

        # Filter by supplier
        supplier = self.request.query_params.get('supplier', None)
        if supplier:
            queryset = queryset.filter(supplier_id=supplier)

        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date:
            queryset = queryset.filter(order_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(order_date__lte=end_date)

        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a purchase order"""
        purchase_order = self.get_object()

        if purchase_order.status != 'draft':
            return Response(
                {'error': 'Only draft orders can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )

        purchase_order.status = 'sent'
        purchase_order.approved_by = request.user
        purchase_order.save()

        return Response({'message': 'Purchase order approved'})

    @action(detail=True, methods=['post'])
    def receive_items(self, request, pk=None):
        """Receive items from a purchase order"""
        purchase_order = self.get_object()
        items_data = request.data.get('items', [])

        if not items_data:
            return Response(
                {'error': 'No items provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        for item_data in items_data:
            try:
                po_item = PurchaseOrderItem.objects.get(
                    id=item_data['id'],
                    purchase_order=purchase_order
                )
                received_quantity = Decimal(str(item_data['quantity_received']))

                if received_quantity > po_item.quantity_remaining:
                    return Response(
                        {'error': f'Cannot receive more than remaining quantity for {po_item.inventory_item.name}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                po_item.quantity_received += received_quantity
                po_item.save()

                # Update inventory stock
                po_item.inventory_item.update_stock(
                    received_quantity,
                    reason='Purchase order receipt',
                    reference=purchase_order.po_number,
                    user=request.user
                )

            except PurchaseOrderItem.DoesNotExist:
                return Response(
                    {'error': f'Purchase order item {item_data["id"]} not found'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Update purchase order status
        all_received = all(item.is_fully_received for item in purchase_order.items.all())
        if all_received:
            purchase_order.status = 'received'
            purchase_order.actual_delivery_date = timezone.now().date()
        else:
            purchase_order.status = 'partially_received'
        purchase_order.save()

        return Response({'message': 'Items received successfully'})


class InventoryReportsViewSet(viewsets.ViewSet):
    """ViewSet for inventory reports"""
    permission_classes = [IsAuthenticated, IsOwnerOrManager]

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get inventory summary report"""
        items = InventoryItem.objects.filter(is_active=True)

        # Calculate totals
        total_items = items.count()
        total_value = items.aggregate(
            total=Sum(F('current_stock') * F('unit_cost'))
        )['total'] or Decimal('0.00')

        # Stock status counts
        low_stock_items = items.filter(current_stock__lte=F('reorder_point')).count()
        out_of_stock_items = items.filter(current_stock__lte=0).count()

        # Items by category
        items_by_category = items.values('category__name').annotate(
            count=Count('id'),
            value=Sum(F('current_stock') * F('unit_cost'))
        ).order_by('-count')

        # Recent transactions
        recent_transactions = StockTransaction.objects.select_related(
            'item', 'performed_by'
        ).order_by('-created_at')[:10]

        transactions_data = []
        for transaction in recent_transactions:
            transactions_data.append({
                'id': transaction.id,
                'item_name': transaction.item.name,
                'transaction_type': transaction.get_transaction_type_display(),
                'quantity_change': float(transaction.quantity_change),
                'performed_by': transaction.performed_by.get_full_name() if transaction.performed_by else 'System',
                'created_at': transaction.created_at.isoformat()
            })

        report_data = {
            'total_items': total_items,
            'total_value': float(total_value),
            'low_stock_items': low_stock_items,
            'out_of_stock_items': out_of_stock_items,
            'items_by_category': list(items_by_category),
            'recent_transactions': transactions_data,
            'generated_at': timezone.now().isoformat()
        }

        serializer = InventoryReportSerializer(data=report_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data)

    @action(detail=False, methods=['get'])
    def stock_movement(self, request):
        """Get stock movement report"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not start_date or not end_date:
            return Response(
                {'error': 'start_date and end_date are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        transactions = StockTransaction.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).select_related('item')

        # Group by item and transaction type
        movements = {}
        for transaction in transactions:
            item_key = transaction.item.name
            if item_key not in movements:
                movements[item_key] = {
                    'item_name': item_key,
                    'sku': transaction.item.sku,
                    'purchases': 0,
                    'sales': 0,
                    'adjustments': 0,
                    'returns': 0,
                    'net_change': 0
                }

            if transaction.transaction_type == 'purchase':
                movements[item_key]['purchases'] += float(transaction.quantity_change)
            elif transaction.transaction_type == 'sale':
                movements[item_key]['sales'] += float(transaction.quantity_change)
            elif transaction.transaction_type == 'adjustment':
                movements[item_key]['adjustments'] += float(transaction.quantity_change)
            elif transaction.transaction_type == 'return':
                movements[item_key]['returns'] += float(transaction.quantity_change)

            movements[item_key]['net_change'] += float(transaction.quantity_change)

        return Response({
            'movements': list(movements.values()),
            'date_range': f"{start_date} to {end_date}",
            'generated_at': timezone.now().isoformat()
        })
