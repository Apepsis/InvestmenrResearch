import type {
  AlertDataset,
  BacktestDataset,
  BuildJournal,
  EventStudyDataset,
  FastSignalsDataset,
  LivePredictionsDataset,
  ModelMonitoringDataset,
  ModelRegistryDataset,
  PredictionLedgerDataset,
  ResearchManifest,
  RiskDataset,
} from "@/lib/types";

export const demoFastSignals: FastSignalsDataset = {
  generatedAt: "Sin ejecutar",
  mode: "sample",
  refreshIntervalMinutes: 20,
  policy: "Vigilancia rápida independiente; no modifica el score oficial hasta el pipeline diario.",
  stocks: {},
};

const sampleMetrics = (overrides: Partial<BacktestDataset["metrics"][string]> = {}) => ({
  totalReturn: 0,
  cagr: 0,
  sharpe: 0,
  sortino: 0,
  maxDrawdown: 0,
  volatility: 0,
  hitRate: 0,
  alpha: 0,
  beta: 0,
  observations: 0,
  ...overrides,
});

export const demoBacktest: BacktestDataset = {
  generatedAt: "Ejemplo estructural; ejecuta el pipeline para resultados reales",
  mode: "sample",
  hypothesis: "Un modelo transparente puede estimar la probabilidad de superar al SPY a 60 sesiones sin usar informacion futura.",
  horizonSessions: 60,
  rebalanceSessions: 60,
  transactionCostBps: 10,
  period: { start: "Sin ejecutar", end: "Sin ejecutar" },
  methodology: {
    validation: "Walk-forward anual; cada prueba usa exclusivamente observaciones anteriores.",
    models: {
      spy: "Comprar y mantener SPY",
      technical: "Regla tecnica determinista",
      heuristic: "Score transparente ponderado",
      statistical: "Regresion logistica regularizada con calibracion temporal",
      riskControlled: "Challenger con límites de exposición, volatilidad, CVaR y régimen",
    },
    safeguards: [
      "Desplazamiento explicito del objetivo 60 sesiones hacia el futuro.",
      "Normalizacion calculada solo con el conjunto de entrenamiento.",
      "Costos de transaccion incluidos en cada rebalanceo.",
      "Fechas de entrenamiento y prueba registradas por ejecucion.",
    ],
    limitations: [
      "La muestra incluida no contiene resultados; el workflow debe generar el backtest real.",
      "Los fundamentales y titulares sin historial point-in-time no se introducen retrospectivamente.",
      "El universo actual es pequeno y no representa todo el mercado.",
    ],
  },
  metrics: {
    spy: sampleMetrics(),
    technical: sampleMetrics(),
    heuristic: sampleMetrics(),
    statistical: sampleMetrics(),
    riskControlled: sampleMetrics(),
  },
  equity: [],
  drawdown: [],
  annualReturns: [],
  calibration: { brierScore: null, accuracy: null, sampleSize: 0, bins: [] },
};

export const demoPredictions: LivePredictionsDataset = {
  generatedAt: "Sin ejecutar",
  mode: "sample",
  modelVersion: "transparent-research-v5.0",
  horizons: [5, 20, 60],
  hypothesis: "Probabilidad de superar a SPY usando únicamente información disponible al publicar.",
  predictions: [],
  modelFits: {},
  limitations: ["Ejecuta el pipeline para publicar predicciones reales."],
};

export const demoLedger: PredictionLedgerDataset = {
  generatedAt: "Sin ejecutar",
  mode: "sample",
  policy: "Los campos publicados son inmutables; el resultado se completa al madurar.",
  immutableFields: [],
  recordCount: 0,
  evaluatedCount: 0,
  records: [],
};

export const demoRegistry: ModelRegistryDataset = {
  generatedAt: "Sin ejecutar",
  mode: "sample",
  champion: { key: "statistical", version: "transparent-research-v4.0", metrics: sampleMetrics() },
  challenger: { key: "riskControlled", version: "risk-controlled-v5.0", metrics: sampleMetrics() },
  baseline: { key: "statistical", version: "transparent-research-v4.0", metrics: sampleMetrics() },
  promotionCriteria: { minimumObservations: false, sharpeImprovement: false, drawdownImprovement: false, cagrTolerance: false },
  qualifiedThisRun: false,
  qualificationStreak: 0,
  requiredStreak: 3,
  lastQualificationDate: "Sin ejecutar",
  decision: "Esperando la primera comparación fuera de muestra.",
  guardrail: "Nunca se reemplaza un modelo silenciosamente.",
};

export const demoMonitoring: ModelMonitoringDataset = {
  generatedAt: "Sin ejecutar",
  mode: "sample",
  status: "warning",
  data: { predictionCoverage: 0, predictionsPublished: 0, predictionsExpected: 96, marketDataAgeHours: 0, providerErrors: 0 },
  featureDrift: { maximumAbsoluteShift: 0, thresholdWarning: 2, thresholdCritical: 3, topShifts: [] },
  performance: { evaluatedPredictions: 0, recentWindow: 0, accuracy: null, brierScore: null, minimumWindowForAlert: 30 },
  governance: { champion: "statistical", challengerQualified: false, qualificationStreak: 0 },
  issues: [],
  interpretation: "Esperando la primera ejecución.",
};

export const demoAlerts: AlertDataset = {
  generatedAt: "Sin ejecutar",
  mode: "sample",
  deliveryEnabled: false,
  deliveryStatus: "disabled",
  newAlertsSent: 0,
  candidates: [],
  pendingAfterCooldown: 0,
  policy: "Digest deduplicado; no ejecuta operaciones.",
};

export const demoEventStudy: EventStudyDataset = {
  generatedAt: "Sin ejecutar",
  mode: "sample",
  benchmark: "SPY",
  methodology: "Retorno del activo menos retorno de SPY durante ventanas de 1, 5 y 20 sesiones posteriores al evento.",
  coverage: 0,
  items: [],
};

const sampleReturns = [0.004, -0.006, 0.003, 0.001, -0.002, 0.005, -0.004, 0.002, 0.003, -0.001];
const sampleTickers = ["UBER", "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "SPY"];

export const demoRisk: RiskDataset = {
  generatedAt: "Ejemplo estructural; ejecuta el pipeline para datos reales",
  mode: "sample",
  windowSessions: sampleReturns.length,
  tickers: sampleTickers,
  dailyReturns: Object.fromEntries(sampleTickers.map((ticker, index) => [ticker, sampleReturns.map((value) => value * (1 + index * 0.04))])),
  correlation: Object.fromEntries(sampleTickers.map((ticker) => [ticker, Object.fromEntries(sampleTickers.map((other) => [other, ticker === other ? 1 : 0.55]))])),
  beta: Object.fromEntries(sampleTickers.map((ticker, index) => [ticker, ticker === "SPY" ? 1 : 0.85 + index * 0.05])),
  annualVolatility: Object.fromEntries(sampleTickers.map((ticker, index) => [ticker, 0.2 + index * 0.015])),
  stressScenarios: [
    {
      id: "market-20",
      label: "Mercado -20%",
      description: "Shock hipotetico aplicado mediante la beta estimada de cada activo.",
      shocks: Object.fromEntries(sampleTickers.map((ticker, index) => [ticker, ticker === "SPY" ? -0.2 : -0.2 * (0.85 + index * 0.05)])),
    },
    {
      id: "single-30",
      label: "Mayor posicion -30%",
      description: "Prueba de concentracion aplicada en el navegador a la posicion de mayor peso.",
      shocks: {},
    },
  ],
};

export const demoManifest: ResearchManifest = {
  generatedAt: "Sin ejecutar",
  mode: "sample",
  runId: "SAMPLE-NOT-A-REAL-RUN",
  modelVersion: "transparent-research-v5.0",
  gitCommit: "no-disponible",
  dataHash: "no-disponible",
  horizon: "5, 20 y 60 sesiones",
  assetsProcessed: 0,
  assetsExpected: 33,
  newsClassified: 0,
  nonCriticalErrors: 0,
  testsPassed: 0,
  dataCoverage: 0,
  durationSeconds: 0,
  artifacts: [],
};

export const demoBuildJournal: BuildJournal = {
  version: "5.0",
  question: "¿Puede un sistema transparente combinar mercado, fundamentos, macroeconomia y noticias para investigar retornos excedentes a 60 sesiones?",
  principles: ["No usar informacion futura", "Separar evidencia de interpretacion", "Publicar errores y limitaciones", "Preferir modelos simples que puedan auditarse"],
  milestones: [
    {
      date: "2026-08",
      title: "Prototipo funcional",
      problem: "Los datos personales debian persistir entre dispositivos.",
      decision: "Firebase Authentication y Firestore con aislamiento por UID.",
      evidence: "Inicio de sesion, portafolio, vigilancia y diario sincronizados.",
      status: "completed",
    },
    {
      date: "2026-08",
      title: "Cotizacion reciente sin exponer secretos",
      problem: "GitHub Pages no puede proteger claves privadas.",
      decision: "Cloudflare Worker como proxy de solo lectura para Alpaca IEX.",
      evidence: "Claves fuera del navegador y actualizacion cada minuto mientras la pagina esta abierta.",
      status: "completed",
    },
    {
      date: "2026-08",
      title: "Research Lab auditable",
      problem: "Un score aislado no demostraba validez ni procedencia.",
      decision: "Agregar backtesting walk-forward, explicabilidad, riesgo, event studies y manifiestos reproducibles.",
      evidence: "Código y pantallas incluidos; los resultados reales se generan en GitHub Actions.",
      status: "in-progress",
    },
  ],
  failedExperiments: [
    {
      experiment: "Presentar un comite de inversores famosos como agentes",
      result: "La interfaz podia sugerir una inteligencia multiagente que las reglas no implementaban realmente.",
      lesson: "Renombrar como lentes metodologicos y publicar la regla exacta de cada lente.",
    },
    {
      experiment: "Usar noticias externas como evidencia principal",
      result: "El widget era visualmente util, pero no demostraba clasificacion ni medicion propia.",
      lesson: "Mantenerlo como vigilancia secundaria y construir un pipeline auditable de eventos.",
    },
  ],
  limitations: [
    "Alpaca Basic utiliza IEX y puede diferir del mercado consolidado.",
    "Los fundamentales historicos point-in-time requieren especial cuidado para evitar revisiones posteriores.",
    "El universo ampliado sigue teniendo sesgo de supervivencia y produce evidencia exploratoria.",
    "Las pruebas de estres describen sensibilidad y no son predicciones.",
  ],
  nextExperiments: [
    "Construir un conjunto etiquetado manualmente de titulares.",
    "Comparar clasificador lexicografico, regresion logistica y FinBERT.",
    "Construir un universo histórico point-in-time para reducir sesgo de supervivencia.",
  ],
};
