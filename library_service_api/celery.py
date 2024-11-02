import os

from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "library_service_api.settings")

app = Celery("library_service_api")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")


app.conf.beat_schedule = {
    "Send notification about overdue to admin every day at noon": {
        "task": "notifications_service.tasks.send_notification_about_overdue_to_admin",
        "schedule": crontab(hour="12", minute="0"),
    },
    "Send notification about overdue to users every every day at noon": {
        "task": "notifications_service.tasks.send_notification_about_overdue_to_users",
        "schedule": crontab(hour="12", minute="0"),
    },
    "Checking and marking stripe session as expired": {
        "task": "notifications_service.tasks.checking_stripe_session_for_expiration",
        "schedule": crontab(minute="*"),
    },
}
