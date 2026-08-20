Change how forms are rendered
#############################

The templates that ship with the package render Bootstrap 5 markup. Everything
about that can be replaced, from a single widget to the whole form.

Adjust the built-in options first
=================================

Two settings of the form plugin need no code:

**Margin between fields**
   The CSS class put between fields. The choices come from
   ``DJANGO_FORM_BUILDER_SPACER_CHOICES``, or - if you already use
   djangocms-frontend - from ``DJANGOCMS_FRONTEND_SPACER_SIZES``, whose keys are
   turned into ``mb-<key>`` classes. Without either, the only choice is
   ``mb-3``.

**Floating labels**
   Renders the label after the input and adds Bootstrap's ``form-floating``
   class, except for checkboxes and radio buttons.

The colours offered for the submit button come from
``DJANGOCMS_FORM_BUILDER_COLOR_STYLE_CHOICES``, or from
``DJANGOCMS_FRONTEND_COLOR_STYLE_CHOICES``, and default to *Primary* and
*Secondary*.

Override a template
===================

Put a template with the same path earlier in your template search path. The ones
you are most likely to want are:

``djangocms_form_builder/bootstrap5/form.html``
   The ``<form>`` element itself, the CSRF token and the fallback submit button.

``djangocms_form_builder/ajax_form.html``
   What goes inside the form: the error container, the field plugins, the
   captcha widget and the ``<script>`` tag.

``djangocms_form_builder/bootstrap5/render/form.html``
   Used for forms that are *not* built from field plugins - it walks the
   fieldsets. Its path can be changed with the ``FORM_TEMPLATE`` setting.

``djangocms_form_builder/bootstrap5/render/section.html`` and ``render/field.html``
   One fieldset and one field of such a form.

``djangocms_form_builder/bootstrap5/widgets/base.html`` and ``widgets/submit.html``
   A single field plugin and the submit button plugin.

Render a field yourself
=======================

The template tags in ``form_builder_tags`` are what the templates above use, and
they work in your own templates too:

.. code-block:: html+django

   {% load form_builder_tags %}
   {% render_widget form "email" %}

See :doc:`../reference/template-tags` for the full list.

Use another CSS framework
=========================

``DJANGOCMS_FRONTEND_FRAMEWORK`` (default ``"bootstrap5"``) selects both the
template directory and the map from widget class to CSS classes.

The package ships templates for Bootstrap 5 only. It also contains an attribute
map for Foundation 6, but no templates to go with it: pointing the setting at
``foundation6`` means providing a
``djangocms_form_builder/foundation6/`` template directory of your own.

Add render mixins from a theme app
==================================

``DJANGOCMS_FRONTEND_THEME`` (default ``"djangocms_frontend"``) names a module
that may contribute render mixins to the field plugins. A class called
``<name>RenderMixin`` in ``<theme>.frameworks.<framework>`` is mixed into the
matching plugin, for these names:

``CharField``, ``EmailField``, ``URLField``, ``DecimalField``, ``IntegerField``,
``SelectField``, ``ChoiceField``, ``FileField``, ``MultipleFileField``,
``BooleanField`` and ``SubmitButton``.

A theme module that does not exist is ignored, so the setting is safe to leave
at its default.
