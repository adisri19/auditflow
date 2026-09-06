import React from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import RecordDrawer from '../components/RecordDrawer/RecordDrawer';

const RecordDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();

  return (
    <div className="h-full flex flex-col">
      <div className="mb-4 flex items-center gap-3">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-sm text-slate-400 hover:text-slate-200"
        >
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
        <span className="text-slate-600">|</span>
        <Link to="/review" className="text-sm text-emerald-400 hover:text-emerald-300">
          Review console
        </Link>
      </div>
      <RecordDrawer
        recordId={id}
        variant="page"
        onClose={() => navigate('/review')}
      />
    </div>
  );
};

export default RecordDetail;
