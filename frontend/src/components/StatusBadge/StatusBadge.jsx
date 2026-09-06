import React from 'react';

const StatusBadge = ({ status }) => {
  const styles = {
    PENDING: {
      bg: 'bg-amber-500/10',
      text: 'text-amber-400',
      border: 'border-amber-500/20',
      dot: 'bg-amber-400',
      label: 'Pending Review'
    },
    APPROVED: {
      bg: 'bg-emerald-500/10',
      text: 'text-emerald-400',
      border: 'border-emerald-500/20',
      dot: 'bg-emerald-400',
      label: 'Approved'
    },
    FLAGGED: {
      bg: 'bg-orange-500/10',
      text: 'text-orange-400',
      border: 'border-orange-500/20',
      dot: 'bg-orange-400',
      label: 'Flagged'
    },
    REJECTED: {
      bg: 'bg-rose-500/10',
      text: 'text-rose-400',
      border: 'border-rose-500/20',
      dot: 'bg-rose-400',
      label: 'Rejected'
    },
    LOCKED: {
      bg: 'bg-sky-500/10',
      text: 'text-sky-400',
      border: 'border-sky-500/20',
      dot: 'bg-sky-400',
      label: 'Locked'
    }
  };

  const style = styles[status] || styles.PENDING;

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${style.bg} ${style.text} ${style.border}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`}></span>
      {style.label}
    </span>
  );
};

export default StatusBadge;
