import importlib

from django.test import TestCase, override_settings

import djangocms_form_builder.constants as constants_module
import djangocms_form_builder.settings as builder_settings_module
from djangocms_form_builder.frontends import bootstrap5 as bootstrap5_module
from djangocms_form_builder.frontends import foundation6 as foundation6_module


class SubmitButtonChoicesTestCase(TestCase):
    def tearDown(self):
        # Reload modules with default settings to avoid leaking state
        importlib.reload(builder_settings_module)
        importlib.reload(bootstrap5_module)
        importlib.reload(foundation6_module)
        importlib.reload(constants_module)
        super().tearDown()

    def test_submit_button_choices_default(self):
        with override_settings(
            DJANGO_FORM_BUILDER_COLOR_STYLE_CHOICES=None,
            DJANGOCMS_FRONTEND_COLOR_STYLE_CHOICES=None,
        ):
            importlib.reload(bootstrap5_module)
            importlib.reload(constants_module)

            self.assertEqual(
                bootstrap5_module.SUBMIT_BUTTON_CHOICES,
                bootstrap5_module.DEFAULT_COLOR_STYLE_CHOICES,
            )
            self.assertEqual(
                constants_module.SUBMIT_BUTTON_CHOICES,
                bootstrap5_module.DEFAULT_COLOR_STYLE_CHOICES,
            )

    def test_submit_button_choices_from_djangocms_frontend_color_style_choices(self):
        frontend_choices = (
            ("primary", "Primary"),
            ("danger", "Danger"),
        )
        expected = (
            ("primary", "Primary"),
            ("danger", "Danger"),
        )

        with override_settings(
            DJANGO_FORM_BUILDER_COLOR_STYLE_CHOICES=None,
            DJANGOCMS_FRONTEND_COLOR_STYLE_CHOICES=frontend_choices,
        ):
            importlib.reload(bootstrap5_module)
            importlib.reload(constants_module)

            self.assertEqual(bootstrap5_module.SUBMIT_BUTTON_CHOICES, expected)
            self.assertEqual(constants_module.SUBMIT_BUTTON_CHOICES, expected)

    def test_submit_button_choices_form_builder_setting_takes_precedence(self):
        builder_choices = (("custom", "Custom"),)
        frontend_choices = (("primary", "Primary"),)

        with override_settings(
            DJANGOCMS_FORM_BUILDER_COLOR_STYLE_CHOICES=builder_choices,
            DJANGOCMS_FRONTEND_COLOR_STYLE_CHOICES=frontend_choices,
        ):
            importlib.reload(bootstrap5_module)
            importlib.reload(constants_module)

            self.assertEqual(bootstrap5_module.SUBMIT_BUTTON_CHOICES, builder_choices)
            self.assertEqual(constants_module.SUBMIT_BUTTON_CHOICES, builder_choices)

    def test_submit_button_choices_default_foundation6(self):
        with override_settings(
            DJANGOCMS_FRONTEND_FRAMEWORK="foundation6",
            DJANGOCMS_FORM_BUILDER_COLOR_STYLE_CHOICES=None,
            DJANGOCMS_FRONTEND_COLOR_STYLE_CHOICES=None,
        ):
            importlib.reload(builder_settings_module)
            importlib.reload(foundation6_module)
            importlib.reload(constants_module)

            self.assertEqual(
                foundation6_module.SUBMIT_BUTTON_CHOICES,
                foundation6_module.DEFAULT_COLOR_STYLE_CHOICES,
            )
            self.assertEqual(
                constants_module.SUBMIT_BUTTON_CHOICES,
                foundation6_module.DEFAULT_COLOR_STYLE_CHOICES,
            )

    def test_submit_button_choices_from_djangocms_frontend_color_style_choices_foundation6(
        self,
    ):
        frontend_choices = (
            ("primary", "Primary"),
            ("danger", "Danger"),
        )
        expected = [
            ("mb-primary", "Primary"),
            ("mb-danger", "Danger"),
        ]

        with override_settings(
            DJANGOCMS_FRONTEND_FRAMEWORK="foundation6",
            DJANGO_FORM_BUILDER_COLOR_STYLE_CHOICES=None,
            DJANGOCMS_FRONTEND_COLOR_STYLE_CHOICES=frontend_choices,
        ):
            importlib.reload(builder_settings_module)
            importlib.reload(foundation6_module)
            importlib.reload(constants_module)

            self.assertEqual(foundation6_module.SUBMIT_BUTTON_CHOICES, expected)
            self.assertEqual(constants_module.SUBMIT_BUTTON_CHOICES, expected)

    def test_submit_button_choices_form_builder_setting_takes_precedence_foundation6(
        self,
    ):
        builder_choices = (("custom", "Custom"),)
        frontend_choices = (("primary", "Primary"),)

        with override_settings(
            DJANGOCMS_FRONTEND_FRAMEWORK="foundation6",
            DJANGO_FORM_BUILDER_COLOR_STYLE_CHOICES=builder_choices,
            DJANGOCMS_FRONTEND_COLOR_STYLE_CHOICES=frontend_choices,
        ):
            importlib.reload(builder_settings_module)
            importlib.reload(foundation6_module)
            importlib.reload(constants_module)

            self.assertEqual(foundation6_module.SUBMIT_BUTTON_CHOICES, builder_choices)
            self.assertEqual(constants_module.SUBMIT_BUTTON_CHOICES, builder_choices)
