Use a Django form you already have
##################################

Instead of building a form from plugins, you can hand an existing Django form
class to **djangocms-form-builder** and let editors place it on a page.

Register the form
=================

.. code-block:: python

   from django import forms
   from djangocms_form_builder import register_with_form_builder


   @register_with_form_builder
   class MyGreatForm(forms.Form):
       ...

The decorator also works as a plain function call:
``register_with_form_builder(AnotherGreatForm)``.

As soon as at least one form is registered, the form plugin shows a **Form**
select listing them. Until then the select is hidden.

The name in that select is derived from the class name (``MyGreatForm`` becomes
*My Great Form*) unless the form says otherwise:

.. code-block:: python

   @register_with_form_builder
   class MyGreatForm(forms.Form):
       class Meta:
           verbose_name = _("My great form")

Tell the plugin what to do afterwards
=====================================

Form actions are **not** available for registered forms - the Actions section
disappears once a form is selected. Everything that should happen upon
submission belongs into the form's ``save()`` method, which is called if it
exists.

The response the visitor gets is decided by ``Meta.options``:

.. code-block:: python

   @register_with_form_builder
   class MyGreatForm(forms.Form):
       class Meta:
           verbose_name = _("My great form")
           options = {
               "redirect": "https://example.com/thank-you/",
           }

       def save(self):
           ...

``options["redirect"]`` accepts a URL, a URL name that can be reversed, or an
object with a ``get_absolute_url()`` method. Alternatively set
``options["render_success"]`` to a template that replaces the form, and add a
``get_success_context(request, instance, form)`` method to give it a context.

.. important::

   Set one of the two. A registered form with neither ``redirect`` nor
   ``render_success`` answers a successful submission with the error *No content
   in response form* - even though ``save()`` has already run.

Other options understood here are ``floating_labels``, ``field_sep`` and
``crispy_form``, see :ref:`form-options`.

Control the layout
==================

There are three ways a registered form is rendered:

#. **Field by field.** With no further information all visible fields are
   rendered below one another. Good enough for a contact form.

#. **With fieldsets.** If the form has a ``get_fieldsets()`` method or a
   ``Meta.fieldsets`` attribute, it is rendered section by section, the way
   ``ModelAdmin`` fieldsets work. Fields grouped in a tuple share a row.

#. **With django-crispy-forms.** If `django-crispy-forms
   <https://github.com/django-crispy-forms/django-crispy-forms>`_ is installed
   and the form has a ``helper`` attribute (or ``options["crispy_form"]`` is
   set), the form is rendered by crispy-forms and its layout is retained. The
   helper's ``form_tag`` and CSRF handling are switched off, since the plugin
   renders the surrounding ``<form>`` element and its token.

Do not include a submit button in the layout - the plugin renders one.

Things to know
==============

* Field plugins win. If the form plugin has child plugins, a form built from
  those is used and the selection is ignored.
* Registered forms get no captcha field. The plugin's captcha configuration
  applies to forms built from field plugins.
* ``login_required`` and *User can reopen form* are enforced by the form class
  the plugin builds from field plugins, not by a registered form.
* Your form is instantiated without the request. If it needs one, set
  ``takes_request = True`` on the class and accept a ``request`` keyword
  argument, the way ``SimpleFrontendForm`` does.
* Field ``id`` attributes are rewritten to ``<field name><plugin id>`` so that
  several forms can live on the same page.
