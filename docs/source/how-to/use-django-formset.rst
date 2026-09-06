Use the django-formset frontend
###############################

The optional django-formset frontend adds its Bootstrap renderer, browser-side
validation and web component while retaining djangocms-form-builder's form
plugins and submission actions.

Install and enable it
=====================

Install the extra:

.. code-block:: bash

   pip install "djangocms-form-builder[formset]"

Add django-formset and select the frontend:

.. code-block:: python

   INSTALLED_APPS = [
       ...,
       "formset",
       "djangocms_form_builder",
   ]

   DJANGOCMS_FORM_BUILDER_FRONTEND = "django_formset"

The page template must render both django-sekizai blocks, normally once in the
``<head>`` and once before ``</body>``:

.. code-block:: html+django

   {% load sekizai_tags %}
   <head>
       ...
       {% render_block "css" %}
   </head>
   <body>
       ...
       {% render_block "js" %}
   </body>

The frontend loads django-formset's web component and its small Bootstrap 5
supplement through those blocks. Your site still provides Bootstrap 5 itself.

For translated browser-side messages, add django-formset's JavaScript catalogue
to the project URLconf as described by the `django-formset installation guide
<https://django-formset.fly.dev/installation/>`_.

What changes
============

Fields are rendered by django-formset's Bootstrap renderer. The web component
validates browser-side constraints and submits JSON to the form plugin's normal
endpoint. Valid submissions still execute the actions selected by the editor;
invalid submissions return django-formset's ``422`` error response.

The form plugin is not cached because the web component receives a request CSRF
token in its markup.

Current scope
=============

This is basic single-form support. django-formset collections, advanced widgets
and conditional field expressions are not exposed by the CMS plugins yet. The
Form plugin's floating-label option is not applied by this renderer.

File fields do not currently work through django-formset itself. A form
containing a single or multiple file field therefore automatically falls back
to djangocms-form-builder's standard multipart frontend. Uploads, validation
presets and storage lifecycle continue to work, but that whole form does not use
django-formset's rendering or browser-side validation. Registered forms
rendered through django-formset ignore django-crispy-forms helpers.

Native file support
===================

Supporting uploads without the fallback requires integration with
django-formset's upload lifecycle rather than only its final JSON submission:

* render file fields with django-formset's ``UploadedFileInput``;
* accept its separate multipart request and store the upload temporarily;
* return a signed temporary-file handle for the final JSON payload;
* convert that handle back into one or more Django uploaded files before form
  validation;
* preserve djangocms-form-builder's validation presets, maximum-file limits,
  permanent storage and cleanup behavior.

Multiple uploads additionally need a widget and handle format that retains all
files instead of django-formset's single-file value. This requires an extension
to django-formset's upload widget or a form-builder-specific equivalent.
