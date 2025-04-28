from config.settings import AppSettings  # Changed from AuthSettings to AppSettings
from addons.integration.hooks import hookspec
from addons.integration.plugins.capsule import CapsuleCRMPlugin
from addons.integration.plugins.zoho import ZohoCRMPlugin
import pluggy


class Spec:
    @hookspec
    def get_auth_url(self, crm_name: str, settings: AppSettings, session: dict):
        """Return the OAuth authorization URL for a CRM integration."""
        ...


def get_plugin_manager() -> pluggy.PluginManager:
    pm = pluggy.PluginManager("crmintegration")
    pm.add_hookspecs(Spec)
    pm.register(CapsuleCRMPlugin())
    pm.register(ZohoCRMPlugin())
    return pm
