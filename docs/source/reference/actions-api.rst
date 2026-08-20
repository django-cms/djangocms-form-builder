Form actions
############

What happens to a submission is decided by the **form actions** selected in the
form plugin. An action is a class with an ``execute()`` method that runs once a
form has been submitted and validated. A form can run several actions.

Built-in actions
================

**Save form submission** (``SaveToDBAction``)
   Stores the submitted data as a :class:`FormEntry`. For a form with *Login
   required* **and** *User can reopen form*, an existing entry of that user and
   form is updated instead of a new one created. Uploaded files are written to
   storage and replaced files deleted, see :doc:`../how-to/handle-file-uploads`.

**Send email** (``SendMailAction``)
   Mails the submission to the site admins, or to the addresses the editor
   entered in *Mail recipients* (space or newline separated). The mail is
   rendered from the template set chosen in ``DJANGOCMS_MAIL_TEMPLATE_SETS``.

   The mail body describes the **last** form entry in the database, so this
   action is meant to be combined with *Save form submission*.

   A failed delivery does not break the submission; it is logged to the
   ``djangocms_form_builder.actions`` logger.

**Success message** (``SuccessMessageAction``)
   Replaces the form with the message the editor entered. The message is edited
   with djangocms-text if that package is installed, and in a plain textarea
   otherwise.

**Redirect after submission** (``RedirectAction``)
   Redirects to the link the editor chose. Only registered if **djangocms-link**
   is installed.

**Send confirmation email to submitter** (``SendConfirmationMailAction``)
   Mails a confirmation to the address submitted with the form. Only registered
   if ``DJANGOCMS_CONFIRMATION_MAIL_TEMPLATE_SETS`` is configured, see
   :doc:`../how-to/send-confirmation-mail`.

Actions that need additional input add their own fields to the form plugin's
editing dialog.

An action whose class is no longer registered is not an error: the submission
reports *Action not available any more* for it and the remaining actions run.

.. _confirmation-mail-context:

Confirmation mail template context
----------------------------------

The templates of ``SendConfirmationMailAction`` are rendered with the submitted
values as plain text:

``form_name``
   The form identifier configured in the form plugin.

``form_fields``
   Mapping of field name to submitted value.

``form_field_rows``
   List of dictionaries with ``name``, ``label`` and ``value``, in the order of
   the form's fields. Useful to render a summary table.

Uploads and the captcha field are left out, and values are truncated to 2000
characters. Auto-escaping protects your site from submitted markup - do **not**
use the ``safe`` filter on these values.

The ``FormAction`` API
======================

.. code-block:: python

   from djangocms_form_builder import actions

``actions.FormAction``
   Base class of all actions. It is an ``EntangledModelFormMixin`` on the
   ``Form`` plugin model, which is why an action can contribute fields to the
   plugin's dialog.

   ``verbose_name``
      Required. The name editors see.

   ``rate_limits``
      Built-in rate limits as ``{kind: (limit, window in seconds)}``. Empty by
      default. Projects override them per action class name in
      ``DJANGOCMS_FORM_BUILDER_RATE_LIMITS``.

   ``execute(form, request)``
      Called after a successful submission. Must be implemented; the base
      implementation raises ``NotImplementedError``. The return value is
      ignored.

   ``get_rate_limit_values(form, request)``
      The values this submission is counted against, by quota kind. Returns
      ``{"source": <client address>}`` by default. Kinds an action does not
      provide are not rate limited.

   ``check_rate_limits(form, request)``
      Consumes this submission's quotas. ``False`` means the action is skipped.

   ``get_parameter(form, name)`` (static)
      The value an editor entered for one of the action's own fields.

``actions.register(action_class)``
   Registers an action; usable as a decorator. Raises ``ImproperlyConfigured``
   for anything that is not a ``FormAction`` subclass or that has no
   ``verbose_name``.

``actions.unregister(action_class)``
   Removes an action from the registry again.

``actions.get_registered_actions()``
   ``(hash, verbose name)`` pairs for a choice field.

``actions.get_action_class(hash)``
   The action class for a stored hash, or ``None``.

``actions.get_hash(action_class)``
   The hash a class is stored under - the SHA-1 of its class name.

Actions are identified by the hash of their **class name**, so renaming an
action class detaches it from the forms that use it.

Rate limits
===========

``djangocms_form_builder.rate_limit`` implements fixed-window counters:

``get_rate_limits(action_class)``
   The action's own limits, merged with ``DJANGOCMS_FORM_BUILDER_RATE_LIMITS``
   (``"default"`` first, then the entry for the class name).

``client_address(request)``
   The submitting client, read from the ``request.META`` key named by
   ``DJANGOCMS_FORM_BUILDER_RATE_LIMIT_IP_META_KEY``.

``check_rate_limits(action, form, request)``
   Consumes the quotas of one action. Returns ``False`` if a limit is used up,
   if a value that should be counted is unavailable, or if the counters cannot
   be read or written.

Counters are stored in :class:`SubmissionQuota`, keyed by an HMAC of the counted
value under the project's ``SECRET_KEY``. Expired counters are deleted by
``prune_expired_if_due()``, which runs at most once per ``PRUNE_INTERVAL``
(one hour) and process so that pruning stays off the hot path of a submission.
