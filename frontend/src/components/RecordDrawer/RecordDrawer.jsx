import React, { useState, useEffect } from 'react';
import { 
  X, 
  Edit, 
  Check, 
  Flag, 
  AlertTriangle, 
  Lock, 
  Calendar, 
  MapPin, 
  Database, 
  User, 
  Info,
  Clock
} from 'lucide-react';
import { getRecord, patchRecord, approveRecord, flagRecord, rejectRecord, lockRecord, getRecordHistory } from '../../api/records';
import StatusBadge from '../StatusBadge/StatusBadge';

const RecordDrawer = ({ recordId, onClose, onStatusChanged, variant = 'drawer' }) => {
  const isPage = variant === 'page';
  const [record, setRecord] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  
  // Form fields
  const [quantity, setQuantity] = useState('');
  const [unit, setUnit] = useState('');
  const [ef, setEf] = useState('');
  const [co2e, setCo2e] = useState('');
  const [reviewNotes, setReviewNotes] = useState('');

  const fetchRecordData = async () => {
    try {
      setLoading(true);
      const [recData, histData] = await Promise.all([
        getRecord(recordId),
        getRecordHistory(recordId)
      ]);
      setRecord(recData);
      setHistory(histData);
      
      // Initialize form
      setQuantity(recData.quantity);
      setUnit(recData.unit);
      setEf(recData.emission_factor || '');
      setCo2e(recData.co2e_kg || '');
      setReviewNotes(recData.review_notes || '');
    } catch (err) {
      console.error("Failed to fetch record details", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (recordId) {
      fetchRecordData();
      setIsEditing(false);
    }
  }, [recordId]);

  const handleSave = async (e) => {
    e.preventDefault();
    try {
      setSaving(true);
      const updated = await patchRecord(recordId, {
        quantity: quantity,
        unit: unit,
        emission_factor: ef !== '' ? ef : null,
        co2e_kg: co2e !== '' ? co2e : null,
        review_notes: reviewNotes
      });
      setRecord(updated);
      setIsEditing(false);
      await fetchRecordData();
      if (onStatusChanged) onStatusChanged();
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to update record.");
    } finally {
      setSaving(false);
    }
  };

  const handleAction = async (actionType) => {
    try {
      setSaving(true);
      let updated;
      if (actionType === 'approve') {
        updated = await approveRecord(recordId, reviewNotes);
      } else if (actionType === 'flag') {
        updated = await flagRecord(recordId, reviewNotes);
      } else if (actionType === 'reject') {
        updated = await rejectRecord(recordId, reviewNotes);
      } else if (actionType === 'lock') {
        updated = await lockRecord(recordId);
      }
      setRecord(updated);
      await fetchRecordData();
      if (onStatusChanged) onStatusChanged();
    } catch (err) {
      alert(err.response?.data?.detail || `Failed to ${actionType} record.`);
    } finally {
      setSaving(false);
    }
  };

  if (!recordId) return null;

  const containerClass = isPage
    ? 'flex flex-col h-full max-w-5xl mx-auto w-full'
    : 'fixed inset-y-0 right-0 w-[550px] bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col z-50 transform transition-transform duration-300 ease-in-out glass';

  return (
    <div className={containerClass}>
      {/* Header */}
      <div className="p-6 border-b border-slate-800 flex items-center justify-between">
        <div>
          <span className="text-[10px] uppercase font-bold tracking-widest text-emerald-400">Activity Record Detail</span>
          <h2 className="text-md font-extrabold text-slate-200 mt-1 truncate max-w-[400px]">
            {record?.description || 'Loading...'}
          </h2>
        </div>
        {onClose && (
          <button 
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-slate-800 hover:bg-slate-700 flex items-center justify-center text-slate-400 hover:text-slate-100 cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center text-slate-400 text-sm">
          <Clock className="w-5 h-5 animate-spin mr-2" /> Loading details...
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Status Row */}
          <div className="flex items-center justify-between bg-slate-950/40 p-4 rounded-xl border border-slate-800/40">
            <div>
              <p className="text-[10px] text-slate-500 font-bold uppercase">Audit Status</p>
              <div className="mt-1">
                <StatusBadge status={record.status} />
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              {record.status !== 'LOCKED' && (
                <>
                  <button
                    onClick={() => handleAction('approve')}
                    disabled={saving}
                    className="px-3 py-1.5 rounded-lg text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 cursor-pointer"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => handleAction('flag')}
                    disabled={saving}
                    className="px-3 py-1.5 rounded-lg text-xs font-bold bg-orange-500/10 text-orange-400 border border-orange-500/20 hover:bg-orange-500/20 cursor-pointer"
                  >
                    Flag
                  </button>
                  <button
                    onClick={() => handleAction('reject')}
                    disabled={saving}
                    className="px-3 py-1.5 rounded-lg text-xs font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20 hover:bg-rose-500/20 cursor-pointer"
                  >
                    Reject
                  </button>
                </>
              )}
              {record.status === 'APPROVED' && (
                <button
                  onClick={() => handleAction('lock')}
                  disabled={saving}
                  className="px-3 py-1.5 rounded-lg text-xs font-bold bg-sky-500/10 text-sky-400 border border-sky-500/20 hover:bg-sky-500/20 flex items-center gap-1 cursor-pointer"
                >
                  <Lock className="w-3 h-3" /> Lock
                </button>
              )}
            </div>
          </div>

          {/* Form / Edit mode */}
          <form onSubmit={handleSave} className="space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="text-xs font-extrabold uppercase text-slate-400 tracking-wider">Metrics & Calculation</h3>
              {record.status !== 'LOCKED' && !isEditing && (
                <button
                  type="button"
                  onClick={() => setIsEditing(true)}
                  className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 flex items-center gap-1 cursor-pointer"
                >
                  <Edit className="w-3 h-3" /> Edit Fields
                </button>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-[10px] text-slate-500 font-bold uppercase block mb-1">Quantity</label>
                <input
                  type="number"
                  step="any"
                  disabled={!isEditing || saving}
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-brand-500 disabled:opacity-60"
                />
              </div>

              <div>
                <label className="text-[10px] text-slate-500 font-bold uppercase block mb-1">Unit</label>
                <input
                  type="text"
                  disabled={!isEditing || saving}
                  value={unit}
                  onChange={(e) => setUnit(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-brand-500 disabled:opacity-60"
                />
              </div>

              <div>
                <label className="text-[10px] text-slate-500 font-bold uppercase block mb-1">Emission Factor</label>
                <input
                  type="number"
                  step="any"
                  disabled={!isEditing || saving}
                  value={ef}
                  onChange={(e) => setEf(e.target.value)}
                  placeholder="Not set"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-brand-500 disabled:opacity-60"
                />
              </div>

              <div>
                <label className="text-[10px] text-slate-500 font-bold uppercase block mb-1">CO₂e (kg)</label>
                <input
                  type="number"
                  step="any"
                  disabled={!isEditing || saving}
                  value={co2e}
                  onChange={(e) => setCo2e(e.target.value)}
                  placeholder="Auto-calculated"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-brand-500 disabled:opacity-60"
                />
              </div>
            </div>

            <div>
              <label className="text-[10px] text-slate-500 font-bold uppercase block mb-1">Analyst Notes</label>
              <textarea
                rows="3"
                disabled={!isEditing && record.status === 'LOCKED'}
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                placeholder="Add audit justification notes..."
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-brand-500 disabled:opacity-60 resize-none"
              />
            </div>

            {isEditing && (
              <div className="flex gap-2">
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-2 rounded-xl text-xs font-bold bg-brand-600 hover:bg-brand-500 text-white flex-1 cursor-pointer"
                >
                  Save Changes
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsEditing(false);
                    setQuantity(record.quantity);
                    setUnit(record.unit);
                    setEf(record.emission_factor || '');
                    setCo2e(record.co2e_kg || '');
                  }}
                  className="px-4 py-2 rounded-xl text-xs font-bold bg-slate-800 hover:bg-slate-700 text-slate-300 flex-1 cursor-pointer"
                >
                  Cancel
                </button>
              </div>
            )}
          </form>

          {/* Provenance */}
          <div className="space-y-3">
            <h3 className="text-xs font-extrabold uppercase text-slate-400 tracking-wider">Provenance</h3>
            <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-xs bg-slate-950/20 p-4 rounded-xl border border-slate-800/40">
              <div>
                <p className="text-[9px] text-slate-500 font-semibold uppercase">Scope Category</p>
                <p className="text-slate-200 font-medium mt-0.5">Scope {record.scope} — {record.category}</p>
              </div>
              <div>
                <p className="text-[9px] text-slate-500 font-semibold uppercase">Source System</p>
                <p className="text-slate-200 font-medium mt-0.5">{record.source_system} ({record.source_row_id})</p>
              </div>
              <div className="mt-2">
                <p className="text-[9px] text-slate-500 font-semibold uppercase">Facility Code</p>
                <p className="text-slate-200 font-medium mt-0.5">{record.facility_code || 'None'}</p>
              </div>
              <div className="mt-2">
                <p className="text-[9px] text-slate-500 font-semibold uppercase">Activity Date</p>
                <p className="text-slate-200 font-medium mt-0.5">{record.activity_date}</p>
              </div>
            </div>
          </div>

          {/* Raw Ingestion Data */}
          {record.raw_row?.raw_data && (
            <div className="space-y-3">
              <h3 className="text-xs font-extrabold uppercase text-slate-400 tracking-wider">Raw Ingested JSON</h3>
              <pre className="p-4 rounded-xl bg-slate-950 text-[11px] text-slate-400 overflow-x-auto border border-slate-800/60 max-h-[160px]">
                {JSON.stringify(record.raw_row.raw_data, null, 2)}
              </pre>
            </div>
          )}

          {/* Audit Log / History */}
          <div className="space-y-4">
            <h3 className="text-xs font-extrabold uppercase text-slate-400 tracking-wider flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-slate-500" /> Audit Log Trail
            </h3>
            
            <div className="relative border-l border-slate-800 ml-3 pl-5 space-y-4 text-xs">
              {history.length > 0 ? (
                history.map((log) => (
                  <div key={log.id} className="relative">
                    {/* Bullet */}
                    <span className="absolute -left-[27px] top-1.5 w-3 h-3 rounded-full bg-slate-900 border-2 border-slate-700 flex items-center justify-center"></span>
                    
                    <div className="bg-slate-950/20 p-3 rounded-xl border border-slate-800/40">
                      <div className="flex items-center justify-between text-[10px] text-slate-500 font-semibold">
                        <span className="text-emerald-400 font-bold uppercase">{log.action}</span>
                        <span>{new Date(log.timestamp).toLocaleString()}</span>
                      </div>
                      
                      <div className="mt-1 text-slate-300">
                        {log.action === 'EDITED' ? (
                          <p>Record values modified by audit team.</p>
                        ) : log.action === 'APPROVED' ? (
                          <p>Approved for ledger audit lock.</p>
                        ) : log.action === 'FLAGGED' ? (
                          <p>Flagged for secondary check.</p>
                        ) : log.action === 'REJECTED' ? (
                          <p>Record rejected from emission inventories.</p>
                        ) : (
                          <p>Audit status updated.</p>
                        )}
                      </div>

                      {log.after_state?.review_notes && (
                        <p className="mt-1.5 bg-slate-950/50 p-2 rounded text-slate-400 italic text-[11px]">
                          Note: "{log.after_state.review_notes}"
                        </p>
                      )}

                      <div className="mt-2 text-[9px] text-slate-500 flex justify-between font-medium">
                        <span>Actor: {log.actor?.email || 'System'}</span>
                        <span>IP: {log.ip_address || 'Internal'}</span>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-slate-500 italic py-2">No audit logs recorded.</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default RecordDrawer;
