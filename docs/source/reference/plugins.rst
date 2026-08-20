Plugins
#######

All plugins are listed in the **Forms** category of the plugin picker.

Form
====

The container. It renders the ``<form>`` element, builds the Django form class
and receives the submission.

:Model: ``djangocms_form_builder.models.Form``
:Children: any plugin; field plugins become form fields
:Restriction: must not be placed inside another Form plugin

Editing dialog:

**Form** (``form_selection``)
   One of the forms your project registered. Hidden while no form is
   registered. See :doc:`../how-to/use-a-django-form`.

**Form identifier** (``form_name``)
   Slug identifying the form. Required unless a registered form is selected.

**Login required to submit form** (``form_login_required``)
   Submissions by anonymous visitors are rejected with a validation error.

**User can reopen form** (``form_unique``)
   A logged-in user's submission is loaded back into the form and updated
   instead of stored a second time. Requires *Login required* and the *Save form
   submission* action; the plugin refuses to be saved otherwise.

**Floating labels** (``form_floating_labels``) and **Margin between fields** (``form_spacing``)
   Rendering options, see :doc:`../how-to/style-forms`.

**Actions**
   Which actions run after a valid submission. Hidden when a registered form is
   selected. Actions that ask for parameters add a section of their own below.

**Captcha**
   Only shown if a captcha package is installed, see
   :doc:`../how-to/add-a-captcha`.

If the form plugin has child plugins, the form is built from them and
``form_selection`` is ignored.

Field plugins
=============

Every field plugin asks for **Label** (``field_label``), **Field name**
(``field_name``, a slug that is not a reserved name), **Required**
(``field_required``), **Placeholder** (``field_placeholder``) and **Help text**
(``field_help_text``). Plugin-specific settings are listed below.

A field plugin is only accepted as a descendant of a Form plugin - it may sit
inside rows, columns or any other plugin in between.

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Plugin
     - Form field
     - Settings
   * - Text
     - ``CharField`` with a text input
     - *Minimum/Maximum text length*, enforced server-side
   * - Textarea
     - ``CharField`` with a textarea
     - *Rows* (1-40, default 10), *Minimum/Maximum text length*
   * - Email
     - ``EmailField``
     - -
   * - URL
     - ``URLField``
     - -
   * - Integer
     - ``IntegerField``
     - *Minimum/Maximum value* - stored, but currently not applied to the
       rendered field
   * - Decimal
     - ``DecimalField`` (cleaned to a string)
     - *Decimal places*, *Minimum/Maximum value*
   * - Date
     - ``DateField`` with ``<input type="date">``
     - -
   * - Time
     - ``TimeField`` with ``<input type="time">``
     - -
   * - Date and time
     - ``DateTimeField`` with ``<input type="datetime-local">``
     - -
   * - Boolean
     - ``BooleanField``
     - *Layout*: checkbox or switch
   * - Select
     - ``ChoiceField`` or ``MultipleChoiceField``
     - *Selection type*, *Choices*
   * - Choice
     - one option of a Select
     - *Value* (stored) and *Display text* (shown)
   * - File upload
     - single file field
     - *Validation presets*
   * - Multiple file upload
     - multiple file field
     - *Max files* (default 2), *Validation presets*
   * - Submit button
     - the submit button
     - *Button label*, *Button context*
   * - Captcha
     - marks where the captcha widget goes
     - -

Select and Choice
-----------------

The *Selection type* decides the field and the widget:

.. list-table::
   :header-rows: 1

   * - Selection type
     - Field
     - Widget
   * - Drop down
     - ``ChoiceField``
     - ``Select``
   * - Radio buttons
     - ``ChoiceField``
     - ``RadioSelect``
   * - Checkboxes
     - ``MultipleChoiceField``
     - ``CheckboxSelectMultiple``
   * - List
     - ``MultipleChoiceField``
     - ``SelectMultiple``

A single-choice field that is not required is given an additional empty *No
selection* option. A required *Checkboxes* field is refused - use *List*
instead.

The options themselves are **Choice** child plugins. The *Choices* section of
the Select dialog is a quick editor for them: saving creates missing choices,
updates changed display texts and deletes the ones you removed. Their order is
changed in the structure board.

Submit button
-------------

A form without a Submit button plugin is rendered with a default submit button
labelled *Submit*. Add the plugin to change its caption or colour, or to place
it somewhere other than at the end of the form.

Captcha
-------

Marks the position of the captcha widget configured on the Form plugin. Without
this plugin the widget is rendered after all field plugins. It has no settings
of its own.

Replaced plugins
================

If ``djangocms_frontend.contrib.frontend_forms`` is installed, its form plugins
are unregistered when this app loads, so that only one set of form plugins is
offered.
