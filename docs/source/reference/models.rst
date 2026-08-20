Models and stored data
######################

``FormEntry``
=============

``djangocms_form_builder.models.FormEntry`` (defined in ``entry_model.py``)
holds one submission stored by the *Save form submission* action.

``form_name``
   Slug of the form the submission belongs to - the form plugin's *Form
   identifier*.

``form_user``
   The submitting user, or ``NULL`` for anonymous submissions. Deleting the user
   deletes their entries.

``entry_data``
   JSON object mapping field name to submitted value.

``html_headers``
   JSON object, kept for backwards compatibility. It is no longer written to.

``entry_created_at``, ``entry_updated_at``
   Timestamps. ``entry_updated_at`` is what ``prune_form_entries`` compares
   against.

Deleting an entry - individually or through a queryset - deletes the files it
references through the configured storage backend.

Uploaded files in ``entry_data``
--------------------------------

A file field is stored as a dictionary, a multiple file field as a list of
them:

.. code-block:: json

   {
     "attachment": {
       "_form_builder_file": true,
       "filename": "order.pdf",
       "name": "form_uploads/6f1b…_order.pdf",
       "url": "/media/form_uploads/6f1b…_order.pdf"
     }
   }

``_form_builder_file``
   Marks the value as a stored file. This is how the admin, the mail templates
   and the cleanup code recognise uploads.

``filename``
   The name the visitor's file had.

``name``
   The path in the storage backend, used to delete the file again.

``url``
   The URL the storage backend produced when the file was saved.

Helper methods:

``get_file_entry_items(value)`` (static)
   Normalises a value into a list of file dictionaries, empty for anything else.

``get_file_entry_data_keys()``
   The keys of ``entry_data`` that hold uploads.

``get_mail_data()``
   The entry as a list of ``{"label", "value"}`` - or ``{"label", "files"}`` for
   uploads - as used by the mail templates.

   .. warning::

      Only a *list* of files is handled. An entry holding a single **File
      upload** raises ``TypeError`` here, which breaks the *Send email* action
      for such forms.

``get_admin_form()``, ``get_admin_fieldsets()``
   Build the admin form for this particular entry. Strings, lists, booleans,
   integers and decimals become editable fields; uploads are shown as links
   only and preserved when the entry is saved.

In the admin
------------

Form entries are listed under **Form builder** in the Django admin, filterable
by form, user and date. Entries cannot be created by hand, and ``form_name`` and
``form_user`` are read-only.

``SubmissionQuota``
===================

``djangocms_form_builder.models.SubmissionQuota`` (defined in
``rate_limit.py``) backs the rate limits.

``key``
   Primary key: an HMAC of quota kind, time bucket and the counted value under
   the project's ``SECRET_KEY``. Neither IP addresses nor mail addresses are
   stored.

``count``
   Uses within the current window.

``expires_at``
   End of the window. Rows past it are deleted as new submissions arrive.

Plugin models
=============

``Form``
   The form plugin's model. Its editor-facing fields are listed in
   :doc:`plugins`; ``action_parameters`` is a JSON field holding the values of
   all action fields, and ``form_actions`` holds the list of selected action
   hashes.

``FormField``
   One model for all field plugins, with the plugin type in ``ui_item`` and
   everything else in the JSON field ``config``. Configuration keys are readable
   as attributes: ``instance.field_label`` returns ``config["field_label"]``.

   The concrete field plugins (``CharField``, ``EmailField``, ``Select``,
   ``FileField``, …) are proxy models of it. Each implements
   ``get_form_field(request=None)``, returning the field name and a Django form
   field. Custom field plugins do the same.
