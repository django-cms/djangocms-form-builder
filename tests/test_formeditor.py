import inspect

from cms.api import add_plugin
from cms.test_utils.testcases import CMSTestCase

from djangocms_form_builder import cms_plugins, settings
from djangocms_form_builder.cms_plugins.form_plugins import FormElementPlugin
from tests.test_app.cms_plugins import ContainerPlugin

from .fixtures import TestFixture


class FormEditorTestCase(TestFixture, CMSTestCase):
    def assert_submit_action(self, content, label):
        if settings.frontend == "django_formset":
            self.assertEqual(content.count('df-click="submit -> proceed"'), 1)
            self.assertIn(label, content)
        else:
            self.assertEqual(content.count('type="submit"'), 1)
            self.assertIn(f'value="{label}"', content)

    def test_form_editor(self):
        form = add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.FormPlugin.__name__,
            language=self.language,
            form_selection="",
            form_name="my-test-form",
        )

        for item, cls in cms_plugins.__dict__.items():
            if (
                inspect.isclass(cls)
                and issubclass(cls, FormElementPlugin)
                and not issubclass(cls, cms_plugins.ChoicePlugin)
                and cls not in (cms_plugins.SubmitPlugin, cms_plugins.CaptchaPlugin)
            ):
                field = add_plugin(
                    placeholder=self.placeholder,
                    plugin_type=cls.__name__,
                    target=form,
                    language=self.language,
                    config=dict(
                        field_name="field_" + item,
                    ),
                )
                field.initialize_from_form()

        self.publish(self.page, self.language)

        with self.login_user_context(self.superuser):
            response = self.client.get(self.request_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'action="/@form-builder/1"')
        self.assertNotContains(
            response, '<input type="hidden" name="csrfmiddlewaretoken"'
        )
        for item, cls in cms_plugins.__dict__.items():
            if (
                inspect.isclass(cls)
                and issubclass(cls, FormElementPlugin)
                and not issubclass(cls, cms_plugins.ChoicePlugin)
                and cls not in (cms_plugins.SubmitPlugin, cms_plugins.CaptchaPlugin)
            ):
                self.assertContains(response, f'name="field_{item}"')

    def test_auto_submit_button_appears_when_no_button(self):
        form = add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.FormPlugin.__name__,
            language=self.language,
            form_selection="",
            form_name="test-form",
        )
        add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.CharFieldPlugin.__name__,
            target=form,
            language=self.language,
            config=dict(
                field_name="text_field",
            ),
        )
        self.publish(self.page, self.language)
        with self.login_user_context(self.superuser):
            response = self.client.get(self.request_url)

        self.assertEqual(response.status_code, 200)
        self.assert_submit_action(response.content.decode(), "Submit")

    def test_auto_submit_button_does_not_appear_when_button_exists(self):
        form = add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.FormPlugin.__name__,
            language=self.language,
            form_selection="",
            form_name="test-form",
        )
        add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.CharFieldPlugin.__name__,
            target=form,
            language=self.language,
            config=dict(
                field_name="text_field",
            ),
        )
        add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.SubmitPlugin.__name__,
            target=form,
            language=self.language,
            config=dict(
                submit_cta="Submit Form",
            ),
        )
        self.publish(self.page, self.language)
        with self.login_user_context(self.superuser):
            response = self.client.get(self.request_url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assert_submit_action(content, "Submit Form")

    def test_submit_button_renders_context_class(self):
        form = add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.FormPlugin.__name__,
            language=self.language,
            form_selection="",
            form_name="test-form",
        )
        add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.CharFieldPlugin.__name__,
            target=form,
            language=self.language,
            config=dict(
                field_name="text_field",
            ),
        )
        add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.SubmitPlugin.__name__,
            target=form,
            language=self.language,
            config=dict(
                submit_cta="Send",
                form_submit_context="secondary",
            ),
        )
        self.publish(self.page, self.language)
        with self.login_user_context(self.superuser):
            response = self.client.get(self.request_url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assert_submit_action(content, "Send")
        self.assertIn('class="btn btn-secondary"', content)

    def test_auto_submit_button_does_not_appear_with_nested_button(self):
        form = add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.FormPlugin.__name__,
            language=self.language,
            form_selection="",
            form_name="test-form",
        )
        add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.CharFieldPlugin.__name__,
            target=form,
            language=self.language,
            config=dict(
                field_name="text_field",
            ),
        )
        container = add_plugin(
            placeholder=self.placeholder,
            plugin_type=ContainerPlugin.__name__,
            target=form,
            language=self.language,
        )
        nested_container = add_plugin(
            placeholder=self.placeholder,
            plugin_type=ContainerPlugin.__name__,
            target=container,
            language=self.language,
        )
        add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.SubmitPlugin.__name__,
            target=nested_container,
            language=self.language,
            config=dict(
                submit_cta="Submit Form",
            ),
        )
        self.publish(self.page, self.language)
        with self.login_user_context(self.superuser):
            response = self.client.get(self.request_url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assert_submit_action(content, "Submit Form")

    def test_auto_submit_button_appears_with_empty_nested_containers(self):
        form = add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.FormPlugin.__name__,
            language=self.language,
            form_selection="",
            form_name="test-form",
        )
        add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.CharFieldPlugin.__name__,
            target=form,
            language=self.language,
            config=dict(
                field_name="text_field",
            ),
        )
        container = add_plugin(
            placeholder=self.placeholder,
            plugin_type=ContainerPlugin.__name__,
            target=form,
            language=self.language,
        )
        add_plugin(
            placeholder=self.placeholder,
            plugin_type=ContainerPlugin.__name__,
            target=container,
            language=self.language,
        )
        self.publish(self.page, self.language)
        with self.login_user_context(self.superuser):
            response = self.client.get(self.request_url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assert_submit_action(content, "Submit")
