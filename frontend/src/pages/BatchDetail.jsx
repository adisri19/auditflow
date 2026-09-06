import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getBatch, getBatchRawRows } from '../api/batches';
import { getRecords } from '../api/records';
import { 
  ArrowLeft, 
  Calendar, 
  User, 
  FileText, 
  AlertTriangle, 
  CheckCircle,
  Database,
  ArrowRight,
  HelpCircle,
  Clock
} from 'lucide-react';
import StatusBadge from '../components/StatusBadge/StatusBadge';
import RecordDrawer from '../components/RecordDrawer/RecordDrawer';

const BatchDetail = () => {
  const { id } = useParams();
  const [selectedRecordId, setSelectedRecordId] = useState(null);

  // Fetch batch details
  const { data: batch, isLoading: batchLoading } = useQuery({
    queryKey: ['batch', id],
    queryFn: () => getBatch(id)
  });

  // Fetch raw rows
  const { data: rawRows, isLoading: rowsLoading } = useQuery({
    queryKey: ['batch-rows', id],
    queryFn: () => getBatchRawRows(id)
  });

  // Fetch successfully created records
  const { data: recordsData, isLoading: recordsLoading, refetch: refetchRecords } = useQuery({
    queryKey: ['batch-records', id],
    queryFn: () => getRecords({ batch_id: id, page_size: 100 })
  });

  if (batchLoading || rowsLoading || recordsLoading) {
    return (
      <div className="flex h-64 items-center justify-center text-slate-400 text-sm">
        <Clock className="w-5 h-5 animate-spin mr-2" /> Loading batch run details...
      </div>
    );
  }

  if (!batch) {
    return (
      <div className="text-center py-12">
        <h2 className="text-lg font-bold text-slate-200">Batch Not Found</h2>
        <Link to="/" className="text-emerald-400 text-xs mt-2 inline-block">Return home</Link>
      </div>
    );
  }

  // Count successes and failures
  const failedRows = rawRows?.filter(row => row.parse_error && !row.parse_error.toLowerCase().includes('warning') && !row.parse_error.toLowerCase().includes('demand')) || [];
  const warningRows = rawRows?.filter(row => row.parse_error && (row.parse_error.toLowerCase().includes('warning') || row.parse_error.toLowerCase().includes('demand'))) || [];
  const records = recordsData?.results || [];
  const successCount = records.length;

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16">
      {/* Back link */}
      <div>
        <Link to="/batches" className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-slate-200">
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Ingestion logs
        </Link>
      </div>

      {/* Header Summary Card */}
      <div className="border border-slate-800/80 bg-slate-900/40 backdrop-blur-xl p-8 rounded-3xl space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <span className="text-[10px] uppercase font-bold tracking-widest text-slate-400">Ingestion Inquest</span>
            <h2 className="text-xl font-black text-slate-200 mt-1">
              Batch: {batch.source_type === 'SAP_FUEL_PROC' && 'SAP Fuel & Procurement'}
              {batch.source_type === 'UTILITY_ELEC' && 'Utility Electricity'}
              {batch.source_type === 'CORP_TRAVEL' && 'Corporate Travel'}
            </h2>
            <p className="text-xs text-slate-500 mt-1 truncate max-w-lg">ID: {batch.id}</p>
          </div>
          
          <div className="flex items-center gap-3 shrink-0">
            <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${
              batch.status === 'DONE' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
              batch.status === 'FAILED' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
              'bg-amber-500/10 text-amber-400 border border-amber-500/20'
            }`}>
              {batch.status}
            </span>
          </div>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-3 gap-6 pt-4 border-t border-slate-800/40">
          <div className="bg-slate-950/20 p-4 rounded-2xl border border-slate-800/20 text-center">
            <p className="text-[10px] text-slate-500 uppercase font-bold">Total Rows Processed</p>
            <p className="text-xl font-extrabold text-slate-200 mt-1">{batch.row_count}</p>
          </div>
          <div className="bg-emerald-500/5 p-4 rounded-2xl border border-emerald-500/10 text-center">
            <p className="text-[10px] text-emerald-400 uppercase font-bold">Successfully Normalized</p>
            <p className="text-xl font-extrabold text-emerald-400 mt-1">{successCount}</p>
          </div>
          <div className="bg-rose-500/5 p-4 rounded-2xl border border-rose-500/10 text-center">
            <p className="text-[10px] text-rose-400 uppercase font-bold">Skipped / Failed</p>
            <p className="text-xl font-extrabold text-rose-400 mt-1">{failedRows.length}</p>
          </div>
        </div>

        {/* Meta details */}
        <div className="flex flex-wrap gap-x-8 gap-y-2 text-xs text-slate-400">
          <div className="flex items-center gap-1.5">
            <Calendar className="w-3.5 h-3.5 text-slate-500" />
            <span>Ingested At: {new Date(batch.ingested_at).toLocaleString()}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <User className="w-3.5 h-3.5 text-slate-500" />
            <span>Actor: {batch.ingested_by?.email || 'System'}</span>
          </div>
          {batch.notes && (
            <div className="flex items-center gap-1.5 w-full mt-2 bg-slate-950/40 p-3 rounded-xl border border-slate-800/20 text-slate-400 italic">
              <span>Notes: {batch.notes}</span>
            </div>
          )}
        </div>
      </div>

      {/* Parse Failures Section */}
      {failedRows.length > 0 && (
        <div className="border border-rose-500/20 bg-rose-500/5 rounded-3xl p-8 space-y-4">
          <div className="flex items-center gap-2 text-rose-400">
            <AlertTriangle className="w-5 h-5" />
            <h3 className="font-bold text-sm">Failed Rows ({failedRows.length})</h3>
          </div>
          <p className="text-xs text-slate-400">The following rows could not be normalized. Check for formatting errors or missing fields.</p>

          <div className="overflow-x-auto border border-rose-500/10 rounded-2xl bg-slate-950/40">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-rose-500/10 text-rose-400/80 font-bold uppercase tracking-wider bg-rose-500/5">
                  <th className="p-3">Row #</th>
                  <th className="p-3">Raw Data Snippet</th>
                  <th className="p-3">Reason for Failure</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rose-500/10 text-slate-300">
                {failedRows.map((row) => (
                  <tr key={row.id} className="hover:bg-rose-500/5">
                    <td className="p-3 font-bold text-slate-400">Row {row.row_index}</td>
                    <td className="p-3 font-mono text-[11px] text-slate-500 max-w-sm truncate">
                      {JSON.stringify(row.raw_data)}
                    </td>
                    <td className="p-3 font-semibold text-rose-400 bg-rose-500/5 italic">{row.parse_error}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Warnings / skipped columns section (non-fatal, like demand charges skipped) */}
      {warningRows.length > 0 && (
        <div className="border border-amber-500/20 bg-amber-500/5 rounded-3xl p-8 space-y-4">
          <div className="flex items-center gap-2 text-amber-400">
            <AlertTriangle className="w-5 h-5" />
            <h3 className="font-bold text-sm">Warnings / Non-Fatal Skipped Columns ({warningRows.length})</h3>
          </div>
          <p className="text-xs text-slate-400">The energy quantities were parsed successfully, but some secondary metrics were skipped.</p>

          <div className="overflow-x-auto border border-amber-500/10 rounded-2xl bg-slate-950/40">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-amber-500/10 text-amber-400/80 font-bold uppercase tracking-wider bg-amber-500/5">
                  <th className="p-3">Row #</th>
                  <th className="p-3">Raw Data Snippet</th>
                  <th className="p-3">Warning Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-amber-500/10 text-slate-300">
                {warningRows.map((row) => (
                  <tr key={row.id} className="hover:bg-amber-500/5">
                    <td className="p-3 font-bold text-slate-400">Row {row.row_index}</td>
                    <td className="p-3 font-mono text-[11px] text-slate-500 max-w-sm truncate">
                      {JSON.stringify(row.raw_data)}
                    </td>
                    <td className="p-3 font-medium text-amber-400 italic bg-amber-500/5">{row.parse_error}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Created Records Section */}
      <div className="border border-slate-800/80 bg-slate-900/30 rounded-3xl p-8 space-y-6">
        <div>
          <h3 className="text-md font-bold text-slate-200">Normalized Emissions Activity Records ({records.length})</h3>
          <p className="text-xs text-slate-500 mt-1">Successfully parsed rows that have been loaded into the database as Scope records.</p>
        </div>

        {records.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-500 font-bold uppercase tracking-wider">
                  <th className="pb-3">Date</th>
                  <th className="pb-3">Facility</th>
                  <th className="pb-3">Scope</th>
                  <th className="pb-3">Category</th>
                  <th className="pb-3 text-right">Quantity</th>
                  <th className="pb-3">Unit</th>
                  <th className="pb-3 text-right">CO₂e (kg)</th>
                  <th className="pb-3">Status</th>
                  <th className="pb-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/40 text-slate-300">
                {records.map((record) => (
                  <tr key={record.id} className="hover:bg-slate-900/20 group">
                    <td className="py-3.5 font-medium">{record.activity_date}</td>
                    <td className="py-3.5 font-semibold text-slate-200">{record.facility_code || '—'}</td>
                    <td className="py-3.5">
                      <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        record.scope === 1 ? 'bg-emerald-500/10 text-emerald-400' :
                        record.scope === 2 ? 'bg-sky-500/10 text-sky-400' :
                        'bg-purple-500/10 text-purple-400'
                      }`}>
                        Scope {record.scope}
                      </span>
                    </td>
                    <td className="py-3.5 text-slate-400">{record.category}</td>
                    <td className="py-3.5 text-right font-bold text-slate-200">{Number(record.quantity).toLocaleString()}</td>
                    <td className="py-3.5 text-slate-500 font-semibold">{record.unit}</td>
                    <td className="py-3.5 text-right font-black text-emerald-400">
                      {record.co2e_kg ? Number(record.co2e_kg).toLocaleString(undefined, {minimumFractionDigits: 1}) : '—'}
                    </td>
                    <td className="py-3.5">
                      <StatusBadge status={record.status} />
                    </td>
                    <td className="py-3.5 text-right">
                      <button
                        onClick={() => setSelectedRecordId(record.id)}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-[11px] font-bold bg-slate-800 text-slate-200 border border-slate-700 hover:bg-slate-700 cursor-pointer"
                      >
                        Inspect <ArrowRight className="w-3 h-3" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-slate-500 italic py-4 text-center">No successful records created from this batch.</div>
        )}
      </div>

      {/* Record Inspect Drawer */}
      <RecordDrawer
        recordId={selectedRecordId}
        onClose={() => setSelectedRecordId(null)}
        onStatusChanged={refetchRecords}
      />
    </div>
  );
};

export default BatchDetail;
