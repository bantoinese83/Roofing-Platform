from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from decimal import Decimal

from .models import PaymentMethod, Invoice, Payment, PaymentSettings
from .serializers import (
    PaymentMethodSerializer, InvoiceSerializer, InvoiceCreateSerializer,
    PaymentSerializer, PaymentIntentSerializer, PaymentSettingsSerializer
)
from .services import get_payment_service
from accounts.permissions import ManagerAndAbove


class PaymentMethodViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing customer payment methods.
    """
    permission_classes = [IsAuthenticated, ManagerAndAbove]
    serializer_class = PaymentMethodSerializer

    def get_queryset(self):
        queryset = PaymentMethod.objects.select_related('customer', 'created_by')

        # Filter by customer if specified
        customer_id = self.request.query_params.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)

        return queryset.order_by('-is_default', '-created_at')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """
        Set this payment method as the default for the customer.
        """
        payment_method = self.get_object()
        payment_method.is_default = True
        payment_method.save()

        serializer = self.get_serializer(payment_method)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def detach(self, request, pk=None):
        """
        Detach payment method from Stripe and mark as inactive.
        """
        payment_method = self.get_object()
        payment_method.is_active = False
        payment_method.save()

        # TODO: Call Stripe API to detach payment method

        serializer = self.get_serializer(payment_method)
        return Response(serializer.data)


class InvoiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing invoices.
    """
    permission_classes = [IsAuthenticated, ManagerAndAbove]

    def get_queryset(self):
        queryset = Invoice.objects.select_related('customer', 'job', 'created_by')

        # Filter by customer if specified
        customer_id = self.request.query_params.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by('-issue_date', '-created_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return InvoiceCreateSerializer
        return InvoiceSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """
        Send invoice to customer via email.
        """
        invoice = self.get_object()
        success = invoice.send_to_customer()

        if success:
            return Response({'message': 'Invoice sent successfully'})
        else:
            return Response(
                {'error': 'Failed to send invoice'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """
        Generate PDF version of invoice.
        """
        invoice = self.get_object()
        # TODO: Implement PDF generation
        return Response({'message': 'PDF generation not yet implemented'})

    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        """
        Finalize draft invoice.
        """
        invoice = self.get_object()
        if invoice.status != 'draft':
            return Response(
                {'error': 'Only draft invoices can be finalized'},
                status=status.HTTP_400_BAD_REQUEST
            )

        invoice.status = 'sent'
        invoice.save()

        serializer = self.get_serializer(invoice)
        return Response(serializer.data)


class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing payments.
    """
    permission_classes = [IsAuthenticated, ManagerAndAbove]
    serializer_class = PaymentSerializer

    def get_queryset(self):
        queryset = Payment.objects.select_related('invoice', 'customer', 'payment_method', 'created_by')

        # Filter by invoice if specified
        invoice_id = self.request.query_params.get('invoice')
        if invoice_id:
            queryset = queryset.filter(invoice_id=invoice_id)

        # Filter by customer
        customer_id = self.request.query_params.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)

        return queryset.order_by('-payment_date', '-created_at')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """
        Process the payment through Stripe.
        """
        payment = self.get_object()
        success = get_payment_service().process_payment(payment)

        if success:
            serializer = self.get_serializer(payment)
            return Response(serializer.data)
        else:
            return Response(
                {'error': 'Payment processing failed'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def refund(self, request, pk=None):
        """
        Process a refund for the payment.
        """
        payment = self.get_object()
        amount = request.data.get('amount')
        reason = request.data.get('reason', '')

        refund_amount = Decimal(amount) if amount else None
        success = get_payment_service().process_refund(payment, refund_amount, reason)

        if success:
            serializer = self.get_serializer(payment)
            return Response(serializer.data)
        else:
            return Response(
                {'error': 'Refund processing failed'},
                status=status.HTTP_400_BAD_REQUEST
            )


class PaymentSettingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing payment settings.
    """
    permission_classes = [IsAuthenticated, ManagerAndAbove]
    serializer_class = PaymentSettingsSerializer

    def get_queryset(self):
        # PaymentSettings is a singleton, so return all (should be one)
        return PaymentSettings.objects.all()

    def get_object(self):
        # Return the singleton settings object
        return PaymentSettings.get_settings()

    def list(self, request, *args, **kwargs):
        """
        Get the global payment settings.
        """
        settings = PaymentSettings.get_settings()
        serializer = self.get_serializer(settings)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Create is not allowed for singleton settings.
        """
        return Response(
            {'error': 'Settings already exist. Use PUT to update.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def destroy(self, request, *args, **kwargs):
        """
        Delete is not allowed for singleton settings.
        """
        return Response(
            {'error': 'Cannot delete global settings.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_payment_intent(request):
    """
    Create a Stripe PaymentIntent for frontend payment processing.
    """
    serializer = PaymentIntentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    amount = serializer.validated_data['amount']
    currency = serializer.validated_data.get('currency', 'usd')
    customer_id = serializer.validated_data.get('customer_id')
    payment_method_id = serializer.validated_data.get('payment_method_id')
    metadata = serializer.validated_data.get('metadata', {})

    intent_id, client_secret = get_payment_service().create_payment_intent(
        amount, currency, customer_id, payment_method_id, metadata
    )

    if intent_id and client_secret:
        return Response({
            'payment_intent_id': intent_id,
            'client_secret': client_secret
        })
    else:
        return Response(
            {'error': 'Failed to create payment intent'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def stripe_webhook(request):
    """
    Handle Stripe webhook events.
    """
    payload = request.body.decode('utf-8')
    signature = request.headers.get('stripe-signature', '')

    success = get_payment_service().handle_webhook(payload, signature)

    if success:
        return Response({'status': 'success'})
    else:
        return Response(
            {'error': 'Webhook processing failed'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_stats(request):
    """
    Get payment processing statistics.
    """
    stats = get_payment_service().get_payment_stats()
    return Response(stats)
