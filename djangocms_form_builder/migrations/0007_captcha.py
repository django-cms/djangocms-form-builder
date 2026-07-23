from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("djangocms_form_builder", "0006_filefield_multiplefilefield"),
    ]

    operations = [
        migrations.CreateModel(
            name="Captcha",
            fields=[],
            options={
                "verbose_name": "Captcha",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("djangocms_form_builder.formfield",),
        ),
    ]
