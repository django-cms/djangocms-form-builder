"""Rendering of the form editor, i.e. of a form object in its own right."""

from cms.utils import get_language_from_request
from django.conf import settings as django_settings
from django.template.response import TemplateResponse

from . import recaptcha, settings
from .form_factory import build_form_class, has_plugin_of_type


def render_form_content(request, form_content):
    """django CMS' frontend-editing endpoint for a :class:`FormContent`.

    The editor sees the form as a visitor would - it is rendered by the same
    template as on a page, the field plugins render their widgets against a
    real (unbound) form - while the structure board lets them add, move and
    configure the fields. The form is not submitted from here.
    """
    # A form is built per language inside one form object, so the editor shows
    # the plugins of the language it is being edited in.
    language = get_language_from_request(request)
    plugins = form_content.get_plugins(language)
    form_class = build_form_class(form_content, plugins, request=request)
    return TemplateResponse(
        request,
        "djangocms_form_builder/form_content.html",
        {
            "form_content": form_content,
            "form_template": f"djangocms_form_builder/{settings.framework}/form.html",
            "form_preview": True,
            "uid": f"-form-content-{form_content.pk}",
            # Field plugins look for "instance" (their own) and "form" (ours).
            "form": form_class(request=request, label_suffix=""),
            "form_plugins": plugins,
            "form_language": language,
            "has_submit_button": has_plugin_of_type(plugins, "SubmitPlugin"),
            "has_captcha_plugin": has_plugin_of_type(plugins, "CaptchaPlugin"),
            "captcha_widget": form_content.captcha_widget,
            "csrf_cookie_httponly": django_settings.CSRF_COOKIE_HTTPONLY,
            "RECAPTCHA_PUBLIC_KEY": recaptcha.RECAPTCHA_PUBLIC_KEY,
        },
    )
