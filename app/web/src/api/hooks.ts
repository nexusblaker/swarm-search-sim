import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";

export function useHealth() {
  return useQuery({ queryKey: ["health"], queryFn: api.health, refetchInterval: 15000 });
}

export function useDashboardSummary() {
  return useQuery({ queryKey: ["dashboard-summary"], queryFn: api.dashboardSummary, refetchInterval: 10000 });
}

export function useScenarios() {
  return useQuery({ queryKey: ["scenarios"], queryFn: api.scenarios });
}

export function usePlans() {
  return useQuery({ queryKey: ["plans"], queryFn: api.plans });
}

export function useComparisons() {
  return useQuery({ queryKey: ["comparisons"], queryFn: api.comparisons });
}

export function useRuns(refetchInterval?: number | false) {
  return useQuery({ queryKey: ["runs"], queryFn: api.runs, refetchInterval });
}

export function useExperiments() {
  return useQuery({ queryKey: ["experiments"], queryFn: api.experiments });
}

export function useReports() {
  return useQuery({ queryKey: ["reports"], queryFn: api.reports });
}

export function useReviews() {
  return useQuery({ queryKey: ["reviews"], queryFn: api.reviews });
}

export function useLibraryTemplates() {
  return useQuery({ queryKey: ["library-templates"], queryFn: api.templates });
}

export function useInvalidateResources() {
  const queryClient = useQueryClient();
  return () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] }),
      queryClient.invalidateQueries({ queryKey: ["scenarios"] }),
      queryClient.invalidateQueries({ queryKey: ["plans"] }),
      queryClient.invalidateQueries({ queryKey: ["comparisons"] }),
      queryClient.invalidateQueries({ queryKey: ["runs"] }),
      queryClient.invalidateQueries({ queryKey: ["experiments"] }),
      queryClient.invalidateQueries({ queryKey: ["reports"] }),
      queryClient.invalidateQueries({ queryKey: ["reviews"] }),
      queryClient.invalidateQueries({ queryKey: ["library-templates"] }),
    ]);
}

export function useCreatePlanMutation() {
  const invalidate = useInvalidateResources();
  return useMutation({
    mutationFn: api.createPlan,
    onSuccess: () => invalidate(),
  });
}
