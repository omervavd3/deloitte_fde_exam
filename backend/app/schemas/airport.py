from pydantic import BaseModel


class Airport(BaseModel):
    iata: str
    name: str
    municipality: str | None = None
    iso_region: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    runway_count: int | None = None
    longest_runway_ft: int | None = None


class AirportResolution(BaseModel):
    """Result of turning user text into airport codes."""

    resolved: list[str]
    ambiguous: dict[str, list[str]] = {}
    unresolved: list[str] = []
