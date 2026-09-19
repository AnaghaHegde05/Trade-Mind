"use client";

import React, { useEffect, useRef, useState } from 'react';
import { useTradeStore } from '../store/useTradeStore';
import { Terminal, Shield, Cpu, RefreshCw, Layers } from 'lucide-react';

export default function LogTerminal() {
  const { logs, status, progress, activeAgent, clearLogs } = useTradeStore();
  const terminalEndRef = useRef<HTMLDivElement>(null);
  const [selectedAgentFilter, setSelectedAgentFilter] = useState<string>('ALL');

  useEffect(() => {
    // Scroll to bottom on new logs
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Unique agents list for filter
  const agents = ['ALL', ...Array.from(new Set(logs.map(l => l.agent).filter(Boolean)))];

  const filteredLogs = selectedAgentFilter === 'ALL'
    ? logs
    : logs.filter(l => l.agent === selectedAgentFilter);

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'ERROR': return 'text-red-400 font-bold';
      case 'WARNING': return 'text-amber-400';
      case 'DEBUG': return 'text-slate-500';
      default: return 'text-emerald-400';
    }
  };

  const getAgentBadgeColor = (agent: string) => {
    if (agent === 'System') return 'bg-slate-800 text-slate-300 border border-slate-700';
    if (agent === 'Market Agent') return 'bg-blue-950 text-blue-300 border border-blue-800';
    if (agent === 'Decision Agent') return 'bg-purple-950 text-purple-300 border border-purple-800';
    return 'bg-emerald-950 text-emerald-300 border border-emerald-800';
  };

  return (
    <div className="w-full glass-panel rounded-3xl overflow-hidden shadow-2xl flex flex-col border border-white/5 h-[500px]">
      {/* Header */}
      <div className="bg-slate-950/80 px-6 py-4 border-b border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 rounded-full bg-red-500" />
          <div className="w-3 h-3 rounded-full bg-yellow-500" />
          <div className="w-3 h-3 rounded-full bg-green-500" />
          <span className="text-sm font-mono text-slate-400 font-semibold ml-2 flex items-center gap-1.5">
            <Terminal className="w-4 h-4 text-blue-500" />
            agent_orchestrator@trademind:~
          </span>
        </div>
        
        {/* Filter */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs text-slate-500 font-bold uppercase tracking-wider">
            <Layers className="w-3 h-3" /> Filter:
          </div>
          <select 
            value={selectedAgentFilter}
            onChange={(e) => setSelectedAgentFilter(e.target.value)}
            className="bg-slate-900 border border-white/5 text-slate-300 text-xs px-2.5 py-1.5 rounded-xl font-mono focus:outline-none focus:border-blue-500"
          >
            {agents.map(agent => (
              <option key={agent} value={agent}>{agent}</option>
            ))}
          </select>
          <button 
            onClick={clearLogs}
            className="text-xs text-slate-500 hover:text-white px-2.5 py-1.5 bg-slate-900 rounded-xl hover:bg-slate-800 border border-white/5 font-mono"
          >
            Clear
          </button>
        </div>
      </div>

      {/* Terminal logs content */}
      <div className="flex-1 terminal-window p-6 overflow-y-auto terminal-scroll font-mono text-xs leading-relaxed">
        {filteredLogs.length === 0 ? (
          <div className="text-slate-600 italic h-full flex items-center justify-center">
            {"Waiting for agents execution to begin... Triggers logged in real-time."}
          </div>
        ) : (
          filteredLogs.map((log, idx) => (
            <div key={idx} className="mb-2.5 flex items-start gap-2.5 border-b border-white/[0.01] pb-1.5">
              <span className="text-slate-600 select-none">[{log.timestamp}]</span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase select-none ${getAgentBadgeColor(log.agent)}`}>
                {log.agent}
              </span>
              <span className={`font-semibold uppercase select-none ${getLevelColor(log.level)}`}>
                {log.level}
              </span>
              <span className="text-slate-300 select-all whitespace-pre-wrap">{log.message}</span>
            </div>
          ))
        )}
        <div ref={terminalEndRef} />
      </div>

      {/* Status Bar */}
      <div className="bg-slate-950/80 px-6 py-4 border-t border-white/5 flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Active agent */}
        <div className="flex items-center gap-3">
          <Cpu className={`w-5 h-5 text-blue-500 ${status === 'RUNNING' ? 'animate-spin' : ''}`} />
          <div>
            <div className="text-[10px] font-bold uppercase text-slate-500 tracking-wider">Active Execution Task</div>
            <div className="text-sm font-semibold text-slate-200">{activeAgent}</div>
          </div>
        </div>

        {/* Progress bar */}
        <div className="flex-1 w-full max-w-md">
          <div className="flex justify-between text-xs font-semibold text-slate-400 mb-1">
            <span>Workflow Completion Progress</span>
            <span>{progress}%</span>
          </div>
          <div className="w-full bg-slate-900 rounded-full h-2.5 overflow-hidden border border-white/5">
            <div 
              className="bg-gradient-to-r from-blue-600 to-emerald-500 h-full rounded-full transition-all duration-500" 
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Status label */}
        <div className="px-4 py-1.5 rounded-full text-xs font-extrabold uppercase tracking-wide bg-slate-900 border border-white/5 text-slate-300">
          Status: <span className={
            status === 'SUCCESS' ? 'text-emerald-400' :
            status === 'FAILED' ? 'text-red-400' :
            status === 'RUNNING' ? 'text-blue-400 animate-pulse' : 'text-slate-500'
          }>{status}</span>
        </div>
      </div>
    </div>
  );
}
