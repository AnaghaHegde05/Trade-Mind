"use client";

import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useTradeStore, LogEntry, ReportData } from '../store/useTradeStore';
import Navbar from '../components/Navbar';
import LogTerminal from '../components/LogTerminal';
import SHAPChart from '../components/SHAPChart';
import PriceChart from '../components/PriceChart';
import DemandChart from '../components/DemandChart';
import {
  Play, Shield, DollarSign, Calendar, Globe, Award, CheckCircle,
  AlertTriangle, Upload, Eye, FileText, ChevronRight, BarChart3, Info, Server, RefreshCw, Phone, Mail, MapPin
} from 'lucide-react';

// Backend API location. Falls back to localhost for local dev, but reads
// from an env var so this can be deployed anywhere without code changes.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws');

export default function Home() {
  const {
    activeTab, setActiveTab, taskId, setTaskId, status, setStatus,
    setProgress, logs, addLog, currentResult, setCurrentResult,
    reportsList, setReportsList, healthStatus, setHealthStatus, clearLogs
  } = useTradeStore();

  // Trigger Form Inputs
  const [hsCode, setHsCode] = useState('5201');
  const [qtyTons, setQtyTons] = useState('50');
  const [commodityName, setCommodityName] = useState('cotton');

  // File Upload States
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadType, setUploadType] = useState('market');
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadLoading, setUploadLoading] = useState(false);

  // Poll Reports List
  const fetchReports = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/reports`);
      setReportsList(response.data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchReports();
  }, [activeTab]);

  // Handle WebSocket log streaming
  useEffect(() => {
    let ws: WebSocket | null = null;

    // Connect to WebSocket regardless of active status to capture system logs
    const connectWS = () => {
      ws = new WebSocket(`${WS_BASE_URL}/ws`);

      ws.onmessage = (event) => {
        try {
          const logEntry: LogEntry = JSON.parse(event.data);
          addLog(logEntry);
        } catch (e) {
          // Plain text message
        }
      };

      ws.onclose = () => {
        // Attempt reconnect after 5s
        setTimeout(connectWS, 5000);
      };

      ws.onerror = () => {
        ws?.close();
      };
    };

    connectWS();
    return () => {
      ws?.close();
    };
  }, [addLog]);

  // Handle SUCCESS status loading
  useEffect(() => {
    const loadResults = async () => {
      if (status === 'SUCCESS' && taskId) {
        try {
          const response = await axios.get(`${API_BASE_URL}/reports/${taskId}`);
          setCurrentResult(response.data);
          setActiveTab('dashboard'); // Redirect to dashboard once complete
        } catch (e) {
          console.error("Failed to load results", e);
        }
      }
    };
    loadResults();
  }, [status, taskId, setCurrentResult, setActiveTab]);

  // Trigger analysis
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearLogs();
    setStatus('QUEUED');
    setProgress(0);
    setActiveTab('dashboard'); // Navigate immediately to dashboard (showing progress and terminal)

    try {
      const response = await axios.post(`${API_BASE_URL}/analyze`, {
        hs_code: hsCode,
        quantity_tons: parseFloat(qtyTons),
        commodity_name: commodityName
      });
      setTaskId(response.data.task_id);
    } catch (e: any) {
      setStatus('FAILED');
      addLog({
        timestamp: new Date().toLocaleTimeString(),
        level: 'ERROR',
        logger: 'WebUI',
        agent: 'System',
        message: `Trigger failed: ${e.response?.data?.detail || e.message}`
      });
    }
  };

  // Handle File Upload
  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      setUploadError("Please select a file.");
      return;
    }
    setUploadLoading(true);
    setUploadError(null);
    setUploadStatus(null);

    const formData = new FormData();
    formData.append('file', uploadFile);
    formData.append('dataset_type', uploadType);

    try {
      const response = await axios.post(`${API_BASE_URL}/datasets/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setUploadStatus(`File ${response.data.filename} uploaded successfully to ${uploadType} folder!`);
      setUploadFile(null);
    } catch (e: any) {
      setUploadError(e.response?.data?.detail || "Upload failed. Verify file schema.");
    } finally {
      setUploadLoading(false);
    }
  };

  // Load Past Report
  const handleLoadReport = async (id: string) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/reports/${id}`);
      setCurrentResult(response.data);
      setTaskId(id);
      setStatus('SUCCESS');
      setActiveTab('dashboard');
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      {/* Main Body */}
      <main className="flex-1 w-full max-w-7xl mx-auto px-6 md:px-12 py-10 flex flex-col gap-10">

        {/* ==================== 1. LANDING PAGE ==================== */}
        {activeTab === 'landing' && (
          <div className="flex flex-col gap-12">
            {/* Hero Panel */}
            <div className="text-center flex flex-col items-center gap-6 max-w-3xl mx-auto">
              <span className="px-4 py-1.5 rounded-full bg-blue-600/10 border border-blue-500/20 text-xs font-bold text-blue-400 uppercase tracking-widest">
                Real-Time Multi-Agent AI
              </span>
              <h1 className="text-4xl md:text-5xl font-black leading-tight tracking-tight">
                Global Trade Intelligence & <br />
                <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400">
                  Opportunity Optimization
                </span>
              </h1>
              <p className="text-slate-400 text-sm md:text-base font-medium leading-relaxed">
                Trade Mind runs independent asynchronous agents to evaluate best export countries, tariffs, currency volatility, economic risks, and logistical pricing based on real data only.
              </p>
            </div>

            {/* Input Trigger Form & Info Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
              {/* Form */}
              <div className="lg:col-span-5 glass-panel rounded-3xl p-8 border border-white/5 flex flex-col gap-6">
                <div className="flex items-center gap-3">
                  <Play className="w-5 h-5 text-emerald-400" />
                  <h3 className="text-lg font-extrabold text-slate-200">Start Trade Ingestion</h3>
                </div>

                <form onSubmit={handleSubmit} className="flex flex-col gap-4">
                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-bold uppercase text-slate-500 tracking-wider">HS Code</label>
                    <input
                      type="text"
                      value={hsCode}
                      onChange={(e) => setHsCode(e.target.value)}
                      className="bg-slate-950/80 border border-white/10 rounded-xl px-4 py-3 text-slate-300 font-mono text-sm focus:outline-none focus:border-blue-500"
                      placeholder="e.g. 5201"
                      required
                    />
                  </div>

                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-bold uppercase text-slate-500 tracking-wider">Quantity (Metric Tons)</label>
                    <input
                      type="number"
                      value={qtyTons}
                      onChange={(e) => setQtyTons(e.target.value)}
                      className="bg-slate-950/80 border border-white/10 rounded-xl px-4 py-3 text-slate-300 font-mono text-sm focus:outline-none focus:border-blue-500"
                      placeholder="e.g. 50"
                      required
                    />
                  </div>

                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-bold uppercase text-slate-500 tracking-wider">Commodity Name</label>
                    <input
                      type="text"
                      value={commodityName}
                      onChange={(e) => setCommodityName(e.target.value)}
                      className="bg-slate-950/80 border border-white/10 rounded-xl px-4 py-3 text-slate-300 font-mono text-sm focus:outline-none focus:border-blue-500"
                      placeholder="e.g. cotton"
                      required
                    />
                  </div>

                  <button
                    type="submit"
                    className="w-full bg-gradient-to-r from-blue-600 to-emerald-500 hover:from-blue-700 hover:to-emerald-600 text-white font-extrabold text-sm py-4 rounded-xl shadow-lg shadow-blue-500/10 transition-all flex items-center justify-center gap-2 cursor-pointer"
                  >
                    <Play className="w-4 h-4 fill-white" />
                    RUN TRADE INTELLIGENCE
                  </button>
                </form>
              </div>

              {/* Agents Info Cards */}
              <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="glass-panel rounded-3xl p-6 border border-white/5 flex flex-col gap-2">
                  <div className="w-8 h-8 rounded-lg bg-blue-600/10 flex items-center justify-center font-bold text-blue-400">M</div>
                  <h4 className="font-extrabold text-sm text-slate-200">Market Attractiveness</h4>
                  <p className="text-xs text-slate-500 leading-relaxed font-medium">Loads files from dataset directory dynamically to rank countries by trade volumes and CAGR.</p>
                </div>
                <div className="glass-panel rounded-3xl p-6 border border-white/5 flex flex-col gap-2">
                  <div className="w-8 h-8 rounded-lg bg-emerald-600/10 flex items-center justify-center font-bold text-emerald-400">P</div>
                  <h4 className="font-extrabold text-sm text-slate-200">Price Forecasting</h4>
                  <p className="text-xs text-slate-500 leading-relaxed font-medium">Runs Prophet/RandomForest models on pricing datasets to predict values and profit margins.</p>
                </div>
                <div className="glass-panel rounded-3xl p-6 border border-white/5 flex flex-col gap-2">
                  <div className="w-8 h-8 rounded-lg bg-purple-600/10 flex items-center justify-center font-bold text-purple-400">R</div>
                  <h4 className="font-extrabold text-sm text-slate-200">Risk Scorer</h4>
                  <p className="text-xs text-slate-500 leading-relaxed font-medium">Fetches real-time World Bank political governance indices and inflation rates for target countries.</p>
                </div>
                <div className="glass-panel rounded-3xl p-6 border border-white/5 flex flex-col gap-2">
                  <div className="w-8 h-8 rounded-lg bg-amber-600/10 flex items-center justify-center font-bold text-amber-400">L</div>
                  <h4 className="font-extrabold text-sm text-slate-200">Logistics Routing</h4>
                  <p className="text-xs text-slate-500 leading-relaxed font-medium">Calculates sea routes, shipping costs, and port handling efficiencies from Nhava Sheva port.</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ==================== 3. DASHBOARD PAGE ==================== */}
        {activeTab === 'dashboard' && (
          <div className="flex flex-col gap-8">
            {status === 'QUEUED' || status === 'RUNNING' ? (
              <div className="flex flex-col gap-6">
                <div className="glass-panel rounded-3xl p-8 border border-white/5 flex flex-col items-center gap-6 text-center">
                  <div className="relative w-20 h-20">
                    <div className="absolute inset-0 rounded-full border-4 border-blue-500/10" />
                    <div className="absolute inset-0 rounded-full border-4 border-t-blue-500 border-r-emerald-500 animate-spin" />
                  </div>
                  <div>
                    <h3 className="text-xl font-black text-slate-200">Asynchronous Multi-Agent Ingestion Active</h3>
                    <p className="text-xs text-slate-400 mt-1">Executing market, pricing, risk, tariff, and logistics agent nodes...</p>
                  </div>
                </div>

                {/* Live agent log stream */}
                <LogTerminal />
              </div>
            ) : !currentResult ? (
              <div className="h-[400px] flex flex-col items-center justify-center gap-4 text-slate-500 text-sm glass-panel rounded-3xl p-6">
                <AlertTriangle className="w-12 h-12 text-yellow-500 animate-bounce" />
                <span>No analysis data loaded yet. Run a trade analysis from the homepage or load a report from history.</span>
                <button
                  onClick={() => setActiveTab('landing')}
                  className="bg-blue-600 text-white font-bold text-xs px-4 py-2 rounded-xl"
                >
                  Start New Ingestion
                </button>
              </div>
            ) : (
              <div className="flex flex-col gap-8">
                {/* Header Summary */}
                <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 glass-panel rounded-3xl p-8 border border-white/5">
                  <div className="flex flex-col gap-1">
                    <span className="text-[10px] font-bold text-slate-500 tracking-widest uppercase">Analysis Complete</span>
                    <h2 className="text-2xl md:text-3xl font-black text-slate-200">
                      Best Export Market: <span className="text-emerald-400">{currentResult.best_export_market}</span>
                    </h2>
                    <p className="text-xs text-slate-400 font-semibold">
                      Commodity: {currentResult.commodity_name} | HS Code: {currentResult.hs_code} | Volume: {currentResult.quantity_tons} tons
                    </p>
                  </div>

                  {/* Summary Values */}
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-6 shrink-0 bg-slate-950/40 p-6 rounded-2xl border border-white/5">
                    <div>
                      <div className="text-[10px] font-bold text-slate-500 tracking-wider uppercase mb-1">Expected Profit</div>
                      <div className="text-lg font-black text-emerald-400 flex items-center">
                        <DollarSign className="w-4 h-4 shrink-0" />
                        {currentResult.expected_profit_usd.toLocaleString()}
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] font-bold text-slate-500 tracking-wider uppercase mb-1">AI Match Score</div>
                      <div className="text-lg font-black text-blue-400">
                        {currentResult.final_ai_score.toFixed(2)}
                      </div>
                    </div>
                    <div className="col-span-2 sm:col-span-1">
                      <div className="text-[10px] font-bold text-slate-500 tracking-wider uppercase mb-1">Risk Rating</div>
                      <div className={`text-sm font-black mt-1 ${currentResult.risk_level === 'Low' ? 'text-emerald-400' :
                        currentResult.risk_level === 'Medium' ? 'text-amber-400' :
                          'text-red-400'
                        }`}>
                        {currentResult.risk_level?.toUpperCase()} RISK
                      </div>
                    </div>
                  </div>
                </div>

                {/* Country Rankings Table */}
                <div className="glass-panel rounded-3xl p-6 border border-white/5 flex flex-col gap-4">
                  <div>
                    <h3 className="text-base font-extrabold text-slate-200 tracking-wide">Dynamic Country Evaluation Rankings</h3>
                    <p className="text-xs text-slate-500 font-semibold uppercase">Multi-agent weighted consolidation</p>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left font-sans text-xs border-collapse">
                      <thead>
                        <tr className="border-b border-white/5 text-slate-400 font-bold uppercase tracking-wider">
                          <th className="py-4 px-3">Rank</th>
                          <th className="py-4 px-3">Country</th>
                          <th className="py-4 px-3">Market Vol</th>
                          <th className="py-4 px-3">GDP Growth</th>
                          <th className="py-4 px-3">Tariffs</th>
                          <th className="py-4 px-3">Transit Days</th>
                          <th className="py-4 px-3">FX Risk</th>
                          <th className="py-4 px-3 text-right">Profit Est (USD)</th>
                          <th className="py-4 px-3 text-right">AI Score</th>
                        </tr>
                      </thead>
                      <tbody>
                        {currentResult.countries.map((c) => (
                          <tr key={c.country} className="border-b border-white/[0.02] hover:bg-white/[0.01] transition-all text-slate-300">
                            <td className="py-4 px-3 font-extrabold text-blue-400">#{c.rank}</td>
                            <td className="py-4 px-3 font-bold text-slate-100">{c.country}</td>
                            <td className="py-4 px-3 font-mono">{c.import_volume ? c.import_volume.toLocaleString() : 'N/A'} kg</td>
                            <td className="py-4 px-3 text-emerald-400 font-semibold">+{c.predicted_demand_growth_pct}%</td>
                            <td className="py-4 px-3 text-amber-400 font-semibold">{c.tariff_pct}%</td>
                            <td className="py-4 px-3 font-mono">{c.transit_days} days</td>
                            <td className="py-4 px-3">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${c.currency_risk_level === 'Low' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' :
                                c.currency_risk_level === 'Medium' ? 'bg-blue-950 text-blue-300 border border-blue-800' :
                                  'bg-red-950 text-red-300 border border-red-800'
                                }`}>
                                {c.currency_risk_level}
                              </span>
                            </td>
                            <td className="py-4 px-3 text-right font-bold text-emerald-400">${c.expected_profit_usd.toLocaleString()}</td>
                            <td className="py-4 px-3 text-right font-black text-blue-400">{c.final_score.toFixed(2)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Pricing & Demand Trends */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <PriceChart />
                  <DemandChart />
                </div>

                {/* AI Recommendations */}
                <div className="glass-panel rounded-3xl p-6 border border-white/5 flex flex-col gap-4">
                  <div className="flex items-center gap-2">
                    <Award className="w-5 h-5 text-emerald-400" />
                    <h3 className="text-base font-extrabold text-slate-200 tracking-wide">Explainable AI Recommendations</h3>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {currentResult.recommendations.map((rec: any, idx: number) => (
                      <div key={idx} className="bg-slate-950/40 p-6 rounded-2xl border border-white/5 flex flex-col gap-4">
                        <div className="flex items-center justify-between border-b border-white/5 pb-3">
                          <span className="font-extrabold text-slate-200">{rec.country}</span>
                          <span className="text-xs bg-blue-600/10 border border-blue-500/20 text-blue-400 px-2.5 py-1 rounded-full font-bold">Rank #{rec.rank}</span>
                        </div>
                        <p className="text-xs text-slate-400 leading-relaxed font-medium">{rec.reasoning}</p>

                        {rec.recs.length > 0 && (
                          <div className="flex flex-col gap-2 mt-2">
                            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">Mitigation Strategies</span>
                            {rec.recs.map((r: string, rid: number) => (
                              <div key={rid} className="flex items-start gap-2 text-xs text-slate-300">
                                <ChevronRight className="w-3.5 h-3.5 text-blue-500 shrink-0 mt-0.5" />
                                <span>{r}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Score Explainability */}
                <SHAPChart />

                {/* Indian Exporter Matching */}
                <div className="glass-panel rounded-3xl p-6 border border-white/5 flex flex-col gap-4">
                  <div>
                    <h3 className="text-base font-extrabold text-slate-200 tracking-wide">Indian Exporter Matching</h3>
                    <p className="text-xs text-slate-500 font-semibold uppercase">Verified Suppliers & Contact Information</p>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                    {currentResult.suppliers.slice(0, 10).map((sup: any, idx: number) => (
                      <div key={`${sup.supplier_name || sup.name}-${idx}`} className="bg-slate-950/40 p-6 rounded-2xl border border-white/5 flex flex-col gap-4 justify-between">
                        <div className="flex flex-col gap-3">
                          <div className="flex items-center justify-between border-b border-white/5 pb-3">
                            <span className="font-extrabold text-slate-200 text-sm line-clamp-1">{sup.supplier_name || sup.name}</span>
                            <span className="text-[10px] bg-emerald-600/10 border border-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full font-bold">
                              Verified
                            </span>
                          </div>
                          
                          <div className="text-xs text-slate-400 flex flex-col gap-2.5">
                            {sup.city_state && (
                              <div className="flex items-start gap-2">
                                <MapPin className="w-3.5 h-3.5 text-blue-400 shrink-0 mt-0.5" />
                                <div>
                                  <span className="text-slate-500 block text-[9px] uppercase font-bold tracking-wider">Region/State</span>
                                  <span className="text-slate-300 font-medium">{sup.city_state}</span>
                                </div>
                              </div>
                            )}
                            {sup.address && (
                              <div className="flex items-start gap-2">
                                <Globe className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                                <div>
                                  <span className="text-slate-500 block text-[9px] uppercase font-bold tracking-wider">Address</span>
                                  <span className="text-slate-300 font-medium line-clamp-2">{sup.address}</span>
                                </div>
                              </div>
                            )}
                            {sup.contact_no && (
                              <div className="flex items-start gap-2">
                                <Phone className="w-3.5 h-3.5 text-purple-400 shrink-0 mt-0.5" />
                                <div>
                                  <span className="text-slate-500 block text-[9px] uppercase font-bold tracking-wider">Contact No</span>
                                  <span className="text-slate-300 font-mono font-medium">{sup.contact_no}</span>
                                </div>
                              </div>
                            )}
                            {sup.email && (
                              <div className="flex items-start gap-2">
                                <Mail className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                                <div>
                                  <span className="text-slate-500 block text-[9px] uppercase font-bold tracking-wider">Email</span>
                                  <span className="text-slate-300 font-mono font-medium break-all">{sup.email}</span>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}



        {/* ==================== 7. HISTORY REPORTS ==================== */}
        {activeTab === 'reports' && (
          <div className="flex flex-col gap-6">
            <div>
              <h2 className="text-2xl font-black text-slate-100 tracking-tight">Historic Trade Analysis Logs</h2>
              <p className="text-xs text-slate-500 font-semibold tracking-wider uppercase">Saved SQL analysis results</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {reportsList.length === 0 ? (
                <div className="col-span-full h-[200px] flex items-center justify-center text-slate-500 text-sm glass-panel rounded-3xl p-6">
                  No historical reports found in database.
                </div>
              ) : (
                reportsList.map((rep) => (
                  <div key={rep.id} className="glass-panel rounded-3xl p-6 border border-white/5 flex flex-col gap-4 justify-between">
                    <div className="flex flex-col gap-2">
                      <div className="flex justify-between items-start">
                        <span className="text-[10px] font-bold text-blue-400 uppercase font-mono">{rep.id.slice(0, 8)}...</span>
                        <span className="text-[10px] text-slate-500 font-semibold">{new Date(rep.created_at).toLocaleDateString()}</span>
                      </div>
                      <h4 className="font-extrabold text-slate-200 text-base capitalize">{rep.commodity_name} Export Analysis</h4>
                      <div className="text-xs text-slate-400 flex flex-col gap-1">
                        <div>HS Code: <span className="font-mono text-slate-300">{rep.hs_code}</span></div>
                        <div>Quantity: <span className="text-slate-300">{rep.quantity_tons} tons</span></div>
                        <div>Best Country: <span className="text-emerald-400 font-bold">{rep.best_export_market}</span></div>
                      </div>
                    </div>

                    <button
                      onClick={() => handleLoadReport(rep.id)}
                      className="w-full bg-slate-900 hover:bg-slate-800 border border-white/5 text-slate-200 text-xs font-bold py-3 rounded-xl transition-all flex items-center justify-center gap-1.5 cursor-pointer mt-4"
                    >
                      <FileText className="w-3.5 h-3.5" /> LOAD REPORT
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

      </main>

      {/* Footer */}
      <footer className="py-8 px-6 text-center border-t border-white/5 text-xs text-slate-500 font-semibold uppercase tracking-widest mt-20">
        Trade Mind Multi-Agent Trade Management Platform © 2026
      </footer>
    </div>
  );
}
