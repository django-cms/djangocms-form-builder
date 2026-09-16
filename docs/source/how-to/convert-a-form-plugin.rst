Convert an existing form plugin into a form
###########################################

Before forms became objects of their own, a form was built *inside* the form
plugin: the field plugins were its children, and the plugin carried the form's
settings. Those plugins keep working exactly as they did, and nothing forces
you to change them.

You will want to convert one anyway when you want to show the same form on a
second page, edit it without opening the page it sits on, or - with
djangocms-versioning - draft and publish it separately.

What conversion does
====================

Converting moves the plugin's children into a new form object and points the
plugin at it. The plugin stays where it is, and visitors see no difference:

* the field plugins are moved into the new form, in the same order, keeping
  the language they were in - so converting from a German page gives the new
  form its German fields;
* the plugin's settings - actions and their parameters, captcha, login
  requirements, layout - are copied onto the form;
* the new form is published right away where versioning is installed, because
  the plugin was already showing it.

Convert a plugin
================

#. Open the page in the structure board. The page must be a draft: a published
   page is read-only, so the menu entry does nothing there.
#. Open the form plugin's menu (the ⋮ next to it) and choose **Convert to
   form**.
#. Check the two fields:

   **Name**
      What editors will see when they pick this form.

   **Form identifier**
      The slug submissions are filed under. Keep the plugin's current
      identifier to keep new submissions together with the ones you have
      already collected - the dialog only suggests a different one when that
      identifier is taken by another form.

#. Confirm. The plugin now shows the new form, and the form appears under
   **Forms**.

Two identifiers, one form
=========================

Form identifiers are unique across forms, while nothing stopped two form
plugins from using the same one. If you converted one of them, the other keeps
its own copy of the fields and keeps writing submissions under the shared
identifier. Convert it too - the dialog will offer a free identifier - and
decide then whether the two forms should keep collecting into one pot or be
told apart.

What happens if you do not convert
==================================

Nothing breaks. An unconverted plugin renders its children as before and
accepts submissions as before. What it cannot do any more is grow: no new field
plugins can be added below it, because field plugins are only offered inside a
form. Its existing fields stay editable.

.. seealso::

   :doc:`../explanation/architecture` for how a tree of plugins becomes a form
   class, in a form object and below a plugin alike.
