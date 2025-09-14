import logging
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.utils import timezone
from django.template import Template, Context
from .models import NotificationTemplate, NotificationLog, NotificationSettings

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for managing and sending notifications.
    """

    def __init__(self):
        self.settings = NotificationSettings.get_settings()

    def send_notification(
        self,
        template_type: str,
        notification_method: str,
        recipient_email: str = None,
        recipient_phone: str = None,
        context_data: Dict[str, Any] = None,
        job=None,
        customer=None,
        technician=None,
        created_by=None
    ) -> NotificationLog:
        """
        Send a notification using the specified template.
        """
        try:
            # Get the template
            template = NotificationTemplate.objects.get(
                template_type=template_type,
                notification_method=notification_method,
                is_active=True
            )
        except NotificationTemplate.DoesNotExist:
            logger.error(f"Template not found: {template_type} - {notification_method}")
            return None

        # Prepare context data
        context = self._prepare_context_data(context_data or {}, job, customer, technician)

        # Render content
        try:
            content = template.render_content(context)
            subject = template.render_subject(context) if template.subject else ""
        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            return None

        # Create notification log
        notification_log = NotificationLog.objects.create(
            job=job,
            customer=customer,
            technician=technician,
            notification_type=notification_method,
            template=template,
            recipient_email=recipient_email,
            recipient_phone=recipient_phone,
            subject=subject,
            content=content,
            created_by=created_by
        )

        # Send the notification asynchronously
        if notification_method == 'sms':
            self._send_sms_notification.delay(notification_log.id)
        elif notification_method == 'email':
            self._send_email_notification.delay(notification_log.id)

        return notification_log

    def send_bulk_notifications(
        self,
        template_id: int,
        job_ids: List[int] = None,
        customer_ids: List[int] = None,
        technician_ids: List[int] = None,
        custom_recipients: List[Dict] = None,
        context_overrides: Dict[str, Any] = None,
        created_by=None
    ) -> List[NotificationLog]:
        """
        Send bulk notifications to multiple recipients.
        """
        from jobs.models import Job
        from customers.models import Customer
        from technicians.models import TechnicianProfile

        notifications = []

        try:
            template = NotificationTemplate.objects.get(id=template_id, is_active=True)
        except NotificationTemplate.DoesNotExist:
            logger.error(f"Template not found: {template_id}")
            return []

        # Process jobs
        if job_ids:
            jobs = Job.objects.filter(id__in=job_ids).select_related('customer')
            for job in jobs:
                context = self._prepare_context_data(context_overrides or {}, job=job)
                notifications.extend(self._create_notifications_for_job(
                    job, template, context, created_by
                ))

        # Process customers
        if customer_ids:
            customers = Customer.objects.filter(id__in=customer_ids)
            for customer in customers:
                context = self._prepare_context_data(context_overrides or {}, customer=customer)
                notifications.extend(self._create_notifications_for_customer(
                    customer, template, context, created_by
                ))

        # Process technicians
        if technician_ids:
            technicians = TechnicianProfile.objects.filter(id__in=technician_ids).select_related('user')
            for technician in technicians:
                context = self._prepare_context_data(context_overrides or {}, technician=technician)
                notifications.extend(self._create_notifications_for_technician(
                    technician, template, context, created_by
                ))

        # Process custom recipients
        if custom_recipients:
            for recipient in custom_recipients:
                context = self._prepare_context_data(
                    {**(context_overrides or {}), **recipient.get('context', {})},
                    recipient.get('job'),
                    recipient.get('customer'),
                    recipient.get('technician')
                )

                notification_log = NotificationLog.objects.create(
                    job=recipient.get('job'),
                    customer=recipient.get('customer'),
                    technician=recipient.get('technician'),
                    notification_type=template.notification_method,
                    template=template,
                    recipient_email=recipient.get('email'),
                    recipient_phone=recipient.get('phone'),
                    subject=template.render_subject(context),
                    content=template.render_content(context),
                    created_by=created_by
                )
                notifications.append(notification_log)

        # Send notifications asynchronously
        for notification in notifications:
            if notification.notification_type == 'sms':
                self._send_sms_notification.delay(notification.id)
            elif notification.notification_type == 'email':
                self._send_email_notification.delay(notification.id)

        return notifications

    def _prepare_context_data(self, context_data: Dict[str, Any], job=None, customer=None, technician=None) -> Dict[str, Any]:
        """
        Prepare context data for template rendering.
        """
        context = {
            'company_name': self.settings.company_name,
            'company_phone': self.settings.company_phone,
            'company_website': self.settings.company_website,
            'current_date': timezone.now().date(),
            'current_time': timezone.now().time(),
        }

        # Add job data
        if job:
            context.update({
                'job_title': job.title,
                'job_number': job.job_number,
                'job_type': job.get_job_type_display(),
                'job_status': job.get_status_display(),
                'scheduled_date': job.scheduled_date,
                'scheduled_time': job.scheduled_time,
                'job_address': job.address,
                'estimated_cost': job.estimated_cost,
                'special_instructions': job.special_instructions,
            })

        # Add customer data
        if customer:
            context.update({
                'customer_name': customer.get_full_name(),
                'customer_email': customer.email,
                'customer_phone': customer.phone_number or customer.alt_phone_number,
                'customer_address': customer.primary_address.get_full_address() if customer.primary_address else '',
            })

        # Add technician data
        if technician:
            context.update({
                'technician_name': technician.full_name,
                'technician_email': technician.user.email,
                'technician_phone': technician.user.phone_number,
            })

        # Override with provided context data
        context.update(context_data)

        return context

    def _create_notifications_for_job(self, job, template, context, created_by) -> List[NotificationLog]:
        """Create notifications for a job based on template settings."""
        notifications = []

        # Customer notifications
        if template.send_to_customer and job.customer:
            notification_log = NotificationLog.objects.create(
                job=job,
                customer=job.customer,
                notification_type=template.notification_method,
                template=template,
                recipient_email=job.customer.email if template.notification_method == 'email' else None,
                recipient_phone=job.customer.phone_number if template.notification_method == 'sms' else None,
                subject=template.render_subject(context),
                content=template.render_content(context),
                created_by=created_by
            )
            notifications.append(notification_log)

        # Technician notifications
        if template.send_to_technician:
            for technician in job.assigned_technicians.all():
                tech_context = context.copy()
                tech_context.update({
                    'technician_name': technician.full_name,
                    'technician_email': technician.user.email,
                    'technician_phone': technician.user.phone_number,
                })

                notification_log = NotificationLog.objects.create(
                    job=job,
                    technician=technician,
                    notification_type=template.notification_method,
                    template=template,
                    recipient_email=technician.user.email if template.notification_method == 'email' else None,
                    recipient_phone=technician.user.phone_number if template.notification_method == 'sms' else None,
                    subject=template.render_subject(tech_context),
                    content=template.render_content(tech_context),
                    created_by=created_by
                )
                notifications.append(notification_log)

        return notifications

    def _create_notifications_for_customer(self, customer, template, context, created_by) -> List[NotificationLog]:
        """Create notifications for a customer."""
        notifications = []

        notification_log = NotificationLog.objects.create(
            customer=customer,
            notification_type=template.notification_method,
            template=template,
            recipient_email=customer.email if template.notification_method == 'email' else None,
            recipient_phone=customer.phone_number if template.notification_method == 'sms' else None,
            subject=template.render_subject(context),
            content=template.render_content(context),
            created_by=created_by
        )
        notifications.append(notification_log)

        return notifications

    def _create_notifications_for_technician(self, technician, template, context, created_by) -> List[NotificationLog]:
        """Create notifications for a technician."""
        notifications = []

        notification_log = NotificationLog.objects.create(
            technician=technician,
            notification_type=template.notification_method,
            template=template,
            recipient_email=technician.user.email if template.notification_method == 'email' else None,
            recipient_phone=technician.user.phone_number if template.notification_method == 'sms' else None,
            subject=template.render_subject(context),
            content=template.render_content(context),
            created_by=created_by
        )
        notifications.append(notification_log)

        return notifications

    @staticmethod
    def send_sms_via_twilio(to_phone: str, message: str) -> Dict[str, Any]:
        """
        Send SMS via Twilio.
        """
        try:
            from twilio.rest import Client
            from notifications.models import NotificationSettings

            settings = NotificationSettings.get_settings()

            if not all([
                settings.twilio_account_sid,
                settings.twilio_auth_token,
                settings.twilio_phone_number
            ]):
                raise ValueError("Twilio settings not configured")

            client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

            message_obj = client.messages.create(
                body=message,
                from_=settings.twilio_phone_number,
                to=to_phone
            )

            return {
                'success': True,
                'external_id': message_obj.sid,
                'status': message_obj.status
            }

        except Exception as e:
            logger.error(f"Twilio SMS failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def send_email_via_sendgrid(to_email: str, subject: str, content: str) -> Dict[str, Any]:
        """
        Send email via SendGrid.
        """
        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail, Email, To, Content
            from notifications.models import NotificationSettings

            settings = NotificationSettings.get_settings()

            if not all([
                settings.sendgrid_api_key,
                settings.sendgrid_from_email
            ]):
                raise ValueError("SendGrid settings not configured")

            sg = sendgrid.SendGridAPIClient(api_key=settings.sendgrid_api_key)

            from_email = Email(settings.sendgrid_from_email)
            if settings.sendgrid_from_name:
                from_email.name = settings.sendgrid_from_name

            to_email_obj = To(to_email)
            subject_obj = subject
            content_obj = Content("text/plain", content)

            mail = Mail(from_email, to_email_obj, subject_obj, content_obj)

            response = sg.client.mail.send.post(request_body=mail.get())

            return {
                'success': response.status_code == 202,
                'external_id': response.headers.get('X-Message-Id', ''),
                'status_code': response.status_code
            }

        except Exception as e:
            logger.error(f"SendGrid email failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def _send_sms_notification(notification_id: int):
        """
        Celery task to send SMS notification.
        """
        try:
            notification = NotificationLog.objects.get(id=notification_id)

            if notification.recipient_phone and notification.content:
                result = NotificationService.send_sms_via_twilio(
                    notification.recipient_phone,
                    notification.content
                )

                if result['success']:
                    notification.mark_as_sent(result.get('external_id'))
                else:
                    notification.mark_as_failed(result.get('error'))

        except Exception as e:
            logger.error(f"SMS notification task failed: {e}")

    @staticmethod
    def _send_email_notification(notification_id: int):
        """
        Celery task to send email notification.
        """
        try:
            notification = NotificationLog.objects.get(id=notification_id)

            if notification.recipient_email and notification.content:
                result = NotificationService.send_email_via_sendgrid(
                    notification.recipient_email,
                    notification.subject,
                    notification.content
                )

                if result['success']:
                    notification.mark_as_sent(result.get('external_id'))
                else:
                    notification.mark_as_failed(result.get('error'))

        except Exception as e:
            logger.error(f"Email notification task failed: {e}")


# Global service instance
notification_service = NotificationService()
