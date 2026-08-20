The submission endpoint
#######################

Forms are not submitted to the page they are on. They are sent by ``fetch()`` to
a JSON endpoint that the app adds to the project's root URLconf when it is
ready, under the prefix ``@form-builder/`` and the namespace ``form_builder``.
Adding it a second time is prevented, so there is nothing to add to your
``urls.py``.

URLs
====

``@form-builder/<instance_id>`` (``form_builder:ajaxview``)
   The plugin with this primary key handles the request.

``@form-builder/<instance_id>/<parameter>`` (``form_builder:ajaxview``)
   As above, with parameters. The path is split at commas, each element at the
   first ``=`` (or ``%3D``); an element without one becomes ``True``. The
   resulting dictionary is passed to the plugin. The key ``s`` selects one of a
   plugin's ``form_classes`` by its ``slug``.

``@form-builder/f<form_id>`` (``form_builder:ajaxformbuilder``)
   A view registered with ``register_form_view()`` handles the request.

A request is only treated as an AJAX request if it accepts
``application/json``; other requests fall through to Django's ``View``
dispatching, which answers ``405``.

For plugin requests, the plugin class must implement ``ajax_post()`` or
``ajax_get()`` - otherwise the endpoint answers ``404``. A ``ValidationError``
raised while handling the request becomes ``{"result": "error", "msg": ...}``.

``GET``: the CSRF token
=======================

A ``GET`` returns ``{"csrf_token": "..."}``, which the JavaScript sends as the
``X-CSRFToken`` header of the following ``POST``. This works regardless of
``CSRF_COOKIE_HTTPONLY`` or ``CSRF_USE_SESSIONS``.

If ``CSRF_COOKIE_HTTPONLY`` is set, the site has decided to keep the token away
from JavaScript. The endpoint then answers ``405``, the form template renders
``{% csrf_token %}`` inline instead, and the form plugin is excluded from the
plugin cache because its HTML is now request-specific.

``POST``: the answer to a submission
====================================

The form is bound to ``request.POST`` and ``request.FILES`` - submissions are
sent as ``multipart/form-data`` so that uploads survive.

A **valid** submission answers with:

.. code-block:: json

   {
     "result": "success",
     "redirect": "/thank-you/",
     "errors": [],
     "field_errors": {},
     "content": ""
   }

``result``
   ``"success"``, or whatever a ``render_success`` context put in ``result``.

``redirect``
   Where the browser should go. The form plugin presets this to ``"result"``,
   which makes the JavaScript reload the current page.

``content``
   The HTML of the ``render_success`` template, if the form has one. The
   JavaScript replaces the form with it.

An **invalid** submission answers with:

.. code-block:: json

   {
     "result": "invalid form",
     "errors": ["..."],
     "field_errors": {"email42": ["Enter a valid email address."]},
     "html": "..."
   }

``errors`` holds the non-field errors. The keys of ``field_errors`` are the
field name followed by the plugin's primary key, matching the ``id`` attributes
the plugin gives the widgets so that several forms can share a page.

Registering a view
==================

.. code-block:: python

   from djangocms_form_builder.views import register_form_view

   form_id = register_form_view(MyFormView, slug="newsletter")

Registers a class the ``f<form_id>`` URL delegates to; ``form_id`` is the SHA-384
of the slug. Without a slug a random one is generated. Registering the same slug
for a different class raises ``ImproperlyConfigured``.

On a request the class is instantiated and its ``ajax_post()``/``ajax_get()`` is
called, falling back to ``post()``/``get()``. A class with neither answers
``404``.

Plugins that answer AJAX
========================

``djangocms_form_builder.cms_plugins.ajax_plugins`` provides the base classes the
form plugin is built from, and any plugin of your own can use them:

``CMSAjaxBase``
   Adds ``ajax_get()`` and ``ajax_post()`` to a ``CMSPluginBase``.

``AjaxFormMixin``
   Django's ``FormMixin`` adapted to the JSON protocol above:
   ``get_ajax_form()``, ``form_valid()`` and ``form_invalid()``. Form classes
   with ``takes_request = True`` are instantiated with the request.

``CMSAjaxForm``
   The two combined - what ``FormPlugin`` derives from.
