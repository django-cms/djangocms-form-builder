########################
 django CMS form builder
########################

|pypi| |coverage| |python| |django| |djangocms|

**djangocms-form-builder** supports rendering of styled forms. The objective is to tightly integrate forms in the website design. **djangocms-form-builder** allows as many forms as you wish on one page. All forms are **xhr-based**. To this end, **djangocms-form-builder** extends the django CMS plugin model allowing a form plugin to receive xhr post requests.

There are two different ways to manage forms with **djangocms-form-builder**:

1. **Building a form with django CMS' powerful structure board.** This is fast an easy. It integrates smoothly with other design elements, especially the grid elements allowing to design simple responsive forms.

   Form actions can be configured by form. Built in actions include saving the    results in the database for later evaluation and mailing submitted forms to   the site admins. Other form actions can be registered.

2. Works with **django CMS v4+** and **djangocms-alias** to manage your forms centrally. Djangocms-alias becomes your form editor and forms can be placed on pages by referring to them with their alias.

3. **Registering an application-specific form with djangocms-form-builder.** If you already have forms you may register them with djangocms-form-builder and allow editors to use them in the form plugin. If you only have simpler design requirements, **djangocms-form-builder** allows you to use fieldsets as with admin forms.

**************
 Key features
**************

-  Supports `Bootstrap 5 <https://getbootstrap.com>`_.

-  Open architecture to support other css frameworks.

-  Integrates with `django-crispy-forms <https://github.com/django-crispy-forms/django-crispy-forms>`_

- Integrates with `djangocms-frontend <https://github.com/django-cms/djangocms-frontend>`_


Feedback
========

This project is in a early stage. All feedback is welcome! Please mail me at fsbraun(at)gmx.de

Also, all contributions are welcome.

Contributing
============

This is a an open-source project. We'll be delighted to receive your feedback in the form of issues and pull requests. Before submitting your pull request, please review our `contribution guidelines <http://docs.django-cms.org/en/latest/contributing/index.html>`_.

We're grateful to all contributors who have helped create and maintain this package. Contributors are listed at the `contributors <https://github.com/fsbraun/djangocms-form-builder/graphs/contributors>`_ section.


************
Installation
************

For a manual install:

- run ``pip install djangocms-form-builder``, **or**

-  run ``pip install git+https://github.com/django-cms/djangocms-form-builder@main#egg=djangocms-form-builder``

-  add ``djangocms_form_builder`` to your ``INSTALLED_APPS``. (If you are using both djangocms-frontend and djangocms-form-builder, add it **after** djangocms-frontend

-  run ``python manage.py migrate``

*****
Usage
*****

Creating forms using django CMS' structure board
================================================

First create a ``Form`` plugin to add a form. Each form created with help of the structure board needs a unique identifier (formatted as a slug).

Add form fields by adding child classes to the form plugin. Child classes can be form fields but also any other CMS Plugin. CMS Plugins may, e.g., be used to add custom formatting or additional help texts to a form.

Form fields
-----------

Currently the following form fields are supported:

* CharField, EmailField, URLField
* DecimalField, IntegerField
* Textarea
* DateField, DateTimeField, TimeField
* SelectField
* BooleanField

A Form plugin must not be used within another Form plugin.

Actions
-------

Upon submission of a valid form actions can be performed.

Four actions come with djangocms-form-builder comes with four actions built-in

* **Save form submission** - Saves each form submission to the database. See the
  results in the admin interface.
* **Send email** - Sends an email to the site admins with the form data.
* **Success message** - Specify a message to be shown to the user upon
  successful form submission.
* **Redirect after submission** - Specify a link to a page where the user is
  redirected after successful form submission.

Actions can be configured in the form plugin.

A project can register as many actions as it likes::

    from djangocms_form_builder import actions

    @actions.register
    class MyAction(actions.FormAction):
        verbose_name = _("Everything included action")

        def execute(self, form, request):
            ...  # This method is run upon successful submission of the form


To add this action, might need to be added to your project only after all Django apps have loaded at startup.
You can put these actions in your apps models.py file. Another options is your apps, apps.py file::

    from django.apps import AppConfig

    class MyAppConfig(AppConfig):
        default_auto_field = 'django.db.models.BigAutoField'
        name = 'myapp'
        label = 'myapp'
        verbose_name = _("My App")

        def ready(self):
            super().ready()

            from djangocms_form_builder import actions

            @actions.register
            class MyAction(actions.FormAction):  # Or import from within the ready method
                verbose_name = _("Everything included action")

                def execute(self, form, request):
                    ...  # This method is run upon successful submission of the form
                    # Process form and request data, you can send an email to the person who filled the form
                    # Or admins though that functionality is available from the default SendMailAction



Using (existing) Django forms with djangocms-form-builder
=========================================================

The ``Form`` plugin also provides access to Django forms if they are registered with djangocms-form-builder::

    from djangocms_form_builder import register_with_form_builder

    @register_with_form_builder
    class MyGreatForm(forms.Form):
        ...

Alternatively you can also register at any other place in the code by running ``register_with_form_builder(AnotherGreatForm)``.

By default the class name is translated to a human readable form (``MyGreatForm`` -> ``"My Great Form"``). Additional information may be added using Meta classes::

    @register_with_form_builder
    class MyGreatForm(forms.Form):
        class Meta:
            verbose_name = _("My great form")  # can be localized
            redirect = "https://somewhere.org"  # string or object with get_absolute_url() method
            floating_labels = True  # switch on floating labels
            field_sep = "mb-3"  # separator used between fields (depends on css framework)

The verbose name will be shown in a Select field of the Form plugin.

Upon form submission a ``save()`` method of the form (if it has one). After executing the ``save()`` method the user is redirected to the url given in the  ``redirect`` attribute.

Actions are not available for Django forms. Any actions to be performed upon submission should reside in its ``save()`` method.

Tests
=====

Install test dependencies:

.. code-block:: bash

    python3 -m venv .venv
    . .venv/bin/activate
    python3 -m pip install -e ".[altcha,tests]"
    python3 -m pip install djangocms_versioning

To launch the tests, run:

.. code-block:: bash

    . .venv/bin/activate
    python3 run_tests.py

Configuring Altcha CAPTCHA
==========================

`Altcha <https://altcha.org/>`_ is an open-source, GDPR-compliant, Proof-of-Work CAPTCHA: no tracking, no cookies, and no external calls when used in built-in mode. For widget and integration details, see the `Altcha documentation <https://altcha.org/docs/v2/>`_.

**djangocms-form-builder** integrates `django-altcha <https://github.com/aboutcode-org/django-altcha/tree/main>`_ so you can add Altcha to form plugins. You can use either Django’s built-in challenge view (fully self-hosted) or an external challenge server such as `Altcha Sentinel <https://altcha.org/>`_.

**1. Install and enable django-altcha**

-  Install the package (e.g. ``pip install django-altcha`` from the `django-altcha repository <https://github.com/aboutcode-org/django-altcha/tree/main>`_).
-  Add ``django_altcha`` to ``INSTALLED_APPS`` and follow the `django-altcha configuration instructions <https://github.com/aboutcode-org/django-altcha/tree/main>`_.

**2. Configure where challenges come from**

You can either have Django generate challenges (built-in) or use an external challenge server (e.g. Altcha Sentinel).

**Option A — Django generates challenges (built-in, no external service)**

Add a URL route so the widget can request a new challenge::

    from django.urls import path
    from django_altcha import AltchaChallengeView

    urlpatterns = [
        path("altcha/challenge/", AltchaChallengeView.as_view(), name="altcha_challenge"),
    ]

In your project settings, point the widget to that URL and set a secret HMAC key (see django-altcha docs to generate one)::

    from django.urls import reverse_lazy

    ALTCHA_HMAC_KEY = "your-secret-hmac-key"  # required for built-in mode
    ALTCHA_FIELD_OPTIONS = {
        "challengeurl": reverse_lazy("altcha_challenge"),
    }

**Option B — External challenge server (e.g. Altcha Sentinel)**

If you use an external API to generate challenges, set only the challenge URL (no ``ALTCHA_HMAC_KEY`` needed)::

    ALTCHA_FIELD_OPTIONS = {
        "challengeurl": "https://altcha.your-domain.example/api/v1/challenge?apiKey=YOUR_API_KEY",
    }

**3. Use Altcha in the form plugin**

In the form plugin settings in the CMS, choose **Altcha** as the captcha widget.

**Recommended Django settings**

-  **ALTCHA_HMAC_KEY** — required only for Option A (built-in challenges). Keep it secret.
-  **ALTCHA_INCLUDE_TRANSLATIONS** — set to ``True`` to load Altcha UI translations (e.g. checkbox label in the user’s language).

**ALTCHA_FIELD_OPTIONS**

The setting **ALTCHA_FIELD_OPTIONS** lets you override the default options passed to django-altcha's ``AltchaField``. It is a dictionary of options supported by the field (see `AltchaField.default_options <https://github.com/aboutcode-org/django-altcha/blob/main/django_altcha/__init__.py#L134>`_). Example: enable floating UI and French language::

    ALTCHA_FIELD_OPTIONS = {"challengeurl": reverse_lazy("altcha_challenge"), "floating": True, "language": "fr"}

**Workaround: Altcha script URLs (django-altcha)**

Some **django-altcha** versions have static urls of JS files hardcoded, which create an issue when using in production environments. A fix is tracked in `django-altcha PR #38 <https://github.com/aboutcode-org/django-altcha/pull/38>`_.

Until that ships in a release, override ``ALTCHA_JS_URL`` and ``ALTCHA_JS_TRANSLATIONS_URL`` so URLs are resolved lazily when the widget renders. You can do this in your project settings.py file:

    def _lazy_static(path):
        """Resolve static(path) only when stringified (e.g. in templates)."""

        class _LazyStaticUrl:
            __slots__ = ("_path",)

            def __init__(self, path):
                self._path = path

            def __str__(self):
                from django.templatetags.static import static

                return static(self._path)

        return _LazyStaticUrl(path)

    ALTCHA_JS_URL = _lazy_static("altcha/altcha.min.js")
    ALTCHA_JS_TRANSLATIONS_URL = _lazy_static("altcha/dist_i18n/all.min.js")


.. |pypi| image:: https://badge.fury.io/py/djangocms-form-builder.svg
   :target: http://badge.fury.io/py/djangocms-form-builder

.. |coverage| image:: https://codecov.io/gh/django-cms/djangocms-form-builder/branch/main/graph/badge.svg
   :target: https://codecov.io/gh/django-cms/djangocms-form-builder

.. |python| image:: https://img.shields.io/pypi/pyversions/djangocms-form-builder
    :alt: PyPI - Python Version
    :target: https://pypi.org/project/djangocms-form-builder/

.. |django| image:: https://img.shields.io/pypi/frameworkversions/django/djangocms-form-builder
    :alt: PyPI - Django Versions from Framework Classifiers
    :target: https://www.djangoproject.com/

.. |djangocms| image:: https://img.shields.io/pypi/frameworkversions/django-cms/djangocms-form-builder
    :alt: PyPI - django CMS Versions from Framework Classifiers
    :target: https://www.django-cms.org/
