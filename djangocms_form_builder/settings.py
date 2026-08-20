import importlib
import re

from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import default_storage
from django.utils.translation import gettext_lazy as _

EMPTY_CHOICE = (("", "-----"),)

FORM_OPTIONS = getattr(django_settings, "DJANGOCMS_FORMS_OPTIONS", {})
MAIL_TEMPLATE_SETS = getattr(
    django_settings, "DJANGOCMS_MAIL_TEMPLATE_SETS", (("default", _("Default")),)
)

#: Template sets for the confirmation mail sent to the person submitting a form.
#: djangocms-form-builder does not ship any such templates: as long as this
#: setting is empty the corresponding form action is not registered at all.
CONFIRMATION_MAIL_TEMPLATE_SETS = tuple(
    getattr(django_settings, "DJANGOCMS_CONFIRMATION_MAIL_TEMPLATE_SETS", None) or ()
)
if any(
    not isinstance(key, str) or not re.fullmatch(r"[-\w]+", key)
    for key, verbose_name in CONFIRMATION_MAIL_TEMPLATE_SETS
):
    raise ImproperlyConfigured(
        "Keys of DJANGOCMS_CONFIRMATION_MAIL_TEMPLATE_SETS must be non-empty slugs"
    )
CONFIRMATION_MAIL_TEMPLATE_KEYS = frozenset(
    key for key, verbose_name in CONFIRMATION_MAIL_TEMPLATE_SETS
)
#: Name of the form field carrying the address a confirmation mail is sent to.
CONFIRMATION_MAIL_FIELD_NAME = getattr(
    django_settings, "DJANGOCMS_CONFIRMATION_MAIL_FIELD_NAME", "email"
)


def _validate_rate_limits(rate_limits):
    """Check the ``{action: {kind: (limit, window)}}`` structure early."""
    if not isinstance(rate_limits, dict):
        raise ImproperlyConfigured(
            "DJANGOCMS_FORM_BUILDER_RATE_LIMITS must be a dict of action names"
        )
    for action, limits in rate_limits.items():
        if not isinstance(limits, dict):
            raise ImproperlyConfigured(
                f"DJANGOCMS_FORM_BUILDER_RATE_LIMITS['{action}'] must be a dict "
                "mapping a quota kind to (limit, window in seconds)"
            )
        for kind, spec in limits.items():
            if spec is None:  # Switches a built-in limit of the action off
                continue
            try:
                limit, window = (int(value) for value in spec)
            except (TypeError, ValueError):
                raise ImproperlyConfigured(
                    f"DJANGOCMS_FORM_BUILDER_RATE_LIMITS['{action}']['{kind}'] "
                    "must be a (limit, window in seconds) pair of integers"
                ) from None
            if limit < 1 or window < 1:
                raise ImproperlyConfigured(
                    f"DJANGOCMS_FORM_BUILDER_RATE_LIMITS['{action}']['{kind}'] "
                    "must use positive integers"
                )
    return rate_limits


#: Rate limits for form actions, see ``djangocms_form_builder.rate_limit``.
RATE_LIMITS = _validate_rate_limits(
    getattr(django_settings, "DJANGOCMS_FORM_BUILDER_RATE_LIMITS", None) or {}
)
#: ``request.META`` key identifying the submitting client, e.g. set it to
#: ``"HTTP_X_FORWARDED_FOR"`` if your project runs behind a trusted proxy.
RATE_LIMIT_IP_META_KEY = getattr(
    django_settings, "DJANGOCMS_FORM_BUILDER_RATE_LIMIT_IP_META_KEY", "REMOTE_ADDR"
)

framework = getattr(django_settings, "DJANGOCMS_FRONTEND_FRAMEWORK", "bootstrap5")
theme = getattr(django_settings, "DJANGOCMS_FRONTEND_THEME", "djangocms_frontend")

DEFAULT_SPACER_SIZE_CHOICES = (("mb-3", "Default"),)
TAG_CHOICES = (("div", "div"),)
FORM_TEMPLATE = getattr(
    django_settings,
    "FORM_TEMPLATE",
    f"djangocms_form_builder/{framework}/render/form.html",
)

theme_render_path = f"{theme}.frameworks.{framework}"

if not getattr(django_settings, "DJANGO_FORM_BUILDER_SPACER_CHOICES", False):
    if not getattr(django_settings, "DJANGOCMS_FRONTEND_SPACER_SIZES", False):
        SPACER_SIZE_CHOICES = DEFAULT_SPACER_SIZE_CHOICES
    else:
        SPACER_SIZE_CHOICES = [
            (f"mb-{key}", value)
            for key, value in django_settings.DJANGOCMS_FRONTEND_SPACER_SIZES
        ]
else:
    SPACER_SIZE_CHOICES = django_settings.DJANGO_FORM_BUILDER_SPACER_CHOICES


ALTCHA_FIELD_OPTIONS = getattr(
    django_settings, "ALTCHA_FIELD_OPTIONS", {}
)  # See https://github.com/aboutcode-org/django-altcha/blob/9d0895f5f77fec058272821502cbb71d0cabab50/django_altcha/__init__.py#L134 for config options


FILE_FIELD_STORAGE = getattr(
    django_settings, "DJANGOCMS_FORM_BUILDER_FILE_FIELD_STORAGE", default_storage
)


def render_factory(cls, theme_module, render_module):
    parents = tuple(
        getattr(module, cls, None)
        for module in (theme_module, render_module)
        if module is not None and getattr(module, cls, None) is not None
    )
    return type(cls, parents, dict())  # Empty Mix


def get_mixins(naming, theme_path, mixin_path):
    try:
        theme_module = importlib.import_module(theme_path) if theme_path else None
    except ModuleNotFoundError:
        theme_module = None
    try:
        render_module = importlib.import_module(mixin_path) if mixin_path else None
    except ModuleNotFoundError:
        render_module = None

    return lambda name: render_factory(
        naming.format(name=name), theme_module, render_module
    )


def get_renderer(my_module):
    if not isinstance(my_module, str):
        my_module = my_module.__name__
    return get_mixins(
        "{name}RenderMixin", theme_render_path, f"{my_module}.frameworks.{framework}"
    )
