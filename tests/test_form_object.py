"""The frontend-editable form object and the plugin showing it."""

import json

from cms.api import add_plugin
from cms.models import CMSPlugin
from cms.test_utils.testcases import CMSTestCase
from cms.toolbar.utils import get_object_edit_url, get_object_preview_url
from cms.utils.urlutils import admin_reverse

from djangocms_form_builder import actions, cms_plugins
from djangocms_form_builder.constants import (
    CHANGE_FORM_URL_NAME,
    CONVERT_TO_FORM_URL_NAME,
    LIST_FORM_URL_NAME,
    SETTINGS_FORM_URL_NAME,
    USAGE_FORM_URL_NAME,
)
from djangocms_form_builder.form_model import Form, FormContent
from djangocms_form_builder.models import FormPlugin

from .fixtures import VERSIONING, TestFixture


class FormObjectTestCase(TestFixture, CMSTestCase):
    def setUp(self):
        super().setUp()
        self.form, self.form_content = self.create_form(
            form_name="contact",
            name="Contact form",
            form_actions=json.dumps([actions.SAVE_TO_DB_ACTION]),
        )

    def add_field(self, plugin_type="CharFieldPlugin", language=None, **config):
        config.setdefault("field_name", "name")
        config.setdefault("field_label", "Name")
        plugin = add_plugin(
            placeholder=self.form_content.placeholder,
            plugin_type=plugin_type,
            language=language or self.language,
            config=config,
        )
        plugin.initialize_from_form()
        plugin.save()
        return plugin

    def test_a_form_has_no_language_of_its_own(self):
        """One form, one identifier, one set of settings - in every language."""
        self.assertNotIn(
            "language", {field.name for field in FormContent._meta.get_fields()}
        )
        self.assertFalse(hasattr(self.form_content, "language"))

    def test_form_name_comes_from_the_grouper(self):
        """Submissions stay filed under one name across content versions."""
        self.assertEqual(self.form_content.form_name, "contact")

    def test_get_form_class_builds_fields_from_plugins(self):
        self.add_field(field_name="username", field_label="User name")
        self.add_field(plugin_type="EmailFieldPlugin", field_name="email")

        form_class = self.form_content.get_form_class()

        self.assertIn("username", form_class.base_fields)
        self.assertIn("email", form_class.base_fields)
        self.assertEqual(form_class.Meta.options["form_name"], "contact")
        self.assertEqual(
            form_class.Meta.options["form_actions"], [actions.SAVE_TO_DB_ACTION]
        )

    def test_plugin_renders_the_form_object(self):
        self.add_field(field_name="username", field_label="User name")
        self.publish(self.form)

        add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.FormPlugin.__name__,
            language=self.language,
            form=self.form,
        )
        self.publish(self.page, self.language)

        with self.login_user_context(self.superuser):
            response = self.client.get(self.request_url)

        self.assertContains(response, "User name")
        self.assertContains(response, 'name="username"')

    def test_fields_are_taken_from_the_plugins_of_the_current_language(self):
        """A form is built per language inside the one form object."""
        self.add_field(field_name="username", field_label="User name")
        self.add_field(
            language="de", field_name="benutzername", field_label="Benutzername"
        )
        self.publish(self.form)

        self.assertEqual(
            set(self.form_content.get_form_class(language="en").base_fields),
            {"username"},
        )
        self.assertEqual(
            set(self.form_content.get_form_class(language="de").base_fields),
            {"benutzername"},
        )

    def test_plugin_without_form_object_renders_nothing(self):
        plugin = add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.FormPlugin.__name__,
            language=self.language,
        )
        plugin_class = plugin.get_plugin_class_instance()
        plugin_class.instance = plugin
        plugin_class.request = self.get_request("/")

        self.assertIsNone(plugin_class.get_form_class())

    def test_form_editor_renders_the_form(self):
        self.add_field(field_name="username", field_label="User name")

        with self.login_user_context(self.superuser):
            response = self.client.get(get_object_edit_url(self.form_content))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Contact form")
        self.assertContains(response, 'name="username"')

    def test_form_editor_preview_renders_the_form(self):
        self.add_field(field_name="username", field_label="User name")

        with self.login_user_context(self.superuser):
            response = self.client.get(get_object_preview_url(self.form_content))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="username"')

    def test_edit_url_carries_the_language_being_edited(self):
        self.assertIn("language=de", get_object_edit_url(self.form_content, "de"))

    def test_form_in_use_is_reported(self):
        self.assertFalse(Form.objects.get(pk=self.form.pk).is_in_use)

        add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.FormPlugin.__name__,
            language=self.language,
            form=self.form,
        )

        self.assertTrue(Form.objects.get(pk=self.form.pk).is_in_use)

    def test_objects_using_lists_the_page(self):
        add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.FormPlugin.__name__,
            language=self.language,
            form=self.form,
        )
        self.assertIn(self.page, Form.objects.get(pk=self.form.pk).objects_using)

    def test_form_plugin_takes_no_children(self):
        """Fields are added to a form object, not below the plugin."""
        self.assertEqual(
            cms_plugins.FormPlugin.get_child_classes(
                slot="content", page=self.page, instance=None
            ),
            [],
        )

    def test_field_plugins_are_offered_inside_a_form_only(self):
        char_field = cms_plugins.CharFieldPlugin

        # Inside a form: no parent required, so it can sit at the root.
        self.assertFalse(
            char_field.requires_parent_plugin("form", self.form_content),
        )
        # Anywhere else: not offered at all.
        self.assertEqual(
            char_field.get_parent_classes("content", self.page, None), [""]
        )

    def test_form_plugin_is_not_allowed_inside_a_form(self):
        self.assertEqual(
            cms_plugins.FormPlugin.get_parent_classes("form", self.form_content, None),
            [""],
        )


class FormObjectSubmissionTestCase(TestFixture, CMSTestCase):
    """Submitting a form defined by a form object."""

    def setUp(self):
        super().setUp()
        self.form, self.form_content = self.create_form(
            form_name="contact",
            name="Contact form",
            form_actions=json.dumps([actions.SAVE_TO_DB_ACTION]),
        )
        plugin = add_plugin(
            placeholder=self.form_content.placeholder,
            plugin_type="CharFieldPlugin",
            language=self.language,
            config={"field_name": "username", "field_label": "User name"},
        )
        plugin.initialize_from_form()
        plugin.save()
        self.publish(self.form)

        self.plugin = add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.FormPlugin.__name__,
            language=self.language,
            form=self.form,
        )
        self.publish(self.page, self.language)

    def test_the_rendered_form_names_the_language_it_was_built_from(self):
        """The submission endpoint is not language-prefixed - see form.html."""
        with self.login_user_context(self.superuser):
            response = self.client.get(self.request_url)
        self.assertContains(
            response, f"/@form-builder/{self.plugin.pk}?language={self.language}"
        )

    def test_submission_is_saved_under_the_form_name(self):
        from djangocms_form_builder.models import FormEntry

        response = self.client.post(
            f"/@form-builder/{self.plugin.pk}?language={self.language}",
            data={"username": "Alice"},
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        entry = FormEntry.objects.get()
        self.assertEqual(entry.form_name, "contact")
        self.assertEqual(entry.entry_data["username"], "Alice")

    if VERSIONING:

        def test_visitors_submit_against_the_published_form(self):
            """A draft change must not alter what visitors can submit."""
            from djangocms_versioning.models import Version

            published = Version.objects.filter_by_grouper(self.form).first()
            draft = published.copy(self.superuser)
            new_field = add_plugin(
                placeholder=draft.content.placeholder,
                plugin_type="CharFieldPlugin",
                language=self.language,
                config={"field_name": "nickname", "field_label": "Nickname"},
            )
            new_field.initialize_from_form()
            new_field.save()

            plugin_class = self.plugin.get_plugin_class_instance()
            plugin_class.instance = FormPlugin.objects.get(pk=self.plugin.pk)
            plugin_class.request = self.get_request("/")

            form_class = plugin_class.get_form_class()
            self.assertIn("username", form_class.base_fields)
            self.assertNotIn("nickname", form_class.base_fields)


class ConvertToFormTestCase(TestFixture, CMSTestCase):
    """Turning a plugin that carries its fields as children into a form."""

    def setUp(self):
        super().setUp()
        # Plugins are converted while editing, so work on an unpublished page:
        # a published page content is read-only.
        self.draft_page = self.create_page(title="draft", template="page.html")
        self.draft_placeholder = self.get_draft_placeholders(self.draft_page).get(
            slot="content"
        )
        self.plugin = add_plugin(
            placeholder=self.draft_placeholder,
            plugin_type=cms_plugins.FormPlugin.__name__,
            language=self.language,
            form_name="legacy-form",
            form_actions=json.dumps([actions.SAVE_TO_DB_ACTION]),
            form_floating_labels=True,
        )
        for field_name, label in (("username", "User name"), ("email", "Email")):
            child = add_plugin(
                placeholder=self.draft_placeholder,
                plugin_type="CharFieldPlugin",
                target=self.plugin,
                language=self.language,
                config={"field_name": field_name, "field_label": label},
            )
            child.initialize_from_form()
            child.save()
        self.url = admin_reverse(CONVERT_TO_FORM_URL_NAME, args=[self.plugin.pk])

    def tearDown(self):
        self.draft_page.delete()
        return super().tearDown()

    def draft_page_url(self):
        """The public url of the page - only resolvable once published."""
        return self.draft_page.get_absolute_url(self.language) + "?toolbar_off=true"

    def test_legacy_plugin_still_renders_its_children(self):
        self.publish(self.draft_page, self.language)
        with self.login_user_context(self.superuser):
            response = self.client.get(self.draft_page_url())
        self.assertContains(response, 'name="username"')

    def test_menu_item_offered_for_legacy_plugin_only(self):
        request = self.get_request("/")
        request.user = self.superuser

        items = cms_plugins.FormPlugin.get_extra_plugin_menu_items(
            request, CMSPlugin.objects.get(pk=self.plugin.pk)
        )
        self.assertEqual([item.name for item in items], ["Convert to form"])

        plain = add_plugin(
            placeholder=self.draft_placeholder,
            plugin_type=cms_plugins.FormPlugin.__name__,
            language=self.language,
        )
        self.assertEqual(
            cms_plugins.FormPlugin.get_extra_plugin_menu_items(
                request, CMSPlugin.objects.get(pk=plain.pk)
            ),
            [],
        )

    def test_convert_view_shows_a_prefilled_form(self):
        with self.login_user_context(self.superuser):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "legacy-form")

    def test_conversion_moves_the_fields_into_a_form_object(self):
        with self.login_user_context(self.superuser):
            response = self.client.post(
                self.url, data={"name": "Legacy form", "form_name": "legacy-form"}
            )
        self.assertEqual(response.status_code, 200)

        form = Form.objects.get(form_name="legacy-form")
        self.assertEqual(form.creation_method, Form.CREATION_BY_CONVERSION)

        content = form.get_content(show_draft_content=True)
        self.assertEqual(content.name, "Legacy form")
        # Settings moved along, so the form behaves exactly as before.
        self.assertTrue(content.form_floating_labels)
        self.assertEqual(content.form_actions, json.dumps([actions.SAVE_TO_DB_ACTION]))

        field_names = set(content.get_form_class().base_fields)
        self.assertEqual(field_names, {"username", "email"})

        plugin = FormPlugin.objects.get(pk=self.plugin.pk)
        self.assertEqual(plugin.form_id, form.pk)
        self.assertEqual(plugin.get_children().count(), 0)

    def test_converted_form_still_renders_on_the_page(self):
        with self.login_user_context(self.superuser):
            self.client.post(
                self.url, data={"name": "Legacy form", "form_name": "legacy-form"}
            )
        self.publish(self.draft_page, self.language)

        with self.login_user_context(self.superuser):
            response = self.client.get(self.draft_page_url())

        self.assertContains(response, 'name="username"')
        self.assertContains(response, "User name")

    def test_duplicate_identifier_is_rejected(self):
        Form.objects.create(form_name="taken")
        with self.login_user_context(self.superuser):
            response = self.client.post(
                self.url, data={"name": "Legacy form", "form_name": "taken"}
            )
        self.assertContains(response, "already exists")
        self.assertEqual(FormPlugin.objects.get(pk=self.plugin.pk).form_id, None)

    def test_conversion_requires_permission(self):
        staff = self.get_staff_user_with_no_permissions()
        with self.login_user_context(staff):
            response = self.client.post(
                self.url, data={"name": "Legacy form", "form_name": "legacy-form"}
            )
        self.assertEqual(response.status_code, 403)


class FormAdminTestCase(TestFixture, CMSTestCase):
    """Managing forms through the admin."""

    def setUp(self):
        super().setUp()
        self.form, self.form_content = self.create_form(
            form_name="contact", name="Contact form"
        )

    def test_form_list_shows_the_form(self):
        with self.login_user_context(self.superuser):
            response = self.client.get(admin_reverse(LIST_FORM_URL_NAME))
        self.assertContains(response, "Contact form")
        self.assertContains(response, "contact")

    def test_form_content_is_not_listed_on_its_own(self):
        """A form content only makes sense as part of its form."""
        with self.login_user_context(self.superuser):
            response = self.client.get(
                admin_reverse("djangocms_form_builder_formcontent_changelist")
            )
        self.assertRedirects(
            response, admin_reverse(LIST_FORM_URL_NAME), fetch_redirect_response=False
        )

    def test_settings_can_be_saved(self):
        url = admin_reverse(SETTINGS_FORM_URL_NAME, args=[self.form_content.pk])
        with self.login_user_context(self.superuser):
            # Start from what the change form actually offers, so the post
            # carries the same defaults a browser would submit.
            form = self.client.get(url).context_data["adminform"].form
            data = {
                name: field.field.initial or ""
                for name, field in zip(form.fields, form)
            }
            data.update(
                {
                    "name": "Contact form",
                    "form_actions": [actions.SAVE_TO_DB_ACTION],
                    "form_login_required": "on",
                    "form_unique": "on",
                }
            )
            response = self.client.post(url, data=data)

        self.assertIn(response.status_code, (200, 302))
        if response.status_code == 200:
            self.assertFalse(
                response.context_data["adminform"].form.errors,
                response.context_data["adminform"].form.errors.as_text(),
            )

        content = FormContent.admin_manager.get(pk=self.form_content.pk)
        self.assertEqual(
            content.get_form_class().Meta.options["form_actions"],
            [actions.SAVE_TO_DB_ACTION],
        )
        self.assertTrue(content.form_login_required)
        self.assertTrue(content.form_unique)

    def test_usage_view_lists_pages_showing_the_form(self):
        add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.FormPlugin.__name__,
            language=self.language,
            form=self.form,
        )
        with self.login_user_context(self.superuser):
            response = self.client.get(
                admin_reverse(USAGE_FORM_URL_NAME, args=[self.form.pk])
            )
        self.assertContains(response, str(self.page))

    def test_form_in_use_cannot_be_deleted(self):
        from django.contrib.admin.sites import AdminSite

        from djangocms_form_builder.admin import FormAdmin

        form_admin = FormAdmin(Form, AdminSite())
        request = self.get_request("/")
        request.user = self.superuser

        self.assertTrue(form_admin.has_delete_permission(request, self.form))

        add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.FormPlugin.__name__,
            language=self.language,
            form=self.form,
        )
        self.assertFalse(
            form_admin.has_delete_permission(request, Form.objects.get(pk=self.form.pk))
        )

    def test_a_form_can_be_created_in_the_admin(self):
        url = admin_reverse("djangocms_form_builder_form_add")
        with self.login_user_context(self.superuser):
            response = self.client.post(
                url, data={"form_name": "newsletter", "content__name": "Newsletter"}
            )
        if response.status_code == 200:
            self.fail(
                response.context_data["adminform"].form.errors.as_text()
                or "Add form did not save"
            )

        form = Form.objects.get(form_name="newsletter")
        content = form.get_content(show_draft_content=True)
        self.assertIsNotNone(content, "A new form must come with a content object")
        self.assertEqual(content.name, "Newsletter")

    def test_renaming_a_form_keeps_its_settings(self):
        """The form list edits identity only - behaviour lives in the settings."""
        self.form_content.form_actions = json.dumps([actions.SAVE_TO_DB_ACTION])
        self.form_content.form_login_required = True
        self.form_content.save()

        url = admin_reverse(CHANGE_FORM_URL_NAME, args=[self.form.pk])
        with self.login_user_context(self.superuser):
            response = self.client.post(
                url, data={"form_name": "contact", "content__name": "Renamed"}
            )
        if response.status_code == 200:
            self.fail(
                response.context_data["adminform"].form.errors.as_text()
                or "Change form did not save"
            )

        content = FormContent.admin_manager.get(pk=self.form_content.pk)
        self.assertEqual(content.name, "Renamed")
        self.assertEqual(
            content.get_form_class().Meta.options["form_actions"],
            [actions.SAVE_TO_DB_ACTION],
        )
        self.assertTrue(content.form_login_required)
