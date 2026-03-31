import type { RouteObject } from "react-router-dom";
import { createBrowserRouter } from "react-router-dom";

import { App } from "@/App";
import { DashboardPage } from "@/pages/DashboardPage";
import { ExperimentsPage } from "@/pages/ExperimentsPage";
import { LibraryPage } from "@/pages/LibraryPage";
import { MissionControlPage } from "@/pages/MissionControlPage";
import { MissionIntakePage } from "@/pages/MissionIntakePage";
import { MissionPlansPage } from "@/pages/MissionPlansPage";
import { PlanComparisonPage } from "@/pages/PlanComparisonPage";
import { RecommendationsPage } from "@/pages/RecommendationsPage";
import { ReplayPage } from "@/pages/ReplayPage";
import { ReportsPage } from "@/pages/ReportsPage";
import { ReviewsPage } from "@/pages/ReviewsPage";
import { RunHistoryPage } from "@/pages/RunHistoryPage";
import { ScenariosPage } from "@/pages/ScenariosPage";

export const appRouteDefinitions: RouteObject[] = [
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "mission-intake", element: <MissionIntakePage /> },
      { path: "scenarios", element: <ScenariosPage /> },
      { path: "plans", element: <MissionPlansPage /> },
      { path: "library", element: <LibraryPage /> },
      { path: "comparisons", element: <PlanComparisonPage /> },
      { path: "recommendations", element: <RecommendationsPage /> },
      { path: "mission-control", element: <MissionControlPage /> },
      { path: "replay", element: <ReplayPage /> },
      { path: "runs", element: <RunHistoryPage /> },
      { path: "experiments", element: <ExperimentsPage /> },
      { path: "reports", element: <ReportsPage /> },
      { path: "reviews", element: <ReviewsPage /> },
    ],
  },
];

export const router = createBrowserRouter(appRouteDefinitions);
