import type {
  AssetPackage,
  MissionAreaSummary,
  MissionIntent,
  RecommendationResponse,
  ResolvedLocation,
  WeatherSummary,
} from "@/api/types";

export type LastKnownStatus = "known" | "unknown";
export type SearchAreaSize = "small" | "medium" | "large" | "very_large";
export type EnvironmentType =
  | "open_terrain"
  | "mixed_terrain"
  | "dense_forest"
  | "obstacle_heavy"
  | "poor_comms";
export type WeatherType = "clear" | "windy" | "rain" | "storm";
export type TimeSinceContact = "under_1h" | "one_to_three_h" | "three_to_eight_h" | "over_eight_h";
export type StagingLocation = "north_base" | "south_base" | "east_base" | "west_base" | "central_base";
export type SensorCapabilityLevel = "basic" | "standard" | "enhanced" | "advanced";
export type ThermalCapabilityLevel = "none" | "assisted" | "full";
export type SearchPatternChoice =
  | "auto"
  | "broad_area_sweep"
  | "sector_split"
  | "expanding_ring"
  | "perimeter_containment"
  | "adaptive_rebalance";

const SEARCH_PATTERN_CHOICES: SearchPatternChoice[] = [
  "auto",
  "broad_area_sweep",
  "sector_split",
  "expanding_ring",
  "perimeter_containment",
  "adaptive_rebalance",
];

export interface DroneTypeDraft {
  id: string;
  displayName: string;
  count: string;
  maxEnduranceMinutes: string;
  estimatedMaxRangeKm: string;
  cruiseSpeedKph: string;
  sensorCapabilityLevel: SensorCapabilityLevel;
  thermalCapabilityLevel: ThermalCapabilityLevel;
  detectionCapabilityProxy: string;
  turnaroundTimeMinutes: string;
  notes: string;
}

export interface MissionIntakeDraft {
  missionName: string;
  locationQuery: string;
  resolvedLocation: ResolvedLocation | null;
  missionArea: MissionAreaSummary | null;
  weatherSummary: WeatherSummary | null;
  lastKnownLocation: MissionAreaSummary["last_known_location"] | null;
  gridResolutionMeters: string;
  lastKnownStatus: LastKnownStatus;
  searchAreaSize: SearchAreaSize;
  environmentType: EnvironmentType;
  weather: WeatherType;
  timeSinceContact: TimeSinceContact;
  allDronesSame: boolean;
  stagingLocation: StagingLocation;
  assets: DroneTypeDraft[];
  missionIntent: MissionIntent;
  searchPattern: SearchPatternChoice;
  operatorNotes: string;
}

export const missionIntentOptions: Array<{ value: MissionIntent; label: string; description: string }> = [
  {
    value: "broad_area_coverage",
    label: "Broad area coverage",
    description: "Cover the search box quickly and keep the team moving.",
  },
  {
    value: "fast_containment",
    label: "Fast containment",
    description: "Move quickly to reduce escape routes and tighten the search window.",
  },
  {
    value: "high_confidence_confirmation",
    label: "High-confidence confirmation",
    description: "Spend more effort confirming likely detections before moving on.",
  },
  {
    value: "battery_conservative",
    label: "Battery-conservative search",
    description: "Protect reserve margins for longer missions and re-tasking.",
  },
];

export const searchPatternOptions: Array<{ value: SearchPatternChoice; label: string; description: string }> = [
  {
    value: "auto",
    label: "Let the system recommend",
    description: "Choose the strongest pattern from the mission area, uncertainty, fleet, and reserve profile.",
  },
  {
    value: "broad_area_sweep",
    label: "Broad Area Sweep",
    description: "Evenly spaced lanes for wide-area early coverage when the location is uncertain.",
  },
  {
    value: "sector_split",
    label: "Sector Split",
    description: "Divide the search box into sectors so the fleet can work in parallel.",
  },
  {
    value: "expanding_ring",
    label: "Expanding Ring",
    description: "Start near the last known area and grow outward over time.",
  },
  {
    value: "perimeter_containment",
    label: "Perimeter Containment",
    description: "Prioritize the outer boundary when containment matters most.",
  },
  {
    value: "adaptive_rebalance",
    label: "Adaptive Rebalance",
    description: "Start structured, then shift toward clues, inspections, and thinner coverage.",
  },
];

export const searchAreaOptions: Array<{ value: SearchAreaSize; label: string; description: string }> = [
  { value: "small", label: "Small", description: "Under 5 km²" },
  { value: "medium", label: "Medium", description: "5 to 20 km²" },
  { value: "large", label: "Large", description: "20 to 60 km²" },
  { value: "very_large", label: "Very large", description: "More than 60 km²" },
];

export const environmentOptions: Array<{ value: EnvironmentType; label: string; description: string }> = [
  { value: "open_terrain", label: "Open terrain", description: "Clear lines of sight and faster coverage." },
  { value: "mixed_terrain", label: "Mixed terrain", description: "Balanced obstacles, vegetation, and open ground." },
  { value: "dense_forest", label: "Dense forest", description: "Slower coverage with higher confirmation demand." },
  { value: "obstacle_heavy", label: "Obstacle-heavy", description: "Urban edges, ridges, or complex ground features." },
  { value: "poor_comms", label: "Poor communications", description: "Patchy links and distributed coordination." },
];

export const weatherOptions: Array<{ value: WeatherType; label: string }> = [
  { value: "clear", label: "Clear" },
  { value: "windy", label: "Windy" },
  { value: "rain", label: "Rain" },
  { value: "storm", label: "Storm" },
];

export const timeSinceContactOptions: Array<{ value: TimeSinceContact; label: string; description: string }> = [
  { value: "under_1h", label: "Under 1 hour", description: "Tighter initial uncertainty." },
  { value: "one_to_three_h", label: "1 to 3 hours", description: "Moderate drift from the last contact area." },
  { value: "three_to_eight_h", label: "3 to 8 hours", description: "Broader spread likely." },
  { value: "over_eight_h", label: "Over 8 hours", description: "Large uncertainty and longer mission pacing." },
];

export const stagingLocationOptions: Array<{ value: StagingLocation; label: string }> = [
  { value: "south_base", label: "Southern base" },
  { value: "north_base", label: "Northern base" },
  { value: "east_base", label: "Eastern base" },
  { value: "west_base", label: "Western base" },
  { value: "central_base", label: "Central base" },
];

const AREA_PRESETS: Record<SearchAreaSize, { mapSize: [number, number]; maxSteps: number }> = {
  small: { mapSize: [12, 10], maxSteps: 28 },
  medium: { mapSize: [18, 14], maxSteps: 40 },
  large: { mapSize: [24, 18], maxSteps: 52 },
  very_large: { mapSize: [30, 22], maxSteps: 64 },
};

const TIME_PRESETS: Record<TimeSinceContact, { targetStartRadius: number; driftSigma: number; moveProbability: number }> = {
  under_1h: { targetStartRadius: 2, driftSigma: 3.4, moveProbability: 0.25 },
  one_to_three_h: { targetStartRadius: 4, driftSigma: 5.0, moveProbability: 0.34 },
  three_to_eight_h: { targetStartRadius: 6, driftSigma: 6.8, moveProbability: 0.4 },
  over_eight_h: { targetStartRadius: 8, driftSigma: 8.4, moveProbability: 0.48 },
};

const ENVIRONMENT_PRESETS: Record<EnvironmentType, { targetBehavior: string; coordinationMode: string }> = {
  open_terrain: { targetBehavior: "terrain_biased", coordinationMode: "centralized" },
  mixed_terrain: { targetBehavior: "terrain_biased", coordinationMode: "centralized" },
  dense_forest: { targetBehavior: "terrain_biased", coordinationMode: "centralized" },
  obstacle_heavy: { targetBehavior: "trail_biased", coordinationMode: "centralized" },
  poor_comms: { targetBehavior: "terrain_biased", coordinationMode: "decentralized" },
};

const DEFAULT_STRATEGY_BY_INTENT: Record<MissionIntent, string> = {
  broad_area_coverage: "sector_search",
  fast_containment: "auction_based",
  high_confidence_confirmation: "information_gain",
  battery_conservative: "probability_greedy",
};

const DEFAULT_RESERVE_BY_INTENT: Record<MissionIntent, number> = {
  broad_area_coverage: 28,
  fast_containment: 24,
  high_confidence_confirmation: 30,
  battery_conservative: 34,
};

export const assetFieldHelpText: Record<string, string> = {
  maxEnduranceMinutes: "Estimated battery life or total usable flight time for one sortie.",
  estimatedMaxRangeKm: "Estimated maximum practical distance the drone can travel in one sortie.",
  cruiseSpeedKph: "Typical transit speed used for planning broad search timing and return pacing.",
  turnaroundTimeMinutes:
    "Estimated time needed after return to base before the drone can launch again, including battery swap, recharge, or basic servicing.",
  sensorCapabilityLevel: "Overall sensing quality for broad search, cueing, and follow-up inspection work.",
  thermalCapabilityLevel: "How well the drone supports thermal search, especially in low-visibility or cooler conditions.",
  detectionCapabilityProxy: "Simple planning multiplier for how readily this drone can generate useful target clues.",
};

export function createDroneTypeDraft(id: string, overrides?: Partial<DroneTypeDraft>): DroneTypeDraft {
  return {
    id,
    displayName: "General purpose drone",
    count: "4",
    maxEnduranceMinutes: "120",
    estimatedMaxRangeKm: "14",
    cruiseSpeedKph: "42",
    sensorCapabilityLevel: "standard",
    thermalCapabilityLevel: "assisted",
    detectionCapabilityProxy: "1.0",
    turnaroundTimeMinutes: "18",
    notes: "",
    ...overrides,
  };
}

export function createDefaultMissionIntakeDraft(): MissionIntakeDraft {
  return {
    missionName: "New search mission",
    locationQuery: "",
    resolvedLocation: null,
    missionArea: null,
    weatherSummary: null,
    lastKnownLocation: null,
    gridResolutionMeters: "500",
    lastKnownStatus: "unknown",
    searchAreaSize: "medium",
    environmentType: "mixed_terrain",
    weather: "clear",
    timeSinceContact: "one_to_three_h",
    allDronesSame: true,
    stagingLocation: "south_base",
    assets: [createDroneTypeDraft("asset-1")],
    missionIntent: "broad_area_coverage",
    searchPattern: "auto",
    operatorNotes: "",
  };
}

function toNumber(value: string, fallback: number): number {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
}

function normalizeSearchPatternChoice(value: string | null | undefined): SearchPatternChoice {
  if (!value) {
    return "auto";
  }
  return SEARCH_PATTERN_CHOICES.includes(value as SearchPatternChoice) ? (value as SearchPatternChoice) : "auto";
}

export function deriveSearchAreaSize(areaSqKm: number | null | undefined): SearchAreaSize {
  if (!areaSqKm || areaSqKm <= 0) {
    return "medium";
  }
  if (areaSqKm < 5) {
    return "small";
  }
  if (areaSqKm < 20) {
    return "medium";
  }
  if (areaSqKm < 60) {
    return "large";
  }
  return "very_large";
}

function totalDroneCount(assets: DroneTypeDraft[]): number {
  return assets.reduce((total, asset) => total + Math.max(1, toNumber(asset.count, 1)), 0);
}

function stagingLocationLabel(stagingLocation: StagingLocation): string {
  return stagingLocationOptions.find((option) => option.value === stagingLocation)?.label ?? "Southern base";
}

function stagingPosition(stagingLocation: StagingLocation, mapSize: [number, number]): [number, number] {
  const [width, height] = mapSize;
  const centerX = Math.floor(width / 2);
  const centerY = Math.floor(height / 2);
  switch (stagingLocation) {
    case "north_base":
      return [centerX, 1];
    case "east_base":
      return [width - 2, centerY];
    case "west_base":
      return [1, centerY];
    case "central_base":
      return [centerX, centerY];
    case "south_base":
    default:
      return [centerX, height - 2];
  }
}

export function buildAssetPackage(draft: MissionIntakeDraft): AssetPackage {
  return {
    package_name: `${draft.missionName} fleet`,
    uniform_fleet: draft.allDronesSame,
    staging_location: draft.missionArea?.staging?.label ?? stagingLocationLabel(draft.stagingLocation),
    notes: "",
    operator_summary: "",
    fleet_composition: {
      mix_type: draft.allDronesSame ? "uniform" : "mixed",
      total_drones: totalDroneCount(draft.assets),
      drone_type_count: draft.assets.length,
      aggregate_endurance_minutes: 0,
      aggregate_range_km: 0,
      aggregate_speed_kph: 0,
      sensor_score: 0,
      thermal_score: 0,
      detection_score: 0,
      endurance_score: 0,
      coverage_score: 0,
      coordination_complexity: draft.allDronesSame ? "low" : "moderate",
      average_turnaround_minutes: 0,
    },
    drone_types: draft.assets.map((asset) => ({
      display_name: asset.displayName,
      model_name: asset.displayName,
      count: Math.max(1, toNumber(asset.count, 1)),
      max_endurance_minutes: Math.max(20, toNumber(asset.maxEnduranceMinutes, 120)),
      estimated_max_range_km: Math.max(1, toNumber(asset.estimatedMaxRangeKm, 14)),
      cruise_speed_kph: Math.max(10, toNumber(asset.cruiseSpeedKph, 42)),
      sensor_capability_level: asset.sensorCapabilityLevel,
      thermal_capability_level: asset.thermalCapabilityLevel,
      detection_capability_proxy: Math.max(0.6, toNumber(asset.detectionCapabilityProxy, 1.0)),
      turnaround_time_minutes: Math.max(5, toNumber(asset.turnaroundTimeMinutes, 18)),
      notes: asset.notes,
    })),
  };
}

export function buildMissionScenario(draft: MissionIntakeDraft) {
  const areaPreset = AREA_PRESETS[draft.searchAreaSize];
  const timePreset = TIME_PRESETS[draft.timeSinceContact];
  const environmentPreset = ENVIRONMENT_PRESETS[draft.environmentType];
  const missionArea = draft.missionArea ?? undefined;
  const mapSize = (missionArea?.grid_size as [number, number] | undefined) ?? areaPreset.mapSize;
  const basePosition =
    (missionArea?.staging?.grid_position as [number, number] | undefined) ?? stagingPosition(draft.stagingLocation, mapSize);
  const center: [number, number] =
    (missionArea?.center_grid_position as [number, number] | undefined) ??
    [Math.floor(mapSize[0] / 2), Math.floor(mapSize[1] / 2)];
  const lastKnownPosition: [number, number] =
    (missionArea?.last_known_grid_position as [number, number] | undefined) ?? center;
  const uncertaintyOffset = draft.lastKnownStatus === "unknown" ? 2 : 0;
  const scenarioFamily =
    (missionArea?.terrain_summary?.suggested_scenario_family as string | undefined) ?? draft.environmentType;
  const maxSteps = missionArea
    ? Math.max(areaPreset.maxSteps, Math.round((mapSize[0] + mapSize[1]) * 1.6))
    : areaPreset.maxSteps;

  return {
    scenario: {
      name: draft.missionName,
      map_size: mapSize,
      weather: draft.weather,
      num_drones: totalDroneCount(draft.assets),
      last_known_position: draft.lastKnownStatus === "known" ? lastKnownPosition : center,
      target_assumptions: {
        behavior: environmentPreset.targetBehavior,
        target_move_probability: Number((timePreset.moveProbability + (uncertaintyOffset * 0.04)).toFixed(2)),
        target_speed: draft.timeSinceContact === "over_eight_h" ? 2 : 1,
        drift_sigma: Number((timePreset.driftSigma + uncertaintyOffset).toFixed(1)),
      },
      target_start_radius: timePreset.targetStartRadius + uncertaintyOffset,
      max_steps: maxSteps,
      strategy: DEFAULT_STRATEGY_BY_INTENT[draft.missionIntent],
      search_pattern: draft.searchPattern,
      scenario_family: scenarioFamily,
      last_known_status: draft.lastKnownStatus,
      base_position: basePosition,
      mission_area: missionArea,
      communication: {
        coordination_mode: environmentPreset.coordinationMode,
      },
      battery_policy: {
        return_threshold: DEFAULT_RESERVE_BY_INTENT[draft.missionIntent],
      },
      render: {
        save_frames: false,
        frame_stride: 3,
      },
      mission_intent: draft.missionIntent,
    },
  };
}

export function buildRecommendationRequest(draft: MissionIntakeDraft) {
  return {
    scenario: buildMissionScenario(draft),
    asset_package: buildAssetPackage(draft),
    mission_intent: draft.missionIntent,
    search_pattern: draft.searchPattern,
    num_seeds: 1,
  };
}

export function buildIntakeSummary(draft: MissionIntakeDraft) {
  return {
    mission_name: draft.missionName,
    location_display_name: draft.missionArea?.location_display_name ?? draft.resolvedLocation?.display_name ?? "",
    last_known_status: draft.lastKnownStatus,
    search_area_size: draft.searchAreaSize,
    environment_type: draft.missionArea?.environment_summary?.label ?? draft.environmentType,
    weather: draft.weather,
    weather_summary: draft.weatherSummary?.operator_summary,
    time_since_contact: draft.timeSinceContact,
    mission_intent: draft.missionIntent,
    search_pattern_preference: draft.searchPattern,
    staging_location: draft.missionArea?.staging?.label ?? stagingLocationLabel(draft.stagingLocation),
    area_sq_km: draft.missionArea?.area_sq_km,
    area_metrics_summary: draft.missionArea?.area_metrics_summary,
    grid_resolution_m: draft.missionArea?.grid_resolution_m ?? Number(draft.gridResolutionMeters),
    grid_rows: draft.missionArea?.grid_rows ?? draft.missionArea?.area_metrics?.grid_rows,
    grid_cols: draft.missionArea?.grid_cols ?? draft.missionArea?.area_metrics?.grid_cols,
    mission_area_summary: draft.missionArea?.context_summary ?? draft.missionArea?.operator_summary,
    terrain_burden_summary: draft.missionArea?.terrain_burden_summary,
    slope_elevation_summary: draft.missionArea?.slope_elevation_summary,
    planner_status_summary: draft.missionArea?.planner_status_summary,
    last_known_summary: draft.missionArea?.last_known_summary,
    total_drones: totalDroneCount(draft.assets),
    mixed_fleet: !draft.allDronesSame,
  };
}

export function buildPlanPayload(draft: MissionIntakeDraft, recommendation?: RecommendationResponse) {
  const scenario = buildMissionScenario(draft);
  const topRecommendation = recommendation?.recommendation_snapshot["top_recommendation"] as
    | Record<string, unknown>
    | undefined;
  const selectedPattern: SearchPatternChoice =
    draft.searchPattern === "auto"
      ? normalizeSearchPatternChoice(recommendation?.recommended_search_pattern)
      : draft.searchPattern;
  scenario.scenario.search_pattern = selectedPattern;
  return {
    name: draft.missionName,
    scenario,
    asset_package: buildAssetPackage(draft),
    map_selection: draft.missionArea ?? undefined,
    mission_intent: draft.missionIntent,
    search_pattern: selectedPattern,
    intake_summary: buildIntakeSummary(draft),
    operator_notes: draft.operatorNotes,
    approval_state: "draft",
    strategy: recommendation?.recommended_strategy ?? DEFAULT_STRATEGY_BY_INTENT[draft.missionIntent],
    num_drones: recommendation?.recommended_drone_count ?? totalDroneCount(draft.assets),
    reserve_policy: {
      return_threshold: recommendation?.recommended_return_threshold ?? DEFAULT_RESERVE_BY_INTENT[draft.missionIntent],
    },
    communication_assumptions: {
      coordination_mode: topRecommendation?.coordination_mode ?? ENVIRONMENT_PRESETS[draft.environmentType].coordinationMode,
    },
    recommendation_snapshot: recommendation,
    candidate_alternatives: recommendation?.candidate_plans?.slice(1, 3) ?? [],
  };
}
