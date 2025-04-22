from config.settings import AuthSettings
from addons.integration.hooks import hookspec
from addons.integration.plugins.capsule import CapsulePlugin
import pluggy


class Spec:
    @hookspec
    def get_auth_url(self, settings: AuthSettings, session):
        """Return the OAuth authorization URL for a CRM integration."""
        ...


def get_plugin_manager() -> pluggy.PluginManager:
    pm = pluggy.PluginManager("crmintegration")
    pm.add_hookspecs(Spec)
    pm.register(CapsulePlugin())
    return pm
