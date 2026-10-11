"""
Schedule Task Test Suite

This test suite covers:
- Celery beat configuration for the database-stored periodic tasks
- Periodic tasks created for repeating events
- event_notify task
"""

from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django_celery_beat.models import PeriodicTask

from backend.celery import app
from flowback.schedule.models import ScheduleEvent
from flowback.schedule.tasks import event_notify
from flowback.schedule.tests.factories import ScheduleEventFactory


class ScheduleTaskTest(TestCase):
    def setUp(self):
        # Started yesterday and repeats daily, so the next occurrence is in the future
        self.event = ScheduleEventFactory.create(start_date=timezone.now() - timedelta(days=1),
                                                 end_date=timezone.now() - timedelta(days=1) + timedelta(hours=2),
                                                 repeat_frequency=ScheduleEvent.Frequency.DAILY)

    def future_notifications(self):
        return self.event.notification_channel.notificationobject_set.filter(timestamp__gte=timezone.now())

    def periodic_task(self):
        return PeriodicTask.objects.filter(name=f"schedule_event_{self.event.id}")

    def test_beat_uses_database_scheduler(self):
        self.assertEqual(app.conf.beat_scheduler, "django_celery_beat.schedulers:DatabaseScheduler")

    def test_repeating_event_periodic_task_uses_registered_task_name(self):
        self.assertEqual(self.periodic_task().get().task, event_notify.name)

    def test_event_notify_removed_event(self):
        event_id = self.event.id
        self.event.delete()

        event_notify(event_id=event_id)

        self.assertFalse(PeriodicTask.objects.filter(name=f"schedule_event_{event_id}").exists())

    def test_event_notify_event_no_longer_repeating(self):
        ScheduleEvent.objects.filter(id=self.event.id).update(repeat_frequency=None)

        event_notify(event_id=self.event.id)

        self.assertFalse(self.periodic_task().exists())

    def test_event_notify_regenerates_notifications(self):
        self.future_notifications().delete()

        event_notify(event_id=self.event.id)

        self.assertTrue(self.future_notifications().exists())
        self.assertTrue(self.periodic_task().exists())

    def test_event_notify_skips_when_next_occurrence_is_after_repeat_end(self):
        ScheduleEvent.objects.filter(id=self.event.id).update(
            repeat_frequency_end_date=timezone.now() + timedelta(hours=1))
        self.future_notifications().delete()

        event_notify(event_id=self.event.id)

        self.assertFalse(self.future_notifications().exists())

    def test_event_notify_skips_event_not_started(self):
        ScheduleEvent.objects.filter(id=self.event.id).update(start_date=timezone.now() + timedelta(days=1),
                                                              end_date=timezone.now() + timedelta(days=1, hours=2))
        self.future_notifications().delete()

        event_notify(event_id=self.event.id)

        self.assertFalse(self.future_notifications().exists())
