How a plugin tree becomes a form
################################

A form built in the structure board has no form class anywhere in your project.
This page describes what takes its place.

From plugins to a form class
============================

Field plugins do not render inputs themselves. What they contribute is a method:
every field plugin model implements ``get_form_field(request=None)``, returning a
field name and a Django form field.

When the form plugin is rendered - or receives a submission - it walks its
descendants, collects everything that has such a method, and builds a form class
from the result with ``type()``. Nesting does not matter: a field inside a row
inside a card is found just the same, which is what lets editors lay out a form
with ordinary layout plugins.

The class is rebuilt on every request. That is what allows a field to capture the
request, which the upload fields need to pass the user to validation presets.

Alongside the fields, the plugin builds a ``Meta`` class whose ``options``
dictionary carries everything the editor configured: the form identifier, the
selected actions, the parameters of those actions, the redirect, the layout
options. Everything downstream - the form's ``clean()``, the actions, the
template tags - reads its configuration from there through ``get_option()``,
which falls back to a project-wide ``DJANGOCMS_FORMS_OPTIONS``. A form your
project registers can therefore be configured exactly like a generated one; it
just sets ``Meta.options`` itself.

Why the configuration is JSON
=============================

Field plugins share a single model, ``FormField``, with the plugin type in
``ui_item`` and everything else in a JSON field, ``config``. The concrete
plugins are proxy models. `django-entangled
<https://github.com/jrief/django-entangled>`_ presents the JSON contents as
ordinary form fields in the editing dialog.

The result is that a new field type - or a new option on an existing one - does
not change the database schema. This is also why the form plugin's captcha
configuration is a JSON attributes field: which captcha packages a project has
installed must not decide what its migrations look like.

Why submissions go through AJAX
===============================

A CMS page is a tree of plugins with a single URL, and that URL belongs to the
CMS. A form that posted to it would have to be dealt with by the CMS' own view,
which knows nothing about forms, and a page could carry only one form.

Instead every form posts to its own endpoint, addressed by the plugin's primary
key, and the answer is JSON that the shipped JavaScript applies to the page:
replace the form with a success message, show field errors next to the fields,
or navigate to a redirect. A page can hold as many forms as an editor likes, and
each of them is a plugin like any other. The exact protocol is described in
:doc:`../reference/ajax-api`.

Caching and the CSRF token
==========================

A form's HTML is the same for every visitor - except for the CSRF token. That is
why the token is not in the form by default: the JavaScript fetches it from the
same endpoint with a ``GET`` right before submitting, and the plugin's HTML
stays cacheable like any other plugin.

If a project sets ``CSRF_COOKIE_HTTPONLY``, it has decided that JavaScript must
not see the token. The app respects that instead of working around it: the
endpoint refuses to hand the token out, the template renders ``{% csrf_token %}``
inline, and the form plugin switches its caching off, because its HTML now
differs per request.

Actions instead of hooks
========================

What happens after a valid submission is not part of the form. It is a list of
*actions*, each a small class registered in a process-wide registry, that the
editor ticks in the form plugin.

Actions are stored by the SHA-1 hash of their class name, not by an index or an
import path, so a project can register and unregister them freely. Two
consequences follow: renaming an action class detaches it from the forms using
it, and a form referring to an action that is no longer registered reports that
one action as unavailable instead of failing the submission.

Actions can do more than run code. They contribute their own fields to the form
plugin's dialog - which is why ``FormAction`` is a form mixin - and they can
change the answer the visitor gets by writing to ``Meta.options``. The
built-in *Success message* and *Redirect* actions are nothing but that.

The same mechanism carries the rate limits: an action declares which values a
submission should be counted against, and the framework consumes those counters
before ``execute()`` runs.
