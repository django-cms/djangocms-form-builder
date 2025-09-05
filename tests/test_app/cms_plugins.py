from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import gettext_lazy as _


@plugin_pool.register_plugin
class ContainerPlugin(CMSPluginBase):
    name = _("Container")
    render_template = "test_app/container.html"
    allow_children = True
