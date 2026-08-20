Accept file uploads
###################

Two field plugins accept files: **File upload** for a single file and
**Multiple file upload** for several at once. Both are added as children of the
form plugin like any other field.

Files are sent as ``multipart/form-data`` together with the rest of the
submission and validated server-side before any action runs.

Store uploads privately
=======================

.. warning::

   Uploaded files are written to
   ``django.core.files.storage.default_storage`` unless you configure a
   different backend. With the default storage anyone who knows or guesses a
   file's URL can download it - the random prefix in the stored file name makes
   guessing harder, not impossible.

Point the app at a private storage backend if forms may collect sensitive
attachments:

.. code-block:: python

   DJANGOCMS_FORM_BUILDER_FILE_FIELD_STORAGE = my_private_storage

The setting takes a storage *instance*. It is used for writing, for building
the URL that is stored with the entry, and for deleting files again.

Restrict what may be uploaded
=============================

Which files are acceptable is a project decision, so the rules live in your
settings and editors only pick one of them per field. A rule ("preset") points
at a function of yours:

.. code-block:: python

   DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS = {
       "documents": {
           "label": _("Documents"),
           "validate": "myapp.upload_rules.validate_documents",
           "accept_extensions": [".pdf", ".docx"],
       },
   }

Write the function with the signature the runner uses, and raise
``FileValidationError`` to reject a file. The helpers in
``djangocms_form_builder.file_validation_validators`` cover the common checks:

.. code-block:: python

   from djangocms_form_builder.file_validation_validators import (
       enforce_extension,
       enforce_max_size,
       enforce_mime_from_filename,
   )

   MAX_BYTES = 5 * 1024 * 1024


   def validate_documents(uploaded_file, *, user, request, field_name):
       enforce_max_size(uploaded_file, MAX_BYTES, field_name=field_name)
       enforce_extension(uploaded_file, [".pdf", ".docx"], field_name=field_name)
       enforce_mime_from_filename(
           uploaded_file,
           ["application/pdf", "application/vnd.openxmlformats-officedocument."],
           field_name=field_name,
       )

The preset now appears as **Validation presets** in the settings section of both
upload plugins. An editor can select several; they run in order, for every file
of a multiple upload. Selecting none means no preset validation runs - Django's
own upload limits still do.

``accept_extensions`` is used for the ``accept`` attribute of the file input,
which limits what the file dialog offers. It is a convenience for the visitor,
not a check: the presets are what actually rejects a file.

If you already have a validator written for `django-filer
<https://github.com/django-cms/django-filer>`_, set ``"filer_validator": True``
on the preset instead of rewriting it.

The full format of the preset registry, the calling conventions and the helper
signatures are described in :doc:`../reference/file-validation`.

Limit how many files a visitor may send
=======================================

The **Multiple file upload** plugin has a **Max files** setting (2 by default).
A submission with more files is rejected with a validation error.

This limit is about the field. The size of the request as a whole is governed by
Django's settings, which apply to all uploads regardless of any preset:

* ``DATA_UPLOAD_MAX_MEMORY_SIZE``
* ``FILE_UPLOAD_MAX_MEMORY_SIZE``
* ``DATA_UPLOAD_MAX_NUMBER_FIELDS``

See the `Django file upload documentation
<https://docs.djangoproject.com/en/stable/topics/http/file-uploads/>`_.

Know when files are deleted
===========================

Stored files belong to the form entry that references them, and the app cleans
up after itself:

* reopening a *unique* form and leaving an optional upload empty keeps the file
  that is already stored;
* replacing an upload deletes the previous file once the updated entry was
  saved;
* deleting an entry - by hand in the admin, or through
  ``prune_form_entries`` - deletes its files through the configured storage;
* if saving the entry fails, files written for that attempt are removed again,
  so a failed submission leaves no orphans behind.

Storage backends can fail at any of these points. Failures are logged to the
``djangocms_form_builder.form_entry_data`` logger rather than raised - make sure
your ``LOGGING`` configuration surfaces them, because an unreferenced file needs
manual cleanup.
