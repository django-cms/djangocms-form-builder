from cms.plugin_pool import plugin_pool
from django.conf import settings

if "djangocms_frontend.contrib.frontend_forms" in settings.INSTALLED_APPS:
    from djangocms_frontend.contrib.frontend_forms.cms_plugins import (
        BooleanFieldPlugin,
        CharFieldPlugin,
        ChoicePlugin,
        DateFieldPlugin,
        DateTimeFieldPlugin,
        DecimalFieldPlugin,
        EmailFieldPlugin,
        FormPlugin,
        IntegerFieldPlugin,
        SelectPlugin,
        TextareaPlugin,
        TimeFieldPlugin,
        URLFieldPlugin,
    )

    for plugin in (
        FormPlugin,
        BooleanFieldPlugin,
        CharFieldPlugin,
        ChoicePlugin,
        DateFieldPlugin,
        DateTimeFieldPlugin,
        DecimalFieldPlugin,
        EmailFieldPlugin,
        IntegerFieldPlugin,
        SelectPlugin,
        TextareaPlugin,
        TimeFieldPlugin,
        URLFieldPlugin,
    ):
        plugin_pool.unregister_plugin(plugin)
