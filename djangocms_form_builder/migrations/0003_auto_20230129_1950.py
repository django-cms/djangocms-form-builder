# Generated by Django 3.2 on 2023-01-29 19:50

import django.core.serializers.json
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("djangocms_form_builder", "0002_alter_form_cmsplugin_ptr_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="form",
            name="tag_type",
        ),
        migrations.RemoveField(
            model_name="formfield",
            name="tag_type",
        ),
        migrations.AddField(
            model_name="form",
            name="action_parameters",
            field=models.JSONField(
                blank=True,
                default=dict,
                encoder=django.core.serializers.json.DjangoJSONEncoder,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="form",
            name="captcha_widget",
            field=models.CharField(
                blank=True,
                choices=[("", "-----")],
                default="",
                help_text='Read more in the <a href="https://developers.google.com/recaptcha" target="_blank">documentation</a>.',
                max_length=16,
                verbose_name="captcha widget",
            ),
        ),
    ]
