from typing import Dict, List, Union
from fastapi import Request
from addons.integration.crm_enum import CRMName
from config.settings import AppSettings
from addons.integration.hooks import hookspec
from addons.integration.plugins.capsule import CapsuleCRMPlugin
from addons.integration.plugins.zoho import ZohoCRMPlugin
import pluggy


class Spec:
    @hookspec
    def get_auth_url(crm_name: str, settings: AppSettings, session: dict):
        """Return the OAuth authorization URL for a CRM integration."""
        ...

    @hookspec
    def exchange_token(crm_name: str, code: str, settings: AppSettings) -> dict:
        """Exchange authorization code for access token."""
        ...

    @hookspec
    def refresh_access_token(
        crm_name: str, refresh_token: str, settings: AppSettings
    ) -> dict:
        """Refresh access token using refresh token."""
        ...

    @hookspec
    def get_contacts(
        crm_name: str, access_token: str, refresh_token: str, page: int = 1
    ) -> dict:
        """Fetch contacts from the CRM."""
        ...

    @hookspec
    def filter_contacts(contacts: Union[List, Dict]) -> List[Dict]:
     """Filter fetched contacts."""
    ...


def get_plugin_manager(crm_name: str = None) -> pluggy.PluginManager:
    pm = pluggy.PluginManager("crmintegration")
    pm.add_hookspecs(Spec)

    if crm_name is None:
        pm.register(CapsuleCRMPlugin(), name="CapsuleCRMPlugin")
        pm.register(ZohoCRMPlugin(), name="ZohoCRMPlugin")
    else:
        plugin = CRMName.get_plugin(crm_name)
        pm.register(plugin, name=f"{plugin.__class__.__name__}")
    return pm
