from importlib import import_module

from django.apps import AppConfig
from django.conf import settings
from django.urls import clear_url_caches, include, path
from django.utils.translation import gettext_lazy as _


class FormsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "djangocms_form_builder"
    verbose_name = _("Form builder")

    def ready(self):
        """Install the URLs"""
        urlconf_module = import_module(settings.ROOT_URLCONF)

        # Idempotency guard
        for pattern in urlconf_module.urlpatterns:
            if hasattr(pattern, "urlconf_name"):
                # Check if this pattern includes the form builder urls
                urlconf_name = pattern.urlconf_name
                if urlconf_name == "djangocms_form_builder.urls" or (
                    hasattr(pattern, "urlconf_module")
                    and getattr(pattern.urlconf_module, "__name__", None)
                    == "djangocms_form_builder.urls"
                ):
                    return

        urlconf_module.urlpatterns = [
            path(
                "@form-builder/",
                include(
                    "djangocms_form_builder.urls",
                    namespace="form_builder",
                ),
            ),
            *urlconf_module.urlpatterns,
        ]

        clear_url_caches()
