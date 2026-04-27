from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("djangocms_form_builder", "0004_alter_form_captcha_requirement_and_more"),
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
