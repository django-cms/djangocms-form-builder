########################
 django CMS form builder
########################

|pypi| |coverage| |python| |django| |djangocms| |djangocms4|

**djangocms-form-builder** supports rendering of styled forms. The objective is to tightly integrate forms in the website design. **djangocms-form-builder** allows as many forms as you wish on one page. All forms are **xhr-based**. To this end, **djangocms-form-builder** extends the django CMS plugin model allowing a form plugin to receive xhr post requests.

There are two different ways to manage forms with **djangocms-form-builder**:

1. **Building a form with django CMS' powerful structure board.** This is fast an easy. It integrates smoothly with other design elements, especially the grid elements allowing to design simple responsive forms.

   Form actions can be configured by form. Built in actions include saving the    results in the database for later evaluation and mailing submitted forms to   the site admins. Other form actions can be registered.

2. Works with **django CMS v4** and **djangocms-alias** to manage your forms centrally. Djangocms-alias becomes your form editor and forms can be placed on pages by referring to them with their alias.

3. **Registering an application-specific form with djangocms-form-builder.** If you already have forms you may register them with djangocms-form-builder and allow editors to use them in the form plugin. If you only have simpler design requirements, **djangocms-form-builder** allows you to use fieldsets as with admin forms.

**************
 Key features
**************

-  Supports `Bootstrap 5 <https://getbootstrap.com>`_.

-  Open architecture to support other css frameworks.

-  Integrates with `django-crispy-forms <https://github.com/django-crispy-forms/django-crispy-forms>`_

- Integrates with `djangocms-frontend <https://github.com/django-cms/djangocms-frontend>`_


Feedback
========

This project is in a early stage. All feedback is welcome! Please mail me at fsbraun(at)gmx.de

Also, all contributions are welcome.

Contributing
============

This is a an open-source project. We'll be delighted to receive your feedback in the form of issues and pull requests. Before submitting your pull request, please review our `contribution guidelines <http://docs.django-cms.org/en/latest/contributing/index.html>`_.

We're grateful to all contributors who have helped create and maintain this package. Contributors are listed at the `contributors <https://github.com/fsbraun/djangocms-form-builder/graphs/contributors>`_ section.


************
Installation
************

For a manual install:

- run ``pip install djangocms-form-builder``, **or**

-  run ``pip install git+https://github.com/fsbraun/djangocms-form-builder@master#egg=djangocms-form-builder``

-  add ``djangocms_form_builder`` to your ``INSTALLED_APPS``. (If you are using both djangocms-frontend and djangocms-form-builder, add it **after** djangocms-frontend

-  run ``python manage.py migrate``

*****
Usage
*****

Creating forms using django CMS' structure board
================================================

First create a ``Form`` plugin to add a form. Each form created with help of the structure board needs a unique identifier (formatted as a slug).

Add form fields by adding child classes to the form plugin. Child classes can be form fields but also any other CMS Plugin. CMS Plugins may, e.g., be used to add custom formatting or additional help texts to a form.

Form fields
-----------

Currently the following form fields are supported:

* CharField, EmailField, URLField
* DecimalField, IntegerField
* Textarea
* DateField, DateTimeField, TimeField
* SelectField
* BooleanField

A Form plugin must not be used within another Form plugin.

Actions
-------

Upon submission of a valid form actions can be performed. A project can register as many actions as it likes::

    from djangocms_form_builder import actions

    @actions.register
    class MyAction(actions.FormAction):
        verbose_name = _("Everything included action")

        def execute(self, form, request):
            ...  # This method is run upon successful submission of the form


To add this action, this needs to be added to your project at startup. Fabian suggests putting these actions in your apps models.py file. Another options is your apps, apps.py file::

    from django.apps import AppConfig

    class MyAppConfig(AppConfig):
        default_auto_field = 'django.db.models.BigAutoField'
        name = 'myapp'
        label = 'myapp'
        verbose_name = _("My App")
        
        def ready(self):
            super().ready()

            from djangocms_form_builder import actions

            @actions.register
            class MyAction(actions.FormAction):
                verbose_name = _("Everything included action")

                def execute(self, form, request):
                    ...  # This method is run upon successful submission of the form
                    # Process form and request data, you can send an email to the person who filled the form
                    # Or admins though that functionality is available from the default SendMailAction



Using (existing) Django forms with djangocms-form-builder
=========================================================

The ``Form`` plugin also provides access to Django forms if they are registered with djangocms-form-builder::

    from djangocms_form_builder import register_with_form_builder

    @register_with_form_builder
    class MyGreatForm(forms.Form):
        ...

Alternatively you can also register at any other place in the code by running ``register_with_form_builder(AnotherGreatForm)``.

By default the class name is translated to a human readable form (``MyGreatForm`` -> ``"My Great Form"``). Additional information may be added using Meta classes::

    @register_with_form_builder
    class MyGreatForm(forms.Form):
        class Meta:
            verbose_name = _("My great form")  # can be localized
            redirect = "https://somewhere.org"  # string or object with get_absolute_url() method
            floating_labels = True  # switch on floating labels
            field_sep = "mb-3"  # separator used between fields (depends on css framework)

The verbose name will be shown in a Select field of the Form plugin.

Upon form submission a ``save()`` method of the form (if it has one). After executing the ``save()`` method the user is redirected to the url given in the  ``redirect`` attribute.

Actions are not available for Django forms. Any actions to be performed upon submission should reside in its ``save()`` method.


.. |pypi| image:: https://badge.fury.io/py/djangocms-form-builder.svg
   :target: http://badge.fury.io/py/djangocms-form-builder

.. |coverage| image:: https://codecov.io/gh/fsbraun/djangocms-form-builder/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/fsbraun/djangocms-form-builder

.. |python| image:: https://img.shields.io/badge/python-3.7+-blue.svg
   :target: https://pypi.org/project/djangocms-form-builder/

.. |django| image:: https://img.shields.io/badge/django-3.2-blue.svg
   :target: https://www.djangoproject.com/

.. |djangocms| image:: https://img.shields.io/badge/django%20CMS-3.8%2B-blue.svg
   :target: https://www.django-cms.org/

.. |djangocms4| image:: https://img.shields.io/badge/django%20CMS-4-blue.svg
   :target: https://www.django-cms.org/
