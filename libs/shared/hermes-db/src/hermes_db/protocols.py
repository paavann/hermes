from typing import Protocol


class EventExtractionData(Protocol):
    @property
    def headline(self) -> str: ...


    @property
    def summary(self) -> str: ...


    @property
    def category(self) -> str: ...


    @property
    def category_color(self) -> str | None: ...


    @property
    def location_name(self) -> str | None: ...


    @property
    def impact_level(self) -> str | None: ...


class GeocodingData(Protocol):
    @property
    def latitude(self) -> float: ...


    @property
    def longitude(self) -> float: ...
