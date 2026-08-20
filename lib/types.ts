export type ScoreKey = "technical" | "fundamental" | "news" | "macro" | "risk";

export type ScoreBreakdown = Record<ScoreKey, number>;

export type NewsItem = {
  title: string;
  source: string;
  url: string;
  publishedAt: string;
  sentiment: "positive" | "neutral" | "negative";
  eventType: string;
  duration: "temporary" | "medium" | "structural";
  confidence: number;
  relevance?: number;
  novelty?: number;
  entityMatched?: boolean;
  impactWeight?: number;
};

export type ScoreContribution = {
  feature: string;
  group: ScoreKey;
  rawValue: string;
  normalized: number;
  weight: number;
  contribution: number;
  formula: string;
  source: string;
  asOf: string;
  status: "verified" | "estimated" | "missing";
};

export type ScoreExplanation = {
  base: number;
  result: number;
  interval: { low: number; high: number; level: number };
  dataQuality: number;
  method: string;
  contributions: ScoreContribution[];
};

export type DataTrace = {
  prices: string;
  fundamentals: string;
  news: string;
  macro: string;
  method: string;
};

export type Indicator = {
  label: string;
  value: string;
  interpretation: string;
  tone: "positive" | "neutral" | "negative";
};

export type StockAnalysis = {
  ticker: string;
  name: string;
  sector: string;
  currency: string;
  price: number;
  changePct: number;
  asOf: string;
  score: number;
  verdict: string;
  source: "live" | "sample";
  confidence: number;
  scores: ScoreBreakdown;
  history: number[];
  technical: Indicator[];
  fundamental: Indicator[];
  thesis: string[];
  risks: string[];
  invalidation: string[];
  committee: { agent: string; focus: string; view: string; tone: "positive" | "neutral" | "negative" }[];
  news: NewsItem[];
  explanation?: ScoreExplanation;
  trace?: DataTrace;
};

export type MarketDataset = {
  generatedAt: string;
  mode: "live" | "sample";
  macro: Record<string, { label: string; value: number | null; unit: string; asOf: string; source?: string; error?: string }>;
  stocks: Record<string, StockAnalysis>;
  errors?: Record<string, string>;
  methodology?: { weights: Record<string, number>; horizon: string; disclaimer: string };
};

export type BacktestMetric = {
  totalReturn: number;
  cagr: number;
  sharpe: number;
  sortino: number;
  maxDrawdown: number;
  volatility: number;
  hitRate: number;
  alpha: number;
  beta: number;
  observations: number;
};

export type BacktestDataset = {
  generatedAt: string;
  mode: "live" | "sample";
  hypothesis: string;
  horizonSessions: number;
  rebalanceSessions: number;
  transactionCostBps: number;
  period: { start: string; end: string };
  methodology: {
    validation: string;
    models: Record<string, string>;
    safeguards: string[];
    limitations: string[];
  };
  metrics: Record<string, BacktestMetric>;
  equity: Array<Record<string, string | number>>;
  drawdown: Array<Record<string, string | number>>;
  annualReturns: Array<Record<string, string | number>>;
  calibration: {
    brierScore: number | null;
    accuracy: number | null;
    sampleSize: number;
    bins: Array<{ predicted: number; observed: number; count: number }>;
  };
};

export type EventStudyItem = {
  ticker: string;
  title: string;
  source: string;
  publishedAt: string;
  eventType: string;
  sentiment: string;
  relevance: number;
  novelty: number;
  entityMatched: boolean;
  abnormalReturn1d: number | null;
  abnormalReturn5d: number | null;
  abnormalReturn20d: number | null;
  status: "measured" | "pending" | "unavailable";
};

export type EventStudyDataset = {
  generatedAt: string;
  mode: "live" | "sample";
  benchmark: string;
  methodology: string;
  coverage: number;
  items: EventStudyItem[];
};

export type RiskDataset = {
  generatedAt: string;
  mode: "live" | "sample";
  windowSessions: number;
  tickers: string[];
  dailyReturns: Record<string, number[]>;
  correlation: Record<string, Record<string, number>>;
  beta: Record<string, number>;
  annualVolatility: Record<string, number>;
  stressScenarios: Array<{
    id: string;
    label: string;
    description: string;
    shocks: Record<string, number>;
  }>;
};

export type ResearchManifest = {
  generatedAt: string;
  mode: "live" | "sample";
  runId: string;
  modelVersion: string;
  gitCommit: string;
  dataHash: string;
  horizon: string;
  assetsProcessed: number;
  assetsExpected: number;
  newsClassified: number;
  nonCriticalErrors: number;
  testsPassed: number;
  dataCoverage: number;
  durationSeconds: number;
  artifacts: Array<{ name: string; sha256: string; bytes: number }>;
};

export type BuildJournal = {
  version: string;
  question: string;
  principles: string[];
  milestones: Array<{
    date: string;
    title: string;
    problem: string;
    decision: string;
    evidence: string;
    status: "completed" | "in-progress" | "planned";
  }>;
  failedExperiments: Array<{ experiment: string; result: string; lesson: string }>;
  limitations: string[];
  nextExperiments: string[];
};

export type LiveQuote = {
  ticker: string;
  price: number;
  asOf: string;
  source: "Alpaca IEX" | string;
};

export type LiveQuoteDataset = {
  generatedAt: string;
  feed: string;
  quotes: Record<string, LiveQuote>;
};

export type Position = {
  id: string;
  ticker: string;
  shares: number;
  averageCost: number;
  createdAt: string;
};

export type WatchItem = {
  id: string;
  ticker: string;
  targetPrice: number | null;
  note: string;
  createdAt: string;
};

export type JournalEntry = {
  id: string;
  ticker: string;
  decision: "Comprar por tramos" | "Esperar" | "Mantener" | "Evitar";
  confidence: number;
  thesis: string;
  invalidation: string;
  createdAt: string;
};

export type Weights = Record<ScoreKey, number>;
