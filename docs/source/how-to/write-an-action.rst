Write your own form action
##########################

An action is a small class with an ``execute()`` method that runs after a form
has been submitted and validated. Registering one makes it selectable in the
Actions section of every form plugin.

Register an action
==================

.. code-block:: python

   from django.utils.translation import gettext_lazy as _
   from djangocms_form_builder import actions


   @actions.register
   class NotifySalesAction(actions.FormAction):
       verbose_name = _("Notify sales")

       def execute(self, form, request):
           ...  # runs upon successful submission

``execute()`` receives the validated form - its ``cleaned_data`` holds the
submission - and the request. Its return value is not used.

Register your actions once all apps have loaded, e.g. in your app's
``models.py`` or in the ``ready()`` method of its ``AppConfig``. A
``verbose_name`` is mandatory, and only subclasses of ``FormAction`` are
accepted; anything else raises ``ImproperlyConfigured``.

Ask the editor for parameters
=============================

An action may add its own fields to the form plugin's editing dialog by
declaring them as entangled fields. They appear in a section of their own, named
after the action, and their values are read back with ``get_parameter()``:

.. code-block:: python

   from django import forms


   @actions.register
   class NotifySalesAction(actions.FormAction):
       class Meta:
           entangled_fields = {"action_parameters": ["notifysales_team"]}

       verbose_name = _("Notify sales")

       notifysales_team = forms.CharField(label=_("Team"), required=False)

       def execute(self, form, request):
           team = self.get_parameter(form, "notifysales_team")
           ...

All actions contribute their fields to the same plugin dialog, so prefix field
names with the action's name to keep them apart from the fields of other
actions.

Rate limit your action
======================

An action can declare rate limits and the values they are counted against:

.. code-block:: python

   @actions.register
   class NotifySalesAction(actions.FormAction):
       verbose_name = _("Notify sales")
       rate_limits = {"source": (5, 60 * 60)}

       def get_rate_limit_values(self, form, request):
           values = super().get_rate_limit_values(form, request)  # {"source": ...}
           values["customer"] = form.cleaned_data.get("customer_number", "")
           return values

       def execute(self, form, request):
           ...

Projects adjust or switch off these limits through
``DJANGOCMS_FORM_BUILDER_RATE_LIMITS["NotifySalesAction"]``, see
:doc:`rate-limit-actions`. A value that an action declares but cannot determine
- an empty string or ``None`` - blocks the action, so only declare kinds a
submission really provides.

Register an action conditionally
================================

If an action should only be available under certain conditions, register it
conditionally - the built-in redirect and confirmation mail actions do exactly
that:

.. code-block:: python

   if getattr(settings, "MY_PROJECT_NOTIFIES_SALES", False):

       @actions.register
       class NotifySalesAction(actions.FormAction):
           ...

Actions that are not registered do not show up in the form plugin. Forms that
still refer to an unregistered action report that the action is not available
any more instead of failing.

Change what the visitor sees
============================

Actions can influence the response by writing to ``form.Meta.options`` - this is
how the built-in actions redirect or replace the form with a message:

``options["redirect"]``
   A URL, a URL name, or an object with ``get_absolute_url()``. The visitor's
   browser navigates there after a successful submission.

``options["render_success"]``
   A template rendered instead of the form. Set ``form.get_success_context`` to
   supply its context.

If several actions of a form write to the same option, the one that runs last
wins. Actions run in the order they are stored with the plugin, which follows
the order in which they were registered - not the order in which an editor
ticked them.
