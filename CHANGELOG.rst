=========
Changelog
=========

unpublished
==================

* feat: Add support for Django 6.1
* feat: Add a "Send confirmation email to submitter" action which mails a
  server-owned template to the address submitted with a form. It is only
  offered if the project configures
  ``DJANGOCMS_CONFIRMATION_MAIL_TEMPLATE_SETS`` - no templates are shipped
* feat: Form actions can be rate limited per client and per action-specific
  value (e.g. a mail recipient) through ``DJANGOCMS_FORM_BUILDER_RATE_LIMITS``


0.6.0 (2026-07-23)
==================

* feat: add FileUpload and MultipleFileUpload fields in forms by
  @corentinbettiol in https://github.com/django-cms/djangocms-form-builder/pull/44
* feat: Add Captcha form element plugin by @fsbraun in https://github.com/django-cms/djangocms-form-builder/pull/59
* feat: Add ``prune_form_entries`` management command to enforce a retention
  policy for stored form entries
* feat: The send email action logs failed deliveries to the
  ``djangocms_form_builder.actions`` logger instead of silently dropping them
* feat: Security hardening for public forms by @fsbraun in https://github.com/django-cms/djangocms-form-builder/pull/57
* fix: Make ``djangocms-text`` a soft dependency - the success message action
  falls back to a plain textarea if it is not installed
* fix: ``SaveToDBAction`` no longer stores the ``User-Agent`` and ``Referer``
  request headers (which also caused a server error when the headers were
  absent); the ``html_headers`` field is no longer populated
* fix: Captcha configuration parameters (``data-*`` attributes and api
  parameters) were never passed to the captcha widget
* fix: Make the database schema independent of installed captcha packages to
  avoid spurious migrations in user projects
* fix: ``register_form_view`` raises ``ImproperlyConfigured`` instead of using
  ``assert`` (which is stripped in optimized mode) for duplicate slugs
* fix: Correct verbose names of ``DateTimeField`` and ``TimeField`` models
* fix: Escape help texts, validation error messages and attribute names when
  rendering widgets
* fix: Reserved form field name list contained ``html_header`` instead of
  ``html_headers``
* fix: Enforce min/max length on CharField and TextareaField (#53) by @fsbraun
  in https://github.com/django-cms/djangocms-form-builder/pull/56
* chore: Remove dead code inherited from djangocms-frontend (device choice
  fields, icon widgets, template helpers, form mixin stubs, and more)

**New Contributors**

* @corentinbettiol made their first contribution in https://github.com/django-cms/djangocms-form-builder/pull/44


0.5.1 (2026-06-01)
==================

* feat: Allow caching of form plugin by @fsbraun in https://github.com/django-cms/djangocms-form-builder/pull/52
* feat: Add Altcha CAPTCHA support by @pierreben in https://github.com/django-cms/djangocms-form-builder/pull/43
* fix: Remove context print on ajax form when form is valid by @pierreben in https://github.com/django-cms/djangocms-form-builder/pull/48
* fix: GET form endpoint caused a server error by @fsbraun in https://github.com/django-cms/djangocms-form-builder/pull/47
* fix: FormPlugin should never be in cache by @pierreben in https://github.com/django-cms/djangocms-form-builder/pull/50
* fix: Anonymous users not detected correctly in mail_html.html by @svandeneertwegh in https://github.com/django-cms/djangocms-form-builder/pull/54
* docs: Update django-altcha related docs and version requirement after… by @pierreben in https://github.com/django-cms/djangocms-form-builder/pull/49

**New Contributors**

* @vinitkumar made their first contribution in https://github.com/django-cms/djangocms-form-builder/pull/45


0.5.0 (2026-03-09)
==================

* feat: Add required class to form widget div attributes by @pierreben in https://github.com/django-cms/djangocms-form-builder/pull/35
* feat: Add help text for form fields and submit button context by @fsbraun in https://github.com/django-cms/djangocms-form-builder/pull/40
* fix: Strip email subject to remove newline characters by @pierreben in https://github.com/django-cms/djangocms-form-builder/pull/36
* fix: Avoid reverse in apps.ready() since it is not async safe by @fsbraun in https://github.com/django-cms/djangocms-form-builder/pull/39
* fix: Exclude captcha field from mail by @pierreben in https://github.com/django-cms/djangocms-form-builder/pull/37

**New Contributor**

* @pierreben made their first contribution in https://github.com/django-cms/djangocms-form-builder/pull/35


0.4.0 (2025-11-03)
==================

* feat: French and Dutch locales
* fix: Form entries admin compatibility with latest django-entangled (#32)

0.3.2 (2025-03-04)
==================

* fix: Action tab failed form validation if djangocms-link was installed

0.3.1 (2025-03-03)
==================

* fix: Send mail action failed  by @fsbraun in https://github.com/django-cms/djangocms-form-builder/pull/21
* fix: Correct send_mail recipients parameter in action.py by @fdik in https://github.com/django-cms/djangocms-form-builder/pull/22
* docs: Update Codecov link in  README.rst by @fsbraun in https://github.com/django-cms/djangocms-form-builder/pull/23
* fix: prevent duplicate submit buttons in forms by @earthcomfy in https://github.com/django-cms/djangocms-form-builder/pull/27

**New Contributors**

* @fdik made their first contribution in https://github.com/django-cms/djangocms-form-builder/pull/22
* @earthcomfy made their first contribution in https://github.com/django-cms/djangocms-form-builder/pull/27


0.3.0 (2025-01-07)
==================

* feat: Success message and redirect action by @fsbraun
* fix: forms did not redirect to same page if sent from alias by @fsbraun

0.2.0 (2025-01-06)
==================

* fix: github coverage action by @fsbraun in https://github.com/django-cms/djangocms-form-builder/pull/12
* fix: an error when an anonymous user fills the form by @arunk in https://github.com/django-cms/djangocms-form-builder/pull/13
* fix: Add support for Django-entangled 0.6+ by @fsbraun in https://github.com/django-cms/djangocms-form-builder/pull/19
* docs: Updated README.rst to show where to add actions by @arunk in https://github.com/django-cms/djangocms-form-builder/pull/14
* chore: Added venv/ directory to .gitignore by @arunk in https://github.com/django-cms/djangocms-form-builder/pull/15

**New Contributor**
* @arunk made their first contribution in https://github.com/django-cms/djangocms-form-builder/pull/13


0.1.1 (2021-09-14)
==================

* feat: updated captcha optional til active by @svandeneertwegh in https://github.com/fsbraun/djangocms-form-builder/pull/4
* feat: Allow actions to add form fields for configuration by @fsbraun in https://github.com/fsbraun/djangocms-form-builder/pull/6
* fix: Update converage action by @fsbraun in https://github.com/fsbraun/djangocms-form-builder/pull/10
* feat: move to hatch build process by @fsbraun
* ci: Add tests for registry by @fsbraun in https://github.com/fsbraun/djangocms-form-builder/pull/5

**New Contributor**

* @svandeneertwegh made their first contribution in https://github.com/fsbraun/djangocms-form-builder/pull/4

0.1.0 (unreleased)
==================

* Set ``default_auto_field`` to ``BigAutoField`` to ensure projects don't try to create a migration if they still use ``AutoField``
* Transfer of forms app from djangocms-frontend
