# Generated by Django 2.2.16 on 2022-03-05 12:05

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0015_auto_20220304_2259'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='follow',
            name='unique_users',
        ),
    ]