import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Upload, 
  FileText, 
  Zap, 
  Plane,
  AlertCircle,
  Clock,
  Sparkles
} from 'lucide-react';
import FileUploadZone from '../components/FileUploadZone/FileUploadZone';
import { uploadBatch } from '../api/batches';

const UploadPage = () => {
  const [activeTab, setActiveTab] = useState('SAP_FUEL_PROC');
  const [selectedFile, setSelectedFile] = useState(null);
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const tabs = [
    {
      id: 'SAP_FUEL_PROC',
      name: 'SAP Fuel & Procurement',
      desc: 'Ingest raw SE16 material receipts, diesel purchases, and procurement logs.',
      accept: '.xlsx,.csv,.txt',
      icon: FileText
    },
    {
      id: 'UTILITY_ELEC',
      name: 'Utility Electricity',
      desc: 'Ingest UK meter logs or US utility portal billing exports.',
      accept: '.csv',
      icon: Zap
    },
    {
      id: 'CORP_TRAVEL',
      name: 'Corporate Travel',
      desc: 'Ingest Navan/Concur travel lists including flight classes, hotels, and rentals.',
      accept: '.csv',
      icon: Plane
    }
  ];

  const currentTab = tabs.find(t => t.id === activeTab);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile) {
      setError('Please select or drop a valid file first.');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      const batch = await uploadBatch(activeTab, selectedFile, notes);
      navigate(`/batches/${batch.id}`);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to upload and parse file. Please verify file columns.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      {/* Page Header */}
      <div className="border-b border-slate-800 pb-5">
        <span className="text-[10px] uppercase font-black tracking-widest text-emerald-400">Ingestion Pipeline</span>
        <h2 className="text-2xl font-black text-slate-100 mt-1 tracking-tight">Upload Raw Data Files</h2>
        <p className="text-xs text-slate-500 mt-1">
          Breathe ESG engine maps, normalizes, and classifies raw spreadsheets into audit-ready Scope records.
        </p>
      </div>

      {/* Tabs list */}
      <div className="grid grid-cols-3 gap-3 bg-slate-900/40 p-1.5 rounded-2xl border border-slate-800/80">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = tab.id === activeTab;
          return (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id);
                setSelectedFile(null);
                setError(null);
              }}
              className={`flex flex-col md:flex-row items-center gap-2.5 px-4 py-3.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                isActive
                  ? 'bg-gradient-to-r from-brand-600 to-brand-500 text-white shadow-lg shadow-brand-500/10'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span className="text-center md:text-left leading-tight">{tab.name}</span>
            </button>
          );
        })}
      </div>

      {/* Active Tab Explanation card */}
      <div className="bg-slate-900/20 border border-slate-800/40 rounded-2xl p-6 flex gap-4 items-start">
        <div className="w-10 h-10 rounded-xl bg-slate-800/80 flex items-center justify-center shrink-0">
          <Sparkles className="w-5 h-5 text-emerald-400" />
        </div>
        <div>
          <h4 className="text-xs font-bold text-slate-300">Parser Description</h4>
          <p className="text-xs text-slate-500 mt-1 leading-relaxed">
            {currentTab.desc}
          </p>
        </div>
      </div>

      {/* Upload Form */}
      <form onSubmit={handleUpload} className="space-y-6">
        {/* File Dropzone */}
        <div>
          <label className="block text-xs font-bold text-slate-400 uppercase tracking-wide mb-2.5">
            Select Spreadsheet File
          </label>
          <FileUploadZone
            key={activeTab} // Resets file selection when switching tabs
            accept={currentTab.accept}
            title={`Select a ${currentTab.accept} file`}
            onFileSelected={(file) => {
              setSelectedFile(file);
              setError(null);
            }}
          />
        </div>

        {/* Notes */}
        <div>
          <label className="block text-xs font-bold text-slate-400 uppercase tracking-wide mb-2.5">
            Ingestion Notes (Optional)
          </label>
          <textarea
            rows="3"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Add context for this data upload (e.g., 'Q3 fuel billing sheets from plants')..."
            className="w-full bg-slate-900/40 border border-slate-800 rounded-2xl px-4 py-3 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-all resize-none"
          />
        </div>

        {error && (
          <div className="flex items-center gap-2.5 px-4 py-3 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-semibold">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={loading || !selectedFile}
          className="w-full flex justify-center items-center gap-2 py-4 px-4 rounded-2xl border border-transparent text-sm font-bold text-white bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-500 shadow-lg shadow-brand-500/10 transition-all cursor-pointer disabled:opacity-50"
        >
          {loading ? (
            <>
              <Clock className="w-4 h-4 animate-spin" /> Ingesting and Running Calculations...
            </>
          ) : (
            <>
              <Upload className="w-4 h-4" /> Start Ingestion Run
            </>
          )}
        </button>
      </form>
    </div>
  );
};

export default UploadPage;
