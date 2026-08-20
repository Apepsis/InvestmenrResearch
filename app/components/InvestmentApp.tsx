"use client";

import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import {
  GoogleAuthProvider,
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut,
  type User,
} from "firebase/auth";
import {
  addDoc,
  collection,
  deleteDoc,
  doc,
  onSnapshot,
  setDoc,
} from "firebase/firestore";
import { LiveMarketChart, LiveMarketNews } from "@/app/components/TradingViewWidgets";
import { demoMarket } from "@/data/demo";
import { firebaseConfigured, getFirebaseServices } from "@/lib/firebase";
import type {
  JournalEntry,
  MarketDataset,
  Position,
  ScoreKey,
  WatchItem,
  Weights,
} from "@/lib/types";

type View = "dashboard" | "analysis" | "portfolio" | "watchlist" | "journal" | "settings";

const defaultWeights: Weights = { technical: 25, fundamental: 30, news: 15, macro: 15, risk: 15 };
const scoreLabels: Record<ScoreKey, string> = {
  technical: "Tecnico",
  fundamental: "Fundamental",
  news: "Noticias",
  macro: "Macro",
  risk: "Riesgo",
};

const nav: { id: View; label: string; glyph: string }[] = [
  { id: "dashboard", label: "Panel", glyph: "D" },
  { id: "analysis", label: "Analisis", glyph: "A" },
  { id: "portfolio", label: "Portafolio", glyph: "P" },
  { id: "watchlist", label: "Vigilancia", glyph: "V" },
  { id: "journal", label: "Diario", glyph: "J" },
  { id: "settings", label: "Ajustes", glyph: "C" },
];

const money = (value: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(value);

function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`card ${className}`}>{children}</section>;
}

function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: "positive" | "neutral" | "negative" }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

function ScoreRing({ score }: { score: number }) {
  return (
    <div className="score-ring" style={{ "--score": `${score * 3.6}deg` } as React.CSSProperties}>
      <div><strong>{Math.round(score)}</strong><span>/ 100</span></div>
    </div>
  );
}

function SetupNotice({ onDemo }: { onDemo: () => void }) {
  return (
    <main className="auth-shell">
      <div className="auth-brand">
        <div className="brand-mark">↗</div>
        <span>Investment Research Agent</span>
      </div>
      <Card className="setup-card">
        <p className="eyebrow">Un paso antes de ingresar</p>
        <h1>Conecta tu proyecto de Firebase</h1>
        <p className="muted">
          La aplicacion ya esta lista, pero necesita las seis variables de configuracion de tu app web para activar el inicio de sesion y Firestore.
        </p>
        <ol className="setup-steps">
          <li>Copia <code>.env.example</code> como <code>.env</code>.</li>
          <li>Pega los valores del objeto <code>firebaseConfig</code>.</li>
          <li>Activa Email/Password y Google en Firebase Authentication.</li>
          <li>Publica las reglas incluidas en <code>firestore.rules</code>.</li>
        </ol>
        <button className="primary-button" onClick={onDemo}>Explorar la demostracion</button>
        <p className="fine-print">La clave web de Firebase identifica tu proyecto; la proteccion real esta en las reglas de Firestore incluidas.</p>
      </Card>
    </main>
  );
}

function AuthScreen({ onDemo }: { onDemo: () => void }) {
  const services = useMemo(() => getFirebaseServices(), []);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!services) return;
    setBusy(true);
    setError("");
    try {
      if (mode === "login") await signInWithEmailAndPassword(services.auth, email, password);
      else await createUserWithEmailAndPassword(services.auth, email, password);
    } catch {
      setError("No se pudo completar el acceso. Revisa el correo, la contrasena y la configuracion de Firebase.");
    } finally {
      setBusy(false);
    }
  }

  async function googleLogin() {
    if (!services) return;
    setBusy(true);
    setError("");
    try {
      await signInWithPopup(services.auth, new GoogleAuthProvider());
    } catch {
      setError("Google no pudo iniciar sesion. Confirma que el proveedor este habilitado y que tu dominio este autorizado.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-shell">
      <div className="auth-brand"><div className="brand-mark">↗</div><span>Investment Research Agent</span></div>
      <Card className="auth-card">
        <p className="eyebrow">Investigacion personal</p>
        <h1>{mode === "login" ? "Bienvenido de nuevo" : "Crea tu cuenta"}</h1>
        <p className="muted">Tus posiciones, tesis y listas se sincronizan entre laptop y celular.</p>
        <div className="auth-tabs">
          <button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>Ingresar</button>
          <button className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>Registrarme</button>
        </div>
        <form onSubmit={submit} className="stack-form">
          <label>Correo<input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="tu@correo.com" /></label>
          <label>Contrasena<input type="password" required minLength={6} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Minimo 6 caracteres" /></label>
          {error && <p className="form-error">{error}</p>}
          <button className="primary-button" disabled={busy}>{busy ? "Procesando..." : mode === "login" ? "Ingresar" : "Crear cuenta"}</button>
        </form>
        <div className="or"><span>o</span></div>
        <button className="secondary-button" onClick={googleLogin} disabled={busy}>Continuar con Google</button>
        <button className="text-button" onClick={onDemo}>Ver demo sin iniciar sesion</button>
      </Card>
    </main>
  );
}

export default function InvestmentApp() {
  const [authReady, setAuthReady] = useState(!firebaseConfigured);
  const [user, setUser] = useState<User | null>(null);
  const [demo, setDemo] = useState(false);
  const [view, setView] = useState<View>("dashboard");
  const [market, setMarket] = useState<MarketDataset>(demoMarket);
  const [selectedTicker, setSelectedTicker] = useState("UBER");
  const [positions, setPositions] = useState<Position[]>([]);
  const [watchlist, setWatchlist] = useState<WatchItem[]>([]);
  const [journal, setJournal] = useState<JournalEntry[]>([]);
  const [weights, setWeights] = useState<Weights>(defaultWeights);
  const [notice, setNotice] = useState("");
  const services = useMemo(() => getFirebaseServices(), []);

  useEffect(() => {
    fetch(new URL("data/market.json", document.baseURI))
      .then((response) => (response.ok ? response.json() : Promise.reject()))
      .then((data: MarketDataset) => {
        if (data?.stocks && Object.keys(data.stocks).length) setMarket(data);
      })
      .catch(() => setMarket(demoMarket));
  }, []);

  useEffect(() => {
    if (!services) return;
    return onAuthStateChanged(services.auth, (nextUser) => {
      setUser(nextUser);
      setAuthReady(true);
      if (nextUser) setDemo(false);
    });
  }, [services]);

  useEffect(() => {
    if (!services || !user) return;
    const cleanups = [
      onSnapshot(collection(services.db, "users", user.uid, "portfolio"), (snap) => setPositions(snap.docs.map((item) => ({ id: item.id, ...item.data() } as Position)))),
      onSnapshot(collection(services.db, "users", user.uid, "watchlist"), (snap) => setWatchlist(snap.docs.map((item) => ({ id: item.id, ...item.data() } as WatchItem)))),
      onSnapshot(collection(services.db, "users", user.uid, "journal"), (snap) => setJournal(snap.docs.map((item) => ({ id: item.id, ...item.data() } as JournalEntry)).sort((a, b) => b.createdAt.localeCompare(a.createdAt)))),
      onSnapshot(doc(services.db, "users", user.uid, "settings", "preferences"), (snap) => {
        if (snap.exists()) setWeights({ ...defaultWeights, ...(snap.data().weights as Weights) });
      }),
    ];
    return () => cleanups.forEach((cleanup) => cleanup());
  }, [services, user]);

  const stock = market.stocks[selectedTicker] ?? Object.values(market.stocks)[0];
  const tickers = Object.keys(market.stocks);
  const totalPortfolio = useMemo(
    () => positions.reduce((sum, position) => sum + (market.stocks[position.ticker]?.price ?? position.averageCost) * position.shares, 0),
    [positions, market],
  );
  const costPortfolio = positions.reduce((sum, position) => sum + position.averageCost * position.shares, 0);
  const portfolioReturn = costPortfolio ? ((totalPortfolio - costPortfolio) / costPortfolio) * 100 : 0;

  function flash(message: string) {
    setNotice(message);
    window.setTimeout(() => setNotice(""), 2600);
  }

  async function addPosition(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    const item = {
      ticker: String(values.get("ticker") || "").toUpperCase(),
      shares: Number(values.get("shares")),
      averageCost: Number(values.get("averageCost")),
      createdAt: new Date().toISOString(),
    };
    if (!item.ticker || item.shares <= 0 || item.averageCost <= 0) return;
    if (services && user) await addDoc(collection(services.db, "users", user.uid, "portfolio"), item);
    else setPositions((current) => [...current, { id: crypto.randomUUID(), ...item }]);
    event.currentTarget.reset();
    flash(user ? "Posicion guardada y sincronizada." : "Posicion agregada solo a esta demo.");
  }

  async function addWatch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    const item = {
      ticker: String(values.get("ticker") || "").toUpperCase(),
      targetPrice: Number(values.get("targetPrice")) || null,
      note: String(values.get("note") || ""),
      createdAt: new Date().toISOString(),
    };
    if (!item.ticker) return;
    if (services && user) await addDoc(collection(services.db, "users", user.uid, "watchlist"), item);
    else setWatchlist((current) => [...current, { id: crypto.randomUUID(), ...item }]);
    event.currentTarget.reset();
    flash(user ? "Activo agregado a vigilancia." : "Activo agregado solo a esta demo.");
  }

  async function addJournal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    const item = {
      ticker: String(values.get("ticker") || "").toUpperCase(),
      decision: String(values.get("decision")) as JournalEntry["decision"],
      confidence: Number(values.get("confidence")),
      thesis: String(values.get("thesis") || ""),
      invalidation: String(values.get("invalidation") || ""),
      createdAt: new Date().toISOString(),
    };
    if (!item.ticker || !item.thesis) return;
    if (services && user) await addDoc(collection(services.db, "users", user.uid, "journal"), item);
    else setJournal((current) => [{ id: crypto.randomUUID(), ...item }, ...current]);
    event.currentTarget.reset();
    flash(user ? "Entrada guardada en tu diario." : "Entrada agregada solo a esta demo.");
  }

  async function removeItem(kind: "portfolio" | "watchlist" | "journal", id: string) {
    if (services && user) await deleteDoc(doc(services.db, "users", user.uid, kind, id));
    else if (kind === "portfolio") setPositions((items) => items.filter((item) => item.id !== id));
    else if (kind === "watchlist") setWatchlist((items) => items.filter((item) => item.id !== id));
    else setJournal((items) => items.filter((item) => item.id !== id));
  }

  async function saveWeights() {
    if (Object.values(weights).reduce((sum, value) => sum + value, 0) !== 100) {
      flash("Los pesos deben sumar exactamente 100%.");
      return;
    }
    if (services && user) await setDoc(doc(services.db, "users", user.uid, "settings", "preferences"), { weights, updatedAt: new Date().toISOString() });
    flash(user ? "Pesos sincronizados." : "Pesos aplicados solo a esta demo.");
  }

  if (!authReady) return <main className="loading-screen"><div className="loader" /><span>Preparando tu espacio...</span></main>;
  if (!firebaseConfigured && !demo) return <SetupNotice onDemo={() => setDemo(true)} />;
  if (firebaseConfigured && !user && !demo) return <AuthScreen onDemo={() => setDemo(true)} />;

  const dataTone = market.mode === "live" ? "positive" : "neutral";
  const dataLabel = market.mode === "live" ? "Datos actualizados" : "Datos de demostracion";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark">↗</div><div><strong>Investment</strong><span>Research Agent</span></div></div>
        <nav>{nav.map((item) => <button key={item.id} className={view === item.id ? "active" : ""} onClick={() => setView(item.id)}><span>{item.glyph}</span>{item.label}</button>)}</nav>
        <div className="sidebar-foot">
          <div className="user-chip"><div>{(user?.email ?? "D").charAt(0).toUpperCase()}</div><span><strong>{user ? "Cuenta conectada" : "Modo demo"}</strong><small>{user?.email ?? "Sin sincronizacion"}</small></span></div>
          {user ? <button className="logout" onClick={() => services && signOut(services.auth)}>Cerrar sesion</button> : <button className="logout" onClick={() => setDemo(false)}>Ir al acceso</button>}
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div><p className="eyebrow">Horizonte de 1 mes a 1 ano</p><h1>{nav.find((item) => item.id === view)?.label}</h1></div>
          <div className="top-actions">
            <Badge tone={dataTone}>{dataLabel}</Badge>
            <label className="ticker-select"><span>Activo</span><select value={selectedTicker} onChange={(e) => setSelectedTicker(e.target.value)}>{tickers.map((ticker) => <option key={ticker}>{ticker}</option>)}</select></label>
          </div>
        </header>

        {notice && <div className="toast">{notice}</div>}

        {view === "dashboard" && (
          <div className="page-grid dashboard-page">
            <Card className="hero-card live-market-card">
              <div className="card-heading live-card-heading">
                <div className="stock-heading">
                  <div className="ticker-logo">{stock.ticker.slice(0, 2)}</div>
                  <div><div className="title-line"><h2>{stock.name}</h2><Badge tone="neutral">{stock.ticker}</Badge></div><p>{stock.sector} · {stock.currency}</p></div>
                </div>
                <Badge tone="positive">Grafica dinamica</Badge>
              </div>
              <LiveMarketChart ticker={stock.ticker} />
              <div className="analysis-data-stamp">
                <span>El score y el portafolio usan el ultimo analisis guardado.</span>
                <strong>{market.mode === "live" ? market.generatedAt : "Modo demostracion"}</strong>
              </div>
            </Card>

            <Card className="score-card">
              <div className="card-heading"><div><p className="eyebrow">Score compuesto</p><h2>{stock.verdict}</h2></div><Badge tone={stock.score >= 60 ? "positive" : stock.score >= 40 ? "neutral" : "negative"}>{stock.confidence}% confianza</Badge></div>
              <ScoreRing score={stock.score} />
              <div className="score-bars">{(Object.keys(stock.scores) as ScoreKey[]).map((key) => <div key={key}><span>{scoreLabels[key]}</span><div><i style={{ width: `${stock.scores[key]}%` }} /></div><strong>{Math.round(stock.scores[key])}</strong></div>)}</div>
            </Card>

            <Card className="thesis-card">
              <div className="card-heading"><div><p className="eyebrow">Tesis explicable</p><h2>Por que podria importar</h2></div><button className="link-button" onClick={() => setView("analysis")}>Ver analisis completo →</button></div>
              <ul className="evidence-list">{stock.thesis.map((item, index) => <li key={item}><span>{index + 1}</span><p>{item}</p></li>)}</ul>
            </Card>

            <Card className="risk-card">
              <p className="eyebrow">Control humano</p><h2>Riesgos que no debes ignorar</h2>
              <ul>{stock.risks.slice(0, 3).map((risk) => <li key={risk}>{risk}</li>)}</ul>
              <div className="disclaimer">No es una orden de compra o venta. Verifica datos y decide segun tu tolerancia al riesgo.</div>
            </Card>

            <Card className="committee-card">
              <div className="card-heading"><div><p className="eyebrow">Comite artificial</p><h2>Perspectivas y desacuerdos</h2></div><span className="tiny-label">5 agentes</span></div>
              <div className="committee-grid">{stock.committee.map((agent) => <article key={agent.agent}><div><span className={`tone-dot ${agent.tone}`} /><strong>{agent.agent}</strong><small>{agent.focus}</small></div><p>{agent.view}</p></article>)}</div>
            </Card>

            <Card className="portfolio-mini">
              <div className="card-heading"><div><p className="eyebrow">Portafolio</p><h2>{positions.length ? money(totalPortfolio) : "Aun sin posiciones"}</h2></div>{positions.length > 0 && <Badge tone={portfolioReturn >= 0 ? "positive" : "negative"}>{portfolioReturn >= 0 ? "+" : ""}{portfolioReturn.toFixed(1)}%</Badge>}</div>
              <p className="muted">Analiza cada activo dentro de tu exposicion total, no de forma aislada.</p>
              <button className="secondary-button" onClick={() => setView("portfolio")}>{positions.length ? "Revisar portafolio" : "Agregar primera posicion"}</button>
            </Card>
          </div>
        )}

        {view === "analysis" && (
          <div className="analysis-page">
            <section className="analysis-intro"><div><p className="eyebrow">{stock.ticker} · Analisis integrado</p><h2>{stock.name}</h2><p>La salida combina evidencias independientes y conserva lo que invalidaria la tesis.</p></div><ScoreRing score={stock.score} /></section>
            <Card className="live-news-card">
              <div className="card-heading live-card-heading"><div><p className="eyebrow">Vigilancia informativa</p><h2>Noticias dinamicas de {stock.ticker}</h2></div><Badge tone="positive">Actualizacion externa</Badge></div>
              <p className="live-card-copy">Utiliza este bloque para detectar eventos recientes. Las noticias clasificadas y el score que aparecen debajo corresponden a la ultima ejecucion completa del agente.</p>
              <LiveMarketNews ticker={stock.ticker} />
            </Card>
            <div className="two-column">
              <Card><div className="card-heading"><h2>Analisis tecnico</h2><Badge tone="positive">{stock.scores.technical}/100</Badge></div><div className="indicator-list">{stock.technical.map((item) => <article key={item.label}><span className={`tone-dot ${item.tone}`} /><div><strong>{item.label}</strong><p>{item.interpretation}</p></div><b>{item.value}</b></article>)}</div></Card>
              <Card><div className="card-heading"><h2>Analisis fundamental</h2><Badge tone="positive">{stock.scores.fundamental}/100</Badge></div><div className="indicator-list">{stock.fundamental.map((item) => <article key={item.label}><span className={`tone-dot ${item.tone}`} /><div><strong>{item.label}</strong><p>{item.interpretation}</p></div><b>{item.value}</b></article>)}</div></Card>
            </div>
            <div className="two-column">
              <Card><p className="eyebrow">Noticias clasificadas</p><h2>Eventos recientes</h2><div className="news-list">{stock.news.map((item) => <a key={item.title} href={item.url === "#" ? undefined : item.url} target="_blank" rel="noreferrer"><div><Badge tone={item.sentiment}>{item.sentiment}</Badge><span>{item.source}</span></div><strong>{item.title}</strong><small>{item.eventType} · {item.duration} · confianza {Math.round(item.confidence * 100)}%</small></a>)}</div></Card>
              <Card><p className="eyebrow">Prueba de falsacion</p><h2>Que invalidaria la tesis</h2><ul className="warning-list">{stock.invalidation.map((item) => <li key={item}><span>!</span>{item}</li>)}</ul></Card>
            </div>
            <Card><div className="card-heading"><div><p className="eyebrow">Entorno economico</p><h2>Variables macro</h2></div><Badge tone={market.mode === "live" ? "positive" : "neutral"}>{market.generatedAt}</Badge></div><div className="macro-grid">{Object.values(market.macro).map((item) => <article key={item.label}><span>{item.label}</span><strong>{item.value == null ? "Pendiente" : `${item.value.toFixed(2)} ${item.unit}`}</strong><small>{item.asOf}</small></article>)}</div></Card>
          </div>
        )}

        {view === "portfolio" && (
          <div className="management-page">
            <div className="summary-strip"><div><span>Valor actual</span><strong>{money(totalPortfolio)}</strong></div><div><span>Costo invertido</span><strong>{money(costPortfolio)}</strong></div><div><span>Resultado</span><strong className={portfolioReturn >= 0 ? "up" : "down"}>{portfolioReturn >= 0 ? "+" : ""}{portfolioReturn.toFixed(2)}%</strong></div><div><span>Posiciones</span><strong>{positions.length}</strong></div></div>
            <div className="two-column form-layout"><Card><p className="eyebrow">Nueva posicion</p><h2>Agrega una compra</h2><form className="stack-form" onSubmit={addPosition}><label>Ticker<select name="ticker" defaultValue={selectedTicker}>{tickers.map((ticker) => <option key={ticker}>{ticker}</option>)}</select></label><div className="form-row"><label>Acciones<input name="shares" type="number" min="0.0001" step="0.0001" required /></label><label>Costo promedio<input name="averageCost" type="number" min="0.01" step="0.01" required /></label></div><button className="primary-button">Guardar posicion</button></form></Card><Card><p className="eyebrow">Diagnostico de cartera</p><h2>{positions.length ? "Exposicion registrada" : "Empieza por tus posiciones reales"}</h2><p className="muted">El asistente calcula valor, retorno y concentracion usando el ultimo precio disponible. No calcula impuestos ni comisiones.</p><div className="metric-callout"><span>Mayor exposicion individual</span><strong>{positions.length ? `${Math.max(...positions.map((p) => ((market.stocks[p.ticker]?.price ?? p.averageCost) * p.shares / Math.max(totalPortfolio, 1)) * 100)).toFixed(1)}%` : "0%"}</strong></div></Card></div>
            <Card><div className="card-heading"><h2>Posiciones</h2><span className="tiny-label">Sincronizadas por usuario</span></div>{positions.length ? <div className="data-table"><div className="table-head"><span>Activo</span><span>Cantidad</span><span>Costo</span><span>Actual</span><span>Resultado</span><span /></div>{positions.map((position) => { const current = market.stocks[position.ticker]?.price ?? position.averageCost; const result = ((current - position.averageCost) / position.averageCost) * 100; return <div key={position.id}><strong>{position.ticker}</strong><span>{position.shares}</span><span>{money(position.averageCost)}</span><span>{money(current)}</span><span className={result >= 0 ? "up" : "down"}>{result >= 0 ? "+" : ""}{result.toFixed(1)}%</span><button onClick={() => removeItem("portfolio", position.id)} aria-label={`Eliminar ${position.ticker}`}>×</button></div>; })}</div> : <EmptyState title="Aun no hay posiciones" text="Agrega tu primera compra para evaluar concentracion y resultado." />}</Card>
          </div>
        )}

        {view === "watchlist" && (
          <div className="management-page"><div className="two-column form-layout"><Card><p className="eyebrow">Lista de vigilancia</p><h2>Define que estas esperando</h2><form className="stack-form" onSubmit={addWatch}><div className="form-row"><label>Ticker<select name="ticker" defaultValue={selectedTicker}>{tickers.map((ticker) => <option key={ticker}>{ticker}</option>)}</select></label><label>Precio objetivo<input name="targetPrice" type="number" min="0" step="0.01" placeholder="Opcional" /></label></div><label>Condicion o nota<textarea name="note" placeholder="Ej.: esperar confirmacion de margen y entrada por debajo de..." /></label><button className="primary-button">Agregar a vigilancia</button></form></Card><Card><p className="eyebrow">Disciplina</p><h2>Una lista no es una recomendacion</h2><p className="muted">Registra por adelantado el precio, evento o cambio fundamental que justificaria revisar la tesis. Esto reduce decisiones por impulso.</p></Card></div><Card><div className="card-heading"><h2>Activos vigilados</h2><Badge tone="neutral">{watchlist.length}</Badge></div>{watchlist.length ? <div className="watch-grid">{watchlist.map((item) => { const current = market.stocks[item.ticker]?.price; return <article key={item.id}><div><span className="ticker-logo small">{item.ticker.slice(0, 2)}</span><div><strong>{item.ticker}</strong><small>{market.stocks[item.ticker]?.name ?? "Sin datos de mercado"}</small></div><button onClick={() => removeItem("watchlist", item.id)}>×</button></div><p>{item.note || "Sin condicion registrada."}</p><div><span>Actual <b>{current ? money(current) : "N/D"}</b></span><span>Objetivo <b>{item.targetPrice ? money(item.targetPrice) : "N/D"}</b></span></div></article>; })}</div> : <EmptyState title="Tu lista esta vacia" text="Agrega activos y la condicion que debe cumplirse antes de actuar." />}</Card></div>
        )}

        {view === "journal" && (
          <div className="management-page"><div className="two-column form-layout"><Card><p className="eyebrow">Nueva decision</p><h2>Registra tu razonamiento</h2><form className="stack-form" onSubmit={addJournal}><div className="form-row"><label>Ticker<select name="ticker" defaultValue={selectedTicker}>{tickers.map((ticker) => <option key={ticker}>{ticker}</option>)}</select></label><label>Decision<select name="decision"><option>Esperar</option><option>Comprar por tramos</option><option>Mantener</option><option>Evitar</option></select></label></div><label>Confianza: <output id="confidenceOutput">60%</output><input name="confidence" type="range" min="0" max="100" defaultValue="60" onInput={(e) => { const out = document.getElementById("confidenceOutput"); if (out) out.textContent = `${e.currentTarget.value}%`; }} /></label><label>Tesis<textarea name="thesis" required placeholder="Que evidencias sostienen tu decision?" /></label><label>Invalidacion<textarea name="invalidation" placeholder="Que hecho demostraria que estabas equivocado?" /></label><button className="primary-button">Guardar en el diario</button></form></Card><Card><p className="eyebrow">Revision futura</p><h2>Separa proceso de resultado</h2><p className="muted">Una buena decision puede tener un mal resultado y viceversa. El diario conserva lo que sabias al momento de decidir.</p><div className="metric-callout"><span>Entradas registradas</span><strong>{journal.length}</strong></div></Card></div><div className="journal-list">{journal.length ? journal.map((entry) => <Card key={entry.id}><div className="journal-top"><div><Badge tone="neutral">{entry.ticker}</Badge><h2>{entry.decision}</h2></div><button onClick={() => removeItem("journal", entry.id)}>×</button></div><div className="confidence-bar"><i style={{ width: `${entry.confidence}%` }} /><span>{entry.confidence}% confianza</span></div><p>{entry.thesis}</p>{entry.invalidation && <div className="invalidation"><strong>Invalidacion</strong><span>{entry.invalidation}</span></div>}<small>{new Date(entry.createdAt).toLocaleString("es-PE")}</small></Card>) : <Card><EmptyState title="No hay decisiones registradas" text="Documenta una tesis antes de comprar, vender o esperar." /></Card>}</div></div>
        )}

        {view === "settings" && (
          <div className="settings-page"><Card><p className="eyebrow">Motor de puntuacion</p><h2>Ajusta la importancia de cada evidencia</h2><p className="muted">Los cinco pesos deben sumar 100%. Los valores originales del blueprint se muestran por defecto.</p><div className="weight-list">{(Object.keys(weights) as ScoreKey[]).map((key) => <label key={key}><span>{scoreLabels[key]}</span><input type="range" min="0" max="50" value={weights[key]} onChange={(e) => setWeights({ ...weights, [key]: Number(e.target.value) })} /><output>{weights[key]}%</output></label>)}</div><div className="settings-actions"><strong className={Object.values(weights).reduce((a, b) => a + b, 0) === 100 ? "up" : "down"}>Total: {Object.values(weights).reduce((a, b) => a + b, 0)}%</strong><button className="primary-button" onClick={saveWeights}>Guardar pesos</button></div></Card><div className="two-column"><Card><p className="eyebrow">Firebase</p><h2>{firebaseConfigured ? "Conexion configurada" : "Configuracion pendiente"}</h2><p className="muted">{user ? `Sesion activa para ${user.email}. Tus datos usan una ruta exclusiva asociada a tu UID.` : "Estas explorando la demo. Inicia sesion para sincronizar datos."}</p><Badge tone={user ? "positive" : "neutral"}>{user ? "Sincronizacion activa" : "Solo este dispositivo"}</Badge></Card><Card><p className="eyebrow">Datos de mercado</p><h2>{market.mode === "live" ? "Pipeline ejecutado" : "Muestra incluida"}</h2><p className="muted">{market.mode === "live" ? `Ultima generacion: ${market.generatedAt}` : "Ejecuta el workflow Actualizar datos de mercado en GitHub Actions para reemplazar la muestra por datos reales."}</p><Badge tone={dataTone}>{dataLabel}</Badge></Card></div><Card><p className="eyebrow">Limites honestos</p><h2>Lo que este sistema no hace</h2><ul className="limits"><li>No ejecuta operaciones ni garantiza rentabilidad.</li><li>No intenta adivinar un precio futuro exacto.</li><li>La grafica y las noticias dinamicas no recalculan automaticamente el score.</li><li>Las cotizaciones de widgets gratuitos pueden tener retraso.</li><li>No sustituye la verificacion de estados financieros o fuentes primarias.</li><li>No debe exponer claves privadas, tokens de brokers ni cuentas bancarias.</li></ul></Card></div>
        )}
      </main>
    </div>
  );
}

function EmptyState({ title, text }: { title: string; text: string }) {
  return <div className="empty-state"><div>+</div><strong>{title}</strong><p>{text}</p></div>;
}
