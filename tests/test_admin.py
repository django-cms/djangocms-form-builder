import decimal

from django.contrib.auth import get_user_model
from django.contrib.admin.sites import site
from django.test import TestCase, RequestFactory
from django.urls import reverse

from djangocms_form_builder.models import FormEntry


class FormEntryAdminTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="pass"
        )
        self.user1 = User.objects.create_user(
            username="alice", email="alice@example.com", password="pass"
        )
        self.user2 = User.objects.create_user(
            username="bob", email="bob@example.com", password="pass"
        )
        self.client.force_login(self.admin_user)
        self.factory = RequestFactory()

    def test_changelist_renders_and_lists_entries(self):
        e1 = FormEntry.objects.create(
            form_name="form-a",
            form_user=self.user1,
            entry_data={"name": "John"},
        )
        e2 = FormEntry.objects.create(
            form_name="form-b",
            form_user=self.user2,
            entry_data={"name": "Jane"},
        )

        url = reverse("admin:djangocms_form_builder_formentry_changelist")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        # list_display includes __str__ representation and form_user
        self.assertContains(resp, str(e1))
        self.assertContains(resp, str(e2))
        self.assertContains(resp, self.user1.username)
        self.assertContains(resp, self.user2.username)

    def test_add_permission_is_denied(self):
        url = reverse("admin:djangocms_form_builder_formentry_add")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)

        # No "Add" button on changelist
        cl_url = reverse("admin:djangocms_form_builder_formentry_changelist")
        cl_resp = self.client.get(cl_url)
        addlink = reverse("admin:djangocms_form_builder_formentry_add")
        self.assertNotContains(cl_resp, addlink)

    def test_change_view_shows_dynamic_fields_and_readonly(self):
        entry = FormEntry.objects.create(
            form_name="contact",
            form_user=self.user1,
            entry_data={
                "name": "John Doe",
                "tags": ["a", "b"],
                "agree": True,
                "price": decimal.Decimal("12.50"),
            },
        )

        url = reverse("admin:djangocms_form_builder_formentry_change", args=[entry.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        # Dynamic fields from entry_data are rendered
        self.assertContains(resp, 'name="name"')
        self.assertContains(resp, 'name="tags"')
        self.assertContains(resp, 'name="agree"')
        self.assertContains(resp, 'name="price"')

        # Readonly fields should not be editable inputs
        self.assertNotContains(resp, 'name="form_name"')
        self.assertNotContains(resp, 'name="form_user"')

    def test_change_post_updates_entangled_entry_data(self):
        entry = FormEntry.objects.create(
            form_name="contact",
            form_user=self.user1,
            entry_data={
                "name": "John Doe",
                "tags": ["a", "b"],
                "agree": False,
                "price": decimal.Decimal("12.50"),
            },
        )
        url = reverse("admin:djangocms_form_builder_formentry_change", args=[entry.pk])
        post_data = {
            "name": "Jane Roe",
            "tags": "x, y",
            "agree": "on",
            "price": "12.50",
            "_save": "Save",
        }
        resp = self.client.post(url, post_data, follow=True)
        self.assertEqual(resp.status_code, 200)

        entry.refresh_from_db()
        self.assertEqual(entry.entry_data.get("name"), "Jane Roe")
        self.assertEqual(entry.entry_data.get("tags"), ["x", "y"])
        self.assertEqual(entry.entry_data.get("agree"), True)
        self.assertEqual(entry.entry_data.get("price"), str(decimal.Decimal("12.50")))

    def test_admin_configuration_and_dynamic_form(self):
        # sanity-check admin class settings and dynamic form/fieldsets
        admin_instance = site._registry[FormEntry]
        self.assertEqual(admin_instance.date_hierarchy, "entry_created_at")
        self.assertIn("form_user", admin_instance.list_display)
        self.assertIn("entry_created_at", admin_instance.list_filter)
        self.assertIn("form_name", admin_instance.readonly_fields)

        entry = FormEntry.objects.create(
            form_name="feedback",
            form_user=self.user2,
            entry_data={
                "comment": "Nice",
                "notify": True,
                "score": 3,
            },
        )

        request = self.factory.get("/")
        form_class = admin_instance.get_form(request, obj=entry)
        self.assertTrue(issubclass(form_class, object))
        form = form_class()
        # form fields populated from entry_data
        self.assertIn("comment", form.fields)
        self.assertIn("notify", form.fields)
        self.assertIn("score", form.fields)

        # fieldsets include only str/list/tuple/bool
        fieldsets = admin_instance.get_fieldsets(request, obj=entry)
        self.assertEqual(fieldsets[0][1]["fields"], (("form_name", "form_user"),))
        data_fields = fieldsets[1][1]["fields"]
        self.assertIn("comment", data_fields)
        self.assertIn("notify", data_fields)
        self.assertIn("score", data_fields)
