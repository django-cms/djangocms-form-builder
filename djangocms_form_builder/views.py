import hashlib

from cms.models import CMSPlugin
from django.core.exceptions import ValidationError
from django.http import Http404, JsonResponse, QueryDict
from django.shortcuts import get_object_or_404
from django.utils.crypto import get_random_string
from django.utils.translation import gettext as _
from django.views import View

_formview_pool = {}


def register_form_view(cls, slug=None):
    """
    Registers a Widget (with type defined by cls) and slug
    :type cls: class
    :type slug: string to instantiate dashboard_widget
    """
    if not slug:
        slug = get_random_string(length=12)
    key = hashlib.sha384(slug.encode("utf-8")).hexdigest()
    if key in _formview_pool:
        assert _formview_pool[key][0] == cls, _(
            "Only unique slugs accepted for form views"
        )
    _formview_pool[key] = (cls, slug, key)
    return key


class AjaxView(View):
    r"""
    A Django view to handle AJAX requests for GET and POST methods for django CMS Form Builder forms.
    this view allows django CMS plugins to receive ajax requests if they implement the `ajax_get` and
    `ajax_post` methods. The form plugin implements the `ajax_post` method to handle form submissions.

    Methods
    -------

    dispatch(request, \*args, \*\*kwargs)
        Overrides the default dispatch method to handle AJAX requests.

    decode_path(path)
        Decodes a URL path into a dictionary of parameters.

    plugin_instance(pk)
        Retrieves the plugin instance and its associated model instance by primary key.

    ajax_post(request, \*args, \*\*kwargs)
        Handles AJAX POST requests. Calls the `ajax_post` method of the plugin or form instance if available.

    ajax_get(request, \*args, \*\*kwargs)
        Handles AJAX GET requests. Calls the `ajax_get` method of the plugin or form instance if available.
    """
    def dispatch(self, request, *args, **kwargs):
        if request.accepts("application/json"):
            if request.method == "GET" and "get" in self.http_method_names:
                return self.ajax_get(request, *args, **kwargs)
            elif request.method == "POST" and "post" in self.http_method_names:
                return self.ajax_post(request, *args, **kwargs)
        return super().dispatch(request, *args, **kwargs)

    @staticmethod
    def decode_path(path):
        params = {}
        for element in path.split(","):
            if "=" in element:
                params[element.split("=", 1)[0]] = element.split("=", 1)[1]
            elif "%3D" in element:
                params[element.split("%3D", 1)[0]] = element.split("%3D", 1)[1]
            else:
                params[element] = True
        return params

    @staticmethod
    def plugin_instance(pk):
        plugin = get_object_or_404(CMSPlugin, pk=pk)
        plugin.__class__ = plugin.get_plugin_class()
        instance = (
            plugin.model.objects.get(cmsplugin_ptr=plugin.id)
            if hasattr(plugin.model, "cmsplugin_ptr")
            else plugin
        )
        return plugin, instance

    def ajax_post(self, request, *args, **kwargs):
        r"""
        Handles AJAX POST requests for the form builder.

        This method processes AJAX POST requests by determining the appropriate
        plugin or form instance to handle the request based on the provided
        keyword arguments.

        Args:
            request (HttpRequest): The HTTP request object.
            \*args: Additional positional arguments.
            \*\*kwargs: Additional keyword arguments, which may include:
                - instance_id (int): The ID of the plugin instance.
                - parameter (str): Optional parameter for decoding.
                - form_id (str): The ID of the form instance.

        Returns:
            JsonResponse: A JSON response with the result of the AJAX POST request.
            Http404: If the plugin or form instance cannot be found or does not
                     support AJAX POST requests.

        Raises:
            Http404: If the plugin or form instance cannot be found or does not
                     support AJAX POST requests.
            ValidationError: If there is a validation error during the request
                             processing.
        """
        if "instance_id" in kwargs:
            plugin, instance = self.plugin_instance(kwargs["instance_id"])
            if hasattr(plugin, "ajax_post"):
                request.POST = QueryDict(request.body)
                try:
                    params = (
                        self.decode_path(kwargs["parameter"])
                        if "parameter" in kwargs
                        else {}
                    )
                    return plugin.ajax_post(request, instance, params)
                except ValidationError as error:
                    return JsonResponse({"result": "error", "msg": str(error.args[0])})
            else:
                raise Http404()
        elif "form_id" in kwargs:
            if kwargs["form_id"] in _formview_pool:
                form_id = kwargs.pop("form_id")
                instance = _formview_pool[form_id][0](*args, **kwargs)
                if hasattr(instance, "ajax_post"):
                    return instance.ajax_post(request, *args, **kwargs)
                elif hasattr(instance, "post"):
                    return instance.post(request, *args, **kwargs)
            raise Http404()
        raise Http404()

    def ajax_get(self, request, *args, **kwargs):
        r"""
        Handles AJAX GET requests.

        This method processes AJAX GET requests by checking for specific keys in the
        `kwargs` and delegating the request to the appropriate handler.

        Args:
            request (HttpRequest): The HTTP request object.
            \*args: Additional positional arguments.
            \*\*kwargs: Additional keyword arguments.

        Returns:
            JsonResponse: A JSON response with the result of the AJAX request.
            Http404: If the required keys are not found in `kwargs` or the handler is not available.

        Raises:
            ValidationError: If there is an error during the processing of the AJAX request.

        Notes:
            - If "instance_id" is present in `kwargs`, it attempts to retrieve the plugin instance
              and calls its `ajax_get` method if available.
            - If "form_id" is present in `kwargs`, it attempts to retrieve the form instance from
              the `_formview_pool` and calls its `ajax_get` or `get` method if available.
        """
        if "instance_id" in kwargs:
            plugin, instance = self.plugin_instance(kwargs["instance_id"])
            if hasattr(plugin, "ajax_get"):
                request.GET = QueryDict(request.body)
                try:
                    params = (
                        self.decode_path(kwargs["parameter"])
                        if "parameter" in kwargs
                        else {}
                    )
                    return plugin.ajax_get(request, instance, params)
                except ValidationError as error:
                    return JsonResponse({"result": "error", "msg": str(error.args[0])})
        elif "form_id" in kwargs:
            if kwargs["form_id"] in _formview_pool:
                form_id = kwargs.pop("form_id")
                instance = _formview_pool[form_id][0](**kwargs)
                if hasattr(instance, "ajax_get"):
                    return instance.ajax_get(request, *args, **kwargs)
                elif hasattr(instance, "get"):
                    return instance.get(request, *args, **kwargs)
            raise Http404()
        raise Http404()
