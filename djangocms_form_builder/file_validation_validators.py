"""
Built-in file checks for form builder presets.

Use the **functions** inside your own preset callables, or register the **classes**
in ``DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS`` together with
``validate_options`` (see :func:`djangocms_form_builder.file_validation.validate_form_builder_file`).
"""

from __future__ import annotations

import mimetypes
import os
import typing

from django.utils.translation import gettext as _

from .file_validation import FileValidationError

if typing.TYPE_CHECKING:
    from django.core.files.uploadedfile import UploadedFile


def _normalize_extension(ext: str) -> str:
    ext = ext.lower().strip()
    if not ext:
        return ext
    return ext if ext.startswith(".") else f".{ext}"


def _format_one_decimal_trim(value: float) -> str:
    """Format with one decimal place, drop trailing ``.0``."""
    s = f"{value:.1f}"
    if s.endswith(".0"):
        return s[:-2] or "0"
    return s


def _format_size_limit(max_bytes: int) -> str:
    """Human-readable limit for error messages (MB/KB/bytes)."""
    if max_bytes >= 1024 * 1024:
        mb = max_bytes / (1024 * 1024)
        return _("%(size)s MB") % {"size": _format_one_decimal_trim(mb)}
    if max_bytes >= 1024:
        kb = max_bytes / 1024
        return _("%(size)s KB") % {"size": _format_one_decimal_trim(kb)}
    return _("%(n)s bytes") % {"n": max_bytes}


def enforce_max_size(
    uploaded_file: UploadedFile,
    max_bytes: int,
    *,
    field_name: str = "",
) -> None:
    """Reject if ``uploaded_file.size`` exceeds ``max_bytes``."""
    size = getattr(uploaded_file, "size", None)
    if size is None:
        return
    if size > max_bytes:
        name = getattr(uploaded_file, "name", field_name or "?")
        raise FileValidationError(
            _('File "%(name)s" is too large (maximum %(limit)s).')
            % {"name": name, "limit": _format_size_limit(max_bytes)}
        )


def enforce_extension(
    uploaded_file: UploadedFile,
    allowed_extensions: typing.Iterable[str],
    *,
    field_name: str = "",
) -> None:
    """Reject if the filename suffix is not in ``allowed_extensions`` (e.g. ``".pdf"`` or ``"pdf"``)."""
    allowed = frozenset(_normalize_extension(x) for x in allowed_extensions if x)
    name = getattr(uploaded_file, "name", "") or field_name
    _stem, ext = os.path.splitext(name.lower())
    if ext not in allowed:
        allowed_list = ", ".join(sorted(allowed))
        if allowed_list:
            raise FileValidationError(
                _(
                    'File "%(name)s" has a disallowed extension. '
                    "Allowed formats: %(allowed)s."
                )
                % {"name": name, "allowed": allowed_list}
            )
        raise FileValidationError(
            _('File "%(name)s" has a disallowed extension.') % {"name": name}
        )


def _mime_matches(mime: str, pattern: str) -> bool:
    if pattern.endswith("/"):
        return mime.startswith(pattern)
    return mime == pattern


def enforce_mime_from_filename(
    uploaded_file: UploadedFile,
    allowed_patterns: typing.Iterable[str],
    *,
    field_name: str = "",
) -> None:
    """
    Guess MIME type from the filename and reject if it does not match any pattern.

    Each pattern is either a full MIME type (exact match) or a prefix ending with
    ``/`` (e.g. ``"image/"`` matches ``image/png``).
    """
    patterns = tuple(allowed_patterns)
    if not patterns:
        return

    name = getattr(uploaded_file, "name", "") or field_name
    mime, _encoding = mimetypes.guess_type(name)
    if not mime:
        raise FileValidationError(
            _('Could not determine file type for "%(name)s".') % {"name": name}
        )
    if not any(_mime_matches(mime, p) for p in patterns):
        allowed_list = ", ".join(sorted(patterns))
        raise FileValidationError(
            _(
                'File "%(name)s" has a disallowed type (%(mime)s). '
                "Allowed types: %(allowed)s."
            )
            % {"name": name, "mime": mime, "allowed": allowed_list}
        )


class BaseFilePresetValidator:
    """
    Subclass and implement :meth:`validate`, or use the concrete validators below.

    Instances are callable with the same signature as a preset function.
    """

    helper: typing.Callable[..., None] | None = None
    option_name: str | None = None

    def __init__(self, **options):
        if not self.option_name:
            raise TypeError(
                f"{self.__class__.__name__} must define option_name to be instantiated."
            )
        try:
            self._option_value = options[self.option_name]
        except KeyError as exc:
            raise TypeError(
                f"{self.__class__.__name__} requires option {self.option_name!r}"
            ) from exc

    def __call__(
        self,
        uploaded_file: UploadedFile,
        *,
        user,
        request,
        field_name: str,
    ) -> None:
        self.validate(
            uploaded_file,
            user=user,
            request=request,
            field_name=field_name,
        )

    def validate(
        self,
        uploaded_file: UploadedFile,
        *,
        user,
        request,
        field_name: str,
    ) -> None:
        if self.helper is None:
            raise NotImplementedError
        self.helper(uploaded_file, self._option_value, field_name=field_name)


class MaxSizePresetValidator(BaseFilePresetValidator):
    """Preset class: maximum file size in bytes (``validate_options``: ``{"max_bytes": int}``)."""

    helper = enforce_max_size
    option_name = "max_bytes"


class ExtensionPresetValidator(BaseFilePresetValidator):
    """
    Preset class: allowed filename extensions
    (``validate_options``: ``{"allowed_extensions": [".pdf", "png", ...]}``).
    """

    helper = enforce_extension
    option_name = "allowed_extensions"


class MimeFilenamePresetValidator(BaseFilePresetValidator):
    """
    Preset class: MIME guessed from filename
    (``validate_options``: ``{"allowed_patterns": ["application/pdf", "image/", ...]}``).
    """

    helper = enforce_mime_from_filename
    option_name = "allowed_patterns"
