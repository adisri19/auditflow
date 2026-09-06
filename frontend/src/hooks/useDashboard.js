import { useQuery } from '@tanstack/react-query';
import { getDashboardSummary, getDashboardTimeline } from '../api/dashboard';

export const useDashboardSummary = (params = {}) => {
  return useQuery({
    queryKey: ['dashboard', 'summary', params],
    queryFn: () => getDashboardSummary(params),
  });
};

export const useDashboardTimeline = () => {
  return useQuery({
    queryKey: ['dashboard', 'timeline'],
    queryFn: () => getDashboardTimeline(),
  });
};
