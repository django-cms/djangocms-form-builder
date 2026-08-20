Management commands
###################

``prune_form_entries``
======================

Deletes form entries that have not been updated for a given number of days. Use
it to enforce a retention policy for the personal data collected through forms,
see :doc:`../how-to/prune-form-entries`.

.. code-block:: bash

   python manage.py prune_form_entries --days 90 [--form-name NAME] [--dry-run]

``--days DAYS``
   Required. Deletes entries whose ``entry_updated_at`` is older than ``DAYS``
   days. A negative value raises a ``CommandError``.

``--form-name NAME``
   Only delete entries of the form with this identifier.

``--dry-run``
   Only report how many entries would be deleted.

Deleting an entry also deletes the files it references through the configured
storage backend.
