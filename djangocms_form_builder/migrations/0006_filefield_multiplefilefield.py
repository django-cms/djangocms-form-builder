from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("djangocms_form_builder", "0005_static_captcha_schema"),
    ]

    operations = [
        migrations.CreateModel(
            name="FileField",
            fields=[],
            options={
                "verbose_name": "File upload",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("djangocms_form_builder.formfield",),
        ),
        migrations.CreateModel(
            name="MultipleFileField",
            fields=[],
            options={
                "verbose_name": "Multiple file upload",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("djangocms_form_builder.formfield",),
        ),
    ]
