import React from 'react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer 
} from 'recharts';

const ScopeChart = ({ data }) => {
  // Format months like '2024-01' -> 'Jan 2024'
  const formatMonth = (tickItem) => {
    try {
      const [year, month] = tickItem.split('-');
      const date = new Date(year, month - 1);
      return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
    } catch {
      return tickItem;
    }
  };

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl shadow-xl backdrop-blur-md">
          <p className="text-xs font-bold text-slate-400 mb-2">{formatMonth(label)}</p>
          {payload.map((p, idx) => (
            <div key={idx} className="flex items-center gap-2 text-xs font-semibold" style={{ color: p.color }}>
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color }}></span>
              <span>{p.name}: {p.value.toFixed(2)} tCO₂e</span>
            </div>
          ))}
          <div className="border-t border-slate-800 mt-2 pt-2 flex items-center justify-between text-xs font-bold text-slate-100">
            <span>Total:</span>
            <span>{payload.reduce((acc, curr) => acc + curr.value, 0).toFixed(2)} tCO₂e</span>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="w-full h-80">
      {data && data.length > 0 ? (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{ top: 20, right: 30, left: 0, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" opacity={0.4} vertical={false} />
            <XAxis 
              dataKey="month" 
              tickFormatter={formatMonth} 
              stroke="#64748b" 
              fontSize={11} 
              tickLine={false}
              axisLine={false}
            />
            <YAxis 
              stroke="#64748b" 
              fontSize={11} 
              tickLine={false}
              axisLine={false}
              label={{ value: 'tCO₂e', angle: -90, position: 'insideLeft', fill: '#64748b', style: { textAnchor: 'middle', fontSize: 11, fontWeight: 500 } }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend 
              verticalAlign="top" 
              height={36} 
              iconType="circle" 
              iconSize={8}
              wrapperStyle={{ fontSize: 11, fontWeight: 500 }}
            />
            <Bar dataKey="scope1" name="Scope 1 (Direct)" stackId="a" fill="#10b981" radius={[0, 0, 0, 0]} />
            <Bar dataKey="scope2" name="Scope 2 (Indirect Grid)" stackId="a" fill="#0ea5e9" radius={[0, 0, 0, 0]} />
            <Bar dataKey="scope3" name="Scope 3 (Value Chain)" stackId="a" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <div className="flex h-full items-center justify-center text-slate-500 text-sm">
          No emissions timeline data found.
        </div>
      )}
    </div>
  );
};

export default ScopeChart;
