import client from './client';

export const getRecords = async (params = {}) => {
  const response = await client.get('/records/', { params });
  return response.data;
};

export const getRecord = async (id) => {
  const response = await client.get(`/records/${id}/`);
  return response.data;
};

export const patchRecord = async (id, data) => {
  const response = await client.patch(`/records/${id}/`, data);
  return response.data;
};

export const approveRecord = async (id, reviewNotes = '') => {
  const response = await client.post(`/records/${id}/approve/`, { review_notes: reviewNotes });
  return response.data;
};

export const flagRecord = async (id, reviewNotes = '') => {
  const response = await client.post(`/records/${id}/flag/`, { review_notes: reviewNotes });
  return response.data;
};

export const rejectRecord = async (id, reviewNotes = '') => {
  const response = await client.post(`/records/${id}/reject/`, { review_notes: reviewNotes });
  return response.data;
};

export const lockRecord = async (id) => {
  const response = await client.post(`/records/${id}/lock/`);
  return response.data;
};

export const getRecordHistory = async (id) => {
  const response = await client.get(`/records/${id}/history/`);
  return response.data;
};

export const bulkApproveRecords = async (ids) => {
  const response = await client.post('/records/bulk_approve/', { ids });
  return response.data;
};
