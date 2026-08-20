Protect a form with a captcha
#############################

A form that anyone can reach will be found by bots. **djangocms-form-builder**
can add a captcha field to a form, but it ships no captcha implementation of its
own: install one of the supported packages and the option appears.

Install a provider
==================

Three providers are recognised. The app checks whether their Django app is
installed:

.. list-table::
   :header-rows: 1

   * - Package
     - App in ``INSTALLED_APPS``
     - Choices offered
   * - `django-altcha <https://github.com/aboutcode-org/django-altcha>`_
     - ``django_altcha``
     - *Altcha*
   * - `django-recaptcha <https://github.com/django-recaptcha/django-recaptcha>`_
     - ``captcha``
     - *reCaptcha - v2 checkbox*, *reCaptcha - v2 invisible*
   * - a package providing ``hcaptcha.fields.hCaptchaField``
     - ``hcaptcha``
     - *hCaptcha*

Altcha is the recommended default: it is open source, needs no third-party
service in its built-in mode, and is installable as an extra of this package:

.. code-block:: bash

   pip install djangocms-form-builder[altcha]

``django-recaptcha`` is available as the ``reCaptcha`` extra.

Switch the captcha on
=====================

With at least one provider installed, the Form plugin's dialog gains a
**Captcha** section:

**Captcha widget**
   Empty (no captcha) or one of the choices above.

**Minimum score requirement**
   Only relevant for reCaptcha v3, which cannot currently be selected - see
   :ref:`captcha-limitations`.

**Recaptcha configuration parameters**
   Key/value pairs for reCaptcha and hCaptcha widgets. Names starting with
   ``data-`` are passed to the widget as HTML attributes, all other names are
   passed as API parameters (``hl`` to set the language, for example). They are
   **not** used for Altcha, which is configured through
   ``ALTCHA_FIELD_OPTIONS`` instead.

The captcha field is added to the form as ``captcha_field``. It is stripped
from the cleaned data before actions run, so it never ends up in a stored entry
or in a mail.

Choose where the widget appears
===============================

By default the widget is rendered after all field plugins of the form. To put
it somewhere else, add a **Captcha** plugin as a child of the form plugin at the
position where you want it. The widget is then rendered there and not appended.

Configure reCaptcha
===================

``django-recaptcha`` needs its keys in your settings:

.. code-block:: python

   RECAPTCHA_PUBLIC_KEY = "..."
   RECAPTCHA_PRIVATE_KEY = "..."

Without both of them the plugin's Captcha section shows a warning: the widget is
rendered but cannot verify anything.

Configure Altcha
================

Install ``django-altcha``, add ``django_altcha`` to ``INSTALLED_APPS``, and set
up a challenge URL as described in its documentation - either its built-in
challenge view (self-hosted, needs ``ALTCHA_HMAC_KEY``) or an external challenge
server.

Everything in ``ALTCHA_FIELD_OPTIONS`` is passed on to django-altcha's
``AltchaField`` unchanged:

.. code-block:: python

   from django.urls import reverse_lazy

   ALTCHA_FIELD_OPTIONS = {
       "challengeurl": reverse_lazy("altcha_challenge"),
       "floating": True,
   }

The stylesheet that adapts the widget to the form layout is added automatically
when an Altcha field is rendered.

.. _captcha-limitations:

Limitations
===========

* reCaptcha v3 cannot be selected in the plugin. The score handling exists in
  the code, but the widget choice is not offered, which also makes the
  *Minimum score requirement* field inconsequential.
* A captcha only protects a form built from field plugins. Forms registered by
  your project (see :doc:`use-a-django-form`) are rendered as they are and get
  no captcha field.
