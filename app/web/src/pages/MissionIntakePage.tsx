import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";

import { api } from "@/api/client";
import type { MissionIntent, ResolvedLocation, WeatherSummary } from "@/api/types";
import { MissionAreaPlanner } from "@/components/mission/MissionAreaPlanner";
import { CollapsiblePanel } from "@/components/ui/CollapsiblePanel";
import { EmptyState } from "@/components/ui/EmptyState";
import { FieldHelp } from "@/components/ui/FieldHelp";
import { InlineHint } from "@/components/ui/InlineHint";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { RecommendationCard } from "@/components/ui/RecommendationCard";
import { useInvalidateResources } from "@/api/hooks";
import { cn } from "@/lib/cn";
import {
  buildAssetPackage,
  buildIntakeSummary,
  buildPlanPayload,
  buildRecommendationRequest,
  createDefaultMissionIntakeDraft,
  createDroneTypeDraft,
  deriveSearchAreaSize,
  environmentOptions,
  missionIntentOptions,
  searchPatternOptions,
  assetFieldHelpText,
  stagingLocationOptions,
  timeSinceContactOptions,
  weatherOptions,
  type DroneTypeDraft,
  type EnvironmentType,
  type MissionIntakeDraft,
  type SearchPatternChoice,
  type StagingLocation,
  type TimeSinceContact,
  type WeatherType,
} from "@/features/intake";

const stepLabels = ["Situation", "Assets", "Search style", "Recommendation", "Continue"] as const;
type StepIndex = 0 | 1 | 2 | 3 | 4;
type ContinueAction = "save" | "compare" | "launch";

function previousStep(step: StepIndex): StepIndex {
  return (step === 0 ? 0 : step - 1) as StepIndex;
}

function nextStep(step: StepIndex): StepIndex {
  return (step === 4 ? 4 : step + 1) as StepIndex;
}

function ChoiceCard({
  label,
  description,
  selected,
  onClick,
}: {
  label: string;
  description: string;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "rounded-[24px] border p-5 text-left transition",
        selected
          ? "border-accentStrong/60 bg-white/[0.06] shadow-soft"
          : "border-border bg-surfaceAlt/50 hover:border-accentStrong/35 hover:bg-surfaceAlt/75",
      ].join(" ")}
    >
      <p className="text-base font-semibold text-white">{label}</p>
      <p className="mt-2 text-sm leading-6 text-muted">{description}</p>
    </button>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4 py-2.5">
      <p className="text-sm text-muted">{label}</p>
      <p className="text-right text-sm font-medium text-white">{value}</p>
    </div>
  );
}

function FieldLabelWithHelp({ label, help }: { label: string; help?: string }) {
  return (
    <span className="field-label inline-flex items-center gap-2">
      <span>{label}</span>
      {help ? <FieldHelp text={help} /> : null}
    </span>
  );
}

export function MissionIntakePage() {
  const navigate = useNavigate();
  const invalidate = useInvalidateResources();
  const [step, setStep] = useState<StepIndex>(0);
  const [draft, setDraft] = useState<MissionIntakeDraft>(createDefaultMissionIntakeDraft);
  const [locationSuggestions, setLocationSuggestions] = useState<ResolvedLocation[]>([]);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<ContinueAction | null>(null);
  const recommendation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.recommend(payload),
  });
  const resolveLocation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.resolveLocation(payload),
  });
  const areaPreview = useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.previewMissionArea(payload),
  });
  const weatherLookup = useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.weather(payload),
  });

  const assetPackage = useMemo(() => buildAssetPackage(draft), [draft]);
  const intakeSummary = useMemo(() => buildIntakeSummary(draft), [draft]);
  const missionAreaLabel = draft.missionArea?.area_sq_km ? `${draft.missionArea.area_sq_km.toFixed(1)} km²` : "Draw on map";
  const environmentLabel =
    draft.missionArea?.environment_summary?.label ??
    environmentOptions.find((option) => option.value === draft.environmentType)?.label ??
    "Pending";
  const terrainBurdenLabel =
    draft.missionArea?.terrain_summary?.terrain_burden_label ??
    draft.missionArea?.environment_summary?.label ??
    "Pending";
  const terrainBurdenSummary =
    draft.missionArea?.terrain_burden_summary ??
    draft.missionArea?.terrain_summary?.operator_summary ??
    "Terrain burden will derive from the mission area once the search box is set.";
  const slopeLabel =
    draft.missionArea?.slope_summary?.label ??
    draft.missionArea?.slope_elevation_summary ??
    "Pending";
  const weatherLabel =
    draft.weatherSummary?.condition_label ??
    weatherOptions.find((option) => option.value === draft.weather)?.label ??
    "Pending";
  const lastKnownLabel =
    draft.lastKnownStatus === "known"
      ? draft.missionArea?.last_known_location
        ? "Placed on map"
        : "Placement needed"
      : "Unknown";
  const missionContextSummary =
    draft.missionArea?.context_summary ??
    draft.missionArea?.operator_summary ??
    "Draw the mission area to let the system derive the search context automatically.";
  const plannerStatusLabel =
    draft.missionArea?.planner_status_summary ??
    "Planning context will show up here once the mission area, staging point, and weather are set.";
  const gridSummaryLabel = String(
    draft.missionArea?.grid_summary?.operator_summary ?? "Grid summary will appear after the search area is drawn.",
  );
  const canAdvance = step < 4;
  const hasRecommendation = Boolean(recommendation.data);

  function updateDraft(next: MissionIntakeDraft | ((current: MissionIntakeDraft) => MissionIntakeDraft)) {
    setDraft((current) => {
      const updated = typeof next === "function" ? next(current) : next;
      return updated;
    });
    setSaveError(null);
    recommendation.reset();
  }

  useEffect(() => {
    const query = draft.locationQuery.trim();
    if (query.length < 2) {
      setLocationSuggestions([]);
      return;
    }
    const timeout = window.setTimeout(async () => {
      try {
        const response = await api.searchLocations({ query, limit: 5 });
        setLocationSuggestions(response.items);
      } catch {
        setLocationSuggestions([]);
      }
    }, 220);
    return () => window.clearTimeout(timeout);
  }, [draft.locationQuery]);

  async function refreshMissionArea(
    nextDraft: MissionIntakeDraft,
    overrides?: {
      resolvedLocation?: MissionIntakeDraft["resolvedLocation"];
      rectangle?: Record<string, number>;
      staging?: Record<string, unknown>;
      lastKnownLocation?: Record<string, unknown> | null;
      weatherSummary?: WeatherSummary | null;
    },
  ) {
    const resolvedLocation = overrides?.resolvedLocation ?? nextDraft.resolvedLocation;
    if (!resolvedLocation) {
      return;
    }
    const weatherSummary = overrides?.weatherSummary ?? nextDraft.weatherSummary ?? undefined;
    const lastKnownLocation =
      nextDraft.lastKnownStatus === "known"
        ? overrides?.lastKnownLocation ?? nextDraft.lastKnownLocation ?? nextDraft.missionArea?.last_known_location ?? undefined
        : undefined;
    const preview = await areaPreview.mutateAsync({
      location: resolvedLocation,
      rectangle: overrides?.rectangle ?? nextDraft.missionArea?.rectangle ?? undefined,
      grid_resolution_m: Number(nextDraft.gridResolutionMeters) || 500,
      staging: overrides?.staging ?? nextDraft.missionArea?.staging ?? undefined,
      last_known_location: lastKnownLocation,
      weather_summary: weatherSummary ?? undefined,
      last_known_status: nextDraft.lastKnownStatus,
      environment_type: nextDraft.environmentType,
      weather: nextDraft.weather,
    });
    const derivedEnvironment = (preview.mission_area.environment_type as EnvironmentType | undefined) ?? nextDraft.environmentType;
    const derivedWeather = (weatherSummary?.recommended_weather as WeatherType | undefined) ?? nextDraft.weather;
    setDraft((current) => ({
      ...current,
      resolvedLocation,
      missionArea: preview.mission_area,
      weatherSummary: weatherSummary ?? current.weatherSummary,
      lastKnownLocation: (preview.mission_area.last_known_location as MissionIntakeDraft["lastKnownLocation"] | undefined) ?? current.lastKnownLocation,
      searchAreaSize: deriveSearchAreaSize(Number(preview.mission_area.area_sq_km ?? current.missionArea?.area_sq_km ?? 0)),
      environmentType: derivedEnvironment,
      weather: derivedWeather,
      gridResolutionMeters: String(Math.round(Number(preview.mission_area.grid_resolution_m ?? nextDraft.gridResolutionMeters))),
    }));
    recommendation.reset();
  }

  async function loadWeatherForLocation(resolved: ResolvedLocation): Promise<WeatherSummary> {
    try {
      return await weatherLookup.mutateAsync({
        latitude: resolved.latitude,
        longitude: resolved.longitude,
      });
    } catch {
      return {
        source: "manual",
        recommended_weather: draft.weather,
        condition_label: "Manual weather",
        temperature_c: 0,
        wind_speed_kph: 0,
        precipitation_mm: 0,
        cloud_cover_pct: 0,
        visibility_label: "Good",
        operator_summary: "Weather lookup was unavailable. Review and set mission weather manually if needed.",
        fallback_note: "Weather service unavailable during setup.",
      };
    }
  }

  async function applyResolvedLocation(resolved: ResolvedLocation) {
    const weatherSummary = await loadWeatherForLocation(resolved);
    const recommendedWeather = (weatherSummary.recommended_weather as WeatherType | undefined) ?? draft.weather;
    const nextDraft = {
      ...draft,
      resolvedLocation: resolved,
      weatherSummary,
      weather: recommendedWeather,
    };
    setDraft((current) => ({
      ...current,
      resolvedLocation: resolved,
      weatherSummary,
      weather: recommendedWeather,
      locationQuery: resolved.display_name,
    }));
    setLocationSuggestions([]);
    recommendation.reset();
    await refreshMissionArea(nextDraft, {
      resolvedLocation: resolved,
      weatherSummary,
    });
  }

  async function handleResolveLocation() {
    setSaveError(null);
    try {
      const resolved = await resolveLocation.mutateAsync({ query: draft.locationQuery });
      await applyResolvedLocation(resolved);
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Unable to resolve the selected location.");
    }
  }

  function updateAsset(id: string, field: keyof DroneTypeDraft, value: string) {
    updateDraft((current) => ({
      ...current,
      assets: current.assets.map((asset) => (asset.id === id ? { ...asset, [field]: value } : asset)),
    }));
  }

  async function handleContinue(action: ContinueAction) {
    setPendingAction(action);
    setSaveError(null);
    try {
      const plan = await api.createPlan(buildPlanPayload(draft, recommendation.data));
      if (action === "compare") {
        await api.createComparison({ plan_id: plan.id, num_seeds: 1 });
      }
      if (action === "launch") {
        await api.launchRun({ plan_id: plan.id });
      }
      await invalidate();
      navigate(action === "save" ? "/plans" : action === "compare" ? "/comparisons" : "/mission-control");
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Unable to continue from mission intake.");
    } finally {
      setPendingAction(null);
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Guided setup"
        title="Build a new mission in five guided steps"
        description="Describe the situation, define the available fleet, review the recommended plan, and continue into the existing mission workflow without getting pulled into technical setup."
        actions={
          <div className="flex flex-wrap gap-3">
            <span className="pill">{`Step ${step + 1} of ${stepLabels.length}`}</span>
            <Link to="/plans" className="ghost-button">
              Open saved missions
            </Link>
          </div>
        }
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-6">
          <div className="panel-surface p-5 md:p-6">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="section-kicker">Mission intake</p>
                <h2 className="mt-2 text-[26px] font-semibold text-white">{stepLabels[step]}</h2>
                <p className="mt-2 text-sm leading-6 text-muted">
                  Complete the current step, then continue when you are ready.
                </p>
              </div>
              <div className="grid gap-2 sm:grid-cols-5 md:max-w-[540px]">
                {stepLabels.map((label, index) => {
                  const stepIndex = index as StepIndex;
                  const active = step === stepIndex;
                  const complete = step > stepIndex;
                  return (
                    <button
                      key={label}
                      type="button"
                      onClick={() => setStep(stepIndex)}
                      className={cn(
                        "rounded-[18px] border px-3 py-3 text-left transition duration-150",
                        active
                          ? "border-accentStrong/55 bg-white/[0.07] text-white"
                          : complete
                            ? "border-border/80 bg-surfaceAlt/55 text-white/90 hover:bg-white/[0.06]"
                            : "border-border bg-surfaceAlt/40 text-muted hover:border-accentStrong/30 hover:text-white",
                      )}
                    >
                      <p className="text-[10px] uppercase tracking-[0.18em]">{`Step ${index + 1}`}</p>
                      <p className="mt-1.5 text-sm font-semibold">{label}</p>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {step === 0 ? (
            <Panel
              eyebrow="Step 1"
              title="Describe the situation"
              description="Start with the mission location and search area, then keep the rest of the brief high level. The product will translate this into a practical search setup behind the scenes."
            >
              <div className="grid gap-6">
                <div>
                  <label className="field-label" htmlFor="mission-name">
                    Mission name
                  </label>
                  <input
                    id="mission-name"
                    className="field-input"
                    value={draft.missionName}
                    onChange={(event) => updateDraft((current) => ({ ...current, missionName: event.target.value }))}
                    placeholder="North ridge daylight search"
                  />
                </div>

                <div className="rounded-[26px] border border-border bg-surfaceAlt/45 p-5">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <p className="section-kicker">Mission location</p>
                      <h3 className="mt-1 text-lg font-semibold text-white">Set the real search area</h3>
                      <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
                        Search by place name or paste coordinates. The map centers on the selected location, then lets you draw the mission box, place the base, and add the last known point when it matters.
                      </p>
                    </div>
                    {draft.resolvedLocation ? <span className="pill">{draft.resolvedLocation.source.replaceAll("_", " ")}</span> : null}
                  </div>
                  <div className="mt-5 grid gap-4 xl:grid-cols-[minmax(0,1fr)_220px]">
                    <div className="space-y-3">
                      <label className="block">
                        <span className="field-label">Search by place name or coordinates</span>
                        <input
                          className="field-input"
                          value={draft.locationQuery}
                          onChange={(event) => updateDraft((current) => ({ ...current, locationQuery: event.target.value }))}
                          placeholder="Katoomba, NSW or -33.7126, 150.3119"
                        />
                      </label>
                      {locationSuggestions.length > 0 ? (
                        <div className="rounded-[22px] border border-border/70 bg-[#08111b]/95 p-2 shadow-soft">
                          {locationSuggestions.map((suggestion) => (
                            <button
                              key={`${suggestion.display_name}-${suggestion.latitude}-${suggestion.longitude}`}
                              type="button"
                              className="flex w-full items-start justify-between gap-3 rounded-[18px] px-3 py-3 text-left transition hover:bg-white/[0.05]"
                              onClick={() => void applyResolvedLocation(suggestion)}
                            >
                              <div>
                                <p className="text-sm font-semibold text-white">{suggestion.display_name}</p>
                                <p className="mt-1 text-xs leading-5 text-muted">
                                  {suggestion.match_reason ?? suggestion.source.replaceAll("_", " ")}
                                </p>
                              </div>
                              <span className="pill whitespace-nowrap">{suggestion.source.replaceAll("_", " ")}</span>
                            </button>
                          ))}
                        </div>
                      ) : null}
                    </div>
                    <div className="flex items-end">
                      <button type="button" className="primary-button w-full" onClick={() => void handleResolveLocation()}>
                        {resolveLocation.isPending || areaPreview.isPending || weatherLookup.isPending ? "Centering map..." : "Center map"}
                      </button>
                    </div>
                  </div>
                  {draft.resolvedLocation?.fallback_note ? (
                    <p className="mt-3 text-sm leading-6 text-muted">{draft.resolvedLocation.fallback_note}</p>
                  ) : null}
                  {draft.resolvedLocation ? (
                    <div className="mt-5 space-y-4">
                      <MissionAreaPlanner
                        location={draft.resolvedLocation}
                        missionArea={draft.missionArea}
                        isUpdating={areaPreview.isPending}
                        showLastKnownPlacement={draft.lastKnownStatus === "known"}
                        onRectangleChange={(rectangle) => {
                          const nextDraft = { ...draft };
                          void refreshMissionArea(nextDraft, { rectangle });
                        }}
                        onStagingChange={(point) => {
                          const nextDraft = { ...draft };
                          void refreshMissionArea(nextDraft, { staging: point });
                        }}
                        onLastKnownChange={(point) => {
                          const nextDraft = { ...draft, lastKnownLocation: point };
                          updateDraft(nextDraft);
                          void refreshMissionArea(nextDraft, { lastKnownLocation: point });
                        }}
                      />

                      {draft.missionArea ? (
                        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px]">
                          <div className="rounded-[24px] border border-border/70 bg-surfaceAlt/45 p-5">
                            <p className="section-kicker">Mission area briefing</p>
                            <p className="mt-3 text-base leading-7 text-white">{missionContextSummary}</p>
                            <div className="mt-4 grid gap-3 sm:grid-cols-2">
                              <div className="rounded-[18px] border border-border/60 bg-black/10 p-3">
                                <p className="text-[11px] uppercase tracking-[0.14em] text-muted">Environment</p>
                                <p className="mt-2 text-sm font-medium text-white">{environmentLabel}</p>
                              </div>
                              <div className="rounded-[18px] border border-border/60 bg-black/10 p-3">
                                <p className="text-[11px] uppercase tracking-[0.14em] text-muted">Terrain burden</p>
                                <p className="mt-2 text-sm font-medium text-white">{terrainBurdenLabel}</p>
                              </div>
                              <div className="rounded-[18px] border border-border/60 bg-black/10 p-3">
                                <p className="text-[11px] uppercase tracking-[0.14em] text-muted">Slope burden</p>
                                <p className="mt-2 text-sm font-medium text-white">{slopeLabel}</p>
                              </div>
                              <div className="rounded-[18px] border border-border/60 bg-black/10 p-3">
                                <p className="text-[11px] uppercase tracking-[0.14em] text-muted">Planner status</p>
                                <p className="mt-2 text-sm font-medium text-white">
                                  {draft.missionArea.planner_ready ? "Ready to plan" : "Needs attention"}
                                </p>
                              </div>
                            </div>
                            <p className="mt-4 text-sm leading-6 text-muted">{terrainBurdenSummary}</p>
                            {draft.missionArea.slope_elevation_summary ? (
                              <p className="mt-3 text-sm leading-6 text-muted">{draft.missionArea.slope_elevation_summary}</p>
                            ) : null}
                            {draft.missionArea.warnings?.length ? (
                              <div className="mt-4 space-y-2">
                                {draft.missionArea.warnings.map((warning) => (
                                  <p key={warning} className="text-sm leading-6 text-[#ffcf99]">
                                    {warning}
                                  </p>
                                ))}
                              </div>
                            ) : null}
                          </div>
                          <div className="rounded-[24px] border border-border/70 bg-surfaceAlt/45 p-5">
                            <p className="section-kicker">Grid and placement</p>
                            <label className="mt-4 block">
                              <span className="field-label">Cell resolution</span>
                              <select
                                className="field-input"
                                value={draft.gridResolutionMeters}
                                onChange={(event) => {
                                  const nextDraft = { ...draft, gridResolutionMeters: event.target.value };
                                  updateDraft(nextDraft);
                                  if (nextDraft.resolvedLocation) {
                                    void refreshMissionArea(nextDraft);
                                  }
                                }}
                              >
                                {["250", "400", "500", "750", "1000"].map((option) => (
                                  <option key={option} value={option}>
                                    {option} m cells
                                  </option>
                                ))}
                              </select>
                            </label>
                            <div className="mt-4 space-y-2 text-sm leading-6 text-muted">
                              <p>{draft.missionArea.area_metrics_summary ?? missionAreaLabel}</p>
                              <p>{gridSummaryLabel}</p>
                              <p>{draft.missionArea.staging_summary ?? "Base summary pending."}</p>
                              <p>{draft.missionArea.last_known_summary ?? "No last known point is being used for this mission."}</p>
                              <p>
                                {draft.weatherSummary?.operator_summary ??
                                  "Current weather becomes the starting mission condition and can still be overridden."}
                              </p>
                              <p>{plannerStatusLabel}</p>
                            </div>
                          </div>
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                  {saveError ? <p className="mt-4 text-sm text-[#ffb4a2]">{saveError}</p> : null}
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <ChoiceCard
                    label="Last known location available"
                    description="Use a tighter starting search area around the known contact point."
                    selected={draft.lastKnownStatus === "known"}
                    onClick={() => {
                      const nextDraft = { ...draft, lastKnownStatus: "known" as const };
                      updateDraft(nextDraft);
                      if (nextDraft.resolvedLocation) {
                        void refreshMissionArea(nextDraft);
                      }
                    }}
                  />
                  <ChoiceCard
                    label="Last known location unknown"
                    description="Start with a broader uncertainty model and wider sweep assumptions."
                    selected={draft.lastKnownStatus === "unknown"}
                    onClick={() => {
                      const nextDraft = { ...draft, lastKnownStatus: "unknown" as const, lastKnownLocation: null };
                      updateDraft(nextDraft);
                      if (nextDraft.resolvedLocation) {
                        void refreshMissionArea(nextDraft, { lastKnownLocation: null });
                      }
                    }}
                  />
                </div>
                {draft.lastKnownStatus === "known" ? (
                  <InlineHint>
                    Place the last known point on the map to tighten pattern selection and starting search geometry.
                  </InlineHint>
                ) : null}

                {draft.missionArea ? (
                  <div className="rounded-[22px] border border-border/70 bg-surfaceAlt/45 p-4">
                    <p className="section-kicker">Auto-derived mission context</p>
                    <p className="mt-3 text-sm leading-6 text-white">{missionContextSummary}</p>
                    <p className="mt-2 text-sm leading-6 text-muted">
                      {draft.weatherSummary?.operator_summary ??
                        "Area size, terrain character, and weather are being derived from the selected map area."}
                    </p>
                    <p className="mt-2 text-sm leading-6 text-muted">{plannerStatusLabel}</p>
                  </div>
                ) : (
                  <InlineHint>
                    Resolve a location first. Area size, terrain character, and weather will then auto-fill from the selected mission area.
                  </InlineHint>
                )}

                <label>
                  <span className="field-label">Time since last contact</span>
                  <select
                    className="field-input"
                    value={draft.timeSinceContact}
                    onChange={(event) =>
                      updateDraft((current) => ({
                        ...current,
                        timeSinceContact: event.target.value as TimeSinceContact,
                      }))
                    }
                  >
                    {timeSinceContactOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>

                <CollapsiblePanel
                  title="Override derived mission context"
                  description="Adjust weather or environment only when the imported area needs a manual correction."
                  defaultOpen={false}
                  className="border-none bg-transparent shadow-none"
                  headerClassName="rounded-[24px] border border-border bg-surfaceAlt/45"
                >
                  <div className="grid gap-4 md:grid-cols-2">
                    <label>
                      <span className="field-label">Environment override</span>
                      <select
                        className="field-input"
                        value={draft.environmentType}
                        onChange={(event) => {
                          const nextDraft = { ...draft, environmentType: event.target.value as EnvironmentType };
                          updateDraft(nextDraft);
                          if (nextDraft.resolvedLocation) {
                            void refreshMissionArea(nextDraft);
                          }
                        }}
                      >
                        {environmentOptions.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      <span className="field-label">Weather override</span>
                      <select
                        className="field-input"
                        value={draft.weather}
                        onChange={(event) => {
                          const nextDraft = { ...draft, weather: event.target.value as WeatherType };
                          updateDraft(nextDraft);
                          if (nextDraft.resolvedLocation) {
                            void refreshMissionArea(nextDraft, {
                              weatherSummary: {
                                ...(draft.weatherSummary ?? {}),
                                recommended_weather: event.target.value,
                                condition_label: draft.weatherSummary?.condition_label ?? event.target.value,
                                source: draft.weatherSummary?.source ?? "manual",
                              },
                            });
                          }
                        }}
                      >
                        {weatherOptions.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>
                </CollapsiblePanel>

                <CollapsiblePanel
                  title="Advanced area details"
                  description="Open coordinates and grid assumptions only when you need them."
                  defaultOpen={false}
                  className="border-none bg-transparent shadow-none"
                  headerClassName="rounded-[24px] border border-border bg-surfaceAlt/45"
                >
                  <div className="space-y-2 text-sm leading-6 text-muted">
                    <p>Resolved location: {draft.resolvedLocation?.display_name ?? "Not set"}</p>
                    <p>Center: {draft.resolvedLocation ? `${draft.resolvedLocation.latitude.toFixed(4)}, ${draft.resolvedLocation.longitude.toFixed(4)}` : "Not set"}</p>
                    <p>Grid resolution: {draft.missionArea?.grid_resolution_m ?? draft.gridResolutionMeters} m</p>
                    <p>Map size: {draft.missionArea?.grid_size?.[0] ?? "n/a"} x {draft.missionArea?.grid_size?.[1] ?? "n/a"} cells</p>
                    <p>Terrain burden: {terrainBurdenLabel}</p>
                    <p>Slope burden: {slopeLabel}</p>
                  </div>
                </CollapsiblePanel>
              </div>
            </Panel>
          ) : null}

          {step === 1 ? (
            <Panel
              eyebrow="Step 2"
              title="Describe the available fleet"
              description="Use a single profile for a uniform fleet or add multiple drone types for a mixed package."
            >
              <div className="space-y-6">
                <div className="grid gap-3 md:grid-cols-2">
                  <ChoiceCard
                    label="All drones are the same"
                    description="Enter one drone profile and a total count."
                    selected={draft.allDronesSame}
                    onClick={() =>
                      updateDraft((current) => ({
                        ...current,
                        allDronesSame: true,
                        assets: [current.assets[0] ?? createDroneTypeDraft("asset-1")],
                      }))
                    }
                  />
                  <ChoiceCard
                    label="Mixed fleet"
                    description="Combine multiple drone types with different endurance, range, and sensors."
                    selected={!draft.allDronesSame}
                    onClick={() =>
                      updateDraft((current) => ({
                        ...current,
                        allDronesSame: false,
                        assets:
                          current.assets.length > 1
                            ? current.assets
                            : [
                                current.assets[0] ?? createDroneTypeDraft("asset-1"),
                                createDroneTypeDraft("asset-2", {
                                  displayName: "Long-endurance drone",
                                  count: "2",
                                  maxEnduranceMinutes: "160",
                                  estimatedMaxRangeKm: "20",
                                  cruiseSpeedKph: "55",
                                  sensorCapabilityLevel: "enhanced",
                                  thermalCapabilityLevel: "full",
                                  detectionCapabilityProxy: "1.15",
                                }),
                              ],
                      }))
                    }
                  />
                </div>

                {draft.missionArea ? (
                  <div className="rounded-[24px] border border-border/70 bg-surfaceAlt/45 p-4">
                    <p className="section-kicker">Staging point</p>
                    <p className="mt-2 text-sm font-medium text-white">
                      {draft.missionArea.staging?.label ?? "Primary staging point"}
                    </p>
                    <p className="mt-2 text-sm leading-6 text-muted">
                      Base position is tied to the selected mission area and will drive return-to-base and redeploy behaviour.
                    </p>
                  </div>
                ) : (
                  <label className="max-w-md">
                    <span className="field-label">Fallback staging location</span>
                    <select
                      className="field-input"
                      value={draft.stagingLocation}
                      onChange={(event) =>
                        updateDraft((current) => ({
                          ...current,
                          stagingLocation: event.target.value as StagingLocation,
                        }))
                      }
                    >
                      {stagingLocationOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                )}

                <div className="space-y-4">
                  {draft.assets.map((asset, index) => (
                    <div key={asset.id} className="rounded-[26px] border border-border bg-surfaceAlt/45 p-5">
                      <div className="mb-4 flex items-center justify-between gap-4">
                        <div>
                          <p className="section-kicker">Drone type {index + 1}</p>
                          <h3 className="mt-1 text-lg font-semibold text-white">{asset.displayName}</h3>
                        </div>
                        {!draft.allDronesSame && draft.assets.length > 1 ? (
                          <button
                            type="button"
                            className="ghost-button"
                            onClick={() =>
                              updateDraft((current) => ({
                                ...current,
                                assets: current.assets.filter((item) => item.id !== asset.id),
                              }))
                            }
                          >
                            Remove
                          </button>
                        ) : null}
                      </div>
                      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                        <label>
                          <span className="field-label">Display name</span>
                          <input
                            className="field-input"
                            value={asset.displayName}
                            onChange={(event) => updateAsset(asset.id, "displayName", event.target.value)}
                          />
                        </label>
                        <label>
                          <span className="field-label">Count</span>
                          <input
                            className="field-input"
                            value={asset.count}
                            onChange={(event) => updateAsset(asset.id, "count", event.target.value)}
                          />
                        </label>
                        <label>
                          <FieldLabelWithHelp label="Endurance (minutes)" help={assetFieldHelpText.maxEnduranceMinutes} />
                          <input
                            className="field-input"
                            value={asset.maxEnduranceMinutes}
                            onChange={(event) => updateAsset(asset.id, "maxEnduranceMinutes", event.target.value)}
                          />
                        </label>
                        <label>
                          <FieldLabelWithHelp label="Max range (km)" help={assetFieldHelpText.estimatedMaxRangeKm} />
                          <input
                            className="field-input"
                            value={asset.estimatedMaxRangeKm}
                            onChange={(event) => updateAsset(asset.id, "estimatedMaxRangeKm", event.target.value)}
                          />
                        </label>
                        <label>
                          <FieldLabelWithHelp label="Cruise speed (kph)" help={assetFieldHelpText.cruiseSpeedKph} />
                          <input
                            className="field-input"
                            value={asset.cruiseSpeedKph}
                            onChange={(event) => updateAsset(asset.id, "cruiseSpeedKph", event.target.value)}
                          />
                        </label>
                        <label>
                          <FieldLabelWithHelp label="Turnaround (minutes)" help={assetFieldHelpText.turnaroundTimeMinutes} />
                          <input
                            className="field-input"
                            value={asset.turnaroundTimeMinutes}
                            onChange={(event) => updateAsset(asset.id, "turnaroundTimeMinutes", event.target.value)}
                          />
                        </label>
                      </div>
                      <div className="mt-4">
                        <CollapsiblePanel
                          title="Advanced asset details"
                          description="Open sensor detail, detection strength, and notes only when they matter."
                          defaultOpen={false}
                          className="border-border bg-surfaceAlt/30"
                        >
                          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                            <label>
                              <FieldLabelWithHelp label="Sensor capability" help={assetFieldHelpText.sensorCapabilityLevel} />
                              <select
                                className="field-input"
                                value={asset.sensorCapabilityLevel}
                                onChange={(event) => updateAsset(asset.id, "sensorCapabilityLevel", event.target.value)}
                              >
                                {["basic", "standard", "enhanced", "advanced"].map((option) => (
                                  <option key={option} value={option}>
                                    {option}
                                  </option>
                                ))}
                              </select>
                            </label>
                            <label>
                              <FieldLabelWithHelp label="Thermal capability" help={assetFieldHelpText.thermalCapabilityLevel} />
                              <select
                                className="field-input"
                                value={asset.thermalCapabilityLevel}
                                onChange={(event) => updateAsset(asset.id, "thermalCapabilityLevel", event.target.value)}
                              >
                                {["none", "assisted", "full"].map((option) => (
                                  <option key={option} value={option}>
                                    {option}
                                  </option>
                                ))}
                              </select>
                            </label>
                            <label>
                              <FieldLabelWithHelp label="Detection proxy" help={assetFieldHelpText.detectionCapabilityProxy} />
                              <input
                                className="field-input"
                                value={asset.detectionCapabilityProxy}
                                onChange={(event) => updateAsset(asset.id, "detectionCapabilityProxy", event.target.value)}
                              />
                            </label>
                          </div>
                          <label className="mt-4 block">
                            <span className="field-label">Notes</span>
                            <textarea
                              className="field-textarea"
                              value={asset.notes}
                              onChange={(event) => updateAsset(asset.id, "notes", event.target.value)}
                            />
                          </label>
                        </CollapsiblePanel>
                      </div>
                    </div>
                  ))}
                </div>

                {!draft.allDronesSame ? (
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() =>
                      updateDraft((current) => ({
                        ...current,
                        assets: [...current.assets, createDroneTypeDraft(`asset-${current.assets.length + 1}`)],
                      }))
                    }
                  >
                    Add another drone type
                  </button>
                ) : null}

                <InlineHint>
                  Mixed fleets are stored at the product layer and folded into the recommendation briefing without forcing a simulation-core rewrite.
                </InlineHint>
              </div>
            </Panel>
          ) : null}

          {step === 2 ? (
            <Panel
              eyebrow="Step 3"
              title="Set the search intent and pattern"
              description="Choose the operational intent first, then either let the system recommend the search layout or guide it toward a preferred pattern."
            >
              <div className="space-y-6">
                <div>
                  <p className="field-label">Search intent</p>
                  <div className="grid gap-3 md:grid-cols-2">
                    {missionIntentOptions.map((option) => (
                      <ChoiceCard
                        key={option.value}
                        label={option.label}
                        description={option.description}
                        selected={draft.missionIntent === option.value}
                        onClick={() =>
                          updateDraft((current) => ({ ...current, missionIntent: option.value as MissionIntent }))
                        }
                      />
                    ))}
                  </div>
                </div>

                <div>
                  <p className="field-label">Search pattern</p>
                  <div className="grid gap-3 md:grid-cols-2">
                    {searchPatternOptions.map((option) => (
                      <ChoiceCard
                        key={option.value}
                        label={option.label}
                        description={option.description}
                        selected={draft.searchPattern === option.value}
                        onClick={() =>
                          updateDraft((current) => ({
                            ...current,
                            searchPattern: option.value as SearchPatternChoice,
                          }))
                        }
                      />
                    ))}
                  </div>
                  <p className="mt-3 text-sm leading-6 text-muted">
                    Automatic selection is recommended for first use. The recommendation briefing will still explain why the chosen layout fits.
                  </p>
                </div>

                <label className="block">
                  <span className="field-label">Operator notes</span>
                  <textarea
                    className="field-textarea"
                    value={draft.operatorNotes}
                    onChange={(event) => updateDraft((current) => ({ ...current, operatorNotes: event.target.value }))}
                    placeholder="Optional briefing notes, assumptions, handoff details, or special constraints."
                  />
                </label>
              </div>
            </Panel>
          ) : null}

          {step === 3 ? (
            <Panel
              eyebrow="Step 4"
              title="Review the recommended plan"
              description="Generate a concise recommendation first. The visible result should read like a decision briefing, not a settings dump."
              actions={
                <button
                  type="button"
                  className="primary-button"
                  onClick={() => recommendation.mutate(buildRecommendationRequest(draft))}
                >
                  {recommendation.isPending ? "Generating recommendation..." : "Generate recommendation"}
                </button>
              }
            >
              {recommendation.data ? (
                <RecommendationCard
                  strategy={recommendation.data.recommended_strategy}
                  searchPattern={recommendation.data.recommended_search_pattern}
                  searchPatternLabel={recommendation.data.recommended_search_pattern_label}
                  searchPatternSummary={recommendation.data.search_pattern_summary}
                  searchPatternReason={recommendation.data.search_pattern_reason}
                  searchPatternFitSummary={recommendation.data.search_pattern_fit_summary}
                  drones={recommendation.data.recommended_drone_count}
                  reserveThreshold={recommendation.data.recommended_return_threshold}
                  explanation={recommendation.data.explanation}
                  conciseSummary={recommendation.data.concise_summary}
                  topAlternativeSummary={recommendation.data.top_alternative_summary}
                  keyTradeoffs={recommendation.data.key_tradeoffs}
                  keyRisks={recommendation.data.key_risks}
                  teamCoordinationLabel={recommendation.data.team_coordination_label}
                  assetPackage={recommendation.data.asset_package}
                  riskSummary={recommendation.data.risk_summary}
                  uncertaintySummary={recommendation.data.uncertainty_summary}
                  technicalDetails={recommendation.data.technical_details}
                />
              ) : (
                <EmptyState
                  title="No recommendation yet"
                  body="Use the mission setup from the previous steps to generate a concise operator briefing."
                />
              )}
            </Panel>
          ) : null}

          {step === 4 ? (
            <Panel
              eyebrow="Step 5"
              title="Continue into the mission workflow"
              description="The guided intake creates a standard mission plan, so the rest of the workflow keeps working as before."
            >
              <div className="grid gap-3 md:grid-cols-3">
                <button
                  type="button"
                  className="primary-button"
                  disabled={!hasRecommendation || pendingAction !== null}
                  onClick={() => handleContinue("save")}
                >
                  {pendingAction === "save" ? "Saving..." : "Save draft"}
                </button>
                <button
                  type="button"
                  className="secondary-button"
                  disabled={!hasRecommendation || pendingAction !== null}
                  onClick={() => handleContinue("compare")}
                >
                  {pendingAction === "compare" ? "Preparing..." : "Save and compare"}
                </button>
                <button
                  type="button"
                  className="secondary-button"
                  disabled={!hasRecommendation || pendingAction !== null}
                  onClick={() => handleContinue("launch")}
                >
                  {pendingAction === "launch" ? "Launching..." : "Save and launch simulation"}
                </button>
              </div>
              {!hasRecommendation ? (
                <InlineHint>Generate the recommendation first so the saved plan includes the briefing summary.</InlineHint>
              ) : null}
              {saveError ? <p className="mt-4 text-sm text-[#ffb4a2]">{saveError}</p> : null}
            </Panel>
          ) : null}

          <div className="flex flex-wrap items-center justify-between gap-3">
            <button
              type="button"
              className="secondary-button"
              disabled={step === 0}
              onClick={() => setStep((current) => previousStep(current))}
            >
              Back
            </button>
            {canAdvance ? (
              <button
                type="button"
                className="primary-button"
                onClick={() => setStep((current) => nextStep(current))}
              >
                Continue
              </button>
            ) : null}
          </div>
        </div>

        <aside className="space-y-4 xl:sticky xl:top-[7.5rem] xl:self-start">
          <div className="panel-subtle p-5">
            <p className="section-kicker">Mission summary</p>
            <p className="mt-3 text-lg font-semibold text-white">{draft.missionName}</p>
            <div className="mt-4 divide-y divide-border/60">
              <SummaryRow label="Location" value={draft.missionArea?.location_display_name ?? draft.resolvedLocation?.display_name ?? "Not set"} />
              <SummaryRow label="Area profile" value={environmentLabel} />
              <SummaryRow label="Mission area" value={missionAreaLabel} />
              <SummaryRow label="Terrain" value={terrainBurdenLabel} />
              <SummaryRow label="Weather" value={weatherLabel} />
              <SummaryRow label="Last known position" value={lastKnownLabel} />
              <SummaryRow label="Fleet" value={assetPackage.drone_types.length > 1 ? "Mixed fleet" : "Uniform fleet"} />
              <SummaryRow label="Assets ready" value={`${intakeSummary.total_drones} drones`} />
              <SummaryRow
                label="Search style"
                value={missionIntentOptions.find((option) => option.value === draft.missionIntent)?.label ?? draft.missionIntent}
              />
              <SummaryRow
                label="Pattern"
                value={searchPatternOptions.find((option) => option.value === draft.searchPattern)?.label ?? "Let the system recommend"}
              />
              <SummaryRow label="Grid" value={draft.missionArea?.grid_size ? `${draft.missionArea.grid_size[0]} x ${draft.missionArea.grid_size[1]}` : "Pending"} />
              <SummaryRow label="Planner" value={draft.missionArea?.planner_ready ? "Ready" : "In progress"} />
            </div>
          </div>

          <div className="panel-subtle p-5">
            <p className="section-kicker">Quick actions</p>
            <div className="mt-4 space-y-3">
              <Link to="/plans" className="secondary-button w-full">
                Open saved missions
              </Link>
              <Link to="/library" className="ghost-button w-full">
                Explore sample missions
              </Link>
            </div>
          </div>

          <CollapsiblePanel
            title="Fleet package"
            description="Open a compact view of the current asset package."
            defaultOpen={step === 1}
          >
            <div className="space-y-3">
              {assetPackage.drone_types.map((asset, index) => (
                <div key={`${asset.display_name}-${index}`} className="rounded-[22px] border border-border bg-surfaceAlt/45 p-4">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="text-sm font-semibold text-white">{asset.display_name}</p>
                      <p className="mt-1 text-sm leading-6 text-muted">
                        {asset.count} available, {asset.max_endurance_minutes} min endurance, {asset.estimated_max_range_km} km range
                      </p>
                    </div>
                    <span className="pill whitespace-nowrap">{asset.sensor_capability_level}</span>
                  </div>
                </div>
              ))}
            </div>
          </CollapsiblePanel>

          <CollapsiblePanel
            title="Technical details"
            description="Open the product-layer notes behind this mission intake."
            defaultOpen={false}
          >
            <div className="space-y-2 text-sm leading-6 text-muted">
              <p>The intake builds a standard mission scenario payload and stores the asset package with the mission plan.</p>
              <p>Recommendations remain deterministic and explainable. The simulation core still runs on aggregated fleet assumptions where needed.</p>
            </div>
          </CollapsiblePanel>
        </aside>
      </div>
    </div>
  );
}
