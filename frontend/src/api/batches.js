import client from './client';

export const getBatches = async () => {
  const response = await client.get('/batches/');
  return response.data;
};

export const getBatch = async (id) => {
  const response = await client.get(`/batches/${id}/`);
  return response.data;
};

export const getBatchRawRows = async (id) => {
  const response = await client.get(`/batches/${id}/rows/`);
  return response.data;
};

export const uploadBatch = async (sourceType, file, notes = '') => {
  const formData = new FormData();
  formData.append('source_type', sourceType);
  formData.append('raw_file', file);
  formData.append('notes', notes);

  const response = await client.post('/batches/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};
