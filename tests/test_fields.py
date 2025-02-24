from django.test import TestCase

from djangocms_form_builder.fields import AttributesField, TagTypeField


class FieldsTestCase(TestCase):
    def test_attributes_field(self):
        field = AttributesField()
        self.assertEqual(field.verbose_name, "Attributes")
        self.assertEqual(field.blank, True)

    def test_tag_type_field(self):
        field = TagTypeField()
        self.assertEqual(field.verbose_name, "Tag type")
        self.assertEqual(
            list(field.choices),
            list((("div", "div"),)),
        )
        self.assertEqual(field.default, "div")
        self.assertEqual(field.max_length, 255)
        self.assertEqual(
            field.help_text,
            "Select the HTML tag to be used.",
        )
