import base64

from cms.admin.utils import GrouperModelAdmin
from cms.utils.urlutils import admin_reverse
from django.contrib import admin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models as django_models
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import path
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _

from . import recaptcha
from .actions import ActionMixin
from .constants import (
    CHANGE_FORM_URL_NAME,
    LIST_FORM_URL_NAME,
    SETTINGS_FORM_URL_NAME,
    USAGE_FORM_URL_NAME,
)
from .forms import FormContentForm, FormGrouperForm
from .helpers import insert_fields, mark_safe_lazy
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


@admin.register(Form)
class FormAdmin(GrouperModelAdmin):
    """The list of forms - the entry point into the form editor."""

    form = FormGrouperForm
    list_display = ("content__name", "form_name", "used", "admin_list_actions")
    list_display_links = None
    search_fields = ("form_name", "content__name")
    fields = ("content__name", "form_name")
    ordering = ("form_name",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(cms_plugins_count=django_models.Count("cms_plugins"))

    @admin.display(description=_("In use"), boolean=True, ordering="cms_plugins_count")
    def used(self, obj):
        return obj.cms_plugins_count > 0

    def get_actions_list(self):
        return super().get_actions_list() + [
            self._get_form_settings_action,
            self._get_usage_action,
        ]

    def _get_form_settings_action(self, obj, request):
        content_obj = self.get_content_obj(obj)
        if content_obj is None:
            return self.EMPTY_ACTION
        return self.admin_action_button(
            url=admin_reverse(SETTINGS_FORM_URL_NAME, args=[content_obj.pk]),
            icon="cogs",
            title=_("Form settings"),
            burger_menu=True,
            name="form-settings",
        )

    def _get_usage_action(self, obj, request):
        return self.admin_action_button(
            url=admin_reverse(USAGE_FORM_URL_NAME, args=[obj.pk]),
            icon="info",
            title=_("View usage"),
            burger_menu=True,
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
        if not request.user.is_staff:
            raise PermissionDenied
        form = get_object_or_404(Form, pk=pk)
        opts = self.model._meta
        title = _("Objects using form: %(form)s") % {"form": form}
        return TemplateResponse(
            request,
            "djangocms_form_builder/admin/form_usage.html",
            {
                "has_change_permission": True,
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
class FormContentAdmin(ActionMixin, admin.ModelAdmin):
    """The behaviour of a form: what happens once it is submitted.

    Reached from the form editor's toolbar and from the form list; not an
    entry of its own in the admin index, because a form content object only
    ever makes sense in the context of its form.
    """

    form = FormContentForm
    actions = None
    change_form_template = "djangocms_frontend/admin/base.html"

    fieldsets = [
        (
            None,
            {
                "fields": [
                    "name",
                    (
                        "form_login_required",
                        "form_unique",
                    ),
                    "form_floating_labels",
                    "form_spacing",
                ],
            },
        ),
    ]

    def has_module_permission(self, request):
        """Hide from the admin index - forms are managed through the form list."""
        return False

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        fieldsets = insert_fields(
            fieldsets,
            ("form_actions",),
            block=None,
            position=1,
            blockname=_("Actions"),
            blockattrs={"classes": ("collapse", "action-auto-hide")},
        )
        if recaptcha.installed:
            fieldsets = insert_fields(
                fieldsets,
                ("captcha_widget", "captcha_requirement", "captcha_config"),
                block=None,
                position=1,
                blockname=_("Captcha"),
                blockattrs={}
                if recaptcha.keys_available
                else dict(
                    description=mark_safe_lazy(
                        _(
                            '<blockquote style="color: var(--error-fg);">Please get a public and secret '
                            'key from <a href="{key_link}" target="_blank">Google</a> '
                            "and ensure that they are available through django settings "
                            "<code>RECAPTCHA_PUBLIC_KEY</code> and <code>RECAPTCHA_PRIVATE_KEY</code>. "
                            "Without these keys captcha protection will not work.</blockquote>"
                        ).format(key_link="https://developers.google.com/recaptcha")
                    )
                ),
            )
        return fieldsets

    def changelist_view(self, request, extra_context=None):
        """There is no list of form contents - show the list of forms."""
        return HttpResponseRedirect(admin_reverse(LIST_FORM_URL_NAME))

    def response_post_save_change(self, request, obj):
        return HttpResponseRedirect(
            admin_reverse(CHANGE_FORM_URL_NAME, args=[obj.form_id])
        )

    def has_add_permission(self, request):
        """Form contents are created together with their form."""
        return False

    def get_object(self, request, object_id, from_field=None):
        """Also find drafts and unpublished versions."""
        try:
            return self.model.admin_manager.get(pk=object_id)
        except (self.model.DoesNotExist, ValueError, ValidationError):
            return None
