# original from
# http://tech.octopus.energy/news/2016/01/21/testing-for-missing-migrations-in-django.html
import os
import subprocess
import sys
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase, override_settings


class MigrationTestCase(TestCase):
    @override_settings(MIGRATION_MODULES={})
    def test_for_missing_migrations(self):
        output = StringIO()
        options = {
            "interactive": False,
            "dry_run": True,
            "stdout": output,
            "check_changes": True,
        }

        try:
            call_command("makemigrations", "djangocms_form_builder", **options)
        except SystemExit as e:
            status_code = str(e)
        else:
            # the "no changes" exit code is 0
            status_code = "0"

        if status_code == "1":
            self.fail(f"There are missing migrations:\n {output.getvalue()}")

    def test_for_missing_migrations_in_other_language(self):
        """Strings evaluated at import time (non-lazy gettext, ``.format()`` on a
        lazy string) end up translated in the model state. Import the models in a
        fresh process with a non-English LANGUAGE_CODE to catch them."""
        script = (
            "import django\n"
            "from django.conf import settings\n"
            "settings.LANGUAGE_CODE = 'nl'\n"
            "settings.MIGRATION_MODULES = {}\n"
            "django.setup()\n"
            "from django.core.management import call_command\n"
            "call_command('makemigrations', 'djangocms_form_builder', "
            "check_changes=True, dry_run=True, interactive=False)\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=Path(__file__).resolve().parent.parent,
            env={**os.environ, "DJANGO_SETTINGS_MODULE": "tests.test_settings"},
            capture_output=True,
            text=True,
        )
        if result.returncode:
            self.fail(f"There are missing migrations:\n {result.stdout}{result.stderr}")
