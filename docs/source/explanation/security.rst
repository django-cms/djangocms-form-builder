Forms open to the public
########################

A form on a public page is an endpoint that anyone - and anything - can post to.
This page describes what the package does about that, and what it leaves to you.

What the package assumes
========================

Three assumptions run through the code:

#. **Everything a visitor sends is untrusted.** Submitted values are escaped
   wherever they are rendered, and stripped of safe-string markers before they
   reach a mail template.
#. **A failing side effect must not fail the submission.** A mail that cannot be
   sent, a file that cannot be deleted, a counter that cannot be written - all
   of these are logged, not raised. Which means the logs are where problems
   surface.
#. **Nothing that could be abused is on by default.** No captcha, no rate
   limits, no confirmation mail. Turning them on is a decision the project makes.

That last point cuts both ways: a form built exactly as the tutorial describes
has no anti-spam measure at all.

Spam and automated submissions
==============================

The only measure the package offers here is a captcha, and it requires
installing a provider - see :doc:`../how-to/add-a-captcha`. Altcha is worth a
look because it needs no third-party service and no keys.

Rate limits (:doc:`../how-to/rate-limit-actions`) are not an anti-spam measure
in the same sense, but they bound the damage: they are applied per action, so a
flood can still be stored while the mails it would have triggered stop.

Mails to addresses a visitor typed
==================================

Any mail sent to an address that came out of a public form can be used to send
mail on your behalf: pick a target address, submit the form repeatedly, and your
server does the delivering. This is why the *Send confirmation email to
submitter* action is hedged in as it is:

* the action does not exist until the project provides mail templates - editors
  can never write the text of a mail that goes to a stranger;
* the recipient has to come from an actual ``EmailField``, so a text field an
  editor happened to name ``email`` cannot start a mail flow;
* the form has to be protected by a captcha or a login;
* mails are limited per client and per recipient address.

If you write an action that mails visitors, apply the same reasoning - the
building blocks are documented in :doc:`../how-to/write-an-action`.

Uploads
=======

Uploaded files go to Django's ``default_storage`` unless configured otherwise.
On a typical project that means they are served under ``MEDIA_URL``, readable by
anyone with the URL. The random component in the stored file name makes URLs
hard to guess, which is not the same as access control.

For forms that collect anything sensitive, point
``DJANGOCMS_FORM_BUILDER_FILE_FIELD_STORAGE`` at a private backend. The setting
is used for writing, for the stored URL and for deletion, so a private backend
stays private throughout the file's life.

Beyond that, uploads are validated server-side by the presets a project defines
(:doc:`../how-to/handle-file-uploads`), the number of files per field is capped
by the editor, and Django's own upload limits apply to every request.

Stored submissions
==================

Submissions are personal data more often than not, and nothing expires them
automatically. ``prune_form_entries`` is the tool
(:doc:`../how-to/prune-form-entries`); running it regularly is the project's
job. Deleting an entry deletes its uploads too, so retention covers
attachments.

The rate limit counters deliberately store no personal data: the counted value -
a client address, a mail address - is put through an HMAC keyed with the
project's ``SECRET_KEY``, and only the resulting key is written to the database.

What to watch in the logs
=========================

Because failures are logged rather than raised, these loggers are worth routing
somewhere visible:

``djangocms_form_builder.actions``
   Mails that could not be sent; confirmation mails skipped because a form has
   no valid email field or no protection.

``djangocms_form_builder.rate_limit``
   Actions skipped because a limit was reached - or because the counters could
   not be read, in which case the action is skipped rather than run.

``djangocms_form_builder.confirmation_mail``
   Confirmation mails that failed in the background threads, and a full delivery
   queue.

``djangocms_form_builder.form_entry_data``
   Uploads that could not be deleted from storage, and therefore need manual
   cleanup.

``djangocms_form_builder.upload_form_fields``
   Misconfigured validation presets. Visitors see a generic message; the reason
   is in this log.
