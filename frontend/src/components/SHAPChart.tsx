"use client";

import React, { useState } from 'react';
import { useTradeStore } from '../store/useTradeStore';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts';
import { HelpCircle, AlertCircle } from 'lucide-react';

export default function SHAPChart() {
  const { currentResult } = useTradeStore();
  const [selectedCountry, setSelectedCountry] = useState<string>('');

  if (!currentResult || !currentResult.shap_explainability) {
    return (
      <div className="h-[300px] flex items-center justify-center text-slate-500 text-sm glass-panel rounded-3xl p-6">
        No explainability data loaded. Run an analysis to generate factor attributions.
      </div>
    );
  }

  const explainData = currentResult.shap_explainability;
  const localAttributions = explainData.local_attributions || {};
  const countries = Object.keys(localAttributions);

  // Set default country if empty
  const activeCountry = selectedCountry || countries[0] || '';

  const activeAttrib = localAttributions[activeCountry];
  if (!activeAttrib) {
    return (
      <div className="h-[300px] flex items-center justify-center text-slate-500 text-sm glass-panel rounded-3xl p-6">
        Select a country to view attributions.
      </div>
    );
  }

  // Format contributions for Recharts
  const chartData = Object.entries(activeAttrib.contributions).map(([factor, val]) => ({
    name: factor.toUpperCase(),
    value: parseFloat((val as number).toFixed(4))
  }));

  // Sort by contribution magnitude
  chartData.sort((a, b) => Math.abs(b.value) - Math.abs(a.value));

  const formatTooltip = (value: any) => {
    const numVal = typeof value === 'number' ? value : parseFloat(value);
    return [numVal >= 0 ? `+${numVal.toFixed(4)}` : `${numVal.toFixed(4)}`, 'Attribution Impact'];
  };

  return (
    <div className="w-full glass-panel rounded-3xl p-6 border border-white/5 flex flex-col gap-4">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-extrabold text-slate-200 tracking-wide flex items-center gap-1.5">
            AI Score Attribution
          </h3>
          <p className="text-xs text-slate-500 font-medium">
            Shows how each agent's evaluation drove the final score relative to the baseline.
          </p>
        </div>

        {/* Dropdown Selector */}
        <select
          value={activeCountry}
          onChange={(e) => setSelectedCountry(e.target.value)}
          className="bg-slate-900 border border-white/5 text-slate-300 text-xs px-3 py-2 rounded-xl font-mono focus:outline-none focus:border-blue-500"
        >
          {countries.map(c => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      <div className="bg-slate-950/40 p-4 rounded-2xl border border-white/[0.02] flex items-start gap-3">
        <HelpCircle className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
        <div className="text-xs text-slate-400 leading-relaxed">
          <span className="font-semibold text-slate-200">Baseline Score: </span> 
          {activeAttrib.baseline_score.toFixed(2)} | 
          <span className="font-semibold text-slate-200"> Final AI Score: </span> 
          {activeAttrib.actual_score.toFixed(2)}
          <p className="mt-1">
            Factors extending to the <span className="text-emerald-400 font-semibold">right (+)</span> increased the score, while factors extending to the <span className="text-red-400 font-semibold">left (-)</span> decreased the score from the average baseline.
          </p>
        </div>
      </div>

      <div className="h-[250px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 10, right: 30, left: 40, bottom: 10 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" horizontal={false} />
            <XAxis type="number" stroke="#64748b" fontSize={10} domain={['-dataMax - 0.05', 'dataMax + 0.05']} />
            <YAxis dataKey="name" type="category" stroke="#64748b" fontSize={10} width={80} />
            <Tooltip 
              formatter={formatTooltip}
              contentStyle={{ background: '#020617', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px' }}
            />
            <ReferenceLine x={0} stroke="rgba(255,255,255,0.2)" />
            <Bar dataKey="value" radius={[0, 4, 4, 0]}>
              {chartData.map((entry, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={entry.value >= 0 ? '#10b981' : '#ef4444'} 
                  fillOpacity={0.7}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
