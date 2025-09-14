from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Job


@receiver(post_save, sender=Job)
def send_job_notifications(sender, instance, created, **kwargs):
    """
    Send notifications when jobs are created or updated.
    """
    if created:
        # Send job created notifications
        _send_job_created_notifications(instance)
    else:
        # Check if status changed
        if instance.status != instance._original_status:
            _send_job_status_notifications(instance)


def _send_job_created_notifications(job):
    """
    Send notifications when a job is created.
    """
    from notifications.models import NotificationTemplate
    from notifications.services import notification_service

    templates = NotificationTemplate.objects.filter(
        trigger_on_job_create=True,
        is_active=True
    )

    for template in templates:
        try:
            notification_service.send_notification(
                template.template_type,
                template.notification_method,
                recipient_phone=job.customer.phone_number if template.send_to_customer else None,
                recipient_email=job.customer.email if template.send_to_customer and template.notification_method == 'email' else None,
                job=job,
                customer=job.customer
            )
        except Exception as e:
            # Log error but don't break the job save
            print(f"Failed to send job created notification: {e}")


def _send_job_status_notifications(job):
    """
    Send notifications when job status changes.
    """
    from notifications.models import NotificationTemplate
    from notifications.services import notification_service

    templates = NotificationTemplate.objects.filter(
        trigger_on_status_change=True,
        is_active=True
    )

    for template in templates:
        # Check if this status should trigger the notification
        trigger_statuses = template.trigger_statuses or []
        if job.status not in trigger_statuses:
            continue

        try:
            # Customer notifications
            if template.send_to_customer and job.customer:
                notification_service.send_notification(
                    template.template_type,
                    template.notification_method,
                    recipient_phone=job.customer.phone_number if template.notification_method == 'sms' else None,
                    recipient_email=job.customer.email if template.notification_method == 'email' else None,
                    job=job,
                    customer=job.customer,
                    context_data={
                        'old_status': job._original_status,
                        'new_status': job.status
                    }
                )

            # Technician notifications
            if template.send_to_technician:
                for technician in job.assigned_technicians.all():
                    notification_service.send_notification(
                        template.template_type,
                        template.notification_method,
                        recipient_phone=technician.user.phone_number if template.notification_method == 'sms' else None,
                        recipient_email=technician.user.email if template.notification_method == 'email' else None,
                        job=job,
                        technician=technician,
                        context_data={
                            'old_status': job._original_status,
                            'new_status': job.status
                        }
                    )

        except Exception as e:
            # Log error but don't break the job save
            print(f"Failed to send job status notification: {e}")


def _track_original_status(sender, instance, **kwargs):
    """
    Track the original status before save for comparison.
    """
    if instance.pk:
        try:
            original = Job.objects.get(pk=instance.pk)
            instance._original_status = original.status
        except Job.DoesNotExist:
            instance._original_status = instance.status
    else:
        instance._original_status = instance.status


# Connect the signal to track original status
from django.db.models.signals import pre_save
pre_save.connect(_track_original_status, sender=Job)
