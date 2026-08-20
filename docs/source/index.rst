djangocms-form-builder documentation
####################################

**djangocms-form-builder** adds a form editor to the structure board of
`django CMS <https://www.django-cms.org>`_. Editors build forms from plugins -
one plugin per form field - and decide per form what happens to a submission:
store it, mail it, show a message, redirect, or run an action your project
provides.

Forms are submitted by ``fetch()`` to a JSON endpoint the app installs itself,
so a page may carry as many forms as you like without a page reload.

The documentation is organised along the four kinds of documentation described
by the `Diátaxis framework <https://diataxis.fr>`_:

:doc:`Tutorial <tutorial/index>`
   A guided first form: install the app, build a contact form in the structure
   board and read the submission in the admin.

:doc:`How-to guides <how-to/index>`
   Recipes for a concrete goal - registering an existing Django form, writing
   an action, protecting a public form with a captcha, accepting uploads.

:doc:`Reference <reference/index>`
   The settings, plugins, models, template tags, management commands and Python
   APIs, described as they are implemented.

:doc:`Explanation <explanation/index>`
   Background on how the pieces fit together and why forms open to the public
   are treated the way they are.

.. toctree::
   :maxdepth: 2

   tutorial/index
   how-to/index
   reference/index
   explanation/index

.. toctree::
   :hidden:

   genindex

Indices and tables
==================

-  :ref:`genindex`
-  :ref:`search`
