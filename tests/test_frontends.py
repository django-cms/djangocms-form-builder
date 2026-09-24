import importlib

from django import forms
from django.template import RequestContext, Template
from django.test import RequestFactory, TestCase, override_settings

import djangocms_form_builder.constants as constants_module
import djangocms_form_builder.settings as builder_settings_module
from djangocms_form_builder.frontends import bootstrap5 as bootstrap5_module
from djangocms_form_builder.frontends import django_formset as django_formset_module
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
            DJANGOCMS_FORM_BUILDER_FRONTEND="bootstrap5",
            DJANGO_FORM_BUILDER_COLOR_STYLE_CHOICES=None,
            DJANGOCMS_FRONTEND_COLOR_STYLE_CHOICES=None,
        ):
            importlib.reload(builder_settings_module)
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
            DJANGOCMS_FORM_BUILDER_FRONTEND="bootstrap5",
            DJANGO_FORM_BUILDER_COLOR_STYLE_CHOICES=None,
            DJANGOCMS_FRONTEND_COLOR_STYLE_CHOICES=frontend_choices,
        ):
            importlib.reload(builder_settings_module)
            importlib.reload(bootstrap5_module)
            importlib.reload(constants_module)

            self.assertEqual(bootstrap5_module.SUBMIT_BUTTON_CHOICES, expected)
            self.assertEqual(constants_module.SUBMIT_BUTTON_CHOICES, expected)

    def test_submit_button_choices_form_builder_setting_takes_precedence(self):
        builder_choices = (("custom", "Custom"),)
        frontend_choices = (("primary", "Primary"),)

        with override_settings(
            DJANGOCMS_FORM_BUILDER_FRONTEND="bootstrap5",
            DJANGOCMS_FORM_BUILDER_COLOR_STYLE_CHOICES=builder_choices,
            DJANGOCMS_FRONTEND_COLOR_STYLE_CHOICES=frontend_choices,
        ):
            importlib.reload(builder_settings_module)
            importlib.reload(bootstrap5_module)
            importlib.reload(constants_module)

            self.assertEqual(bootstrap5_module.SUBMIT_BUTTON_CHOICES, builder_choices)
            self.assertEqual(constants_module.SUBMIT_BUTTON_CHOICES, builder_choices)

    def test_submit_button_choices_default_foundation6(self):
        with override_settings(
            DJANGOCMS_FORM_BUILDER_FRONTEND="foundation6",
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
            DJANGOCMS_FORM_BUILDER_FRONTEND="foundation6",
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
            DJANGOCMS_FORM_BUILDER_FRONTEND="foundation6",
            DJANGOCMS_FRONTEND_FRAMEWORK="foundation6",
            DJANGO_FORM_BUILDER_COLOR_STYLE_CHOICES=builder_choices,
            DJANGOCMS_FRONTEND_COLOR_STYLE_CHOICES=frontend_choices,
        ):
            importlib.reload(builder_settings_module)
            importlib.reload(foundation6_module)
            importlib.reload(constants_module)

            self.assertEqual(foundation6_module.SUBMIT_BUTTON_CHOICES, builder_choices)
            self.assertEqual(constants_module.SUBMIT_BUTTON_CHOICES, builder_choices)


class DjangoFormsetFrontendTestCase(TestCase):
    def tearDown(self):
        importlib.reload(builder_settings_module)
        importlib.reload(constants_module)
        super().tearDown()

    def test_uses_bootstrap_renderer_and_project_button_choices(self):
        self.assertEqual(
            django_formset_module.SUBMIT_BUTTON_CHOICES,
            bootstrap5_module.SUBMIT_BUTTON_CHOICES,
        )
        self.assertEqual(
            django_formset_module.FormsetRenderer.framework,
            "bootstrap",
        )

    def test_renders_field_with_django_formset(self):
        class ContactForm(forms.Form):
            name = forms.CharField(label="Name", min_length=2)

        request = RequestFactory().get("/")
        context = RequestContext(request, {"form": ContactForm()})
        template = Template(
            "{% load formsetify form_builder_tags %}"
            "{% formsetify form 'bootstrap' %}"
            "{% render_formset_widget form 'name' %}"
        )

        rendered = template.render(context)

        self.assertIn('role="group"', rendered)
        self.assertIn('class="form-control"', rendered)
        self.assertIn("dj-field-errors", rendered)
        self.assertIn('name="name"', rendered)

    def test_renders_captcha_field_with_django_formset(self):
        class CaptchaForm(forms.Form):
            captcha_field = forms.CharField(label="", widget=forms.TextInput)

        form = CaptchaForm()
        form.form_id = "captcha-form"
        request = RequestFactory().get("/")
        context = RequestContext(request, {"form": form})
        template = Template(
            "{% load formsetify form_builder_tags %}"
            "{% formsetify form 'bootstrap' %}"
            "{% render_captcha_widget form %}"
        )

        rendered = template.render(context)

        self.assertIn('role="group"', rendered)
        self.assertIn('name="captcha_field"', rendered)
        self.assertIn('form="captcha-form"', rendered)

    @override_settings(DJANGOCMS_FORM_BUILDER_FRONTEND="django_formset")
    def test_frontend_setting_takes_precedence_over_framework(self):
        importlib.reload(builder_settings_module)

        self.assertEqual(builder_settings_module.frontend, "django_formset")
