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
- reusable metric, status, risk, recommendation, and comparison briefing cards
- cleaner empty, loading, and error states
- stronger page framing so each screen makes the next action obvious
- live-focused Mission Control and clearer replay/review workspaces

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

The intake produces a standard `MissionPlan`, so the rest of the workflow remains compatible.

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

- recommended strategy
- recommended drone count
- recommended reserve threshold
- concise operator-facing summary
- top alternative summary
- key tradeoffs
- key risks
- human-readable rationale
- risk summary
- uncertainty summary
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

### Mission Control

Mission Control is the live operator view. It supports:

- launching runs from plans, scenarios, comparisons, or templates
- polling run status and progress
- viewing the latest mission snapshot
- inspecting mission metrics
- viewing a recent event feed
- applying interventions
- clearer separation between mission state and operator actions
- subtle live refresh behavior while the run is active

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
- step summaries with cleaner timeline-oriented layout

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
- links back to replay and run artifacts
- clearer artifact linkage and cleaner export browsing

## Page Overview

- `Mission Desk`: start-here view with primary actions, quieter status context, and recent mission access
- `New Mission`: guided intake workflow from situation through recommendation and save / compare / launch actions
- `Scenarios`: grouped editor for map, target, drone, sensing, battery, and planner settings
- `Mission Plans`: central workspace for planning context, notes, recommendation snapshot, and downstream links
- `Doctrine Library`: operational presets with intended use, assumptions, risks, and recommended strategies
- `Plan Comparison`: saved candidate analysis workspace with ranked options and tradeoff summaries
- `Recommendations`: decision-support briefing for a selected mission plan
- `Mission Control`: live monitoring page with status, metrics, snapshot, event feed, and interventions
- `Replay`: playback workstation for completed runs
- `Run History`: filterable ledger of mission runs
- `Experiments`: grouped robustness experiments and artifact browsing
- `Reports`: indexed report browser
- `After-Action Review`: operational review center for completed missions

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

## API Coverage

Main route groups:

- `/health`
- `/dashboard/summary`
- `/scenarios`
- `/templates`
- `/library/templates`
- `/plans` with asset-package and mission-intent aware payloads
- `/comparisons`
- `/runs`
- `/experiments`
- `/jobs`
- `/reports`
- `/reviews`
- `/compare-plans`
- `/recommend` with concise recommendation summaries, alternatives, tradeoffs, risks, and technical details
- `/artifacts/{owner_type}/{owner_id}/{artifact_type}`

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
