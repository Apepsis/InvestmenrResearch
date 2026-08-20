import type { MarketDataset, ResearchManifest, StockAnalysis } from "@/lib/types";

type Props = { market: MarketDataset; stock: StockAnalysis; manifest: ResearchManifest };

const statusLabel = (value: number | null) => value == null ? "No disponible" : "Verificado";

export default function MethodologyLab({ market, stock, manifest }: Props) {
  const sources = [
    { variable: `Precio diario ${stock.ticker}`, source: stock.trace?.prices ?? "Yahoo Finance mediante yfinance", date: stock.asOf, status: stock.price ? "Verificado" : "No disponible", use: "Técnico y respaldo" },
    { variable: `Fundamentales ${stock.ticker}`, source: stock.trace?.fundamentals ?? "SEC EDGAR; respaldo de mercado", date: stock.asOf, status: stock.fundamental.length ? "Verificado" : "No disponible", use: "Score fundamental" },
    { variable: `Noticias ${stock.ticker}`, source: stock.trace?.news ?? "Google News RSS y fuente original", date: market.generatedAt, status: stock.news.length ? "Clasificado" : "No disponible", use: "Eventos" },
    ...Object.values(market.macro).map((item) => ({ variable: item.label, source: item.source ?? "FRED", date: item.asOf, status: statusLabel(item.value), use: "Contexto macro" })),
    { variable: `Precio reciente ${stock.ticker}`, source: "Alpaca Basic · IEX mediante Cloudflare Worker", date: "Consulta mientras la página está abierta", status: "Independiente", use: "Panel y portafolio" },
  ];
  const artifacts = manifest.artifacts.length ? manifest.artifacts : [
    { name: "market.json", sha256: "Se genera durante el workflow", bytes: 0 },
    { name: "backtest.json", sha256: "Se genera durante el workflow", bytes: 0 },
    { name: "risk_model.json", sha256: "Se genera durante el workflow", bytes: 0 },
    { name: "event_studies.json", sha256: "Se genera durante el workflow", bytes: 0 },
  ];
  return (
    <div className="methodology-page">
      <section className="research-hero methodology-hero">
        <div><p className="eyebrow">Datos y metodología</p><h2>De la fuente a una conclusión auditable</h2><p>Cada cifra debe declarar su procedencia, fecha efectiva, transformación y función dentro del sistema.</p></div>
        <div className="coverage-orb"><strong>{manifest.dataCoverage.toFixed(0)}%</strong><span>cobertura</span></div>
      </section>

      <section className="research-panel">
        <div className="research-heading"><div><p className="eyebrow">Data lineage</p><h2>Evidencia utilizada para {stock.ticker}</h2></div><span className={`research-status ${market.mode === "live" ? "is-live" : "is-sample"}`}>{market.mode === "live" ? "Dataset real" : "Modo demostración"}</span></div>
        <div className="provenance-table">
          <div className="provenance-head"><span>Variable</span><span>Fuente</span><span>Fecha efectiva</span><span>Estado</span><span>Uso</span></div>
          {sources.map((item) => <div key={`${item.variable}-${item.source}`}><strong>{item.variable}</strong><span>{item.source}</span><span>{item.date}</span><span className={item.status === "No disponible" ? "down" : "up"}>{item.status}</span><span>{item.use}</span></div>)}
        </div>
      </section>

      <div className="research-two-column">
        <section className="research-panel">
          <p className="eyebrow">Arquitectura</p><h2>Separación de responsabilidades</h2>
          <div className="architecture-stack">
            <article><span>01</span><div><strong>Ingesta</strong><p>SEC, FRED, RSS, yfinance y Alpaca se consultan de forma aislada. Un proveedor no puede corromper toda la ejecución.</p></div></article>
            <article><span>02</span><div><strong>Validación</strong><p>Tipos, rangos, fechas, credenciales accidentales y cobertura mínima se verifican antes de publicar.</p></div></article>
            <article><span>03</span><div><strong>Investigación</strong><p>Features, backtest temporal, event studies y riesgo se calculan sin acceder a datos privados de Firebase.</p></div></article>
            <article><span>04</span><div><strong>Publicación</strong><p>GitHub Pages recibe únicamente artefactos JSON de solo lectura; Firestore conserva los datos privados por UID.</p></div></article>
          </div>
        </section>
        <section className="research-panel">
          <p className="eyebrow">Especificación del modelo</p><h2>{manifest.modelVersion}</h2>
          <dl className="model-spec">
            <div><dt>Objetivo</dt><dd>Retorno excedente positivo frente a SPY a 60 sesiones.</dd></div>
            <div><dt>Validación</dt><dd>Walk-forward anual con calibración temporal.</dd></div>
            <div><dt>Regularización</dt><dd>L2 para reducir sensibilidad a una muestra pequeña.</dd></div>
            <div><dt>Rebalanceo</dt><dd>Cada 60 sesiones; tres activos con mayor probabilidad estimada.</dd></div>
            <div><dt>Costos</dt><dd>10 puntos básicos descontados por rebalanceo.</dd></div>
            <div><dt>Salida</dt><dd>Probabilidad, score explicable, rango de incertidumbre y evidencia.</dd></div>
          </dl>
        </section>
      </div>

      <section className="research-panel">
        <div className="research-heading"><div><p className="eyebrow">Reproducibilidad</p><h2>Artefactos firmados por contenido</h2></div><span className={`research-status ${manifest.mode === "live" ? "is-live" : "is-sample"}`}>{manifest.runId}</span></div>
        <div className="manifest-grid">
          <article><span>Commit</span><strong>{manifest.gitCommit}</strong></article>
          <article><span>Hash del dataset</span><strong>{manifest.dataHash}</strong></article>
          <article><span>Pruebas aprobadas</span><strong>{manifest.testsPassed}</strong></article>
          <article><span>Duración</span><strong>{manifest.durationSeconds.toFixed(1)} s</strong></article>
          <article><span>Activos</span><strong>{manifest.assetsProcessed}/{manifest.assetsExpected}</strong></article>
          <article><span>Noticias</span><strong>{manifest.newsClassified}</strong></article>
        </div>
        <div className="artifact-list">{artifacts.map((item) => <article key={item.name}><strong>{item.name}</strong><span>{item.sha256}</span><small>{item.bytes ? `${new Intl.NumberFormat("en-US").format(item.bytes)} bytes` : "Pendiente de ejecución"}</small></article>)}</div>
      </section>

      <section className="research-panel limitation-panel">
        <p className="eyebrow">Reglas de honestidad</p><h2>El sistema prefiere “no disponible” antes que inventar un valor</h2>
        <ul><li>Los widgets externos no modifican el score.</li><li>Los precios por minuto no recalculan fundamentales.</li><li>Las noticias sin ventana posterior permanecen como “pendientes”.</li><li>Los datos revisados posteriormente no se presentan como si hubieran estado disponibles históricamente.</li><li>Los resultados de demostración se separan visualmente de una ejecución real.</li></ul>
      </section>
    </div>
  );
}
