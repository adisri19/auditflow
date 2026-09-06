import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { 
  Check, 
  Flag, 
  Trash2, 
  Filter, 
  Search, 
  ChevronLeft, 
  ChevronRight,
  ShieldCheck,
  Building2,
  AlertCircle,
  HelpCircle,
  FolderLock
} from 'lucide-react';
import { useRecords } from '../hooks/useRecords';
import { useDashboardSummary } from '../hooks/useDashboard';
import StatusBadge from '../components/StatusBadge/StatusBadge';
import RecordDrawer from '../components/RecordDrawer/RecordDrawer';

const ReviewDashboard = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  
  // Search & Filter state
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || '');
  const [scopeFilter, setScopeFilter] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  
  // Selected rows for bulk actions
  const [selectedIds, setSelectedIds] = useState([]);
  
  // Drawer state
  const [selectedRecordId, setSelectedRecordId] = useState(null);

  // Sync state with URL params if it changes
  useEffect(() => {
    const urlStatus = searchParams.get('status');
    if (urlStatus !== null) {
      setStatusFilter(urlStatus);
    }
  }, [searchParams]);

  // Construct query params for API
  const queryParams = {
    search,
    status: statusFilter,
    scope: scopeFilter,
    source_type: sourceFilter,
    date_from: dateFrom,
    date_to: dateTo,
    page,
    page_size: pageSize
  };

  const { data: recordsData, isLoading, refetch, approveRecord, flagRecord, rejectRecord, bulkApproveRecords } = useRecords(queryParams);
  const { data: summary, refetch: refetchSummary } = useDashboardSummary();

  const handleSearchChange = (e) => {
    setSearch(e.target.value);
    setPage(1);
  };

  const handleFilterChange = (setter, val) => {
    setter(val);
    setPage(1);
    
    // Update URL params for status if status changes
    if (setter === setStatusFilter) {
      if (val) {
        setSearchParams({ status: val });
      } else {
        searchParams.delete('status');
        setSearchParams(searchParams);
      }
    }
  };

  const handleSelectAll = (e) => {
    if (e.target.checked && recordsData?.results) {
      const pendingIds = recordsData.results
        .filter(r => r.status !== 'LOCKED')
        .map(r => r.id);
      setSelectedIds(pendingIds);
    } else {
      setSelectedIds([]);
    }
  };

  const handleSelectRow = (e, id) => {
    if (e.target.checked) {
      setSelectedIds(prev => [...prev, id]);
    } else {
      setSelectedIds(prev => prev.filter(item => item !== id));
    }
  };

  const handleBulkApprove = async () => {
    if (selectedIds.length === 0) return;
    if (window.confirm(`Are you sure you want to approve ${selectedIds.length} records?`)) {
      try {
        await bulkApproveRecords(selectedIds);
        setSelectedIds([]);
        refetch();
        refetchSummary();
      } catch (err) {
        alert("Failed bulk approval.");
      }
    }
  };

  const handleQuickAction = async (e, id, actionType) => {
    e.stopPropagation(); // Prevent drawer opening on row click
    try {
      if (actionType === 'approve') {
        await approveRecord({ id, reviewNotes: 'Quick approved from grid.' });
      } else if (actionType === 'flag') {
        await flagRecord({ id, reviewNotes: 'Quick flagged.' });
      } else if (actionType === 'reject') {
        await rejectRecord({ id, reviewNotes: 'Quick rejected.' });
      }
      refetch();
      refetchSummary();
    } catch (err) {
      alert(`Action failed: ${err.message}`);
    }
  };

  const results = recordsData?.results || [];
  const totalCount = recordsData?.count || 0;
  const numPages = recordsData?.num_pages || 1;

  // Header cards
  const stats = [
    { name: 'Pending Review', count: summary?.status_counts?.PENDING || 0, icon: AlertCircle, color: 'text-amber-400 bg-amber-400/10' },
    { name: 'Flagged Issues', count: summary?.status_counts?.FLAGGED || 0, icon: HelpCircle, color: 'text-orange-400 bg-orange-400/10' },
    { name: 'Total Certified', count: summary?.status_counts?.LOCKED || 0, icon: ShieldCheck, color: 'text-sky-400 bg-sky-400/10' },
    { name: 'Certified Volume', count: `${summary?.total_tco2e_approved || 0} tCO₂e`, icon: FolderLock, color: 'text-emerald-400 bg-emerald-400/10' }
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Top Banner stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat, idx) => {
          const Icon = stat.icon;
          return (
            <div key={idx} className="border border-slate-800 bg-slate-900/30 rounded-2xl p-5 flex items-center justify-between">
              <div>
                <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">{stat.name}</p>
                <p className="text-lg font-black text-slate-100 mt-1">{stat.count}</p>
              </div>
              <div className={`p-2.5 rounded-xl border border-transparent ${stat.color}`}>
                <Icon className="w-4 h-4" />
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Sidebar Filters */}
        <aside className="w-full lg:w-64 shrink-0 bg-slate-900/30 border border-slate-800/80 rounded-3xl p-6 space-y-6 h-fit">
          <div className="flex items-center gap-2 text-slate-300 pb-3 border-b border-slate-800/40">
            <Filter className="w-4 h-4 text-emerald-400" />
            <h3 className="text-xs font-bold uppercase tracking-wider">Search Filters</h3>
          </div>

          <div className="space-y-4">
            {/* Status */}
            <div>
              <label className="text-[10px] text-slate-500 font-bold uppercase block mb-1.5">Review Status</label>
              <select
                value={statusFilter}
                onChange={(e) => handleFilterChange(setStatusFilter, e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-xs text-slate-300 focus:outline-none focus:border-brand-500"
              >
                <option value="">All Statuses</option>
                <option value="PENDING">Pending Review</option>
                <option value="APPROVED">Approved</option>
                <option value="FLAGGED">Flagged</option>
                <option value="REJECTED">Rejected</option>
                <option value="LOCKED">Locked for Audit</option>
              </select>
            </div>

            {/* Scope */}
            <div>
              <label className="text-[10px] text-slate-500 font-bold uppercase block mb-1.5">Scope Level</label>
              <select
                value={scopeFilter}
                onChange={(e) => handleFilterChange(setScopeFilter, e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-xs text-slate-300 focus:outline-none focus:border-brand-500"
              >
                <option value="">All Scopes</option>
                <option value="1">Scope 1 (Direct)</option>
                <option value="2">Scope 2 (Indirect Grid)</option>
                <option value="3">Scope 3 (Value Chain)</option>
              </select>
            </div>

            {/* Source */}
            <div>
              <label className="text-[10px] text-slate-500 font-bold uppercase block mb-1.5">Source System</label>
              <select
                value={sourceFilter}
                onChange={(e) => handleFilterChange(setSourceFilter, e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-xs text-slate-300 focus:outline-none focus:border-brand-500"
              >
                <option value="">All Sources</option>
                <option value="SAP_FUEL_PROC">SAP Fuel & Procurement</option>
                <option value="UTILITY_ELEC">Utility Electricity</option>
                <option value="CORP_TRAVEL">Corporate Travel</option>
              </select>
            </div>

            {/* Dates */}
            <div>
              <label className="text-[10px] text-slate-500 font-bold uppercase block mb-1.5">Start Date</label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => handleFilterChange(setDateFrom, e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-brand-500"
              />
            </div>
            <div>
              <label className="text-[10px] text-slate-500 font-bold uppercase block mb-1.5">End Date</label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => handleFilterChange(setDateTo, e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-brand-500"
              />
            </div>

            {/* Reset */}
            <button
              onClick={() => {
                setSearch('');
                setStatusFilter('');
                setScopeFilter('');
                setSourceFilter('');
                setDateFrom('');
                setDateTo('');
                setSearchParams({});
                setPage(1);
              }}
              className="w-full py-2.5 rounded-xl text-xs font-bold bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-all cursor-pointer text-center"
            >
              Reset Filters
            </button>
          </div>
        </aside>

        {/* Records Table section */}
        <div className="flex-1 border border-slate-800/80 bg-slate-900/30 rounded-3xl p-6 lg:p-8 space-y-6 overflow-hidden">
          {/* Controls Bar */}
          <div className="flex flex-col sm:flex-row gap-4 items-stretch sm:items-center justify-between">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="text"
                placeholder="Search description, plant, facility..."
                value={search}
                onChange={handleSearchChange}
                className="w-full bg-slate-950 border border-slate-800 rounded-2xl pl-10 pr-4 py-2.5 text-xs text-slate-300 placeholder-slate-600 focus:outline-none focus:border-brand-500"
              />
            </div>

            {selectedIds.length > 0 && (
              <button
                onClick={handleBulkApprove}
                className="px-4 py-2.5 rounded-2xl text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-500/10 flex items-center gap-1.5 transition-all cursor-pointer shrink-0"
              >
                <Check className="w-4 h-4" /> Bulk Approve ({selectedIds.length})
              </button>
            )}
          </div>

          {/* Table */}
          {isLoading ? (
            <div className="py-20 text-center text-slate-500 text-xs">Loading records list...</div>
          ) : results.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-500 font-bold uppercase tracking-wider pb-3">
                    <th className="pb-3 w-8">
                      <input
                        type="checkbox"
                        checked={selectedIds.length > 0 && selectedIds.length === results.filter(r => r.status !== 'LOCKED').length}
                        onChange={handleSelectAll}
                        className="rounded border-slate-800 text-brand-600 focus:ring-brand-500"
                      />
                    </th>
                    <th className="pb-3">Date</th>
                    <th className="pb-3">Facility</th>
                    <th className="pb-3">Category</th>
                    <th className="pb-3">Scope</th>
                    <th className="pb-3 text-right">Quantity</th>
                    <th className="pb-3">Unit</th>
                    <th className="pb-3 text-right">CO₂e (kg)</th>
                    <th className="pb-3">Status</th>
                    <th className="pb-3 text-right">Quick Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/40 text-slate-300">
                  {results.map((record) => (
                    <tr
                      key={record.id}
                      onClick={() => setSelectedRecordId(record.id)}
                      onDoubleClick={() => navigate(`/records/${record.id}`)}
                      title="Click to preview · double-click for full page"
                      className="hover:bg-slate-900/20 group cursor-pointer"
                    >
                      <td className="py-4" onClick={(e) => e.stopPropagation()}>
                        {record.status !== 'LOCKED' && (
                          <input
                            type="checkbox"
                            checked={selectedIds.includes(record.id)}
                            onChange={(e) => handleSelectRow(e, record.id)}
                            className="rounded border-slate-800 text-brand-600 focus:ring-brand-500"
                          />
                        )}
                      </td>
                      <td className="py-4 font-medium">{record.activity_date}</td>
                      <td className="py-4 font-bold text-slate-200">{record.facility_code || 'HQ'}</td>
                      <td className="py-4 text-slate-400 truncate max-w-[140px]" title={record.description}>
                        {record.category}
                      </td>
                      <td className="py-4">
                        <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-bold ${
                          record.scope === 1 ? 'bg-emerald-500/10 text-emerald-400' :
                          record.scope === 2 ? 'bg-sky-500/10 text-sky-400' :
                          'bg-purple-500/10 text-purple-400'
                        }`}>
                          S{record.scope}
                        </span>
                      </td>
                      <td className="py-4 text-right font-bold text-slate-200">
                        {Number(record.quantity).toLocaleString()}
                      </td>
                      <td className="py-4 text-slate-500 font-semibold">{record.unit}</td>
                      <td className="py-4 text-right font-black text-emerald-400">
                        {record.co2e_kg ? Number(record.co2e_kg).toLocaleString(undefined, {minimumFractionDigits: 1}) : '—'}
                      </td>
                      <td className="py-4">
                        <StatusBadge status={record.status} />
                      </td>
                      <td className="py-4 text-right" onClick={(e) => e.stopPropagation()}>
                        {record.status !== 'LOCKED' ? (
                          <div className="inline-flex gap-1.5 opacity-60 group-hover:opacity-100 transition-opacity">
                            <button
                              onClick={(e) => handleQuickAction(e, record.id, 'approve')}
                              title="Approve row"
                              className="w-7 h-7 rounded-lg bg-emerald-500/5 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/15 flex items-center justify-center cursor-pointer"
                            >
                              <Check className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={(e) => handleQuickAction(e, record.id, 'flag')}
                              title="Flag row"
                              className="w-7 h-7 rounded-lg bg-orange-500/5 hover:bg-orange-500/20 text-orange-400 border border-orange-500/15 flex items-center justify-center cursor-pointer"
                            >
                              <Flag className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={(e) => handleQuickAction(e, record.id, 'reject')}
                              title="Reject row"
                              className="w-7 h-7 rounded-lg bg-rose-500/5 hover:bg-rose-500/20 text-rose-400 border border-rose-500/15 flex items-center justify-center cursor-pointer"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        ) : (
                          <Lock className="w-3.5 h-3.5 text-slate-600 inline mr-2" />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="py-20 text-center text-slate-500 text-xs">No records matching the search filter.</div>
          )}

          {/* Pagination Controls */}
          {totalCount > pageSize && (
            <div className="flex items-center justify-between pt-4 border-t border-slate-800/40 text-xs text-slate-500">
              <div>
                Showing <span className="font-semibold text-slate-300">{((page - 1) * pageSize) + 1}</span> to{' '}
                <span className="font-semibold text-slate-300">{Math.min(page * pageSize, totalCount)}</span> of{' '}
                <span className="font-semibold text-slate-300">{totalCount}</span> results
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => setPage(p => Math.max(p - 1, 1))}
                  disabled={page === 1}
                  className="px-3 py-1.5 rounded-xl border border-slate-850 hover:bg-slate-800/40 text-slate-400 hover:text-slate-200 disabled:opacity-40 cursor-pointer"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="px-3 py-1.5 rounded-xl bg-slate-850 text-slate-200 font-semibold">
                  Page {page} of {numPages}
                </span>
                <button
                  onClick={() => setPage(p => Math.min(p + 1, numPages))}
                  disabled={page === numPages}
                  className="px-3 py-1.5 rounded-xl border border-slate-850 hover:bg-slate-800/40 text-slate-400 hover:text-slate-200 disabled:opacity-40 cursor-pointer"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Record Inspect Drawer */}
      <RecordDrawer
        recordId={selectedRecordId}
        onClose={() => setSelectedRecordId(null)}
        onStatusChanged={() => {
          refetch();
          refetchSummary();
        }}
      />
    </div>
  );
};

export default ReviewDashboard;
