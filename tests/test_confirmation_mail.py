import importlib
from threading import Event
from unittest.mock import patch

from cms.test_utils.testcases import CMSTestCase
from django import forms
from django.contrib.auth.models import AnonymousUser
from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from django.utils.safestring import mark_safe

from djangocms_form_builder import actions as actions_module
from djangocms_form_builder import confirmation_mail, recaptcha
from djangocms_form_builder import settings as settings_module
from djangocms_form_builder.actions import (
    SendConfirmationMailAction,
    get_registered_actions,
)
from djangocms_form_builder.settings import ALTCHA_FIELD_OPTIONS


def captcha_field():
    return recaptcha.ALTCHA_FIELD(**ALTCHA_FIELD_OPTIONS)


class FakeForm:
    """Stands in for the form a form plugin builds at submission time."""

    def __init__(self, fields=None, cleaned_data=None, options=None, protected=True):
        self.fields = dict(fields or {"email": forms.EmailField(label="Email")})
        if protected:
            self.fields[recaptcha.field_name] = captcha_field()
        self.cleaned_data = dict(
            cleaned_data if cleaned_data is not None else {"email": "guest@example.com"}
        )
        self.Meta = type(
            "Meta",
            (),
            {
                "options": {
                    "form_name": "contact",
                    "form_parameters": {"confirmationmail_template": "default"},
                    **(options or {}),
                }
            },
        )


class SyncExecutor:
    """Sends inline so that tests need not wait for the worker pool."""

    def __init__(self, accept=True):
        self.accept = accept

    def submit(self, message):
        if not self.accept:
            return False
        message.send(fail_silently=False)
        return True


class ConfirmationMailActionTests(CMSTestCase):
    def setUp(self):
        super().setUp()
        self.request = self.get_request("/")
        self.request.user = AnonymousUser()
        mail.outbox = []
        patcher = patch.object(
            confirmation_mail, "get_executor", return_value=SyncExecutor()
        )
        self.executor = patcher.start()
        self.addCleanup(patcher.stop)

    def execute(self, form=None):
        return SendConfirmationMailAction().execute(form or FakeForm(), self.request)

    def test_action_is_registered(self):
        self.assertIn(
            "Send confirmation email to submitter",
            dict(get_registered_actions()).values(),
        )

    def test_sends_mail_to_the_submitted_address(self):
        self.assertEqual(self.execute(), 1)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["guest@example.com"])
        self.assertEqual(message.from_email, "noreply@example.com")
        self.assertEqual(message.subject, "Thank you for contact")
        self.assertIn("Thank you for your submission.", message.body)
        self.assertEqual(message.extra_headers["Auto-Submitted"], "auto-generated")
        self.assertEqual(message.extra_headers["X-Auto-Response-Suppress"], "All")
        self.assertEqual(
            [content_type for _content, content_type in message.alternatives],
            ["text/html"],
        )

    def test_subject_is_reduced_to_a_single_line(self):
        form = FakeForm(
            options={"form_parameters": {"confirmationmail_template": "second"}}
        )
        self.assertEqual(self.execute(form), 1)
        self.assertEqual(mail.outbox[0].subject, "Second subject for contact")

    def test_text_body_falls_back_to_the_html_body(self):
        form = FakeForm(
            options={"form_parameters": {"confirmationmail_template": "second"}}
        )
        self.assertEqual(self.execute(form), 1)
        self.assertEqual(
            mail.outbox[0].body.strip(), "HTML only body for guest@example.com"
        )

    def test_skipped_without_an_email_field(self):
        form = FakeForm(
            fields={"name": forms.CharField(label="Name")},
            cleaned_data={"name": "guest@example.com"},
        )
        with self.assertLogs("djangocms_form_builder.actions", "WARNING") as logs:
            self.assertEqual(self.execute(form), 0)
        self.assertIn("no valid email field", logs.output[0])
        self.assertEqual(mail.outbox, [])

    def test_skipped_when_a_plain_field_is_named_email(self):
        form = FakeForm(fields={"email": forms.CharField(label="Email")})
        with self.assertLogs("djangocms_form_builder.actions", "WARNING"):
            self.assertEqual(self.execute(form), 0)
        self.assertEqual(mail.outbox, [])

    def test_skipped_for_an_invalid_address(self):
        form = FakeForm(cleaned_data={"email": "not-an-address"})
        with self.assertLogs("djangocms_form_builder.actions", "WARNING"):
            self.assertEqual(self.execute(form), 0)
        self.assertEqual(mail.outbox, [])

    def test_skipped_for_an_unprotected_form(self):
        form = FakeForm(protected=False)
        with self.assertLogs("djangocms_form_builder.actions", "WARNING") as logs:
            self.assertEqual(self.execute(form), 0)
        self.assertIn("neither login nor a captcha", logs.output[0])
        self.assertEqual(mail.outbox, [])

    def test_skipped_when_a_plain_field_is_named_captcha_field(self):
        form = FakeForm(protected=False)
        form.fields[recaptcha.field_name] = forms.CharField()
        with self.assertLogs("djangocms_form_builder.actions", "WARNING"):
            self.assertEqual(self.execute(form), 0)

    def test_login_required_forms_need_no_captcha(self):
        form = FakeForm(protected=False, options={"login_required": True})
        self.assertEqual(self.execute(form), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_skipped_for_an_unknown_template_set(self):
        form = FakeForm(
            options={"form_parameters": {"confirmationmail_template": "../secrets"}}
        )
        with self.assertLogs("djangocms_form_builder.actions", "ERROR") as logs:
            self.assertEqual(self.execute(form), 0)
        self.assertIn("unknown template set", logs.output[0])
        self.assertEqual(mail.outbox, [])

    def test_skipped_when_the_queue_is_full(self):
        self.executor.return_value = SyncExecutor(accept=False)
        with self.assertLogs("djangocms_form_builder.actions", "WARNING") as logs:
            self.assertEqual(self.execute(), 0)
        self.assertIn("delivery queue is full", logs.output[0])

    def test_rate_limits_the_recipient(self):
        for _i in range(3):
            self.assertTrue(
                SendConfirmationMailAction().check_rate_limits(FakeForm(), self.request)
            )
        with self.assertLogs("djangocms_form_builder.rate_limit", "WARNING") as logs:
            self.assertFalse(
                SendConfirmationMailAction().check_rate_limits(FakeForm(), self.request)
            )
        self.assertIn("recipient rate limit reached", logs.output[0])

    def test_rate_limit_values_omit_a_missing_recipient(self):
        values = SendConfirmationMailAction().get_rate_limit_values(
            FakeForm(cleaned_data={}), self.request
        )
        self.assertEqual(values, {"source": "127.0.0.1"})

    def test_rate_limit_values_ignore_the_address_case(self):
        values = SendConfirmationMailAction().get_rate_limit_values(
            FakeForm(cleaned_data={"email": "Guest@Example.COM"}), self.request
        )
        self.assertEqual(values["recipient"], "guest@example.com")


class ConfirmationMailContextTests(SimpleTestCase):
    def test_captcha_and_uploads_are_left_out(self):
        form = FakeForm(
            fields={
                "email": forms.EmailField(label="Email"),
                "attachment": forms.FileField(label="Attachment"),
            },
            cleaned_data={
                "email": "guest@example.com",
                "attachment": SimpleUploadedFile("cv.pdf", b"%PDF-"),
            },
        )
        context = confirmation_mail.get_context(form)

        self.assertEqual(list(context["form_fields"]), ["email"])
        self.assertEqual(context["form_name"], "contact")
        self.assertEqual(
            context["form_field_rows"],
            [{"name": "email", "label": "Email", "value": "guest@example.com"}],
        )

    def test_values_are_bounded_and_no_longer_marked_safe(self):
        form = FakeForm(
            fields={"message": forms.CharField(label="Message")},
            cleaned_data={"message": mark_safe("<b>x</b>" + "y" * 5000)},
        )
        value = confirmation_mail.get_context(form)["form_fields"]["message"]

        self.assertEqual(len(value), confirmation_mail.MAX_CONTEXT_VALUE_LENGTH)
        self.assertNotIsInstance(value, type(mark_safe("")))

    def test_multiple_choices_are_kept(self):
        form = FakeForm(
            fields={"topics": forms.MultipleChoiceField(label="Topics")},
            cleaned_data={"topics": ["a", "b"]},
        )
        self.assertEqual(
            confirmation_mail.get_context(form)["form_fields"]["topics"], ("a", "b")
        )

    def test_none_becomes_an_empty_string(self):
        form = FakeForm(
            fields={"note": forms.CharField(label="Note")}, cleaned_data={"note": None}
        )
        self.assertEqual(confirmation_mail.get_context(form)["form_fields"]["note"], "")


class ConfirmationMailExecutorTests(SimpleTestCase):
    def setUp(self):
        super().setUp()
        confirmation_mail._executor = None
        self.addCleanup(setattr, confirmation_mail, "_executor", None)

    def test_pending_messages_are_capped(self):
        executor = confirmation_mail._BoundedMailExecutor(max_workers=1, max_pending=1)
        self.addCleanup(executor.shutdown)
        release = Event()
        blocked = mail.EmailMultiAlternatives(to=["guest@example.com"])
        extra = mail.EmailMultiAlternatives(to=["other@example.com"])
        with patch.object(blocked, "send", side_effect=lambda **kw: release.wait(5)):
            self.assertTrue(executor.submit(blocked))
            # The single slot stays taken until the first message has been sent.
            self.assertFalse(executor.submit(extra))
            release.set()
            executor.shutdown(wait=True)
        # ... and is available again afterwards.
        self.assertTrue(executor._slots.acquire(blocking=False))

    def test_dispatch_survives_a_broken_executor(self):
        with (
            patch.object(
                confirmation_mail, "get_executor", side_effect=OSError("no threads")
            ),
            self.assertLogs(
                "djangocms_form_builder.confirmation_mail", "ERROR"
            ) as logs,
        ):
            self.assertFalse(confirmation_mail.dispatch(object()))
        self.assertIn("Failed to enqueue", logs.output[0])

    def test_send_failures_are_logged_not_raised(self):
        executor = confirmation_mail._BoundedMailExecutor(max_workers=1, max_pending=1)
        self.addCleanup(executor.shutdown)
        message = mail.EmailMultiAlternatives(to=["guest@example.com"])
        with (
            patch.object(message, "send", side_effect=OSError("smtp is down")),
            self.assertLogs(
                "djangocms_form_builder.confirmation_mail", "ERROR"
            ) as logs,
        ):
            executor.submit(message)
            executor.shutdown(wait=True)
        self.assertIn("Failed to send form confirmation mail", logs.output[0])

    @override_settings(DJANGOCMS_CONFIRMATION_MAIL_WORKERS=0)
    def test_invalid_worker_count_is_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            confirmation_mail.get_executor()


class ConfirmationMailConfigurationTests(SimpleTestCase):
    """Without configured template sets the action must not show up at all."""

    def setUp(self):
        super().setUp()
        registry = actions_module._action_registry
        self.addCleanup(self._reload, dict(registry))

    @staticmethod
    def _reload(registry=None):
        importlib.reload(settings_module)
        importlib.reload(confirmation_mail)
        importlib.reload(actions_module)
        if registry is not None:
            actions_module._action_registry.clear()
            actions_module._action_registry.update(registry)

    @override_settings(DJANGOCMS_CONFIRMATION_MAIL_TEMPLATE_SETS=())
    def test_action_is_not_registered_without_template_sets(self):
        self._reload()

        self.assertFalse(settings_module.CONFIRMATION_MAIL_TEMPLATE_SETS)
        self.assertNotIn(
            "Send confirmation email to submitter",
            dict(actions_module.get_registered_actions()).values(),
        )

    @override_settings(
        DJANGOCMS_CONFIRMATION_MAIL_TEMPLATE_SETS=(("../etc", "Escaping key"),)
    )
    def test_template_set_keys_must_be_slugs(self):
        with self.assertRaises(ImproperlyConfigured):
            importlib.reload(settings_module)

    @override_settings(
        DJANGOCMS_CONFIRMATION_MAIL_TEMPLATE_SETS=(("only", "Only one"),)
    )
    def test_single_template_set_is_not_offered_for_selection(self):
        self._reload()

        field = actions_module.SendConfirmationMailAction.declared_fields[
            "confirmationmail_template"
        ]
        self.assertIsInstance(field.widget, forms.HiddenInput)
        self.assertEqual(field.initial, "only")

    def test_several_template_sets_are_offered_for_selection(self):
        field = SendConfirmationMailAction.declared_fields["confirmationmail_template"]
        self.assertIsInstance(field.widget, forms.Select)
        self.assertEqual(
            [key for key, verbose_name in field.choices], ["default", "second"]
        )
