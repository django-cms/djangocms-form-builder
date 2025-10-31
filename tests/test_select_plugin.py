from cms.api import add_plugin
from cms.plugin_pool import plugin_pool
from cms.test_utils.testcases import CMSTestCase
from django.contrib.admin.sites import AdminSite
from django.http import QueryDict

from djangocms_form_builder.cms_plugins.form_plugins import SelectPlugin
from djangocms_form_builder.models import Select

from .fixtures import TestFixture


class SelectPluginTests(TestFixture, CMSTestCase):
    def setUp(self):
        super().setUp()
        self.plugin_class = plugin_pool.get_plugin("SelectPlugin")
        self.admin_site = AdminSite()

    def _create_select_plugin(self, **config_kwargs):
        """Helper to create a SelectPlugin instance"""
        defaults = {
            "field_name": "test_select",
            "field_label": "Test Select",
            "field_select": "select",
            "field_required": False,
        }
        defaults.update(config_kwargs)

        return add_plugin(
            placeholder=self.placeholder,
            plugin_type="SelectPlugin",
            language=self.language,
            config=defaults,
        )

    def _create_choice_plugin(self, parent, value, verbose):
        """Helper to create a ChoicePlugin as child of SelectPlugin"""
        return add_plugin(
            placeholder=self.placeholder,
            plugin_type="ChoicePlugin",
            language=self.language,
            target=parent,
            config={"value": value, "verbose": verbose},
        )

    def _get_form_with_choices(self, instance, choices_data):
        """Helper to get admin form with field_choices populated

        choices_data should be a list of (value, verbose) tuples.
        The ChoicesFormField uses AttributesWidget which expects POST data
        with attributes_key[field_name] and attributes_value[field_name] lists.
        We need to use a QueryDict to provide getlist() method.
        """
        form_class = self.plugin_class.form

        # Build a QueryDict with the form data
        query_string_parts = [
            f"field_name={instance.config.get('field_name', 'test')}",
            f"field_label={instance.config.get('field_label', 'Test')}",
            f"field_select={instance.config.get('field_select', 'select')}",
            f"field_required={instance.config.get('field_required', False)}",
        ]

        # Add choices in the AttributesWidget format
        for value, verbose in choices_data:
            query_string_parts.append(f"attributes_key[field_choices]={value}")
            query_string_parts.append(f"attributes_value[field_choices]={verbose}")

        query_string = "&".join(query_string_parts)
        data = QueryDict(query_string, mutable=False)

        form = form_class(data=data, instance=instance)
        return form

    def test_select_plugin_registered(self):
        """Verify SelectPlugin is properly registered"""
        self.assertIsNotNone(self.plugin_class)
        self.assertEqual(self.plugin_class.name, "Select")
        self.assertEqual(self.plugin_class.model, Select)

    def test_select_plugin_allows_choice_children(self):
        """Verify SelectPlugin allows ChoicePlugin children"""
        self.assertTrue(self.plugin_class.allow_children)
        self.assertIn("ChoicePlugin", self.plugin_class.child_classes)

    def test_save_model_adds_new_choices(self):
        """Test that save_model adds new ChoicePlugin instances from field_choices"""
        select_instance = self._create_select_plugin()

        # Initially no children
        self.assertEqual(select_instance.get_children().count(), 0)

        # Create form with new choices
        choices_data = [
            ("val1", "Option 1"),
            ("val2", "Option 2"),
            ("val3", "Option 3"),
        ]
        form = self._get_form_with_choices(select_instance, choices_data)
        self.assertTrue(form.is_valid(), form.errors)

        # Save via plugin's save_model
        plugin_instance = SelectPlugin(self.plugin_class.model, self.admin_site)
        plugin_instance.save_model(
            request=self.get_request("/"),
            obj=select_instance,
            form=form,
            change=True,
        )

        # Verify children were created
        children = select_instance.get_children()
        self.assertEqual(children.count(), 3)

        # Verify choice values and verbose names
        choice_plugins = [child.djangocms_form_builder_formfield for child in children]
        actual_choices = [
            (c.config["value"], c.config["verbose"]) for c in choice_plugins
        ]
        self.assertEqual(sorted(actual_choices), sorted(choices_data))

    def test_save_model_updates_existing_choices(self):
        """Test that save_model updates existing ChoicePlugin verbose names"""
        select_instance = self._create_select_plugin()

        # Add initial choices
        self._create_choice_plugin(select_instance, "opt1", "Original 1")
        self._create_choice_plugin(select_instance, "opt2", "Original 2")

        initial_count = select_instance.get_children().count()
        self.assertEqual(initial_count, 2)

        # Update choices via form (same values, different verbose names)
        choices_data = [("opt1", "Updated 1"), ("opt2", "Updated 2")]
        form = self._get_form_with_choices(select_instance, choices_data)
        self.assertTrue(form.is_valid(), form.errors)

        plugin_instance = SelectPlugin(self.plugin_class.model, self.admin_site)
        plugin_instance.save_model(
            request=self.get_request("/"),
            obj=select_instance,
            form=form,
            change=True,
        )

        # Verify count stays the same
        self.assertEqual(select_instance.get_children().count(), initial_count)

        # Verify verbose names were updated
        children = select_instance.get_children()
        choice_plugins = [child.djangocms_form_builder_formfield for child in children]
        choices_dict = {c.config["value"]: c.config["verbose"] for c in choice_plugins}
        self.assertEqual(choices_dict["opt1"], "Updated 1")
        self.assertEqual(choices_dict["opt2"], "Updated 2")

    def test_save_model_deletes_removed_choices(self):
        """Test that save_model deletes ChoicePlugin instances not in field_choices"""
        select_instance = self._create_select_plugin()

        # Add initial choices
        self._create_choice_plugin(select_instance, "keep", "Keep This")
        self._create_choice_plugin(select_instance, "remove1", "Remove 1")
        self._create_choice_plugin(select_instance, "remove2", "Remove 2")

        self.assertEqual(select_instance.get_children().count(), 3)

        # Update to only keep one choice
        choices_data = [("keep", "Keep This")]
        form = self._get_form_with_choices(select_instance, choices_data)
        self.assertTrue(form.is_valid(), form.errors)

        plugin_instance = SelectPlugin(self.plugin_class.model, self.admin_site)
        plugin_instance.save_model(
            request=self.get_request("/"),
            obj=select_instance,
            form=form,
            change=True,
        )

        # Verify only one child remains
        children = select_instance.get_children()
        self.assertEqual(children.count(), 1)

        # Verify it's the correct one
        remaining = children.first().djangocms_form_builder_formfield
        self.assertEqual(remaining.config["value"], "keep")
        self.assertEqual(remaining.config["verbose"], "Keep This")

    def test_save_model_mixed_operations(self):
        """Test save_model with add, update, and delete in one operation"""
        select_instance = self._create_select_plugin()

        # Add initial choices
        self._create_choice_plugin(select_instance, "update", "Original")
        self._create_choice_plugin(select_instance, "delete", "Will Delete")

        self.assertEqual(select_instance.get_children().count(), 2)

        # Mixed operation: update "update", delete "delete", add "new"
        choices_data = [
            ("update", "Updated Value"),
            ("new", "Newly Added"),
        ]
        form = self._get_form_with_choices(select_instance, choices_data)
        self.assertTrue(form.is_valid(), form.errors)

        plugin_instance = SelectPlugin(self.plugin_class.model, self.admin_site)
        plugin_instance.save_model(
            request=self.get_request("/"),
            obj=select_instance,
            form=form,
            change=True,
        )

        # Verify count: 2 original - 1 deleted + 1 added = 2
        children = select_instance.get_children()
        self.assertEqual(children.count(), 2)

        # Verify the correct choices remain
        choice_plugins = [child.djangocms_form_builder_formfield for child in children]
        choices_dict = {c.config["value"]: c.config["verbose"] for c in choice_plugins}

        self.assertIn("update", choices_dict)
        self.assertEqual(choices_dict["update"], "Updated Value")
        self.assertIn("new", choices_dict)
        self.assertEqual(choices_dict["new"], "Newly Added")
        self.assertNotIn("delete", choices_dict)

    def test_save_model_preserves_choice_order(self):
        """Test that choices maintain their order after updates"""
        select_instance = self._create_select_plugin()

        # Add initial choices in specific order
        choices_data = [("a", "Alpha"), ("b", "Beta"), ("c", "Gamma")]
        form = self._get_form_with_choices(select_instance, choices_data)
        self.assertTrue(form.is_valid(), form.errors)

        plugin_instance = SelectPlugin(self.plugin_class.model, self.admin_site)
        plugin_instance.save_model(
            request=self.get_request("/"),
            obj=select_instance,
            form=form,
            change=True,
        )

        # Refresh the instance to clear cached choices
        select_instance.refresh_from_db()
        select_instance._choices = None  # Clear the cached choices

        # Get choices via the model's get_choices method
        actual_choices = select_instance.get_choices()
        expected_choices = [("a", "Alpha"), ("b", "Beta"), ("c", "Gamma")]
        self.assertEqual(actual_choices, expected_choices)

    def test_save_model_no_changes_to_choices(self):
        """Test that save_model handles unchanged choices correctly"""
        select_instance = self._create_select_plugin()

        # Add initial choices
        choice1 = self._create_choice_plugin(select_instance, "same1", "Same 1")
        choice2 = self._create_choice_plugin(select_instance, "same2", "Same 2")

        initial_ids = [choice1.pk, choice2.pk]

        # Re-save with same choices
        choices_data = [("same1", "Same 1"), ("same2", "Same 2")]
        form = self._get_form_with_choices(select_instance, choices_data)
        self.assertTrue(form.is_valid(), form.errors)

        plugin_instance = SelectPlugin(self.plugin_class.model, self.admin_site)
        plugin_instance.save_model(
            request=self.get_request("/"),
            obj=select_instance,
            form=form,
            change=True,
        )

        # Verify same instances remain (IDs unchanged)
        children = select_instance.get_children()
        self.assertEqual(children.count(), 2)

        # IDs should be the same
        current_ids = sorted([child.pk for child in children])
        self.assertEqual(sorted(initial_ids), current_ids)

    def test_save_model_empty_choices(self):
        """Test that ChoicesFormField validation requires at least one choice"""
        select_instance = self._create_select_plugin()

        # Add initial choices
        self._create_choice_plugin(select_instance, "remove1", "Remove 1")
        self._create_choice_plugin(select_instance, "remove2", "Remove 2")

        self.assertEqual(select_instance.get_children().count(), 2)

        # Try to save with empty choices - should fail validation
        choices_data = []
        form = self._get_form_with_choices(select_instance, choices_data)

        # The form should NOT be valid with empty choices
        self.assertFalse(form.is_valid())
        self.assertIn("field_choices", form.errors)

    def test_get_choices_returns_ordered_list(self):
        """Test that Select.get_choices() returns choices in correct order"""
        select_instance = self._create_select_plugin()

        # Add choices in specific order
        self._create_choice_plugin(select_instance, "first", "First Choice")
        self._create_choice_plugin(select_instance, "second", "Second Choice")
        self._create_choice_plugin(select_instance, "third", "Third Choice")

        choices = select_instance.get_choices()

        self.assertEqual(len(choices), 3)
        self.assertEqual(choices[0], ("first", "First Choice"))
        self.assertEqual(choices[1], ("second", "Second Choice"))
        self.assertEqual(choices[2], ("third", "Third Choice"))

    def test_select_field_form_initializes_with_existing_choices(self):
        """Test that SelectFieldForm populates field_choices from instance"""
        select_instance = self._create_select_plugin()

        # Add some choices
        self._create_choice_plugin(select_instance, "opt1", "Option 1")
        self._create_choice_plugin(select_instance, "opt2", "Option 2")

        # Create form with instance
        form_class = self.plugin_class.form
        form = form_class(instance=select_instance)

        # field_choices should be initialized with existing choices
        initial_choices = form.fields["field_choices"].initial
        self.assertEqual(len(initial_choices), 2)
        self.assertIn(("opt1", "Option 1"), initial_choices)
        self.assertIn(("opt2", "Option 2"), initial_choices)
