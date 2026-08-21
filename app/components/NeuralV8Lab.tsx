import type { NeuralLabDataset, NeuralPredictionLedgerDataset } from "@/lib/types";

type Props = {
  ticker: string;
  neural: NeuralLabDataset;
  ledger: NeuralPredictionLedgerDataset;
};

const pct = (value: number, digits = 1) => `${(value * 100).toFixed(digits)}%`;
const metric = (value: number | undefined, digits = 3) => Number.isFinite(value) ? Number(value).toFixed(digits) : "N/D";

export default function NeuralV8Lab({ ticker, neural, ledger }: Props) {
  const predictions = neural.currentPredictions.filter((item) => item.ticker === ticker).sort((a, b) => a.horizonSessions - b.horizonSessions);
  const history = ledger.records.filter((item) => item.ticker === ticker).sort((a, b) => b.predictionDate.localeCompare(a.predictionDate)).slice(0, 9);
  const activeIsChampion = neural.active.role === "champion";
  const maximumSensitivity = Math.max(...neural.globalSensitivity.map((item) => item.meanAbsoluteProbabilityChange), .0001);
  const checks = Object.entries(neural.bestChallenger.promotionChecks);

  return (
    <section className="neural-v8-shell">
      <div className="neural-v8-header">
        <div>
          <p className="eyebrow">V8 · aprendizaje persistente y gobernado</p>
          <h2>Neural Model Observatory</h2>
          <p>{neural.hypothesis}</p>
        </div>
        <span className={`research-status ${activeIsChampion ? "is-live" : "is-sample"}`}>
          {activeIsChampion ? "Neural Champion" : "Shadow challenger"}
        </span>
      </div>

      <div className="neural-proof-grid">
        <article className="neural-architecture-card">
          <span>Arquitectura activa</span>
          <div className="neural-network-map" aria-label="Arquitectura de la red neuronal">
            <b>{neural.active.architecture.input}<small>variables</small></b><i>→</i>
            {neural.active.architecture.hidden.map((size, index) => <b key={index}>{size}<small>capa {index + 1}</small></b>)}<i>→</i>
            <b>{neural.active.architecture.output}<small>horizontes</small></b>
          </div>
          <p>{neural.active.architecture.ensembleMembers} redes · {neural.active.architecture.activation} · {neural.active.architecture.optimizer}</p>
        </article>
        <article><span>Memoria</span><strong>{neural.active.memory.method}</strong><small>{neural.active.memory.parentVersion ? `Continúa desde ${neural.active.memory.parentVersion}` : "Entrenamiento desde cero"}</small></article>
        <article><span>Pruebas intentadas</span><strong>{neural.governance.trialCount}</strong><small>El umbral aumenta al probar más variantes</small></article>
        <article><span>Modelos recuperados</span><strong>{neural.governance.archivedModelsReevaluated}</strong><small>Perdedores anteriores evaluados en el régimen actual</small></article>
      </div>

      <div className="neural-prediction-grid">
        {predictions.map((item) => <article key={item.id}>
          <header><span>{item.horizonSessions} sesiones</span><b>{item.modelRole === "champion" ? "OFICIAL" : "SHADOW"}</b></header>
          <strong>{pct(item.probability)}</strong>
          <p>P(superar SPY)</p>
          <div className="neural-probability"><i style={{ width: `${item.probability * 100}%` }} /></div>
          <dl>
            <div><dt>Banda 80%</dt><dd>{pct(item.uncertainty.low)}–{pct(item.uncertainty.high)}</dd></div>
            <div><dt>Desacuerdo</dt><dd>{pct(item.uncertainty.ensembleStd, 2)}</dd></div>
            <div><dt>Maduración</dt><dd>{item.estimatedMaturityDate}</dd></div>
          </dl>
        </article>)}
        {!predictions.length && <div className="chart-empty compact"><strong>V8 esperando su primera ejecución</strong><span>El workflow diario entrenará los challengers y guardará sus pesos.</span></div>}
      </div>

      <div className="neural-compare-grid">
        <article className="neural-metric-duel">
          <div><span>Referencia congelada</span><strong>{neural.reference.kind}</strong><small>{neural.reference.version}</small></div>
          <div><span>Mejor challenger</span><strong>{neural.bestChallenger.candidateKind}</strong><small>{neural.bestChallenger.version}</small></div>
          <div className="neural-metric-row"><span>Brier ↓</span><b>{metric(neural.reference.metrics.brierScore, 4)}</b><b>{metric(neural.bestChallenger.metrics.brierScore, 4)}</b></div>
          <div className="neural-metric-row"><span>Log loss ↓</span><b>{metric(neural.reference.metrics.logLoss, 4)}</b><b>{metric(neural.bestChallenger.metrics.logLoss, 4)}</b></div>
          <div className="neural-metric-row"><span>ECE ↓</span><b>{metric(neural.reference.metrics.ece, 4)}</b><b>{metric(neural.bestChallenger.metrics.ece, 4)}</b></div>
          <div className="neural-metric-row"><span>Acierto</span><b>{pct(neural.reference.metrics.accuracy)}</b><b>{pct(neural.bestChallenger.metrics.accuracy)}</b></div>
        </article>
        <article className="neural-gates">
          <span>Puerta de promoción</span>
          <strong>{neural.bestChallenger.qualified ? "Todos los controles aprobados" : "Champion protegido"}</strong>
          <div>{checks.map(([name, passed]) => <span key={name} className={passed ? "passed" : "failed"}><i>{passed ? "✓" : "×"}</i>{name}</span>)}</div>
          <small>Mejora Brier mínima ajustada: {neural.bestChallenger.requiredBrierImprovement.toFixed(5)}</small>
        </article>
      </div>

      <div className="neural-decision"><span>{neural.promotedThisRun ? "PROMOCIÓN" : "DECISIÓN"}</span><p>{neural.decision}</p></div>

      <div className="neural-two-column">
        <article className="neural-zoo">
          <div><p className="eyebrow">Model zoo</p><h3>Challengers y modelos recuperados</h3></div>
          <div className="neural-zoo-table">
            <div><span>Origen</span><span>Brier</span><span>Bloques</span><span>Estado</span></div>
            {neural.candidates.slice(0, 8).map((item) => <div key={item.version}>
              <strong>{item.candidateKind}<small>{item.source === "trained-this-run" ? "nuevo" : "archivado"}</small></strong>
              <span>{item.metrics.brierScore.toFixed(4)}</span>
              <span>{pct(item.metrics.temporalBlockWinRate ?? 0, 0)}</span>
              <b className={item.qualified ? "up" : "down"}>{item.qualified ? "califica" : "rechazado"}</b>
            </div>)}
          </div>
        </article>
        <article className="neural-sensitivity">
          <div><p className="eyebrow">Sensibilidad por ablación</p><h3>Qué utiliza la red</h3></div>
          {neural.globalSensitivity.slice(0, 8).map((item) => <div key={item.feature}>
            <span>{item.feature}</span><i><b style={{ width: `${Math.max(3, item.meanAbsoluteProbabilityChange / maximumSensitivity * 100)}%` }} /></i><strong>{pct(item.meanAbsoluteProbabilityChange, 2)}</strong>
          </div>)}
          {!neural.globalSensitivity.length && <p className="muted">Esperando el primer análisis de sensibilidad.</p>}
          <small>Sensibilidad no significa causalidad.</small>
        </article>
      </div>

      <div className="neural-audit-strip">
        <span><b>Entrena</b>{neural.temporalSplit.trainStart} → {neural.temporalSplit.trainEnd}</span>
        <span><b>Calibra</b>{neural.temporalSplit.calibrationStart} → {neural.temporalSplit.calibrationEnd}</span>
        <span><b>Shadow</b>{neural.temporalSplit.shadowStart} → {neural.temporalSplit.shadowEnd}</span>
        <span><b>Embargo</b>{neural.temporalSplit.purgeSessions} sesiones</span>
        <span><b>Pesos</b>{neural.reproducibility.savedWeights ? "guardados" : "no guardados"}</span>
      </div>

      {history.length > 0 && <details className="neural-ledger-details">
        <summary>Ver predicciones neuronales inmutables de {ticker} ({ledger.evaluatedCount}/{ledger.recordCount} evaluadas)</summary>
        <div>{history.map((item) => <span key={item.id}><b>{item.predictionDate}</b>{item.horizonSessions}d · {pct(item.probability)} · {item.status === "evaluated" ? item.correct ? "correcta" : "incorrecta" : "madurando"}</span>)}</div>
      </details>}

      <p className="research-note">La V8 no se autoautoriza a operar. Aprende y propone, pero una promoción solo cambia el modelo predictivo después de superar controles publicados; nunca reescribe resultados anteriores.</p>
    </section>
  );
}
