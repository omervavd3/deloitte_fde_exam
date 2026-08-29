# Airport Investment Intelligence Agent

A conversational agent that ranks and compares US airports as infrastructure
investment opportunities, using public aviation data.

Ask *"Which airports in New England are strong candidates for terminal
expansion?"* and it resolves the region, picks a weighting thesis, scores every
airport nationally, and explains what drove the result - showing the ranking,
the per-metric breakdown, the decisions it made, and the caveats on reading it.

## How it works

A LangGraph agent of eight nodes. **Only two of them call an LLM:**

- `parse_intent` - question → intent, entity strings, weight profile. No numbers.
- `narrate` - explains results it may only restate, never compute.

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
Air Mail Hub…) stored in Postgres and editable from the dashboard - see
[Weight profiles](#weight-profiles) below for why the design works this way.

**Transparency** is computed, not narrated: a reasoning trace of the decisions
taken before any number existed, method notes on how to read the ranking, and a
per-airport attribution of what built each score.

## How a score is computed

Every user-visible number originates in `app/scoring/score.py`. No LLM, no I/O,
no network.

**1. Percentile-rank each metric nationally.** Each weighted metric is converted
to a 0-100 rank across every US airport with reported traffic. Percentile rank
rather than a z-score, because a handful of very large hubs would otherwise
dominate the distribution and flatten every difference below them.

**2. Multiply by the profile's weight and sum.** A metric weighted at 40% can
contribute at most 40 points, so the total lands on a 0-100 scale and the
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
than its neighbours - so the row is flagged, and the response says so.

**Two scores within 1.0 point are one band.** Percentile scoring compresses hard
at the ceiling; below that threshold the gap is smaller than the method can
resolve, so the API reports the pair as level rather than ordered.

**What a score is not.** It measures demand pressure. Nothing here knows what has
already been built - gates, terminal floor area, stands, slots - so a high score
never means capacity is short, only that the traffic is there.

## Weight profiles

A profile is a named investment thesis - a set of metric weights summing to 1.0,
plus a description written for the agent to read.

```
terminal_expansion   pax_per_departure 40% · enplanement_volume 30% · load_factor 30%
cargo_facility       freight_share 50% · operations_per_runway 25% · enplanement_volume 25%
air_mail_hub         mail_share 45% · freight_share 20% · operations_per_runway 20% · …
```

### Why the agent works this way

The obvious alternative is to let the model emit weights directly - ask it for
"40% passenger throughput, 30% size" and score on whatever it returns. That was
rejected deliberately. Profiles exist to keep the system **traceable, debuggable
and reproducible**:

**One bounded decision instead of an open one.** The model picks a *name* from a
fixed catalog, not a set of numbers. That choice is validated against the
catalog; anything unrecognised falls back to `general_modernization` and records
an assumption saying so. There is no path by which a model hallucinates a weight.

**The same question always produces the same numbers.** Once a profile is
selected, scoring is pure arithmetic over a fixed frame - no sampling, no
temperature. Ask twice, get identical scores. This is test-locked
(`test_scores_are_reproducible`), and it is what makes the output defensible
rather than merely plausible.

**Failures become diagnosable.** When an answer looks wrong there are only two
places to look, and the response tells you which:

- *the wrong thesis was chosen* - an LLM problem, visible in the reasoning trace
  as `Scored under the profile: cargo_facility. Chosen because: …`
- *the thesis is right but weighted badly* - a data problem, visible in the score
  breakdown showing which metric contributed what

Without profiles those two failure modes are indistinguishable, because the
weights would be a model output too.

**The reasoning is captured, not discarded.** `parse_intent` returns a
one-sentence rationale for its choice, surfaced in the trace and labelled as a
machine justification - so a reader knows which line is the model's reasoning
and which are facts about what ran.

**Behaviour is tunable without touching code.** The agent selects a profile by
matching the question against profile *descriptions*. Editing a description
changes how it chooses; editing weights changes what it produces. Neither needs
a deployment.

### The trade-off

Constraining the model is the point, but it is not free. Every bit of judgment
taken away from the LLM has to be supplied by a person instead, and that person
should be a domain expert. **I am not one.**

The weights are a hypothesis, not a measured fact. Someone decided that terminal
expansion is 40/30/30 across passengers per departure, enplanement volume and
load factor, rather than 50/25/25. That someone was me, reasoning from what the
data can support, not an airport planner reasoning from how terminals actually
get built. The same goes for the assumed runway ceiling, the 2,500 mile long-haul
threshold and the 200 lb passenger weight. All are documented and defensible;
none are authoritative.

Two further limits worth stating plainly:

**A new thesis needs a human to write it.** The agent can only choose from
profiles that already exist. Ask about something no profile covers and it falls
back to `general_modernization` and says so, rather than inventing a weighting.
That is the safe failure, but it is still a failure, and closing it means a
person adding a profile.

**The data constrains what a profile can even express.** Almost every metric here
scales with airport size, so a new thesis that does not lean on one of the
genuinely independent axes - freight share, mail share, the international shares,
schedule shortfall - will return the big hubs again whatever its weights say.
Judge a new profile by the ranking it produces, not by how its description reads.

What the design does offer is that a non-expert cannot hide behind it. Every
weight is visible in the dashboard, every assumption is published in
`provenance`, and every score decomposes into the metric that produced it. An
expert can look at this and say "your cargo weighting is wrong, freight share
should dominate less" - and then fix it in the UI, without touching code. That
is the best a non-expert can offer: not correct answers, but answers that are
cheap to correct.

The concrete next step would be validation against ground truth. The FAA
publishes its own assessment of which airports are runway-capacity constrained
(see [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md)). Checking how many of those
this model independently surfaces would turn the weights from a reasoned guess
into something with measured external agreement. That has not been done.

### Adding your own

The **Weight profiles** tab in the app is a full editor. Create a profile, give
it a name and description, set weights with sliders, and it is live immediately:
the agent can select it on the next question.

Three things the editor does for you:

- **Weights normalize to 1.0 on save**, so sliders need not add up by hand.
- **It warns on double-counting.** Some metric pairs rank airports identically:
  `departures_per_runway` and `runway_pressure` are the same signal, one divided
  by a fixed ceiling. Weighting both puts the sum of both weights on one signal
  instead of blending two. The editor flags it; no built-in profile does it.
- **The glossary** above the cards explains what every metric measures and how it
  is computed, served from the same source the agent narrates from.

The description matters more than it looks - it *is* the selection criterion.
Write it as instructions for choosing ("Choose when the question concerns cargo
or freight rather than passenger traffic"), not as marketing.

Built-in profiles can be edited but not deleted. Code-side changes to their
defaults do not overwrite a live database - run `scripts/reseed_profiles.py` to
preview and apply those deliberately.

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
wipes the previous turn's numbers - otherwise answering "hello" mid-conversation
would return the last ranking still attached.

**Each answer carries its own numbers.** State holds only the *latest* turn's
results, so `narrate` pins a copy to the assistant message it wrote. That is what
lets the UI rebuild every table when you reopen an old conversation.

## Data sources

### Why these sources

Free aviation data is scarcer than it looks, and that constraint shaped the
whole pipeline. Every source below was live-tested before being adopted; the
selection rule was **keyless, free, and no login** - so that running this project
never depends on a credential the next person does not have.

What that ruled out:

- **FlightAware AeroAPI, Flightradar24** - real cost, no useful free tier.
- **AeroDataBox, aviationstack** - freemium, but quotas small enough that a few
  debugging runs exhaust a month. Fine as garnish, never load-bearing.
- **FAA OPSNET / ASPM** - free, but recent data needs a login.
- **OpenFlights routes** - free and easy, but frozen around 2014.

And what survived is mostly **not** APIs. Of everything checked, only three are
genuine keyless REST endpoints: the T-100 ArcGIS mirror, FAA NAS Status, and
OpenSky. The richest aviation data - the full T-100 segment tables, on-time
performance, FAA forecasts - ships as bulk file downloads, several behind
ASP.NET forms with no stable URL. That is why the T-100 Segment extract is a
scripted one-off download rather than a live call.

**What the constraint cost.** The keyless sources carry annual totals for a
single year, so there is no time series and no growth trend. The ArcGIS mirror
has no `seats` column, which is why load factor needs the separate segment
extract. And no adopted source carries a departure time, so **nothing here
measures delay** - the reason every airfield metric is framed as capacity
utilization rather than congestion.

### What is used

Fetched live at startup:

| Source | Auth | What it provides |
|---|---|---|
| [BTS T-100 via USDOT ArcGIS](https://services.arcgis.com/xOi1kZaI0eWDREZv/arcgis/rest/services/T100_Domestic_Market_and_Segment_Data/FeatureServer/1) | none | CY2024 airport totals for ~1,279 US airports: enplanements, passengers, departures, arrivals, freight, mail |
| [OurAirports](https://ourairports.com/data/) | none | Airport reference and runway data - `iso_region`, lat/lon, runway counts and lengths |

Queried live per turn, **advisory only - never part of a score**:

| Source | Auth | What it provides |
|---|---|---|
| [FAA NAS Status](https://nasstatus.faa.gov/api/airport-status-information) | none | Current ground stops, delay programs, closures |
| [OpenSky Network](https://opensky-network.org/) | anonymous | Aircraft currently within a box around an airport |

Optional, read from disk:

**BTS T-100 Segment (All Carriers)** adds route-level metrics - load factor,
long-haul and international share, schedule shortfall. TranStats serves it from
an ASP.NET form with no stable URL, so it is downloaded once into
`backend/data/raw/` (automatically on first Docker boot, or via
`python scripts/fetch_t100_segment.py`). Everything it adds is additive: without
the file the system runs exactly as before, minus those metrics.

### Documented assumptions

Public data does not measure investment need directly, so several figures rest
on stated assumptions - passenger weight for putting freight and passengers on
one scale, an assumed annual runway ceiling, a long-haul distance threshold.
Every one is published in the `provenance` block of `/health` and each chat
response, so a reader can see what a number rests on rather than taking it on
trust.

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

> **Note the database host.** The root `.env` points at `postgres:5432` - the
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
2. **The T-100 Segment extract downloads** - about 18 MB and 80 seconds. It
   lands in `backend/data/raw/`, which is bind-mounted from the host, so it
   survives rebuilds and never downloads twice.
3. **The backend warms** - fetches T-100 totals and OurAirports data, builds the
   metrics frame, creates tables, and seeds the built-in weight profiles.
4. **The frontend** comes up on 5173.

Expect roughly two minutes for the first run. Subsequent starts skip the
download and take a few seconds.

The download is fail-soft: if TranStats is unreachable, the API starts anyway
without those four metrics. To skip it deliberately - offline work, CI, or a
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

Useful for backend work - `run.py` enables autoreload and sets the Windows event
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

**Tests** - no network, no database, no API key:

```bash
cd backend
python -m pytest          # 81 passed, 7 skipped
```

## Configuration

`backend/.env.example` documents every setting with its default. In short:

- **Connections** - `DATABASE_URL`, `CORS_ORIGINS`
- **LLM** - `OPENAI_API_KEY`, `OPENAI_MODEL` (must support structured output)
- **Tracing** - `LANGSMITH_*`; needs both `LANGSMITH_TRACING=true` *and* a key
- **Agent behaviour** - `HISTORY_MESSAGES`, `DEFAULT_RESULT_LIMIT`,
  `MAX_CLARIFY_ROUNDS`, `MAX_FACT_AIRPORTS`, `MAX_LIVE_LOOKUPS`,
  `MAX_ATTRIBUTED_ROWS`
- **Startup** - `WARM_ATTEMPTS`, `WARM_BACKOFF_SECONDS`, `T100_PAGE_SIZE`

The agent-behaviour settings are deliberately tuning knobs only - none of them
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
| `GET /api/metrics` | Metric vocabulary - name, formula, meaning per metric |
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

## What I would improve next

### Engineering and debuggability

The deterministic core is well covered by tests. The full stack around it is not.

- **No tests above the unit layer.** The scoring, clarification and metric logic
  have real coverage, but nothing exercises the FastAPI routes, and the frontend
  has no tests at all. A handful of `TestClient` tests over `/api/chat` and
  `/api/profiles` would catch contract breaks that currently only show up in the
  browser.
- **The intent eval set is switched off.** `tests/test_intent.py` holds the
  question to profile mappings that would verify the agent picks the right
  thesis, but the tests are skipped with an empty body and a stale reason
  (`parse_intent not implemented`, which it now is). Wiring that up against the
  real classifier is the single highest-value test to add, because profile
  selection is the one place a model decision moves the ranking.
- **No linting in the loop.** `ruff` is not installed and ESLint has no config
  file, so nothing catches dead imports or unused state automatically.
- **Dead code to remove.** `TTLCache` is constructed and never read,
  `sensitivity.py` raises `NotImplementedError` and is never imported, and
  `schemas/airport.py::Airport` is unused. The unused cache is the interesting
  one: `enrich_live` calls the FAA and OpenSky APIs on every ranking turn with
  no caching at all, so repeated questions re-hit rate-limited endpoints.
- **Type drift between backend and frontend.** `Intent` has seven values in
  Python and five in TypeScript, missing `answer` and `chitchat`. Latent today
  because nothing in the UI reads it, wrong the moment something does.
- **The UI has the problem the narration just fixed.** The agent now explains a
  score as "37.8 of the 40 points that metric can contribute", but the score
  composition bars still show a bare `37.8 pts` with no scale. `drivers` is
  computed and sits in state; it is simply not passed through to the frontend.
- **Dev defaults in the container.** `UVICORN_RELOAD` defaults to on, so the
  Docker image ships with `--reload`. Fine for this project, wrong for anything
  real, and undocumented either way.

### Data, to make it more accurate

The scoring is only as good as the columns behind it, and the free-data
constraint left real gaps:

- **Installed capacity is the big one.** Nothing here knows how many gates,
  stands or slots an airport already has, which is why a score can only ever be
  demand pressure. An airport that just opened a concourse still ranks high.
  Closing this needs data the free sources do not carry.
- **No delay data, though it is available.** BTS On-Time Performance is free and
  scriptable, and its `NASDelay` column isolates airport and airspace capacity
  delay from airline problems, which is about as direct a congestion signal as
  public data offers. It was skipped on size (50 to 200 MB compressed per month,
  several GB a year). Ingesting it, aggregated to airport-month, would replace
  the current annual-average proxy with something that actually measures peak
  behaviour.
- **One year, so no trend.** Everything is CY2024 totals. There is no growth
  rate, and growth is arguably more investable than level. The FAA Terminal Area
  Forecast publishes enplanement and operations forecasts per airport out to
  2045 and would add a forward-looking component.
- **Hub tier is a proxy.** It is derived here from enplanement share rather than
  read from the FAA ACAIS file, so it approximates the official classification
  instead of matching it.
- **The segment extract has no refresh story.** It is a one-off download; there
  is nothing that notices when it is stale.
- **Planned capital spend is missing.** FAA NPIAS lists planned development per
  airport, which would work well as a modifier rather than an input: an airport
  with a large funded program already underway is arguably a worse incremental
  investment than one with unmet need and no plan.

### Working with a domain expert

This is the one that would change the output most, and it is not an engineering
task. The dashboard already lets someone edit weights and descriptions without
touching code, so the mechanism exists. What is missing is the collaboration
around it:

- **Which parameters should the agent even look at?** The current twelve metrics
  are the ones the free data could support, not the ones an airport planner would
  choose. An expert would likely add some, drop some, and reject others as
  misleading. That conversation has not happened.
- **Are the right theses represented?** Seven profiles cover terminal, runway,
  cargo, mail, international, capacity relief and a general blend. Whether those
  are the real investment categories, or whether two should merge and three are
  missing, is a domain question.
- **Calibrating the thresholds.** The runway ceiling of 120,000 departures a
  year, the 2,500 mile long-haul cut, the 200 lb passenger weight, and the
  1.0-point tie band are all reasoned defaults. Each is the kind of number a
  practitioner would either confirm in seconds or correct immediately.
- **Back-testing against known answers.** The FAA publishes its own list of
  capacity-constrained airports. Scoring against that would turn weight tuning
  from argument into measurement, and give an expert something concrete to react
  to rather than a set of abstract percentages.

Two features would make that collaboration practical: a side-by-side view
comparing what two profiles return for the same question, so a weighting change
can be judged by its effect rather than its wording, and an audit trail on
profile edits recording who changed what and why. Right now a profile can be
retuned in the dashboard with no record of the reasoning, which is exactly the
thing the rest of the system works hard to preserve.

## Troubleshooting

**Backend hangs on startup** - usually the wrong `DATABASE_URL`. Inside Docker
the host is `postgres`; outside it is `localhost:5433`.

**Chat returns an error but `/api/airports` works** - the deterministic path is
fine and the LLM is not. Check `OPENAI_API_KEY`.

**Rankings are missing load factor or international share** - the T-100 Segment
extract is absent. Run `python scripts/fetch_t100_segment.py` from `backend/`,
or drop a file into `backend/data/raw/`.

**Profile weights changed in code but not in the app** - seeding is
`ON CONFLICT DO NOTHING`, so an existing database keeps its values. Run
`python scripts/reseed_profiles.py` to preview the drift, then `--apply`.
