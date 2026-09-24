import base64
import json
from copy import deepcopy
from urllib.parse import urlencode

from cms.admin.utils import CONTENT_PREFIX, GrouperAdminFormMixin, GrouperModelAdmin
from cms.utils.urlutils import admin_reverse
from django import forms
from django.contrib import admin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models as django_models
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import path
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _

from . import actions, recaptcha
from .constants import (
    CHANGE_FORM_URL_NAME,
    LIST_FORM_URL_NAME,
    USAGE_FORM_URL_NAME,
)
from .forms import FormSettingsFormMixin, form_settings_errors
from .helpers import mark_safe_lazy
from .models import Form, FormContent, FormEntry


@admin.register(FormEntry)
class FormEntryAdmin(admin.ModelAdmin):
    date_hierarchy = "entry_created_at"
    list_display = ("__str__", "form_user", "entry_created_at")
    list_filter = ("form_name", "form_user", "entry_created_at")
    readonly_fields = ["form_name", "form_user"]

    def has_add_permission(self, request):
        return False

    def get_form(self, request, obj=None, **kwargs):
        if obj:
            kwargs["form"] = obj.get_admin_form()
        return super().get_form(request, obj, **kwargs)

    @staticmethod
    def entry_file_attr_name(key):
        encoded = base64.urlsafe_b64encode(str(key).encode()).decode().rstrip("=")
        return f"entry_file_{encoded}"

    @staticmethod
    def entry_file_key_from_attr(name):
        encoded = name.removeprefix("entry_file_")
        padding = (-len(encoded)) % 4
        return base64.urlsafe_b64decode(encoded + "=" * padding).decode()

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if obj:
            ro.extend(
                self.entry_file_attr_name(k) for k in obj.get_file_entry_data_keys()
            )
        return ro

    def get_fieldsets(self, request, obj=None):
        if obj:
            file_fields = [
                self.entry_file_attr_name(k) for k in obj.get_file_entry_data_keys()
            ]
            fieldsets = list(obj.get_admin_fieldsets())
            if file_fields:
                fieldsets.append(
                    (
                        _("Uploaded files"),
                        {
                            "fields": tuple(file_fields),
                        },
                    ),
                )
            return fieldsets
        return super().get_fieldsets(request, obj)

    @staticmethod
    def format_entry_file_field(obj, key):
        items = FormEntry.get_file_entry_items(obj.entry_data.get(key))
        if not items:
            return "—"
        if len(items) == 1:
            value = items[0]
            return format_html(
                '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>',
                value["url"],
                value["filename"],
            )
        return format_html(
            "<ul>{}</ul>",
            format_html_join(
                "",
                '<li><a href="{}" target="_blank" rel="noopener noreferrer">{}</a></li>',
                ((d["url"], d["filename"]) for d in items),
            ),
        )

    def __getattr__(self, name):
        if name.startswith("entry_file_"):
            try:
                key = self.entry_file_key_from_attr(name)
            except (ValueError, UnicodeDecodeError):
                raise AttributeError(
                    f"{type(self).__name__!r} object has no attribute {name!r}"
                ) from None

            def display(admin, obj, _key=key):
                return FormEntryAdmin.format_entry_file_field(obj, _key)

            display.short_description = key
            return display.__get__(self, type(self))
        raise AttributeError(
            f"{type(self).__name__!r} object has no attribute {name!r}"
        )

    def save_model(self, request, obj, form, change):
        """
        Preserve file payload in ``entry_data`` when those keys are not in the
        entangled form (shown only as readonly links).
        """
        preserved = {}
        if change and obj.pk:
            previous = FormEntry.objects.filter(pk=obj.pk).only("entry_data").first()
            if previous:
                for k in previous.get_file_entry_data_keys():
                    preserved[k] = previous.entry_data[k]
        super().save_model(request, obj, form, change)
        if preserved:
            merged = dict(obj.entry_data)
            merged.update(preserved)
            if merged != obj.entry_data:
                obj.entry_data = merged
                obj.save(update_fields=["entry_data"])


def selected_actions(value):
    """The actions stored in ``FormContent.form_actions`` as a list."""
    if isinstance(value, str):
        return json.loads(value.replace("'", '"')) if value.strip() else []
    return list(value or [])


def get_action_fields():
    """The registered actions' parameter fields as ``{name: (action, field)}``.

    ``action`` is the hash an action is selected by in ``form_actions``.
    """
    return {
        name: (action_hash, field)
        for action_hash, action in actions._action_registry.items()
        for name, field in action.declared_fields.items()
        # Skip the JSON field the parameters are stored in.
        if name != "action_parameters"
    }


#: The settings of a form, as named on :class:`FormContent`.
FORM_SETTINGS = (
    "form_login_required",
    "form_unique",
    "form_floating_labels",
    "form_spacing",
    "form_actions",
    "captcha_widget",
    "captcha_requirement",
    "captcha_config",
)


class FormGrouperFormBase(GrouperAdminFormMixin(FormContent), forms.ModelForm):
    """A form's identity and settings, edited together in the form admin.

    The settings live on the form's content object. ``GrouperModelAdmin``
    offers its fields as ``content__<name>`` and writes back every one the form
    carries. The actions' parameters are gathered into ``action_parameters``;
    :meth:`FormAdmin.get_form` adds their fields, as ``action_fields``.
    """

    #: ``{name: (action, required)}`` of the action parameter fields present.
    action_fields = {}

    class Meta:
        model = Form
        fields = ("form_name",)

    class Media:
        js = ("djangocms_form_builder/js/actions_form.js",)
        css = {"all": ("djangocms_form_builder/css/actions_form.css",)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only fields the admin renders may be saved - any other content field
        # would be written back with an empty value.
        rendered = set(self._meta.fields or self.fields)
        rendered.add(CONTENT_PREFIX + self._admin.grouper_field_name)
        for name in list(self.fields):
            if name.startswith(CONTENT_PREFIX) and name not in rendered:
                del self.fields[name]

        actions_field = CONTENT_PREFIX + "form_actions"
        if actions_field in self.fields:
            self.fields[actions_field].choices = actions.get_registered_actions()
            self.initial[actions_field] = selected_actions(
                self.initial.get(actions_field)
            )
        parameters = getattr(self._content_instance, "action_parameters", None) or {}
        for name in self.action_fields:
            if name in parameters:
                self.initial[name] = parameters[name]

    def clean(self):
        cleaned_data = super().clean()
        actions_field = CONTENT_PREFIX + "form_actions"
        if actions_field not in self.fields:
            # The content is read-only: nothing to gather or check.
            return cleaned_data

        selected = cleaned_data.get(actions_field) or []
        parameters = dict(
            getattr(self._content_instance, "action_parameters", None) or {}
        )
        for name, (action_hash, required) in self.action_fields.items():
            if name not in self.fields or name in self.errors:
                continue
            value = cleaned_data.get(name)
            # Parameters are only required by the actions actually selected.
            if (
                required
                and action_hash in selected
                and value in self.fields[name].empty_values
            ):
                self.add_error(
                    name,
                    ValidationError(
                        self.fields[name].error_messages["required"], code="required"
                    ),
                )
                continue
            parameters[name] = value
        cleaned_data[CONTENT_PREFIX + "action_parameters"] = parameters
        cleaned_data[actions_field] = json.dumps(selected)

        errors = form_settings_errors(
            form_actions=selected,
            form_unique=cleaned_data.get(CONTENT_PREFIX + "form_unique"),
            form_login_required=cleaned_data.get(
                CONTENT_PREFIX + "form_login_required"
            ),
        )
        for name, error in errors.items():
            self.add_error(CONTENT_PREFIX + name, error)
        return cleaned_data


def _settings_fields():
    """The settings fields the legacy form plugin edits, prefixed."""
    fields = {
        CONTENT_PREFIX + name: deepcopy(FormSettingsFormMixin.declared_fields[name])
        for name in FORM_SETTINGS
    }
    # Only meaningful with a captcha widget selected; the model defaults it.
    fields[CONTENT_PREFIX + "captcha_requirement"].required = False
    return fields


FormGrouperForm = type("FormGrouperForm", (FormGrouperFormBase,), _settings_fields())


@admin.register(Form)
class FormAdmin(GrouperModelAdmin):
    """Forms: the list of forms, and each form's identity and settings."""

    form = FormGrouperForm
    list_display = ("content__name", "form_name", "used", "admin_list_actions")
    list_display_links = None
    search_fields = ("form_name", "content__name")
    ordering = ("form_name",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(cms_plugins_count=django_models.Count("cms_plugins"))

    @admin.display(description=_("In use"), boolean=True, ordering="cms_plugins_count")
    def used(self, obj):
        return obj.cms_plugins_count > 0

    @admin.display(description=_("Actions to be taken after form submission"))
    def content__form_actions(self, obj):
        """Shown when the settings are read-only, e.g. for a published form."""
        content = self.get_content_obj(obj)
        names = dict(actions.get_registered_actions())
        return ", ".join(
            str(names.get(action, action))
            for action in selected_actions(getattr(content, "form_actions", ""))
        )

    def can_edit_settings(self, request, obj):
        return self.can_change_content(request, self.get_content_obj(obj))

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            (
                None,
                {
                    "fields": [
                        CONTENT_PREFIX + "name",
                        "form_name",
                        (
                            CONTENT_PREFIX + "form_login_required",
                            CONTENT_PREFIX + "form_unique",
                        ),
                        CONTENT_PREFIX + "form_floating_labels",
                        CONTENT_PREFIX + "form_spacing",
                    ],
                },
            ),
        ]
        if recaptcha.installed:
            captcha = {
                "fields": [
                    CONTENT_PREFIX + "captcha_widget",
                    CONTENT_PREFIX + "captcha_requirement",
                    CONTENT_PREFIX + "captcha_config",
                ],
            }
            if not recaptcha.keys_available:
                captcha["description"] = mark_safe_lazy(
                    _(
                        '<blockquote style="color: var(--error-fg);">Please get a public and secret '
                        'key from <a href="{key_link}" target="_blank">Google</a> '
                        "and ensure that they are available through django settings "
                        "<code>RECAPTCHA_PUBLIC_KEY</code> and <code>RECAPTCHA_PRIVATE_KEY</code>. "
                        "Without these keys captcha protection will not work.</blockquote>"
                    ).format(key_link="https://developers.google.com/recaptcha")
                )
            fieldsets.append((_("Captcha"), captcha))
        fieldsets.append(
            (
                _("Actions"),
                {
                    "fields": [CONTENT_PREFIX + "form_actions"],
                    "classes": ("collapse", "action-auto-hide"),
                },
            )
        )
        if self.can_edit_settings(request, obj):
            # One block per action with parameters, shown while it is selected.
            blocks = {}
            for name, (action_hash, _field) in get_action_fields().items():
                blocks.setdefault(action_hash, []).append(name)
            for action_hash, names in blocks.items():
                fieldsets.append(
                    (
                        actions._action_registry[action_hash].verbose_name,
                        {
                            "fields": names,
                            "classes": (f"c{action_hash}", "action-hide"),
                        },
                    )
                )
        return fieldsets

    def get_form(self, request, obj=None, change=False, **kwargs):
        """Add the registered actions' parameter fields to the form.

        Actions may be registered after the admin is set up, so the fields
        are added per request. They are optional here: the form requires the
        parameters of the selected actions only.
        """
        attrs = {}
        if self.can_edit_settings(request, obj):
            action_fields = get_action_fields()
            for name, (_action_hash, field) in action_fields.items():
                attrs[name] = deepcopy(field)
                attrs[name].required = False
            attrs["action_fields"] = {
                name: (action_hash, field.required)
                for name, (action_hash, field) in action_fields.items()
            }
        # What ModelAdmin.get_form does for self.form, which is replaced here:
        # read-only fields must not be form fields.
        readonly = self.get_readonly_fields(request, obj)
        attrs.update(
            dict.fromkeys(f for f in readonly if f in self.form.declared_fields)
        )
        kwargs["form"] = type(self.form.__name__, (self.form,), attrs)
        return super().get_form(request, obj, change=change, **kwargs)

    def get_actions_list(self):
        return super().get_actions_list() + [self._get_usage_action]

    def _get_usage_action(self, obj, request):
        return self.admin_action_button(
            url=admin_reverse(USAGE_FORM_URL_NAME, args=[obj.pk]),
            icon="info",
            title=_("View usage"),
            name="form-usage",
        )

    def has_delete_permission(self, request, obj=None):
        """A form that is still shown somewhere must not be deleted.

        The plugin's ``on_delete=PROTECT`` would refuse anyway; saying so up
        front is friendlier than a database error.
        """
        if obj is not None and obj.is_in_use:
            return False
        return super().has_delete_permission(request, obj)

    def get_urls(self):
        return [
            path(
                "<int:pk>/usage/",
                self.admin_site.admin_view(self.usage_view),
                name=USAGE_FORM_URL_NAME,
            ),
        ] + super().get_urls()

    def usage_view(self, request, pk):
        form = get_object_or_404(Form, pk=pk)
        if not self.has_view_permission(request, form):
            raise PermissionDenied
        opts = self.model._meta
        title = _("Objects using form: %(form)s") % {"form": form}
        return TemplateResponse(
            request,
            "djangocms_form_builder/admin/form_usage.html",
            {
                "has_change_permission": self.has_change_permission(request, form),
                "opts": opts,
                "root_path": admin_reverse("index"),
                "is_popup": True,
                "app_label": opts.app_label,
                "object_name": _("Form"),
                "object": form,
                "title": title,
                "original": title,
                "objects_list": form.objects_using,
            },
        )


@admin.register(FormContent)
class FormContentAdmin(admin.ModelAdmin):
    """Stands in for the form admin wherever a form content is addressed.

    djangocms-versioning relies on an admin for the versioned model. A form
    content is edited as part of its form, so its change view leads there,
    showing exactly this content object.
    """

    actions = None

    def has_module_permission(self, request):
        """Hide from the admin index - forms are managed through the form list."""
        return False

    def has_add_permission(self, request):
        """Form contents are created together with their form."""
        return False

    def changelist_view(self, request, extra_context=None):
        """There is no list of form contents - show the list of forms."""
        return HttpResponseRedirect(admin_reverse(LIST_FORM_URL_NAME))

    def change_view(self, request, object_id, form_url="", extra_context=None):
        content = self.get_object(request, object_id)
        if content is None:
            raise Http404
        url = admin_reverse(CHANGE_FORM_URL_NAME, args=[content.form_id])
        param = getattr(FormAdmin, "content_pk_url_param", None)
        if param:
            url += "?" + urlencode({param: content.pk})
        return HttpResponseRedirect(url)

    def get_object(self, request, object_id, from_field=None):
        """Also find drafts and unpublished versions."""
        try:
            return self.model.admin_manager.get(pk=object_id)
        except (self.model.DoesNotExist, ValueError, ValidationError):
            return None
