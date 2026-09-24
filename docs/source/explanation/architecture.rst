How a plugin tree becomes a form
################################

A form built in the structure board has no form class anywhere in your project.
This page describes what takes its place.

Why a form is an object
=======================

A form used to be built inside the form plugin, as its children. That made the
form a part of one page: to show it twice you built it twice, and to change it
you opened the page it happened to sit on.

A form is therefore an object of its own, following the grouper/content split
django CMS uses for its own content. ``Form`` carries the identity that must
survive everything else - the identifier submissions are filed under - and
``FormContent`` carries what is edited: the settings, and the placeholder
holding the field plugins. The form plugin is reduced to a placement: a
foreign key to a ``Form`` and nothing more.

The split is what makes versioning possible. With djangocms-versioning
installed, a form has drafts and published versions like a page does, and the
plugin resolves to the published one for visitors and to the draft while an
editor is in edit or preview mode. A half-finished field cannot change what a
visitor is able to submit.

In the admin the split disappears again: one dialog, the form admin, edits the
identifier on ``Form`` and the settings on ``FormContent`` together, the way
django CMS' ``GrouperModelAdmin`` presents a grouper with its content.

The form editor - django CMS' edit and preview endpoint for a ``FormContent`` -
renders the form with the same template a page uses, so an editor sees exactly
what a visitor will, submit button included. It sets ``form_preview`` in the
context: the ``<form>`` gets no submission endpoint and the class
``djangocms-form-builder-preview`` instead of
``djangocms-form-builder-ajax-form``, so the AJAX script leaves it alone, and
``form_preview.js`` stops the browser from submitting it. That is a script file
rather than an inline ``onsubmit`` handler, which a Content Security Policy
would block.

Why a form has no language
==========================

A form has no language field, and no version per language: there is one form,
with one identifier and one set of settings, however many languages a site
has. The identifier is what submissions are filed under, so splitting it per
language would split the submissions with it.

Its *plugins* do carry a language, because every django CMS plugin does. A
form is therefore built per language inside that single object - the way a
static placeholder used to work. Editing a form in German adds German plugins
to it; a form plugin on a German page renders those. Labels and help texts are
written per language this way, while the form stays one object with one set of
actions.

The consequence is worth knowing: a form only built in one language renders
nothing on a page in another, the same way an untranslated page shows nothing.
Build the form in each language you place it in.

One place needs care. The endpoint a form is submitted to is not
language-prefixed - it addresses the plugin, not a page - so the language the
form was built from is named explicitly in the form's ``action`` URL. Without
that, a submission could be validated against a different language's fields
than the visitor was shown.

From plugins to a form class
============================

Field plugins do not render inputs themselves. What they contribute is a method:
every field plugin model implements ``get_form_field(request=None)``, returning a
field name and a Django form field.

When a form is rendered - or receives a submission - the plugins it is built
from are walked, everything that has such a method is collected, and a form
class is built from the result with ``type()``. Nesting does not matter: a
field inside a row inside a card is found just the same, which is what lets
editors lay out a form with ordinary layout plugins.

Where those plugins come from is the only difference between a form object and
a form plugin predating it. The object hands over the plugins of its
placeholder; the plugin hands over its own children. Both then go through the
same code in ``form_factory``, which is why a plugin that has not been
converted behaves exactly as it did - see
:doc:`../how-to/convert-a-form-plugin`.

The class is rebuilt on every request. That is what allows a field to capture the
request, which the upload fields need to pass the user to validation presets.

Alongside the fields, a ``Meta`` class is built whose ``options``
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

A form's action parameters follow the same idea: whatever fields the
registered actions declare, their values are kept in one JSON field,
``action_parameters``, on the form content.

The result is that a new field type - or a new option on an existing one - does
not change the database schema. This is also why a form's captcha
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

A form object brings a second concern. Its fields are rendered into the
placeholder cache of the page showing it - there is no cache of the form's own
- so a change to the form does not invalidate anything by itself. With
djangocms-versioning, publishing or unpublishing a form therefore clears the
cache of exactly those placeholders that hold a form plugin pointing at it;
otherwise visitors could be shown the old fields while their submission is
validated against the new ones. Two cases are not covered: without versioning,
editing a form clears no page cache, and a form placed inside an alias clears
the alias' placeholder but not the page showing the alias - the cached markup
then expires after ``CMS_CACHE_DURATIONS["content"]``.

Actions instead of hooks
========================

What happens after a valid submission is not part of the form. It is a list of
*actions*, each a small class registered in a process-wide registry, that the
editor ticks in the form's settings.

Actions are stored by the SHA-1 hash of their class name, not by an index or an
import path, so a project can register and unregister them freely. Two
consequences follow: renaming an action class detaches it from the forms using
it, and a form referring to an action that is no longer registered reports that
one action as unavailable instead of failing the submission.

Actions can do more than run code. They contribute their own fields to the
form's settings dialog - which is why ``FormAction`` is a form mixin - and they
can change the answer the visitor gets by writing to ``Meta.options``. The
built-in *Success message* and *Redirect* actions are nothing but that.

The same mechanism carries the rate limits: an action declares which values a
submission should be counted against, and the framework consumes those counters
before ``execute()`` runs.
