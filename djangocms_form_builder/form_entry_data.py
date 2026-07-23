"""Turn form cleaned_data into JSON-safe values for :class:`~djangocms_form_builder.entry_model.FormEntry`."""

from __future__ import annotations

import logging
import typing
import uuid

from django.core.files.uploadedfile import UploadedFile
from django.utils.text import get_valid_filename

from .settings import FILE_FIELD_STORAGE

if typing.TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def store_uploaded_file(uploaded_file: UploadedFile) -> dict:
    """Save a single upload to default storage; return metadata for ``entry_data`` JSON."""
    safe = get_valid_filename(uploaded_file.name) or "upload"
    path = f"form_uploads/{uuid.uuid4().hex}_{safe}"
    saved_name = FILE_FIELD_STORAGE.save(path, uploaded_file)
    return {
        "_form_builder_file": True,
        "filename": uploaded_file.name,
        "name": saved_name,
        "url": FILE_FIELD_STORAGE.url(saved_name),
    }


def iter_stored_file_metadata(data: dict):
    """Yield stored-file metadata dictionaries contained in entry data."""
    for value in data.values():
        if isinstance(value, dict) and value.get("_form_builder_file"):
            yield value
        elif isinstance(value, list):
            yield from (
                item
                for item in value
                if isinstance(item, dict) and item.get("_form_builder_file")
            )


def delete_stored_file(meta: dict) -> None:
    """Delete one serialized upload through the configured storage backend."""
    name = meta.get("name")
    if not name:
        logger.warning(
            "Cannot delete uploaded file %s: no storage name in entry_data",
            meta.get("filename", meta.get("url", "?")),
        )
        return
    try:
        FILE_FIELD_STORAGE.delete(name)
    except Exception:
        logger.exception(
            "Failed to delete uploaded file %s",
            meta.get("filename", name),
        )


def delete_stored_files(data: dict, *, excluding=()) -> None:
    """Delete serialized uploads, optionally retaining specified storage names."""
    excluded_names = set(excluding)
    for meta in iter_stored_file_metadata(data):
        if meta.get("name") not in excluded_names:
            delete_stored_file(meta)


def serialize_cleaned_data_for_entry(cleaned_data: dict) -> dict:
    """
    Replace ``UploadedFile`` values with small dicts (filename + URL).
    Lists of uploads (multiple file field) become lists of those dicts.
    """
    result = {}
    newly_stored = []
    try:
        for key, value in cleaned_data.items():
            if isinstance(value, UploadedFile):
                result[key] = store_uploaded_file(value)
                newly_stored.append(result[key])
            elif (
                isinstance(value, list)
                and value
                and all(isinstance(item, UploadedFile) for item in value)
            ):
                result[key] = []
                for uploaded_file in value:
                    metadata = store_uploaded_file(uploaded_file)
                    result[key].append(metadata)
                    newly_stored.append(metadata)
            else:
                result[key] = value
    except Exception:
        # Storage writes are not transactional. Roll back files saved before a
        # later write failed so they do not become unreferenced orphans.
        for metadata in newly_stored:
            delete_stored_file(metadata)
        raise
    return result
