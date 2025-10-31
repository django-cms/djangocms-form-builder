from unittest.mock import patch

from cms.api import add_plugin
from cms.test_utils.testcases import CMSTestCase
from django.apps import apps
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import AnonymousUser

from djangocms_form_builder.actions import get_registered_actions
from djangocms_form_builder.cms_plugins.ajax_plugins import FormPlugin
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
        self.assertEqual(form.Meta.options.get("redirect"), "/home/")

    def test_actions_appear_in_form_plugin_fieldsets(self):
        """Test that registered actions appear in FormPlugin admin fieldsets"""
        # Create FormPlugin instance
        admin_site = AdminSite()
        form_plugin = FormPlugin(model=FormPlugin.model, admin_site=admin_site)

        # Get fieldsets for a new form (obj=None means no existing form selected)
        request = self.get_request("/")
        fieldsets = form_plugin.get_fieldsets(request, obj=None)

        # Convert fieldsets to a flat list of (block_name, fields) for easier inspection
        fieldset_info = [(name, data.get("fields", [])) for name, data in fieldsets]

        # Check that form_actions field appears (added by FormPlugin.get_fieldsets)
        all_fields = [field for _, fields in fieldset_info for field in fields]
        flat_fields = []
        for field in all_fields:
            if isinstance(field, (list, tuple)):
                flat_fields.extend(field)
            else:
                flat_fields.append(field)

        self.assertIn(
            "form_actions", flat_fields, "form_actions field should appear in fieldsets"
        )

        # Check that action-specific fieldsets are added by ActionMixin.get_fieldsets
        # Each registered action with declared_fields should have its own fieldset
        action_names = [verbose for _, verbose in get_registered_actions()]
        fieldset_names = [name for name, _ in fieldset_info if name]

        # At least some action names should appear as fieldset names
        # (Actions like SendMailAction have fields like sendemail_recipients)
        has_action_fieldsets = any(
            action_name in fieldset_names for action_name in action_names
        )
        self.assertTrue(
            has_action_fieldsets,
            f"Expected at least one action fieldset. Actions: {action_names}, Fieldsets: {fieldset_names}",
        )

    def test_actions_fieldsets_include_action_fields(self):
        """Test that action fieldsets include the action's declared fields"""
        admin_site = AdminSite()
        form_plugin = FormPlugin(model=FormPlugin.model, admin_site=admin_site)

        request = self.get_request("/")
        fieldsets = form_plugin.get_fieldsets(request, obj=None)

        # Look for SendMailAction fieldset and its fields
        send_mail_fieldset = None
        for name, data in fieldsets:
            if name and "email" in str(name).lower():
                send_mail_fieldset = data
                break

        if send_mail_fieldset:
            # SendMailAction should have sendemail_recipients and sendemail_template
            all_fields = []
            for field in send_mail_fieldset.get("fields", []):
                if isinstance(field, (list, tuple)):
                    all_fields.extend(field)
                else:
                    all_fields.append(field)

            # Check for SendMailAction specific fields
            self.assertTrue(
                any("sendemail" in str(f) for f in all_fields),
                "SendMailAction fields should be in its fieldset",
            )

    def test_actions_fieldsets_have_action_hide_class(self):
        """Test that action fieldsets have action-related CSS classes"""
        admin_site = AdminSite()
        form_plugin = FormPlugin(model=FormPlugin.model, admin_site=admin_site)

        request = self.get_request("/")
        fieldsets = form_plugin.get_fieldsets(request, obj=None)

        # Check that action fieldsets have appropriate CSS classes
        action_fieldsets_found = False
        for name, data in fieldsets:
            if name and name != "None":
                classes = data.get("classes", ())
                # Action fieldsets should have "action-hide" or "action-auto-hide" class
                if any("action" in str(cls) for cls in classes):
                    action_fieldsets_found = True
                    self.assertTrue(
                        "action-hide" in classes or "action-auto-hide" in classes,
                        f"Fieldset '{name}' should have action-hide or action-auto-hide class, got {classes}",
                    )

        # At least one action fieldset should be found
        self.assertTrue(
            action_fieldsets_found,
            "Should find at least one action fieldset with classes",
        )
