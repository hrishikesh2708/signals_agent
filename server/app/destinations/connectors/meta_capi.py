from app.destinations.register import register_destination
from app.destinations.spec import Destination


@register_destination("meta_capi")
class MetaCapiConnector:
    def __init__(self, destination: Destination) -> None:
        self._destination = destination

    @property
    def id(self) -> str:
        return self._destination.id
