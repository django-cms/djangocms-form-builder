from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from djangocms_form_builder import actions
from djangocms_form_builder.forms import FormsForm


class FormsFormValidationTests(SimpleTestCase):
    def _clean(self, **overrides):
        cleaned_data = {
            "form_selection": "",
            "form_name": "feedback",
            "form_actions": [actions.SAVE_TO_DB_ACTION],
            "form_unique": False,
            "form_login_required": False,
        }
        cleaned_data.update(overrides)
        form = FormsForm()
        form.cleaned_data = cleaned_data
        return form.clean()

    def test_custom_form_requires_name(self):
        with self.assertRaises(ValidationError) as ctx:
            self._clean(form_name="")
        self.assertIn("form_name", ctx.exception.error_dict)

    def test_unique_form_requires_database_action(self):
        with self.assertRaises(ValidationError) as ctx:
            self._clean(form_unique=True, form_actions=[])
        self.assertEqual(set(ctx.exception.error_dict), {"form_actions", "form_unique"})

    def test_missing_actions_are_rejected(self):
        form = FormsForm()
        form.cleaned_data = {
            "form_selection": "",
            "form_name": "feedback",
            "form_unique": False,
            "form_login_required": False,
        }
        with self.assertRaises(ValidationError) as ctx:
            form.clean()
        self.assertIn("form_actions", ctx.exception.error_dict)

    def test_unique_form_requires_login(self):
        with self.assertRaises(ValidationError) as ctx:
            self._clean(form_unique=True)
        self.assertEqual(
            set(ctx.exception.error_dict), {"form_login_required", "form_unique"}
        )

    def test_consistent_unique_form_is_accepted(self):
        cleaned_data = self._clean(form_unique=True, form_login_required=True)
        self.assertTrue(cleaned_data["form_unique"])
