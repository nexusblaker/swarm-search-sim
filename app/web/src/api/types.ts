export type ResourceStatus =
  | "queued"
  | "running"
  | "paused"
  | "completed"
  | "failed"
  | "cancelled"
  | "draft"
  | "recommended"
  | "approved"
  | "archived";

export type SummaryRecord = Record<string, unknown>;

export interface BatteryMarginSummary {
  minimum_margin?: number;
  average_margin?: number;
  sustainability?: string;
}

export interface LifecycleHighlight {
  step?: number;
  event_type?: string;
  title?: string;
  summary?: string;
}

export interface BatteryLifecycleSummary {
  run_phase?: string;
  reserve_preset?: string;
  return_to_base_count?: number;
  recharge_started_count?: number;
  recharge_completed_count?: number;
  redeploy_count?: number;
  rejoin_count?: number;
  coverage_gap_count?: number;
  battery_margin_summary?: BatteryMarginSummary;
  asset_utilization_summary?: string;
  mission_continuity_impact?: string;
  highlights?: LifecycleHighlight[];
}

export interface SensingLifecycleSummary {
  candidate_detection_count?: number;
  inspection_initiated_count?: number;
  inspection_pass_count?: number;
  confirmed_detection_count?: number;
  false_positive_count?: number;
  active_candidate_contacts?: number;
  contacts_under_inspection?: number;
  confirmation_pending?: number;
  operator_summary?: string;
  inspection_burden_summary?: string;
  mission_impact_summary?: string;
  highlights?: LifecycleHighlight[];
}

export interface SearchPatternSummary {
  pattern?: string;
  pattern_label?: string;
  base_pattern?: string;
  base_pattern_label?: string;
  summary?: string;
  reason?: string;
  fit_summary?: string;
  rebalanced?: boolean;
  rebalance_reason?: string | null;
  geometry?: Record<string, unknown>;
  mission_effect_summary?: string;
  change_count?: number;
  highlights?: LifecycleHighlight[];
}

export interface TerrainAreaSummary {
  source_mode?: string;
  dominant_terrain?: string;
  terrain_mix?: Record<string, number>;
  elevation_range_m?: [number, number];
  mean_elevation_m?: number;
  slope_burden?: string;
  trail_access?: string;
  trail_coverage_pct?: number;
  obstacle_coverage_pct?: number;
  suggested_scenario_family?: string;
  operator_summary?: string;
}

export interface EnvironmentSummary {
  value?: string;
  label?: string;
  operator_summary?: string;
}

export interface WeatherSummary {
  source?: string;
  provider?: string | null;
  recommended_weather?: string;
  condition_label?: string;
  temperature_c?: number;
  wind_speed_kph?: number;
  precipitation_mm?: number;
  cloud_cover_pct?: number;
  visibility_label?: string;
  operator_summary?: string;
  fallback_note?: string | null;
  fetched_at?: string | null;
}

export interface MissionAreaSummary {
  location_display_name?: string;
  location_source?: string;
  location_query?: string;
  center?: { latitude: number; longitude: number };
  preview_span_km?: number;
  shape_type?: string;
  shape_summary?: string;
  rectangle?: Record<string, number>;
  polygon?: Array<Record<string, number>>;
  bounds?: Record<string, number>;
  width_km?: number;
  height_km?: number;
  area_sq_km?: number;
  shape_ratio?: number;
  requested_grid_resolution_m?: number;
  grid_resolution_m?: number;
  cell_size_m?: number;
  grid_size?: [number, number];
  max_safe_cells?: number;
  warnings?: string[];
  terrain_hint?: string;
  last_known_status?: string;
  environment_label?: string;
  environment_summary?: EnvironmentSummary;
  environment_type?: string;
  last_known_location?: {
    latitude?: number;
    longitude?: number;
    label?: string;
    placement?: string;
    grid_position?: [number, number];
  } | null;
  last_known_summary?: string;
  staging?: {
    latitude?: number;
    longitude?: number;
    label?: string;
    placement?: string;
    grid_position?: [number, number];
  };
  staging_distance_to_center_km?: number;
  last_known_grid_position?: [number, number];
  center_grid_position?: [number, number];
  operator_summary?: string;
  grid_summary?: Record<string, unknown>;
  terrain_summary?: TerrainAreaSummary;
  weather_summary?: WeatherSummary;
}

export interface ResolvedLocation {
  display_name: string;
  latitude: number;
  longitude: number;
  source: string;
  preview_span_km: number;
  terrain_hint?: string;
  fallback_note?: string | null;
  provider?: string | null;
  match_reason?: string | null;
}

export interface LocationSearchResponse {
  items: ResolvedLocation[];
}

export interface DroneStatusSummary {
  id: number;
  operator_status?: string;
  sensing_status?: string;
  assigned_contact_id?: string | null;
  reserve_status_label?: string;
  battery_pct?: number;
  return_service_eta_steps?: number | null;
  contributing_to_search?: boolean;
}

export interface LifecycleSummaryRecord {
  run_phase?: string;
  reserve_preset?: string;
  drone_state_counts?: Record<string, number>;
  active_search_drones?: number;
  returning_drones?: number;
  recharging_drones?: number;
  ready_to_redeploy?: number;
  coverage_gap_active?: boolean;
  coverage_gap_steps?: number;
}

export interface RunSummaryRecord extends SummaryRecord {
  strategy?: string;
  search_pattern?: string;
  search_pattern_label?: string;
  search_pattern_summary?: string;
  search_pattern_reason?: string;
  search_pattern_fit_summary?: string;
  search_pattern_base?: string;
  search_pattern_base_label?: string;
  search_pattern_rebalanced?: boolean;
  search_pattern_rebalance_reason?: string | null;
  search_pattern_geometry?: Record<string, unknown>;
  mission_area?: MissionAreaSummary;
  mission_area_summary?: string;
  scenario_family?: string;
  coordination_mode?: string;
  reserve_preset?: string;
  run_phase?: string;
  metrics?: Record<string, unknown>;
  lifecycle_summary?: LifecycleSummaryRecord;
  sensing_summary?: Record<string, unknown>;
  drone_statuses?: DroneStatusSummary[];
  battery_lifecycle?: BatteryLifecycleSummary;
  sensing_lifecycle?: SensingLifecycleSummary;
}

export interface ReviewTimelineKeyEvent extends Record<string, unknown> {
  step?: number;
  event_type?: string;
  summary?: string;
  details?: Record<string, unknown>;
}

export interface ReviewTimelineRecord extends SummaryRecord {
  key_events?: ReviewTimelineKeyEvent[];
  interventions?: Record<string, unknown>[];
  detection_timeline?: Record<string, unknown>[];
}

export interface ReviewSummaryRecord extends SummaryRecord {
  mission_timeline?: string;
  actual_outcome?: Record<string, unknown>;
  deviation_from_recommendation?: Record<string, unknown>;
  asset_utilization?: Record<string, unknown>;
  battery_lifecycle?: BatteryLifecycleSummary;
  sensing_lifecycle?: SensingLifecycleSummary;
  search_pattern?: SearchPatternSummary;
  mission_area?: MissionAreaSummary;
  battery_comms_risk_summary?: Record<string, unknown>;
  alternate_plan_summary?: Record<string, unknown>;
  links?: Record<string, unknown>;
}

export interface ReportSummaryRecord extends SummaryRecord {
  run_id?: string;
  review_id?: string;
  plan_id?: string | null;
  strategy?: string;
  search_pattern?: SearchPatternSummary;
  search_pattern_label?: string;
  mission_area?: MissionAreaSummary;
  status?: string;
  run_phase?: string;
  battery_lifecycle?: BatteryLifecycleSummary;
  sensing_lifecycle?: SensingLifecycleSummary;
}

export interface CandidateContact {
  id: string;
  position: [number, number];
  status?: string;
  status_label?: string;
  confidence?: number;
  candidate_score?: number;
  cue_step?: number;
  detecting_drone_id?: number | null;
  assigned_drone_id?: number | null;
  inspection_attempts?: number;
  resolved?: boolean;
  outcome?: string | null;
  resolution_step?: number | null;
  note?: string;
}

export type MissionIntent =
  | "broad_area_coverage"
  | "fast_containment"
  | "high_confidence_confirmation"
  | "battery_conservative";

export interface DroneTypeProfile {
  display_name: string;
  model_name?: string | null;
  count: number;
  max_endurance_minutes: number;
  estimated_max_range_km: number;
  cruise_speed_kph: number;
  sensor_capability_level: string;
  thermal_capability_level: string;
  detection_capability_proxy: number;
  turnaround_time_minutes: number;
  notes: string;
}

export interface FleetComposition {
  mix_type: string;
  total_drones: number;
  drone_type_count: number;
  aggregate_endurance_minutes: number;
  aggregate_range_km: number;
  aggregate_speed_kph: number;
  sensor_score: number;
  thermal_score: number;
  detection_score: number;
  endurance_score: number;
  coverage_score: number;
  coordination_complexity: string;
  average_turnaround_minutes: number;
}

export interface AssetPackage {
  package_name: string;
  uniform_fleet: boolean;
  staging_location: string;
  notes: string;
  drone_types: DroneTypeProfile[];
  fleet_composition: FleetComposition;
  operator_summary: string;
}

export interface HealthResponse {
  status: string;
  database_path: string;
  storage_root: string;
}

export interface DashboardActivityRecord {
  id: string;
  kind: string;
  title: string;
  subtitle: string;
  timestamp: number;
  status?: string | null;
  owner_id?: string | null;
}

export interface DashboardSuggestedAction {
  label: string;
  description: string;
  route: string;
}

export interface DashboardSummaryResponse {
  counts: {
    scenarios: number;
    plans: number;
    comparisons: number;
    runs: number;
    reviews: number;
    reports: number;
  };
  active_runs: number;
  completed_runs: number;
  queued_jobs: number;
  backend_status: string;
  recent_runs: RunRecord[];
  recent_reports: ReportRecord[];
  recent_activity: DashboardActivityRecord[];
  suggested_actions: DashboardSuggestedAction[];
}

export interface ScenarioRecord {
  id: string;
  name: string;
  type: string;
  created_at: number;
  updated_at: number;
  deleted_at?: number | null;
  config_json: Record<string, unknown>;
  summary_json: SummaryRecord;
  file_path?: string | null;
}

export interface LibraryTemplateRecord {
  id: string;
  template_id: string;
  name: string;
  family: string;
  doctrine_type: string;
  description: string;
  intended_use: string;
  recommended_strategies_json: string[];
  risks_json: string[];
  assumptions_json: string[];
  tags_json: string[];
  config_json: Record<string, unknown>;
  summary_json: SummaryRecord;
  file_path?: string | null;
}

export interface MissionPlanRecord {
  id: string;
  name: string;
  scenario_id?: string | null;
  template_id?: string | null;
  approval_state: ResourceStatus;
  created_at: number;
  updated_at: number;
  plan_json: Record<string, unknown>;
  summary_json: SummaryRecord;
  recommendation_json: Record<string, unknown>;
  asset_package?: AssetPackage | null;
  mission_intent?: MissionIntent | null;
  intake_summary: Record<string, unknown>;
  operator_notes: string;
  candidate_alternatives_json: Record<string, unknown>[];
  priority_zones_json: Record<string, unknown>[];
  exclusion_zones_json: Record<string, unknown>[];
  latest_comparison_id?: string | null;
  latest_review_id?: string | null;
  linked_run_ids_json: string[];
}

export interface JobRecord {
  id: string;
  job_type: string;
  owner_type: string;
  owner_id: string;
  status: ResourceStatus;
  progress: number;
  created_at: number;
  updated_at: number;
  completed_at?: number | null;
  error?: string | null;
  summary_json: SummaryRecord;
}

export interface RunRecord {
  id: string;
  scenario_id: string;
  plan_id?: string | null;
  comparison_id?: string | null;
  candidate_id?: string | null;
  status: ResourceStatus;
  created_at: number;
  updated_at: number;
  completed_at?: number | null;
  config_json: Record<string, unknown>;
  summary_json: RunSummaryRecord;
  latest_snapshot_json?: Snapshot | null;
  output_dir: string;
  job_id?: string | null;
  artifact_paths: Record<string, string>;
  job?: JobRecord | null;
  interventions: InterventionRecord[];
}

export interface InterventionRecord {
  id?: string | number;
  action?: string;
  payload_json?: Record<string, unknown>;
  created_at?: number;
  [key: string]: unknown;
}

export interface PlanCandidateRecord {
  id: string;
  comparison_id: string;
  name: string;
  rank: number;
  linked_run_id?: string | null;
  config_json: Record<string, unknown>;
  summary_json: SummaryRecord;
}

export interface PlanComparisonRecord {
  id: string;
  plan_id?: string | null;
  name: string;
  status: ResourceStatus;
  created_at: number;
  updated_at: number;
  completed_at?: number | null;
  request_json: Record<string, unknown>;
  summary_json: Record<string, unknown>[];
  recommendation_json: Record<string, unknown>;
  uncertainty_json: Record<string, unknown>;
  sensitivity_json: Record<string, unknown>;
  linked_run_ids_json: string[];
  report_id?: string | null;
  job_id?: string | null;
  candidates: PlanCandidateRecord[];
}

export interface ExperimentRecord {
  id: string;
  status: ResourceStatus;
  created_at: number;
  updated_at: number;
  completed_at?: number | null;
  request_json: Record<string, unknown>;
  summary_json: Record<string, unknown>[] | Record<string, unknown>;
  output_dir: string;
  job_id?: string | null;
  error?: string | null;
  artifact_paths: Record<string, string>;
  job?: JobRecord | null;
}

export interface ReportRecord {
  id: string;
  run_id: string;
  owner_type: string;
  owner_id?: string | null;
  report_type: string;
  created_at: number;
  summary_json: ReportSummaryRecord;
  file_path: string;
}

export interface AfterActionReviewRecord {
  id: string;
  run_id: string;
  plan_id?: string | null;
  comparison_id?: string | null;
  name: string;
  created_at: number;
  updated_at: number;
  summary_json: ReviewSummaryRecord;
  timeline_json: ReviewTimelineRecord;
  alternate_plan_json: Record<string, unknown>;
  report_id?: string | null;
  report?: ReportRecord | null;
}

export interface ComparePlansResponse {
  ranked_plans: Record<string, unknown>[];
  top_recommendation: Record<string, unknown>;
  confidence_summary: Record<string, unknown>;
  uncertainty_summary: Record<string, unknown>;
  sensitivity_summary: Record<string, unknown>;
}

export interface RecommendationResponse {
  recommended_strategy?: string | null;
  recommended_search_pattern?: string | null;
  recommended_search_pattern_label?: string | null;
  search_pattern_summary?: string | null;
  search_pattern_reason?: string | null;
  search_pattern_fit_summary?: string | null;
  recommended_drone_count?: number | null;
  recommended_return_threshold?: number | null;
  risk_summary: Record<string, unknown>;
  uncertainty_summary: Record<string, unknown>;
  explanation: string;
  concise_summary: string;
  top_alternative_summary?: string | null;
  key_tradeoffs: string[];
  key_risks: string[];
  team_coordination_label?: string | null;
  asset_package?: AssetPackage | null;
  technical_details: Record<string, unknown>;
  recommendation_snapshot: Record<string, unknown>;
  candidate_plans: Record<string, unknown>[];
}

export interface MissionAreaPreviewResponse {
  mission_area: MissionAreaSummary;
}

export interface SnapshotDrone {
  id: number;
  position: [number, number];
  battery: number;
  battery_pct?: number;
  path_history: [number, number][];
  planned_path: [number, number][];
  intended_target?: [number, number] | null;
  comms_online: boolean;
  returning_to_base: boolean;
  stale_steps: number;
  lifecycle_state?: string;
  operator_status?: string;
  sensing_state?: string;
  sensing_status?: string;
  assigned_contact_id?: string | null;
  active_contact_position?: [number, number] | null;
  reserve_status?: string;
  reserve_status_label?: string;
  reserve_reason?: string;
  energy_required_to_base?: number;
  reserve_required?: number;
  continue_margin_required?: number;
  battery_margin?: number;
  return_eta_steps?: number | null;
  return_service_eta_steps?: number | null;
  turnaround_remaining_steps?: number;
  sorties_completed?: number;
  recharge_cycles?: number;
  redeployments?: number;
  investigations_started?: number;
  contacts_confirmed?: number;
  contacts_rejected?: number;
  contributing_to_search?: boolean;
}

export interface Snapshot {
  step: number;
  done: boolean;
  paused: boolean;
  weather: string;
  strategy: string;
  mission_area?: MissionAreaSummary;
  last_known_position?: [number, number];
  last_known_status?: string;
  search_pattern?: string;
  search_pattern_label?: string;
  search_pattern_summary?: string;
  search_pattern_reason?: string;
  search_pattern_fit_summary?: string;
  search_pattern_base?: string;
  search_pattern_base_label?: string;
  search_pattern_rebalanced?: boolean;
  search_pattern_rebalance_reason?: string | null;
  search_pattern_geometry?: Record<string, unknown>;
  coordination_mode: string;
  run_phase?: string;
  base_position: [number, number];
  terrain_grid: number[][];
  obstacle_mask: boolean[][];
  probability_map: number[][];
  target_position: [number, number];
  target_detected: boolean;
  visited_cells: [number, number][];
  searched_cells: [number, number][];
  last_searched_cells: [number, number][];
  communication_links: [[number, number], [number, number]][];
  reserved_paths: Record<string, [number, number][]>;
  global_objectives: Record<string, [number, number]>;
  active_search_drones?: number[];
  lifecycle_summary?: LifecycleSummaryRecord;
  sensing_summary?: Record<string, unknown>;
  candidate_contacts?: CandidateContact[];
  detection_event?: Record<string, unknown> | null;
  drones: SnapshotDrone[];
  metrics: Record<string, unknown>;
}
