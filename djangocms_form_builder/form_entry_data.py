"""Turn form cleaned_data into JSON-safe values for :class:`~djangocms_form_builder.entry_model.FormEntry`."""

from __future__ import annotations

import typing
import uuid

from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile
from django.utils.text import get_valid_filename

if typing.TYPE_CHECKING:
    pass


def _store_uploaded_file(uploaded_file: UploadedFile) -> dict:
    """Save a single upload to default storage; return metadata for ``entry_data`` JSON."""
    safe = get_valid_filename(uploaded_file.name) or "upload"
    path = f"form_uploads/{uuid.uuid4().hex}_{safe}"
    saved_name = default_storage.save(path, uploaded_file)
    return {
        "_form_builder_file": True,
        "filename": uploaded_file.name,
        "url": default_storage.url(saved_name),
    }


def serialize_cleaned_data_for_entry(cleaned_data: dict) -> dict:
    """
    Replace ``UploadedFile`` values with small dicts (filename + URL).
    Lists of uploads (multiple file field) become lists of those dicts.
    """
    result = {}
    for key, value in cleaned_data.items():
        if isinstance(value, UploadedFile):
            result[key] = _store_uploaded_file(value)
        elif isinstance(value, list) and value and isinstance(value[0], UploadedFile):
            result[key] = [_store_uploaded_file(f) for f in value]
        else:
            result[key] = value
    return result
