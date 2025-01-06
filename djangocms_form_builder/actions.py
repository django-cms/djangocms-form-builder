import hashlib

from django import forms
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import mail_admins, send_mail
from django.core.validators import EmailValidator
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
from entangled.forms import EntangledModelFormMixin

from . import models
from .entry_model import FormEntry
from .helpers import get_option, insert_fields
from .settings import MAIL_TEMPLATE_SETS

_action_registry = {}


def get_registered_actions():
    """Creates a tuple for a ChoiceField to select form"""
    result = tuple(
        (hash, action_class.verbose_name)
        for hash, action_class in _action_registry.items()
    )
    return result if result else ((_("No actions registered"), ()),)


def register(action_class):
    """Function to call or decorator for an Action class to make it available for the plugin"""

    if not issubclass(action_class, FormAction):
        raise ImproperlyConfigured(
            "djangocms_form_builder.actions.register only "
            "accepts subclasses of djangocms_form_builder.actions.FormAction"
        )
    if not action_class.verbose_name:
        raise ImproperlyConfigured(
            "FormActions need to have a verbose_name property to be registered",
        )
    hash = hashlib.sha1(action_class.__name__.encode("utf-8")).hexdigest()
    _action_registry.update({hash: action_class})
    return action_class


def unregister(action_class):
    hash = hashlib.sha1(action_class.__name__.encode("utf-8")).hexdigest()
    if hash in _action_registry:
        del _action_registry[hash]
    return action_class


def get_action_class(action):
    return _action_registry.get(action, None)


class ActionMixin:
    """Adds action form elements to Form plugin admin"""
    def get_form(self, request, *args, **kwargs):
        """Creates new form class based adding the actions as mixins"""
        return type(
            "FormActionAdminForm",
            (self.form, *_action_registry.values()),
            {}
        )

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        for action in _action_registry.values():
            new_fields = list(action.declared_fields.keys())
            if new_fields:
                hash = hashlib.sha1(action.__name__.encode("utf-8")).hexdigest()
                fieldsets = insert_fields(
                    fieldsets,
                    new_fields,
                    block=None,
                    position=-1,
                    blockname=action.verbose_name,
                    blockattrs=dict(classes=(hash, 'action-hide')),
                )
        return fieldsets


class FormAction(EntangledModelFormMixin):
    class Meta:
        entangled_fields = {"action_parameters": []}
        model = models.Form
        exclude = ()

    class Media:
        js = ("djangocms_form_builder/js/actions_form.js",)
        css = {"all": ("djangocms_form_builder/css/actions_form.css",)}

    verbose_name = None

    def execute(self, form, request):
        raise NotImplementedError()

    @staticmethod
    def get_parameter(form, param):
        return (get_option(form, "form_parameters") or {}).get(param, None)


@register
class SaveToDBAction(FormAction):
    verbose_name = _("Save form submission")

    def execute(self, form, request):
        if get_option(form, "unique", False) and get_option(
            form, "login_required", False
        ):
            keys = {
                "form_name": get_option(form, "form_name"),
                "form_user": request.user,
            }
            defaults = {}
        else:
            keys = {}
            defaults = {
                "form_name": get_option(form, "form_name"),
                "form_user": None if request.user.is_anonymous else request.user
            }
        defaults.update(
            {
                "entry_data": form.cleaned_data,
                "html_headers": dict(
                    user_agent=request.headers["User-Agent"],
                    referer=request.headers["Referer"],
                ),
            }
        )
        if keys:  # update_or_create only works if at least one key is given
            try:
                FormEntry.objects.update_or_create(**keys, defaults=defaults)
            except FormEntry.MultipleObjectsReturned:  # Delete outdated objects
                FormEntry.objects.filter(**keys).delete()
                FormEntry.objects.create(**keys, **defaults)
        else:
            FormEntry.objects.create(**defaults), True


SAVE_TO_DB_ACTION = next(iter(_action_registry)) if _action_registry else None


def validate_recipients(value):
    recipients = value.split()
    for recipient in recipients:
        EmailValidator(message=_("Please replace \"%s\" by a valid email address.") % recipient)(recipient)


@register
class SendMailAction(FormAction):
    class Meta:
        entangled_fields = {
            "action_parameters": [
                "sendemail_recipients",
                "sendemail_template",
            ]
        }

    verbose_name = _("Send email")
    from_mail = None
    template = "djangocms_form_builder/actions/mail.html"
    subject = _("%(form_name)s form submission")

    sendemail_recipients = forms.CharField(
        label=_("Mail recipients"),
        required=False,
        initial="",
        validators=[
            validate_recipients,
        ],
        help_text=_("Space or newline separated list of email addresses."),
        widget=forms.Textarea,
    )

    sendemail_template = forms.ChoiceField(
        label=_("Mail template set"),
        required=True,
        initial=MAIL_TEMPLATE_SETS[0][0],
        choices=MAIL_TEMPLATE_SETS,
        widget=forms.Select if len(MAIL_TEMPLATE_SETS) > 1 else forms.HiddenInput,
    )

    def execute(self, form, request):
        recipients = (self.get_parameter(form, "sendemail_recipients") or [])
        template_set = self.get_parameter(form, "sendemail_template") or "default"
        context = dict(
            cleaned_data=form.cleaned_data,
            form_name=getattr(form.Meta, "verbose_name", ""),
            user=request.user,
            user_agent=request.headers["User-Agent"],
            referer=request.headers["Referer"],
        )

        html_message = render_to_string(f"djangocms_form_builder/mails/{template_set}/mail_html.html", context)
        try:
            message = render_to_string(f"djangocms_form_builder/mails/{template_set}/mail.txt", context)
        except TemplateDoesNotExist:
            message = strip_tags(html_message)
        try:
            subject = render_to_string(f"djangocms_form_builder/mails/{template_set}/subject.txt", context)
        except TemplateDoesNotExist:
            subject = self.subject % dict(form_name=context["form_name"])
        if not recipients:
            mail_admins(
                subject,
                message,
                fail_silently=True,
                html_message=html_message,
            )
        else:
            send_mail(
                subject,
                message,
                recipients,
                self.from_mail,
                fail_silently=True,
                html_message=html_message,
            )
