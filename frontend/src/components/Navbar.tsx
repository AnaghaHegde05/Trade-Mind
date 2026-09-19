"use client";

import React from 'react';
import { useTradeStore } from '../store/useTradeStore';
import { BarChart2, History, Database, BarChart3 } from 'lucide-react';

export default function Navbar() {
  const { activeTab, setActiveTab } = useTradeStore();

  const navItems = [
    { id: 'landing', label: 'Home', icon: Database },
    { id: 'dashboard', label: 'Dashboard', icon: BarChart2 },
    { id: 'reports', label: 'Reports', icon: History }
  ];

  return (
    <nav className="sticky top-0 z-50 w-full glass-panel border-b border-white/5 py-4 px-6 md:px-12 flex flex-col md:flex-row items-center justify-between gap-4">
      {/* Brand */}
      <div 
        className="flex items-center gap-2 cursor-pointer"
        onClick={() => setActiveTab('landing')}
      >
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-emerald-500 flex items-center justify-center font-bold text-white shadow-lg shadow-blue-500/20">
          TM
        </div>
        <div>
          <span className="font-extrabold text-lg bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400">
            TRADE MIND
          </span>
          <span className="text-xs block text-slate-500 font-semibold tracking-wider">TRADE INTELLIGENCE</span>
        </div>
      </div>

      {/* Nav links */}
      <div className="flex items-center flex-wrap justify-center gap-2 md:gap-4 bg-slate-950/40 p-1.5 rounded-2xl border border-white/5">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold tracking-wide transition-all ${
                isActive 
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-600/10' 
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>

      {/* Empty div for balancing flex layout */}
      <div className="hidden md:block w-32"></div>
    </nav>
  );
}
