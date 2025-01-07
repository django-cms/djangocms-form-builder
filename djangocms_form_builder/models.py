import decimal

from cms.models import CMSPlugin
from django import forms
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import validate_slug
from django.db import models
from django.forms.widgets import Input
from django.utils.html import conditional_escape, mark_safe
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from . import recaptcha, settings
from .entry_model import FormEntry  # NoQA
from .fields import AttributesField
from .helpers import coerce_decimal, mark_safe_lazy

MAX_LENGTH = 256


class Form(CMSPlugin):
    class Meta:
        verbose_name = _("Form")

    form_selection = models.CharField(
        verbose_name=_("Form"),
        max_length=MAX_LENGTH,
        blank=True,
        default="",
    )
    form_name = models.CharField(
        verbose_name=_("Form name"),
        max_length=MAX_LENGTH,
        blank=True,
        default="",
        validators=[
            validate_slug,
        ],
    )
    form_login_required = models.BooleanField(
        verbose_name=_("Login required to submit form"),
        blank=True,
        default=False,
        help_text=_(
            "To avoid issues with user experience use this type of form only on pages, "
            "which require login."
        ),
    )
    form_unique = models.BooleanField(
        verbose_name=_("User can reopen form"),
        default=False,
        help_text=_('Requires "Login required" to be checked to work.'),
    )
    form_floating_labels = models.BooleanField(
        verbose_name=_("Floating labels"),
        default=False,
    )
    form_spacing = models.CharField(
        verbose_name=_("Margin between fields"),
        max_length=16,
    )

    form_actions = models.CharField(
        verbose_name=_("Actions to be taken after form submission"),
        blank=True,
        max_length=4 * MAX_LENGTH,
    )

    action_parameters = models.JSONField(
        default=dict,
        encoder=DjangoJSONEncoder,
        blank=True,
        null=True,
    )

    attributes = AttributesField()

    captcha_widget = models.CharField(
        verbose_name=_("captcha widget"),
        max_length=16,
        blank=True,
        default="v2-invisible" if recaptcha.installed else "",
        choices=settings.EMPTY_CHOICE + recaptcha.CAPTCHA_CHOICES,
        help_text=mark_safe_lazy(
            _(
                'Read more in the <a href="{link}" target="_blank">documentation</a>.'
            ).format(link="https://developers.google.com/recaptcha")
        ),
    )
    captcha_requirement = models.DecimalField(
        verbose_name=_("Minimum score requirement"),
        null=not recaptcha.installed,
        decimal_places=2,
        max_digits=3,
        default=0.5,
        help_text=_(
            "Only for reCaptcha v3: Minimum score required to accept challenge."
        ),
    )
    captcha_config = AttributesField(
        verbose_name=_("Recaptcha configuration parameters"),
        help_text=mark_safe_lazy(
            _(
                'The reCAPTCHA widget supports several <a href="{attr_link}" target="_blank">data attributes</a> '
                "that customize the behaviour of the widget, such as <code>data-theme</code>, "
                "<code>data-size</code>. "
                'The reCAPTCHA api supports several <a href="{api_link}" target="_blank">parameters</a>. '
                "Add these api parameters as attributes, e.g. <code>hl</code> to set the language."
            ).format(
                attr_link="https://developers.google.com/recaptcha/docs/display#render_param",
                api_link="https://developers.google.com/recaptcha/docs/display#javascript_resource_apijs_parameters",
            )
        ),
    )

    def get_short_description(self):
        return f"({self.form_name})" if self.form_name else "<unnamed>"

    def __str__(self):
        return f"{self.__class__.__name__} ({self.id})"


class FormField(CMSPlugin):
    """
    Generic plugin model to store all form items. Plugin and field-specific information is stored in a JSON field
    called "config".
    """

    class Meta:
        verbose_name = gettext("Form field item")

    ui_item = models.CharField(max_length=30)
    config = models.JSONField(default=dict, encoder=DjangoJSONEncoder)

    def __init__(self, *args, **kwargs):
        self._additional_classes = []
        super().__init__(*args, **kwargs)

    def __getattr__(self, item):
        """Makes properties of plugin config available as plugin properties."""
        if (
            item[0] != "_" and item in self.config
        ):  # Avoid infinite recursion trying to get .config from db
            return self.config[item]
        return super().__getattribute__(item)

    def __str__(self):
        if "__str__" in self.config:
            return self.config["__str__"]
        return f"{gettext(self.ui_item)} ({str(self.pk)})"

    def add_classes(self, *args):
        for arg in args:
            if arg:
                self._additional_classes += arg.split() if isinstance(arg, str) else arg

    def add_attribute(self, attr, value=None):
        attrs = self.config.get("attributes", {})
        attrs.update({attr: value})
        self.config["attributes"] = attrs

    def get_attributes(self):
        attributes = self.config.get("attributes", {})
        classes = set(attributes.get("class", "").split())
        classes.update(self._additional_classes)
        if classes:
            attributes["class"] = " ".join(classes)
        parts = (
            f'{item}="{conditional_escape(value)}"' if value else f"{item}"
            for item, value in attributes.items()
        )
        return mark_safe(" " + " ".join(parts)) if parts else ""

    def save(self, *args, **kwargs):
        self.ui_item = self.__class__.__name__
        return super().save(*args, **kwargs)

    def initialize_from_form(self, form=None):
        """Populates the config JSON field based on initial values provided by the fields of form"""
        if form is None:
            form = self.get_plugin_class().form
        if isinstance(form, type):  # if is class
            form = form()  # instantiate
        entangled_fields = getattr(
            getattr(form, "Meta", None), "entangled_fields", {}
        ).get("config", ())
        for field in entangled_fields:
            self.config.setdefault(
                field, {} if field == "attributes" else form[field].initial or ""
            )
        return self

    def get_short_description(self):
        label = self.config.get("field_label", "")
        return f"{label} ({self.config.get('field_name')})"


class CharField(FormField):
    class Meta:
        proxy = True
        verbose_name = _("Character field")

    def get_form_field(self):
        return self.field_name, forms.CharField(
            label=self.config.get("field_label", ""),
            required=self.config.get("field_required", False),
            widget=forms.TextInput(
                attrs=dict(placeholder=self.config.get("field_placeholder", ""))
            ),
        )


class EmailField(FormField):
    class Meta:
        proxy = True
        verbose_name = _("Email field")

    def get_form_field(self):
        return self.field_name, forms.EmailField(
            label=self.config.get("field_label", ""),
            required=self.config.get("field_required", False),
            widget=forms.EmailInput(
                attrs=dict(placeholder=self.config.get("field_placeholder", ""))
            ),
        )


class UrlField(FormField):
    class Meta:
        proxy = True
        verbose_name = _("URL field")

    def get_form_field(self):
        return self.field_name, forms.URLField(
            label=self.config.get("field_label", ""),
            required=self.config.get("field_required", False),
            widget=forms.URLInput(
                attrs=dict(placeholder=self.config.get("field_placeholder", ""))
            ),
        )


class DecimalField(FormField):
    class Meta:
        proxy = True
        verbose_name = _("Decimal field")

    class NumberInput(forms.NumberInput):
        def __init__(self, **kwargs):
            self.decimal_places = kwargs.pop("decimal_places", None)
            super().__init__(**kwargs)

        def format_value(self, value):
            if value is None:
                return ""
            value = str(value)
            if "." in value:
                left, right = value.rsplit(".", 1)
            else:
                left, right = value, ""
            if self.decimal_places == 0:
                return left
            right = (right + self.decimal_places * "0")[: self.decimal_places]
            return super().format_value(".".join((left, right)))

    class StrDecimalField(forms.DecimalField):
        def clean(self, value):
            value = super().clean(value)
            if isinstance(value, decimal.Decimal):
                value = str(value)
            return value

    def get_form_field(self):
        return self.field_name, DecimalField.StrDecimalField(
            label=self.config.get("field_label", ""),
            required=self.config.get("field_required", False),
            min_value=coerce_decimal(self.config.get("min_value", None)),
            max_value=coerce_decimal(self.config.get("max_value", None)),
            decimal_places=self.config.get("decimal_places", None),
            widget=DecimalField.NumberInput(
                attrs=dict(placeholder=self.config.get("field_placeholder", "")),
                decimal_places=self.config.get("decimal_places", None),
            ),
        )


class IntegerField(FormField):
    class Meta:
        proxy = True
        verbose_name = _("Integer field")

    def get_form_field(self):
        return self.field_name, forms.IntegerField(
            label=self.config.get("field_label", ""),
            required=self.config.get("field_required", False),
            widget=DecimalField.NumberInput(
                attrs=dict(placeholder=self.config.get("field_placeholder", "")),
            ),
        )


class TextareaField(FormField):
    class Meta:
        proxy = True
        verbose_name = _("Text field")

    def get_form_field(self):
        return self.field_name, forms.CharField(
            label=self.config.get("field_label", ""),
            required=self.config.get("field_required", False),
            widget=forms.Textarea(
                attrs=dict(
                    rows=self.config.get("field_rows", 10),
                    placeholder=self.config.get("field_placeholder", ""),
                    style="height: inherit;",
                )
            ),
        )


class DateField(FormField):
    class Meta:
        proxy = True
        verbose_name = _("Date field")

    class DateInput(forms.DateInput):
        input_type = "date"

    def get_form_field(self):
        return self.field_name, forms.DateField(
            label=self.config.get("field_label", ""),
            required=self.config.get("field_required", False),
            widget=DateField.DateInput(
                attrs=dict(placeholder=self.config.get("field_placeholder", "")),
            ),
        )


class DateTimeField(FormField):
    class Meta:
        proxy = True
        verbose_name = _("Date field")

    class DateTimeField(forms.DateTimeField):
        def prepare_value(self, value):
            if isinstance(value, str):
                from django.utils import dateparse

                return super().prepare_value(dateparse.parse_datetime(value))
            return super().prepare_value(value)

    class DateTimeInput(forms.DateTimeInput):
        input_type = "datetime-local"

    def get_form_field(self):
        return self.field_name, DateTimeField.DateTimeField(
            label=self.config.get("field_label", ""),
            required=self.config.get("field_required", False),
            widget=DateTimeField.DateTimeInput(
                attrs=dict(placeholder=self.config.get("field_placeholder", "")),
            ),
        )


class TimeField(FormField):
    class Meta:
        proxy = True
        verbose_name = _("Date field")

    class TimeInput(forms.TimeInput):
        input_type = "time"

    def get_form_field(self):
        return self.field_name, forms.TimeField(
            label=self.config.get("field_label", ""),
            required=self.config.get("field_required", False),
            widget=TimeField.TimeInput(
                attrs=dict(placeholder=self.config.get("field_placeholder", "")),
            ),
        )


class Select(FormField):
    class Meta:
        proxy = True
        verbose_name = _("Select")

    _choices = None
    no_selection = [("", _("No selection"))]

    def get_choices(self):
        if self._choices is None:
            descendants = self.get_children().order_by("position")
            self._choices = []
            for child in descendants:
                instance = child.djangocms_form_builder_formfield
                self._choices.append(
                    (instance.config["value"], instance.config["verbose"])
                )
        return self._choices

    def get_form_field(self):
        multiple_choice = self.config.get("field_select", "") in (
            "multiselect",
            "checkbox",
        )
        field = forms.MultipleChoiceField if multiple_choice else forms.ChoiceField
        required = self.config.get("field_required", False)
        choices = self.get_choices()
        if not required and not multiple_choice:
            choices = self.no_selection + choices
        widget_choice = self.config.get("field_select", "")
        if widget_choice == "select":
            widget = forms.Select()
        elif widget_choice == "radio":
            widget = forms.RadioSelect()
        elif widget_choice == "multiselect":
            widget = forms.SelectMultiple(attrs=dict(style="min-height: 6em;"))
        else:
            widget = forms.CheckboxSelectMultiple()

        return self.field_name, field(
            label=self.config.get("field_label", ""),
            required=required,
            choices=choices,
            widget=widget,
        )


class Choice(FormField):
    class Meta:
        proxy = True
        verbose_name = _("Choice")

    def get_short_description(self):
        return f'{self.config.get("verbose", "-")} ("{self.config.get("value", "")}")'


class SwitchInput(forms.CheckboxInput):
    pass


class BooleanField(FormField):
    class Meta:
        proxy = True
        verbose_name = _("Boolean field")

    def get_form_field(self):
        return self.field_name, forms.BooleanField(
            label=self.config.get("field_label", ""),
            required=self.config.get("field_required", False),
            widget=SwitchInput()
            if self.config.get("field_as_switch", False)
            else forms.CheckboxInput(),
        )


class FormSubmitButton(forms.Field):
    widget = Input(attrs=dict(type="submit"))


class SubmitButton(FormField):
    class Meta:
        proxy = True
        verbose_name = _("Submit button")
