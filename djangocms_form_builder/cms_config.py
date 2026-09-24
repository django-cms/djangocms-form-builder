from cms.app_base import CMSAppConfig
from django.conf import settings

from .form_model import FormContent, on_form_content_publish
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
                    grouper_admin_mixin="__default__",
                    # Pages showing the form cache its rendered fields.
                    on_publish=on_form_content_publish,
                    on_unpublish=on_form_content_publish,
                ),
            ]
