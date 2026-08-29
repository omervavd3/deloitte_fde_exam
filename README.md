# Airport Investment Intelligence Agent

A conversational agent that ranks and compares US airports as infrastructure
investment opportunities, using public aviation data.

Ask *"Which airports in New England are strong candidates for terminal
expansion?"* and it resolves the region, picks a weighting thesis, scores every
airport nationally, and explains what drove the result — showing the ranking,
the per-metric breakdown, the decisions it made, and the caveats on reading it.

## How it works

A LangGraph agent of eight nodes. **Only two of them call an LLM:**

- `parse_intent` — question → intent, entity strings, weight profile. No numbers.
- `narrate` — explains results it may only restate, never compute.

Everything between them is deterministic. Entity resolution, clarification,
scoring, and every caveat are ordinary Python, so the numbers a user sees never
originate from a model.

```
                      ┌──────────────┐
                      ▼              │ answers in hand
parse_intent → resolve_entities → clarify ──────────────────┐ asks a question
                      │                                     │
                      ├→ load_facts ────────────────────────┤ direct question
                      ├→ load_metrics → score → enrich_live ┤ ranking
                      └─────────────────────────────────────┤ small talk / out of scope
                                                            ▼
                                                         narrate → END
```

`clarify` loops back to `resolve_entities` once its queue is empty; terms already
answered are not re-resolved, which is what closes the cycle. The rendered
diagram is written to `backend/app/agent/graph.png` on startup.

**Weight profiles** are investment theses (Terminal Expansion, Cargo Facility,
Air Mail Hub…) stored in Postgres and editable from the dashboard. The agent
picks one by reading the profile descriptions, so changing a description changes
how it chooses with no code change.

**Transparency** is computed, not narrated: a reasoning trace of the decisions
taken before any number existed, method notes on how to read the ranking, and a
per-airport attribution of what built each score.

## How a score is computed

Every user-visible number originates in `app/scoring/score.py`. No LLM, no I/O,
no network.

**1. Percentile-rank each metric nationally.** Each weighted metric is converted
to a 0–100 rank across every US airport with reported traffic. Percentile rank
rather than a z-score, because a handful of very large hubs would otherwise
dominate the distribution and flatten every difference below them.

**2. Multiply by the profile's weight and sum.** A metric weighted at 40% can
contribute at most 40 points, so the total lands on a 0–100 scale and the
components always add up to the score.

Worked through, for BDL under `terminal_expansion`:

| Metric | Percentile | × Weight | = Points | Ceiling |
|---|---|---|---|---|
| `pax_per_departure` | 94.4 | 0.40 | 37.8 | 40 |
| `enplanement_volume` | 94.7 | 0.30 | 28.4 | 30 |
| `load_factor` | 92.5 | 0.30 | 27.8 | 30 |
| | | | **93.9** | 100 |

**Percentiles are taken over the whole country before any filter is applied.**
This is the part most easily misread: 93.9 is BDL's standing against every US
airport with reported traffic, *not* its position among the New England rows on
screen. Ranking within a filtered set would make BOS "100th percentile" merely
for being the only large hub in the region. The size of that national frame is
reported with every ranking, in the Normalization method note.

**Missing metrics renormalize rather than drop.** An airport with no
`load_factor` is scored on the other two, reweighted 0.40/0.70 → 57% and
0.30/0.70 → 43%. It still gets a score, but it was ranked on a different blend
than its neighbours — so the row is flagged, and the response says so.

**Two scores within 1.0 point are one band.** Percentile scoring compresses hard
at the ceiling; below that threshold the gap is smaller than the method can
resolve, so the API reports the pair as level rather than ordered.

**What a score is not.** It measures demand pressure. Nothing here knows what has
already been built — gates, terminal floor area, stands, slots — so a high score
never means capacity is short, only that the traffic is there.

## Agent state

One `AgentState` dict (`app/agent/state.py`) flows through the graph, checkpointed
to Postgres per conversation by LangGraph's `AsyncPostgresSaver`. That checkpoint
is what makes a thread resumable and what lets a clarification span turns.

| Group | Fields |
|---|---|
| Conversation | `messages` |
| Written by the LLM | `intent`, `raw_entities`, `profile_name`, `profile_rationale`, `clarification`, `scope_answer`, `scope_count` |
| Written by deterministic code | `airports`, `region`, `weights`, `scores`, `breakdown`, `method_notes`, `drivers`, `facts`, `live_conditions` |
| Clarification loop | `clarify_queue`, `clarify_answered`, `clarify_attempts` |
| Carried between turns | `focus`, `pending_options`, `result_limit`, `assumptions`, `warnings` |

The split in that table is the core invariant: **the LLM never writes a number.**
It contributes an intent, some entity strings and a profile name; every figure
comes from the deterministic half.

Two consequences worth knowing:

**State persists, so a turn that skips scoring must clear it.** `cleared_results()`
wipes the previous turn's numbers — otherwise answering "hello" mid-conversation
would return the last ranking still attached.

**Each answer carries its own numbers.** State holds only the *latest* turn's
results, so `narrate` pins a copy to the assistant message it wrote. That is what
lets the UI rebuild every table when you reopen an old conversation.

## Data sources

Fetched live at startup:

| Source | Auth | What it provides |
|---|---|---|
| [BTS T-100 via USDOT ArcGIS](https://services.arcgis.com/xOi1kZaI0eWDREZv/arcgis/rest/services/T100_Domestic_Market_and_Segment_Data/FeatureServer/1) | none | CY2024 airport totals for ~1,279 US airports: enplanements, passengers, departures, arrivals, freight, mail |
| [OurAirports](https://ourairports.com/data/) | none | Airport reference and runway data — `iso_region`, lat/lon, runway counts and lengths |

Queried live per turn, **advisory only — never part of a score**:

| Source | Auth | What it provides |
|---|---|---|
| [FAA NAS Status](https://nasstatus.faa.gov/api/airport-status-information) | none | Current ground stops, delay programs, closures |
| [OpenSky Network](https://opensky-network.org/) | anonymous | Aircraft currently within a box around an airport |

Optional, read from disk:

**BTS T-100 Segment (All Carriers)** adds route-level metrics — load factor,
long-haul and international share, schedule shortfall. TranStats serves it from
an ASP.NET form with no stable URL, so it is downloaded once into
`backend/data/raw/` (automatically on first Docker boot, or via
`python scripts/fetch_t100_segment.py`). Everything it adds is additive: without
the file the system runs exactly as before, minus those metrics.

📖 **[docs/DATA_SOURCES.md](docs/DATA_SOURCES.md)** is the full reference —
every endpoint live-tested, with response shapes, quotas, gotchas, and the
sources deliberately *not* used.

### Documented assumptions

Public data does not measure investment need directly, so several figures rest
on stated assumptions — passenger weight for putting freight and passengers on
one scale, an assumed annual runway ceiling, a long-haul distance threshold.
Every one is published in the `provenance` block of `/health` and each chat
response. Notably, **nothing here measures delay**: airfield metrics are annual
averages against an assumed ceiling, which is capacity utilization, not
congestion.

---

## Running it with Docker Compose

The recommended path. Brings up Postgres, the API and the frontend together, and
handles the one-off data download for you.

### 1. Configure

```bash
cp .env.example .env
```

Edit `.env` and set your key:

```
OPENAI_API_KEY=sk-...
```

That is the only value you must change. Everything else has a working default.

> **Note the database host.** The root `.env` points at `postgres:5432` — the
> Compose service name. `backend/.env` is the separate file used when running
> the backend *outside* Docker, and points at `localhost:5433`. Mixing them up
> is the usual cause of a backend that hangs on startup.

### 2. Start

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| Postgres | `localhost:5433` |

### What happens on first boot

1. **Postgres starts** and the backend waits on its healthcheck.
2. **The T-100 Segment extract downloads** — about 18 MB and 80 seconds. It
   lands in `backend/data/raw/`, which is bind-mounted from the host, so it
   survives rebuilds and never downloads twice.
3. **The backend warms** — fetches T-100 totals and OurAirports data, builds the
   metrics frame, creates tables, and seeds the built-in weight profiles.
4. **The frontend** comes up on 5173.

Expect roughly two minutes for the first run. Subsequent starts skip the
download and take a few seconds.

The download is fail-soft: if TranStats is unreachable, the API starts anyway
without those four metrics. To skip it deliberately — offline work, CI, or a
faster start:

```bash
SKIP_T100_DOWNLOAD=1 docker compose up
```

### Everyday commands

```bash
docker compose up                  # start (after the first build)
docker compose up --build backend  # rebuild just the API
docker compose logs -f backend     # follow API logs
docker compose down                # stop
docker compose down -v             # stop and drop the database volume
```

`docker compose down -v` discards saved conversations and any weight profiles
you created or edited in the dashboard.

---

## Running it locally

Useful for backend work — `run.py` enables autoreload and sets the Windows event
loop policy that async psycopg requires.

You still need Postgres. The easiest way is to run just that service:

```bash
docker compose up postgres
```

**Backend:**

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                              # set OPENAI_API_KEY
python run.py                                     # http://localhost:8000
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev                                       # http://localhost:5173
```

**Tests** — no network, no database, no API key:

```bash
cd backend
python -m pytest          # 81 passed, 7 skipped
```

## Configuration

`backend/.env.example` documents every setting with its default. In short:

- **Connections** — `DATABASE_URL`, `CORS_ORIGINS`
- **LLM** — `OPENAI_API_KEY`, `OPENAI_MODEL` (must support structured output)
- **Tracing** — `LANGSMITH_*`; needs both `LANGSMITH_TRACING=true` *and* a key
- **Agent behaviour** — `HISTORY_MESSAGES`, `DEFAULT_RESULT_LIMIT`,
  `MAX_CLARIFY_ROUNDS`, `MAX_FACT_AIRPORTS`, `MAX_LIVE_LOOKUPS`,
  `MAX_ATTRIBUTED_ROWS`
- **Startup** — `WARM_ATTEMPTS`, `WARM_BACKOFF_SECONDS`, `T100_PAGE_SIZE`

The agent-behaviour settings are deliberately tuning knobs only — none of them
change what a score means, so two deployments still rank an airport identically.
The assumptions that *would* move scores stay in code and are published in
`provenance`.

## API

| Endpoint | Purpose |
|---|---|
| `GET /health` | Status and data provenance |
| `POST /api/chat` | Ask a question |
| `GET/POST/PATCH/DELETE /api/conversations` | Conversation history |
| `GET /api/airports` · `GET /api/airports/{iata}` | Raw metrics, unscored |
| `GET /api/regions` | Named multi-state regions |
| `GET /api/metrics` | Metric vocabulary — name, formula, meaning per metric |
| `GET/POST/PUT/DELETE /api/profiles` | Weight profiles |

## Layout

```
backend/
  app/
    agent/         LangGraph graph, nodes, prompts, state, reasoning trace
    scoring/       Deterministic scoring: normalize, score, explain, drivers, glossary
    data/          Source clients and metric derivation
    services/      Airport, region and profile resolution
    api/           FastAPI routes
  scripts/         T-100 download, profile reseed, container entrypoint
  tests/
frontend/src/      React dashboard and chat UI
docs/              Data source reference
```

## Troubleshooting

**Backend hangs on startup** — usually the wrong `DATABASE_URL`. Inside Docker
the host is `postgres`; outside it is `localhost:5433`.

**Chat returns an error but `/api/airports` works** — the deterministic path is
fine and the LLM is not. Check `OPENAI_API_KEY`.

**Rankings are missing load factor or international share** — the T-100 Segment
extract is absent. Run `python scripts/fetch_t100_segment.py` from `backend/`,
or drop a file into `backend/data/raw/`.

**Profile weights changed in code but not in the app** — seeding is
`ON CONFLICT DO NOTHING`, so an existing database keeps its values. Run
`python scripts/reseed_profiles.py` to preview the drift, then `--apply`.
