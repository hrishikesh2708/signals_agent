from app.destinations.register import register_destination
from app.destinations.spec import Destination


@register_destination("google_offline_conversions")
class GoogleOfflineConversionsConnector:
    def __init__(self, destination: Destination) -> None:
        self._destination = destination

    @property
    def id(self) -> str:
        return self._destination.id


@register_destination("google_customer_match")
class GoogleCustomerMatchConnector:
    def __init__(self, destination: Destination) -> None:
        self._destination = destination

    @property
    def id(self) -> str:
        return self._destination.id
