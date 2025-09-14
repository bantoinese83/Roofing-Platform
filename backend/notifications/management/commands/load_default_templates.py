from django.core.management.base import BaseCommand
from notifications.models import NotificationTemplate


class Command(BaseCommand):
    help = 'Load default notification templates'

    def handle(self, *args, **options):
        templates_data = [
            # SMS Templates
            {
                'name': 'Appointment Confirmation - SMS',
                'template_type': 'appointment_confirmation',
                'notification_method': 'sms',
                'subject': '',
                'content': 'Hi {{customer_name}}! Your {{job_title}} appointment is confirmed for {{scheduled_date}} at {{scheduled_time}}. {{company_name}} - {{company_phone}}',
                'is_active': True,
                'send_to_customer': True,
                'trigger_on_job_create': True,
            },
            {
                'name': 'Appointment Reminder - SMS',
                'template_type': 'appointment_reminder',
                'notification_method': 'sms',
                'subject': '',
                'content': 'Hi {{customer_name}}! Reminder: Your {{job_title}} is scheduled for tomorrow at {{scheduled_time}}. {{company_name}} - {{company_phone}}',
                'is_active': True,
                'send_before_hours': 24,
                'send_to_customer': True,
            },
            {
                'name': 'Job Status Update - SMS',
                'template_type': 'job_status_update',
                'notification_method': 'sms',
                'subject': '',
                'content': 'Hi {{customer_name}}! Your {{job_title}} status changed from {{old_status}} to {{new_status}}. {{company_name}}',
                'is_active': True,
                'send_to_customer': True,
                'trigger_on_status_change': True,
                'trigger_statuses': ['dispatched', 'in_progress', 'completed', 'cancelled'],
            },
            {
                'name': 'Job Assigned to Technician - SMS',
                'template_type': 'job_assigned',
                'notification_method': 'sms',
                'subject': '',
                'content': 'Hi {{technician_name}}! You have been assigned to {{job_title}} for {{customer_name}} on {{scheduled_date}} at {{scheduled_time}}.',
                'is_active': True,
                'send_to_technician': True,
                'trigger_on_job_update': True,
            },
            {
                'name': 'Job Completed - SMS',
                'template_type': 'job_completed',
                'notification_method': 'sms',
                'subject': '',
                'content': 'Hi {{customer_name}}! Your {{job_title}} has been completed. Thank you for choosing {{company_name}}!',
                'is_active': True,
                'send_to_customer': True,
                'trigger_on_status_change': True,
                'trigger_statuses': ['completed'],
            },

            # Email Templates
            {
                'name': 'Appointment Confirmation - Email',
                'template_type': 'appointment_confirmation',
                'notification_method': 'email',
                'subject': 'Appointment Confirmed - {{job_title}}',
                'content': '''Hi {{customer_name}},

Your appointment has been confirmed!

Job: {{job_title}}
Date: {{scheduled_date}}
Time: {{scheduled_time}}
Address: {{job_address}}

If you need to reschedule or have any questions, please contact us at {{company_phone}}.

Thank you for choosing {{company_name}}!

Best regards,
{{company_name}} Team
{{company_phone}}
{{company_website}}''',
                'is_active': True,
                'send_to_customer': True,
                'trigger_on_job_create': True,
            },
            {
                'name': 'Welcome New Customer - Email',
                'template_type': 'welcome_customer',
                'notification_method': 'email',
                'subject': 'Welcome to {{company_name}}!',
                'content': '''Hi {{customer_name}},

Welcome to {{company_name}}! We're excited to have you as a customer.

We provide top-quality roofing services and are here to help with all your roofing needs.

Contact us anytime:
Phone: {{company_phone}}
Website: {{company_website}}

Thank you for choosing {{company_name}}!

Best regards,
{{company_name}} Team''',
                'is_active': True,
                'send_to_customer': True,
            },
        ]

        created_count = 0
        updated_count = 0

        for template_data in templates_data:
            template, created = NotificationTemplate.objects.get_or_create(
                template_type=template_data['template_type'],
                notification_method=template_data['notification_method'],
                defaults=template_data
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created template: {template.name}')
                )
            else:
                # Update existing template
                for key, value in template_data.items():
                    setattr(template, key, value)
                template.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated template: {template.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed {created_count + updated_count} templates '
                f'({created_count} created, {updated_count} updated)'
            )
        )
