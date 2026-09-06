from django.core.exceptions import ImproperlyConfigured

try:
    from formset.renderers.bootstrap import (
        FormRenderer as FormsetRenderer,  # noqa: F401
    )
except ImportError as exc:
    raise ImproperlyConfigured(
        "The django_formset frontend requires django-formset. "
        "Install djangocms-form-builder[formset]."
    ) from exc

from .bootstrap5 import (  # noqa: E402, F401
    DEFAULT_COLOR_STYLE_CHOICES,
    DEFAULT_FIELD_SEP,
    SUBMIT_BUTTON_CHOICES,
    attr_dict,
    default_attr,
)


class FormRenderMixin:
    render_template = "djangocms_form_builder/django_formset/form.html"
