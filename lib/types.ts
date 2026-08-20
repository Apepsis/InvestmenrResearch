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
};

export type MarketDataset = {
  generatedAt: string;
  mode: "live" | "sample";
  macro: Record<string, { label: string; value: number | null; unit: string; asOf: string }>;
  stocks: Record<string, StockAnalysis>;
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
