import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "library_service_api.settings")

import django
django.setup()

from django_celery_beat.models import (
    PeriodicTask,
    CrontabSchedule
)


def create_periodic_tasks():
    tasks = {
        "library_service_api.tasks.send_notification_about_overdue_to_admins": "Send notification about overdue to admins",
        "library_service_api.tasks.send_notification_about_overdue_to_users": "Send notification about overdue to users",
    }

    schedule, created = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="12",
        day_of_week="*",
        day_of_month="*",
        month_of_year="*",
    )

    for task, description in tasks.items():
        PeriodicTask.objects.create(
            crontab=schedule,
            name=f"{description}, daily at 12:00",
            task=task,
        )

if __name__ == "__main__":
    create_periodic_tasks()