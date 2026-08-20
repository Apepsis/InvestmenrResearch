import type { BuildJournal, ResearchManifest } from "@/lib/types";

export default function ConstructionLab({ journal, manifest }: { journal: BuildJournal; manifest: ResearchManifest }) {
  return (
    <div className="construction-page">
      <section className="research-hero construction-hero">
        <div><p className="eyebrow">Build journal · versión {journal.version}</p><h2>El proceso también es parte del resultado</h2><p>{journal.question}</p></div>
        <div className="run-proof"><span className={`research-status ${manifest.mode === "live" ? "is-live" : "is-sample"}`}>{manifest.mode === "live" ? "Última ejecución real" : "Proyecto en construcción"}</span><strong>{manifest.modelVersion}</strong><small>{manifest.generatedAt}</small></div>
      </section>

      <section className="research-panel">
        <p className="eyebrow">Principios de diseño</p><h2>Decisiones que limitan lo que el sistema puede afirmar</h2>
        <div className="principle-grid">{journal.principles.map((item, index) => <article key={item}><span>{String(index + 1).padStart(2, "0")}</span><strong>{item}</strong></article>)}</div>
      </section>

      <section className="research-panel">
        <div className="research-heading"><div><p className="eyebrow">Línea de construcción</p><h2>Problema → decisión → evidencia</h2></div><span className="research-status is-live">Documentado</span></div>
        <div className="build-timeline">{journal.milestones.map((item) => <article key={`${item.date}-${item.title}`}><div><span>{item.date}</span><i className={`status-${item.status}`} /></div><section><header><h3>{item.title}</h3><small>{item.status}</small></header><dl><div><dt>Problema</dt><dd>{item.problem}</dd></div><div><dt>Decisión</dt><dd>{item.decision}</dd></div><div><dt>Evidencia</dt><dd>{item.evidence}</dd></div></dl></section></article>)}</div>
      </section>

      <div className="research-two-column">
        <section className="research-panel failure-panel">
          <p className="eyebrow">Experimentos fallidos</p><h2>Qué se descartó y por qué</h2>
          <div className="failure-list">{journal.failedExperiments.map((item) => <article key={item.experiment}><strong>{item.experiment}</strong><p>{item.result}</p><span>Lección: {item.lesson}</span></article>)}</div>
        </section>
        <section className="research-panel">
          <p className="eyebrow">Próximos experimentos</p><h2>Trabajo todavía abierto</h2>
          <ol className="next-experiments">{journal.nextExperiments.map((item) => <li key={item}>{item}</li>)}</ol>
        </section>
      </div>

      <section className="research-panel limitation-panel">
        <p className="eyebrow">Limitaciones actuales</p><h2>Lo que un revisor debe conocer antes de interpretar resultados</h2>
        <ul>{journal.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
      </section>
    </div>
  );
}
