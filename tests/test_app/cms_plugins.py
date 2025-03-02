from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import gettext_lazy as _

from .models import Container


@plugin_pool.register_plugin
class ContainerPlugin(CMSPluginBase):
    name = _("Container")
    model = Container
    render_template = "test_app/container.html"
    allow_children = True
