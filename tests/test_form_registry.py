from django import forms
from django.test import TestCase

from djangocms_form_builder.forms import FormsForm


class MyTestForm(forms.Form):
    field = forms.TextInput()


class NamedForm(MyTestForm):
    class Meta:
        verbose_name = "This form has a custom name"


class TestRegistry(TestCase):
    def test_registry(self):
        from djangocms_form_builder import (
            get_registered_forms,
            register_with_form_builder,
        )

        registered_forms = get_registered_forms()
        # no forms registered yet
        self.assertEqual(registered_forms[0][0], "No forms registered")
        forms_form = FormsForm()
        # No forms to select: hide field in form plugin admin form
        self.assertIsInstance(
            forms_form.fields["form_selection"].widget, forms.HiddenInput
        )

        register_with_form_builder(MyTestForm)

        registered_forms = get_registered_forms()
        self.assertEqual(len(registered_forms), 1)  # one form
        self.assertEqual(
            registered_forms[0][1], "My Test Form"
        )  # derived from the class name
        forms_form = FormsForm()
        # Form registered: Select widget in form plugin admin form
        self.assertIsInstance(forms_form.fields["form_selection"].widget, forms.Select)

        register_with_form_builder(NamedForm)

        registered_forms = get_registered_forms()
        self.assertEqual(len(registered_forms), 2)  # second form
        self.assertEqual(
            registered_forms[1][1], "This form has a custom name"
        )  # attribute-driven
