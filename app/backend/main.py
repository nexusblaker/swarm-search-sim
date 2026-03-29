"""FastAPI entrypoint for the product backend."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.backend.api import (
    artifacts,
    comparisons,
    decision_support,
    experiments,
    health,
    jobs,
    library,
    plans,
    reports,
    reviews,
    runs,
    scenarios,
    templates,
)
from app.backend.core.settings import BackendSettings
from app.backend.services import ProductBackend


def create_app(settings: BackendSettings | None = None) -> FastAPI:
    app = FastAPI(
        title="Swarm Mission Decision Support API",
        version="0.7.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.backend = ProductBackend(settings or BackendSettings.from_env())
    for router in (
        health.router,
        artifacts.router,
        scenarios.router,
        templates.router,
        library.router,
        plans.router,
        runs.router,
        experiments.router,
        comparisons.router,
        jobs.router,
        reports.router,
        reviews.router,
        decision_support.router,
    ):
        app.include_router(router)
    return app


app = create_app()
