from decimal import Decimal

from django.test import SimpleTestCase

from djangocms_form_builder import helpers


class HelpersTests(SimpleTestCase):
    def test_get_option_prefers_form_meta_over_global_and_default(self):
        class DummyForm:
            class Meta:
                options = {"opt": "from-meta"}

        # If present in Meta.options -> returns that
        self.assertEqual(
            helpers.get_option(DummyForm, "opt", default="dflt"), "from-meta"
        )

        # If missing in Meta, use global_options (we temporarily override)
        orig = helpers.global_options.copy()
        try:
            helpers.global_options.update({"x": 123})

            class NoOpt:
                class Meta:
                    options = {}

            self.assertEqual(helpers.get_option(NoOpt, "x", default=0), 123)
        finally:
            helpers.global_options.clear()
            helpers.global_options.update(orig)

        # If missing in both, use provided default
        self.assertEqual(
            helpers.get_option(DummyForm, "missing", default="dflt"), "dflt"
        )

    def test_insert_fields_appends_new_block_when_block_none(self):
        fieldsets = [("Main", {"fields": ["a", "b"]})]
        fs = helpers.insert_fields(
            fieldsets, ["x", "y"], block=None, position=-1, blockname="Extra"
        )
        # Expect two blocks now, with new block at end
        self.assertEqual(len(fs), 2)
        self.assertEqual(fs[1][0], "Extra")
        self.assertEqual(fs[1][1]["fields"], ["x", "y"])
        # classes contains 'collapse' because original fieldsets not empty
        self.assertIn("collapse", fs[1][1]["classes"])

    def test_insert_fields_inserts_into_existing_block(self):
        fieldsets = [("Main", {"fields": ["a", "b"]})]
        # Insert at position 0 -> before first field
        fs0 = helpers.insert_fields(fieldsets, ["x"], block=0, position=0)
        self.assertEqual(fs0[0][1]["fields"], ["x", "a", "b"])
        # Insert at position -1 -> append to end
        fs1 = helpers.insert_fields(fieldsets, ["x"], block=0, position=-1)
        self.assertEqual(fs1[0][1]["fields"], ["a", "b", "x"])

    def test_first_choice_nested(self):
        choices = (("group", (("a", "A"), ("b", "B"))), ("c", "C"))
        self.assertEqual(helpers.first_choice(choices), "a")
        self.assertEqual(helpers.first_choice((("x", "X"),)), "x")

    def test_mark_safe_lazy(self):
        s = helpers.mark_safe_lazy("<b>hi</b>")
        # Evaluates to a SafeString
        self.assertIn("<b>hi</b>", str(s))

    def test_add_plugin_delegates(self):
        calls = {}

        class Placeholder:
            def add_plugin(self, plugin):
                calls["added"] = plugin

        class Plugin:
            parent = None
            position = None

        plugin = Plugin()
        helpers.add_plugin(Placeholder(), plugin)
        self.assertIs(calls["added"], plugin)

    def test_delete_plugin_delegates(self):
        class Placeholder:
            def delete_plugin(self, plugin):
                return ("deleted", plugin)

        class Plugin:
            placeholder = Placeholder()

        marker = object()
        plugin = Plugin()
        plugin.marker = marker

        res = helpers.delete_plugin(plugin)
        self.assertEqual(res, ("deleted", plugin))

    def test_coerce_decimal(self):
        self.assertEqual(helpers.coerce_decimal("1.23"), Decimal("1.23"))
        self.assertIsNone(helpers.coerce_decimal(None))
        # A non-numeric string would raise InvalidOperation (not caught), so we don't test it
