Delete old submissions
######################

Submissions stored by the **Save form submission** action stay in the database
until something removes them. They regularly contain personal data, so decide
how long you need them and delete the rest.

The ``prune_form_entries`` management command deletes entries by age:

.. code-block:: bash

   python manage.py prune_form_entries --days 90

``--days`` is required and compares against the time an entry was last
*updated*, not created - reopening a unique form therefore restarts its
retention period.

Before deleting anything, check how much would go:

.. code-block:: bash

   python manage.py prune_form_entries --days 90 --dry-run

Restrict the command to a single form with its identifier:

.. code-block:: bash

   python manage.py prune_form_entries --days 90 --form-name contact

Deleting an entry also deletes the files uploaded with it through the configured
storage backend, so this is the way to expire attachments as well.

Run it regularly - from cron, from a scheduler, or from whatever runs periodic
jobs in your project.
