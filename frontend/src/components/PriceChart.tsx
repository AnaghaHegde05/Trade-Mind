"use client";

import React from 'react';
import { useTradeStore } from '../store/useTradeStore';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { TrendingUp, HelpCircle } from 'lucide-react';

export default function PriceChart() {
  const { currentResult } = useTradeStore();

  if (!currentResult || !currentResult.global_pricing) {
    return (
      <div className="h-[300px] flex items-center justify-center text-slate-500 text-sm glass-panel rounded-3xl p-6">
        No pricing data loaded. Run analysis to display commodity pricing forecast.
      </div>
    );
  }

  const { price_history, price_forecast } = currentResult.global_pricing;

  // Format data for chart
  const years = Array.from(new Set([
    ...Object.keys(price_history).map(Number),
    ...Object.keys(price_forecast).map(Number)
  ])).sort((a, b) => a - b);

  const chartData = years.map(yr => ({
    year: String(yr),
    historical: price_history[yr] ? parseFloat(price_history[yr].toFixed(2)) : null,
    forecasted: price_forecast[yr] ? parseFloat(price_forecast[yr].toFixed(2)) : null,
  }));

  // Append latest historical value to forecasted line so it links up smoothly
  const histYears = Object.keys(price_history).map(Number).sort((a, b) => a - b);
  if (histYears.length > 0) {
    const lastHistYear = histYears[histYears.length - 1];
    const lastHistVal = price_history[lastHistYear];
    
    const fcDataPoint = chartData.find(d => d.year === String(lastHistYear));
    if (fcDataPoint) {
      fcDataPoint.forecasted = parseFloat(lastHistVal.toFixed(2));
    }
  }

  return (
    <div className="w-full glass-panel rounded-3xl p-6 border border-white/5 flex flex-col gap-4">
      <div>
        <h3 className="text-base font-extrabold text-slate-200 tracking-wide flex items-center gap-1.5">
          Global Pricing Forecast ({currentResult.commodity_name})
        </h3>
        <p className="text-xs text-slate-500 font-medium">
          Historical trade values integrated with Prophet/XGBoost dynamic price predictions.
        </p>
      </div>

      <div className="h-[250px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={chartData}
            margin={{ top: 10, right: 10, left: 10, bottom: 0 }}
          >
            <defs>
              <linearGradient id="colorHist" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2}/>
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="colorFC" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.2}/>
                <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
            <XAxis dataKey="year" stroke="#64748b" fontSize={10} />
            <YAxis 
              stroke="#64748b" 
              fontSize={10} 
              tickFormatter={(v) => `$${v}`}
              domain={['dataMin - 200', 'dataMax + 200']}
            />
            <Tooltip 
              formatter={(value) => [`$${value}/Ton`, '']}
              contentStyle={{ background: '#020617', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px' }}
            />
            <Legend verticalAlign="top" height={36} iconType="circle" />
            <Area 
              name="Historical Price" 
              type="monotone" 
              dataKey="historical" 
              stroke="#3b82f6" 
              strokeWidth={2.5}
              fillOpacity={1} 
              fill="url(#colorHist)" 
              connectNulls
            />
            <Area 
              name="Forecasted Price" 
              type="monotone" 
              dataKey="forecasted" 
              stroke="#f59e0b" 
              strokeWidth={2.5}
              strokeDasharray="4 4"
              fillOpacity={1} 
              fill="url(#colorFC)" 
              connectNulls
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
