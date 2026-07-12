from datetime import timedelta
from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase
from django.utils import timezone

from djangocms_form_builder.entry_model import FormEntry


class PruneFormEntriesCommandTestCase(TestCase):
    def setUp(self):
        # auto_now is bypassed by queryset .update(), so entries can be
        # backdated after creation
        old_contact = FormEntry.objects.create(
            form_name="contact", entry_data={"field": "old"}
        )
        old_other = FormEntry.objects.create(
            form_name="other", entry_data={"field": "old"}
        )
        FormEntry.objects.filter(pk__in=[old_contact.pk, old_other.pk]).update(
            entry_updated_at=timezone.now() - timedelta(days=40)
        )
        FormEntry.objects.create(form_name="contact", entry_data={"field": "new"})

    def call(self, *args):
        out = StringIO()
        call_command("prune_form_entries", *args, stdout=out)
        return out.getvalue()

    def test_prune_deletes_old_entries_only(self):
        output = self.call("--days", "30")
        self.assertIn("Deleted 2 form entries.", output)
        self.assertEqual(FormEntry.objects.count(), 1)
        self.assertEqual(FormEntry.objects.get().entry_data, {"field": "new"})

    def test_dry_run_deletes_nothing(self):
        output = self.call("--days", "30", "--dry-run")
        self.assertIn("Would delete 2 form entries.", output)
        self.assertEqual(FormEntry.objects.count(), 3)

    def test_form_name_filter(self):
        output = self.call("--days", "30", "--form-name", "contact")
        self.assertIn("Deleted 1 form entry.", output)
        self.assertEqual(FormEntry.objects.count(), 2)
        self.assertFalse(
            FormEntry.objects.filter(
                form_name="contact", entry_data={"field": "old"}
            ).exists()
        )

    def test_negative_days_rejected(self):
        with self.assertRaises(CommandError):
            self.call("--days", "-1")
