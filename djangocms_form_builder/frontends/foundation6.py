from django.conf import settings as django_settings
from django.utils.translation import gettext_lazy as _

default_attr = dict(
    input="form-control",
    label="form-label",
    div="",
    group="",
)

attr_dict = dict(
    Select=dict(input="form-select"),
    SelectMultiple=dict(input="form-select"),
    NullBooleanSelect=dict(input="form-select"),
    RadioSelect=dict(
        input="form-check-input", label="form-check-label", div="form-check"
    ),
    CheckboxInput=dict(
        input="form-check-input", label="form-check-label", div="form-check"
    ),
    ButtonRadio=dict(input="btn-check", label="btn btn-outline-primary"),
    ButtonCheckbox=dict(input="btn-check", label="btn btn-outline-primary"),
)

DEFAULT_FIELD_SEP = "mb-3"


DEFAULT_COLOR_STYLE_CHOICES = (
    ("primary", _("Primary")),
    ("secondary", _("Secondary")),
)

if not getattr(django_settings, "DJANGO_FORM_BUILDER_COLOR_STYLE_CHOICES", False):
    if not getattr(django_settings, "DJANGOCMS_FRONTEND_COLOR_STYLE_CHOICES", False):
        SUBMIT_BUTTON_CHOICES = DEFAULT_COLOR_STYLE_CHOICES
    else:
        SUBMIT_BUTTON_CHOICES = [
            (f"mb-{key}", value)
            for key, value in django_settings.DJANGOCMS_FRONTEND_COLOR_STYLE_CHOICES
        ]
else:
    SUBMIT_BUTTON_CHOICES = django_settings.DJANGO_FORM_BUILDER_COLOR_STYLE_CHOICES
