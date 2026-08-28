"""BTS T-100 airport totals (CY2024) via the USDOT ArcGIS FeatureServer.

Keyless. Layer id is 1, not 0.
Fields: year, origin, enplanements, passengers, departures, arrivals, freight, mail
"""

import httpx
import pandas as pd

BASE_URL = (
    "https://services.arcgis.com/xOi1kZaI0eWDREZv/arcgis/rest/services/"
    "T100_Domestic_Market_and_Segment_Data/FeatureServer/1/query"
)
PAGE_SIZE = 1000

FIELDS = ["year", "origin", "enplanements", "passengers", "departures",
          "arrivals", "freight", "mail"]


async def fetch_all(timeout: float = 60.0) -> pd.DataFrame:
    """All ~1,279 airport rows, paged."""
    rows: list[dict] = []
    offset = 0

    async with httpx.AsyncClient(timeout=timeout) as client:
        while True:
            response = await client.get(BASE_URL, params={
                "where": "1=1",
                "outFields": ",".join(FIELDS),
                "returnGeometry": "false",
                "resultOffset": offset,
                "resultRecordCount": PAGE_SIZE,
                "f": "json",
            })
            response.raise_for_status()
            payload = response.json()

            if "error" in payload:
                raise RuntimeError(f"T-100 query failed: {payload['error']}")

            features = payload.get("features", [])
            if not features:
                break

            rows.extend(f["attributes"] for f in features)
            if len(features) < PAGE_SIZE:
                break
            offset += len(features)

    df = pd.DataFrame(rows)
    return df[df["origin"].notna()].rename(columns={"origin": "iata"})
