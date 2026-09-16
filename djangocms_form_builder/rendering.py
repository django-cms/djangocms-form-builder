"""Rendering of the form editor, i.e. of a form object in its own right."""

from cms.utils import get_language_from_request
from django.template.response import TemplateResponse

from . import recaptcha
from .form_factory import build_form_class


def render_form_content(request, form_content):
    """django CMS' frontend-editing endpoint for a :class:`FormContent`.

    The editor sees the form as a visitor would - the field plugins render
    their widgets against a real (unbound) form - while the structure board
    lets them add, move and configure the fields.
    """
    # A form is built per language inside one form object, so the editor shows
    # the plugins of the language it is being edited in.
    plugins = form_content.get_plugins(get_language_from_request(request))
    form_class = build_form_class(form_content, plugins, request=request)
    return TemplateResponse(
        request,
        "djangocms_form_builder/form_content.html",
        {
            "form_content": form_content,
            # Field plugins look for "instance" (their own) and "form" (ours).
            "form": form_class(request=request, label_suffix=""),
            "form_plugins": plugins,
            "RECAPTCHA_PUBLIC_KEY": recaptcha.RECAPTCHA_PUBLIC_KEY,
        },
    )
