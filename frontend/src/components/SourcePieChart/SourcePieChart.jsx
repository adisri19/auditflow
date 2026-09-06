import React from 'react';
import { 
  PieChart, 
  Pie, 
  Cell, 
  Tooltip, 
  Legend, 
  ResponsiveContainer 
} from 'recharts';

const SourcePieChart = ({ data }) => {
  const SOURCE_NAMES = {
    SAP_FUEL_PROC: 'SAP Fuel & Procurement',
    UTILITY_ELEC: 'Utility Electricity',
    CORP_TRAVEL: 'Corporate Travel'
  };

  const COLORS = {
    SAP_FUEL_PROC: '#10b981', // Emerald
    UTILITY_ELEC: '#0ea5e9',  // Sky
    CORP_TRAVEL: '#8b5cf6'    // Violet
  };

  const chartData = Object.entries(data || {})
    .map(([key, val]) => ({
      name: SOURCE_NAMES[key] || key,
      value: val,
      color: COLORS[key] || '#94a3b8'
    }))
    .filter(item => item.value > 0);

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-slate-900/90 border border-slate-800 px-3 py-2 rounded-xl shadow-xl backdrop-blur-md">
          <p className="text-xs font-bold text-slate-200" style={{ color: data.color }}>
            {data.name}
          </p>
          <p className="text-xs font-semibold text-slate-400 mt-1">
            {data.value} records ({((data.value / chartData.reduce((acc, c) => acc + c.value, 0)) * 100).toFixed(0)}%)
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="w-full h-80 flex flex-col justify-center">
      {chartData.length > 0 ? (
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={90}
              paddingAngle={4}
              dataKey="value"
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} stroke="rgba(2, 6, 23, 0.4)" strokeWidth={2} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
            <Legend 
              verticalAlign="bottom" 
              align="center"
              height={36} 
              iconType="circle" 
              iconSize={8}
              wrapperStyle={{ fontSize: 11, fontWeight: 500 }}
            />
          </PieChart>
        </ResponsiveContainer>
      ) : (
        <div className="flex h-full items-center justify-center text-slate-500 text-sm">
          No data source metrics available.
        </div>
      )}
    </div>
  );
};

export default SourcePieChart;
