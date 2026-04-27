#######################
 File upload validation
#######################

The **File upload** and **Multiple file upload** form field plugins optionally run
validation logic defined in your Django project settings. Each preset is a named
entry that points to a **function**.

What is included in this package
================================

* Running zero or more presets in order.
* :exc:`djangocms_form_builder.file_validation.FileValidationError` for rejecting an
  upload from inside a preset.
* Optional helper functions in ``djangocms_form_builder.file_validation_validators``.

If no preset is selected in the plugin admin, or the preset list is empty, no preset
validation runs. Django global upload limits still apply.

Django upload limits (separate from presets)
============================================

These are standard Django settings and are not part of the preset system:

* ``DATA_UPLOAD_MAX_MEMORY_SIZE`` - total in-memory size for a request body.
* ``FILE_UPLOAD_MAX_MEMORY_SIZE`` - threshold before large files go to disk.
* ``DATA_UPLOAD_MAX_NUMBER_FIELDS`` - maximum number of POST parameters (including
  file parts in multipart requests).

See the `Django file upload documentation
<https://docs.djangoproject.com/en/stable/topics/http/file-uploads/>`_.

Settings
========

``DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS``
   Maps preset keys (stored in plugin ``config``) to:

   * ``label`` - short text shown in plugin admin.
   * ``validate`` - dotted import path to a function.
   * ``filer_validator`` - optional boolean. If ``True``, ``validate`` must follow
     django-filer signature (see below).
   * ``validate_options`` - optional dict passed as keyword arguments to
     ``validate``. For filer presets, it is used by the adapter options
     (for example ``mime_source``).
   * ``accept_extensions`` - optional list of extensions used to set HTML
     ``accept`` on file inputs (for example ``[".pdf", "png"]``).

Example with a regular preset function::

    DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS = {
        "custom": {
            "label": _("Custom check"),
            "validate": "myapp.upload_rules.my_preset",
        },
    }

Example with ``accept_extensions`` metadata::

    DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS = {
        "documents": {
            "label": _("Documents"),
            "validate": "myapp.upload_rules.validate_documents",
            "accept_extensions": [".pdf", ".docx"],
        },
    }

.. _filer-style-presets:

django-filer compatible presets
===============================

If you already have a validator written for `django-filer
<https://github.com/django-cms/django-filer>`_ (or the same calling convention), set
``"filer_validator": True`` on the preset. The runner wraps it so you do not need to
change existing code. This package does not depend on django-filer.

Filer-style functions are called as::

    def my_filer_check(file_name, file, owner, mime_type):
        ...

Optional ``validate_options`` for filer presets:

* ``mime_source`` - how ``mime_type`` is built:

  * ``auto`` (default) - use ``uploaded_file.content_type`` if available, else guess
    from filename, else ``application/octet-stream``.
  * ``guess`` - ignore ``content_type`` and use ``mimetypes.guess_type``.
  * ``content_type`` - use ``content_type`` only; if empty, fallback to
    ``application/octet-stream``.

Non-:class:`~django.core.exceptions.ValidationError` exceptions raised by filer-style
functions are wrapped in
:exc:`~djangocms_form_builder.file_validation.FileValidationError`.

Preset callable contract
========================

Functions are called as::

    def my_preset(uploaded_file, *, user, request, field_name):
        ...

* ``uploaded_file`` - ``UploadedFile``.
* ``user`` - ``request.user`` when available, else ``None``.
* ``request`` - ``HttpRequest`` or ``None``.
* ``field_name`` - internal field name.

Raise :exc:`djangocms_form_builder.file_validation.FileValidationError` (or Django
``ValidationError``) to reject uploads.

Built-in helper functions
=========================

Module: ``djangocms_form_builder.file_validation_validators``.

These helpers perform checks and can be composed in your own preset function:

* ``enforce_max_size(uploaded_file, max_bytes, *, field_name="")``
* ``enforce_extension(uploaded_file, allowed_extensions, *, field_name="")``
* ``enforce_mime_from_filename(uploaded_file, allowed_patterns, *, field_name="")``

Example preset using helpers
============================

.. code-block:: python

    from djangocms_form_builder.file_validation_validators import (
        enforce_extension,
        enforce_max_size,
        enforce_mime_from_filename,
    )

    MAX_BYTES = 5 * 1024 * 1024

    def validate_documents(uploaded_file, *, user, request, field_name):
        enforce_max_size(uploaded_file, MAX_BYTES, field_name=field_name)
        enforce_extension(
            uploaded_file,
            [".pdf", ".png", ".jpg", ".jpeg"],
            field_name=field_name,
        )
        enforce_mime_from_filename(
            uploaded_file,
            ["application/pdf", "image/"],
            field_name=field_name,
        )

Saving uploads ("Save form submission" action)
==============================================

AJAX forms send data with ``multipart/form-data`` so files reach Django; preset
validation runs server-side before final cleaned data is used.

The **Save form submission** action stores ``entry_data`` as JSON. Uploaded files are
written to ``default_storage`` under ``form_uploads/...``, and each file field becomes
a dict with ``_form_builder_file``, ``filename``, and ``url``.

Plugin admin
============

Presets run in order for each file:

* single-file field: one file
* multiple-file field: each uploaded file in the batch

Presets are stored in ``config`` as ``field_file_validation_presets``.
