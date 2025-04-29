from enum import Enum

from addons.integration.plugins.capsule import CapsuleCRMPlugin
from addons.integration.plugins.zoho import ZohoCRMPlugin

class CRMName(str, Enum):
    ZOHO = "zoho"
    CAPSULE = "capsule"
    
    @classmethod
    def get_plugin(cls, crm_name: str):
        crm_name = crm_name.lower()
        if crm_name == cls.ZOHO:
            return ZohoCRMPlugin()
        elif crm_name == cls.CAPSULE:
            return CapsuleCRMPlugin()
        raise ValueError(f"Unsupported CRM: {crm_name}")