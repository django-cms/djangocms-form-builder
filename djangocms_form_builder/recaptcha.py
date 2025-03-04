from django.apps import apps
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from .helpers import coerce_decimal

CAPTCHA_WIDGETS = {}
CAPTCHA_FIELDS = {}
CAPTCHA_CHOICES = ()

if apps.is_installed("captcha"):
    """Soft dependency on django-captcha for reCaptchaField"""

    from captcha.fields import ReCaptchaField  # NOQA
    from captcha.widgets import ReCaptchaV2Checkbox, ReCaptchaV2Invisible  # NOQA

    CAPTCHA_WIDGETS["v2-checkbox"] = ReCaptchaV2Checkbox
    CAPTCHA_WIDGETS["v2-invisible"] = ReCaptchaV2Invisible

    CAPTCHA_FIELDS["v2-checkbox"] = ReCaptchaField
    CAPTCHA_FIELDS["v2-invisible"] = ReCaptchaField

    CAPTCHA_CHOICES += (
        ("v2-checkbox", f"reCaptcha - {_('v2 checkbox')}"),
        ("v2-invisible", f"reCaptcha - {_('v2 invisible')}"),
    )

if apps.is_installed("hcaptcha"):
    """Soft dependency on django-hcaptcha for hcaptcha"""

    from hcaptcha.fields import hCaptchaField  # NOQA
    from hcaptcha.widgets import hCaptchaWidget  # NOQA

    CAPTCHA_FIELDS["hcaptcha"] = hCaptchaField
    CAPTCHA_WIDGETS["hcaptcha"] = hCaptchaWidget

    CAPTCHA_CHOICES += (("hcaptcha", _("hCaptcha")),)

if len(CAPTCHA_CHOICES) > 0:
    installed = True
else:
    installed = False


def get_recaptcha_field(instance):
    config = instance.captcha_config
    widget_params = {
        "attrs": {
            key: value
            for key, value in config.get("captcha_config", {}).items()
            if key.startswith("data-")
        },
        "api_params": {
            key: value
            for key, value in config.get("captcha_config", {}).items()
            if not key.startswith("data-")
        },
    }
    widget_params["attrs"]["no_field_sep"] = True
    if config.get("captcha_widget", "") == "v3":
        widget_params["attrs"]["required_score"] = coerce_decimal(
            config.get("captcha_requirement", 0.5)
        )  # installing recaptcha 3 ?
    if not widget_params["api_params"]:
        del widget_params["api_params"]
    return CAPTCHA_FIELDS[instance.captcha_widget](
        widget=CAPTCHA_WIDGETS[instance.captcha_widget](**widget_params), label=""
    )


keys_available = installed and (
    hasattr(settings, "RECAPTCHA_PUBLIC_KEY")
    and hasattr(settings, "RECAPTCHA_PRIVATE_KEY")
)

field_name = "captcha_field"
RECAPTCHA_PUBLIC_KEY = getattr(settings, "RECAPTCHA_PUBLIC_KEY", "")
