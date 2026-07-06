from app.destinations.connectors import google, meta_capi  # noqa: F401
from app.destinations.exceptions import (
    DestinationConfigError,
    DestinationError,
    DestinationRegistryError,
)
from app.destinations.protocol import DestinationConnector, DryRunResult
from app.destinations.registry import (
    GOOGLE_CUSTOMER_MATCH,
    GOOGLE_OFFLINE_CONVERSIONS,
    VALID_PLATFORMS,
    DestinationRegistry,
    catalog_api_entry,
    get_destination,
    get_destination_ids,
    get_destination_registry,
    get_routing_meta,
    is_supported_destination,
    is_v1_active,
    list_destinations,
    resolve_destination,
)
from app.destinations.spec import (
    Destination,
    DestinationField,
    OAuthSpec,
    PerStageSpec,
    RequiredMetadata,
)

DestinationCatalogEntry = Destination

__all__ = [
    "GOOGLE_CUSTOMER_MATCH",
    "GOOGLE_OFFLINE_CONVERSIONS",
    "VALID_PLATFORMS",
    "Destination",
    "DestinationCatalogEntry",
    "DestinationConfigError",
    "DestinationConnector",
    "DestinationError",
    "DestinationField",
    "DestinationRegistry",
    "DestinationRegistryError",
    "DryRunResult",
    "OAuthSpec",
    "PerStageSpec",
    "RequiredMetadata",
    "catalog_api_entry",
    "get_destination",
    "get_destination_ids",
    "get_destination_registry",
    "get_routing_meta",
    "is_supported_destination",
    "is_v1_active",
    "list_destinations",
    "resolve_destination",
]
