=========
Changelog
=========

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

**New Contributors**
* @arunk made their first contribution in https://github.com/django-cms/djangocms-form-builder/pull/13


0.1.1 (2021-09-14)
==================

* feat: updated captcha optional til active by @svandeneertwegh in https://github.com/fsbraun/djangocms-form-builder/pull/4
* feat: Allow actions to add form fields for configuration by @fsbraun in https://github.com/fsbraun/djangocms-form-builder/pull/6
* fix: Update converage action by @fsbraun in https://github.com/fsbraun/djangocms-form-builder/pull/10
* feat: move to hatch build process by @fsbraun
* ci: Add tests for registry by @fsbraun in https://github.com/fsbraun/djangocms-form-builder/pull/5

New Contributors

* @svandeneertwegh made their first contribution in https://github.com/fsbraun/djangocms-form-builder/pull/4

0.2.0 (unreleased)
=================
* Removed col and rows setting from CharField form plugin
* Set more margin options in spacing between fields
* Fixed anonymous as None to Foregin key 'form_user'
* Added attributesField to every Form plugin for customizing

0.1.0
==================

* Set ``default_auto_field`` to ``BigAutoField`` to ensure projects don't try to create a migration if they still use ``AutoField``
* Transfer of forms app from djangocms-frontend
