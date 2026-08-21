import type {
  AlertDataset,
  BacktestDataset,
  BacktestHistoryDataset,
  EventStudyDataset,
  LivePredictionsDataset,
  ModelMonitoringDataset,
  ModelRegistryDataset,
  NeuralLabDataset,
  NeuralPredictionLedgerDataset,
  PredictionLedgerDataset,
  ResearchManifest,
  ScoreContribution,
  StockAnalysis,
} from "@/lib/types";
import { useEffect, useState, type ReactNode } from "react";
import PredictionV5Lab from "@/app/components/PredictionV5Lab";
import NeuralV8Lab from "@/app/components/NeuralV8Lab";

type Props = {
  stock: StockAnalysis;
  backtest: BacktestDataset;
  backtestHistory: BacktestHistoryDataset;
  events: EventStudyDataset;
  manifest: ResearchManifest;
  predictions: LivePredictionsDataset;
  ledger: PredictionLedgerDataset;
  registry: ModelRegistryDataset;
  monitoring: ModelMonitoringDataset;
  alerts: AlertDataset;
  neural: NeuralLabDataset;
  neuralLedger: NeuralPredictionLedgerDataset;
};

const percent = (value: number, digits = 1) => `${value >= 0 ? "+" : ""}${(value * 100).toFixed(digits)}%`;
const number = (value: number, digits = 2) => Number.isFinite(value) ? value.toFixed(digits) : "N/D";

function StatusPill({ live, children }: { live: boolean; children: ReactNode }) {
  return <span className={`research-status ${live ? "is-live" : "is-sample"}`}>{children}</span>;
}

function Metric({ label, value, help }: { label: string; value: string; help: string }) {
  return <article className="research-metric"><span>{label}</span><strong>{value}</strong><small>{help}</small></article>;
}

function LineChart({ data, keys }: { data: Array<Record<string, string | number>>; keys: Array<{ key: string; label: string; color: string }> }) {
  if (!data.length) return <div className="chart-empty"><strong>Backtest todavía no ejecutado</strong><span>Ejecuta “Actualizar datos e investigación” en GitHub Actions.</span></div>;
  const availableKeys = keys.filter(({ key }) => data.some((point) => Number.isFinite(Number(point[key]))));
  const width = 900;
  const height = 310;
  const pad = 28;
  const values = data.flatMap((point) => availableKeys.map(({ key }) => Number(point[key]))).filter(Number.isFinite);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = Math.max(max - min, 0.0001);
  const pathFor = (key: string) => data.map((point, index) => {
    const x = pad + (index / Math.max(data.length - 1, 1)) * (width - pad * 2);
    const y = height - pad - ((Number(point[key]) - min) / range) * (height - pad * 2);
    return `${index ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  return (
    <div className="research-chart-wrap">
      <svg className="research-line-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Curvas de capital del backtest">
        {[0, 1, 2, 3, 4].map((line) => <line key={line} x1={pad} x2={width - pad} y1={pad + line * ((height - pad * 2) / 4)} y2={pad + line * ((height - pad * 2) / 4)} />)}
        {availableKeys.map(({ key, color }) => <path key={key} d={pathFor(key)} style={{ stroke: color }} />)}
      </svg>
      <div className="chart-legend">{availableKeys.map(({ key, label, color }) => <span key={key}><i style={{ background: color }} />{label}</span>)}</div>
      <div className="chart-axis"><span>{String(data[0]?.date ?? "")}</span><span>{String(data[data.length - 1]?.date ?? "")}</span></div>
    </div>
  );
}

function ScoreWaterfall({ stock }: { stock: StockAnalysis }) {
  const fallback: ScoreContribution[] = (Object.entries(stock.scores) as Array<[ScoreContribution["group"], number]>).map(([group, value]) => ({
    feature: group,
    group,
    rawValue: `${value.toFixed(1)}/100`,
    normalized: value,
    weight: ({ technical: 25, fundamental: 30, news: 15, macro: 15, risk: 15 } as Record<string, number>)[group],
    contribution: ((value - 50) * ({ technical: .25, fundamental: .30, news: .15, macro: .15, risk: .15 } as Record<string, number>)[group]),
    formula: `(score ${group} - 50) × peso`,
    source: stock.trace?.method ?? "Score transparente",
    asOf: stock.asOf,
    status: "estimated",
  }));
  const explanation = stock.explanation;
  const contributions = explanation?.contributions ?? fallback;
  const maxMagnitude = Math.max(...contributions.map((item) => Math.abs(item.contribution)), 1);
  const base = explanation?.base ?? 50;
  const result = explanation?.result ?? stock.score;
  const interval = explanation?.interval ?? { low: Math.max(0, stock.score - 10), high: Math.min(100, stock.score + 10), level: 80 };
  return (
    <section className="research-panel score-explanation-panel">
      <div className="research-heading"><div><p className="eyebrow">Explicabilidad</p><h2>Por qué {stock.ticker} obtuvo {result.toFixed(1)}</h2></div><StatusPill live={Boolean(explanation)}>{explanation ? "Explicación generada" : "Reconstrucción compatible"}</StatusPill></div>
      <div className="score-equation"><span>Base <b>{base.toFixed(1)}</b></span><i>+</i><span>Contribuciones <b>{(result - base).toFixed(1)}</b></span><i>=</i><span>Resultado <b>{result.toFixed(1)}</b></span><span>Intervalo {interval.level}% <b>{interval.low.toFixed(1)}–{interval.high.toFixed(1)}</b></span></div>
      <div className="waterfall-list">
        {contributions.map((item) => {
          const positive = item.contribution >= 0;
          return <article key={`${item.group}-${item.feature}`}>
            <div><strong>{item.feature}</strong><small>{item.rawValue} · peso {item.weight.toFixed(1)}%</small></div>
            <div className="waterfall-track"><i className={positive ? "positive" : "negative"} style={{ width: `${Math.max(4, Math.abs(item.contribution) / maxMagnitude * 48)}%`, marginLeft: positive ? "50%" : `${50 - Math.abs(item.contribution) / maxMagnitude * 48}%` }} /></div>
            <b className={positive ? "up" : "down"}>{positive ? "+" : ""}{item.contribution.toFixed(2)}</b>
            <details><summary>Auditar variable</summary><p><b>Fórmula:</b> {item.formula}</p><p><b>Fuente:</b> {item.source}</p><p><b>Fecha:</b> {item.asOf}</p><p><b>Estado:</b> {item.status}</p></details>
          </article>;
        })}
      </div>
      <p className="research-note">El intervalo representa incertidumbre metodológica y cobertura de datos; no garantiza que el precio futuro permanezca dentro de ese rango.</p>
    </section>
  );
}

export default function ResearchLab({ stock, backtest: latestBacktest, backtestHistory, events, manifest, predictions, ledger, registry, monitoring, alerts, neural, neuralLedger }: Props) {
  const [selectedFingerprint, setSelectedFingerprint] = useState(backtestHistory.currentFingerprint);
  useEffect(() => {
    setSelectedFingerprint(backtestHistory.currentFingerprint);
  }, [backtestHistory.currentFingerprint]);
  const historyNewestFirst = [...backtestHistory.snapshots].reverse();
  const selectedSnapshot = backtestHistory.snapshots.find((item) => item.fingerprint === selectedFingerprint);
  const backtest = selectedSnapshot?.backtest ?? latestBacktest;
  const viewingArchivedRun = Boolean(selectedSnapshot && selectedSnapshot.fingerprint !== backtestHistory.currentFingerprint);
  const live = backtest.mode === "live";
  const statistical = backtest.metrics.statistical;
  const spy = backtest.metrics.spy;
  const visibleEvents = events.items.filter((item) => item.ticker === stock.ticker).slice(0, 8);
  const chartKeys = [
    { key: "spy", label: "SPY", color: "#8ea6a0" },
    { key: "technical", label: "Técnico", color: "#f3c56c" },
    { key: "heuristic", label: "Heurístico", color: "#68a8ff" },
    { key: "statistical", label: "Estadístico", color: "#70e6b1" },
    { key: "riskControlled", label: "Control de riesgo", color: "#d884ff" },
  ];
  return (
    <div className="research-page">
      <section className="research-hero">
        <div><p className="eyebrow">Hipótesis falsable · horizonte 60 sesiones</p><h2>Research Lab auditable</h2><p>{backtest.hypothesis}</p></div>
        <div className="run-proof"><StatusPill live={manifest.mode === "live"}>{manifest.mode === "live" ? "Ejecución real" : "Estructura de demostración"}</StatusPill><strong>{manifest.modelVersion}</strong><small>{manifest.runId}</small></div>
      </section>

      <div className="research-kpis">
        <Metric label="CAGR del modelo" value={live ? percent(statistical?.cagr ?? 0) : "Sin ejecutar"} help="Rendimiento anualizado fuera de muestra" />
        <Metric label="CAGR de SPY" value={live ? percent(spy?.cagr ?? 0) : "Sin ejecutar"} help="Benchmark para el mismo periodo" />
        <Metric label="Sharpe" value={live ? number(statistical?.sharpe ?? 0) : "N/D"} help="Retorno por unidad de volatilidad" />
        <Metric label="Drawdown máximo" value={live ? percent(statistical?.maxDrawdown ?? 0) : "N/D"} help="Mayor caída pico–valle" />
        <Metric label="Brier score" value={backtest.calibration.brierScore == null ? "N/D" : number(backtest.calibration.brierScore, 3)} help="Error de probabilidad; menor es mejor" />
        <Metric label="Cobertura de datos" value={`${manifest.dataCoverage.toFixed(1)}%`} help={`${manifest.assetsProcessed}/${manifest.assetsExpected} activos procesados`} />
      </div>

      <PredictionV5Lab ticker={stock.ticker} predictions={predictions} ledger={ledger} registry={registry} monitoring={monitoring} alerts={alerts} />

      <NeuralV8Lab ticker={stock.ticker} neural={neural} ledger={neuralLedger} />

      <section className="research-panel">
        <div className="research-heading">
          <div><p className="eyebrow">Validación histórica</p><h2>Capital fuera de muestra vs. SPY</h2></div>
          <div className="backtest-history-control">
            <StatusPill live={live}>{viewingArchivedRun ? "Ejecución archivada" : live ? `${backtest.period.start} — ${backtest.period.end}` : "Esperando pipeline"}</StatusPill>
            {historyNewestFirst.length > 0 && <label>Medición
              <select value={selectedFingerprint || backtestHistory.currentFingerprint} onChange={(event) => setSelectedFingerprint(event.target.value)}>
                {historyNewestFirst.map((item, index) => <option key={item.fingerprint} value={item.fingerprint}>{index === 0 ? "Actual · " : "Archivada · "}{item.backtest.generatedAt.slice(0, 10)} · {item.universeSize} activos</option>)}
              </select>
            </label>}
          </div>
        </div>
        <LineChart data={backtest.equity} keys={chartKeys} />
        <div className="method-strip"><span>Walk-forward anual</span><span>{backtest.horizonSessions} sesiones</span><span>{backtest.transactionCostBps} bps de costo</span><span>Sin información futura</span></div>
        <p className="research-note">{backtestHistory.snapshots.length > 0 ? `Historial inmutable activo: ${backtestHistory.snapshots.length} medición${backtestHistory.snapshots.length === 1 ? "" : "es"} conservada${backtestHistory.snapshots.length === 1 ? "" : "s"}.` : "El próximo pipeline comenzará a conservar cada medición distinta sin sobrescribir las anteriores."}</p>
      </section>

      <section className="research-panel">
        <div className="research-heading"><div><p className="eyebrow">Comparación de modelos</p><h2>Cinco métodos bajo el mismo protocolo</h2></div><StatusPill live={live}>{backtest.metrics.statistical?.observations ?? 0} rebalanceos</StatusPill></div>
        <div className="model-table">
          <div className="model-table-head"><span>Modelo</span><span>CAGR</span><span>Sharpe</span><span>Sortino</span><span>Drawdown</span><span>Aciertos</span><span>Alpha</span><span>Beta</span></div>
          {Object.entries(backtest.metrics).map(([key, metric]) => <div key={key}><strong>{backtest.methodology.models[key] ?? key}</strong><span>{live ? percent(metric.cagr) : "N/D"}</span><span>{live ? number(metric.sharpe) : "N/D"}</span><span>{live ? number(metric.sortino) : "N/D"}</span><span>{live ? percent(metric.maxDrawdown) : "N/D"}</span><span>{live ? percent(metric.hitRate) : "N/D"}</span><span>{live ? percent(metric.alpha) : "N/D"}</span><span>{live ? number(metric.beta) : "N/D"}</span></div>)}
        </div>
      </section>

      <ScoreWaterfall stock={stock} />

      <div className="research-two-column">
        <section className="research-panel">
          <div className="research-heading"><div><p className="eyebrow">Calibración</p><h2>Probabilidad predicha vs. observada</h2></div><StatusPill live={backtest.calibration.sampleSize > 0}>{backtest.calibration.sampleSize} predicciones</StatusPill></div>
          {backtest.calibration.bins.length ? <div className="calibration-bars">{backtest.calibration.bins.map((bin, index) => <article key={index}><span>{Math.round(bin.predicted * 100)}% pred.</span><div><i style={{ width: `${bin.observed * 100}%` }} /></div><strong>{Math.round(bin.observed * 100)}%</strong><small>n={bin.count}</small></article>)}</div> : <div className="chart-empty compact"><strong>Sin observaciones calibradas</strong><span>Se generarán después del primer backtest completo.</span></div>}
        </section>
        <section className="research-panel">
          <p className="eyebrow">Controles contra sesgos</p><h2>Qué impide un resultado artificial</h2>
          <ul className="research-checks">{backtest.methodology.safeguards.map((item) => <li key={item}><span>✓</span>{item}</li>)}</ul>
        </section>
      </div>

      <section className="research-panel">
        <div className="research-heading"><div><p className="eyebrow">Event study · {stock.ticker}</p><h2>¿Qué ocurrió después de cada noticia?</h2></div><StatusPill live={events.mode === "live"}>Cobertura {events.coverage.toFixed(1)}%</StatusPill></div>
        <p className="research-copy">{events.methodology}</p>
        {visibleEvents.length ? <div className="event-table"><div className="event-table-head"><span>Evento</span><span>Tipo</span><span>Relevancia</span><span>1 sesión</span><span>5 sesiones</span><span>20 sesiones</span><span>Estado</span></div>{visibleEvents.map((event) => <div key={`${event.publishedAt}-${event.title}`}><strong>{event.title}<small>{event.source} · {event.publishedAt}</small></strong><span>{event.eventType}</span><span>{Math.round(event.relevance * 100)}%</span><span>{event.abnormalReturn1d == null ? "Pendiente" : percent(event.abnormalReturn1d)}</span><span>{event.abnormalReturn5d == null ? "Pendiente" : percent(event.abnormalReturn5d)}</span><span>{event.abnormalReturn20d == null ? "Pendiente" : percent(event.abnormalReturn20d)}</span><span>{event.status}</span></div>)}</div> : <div className="chart-empty compact"><strong>No hay eventos medibles para {stock.ticker}</strong><span>El sistema no inventa retornos cuando aún no existe una ventana posterior suficiente.</span></div>}
      </section>

      <section className="research-panel limitation-panel">
        <p className="eyebrow">Límites publicados</p><h2>Qué todavía no puede concluir este experimento</h2>
        <ul>{backtest.methodology.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
      </section>
    </div>
  );
}
