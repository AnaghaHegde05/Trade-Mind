"use client";

import React, { useState } from 'react';
import { useTradeStore } from '../store/useTradeStore';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Layers } from 'lucide-react';

export default function DemandChart() {
  const { currentResult } = useTradeStore();
  const [selectedCountry, setSelectedCountry] = useState<string>('');

  if (!currentResult || !currentResult.countries) {
    return (
      <div className="h-[300px] flex items-center justify-center text-slate-500 text-sm glass-panel rounded-3xl p-6">
        No country-wise demand data loaded.
      </div>
    );
  }

  const countriesData = currentResult.countries;
  const countriesList = countriesData.map(c => c.country);
  const activeCountry = selectedCountry || countriesList[0] || '';

  const countryItem = countriesData.find(c => c.country === activeCountry);
  if (!countryItem) {
    return (
      <div className="h-[300px] flex items-center justify-center text-slate-500 text-sm glass-panel rounded-3xl p-6">
        Select a country to view demand trends.
      </div>
    );
  }

  const history = countryItem.trade_volume_history || {};
  const forecast = countryItem.trade_volume_forecast || {};

  const years = Array.from(new Set([
    ...Object.keys(history).map(Number),
    ...Object.keys(forecast).map(Number)
  ])).sort((a, b) => a - b);

  const chartData = years.map(yr => ({
    year: String(yr),
    historical: history[yr] ? parseFloat((history[yr] / 1_000_000).toFixed(2)) : null, // Convert to Million USD
    forecasted: forecast[yr] ? parseFloat((forecast[yr] / 1_000_000).toFixed(2)) : null,
  }));

  // Smooth connector
  const histYears = Object.keys(history).map(Number).sort((a, b) => a - b);
  if (histYears.length > 0) {
    const lastHistYear = histYears[histYears.length - 1];
    const lastHistVal = history[lastHistYear];
    
    const fcDataPoint = chartData.find(d => d.year === String(lastHistYear));
    if (fcDataPoint) {
      fcDataPoint.forecasted = parseFloat((lastHistVal / 1_000_000).toFixed(2));
    }
  }

  return (
    <div className="w-full glass-panel rounded-3xl p-6 border border-white/5 flex flex-col gap-4">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-extrabold text-slate-200 tracking-wide flex items-center gap-1.5">
            Country Demand Volume (Trade Value)
          </h3>
          <p className="text-xs text-slate-500 font-medium">
            Aggregated imports history and predicted growth trends in US $ Millions.
          </p>
        </div>

        {/* Dropdown Selector */}
        <select
          value={activeCountry}
          onChange={(e) => setSelectedCountry(e.target.value)}
          className="bg-slate-900 border border-white/5 text-slate-300 text-xs px-3 py-2 rounded-xl font-mono focus:outline-none focus:border-blue-500"
        >
          {countriesList.map(c => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      <div className="h-[250px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={chartData}
            margin={{ top: 10, right: 10, left: 10, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
            <XAxis dataKey="year" stroke="#64748b" fontSize={10} />
            <YAxis 
              stroke="#64748b" 
              fontSize={10} 
              tickFormatter={(v) => `$${v}M`}
            />
            <Tooltip 
              formatter={(value) => [`$${value}M USD`, '']}
              contentStyle={{ background: '#020617', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px' }}
            />
            <Legend verticalAlign="top" height={36} iconType="circle" />
            <Line 
              name="Historical Volume" 
              type="monotone" 
              dataKey="historical" 
              stroke="#10b981" 
              strokeWidth={3}
              dot={{ r: 4, strokeWidth: 1 }}
              activeDot={{ r: 6 }}
              connectNulls
            />
            <Line 
              name="Forecasted Volume" 
              type="monotone" 
              dataKey="forecasted" 
              stroke="#ef4444" 
              strokeWidth={3}
              strokeDasharray="5 5"
              dot={{ r: 4, strokeWidth: 1 }}
              activeDot={{ r: 6 }}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
