import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getBatches } from '../api/batches';
import { Link } from 'react-router-dom';
import { Calendar, User, Database, ArrowRight, FileSpreadsheet, Clock } from 'lucide-react';

const BatchList = () => {
  const { data: batches, isLoading } = useQuery({
    queryKey: ['batches-list'],
    queryFn: getBatches
  });

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-12">
      {/* Header */}
      <div className="border-b border-slate-800 pb-5">
        <span className="text-[10px] uppercase font-bold tracking-widest text-emerald-400">Pipeline Registry</span>
        <h2 className="text-2xl font-black text-slate-100 mt-1 tracking-tight">Ingestion Batches Log</h2>
        <p className="text-xs text-slate-500 mt-1">
          Historical registry of files uploaded to the platform, including row validation summaries and error logs.
        </p>
      </div>

      {isLoading ? (
        <div className="flex h-64 items-center justify-center text-slate-400 text-sm">
          <Clock className="w-5 h-5 animate-spin mr-2" /> Loading ingestion logs...
        </div>
      ) : batches && batches.length > 0 ? (
        <div className="border border-slate-800/80 bg-slate-900/30 rounded-3xl p-8 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-500 font-bold uppercase tracking-wider">
                  <th className="pb-4 font-semibold">Upload Date</th>
                  <th className="pb-4 font-semibold">Source Type</th>
                  <th className="pb-4 font-semibold">Status</th>
                  <th className="pb-4 font-semibold">Success Count</th>
                  <th className="pb-4 font-semibold">Error Count</th>
                  <th className="pb-4 font-semibold">Ingested By</th>
                  <th className="pb-4 font-semibold">Notes</th>
                  <th className="pb-4 text-right font-semibold">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/40 text-slate-300">
                {batches.map((batch) => (
                  <tr key={batch.id} className="hover:bg-slate-900/10">
                    <td className="py-4 font-medium flex items-center gap-2 text-slate-400">
                      <Calendar className="w-3.5 h-3.5 text-slate-600" />
                      {new Date(batch.ingested_at).toLocaleString()}
                    </td>
                    <td className="py-4 font-bold text-slate-200">
                      {batch.source_type === 'SAP_FUEL_PROC' && 'SAP Fuel & Procurement'}
                      {batch.source_type === 'UTILITY_ELEC' && 'Utility Electricity'}
                      {batch.source_type === 'CORP_TRAVEL' && 'Corporate Travel'}
                    </td>
                    <td className="py-4">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[10px] font-bold ${
                        batch.status === 'DONE' ? 'bg-emerald-500/10 text-emerald-400' :
                        batch.status === 'FAILED' ? 'bg-rose-500/10 text-rose-400' :
                        'bg-amber-500/10 text-amber-400'
                      }`}>
                        {batch.status}
                      </span>
                    </td>
                    <td className="py-4 font-semibold text-slate-300">{batch.row_count - batch.error_count} rows</td>
                    <td className="py-4">
                      {batch.error_count > 0 ? (
                        <span className="text-rose-400 font-semibold">{batch.error_count} errors</span>
                      ) : (
                        <span className="text-slate-500">0</span>
                      )}
                    </td>
                    <td className="py-4 text-slate-400 flex items-center gap-1.5 mt-0.5">
                      <User className="w-3.5 h-3.5 text-slate-600" />
                      {batch.ingested_by?.username || 'admin'}
                    </td>
                    <td className="py-4 text-slate-500 italic max-w-[200px] truncate" title={batch.notes}>
                      {batch.notes || '—'}
                    </td>
                    <td className="py-4 text-right">
                      <Link 
                        to={`/batches/${batch.id}`}
                        className="inline-flex items-center gap-1 text-emerald-400 hover:text-emerald-300 font-bold hover:underline"
                      >
                        Inspect Runs <ArrowRight className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="bg-slate-900/10 border border-slate-800/40 p-12 rounded-3xl flex flex-col items-center justify-center text-center">
          <FileSpreadsheet className="w-12 h-12 text-slate-700 mb-4" />
          <h3 className="text-md font-bold text-slate-400">No batch uploads recorded</h3>
          <p className="text-xs text-slate-600 mt-2 max-w-sm">Use the Upload Data tab to start sending logs to the platform.</p>
        </div>
      )}
    </div>
  );
};

export default BatchList;
