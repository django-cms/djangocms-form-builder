"""Render production templates for browser tests without a running CMS/database."""

import os
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ["DJANGO_SETTINGS_MODULE"] = "tests.test_settings"
os.environ["DJANGOCMS_FORM_BUILDER_FRONTEND"] = "django_formset"

import django  # noqa: E402
from django.conf import settings  # noqa: E402

settings.DATABASES["default"]["NAME"] = ":memory:"
django.setup()

import formset  # noqa: E402
from django import forms  # noqa: E402
from django.template import Template  # noqa: E402
from django.template.loader import render_to_string  # noqa: E402
from django.test import RequestFactory  # noqa: E402
from django.utils.safestring import mark_safe  # noqa: E402
from sekizai.context import SekizaiContext  # noqa: E402

from djangocms_form_builder import recaptcha  # noqa: E402
from djangocms_form_builder.cms_plugins.ajax_plugins import CMSAjaxForm  # noqa: E402

DEST = Path(__file__).parent / ".generated"
DEST.mkdir(exist_ok=True)
shutil.copytree(Path(formset.__file__).parent / "static", DEST, dirs_exist_ok=True)
shutil.copytree(ROOT / "djangocms_form_builder/static", DEST, dirs_exist_ok=True)


class ContactForm(forms.Form):
    name = forms.CharField(min_length=2)
    email = forms.EmailField(required=False)


class CaptchaWidget(forms.TextInput):
    def render(self, name, value, attrs=None, renderer=None):
        # The provider's explicit-render placeholder, initialized by ajax_form.js.
        includes = render_to_string("captcha/includes/js_v2_invisible.html")
        return mark_safe(
            includes + '<div class="g-recaptcha" data-size="invisible"></div>'
        )


class CaptchaField(forms.CharField):
    widget = CaptchaWidget


class ProtectedForm(ContactForm):
    captcha_field = CaptchaField()


template = Template(
    '{% load sekizai_tags %}<html><head>{% render_block "css" %}</head><body>'
    '{% include "djangocms_form_builder/django_formset/form.html" %}'
    '{% render_block "js" %}</body></html>'
)
for name, form in [
    ("basic", ContactForm()),
    ("prefix", ContactForm(prefix="contact")),
    ("captcha", ProtectedForm()),
]:
    request = RequestFactory().get("/")
    instance = SimpleNamespace(
        id=1,
        child_plugin_instances=[],
        captcha_widget="v2-invisible" if name == "captcha" else "",
    )
    plugin = CMSAjaxForm(model=None, admin_site=None)
    plugin.get_ajax_form = lambda: form
    context = SekizaiContext({"request": request})
    with patch.dict(recaptcha.CAPTCHA_FIELDS, {"v2-invisible": CaptchaField}):
        plugin.render(context, instance, None)
    html = template.render(context)
    (DEST / f"{name}.html").write_text(html)
    if name == "basic":
        # Exercise the editor-added Submit plugin's separate production template.
        submit = render_to_string(
            "djangocms_form_builder/django_formset/widgets/submit.html",
            {
                "use_django_formset": True,
                "form": form,
                "instance": {
                    "config": {"submit_cta": "Send message"},
                    "form_submit_context": "primary",
                },
            },
        )
        start = html.index('<button type="submit"')
        end = html.index("</button>", start) + len("</button>")
        (DEST / "custom.html").write_text(html[:start] + submit + html[end:])
print(f"Rendered browser fixtures in {DEST}")
