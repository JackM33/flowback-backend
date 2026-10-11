from celery import shared_task
from django.utils import timezone
from django_celery_beat.models import PeriodicTask

from flowback.schedule.models import ScheduleEvent


@shared_task
def event_notify(event_id: int):
    """
    :param event_id:  ScheduleEvent id
    """
    event = ScheduleEvent.objects.filter(id=event_id).first()

    # Stop notifying if event is removed
    if not event or not event.repeat_frequency:
        PeriodicTask.objects.filter(name=f"schedule_event_{event_id}").delete()
        return

    # Skip notify if scheduled at a later date
    if event.start_date > timezone.now():
        return

    # Skip regenerating notifications if the next occurrence is after the repetition ends
    if (event.repeat_frequency_end_date
            and event.next_start_date
            and event.next_start_date > event.repeat_frequency_end_date):
        return

    event.regenerate_notifications()
