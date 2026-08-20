Rate limit form actions
#######################

Any form action can be rate limited. Before an action runs, the values it
declares are counted against a fixed time window. Once a limit is used up, that
action is skipped for the rest of the window - the form's other actions still
run, so a submission can still be saved to the database while no further mail
is sent.

Rate limits are opt-in and configured per action class:

.. code-block:: python

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
action brings itself: the confirmation mail action, for example, already limits
submissions to 10 per hour and client address and to 3 mails per recipient and
day.

The configuration is validated when the app is loaded: a malformed entry raises
``ImproperlyConfigured`` at startup rather than silently doing nothing.

Quota kinds
===========

``source``
   The submitting client, available for every action. It is read from
   ``REMOTE_ADDR``. If your project runs behind a trusted proxy, point
   ``DJANGOCMS_FORM_BUILDER_RATE_LIMIT_IP_META_KEY`` at the ``request.META`` key
   your proxy sets, e.g. ``"HTTP_X_FORWARDED_FOR"``.

Other kinds are provided by the actions themselves - the confirmation mail
action adds ``recipient``. A kind that an action does not provide is ignored, so
configuring ``recipient`` for an action that sends no mail does nothing.

Watch the log
=============

A skipped action is logged as a warning to the ``djangocms_form_builder.rate_limit``
logger. Make sure your ``LOGGING`` configuration surfaces it: a form that
quietly stops mailing is easy to miss.

The check fails closed. If the counters cannot be read or written - a database
incident, say - the action is skipped rather than executed, because an outage
must not silently disable the limits.

Counters live in the database under a keyed hash of the value, so neither IP
addresses nor email addresses are stored. Counters of windows that have passed
are removed once an hour and process, as submissions come in - there is nothing
to schedule.

To rate limit an action of your own, see :doc:`write-an-action`.
