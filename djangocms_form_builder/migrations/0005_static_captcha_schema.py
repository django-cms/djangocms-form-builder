from django.db import migrations, models


class Migration(migrations.Migration):
    """Make the schema independent of which captcha packages are installed.

    Previously ``captcha_requirement.null`` and the ``captcha_widget`` default
    and choices depended on the apps installed when migrations were generated,
    causing spurious migrations in user projects.
    """

    dependencies = [
        ("djangocms_form_builder", "0004_alter_form_captcha_requirement_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="datetimefield",
            options={"verbose_name": "Date and time field"},
        ),
        migrations.AlterModelOptions(
            name="timefield",
            options={"verbose_name": "Time field"},
        ),
        migrations.AlterField(
            model_name="form",
            name="captcha_requirement",
            field=models.DecimalField(
                decimal_places=2,
                default=0.5,
                help_text="Only for reCaptcha v3: Minimum score required to accept challenge.",
                max_digits=3,
                null=True,
                verbose_name="Minimum score requirement",
            ),
        ),
        migrations.AlterField(
            model_name="form",
            name="captcha_widget",
            field=models.CharField(
                blank=True,
                default="",
                help_text='Read more in the <a href="https://developers.google.com/recaptcha" target="_blank">documentation</a>.',
                max_length=16,
                verbose_name="captcha widget",
            ),
        ),
        migrations.AlterField(
            model_name="form",
            name="form_spacing",
            field=models.CharField(
                blank=True,
                max_length=16,
                verbose_name="Margin between fields",
            ),
        ),
    ]
