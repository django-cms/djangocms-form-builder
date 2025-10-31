from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from djangocms_form_builder import actions as actions_module
from djangocms_form_builder.actions import FormAction


class DummyAction(FormAction):
    verbose_name = "Dummy action"

    def execute(self, form, request):  # pragma: no cover - trivial
        return None


class NoVerboseAction(FormAction):
    verbose_name = None

    def execute(self, form, request):  # pragma: no cover - trivial
        return None


class NotAnAction:
    pass


class ActionRegistryTests(SimpleTestCase):
    def setUp(self):
        super().setUp()
        # Backup the original registry so we can safely modify it
        self._orig_registry = actions_module._action_registry.copy()

    def tearDown(self):
        # Restore the registry to its original state
        actions_module._action_registry.clear()
        actions_module._action_registry.update(self._orig_registry)
        super().tearDown()

    def test_register_adds_action_and_getters_work(self):
        action_hash = actions_module.get_hash(DummyAction)
        self.assertIsNone(actions_module.get_action_class(action_hash))

        actions_module.register(DummyAction)

        # get_action_class returns the class
        self.assertIs(actions_module.get_action_class(action_hash), DummyAction)
        # get_registered_actions contains our (hash, verbose_name) pair
        choices = dict(actions_module.get_registered_actions())
        self.assertIn(action_hash, choices)
        self.assertEqual(choices[action_hash], DummyAction.verbose_name)

    def test_unregister_removes_action(self):
        action_hash = actions_module.get_hash(DummyAction)
        actions_module.register(DummyAction)
        self.assertIsNotNone(actions_module.get_action_class(action_hash))

        actions_module.unregister(DummyAction)
        self.assertIsNone(actions_module.get_action_class(action_hash))

        choices = dict(actions_module.get_registered_actions())
        self.assertNotIn(action_hash, choices)

    def test_register_rejects_non_subclass(self):
        with self.assertRaises(ImproperlyConfigured):
            actions_module.register(NotAnAction)  # type: ignore[arg-type]

    def test_register_rejects_missing_verbose_name(self):
        with self.assertRaises(ImproperlyConfigured):
            actions_module.register(NoVerboseAction)

    def test_register_is_idempotent(self):
        # capture current size
        size_before = len(actions_module._action_registry)
        actions_module.register(DummyAction)
        size_after_first = len(actions_module._action_registry)
        actions_module.register(DummyAction)
        size_after_second = len(actions_module._action_registry)

        self.assertEqual(size_after_first, size_before + 1)
        self.assertEqual(size_after_second, size_after_first)

        actions_module.unregister(DummyAction)
        self.assertEqual(len(actions_module._action_registry), size_before)

    def test_unregister_is_safe_when_absent(self):
        size_before = len(actions_module._action_registry)
        actions_module.unregister(DummyAction)  # should not raise
        self.assertEqual(len(actions_module._action_registry), size_before)

    def test_get_registered_actions_empty_fallback(self):
        # Clear registry to simulate no actions registered
        actions_module._action_registry.clear()
        choices = actions_module.get_registered_actions()

        # Expect a single-choice tuple with an empty options tuple
        self.assertIsInstance(choices, tuple)
        self.assertEqual(len(choices), 1)
        self.assertIsInstance(choices[0], tuple)
        self.assertEqual(len(choices[0]), 2)
        self.assertIsInstance(choices[0][1], tuple)
        self.assertEqual(choices[0][1], ())
