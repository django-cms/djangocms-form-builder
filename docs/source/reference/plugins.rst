Plugins
#######

All plugins are listed in the **Forms** category of the plugin picker.

Form
====

Shows a form on a page. It renders the ``<form>`` element, builds the Django
form class from the form it points at, and receives the submission.

:Model: ``djangocms_form_builder.models.FormPlugin``
:Children: none - a form's fields live in the form object
:Restriction: must not be placed inside another Form plugin, nor inside a form

Editing dialog:

**Form** (``form``)
   The form to show. Forms are built in the form editor, reachable through
   **Forms** in the toolbar's site menu.

**Registered form** (``form_selection``)
   One of the forms your project registered, instead of a form object. Hidden
   while no form is registered. See :doc:`../how-to/use-a-django-form`.

The plugin menu offers **Edit form**, which opens the form it shows.

Plugins that carry their own fields
-----------------------------------

A plugin created before forms became objects has its field plugins as children
and its settings on itself. Such a plugin keeps working, keeps its own editing
dialog - *Form identifier*, *Login required to submit form*, *User can reopen
form*, *Floating labels*, *Margin between fields*, *Actions* and *Captcha*, all
described under `Form settings`_ - and offers **Convert to form** in its plugin
menu. No further child can be added to it. See
:doc:`../how-to/convert-a-form-plugin`.

Form settings
=============

What a form does, rather than where it is shown. Reached through **Form
settings** in the toolbar while editing a form, or with the settings icon in the
form list. One dialog holds everything about a form.

:Model: ``djangocms_form_builder.models.Form`` (identifier) and
   ``djangocms_form_builder.models.FormContent`` (everything else)

**Name** (``name``)
   Shown to editors picking this form. Not shown to visitors.

**Form identifier** (``form_name``)
   The slug submissions are filed under. It lives on the form itself rather
   than on its content, so it stays the same across versions. Changing it
   separates new submissions from the ones collected so far.

**Login required to submit form** (``form_login_required``)
   Submissions by anonymous visitors are rejected with a validation error.

**User can reopen form** (``form_unique``)
   A logged-in user's submission is loaded back into the form and updated
   instead of stored a second time. Requires *Login required* and the *Save form
   submission* action; the form refuses to be saved otherwise.

**Floating labels** (``form_floating_labels``) and **Margin between fields** (``form_spacing``)
   Rendering options, see :doc:`../how-to/style-forms`.

**Actions**
   Which actions run after a valid submission. Actions that ask for parameters
   add a section of their own below.

**Captcha**
   Only shown if a captcha package is installed, see
   :doc:`../how-to/add-a-captcha`.

With djangocms-versioning, a published form's settings are read-only: edit the
form to create a draft first.

Field plugins
=============

Every field plugin asks for **Label** (``field_label``), **Field name**
(``field_name``, a slug that is not a reserved name), **Required**
(``field_required``), **Placeholder** (``field_placeholder``) and **Help text**
(``field_help_text``). Plugin-specific settings are listed below.

A field plugin is only offered inside a form - it may sit inside rows, columns
or any other plugin in between. Fields of a plugin that has not been converted
stay editable where they are.

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
