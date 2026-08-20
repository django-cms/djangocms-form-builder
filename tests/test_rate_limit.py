from datetime import timedelta
from unittest.mock import patch

from cms.test_utils.testcases import CMSTestCase
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from djangocms_form_builder import actions as actions_module
from djangocms_form_builder import rate_limit
from djangocms_form_builder.actions import FormAction
from djangocms_form_builder.forms import SimpleFrontendForm
from djangocms_form_builder.rate_limit import SubmissionQuota
from djangocms_form_builder.settings import _validate_rate_limits

# Aware or naive, exactly as the project's USE_TZ demands.
NOW = timezone.now()


class CountingAction(FormAction):
    verbose_name = "Counting action"
    rate_limits = {"source": (2, 3600)}

    calls = 0

    def execute(self, form, request):
        type(self).calls += 1
        return "executed"


class RateLimitSettingsTests(SimpleTestCase):
    def test_valid_configuration_passes_through(self):
        limits = {"default": {"source": (5, 60)}, "CountingAction": {"source": None}}
        self.assertIs(_validate_rate_limits(limits), limits)

    def test_rejects_non_dict(self):
        with self.assertRaises(ImproperlyConfigured):
            _validate_rate_limits([("source", (5, 60))])

    def test_rejects_non_dict_action_entry(self):
        with self.assertRaises(ImproperlyConfigured):
            _validate_rate_limits({"default": (5, 60)})

    def test_rejects_malformed_pair(self):
        for spec in (5, (5,), (5, 60, 1), ("many", 60)):
            with self.subTest(spec=spec), self.assertRaises(ImproperlyConfigured):
                _validate_rate_limits({"default": {"source": spec}})

    def test_rejects_non_positive_values(self):
        for spec in ((0, 60), (5, 0), (-1, 60)):
            with self.subTest(spec=spec), self.assertRaises(ImproperlyConfigured):
                _validate_rate_limits({"default": {"source": spec}})


class GetRateLimitsTests(SimpleTestCase):
    def test_class_defaults_are_used(self):
        self.assertEqual(
            rate_limit.get_rate_limits(CountingAction), {"source": (2, 3600)}
        )

    def test_default_entry_applies_to_every_action(self):
        with patch.object(rate_limit, "RATE_LIMITS", {"default": {"source": (9, 60)}}):
            self.assertEqual(
                rate_limit.get_rate_limits(CountingAction), {"source": (9, 60)}
            )

    def test_action_entry_wins_over_default(self):
        limits = {
            "default": {"source": (9, 60)},
            "CountingAction": {"source": (1, 30), "recipient": (2, 60)},
        }
        with patch.object(rate_limit, "RATE_LIMITS", limits):
            self.assertEqual(
                rate_limit.get_rate_limits(CountingAction),
                {"source": (1, 30), "recipient": (2, 60)},
            )

    def test_none_switches_a_limit_off(self):
        with patch.object(
            rate_limit, "RATE_LIMITS", {"CountingAction": {"source": None}}
        ):
            self.assertEqual(rate_limit.get_rate_limits(CountingAction), {})


class ConsumeQuotaTests(TestCase):
    def test_counts_up_to_the_limit(self):
        for _i in range(3):
            self.assertTrue(rate_limit.consume_quota("source", "1.2.3.4", 3, 60, NOW))
        self.assertFalse(rate_limit.consume_quota("source", "1.2.3.4", 3, 60, NOW))

    def test_values_are_counted_separately(self):
        self.assertTrue(rate_limit.consume_quota("source", "1.2.3.4", 1, 60, NOW))
        self.assertFalse(rate_limit.consume_quota("source", "1.2.3.4", 1, 60, NOW))
        self.assertTrue(rate_limit.consume_quota("source", "5.6.7.8", 1, 60, NOW))
        self.assertTrue(rate_limit.consume_quota("recipient", "1.2.3.4", 1, 60, NOW))

    def test_next_window_starts_over(self):
        self.assertTrue(rate_limit.consume_quota("source", "1.2.3.4", 1, 60, NOW))
        later = NOW + timedelta(seconds=61)
        self.assertTrue(rate_limit.consume_quota("source", "1.2.3.4", 1, 60, later))

    def test_key_does_not_contain_the_value(self):
        rate_limit.consume_quota("source", "1.2.3.4", 1, 60, NOW)
        key = SubmissionQuota.objects.get().key
        self.assertNotIn("1.2.3.4", key)
        self.assertEqual(len(key), 64)

    def test_expired_counters_are_pruned(self):
        rate_limit.consume_quota("source", "1.2.3.4", 1, 60, NOW)
        rate_limit.prune_expired(NOW + timedelta(seconds=62))
        self.assertFalse(SubmissionQuota.objects.exists())


@override_settings(USE_TZ=False)
class NaiveDatetimeQuotaTests(TestCase):
    """Projects may run without timezone support - Django 4.2 does so by default.

    SQLite refuses to store timezone-aware datetimes then, so the counters have
    to follow whatever ``USE_TZ`` demands.
    """

    def test_counters_work_without_timezone_support(self):
        now = timezone.now()
        self.assertIsNone(now.tzinfo)

        self.assertTrue(rate_limit.consume_quota("source", "1.2.3.4", 1, 60, now))
        self.assertFalse(rate_limit.consume_quota("source", "1.2.3.4", 1, 60, now))

        self.assertIsNone(SubmissionQuota.objects.get().expires_at.tzinfo)
        rate_limit.prune_expired(now + timedelta(seconds=62))
        self.assertFalse(SubmissionQuota.objects.exists())

    def test_action_is_rate_limited_without_timezone_support(self):
        request = RequestFactory().post("/")
        action = CountingAction()

        self.assertTrue(action.check_rate_limits(None, request))
        self.assertTrue(action.check_rate_limits(None, request))
        with self.assertLogs("djangocms_form_builder.rate_limit", "WARNING"):
            self.assertFalse(action.check_rate_limits(None, request))


class CheckRateLimitsTests(CMSTestCase):
    def setUp(self):
        super().setUp()
        self.request = self.get_request("/")
        self.request.user = AnonymousUser()
        self.form = object()

    def test_without_limits_the_action_runs(self):
        class UnlimitedAction(CountingAction):
            rate_limits = {}

        self.assertTrue(UnlimitedAction().check_rate_limits(self.form, self.request))
        self.assertFalse(SubmissionQuota.objects.exists())

    def test_limit_is_consumed_and_then_blocks(self):
        action = CountingAction()
        self.assertTrue(action.check_rate_limits(self.form, self.request))
        self.assertTrue(action.check_rate_limits(self.form, self.request))
        with self.assertLogs("djangocms_form_builder.rate_limit", "WARNING") as logs:
            self.assertFalse(action.check_rate_limits(self.form, self.request))
        self.assertIn("source rate limit reached", logs.output[0])

    def test_unknown_kinds_are_not_rate_limited(self):
        with patch.object(
            rate_limit,
            "RATE_LIMITS",
            {"CountingAction": {"source": None, "recipient": (1, 60)}},
        ):
            action = CountingAction()
            for _i in range(3):
                self.assertTrue(action.check_rate_limits(self.form, self.request))
        self.assertFalse(SubmissionQuota.objects.exists())

    def test_missing_value_fails_closed(self):
        self.request.META.pop("REMOTE_ADDR", None)
        with self.assertLogs("djangocms_form_builder.rate_limit", "WARNING") as logs:
            self.assertFalse(
                CountingAction().check_rate_limits(self.form, self.request)
            )
        self.assertIn("no source to check", logs.output[0])

    def test_database_error_fails_closed(self):
        with (
            patch.object(
                rate_limit, "consume_quota", side_effect=OSError("database is gone")
            ),
            self.assertLogs("djangocms_form_builder.rate_limit", "ERROR") as logs,
        ):
            self.assertFalse(
                CountingAction().check_rate_limits(self.form, self.request)
            )
        self.assertIn("rate limit check failed", logs.output[0])


class RateLimitedSubmissionTests(CMSTestCase):
    """Every action is rate limited by the form's save(), not by itself."""

    def setUp(self):
        super().setUp()
        CountingAction.calls = 0
        actions_module.register(CountingAction)
        self.addCleanup(actions_module.unregister, CountingAction)
        self.action_hash = actions_module.get_hash(CountingAction)
        self.request = self.get_request("/")
        self.request.user = AnonymousUser()

    def _submit(self):
        form_class = type(
            "RateLimitedForm",
            (SimpleFrontendForm,),
            {
                "Meta": type(
                    "Meta",
                    (),
                    {
                        "options": {
                            "form_name": "counting",
                            "form_actions": [self.action_hash],
                        }
                    },
                )
            },
        )
        form = form_class(data={}, request=self.request)
        self.assertTrue(form.is_valid())
        return form.save()

    def test_action_is_skipped_once_its_limit_is_used_up(self):
        self.assertEqual(self._submit()[self.action_hash], "executed")
        self.assertEqual(self._submit()[self.action_hash], "executed")
        with self.assertLogs("djangocms_form_builder.rate_limit", "WARNING"):
            self.assertEqual(
                str(self._submit()[self.action_hash]), "Rate limit reached"
            )
        self.assertEqual(CountingAction.calls, 2)
