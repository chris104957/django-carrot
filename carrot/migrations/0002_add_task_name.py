# Generated by Django 2.0.4 on 2018-05-30 12:19

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('carrot', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='scheduledtask',
            name='task_name',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]
