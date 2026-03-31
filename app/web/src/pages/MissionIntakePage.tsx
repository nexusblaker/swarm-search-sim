import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";

import { api } from "@/api/client";
import type { MissionIntent, RecommendationResponse } from "@/api/types";
import { RecommendationCard } from "@/components/ui/RecommendationCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { InlineHint } from "@/components/ui/InlineHint";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { useInvalidateResources } from "@/api/hooks";
import {
  buildAssetPackage,
  buildIntakeSummary,
  buildPlanPayload,
  buildRecommendationRequest,
  createDefaultMissionIntakeDraft,
  createDroneTypeDraft,
  environmentOptions,
  missionIntentOptions,
  searchAreaOptions,
  stagingLocationOptions,
  timeSinceContactOptions,
  weatherOptions,
  type DroneTypeDraft,
  type EnvironmentType,
  type MissionIntakeDraft,
  type SearchAreaSize,
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

export function MissionIntakePage() {
  const navigate = useNavigate();
  const invalidate = useInvalidateResources();
  const [step, setStep] = useState<StepIndex>(0);
  const [draft, setDraft] = useState<MissionIntakeDraft>(createDefaultMissionIntakeDraft);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<ContinueAction | null>(null);
  const recommendation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.recommend(payload),
  });

  const assetPackage = useMemo(() => buildAssetPackage(draft), [draft]);
  const intakeSummary = useMemo(() => buildIntakeSummary(draft), [draft]);
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
        title="Start a mission in five calm steps"
        description="Capture the situation, define the available fleet, review a concise recommendation, and hand the mission into the existing planning or simulation workflow."
        actions={
          <Link to="/plans" className="secondary-button">
            Open saved missions
          </Link>
        }
      />

      <div className="grid gap-6 xl:grid-cols-[1.08fr_0.92fr]">
        <div className="space-y-6">
          <Panel
            eyebrow="Mission intake"
            title="Mission setup"
            description="The main path keeps only the choices an operator needs for an initial search brief. Technical settings stay tucked away until they are useful."
          >
            <div className="grid gap-3 md:grid-cols-5">
              {stepLabels.map((label, index) => {
                const stepIndex = index as StepIndex;
                const active = step === stepIndex;
                return (
                  <button
                    key={label}
                    type="button"
                    onClick={() => setStep(stepIndex)}
                    className={[
                      "rounded-[22px] border px-4 py-4 text-left transition",
                      active
                        ? "border-accentStrong/60 bg-white/[0.06] text-white"
                        : "border-border bg-surfaceAlt/45 text-muted hover:border-accentStrong/35 hover:text-white",
                    ].join(" ")}
                  >
                    <p className="text-[11px] uppercase tracking-[0.22em]">{`Step ${index + 1}`}</p>
                    <p className="mt-2 text-sm font-semibold">{label}</p>
                  </button>
                );
              })}
            </div>
          </Panel>

          {step === 0 ? (
            <Panel
              eyebrow="Step 1"
              title="Describe the situation"
              description="Keep the first brief high level. The product turns these answers into a practical search setup behind the scenes."
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

                <div className="grid gap-3 md:grid-cols-2">
                  <ChoiceCard
                    label="Last known location available"
                    description="Use a tighter starting search area around the known contact point."
                    selected={draft.lastKnownStatus === "known"}
                    onClick={() => updateDraft((current) => ({ ...current, lastKnownStatus: "known" }))}
                  />
                  <ChoiceCard
                    label="Last known location unknown"
                    description="Start with a broader uncertainty model and wider sweep assumptions."
                    selected={draft.lastKnownStatus === "unknown"}
                    onClick={() => updateDraft((current) => ({ ...current, lastKnownStatus: "unknown" }))}
                  />
                </div>

                <div>
                  <p className="field-label">Search area size</p>
                  <div className="grid gap-3 md:grid-cols-2">
                    {searchAreaOptions.map((option) => (
                      <ChoiceCard
                        key={option.value}
                        label={option.label}
                        description={option.description}
                        selected={draft.searchAreaSize === option.value}
                        onClick={() =>
                          updateDraft((current) => ({ ...current, searchAreaSize: option.value as SearchAreaSize }))
                        }
                      />
                    ))}
                  </div>
                </div>

                <div>
                  <p className="field-label">Environment type</p>
                  <div className="grid gap-3 md:grid-cols-2">
                    {environmentOptions.map((option) => (
                      <ChoiceCard
                        key={option.value}
                        label={option.label}
                        description={option.description}
                        selected={draft.environmentType === option.value}
                        onClick={() =>
                          updateDraft((current) => ({ ...current, environmentType: option.value as EnvironmentType }))
                        }
                      />
                    ))}
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <label>
                    <span className="field-label">Weather</span>
                    <select
                      className="field-input"
                      value={draft.weather}
                      onChange={(event) =>
                        updateDraft((current) => ({ ...current, weather: event.target.value as WeatherType }))
                      }
                    >
                      {weatherOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
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
                </div>

                <details className="rounded-[24px] border border-border bg-surfaceAlt/45 p-5">
                  <summary className="cursor-pointer text-sm font-semibold text-white">Technical details</summary>
                  <p className="mt-3 text-sm leading-6 text-muted">
                    The intake keeps map size, uncertainty radius, and default reserve assumptions behind the scenes so the first brief stays focused on operator language.
                  </p>
                </details>
              </div>
            </Panel>
          ) : null}

          {step === 1 ? (
            <Panel
              eyebrow="Step 2"
              title="Describe the available fleet"
              description="Add a simple package for a uniform fleet or define a mixed fleet with multiple drone types."
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

                <label className="max-w-md">
                  <span className="field-label">Staging location</span>
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
                          <span className="field-label">Endurance (minutes)</span>
                          <input
                            className="field-input"
                            value={asset.maxEnduranceMinutes}
                            onChange={(event) => updateAsset(asset.id, "maxEnduranceMinutes", event.target.value)}
                          />
                        </label>
                        <label>
                          <span className="field-label">Max range (km)</span>
                          <input
                            className="field-input"
                            value={asset.estimatedMaxRangeKm}
                            onChange={(event) => updateAsset(asset.id, "estimatedMaxRangeKm", event.target.value)}
                          />
                        </label>
                        <label>
                          <span className="field-label">Cruise speed (kph)</span>
                          <input
                            className="field-input"
                            value={asset.cruiseSpeedKph}
                            onChange={(event) => updateAsset(asset.id, "cruiseSpeedKph", event.target.value)}
                          />
                        </label>
                        <label>
                          <span className="field-label">Turnaround (minutes)</span>
                          <input
                            className="field-input"
                            value={asset.turnaroundTimeMinutes}
                            onChange={(event) => updateAsset(asset.id, "turnaroundTimeMinutes", event.target.value)}
                          />
                        </label>
                        <label>
                          <span className="field-label">Sensor capability</span>
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
                          <span className="field-label">Thermal capability</span>
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
                          <span className="field-label">Detection proxy</span>
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
              title="Choose the search style"
              description="These choices use operator language and guide the recommendation engine toward the right tradeoffs."
            >
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
              <label className="mt-6 block">
                <span className="field-label">Operator notes</span>
                <textarea
                  className="field-textarea"
                  value={draft.operatorNotes}
                  onChange={(event) => updateDraft((current) => ({ ...current, operatorNotes: event.target.value }))}
                  placeholder="Optional briefing notes, assumptions, handoff details, or special constraints."
                />
              </label>
            </Panel>
          ) : null}

          {step === 3 ? (
            <Panel
              eyebrow="Step 4"
              title="Review the recommended plan"
              description="Generate a short operator-ready summary first. Technical detail stays available below it, but out of the way."
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
              description="The new intake creates a standard mission plan, so the rest of the app keeps working as before."
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

        <div className="space-y-6">
          <Panel
            eyebrow="Mission brief"
            title="Operator summary"
            description="This running summary stays plain-English so the intake never feels like a wall of technical fields."
          >
            <SummaryRow label="Mission" value={draft.missionName} />
            <SummaryRow
              label="Situation"
              value={`${intakeSummary.search_area_size} search, ${draft.environmentType.replace("_", " ")}, ${draft.weather}`}
            />
            <SummaryRow
              label="Last known position"
              value={draft.lastKnownStatus === "known" ? "Known last contact area" : "Unknown, wider initial uncertainty"}
            />
            <SummaryRow label="Time since contact" value={draft.timeSinceContact.replaceAll("_", " ")} />
            <SummaryRow label="Fleet" value={assetPackage.drone_types.length > 1 ? "Mixed fleet package" : "Uniform fleet"} />
            <SummaryRow label="Assets" value={`${intakeSummary.total_drones} drones ready`} />
            <SummaryRow
              label="Search style"
              value={missionIntentOptions.find((option) => option.value === draft.missionIntent)?.label ?? draft.missionIntent}
            />
            <SummaryRow
              label="Staging"
              value={stagingLocationOptions.find((option) => option.value === draft.stagingLocation)?.label ?? ""}
            />
          </Panel>

          <Panel
            eyebrow="Fleet package"
            title="Asset package snapshot"
            description="Mixed-fleet support stays visible here without cluttering the main step flow."
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
          </Panel>

          <details className="panel-surface p-6">
            <summary className="cursor-pointer text-sm font-semibold text-white">Technical details</summary>
            <div className="mt-4 space-y-2 text-sm leading-6 text-muted">
              <p>The intake builds a standard mission scenario payload and stores the asset package with the mission plan.</p>
              <p>Recommendations remain deterministic and explainable. The simulation core still runs on aggregated fleet assumptions where needed.</p>
            </div>
          </details>
        </div>
      </div>
    </div>
  );
}
