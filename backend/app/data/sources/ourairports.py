"""OurAirports reference data. Public domain, rebuilt nightly."""

import io

import httpx
import pandas as pd

BASE = "https://davidmegginson.github.io/ourairports-data/"
AIRPORTS_URL = BASE + "airports.csv"
RUNWAYS_URL = BASE + "runways.csv"

AIRPORT_COLS = ["ident", "type", "name", "municipality", "iso_region",
                "iata_code", "latitude_deg", "longitude_deg"]

# A field with one 10,000 ft runway and three 2,800 ft GA strips has one runway
# for scheduled service, not four. 5,000 ft is the usual planning floor for
# narrowbody operations - an assumption, not a certification standard.
AIR_CARRIER_RUNWAY_FT = 5000


async def _get_csv(url: str, timeout: float) -> pd.DataFrame:
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
    return pd.read_csv(io.StringIO(response.text), low_memory=False)


async def fetch_airports(timeout: float = 60.0) -> pd.DataFrame:
    """US airports with iata_code, iso_region, lat/lon."""
    df = await _get_csv(AIRPORTS_URL, timeout)
    df = df[(df["iso_country"] == "US") & df["iata_code"].notna()]
    df = df[AIRPORT_COLS].rename(columns={"iata_code": "iata"})
    return df.drop_duplicates(subset="iata", keep="first")


async def fetch_runways(
    timeout: float = 60.0, air_carrier_runway_ft: int = AIR_CARRIER_RUNWAY_FT
) -> pd.DataFrame:
    """Runway counts and longest length per airport ident.

    `air_carrier_runway_count` counts only runways long enough for scheduled jet
    service, so airfield loading divides by usable concrete rather than by every
    strip on the field.
    """
    df = await _get_csv(RUNWAYS_URL, timeout)
    df = df[df["closed"] != 1].copy()
    df["length_ft"] = pd.to_numeric(df["length_ft"], errors="coerce")
    df["_air_carrier"] = df["length_ft"] >= air_carrier_runway_ft
    return (
        df.groupby("airport_ident")
        .agg(
            runway_count=("id", "count"),
            air_carrier_runway_count=("_air_carrier", "sum"),
            longest_runway_ft=("length_ft", "max"),
        )
        .reset_index()
        .rename(columns={"airport_ident": "ident"})
    )
