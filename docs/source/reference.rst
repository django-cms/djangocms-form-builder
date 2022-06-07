###########
 Reference
###########

**********
 Settings
**********

**djangocms-frontend** can be configured by putting the appropriate settings
in your project's ``settings.py``.

.. py:attribute:: settings.DJANGOCMS_FRONTEND_TAG_CHOICES

    Defaults to ``['div', 'section', 'article', 'header', 'footer', 'aside']``.

    Lists the choices for the tag field of all djangocms-frontend plugins.
    ``div`` is the default tag.

    These tags appear in Advanced Settings of some elements for editors to
    chose from.

.. py:attribute:: settings.DJANGOCMS_FRONTEND_GRID_SIZE

    Defaults to ``12``.



.. py:attribute:: settings.DJANGOCMS_FRONTEND_GRID_CONTAINERS

    Default:

    .. code::

        (
            ("container", _("Container")),
            ("container-fluid", _("Fluid container")),
            ("container-full", _("Full container")),
        )

.. py:attribute:: settings.DJANGOCMS_FRONTEND_USE_ICONS

    Defaults to ``True``.

    Decides if icons should be offered, e.g. in links.

.. py:attribute:: settings.DJANGOCMS_FRONTEND_CAROUSEL_TEMPLATES

    Defaults to ``(('default', _('Default')),)``

    If more than one option is given editors can select which template a
    carousel uses for rendering. Carousel expects the templates in a template
    folder under ``djangocms_frontend/bootstrap5/carousel/{{ name }}/``.
    ``{{ name }}`` denotes the value of the template, i.e. ``default`` in the
    default example.

    Carousel requires at least two files: ``carousel.html`` and ``slide.html``.

.. py:attribute:: settings.DJANGOCMS_FRONTEND_TAB_TEMPLATES

    Defaults to ``(('default', _('Default')),)``

    If more than one option is given editors can select which template a
    tab element uses for rendering. Tabs expects the templates in a template
    folder under ``djangocms_frontend/bootstrap5/tabs/{{ name }}/``.
    ``{{ name }}`` denotes the value of the template, i.e. ``default`` in the
    default example.

    Tabs requires at least two files: ``tabs.html`` and ``item.html``.


.. py:attribute:: settings.DJANGOCMS_FRONTEND_LINK_TEMPLATES

    Defaults to ``(('default', _('Default')),)``

    If more than one option is given editors can select which template a
    link or button element uses for rendering. Link expects the templates in a template
    folder under ``djangocms_frontend/bootstrap5/link/{{ name }}/``.
    ``{{ name }}`` denotes the value of the template, i.e. ``default`` in the
    default example.

    Link requires at least one file: ``link.html``.


.. py:attribute:: settings.DJANGOCMS_FRONTEND_JUMBOTRON_TEMPLATES

    Defaults to ``(('default', _('Default')),)``

    Jumbotrons have been discontinued form Bootstrap 5 (and are not present
    in other frameworks either). The default template mimics the Bootstrap 4's
    jumbotron.

    If more than one option is given editors can select which template a
    jumbotron element uses for rendering. Jumbotron expects the template in a template
    folder under ``djangocms_frontend/bootstrap5/jumbotron/{{ name }}/``.
    ``{{ name }}`` denotes the value of the template, i.e. ``default`` in the
    default example.

    Link requires at least one file: ``jumbotron.html``.


.. py:attribute:: settings.DJANGOCMS_FRONTEND_SPACER_SIZES

    Default:

    .. code::

        (
           ('0', '* 0'),
           ('1', '* .25'),
           ('2', '* .5'),
           ('3', '* 1'),
           ('4', '* 1.5'),
           ('5', '* 3'),
       )

.. py:attribute:: settings.DJANGOCMS_FRONTEND_CAROUSEL_ASPECT_RATIOS

    Default: ``((16, 9),)``

    Additional aspect ratios offered in the carousel component

.. py:attribute:: settings.DJANGOCMS_FRONTEND_COLOR_STYLE_CHOICES

    Default:

    .. code::

        (
            ("primary", _("Primary")),
            ("secondary", _("Secondary")),
            ("success", _("Success")),
            ("danger", _("Danger")),
            ("warning", _("Warning")),
            ("info", _("Info")),
            ("light", _("Light")),
            ("dark", _("Dark")),
        )

.. py:attribute:: settings.DJANGOCMS_FRONTEND_ADMIN_CSS

    Default: ``None``

    Adds css format files to the frontend editing forms of
    **djangocms-frontend**. The syntax is with a ``ModelForm``'s
    ``css`` attribute of its ``Media`` class, e.g.,
    ``DJANGOCMS_FRONTEND_ADMIN_CSS = {"all": ("css/admin.min.css",)}``.

    This css might be used to style have theme-specific colors available
    in the frontend editing forms. The included css file is custom made and
    should only contain color settings in the form of

    .. code-block::

        .frontend-button-group .btn-primary {
            color: #123456;  // add !important here if using djangocms-admin-style
            background-color: #abcdef;
        }

    .. note::

        Changing the ``color`` attribute might require a ``!important`` statement
        if you are using **djangocms-admin-style**.

.. py:attribute:: settings.DJANGOCMS_FRONTEND_MINIMUM_INPUT_LENGTH

    If unset or smaller than ``1`` the link plugin will render all link options
    into its form. If ``1`` or bigger the link form will wait for the user to
    type at least this many letters and search link targets matching this search
    string using an ajax request.


.. py:attribute:: settings.TEXT_SAVE_IMAGE_FUNCTION

    Requirement: ``TEXT_SAVE_IMAGE_FUNCTION = None``

    .. warning::

        Please be aware that this package does not support
        djangocms-text-ckeditor's `Drag & Drop Images
        <https://github.com/divio/djangocms-text-ckeditor/#drag--drop-images>`_
        so be sure to set ``TEXT_SAVE_IMAGE_FUNCTION = None``.




******
Models
******

**djangocms-frontend** subclasses the ``CMSPlugin`` model.

.. py:class:: FormUIItem(CMSPlugin)

    Import from ``djangocms_frontend.models``.

    All concrete models for UI items are proxy models of this class.
    This implies you can create, delete and update instances of the proxy models
    and all the data will be saved as if you were using this original
    (non-proxied) model.

    This way all proxies can have different python methods as needed while still
    all using the single database table of ``FormUIItem``.

.. py:attribute:: FormUIItem.ui_item

    This CharField contains the UI item's type without the suffix "Plugin",
    e.g. "Link" and not "LinkPlugin". This is a convenience field. The plugin
    type is determined by ``CMSPlugin.plugin_type``.

.. py:attribute:: FormUIItem.tag_type

    This is the tag type field determining what tag type the UI item should have.
    Tag types default to ``<div>``.

.. py:attribute:: FormUIItem.config

    The field ``config`` is the JSON field that contains a dictionary with all specific
    information needed for the UI item. The entries of the dictionary can be
    directly **read** as attributes of the ``FormUIItem`` instance. For
    example, ``ui_item.context`` will give ``ui_item.config["context"]``.

    .. warning::

        Note that changes to the ``config`` must be written directly to the
        dictionary:  ``ui_item.config["context"] = None``.


.. py:method:: FormUIItem.add_classes(self, *args)

    This helper method allows a Plugin's render method to add framework-specific
    html classes to be added when a model is rendered. Each positional argument
    can be a string for a class name or a list of strings to be added to the list
    of html classes.

    These classes are **not** saved to the database. They merely a are stored
    to simplify the rendering process and are lost once a UI item has been
    rendered.

.. py:method:: FormUIItem.get_attributes(self)

    This method renders all attributes given in the optional ``attributes``
    field (stored in ``.config``). The ``class`` attribute reflects all
    additional classes that have been passed to the model instance by means
    of the ``.add_classes`` method.

.. py:method:: FormUIItem.initialize_from_form(self, form)

    Since the UIItem models do not have default values for the contents of
    their ``.config`` dictionary, a newly created instance of an UI item
    will not have config data set, not even required data.

    This method initializes all fields in ``.config`` by setting the value to
    the respective ``initial`` property of the UI items admin form.

.. py:method:: FormUIItem.get_short_description(self)

    returns a plugin-specific short description shown in the structure mode
    of django CMS.

**************
 Form widgets
**************

**djangocms-frontend** contains button group widgets which can be used as
for ``forms.ChoiceField``. They might turn out helpful when adding custom
plugins.

.. py:class:: ButtonGroup(forms.RadioSelect)

    Import from ``djangocms_frontend.fields``

    The button group widget displays a set of buttons for the user to chose. Usable for up
    to roughly five options.

.. py:class:: ColoredButtonGroup(ButtonGroup)

    Import from ``djangocms_frontend.fields``

    Used to display the context color selection buttons.

.. py:class:: IconGroup(ButtonGroup)

    Import from ``djangocms_frontend.fields``.

    This widget displays icons in stead of text for the options. Each icon is rendered
    by ``<span class="icon icon-{{value}}"></span>``. Add css in the ``Media``
    subclass to ensure that for each option's value the span renders the
    appropriate icon.

.. py:class:: IconMultiselect(forms.CheckboxSelectMultiple)

    Import from ``djangocms_frontend.fields``.

    Like ``IconGroup`` this widget displays a choice of icons. Since it inherits
    from ``CheckboxSelectMultiple`` the icons work like checkboxes and not radio
    buttons.

.. py:class:: OptionalDeviceChoiceField(forms.MultipleChoiceField)

    Import from ``djangocms_frontend.fields``.

    This form field displays a choice of devices corresponding to breakpoints
    in the responsive grid. The user can select any combination of devices
    including none and all.

    The result is a list of values of the selected choices or None for all devices
    selected.

.. py:class:: DeviceChoiceField(OptionalDeviceChoiceField)

    Import from ``djangocms_frontend.fields``.

    This form field is identical to the ``OptionalDeviceChoiceField`` above,
    but requires the user to select at least one device.





*********************
 Management commands
*********************

Management commands are run by typing ``./manage.py frontend command`` in the
project directory. ``command`` can be one of the following:

``migrate``
    Migrates plugins from other frontend packages to **djangocms-frontend**.
    Currently supports **djangocms_bootstrap4** and **djangocms_styled_link**.

``stale_references``
    If references in a UI item are moved or removed the UI items are designed to
    fall back gracefully and both not throw errors or be deleted themselves
    (by a db cascade).

    The drawback is, that references might become stale. This command prints all
    stale references, their plugins and pages/placeholder they belong to.

``sync_permissions users`` or ``sync_permissions groups``
    Django allows to set permissions for each user and group on a per plugin
    level. This might become somewhat tedious which is why this command
    will sync permissions. For each user or group it will copy the permissions
    of ``djangocms_frontend.models.FormUIItem`` to all installed
    djangocms-frontend plugins. If you need to change permissions for all
    plugins this requires you only to change them for ``FormUIItem`` and
    then syncing the new permission with these commands.


***************
 Running Tests
***************

You can run tests by executing:

.. code::

   virtualenv env
   source env/bin/activate
   pip install -r tests/requirements.txt
   python ./run_tests.py

