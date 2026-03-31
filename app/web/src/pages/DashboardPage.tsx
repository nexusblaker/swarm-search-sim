import { Link } from "react-router-dom";

import { useDashboardSummary, useLibraryTemplates, usePlans } from "@/api/hooks";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { Panel } from "@/components/ui/Panel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatTimestamp } from "@/lib/format";

function QuietMetric({ label, value, hint }: { label: string; value: string | number; hint: string }) {
  return (
    <div className="rounded-[24px] border border-border/70 bg-surfaceAlt/40 p-4">
      <p className="text-[11px] uppercase tracking-[0.2em] text-muted">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
      <p className="mt-2 text-sm leading-6 text-muted">{hint}</p>
    </div>
  );
}

export function DashboardPage() {
  const dashboard = useDashboardSummary();
  const plansQuery = usePlans();
  const templatesQuery = useLibraryTemplates();

  if (dashboard.isLoading || plansQuery.isLoading || templatesQuery.isLoading) {
    return <LoadingState label="Preparing mission desk..." />;
  }
  if (dashboard.error) return <ErrorState message={(dashboard.error as Error).message} />;
  if (plansQuery.error) return <ErrorState message={(plansQuery.error as Error).message} />;
  if (templatesQuery.error) return <ErrorState message={(templatesQuery.error as Error).message} />;
  if (!dashboard.data) {
    return <EmptyState title="Mission desk unavailable" body="The operator home screen could not load yet." />;
  }

  const recentPlans = plansQuery.data?.items.slice(0, 3) ?? [];
  const sampleMissions = templatesQuery.data?.items.slice(0, 3) ?? [];

  return (
    <div className="page-stack">
      <section className="panel-surface overflow-hidden px-6 py-8 lg:px-8 lg:py-10">
        <div className="grid gap-8 xl:grid-cols-[1.18fr_0.82fr]">
          <div>
            <p className="section-kicker">Welcome back</p>
            <h1 className="mt-3 max-w-3xl text-[34px] font-semibold leading-tight text-white md:text-[42px]">
              Mission desk for search planning, simulation, and review
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-8 text-muted">
              Start a new mission, reopen a saved one, or explore a sample setup. The first steps stay focused on operator choices instead of technical configuration.
            </p>

            <div className="mt-8 grid gap-4 md:grid-cols-2">
              <Link to="/mission-intake" className="hero-button">
                <span className="section-kicker text-[#101317]/70">Primary action</span>
                <span className="mt-2 block text-xl font-semibold">Start a New Mission</span>
                <span className="mt-3 block text-sm leading-6 text-[#26303b]">
                  Use the guided intake to describe the situation, define the fleet, and receive a recommended plan summary.
                </span>
              </Link>
              <Link to="/plans" className="hero-button hero-button-secondary">
                <span className="section-kicker">Primary action</span>
                <span className="mt-2 block text-xl font-semibold text-white">Open an Existing Mission</span>
                <span className="mt-3 block text-sm leading-6 text-muted">
                  Return to a saved mission plan, comparison, or active workflow without hunting through multiple pages.
                </span>
              </Link>
            </div>

            <div className="mt-4 flex flex-wrap gap-3">
              <Link to="/library" className="secondary-button">
                Explore Sample Missions
              </Link>
              <Link to="/recommendations" className="ghost-button">
                Open latest plan brief
              </Link>
            </div>
          </div>

          <div className="space-y-4">
            <div className="rounded-[28px] border border-border/70 bg-white/[0.04] p-5">
              <p className="section-kicker">Start here</p>
              <div className="mt-4 space-y-3">
                {[
                  "1. Start a new mission or reopen an existing one.",
                  "2. Capture the situation and available drones.",
                  "3. Review the recommended plan summary.",
                  "4. Continue to saved plans, mission options, or simulation.",
                ].map((line) => (
                  <div key={line} className="rounded-[20px] border border-border/60 bg-surfaceAlt/40 px-4 py-3 text-sm leading-6 text-muted">
                    {line}
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[28px] border border-border/70 bg-surfaceAlt/40 p-5">
              <p className="section-kicker">What this product is for</p>
              <p className="mt-3 text-sm leading-7 text-muted">
                Plan and evaluate search-and-rescue missions with realistic fleet inputs, simulation-based comparisons, replay, and report generation.
              </p>
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <Panel
          eyebrow="Saved work"
          title="Recent missions"
          description="Existing missions stay easy to reopen, but they no longer crowd the first decision on the page."
        >
          {recentPlans.length === 0 ? (
            <EmptyState
              title="No saved missions yet"
              body="Start a new mission from the guided intake, or explore a sample mission to see the workflow."
            />
          ) : (
            <div className="space-y-3">
              {recentPlans.map((plan) => (
                (() => {
                  const summary = plan.summary_json as Record<string, unknown>;
                  return (
                    <div key={plan.id} className="rounded-[22px] border border-border bg-surfaceAlt/45 p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <p className="text-sm font-semibold text-white">{plan.name}</p>
                          <p className="mt-1 text-sm leading-6 text-muted">
                            {String(summary["scenario_family"] ?? "mixed terrain").replaceAll("_", " ")} search,
                            {" "}
                            {String(plan.mission_intent ?? summary["mission_intent"] ?? "operator-led").replaceAll("_", " ")}
                          </p>
                        </div>
                        <StatusBadge status={plan.approval_state} />
                      </div>
                    </div>
                  );
                })()
              ))}
            </div>
          )}
        </Panel>

        <Panel
          eyebrow="Samples"
          title="Sample missions to explore"
          description="Use these when you want to understand the product flow quickly without entering a brand-new mission."
        >
          {sampleMissions.length === 0 ? (
            <EmptyState title="No sample missions available" body="Sample mission templates have not loaded yet." />
          ) : (
            <div className="space-y-3">
              {sampleMissions.map((template) => (
                <div key={template.id} className="rounded-[22px] border border-border bg-surfaceAlt/45 p-4">
                  <p className="text-sm font-semibold text-white">{template.name}</p>
                  <p className="mt-1 text-sm leading-6 text-muted">{template.description}</p>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>

      <Panel
        eyebrow="Operational context"
        title="Current platform status"
        description="Counts, recent activity, and health stay available below the main actions so the page feels calm instead of dashboard-heavy."
      >
        <div className="grid gap-4 lg:grid-cols-4">
          <QuietMetric label="Saved missions" value={dashboard.data.counts.plans} hint="Mission plans currently available to reopen." />
          <QuietMetric label="Active runs" value={dashboard.data.active_runs} hint="Runs that are queued, running, or paused." />
          <QuietMetric label="Completed runs" value={dashboard.data.completed_runs} hint="Finished mission simulations ready for review." />
          <QuietMetric label="Queued jobs" value={dashboard.data.queued_jobs} hint="Background tasks still in progress." />
        </div>

        <div className="mt-6 grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-3">
            {dashboard.data.recent_activity.length === 0 ? (
              <EmptyState
                title="No recent activity yet"
                body="Create a mission plan, run a comparison, or launch a simulation to populate the activity feed."
              />
            ) : (
              dashboard.data.recent_activity.map((activity) => (
                <div key={`${activity.kind}-${activity.id}`} className="rounded-[22px] border border-border bg-surfaceAlt/45 p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-sm font-semibold text-white">{activity.title}</p>
                      <p className="mt-1 text-sm leading-6 text-muted">{activity.subtitle}</p>
                    </div>
                    <div className="text-right">
                      {activity.status ? <StatusBadge status={activity.status} /> : null}
                      <p className="mt-2 text-xs uppercase tracking-[0.14em] text-muted">
                        {formatTimestamp(activity.timestamp)}
                      </p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="rounded-[24px] border border-border/70 bg-surfaceAlt/40 p-5">
            <p className="section-kicker">System health</p>
            <div className="mt-4 flex items-center gap-3">
              <StatusBadge status={dashboard.data.backend_status} />
              <span className="text-sm leading-6 text-muted">FastAPI backend and local storage are available.</span>
            </div>
            <p className="mt-4 text-sm leading-7 text-muted">
              Recent reports and reviews stay in the review workspace, while the home screen keeps the first-use path focused on starting or reopening a mission.
            </p>
          </div>
        </div>
      </Panel>
    </div>
  );
}
