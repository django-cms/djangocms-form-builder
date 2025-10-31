from unittest.mock import patch

from cms.api import add_plugin
from cms.test_utils.testcases import CMSTestCase
from django.apps import apps
from django.contrib.auth.models import AnonymousUser

from djangocms_form_builder.actions import get_registered_actions
from djangocms_form_builder.entry_model import FormEntry

from .fixtures import TestFixture


class ActionTestCase(TestFixture, CMSTestCase):
    def setUp(self):
        super().setUp()
        self.actions = get_registered_actions()
        self.save_action = [
            key for key, value in self.actions if value == "Save form submission"
        ][0]
        self.send_mail_action = [
            key for key, value in self.actions if value == "Send email"
        ][0]
        self.success_action = [
            key for key, value in self.actions if value == "Success message"
        ][0]
        self.redirect_action = next(
            (
                key
                for key, value in self.actions
                if value == "Redirect after submission"
            ),
            None,
        )

    def test_send_mail_action(self):
        plugin_instance = add_plugin(
            placeholder=self.placeholder,
            plugin_type="FormPlugin",
            language=self.language,
            form_name="test_form",
        )
        plugin_instance.action_parameters = {
            "sendemail_recipients": "a@b.c d@e.f",
            "sendemail_template": "default",
        }
        plugin_instance.form_actions = f'["{self.send_mail_action}"]'
        plugin_instance.save()

        child_plugin = add_plugin(
            placeholder=self.placeholder,
            plugin_type="CharFieldPlugin",
            language=self.language,
            target=plugin_instance,
            config={"field_name": "field1"},
        )
        child_plugin.save()
        plugin_instance.child_plugin_instances = [child_plugin]
        child_plugin.child_plugin_instances = []

        plugin = plugin_instance.get_plugin_class_instance()
        plugin.instance = plugin_instance

        # Simulate form submission
        with patch("django.core.mail.send_mail") as mock_send_mail:
            form = plugin.get_form_class()({}, request=self.get_request("/"))
            form.cleaned_data = {"field1": "value1", "field2": "value2"}
            form.save()

        # Validate send_mail call
        mock_send_mail.assert_called_once()
        args, kwargs = mock_send_mail.call_args
        self.assertEqual(args[0], "Test form form submission")
        self.assertIn("Form submission", args[1])
        self.assertEqual(args[3], ["a@b.c", "d@e.f"])

        # Test with no recipients
        plugin_instance.action_parameters = {
            "sendemail_recipients": "",
            "sendemail_template": "default",
        }
        plugin_instance.save()

        with patch("django.core.mail.mail_admins") as mock_mail_admins:
            form = plugin.get_form_class()({}, request=self.get_request("/"))
            form.cleaned_data = {"field1": "value1", "field2": "value2"}
            form.save()

        # Validate mail_admins call
        mock_mail_admins.assert_called_once()
        args, kwargs = mock_mail_admins.call_args
        self.assertEqual(args[0], "Test form form submission")
        self.assertIn("Form submission", args[1])

    def test_save_to_db_action_creates_entry_with_headers(self):
        plugin_instance = add_plugin(
            placeholder=self.placeholder,
            plugin_type="FormPlugin",
            language=self.language,
            form_name="save_form",
        )
        plugin_instance.form_actions = f'["{self.save_action}"]'
        plugin_instance.save()

        plugin = plugin_instance.get_plugin_class_instance()
        plugin.instance = plugin_instance

        # Prepare request with headers and anonymous user
        request = self.get_request("/")
        request.META["HTTP_USER_AGENT"] = "pytest-agent"
        request.META["HTTP_REFERER"] = "/from"
        request.user = AnonymousUser()

        # ensure at least one field exists to build the form
        child_plugin = add_plugin(
            placeholder=self.placeholder,
            plugin_type="CharFieldPlugin",
            language=self.language,
            target=plugin_instance,
            config={"field_name": "field1"},
        )
        child_plugin.save()

        initial = FormEntry.objects.count()
        form = plugin.get_form_class()({}, request=request)
        form.cleaned_data = {"field1": "value1"}
        form.save()

        self.assertEqual(FormEntry.objects.count(), initial + 1)
        entry = FormEntry.objects.latest("entry_created_at")
        self.assertEqual(entry.form_name, "save_form")
        self.assertEqual(entry.form_user, None)
        self.assertEqual(entry.entry_data.get("field1"), "value1")
        self.assertEqual(entry.html_headers.get("user_agent"), "pytest-agent")
        self.assertEqual(entry.html_headers.get("referer"), "/from")

    def test_save_to_db_action_unique_updates_single_entry(self):
        plugin_instance = add_plugin(
            placeholder=self.placeholder,
            plugin_type="FormPlugin",
            language=self.language,
            form_name="unique_form",
            form_login_required=True,
            form_unique=True,
        )
        plugin_instance.form_actions = f'["{self.save_action}"]'
        plugin_instance.save()

        plugin = plugin_instance.get_plugin_class_instance()
        plugin.instance = plugin_instance

        request = self.get_request("/")
        request.META["HTTP_USER_AGENT"] = "pytest-agent"
        request.META["HTTP_REFERER"] = "/from"
        request.user = self.superuser
        # provide a simple field
        child_plugin = add_plugin(
            placeholder=self.placeholder,
            plugin_type="CharFieldPlugin",
            language=self.language,
            target=plugin_instance,
            config={"field_name": "x"},
        )
        child_plugin.save()

        form = plugin.get_form_class()({}, request=request)
        form.cleaned_data = {"x": 1}
        form.save()

        # Second save should update, not create new
        form = plugin.get_form_class()({}, request=request)
        form.cleaned_data = {"x": 2}
        form.save()

        entries = FormEntry.objects.filter(
            form_name="unique_form", form_user=self.superuser
        )
        self.assertEqual(entries.count(), 1)
        self.assertEqual(entries.first().entry_data.get("x"), 2)

    def test_success_message_action_sets_render_success_and_redirect(self):
        plugin_instance = add_plugin(
            placeholder=self.placeholder,
            plugin_type="FormPlugin",
            language=self.language,
            form_name="success_form",
        )
        plugin_instance.form_actions = f'["{self.success_action}"]'
        plugin_instance.action_parameters = {
            "submitmessage_message": "<p>Thanks!</p>",
        }
        plugin_instance.save()

        plugin = plugin_instance.get_plugin_class_instance()
        plugin.instance = plugin_instance

        request = self.get_request("/")
        # ensure headers exist though not required here
        request.META["HTTP_USER_AGENT"] = "pytest-agent"
        request.META["HTTP_REFERER"] = "/from"

        # add a trivial field
        child_plugin = add_plugin(
            placeholder=self.placeholder,
            plugin_type="CharFieldPlugin",
            language=self.language,
            target=plugin_instance,
            config={"field_name": "unused"},
        )
        child_plugin.save()

        form = plugin.get_form_class()({}, request=request)
        form.cleaned_data = {}
        # Before action, default redirect is SAME_PAGE_REDIRECT and no render_success
        self.assertIsNone(form.Meta.options.get("render_success"))
        self.assertEqual(form.Meta.options.get("redirect"), "result")

        form.save()

        # After SuccessMessageAction, render_success should be set and redirect cleared
        self.assertEqual(
            form.Meta.options.get("render_success"),
            "djangocms_form_builder/actions/submit_message.html",
        )
        self.assertIsNone(form.Meta.options.get("redirect"))

    def test_redirect_action_sets_redirect_url(self):
        if not apps.is_installed("djangocms_link") or self.redirect_action is None:
            self.skipTest("djangocms_link not installed; redirect action not available")

        from djangocms_link.helpers import LinkDict

        plugin_instance = add_plugin(
            placeholder=self.placeholder,
            plugin_type="FormPlugin",
            language=self.language,
            form_name="redirect_form",
        )
        plugin_instance.form_actions = f'["{self.redirect_action}"]'
        plugin_instance.action_parameters = {"redirect_link": LinkDict(self.home)}
        plugin_instance.save()

        plugin = plugin_instance.get_plugin_class_instance()
        plugin.instance = plugin_instance

        request = self.get_request("/")
        # add a trivial field
        child_plugin = add_plugin(
            placeholder=self.placeholder,
            plugin_type="CharFieldPlugin",
            language=self.language,
            target=plugin_instance,
            config={"field_name": "unused"},
        )
        child_plugin.save()

        form = plugin.get_form_class()({}, request=request)
        form.cleaned_data = {}
        form.save()

        self.assertTrue(form.Meta.options.get("redirect"))
