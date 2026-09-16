from django.db import migrations


class Migration(migrations.Migration):
    """Free up the name ``Form`` for the frontend-editable form object.

    The plugin model keeps all of its fields and its ``plugin_type``
    (``FormPlugin``) - only the model, and with it its database table, is
    renamed. Existing plugin instances are unaffected.
    """

    dependencies = [
        ("djangocms_form_builder", "0008_submission_quota"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="Form",
            new_name="FormPlugin",
        ),
        migrations.AlterModelOptions(
            name="formplugin",
            options={"verbose_name": "Form"},
        ),
    ]
