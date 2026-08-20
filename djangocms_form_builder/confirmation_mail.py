"""Helpers for the confirmation mail sent to the person who submitted a form.

Mailing an address that an anonymous visitor typed into a form turns a site into
a potential mail relay. Two mechanisms keep that in check: the rate limits of
:mod:`djangocms_form_builder.rate_limit`, and the fact that the mail body is
rendered from server-owned templates only - editors pick a template set, they
never provide content.

Messages are handed to a bounded worker pool so that a slow mail server delays
neither the visitor's submission nor the remaining form actions.
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from threading import BoundedSemaphore, Lock

from django import forms
from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.core.validators import validate_email
from django.template import TemplateDoesNotExist

from . import recaptcha
from .helpers import get_option
from .settings import CONFIRMATION_MAIL_FIELD_NAME, CONFIRMATION_MAIL_TEMPLATE_KEYS

logger = logging.getLogger(__name__)

#: Submitted values are truncated before they enter the mail templates.
MAX_CONTEXT_VALUE_LENGTH = 2000

_executor = None
_executor_lock = Lock()


def _positive_setting(name, default):
    value = int(getattr(django_settings, name, default))
    if value < 1:
        raise ImproperlyConfigured(f"{name} must be a positive integer")
    return value


class _BoundedMailExecutor:
    """A process-local executor with a hard cap on outstanding messages."""

    def __init__(self, max_workers, max_pending):
        self._slots = BoundedSemaphore(max_pending)
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="form-confirmation-mail",
        )

    def submit(self, message):
        if not self._slots.acquire(blocking=False):
            return False
        try:
            self._executor.submit(self._send, message)
        except Exception:
            self._slots.release()
            raise
        return True

    def _send(self, message):
        try:
            message.send(fail_silently=False)
        except Exception:
            logger.exception("Failed to send form confirmation mail")
        finally:
            self._slots.release()

    def shutdown(self, wait=True):
        self._executor.shutdown(wait=wait)


def get_executor():
    # Create it upon the first submission, rather than at import time before a
    # WSGI server may fork worker processes.
    global _executor
    if _executor is None:
        with _executor_lock:
            if _executor is None:
                _executor = _BoundedMailExecutor(
                    max_workers=_positive_setting(
                        "DJANGOCMS_CONFIRMATION_MAIL_WORKERS", 2
                    ),
                    max_pending=_positive_setting(
                        "DJANGOCMS_CONFIRMATION_MAIL_MAX_PENDING", 10
                    ),
                )
    return _executor


def dispatch(message):
    """Queue ``message`` for delivery. False means the queue is full."""
    try:
        return get_executor().submit(message)
    except Exception:
        logger.exception("Failed to enqueue form confirmation mail")
        return False


def template_name(template_set, filename):
    if template_set not in CONFIRMATION_MAIL_TEMPLATE_KEYS:
        raise TemplateDoesNotExist(template_set)
    return f"djangocms_form_builder/confirmation_mails/{template_set}/{filename}"


def get_recipient(form):
    """The submitted address, or an empty string if the form has none.

    Requiring an actual email field (and not just a same-named text field)
    keeps a form from being turned into a mail relay by accident.
    """
    field = form.fields.get(CONFIRMATION_MAIL_FIELD_NAME)
    value = form.cleaned_data.get(CONFIRMATION_MAIL_FIELD_NAME)
    if not isinstance(field, forms.EmailField) or not value:
        return ""
    try:
        validate_email(value)
    except ValidationError:
        return ""
    return value


def is_protected(form):
    """Whether the form is protected against automated submissions."""
    if get_option(form, "login_required", False):
        return True
    captcha = form.fields.get(recaptcha.field_name)
    return bool(recaptcha.CAPTCHA_FIELD_CLASSES) and isinstance(
        captcha, recaptcha.CAPTCHA_FIELD_CLASSES
    )


def _plain_value(value):
    """Turn submitted values into bounded text safe for template context."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return tuple(_plain_value(item) for item in value)
    # The encoding round-trip deliberately removes SafeString/SafeData markers
    # so even unexpectedly pre-marked input is escaped again by the templates.
    return (str(value).encode("utf-8", errors="replace").decode("utf-8"))[
        :MAX_CONTEXT_VALUE_LENGTH
    ]


def get_context(form):
    """Context for the mail templates: the submitted values as plain text."""
    fields = {}
    rows = []
    for name, field in form.fields.items():
        value = form.cleaned_data.get(name)
        if (
            name == recaptcha.field_name
            or isinstance(field, forms.FileField)
            or isinstance(value, UploadedFile)
            or (
                recaptcha.CAPTCHA_FIELD_CLASSES
                and isinstance(field, recaptcha.CAPTCHA_FIELD_CLASSES)
            )
        ):
            continue
        plain_value = _plain_value(value)
        fields[name] = plain_value
        rows.append(
            {
                "name": name,
                "label": str(field.label or name),
                "value": plain_value,
            }
        )
    return {
        "form_name": get_option(form, "form_name", ""),
        "form_fields": fields,
        "form_field_rows": rows,
    }
