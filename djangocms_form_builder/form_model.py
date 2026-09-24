"""The frontend-editable form object.

A form is built from plugins, just like before, but those plugins now live in
a placeholder of their own instead of below a plugin on some page.  This makes
a form an object in its own right: it can be edited centrally, reused on any
number of pages, and - where djangocms-versioning is installed - drafted and
published independently of the pages showing it.

Following the grouper/content split django CMS uses for its own content
models, :class:`Form` carries the stable identity (the identifier that form
submissions are filed under) while :class:`FormContent` carries everything
that is edited, including the placeholder holding the field plugins.

A form has no language of its own: there is one form, with one identifier and
one set of settings, however many languages a site has.  Its plugins carry a
language like any other django CMS plugin, so a form is built per language
inside that single object - the way a static placeholder used to work.
"""

from collections import defaultdict

from cms.models.fields import PlaceholderRelationField
from cms.models.managers import ContentAdminManager, WithUserMixin
from cms.utils.permissions import get_model_permission_codename
from cms.utils.placeholder import get_placeholder_from_slot
from cms.utils.plugins import (
    copy_plugins_to_placeholder,
    downcast_plugins,
    get_plugins_as_layered_tree,
)
from cms.utils.urlutils import admin_reverse
from django.core.exceptions import FieldDoesNotExist
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models, transaction
from django.utils.functional import cached_property
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from .fields import AttributesField
from .helpers import mark_safe_lazy

MAX_LENGTH = 256


def can_change_form(placeholder, user):
    """Placeholder check used by :class:`FormContent.placeholders`."""
    return user.has_perm(get_model_permission_codename(FormContent, "change"))


class Form(models.Model):
    """A form, independent of where it is shown."""

    CREATION_BY_EDITOR = "editor"
    CREATION_BY_CONVERSION = "conversion"
    CREATION_METHODS = (
        (CREATION_BY_EDITOR, _("in the form editor")),
        (CREATION_BY_CONVERSION, _("converted from a form plugin")),
    )

    form_name = models.SlugField(
        verbose_name=_("Form identifier"),
        max_length=MAX_LENGTH,
        unique=True,
        help_text=_(
            "Slug that uniquely identifies this form. Form submissions are "
            "filed under this name, so changing it separates new submissions "
            "from the ones collected so far."
        ),
    )
    creation_method = models.CharField(
        verbose_name=_("Creation method"),
        choices=CREATION_METHODS,
        default=CREATION_BY_EDITOR,
        max_length=20,
        blank=True,
    )

    class Meta:
        verbose_name = _("form")
        verbose_name_plural = _("forms")
        ordering = ["form_name"]

    def __init__(self, *args, **kwargs):
        self._content_cache = None
        self._draft_content_cache = None
        super().__init__(*args, **kwargs)

    def __str__(self):
        return self.name

    @cached_property
    def name(self):
        content = self.get_content(show_draft_content=True)
        return getattr(content, "name", None) or self.form_name

    @cached_property
    def is_in_use(self):
        return self.cms_plugins.exists()

    @cached_property
    def objects_using(self):
        """The objects (pages, aliases, ...) whose placeholders show this form."""
        objects = set()
        object_ids = defaultdict(set)
        plugins = self.cms_plugins.select_related("placeholder").prefetch_related(
            "placeholder__source"
        )
        for plugin in plugins:
            obj = plugin.placeholder.source
            if obj is None:  # e.g. the clipboard
                continue
            class_name = obj.__class__.__name__
            if class_name.endswith("Content"):
                # Group content objects by what they are content of, so a page
                # is listed once instead of once per language.
                attr_name = class_name[: -len("Content")].lower()
                try:
                    grouper_model = obj._meta.get_field(attr_name).related_model
                except FieldDoesNotExist:
                    objects.add(obj)
                    continue
                grouper_id = getattr(obj, f"{attr_name}_id", None)
                if grouper_id:
                    object_ids[grouper_model].add(grouper_id)
                else:
                    objects.add(obj)
            else:
                objects.add(obj)
        objects.update(
            obj
            for model_class, ids in object_ids.items()
            for obj in model_class.objects.filter(pk__in=ids)
        )
        return list(objects)

    def get_admin_change_url(self):
        return admin_reverse("djangocms_form_builder_form_change", args=[self.pk])

    def get_content(self, show_draft_content=False):
        """The form's content object, or ``None`` if there is none (yet).

        Without versioning there is exactly one; with versioning
        ``show_draft_content`` picks the version an editor is working on over
        the published one.
        """
        if show_draft_content:
            if self._draft_content_cache is None:
                self._draft_content_cache = (
                    self.contents(manager="admin_manager").latest_content().first()
                )
            return self._draft_content_cache
        if self._content_cache is None:
            self._content_cache = self.contents.first()
        return self._content_cache

    def get_placeholder(self, show_draft_content=False):
        content = self.get_content(show_draft_content=show_draft_content)
        return content.placeholder if content else None

    def get_plugins(self, language=None, show_draft_content=False):
        content = self.get_content(show_draft_content=show_draft_content)
        return content.get_plugins(language) if content else []

    def clear_cache(self):
        self._content_cache = None
        self._draft_content_cache = None
        self.__dict__.pop("name", None)
        self.__dict__.pop("is_in_use", None)


class FormContentManager(WithUserMixin, models.Manager):
    """Adds ``with_user`` syntax to FormContent w/o using versioning."""


class FormContent(models.Model):
    """The editable part of a form: its settings and its field plugins."""

    form = models.ForeignKey(
        Form,
        verbose_name=_("Form"),
        on_delete=models.CASCADE,
        related_name="contents",
    )
    name = models.CharField(
        verbose_name=_("Name"),
        max_length=MAX_LENGTH,
        help_text=_("Shown to editors when they pick a form. Not shown to users."),
    )
    placeholders = PlaceholderRelationField(checks=[can_change_form])
    placeholder_slotname = "form"

    form_login_required = models.BooleanField(
        verbose_name=_("Login required to submit form"),
        blank=True,
        default=False,
        help_text=_(
            "To avoid issues with user experience use this type of form only on pages, "
            "which require login."
        ),
    )
    form_unique = models.BooleanField(
        verbose_name=_("User can reopen form"),
        default=False,
        help_text=_('Requires "Login required" to be checked to work.'),
    )
    form_floating_labels = models.BooleanField(
        verbose_name=_("Floating labels"),
        default=False,
    )
    form_spacing = models.CharField(
        verbose_name=_("Margin between fields"),
        max_length=16,
        blank=True,
    )
    form_actions = models.CharField(
        verbose_name=_("Actions to be taken after form submission"),
        blank=True,
        max_length=4 * MAX_LENGTH,
    )
    action_parameters = models.JSONField(
        default=dict,
        encoder=DjangoJSONEncoder,
        blank=True,
        null=True,
    )
    attributes = AttributesField()

    # Keep the schema independent of which captcha packages happen to be
    # installed - choices and defaults are enforced at the form level.
    captcha_widget = models.CharField(
        verbose_name=_("captcha widget"),
        max_length=16,
        blank=True,
        default="",
        help_text=mark_safe_lazy(
            _(
                'Read more in the <a href="{link}" target="_blank">documentation</a>.'
            ).format(link="https://developers.google.com/recaptcha")
        ),
    )
    captcha_requirement = models.DecimalField(
        verbose_name=_("Minimum score requirement"),
        null=True,
        blank=True,
        decimal_places=2,
        max_digits=3,
        default=0.5,
        help_text=_(
            "Only for reCaptcha v3: Minimum score required to accept challenge."
        ),
    )
    captcha_config = AttributesField(
        verbose_name=_("Recaptcha configuration parameters"),
    )

    objects = FormContentManager()
    admin_manager = ContentAdminManager()

    class Meta:
        verbose_name = _("form content")
        verbose_name_plural = _("form contents")

    def __str__(self):
        return self.name

    @cached_property
    def placeholder(self):
        placeholder = get_placeholder_from_slot(
            self.placeholders, self.placeholder_slotname
        )
        placeholder.source = self
        return placeholder

    def get_placeholders(self):
        return [self.placeholder]

    def get_placeholder_slots(self):
        return [self.placeholder_slotname]

    def get_template(self):
        return None

    def get_plugins(self, language=None):
        """The form's root plugins, downcast, with their children attached.

        Downcasting matters: only the concrete plugin models know how to turn
        themselves into a form field.
        """
        language = language or get_language()
        plugins = self.placeholder.get_plugins(language).order_by("position")
        downcast = list(downcast_plugins(plugins, placeholders=[self.placeholder]))
        return list(get_plugins_as_layered_tree(downcast))

    @property
    def form_name(self):
        """The identifier submissions are filed under. Lives on the grouper."""
        return self.form.form_name

    def get_form_class(self, request=None, language=None):
        """The Django form class this form definition describes."""
        from .form_factory import build_form_class

        return build_form_class(self, self.get_plugins(language), request=request)

    @transaction.atomic
    def populate(self, plugins):
        """Copy ``plugins`` (and their descendants) into this form.

        They keep the language they were created in: a form has no language
        of its own, its plugins carry one like any other CMS plugin.
        """
        return copy_plugins_to_placeholder(
            plugins,
            placeholder=self.placeholder,
        )


def create_version(form_content, user=None, publish=False):
    """Register a newly created form content with djangocms-versioning.

    A no-op when versioning is not enabled - then the content is live as soon
    as it exists. ``publish`` is for content that has to be live right away,
    e.g. a form converted from a plugin that was already showing on a page.
    """
    from .utils import is_versioning_enabled

    if not is_versioning_enabled():
        return None

    from djangocms_versioning.models import Version

    version = Version.objects.create(content=form_content, created_by=user)
    if publish and user is not None:
        version.publish(user)
    return version


def clear_placeholder_caches(form):
    """Invalidate the cached markup of every placeholder showing ``form``.

    A form's fields are rendered into the placeholder cache of the page (or
    other object) showing it, not into a cache of their own - so a change to
    the form does not reach visitors until those caches are cleared.
    """
    placeholders = {}
    for plugin in form.cms_plugins.select_related("placeholder"):
        placeholders.setdefault(
            (plugin.placeholder_id, plugin.language), plugin.placeholder
        )
    for (_placeholder_id, language), placeholder in placeholders.items():
        placeholder.clear_cache(language)


def on_form_content_publish(version):
    """djangocms-versioning hook: visitors now see a different version."""
    clear_placeholder_caches(version.content.form)
