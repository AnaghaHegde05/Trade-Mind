import { create } from 'zustand';

export interface LogEntry {
  timestamp: string;
  level: string;
  logger: string;
  message: string;
  agent: string;
  progress?: number;
}

export interface CountryScore {
  country: string;
  rank: number;
  final_score: number;
  market_score: number;
  import_volume?: number;
  import_value?: number;
  demand_score: number;
  price_score: number;
  currency_score: number;
  tariff_score: number;
  logistics_score: number;
  risk_score: number;
  supplier_score: number;
  expected_profit_usd: number;
  predicted_demand_growth_pct: number;
  shipping_cost_per_ton: number;
  transit_days: number;
  tariff_pct: number;
  currency_risk_level: string;
  political_stability_score: number;
  inflation_rate_pct: number;
  logistics_details: any;
  risk_details: any;
  tariff_details: any;
  trade_volume_history: Record<number, number>;
  trade_volume_forecast: Record<number, number>;
}

export interface SupplierDetails {
  name: string;
  country: string;
  capacity_tons: number;
  rating: number;
  cost_competitiveness: number;
  overall_score: number;
}

export interface ReportData {
  id: string;
  hs_code: string;
  commodity_name: string;
  quantity_tons: number;
  best_export_market: string;
  expected_profit_usd: number;
  risk_level: string; // "Low" | "Medium" | "High" - overall risk category
  final_ai_score: number;
  recommendations: any[];
  shap_explainability: any;
  created_at: string;
  countries: CountryScore[];
  global_pricing: {
    price_history: Record<number, number>;
    price_forecast: Record<number, number>;
  };
  suppliers: SupplierDetails[];
}

export interface HealthStatus {
  status: string;
  timestamp: number;
  database: string;
  cache: string;
}

interface TradeState {
  activeTab: string;
  taskId: string | null;
  status: 'IDLE' | 'QUEUED' | 'RUNNING' | 'SUCCESS' | 'FAILED';
  progress: number;
  activeAgent: string;
  logs: LogEntry[];
  currentResult: ReportData | null;
  reportsList: any[];
  healthStatus: HealthStatus | null;
  
  setActiveTab: (tab: string) => void;
  setTaskId: (id: string | null) => void;
  setStatus: (status: 'IDLE' | 'QUEUED' | 'RUNNING' | 'SUCCESS' | 'FAILED') => void;
  setProgress: (prog: number) => void;
  setActiveAgent: (agent: string) => void;
  addLog: (log: LogEntry) => void;
  clearLogs: () => void;
  setCurrentResult: (res: ReportData | null) => void;
  setReportsList: (list: any[]) => void;
  setHealthStatus: (status: HealthStatus | null) => void;
}

export const useTradeStore = create<TradeState>((set) => ({
  activeTab: 'landing',
  taskId: null,
  status: 'IDLE',
  progress: 0,
  activeAgent: 'System',
  logs: [],
  currentResult: null,
  reportsList: [],
  healthStatus: null,
  
  setActiveTab: (tab) => set({ activeTab: tab }),
  setTaskId: (id) => set({ taskId: id }),
  setStatus: (status) => set({ status }),
  setProgress: (progress) => set({ progress }),
  setActiveAgent: (activeAgent) => set({ activeAgent }),
  addLog: (log) => set((state) => {
    // Determine active agent and progress based on log metadata
    const activeAgent = log.agent || state.activeAgent;
    const progress = log.progress !== null && log.progress !== undefined ? log.progress : state.progress;
    
    // Check if task success triggers loading results
    let status = state.status;
    if (log.message.includes('Trade analysis results successfully persisted')) {
      status = 'SUCCESS';
    } else if (log.message.includes('failed') || log.level === 'ERROR') {
      // Don't mark failed on simple warnings, only error level
      if (log.level === 'ERROR') {
        status = 'FAILED';
      }
    } else if (state.status === 'IDLE' || state.status === 'QUEUED') {
      status = 'RUNNING';
    }
    
    return {
      logs: [...state.logs.slice(-499), log], // Cap logs at 500
      activeAgent,
      progress,
      status
    };
  }),
  clearLogs: () => set({ logs: [] }),
  setCurrentResult: (currentResult) => set({ currentResult }),
  setReportsList: (reportsList) => set({ reportsList }),
  setHealthStatus: (healthStatus) => set({ healthStatus }),
}));
