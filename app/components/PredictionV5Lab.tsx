import type {
  AlertDataset,
  LivePredictionsDataset,
  ModelMonitoringDataset,
  ModelRegistryDataset,
  PredictionLedgerDataset,
} from "@/lib/types";

type Props = {
  ticker: string;
  predictions: LivePredictionsDataset;
  ledger: PredictionLedgerDataset;
  registry: ModelRegistryDataset;
  monitoring: ModelMonitoringDataset;
  alerts: AlertDataset;
};

const pct = (value: number, digits = 1) => `${value >= 0 ? "+" : ""}${(value * 100).toFixed(digits)}%`;
const probability = (value: number) => `${(value * 100).toFixed(1)}%`;

export default function PredictionV5Lab({ ticker, predictions, ledger, registry, monitoring, alerts }: Props) {
  const current = predictions.predictions.filter((item) => item.ticker === ticker).sort((a, b) => a.horizonSessions - b.horizonSessions);
  const history = ledger.records.filter((item) => item.ticker === ticker).sort((a, b) => b.predictionDate.localeCompare(a.predictionDate)).slice(0, 12);
  const evaluated = ledger.records.filter((item) => item.status === "evaluated");
  const correct = evaluated.filter((item) => item.correct).length;
  const registryTone = registry.champion.key === "riskControlled" ? "is-live" : "is-sample";
  return (
    <>
      <section className="research-panel prediction-today">
        <div className="research-heading">
          <div><p className="eyebrow">Predicción publicada antes del resultado</p><h2>Predicción de hoy · {ticker}</h2><p className="research-copy">Tres horizontes independientes. La probabilidad, el precio inicial, el modelo y el hash quedan congelados en el ledger.</p></div>
          <span className={`research-status ${predictions.mode === "live" ? "is-live" : "is-sample"}`}>{predictions.mode === "live" ? "Registro real" : "Esperando pipeline"}</span>
        </div>
        {current.length ? <div className="prediction-grid">{current.map((item) => {
          const top = item.contributions[0];
          return <article key={item.id}>
            <header><span>{item.horizonSessions} sesiones</span><b>{item.status === "evaluated" ? "Evaluada" : "Activa"}</b></header>
            <strong>{probability(item.probability)}</strong>
            <p>P(superar SPY)</p>
            <div className="probability-track"><i style={{ width: `${item.probability * 100}%` }} /></div>
            <dl><div><dt>Banda empírica</dt><dd>{probability(item.uncertainty.low)}–{probability(item.uncertainty.high)}</dd></div><div><dt>Precio inicial</dt><dd>${item.initialPrice.toFixed(2)}</dd></div><div><dt>Evaluación estimada</dt><dd>{item.estimatedMaturityDate}</dd></div><div><dt>Cambio diario</dt><dd>{item.changeFromPrevious == null ? "Primera publicación" : pct(item.changeFromPrevious)}</dd></div></dl>
            {top && <small>Mayor contribución: {top.feature} ({top.logitContribution >= 0 ? "+" : ""}{top.logitContribution.toFixed(3)} logit)</small>}
          </article>;
        })}</div> : <div className="chart-empty compact"><strong>La V5 todavía no se ha ejecutado</strong><span>Ejecuta “Actualizar datos e investigación” una vez después de subir estos archivos.</span></div>}
        <p className="research-note">Una probabilidad alta activa una revisión, no una compra automática. El sistema no opera ni modifica retroactivamente una predicción.</p>
      </section>

      <section className="research-panel">
        <div className="research-heading"><div><p className="eyebrow">Registro permanente</p><h2>Ledger inmutable de {ticker}</h2></div><span className="research-status is-live">{ledger.evaluatedCount}/{ledger.recordCount} evaluadas</span></div>
        {history.length ? <div className="ledger-table"><div className="ledger-head"><span>Publicación</span><span>Horizonte</span><span>Probabilidad</span><span>Precio inicial</span><span>Estado</span><span>Exceso vs. SPY</span><span>Correcta</span></div>{history.map((item) => <div key={item.id}><span>{item.predictionDate}</span><span>{item.horizonSessions} sesiones</span><span>{probability(item.probability)}</span><span>${item.initialPrice.toFixed(2)}</span><span>{item.status === "evaluated" ? `Evaluada ${item.evaluatedOn}` : "Esperando"}</span><span>{item.excessReturn == null ? "Pendiente" : pct(item.excessReturn)}</span><span>{item.correct == null ? "—" : item.correct ? "Sí" : "No"}</span></div>)}</div> : <div className="chart-empty compact"><strong>Sin predicciones publicadas</strong><span>El primer registro aparecerá tras la ejecución diaria.</span></div>}
        <div className="ledger-summary"><span>Política <b>append-only</b></span><span>Aciertos maduros <b>{evaluated.length ? `${correct}/${evaluated.length}` : "Pendiente"}</b></span><span>Versión <b>{predictions.modelVersion}</b></span></div>
      </section>

      <div className="research-two-column governance-grid">
        <section className="research-panel">
          <div className="research-heading"><div><p className="eyebrow">Champion vs. challenger</p><h2>Gobernanza del modelo</h2></div><span className={`research-status ${registryTone}`}>{registry.qualificationStreak}/{registry.requiredStreak} ejecuciones</span></div>
          <div className="model-duel"><article><span>Champion</span><strong>{registry.champion.key}</strong><small>{registry.champion.version}</small><b>Sharpe {registry.champion.metrics.sharpe.toFixed(2)}</b></article><article><span>Challenger</span><strong>{registry.challenger.key}</strong><small>{registry.challenger.version}</small><b>DD {pct(registry.challenger.metrics.maxDrawdown)}</b></article></div>
          <ul className="criteria-list">{Object.entries(registry.promotionCriteria).map(([key, passed]) => <li key={key} className={passed ? "passed" : "failed"}><span>{passed ? "✓" : "×"}</span>{key}</li>)}</ul>
          <p className="research-copy">{registry.decision} {registry.guardrail}</p>
        </section>

        <section className="research-panel">
          <div className="research-heading"><div><p className="eyebrow">Model monitoring</p><h2>Drift, datos y precisión</h2></div><span className={`research-status ${monitoring.status === "healthy" ? "is-live" : "is-sample"}`}>{monitoring.status}</span></div>
          <div className="monitor-grid"><article><span>Cobertura</span><strong>{probability(monitoring.data.predictionCoverage)}</strong></article><article><span>Antigüedad</span><strong>{monitoring.data.marketDataAgeHours.toFixed(1)} h</strong></article><article><span>Drift máximo</span><strong>{monitoring.featureDrift.maximumAbsoluteShift.toFixed(2)}σ</strong></article><article><span>Brier realizado</span><strong>{monitoring.performance.brierScore == null ? "Madurando" : monitoring.performance.brierScore.toFixed(3)}</strong></article></div>
          {monitoring.issues.length ? <ul className="monitor-issues">{monitoring.issues.map((item) => <li key={item.code}><b>{item.severity}</b>{item.message}</li>)}</ul> : <p className="monitor-ok">✓ Sin anomalías por encima de los umbrales publicados.</p>}
        </section>
      </div>

      <section className="research-panel alert-panel">
        <div className="research-heading"><div><p className="eyebrow">Alertas deduplicadas</p><h2>Emergencias y oportunidades para revisar</h2></div><span className={`research-status ${alerts.deliveryStatus === "sent" || alerts.deliveryStatus === "no-new-alerts" ? "is-live" : "is-sample"}`}>{alerts.deliveryEnabled ? alerts.deliveryStatus : "Correo desactivado"}</span></div>
        <p className="research-copy">{alerts.policy}</p>
        {alerts.candidates.length ? <div className="alert-list">{alerts.candidates.map((item) => <article key={item.fingerprint}><span className={`alert-severity ${item.severity}`}>{item.severity}</span><div><strong>{item.title}</strong><p>{item.message}</p></div></article>)}</div> : <div className="chart-empty compact"><strong>No hay alertas activas</strong><span>Esto significa que ningún umbral conservador se superó en esta ejecución.</span></div>}
      </section>
    </>
  );
}
