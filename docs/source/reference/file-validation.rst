File upload validation
######################

Uploads accepted by the **File upload** and **Multiple file upload** plugins are
checked by *presets*: named rules your project defines in its settings and
editors select per field. For a task-oriented introduction see
:doc:`../how-to/handle-file-uploads`.

The preset registry
===================

``DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS`` maps a key - the value stored
in the plugin's ``config["field_file_validation_presets"]`` - to a dictionary:

``label``
   Short text shown in the plugin's *Validation presets* choices.

``validate``
   Dotted import path of a function. Resolving to a class raises
   ``ImproperlyConfigured``.

``filer_validator``
   Optional boolean. If ``True``, ``validate`` is expected to follow the
   django-filer signature and is wrapped, see below.

``validate_options``
   Optional dictionary passed to ``validate`` as keyword arguments. For filer
   presets it configures the adapter instead (currently ``mime_source``).

``accept_extensions``
   Optional list of extensions (``".pdf"`` or ``"pdf"``) used to build the HTML
   ``accept`` attribute of the file input. If several selected presets carry the
   list, their intersection is used. It is a hint for the file dialog, not a
   check.

The registry is read on each use, so it may be changed with
``override_settings`` in tests.

The preset callable
===================

.. code-block:: python

   def my_preset(uploaded_file, *, user, request, field_name):
       ...

``uploaded_file``
   The ``UploadedFile``.

``user``
   ``request.user`` when available, else ``None``.

``request``
   The ``HttpRequest``, or ``None``.

``field_name``
   The internal name of the field being validated.

Raise ``djangocms_form_builder.file_validation.FileValidationError`` (a subclass
of Django's ``ValidationError``) to reject the file. Presets of a field run in
the order they are selected, and for a multiple upload once per file. The runner
rewinds the file with ``seek(0)`` after every preset.

A preset key that is not in the registry raises ``ImproperlyConfigured``. The
form field turns that into the visitor-facing message *This field could not be
validated. Contact the site administrator.* and logs the exception to the
``djangocms_form_builder.upload_form_fields`` logger.

django-filer style validators
=============================

With ``"filer_validator": True`` the function is called the way django-filer
calls its validators:

.. code-block:: python

   def my_filer_check(file_name, file, owner, mime_type):
       ...

Exceptions other than ``ValidationError`` are wrapped in
``FileValidationError``. This package does not depend on django-filer.

``validate_options["mime_source"]`` decides how ``mime_type`` is built:

``"auto"`` (default)
   ``uploaded_file.content_type`` if it is non-empty, else a guess from the file
   name, else ``application/octet-stream``.

``"guess"``
   Ignore ``content_type`` and use ``mimetypes.guess_type()`` only.

``"content_type"``
   Use ``content_type`` only, falling back to ``application/octet-stream``.

Built-in helpers
================

``djangocms_form_builder.file_validation_validators`` provides checks to compose
your presets from. Each raises ``FileValidationError`` with a translated
message.

``enforce_max_size(uploaded_file, max_bytes, *, field_name="")``
   Rejects a file larger than ``max_bytes``. Files without a known size pass.

``enforce_extension(uploaded_file, allowed_extensions, *, field_name="")``
   Rejects a file whose name does not end in one of the extensions. Leading dots
   are optional and case is ignored.

``enforce_mime_from_filename(uploaded_file, allowed_patterns, *, field_name="")``
   Guesses the MIME type from the file name and rejects it unless it matches one
   of the patterns. A pattern is either a full type (``"application/pdf"``) or a
   prefix ending in a slash (``"image/"``). A name whose type cannot be guessed
   is rejected.

Field classes
=============

``djangocms_form_builder.upload_form_fields`` holds the two form fields the
upload plugins build:

``ValidatedFileField``
   A ``FileField`` that runs the presets in ``clean()``.

``MultipleUploadedFilesField``
   Accepts a list of files, enforces the plugin's *Max files* limit and collects
   the errors of all rejected files, so a visitor sees every problem at once.

Both set the ``accept`` attribute on their widget when the selected presets
provide ``accept_extensions``.
