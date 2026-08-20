import hashlib
import logging

from django import forms
from django.apps import apps
from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMultiAlternatives
from django.core.validators import EmailValidator
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
from entangled.forms import EntangledModelFormMixin

try:
    from djangocms_text.fields import HTMLFormField
except ModuleNotFoundError:

    class HTMLFormField(forms.CharField):
        """Plain-text fallback if djangocms-text is not installed."""

        widget = forms.Textarea


from . import confirmation_mail, models
from .entry_model import FormEntry
from .form_entry_data import (
    delete_stored_files,
    iter_stored_file_metadata,
    serialize_cleaned_data_for_entry,
)
from .helpers import get_option, insert_fields
from .rate_limit import check_rate_limits, client_address
from .settings import (
    CONFIRMATION_MAIL_FIELD_NAME,
    CONFIRMATION_MAIL_TEMPLATE_KEYS,
    CONFIRMATION_MAIL_TEMPLATE_SETS,
    MAIL_TEMPLATE_SETS,
)

logger = logging.getLogger(__name__)

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


def get_hash(action_class):
    return hashlib.sha1(action_class.__name__.encode("utf-8")).hexdigest()


class ActionMixin:
    """Adds action form elements to Form plugin admin"""

    def get_form(self, request, *args, **kwargs):
        """Creates new form class based adding the actions as mixins"""
        return type("FormActionAdminForm", (self.form, *_action_registry.values()), {})

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
                    blockattrs=dict(classes=(f"c{hash}", "action-hide")),
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

    #: Built-in rate limits of this action as ``{kind: (limit, window)}``.
    #: Projects override them per action class name in the
    #: ``DJANGOCMS_FORM_BUILDER_RATE_LIMITS`` setting.
    rate_limits = {}

    def execute(self, form, request):
        raise NotImplementedError()

    def get_rate_limit_values(self, form, request):
        """The values this submission is counted against, by quota kind.

        Actions add their own kinds here, e.g. the address a mail would be sent
        to. Kinds that an action does not provide are not rate limited.
        """
        return {"source": client_address(request)}

    def check_rate_limits(self, form, request):
        """Consume this submission's quotas. ``False`` means: do not execute."""
        return check_rate_limits(self, form, request)

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
                "form_user": None if request.user.is_anonymous else request.user,
            }
        previous_data = None
        previous_names = set()
        cleaned_data = dict(form.cleaned_data)
        if keys:
            existing_entries = FormEntry.objects.filter(**keys).only("entry_data")
            previous = existing_entries.first()
            has_multiple = (
                previous and existing_entries.exclude(pk=previous.pk).exists()
            )
            if previous and not has_multiple:
                previous_data = previous.entry_data
                previous_names = {
                    meta.get("name")
                    for meta in iter_stored_file_metadata(previous_data)
                }
                # An empty optional file input means "no replacement". Preserve
                # the existing upload; an explicit False still removes it.
                for key in previous.get_file_entry_data_keys():
                    if cleaned_data.get(key) in (None, []):
                        cleaned_data[key] = previous_data[key]

        serialized_data = serialize_cleaned_data_for_entry(cleaned_data)
        defaults["entry_data"] = serialized_data
        if keys:  # update_or_create only works if at least one key is given
            try:
                FormEntry.objects.update_or_create(**keys, defaults=defaults)
            except FormEntry.MultipleObjectsReturned:  # Delete outdated objects
                FormEntry.objects.filter(**keys).delete()
                try:
                    FormEntry.objects.create(**keys, **defaults)
                except Exception:
                    delete_stored_files(serialized_data)
                    raise
                previous_data = None  # queryset deletion already removed its files
            except Exception:
                delete_stored_files(serialized_data, excluding=previous_names)
                raise
        else:
            try:
                FormEntry.objects.create(**defaults)
            except Exception:
                delete_stored_files(serialized_data)
                raise

        if previous_data:
            retained_names = {
                meta.get("name") for meta in iter_stored_file_metadata(serialized_data)
            }
            delete_stored_files(previous_data, excluding=retained_names)


SAVE_TO_DB_ACTION = next(iter(_action_registry)) if _action_registry else None


def validate_recipients(value):
    recipients = value.split()
    for recipient in recipients:
        EmailValidator(
            message=_('Please replace "%s" by a valid email address.') % recipient
        )(recipient)


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
        from django.core.mail import mail_admins, send_mail

        recipients = self.get_parameter(form, "sendemail_recipients") or ""
        template_set = self.get_parameter(form, "sendemail_template") or "default"
        context = dict(
            form_entry=FormEntry.objects.last(),
            form_name=getattr(form.Meta, "verbose_name", ""),
            user=request.user,
            user_agent=request.headers["User-Agent"]
            if "User-Agent" in request.headers
            else "",
            referer=request.headers["Referer"] if "Referer" in request.headers else "",
        )

        html_message = render_to_string(
            f"djangocms_form_builder/mails/{template_set}/mail_html.html", context
        )
        try:
            message = render_to_string(
                f"djangocms_form_builder/mails/{template_set}/mail.txt", context
            )
        except TemplateDoesNotExist:
            message = strip_tags(html_message)
        try:
            subject = render_to_string(
                f"djangocms_form_builder/mails/{template_set}/subject.txt", context
            )
            # Strip beginning and ending new lines
            subject = subject.strip()
        except TemplateDoesNotExist:
            subject = self.subject % dict(form_name=context["form_name"])

        # A failed email must not break the form submission for the user,
        # but it must not go unnoticed either - hence log instead of raise.
        try:
            if not recipients:
                return mail_admins(
                    subject,
                    message,
                    fail_silently=False,
                    html_message=html_message,
                )
            else:
                return send_mail(
                    subject,
                    message,
                    self.from_mail,
                    recipients.split(),
                    fail_silently=False,
                    html_message=html_message,
                )
        except Exception:
            logger.exception(
                "Failed to send email for submission of form %s",
                context["form_name"],
            )


@register
class SuccessMessageAction(FormAction):
    verbose_name = _("Success message")

    class Meta:
        entangled_fields = {
            "action_parameters": [
                "submitmessage_message",
            ]
        }

    submitmessage_message = HTMLFormField(
        label=_("Message"),
        required=True,
        initial=_("<p>Thank you for your submission.</p>"),
    )

    def execute(self, form, request):
        from .cms_plugins.ajax_plugins import SAME_PAGE_REDIRECT

        message = self.get_parameter(form, "submitmessage_message")
        # Overwrite the success context and render template
        form.get_success_context = lambda *args, **kwargs: {"message": message}
        form.Meta.options["render_success"] = (
            "djangocms_form_builder/actions/submit_message.html"
        )
        # Overwrite the default redirect to same page
        if form.Meta.options.get("redirect") == SAME_PAGE_REDIRECT:
            form.Meta.options["redirect"] = None


if apps.is_installed("djangocms_link"):
    from djangocms_link.fields import LinkFormField
    from djangocms_link.helpers import get_link

    @register
    class RedirectAction(FormAction):
        verbose_name = _("Redirect after submission")

        class Meta:
            entangled_fields = {
                "action_parameters": [
                    "redirect_link",
                ]
            }

        redirect_link = LinkFormField(
            label=_("Link"),
            required=True,
        )

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if args:
                self.fields["redirect_link"].required = get_hash(
                    RedirectAction
                ) in args[0].get("form_actions", [])

        def execute(self, form, request):
            form.Meta.options["redirect"] = get_link(
                self.get_parameter(form, "redirect_link")
            )


if CONFIRMATION_MAIL_TEMPLATE_SETS:
    # Without configured template sets there is nothing to send: the action
    # stays unregistered and does not show up in the form plugin.

    @register
    class SendConfirmationMailAction(FormAction):
        """Send a server-owned mail template to the address that was submitted."""

        class Meta:
            entangled_fields = {
                "action_parameters": [
                    "confirmationmail_template",
                ]
            }

        verbose_name = _("Send confirmation email to submitter")
        rate_limits = {
            "source": (10, 60 * 60),
            "recipient": (3, 24 * 60 * 60),
        }

        confirmationmail_template = forms.ChoiceField(
            label=_("Confirmation mail template set"),
            required=True,
            initial=CONFIRMATION_MAIL_TEMPLATE_SETS[0][0],
            choices=CONFIRMATION_MAIL_TEMPLATE_SETS,
            widget=forms.Select
            if len(CONFIRMATION_MAIL_TEMPLATE_SETS) > 1
            else forms.HiddenInput,
        )

        def get_rate_limit_values(self, form, request):
            values = super().get_rate_limit_values(form, request)
            recipient = confirmation_mail.get_recipient(form)
            if recipient:
                values["recipient"] = recipient.casefold()
            return values

        def execute(self, form, request):
            form_name = get_option(form, "form_name", "")
            recipient = confirmation_mail.get_recipient(form)
            if not recipient:
                logger.warning(
                    "Confirmation mail skipped: form %s has no valid email field %r",
                    form_name,
                    CONFIRMATION_MAIL_FIELD_NAME,
                )
                return 0
            if not confirmation_mail.is_protected(form):
                logger.warning(
                    "Confirmation mail skipped: form %s requires neither login "
                    "nor a captcha",
                    form_name,
                )
                return 0

            template_set = self.get_parameter(form, "confirmationmail_template")
            if template_set not in CONFIRMATION_MAIL_TEMPLATE_KEYS:
                logger.error(
                    "Confirmation mail skipped: unknown template set %r", template_set
                )
                return 0

            context = confirmation_mail.get_context(form)
            try:
                subject = render_to_string(
                    confirmation_mail.template_name(template_set, "subject.txt"),
                    context,
                )
            except TemplateDoesNotExist:
                logger.exception(
                    "Confirmation mail skipped: template set %s has no subject",
                    template_set,
                )
                return 0
            # The templates are server-owned and auto-escaping remains enabled.
            # Do not apply the `safe` filter to submitted values in them.
            try:
                message = render_to_string(
                    confirmation_mail.template_name(template_set, "mail.txt"), context
                )
            except TemplateDoesNotExist:
                message = ""
            try:
                html_message = render_to_string(
                    confirmation_mail.template_name(template_set, "mail_html.html"),
                    context,
                )
            except TemplateDoesNotExist:
                html_message = ""
            if not message and not html_message:
                logger.error(
                    "Confirmation mail skipped: template set %s has no mail body",
                    template_set,
                )
                return 0

            subject = " ".join(subject.splitlines()).strip()
            if not message:
                message = strip_tags(html_message)

            mail = EmailMultiAlternatives(
                subject=subject,
                body=message,
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                to=[recipient],
                headers={
                    "Auto-Submitted": "auto-generated",
                    "X-Auto-Response-Suppress": "All",
                },
            )
            if html_message:
                mail.attach_alternative(html_message, "text/html")

            if not confirmation_mail.dispatch(mail):
                logger.warning("Confirmation mail skipped: delivery queue is full")
                return 0
            return 1
