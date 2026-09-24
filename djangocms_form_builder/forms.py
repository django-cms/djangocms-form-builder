import json

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_slug
from django.template.defaultfilters import slugify
from django.utils.translation import gettext_lazy as _
from entangled.forms import EntangledModelForm, EntangledModelFormMixin

from . import (
    _form_registry,
    actions,
    constants,
    get_registered_forms,
    models,
    recaptcha,
    settings,
)
from .entry_model import FormEntry
from .fields import AttributesFormField, ButtonGroup, ChoicesFormField
from .file_validation import validation_preset_choice_tuples
from .helpers import get_option, mark_safe_lazy


class SimpleFrontendForm(forms.Form):
    takes_request = True

    def __init__(self, *args, **kwargs):
        self._request = kwargs.pop("request")
        if get_option(self, "unique", False) and self._request.user.is_authenticated:
            qs = FormEntry.objects.filter(
                form_user=self._request.user, form_name=get_option(self, "form_name")
            )
            if qs:
                kwargs["initial"] = qs.last().entry_data
        super().__init__(*args, **kwargs)

    def clean(self):
        if get_option(self, "login_required", False):
            if not self._request.user.is_authenticated:
                raise ValidationError(
                    _("Please login before submitting this form."), code="unauthorized"
                )

        cleaned_data = super().clean()
        cleaned_data.pop("captcha_field", None)
        return cleaned_data

    def save(self):
        results = {}
        form_actions = get_option(self, "form_actions", [])
        for action in form_actions:
            Action = actions.get_action_class(action)
            if Action is None:
                results[action] = _("Action not available any more")
                continue
            action_instance = Action()
            if not action_instance.check_rate_limits(self, self._request):
                # Only this action is skipped, the remaining ones still run.
                results[action] = _("Rate limit reached")
                continue
            results[action] = action_instance.execute(self, self._request)
        if not form_actions:
            results[None] = _("No action registered")
        return results


class SelectMultipleActionsWidget(forms.CheckboxSelectMultiple):
    def format_value(self, value):
        if isinstance(value, str):
            # Stored as JSON on the model, but a form with no actions holds
            # the empty string rather than "[]".
            value = json.loads(value.replace("'", '"')) if value.strip() else []
        return super().format_value(value)


def form_settings_errors(
    form_actions, form_unique, form_login_required, check_actions=True
):
    """Check a form's settings against each other.

    Returns the errors as ``{field_name: message}``, empty if the settings are
    consistent. Shared by every form editing these settings, whatever the
    names of its fields. ``check_actions=False`` skips the checks involving
    ``form_actions``, e.g. when that field is not being edited.
    """
    if not form_unique:
        return {}
    if check_actions and actions.SAVE_TO_DB_ACTION not in (form_actions or []):
        if not actions.SAVE_TO_DB_ACTION:
            return {
                "form_unique": _(
                    "No form action to save form contents available. Users will "
                    "not be able to reopen a form."
                ),
            }
        return {
            "form_actions": _(
                'Please select "Save form submission" to allow users to reopen forms.'
            ),
            "form_unique": _(
                'Please select the action "Save form submission" to allow users to reopen forms.'
            ),
        }
    if not form_login_required:
        error = _("Users can only reopen forms if they are logged in. %(remedy)s")
        return {
            "form_login_required": error % dict(remedy=_("Either enable this.")),
            "form_unique": _("Or disable this."),
        }
    return {}


class FormSettingsFormMixin(EntangledModelFormMixin):
    """The settings that shape a form, wherever they are stored.

    A form object keeps them on its content model; a form plugin that still
    carries its fields as children keeps them on itself.
    """

    #: ``ActionMixin`` builds the admin form by mixing the registered actions'
    #: forms into this one. That generated class has no ``Meta`` of its own, so
    #: the model it edits is restored per instance.
    settings_model = None

    class Meta:
        entangled_fields = {
            "action_parameters": [],
        }
        untangled_fields = [
            "form_login_required",
            "form_unique",
            "form_floating_labels",
            "form_spacing",
            "form_actions",
            "attributes",
            "captcha_widget",
            "captcha_requirement",
            "captcha_config",
        ]

    form_login_required = forms.BooleanField(
        label=_("Login required to submit form"),
        required=False,
        initial=False,
        help_text=_(
            "To avoid issues with user experience use this type of form only on pages, "
            "which require login."
        ),
    )

    form_unique = forms.BooleanField(
        label=_("User can reopen form"),
        required=False,
        initial=False,
        help_text=_('Requires "Login required" to be checked to work.'),
    )

    form_spacing = forms.ChoiceField(
        label=_("Margin between fields"),
        choices=settings.SPACER_SIZE_CHOICES,
        initial=settings.SPACER_SIZE_CHOICES[len(settings.SPACER_SIZE_CHOICES) // 2][0],
        required=False,
    )

    form_floating_labels = forms.BooleanField(
        label=_("Floating labels"),
        required=False,
        initial=False,
    )

    form_actions = forms.MultipleChoiceField(
        label=_("Actions to be taken after form submission"),
        widget=SelectMultipleActionsWidget(),
        required=False,
    )

    attributes = AttributesFormField()

    captcha_widget = forms.ChoiceField(
        label=_("Captcha widget"),
        required=False,
        initial=recaptcha.CAPTCHA_CHOICES[0][0] if recaptcha.installed else "",
        choices=settings.EMPTY_CHOICE + recaptcha.CAPTCHA_CHOICES,
        help_text=mark_safe_lazy(
            _(
                'Read more in the <a href="{link}" target="_blank">documentation</a>.'
            ).format(link="https://developers.google.com/recaptcha")
        ),
    )
    captcha_requirement = forms.DecimalField(
        label=_("Minimum score requirement"),
        required=recaptcha.installed,
        initial=0.5,
        min_value=0,
        max_value=1,
        help_text=_(
            "Only for reCaptcha v3: Minimum score required to accept challenge."
        ),
    )
    captcha_config = AttributesFormField(
        label=_("Recaptcha configuration parameters"),
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

    def __init__(self, *args, **kwargs):
        if self.settings_model is not None:
            self._meta.model = self.settings_model
        super().__init__(*args, **kwargs)
        if "form_actions" in self.fields:
            self.fields["form_actions"].choices = actions.get_registered_actions()

    def clean(self):
        """Check the settings against each other.

        Only fields actually present are checked: the admin narrows the form
        down to the fieldsets it shows.
        """
        cleaned_data = super().clean()

        if (
            "form_actions" not in cleaned_data
            and "form_actions" in self.fields
            and self.requires_form_action()
        ):
            raise ValidationError(
                {
                    "form_actions": _(
                        "At least one action needs to be selected for the form to have an effect."
                    ),
                }
            )
        errors = form_settings_errors(
            form_actions=cleaned_data.get("form_actions"),
            form_unique=cleaned_data.get("form_unique"),
            form_login_required=cleaned_data.get("form_login_required"),
            check_actions="form_actions" in cleaned_data,
        )
        if errors:
            raise ValidationError(errors, code="inconsistent")
        return cleaned_data

    def requires_form_action(self):
        """Whether a form without any action is pointless here."""
        return True


class FormsForm(FormSettingsFormMixin, EntangledModelForm):
    """Settings of a form plugin.

    New plugins only pick the form to show. The remaining fields configure
    plugins that still carry their form fields as children - see
    :class:`~djangocms_form_builder.cms_plugins.FormPlugin`.
    """

    settings_model = models.FormPlugin

    #: The only fields of a plugin that does not carry its form fields itself.
    #: ``action_parameters`` stays because entangled always fills it in.
    picker_fields = ("form", "form_selection", "action_parameters")

    class Meta:
        model = models.FormPlugin
        exclude = ()
        untangled_fields = [
            "form",
            "form_selection",
            "form_name",
        ]
        entangled_fields = {
            "action_parameters": [],
        }

    form = forms.ModelChoiceField(
        label=_("Form"),
        queryset=models.Form.objects.all(),
        required=False,
        help_text=_("The form to show here. Forms are edited in the form editor."),
    )
    form_selection = forms.ChoiceField(
        label=_("Registered form"),
        required=False,
        initial="",
    )
    form_name = forms.CharField(
        label=_("Form identifier"),
        required=False,
        initial="",
        validators=[
            validate_slug,
        ],
        help_text=_("Slug that allows to uniquely identify forms."),
    )

    def __init__(self, *args, **kwargs):
        if (
            not _form_registry
            and "instance" in kwargs
            and kwargs["instance"] is not None
        ):
            # remove form_selection data if widget will be hidden
            kwargs["instance"].form_selection = ""
        super().__init__(*args, **kwargs)
        if not self.is_legacy():
            # Only the form to show is picked here. The settings - including
            # the fields the actions mix in - belong to the form object, and
            # left in place their validation would fail on fields the plugin
            # admin does not render.
            for name in list(self.fields):
                if name not in self.picker_fields:
                    del self.fields[name]
        if "form_selection" in self.fields:
            self.fields["form_selection"].widget = (
                forms.Select() if _form_registry else forms.HiddenInput()
            )
            self.fields["form_selection"].choices = (
                settings.EMPTY_CHOICE + get_registered_forms()
            )

    def requires_form_action(self):
        # A registered Django form brings its own behaviour.
        return not self.cleaned_data.get("form_selection")

    def is_legacy(self):
        """Whether this plugin still carries its form fields as children.

        Only such a plugin configures a form itself; every other one just
        points at the form to show.
        """
        instance = getattr(self, "instance", None)
        return bool(instance and instance.pk and instance.get_children().exists())

    def clean(self):
        if not self.is_legacy():
            if not self.cleaned_data.get("form") and not self.cleaned_data.get(
                "form_selection"
            ):
                raise ValidationError(
                    {"form": _("Please select the form to show here.")},
                    code="incomplete",
                )
            # A form object (or a registered Django form) carries its own
            # settings; the plugin's remaining fields do not apply.
            return self.cleaned_data

        if self.cleaned_data.get("form"):
            raise ValidationError(
                {
                    "form": _(
                        "This plugin still contains its own form fields. Use "
                        '"Convert to form" in its plugin menu to turn them '
                        "into a form first."
                    )
                },
                code="ambiguous",
            )
        if self.cleaned_data.get("form_selection", "") == "":
            if not self.cleaned_data.get("form_name", "-"):
                raise ValidationError(
                    {
                        "form_name": _(
                            "Please provide a form name to be able to evaluate form submissions."
                        )
                    },
                    code="incomplete",
                )
        return super().clean()


FORBIDDEN_FORM_NAMES = [
    "Meta",
    "get_success_context",
    "form_name",
    "form_user",
    "entry_data",
    "html_headers",
] + dir(SimpleFrontendForm(request=None))


def validate_form_name(value):
    if value in FORBIDDEN_FORM_NAMES:
        raise ValidationError(
            _("This name is reserved. Please chose a different one."), code="illegal"
        )


class FormFieldMixin(EntangledModelFormMixin):
    """
    Components > "Forms" Plugin
    https://getbootstrap.com/docs/5.1/forms/overview/
    """

    class Meta:
        entangled_fields = {
            "config": [
                "field_name",
                "field_label",
                "field_placeholder",
                "field_required",
                "field_help_text",
            ]
        }

    field_name = forms.CharField(
        label=_("Field name"),
        help_text=_(
            "Internal field name consisting of letters, numbers, underscores or hyphens"
        ),
        required=True,
        validators=[validate_slug, validate_form_name],
    )
    field_label = forms.CharField(
        label=_("Label"),
        help_text=_(
            "Field label shown to the user describing the entity to be entered"
        ),
        required=False,
    )
    field_placeholder = forms.CharField(
        label=_("Placeholder"),
        help_text=_("Example input shown muted in an empty field"),
        required=False,
    )
    field_required = forms.BooleanField(
        label=_("Required"),
        initial=False,
        required=False,
        help_text=_(
            "If selected form will not accept submissions with with empty data"
        ),
    )
    field_help_text = forms.CharField(
        label=_("Help text"),
        initial="",
        required=False,
        help_text=_("Help text shown below the field."),
        widget=forms.Textarea,
    )


class CharFieldForm(FormFieldMixin, EntangledModelForm):
    class Meta:
        model = models.FormField
        entangled_fields = {
            "config": [
                "min_length",
                "max_length",
            ]
        }

    min_length = forms.IntegerField(
        label=_("Minimum text length"),
        required=False,
        initial=None,
    )
    max_length = forms.IntegerField(
        label=_("Maximum text length"),
        required=False,
        initial=None,
    )


class EmailFieldForm(FormFieldMixin, EntangledModelForm):
    class Meta:
        model = models.FormField
        entangled_fields = {"config": []}


class UrlFieldForm(FormFieldMixin, EntangledModelForm):
    class Meta:
        model = models.FormField
        entangled_fields = {"config": []}


class DecimalFieldForm(FormFieldMixin, EntangledModelForm):
    class Meta:
        model = models.FormField
        entangled_fields = {
            "config": [
                "min_value",
                "max_value",
                "decimal_places",
            ]
        }

    min_value = forms.DecimalField(
        label=_("Minimum value"),
        required=False,
        initial=None,
    )
    max_value = forms.DecimalField(
        label=_("Maximum value"), required=False, initial=None
    )
    decimal_places = forms.IntegerField(
        label=_("Decimal places"),
        required=False,
        initial=None,
        min_value=0,
    )


class IntegerFieldForm(FormFieldMixin, EntangledModelForm):
    class Meta:
        model = models.FormField
        entangled_fields = {
            "config": [
                "min_value",
                "max_value",
            ]
        }

    min_value = forms.IntegerField(
        label=_("Minimum value"),
        required=False,
        initial=None,
    )
    max_value = forms.IntegerField(
        label=_("Maximum value"), required=False, initial=None
    )


class TextareaFieldForm(FormFieldMixin, EntangledModelForm):
    class Meta:
        model = models.FormField
        entangled_fields = {
            "config": [
                "min_length",
                "max_length",
                "field_rows",
            ]
        }

    field_rows = forms.IntegerField(
        label=_("Rows"),
        min_value=1,
        max_value=40,
        initial=10,
        help_text=_("Defines the vertical size of the text area in number of rows."),
    )
    min_length = forms.IntegerField(
        label=_("Minimum text length"),
        required=False,
        initial=None,
    )
    max_length = forms.IntegerField(
        label=_("Maximum text length"),
        required=False,
        initial=None,
    )


class DateFieldForm(FormFieldMixin, EntangledModelForm):
    class Meta:
        model = models.FormField
        entangled_fields = {"config": []}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["field_placeholder"].help_text = _("Not visible on most browsers.")


class DateTimeFieldForm(FormFieldMixin, EntangledModelForm):
    class Meta:
        model = models.FormField
        entangled_fields = {"config": []}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["field_placeholder"].help_text = _("Not visible on most browsers.")


class TimeFieldForm(FormFieldMixin, EntangledModelForm):
    class Meta:
        model = models.FormField
        entangled_fields = {"config": []}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["field_placeholder"].help_text = _("Not visible on most browsers.")


class SelectFieldForm(FormFieldMixin, EntangledModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "instance" in kwargs and kwargs["instance"] is not None:
            self.fields["field_choices"].initial = kwargs["instance"].get_choices()

    class Meta:
        model = models.FormField
        entangled_fields = {
            "config": [
                "field_select",
            ]
        }
        untangled_fields = ("field_choices",)

    field_select = forms.ChoiceField(
        label=_("Selection type"),
        required=True,
        choices=constants.CHOICE_FIELDS,
        widget=ButtonGroup(
            attrs=dict(property="text", label_class="btn-outline-secondary")
        ),
    )
    field_choices = ChoicesFormField(
        required=True,
    )

    def clean(self):
        if (
            self.cleaned_data.get("field_required", False)
            and self.cleaned_data.get("field_select", "") == "checkbox"
        ):
            raise ValidationError(
                {
                    "field_select": mark_safe_lazy(
                        _(
                            "For a required multiple choice fild select the <b>list</b> selection type."
                        )
                    ),
                    "field_required": mark_safe_lazy(
                        _("Checkbox multiple choice field <b>must not be required</b>.")
                    ),
                }
            )
        return self.cleaned_data


class ChoiceForm(EntangledModelForm):
    class Meta:
        model = models.FormField
        entangled_fields = {
            "config": [
                "value",
                "verbose",
            ]
        }

    value = forms.CharField(
        label=_("Value"),
        required=True,
        help_text=_("Stored in database if the choice is selected."),
    )
    verbose = forms.CharField(
        label=_("Display text"),
        required=True,
        help_text=_("Representation of choice displayed to the user."),
    )


FILE_UPLOAD_STORAGE_HELP = _(
    "Uploaded files are stored via Django file storage. With default_storage, "
    "anyone who knows or guesses the URL can access them. Set "
    "DJANGOCMS_FORM_BUILDER_FILE_FIELD_STORAGE to a private storage backend "
    "for sensitive attachments."
)


class FileFieldForm(FormFieldMixin, EntangledModelForm):
    class Meta:
        model = models.FormField
        entangled_fields = {
            "config": [
                "field_file_validation_presets",
            ]
        }

    field_file_validation_presets = forms.MultipleChoiceField(
        label=_("Validation presets"),
        required=False,
        choices=[],
        help_text=_(
            "Choose a rule to control which file types or sizes users can upload. "
            "Leave empty to allow all files permitted by default."
        )
        + " "
        + FILE_UPLOAD_STORAGE_HELP,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[
            "field_file_validation_presets"
        ].choices = validation_preset_choice_tuples()
        self.fields["field_placeholder"].widget = forms.HiddenInput()


class MultipleFileFieldForm(FormFieldMixin, EntangledModelForm):
    class Meta:
        model = models.FormField
        entangled_fields = {
            "config": [
                "max_files",
                "field_file_validation_presets",
            ]
        }

    max_files = forms.IntegerField(
        label=_("Max files"),
        min_value=1,
        initial=2,
        required=True,
        help_text=_(
            "Allowing to upload too many files may crash your website (denial of service attack)."
        ),
    )

    field_file_validation_presets = forms.MultipleChoiceField(
        label=_("Validation presets"),
        required=False,
        initial=[],
        choices=[],
        help_text=_(
            "Choose a rule to control which file types or sizes users can upload. "
            "Leave empty to allow all files permitted by default (applied to each "
            "uploaded file in order)."
        )
        + " "
        + FILE_UPLOAD_STORAGE_HELP,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[
            "field_file_validation_presets"
        ].choices = validation_preset_choice_tuples()
        self.fields["field_placeholder"].widget = forms.HiddenInput()


class BooleanFieldForm(FormFieldMixin, EntangledModelForm):
    class Meta:
        model = models.FormField
        entangled_fields = {
            "config": [
                "field_as_switch",
            ]
        }

    field_as_switch = forms.BooleanField(
        label=_("Layout"),
        initial=False,
        required=False,
        widget=ButtonGroup(
            choices=((False, _("Checkbox")), (True, _("Switch"))),
            attrs=dict(property="text", label_class="btn-outline-secondary"),
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["field_required"].help_text = _(
            "If checked, the form can only be submitted if the "
            "checkbox is checked or the switch set to on."
        )


class SubmitButtonForm(FormFieldMixin, EntangledModelForm):
    class Meta:
        model = models.FormField
        entangled_fields = {
            "config": [
                "submit_cta",
                "form_submit_context",
            ]
        }

    submit_cta = forms.CharField(
        label=_("Button label"),
        initial=_("Submit"),
        required=False,
    )

    form_submit_context = forms.ChoiceField(
        label=_("Button context"),
        choices=constants.SUBMIT_BUTTON_CHOICES,
        initial=constants.SUBMIT_BUTTON_CHOICES[0][0],
    )


class CaptchaForm(forms.ModelForm):
    class Meta:
        model = models.Captcha
        fields = ()


def unique_form_name(base):
    """A form identifier derived from ``base`` that is not taken yet."""
    base = slugify(base) or "form"
    name, suffix = base, 1
    while models.Form.objects.filter(form_name=name).exists():
        suffix += 1
        name = f"{base}-{suffix}"
    return name


class ConvertToFormForm(forms.Form):
    """Turns a form plugin's children into a form object of their own."""

    name = forms.CharField(
        label=_("Name"),
        help_text=_("Shown to editors when they pick a form. Not shown to users."),
    )
    form_name = forms.SlugField(
        label=_("Form identifier"),
        help_text=_(
            "Submissions are filed under this name. Keep the plugin's current "
            "identifier to keep new submissions together with the ones "
            "collected so far."
        ),
    )

    def clean_form_name(self):
        form_name = self.cleaned_data["form_name"]
        if models.Form.objects.filter(form_name=form_name).exists():
            raise ValidationError(
                _("A form with this identifier already exists."), code="unique"
            )
        return form_name
