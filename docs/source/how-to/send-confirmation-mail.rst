Send a confirmation mail to the submitter
#########################################

The **Send confirmation email to submitter** action mails a confirmation to the
address a visitor entered into the form.

Since visitors control that address, an implementation without safeguards would
turn your site into a mail relay. The action is therefore restrictive by design,
and it is not available until you have made a deliberate decision to offer it.

Provide the templates
=====================

**djangocms-form-builder** ships no confirmation mail templates, because a
confirmation mail is part of your site's voice, not of a generic package. As
long as ``DJANGOCMS_CONFIRMATION_MAIL_TEMPLATE_SETS`` is empty - which is the
default - the action is not registered at all and does not appear in the form
plugin.

Name your template sets:

.. code-block:: python

   DJANGOCMS_CONFIRMATION_MAIL_TEMPLATE_SETS = (
       ("default", _("Confirmation")),
       ("event", _("Event registration")),
   )

Keys have to be slugs; they name a directory. If more than one set is
configured, editors pick one per form, otherwise the single set is used.

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

The context the templates are rendered with is described in
:ref:`confirmation-mail-context`.

Prepare the form
================

Two conditions have to be met by every form using the action, otherwise the mail
is skipped and a warning is logged:

#. The form needs an **Email** field named ``email``. A text field of the same
   name is not accepted, so a form cannot start sending mail by accident. Set
   ``DJANGOCMS_CONFIRMATION_MAIL_FIELD_NAME`` if your forms use a different
   field name.
#. The form has to be protected against automated submissions, either by a
   captcha (see :doc:`add-a-captcha`) or by requiring a login.

Then tick **Send confirmation email to submitter** in the form plugin and pick a
template set.

What the action does not let editors do
=======================================

Editors choose a template set and nothing else. The mail is rendered from
templates your project provides - neither editors nor visitors can influence
what the mail says. Submitted values reach the templates as plain, truncated
text with Django's auto-escaping in force; do **not** apply the ``safe`` filter
to them.

Mails are rate limited per client address and per recipient address, with
built-in limits of 10 submissions per hour and client and 3 mails per recipient
and day. Adjust them through ``DJANGOCMS_FORM_BUILDER_RATE_LIMITS``, see
:doc:`rate-limit-actions`.

Delivery
========

Mails are handed to a small pool of background threads, so a slow mail server
delays neither the visitor's submission nor the form's other actions. Two
settings bound that pool:

``DJANGOCMS_CONFIRMATION_MAIL_WORKERS``
   Number of threads sending mails. Defaults to ``2``.

``DJANGOCMS_CONFIRMATION_MAIL_MAX_PENDING``
   How many mails may wait for delivery at a time. Beyond that, mails are
   skipped and logged instead of piling up. Defaults to ``10``.

Mails are sent through Django's mail backend and use ``DEFAULT_FROM_EMAIL`` as
sender. The pool is created on the first mail and lives as long as the process;
``djangocms_form_builder.confirmation_mail.shutdown_executor()`` tears it down
where that matters, e.g. at the end of a management command, after waiting for
the mails still pending. They carry ``Auto-Submitted: auto-generated`` and
``X-Auto-Response-Suppress: All`` headers so that they do not trigger automatic
replies.

Whatever the outcome, a failure never breaks the submission: the action logs to
the ``djangocms_form_builder.actions`` logger and returns, and a delivery that
fails in a background thread is logged to the
``djangocms_form_builder.confirmation_mail`` logger. Watch that logger -
and the ``djangocms_form_builder.rate_limit`` one - if you rely on the mail
going out.
