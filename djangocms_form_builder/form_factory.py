"""Turns a tree of form plugins into a Django form class.

Both sources of a plugin-built form use this: a :class:`FormContent` object,
and - for instances predating it - a form plugin carrying its fields as
children.  Whatever provides the settings is called the *source* here; it only
has to expose the ``form_*``, ``action_parameters`` and ``captcha_*``
attributes that :class:`djangocms_form_builder.models.FormPlugin` and
:class:`djangocms_form_builder.form_model.FormContent` share.
"""

import json

from . import recaptcha
from .forms import SimpleFrontendForm

#: Default behaviour after a successful submission: stay on the same page.
SAME_PAGE_REDIRECT = "result"


def iter_plugin_tree(plugins):
    """Yield ``plugins`` and all of their descendants, parents first."""
    for plugin in plugins:
        yield plugin
        if plugin.child_plugin_instances is None:  # children already fetched?
            plugin.child_plugin_instances = [
                child.get_plugin_instance()[0] for child in plugin.get_children()
            ]
        yield from iter_plugin_tree(plugin.child_plugin_instances)


def collect_form_fields(plugins, request=None):
    """The form fields declared by ``plugins`` and their descendants.

    A plugin contributes a field by having a ``get_form_field`` method; any
    other plugin is free to sit in a form purely for layout or explanation.
    """
    fields = {}
    for instance in iter_plugin_tree(plugins):
        get_form_field = getattr(instance, "get_form_field", None)
        if get_form_field is None:
            continue
        try:
            name, field = get_form_field(request=request)
        except TypeError:
            # Backwards compatibility for third-party fields using the
            # old no-argument API; remove this fallback in version 1.0.
            name, field = get_form_field()
        fields[name] = field
    return fields


def get_form_options(source):
    """The ``Meta.options`` of the form class built for ``source``."""
    form_actions = source.form_actions or "[]"
    options = {
        "form_name": source.form_name,
        "field_sep": f"{source.form_spacing}",
        # Default behavior: redirect to same page
        "redirect": SAME_PAGE_REDIRECT,
        "login_required": source.form_login_required,
        "unique": source.form_unique,
        "form_actions": json.loads(form_actions.replace("'", '"')),
        "form_parameters": getattr(source, "action_parameters", {}) or {},
    }
    if source.form_floating_labels:
        options["floating_labels"] = True
    return options


def get_form_verbose_name(source):
    name = getattr(source, "name", "")
    if name:
        return name
    return (source.form_name or "").replace("-", " ").replace("_", " ").capitalize()


def build_form_class(source, plugins, request=None):
    """Build the form class for ``source`` out of ``plugins``.

    The class is rebuilt per request, so fields may capture the request (e.g.
    file fields whose validators need the user/request context).
    """
    fields = collect_form_fields(plugins, request=request)

    # Add recaptcha field if necessary
    if recaptcha.installed and source.captcha_widget:
        fields[recaptcha.field_name] = recaptcha.get_recaptcha_field(source)

    fields["Meta"] = type(
        "Meta",
        (),
        dict(
            options=get_form_options(source),
            verbose_name=get_form_verbose_name(source),
        ),
    )

    return type(
        "FrontendAutoForm",
        (SimpleFrontendForm,),
        fields,
    )


def has_plugin_of_type(plugins, plugin_type):
    """Whether ``plugins`` or their descendants contain that plugin type."""
    return any(
        plugin.plugin_type == plugin_type for plugin in iter_plugin_tree(plugins)
    )
