from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from djangocms_form_builder.entry_model import FormEntry


class Command(BaseCommand):
    help = (
        "Delete form entries that have not been updated for a given number of "
        "days. Use this to enforce a retention policy for personal data "
        "collected through forms."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            required=True,
            help="Delete entries last updated more than DAYS days ago.",
        )
        parser.add_argument(
            "--form-name",
            default=None,
            help="Only delete entries submitted to the form with this name.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only report how many entries would be deleted.",
        )

    def handle(self, *args, **options):
        days = options["days"]
        if days < 0:
            raise CommandError("--days must not be negative.")
        cutoff = timezone.now() - timedelta(days=days)
        entries = FormEntry.objects.filter(entry_updated_at__lt=cutoff)
        if options["form_name"]:
            entries = entries.filter(form_name=options["form_name"])
        count = entries.count()
        noun = "form entry" if count == 1 else "form entries"
        if options["dry_run"]:
            self.stdout.write(f"Would delete {count} {noun}.")
            return
        entries.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {count} {noun}."))
