from importlib import import_module

from django.apps import AppConfig
from django.conf import settings
from django.urls import clear_url_caches, include, path
from django.utils.translation import gettext_lazy as _


class FormsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "djangocms_form_builder"
    verbose_name = _("Form builder")

    patterns_added = False

    def ready(self):
        """Install the URLs"""
        if self.patterns_added:
            return
        self.patterns_added = True
        urlconf_module = import_module(settings.ROOT_URLCONF)
        # Add the new URL pattern
        urlconf_module.urlpatterns = [
            path(
                "@form-builder/",
                include(
                    "djangocms_form_builder.urls",
                    namespace="form_builder",
                ),
            )
        ] + urlconf_module.urlpatterns
        # Clear the URL cache
        clear_url_caches()
