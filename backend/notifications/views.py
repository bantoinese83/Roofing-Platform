from rest_framework import generics, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Count, Q
from .models import NotificationTemplate, NotificationLog, NotificationSettings
from .serializers import (
    NotificationTemplateSerializer,
    NotificationLogSerializer,
    NotificationSettingsSerializer,
    NotificationStatsSerializer,
    BulkNotificationSerializer,
    NotificationTemplateTestSerializer
)
from .services import NotificationService
from accounts.permissions import ManagerAndAbove


class NotificationTemplateListCreateView(generics.ListCreateAPIView):
    """
    List all notification templates or create a new one.
    """
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [ManagerAndAbove]

    def get_queryset(self):
        """Filter templates by type and method"""
        queryset = super().get_queryset()

        template_type = self.request.query_params.get('type')
        if template_type:
            queryset = queryset.filter(template_type=template_type)

        method = self.request.query_params.get('method')
        if method:
            queryset = queryset.filter(notification_method=method)

        active_only = self.request.query_params.get('active_only')
        if active_only == 'true':
            queryset = queryset.filter(is_active=True)

        return queryset.order_by('template_type', 'notification_method')


class NotificationTemplateDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a notification template.
    """
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [ManagerAndAbove]


class NotificationTemplateTestView(APIView):
    """
    Test a notification template with sample data.
    """
    permission_classes = [ManagerAndAbove]

    def post(self, request):
        """Test template rendering"""
        serializer = NotificationTemplateTestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        template = get_object_or_404(NotificationTemplate, id=data['template_id'])

        service = NotificationService()
        context = service._prepare_context_data(data['test_data'])

        try:
            rendered_content = template.render_content(context)
            rendered_subject = template.render_subject(context)

            return Response({
                'template_name': template.name,
                'notification_method': template.notification_method,
                'subject': rendered_subject,
                'content': rendered_content,
                'recipient_email': data.get('recipient_email'),
                'recipient_phone': data.get('recipient_phone'),
            })
        except Exception as e:
            return Response(
                {'error': f'Template rendering failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class NotificationLogListView(generics.ListAPIView):
    """
    List notification logs with filtering and search.
    """
    serializer_class = NotificationLogSerializer
    permission_classes = [ManagerAndAbove]

    def get_queryset(self):
        """Filter notification logs"""
        queryset = NotificationLog.objects.select_related(
            'job', 'customer', 'technician', 'template', 'created_by'
        )

        # Filter by type
        notification_type = self.request.query_params.get('type')
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)

        # Filter by status
        log_status = self.request.query_params.get('status')
        if log_status:
            queryset = queryset.filter(status=log_status)

        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)

        # Filter by recipient
        recipient = self.request.query_params.get('recipient')
        if recipient:
            queryset = queryset.filter(
                Q(recipient_email__icontains=recipient) |
                Q(recipient_phone__icontains=recipient)
            )

        # Filter by job
        job_id = self.request.query_params.get('job_id')
        if job_id:
            queryset = queryset.filter(job_id=job_id)

        return queryset.order_by('-created_at')


class NotificationLogDetailView(generics.RetrieveAPIView):
    """
    Retrieve a notification log entry.
    """
    queryset = NotificationLog.objects.select_related(
        'job', 'customer', 'technician', 'template', 'created_by'
    )
    serializer_class = NotificationLogSerializer
    permission_classes = [ManagerAndAbove]


class NotificationStatsView(APIView):
    """
    Get notification statistics.
    """
    permission_classes = [ManagerAndAbove]

    def get(self, request):
        """Get notification statistics"""
        today = timezone.now().date()

        # Total counts
        total_sent = NotificationLog.objects.filter(status='sent').count()
        total_failed = NotificationLog.objects.filter(status__in=['failed', 'bounced']).count()
        total_pending = NotificationLog.objects.filter(status='pending').count()

        # Today's counts
        sms_sent_today = NotificationLog.objects.filter(
            notification_type='sms',
            status='sent',
            created_at__date=today
        ).count()

        email_sent_today = NotificationLog.objects.filter(
            notification_type='email',
            status='sent',
            created_at__date=today
        ).count()

        # Rates
        total_notifications = total_sent + total_failed
        delivery_rate = (total_sent / total_notifications * 100) if total_notifications > 0 else 0
        failure_rate = (total_failed / total_notifications * 100) if total_notifications > 0 else 0

        data = {
            'total_sent': total_sent,
            'total_failed': total_failed,
            'total_pending': total_pending,
            'sms_sent_today': sms_sent_today,
            'email_sent_today': email_sent_today,
            'delivery_rate': round(delivery_rate, 2),
            'failure_rate': round(failure_rate, 2),
        }

        serializer = NotificationStatsSerializer(data)
        return Response(serializer.data)


class NotificationSettingsView(generics.RetrieveUpdateAPIView):
    """
    Get or update global notification settings.
    """
    serializer_class = NotificationSettingsSerializer
    permission_classes = [ManagerAndAbove]

    def get_object(self):
        return NotificationSettings.get_settings()


class BulkNotificationView(APIView):
    """
    Send bulk notifications to multiple recipients.
    """
    permission_classes = [ManagerAndAbove]

    def post(self, request):
        """Send bulk notifications"""
        serializer = BulkNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        service = NotificationService()
        notifications = service.send_bulk_notifications(
            template_id=data['template_id'],
            job_ids=data.get('job_ids'),
            customer_ids=data.get('customer_ids'),
            technician_ids=data.get('technician_ids'),
            custom_recipients=data.get('custom_recipients'),
            context_overrides=data.get('context_overrides'),
            created_by=request.user
        )

        return Response({
            'message': f'Sent {len(notifications)} notifications',
            'notification_ids': [n.id for n in notifications]
        })


class NotificationRetryView(APIView):
    """
    Retry failed notifications.
    """
    permission_classes = [ManagerAndAbove]

    def post(self, request, notification_id):
        """Retry a failed notification"""
        notification = get_object_or_404(NotificationLog, id=notification_id)

        if not notification.can_retry():
            return Response(
                {'error': 'Notification cannot be retried'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Reset status and trigger resend
        notification.status = 'pending'
        notification.save()

        from .tasks import send_notification_task
        send_notification_task.delay(notification.id)

        return Response({'message': 'Notification queued for retry'})


class TriggerNotificationView(APIView):
    """
    Manually trigger notifications for jobs or events.
    """
    permission_classes = [ManagerAndAbove]

    def post(self, request):
        """Trigger notifications based on criteria"""
        trigger_type = request.data.get('trigger_type')
        template_type = request.data.get('template_type')
        notification_method = request.data.get('notification_method', 'sms')

        if not trigger_type or not template_type:
            return Response(
                {'error': 'trigger_type and template_type are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = NotificationService()
        sent_count = 0

        if trigger_type == 'job_status':
            # Send notifications for jobs with specific status
            job_status = request.data.get('job_status')
            if not job_status:
                return Response(
                    {'error': 'job_status is required for job_status trigger'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            from jobs.models import Job
            jobs = Job.objects.filter(status=job_status).select_related('customer')

            for job in jobs:
                notification = service.send_notification(
                    template_type,
                    notification_method,
                    recipient_phone=job.customer.phone_number,
                    job=job,
                    customer=job.customer,
                    created_by=request.user
                )
                if notification:
                    sent_count += 1

        elif trigger_type == 'appointment_reminders':
            # Send appointment reminders for upcoming jobs
            hours_before = request.data.get('hours_before', 24)

            from jobs.models import Job
            from django.utils import timezone
            reminder_time = timezone.now() + timezone.timedelta(hours=hours_before)

            jobs = Job.objects.filter(
                scheduled_date=reminder_time.date(),
                scheduled_time__range=(
                    reminder_time.time(),
                    (reminder_time + timezone.timedelta(minutes=30)).time()
                ),
                status__in=['scheduled', 'dispatched']
            ).select_related('customer')

            for job in jobs:
                notification = service.send_notification(
                    template_type,
                    notification_method,
                    recipient_phone=job.customer.phone_number,
                    job=job,
                    customer=job.customer,
                    context_data={'hours_until': hours_before},
                    created_by=request.user
                )
                if notification:
                    sent_count += 1

        return Response({
            'message': f'Sent {sent_count} notifications',
            'trigger_type': trigger_type,
            'template_type': template_type
        })
