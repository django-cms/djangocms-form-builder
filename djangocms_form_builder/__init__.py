import hashlib

try:
    from django.utils.translation import gettext_lazy as _
except ModuleNotFoundError:
    _ = lambda x: x  # noqa: E731


__version__ = "0.3.2"

_form_registry = {}


def verbose_name(form_class):
    """returns the verbose_name property of a Meta class if present or else
    splits the camel-cased form class name"""
    if hasattr(form_class, "Meta") and hasattr(form_class.Meta, "verbose_name"):
        return getattr(form_class.Meta, "verbose_name")  # noqa
    class_name = form_class.__name__.rsplit(".", 1)[-1]
    from re import finditer

    matches = finditer(
        ".+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)", class_name
    )
    return " ".join(m.group(0) for m in matches)


def get_registered_forms():
    """Creates a tuple for a ChoiceField to select form"""
    result = tuple(
        (hash, verbose_name(form_class)) for hash, form_class in _form_registry.items()
    )
    return result if result else ((_("No forms registered"), ()),)


def register_with_form_builder(form_class):
    """Function to call or decorator for a Form class to make it available for the plugin"""
    hash = hashlib.sha1(form_class.__name__.encode("utf-8")).hexdigest()
    _form_registry.update({hash: form_class})
    return form_class


__all__ = ["register_with_form_builder", "get_registered_forms"]
