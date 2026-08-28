"""OurAirports reference data. Public domain, rebuilt nightly."""

import io

import httpx
import pandas as pd

BASE = "https://davidmegginson.github.io/ourairports-data/"
AIRPORTS_URL = BASE + "airports.csv"
RUNWAYS_URL = BASE + "runways.csv"

AIRPORT_COLS = ["ident", "type", "name", "municipality", "iso_region",
                "iata_code", "latitude_deg", "longitude_deg"]


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


async def fetch_runways(timeout: float = 60.0) -> pd.DataFrame:
    """Runway count and longest length per airport ident."""
    df = await _get_csv(RUNWAYS_URL, timeout)
    df = df[df["closed"] != 1]
    return (
        df.groupby("airport_ident")
        .agg(runway_count=("id", "count"), longest_runway_ft=("length_ft", "max"))
        .reset_index()
        .rename(columns={"airport_ident": "ident"})
    )
