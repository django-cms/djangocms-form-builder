"""Built-in file checks for form builder preset functions."""

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
    user=None,
    request=None,
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
    user=None,
    request=None,
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
    user=None,
    request=None,
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
