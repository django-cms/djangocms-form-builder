"""Integration helpers for optional companion packages."""

from functools import cache

from django.apps import apps


@cache
def get_versionable_item(cms_config=None):
    """djangocms-versioning's ``VersionableItem``, or ``None`` if unavailable.

    django CMS 5.1 hands packages their versioning contract; on older
    versions the class is imported directly.
    """
    if cms_config is not None and hasattr(cms_config, "get_contract"):
        return cms_config.get_contract("djangocms_versioning")
    if apps.is_installed("djangocms_versioning"):
        try:
            from djangocms_versioning.datastructures import VersionableItem

            return VersionableItem
        except ModuleNotFoundError as exc:
            # Only treat a missing djangocms_versioning module as "no
            # versioning"; re-raise anything else so real errors stay visible.
            if exc.name in (
                "djangocms_versioning.datastructures",
                "djangocms_versioning",
            ):
                return None
            raise
    return None


def is_versioning_enabled():
    """Whether forms are versioned in this project."""
    cms_config = apps.get_app_config("djangocms_form_builder").cms_config
    return bool(getattr(cms_config, "versioning", False))
