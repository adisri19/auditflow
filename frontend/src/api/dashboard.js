import client from './client';

export const getDashboardSummary = async (params = {}) => {
  const response = await client.get('/dashboard/summary/', { params });
  return response.data;
};

export const getDashboardTimeline = async () => {
  const response = await client.get('/dashboard/timeline/');
  return response.data;
};
