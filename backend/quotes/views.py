from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Sum
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from .models import Quote, QuoteItem, QuoteTemplate, QuoteSettings
from .serializers import (
    QuoteSerializer, QuoteCreateSerializer, QuoteItemSerializer,
    QuoteTemplateSerializer, QuoteSettingsSerializer
)
from accounts.permissions import ManagerAndAbove


class QuoteViewSet(viewsets.ModelViewSet):
    """ViewSet for managing quotes"""
    queryset = Quote.objects.all()
    permission_classes = [IsAuthenticated, ManagerAndAbove]

    def get_serializer_class(self):
        if self.action == 'create':
            return QuoteCreateSerializer
        return QuoteSerializer

    def get_queryset(self):
        queryset = Quote.objects.select_related('customer', 'created_by')

        # Filter by customer
        customer = self.request.query_params.get('customer', None)
        if customer:
            queryset = queryset.filter(customer_id=customer)

        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)

        # Filter by search term
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(quote_number__icontains=search) |
                Q(customer__first_name__icontains=search) |
                Q(customer__last_name__icontains=search)
            )

        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def send_to_customer(self, request, pk=None):
        """Send quote to customer"""
        quote = self.get_object()

        if quote.status != 'draft':
            return Response(
                {'error': 'Only draft quotes can be sent'},
                status=status.HTTP_400_BAD_REQUEST
            )

        quote.status = 'sent'
        quote.save()

        # Here you would typically send an email to the customer
        # For now, we'll just update the status

        return Response({'message': 'Quote sent to customer'})

    @action(detail=True, methods=['post'])
    def mark_as_viewed(self, request, pk=None):
        """Mark quote as viewed by customer"""
        quote = self.get_object()
        quote.mark_as_viewed()
        return Response({'message': 'Quote marked as viewed'})

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Accept the quote"""
        quote = self.get_object()
        notes = request.data.get('notes', '')

        if quote.status not in ['sent', 'viewed']:
            return Response(
                {'error': 'Quote must be sent before it can be accepted'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if quote.is_expired:
            return Response(
                {'error': 'Quote has expired'},
                status=status.HTTP_400_BAD_REQUEST
            )

        quote.accept_quote(notes)

        # Here you could automatically create a job from the quote
        # or send a confirmation email

        return Response({'message': 'Quote accepted successfully'})

    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        """Decline the quote"""
        quote = self.get_object()
        notes = request.data.get('notes', '')

        if quote.status not in ['sent', 'viewed']:
            return Response(
                {'error': 'Quote must be sent before it can be declined'},
                status=status.HTTP_400_BAD_REQUEST
            )

        quote.decline_quote(notes)
        return Response({'message': 'Quote declined'})

    @action(detail=True, methods=['post'])
    def convert_to_job(self, request, pk=None):
        """Convert accepted quote to a job"""
        quote = self.get_object()

        if quote.status != 'accepted':
            return Response(
                {'error': 'Only accepted quotes can be converted to jobs'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            job = quote.convert_to_job()
            return Response({
                'message': 'Quote converted to job successfully',
                'job_id': job.id,
                'job_number': job.job_number
            })
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """Generate PDF version of the quote"""
        quote = self.get_object()

        # This would integrate with a PDF generation library
        # For now, return a placeholder response
        return Response({
            'message': 'PDF generation would be implemented here',
            'quote_number': quote.quote_number
        })

    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        """Get quotes that are expiring soon"""
        days = int(request.query_params.get('days', 7))
        cutoff_date = timezone.now().date() + timedelta(days=days)

        quotes = self.get_queryset().filter(
            status__in=['sent', 'viewed'],
            valid_until__lte=cutoff_date,
            valid_until__gte=timezone.now().date()
        )

        serializer = self.get_serializer(quotes, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def expired(self, request):
        """Get expired quotes"""
        quotes = self.get_queryset().filter(
            status__in=['sent', 'viewed'],
            valid_until__lt=timezone.now().date()
        )

        serializer = self.get_serializer(quotes, many=True)
        return Response(serializer.data)


class QuoteItemViewSet(viewsets.ModelViewSet):
    """ViewSet for managing quote items"""
    queryset = QuoteItem.objects.all()
    serializer_class = QuoteItemSerializer
    permission_classes = [IsAuthenticated, ManagerAndAbove]

    def get_queryset(self):
        queryset = QuoteItem.objects.select_related('quote', 'inventory_item')

        # Filter by quote
        quote = self.request.query_params.get('quote', None)
        if quote:
            queryset = queryset.filter(quote_id=quote)

        # Filter by category
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category=category)

        return queryset


class QuoteTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for managing quote templates"""
    queryset = QuoteTemplate.objects.all()
    serializer_class = QuoteTemplateSerializer
    permission_classes = [IsAuthenticated, ManagerAndAbove]

    def get_queryset(self):
        queryset = QuoteTemplate.objects.filter(is_active=True)

        # Filter by project type
        project_type = self.request.query_params.get('project_type', None)
        if project_type:
            queryset = queryset.filter(project_type=project_type)

        return queryset

    @action(detail=True, methods=['post'])
    def create_quote_from_template(self, request, pk=None):
        """Create a new quote from this template"""
        template = self.get_object()

        customer_id = request.data.get('customer_id')
        project_address = request.data.get('project_address')
        estimated_start_date = request.data.get('estimated_start_date')

        if not customer_id or not project_address:
            return Response(
                {'error': 'customer_id and project_address are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from customers.models import Customer
            customer = Customer.objects.get(id=customer_id)

            quote = template.create_quote_from_template(
                customer=customer,
                project_address=project_address,
                estimated_start_date=estimated_start_date
            )

            serializer = QuoteSerializer(quote)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Customer.DoesNotExist:
            return Response(
                {'error': 'Customer not found'},
                status=status.HTTP_400_BAD_REQUEST
            )


class QuoteSettingsViewSet(viewsets.ModelViewSet):
    """ViewSet for managing quote settings"""
    queryset = QuoteSettings.objects.all()
    serializer_class = QuoteSettingsSerializer
    permission_classes = [IsAuthenticated, ManagerAndAbove]

    def get_queryset(self):
        # There should only be one settings object
        return QuoteSettings.objects.all()

    def list(self, request):
        """Get the global quote settings"""
        settings_obj = QuoteSettings.get_settings()
        serializer = self.get_serializer(settings_obj)
        return Response(serializer.data)

    def create(self, request):
        """Settings should be created automatically"""
        return Response(
            {'error': 'Settings are created automatically'},
            status=status.HTTP_400_BAD_REQUEST
        )

    def retrieve(self, request, pk=None):
        """Get specific settings object"""
        try:
            settings_obj = QuoteSettings.objects.get(pk=pk)
            serializer = self.get_serializer(settings_obj)
            return Response(serializer.data)
        except QuoteSettings.DoesNotExist:
            return Response(
                {'error': 'Settings not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def update(self, request, pk=None):
        """Update quote settings"""
        try:
            settings_obj = QuoteSettings.objects.get(pk=pk)
            serializer = self.get_serializer(settings_obj, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except QuoteSettings.DoesNotExist:
            return Response(
                {'error': 'Settings not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def destroy(self, request, pk=None):
        """Settings should not be deleted"""
        return Response(
            {'error': 'Settings cannot be deleted'},
            status=status.HTTP_400_BAD_REQUEST
        )
