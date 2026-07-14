from typing import Dict, Type
from app.connectors.base_connector import BaseConnector

class ConnectorRegistry:
    _registry: Dict[str, Type[BaseConnector]] = {}

    @classmethod
    def register(cls, provider: str):
        """
        Decorator to register a connector class dynamically.
        """
        def decorator(subclass: Type[BaseConnector]):
            cls._registry[provider.lower()] = subclass
            return subclass
        return decorator

    @classmethod
    def get_connector_class(cls, provider: str) -> Type[BaseConnector]:
        """
        Retrieves the registered connector class for a provider name.
        """
        prov_key = provider.lower()
        if prov_key not in cls._registry:
            raise ValueError(f"Provider '{provider}' is not registered in ConnectorRegistry.")
        return cls._registry[prov_key]
