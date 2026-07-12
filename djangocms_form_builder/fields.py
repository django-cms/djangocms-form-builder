from django import forms
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from djangocms_attributes_field import fields

from . import settings
from .helpers import first_choice


class ButtonGroup(forms.RadioSelect):
    template_name = "djangocms_form_builder/admin/widgets/button_group.html"
    option_template_name = (
        "djangocms_form_builder/admin/widgets/button_group_option.html"
    )

    class Media:
        css = {"all": ("djangocms_form_builder/css/button_group.css",)}


class AttributesField(fields.AttributesField):
    def __init__(self, *args, **kwargs):
        if "verbose_name" not in kwargs:
            kwargs["verbose_name"] = _("Attributes")
        if "blank" not in kwargs:
            kwargs["blank"] = True
        super().__init__(*args, **kwargs)


class AttributesFormField(fields.AttributesFormField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label", _("Attributes"))
        kwargs.setdefault("required", False)
        kwargs.setdefault("widget", fields.AttributesWidget)
        self.excluded_keys = kwargs.pop("excluded_keys", [])
        super().__init__(*args, **kwargs)


try:
    fields.AttributesWidget(
        sorted=True
    )  # does djangocms-attributes-field support sorted param?
    CHOICESWIDGETPARAMS = dict(sorted=False)  # use unsorted variant
except TypeError:
    CHOICESWIDGETPARAMS = dict()  # Fallback for djangocms-attributes-field < 2.1


class ChoicesFormField(fields.AttributesFormField):
    """Simple choices field based on attributes field. Needs to be extended to
    allow to sort choices"""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label", _("Choices"))
        kwargs.setdefault("required", True)
        kwargs.setdefault("widget", fields.AttributesWidget(**CHOICESWIDGETPARAMS))
        self.excluded_keys = kwargs.pop("excluded_keys", [])
        super().__init__(*args, **kwargs)

    def clean(self, value):
        if not value:
            raise ValidationError(
                mark_safe(
                    _(
                        "Please enter at least one choice. Use the <code>+</code> symbol to add a choice."
                    )
                ),
                code="empty",
            )
        return [(key, value) for key, value in value.items()]

    def prepare_value(self, value):
        if not value:
            return {}
        if isinstance(value, dict):  # Already dict? OK!
            return super().prepare_value(value)
        # Turn items into dict
        return super().prepare_value({key: value for key, value in value})


# Kept because it is referenced by migration 0001 - do not use in new code.
class TagTypeField(models.CharField):
    def __init__(self, *args, **kwargs):
        if "verbose_name" not in kwargs:
            kwargs["verbose_name"] = _("Tag type")
        if "choices" not in kwargs:
            kwargs["choices"] = settings.TAG_CHOICES
        if "default" not in kwargs:
            kwargs["default"] = first_choice(settings.TAG_CHOICES)
        if "max_length" not in kwargs:
            kwargs["max_length"] = 255
        if "help_text" not in kwargs:
            kwargs["help_text"] = _("Select the HTML tag to be used.")
        super().__init__(*args, **kwargs)
