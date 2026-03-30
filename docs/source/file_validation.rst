#######################
 File upload validation
#######################

The **File upload** and **Multiple file upload** form field plugins optionally run
validation logic defined in your Django project settings. Each *preset* is a named
entry that points to a **function** or a **class** (see below).

What is included in this package
================================

* Running zero or more **presets** in order.
* :exc:`djangocms_form_builder.file_validation.FileValidationError` for rejecting an
  upload from inside a preset.
* **Optional helpers** in ``djangocms_form_builder.file_validation_validators``:
  small functions you call from your own code, and preset classes you can register
  directly or subclass.

**Not** included: virus scanning or content-based MIME detection — use your own preset
or an external library if you need that.

If no preset is selected in the plugin admin, or the preset list is empty, **no preset
validation runs**. Django’s global upload limits still apply (see below).

Django upload limits (separate from presets)
============================================

These are standard Django settings; they are **not** part of the preset system:

* ``DATA_UPLOAD_MAX_MEMORY_SIZE`` — total in-memory size for a request body.
* ``FILE_UPLOAD_MAX_MEMORY_SIZE`` — threshold before large files go to disk.
* ``DATA_UPLOAD_MAX_NUMBER_FIELDS`` — maximum number of POST parameters (including
  file parts in multipart requests).

See the `Django file upload documentation
<https://docs.djangoproject.com/en/stable/topics/http/file-uploads/>`_.

Settings
========

``DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS``
   Maps preset keys (stored in the plugin ``config`` JSON) to:

   * ``label`` — short text in the plugin admin (can use ``gettext_lazy``).
   * ``validate`` — dotted import path to a **function** or **class**.
   * ``validate_options`` — optional dict. When ``validate`` is a **class**, passed as
     ``Class(**validate_options)``. When ``filer_validator`` is true, optional keys such
     as ``mime_source`` apply (see :ref:`filer-style-presets`); they are not used for
     class construction.
   * ``filer_validator`` — if ``True``, ``validate`` must be a **function** using the
     django-filer-style signature (see :ref:`filer-style-presets`).

Example with a **function** preset::

    DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS = {
        "custom": {
            "label": _("Custom check"),
            "validate": "myapp.upload_rules.my_preset",
        },
    }

Example with a **bundled class** and options::

    DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS = {
        "max_2mb": {
            "label": _("Maximum 2 MiB"),
            "validate": (
                "djangocms_form_builder.file_validation_validators.MaxSizePresetValidator"
            ),
            "validate_options": {"max_bytes": 2 * 1024 * 1024},
        },
    }

.. _filer-style-presets:

django-filer compatibles presets
================================

If you already have a validator written for `django-filer
<https://github.com/django-cms/django-filer>`_ (or the same calling convention), set
``"filer_validator": True`` on the preset. The runner wraps it so you do **not** need
to change the validator’s code. This package does **not** depend on django-filer; only
your project needs it if you import filer modules.

Filer-style functions are called as::

    def my_filer_check(file_name, file, owner, mime_type):
        ...

where ``file`` is a readable file-like object (an ``UploadedFile`` works), ``owner`` is
the user (same as ``user`` in the form builder contract), and ``mime_type`` is chosen
by the adapter (see below).

Example (SVG checks from filer, when django-filer is installed in your project)::

    DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS = {
        "svg_security": {
            "label": _("SVG security (filer)"),
            "validate": "filer.validation.validate_svg",
            "filer_validator": True,
        },
    }

Use ``filer.validation.sanitize_svg`` in a separate preset when you need to ensure the
upload is a valid SVG (svglib), while ``validate_svg`` focuses on XSS patterns in the
bytes.

Optional ``validate_options`` for these presets:

* ``mime_source`` — how to obtain ``mime_type`` passed to the validator:

  * ``auto`` (default) — use ``uploaded_file.content_type`` if non-empty, else guess
    from the filename, else ``application/octet-stream``.
  * ``guess`` — ignore ``content_type``; use :func:`mimetypes.guess_type` only.
  * ``content_type`` — use ``content_type`` only; if empty, use
    ``application/octet-stream``.

Non-:class:`~django.core.exceptions.ValidationError` exceptions raised inside the filer
function are wrapped in :exc:`~djangocms_form_builder.file_validation.FileValidationError`
so the message still appears on the form.

``filer_validator`` must not be combined with a **class** in ``validate``; that
configuration raises ``ImproperlyConfigured``.

Preset callable contract
========================

**Functions** are called as::

    def my_preset(uploaded_file, *, user, request, field_name):
        ...

**Class instances** (including bundled validators) are called the same way; implement
or reuse :class:`djangocms_form_builder.file_validation_validators.BaseFilePresetValidator`.

* ``uploaded_file`` — ``UploadedFile``; the runner calls ``seek(0)`` after each preset.
* ``user`` — ``request.user`` when the form has a request, else ``None``.
* ``request`` — ``HttpRequest`` or ``None``.
* ``field_name`` — internal field name.

Raise :exc:`djangocms_form_builder.file_validation.FileValidationError` (or Django’s
``ValidationError``) to reject the upload.

Built-in helpers
================

Module: ``djangocms_form_builder.file_validation_validators``.

Functions (use inside your own presets)
---------------------------------------

These only perform checks; they do **not** register a preset by themselves.

.. list-table::
   :header-rows: 1
   :widths: 28 72

   * - Name
     - Behaviour
   * - ``enforce_max_size(uploaded_file, max_bytes, *, field_name="")``
     - Raises if ``uploaded_file.size`` is greater than ``max_bytes``. If ``size`` is
       missing, the check is skipped.
   * - ``enforce_extension(uploaded_file, allowed_extensions, *, field_name="")``
     - ``allowed_extensions`` is an iterable of suffixes, with or without a leading dot
       (e.g. ``".pdf"`` or ``"pdf"``). Normalised to lowercase; rejects unknown suffix.
   * - ``enforce_mime_from_filename(uploaded_file, allowed_patterns, *, field_name="")``
     - Uses ``mimetypes.guess_type`` on the **filename** (not file contents). If
       ``allowed_patterns`` is empty, returns without checking. Otherwise each pattern
       is either a full MIME type (exact match) or a prefix ending with ``"/"``
       (e.g. ``"image/"`` matches ``image/png``). Rejects if the type cannot be guessed
       or matches no pattern.

Classes (register as ``validate``, or subclass)
-----------------------------------------------

All inherit from
:class:`djangocms_form_builder.file_validation_validators.BaseFilePresetValidator`
and implement the same behaviour as the corresponding helper when instantiated with the
shown ``validate_options`` keys:

.. list-table::
   :header-rows: 1
   :widths: 30 40 30

   * - Class
     - ``validate_options`` keys
     - Same as
   * - ``MaxSizePresetValidator``
     - ``max_bytes`` (int)
     - ``enforce_max_size``
   * - ``ExtensionPresetValidator``
     - ``allowed_extensions`` (list/tuple of strings)
     - ``enforce_extension``
   * - ``MimeFilenamePresetValidator``
     - ``allowed_patterns`` (list/tuple of strings)
     - ``enforce_mime_from_filename``

Subclass ``BaseFilePresetValidator`` and override ``validate(self, uploaded_file, *,
user, request, field_name)`` for custom rules. Register the subclass path in
``validate`` and pass constructor keyword arguments via ``validate_options``.

Example preset using only helpers
=================================

.. code-block:: python

    # myapp/upload_rules.py
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

Point ``validate`` to ``"myapp.upload_rules.validate_documents"`` in
``DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS``.

Saving uploads (“Save form submission” action)
==============================================

AJAX forms send data with ``multipart/form-data`` so files reach Django; preset
validation runs on the server before ``cleaned_data`` is built.

The **Save form submission** action stores ``entry_data`` as JSON. Uploaded files are
written to ``default_storage`` under ``form_uploads/…``, and each file field becomes a
small dict with ``_form_builder_file``, ``filename``, and ``url`` (same shape for each
file in a multiple-file field, as a list of dicts). The change view for
:class:`~djangocms_form_builder.entry_model.FormEntry` shows the URL (read-only).

Plugin admin
============

Presets run **in order** for each file (single-file field: one
file; multi-file field: each file in the batch).

They are stored in ``config`` as ``field_file_validation_presets`` (list of preset keys).
