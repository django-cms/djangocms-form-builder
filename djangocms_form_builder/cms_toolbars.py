"""Toolbar entries for the form editor."""

from cms.cms_toolbars import (
    ADMIN_MENU_IDENTIFIER,
    ADMINISTRATION_BREAK,
    SHORTCUTS_BREAK,
)
from cms.toolbar.items import Break
from cms.toolbar.utils import get_object_edit_url
from cms.toolbar_base import CMSToolbar
from cms.toolbar_pool import toolbar_pool
from cms.utils.permissions import get_model_permission_codename
from cms.utils.urlutils import admin_reverse
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from .constants import (
    LIST_FORM_URL_NAME,
    SETTINGS_FORM_URL_NAME,
    USAGE_FORM_URL_NAME,
)
from .models import Form, FormContent

__all__ = ["FormToolbar"]

FORM_MENU_IDENTIFIER = "form-builder"


@toolbar_pool.register
class FormToolbar(CMSToolbar):
    name = _("Form")
    plural_name = _("Forms")

    def populate(self):
        self.add_forms_link_to_admin_menu()
        if isinstance(self.toolbar.obj, FormContent):
            self.add_form_menu()

    def add_forms_link_to_admin_menu(self):
        if not self.request.user.has_perm(
            get_model_permission_codename(Form, "change")
        ):
            return
        admin_menu = self.toolbar.get_or_create_menu(ADMIN_MENU_IDENTIFIER)
        admin_menu.add_sideframe_item(
            self.plural_name,
            url=admin_reverse(LIST_FORM_URL_NAME),
            position=self.get_insert_position(admin_menu, self.plural_name),
        )

    def add_form_menu(self):
        """The menu shown while a form is being edited."""
        form_content = self.toolbar.obj
        menu = self.toolbar.get_or_create_menu(
            FORM_MENU_IDENTIFIER,
            self.name,
            position=1,
        )
        can_change = self.request.user.has_perm(
            get_model_permission_codename(FormContent, "change")
        )
        # Leads to the form admin, showing the content being edited here.
        menu.add_modal_item(
            _("Form settings"),
            url=admin_reverse(SETTINGS_FORM_URL_NAME, args=[form_content.pk]),
            disabled=not can_change,
        )
        menu.add_modal_item(
            _("View usage"),
            url=admin_reverse(USAGE_FORM_URL_NAME, args=[form_content.form_id]),
        )
        menu.add_sideframe_item(
            _("All forms"),
            url=admin_reverse(LIST_FORM_URL_NAME),
        )

    @classmethod
    def get_insert_position(cls, admin_menu, item_name):
        """Alphabetical position among the admin menu's model links.

        Ensures there is a ``SHORTCUTS_BREAK`` and places the item between it
        and the ``ADMINISTRATION_BREAK``.
        """
        start = admin_menu.find_first(Break, identifier=SHORTCUTS_BREAK)
        if not start:
            end = admin_menu.find_first(Break, identifier=ADMINISTRATION_BREAK)
            admin_menu.add_break(SHORTCUTS_BREAK, position=end.index)
            start = admin_menu.find_first(Break, identifier=SHORTCUTS_BREAK)
        end = admin_menu.find_first(Break, identifier=ADMINISTRATION_BREAK)

        items = admin_menu.get_items()[start.index + 1 : end.index]
        for idx, item in enumerate(items):
            name = getattr(item, "name", None)
            if (
                name is not None
                and force_str(item_name).lower() < force_str(name).lower()
            ):
                return idx + start.index + 1
        return end.index

    def get_form_edit_url(self, form):
        content = form.get_content(show_draft_content=True)
        return get_object_edit_url(content) if content else None
