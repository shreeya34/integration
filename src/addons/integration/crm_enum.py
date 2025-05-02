from enum import Enum
from typing import Type, Any, Dict
from addons.integration.plugins.zoho import ZohoCRMPlugin
from addons.integration.plugins.capsule import CapsuleCRMPlugin


class CRMName(str, Enum):
    ZOHO = "zoho"
    CAPSULE = "capsule"

    @classmethod
    def get_plugin(cls, crm_name: str) -> Any:
        crm_name = crm_name.lower()
        plugin_classes = {
            cls.ZOHO: ZohoCRMPlugin,
            cls.CAPSULE: CapsuleCRMPlugin,
        }
        try:
            crm_enum = cls(crm_name)
            return plugin_classes[crm_enum]()
        except ValueError:
            supported_crms = [e.value for e in cls]
            raise ValueError(
                f"Unsupported CRM: {crm_name}. Supported CRMs: {', '.join(supported_crms)}"
            )
