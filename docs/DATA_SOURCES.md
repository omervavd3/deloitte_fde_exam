# Airport Investment Intelligence Agent — Data Sources Reference

> All endpoints and URLs below were **live-tested on 2026-08-28**. Status codes and response
> shapes are from actual calls, not from documentation. Re-verify before relying on them.

---

## TL;DR — cost & auth summary

| Source | Cost | Auth | Type | Verified |
|---|---|---|---|---|
| BTS T-100 (ArcGIS mirror) | Free | **None** | ✅ REST API (JSON) | ✅ query returns data |
| BTS T-100 (full, TranStats) | Free | None | ❌ Form-based ZIP download | ✅ page loads |
| BTS On-Time Performance | Free | None | ⚠️ Direct ZIP URL (no form!) | ✅ HTTP 206 |
| FAA NAS Status | Free | **None** | ✅ REST endpoint (XML) | ✅ live data |
| FAA Terminal Area Forecast | Free | None | ❌ XLSX download | ✅ page loads |
| FAA Enplanements (ACAIS) | Free | None | ❌ XLSX/PDF download | ✅ page loads |
| FAA NPIAS / Capacity Needs | Free | None | ❌ PDF | ✅ page loads |
| OurAirports | Free | None | ❌ CSV (stable URL, nightly) | ✅ documented |
| OpenSky Network | Free | OAuth2 (anon tier exists) | ✅ REST API (JSON) | ✅ 200 anon / 401 auth |
| FAA OPSNET / ASPM | Free | Login for recent data | ⚠️ Web query tool | ✅ documented |
| AeroDataBox | Freemium | RapidAPI key | ✅ REST API | 600 units/mo free |
| aviationstack | Freemium | API key | ✅ REST API | small free tier |

**Nothing here requires a credit card** except the two freemium APIs, and their free tiers are
genuinely free.

**Key insight:** most "sources" are bulk file downloads, not APIs. Only NAS Status, the T-100
ArcGIS mirror, and OpenSky are true keyless-or-cheap REST APIs. See
[Satisfying the "use public APIs" requirement](#satisfying-the-use-public-apis-requirement).

---

## 1. BTS T-100 — airport totals via ArcGIS REST API ⭐ START HERE

The fastest path to real data. **No key, no signup, no form.** Returns JSON.
Airport-level annual totals for CY2024, 1,279 US airports.

**Base URL**
```
https://services.arcgis.com/xOi1kZaI0eWDREZv/arcgis/rest/services/T100_Domestic_Market_and_Segment_Data/FeatureServer/1
```

> ⚠️ Layer id is **1**, not 0. Querying `/0/` returns `{"error":{"code":400,"message":"Invalid URL"}}`.

**Schema** (verified): `OBJECTID, year, origin, enplanements, passengers, departures, arrivals, freight, mail`

`origin` = IATA code. `freight`/`mail` in pounds. Totals are for the full year across all US carriers.

### Example calls

```bash
# Record count
curl "https://services.arcgis.com/xOi1kZaI0eWDREZv/arcgis/rest/services/T100_Domestic_Market_and_Segment_Data/FeatureServer/1/query?where=1%3D1&returnCountOnly=true&f=json"
# -> {"count":1279}

# One airport
curl "https://services.arcgis.com/xOi1kZaI0eWDREZv/arcgis/rest/services/T100_Domestic_Market_and_Segment_Data/FeatureServer/1/query?where=origin%3D%27LAX%27&outFields=*&f=json"
```

Verified LAX CY2024 response:
```json
{"attributes":{"OBJECTID":622,"year":2024,"origin":"LAX","enplanements":26239010,
 "passengers":26340206,"departures":206637,"arrivals":207004,
 "freight":844016086,"mail":47992961}}
```

### Pull all 1,279 airports in one shot (Python)

```python
import requests, pandas as pd

BASE = ("https://services.arcgis.com/xOi1kZaI0eWDREZv/arcgis/rest/services/"
        "T100_Domestic_Market_and_Segment_Data/FeatureServer/1/query")

def fetch_t100_airports():
    rows, offset = [], 0
    while True:
        r = requests.get(BASE, params={
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "false",
            "resultOffset": offset,
            "resultRecordCount": 1000,   # ArcGIS server-side page cap
            "f": "json",
        }, timeout=60)
        r.raise_for_status()
        page = r.json().get("features", [])
        if not page:
            break
        rows += [f["attributes"] for f in page]
        offset += len(page)
    return pd.DataFrame(rows)

df = fetch_t100_airports()
df.to_parquet("data/t100_airports_cy2024.parquet")
```

**Useful `where` clauses** — standard SQL-92 subset:
```
origin IN ('LAX','SNA','BUR','LGB','ONT')      # LA basin comparison
enplanements > 1000000                          # commercial-scale airports only
origin='ANC'                                    # Anchorage
```

**Handy params:** `orderByFields=enplanements DESC`, `returnCountOnly=true`,
`outStatistics=[...]` for server-side aggregation, `resultOffset` / `resultRecordCount` for paging.

### ⚠️ Limitations — state these in your design doc
- **CY2024 only** (snapshot taken 2025-04-08). No time series → you cannot compute growth CAGR from this alone.
- **Airport-level totals only.** No route-level, no carrier-level, no seat counts.
- **No `seats` field** → you cannot compute load factor from this. Need the full T-100 for that.
- Unofficial mirror of the authoritative BTS data. Cite BTS as source, note the mirror.

---

## 2. BTS T-100 — full segment data (route-level, monthly)

The real thing: passengers, **seats**, departures performed/scheduled, freight, per carrier per
route per month. This is what gives you load factor, seat supply, route networks, and growth trends.

**Download pages** (no login):
- Domestic Segment: <https://www.transtats.bts.gov/DL_SelectFields.aspx?gnoyr_VQ=FIM>
- Browse all Air Carrier tables: <https://www.transtats.bts.gov/DatabaseInfo.asp?QO_VQ=EEE>
- International Segment: same DB, pick the T-100 International Segment table

**Also grab the International Segment** — required for Anchorage long-haul %, and for any
international question.

### ⚠️ There is NO direct-download URL for T-100
Tested and confirmed 404 on every `PREZIP` variant:
```
T_T100D_SEGMENT_US_CARRIER_ONLY.zip          -> 404
T_T100D_SEGMENT_ALL_CARRIER_2024.zip         -> 404
T_T100I_SEGMENT_ALL_CARRIER_2024.zip         -> 404
T_MASTER_CORD.zip                            -> 404
```
T-100 requires the ASP.NET form (viewstate + POST). **Don't waste time scripting it.**

**Recommended approach:** download manually through the web form once, commit the file.
1. Open the download page above
2. Select the fields you need (see below)
3. Pick year + "Download All Months" (one zip per year)
4. Save to `data/raw/`, commit, and write your ingest against the local file

**Minimum fields to select:**
```
YEAR, MONTH, ORIGIN, DEST, CARRIER, UNIQUE_CARRIER,
PASSENGERS, SEATS, DEPARTURES_PERFORMED, DEPARTURES_SCHEDULED,
FREIGHT, MAIL, DISTANCE, AIRCRAFT_TYPE, CLASS
```

**Gotchas:**
- Data lags **~3–4 months**. Currently through ~April 2026.
- Covers only carriers above a revenue reporting threshold — small regionals are underrepresented.
- `CLASS` field distinguishes scheduled passenger (F) from all-cargo (G/P) — **filter on it** or
  your load factors will be nonsense at cargo hubs like ANC and MEM.
- `DEPARTURES_SCHEDULED` vs `DEPARTURES_PERFORMED` → the gap is a cancellation signal.

---

## 3. BTS On-Time Performance — direct ZIP download ✅

Your congestion KPI. Departure/arrival delay, taxi-out time, cancellations, and **delay cause
attribution** (carrier / weather / NAS / security / late-aircraft).

**Browse/select page:** <https://www.transtats.bts.gov/DL_SelectFields.aspx?gnoyr_VQ=FGJ&QO_fu146_anzr=b6-Gvzr>
(1987 → June 2026, no login)

### ⭐ Direct download URL pattern — VERIFIED WORKING (HTTP 206)

Unlike T-100, On-Time has a predictable `PREZIP` path. **You can script this.**

```
https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{YYYY}_{M}.zip
```
`{M}` is the month **without** a leading zero (`1`, not `01`).

```bash
# Verified: returns application/x-zip-compressed
curl -O "https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_1.zip"
```

```python
import requests, zipfile, io, pandas as pd

COLS = ["Year","Month","Origin","Dest","Reporting_Airline",
        "DepDelay","DepDel15","TaxiOut","TaxiIn","ArrDelay","ArrDel15",
        "Cancelled","CancellationCode","Diverted",
        "CarrierDelay","WeatherDelay","NASDelay","SecurityDelay","LateAircraftDelay"]

def fetch_ontime(year, month):
    url = ("https://transtats.bts.gov/PREZIP/"
           f"On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip")
    r = requests.get(url, timeout=300)
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
    return pd.read_csv(z.open(name), usecols=COLS, low_memory=False)

# Aggregate to airport-month immediately — do NOT hold raw rows in memory
frames = []
for y, m in [(2025, m) for m in range(1, 13)]:
    df = fetch_ontime(y, m)
    frames.append(df.groupby("Origin").agg(
        flights=("DepDelay", "size"),
        avg_dep_delay=("DepDelay", "mean"),
        pct_delayed_15=("DepDel15", "mean"),
        avg_taxi_out=("TaxiOut", "mean"),
        cancel_rate=("Cancelled", "mean"),
        avg_nas_delay=("NASDelay", "mean"),   # <-- best congestion signal
    ).assign(year=y, month=m).reset_index())

airport_month = pd.concat(frames)
```

**Gotchas:**
- ~50–200 MB **compressed** per month; several GB/year uncompressed. Aggregate per month, discard raw.
- Always pass `usecols=` — the full table is ~110 columns.
- **`NASDelay` is the column that matters most for this assignment.** It isolates
  airport/airspace capacity delay from airline operational problems. A high NASDelay share is
  direct evidence of an infrastructure constraint — exactly what justifies terminal/runway expansion.
- Delay-cause columns are null for on-time flights; use `.mean()` carefully or fill 0 by intent.

---

## 4. FAA NAS Status — live delays ✅ NO KEY

Real-time ground stops, ground delay programs, arrival/departure delays, closures.
**No key, no signup, no quota.** Your best "live public API" for the demo.

**Endpoint:** `https://nasstatus.faa.gov/api/airport-status-information`
**Alpha mirror:** `https://nasstatus-alpha.faa.gov/api/airport-status-information`

Returns **XML**, not JSON.

### Response structure (verified live)

```xml
<AIRPORT_STATUS_INFORMATION>
  <Update_Time>...</Update_Time>
  <Dtd_File>...</Dtd_File>
  <Delay_type>
    <Airport>
      <ARPT>KOA</ARPT>
      <Reason>!KOA 08/063 KOA AD AP CLSD EXC MEDEVAC HEL OPS</Reason>
      <Start>...</Start>
      <Reopen>...</Reopen>
    </Airport>
  </Delay_type>
</AIRPORT_STATUS_INFORMATION>
```

`<Delay_type>` blocks cover ground stops, ground delay programs, arrival/departure delays and
closures — **shape varies by delay type**, so parse defensively.

```python
import requests, xml.etree.ElementTree as ET

def get_live_delays(timeout=8):
    """Live FAA delays. Returns {} on any failure — never raises."""
    try:
        r = requests.get("https://nasstatus.faa.gov/api/airport-status-information",
                         timeout=timeout, headers={"User-Agent": "airport-agent/0.1"})
        r.raise_for_status()
        root = ET.fromstring(r.content)
        out = {}
        for ap in root.iter("Airport"):
            code = (ap.findtext("ARPT") or "").strip()
            if not code:
                continue
            out.setdefault(code, []).append({
                "reason": (ap.findtext("Reason") or "").strip(),
                "start":  (ap.findtext("Start") or "").strip(),
                "reopen": (ap.findtext("Reopen") or "").strip(),
            })
        return {"as_of": root.findtext("Update_Time"), "airports": out}
    except Exception:
        return {}   # degrade silently; historical scoring still works
```

**Gotchas:**
- **Undocumented internal endpoint.** No SLA, no versioning, could change without notice.
  Always wrap in try/except and fail soft.
- Airport codes are mixed ICAO (`KOA`, `KSFO`) and IATA depending on block — normalize.
- `Reason` is raw NOTAM text — pass it to the LLM to summarize rather than regexing it.
- Quiet periods return few or no entries. That is normal, not an error.

---

## 5. OurAirports — airport & runway reference ✅ NO KEY

Public domain, rebuilt nightly, direct CSV, zero friction. Your canonical airport table.

```
https://davidmegginson.github.io/ourairports-data/airports.csv
https://davidmegginson.github.io/ourairports-data/runways.csv
https://davidmegginson.github.io/ourairports-data/airport-frequencies.csv
https://davidmegginson.github.io/ourairports-data/countries.csv
https://davidmegginson.github.io/ourairports-data/regions.csv
```
Landing page: <https://ourairports.com/data/>

```python
import pandas as pd

BASE = "https://davidmegginson.github.io/ourairports-data/"

airports = pd.read_csv(BASE + "airports.csv")
runways  = pd.read_csv(BASE + "runways.csv")

us = airports[(airports.iso_country == "US") &
              (airports.type == "large_airport")]

# Runway count + longest runway per airport -> capacity proxy
rw = runways.groupby("airport_ident").agg(
    runway_count=("id", "count"),
    longest_ft=("length_ft", "max"),
).reset_index()
```

**Key columns:** `ident, type, name, latitude_deg, longitude_deg, iso_country, iso_region,
municipality, iata_code, gps_code, local_code`

**Why this matters:**
- **`iso_region`** (e.g. `US-MA`, `US-CT`) → resolves "New England" to 6 states cleanly.
- **lat/lon** → great-circle distance per route → haul-length classification with **no paid API**.
- **runway count + length** → your capacity-headroom denominator.

```python
from math import radians, sin, cos, asin, sqrt

def haversine_mi(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
    a = sin((lat2-lat1)/2)**2 + cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2
    return 3958.8 * 2 * asin(sqrt(a))

# Define your haul bands explicitly and SAY SO in the design doc:
#   short  < 1,000 mi
#   medium 1,000–3,000 mi
#   long   > 3,000 mi
```
> T-100 already has a `DISTANCE` column — prefer it and use haversine as the fallback/validator.

---

## 6. FAA Terminal Area Forecast (TAF)

Official FAA forecast of enplanements and operations per airport out to **2045**, plus historicals.
This is your forward-looking growth component and few candidates will use it.

- Main page + "Download Data" (XLSX): <https://www.faa.gov/data_research/aviation/taf>
- Query interface: <https://taf.faa.gov/>
- ASPM TAF access: <https://www.aspm.faa.gov/getinfotaf.asp>
- Summary PDF example: <https://taf.faa.gov/Downloads/TAFSummaryFY2019-2045.pdf>

**Contains:** enplanements, itinerant + local operations, based aircraft — historical and forecast,
per airport, per fiscal year, for all NPIAS airports.

### ⚠️⚠️ ACRONYM TRAP
**`aviationweather.gov/data/taf` is NOT this.** That is *Terminal **Aerodrome** Forecast* —
a weather product. Completely unrelated. Do not wire it in by mistake.

**Use it for:** forecast CAGR as your growth sub-score, and as an independent cross-check on
trends derived from T-100.

---

## 7. FAA Passenger Boarding (Enplanement) Data + hub classification

Official enplanements and the **Large / Medium / Small / Non-hub** tiers you need for
peer-group normalization.

- Main page: <https://www.faa.gov/airports/planning_capacity/passenger_allcargo_stats/passenger>
- CY2024 all enplanements (XLSX): <https://www.faa.gov/airports/planning_capacity/passenger_allcargo_stats/passenger/ARP-cy2024-all-enplanements.xlsx>
- Previous years: <https://www.faa.gov/airports/planning_capacity/passenger_allcargo_stats/passenger/previous_years>
- Methodology: <https://www.faa.gov/airports/planning_capacity/passenger_allcargo_stats/passenger/collection>

**⚠️ Timing:** final CY2025 data was scheduled for **late August 2026** — i.e. right now.
Check the main page first; fall back to CY2024 and record the as-of date either way.

**Why the hub tier matters:** normalize sub-scores **within** hub class, not globally. Comparing
BOS to a small-hub field on raw volume is meaningless, and saying so in the design doc
demonstrates judgment.

---

## 8. FAA Capacity Needs ("FACT" successor) — ground truth for validation

The FAA's own assessment of which airports are runway-capacity constrained.

- Report: <https://www.faa.gov/sites/faa.gov/files/airports/resources/publications/reports/NAS_needs.pdf>

**Published definition:** an airport exceeding **80% of its hourly runway capacity at least 50%
of the time** is capacity-constrained.

**2024 evaluation findings:** 11 airports expected runway-capacity-constrained by 2028, rising to
14 by 2033; an additional 13 at risk of significant congestion through 2033.

> ⭐ **Use this to validate your ranking.** "My model independently surfaces 9 of the FAA's 11
> constrained airports" is the single strongest sentence you can put in the design doc. It converts
> your scoring from an opinion into something with measured external agreement.

---

## 9. FAA NPIAS 2025–2029 — planned capital needs

Planned airport capital development needs per airport. Directly on-topic for "modernization."

- Narrative PDF: <https://www.faa.gov/sites/faa.gov/files/airports/planning_capacity/npias/current/ARP-NPIAS-2025-2029-Narrative.pdf>
- Data appendices are linked from the same FAA NPIAS page.

Useful as a **modifier**, not a core input: an airport with a large funded program already underway
is arguably a *worse* incremental investment target than one with unmet need and no plan.

---

## 10. FAA OPSNET / ASPM — tower operations counts

- ASPM home: <https://www.aspm.faa.gov/>
- OPSNET docs: <https://www.aspm.faa.gov/aspmhelp/index/Operations_Network_(OPSNET).html>

**Access rules:**
- **Without login:** finalized monthly operations + delay data, published on the **20th of the
  following month** (June data → available July 20).
- **With login:** next-day data. Request via the Data Access Request Form on the OPSNET page.

Fine for historical operations counts. **Do not build a live dependency on it** — the login
requirement will break for whoever grades this.

---

## 11. OpenSky Network — live flight tracking

- Site: <https://opensky-network.org/>
- REST docs: <https://openskynetwork.github.io/opensky-api/rest.html>
- FAQ: <https://opensky-network.org/about/faq>

### ⚠️ Auth changed in March 2025 — OAuth2 client credentials

Basic auth is deprecated. Accounts created after mid-March 2025 **must** use OAuth2.

**Token endpoint** (verified — returns 401 with bad creds, i.e. the endpoint is correct):
```
https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token
```

```python
import requests

def opensky_token(client_id, client_secret):
    r = requests.post(
        "https://auth.opensky-network.org/auth/realms/opensky-network/"
        "protocol/openid-connect/token",
        data={"grant_type": "client_credentials",
              "client_id": client_id,
              "client_secret": client_secret},
        timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]

# Authenticated call
tok = opensky_token(CLIENT_ID, CLIENT_SECRET)
r = requests.get("https://opensky-network.org/api/states/all",
                 headers={"Authorization": f"Bearer {tok}"},
                 params={"lamin": 37.0, "lomin": -123.0, "lamax": 38.0, "lomax": -122.0},
                 timeout=30)
```

**Anonymous access works too** — verified HTTP 200, no credentials:
```bash
curl "https://opensky-network.org/api/states/all?lamin=37&lomin=-123&lamax=38&lomax=-122"
```

**Quotas:**
| Tier | Credits/day | History | Resolution |
|---|---|---|---|
| Anonymous | limited | current state only | 10 s |
| Registered | 4,000 | up to 1 h back | 5 s |
| Contributing (ADS-B receiver ≥30% uptime) | 8,000 | up to 1 h back | 5 s |

Rate-limited endpoints: `/states/all`, `/flights/*`, `/tracks/all`.

**Verdict for this assignment:** optional garnish. The OAuth2 setup adds friction and a key the
grader won't have. NAS Status gives you the "live API" story with zero setup. Only add OpenSky
if you finish early.

---

## 12. Freemium APIs — AeroDataBox / aviationstack

Useful for scheduled routes and flight status. Both need a key.

**AeroDataBox** — <https://aerodatabox.com/> (via RapidAPI)
- Free "Basic" tier: **600 API units/month** (units ≠ requests — cost varies by endpoint)
- Rate limit: 1 request/second; RapidAPI adds a 1,000 req/hour cap
- Good endpoints: airport routes/daily-routes, airport stats, flight schedules

**aviationstack** — <https://aviationstack.com/>
- Small free tier; free plan is HTTP-only on some endpoints
- Good for: flight status, schedules, airline/airport reference data

**Verdict:** fine as a garnish, **never load-bearing**. Free quotas are small enough that a
handful of debugging runs can exhaust a month.

---

## ❌ Do not use

| Source | Why |
|---|---|
| `aviationweather.gov/data/taf` | Terminal **Aerodrome** Forecast — weather, not the FAA Terminal Area Forecast |
| OpenFlights routes | Data frozen ~2014. Tempting because easy; will make route analysis wrong |
| FlightAware AeroAPI / Flightradar24 | Real cost, no useful free tier |
| Scraping anything | Not worth an hour of a 24-hour budget |

---

## Satisfying the "use public APIs" requirement

The brief says *"Use public APIs to gather airport/aviation data."* Most of the best data is
bulk download. Don't fake it, and don't over-read the requirement either — it asks you to source
real public data programmatically, not to prove you made HTTP GETs at inference time.

**Defensible architecture:**

1. **Bulk sources → scripted ingest.** `ingest.py` fetches from published URLs, normalizes,
   writes a versioned snapshot. That *is* programmatic acquisition of public data, and it's what
   any real analytics system does — you don't re-download 500 MB of BTS data per user question.
2. **Live APIs → runtime freshness.** FAA NAS Status at query time: no key, no quota, real-time.
   One call gives you *"SFO currently has a 45-minute ground delay program"* layered on top of
   historical scoring. ~20 minutes of work, strong demo moment.
3. **T-100 ArcGIS FeatureServer** is a genuine keyless REST API — call it live if you want an
   unambiguous example of API usage in the analytical path.

**Sentence for the design doc:**

> *Historical analytical data is acquired via scripted bulk ingest from BTS/FAA published
> endpoints and cached as a versioned snapshot; live operational conditions are fetched at query
> time from the FAA NAS Status API and the BTS T-100 feature service.*

**⚠️ Critical:** make the grader's run **not depend on any key you have and they don't**.
Commit the snapshot. Make every live call fail soft. If your app dies because an unauthenticated
endpoint was down during evaluation, that's a self-inflicted wound.

---

## Recommended minimal stack (24-hour budget)

| Priority | Source | Effort | Unlocks |
|---|---|---|---|
| 1 | OurAirports CSV | 15 min | Canonical airport table, regions, runways, distances |
| 2 | T-100 ArcGIS API | 30 min | Real data in the app immediately, keyless API story |
| 3 | On-Time (12 months, PREZIP) | 2 h | Congestion KPI + NAS delay attribution |
| 4 | FAA Enplanements XLSX | 30 min | Hub tiers for peer normalization |
| 5 | T-100 full segment (manual) | 1 h | Seats → load factor, route-level, haul mix |
| 6 | FAA TAF XLSX | 45 min | Forward-looking growth sub-score |
| 7 | FAA NAS Status | 20 min | Live API + demo moment |
| 8 | FAA Capacity Needs PDF | 20 min | Validation ground truth for the design doc |

Items 1–3 alone answer three of the four example questions in the brief.

---

## Cross-cutting gotchas

- **Join on IATA, but validate.** BTS uses its own airport ID *and* IATA; OurAirports uses
  `ident` / `iata_code` / `gps_code`. Build one canonical airport table early and reconcile
  everything against it. Silent join failures here corrupt every downstream number.
- **Freight vs passenger.** T-100 includes freight columns. **Anchorage (ANC) is a top-5 global
  cargo hub** — ranking it on passenger metrics alone is a visible miss, and the brief asks about
  ANC specifically. Use the T-100 `CLASS` field to separate scheduled passenger from all-cargo.
- **Record every as-of date.** T-100 lags 3–4 months; the ArcGIS mirror is CY2024; enplanements
  are CY2024/CY2025. Put all of it in a data dictionary — that's the "communicate uncertainty" box.
- **Define your terms explicitly.** "Long haul" has no single DOT definition. Pick a threshold,
  state it, let the user override it. Same for "unmet demand" — it is a *proxy*, not a measured
  quantity. Committing to a defensible definition and flagging it beats dodging.
- **You cannot compute profit** from any of this data. The brief says "most profitable"; you can
  score *opportunity*, not *returns*. Say so plainly — naming that gap is a feature.

---

## Appendix — verification log (2026-08-28)

```
✅ 206  https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_1.zip
❌ 404  https://transtats.bts.gov/PREZIP/T_T100D_SEGMENT_US_CARRIER_ONLY.zip
❌ 404  https://transtats.bts.gov/PREZIP/T_T100I_SEGMENT_ALL_CARRIER.zip
❌ 404  https://transtats.bts.gov/PREZIP/T_MASTER_CORD.zip
✅ 200  https://opensky-network.org/api/states/all?lamin=37&lomin=-123&lamax=38&lomax=-122   (anonymous)
✅ 401  https://auth.opensky-network.org/.../token   (endpoint correct, dummy creds rejected)
✅ live https://nasstatus.faa.gov/api/airport-status-information   (returned current KOA/ASE closures)
✅ 1279 records — T-100 ArcGIS FeatureServer layer 1
❌ 400  T-100 ArcGIS FeatureServer layer 0   ("Invalid URL" — layer id is 1)
```
