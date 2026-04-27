import re
from unittest import skipIf

from cms import __version__ as cms_version
from cms.api import add_plugin
from cms.test_utils.testcases import CMSTestCase
from django import forms
from django.template import Context, Template
from django.test import RequestFactory

from djangocms_form_builder import cms_plugins, recaptcha

from .fixtures import TestFixture


class FormRenderingTestCase(TestFixture, CMSTestCase):
    """Tests for rendering forms including template tags"""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    def test_render_simple_form_with_fields(self):
        """Test rendering a basic form with CharField and EmailField"""
        form_plugin = add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.FormPlugin.__name__,
            language=self.language,
            form_selection="",
            form_name="contact-form",
        )

        # Add CharField
        char_field = add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.CharFieldPlugin.__name__,
            target=form_plugin,
            language=self.language,
            config={
                "field_name": "full_name",
                "field_label": "Full Name",
                "field_required": True,
                "field_placeholder": "Enter your name",
                "field_help_text": "This help text should render below the field.",
            },
        )
        char_field.initialize_from_form()

        # Add EmailField
        email_field = add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.EmailFieldPlugin.__name__,
            target=form_plugin,
            language=self.language,
            config={
                "field_name": "email",
                "field_label": "Email Address",
                "field_required": True,
                "field_placeholder": "you@example.com",
            },
        )
        email_field.initialize_from_form()

        self.publish(self.page, self.language)

        with self.login_user_context(self.superuser):
            response = self.client.get(self.request_url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        # Check form tag
        self.assertIn('id="form', content)
        self.assertIn('method="post"', content)

        # Check CharField rendered
        self.assertIn('name="full_name"', content)
        self.assertIn("Full Name", content)
        self.assertIn('placeholder="Enter your name"', content)
        self.assertIn("This help text should render below the field.", content)
        match = re.search(
            r'name="full_name"[^>]*aria-describedby="(hints_[^"]+)"', content
        )
        self.assertIsNotNone(match)
        hints_id = match.group(1)
        self.assertIn(
            f'id="{hints_id}" class="form-text">This help text should render below the field.</div>',
            content,
        )

        # Check EmailField rendered
        self.assertIn('name="email"', content)
        self.assertIn("Email Address", content)
        self.assertIn('placeholder="you@example.com"', content)

    def test_render_form_with_select_field(self):
        """Test rendering form with Select field and choices"""
        form_plugin = add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.FormPlugin.__name__,
            language=self.language,
            form_selection="",
            form_name="survey-form",
        )

        # Add Select field
        select_field = add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.SelectPlugin.__name__,
            target=form_plugin,
            language=self.language,
            config={
                "field_name": "country",
                "field_label": "Select Country",
                "field_required": True,
                "field_select": "select",
            },
        )
        select_field.initialize_from_form()

        # Add choices
        for value, label in [
            ("us", "United States"),
            ("de", "Germany"),
            ("fr", "France"),
        ]:
            choice = add_plugin(
                placeholder=self.placeholder,
                plugin_type=cms_plugins.ChoicePlugin.__name__,
                target=select_field,
                language=self.language,
                config={"value": value, "verbose": label},
            )
            choice.initialize_from_form()

        self.publish(self.page, self.language)

        with self.login_user_context(self.superuser):
            response = self.client.get(self.request_url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        # Check select field rendered
        self.assertIn('name="country"', content)
        self.assertIn("Select Country", content)
        self.assertIn("<select", content)

        # Check choices rendered
        self.assertIn('value="us"', content)
        self.assertIn("United States", content)
        self.assertIn('value="de"', content)
        self.assertIn("Germany", content)
        self.assertIn('value="fr"', content)
        self.assertIn("France", content)

    def test_render_form_with_boolean_field(self):
        """Test rendering form with checkbox/boolean field"""
        form_plugin = add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.FormPlugin.__name__,
            language=self.language,
            form_selection="",
            form_name="terms-form",
        )

        # Add BooleanField
        bool_field = add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.BooleanFieldPlugin.__name__,
            target=form_plugin,
            language=self.language,
            config={
                "field_name": "agree_terms",
                "field_label": "I agree to the terms",
                "field_required": True,
                "field_as_switch": False,
            },
        )
        bool_field.initialize_from_form()

        self.publish(self.page, self.language)

        with self.login_user_context(self.superuser):
            response = self.client.get(self.request_url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        # Check boolean field rendered
        self.assertIn('name="agree_terms"', content)
        self.assertIn('type="checkbox"', content)
        self.assertIn("I agree to the terms", content)

    def test_form_with_floating_labels(self):
        """Test form renders correctly with floating labels enabled"""
        form_plugin = add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.FormPlugin.__name__,
            language=self.language,
            form_selection="",
            form_name="floating-form",
            form_floating_labels=True,
        )

        char_field = add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.CharFieldPlugin.__name__,
            target=form_plugin,
            language=self.language,
            config={
                "field_name": "username",
                "field_label": "Username",
            },
        )
        char_field.initialize_from_form()

        self.publish(self.page, self.language)

        with self.login_user_context(self.superuser):
            response = self.client.get(self.request_url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        # Check floating label class applied
        self.assertIn("form-floating", content)
        self.assertIn('name="username"', content)

    def test_render_form_with_altcha(self):
        """Test rendering form with Altcha field"""
        form_plugin = add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.FormPlugin.__name__,
            language=self.language,
            form_selection="",
            form_name="altcha-form",
            captcha_widget="altcha",
        )

        # Add CharField
        char_field = add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.CharFieldPlugin.__name__,
            target=form_plugin,
            language=self.language,
            config={
                "field_name": "full_name",
                "field_label": "Full Name",
                "field_required": True,
                "field_placeholder": "Enter your name",
                "field_help_text": "This help text should render below the field.",
            },
        )
        char_field.initialize_from_form()

        self.publish(self.page, self.language)

        with self.login_user_context(self.superuser):
            response = self.client.get(self.request_url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        # Check CharField rendered
        self.assertIn('name="full_name"', content)
        self.assertIn("Full Name", content)
        self.assertIn('placeholder="Enter your name"', content)
        self.assertIn("This help text should render below the field.", content)
        self.assertIn('id="captcha_field', content)
        self.assertIn('type="hidden"', content)
        self.assertIn('name="captcha_field"', content)
        self.assertIn('challengeurl="/altcha/challenge/"', content)
        self.assertIn("altcha.min.js", content)


class TemplateTagsTestCase(CMSTestCase):
    """Tests for template tags in djangocms_form_builder"""

    def test_render_form_tag(self):
        """Test {% render_form %} template tag"""
        template = Template("{% load form_builder_tags %}{% render_form form %}")

        class TestForm(forms.Form):
            name = forms.CharField(label="Name", max_length=100)
            email = forms.EmailField(label="Email")

        form = TestForm()
        context = Context({"form": form})
        rendered = template.render(context)

        self.assertIn('name="name"', rendered)
        self.assertIn('name="email"', rendered)
        self.assertIn("Name", rendered)
        self.assertIn("Email", rendered)

    def test_render_widget_tag(self):
        """Test {% render_widget %} template tag"""
        template = Template(
            "{% load form_builder_tags %}{% render_widget form 'name' %}"
        )

        class TestForm(forms.Form):
            name = forms.CharField(label="Full Name", help_text="Enter your full name")

        form = TestForm()
        context = Context({"form": form})
        rendered = template.render(context)

        self.assertIn('name="name"', rendered)
        self.assertIn("Full Name", rendered)
        self.assertIn("Enter your full name", rendered)
        self.assertIn('aria-describedby="hints_id_name"', rendered)
        self.assertIn(
            'id="hints_id_name" class="form-text">Enter your full name</div>',
            rendered,
        )

    def test_render_widget_with_errors(self):
        """Test {% render_widget %} shows validation errors"""
        template = Template(
            "{% load form_builder_tags %}{% render_widget form 'email' %}"
        )

        class TestForm(forms.Form):
            email = forms.EmailField(label="Email", required=True)

        # Bind form with invalid data
        form = TestForm(data={"email": "not-an-email"})
        form.is_valid()  # Trigger validation

        context = Context({"form": form})
        rendered = template.render(context)

        self.assertIn('name="email"', rendered)
        self.assertIn("invalid-feedback", rendered)
        self.assertIn("is_invalid", rendered)

    def test_add_placeholder_filter(self):
        """Test {% add_placeholder %} filter"""
        template = Template("{% load form_builder_tags %}{{ form|add_placeholder }}")

        class TestForm(forms.Form):
            username = forms.CharField(label="Username")
            password = forms.CharField(label="Password", widget=forms.PasswordInput)

        form = TestForm()
        context = Context({"form": form})
        rendered = template.render(context)

        # After applying filter, placeholders should match labels
        self.assertIn('placeholder="Username"', rendered)
        self.assertIn('placeholder="Password"', rendered)

    def test_get_fieldset_filter(self):
        """Test get_fieldset filter returns fieldsets"""
        template = Template(
            "{% load form_builder_tags %}{% for fieldset_name, fieldset in form|get_fieldset %}{{ fieldset_name }}{% endfor %}"
        )

        class TestForm(forms.Form):
            name = forms.CharField()
            email = forms.EmailField()

            class Meta:
                fieldsets = (("Personal Info", {"fields": ("name", "email")}),)

        form = TestForm()
        context = Context({"form": form})
        rendered = template.render(context)

        self.assertIn("Personal Info", rendered)

    def test_render_recaptcha_widget_when_not_installed(self):
        """Test {% render_recaptcha_widget %} when recaptcha not available"""
        template = Template(
            "{% load form_builder_tags %}{% render_recaptcha_widget form %}"
        )

        class TestForm(forms.Form):
            name = forms.CharField()

        form = TestForm()
        context = Context({"form": form})
        rendered = template.render(context)

        # Should return empty string when recaptcha not installed
        self.assertEqual(rendered.strip(), "")


class AltchaIntegrationTestCase(TestFixture, CMSTestCase):
    """Tests for Altcha CAPTCHA integration (run only when django_altcha is installed)."""

    def test_altcha_in_captcha_choices_when_installed(self):
        """Altcha choice is available when django_altcha is installed."""
        choices_values = [choice[0] for choice in recaptcha.CAPTCHA_CHOICES]
        self.assertIn("altcha", choices_values)

    def test_get_recaptcha_field_returns_altcha_field_when_altcha_selected(self):
        """get_recaptcha_field returns an AltchaField when captcha_widget is 'altcha'."""
        from django_altcha import AltchaField

        instance = type(
            "MockInstance", (), {"captcha_widget": "altcha", "captcha_config": {}}
        )()
        field = recaptcha.get_recaptcha_field(instance)
        self.assertIsInstance(field, AltchaField)


class FormSubmissionRenderingTestCase(TestFixture, CMSTestCase):
    """Tests for form rendering during submission and validation"""

    @skipIf(cms_version < "4", "Form rendering tests require django CMS 4 or higher")
    def test_form_validation_error_rendering(self):
        """Test that validation errors render properly"""
        form_plugin = add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.FormPlugin.__name__,
            language=self.language,
            form_selection="",
            form_name="validation-test",
        )

        email_field = add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.EmailFieldPlugin.__name__,
            target=form_plugin,
            language=self.language,
            config={
                "field_name": "email",
                "field_label": "Email",
                "field_required": True,
            },
        )
        email_field.initialize_from_form()

        self.publish(self.page, self.language)

        with self.login_user_context(self.superuser):
            # Submit invalid data
            response = self.client.post(
                f"/@form-builder/{form_plugin.id}",
                data={"email": "invalid-email"},
                headers={"accept": "application/json"},
            )

        self.assertEqual(response.status_code, 200)
        json_data = response.json()

        # Check error response structure
        self.assertIn("result", json_data)
        self.assertEqual(json_data["result"], "invalid form")
        self.assertIn("field_errors", json_data)

    def test_form_csrf_token_not_rendered(self):
        """CSRF token must not be rendered inside the form so the HTML stays cacheable.

        The token is read from the csrftoken cookie by ajax_form.js and sent as the
        X-CSRFToken header instead.
        """
        form_plugin = add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.FormPlugin.__name__,
            language=self.language,
            form_selection="",
            form_name="csrf-test",
        )

        # Add at least one field so form renders
        char_field = add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.CharFieldPlugin.__name__,
            target=form_plugin,
            language=self.language,
            config={
                "field_name": "test_field",
                "field_label": "Test",
            },
        )
        char_field.initialize_from_form()

        self.publish(self.page, self.language)

        with self.login_user_context(self.superuser):
            response = self.client.get(self.request_url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        # CSRF token must NOT be present in the rendered form (cacheable HTML)
        self.assertNotIn('name="csrfmiddlewaretoken"', content)
