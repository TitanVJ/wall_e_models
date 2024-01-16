# Generated by Django 3.2.20 on 2024-01-16 01:33

from django.db import migrations, models
import django.utils.timezone
import wall_e_models.customFields


class Migration(migrations.Migration):

    dependencies = [
        ('wall_e_models', '0022_auto_20240115_1602'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='banrecord',
            name='unique_active_ban',
        ),
        migrations.RemoveField(
            model_name='banrecord',
            name='epoch_ban_date',
        ),
        migrations.RemoveField(
            model_name='banrecord',
            name='epoch_unban_date',
        ),
        migrations.AlterField(
            model_name='banrecord',
            name='ban_date',
            field=wall_e_models.customFields.PSTDateTimeField(default=django.utils.timezone.now, null=True),
        ),
        migrations.AddConstraint(
            model_name='banrecord',
            constraint=models.UniqueConstraint(condition=models.Q(('unban_date__isnull', True)), fields=('user_id',), name='unique_active_ban'),
        ),
    ]
