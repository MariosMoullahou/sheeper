from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sheepfold', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='sheep',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='milk',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
    ]
