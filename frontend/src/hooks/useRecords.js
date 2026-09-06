import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import {
  getRecords,
  patchRecord,
  approveRecord,
  flagRecord,
  rejectRecord,
  lockRecord,
  bulkApproveRecords,
} from '../api/records';

export const useRecords = (params = {}) => {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ['records', params],
    queryFn: () => getRecords(params),
    placeholderData: keepPreviousData,
  });

  const approveMutation = useMutation({
    mutationFn: ({ id, reviewNotes }) => approveRecord(id, reviewNotes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['records'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  const flagMutation = useMutation({
    mutationFn: ({ id, reviewNotes }) => flagRecord(id, reviewNotes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['records'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: ({ id, reviewNotes }) => rejectRecord(id, reviewNotes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['records'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  const lockMutation = useMutation({
    mutationFn: (id) => lockRecord(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['records'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => patchRecord(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['records'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  const bulkApproveMutation = useMutation({
    mutationFn: (ids) => bulkApproveRecords(ids),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['records'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  return {
    ...query,
    approveRecord: approveMutation.mutateAsync,
    flagRecord: flagMutation.mutateAsync,
    rejectRecord: rejectMutation.mutateAsync,
    lockRecord: lockMutation.mutateAsync,
    updateRecord: updateMutation.mutateAsync,
    bulkApproveRecords: bulkApproveMutation.mutateAsync,
    isMutating:
      approveMutation.isPending ||
      flagMutation.isPending ||
      rejectMutation.isPending ||
      lockMutation.isPending ||
      updateMutation.isPending ||
      bulkApproveMutation.isPending,
  };
};
