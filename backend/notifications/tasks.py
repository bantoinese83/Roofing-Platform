import logging
from celery import shared_task
from django.utils import timezone
from .models import NotificationLog, NotificationTemplate, NotificationSettings
from .services import NotificationService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_notification_task(self, notification_id: int):
    """
    Send a single notification.
    """
    try:
        notification = NotificationLog.objects.get(id=notification_id)

        if notification.notification_type == 'sms':
            result = NotificationService.send_sms_via_twilio(
                notification.recipient_phone,
                notification.content
            )
        elif notification.notification_type == 'email':
            result = NotificationService.send_email_via_sendgrid(
                notification.recipient_email,
                notification.subject,
                notification.content
            )
        else:
            raise ValueError(f"Unknown notification type: {notification.notification_type}")

        if result['success']:
            notification.mark_as_sent(result.get('external_id'))
            logger.info(f"Notification {notification_id} sent successfully")
        else:
            notification.mark_as_failed(result.get('error'))
            logger.error(f"Notification {notification_id} failed: {result.get('error')}")

    except NotificationLog.DoesNotExist:
        logger.error(f"Notification {notification_id} not found")
    except Exception as e:
        logger.error(f"Notification task failed: {e}")
        # Retry with exponential backoff
        raise self.retry(countdown=60 * (2 ** self.request.retries), exc=e)


@shared_task
def send_scheduled_notifications():
    """
    Send scheduled notifications (reminders, etc.).
    """
    logger.info("Running scheduled notifications task")

    settings = NotificationSettings.get_settings()
    now = timezone.now()

    # Send appointment reminders
    if settings.enable_appointment_reminders:
        hours_before = settings.reminder_hours_before

        # Find jobs that need reminders
        from jobs.models import Job
        reminder_time = now + timezone.timedelta(hours=hours_before)

        jobs_needing_reminders = Job.objects.filter(
            scheduled_date=reminder_time.date(),
            scheduled_time__gte=reminder_time.time(),
            scheduled_time__lt=(reminder_time + timezone.timedelta(minutes=30)).time(),
            status__in=['scheduled', 'dispatched']
        ).select_related('customer')

        for job in jobs_needing_reminders:
            try:
                template = NotificationTemplate.objects.get(
                    template_type='appointment_reminder',
                    notification_method='sms',
                    is_active=True
                )

                notification_service = NotificationService()
                notification_service.send_notification(
                    'appointment_reminder',
                    'sms',
                    recipient_phone=job.customer.phone_number,
                    job=job,
                    customer=job.customer,
                    context_data={'hours_until': hours_before}
                )

                logger.info(f"Sent reminder for job {job.job_number}")

            except NotificationTemplate.DoesNotExist:
                logger.warning("Appointment reminder template not found")
            except Exception as e:
                logger.error(f"Failed to send reminder for job {job.job_number}: {e}")

    # Check for failed notifications to retry
    failed_notifications = NotificationLog.objects.filter(
        status__in=['failed', 'bounced'],
        retry_count__lt=3,
        next_retry_at__lte=now
    )

    for notification in failed_notifications:
        if notification.can_retry():
            if notification.notification_type == 'sms':
                send_sms_notification.delay(notification.id)
            elif notification.notification_type == 'email':
                send_email_notification.delay(notification.id)


@shared_task
def cleanup_old_notification_logs():
    """
    Clean up old notification logs based on settings.
    """
    settings = NotificationSettings.get_settings()
    days_to_keep = settings.cleanup_old_logs_days

    cutoff_date = timezone.now() - timezone.timedelta(days=days_to_keep)

    deleted_count, _ = NotificationLog.objects.filter(
        created_at__lt=cutoff_date
    ).delete()

    logger.info(f"Cleaned up {deleted_count} old notification logs")


@shared_task
def send_bulk_notifications_task(
    template_id: int,
    job_ids: list = None,
    customer_ids: list = None,
    technician_ids: list = None,
    custom_recipients: list = None,
    context_overrides: dict = None,
    created_by_id: int = None
):
    """
    Send bulk notifications to multiple recipients.
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()
    created_by = User.objects.get(id=created_by_id) if created_by_id else None

    notification_service = NotificationService()
    notifications = notification_service.send_bulk_notifications(
        template_id=template_id,
        job_ids=job_ids,
        customer_ids=customer_ids,
        technician_ids=technician_ids,
        custom_recipients=custom_recipients,
        context_overrides=context_overrides,
        created_by=created_by
    )

    logger.info(f"Sent {len(notifications)} bulk notifications")


# Legacy task names for backward compatibility
send_sms_notification = send_notification_task
send_email_notification = send_notification_task
