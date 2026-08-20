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
import ConstructionLab from "@/app/components/ConstructionLab";
import MethodologyLab from "@/app/components/MethodologyLab";
import PortfolioRiskLab from "@/app/components/PortfolioRiskLab";
import ResearchLab from "@/app/components/ResearchLab";
import { demoBacktest, demoBuildJournal, demoEventStudy, demoManifest, demoRisk } from "@/data/researchDemo";
import { firebaseConfigured, getFirebaseServices } from "@/lib/firebase";
import type {
  JournalEntry,
  BacktestDataset,
  BuildJournal,
  EventStudyDataset,
  LiveQuoteDataset,
  MarketDataset,
  Position,
  ResearchManifest,
  RiskDataset,
  ScoreKey,
  WatchItem,
  Weights,
} from "@/lib/types";

type View = "dashboard" | "analysis" | "research" | "portfolio" | "watchlist" | "methodology" | "construction" | "journal" | "settings";

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
  { id: "research", label: "Research Lab", glyph: "R" },
  { id: "portfolio", label: "Portafolio", glyph: "P" },
  { id: "watchlist", label: "Vigilancia", glyph: "V" },
  { id: "methodology", label: "Metodologia", glyph: "M" },
  { id: "construction", label: "Construccion", glyph: "B" },
  { id: "journal", label: "Diario", glyph: "J" },
  { id: "settings", label: "Ajustes", glyph: "C" },
];

const money = (value: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(value);

const bundledMarketApiUrl = String(import.meta.env.VITE_MARKET_API_URL || "").replace(/\/+$/, "");
const normalizeMarketApiUrl = (value: string) => value.trim().replace(/\/+$/, "");
const quoteTime = (value: string) => {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString("es-PE");
};

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
  const [backtest, setBacktest] = useState<BacktestDataset>(demoBacktest);
  const [eventStudies, setEventStudies] = useState<EventStudyDataset>(demoEventStudy);
  const [riskDataset, setRiskDataset] = useState<RiskDataset>(demoRisk);
  const [researchManifest, setResearchManifest] = useState<ResearchManifest>(demoManifest);
  const [buildJournal, setBuildJournal] = useState<BuildJournal>(demoBuildJournal);
  const [selectedTicker, setSelectedTicker] = useState("UBER");
  const [positions, setPositions] = useState<Position[]>([]);
  const [watchlist, setWatchlist] = useState<WatchItem[]>([]);
  const [journal, setJournal] = useState<JournalEntry[]>([]);
  const [weights, setWeights] = useState<Weights>(defaultWeights);
  const [marketApiUrl, setMarketApiUrl] = useState(bundledMarketApiUrl);
  const [marketApiInput, setMarketApiInput] = useState(bundledMarketApiUrl);
  const [liveQuotes, setLiveQuotes] = useState<LiveQuoteDataset["quotes"]>({});
  const [liveQuotesGeneratedAt, setLiveQuotesGeneratedAt] = useState("");
  const [liveQuoteStatus, setLiveQuoteStatus] = useState<"disabled" | "loading" | "live" | "error">(
    bundledMarketApiUrl ? "loading" : "disabled",
  );
  const [notice, setNotice] = useState("");
  const services = useMemo(() => getFirebaseServices(), []);
  const requestedMarketSymbols = useMemo(() => Object.keys(market.stocks).sort().join(","), [market.stocks]);

  useEffect(() => {
    fetch(new URL("data/market.json", document.baseURI))
      .then((response) => (response.ok ? response.json() : Promise.reject()))
      .then((data: MarketDataset) => {
        if (data?.stocks && Object.keys(data.stocks).length) setMarket(data);
      })
      .catch(() => setMarket(demoMarket));
  }, []);

  useEffect(() => {
    const resources: Array<[string, (value: never) => void]> = [
      ["data/backtest.json", (value) => setBacktest(value as BacktestDataset)],
      ["data/event_studies.json", (value) => setEventStudies(value as EventStudyDataset)],
      ["data/risk_model.json", (value) => setRiskDataset(value as RiskDataset)],
      ["data/research_manifest.json", (value) => setResearchManifest(value as ResearchManifest)],
      ["data/build_journal.json", (value) => setBuildJournal(value as BuildJournal)],
    ];
    resources.forEach(([path, setter]) => {
      fetch(new URL(path, document.baseURI))
        .then((response) => response.ok ? response.json() : Promise.reject())
        .then((value) => setter(value as never))
        .catch(() => undefined);
    });
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
    if (bundledMarketApiUrl) return;
    const savedUrl = normalizeMarketApiUrl(window.localStorage.getItem("marketApiUrl") || "");
    if (savedUrl) {
      setMarketApiUrl(savedUrl);
      setMarketApiInput(savedUrl);
    }
  }, []);

  useEffect(() => {
    if (!services || !user) return;
    const cleanups = [
      onSnapshot(collection(services.db, "users", user.uid, "portfolio"), (snap) => setPositions(snap.docs.map((item) => ({ id: item.id, ...item.data() } as Position)))),
      onSnapshot(collection(services.db, "users", user.uid, "watchlist"), (snap) => setWatchlist(snap.docs.map((item) => ({ id: item.id, ...item.data() } as WatchItem)))),
      onSnapshot(collection(services.db, "users", user.uid, "journal"), (snap) => setJournal(snap.docs.map((item) => ({ id: item.id, ...item.data() } as JournalEntry)).sort((a, b) => b.createdAt.localeCompare(a.createdAt)))),
      onSnapshot(doc(services.db, "users", user.uid, "settings", "preferences"), (snap) => {
        if (!snap.exists()) return;
        const preferences = snap.data();
        setWeights({ ...defaultWeights, ...(preferences.weights as Weights) });
        if (typeof preferences.marketApiUrl === "string") {
          const savedUrl = normalizeMarketApiUrl(preferences.marketApiUrl);
          setMarketApiUrl(savedUrl);
          setMarketApiInput(savedUrl);
          if (savedUrl) window.localStorage.setItem("marketApiUrl", savedUrl);
          else window.localStorage.removeItem("marketApiUrl");
        }
      }),
    ];
    return () => cleanups.forEach((cleanup) => cleanup());
  }, [services, user]);

  useEffect(() => {
    if (!marketApiUrl || !requestedMarketSymbols) {
      setLiveQuotes({});
      setLiveQuotesGeneratedAt("");
      setLiveQuoteStatus("disabled");
      return;
    }

    let active = true;
    setLiveQuoteStatus("loading");

    async function refreshQuotes() {
      if (document.visibilityState === "hidden") return;
      try {
        const response = await fetch(`${marketApiUrl}/quotes?symbols=${encodeURIComponent(requestedMarketSymbols)}`, {
          cache: "no-store",
        });
        if (!response.ok) throw new Error("Cotizacion no disponible");
        const dataset = (await response.json()) as LiveQuoteDataset;
        if (!active) return;
        setLiveQuotes(dataset.quotes || {});
        setLiveQuotesGeneratedAt(dataset.generatedAt || new Date().toISOString());
        setLiveQuoteStatus("live");
      } catch {
        if (active) setLiveQuoteStatus("error");
      }
    }

    void refreshQuotes();
    const timer = window.setInterval(() => void refreshQuotes(), 60_000);
    const refreshWhenVisible = () => {
      if (document.visibilityState === "visible") void refreshQuotes();
    };
    document.addEventListener("visibilitychange", refreshWhenVisible);

    return () => {
      active = false;
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
    };
  }, [marketApiUrl, requestedMarketSymbols]);

  const stock = market.stocks[selectedTicker] ?? Object.values(market.stocks)[0];
  const tickers = Object.keys(market.stocks);
  const currentQuote = liveQuotes[stock.ticker];
  const currentStockPrice = currentQuote?.price ?? stock.price;
  const currentStockChange = stock.price ? ((currentStockPrice - stock.price) / stock.price) * 100 : stock.changePct;
  const totalPortfolio = useMemo(
    () => positions.reduce((sum, position) => sum + (liveQuotes[position.ticker]?.price ?? market.stocks[position.ticker]?.price ?? position.averageCost) * position.shares, 0),
    [positions, market, liveQuotes],
  );
  const costPortfolio = positions.reduce((sum, position) => sum + position.averageCost * position.shares, 0);
  const portfolioReturn = costPortfolio ? ((totalPortfolio - costPortfolio) / costPortfolio) * 100 : 0;
  const portfolioPrices = useMemo(() => Object.fromEntries(Object.keys(market.stocks).map((ticker) => [ticker, liveQuotes[ticker]?.price ?? market.stocks[ticker]?.price ?? 0])), [market, liveQuotes]);
  const scenarioScore = (Object.keys(stock.scores) as ScoreKey[]).reduce((sum, key) => sum + stock.scores[key] * (weights[key] / 100), 0);

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
    if (services && user) await setDoc(doc(services.db, "users", user.uid, "settings", "preferences"), { weights, updatedAt: new Date().toISOString() }, { merge: true });
    flash(user ? "Escenario personal sincronizado." : "Escenario aplicado solo a esta demo.");
  }

  async function saveMarketApiUrl() {
    const nextUrl = normalizeMarketApiUrl(marketApiInput);
    if (nextUrl) {
      try {
        const parsed = new URL(nextUrl);
        if (parsed.protocol !== "https:") throw new Error("HTTPS requerido");
      } catch {
        flash("Pega una URL HTTPS valida del Worker de Cloudflare.");
        return;
      }
      window.localStorage.setItem("marketApiUrl", nextUrl);
    } else {
      window.localStorage.removeItem("marketApiUrl");
    }
    setMarketApiUrl(nextUrl);
    setMarketApiInput(nextUrl);
    if (services && user) {
      await setDoc(
        doc(services.db, "users", user.uid, "settings", "preferences"),
        { marketApiUrl: nextUrl, updatedAt: new Date().toISOString() },
        { merge: true },
      );
    }
    flash(nextUrl ? "Precio de Alpaca conectado. La aplicacion probara la conexion ahora." : "Precio por minuto desactivado.");
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
            <section className="research-proof-strip">
              <div><span>MODELO</span><strong>{researchManifest.modelVersion}</strong></div>
              <div><span>RUN ID</span><strong>{researchManifest.runId}</strong></div>
              <div><span>VALIDACIÓN</span><strong>{backtest.mode === "live" ? "Walk-forward ejecutado" : "Pendiente de primera ejecución"}</strong></div>
              <div><span>COBERTURA</span><strong>{researchManifest.dataCoverage.toFixed(1)}%</strong></div>
              <button onClick={() => setView("research")}>Auditar investigación →</button>
            </section>
            <Card className="hero-card live-market-card">
              <div className="card-heading live-card-heading">
                <div className="stock-heading">
                  <div className="ticker-logo">{stock.ticker.slice(0, 2)}</div>
                  <div><div className="title-line"><h2>{stock.name}</h2><Badge tone="neutral">{stock.ticker}</Badge></div><p>{stock.sector} · {stock.currency}</p></div>
                </div>
                <Badge tone="positive">Grafica dinamica</Badge>
              </div>
              <div className="live-price-row">
                <div>
                  <strong>{money(currentStockPrice)}</strong>
                  <span className={currentStockChange >= 0 ? "up" : "down"}>
                    {currentStockChange >= 0 ? "+" : ""}{currentStockChange.toFixed(2)}% vs. analisis diario
                  </span>
                </div>
                <div>
                  <Badge tone={liveQuoteStatus === "live" ? "positive" : liveQuoteStatus === "error" ? "negative" : "neutral"}>
                    {liveQuoteStatus === "live" ? "Alpaca · 1 min" : liveQuoteStatus === "loading" ? "Conectando Alpaca" : liveQuoteStatus === "error" ? "Ultimo precio guardado" : "Alpaca sin configurar"}
                  </Badge>
                  <small>{currentQuote ? `IEX · ${quoteTime(currentQuote.asOf)}` : `Base diaria · ${stock.asOf}`}</small>
                </div>
              </div>
              <LiveMarketChart ticker={stock.ticker} />
              <div className="analysis-data-stamp">
                <span>El portafolio usa Alpaca cuando esta disponible; el score conserva el analisis profundo diario.</span>
                <strong>{liveQuotesGeneratedAt ? `Precio: ${quoteTime(liveQuotesGeneratedAt)}` : market.mode === "live" ? `Analisis: ${market.generatedAt}` : "Modo demostracion"}</strong>
              </div>
            </Card>

            <Card className="score-card">
              <div className="card-heading"><div><p className="eyebrow">Score de investigación</p><h2>{stock.verdict}</h2></div><Badge tone={stock.score >= 60 ? "positive" : stock.score >= 40 ? "neutral" : "negative"}>{stock.confidence}% cobertura</Badge></div>
              <ScoreRing score={stock.score} />
              <div className="score-bars">{(Object.keys(stock.scores) as ScoreKey[]).map((key) => <div key={key}><span>{scoreLabels[key]}</span><div><i style={{ width: `${stock.scores[key]}%` }} /></div><strong>{Math.round(stock.scores[key])}</strong></div>)}<button className="score-audit-button" onClick={() => setView("research")}>Ver fórmula, fuentes e incertidumbre →</button></div>
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
              <div className="card-heading"><div><p className="eyebrow">Lentes metodológicos</p><h2>Reglas interpretativas documentadas</h2></div><span className="tiny-label">5 perspectivas · no son personas simuladas</span></div>
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
            <section className="analysis-intro"><div><p className="eyebrow">{stock.ticker} · Analisis integrado</p><h2>{stock.name}</h2><p>La salida combina evidencias independientes, publica incertidumbre y conserva lo que invalidaría la tesis.</p><button className="link-button" onClick={() => setView("research")}>Auditar el score completo →</button></div><ScoreRing score={stock.score} /></section>
            <Card>
              <div className="card-heading"><div><p className="eyebrow">Inteligencia propia de eventos</p><h2>Noticias clasificadas y medibles</h2></div><Badge tone={market.mode === "live" ? "positive" : "neutral"}>{stock.news.length} eventos</Badge></div>
              <p className="live-card-copy">Estos titulares sí forman parte del dataset del agente. Se publican sentimiento, tipo, relevancia, novedad y la medición posterior cuando existe una ventana suficiente.</p>
              <div className="news-list enriched-news-list">{stock.news.map((item) => <a key={item.title} href={item.url === "#" ? undefined : item.url} target="_blank" rel="noreferrer"><div><Badge tone={item.sentiment}>{item.sentiment}</Badge><span>{item.source}</span><span>{item.eventType}</span></div><strong>{item.title}</strong><small>confianza {Math.round(item.confidence * 100)}% · relevancia {Math.round((item.relevance ?? item.confidence) * 100)}% · novedad {Math.round((item.novelty ?? 0.5) * 100)}% · {item.entityMatched === false ? "entidad no confirmada" : "entidad confirmada"}</small></a>)}</div>
            </Card>
            <Card className="live-news-card">
              <div className="card-heading live-card-heading"><div><p className="eyebrow">Vigilancia externa secundaria</p><h2>Explorador de noticias de {stock.ticker}</h2></div><Badge tone="neutral">No modifica el score</Badge></div>
              <p className="live-card-copy">Este widget sirve para descubrir eventos recientes, pero su contenido no es tratado como evidencia hasta pasar por el pipeline propio.</p>
              <LiveMarketNews ticker={stock.ticker} />
            </Card>
            <div className="two-column">
              <Card><div className="card-heading"><h2>Analisis tecnico</h2><Badge tone="positive">{stock.scores.technical}/100</Badge></div><div className="indicator-list">{stock.technical.map((item) => <article key={item.label}><span className={`tone-dot ${item.tone}`} /><div><strong>{item.label}</strong><p>{item.interpretation}</p></div><b>{item.value}</b></article>)}</div></Card>
              <Card><div className="card-heading"><h2>Analisis fundamental</h2><Badge tone="positive">{stock.scores.fundamental}/100</Badge></div><div className="indicator-list">{stock.fundamental.map((item) => <article key={item.label}><span className={`tone-dot ${item.tone}`} /><div><strong>{item.label}</strong><p>{item.interpretation}</p></div><b>{item.value}</b></article>)}</div></Card>
            </div>
            <div className="two-column">
              <Card><p className="eyebrow">Auditoría del score</p><h2>Contribuciones publicadas</h2><div className="mini-contribution-list">{(stock.explanation?.contributions ?? []).map((item) => <article key={`${item.group}-${item.feature}`}><span>{item.feature}</span><strong className={item.contribution >= 0 ? "up" : "down"}>{item.contribution >= 0 ? "+" : ""}{item.contribution.toFixed(2)}</strong><small>{item.source}</small></article>)}{!stock.explanation && <p className="muted">La próxima ejecución V4 agregará las contribuciones exactas. Mientras tanto, el Research Lab reconstruye el peso de cada bloque.</p>}</div></Card>
              <Card><p className="eyebrow">Prueba de falsacion</p><h2>Que invalidaria la tesis</h2><ul className="warning-list">{stock.invalidation.map((item) => <li key={item}><span>!</span>{item}</li>)}</ul></Card>
            </div>
            <Card><div className="card-heading"><div><p className="eyebrow">Entorno economico</p><h2>Variables macro</h2></div><Badge tone={market.mode === "live" ? "positive" : "neutral"}>{market.generatedAt}</Badge></div><div className="macro-grid">{Object.values(market.macro).map((item) => <article key={item.label}><span>{item.label}</span><strong>{item.value == null ? "No disponible" : `${item.value.toFixed(2)} ${item.unit}`}</strong><small>{item.source ?? "FRED"} · {item.asOf}</small></article>)}</div></Card>
          </div>
        )}

        {view === "portfolio" && (
          <div className="management-page">
            <div className="summary-strip"><div><span>Valor actual</span><strong>{money(totalPortfolio)}</strong></div><div><span>Costo invertido</span><strong>{money(costPortfolio)}</strong></div><div><span>Resultado</span><strong className={portfolioReturn >= 0 ? "up" : "down"}>{portfolioReturn >= 0 ? "+" : ""}{portfolioReturn.toFixed(2)}%</strong></div><div><span>Posiciones</span><strong>{positions.length}</strong></div></div>
            <div className="two-column form-layout"><Card><p className="eyebrow">Nueva posicion</p><h2>Agrega una compra</h2><form className="stack-form" onSubmit={addPosition}><label>Ticker<select name="ticker" defaultValue={selectedTicker}>{tickers.map((ticker) => <option key={ticker}>{ticker}</option>)}</select></label><div className="form-row"><label>Acciones<input name="shares" type="number" min="0.0001" step="0.0001" required /></label><label>Costo promedio<input name="averageCost" type="number" min="0.01" step="0.01" required /></label></div><button className="primary-button">Guardar posicion</button></form></Card><Card><p className="eyebrow">Diagnostico de cartera</p><h2>{positions.length ? "Exposicion registrada" : "Empieza por tus posiciones reales"}</h2><p className="muted">El asistente calcula valor, retorno y concentracion usando Alpaca por minuto cuando esta conectado. No calcula impuestos ni comisiones.</p><div className="metric-callout"><span>Mayor exposicion individual</span><strong>{positions.length ? `${Math.max(...positions.map((p) => (((liveQuotes[p.ticker]?.price ?? market.stocks[p.ticker]?.price ?? p.averageCost) * p.shares) / Math.max(totalPortfolio, 1)) * 100)).toFixed(1)}%` : "0%"}</strong></div></Card></div>
            <Card><div className="card-heading"><h2>Posiciones</h2><span className="tiny-label">Precio Alpaca cuando esta disponible</span></div>{positions.length ? <div className="data-table"><div className="table-head"><span>Activo</span><span>Cantidad</span><span>Costo</span><span>Actual</span><span>Resultado</span><span /></div>{positions.map((position) => { const current = liveQuotes[position.ticker]?.price ?? market.stocks[position.ticker]?.price ?? position.averageCost; const result = ((current - position.averageCost) / position.averageCost) * 100; return <div key={position.id}><strong>{position.ticker}</strong><span>{position.shares}</span><span>{money(position.averageCost)}</span><span>{money(current)}</span><span className={result >= 0 ? "up" : "down"}>{result >= 0 ? "+" : ""}{result.toFixed(1)}%</span><button onClick={() => removeItem("portfolio", position.id)} aria-label={`Eliminar ${position.ticker}`}>×</button></div>; })}</div> : <EmptyState title="Aun no hay posiciones" text="Agrega tu primera compra para evaluar concentracion y resultado." />}</Card>
            <PortfolioRiskLab positions={positions} prices={portfolioPrices} risk={riskDataset} />
          </div>
        )}

        {view === "research" && <ResearchLab stock={stock} backtest={backtest} events={eventStudies} manifest={researchManifest} />}

        {view === "methodology" && <MethodologyLab market={market} stock={stock} manifest={researchManifest} />}

        {view === "construction" && <ConstructionLab journal={buildJournal} manifest={researchManifest} />}

        {view === "watchlist" && (
          <div className="management-page"><div className="two-column form-layout"><Card><p className="eyebrow">Lista de vigilancia</p><h2>Define que estas esperando</h2><form className="stack-form" onSubmit={addWatch}><div className="form-row"><label>Ticker<select name="ticker" defaultValue={selectedTicker}>{tickers.map((ticker) => <option key={ticker}>{ticker}</option>)}</select></label><label>Precio objetivo<input name="targetPrice" type="number" min="0" step="0.01" placeholder="Opcional" /></label></div><label>Condicion o nota<textarea name="note" placeholder="Ej.: esperar confirmacion de margen y entrada por debajo de..." /></label><button className="primary-button">Agregar a vigilancia</button></form></Card><Card><p className="eyebrow">Disciplina</p><h2>Una lista no es una recomendacion</h2><p className="muted">Registra por adelantado el precio, evento o cambio fundamental que justificaria revisar la tesis. Esto reduce decisiones por impulso.</p></Card></div><Card><div className="card-heading"><h2>Activos vigilados</h2><Badge tone="neutral">{watchlist.length}</Badge></div>{watchlist.length ? <div className="watch-grid">{watchlist.map((item) => { const current = liveQuotes[item.ticker]?.price ?? market.stocks[item.ticker]?.price; return <article key={item.id}><div><span className="ticker-logo small">{item.ticker.slice(0, 2)}</span><div><strong>{item.ticker}</strong><small>{market.stocks[item.ticker]?.name ?? "Sin datos de mercado"}</small></div><button onClick={() => removeItem("watchlist", item.id)}>×</button></div><p>{item.note || "Sin condicion registrada."}</p><div><span>Actual <b>{current ? money(current) : "N/D"}</b></span><span>Objetivo <b>{item.targetPrice ? money(item.targetPrice) : "N/D"}</b></span></div></article>; })}</div> : <EmptyState title="Tu lista esta vacia" text="Agrega activos y la condicion que debe cumplirse antes de actuar." />}</Card></div>
        )}

        {view === "journal" && (
          <div className="management-page"><div className="two-column form-layout"><Card><p className="eyebrow">Nueva decision</p><h2>Registra tu razonamiento</h2><form className="stack-form" onSubmit={addJournal}><div className="form-row"><label>Ticker<select name="ticker" defaultValue={selectedTicker}>{tickers.map((ticker) => <option key={ticker}>{ticker}</option>)}</select></label><label>Decision<select name="decision"><option>Esperar</option><option>Comprar por tramos</option><option>Mantener</option><option>Evitar</option></select></label></div><label>Confianza: <output id="confidenceOutput">60%</output><input name="confidence" type="range" min="0" max="100" defaultValue="60" onInput={(e) => { const out = document.getElementById("confidenceOutput"); if (out) out.textContent = `${e.currentTarget.value}%`; }} /></label><label>Tesis<textarea name="thesis" required placeholder="Que evidencias sostienen tu decision?" /></label><label>Invalidacion<textarea name="invalidation" placeholder="Que hecho demostraria que estabas equivocado?" /></label><button className="primary-button">Guardar en el diario</button></form></Card><Card><p className="eyebrow">Revision futura</p><h2>Separa proceso de resultado</h2><p className="muted">Una buena decision puede tener un mal resultado y viceversa. El diario conserva lo que sabias al momento de decidir.</p><div className="metric-callout"><span>Entradas registradas</span><strong>{journal.length}</strong></div></Card></div><div className="journal-list">{journal.length ? journal.map((entry) => <Card key={entry.id}><div className="journal-top"><div><Badge tone="neutral">{entry.ticker}</Badge><h2>{entry.decision}</h2></div><button onClick={() => removeItem("journal", entry.id)}>×</button></div><div className="confidence-bar"><i style={{ width: `${entry.confidence}%` }} /><span>{entry.confidence}% confianza</span></div><p>{entry.thesis}</p>{entry.invalidation && <div className="invalidation"><strong>Invalidacion</strong><span>{entry.invalidation}</span></div>}<small>{new Date(entry.createdAt).toLocaleString("es-PE")}</small></Card>) : <Card><EmptyState title="No hay decisiones registradas" text="Documenta una tesis antes de comprar, vender o esperar." /></Card>}</div></div>
        )}

        {view === "settings" && (
          <div className="settings-page">
            <Card>
              <p className="eyebrow">Simulador personal · no altera el modelo auditado</p>
              <h2>Prueba otros pesos sin reescribir el experimento</h2>
              <p className="muted">Los cinco pesos deben sumar 100%. El resultado oficial conserva los pesos versionados y validados por el pipeline; este control calcula solamente un escenario privado.</p>
              <div className="weight-list">{(Object.keys(weights) as ScoreKey[]).map((key) => <label key={key}><span>{scoreLabels[key]}</span><input type="range" min="0" max="50" value={weights[key]} onChange={(e) => setWeights({ ...weights, [key]: Number(e.target.value) })} /><output>{weights[key]}%</output></label>)}</div>
              <div className="scenario-result"><span>Score oficial <strong>{stock.score.toFixed(1)}</strong></span><span>Escenario personal <strong>{scenarioScore.toFixed(1)}</strong></span></div>
              <div className="settings-actions"><strong className={Object.values(weights).reduce((a, b) => a + b, 0) === 100 ? "up" : "down"}>Total: {Object.values(weights).reduce((a, b) => a + b, 0)}%</strong><button className="primary-button" onClick={saveWeights}>Guardar escenario</button></div>
            </Card>

            <div className="two-column">
              <Card>
                <p className="eyebrow">Firebase</p>
                <h2>{firebaseConfigured ? "Conexion configurada" : "Configuracion pendiente"}</h2>
                <p className="muted">{user ? `Sesion activa para ${user.email}. Tus datos usan una ruta exclusiva asociada a tu UID.` : "Estas explorando la demo. Inicia sesion para sincronizar datos."}</p>
                <Badge tone={user ? "positive" : "neutral"}>{user ? "Sincronizacion activa" : "Solo este dispositivo"}</Badge>
              </Card>

              <Card>
                <p className="eyebrow">Precio interno · Alpaca</p>
                <h2>{liveQuoteStatus === "live" ? "Actualizacion cada minuto" : liveQuoteStatus === "loading" ? "Probando conexion" : liveQuoteStatus === "error" ? "Conexion no disponible" : "Falta conectar el Worker"}</h2>
                <p className="muted">Pega solamente la URL publica de tu Worker de Cloudflare. Las claves de Alpaca permanecen guardadas como secretos dentro del Worker.</p>
                <div className="market-api-form">
                  <label>URL del Worker<input type="url" value={marketApiInput} onChange={(event) => setMarketApiInput(event.target.value)} placeholder="https://investment-market-api.tu-cuenta.workers.dev" /></label>
                  <button className="primary-button" type="button" onClick={saveMarketApiUrl}>Guardar y probar</button>
                </div>
                <div className="market-api-status">
                  <Badge tone={liveQuoteStatus === "live" ? "positive" : liveQuoteStatus === "error" ? "negative" : "neutral"}>{liveQuoteStatus === "live" ? "Alpaca IEX activo" : liveQuoteStatus === "loading" ? "Conectando" : liveQuoteStatus === "error" ? "Revisar Worker" : "Desactivado"}</Badge>
                  <small>{liveQuotesGeneratedAt ? `Ultima consulta: ${quoteTime(liveQuotesGeneratedAt)}` : "El precio diario sigue disponible como respaldo."}</small>
                </div>
              </Card>
            </div>

            <div className="two-column">
              <Card><p className="eyebrow">Analisis profundo diario</p><h2>{market.mode === "live" ? "Pipeline ejecutado" : "Muestra incluida"}</h2><p className="muted">{market.mode === "live" ? `Ultima generacion: ${market.generatedAt}` : "Ejecuta el workflow Actualizar datos e investigacion en GitHub Actions para reemplazar la muestra por datos reales."}</p><Badge tone={dataTone}>{dataLabel}</Badge></Card>
              <Card><p className="eyebrow">Uso del precio</p><h2>Panel, vigilancia y portafolio</h2><p className="muted">Cuando Alpaca responde, esas tres areas usan la cotizacion reciente. Si falla, la aplicacion vuelve al ultimo precio del analisis diario.</p><Badge tone={liveQuoteStatus === "live" ? "positive" : "neutral"}>{liveQuoteStatus === "live" ? "Precio reciente en uso" : "Respaldo diario en uso"}</Badge></Card>
            </div>

            <Card><p className="eyebrow">Limites honestos</p><h2>Lo que este sistema no hace</h2><ul className="limits"><li>No ejecuta operaciones ni garantiza rentabilidad.</li><li>No intenta adivinar un precio futuro exacto.</li><li>El precio por minuto no recalcula automaticamente fundamentales, noticias ni score.</li><li>El backtest no convierte una correlación histórica en causalidad.</li><li>Alpaca Basic usa el feed IEX, que puede diferir de una cotizacion consolidada de todo el mercado.</li><li>La actualizacion por minuto funciona mientras la pagina esta abierta; al volver a la pestana consulta de inmediato.</li><li>No sustituye la verificacion de estados financieros o fuentes primarias.</li><li>Nunca pegues claves privadas de Alpaca dentro de GitHub ni en esta aplicacion.</li></ul></Card>
          </div>
        )}
      </main>
    </div>
  );
}

function EmptyState({ title, text }: { title: string; text: string }) {
  return <div className="empty-state"><div>+</div><strong>{title}</strong><p>{text}</p></div>;
}
