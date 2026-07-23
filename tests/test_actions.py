from unittest.mock import Mock, patch

from cms.api import add_plugin
from cms.test_utils.testcases import CMSTestCase
from django.apps import apps
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.files.uploadedfile import SimpleUploadedFile

from djangocms_form_builder.actions import SaveToDBAction, get_registered_actions
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

    def _unique_upload_form(self, cleaned_data):
        class UniqueUploadForm:
            class Meta:
                options = {
                    "unique": True,
                    "login_required": True,
                    "form_name": "unique-upload",
                }

        form = UniqueUploadForm()
        form.cleaned_data = cleaned_data
        return form

    def _authenticated_upload_request(self):
        request = self.get_request("/")
        request.user = self.superuser
        request.META["HTTP_USER_AGENT"] = "test-agent"
        request.META["HTTP_REFERER"] = "/form/"
        return request

    @patch("djangocms_form_builder.form_entry_data.FILE_FIELD_STORAGE")
    def test_unique_submission_preserves_upload_without_replacement(self, storage):
        metadata = {
            "_form_builder_file": True,
            "filename": "old.pdf",
            "name": "form_uploads/old.pdf",
            "url": "/media/form_uploads/old.pdf",
        }
        entry = FormEntry.objects.create(
            form_name="unique-upload",
            form_user=self.superuser,
            entry_data={"attachment": metadata},
        )

        SaveToDBAction().execute(
            self._unique_upload_form({"attachment": None}),
            self._authenticated_upload_request(),
        )

        entry.refresh_from_db()
        self.assertEqual(entry.entry_data["attachment"], metadata)
        storage.delete.assert_not_called()

    @patch("djangocms_form_builder.form_entry_data.FILE_FIELD_STORAGE")
    def test_unique_submission_deletes_replaced_upload(self, storage):
        old_metadata = {
            "_form_builder_file": True,
            "filename": "old.pdf",
            "name": "form_uploads/old.pdf",
            "url": "/media/form_uploads/old.pdf",
        }
        entry = FormEntry.objects.create(
            form_name="unique-upload",
            form_user=self.superuser,
            entry_data={"attachment": old_metadata},
        )
        storage.save.return_value = "form_uploads/new.pdf"
        storage.url.return_value = "/media/form_uploads/new.pdf"
        uploaded = SimpleUploadedFile("new.pdf", b"new")

        SaveToDBAction().execute(
            self._unique_upload_form({"attachment": uploaded}),
            self._authenticated_upload_request(),
        )

        entry.refresh_from_db()
        self.assertEqual(entry.entry_data["attachment"]["name"], "form_uploads/new.pdf")
        storage.delete.assert_called_once_with("form_uploads/old.pdf")

    @patch("djangocms_form_builder.actions.delete_stored_files")
    @patch("djangocms_form_builder.actions.serialize_cleaned_data_for_entry")
    def test_create_failure_cleans_up_new_uploads(self, serialize, delete_files):
        serialized = {"attachment": {"name": "form_uploads/new.pdf"}}
        serialize.return_value = serialized
        form = self._unique_upload_form({"attachment": object()})
        form.Meta.options["unique"] = False

        with patch.object(FormEntry.objects, "create", side_effect=OSError("db down")):
            with self.assertRaisesMessage(OSError, "db down"):
                SaveToDBAction().execute(
                    form,
                    self._authenticated_upload_request(),
                )

        delete_files.assert_called_once_with(serialized)

    @patch("djangocms_form_builder.actions.delete_stored_files")
    @patch("djangocms_form_builder.actions.serialize_cleaned_data_for_entry")
    def test_update_failure_preserves_previous_upload_during_cleanup(
        self, serialize, delete_files
    ):
        old_metadata = {
            "_form_builder_file": True,
            "filename": "old.pdf",
            "name": "form_uploads/old.pdf",
            "url": "/media/form_uploads/old.pdf",
        }
        FormEntry.objects.create(
            form_name="unique-upload",
            form_user=self.superuser,
            entry_data={"attachment": old_metadata},
        )
        serialized = {
            "attachment": {
                "_form_builder_file": True,
                "filename": "new.pdf",
                "name": "form_uploads/new.pdf",
                "url": "/media/form_uploads/new.pdf",
            }
        }
        serialize.return_value = serialized

        with patch.object(
            FormEntry.objects, "update_or_create", side_effect=OSError("db down")
        ):
            with self.assertRaisesMessage(OSError, "db down"):
                SaveToDBAction().execute(
                    self._unique_upload_form({"attachment": object()}),
                    self._authenticated_upload_request(),
                )

        delete_files.assert_called_once_with(
            serialized, excluding={"form_uploads/old.pdf"}
        )

    @patch("djangocms_form_builder.actions.delete_stored_files")
    @patch("djangocms_form_builder.actions.serialize_cleaned_data_for_entry")
    def test_duplicate_recovery_failure_cleans_up_new_uploads(
        self, serialize, delete_files
    ):
        FormEntry.objects.create(
            form_name="unique-upload",
            form_user=self.superuser,
            entry_data={"value": "first"},
        )
        FormEntry.objects.create(
            form_name="unique-upload",
            form_user=self.superuser,
            entry_data={"value": "second"},
        )
        existing_entries = FormEntry.objects.filter(
            form_name="unique-upload", form_user=self.superuser
        )
        cleanup_queryset = Mock()
        serialized = {"attachment": {"name": "form_uploads/new.pdf"}}
        serialize.return_value = serialized

        with (
            patch.object(
                FormEntry.objects,
                "update_or_create",
                side_effect=FormEntry.MultipleObjectsReturned,
            ),
            patch.object(FormEntry.objects, "create", side_effect=OSError("db down")),
            patch.object(
                FormEntry.objects,
                "filter",
                side_effect=[existing_entries, cleanup_queryset],
            ),
        ):
            with self.assertRaisesMessage(OSError, "db down"):
                SaveToDBAction().execute(
                    self._unique_upload_form({"attachment": object()}),
                    self._authenticated_upload_request(),
                )

        cleanup_queryset.delete.assert_called_once()
        delete_files.assert_called_once_with(serialized)

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
        # An anonymous submitter is rendered as "by anonymous", not an empty
        # user line (request.user is an AnonymousUser, which is truthy).
        self.assertIn("anonymous", args[1])

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

    def test_send_mail_action_logs_failures(self):
        plugin_instance = add_plugin(
            placeholder=self.placeholder,
            plugin_type="FormPlugin",
            language=self.language,
            form_name="test_form",
        )
        plugin_instance.action_parameters = {
            "sendemail_recipients": "a@b.c",
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

        with patch("django.core.mail.send_mail", side_effect=Exception("SMTP down")):
            form = plugin.get_form_class()({}, request=self.get_request("/"))
            form.cleaned_data = {"field1": "value1"}
            # The submission must not raise, but the failure must be logged
            with self.assertLogs("djangocms_form_builder.actions", level="ERROR"):
                form.save()

    def test_send_mail_action_authenticated_user(self):
        user = get_user_model().objects.create_user(
            username="johndoe",
            first_name="John",
            last_name="Doe",
        )

        plugin_instance = add_plugin(
            placeholder=self.placeholder,
            plugin_type="FormPlugin",
            language=self.language,
            form_name="test_form",
        )
        plugin_instance.action_parameters = {
            "sendemail_recipients": "a@b.c",
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

        request = self.get_request("/")
        request.user = user

        with patch("django.core.mail.send_mail") as mock_send_mail:
            form = plugin.get_form_class()({}, request=request)
            form.cleaned_data = {"field1": "value1"}
            form.save()

        mock_send_mail.assert_called_once()
        args, kwargs = mock_send_mail.call_args
        # Authenticated submitter is named using the correct User model fields
        # (first_name/last_name, not firstname/lastname).
        self.assertIn("John Doe (johndoe)", kwargs["html_message"])
        self.assertIn("John Doe (johndoe)", args[1])
        self.assertNotIn("anonymous", args[1])

    def test_save_to_db_action_creates_entry(self):
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
        # Request headers (User-Agent, Referer) are deliberately not stored
        self.assertEqual(entry.html_headers, {})

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
