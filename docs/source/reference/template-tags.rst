Template tags
#############

.. code-block:: html+django

   {% load form_builder_tags %}

``render_form``
===============

.. code-block:: html+django

   {% render_form form %}
   {% render_form form template="myapp/my_form.html" %}
   {% render_form form helper=my_helper %}

Renders a whole form. If django-crispy-forms is installed **and** a helper is
passed, the form has a ``helper`` attribute, or the form's ``crispy_form``
option is set, the form is rendered by crispy-forms with ``form_tag`` and CSRF
handling switched off. Otherwise the template given by ``template`` is used,
defaulting to the ``FORM_TEMPLATE`` setting. Any other keyword argument is added
to the template context.

``render_widget``
=================

.. code-block:: html+django

   {% render_widget form "email" %}

Renders one field of a form: a wrapping ``<div>``, the label, the widget, the
error messages and the help text, with the CSS classes of the configured
framework. Extra keyword arguments become widget attributes.

The order of label and widget follows the widget type and the form's
``floating_labels`` option. Bound forms get ``is_valid``/``is_invalid`` classes,
required fields a ``required`` class. Multiple-choice widgets are rendered
through ``djangocms_form_builder/widgets/mutliple_input.html`` so that classes
end up at the right nesting level. Returns an empty string if the form has no
such visible field.

``render_captcha_widget``
=========================

.. code-block:: html+django

   {% render_captcha_widget form %}

Renders the form's captcha field, if it has one, and an empty string otherwise.
Altcha widgets are rendered as they are, other providers go through
``render_widget``. ``render_recaptcha_widget`` is an alias kept for custom
templates using the older name.

``get_fieldset``
================

.. code-block:: html+django

   {% for title, prop in form|get_fieldset %}

Filter returning the fieldsets of a form: from ``get_fieldsets()`` if the form
has one, else from ``Meta.fieldsets``, else a single fieldset with all visible
fields.

``add_placeholder``
===================

.. code-block:: html+django

   {{ form|add_placeholder }}

Filter that copies each field's label into its widget's ``placeholder``
attribute and returns the form.
