import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'roof_platform.settings')

app = Celery('roof_platform')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Define periodic tasks
app.conf.beat_schedule = {
    # Example periodic task - runs every 5 minutes
    'send-reminder-notifications': {
        'task': 'scheduling.tasks.send_reminder_notifications',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
    # Daily summary report
    'generate-daily-summary': {
        'task': 'jobs.tasks.generate_daily_summary',
        'schedule': crontab(hour=18, minute=0),  # 6 PM daily
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
