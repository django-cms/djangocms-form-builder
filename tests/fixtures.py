from cms.api import create_page
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site

#: Whether form (and page) contents are versioned in this test run.
VERSIONING = apps.is_installed("djangocms_versioning")
DJANGO_CMS4 = VERSIONING  # Kept for tests importing the old name


class TestFixture:
    """Sets up generic setUp and tearDown methods for tests."""

    def setUp(self):
        self.language = "en"
        self.superuser = self.get_superuser()
        self.default_site = Site.objects.first()
        self.home = self.create_page(
            title="home",
            template="page.html",
        )
        self.publish(self.home, self.language)
        self.page = self.create_page(
            title="content",
            template="page.html",
        )
        self.publish(self.page, self.language)
        self.placeholder = self.get_placeholders(self.page).get(slot="content")
        self.request_url = (
            self.page.get_absolute_url(self.language) + "?toolbar_off=true"
        )
        return super().setUp()

    def tearDown(self):
        self.page.delete()
        self.home.delete()
        if VERSIONING:
            from djangocms_versioning.models import Version

            # Versions copied from another version protect their source, so
            # the derived ones have to go first.
            Version.objects.filter(source__isnull=False).delete()
            Version.objects.all().delete()
        self.superuser.delete()

        return super().tearDown()

    def create_form(self, form_name="test-form", name="Test form", **kwargs):
        """A form object with one (draft) content object."""
        from djangocms_form_builder.models import Form, FormContent

        form = Form.objects.create(form_name=form_name, **kwargs.pop("form_kwargs", {}))
        content = FormContent.objects.create(form=form, name=name, **kwargs)
        if VERSIONING:
            from djangocms_versioning.constants import DRAFT
            from djangocms_versioning.models import Version

            Version.objects.create(
                content=content,
                created_by=self.superuser,
                state=DRAFT,
                content_type_id=ContentType.objects.get_for_model(FormContent).id,
            )
        return form, content

    def create_page(self, title, **kwargs):
        kwargs.setdefault("language", self.language)
        kwargs.setdefault("created_by", self.superuser)
        kwargs.setdefault("in_navigation", True)
        kwargs.setdefault("limit_visibility_in_menu", None)
        kwargs.setdefault("menu_title", title)
        return create_page(title=title, **kwargs)

    def get_placeholders(self, page):
        return page.get_placeholders(self.language)

    def get_draft_placeholders(self, page):
        """Placeholders of a page that has not been published (yet)."""
        from cms.models import PageContent

        content = PageContent.admin_manager.get(page=page, language=self.language)
        return content.placeholders

    if VERSIONING:

        def _get_version(self, grouper, version_state, language=None):
            language = language or self.language

            from djangocms_versioning.models import Version

            versions = Version.objects.filter_by_grouper(grouper).filter(
                state=version_state
            )
            for version in versions:
                # Content that has no language of its own - a form - has a
                # single version chain, so any version of it matches.
                content_language = getattr(version.content, "language", None)
                if content_language in (None, language):
                    return version

        def publish(self, grouper, language=None):
            from djangocms_versioning.constants import DRAFT

            version = self._get_version(grouper, DRAFT, language)
            if version is not None:
                version.publish(self.superuser)

        def unpublish(self, grouper, language=None):
            from djangocms_versioning.constants import PUBLISHED

            version = self._get_version(grouper, PUBLISHED, language)
            if version is not None:
                version.unpublish(self.superuser)

        def create_url(
            self,
            site=None,
            content_object=None,
            manual_url="",
            relative_path="",
            phone="",
            mailto="",
            anchor="",
        ):
            from djangocms_url_manager.models import Url, UrlGrouper
            from djangocms_url_manager.utils import is_versioning_enabled
            from djangocms_versioning.constants import DRAFT
            from djangocms_versioning.models import Version

            if site is None:
                site = self.default_site

            url = Url.objects.create(
                site=site,
                content_object=content_object,
                manual_url=manual_url,
                relative_path=relative_path,
                phone=phone,
                mailto=mailto,
                anchor=anchor,
                url_grouper=UrlGrouper.objects.create(),
            )
            if is_versioning_enabled():
                Version.objects.create(
                    content=url,
                    created_by=self.superuser,
                    state=DRAFT,
                    content_type_id=ContentType.objects.get_for_model(Url).id,
                )

            return url

        def delete_urls(self):
            from djangocms_url_manager.models import Url

            Url.objects.all().delete()

    else:  # Without djangocms-versioning every object is live right away.

        def publish(self, grouper, language=None):
            pass

        def unpublish(self, grouper, language=None):
            pass
