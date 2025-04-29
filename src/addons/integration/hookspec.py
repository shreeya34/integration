from typing import List, Dict, Any
import pluggy
from addons.integration.crm_enum import CRMName
from config.settings import AppSettings

hookspec = pluggy.HookspecMarker("crmintegration")

class CRMIntegrationSpecs:
    """Hook specifications for CRM plugins."""
    
    @hookspec
    def get_auth_url(self) -> str:
        """Get OAuth authorization URL."""
        pass
    
    @hookspec
    def exchange_token(self, code: str, state: str = None) -> dict:
        """Exchange code for tokens."""
        pass
    
    @hookspec
    def refresh_access_token(self, refresh_token: str) -> dict:
        """Refresh access token."""
        pass
    
    @hookspec
    def get_contacts(self, access_token: str, refresh_token: str, page: int = 1) -> dict:
        """Fetch contacts from CRM."""
        pass


def get_plugin_manager(active_crms: List[str] = None):
    settings = AppSettings()  

    if active_crms is None:
        active_crms = settings.active_crms 

    pm = pluggy.PluginManager("crmintegration")
    pm.add_hookspecs(CRMIntegrationSpecs)

    for plugin in CRMName.get_active_plugins(active_crms):
        pm.register(plugin)

    return pm


def subset_hook_caller(pm, hook_name: str, crm_names: List[str]) -> Dict[str, Any]:
    """
    Create a subset hook caller for specific CRMs.
    
    Args:
        pm: Plugin manager instance
        hook_name: Name of the hook to call
        crm_names: List of CRM names to include
    
    Returns:
        Dictionary mapping CRM names to hook results
    """
    results = {}
    
    for crm_name in crm_names:
        try:
            plugin = CRMName.get_plugin(crm_name)
            result = getattr(plugin, hook_name)()
            results[crm_name] = result
        except Exception as e:
            results[crm_name] = {"error": str(e)}
    
    return results