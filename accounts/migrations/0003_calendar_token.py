import uuid
from django.db import migrations, models


def gen_uuid(apps, schema_editor):
    Farm = apps.get_model('accounts', 'Farm')
    for farm in Farm.objects.all():
        farm.calendar_token = uuid.uuid4()
        farm.save(update_fields=['calendar_token'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_profile'),
    ]

    operations = [
        migrations.AddField(
            model_name='farm',
            name='calendar_token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
        migrations.RunPython(gen_uuid, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='farm',
            name='calendar_token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
