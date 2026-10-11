from django.db import migrations

OLD_TASK = 'schedule.tasks.event_notify'
NEW_TASK = 'flowback.schedule.tasks.event_notify'


# Repeating events' periodic tasks were created with a task name the worker
# doesn't register, so beat's messages for them were rejected
def rename_task(old: str, new: str):
    def run(apps, schema_editor):
        PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')
        PeriodicTask.objects.filter(task=old).update(task=new)

    return run


class Migration(migrations.Migration):

    dependencies = [
        ('schedule', '0023_scheduleevent_repeat_frequency_end_date_and_more'),
        ('django_celery_beat', '0018_improve_crontab_helptext'),
    ]

    operations = [
        migrations.RunPython(rename_task(OLD_TASK, NEW_TASK), rename_task(NEW_TASK, OLD_TASK)),
    ]
