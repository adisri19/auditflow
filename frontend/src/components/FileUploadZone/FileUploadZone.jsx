import React, { useState, useRef } from 'react';
import { UploadCloud, File, AlertCircle, CheckCircle } from 'lucide-react';

const FileUploadZone = ({ onFileSelected, accept, title }) => {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState(null);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const validateFile = (selectedFile) => {
    if (!selectedFile) return false;
    const extension = selectedFile.name.split('.').pop().toLowerCase();
    const acceptedExtensions = accept.replace(/\s/g, '').split(',');
    
    // Convert e.g. '.csv' -> 'csv'
    const isAccepted = acceptedExtensions.some(ext => {
      const cleanExt = ext.replace('.', '').toLowerCase();
      return cleanExt === extension;
    });

    if (!isAccepted) {
      setError(`Invalid file type. Please upload one of: ${accept}`);
      setFile(null);
      return false;
    }

    setError(null);
    setFile(selectedFile);
    onFileSelected(selectedFile);
    return true;
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      validateFile(e.target.files[0]);
    }
  };

  const onButtonClick = () => {
    inputRef.current.click();
  };

  return (
    <div className="space-y-4">
      <div
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        onClick={onButtonClick}
        className={`border-2 border-dashed rounded-2xl p-8 flex flex-col items-center justify-center cursor-pointer transition-all min-h-[220px] ${
          dragActive 
            ? 'border-brand-500 bg-brand-500/5 shadow-inner' 
            : 'border-slate-800 bg-slate-900/30 hover:border-brand-500/50 hover:bg-slate-900/50'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          accept={accept}
          onChange={handleChange}
        />
        
        <div className="w-12 h-12 rounded-xl bg-slate-800/80 flex items-center justify-center mb-4 transition-all">
          <UploadCloud className={`w-6 h-6 ${dragActive ? 'text-brand-400' : 'text-slate-400'}`} />
        </div>

        <p className="text-sm font-semibold text-slate-200 text-center mb-1">
          Drag and drop your file here, or <span className="text-emerald-400 underline hover:text-emerald-300">browse</span>
        </p>
        <p className="text-xs text-slate-500 text-center">
          {title || `Accepts ${accept}`}
        </p>

        {file && (
          <div className="mt-6 flex items-center gap-3 px-4 py-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold">
            <File className="w-4 h-4" />
            <span className="truncate max-w-[200px]">{file.name}</span>
            <span>({(file.size / 1024).toFixed(1)} KB)</span>
            <CheckCircle className="w-4 h-4 fill-emerald-500/10 text-emerald-400 shrink-0" />
          </div>
        )}
      </div>

      {error && (
        <div className="flex items-center gap-2.5 px-4 py-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-semibold">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
};

export default FileUploadZone;
