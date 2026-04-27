"""
File upload validation driven by DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS.

Each preset maps a key to a dict with at least ``label`` and ``validate`` (dotted path).
Optional ``validate_options`` is passed as keyword arguments to the function.

``validate`` must resolve to a function called as::

    fn(uploaded_file, *, user, request, field_name)

If ``filer_validator`` is ``True``, the imported function is wrapped from the
django-filer signature::

    fn(file_name, file, owner, mime_type)

Callables should raise :exc:`FileValidationError` on failure. The runner rewinds the
file with ``seek(0)`` after each preset.
"""

import mimetypes
import typing

from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.utils.module_loading import import_string

if typing.TYPE_CHECKING:
    from django.core.files.uploadedfile import UploadedFile
    from django.http import HttpRequest

    User = typing.Any


class FileValidationError(ValidationError):
    """Rejected upload from a form builder file field preset."""


def get_validation_preset_registry():
    return getattr(
        django_settings,
        "DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS",
        {},
    )


def validation_preset_choice_tuples():
    """Choices for admin single-select: (key, label)."""
    reg = get_validation_preset_registry()
    return [(k, str(v["label"])) for k, v in reg.items()]


def allowed_extensions_for_accept_attribute(preset_keys: list) -> str | None:
    """
    Build a comma-separated value for the HTML ``accept`` attribute from preset
    metadata ``accept_extensions``.

    When several such presets apply, allowed extensions are intersected (same as
    running each check server-side). See
    https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/input/file#accept
    """
    if not preset_keys:
        return None
    from .file_validation_validators import _normalize_extension

    # ``accept`` is a browser-side hint only. We intentionally derive it from
    # extension-based presets and keep server-side validation authoritative for
    # any other preset types.
    registry = get_validation_preset_registry()
    intersection: frozenset | None = None
    for key in preset_keys:
        entry = registry.get(key)
        if not entry:
            continue
        exts_raw = entry.get("accept_extensions")
        if not isinstance(exts_raw, (list, tuple)):
            continue
        exts = frozenset(_normalize_extension(x) for x in exts_raw if x)
        if not exts:
            continue
        intersection = exts if intersection is None else (intersection & exts)
    if not intersection:
        return None
    return ",".join(sorted(intersection))


def _mime_type_for_filer(
    uploaded_file: "UploadedFile", validate_options: dict | None
) -> str:
    """
    MIME string for adapters that call django-filer-style validators.

    ``validate_options`` may include ``mime_source``:

    * ``\"auto\"`` (default) — use ``uploaded_file.content_type`` if non-empty, else
      guess from filename, else ``application/octet-stream``.
    * ``\"guess\"`` — ignore ``content_type``; use :func:`mimetypes.guess_type` only.
    * ``\"content_type\"`` — use ``content_type`` only; if empty, fall back to
      ``application/octet-stream``.
    """
    opts = validate_options or {}
    source = opts.get("mime_source", "auto")
    name = getattr(uploaded_file, "name", "") or ""
    ct = getattr(uploaded_file, "content_type", None)

    if source == "guess":
        return mimetypes.guess_type(name)[0] or "application/octet-stream"
    if source == "content_type":
        if ct and str(ct).strip():
            return ct
        return "application/octet-stream"
    # "auto" or unknown — prefer browser/client content_type, then filename guess
    if ct and str(ct).strip():
        return ct
    return mimetypes.guess_type(name)[0] or "application/octet-stream"


def wrap_filer_style_validator(
    fn: typing.Callable[..., None],
    validate_options: dict | None,
) -> typing.Callable[..., None]:
    """
    Wrap a django-filer-style ``(file_name, file, owner, mime_type)`` validator so it
    matches the form builder preset signature ``(uploaded_file, *, user, request, field_name)``.
    """

    def wrapped(
        uploaded_file: "UploadedFile",
        *,
        user: "User",
        request: typing.Optional["HttpRequest"],
        field_name: str,
    ) -> None:
        mime = _mime_type_for_filer(uploaded_file, validate_options)
        try:
            fn(uploaded_file.name, uploaded_file, user, mime)
        except ValidationError:
            raise
        except Exception as exc:
            raise FileValidationError(str(exc)) from exc

    return wrapped


def validate_form_builder_file(
    uploaded_file: "UploadedFile",
    preset_keys: list,
    *,
    user: "User",
    request: typing.Optional["HttpRequest"],
    field_name: str,
) -> None:
    """Run each preset callable in order for the given keys."""
    if not preset_keys:
        return
    registry = get_validation_preset_registry()
    for key in preset_keys:
        try:
            entry = registry[key]
        except KeyError as exc:
            raise ImproperlyConfigured(
                f"Unknown file validation preset key '{key}' in "
                "DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS"
            ) from exc
        target = import_string(entry["validate"])
        opts = entry.get("validate_options") or {}
        if isinstance(target, type):
            raise ImproperlyConfigured(
                'DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS: "validate" must resolve '
                "to a function, not a class."
            )
        call_kwargs = {
            "user": user,
            "request": request,
            "field_name": field_name,
        }
        if entry.get("filer_validator"):
            target = wrap_filer_style_validator(target, opts)
        else:
            call_kwargs = {**opts, **call_kwargs}
        target(uploaded_file, **call_kwargs)
        uploaded_file.seek(0)
