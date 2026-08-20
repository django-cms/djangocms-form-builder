##############
 Form actions
##############

What happens to a submission is decided by the **form actions** selected in the
form plugin. An action is a small class with an ``execute()`` method that runs
once a form has been submitted and validated. A form can run several actions,
e.g. save the submission, mail it to the site admins and show a success
message.

*****************
 Built-in actions
*****************

* **Save form submission** - stores the submitted data as a form entry. See
  :doc:`file_upload` for how uploads are stored and
  ``python manage.py prune_form_entries`` for enforcing a retention policy.
* **Send email** - mails the submission to the site admins or to a fixed list
  of recipients. The mail is rendered from the template set chosen in
  ``DJANGOCMS_MAIL_TEMPLATE_SETS``.
* **Success message** - shows a message instead of the form after submission.
* **Redirect after submission** - redirects to a link. Only available if
  **djangocms-link** is installed.
* **Send confirmation email to submitter** - mails a confirmation to the
  address that was submitted. Only available if your project provides mail
  templates for it, see below.

Editors select the actions per form in the form plugin. Actions that need
additional input - a mail recipient, a redirect target, a template set - add
their own fields to the form plugin's editing dialog.

*********************************************
 Sending a confirmation mail to the submitter
*********************************************

This action mails a confirmation to the address a visitor entered into the
form. Since visitors control that address, an implementation without
safeguards would turn your site into a mail relay. The action is therefore
restrictive by design:

* Editors only choose a **template set**. The mail is rendered from templates
  your project provides - neither editors nor visitors can influence what the
  mail says.
* The form needs an ``EmailField`` named ``email``. A text field of the same
  name is not accepted, so a form cannot start sending mail by accident. Set
  ``DJANGOCMS_CONFIRMATION_MAIL_FIELD_NAME`` if your forms use a different
  field name.
* The form needs to be protected against automated submissions, either by a
  captcha or by requiring a login. Submissions of unprotected forms are
  skipped and logged.
* Mails are `rate limited`_ per client address and per recipient address.
* Mails are handed to a small pool of background threads, so a slow mail
  server delays neither the visitor's submission nor the form's other actions.

Whatever the outcome, a failure never breaks the submission: the action logs to
the ``djangocms_form_builder.actions`` logger and returns.

Enabling the action
===================

**djangocms-form-builder** ships no confirmation mail templates, because a
confirmation mail is part of your site's voice, not of a generic package. As
long as ``DJANGOCMS_CONFIRMATION_MAIL_TEMPLATE_SETS`` is empty - which is the
default - the action is not registered at all and does not appear in the form
plugin.

To offer it, name your template sets::

    DJANGOCMS_CONFIRMATION_MAIL_TEMPLATE_SETS = (
        ("default", _("Confirmation")),
        ("event", _("Event registration")),
    )

Keys have to be slugs; they name a directory. If more than one set is
configured, editors pick one per form, otherwise the single set is used.

The templates
=============

Each key needs a template directory
``djangocms_form_builder/confirmation_mails/<key>/`` containing:

``subject.txt``
    Required. Rendered and then reduced to a single line.

``mail.txt``
    The plain text body.

``mail_html.html``
    The HTML body, attached as an alternative part.

At least one of the two bodies is required. If only the HTML body exists, the
text body is derived from it by stripping its tags.

The templates are rendered with the submitted values as plain text:

``form_name``
    The name of the form as configured in the form plugin.

``form_fields``
    A mapping of field name to submitted value.

``form_field_rows``
    A list of dictionaries with ``name``, ``label`` and ``value``, in the order
    of the form's fields. Useful to render a summary table.

Uploads and the captcha field are left out, and values are truncated. Django's
auto-escaping protects your site from submitted markup - do **not** use the
``safe`` filter on these values.

A minimal set of templates::

    {# subject.txt #}
    Thank you for your message

    {# mail.txt #}
    Hello,

    we have received your message and will get back to you shortly.
    {% for row in form_field_rows %}
    {{ row.label }}: {{ row.value }}
    {% endfor %}

    {# mail_html.html #}
    <p>Hello,</p>
    <p>we have received your message and will get back to you shortly.</p>
    <dl>{% for row in form_field_rows %}
      <dt>{{ row.label }}</dt><dd>{{ row.value }}</dd>
    {% endfor %}</dl>

Settings
========

``DJANGOCMS_CONFIRMATION_MAIL_TEMPLATE_SETS``
    Tuple of ``(key, verbose name)`` pairs. Empty by default, which hides the
    action.

``DJANGOCMS_CONFIRMATION_MAIL_FIELD_NAME``
    Name of the form field carrying the recipient address. Defaults to
    ``"email"``.

``DJANGOCMS_CONFIRMATION_MAIL_WORKERS``
    Number of threads sending mails. Defaults to ``2``.

``DJANGOCMS_CONFIRMATION_MAIL_MAX_PENDING``
    How many mails may wait for delivery at a time. Beyond that, mails are
    skipped and logged instead of piling up. Defaults to ``10``.

Mails are sent through Django's mail backend and use ``DEFAULT_FROM_EMAIL`` as
sender.

.. _rate limited:

.. _rate-limits:

*************
 Rate limits
*************

Any form action can be rate limited. Before an action runs, the values it
declares are counted against a fixed time window. Once a limit is used up, that
action is skipped for the rest of the window - the form's other actions still
run, so a submission is, for example, still saved to the database while no
further mail is sent.

Rate limits are opt-in and configured per action class::

    DJANGOCMS_FORM_BUILDER_RATE_LIMITS = {
        # 60 submissions per hour and client address, for every action
        "default": {"source": (60, 60 * 60)},
        # ... but only 3 confirmation mails per address and day
        "SendConfirmationMailAction": {"recipient": (3, 24 * 60 * 60)},
        # switch a built-in limit of an action off
        "SaveToDBAction": {"source": None},
    }

Each entry maps a quota kind to a ``(limit, window in seconds)`` pair.
``"default"`` applies to all actions, an action class name only to that action
and takes precedence over ``"default"``. Both are merged into the limits an
action brings itself: the confirmation mail action limits submissions to 10 per
hour and client address and to 3 mails per recipient and day.

The kind ``source`` is the submitting client and is available for every action.
It is taken from ``REMOTE_ADDR``; if your project runs behind a trusted proxy,
point ``DJANGOCMS_FORM_BUILDER_RATE_LIMIT_IP_META_KEY`` at the ``request.META``
key your proxy sets, e.g. ``"HTTP_X_FORWARDED_FOR"``. Other kinds are provided
by the actions themselves; kinds an action does not provide are ignored.

Counters live in the database, keyed by a hash of the value: neither IP
addresses nor email addresses are stored. Counters of windows that have passed
are removed as new submissions come in.

If the counters cannot be read or written, the action is skipped: a database
incident must not silently disable the limits. Skipped actions are logged to
the ``djangocms_form_builder.rate_limit`` logger - make sure your ``LOGGING``
configuration surfaces its warnings, since a form that quietly stops mailing is
easy to miss.

*************************
 Writing your own action
*************************

Actions are registered with ``djangocms_form_builder.actions.register``, either
as a decorator or as a function call::

    from django.utils.translation import gettext_lazy as _
    from djangocms_form_builder import actions

    @actions.register
    class NotifySalesAction(actions.FormAction):
        verbose_name = _("Notify sales")

        def execute(self, form, request):
            ...  # runs upon successful submission

``execute()`` receives the validated form - its ``cleaned_data`` holds the
submission - and the request. Register your actions once all apps have loaded,
e.g. in your app's ``models.py`` or in the ``ready()`` method of its
``AppConfig``.

Actions may add their own fields to the form plugin's editing dialog by
declaring them as entangled fields. Their values are read back with
``get_parameter()``::

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

Prefix such fields with the action's name to keep them apart from the fields of
other actions.

An action can declare rate limits and the values they are counted against::

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
``DJANGOCMS_FORM_BUILDER_RATE_LIMITS["NotifySalesAction"]``. A value that an
action declares but cannot determine - an empty string or ``None`` - blocks the
action, so only declare kinds a submission really provides.

If an action should only be available under certain conditions, register it
conditionally - the built-in redirect and confirmation mail actions do exactly
that::

    if getattr(settings, "MY_PROJECT_NOTIFIES_SALES", False):

        @actions.register
        class NotifySalesAction(actions.FormAction):
            ...

Actions that are not registered do not show up in the form plugin. Forms that
still refer to an unregistered action report that the action is not available
any more instead of failing.
