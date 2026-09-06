import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { 
  ShieldAlert, 
  CheckCircle, 
  Building2, 
  ArrowRight, 
  UploadCloud, 
  Database,
  Calendar,
  AlertCircle,
  FileSpreadsheet
} from 'lucide-react';
import { useDashboardSummary, useDashboardTimeline } from '../hooks/useDashboard';
import { getBatches } from '../api/batches';
import { useQuery } from '@tanstack/react-query';
import ScopeChart from '../components/ScopeChart/ScopeChart';
import SourcePieChart from '../components/SourcePieChart/SourcePieChart';

const Dashboard = () => {
  const navigate = useNavigate();

  // Fetch summary stats
  const { data: summary, isLoading: summaryLoading } = useDashboardSummary();
  // Fetch timeline stats
  const { data: timeline, isLoading: timelineLoading } = useDashboardTimeline();
  // Fetch recent batches
  const { data: batches, isLoading: batchesLoading } = useQuery({
    queryKey: ['recent-batches'],
    queryFn: getBatches
  });

  const kpis = [
    {
      name: 'Pending Analyst Review',
      value: summary?.status_counts?.PENDING ?? 0,
      icon: AlertCircle,
      color: 'text-amber-400 bg-amber-400/10 border-amber-500/20',
      actionText: 'Go to Review',
      actionPath: '/review'
    },
    {
      name: 'Flagged Records',
      value: summary?.status_counts?.FLAGGED ?? 0,
      icon: ShieldAlert,
      color: 'text-orange-400 bg-orange-400/10 border-orange-500/20',
      actionText: 'Inspect issues',
      actionPath: '/review?status=FLAGGED'
    },
    {
      name: 'Approved This Week',
      value: summary?.approved_this_week ?? 0,
      icon: CheckCircle,
      color: 'text-emerald-400 bg-emerald-400/10 border-emerald-500/20',
      actionText: 'View Approved',
      actionPath: '/review?status=APPROVED'
    },
    {
      name: 'Total Ledger Emissions',
      value: `${summary?.total_tco2e_approved ?? '0.00'} tCO₂e`,
      icon: Building2,
      color: 'text-sky-400 bg-sky-400/10 border-sky-500/20',
      actionText: 'View audited data',
      actionPath: '/review?status=LOCKED'
    }
  ];

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Welcome Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-slate-900 via-slate-900 to-brand-950/20 p-8 rounded-3xl border border-slate-800/80">
        <div>
          <h2 className="text-2xl font-black text-slate-100 tracking-tight">Emissions Analytics Dashboard</h2>
          <p className="text-slate-400 text-sm mt-1.5 max-w-xl">
            Real-time calculations, scope classifications, and data verification status for greenhouse gas inventories.
          </p>
        </div>
        <div className="flex gap-3 shrink-0">
          <Link
            to="/upload"
            className="flex items-center gap-2 px-4 py-3 rounded-2xl text-xs font-bold bg-brand-600 hover:bg-brand-500 text-white shadow-lg shadow-brand-500/10 transition-all cursor-pointer"
          >
            <UploadCloud className="w-4 h-4" /> Upload Raw Data
          </Link>
          <Link
            to="/review"
            className="flex items-center gap-2 px-4 py-3 rounded-2xl text-xs font-bold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all cursor-pointer"
          >
            Open Review Console <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {kpis.map((kpi, index) => {
          const Icon = kpi.icon;
          return (
            <div key={index} className={`border rounded-2xl p-6 bg-slate-900/40 backdrop-blur-xl flex flex-col justify-between h-[160px] transition-all hover:bg-slate-900/60`}>
              <div className="flex justify-between items-start">
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{kpi.name}</span>
                <div className={`p-2.5 rounded-xl border ${kpi.color}`}>
                  <Icon className="w-4 h-4" />
                </div>
              </div>
              <div>
                <p className="text-2xl font-extrabold text-slate-100 mt-2">{summaryLoading ? '...' : kpi.value}</p>
                <Link 
                  to={kpi.actionPath} 
                  className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-400 hover:text-emerald-300 mt-3 hover:underline"
                >
                  {kpi.actionText} <ArrowRight className="w-3 h-3" />
                </Link>
              </div>
            </div>
          );
        })}
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Scope chart (2/3 width) */}
        <div className="lg:col-span-2 border border-slate-800/80 bg-slate-900/30 rounded-3xl p-6 space-y-4">
          <div>
            <h3 className="text-sm font-bold text-slate-300">Emissions by Scope Over Time</h3>
            <p className="text-xs text-slate-500">Monthly breakdown of Scope 1, 2, and 3 carbon equivalent outputs.</p>
          </div>
          <div className="pt-2">
            {timelineLoading ? (
              <div className="h-80 flex items-center justify-center text-slate-500 text-sm">Loading timeline...</div>
            ) : (
              <ScopeChart data={timeline} />
            )}
          </div>
        </div>

        {/* Source Pie Chart (1/3 width) */}
        <div className="border border-slate-800/80 bg-slate-900/30 rounded-3xl p-6 space-y-4">
          <div>
            <h3 className="text-sm font-bold text-slate-300">Ingested Record Distribution</h3>
            <p className="text-xs text-slate-500">Breakdown of records across different source types.</p>
          </div>
          <div className="pt-2">
            {summaryLoading ? (
              <div className="h-80 flex items-center justify-center text-slate-500 text-sm">Loading source summary...</div>
            ) : (
              <SourcePieChart data={summary?.source_counts} />
            )}
          </div>
        </div>
      </div>

      {/* Recent Batches List */}
      <div className="border border-slate-800/80 bg-slate-900/30 rounded-3xl p-8 space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h3 className="text-md font-bold text-slate-200">Recent Ingestion Batches</h3>
            <p className="text-xs text-slate-500">Audit trail of the most recent bulk file uploads.</p>
          </div>
          <Link 
            to="/batches"
            className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400 hover:text-emerald-300 hover:underline"
          >
            View all logs <Database className="w-3.5 h-3.5" />
          </Link>
        </div>

        {batchesLoading ? (
          <div className="text-slate-500 text-sm py-4 text-center">Loading ingestion runs...</div>
        ) : batches && batches.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-500 font-bold uppercase tracking-wider">
                  <th className="pb-3 font-semibold">Upload Date</th>
                  <th className="pb-3 font-semibold">Source Type</th>
                  <th className="pb-3 font-semibold">Row Count</th>
                  <th className="pb-3 font-semibold">Error Count</th>
                  <th className="pb-3 font-semibold">Status</th>
                  <th className="pb-3 font-semibold">Notes</th>
                  <th className="pb-3 text-right font-semibold">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/40 text-slate-300">
                {batches.slice(0, 5).map((batch) => (
                  <tr key={batch.id} className="hover:bg-slate-900/10">
                    <td className="py-4 font-medium flex items-center gap-2">
                      <Calendar className="w-3.5 h-3.5 text-slate-500" />
                      {new Date(batch.ingested_at).toLocaleDateString()}
                    </td>
                    <td className="py-4 font-semibold text-slate-200">
                      {batch.source_type === 'SAP_FUEL_PROC' && 'SAP Fuel & Procurement'}
                      {batch.source_type === 'UTILITY_ELEC' && 'Utility Electricity'}
                      {batch.source_type === 'CORP_TRAVEL' && 'Corporate Travel'}
                    </td>
                    <td className="py-4 font-medium">{batch.row_count} rows</td>
                    <td className="py-4">
                      {batch.error_count > 0 ? (
                        <span className="text-rose-400 font-semibold">{batch.error_count} errors</span>
                      ) : (
                        <span className="text-slate-500">0</span>
                      )}
                    </td>
                    <td className="py-4">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold ${
                        batch.status === 'DONE' ? 'bg-emerald-500/10 text-emerald-400' :
                        batch.status === 'FAILED' ? 'bg-rose-500/10 text-rose-400' :
                        'bg-amber-500/10 text-amber-400'
                      }`}>
                        {batch.status}
                      </span>
                    </td>
                    <td className="py-4 text-slate-500 italic max-w-[200px] truncate">{batch.notes || '—'}</td>
                    <td className="py-4 text-right">
                      <Link 
                        to={`/batches/${batch.id}`}
                        className="inline-flex items-center gap-1 text-emerald-400 hover:text-emerald-300 font-bold hover:underline"
                      >
                        Inspect <ArrowRight className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="bg-slate-950/20 border border-slate-800/40 p-8 rounded-2xl flex flex-col items-center justify-center text-center">
            <FileSpreadsheet className="w-10 h-10 text-slate-600 mb-3" />
            <p className="text-sm font-semibold text-slate-400">No Ingestion Batches Found</p>
            <p className="text-xs text-slate-600 mt-1 max-w-xs">Upload your first SAP, Utility, or Travel logs to start analyzing emissions.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
