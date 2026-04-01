# Swarm Search Sim

Swarm Search Sim is a local mission planning and evaluation platform for multi-drone search-and-rescue teams. The simulation core remains under `src/`, the FastAPI product backend lives under `app/backend`, and the primary operator interface is now the React app under `app/web`.

The platform is built around a practical SAR workflow:

1. open the mission desk
2. start a new mission or reopen an existing one
3. complete the guided mission intake
4. review the recommended plan summary
5. continue into mission plans, comparison, launch, monitoring, replay, review, and reporting

## Architecture

### Simulation Core

- `src/scenarios/scenario.py`: scenario configuration and presets
- `src/environment/grid.py`: terrain, obstacles, trails, elevation, and wind
- `src/probability/belief.py`: belief-state propagation, evidence updates, entropy
- `src/coordination/`: search strategies and coordination logic
- `src/simulation/planning.py`: terrain-aware A* routing
- `src/simulation/engine.py`: run loop, sensing, comms, battery, interventions, replay
- `src/visualisation/renderer.py`: mission renders and artifacts

### Backend

- `app/backend/main.py`: FastAPI entrypoint
- `app/backend/api/`: route modules by domain
- `app/backend/domain/`: product services for scenarios, plans, comparisons, runs, experiments, reviews, reports, recommendations
- `app/backend/db/sqlite.py`: SQLite metadata store
- `app/backend/core/job_manager.py`: background mission and experiment jobs
- `app/backend/reporting.py`: HTML report generation

### Frontend

- `app/web/`: React + TypeScript + Vite frontend
- `app/web/src/api/`: typed API client and query hooks
- `app/web/src/components/`: shared operator UI components
- `app/web/src/pages/`: product pages for planning, monitoring, replay, experiments, reports, and review

### Legacy UI

- `app/frontend/`: legacy Streamlit UI retained as a fallback only

## Main Product Workflows

The React app covers:

- mission desk / home
- guided mission intake
- scenarios
- mission plans
- doctrine / template library
- plan comparison
- recommendations
- mission control
- replay
- run history
- experiments
- reports
- after-action review

## Start Here Demo Flow

For the smoothest local demo:

1. start the FastAPI backend on `8000`
2. start the React frontend on `5173`
3. open the mission desk and choose `Start a New Mission`
4. complete the guided intake: situation, assets, search style, recommendation, continue
5. save the mission into the mission plan workspace
6. run a saved comparison from the mission options workspace
7. launch a monitored mission run from the saved plan or top candidate
8. watch Mission Control update live while the run progresses
9. open Replay and After-Action Review once the run completes
10. open the generated report from the Reports page

This is the intended operator journey:

`plan -> compare -> launch -> monitor -> replay -> review -> report`

## Run The Simulator Core

From the repo root:

```bash
python main.py
```

This still runs the simulator directly and writes artifacts under `outputs/`.

## Run The FastAPI Backend

From the repo root:

```bash
python -m app.backend.server --host 127.0.0.1 --port 8000
```

Or:

```bash
uvicorn app.backend.main:app --host 127.0.0.1 --port 8000
```

API docs:

- [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## Run The React Frontend

The React frontend is now the primary product interface.

From the repo root:

```bash
cd app/web
npm install
npm run dev
```

Default local addresses:

- backend: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- frontend: [http://127.0.0.1:5173](http://127.0.0.1:5173)

Frontend environment:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

See `app/web/.env.example`.

## Frontend Commands

From `app/web`:

```bash
npm run dev
npm run build
npm run preview
npm run test
```

## Phase 8 UI Direction

The React UI is now tuned around a restrained mission-console style:

- calm dark achromatic palette with subtle accent usage
- generous spacing and clearer page hierarchy
- collapsible sidebar with lighter persistent navigation weight
- reusable metric, status, risk, recommendation, and comparison briefing cards
- cleaner empty, loading, and error states
- stronger page framing so each screen makes the next action obvious
- collapsible technical and secondary panels so the main operator path stays readable
- live-focused Mission Control and clearer replay/review workspaces with a dominant visual anchor

Contributors should prefer extending the shared UI primitives in `app/web/src/components/ui/` before creating one-off page styling.

## Mission Planning Experience

### Mission Desk

The home screen now behaves as a calmer mission desk instead of a dense dashboard. It:

- greets the user and explains what the product is for
- makes the primary next actions obvious:
  - start a new mission
  - open an existing mission
- keeps sample missions easy to explore
- moves operational counts and health lower on the page
- keeps recent missions and recent activity visible without overwhelming the start experience

### Guided Mission Intake

The new intake flow is staged as:

1. situation
2. assets
3. search style
4. recommendation
5. continue

The guided intake keeps the first pass operator-friendly and hides advanced details until they are useful. It captures:

- whether the last known location is known or unknown
- search area size
- environment type
- weather
- time since last contact
- fleet package details
- staging location
- operator search intent
- preferred search pattern or a request for automatic pattern selection

The intake produces a standard `MissionPlan`, so the rest of the workflow remains compatible.

### Search Patterns And Formations

Slice 4 adds an operator-facing search-pattern layer so the platform can explain how the fleet will actually cover ground. Supported patterns include:

- `Broad Area Sweep`: evenly spaced lane coverage for fast early search over wide areas
- `Sector Split`: parallel zone-based search that makes fleet allocation easy to monitor
- `Expanding Ring`: outward growth from a known or likely origin area
- `Perimeter Containment`: boundary-focused search to reduce missed movement beyond the search box
- `Adaptive Rebalance`: starts from a base pattern and shifts assets when clues, inspections, confirmations, or battery rotations change the mission

Pattern selection is deterministic and explainable. At a high level it considers:

- whether the last known position is known or unknown
- search area size and shape
- fleet size and mixed-fleet composition
- effective sensor swath and overlap margin
- battery sustainability and reserve burden
- mission intent from intake

Unknown-location wide-area missions now bias toward coverage-first layouts instead of acting like a point search. Lane spacing and sector partitioning are derived from effective sensor coverage rather than a fixed arbitrary distance.

### Real Mission Areas And AOI Planning

Slice 5 adds a local-first real-area workflow so operators can plan against a believable mission area instead of a generic synthetic grid. The intake now supports:

- rough location input by place name or direct latitude/longitude
- local-first location resolution through a built-in gazetteer, with direct coordinate fallback for exact areas
- a map-style mission-area planner centered on the selected location
- AOI definition by drawing and reshaping a rectangle
- staging/base placement on the selected area
- grid resolution controls that map the AOI into the existing simulator grid
- deterministic terrain, elevation, trail, and obstacle summaries derived from the selected area

The current Slice 5 model stays intentionally practical:

- no live external GIS dependency is required for local use
- no heavy image classification pipeline is used
- no 3D terrain or 3D replay is added

Instead, the product resolves a real place or coordinate pair, converts the AOI into a sim grid, and derives explainable terrain layers and summaries that the preserved simulation core can use.

### Scenarios

Operators can:

- browse saved scenarios
- edit key parameters in grouped sections
- create new scenarios
- keep advanced settings collapsed until needed
- keep using scenario configs compatible with the existing backend and layer ingestion flow

### Mission Plans

Mission plans are now the core product object and capture:

- linked scenario or template
- mission intent
- mission intake summary
- asset package / mixed fleet details
- selected strategy
- drone count and reserve policy
- communication assumptions
- operator notes
- recommendation snapshot
- linked comparisons, runs, reviews, and reports

### Doctrine / Template Library

The doctrine library surfaces operational presets such as:

- open terrain rescue
- dense canopy poor comms
- windy ridge-line search
- low battery contingency
- staged sector sweep
- rapid containment

Each entry exposes intended use, risks, assumptions, tags, and recommended strategies.

### Plan Comparison

Operators can:

- load a mission plan
- define candidate search spaces
- save a comparison workspace
- inspect ranked candidates
- review recommendation and uncertainty summaries
- inspect performance and risk tradeoffs side by side
- launch a run from a candidate

### Recommendations

Recommendation outputs include:

- recommended search pattern
- recommended strategy
- recommended drone count
- recommended reserve threshold
- concise operator-facing summary
- search-pattern summary and why it fits
- top alternative summary
- key tradeoffs
- key risks
- human-readable rationale
- risk summary
- uncertainty summary
- mission-area summary and area-aware reasoning
- candidate support table
- technical details under a collapsible section in the UI

These summaries are deterministic and template-based. No external LLM is used for the operator brief.

### Asset Package Support

Slice 1 adds first-class product-layer fleet modeling through:

- `DroneTypeProfile`
- `AssetPackage`
- `FleetComposition`

The mission intake and mission plan workflow now support:

- uniform fleets
- mixed fleets with multiple drone types
- endurance, range, cruise speed, sensor level, thermal capability proxy, turnaround time, and notes
- staging location metadata

The simulation core is still preserved. Where the core expects a uniform fleet, the product layer derives an explainable aggregate fleet profile instead of rewriting the simulator.

### Battery Lifecycle Realism

Slice 2 adds a more operationally believable battery lifecycle without rewriting the simulation core. The simulator now models:

- path-aware return-to-base decisions instead of a flat battery percentage trigger
- reserve presets:
  - `conservative`
  - `balanced`
  - `aggressive`
- point-of-no-return evaluation based on route energy, reserve margin, terrain cost, and wind factor
- lifecycle states for:
  - deploying
  - searching
  - returning to base
  - recharging or swapping
  - ready to redeploy
  - redeploying
  - unavailable
- turnaround time driven by fleet metadata such as `turnaround_time_minutes`
- automatic redeploy and rejoin behavior after service completes

The current Slice 2 model stays intentionally lightweight:

- no battery chemistry model
- no direct hardware integration
- no large coordination rewrite

The product layer uses Slice 1 asset package data to influence endurance, return margin, turnaround time, and redeploy sustainability.

### Cue -> Inspect -> Confirm Sensing

Slice 3 extends the sensing model so detections no longer jump straight from a weak hit to full mission success. The simulator now models:

- low-confidence cue generation during broad search
- environment-dependent confidence based on distance, terrain visibility, and weather modifiers
- explicit inspection behavior that sends a drone closer to investigate a possible contact
- confirm or reject outcomes after close inspection
- mission success driven by confirmed contact, not a weak cue alone

The current Slice 3 model stays intentionally explainable:

- no black-box tracker
- no heavy ML
- no direct hardware integration
- no large coordination rewrite

This keeps the cue-to-confirm workflow operationally believable while preserving the existing simulator architecture.

### Mission Control

Mission Control is the live operator view. It supports:

- launching runs from plans, scenarios, comparisons, or templates
- polling run status and progress
- viewing the latest mission snapshot
- inspecting the live fleet roster with battery and lifecycle state
- viewing battery rotation counts and mission phase
- viewing possible contacts, inspections in progress, and confirmed contacts
- viewing a recent event feed with readable lifecycle summaries
- viewing cue, inspect, confirm, and reject events in plain language
- seeing return-to-service timing and reserve status for each drone
- applying interventions
- clearer separation between mission state and operator actions
- a dominant mission visual with collapsible event, roster, intervention, and contact modules
- subtle live refresh behavior while the run is active
- active search-pattern visibility with plain-language pattern status
- real mission-area context, including AOI label, area size, grid resolution, and staging point
- readable rebalance context when coverage shifts because of candidate contacts, confirmations, returns to base, or redeploys

Supported interventions include:

- pause
- resume
- force return
- assign waypoint
- add priority zone
- add exclusion zone
- switch strategy

### Replay

Replay supports:

- loading completed runs
- scrubbing timeline frames
- viewing replay state and events together
- timeline points for return-to-base, service complete, and redeploy events
- timeline points for possible contact, inspection, confirmation, and rejection events
- step summaries with clearer battery rotation context
- step summaries with clearer sensing progression context
- step summaries with clearer search-pattern progression context
- readable fleet state at each replay step
- a fixed playback workstation layout with collapsible event and roster panels
- search-pattern change markers and rebalance summaries when the mission shifts coverage
- AOI-backed mission context so replay reflects the selected real mission area instead of only a generic grid

### Experiments

Operators and analysts can:

- launch grouped robustness experiments
- inspect summary tables
- view comparison charts
- open artifact outputs

### Reports And After-Action Review

Reports and review workflows support:

- indexed HTML reports
- review creation from completed runs
- outcome and deviation summaries
- alternate-plan summary where available
- battery lifecycle summaries
- sensing workflow summaries
- search-pattern summaries and pattern-change highlights
- mission-area summaries with area size, grid, staging, and terrain context
- asset rotation counts
- possible contact, inspection, confirmation, and false-alarm counts
- mission continuity impact notes
- battery margin and reserve policy summaries
- lifecycle event highlights for return, service, redeploy, and rejoin moments
- sensing highlights for cue, inspect, confirm, reject, and search-resume moments
- search-pattern highlights for initial layout, rebalance, and restored coverage moments
- links back to replay and run artifacts
- clearer artifact linkage and cleaner export browsing
- human-readable report actions such as mission brief, run summary, and after-action report exports

## Page Overview

- `Mission Desk`: start-here view with primary actions, a calmer right-hand handoff panel, quieter status context, and recent mission access
- `New Mission`: guided intake workflow with one dominant working column, a compact sticky summary rail, collapsed advanced asset detail, and recommendation-first briefings
- `Scenarios`: grouped editor for map, target, drone, sensing, battery, and planner settings
- `Mission Plans`: central workspace for planning context, notes, recommendation snapshot, and downstream links
- `Doctrine Library`: operational presets with intended use, assumptions, risks, and recommended strategies
- `Plan Comparison`: saved candidate analysis workspace with ranked options and tradeoff summaries
- `Recommendations`: decision-support briefing for a selected mission plan
- `Mission Control`: live monitoring page with a dominant mission visual and collapsible mission context, event, roster, intervention, and contact modules
- `Replay`: playback workstation for completed runs with a fixed visual anchor, richer timeline markers, and collapsible secondary panels
- `Run History`: filterable ledger of mission runs
- `Experiments`: grouped robustness experiments and artifact browsing
- `Reports`: indexed report browser with operator-friendly export language
- `After-Action Review`: operational review center with human-readable summary-first narrative and collapsed technical details

## Storage And Artifacts

SQLite stores metadata and linkages while artifacts remain file-based.

Default locations:

- `app/storage/swarm_product.db`
- `app/storage/scenarios/`
- `app/storage/templates/`
- `app/storage/plans/`
- `app/storage/comparisons/`
- `app/storage/runs/`
- `app/storage/experiments/`
- `app/storage/reviews/`
- `app/storage/reports/`
- `outputs/` for direct simulator artifacts

Run artifacts now include lifecycle-rich replay and event outputs that preserve:

- drone lifecycle state in replay frames
- reserve status and battery margin fields in live and saved snapshots
- return-to-base, service, redeploy, and rejoin events in the event log
- sensing-stage state in replay frames and live snapshots
- candidate contact summaries and cue-to-confirm event history
- active search-pattern state and search-geometry summary
- search-pattern selection, rebalance, and restoration events

## API Coverage

Main route groups:

- `/health`
- `/dashboard/summary`
- `/geo/resolve-location`
- `/geo/preview-area`
- `/scenarios`
- `/templates`
- `/library/templates`
- `/plans` with asset-package and mission-intent aware payloads
- `/comparisons`
- `/runs` with lifecycle-rich snapshots, events, and replay payloads
- `/experiments`
- `/jobs`
- `/reports` with battery lifecycle summaries in run and review exports
- `/reviews` with lifecycle-aware AAR summaries and readable timeline entries
- `/compare-plans`
- `/recommend` with concise recommendation summaries, alternatives, tradeoffs, risks, and technical details
- `/artifacts/{owner_type}/{owner_id}/{artifact_type}`

Important Slice 2 payload additions include:

- scenario / run config:
  - `battery_policy.reserve_preset`
  - `drone.turnaround_time_minutes`
  - `drone.estimated_max_range_km`
  - `scenario.step_duration_minutes`
- run snapshots:
  - `run_phase`
  - `lifecycle_summary`
  - per-drone `lifecycle_state`
  - per-drone `operator_status`
  - per-drone `reserve_status_label`
  - per-drone `return_eta_steps`
  - per-drone `return_service_eta_steps`
- review and report summaries:
  - `battery_lifecycle`
  - mission continuity impact
  - asset utilization summary
  - battery margin summary

Important Slice 3 payload additions include:

- run snapshots:
  - `sensing_summary`
  - `candidate_contacts`
  - per-drone `sensing_state`
  - per-drone `sensing_status`
  - per-drone `assigned_contact_id`
- run, review, and report summaries:
  - `sensing_lifecycle`
  - candidate detection counts
  - inspection counts
  - confirmed vs rejected contact summaries
  - sensing highlight timelines
- event stream:
  - `possible_contact_detected`
  - `inspection_initiated`
  - `inspection_pass_complete`
  - `contact_confirmed`
  - `false_positive_rejected`
  - `search_resumed_after_reject`

Important Slice 4 payload additions include:

- plan and recommendation payloads:
  - `search_pattern`
  - `recommended_search_pattern`
  - `recommended_search_pattern_label`
  - `search_pattern_summary`
  - `search_pattern_reason`
  - `search_pattern_fit_summary`
- run snapshots:
  - `search_pattern`
  - `search_pattern_label`
  - `search_pattern_base`
  - `search_pattern_rebalanced`
  - `search_pattern_rebalance_reason`
  - `search_pattern_geometry`
- run, review, and report summaries:
  - `search_pattern`
  - pattern effectiveness summary
  - pattern-change highlights
- event stream:
  - `search_pattern_selected`
  - `search_pattern_rebalanced`
  - `search_pattern_restored`

Important Slice 5 payload additions include:

- mission plan and scenario payloads:
  - `mission_area`
  - `map_selection`
  - resolved location metadata
  - AOI bounds and rectangle geometry
  - grid size and grid resolution
  - staging/base coordinates and grid position
  - terrain/elevation summary metadata
- run snapshots:
  - `mission_area`
- run, review, and report summaries:
  - `mission_area`
  - `mission_area_summary`

Slice 5 currently uses a local-first fallback for map data:

- place names resolve through a built-in gazetteer
- direct coordinates are supported for exact placement anywhere
- terrain and elevation are derived deterministically from the selected AOI when live external layers are not available

## Docker

Local container flow:

```bash
docker-compose up --build
```

This starts:

- backend on `8000`
- React frontend preview on `5173`

## Testing

Backend and simulator tests:

```bash
pytest
```

Full local validation used for Slice 2:

```bash
pytest -q
cd app/web
npm run test
npm run build
```

Full local validation used for Slice 3:

```bash
pytest -q
cd app/web
npm run test
npm run build
```

Full local validation used for Slice 4:

```bash
pytest tests/test_phase4.py tests/test_phase7_product.py -q
cd app/web
npm run test
npm run build
```

Full local validation used for Slice 5:

```bash
pytest tests/test_phase4.py tests/test_phase7_product.py -q
cd app/web
npm run test
npm run build
```

Optional backend smoke check:

```bash
python -m app.backend.server --host 127.0.0.1 --port 8000
```

Then open [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health).

Frontend tests:

```bash
cd app/web
npm run test
```

Frontend production build check:

```bash
cd app/web
npm run build
```

## Current Direction

The platform is currently focused on mission planning and evaluation for SAR teams. It is not direct drone command software in this phase. The priority is operator trust, explainability, plan comparison, monitored simulation, replay, and review.
