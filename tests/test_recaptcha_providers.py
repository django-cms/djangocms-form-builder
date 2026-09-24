import importlib
import sys
from types import ModuleType
from unittest.mock import patch

from django import forms
from django.test import SimpleTestCase

from djangocms_form_builder import recaptcha


class ProviderWidget(forms.Widget):
    def __init__(self, **kwargs):
        self.options = kwargs
        super().__init__(attrs=kwargs.get("attrs"))


class ReCaptchaField(forms.Field):
    pass


class ReCaptchaV2Checkbox(ProviderWidget):
    pass


class ReCaptchaV2Invisible(ProviderWidget):
    pass


class hCaptchaField(forms.Field):
    pass


class hCaptchaWidget(ProviderWidget):
    pass


def provider_modules(provider):
    package = ModuleType(provider)
    package.__path__ = []
    fields = ModuleType(f"{provider}.fields")
    widgets = ModuleType(f"{provider}.widgets")
    if provider == "captcha":
        fields.ReCaptchaField = ReCaptchaField
        widgets.ReCaptchaV2Checkbox = ReCaptchaV2Checkbox
        widgets.ReCaptchaV2Invisible = ReCaptchaV2Invisible
    else:
        fields.hCaptchaField = hCaptchaField
        widgets.hCaptchaWidget = hCaptchaWidget
    return {
        provider: package,
        f"{provider}.fields": fields,
        f"{provider}.widgets": widgets,
    }


class OptionalCaptchaProviderTests(SimpleTestCase):
    def reload_with_provider(self, provider):
        modules = provider_modules(provider)
        with (
            patch.dict(sys.modules, modules),
            patch.object(
                recaptcha.apps,
                "is_installed",
                side_effect=lambda app_name: app_name == provider,
            ),
        ):
            return importlib.reload(recaptcha)

    def tearDown(self):
        importlib.reload(recaptcha)
        super().tearDown()

    def test_recaptcha_provider_initialization(self):
        loaded = self.reload_with_provider("captcha")

        self.assertEqual(
            [value for value, _label in loaded.CAPTCHA_CHOICES],
            ["v2-checkbox", "v2-invisible"],
        )
        self.assertIs(loaded.CAPTCHA_FIELDS["v2-checkbox"], ReCaptchaField)
        self.assertIs(loaded.CAPTCHA_WIDGETS["v2-invisible"], ReCaptchaV2Invisible)
        instance = type(
            "Instance",
            (),
            {
                "captcha_widget": "v2-checkbox",
                "captcha_config": {"data-theme": "dark", "hl": "de"},
            },
        )()

        field = loaded.get_recaptcha_field(instance)

        self.assertIsInstance(field, ReCaptchaField)
        self.assertEqual(field.widget.options["attrs"]["data-theme"], "dark")
        self.assertTrue(field.widget.options["attrs"]["no_field_sep"])
        self.assertEqual(field.widget.options["api_params"], {"hl": "de"})

    def test_hcaptcha_provider_initialization(self):
        loaded = self.reload_with_provider("hcaptcha")

        self.assertEqual(
            [value for value, _label in loaded.CAPTCHA_CHOICES], ["hcaptcha"]
        )
        self.assertIs(loaded.CAPTCHA_FIELDS["hcaptcha"], hCaptchaField)
        self.assertIs(loaded.CAPTCHA_WIDGETS["hcaptcha"], hCaptchaWidget)
        instance = type(
            "Instance",
            (),
            {
                "captcha_widget": "hcaptcha",
                "captcha_config": {"data-size": "compact"},
            },
        )()

        field = loaded.get_recaptcha_field(instance)

        self.assertIsInstance(field, hCaptchaField)
        self.assertEqual(field.widget.options["attrs"]["data-size"], "compact")
        self.assertNotIn("api_params", field.widget.options)
