Settings
########

All settings are optional. Unless noted otherwise they are read once, when
``djangocms_form_builder.settings`` is first imported.

Forms and rendering
===================

``DJANGOCMS_FORM_BUILDER_FRONTEND``
   Selects the form templates and widget rendering. If unset, it uses
   ``DJANGOCMS_FRONTEND_FRAMEWORK``, falling back to ``"bootstrap5"``. The
   included frontends are ``"bootstrap5"`` and, when the optional dependency is
   installed, ``"django_formset"``. See
   :doc:`../how-to/use-django-formset`.

``DJANGOCMS_FRONTEND_FRAMEWORK``
   Compatibility fallback for selecting the frontend and the CSS framework
   used by djangocms-frontend. Prefer ``DJANGOCMS_FORM_BUILDER_FRONTEND`` when
   changing form rendering only.

``DJANGOCMS_FRONTEND_THEME``
   Module that may provide additional render mixins for the field plugins.
   Default ``"djangocms_frontend"``. Mixins are looked up as
   ``<theme>.frameworks.<framework>.<name>RenderMixin``; a module that cannot be
   imported is ignored.

``FORM_TEMPLATE``
   Template used by the ``render_form`` template tag. Default
   ``"djangocms_form_builder/<framework>/render/form.html"``.

``DJANGO_FORM_BUILDER_SPACER_CHOICES``
   Choices for the form plugin's *Margin between fields*. If unset,
   ``DJANGOCMS_FRONTEND_SPACER_SIZES`` is used, whose keys are turned into
   ``mb-<key>`` classes. If that is unset too, the only choice is
   ``(("mb-3", "Default"),)``.

``DJANGOCMS_FORM_BUILDER_COLOR_STYLE_CHOICES``
   Choices for the submit button plugin's *Button context*. Falls back to
   ``DJANGOCMS_FRONTEND_COLOR_STYLE_CHOICES``, and then to *Primary* and
   *Secondary*.

   .. note::

      This is the name read for ``bootstrap5``. The ``foundation6`` module reads
      ``DJANGO_FORM_BUILDER_COLOR_STYLE_CHOICES`` (without ``CMS``) instead, and
      prefixes values taken from ``DJANGOCMS_FRONTEND_COLOR_STYLE_CHOICES`` with
      ``mb-``.

``DJANGOCMS_FORMS_OPTIONS``
   Dictionary of project-wide defaults for the per-form options described in
   :ref:`form-options`. A form's own ``Meta.options`` takes precedence.
   Default ``{}``.

.. _form-options:

Form options
------------

Options travel with a form as ``Meta.options`` and are read through
``djangocms_form_builder.helpers.get_option``, which falls back to
``DJANGOCMS_FORMS_OPTIONS``. The form plugin fills them in for forms it builds
from field plugins; a form your project registers sets them itself, see
:doc:`../how-to/use-a-django-form`.

``form_name``
   The form identifier. Submissions are stored under it.

``login_required``, ``unique``
   Whether submitting requires a login, and whether a logged-in user reopens
   their previous submission instead of starting a new one.

``form_actions``
   List of hashes of the actions to run.

``form_parameters``
   Dictionary with the values editors entered for action fields; read by
   ``FormAction.get_parameter()``.

``redirect``
   URL, URL name or object with ``get_absolute_url()`` to send the visitor to
   after a successful submission. The form plugin presets this to ``"result"``,
   which reloads the current page.

``render_success``
   Template rendered instead of the form after a successful submission. If the
   form has a ``slug`` attribute, ``render_success_<slug>`` and
   ``get_success_context_<slug>`` are used instead.

``floating_labels``, ``field_sep``
   Rendering options, see :doc:`../how-to/style-forms`.

``crispy_form``
   Render with django-crispy-forms even if the form has no ``helper``.

Mails
=====

``DJANGOCMS_MAIL_TEMPLATE_SETS``
   Template sets offered by the **Send email** action, as ``(key, verbose
   name)`` pairs. Default ``(("default", _("Default")),)``. Editors only see the
   choice if there is more than one set.

   Each key needs an HTML body at
   ``djangocms_form_builder/mails/<key>/mail_html.html``; the package ships one
   for ``default``. ``mail.txt`` and ``subject.txt`` in the same directory are
   optional - without them the text body is derived from the HTML body and the
   subject is ``"<form name> form submission"``.

``DJANGOCMS_CONFIRMATION_MAIL_TEMPLATE_SETS``
   Template sets for the **Send confirmation email to submitter** action, as
   ``(key, verbose name)`` pairs. Empty by default, which keeps the action
   unregistered. Keys must be slugs; a key that is not raises
   ``ImproperlyConfigured``. See :doc:`../how-to/send-confirmation-mail`.

``DJANGOCMS_CONFIRMATION_MAIL_FIELD_NAME``
   Name of the form field carrying the recipient address. Default ``"email"``.

``DJANGOCMS_CONFIRMATION_MAIL_WORKERS``
   Threads sending confirmation mails. Default ``2``. Read on first use.

``DJANGOCMS_CONFIRMATION_MAIL_MAX_PENDING``
   Mails that may wait for delivery at a time. Default ``10``. Read on first
   use.

Confirmation mails are sent through Django's mail backend with
``DEFAULT_FROM_EMAIL`` as sender.

Rate limits
===========

``DJANGOCMS_FORM_BUILDER_RATE_LIMITS``
   ``{action class name or "default": {kind: (limit, window in seconds)}}``.
   Default ``{}``. ``None`` as a value switches an action's built-in limit off.
   The structure is validated on import; a malformed entry raises
   ``ImproperlyConfigured``.

``DJANGOCMS_FORM_BUILDER_RATE_LIMIT_IP_META_KEY``
   ``request.META`` key identifying the submitting client. Default
   ``"REMOTE_ADDR"``.

See :doc:`../how-to/rate-limit-actions`.

File uploads
============

``DJANGOCMS_FORM_BUILDER_FILE_FIELD_STORAGE``
   Storage instance used to save, address and delete uploaded files. Defaults to
   ``django.core.files.storage.default_storage``, which usually makes uploads
   publicly readable.

``DJANGOCMS_FORM_BUILDER_FILE_VALIDATION_PRESETS``
   Named validation rules offered in the upload plugins. Default ``{}``, read on
   each use. Format in :doc:`file-validation`.

Captcha
=======

``ALTCHA_FIELD_OPTIONS``
   Dictionary passed to django-altcha's ``AltchaField`` unchanged. Default
   ``{}``.

``RECAPTCHA_PUBLIC_KEY``, ``RECAPTCHA_PRIVATE_KEY``
   Belong to django-recaptcha. The form plugin checks whether both are present
   and warns editors if they are not.

Django settings that matter
===========================

``CSRF_COOKIE_HTTPONLY``
   When ``True``, the form renders its CSRF token inline, the form plugin is
   excluded from the CMS plugin cache, and the JSON ``GET`` endpoint refuses to
   hand out a token (``405``). When ``False`` (the default), the plugin's HTML
   is cacheable and the token is fetched at submit time.

   The django-formset frontend always embeds a token for its web component and
   therefore always disables plugin caching, independently of this setting.

``DATA_UPLOAD_MAX_MEMORY_SIZE``, ``FILE_UPLOAD_MAX_MEMORY_SIZE``, ``DATA_UPLOAD_MAX_NUMBER_FIELDS``
   Django's own upload limits. They apply to every submission, whether or not a
   validation preset is selected.
