from decimal import Decimal

from cms.api import add_plugin
from cms.test_utils.testcases import CMSTestCase
from django import forms
from django.test import TestCase

from djangocms_form_builder.models import (
    BooleanField,
    CharField,
    Choice,
    DateField,
    DateTimeField,
    DecimalField,
    EmailField,
    Form,
    FormEntry,
    FormField,
    IntegerField,
    Select,
    SubmitButton,
    SwitchInput,
    TextareaField,
    TimeField,
    UrlField,
)

from .fixtures import TestFixture


class FormsModelTestCase(TestCase):
    def test_form_instance(self):
        instance = Form.objects.create()
        instance.save()
        self.assertEqual(str(instance), "Form (1)")
        self.assertEqual(instance.get_short_description(), "<unnamed>")
        instance.form_name = "my-test-form"
        self.assertEqual(instance.get_short_description(), "(my-test-form)")

        entry = FormEntry.objects.create(form_name=instance.form_name)
        self.assertEqual(str(entry), "my-test-form (1)")


class FormFieldModelTests(TestFixture, CMSTestCase):
    """Test FormField base class functionality"""

    def test_formfield_getattr_returns_config_values(self):
        """Test that __getattr__ makes config properties accessible"""
        field = FormField.objects.create(
            placeholder=self.placeholder,
            language=self.language,
            config={"field_name": "test", "field_label": "Test Label"},
        )
        # Direct attribute access should return config values
        self.assertEqual(field.field_name, "test")
        self.assertEqual(field.field_label, "Test Label")

    def test_formfield_str_uses_config_str(self):
        """Test __str__ with custom __str__ in config"""
        field = FormField.objects.create(
            placeholder=self.placeholder,
            language=self.language,
            ui_item="TestItem",
            config={"__str__": "Custom String"},
        )
        self.assertEqual(str(field), "Custom String")

    def test_formfield_str_default(self):
        """Test __str__ default format uses gettext(ui_item) + PK"""
        field = FormField.objects.create(
            placeholder=self.placeholder,
            language=self.language,
            ui_item="TestItem",
            config={},
        )
        # __str__ format is "gettext(ui_item) (pk)"
        result = str(field)
        # Should have format with PK in parentheses
        self.assertRegex(result, r"\(\d+\)$")

    def test_formfield_add_classes(self):
        """Test add_classes method"""
        field = FormField.objects.create(
            placeholder=self.placeholder,
            language=self.language,
            config={},
        )
        field.add_classes("class1", "class2 class3")
        self.assertIn("class1", field._additional_classes)
        self.assertIn("class2", field._additional_classes)
        self.assertIn("class3", field._additional_classes)

    def test_formfield_add_attribute(self):
        """Test add_attribute method"""
        field = FormField.objects.create(
            placeholder=self.placeholder,
            language=self.language,
            config={},
        )
        field.add_attribute("data-test", "value1")
        field.add_attribute("data-other", "value2")

        attrs = field.config.get("attributes", {})
        self.assertEqual(attrs["data-test"], "value1")
        self.assertEqual(attrs["data-other"], "value2")

    def test_formfield_get_attributes(self):
        """Test get_attributes returns formatted HTML attributes"""
        field = FormField.objects.create(
            placeholder=self.placeholder,
            language=self.language,
            config={"attributes": {"id": "test-id", "class": "base-class"}},
        )
        field.add_classes("extra-class")

        attrs = field.get_attributes()
        self.assertIn('id="test-id"', attrs)
        self.assertIn("base-class", attrs)
        self.assertIn("extra-class", attrs)

    def test_formfield_get_attributes_empty(self):
        """Test get_attributes with no attributes returns empty or single space"""
        field = FormField.objects.create(
            placeholder=self.placeholder,
            language=self.language,
            config={},
        )
        attrs = field.get_attributes()
        # Returns " " (single space) when no attributes
        self.assertIn(attrs, ["", " "])

    def test_formfield_save_sets_ui_item(self):
        """Test that save() sets ui_item to class name"""
        field = CharField.objects.create(
            placeholder=self.placeholder,
            language=self.language,
            config={},
        )
        self.assertEqual(field.ui_item, "CharField")

    def test_formfield_initialize_from_form(self):
        """Test initialize_from_form populates config from form"""
        from djangocms_form_builder.forms import CharFieldForm

        field = CharField(
            placeholder=self.placeholder,
            language=self.language,
            config={},
        )
        field.initialize_from_form(CharFieldForm)

        # Should have initialized config fields from CharFieldForm's entangled fields
        # CharFieldForm entangles min_length and max_length, not field_name
        self.assertIn("min_length", field.config)
        self.assertIn("max_length", field.config)

    def test_formfield_get_short_description(self):
        """Test get_short_description returns label and name"""
        field = FormField.objects.create(
            placeholder=self.placeholder,
            language=self.language,
            config={"field_name": "email", "field_label": "Email Address"},
        )
        desc = field.get_short_description()
        self.assertIn("Email Address", desc)
        self.assertIn("email", desc)


class CharFieldModelTests(TestFixture, CMSTestCase):
    """Test CharField model"""

    def test_charfield_get_form_field(self):
        """Test get_form_field returns proper Django form field"""
        field = CharField.objects.create(
            placeholder=self.placeholder,
            language=self.language,
            config={
                "field_name": "username",
                "field_label": "Username",
                "field_required": True,
                "field_placeholder": "Enter username",
            },
        )
        name, form_field = field.get_form_field()

        self.assertEqual(name, "username")
        self.assertIsInstance(form_field, forms.CharField)
        self.assertEqual(form_field.label, "Username")
        self.assertTrue(form_field.required)
        self.assertEqual(form_field.widget.attrs["placeholder"], "Enter username")


class EmailFieldModelTests(TestFixture, CMSTestCase):
    """Test EmailField model"""

    def test_emailfield_get_form_field(self):
        """Test EmailField returns EmailField with proper widget"""
        field = EmailField.objects.create(
            placeholder=self.placeholder,
            language=self.language,
            config={
                "field_name": "email",
                "field_label": "Email",
                "field_required": False,
                "field_placeholder": "you@example.com",
            },
        )
        name, form_field = field.get_form_field()

        self.assertEqual(name, "email")
        self.assertIsInstance(form_field, forms.EmailField)
        self.assertFalse(form_field.required)


class UrlFieldModelTests(TestFixture, CMSTestCase):
    """Test UrlField model"""

    def test_urlfield_get_form_field(self):
        """Test UrlField returns URLField"""
        field = UrlField.objects.create(
            placeholder=self.placeholder,
            language=self.language,
            config={
                "field_name": "website",
                "field_label": "Website",
                "field_required": False,
            },
        )
        name, form_field = field.get_form_field()

        self.assertEqual(name, "website")
        self.assertIsInstance(form_field, forms.URLField)


class DecimalFieldModelTests(TestFixture, CMSTestCase):
    """Test DecimalField model"""

    def test_decimalfield_get_form_field(self):
        """Test DecimalField with min/max/decimal_places"""
        field = DecimalField.objects.create(
            placeholder=self.placeholder,
            language=self.language,
            config={
                "field_name": "amount",
                "field_label": "Amount",
                "field_required": True,
                "min_value": "0.00",
                "max_value": "1000.00",
                "decimal_places": 2,
            },
        )
        name, form_field = field.get_form_field()

        self.assertEqual(name, "amount")
        self.assertIsInstance(form_field, DecimalField.StrDecimalField)
        self.assertEqual(form_field.min_value, Decimal("0.00"))
        self.assertEqual(form_field.max_value, Decimal("1000.00"))
        self.assertEqual(form_field.decimal_places, 2)

    def test_decimalfield_numberinput_format_value(self):
        """Test NumberInput.format_value formats decimal places correctly"""
        widget = DecimalField.NumberInput(decimal_places=2)

        self.assertEqual(widget.format_value("10"), "10.00")
        self.assertEqual(widget.format_value("10.5"), "10.50")
        self.assertEqual(widget.format_value("10.123"), "10.12")
        self.assertEqual(widget.format_value(None), "")

    def test_decimalfield_numberinput_zero_decimals(self):
        """Test NumberInput with decimal_places=0"""
        widget = DecimalField.NumberInput(decimal_places=0)
        self.assertEqual(widget.format_value("10.99"), "10")

    def test_strdecimalfield_clean_returns_string(self):
        """Test StrDecimalField.clean returns string instead of Decimal"""
        field_instance = DecimalField.StrDecimalField()
        result = field_instance.clean("123.45")
        self.assertIsInstance(result, str)
        self.assertEqual(result, "123.45")


class IntegerFieldModelTests(TestFixture, CMSTestCase):
    """Test IntegerField model"""

    def test_integerfield_get_form_field(self):
        """Test IntegerField returns IntegerField"""
        field = IntegerField.objects.create(
            placeholder=self.placeholder,
            language=self.language,
            config={
                "field_name": "age",
                "field_label": "Age",
                "field_required": True,
            },
        )
        name, form_field = field.get_form_field()

        self.assertEqual(name, "age")
        self.assertIsInstance(form_field, forms.IntegerField)


class TextareaFieldModelTests(TestFixture, CMSTestCase):
    """Test TextareaField model"""

    def test_textareafield_get_form_field(self):
        """Test TextareaField with custom rows"""
        field = TextareaField.objects.create(
            placeholder=self.placeholder,
            language=self.language,
            config={
                "field_name": "comments",
                "field_label": "Comments",
                "field_required": False,
                "field_rows": 5,
                "field_placeholder": "Your comments",
            },
        )
        name, form_field = field.get_form_field()

        self.assertEqual(name, "comments")
        self.assertIsInstance(form_field.widget, forms.Textarea)
        self.assertEqual(form_field.widget.attrs["rows"], 5)


class DateFieldModelTests(TestFixture, CMSTestCase):
    """Test DateField model"""

    def test_datefield_get_form_field(self):
        """Test DateField returns DateField with date input type"""
        field = DateField.objects.create(
            placeholder=self.placeholder,
            language=self.language,
            config={
                "field_name": "birthdate",
                "field_label": "Birth Date",
                "field_required": True,
            },
        )
        name, form_field = field.get_form_field()

        self.assertEqual(name, "birthdate")
        self.assertIsInstance(form_field, forms.DateField)
        self.assertIsInstance(form_field.widget, DateField.DateInput)
        self.assertEqual(form_field.widget.input_type, "date")


class DateTimeFieldModelTests(TestFixture, CMSTestCase):
    """Test DateTimeField model"""

    def test_datetimefield_get_form_field(self):
        """Test DateTimeField with datetime-local input"""
        field = DateTimeField.objects.create(
            placeholder=self.placeholder,
            language=self.language,
            config={
                "field_name": "appointment",
                "field_label": "Appointment",
                "field_required": True,
            },
        )
        name, form_field = field.get_form_field()

        self.assertEqual(name, "appointment")
        self.assertIsInstance(form_field, DateTimeField.DateTimeField)
        self.assertEqual(form_field.widget.input_type, "datetime-local")

    def test_datetimefield_prepare_value_parses_string(self):
        """Test DateTimeField.prepare_value parses datetime strings"""
        field_instance = DateTimeField.DateTimeField()
        iso_string = "2025-10-31T14:30:00"
        result = field_instance.prepare_value(iso_string)
        self.assertIsNotNone(result)


class TimeFieldModelTests(TestFixture, CMSTestCase):
    """Test TimeField model"""

    def test_timefield_get_form_field(self):
        """Test TimeField with time input type"""
        field = TimeField.objects.create(
            placeholder=self.placeholder,
            language=self.language,
            config={
                "field_name": "meeting_time",
                "field_label": "Meeting Time",
                "field_required": False,
            },
        )
        name, form_field = field.get_form_field()

        self.assertEqual(name, "meeting_time")
        self.assertIsInstance(form_field, forms.TimeField)
        self.assertEqual(form_field.widget.input_type, "time")


class SelectFieldModelTests(TestFixture, CMSTestCase):
    """Test Select model and choices"""

    def test_select_get_form_field_single_select(self):
        """Test Select returns ChoiceField for single select"""
        select = Select.objects.create(
            placeholder=self.placeholder,
            language=self.language,
            position=0,
            config={
                "field_name": "country",
                "field_label": "Country",
                "field_required": True,
                "field_select": "select",
            },
        )

        # Add choices using add_plugin - config is a dict with value/verbose
        add_plugin(
            placeholder=self.placeholder,
            plugin_type="ChoicePlugin",
            language=self.language,
            target=select,
            config={"value": "us", "verbose": "United States"},
        )

        name, form_field = select.get_form_field()

        self.assertEqual(name, "country")
        self.assertIsInstance(form_field, forms.ChoiceField)
        self.assertIsInstance(form_field.widget, forms.Select)

    def test_select_get_form_field_radio(self):
        """Test Select with radio widget"""
        select = Select.objects.create(
            placeholder=self.placeholder,
            language=self.language,
            config={
                "field_name": "option",
                "field_label": "Option",
                "field_required": False,
                "field_select": "radio",
            },
        )

        name, form_field = select.get_form_field()
        self.assertIsInstance(form_field.widget, forms.RadioSelect)

    def test_select_get_form_field_multiselect(self):
        """Test Select with multiple choice"""
        select = Select.objects.create(
            placeholder=self.placeholder,
            language=self.language,
            config={
                "field_name": "tags",
                "field_label": "Tags",
                "field_required": False,
                "field_select": "multiselect",
            },
        )

        name, form_field = select.get_form_field()
        self.assertIsInstance(form_field, forms.MultipleChoiceField)
        self.assertIsInstance(form_field.widget, forms.SelectMultiple)

    def test_select_get_form_field_checkbox(self):
        """Test Select with checkbox widget"""
        select = Select.objects.create(
            placeholder=self.placeholder,
            language=self.language,
            config={
                "field_name": "interests",
                "field_label": "Interests",
                "field_required": False,
                "field_select": "checkbox",
            },
        )

        name, form_field = select.get_form_field()
        self.assertIsInstance(form_field, forms.MultipleChoiceField)
        self.assertIsInstance(form_field.widget, forms.CheckboxSelectMultiple)

    def test_select_no_selection_added_when_not_required(self):
        """Test that 'No selection' is added for non-required single selects"""
        select = Select.objects.create(
            placeholder=self.placeholder,
            language=self.language,
            config={
                "field_name": "optional",
                "field_label": "Optional",
                "field_required": False,
                "field_select": "select",
            },
        )

        name, form_field = select.get_form_field()
        choices = form_field.choices
        # First choice should be empty/no selection
        self.assertEqual(choices[0][0], "")


class ChoiceModelTests(TestFixture, CMSTestCase):
    """Test Choice model"""

    def test_choice_get_short_description(self):
        """Test Choice.get_short_description shows verbose and value"""
        choice = Choice.objects.create(
            placeholder=self.placeholder,
            language=self.language,
            config={"value": "opt1", "verbose": "Option One"},
        )
        desc = choice.get_short_description()
        self.assertIn("Option One", desc)
        self.assertIn("opt1", desc)


class BooleanFieldModelTests(TestFixture, CMSTestCase):
    """Test BooleanField model"""

    def test_booleanfield_get_form_field_checkbox(self):
        """Test BooleanField with regular checkbox"""
        field = BooleanField.objects.create(
            placeholder=self.placeholder,
            language=self.language,
            config={
                "field_name": "agree",
                "field_label": "I agree",
                "field_required": True,
                "field_as_switch": False,
            },
        )
        name, form_field = field.get_form_field()

        self.assertEqual(name, "agree")
        self.assertIsInstance(form_field, forms.BooleanField)
        self.assertIsInstance(form_field.widget, forms.CheckboxInput)

    def test_booleanfield_get_form_field_switch(self):
        """Test BooleanField with switch widget"""
        field = BooleanField.objects.create(
            placeholder=self.placeholder,
            language=self.language,
            config={
                "field_name": "notifications",
                "field_label": "Enable notifications",
                "field_required": False,
                "field_as_switch": True,
            },
        )
        name, form_field = field.get_form_field()

        self.assertIsInstance(form_field.widget, SwitchInput)


class SubmitButtonModelTests(TestFixture, CMSTestCase):
    """Test SubmitButton model"""

    def test_submitbutton_model_exists(self):
        """Test SubmitButton can be created"""
        button = SubmitButton.objects.create(
            placeholder=self.placeholder,
            language=self.language,
            config={
                "field_name": "submit",
                "field_label": "Submit Form",
            },
        )
        self.assertIsNotNone(button)
        self.assertEqual(button.ui_item, "SubmitButton")
