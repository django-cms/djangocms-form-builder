import inspect

from cms.api import add_plugin
from cms.test_utils.testcases import CMSTestCase

from djangocms_form_builder import cms_plugins
from djangocms_form_builder.cms_plugins.form_plugins import FormElementPlugin

from .fixtures import TestFixture


class FormEditorTestCase(TestFixture, CMSTestCase):
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
                and cls is not cms_plugins.SubmitPlugin
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
        self.assertContains(response, '<input type="hidden" name="csrfmiddlewaretoken"')
        for item, cls in cms_plugins.__dict__.items():
            if (
                inspect.isclass(cls)
                and issubclass(cls, FormElementPlugin)
                and not issubclass(cls, cms_plugins.ChoicePlugin)
                and cls is not cms_plugins.SubmitPlugin
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
        self.assertEqual(response.content.decode().count('type="submit"'), 1)
        self.assertIn('value="Submit"', response.content.decode())

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
        self.assertEqual(content.count('type="submit"'), 1)
        self.assertIn('value="Submit Form"', content)
        self.assertNotIn('value="Submit"', content)

    def test_auto_submit_button_handles_nested_submit_button(self):
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
            plugin_type=cms_plugins.SelectPlugin.__name__,
            target=form,
            language=self.language,
            config=dict(
                field_name="container",
            ),
        )
        choice = add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.ChoicePlugin.__name__,
            target=container,
            language=self.language,
            config=dict(
                value="choice1",
                verbose="Choice 1",
            ),
        )
        add_plugin(
            placeholder=self.placeholder,
            plugin_type=cms_plugins.SubmitPlugin.__name__,
            target=choice,
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
        self.assertEqual(content.count('type="submit"'), 1)
        self.assertIn('value="Submit Form"', content)
        self.assertNotIn('value="Submit"', content)
