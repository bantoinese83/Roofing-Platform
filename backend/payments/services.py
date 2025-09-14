import logging
import stripe
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from .models import PaymentMethod, Payment, Invoice, PaymentSettings

logger = logging.getLogger(__name__)


class PaymentService:
    """
    Service for handling Stripe payment processing.
    """

    def __init__(self):
        self.settings = PaymentSettings.get_settings()
        stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '') or self.settings.stripe_secret_key

    def create_stripe_customer(self, customer_data: Dict[str, Any]) -> Optional[str]:
        """
        Create a Stripe customer.
        """
        try:
            customer = stripe.Customer.create(
                email=customer_data.get('email'),
                name=customer_data.get('name'),
                phone=customer_data.get('phone'),
                metadata={
                    'customer_id': str(customer_data.get('customer_id', ''))
                }
            )
            return customer.id
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer: {e}")
            return None

    def create_payment_method(self, customer_id: str, payment_method_data: Dict[str, Any]) -> Optional[PaymentMethod]:
        """
        Create and attach a payment method to a customer.
        """
        try:
            # Create PaymentMethod in Stripe
            pm = stripe.PaymentMethod.create(
                type=payment_method_data['type'],
                card=payment_method_data.get('card'),
                billing_details={
                    'name': payment_method_data.get('billing_name'),
                    'email': payment_method_data.get('billing_email'),
                    'phone': payment_method_data.get('billing_phone'),
                }
            )

            # Attach to customer
            stripe.PaymentMethod.attach(
                pm.id,
                customer=customer_id,
            )

            # Create local PaymentMethod record
            payment_method = PaymentMethod.objects.create(
                customer_id=payment_method_data['customer_id'],
                payment_type=payment_method_data['type'],
                stripe_payment_method_id=pm.id,
                stripe_customer_id=customer_id,
                last4=pm.card.last4 if hasattr(pm, 'card') else '',
                brand=pm.card.brand if hasattr(pm, 'card') else '',
                expiry_month=pm.card.exp_month if hasattr(pm, 'card') else None,
                expiry_year=pm.card.exp_year if hasattr(pm, 'card') else None,
                is_default=payment_method_data.get('is_default', False)
            )

            return payment_method

        except stripe.error.StripeError as e:
            logger.error(f"Failed to create payment method: {e}")
            return None

    def create_payment_intent(self, amount: Decimal, currency: str = 'usd',
                            customer_id: str = None, payment_method_id: str = None,
                            metadata: Dict[str, Any] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Create a Stripe PaymentIntent for payment processing.
        """
        try:
            intent_data = {
                'amount': int(amount * 100),  # Convert to cents
                'currency': currency,
                'automatic_payment_methods': {'enabled': True},
                'metadata': metadata or {}
            }

            if customer_id:
                intent_data['customer'] = customer_id

            if payment_method_id:
                intent_data['payment_method'] = payment_method_id
                intent_data['confirm'] = True
                intent_data['return_url'] = getattr(settings, 'PAYMENT_SUCCESS_URL', '')

            intent = stripe.PaymentIntent.create(**intent_data)

            return intent.id, intent.client_secret

        except stripe.error.StripeError as e:
            logger.error(f"Failed to create payment intent: {e}")
            return None, None

    def process_payment(self, payment: Payment) -> bool:
        """
        Process a payment through Stripe.
        """
        try:
            # Get or create Stripe customer
            stripe_customer_id = self._get_or_create_stripe_customer(payment.customer)

            if not stripe_customer_id:
                payment.status = 'failed'
                payment.failure_reason = 'Failed to create Stripe customer'
                payment.save()
                return False

            # Create payment intent
            intent_id, client_secret = self.create_payment_intent(
                payment.amount,
                payment.currency,
                stripe_customer_id,
                metadata={
                    'invoice_id': str(payment.invoice.id),
                    'customer_id': str(payment.customer.id),
                    'payment_id': str(payment.id)
                }
            )

            if not intent_id:
                payment.status = 'failed'
                payment.failure_reason = 'Failed to create payment intent'
                payment.save()
                return False

            payment.stripe_payment_intent_id = intent_id
            payment.status = 'processing'
            payment.save()

            return True

        except Exception as e:
            logger.error(f"Payment processing failed: {e}")
            payment.status = 'failed'
            payment.failure_reason = str(e)
            payment.save()
            return False

    def confirm_payment(self, payment_intent_id: str, payment_method_id: str = None) -> bool:
        """
        Confirm a payment intent.
        """
        try:
            intent = stripe.PaymentIntent.confirm(
                payment_intent_id,
                payment_method=payment_method_id,
                return_url=getattr(settings, 'PAYMENT_SUCCESS_URL', '')
            )

            # Update payment status based on intent status
            payment = Payment.objects.get(stripe_payment_intent_id=payment_intent_id)

            if intent.status == 'succeeded':
                # Get charge details for fee calculation
                charge = stripe.Charge.retrieve(intent.latest_charge) if intent.latest_charge else None

                processing_fee = None
                if charge and hasattr(charge, 'balance_transaction'):
                    balance_txn = stripe.BalanceTransaction.retrieve(charge.balance_transaction)
                    processing_fee = Decimal(balance_txn.fee) / 100  # Convert from cents

                payment.mark_as_succeeded(
                    stripe_charge_id=intent.latest_charge,
                    processing_fee=processing_fee
                )

                logger.info(f"Payment {payment.id} succeeded")
                return True

            elif intent.status in ['requires_payment_method', 'requires_action']:
                payment.status = 'failed'
                payment.failure_reason = 'Payment requires additional action'
                payment.save()

            elif intent.status == 'canceled':
                payment.status = 'cancelled'
                payment.save()

            else:
                payment.status = 'failed'
                payment.failure_reason = f'Payment failed with status: {intent.status}'
                payment.save()

            return False

        except stripe.error.StripeError as e:
            logger.error(f"Payment confirmation failed: {e}")

            try:
                payment = Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
                payment.status = 'failed'
                payment.failure_reason = str(e)
                payment.save()
            except Payment.DoesNotExist:
                pass

            return False

    def process_refund(self, payment: Payment, amount: Decimal = None, reason: str = '') -> bool:
        """
        Process a refund for a payment.
        """
        try:
            if not payment.stripe_charge_id:
                logger.error(f"No Stripe charge ID for payment {payment.id}")
                return False

            refund_amount = amount or payment.amount

            refund = stripe.Refund.create(
                charge=payment.stripe_charge_id,
                amount=int(refund_amount * 100),  # Convert to cents
                reason='requested_by_customer' if 'customer' in reason.lower() else 'duplicate',
                metadata={
                    'original_payment_id': str(payment.id),
                    'reason': reason
                }
            )

            # Update payment status
            payment.status = 'refunded'
            payment.save()

            logger.info(f"Refund processed for payment {payment.id}: ${refund_amount}")
            return True

        except stripe.error.StripeError as e:
            logger.error(f"Refund processing failed: {e}")
            return False

    def create_invoice(self, invoice: Invoice) -> bool:
        """
        Create an invoice in Stripe for tracking purposes.
        """
        try:
            # Get or create Stripe customer
            stripe_customer_id = self._get_or_create_stripe_customer(invoice.customer)

            if not stripe_customer_id:
                return False

            # Create invoice in Stripe
            stripe_invoice = stripe.Invoice.create(
                customer=stripe_customer_id,
                collection_method='send_invoice',
                days_until_due=(invoice.due_date - invoice.issue_date).days,
                metadata={
                    'invoice_id': str(invoice.id),
                    'customer_id': str(invoice.customer.id)
                }
            )

            # Add invoice items
            for item in invoice.items.all():
                stripe.InvoiceItem.create(
                    customer=stripe_customer_id,
                    invoice=stripe_invoice.id,
                    amount=int(item.total_price * 100),
                    currency=invoice.currency.lower(),
                    description=item.description,
                    quantity=int(item.quantity),
                    unit_amount=int(item.unit_price * 100)
                )

            invoice.stripe_invoice_id = stripe_invoice.id
            invoice.save()

            return True

        except stripe.error.StripeError as e:
            logger.error(f"Stripe invoice creation failed: {e}")
            return False

    def _get_or_create_stripe_customer(self, customer) -> Optional[str]:
        """
        Get existing Stripe customer ID or create a new one.
        """
        # Check if customer already has a Stripe ID
        payment_methods = PaymentMethod.objects.filter(customer=customer, is_active=True)
        if payment_methods.exists():
            return payment_methods.first().stripe_customer_id

        # Create new Stripe customer
        stripe_customer_id = self.create_stripe_customer({
            'email': customer.email,
            'name': customer.get_full_name(),
            'phone': customer.phone_number,
            'customer_id': customer.id
        })

        return stripe_customer_id

    def handle_webhook(self, payload: str, signature: str) -> bool:
        """
        Handle Stripe webhook events.
        """
        try:
            # Verify webhook signature
            webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '') or self.settings.stripe_webhook_secret

            if webhook_secret:
                event = stripe.Webhook.construct_event(payload, signature, webhook_secret)
            else:
                # For development, skip signature verification
                import json
                event = json.loads(payload)

            event_type = event['type']
            event_data = event['data']['object']

            if event_type == 'payment_intent.succeeded':
                self._handle_payment_success(event_data)
            elif event_type == 'payment_intent.payment_failed':
                self._handle_payment_failure(event_data)
            elif event_type == 'invoice.payment_succeeded':
                self._handle_invoice_payment(event_data)

            return True

        except Exception as e:
            logger.error(f"Webhook processing failed: {e}")
            return False

    def _handle_payment_success(self, payment_intent_data: Dict[str, Any]):
        """Handle successful payment webhook"""
        intent_id = payment_intent_data['id']

        try:
            payment = Payment.objects.get(stripe_payment_intent_id=intent_id)
            charge_id = payment_intent_data.get('latest_charge')

            if charge_id:
                # Get processing fee
                charge = stripe.Charge.retrieve(charge_id)
                if hasattr(charge, 'balance_transaction'):
                    balance_txn = stripe.BalanceTransaction.retrieve(charge.balance_transaction)
                    processing_fee = Decimal(balance_txn.fee) / 100
                else:
                    processing_fee = None

                payment.mark_as_succeeded(charge_id, processing_fee)

        except Payment.DoesNotExist:
            logger.warning(f"Payment not found for PaymentIntent {intent_id}")

    def _handle_payment_failure(self, payment_intent_data: Dict[str, Any]):
        """Handle failed payment webhook"""
        intent_id = payment_intent_data['id']

        try:
            payment = Payment.objects.get(stripe_payment_intent_id=intent_id)
            payment.status = 'failed'
            payment.failure_reason = payment_intent_data.get('last_payment_error', {}).get('message', 'Payment failed')
            payment.save()

        except Payment.DoesNotExist:
            logger.warning(f"Payment not found for PaymentIntent {intent_id}")

    def _handle_invoice_payment(self, invoice_data: Dict[str, Any]):
        """Handle invoice payment webhook"""
        stripe_invoice_id = invoice_data['id']

        try:
            invoice = Invoice.objects.get(stripe_invoice_id=stripe_invoice_id)
            if invoice_data['status'] == 'paid':
                invoice.mark_as_paid()

        except Invoice.DoesNotExist:
            logger.warning(f"Invoice not found for Stripe invoice {stripe_invoice_id}")

    def get_payment_stats(self) -> Dict[str, Any]:
        """Get payment processing statistics"""
        today = timezone.now().date()
        this_month = today.replace(day=1)

        # Today's payments
        today_payments = Payment.objects.filter(
            created_at__date=today
        ).aggregate(
            total_amount=models.Sum('amount'),
            count=models.Count('id')
        )

        # Monthly payments
        monthly_payments = Payment.objects.filter(
            created_at__date__gte=this_month
        ).aggregate(
            total_amount=models.Sum('amount'),
            count=models.Count('id')
        )

        # Success rate
        total_payments = Payment.objects.filter(
            created_at__date__gte=this_month
        ).count()

        successful_payments = Payment.objects.filter(
            created_at__date__gte=this_month,
            status='succeeded'
        ).count()

        success_rate = (successful_payments / total_payments * 100) if total_payments > 0 else 0

        return {
            'today_total': today_payments['total_amount'] or 0,
            'today_count': today_payments['count'] or 0,
            'monthly_total': monthly_payments['total_amount'] or 0,
            'monthly_count': monthly_payments['count'] or 0,
            'success_rate': round(success_rate, 1),
            'pending_payments': Payment.objects.filter(status='pending').count(),
            'failed_payments': Payment.objects.filter(status='failed').count()
        }


# Global service instance (lazy initialization)
_payment_service = None

def get_payment_service():
    """Get the global payment service instance"""
    global _payment_service
    if _payment_service is None:
        _payment_service = PaymentService()
    return _payment_service

# For backward compatibility - use get_payment_service() instead
