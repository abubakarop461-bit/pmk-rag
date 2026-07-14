from app.connectors.connector_registry import ConnectorRegistry
from app.connectors.base_connector import BaseConnector

# Import all connector drivers so they register decorators dynamically
import app.connectors.google_drive_connector
import app.connectors.sharepoint_connector
import app.connectors.onedrive_connector

class ConnectorFactory:
    @staticmethod
    def get_connector(provider: str, access_token: str = None) -> BaseConnector:
        """
        Dynamic factory resolver. Instantiate registered connector classes.
        """
        connector_cls = ConnectorRegistry.get_connector_class(provider)
        # Instantiate with current access token
        return connector_cls(access_token=access_token)
