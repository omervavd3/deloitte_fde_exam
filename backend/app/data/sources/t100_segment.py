"""BTS T-100 Segment (All Carriers) - per-route traffic, aggregated per origin.

This one is a manual download, not a fetch. TranStats serves it from an ASP.NET
form (__VIEWSTATE / __EVENTVALIDATION), so there is no stable URL to call:

    https://transtats.bts.gov/DL_SelectFields.aspx?gnoyr_VQ=FMG
    Geography: All  |  Year: <year>  |  Period: All months

Tick at least these columns, then drop the file in `backend/data/raw/`:

    ORIGIN  DEST  DEST_COUNTRY  DISTANCE
    DEPARTURES_SCHEDULED  DEPARTURES_PERFORMED  SEATS  PASSENGERS

Everything here is additive: without the file the loader returns None and no
score changes. "All Carriers" includes foreign carriers, so unlike the ArcGIS
feed this covers international service.
"""

import logging
import zipfile
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"

# Statute miles above which a segment counts as long haul. An assumption, not a
# standard: ~2,500 sm is the usual proxy for the 6-hour definition.
LONG_HAUL_MILES = 2500

REQUIRED = [
    "ORIGIN",
    "DISTANCE",
    "DEPARTURES_PERFORMED",
]
OPTIONAL = [
    "DEST",
    "DEST_COUNTRY",
    "DEPARTURES_SCHEDULED",
    "SEATS",
    "PASSENGERS",
]


def _data_member(z: zipfile.ZipFile) -> str:
    """The data CSV, not the Documentation.csv TranStats ships beside it.

    The doc file sorts first, so pick by size instead of by order.
    """
    members = [
        i
        for i in z.infolist()
        if i.filename.lower().endswith(".csv")
        and "documentation" not in i.filename.lower()
        and "readme" not in i.filename.lower()
    ]
    if not members:
        members = [i for i in z.infolist() if i.filename.lower().endswith(".csv")]
    return max(members, key=lambda i: i.file_size).filename


def _read_any(path: Path) -> pd.DataFrame:
    """A T-100 extract, whether TranStats zipped it or not."""
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as z:
            with z.open(_data_member(z)) as f:
                return pd.read_csv(f, low_memory=False, encoding="latin-1")
    return pd.read_csv(path, low_memory=False, encoding="latin-1")


def find_extract(raw_dir: Path | None = None) -> Path | None:
    """Newest T-100 segment file in the raw directory, or None."""
    directory = raw_dir or RAW_DIR
    if not directory.is_dir():
        return None
    files = [
        p
        for p in directory.iterdir()
        if p.suffix.lower() in {".csv", ".zip"} and "t100" in p.name.lower().replace("_", "")
        or p.suffix.lower() in {".csv", ".zip"} and "segment" in p.name.lower()
    ]
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def load(
    path: Path | None = None, long_haul_miles: int = LONG_HAUL_MILES
) -> pd.DataFrame | None:
    """Per-origin-airport aggregates, indexed by IATA. None when unavailable.

    Distances are per-segment, so every average is weighted by departures
    performed - a single weekly widebody must not outweigh daily regional
    flying.
    """
    source = path or find_extract()
    if source is None:
        log.info("no T-100 segment extract in %s; skipping segment metrics", RAW_DIR)
        return None

    try:
        df = _read_any(source)
    except Exception as exc:
        log.warning("could not read T-100 segment extract %s: %s", source, exc)
        return None

    df.columns = [c.strip().upper() for c in df.columns]
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        log.warning(
            "T-100 extract %s is missing required columns %s; skipping", source.name, missing
        )
        return None

    for column in REQUIRED + OPTIONAL:
        if column in df.columns and column not in {"ORIGIN", "DEST", "DEST_COUNTRY"}:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df[df["DEPARTURES_PERFORMED"].fillna(0) > 0].copy()
    if df.empty:
        log.warning("T-100 extract %s has no performed departures; skipping", source.name)
        return None

    flown = df["DEPARTURES_PERFORMED"]
    df["_seg_miles"] = flown * df["DISTANCE"]
    df["_long_haul"] = flown.where(df["DISTANCE"] >= long_haul_miles, 0.0)
    if "DEST_COUNTRY" in df.columns:
        df["_intl"] = flown.where(df["DEST_COUNTRY"].astype(str).str.upper() != "US", 0.0)

    grouped = df.groupby("ORIGIN")
    out = pd.DataFrame(index=grouped.size().index)
    out.index.name = "iata"

    total_flown = grouped["DEPARTURES_PERFORMED"].sum()
    out["segment_departures"] = total_flown
    out["avg_stage_length_sm"] = grouped["_seg_miles"].sum() / total_flown
    out["long_haul_share"] = grouped["_long_haul"].sum() / total_flown

    if "_intl" in df.columns:
        out["international_share"] = grouped["_intl"].sum() / total_flown
    if "DEST" in df.columns:
        out["destinations_served"] = grouped["DEST"].nunique()
    if "SEATS" in df.columns and "PASSENGERS" in df.columns:
        seats = grouped["SEATS"].sum()
        out["seats"] = seats
        out["load_factor"] = (grouped["PASSENGERS"].sum() / seats).where(seats > 0)
    if "DEPARTURES_SCHEDULED" in df.columns:
        # Only segments that HAD scheduled service: charter and freight-only
        # flying reports performed departures against zero scheduled, which
        # pushed ANC's naive performed/scheduled ratio to 159%.
        booked = df[df["DEPARTURES_SCHEDULED"].fillna(0) > 0].groupby("ORIGIN")
        scheduled = booked["DEPARTURES_SCHEDULED"].sum().reindex(out.index)
        flown_on_schedule = booked["DEPARTURES_PERFORMED"].sum().reindex(out.index)
        out["scheduled_departures"] = scheduled
        out["completion_rate"] = (flown_on_schedule / scheduled).where(scheduled > 0)

    log.info(
        "loaded T-100 segment metrics for %d airports from %s", len(out), source.name
    )
    return out
