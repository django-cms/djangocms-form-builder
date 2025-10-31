from unittest.mock import patch

from cms.api import add_plugin
from cms.test_utils.testcases import CMSTestCase

from djangocms_form_builder.actions import get_registered_actions

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
