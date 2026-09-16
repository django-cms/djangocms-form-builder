from cms.app_base import CMSAppConfig
from django.conf import settings

from .form_model import FormContent, copy_form_content
from .rendering import render_form_content
from .utils import get_versionable_item


class FormBuilderCMSConfig(CMSAppConfig):
    #: Forms are edited in django CMS' structure board, so the form content
    #: object is frontend-editable.
    cms_enabled = True
    cms_toolbar_enabled_models = [(FormContent, render_form_content, "form")]

    def __init__(self, app_config):
        super().__init__(app_config)
        VersionableItem = get_versionable_item(self)
        self.djangocms_versioning_enabled = getattr(
            settings, "VERSIONING_FORM_MODELS_ENABLED", VersionableItem is not None
        )

        if self.djangocms_versioning_enabled and VersionableItem is not None:
            # Forms have no language dimension, so there is exactly one version
            # chain per form - no extra grouping fields.
            self.versioning = [
                VersionableItem(
                    content_model=FormContent,
                    grouper_field_name="form",
                    copy_function=copy_form_content,
                    grouper_admin_mixin="__default__",
                ),
            ]
