"use client";

import { useEffect, useMemo, useRef } from "react";

const exchangeByTicker: Record<string, string> = {
  UBER: "NYSE",
  AAPL: "NASDAQ",
  MSFT: "NASDAQ",
  NVDA: "NASDAQ",
  AMZN: "NASDAQ",
  GOOGL: "NASDAQ",
  META: "NASDAQ",
  TSLA: "NASDAQ",
  SPY: "AMEX",
};

function resolveSymbol(ticker: string) {
  const cleanTicker = ticker.trim().toUpperCase();
  return `${exchangeByTicker[cleanTicker] ?? "NASDAQ"}:${cleanTicker}`;
}

function publicSymbolUrl(ticker: string) {
  return `https://www.tradingview.com/symbols/${resolveSymbol(ticker).replace(":", "-")}/`;
}

type TradingViewEmbedProps = {
  config: Record<string, unknown>;
  scriptName: string;
  className: string;
  label: string;
};

function TradingViewEmbed({ config, scriptName, className, label }: TradingViewEmbedProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const serializedConfig = useMemo(() => JSON.stringify(config), [config]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.replaceChildren();

    const widgetTarget = document.createElement("div");
    widgetTarget.className = "tradingview-widget-container__widget";

    const script = document.createElement("script");
    script.type = "text/javascript";
    script.src = `https://s3.tradingview.com/external-embedding/${scriptName}`;
    script.async = true;
    script.textContent = serializedConfig;

    container.append(widgetTarget, script);

    return () => container.replaceChildren();
  }, [scriptName, serializedConfig]);

  return (
    <div
      ref={containerRef}
      className={`tradingview-widget-container ${className}`}
      role="region"
      aria-label={label}
    />
  );
}

export function LiveMarketChart({ ticker }: { ticker: string }) {
  const symbol = resolveSymbol(ticker);
  const config = useMemo(
    () => ({
      autosize: true,
      symbol,
      interval: "15",
      timezone: "America/Lima",
      theme: "dark",
      style: "3",
      locale: "es",
      backgroundColor: "rgba(6, 20, 16, 1)",
      gridColor: "rgba(190, 225, 212, 0.06)",
      hide_top_toolbar: false,
      hide_side_toolbar: true,
      allow_symbol_change: false,
      save_image: false,
      calendar: false,
      withdateranges: true,
      details: true,
      support_host: "https://www.tradingview.com",
    }),
    [symbol],
  );

  return (
    <div className="live-widget-wrap">
      <TradingViewEmbed
        className="live-market-widget"
        scriptName="embed-widget-advanced-chart.js"
        config={config}
        label={`Grafica dinamica de ${ticker}`}
      />
      <div className="live-widget-foot">
        <span>Fuente visual externa; las acciones de EE. UU. pueden mostrar retraso.</span>
        <a href={publicSymbolUrl(ticker)} target="_blank" rel="noreferrer">Abrir en TradingView ↗</a>
      </div>
    </div>
  );
}

export function LiveMarketNews({ ticker }: { ticker: string }) {
  const symbol = resolveSymbol(ticker);
  const config = useMemo(
    () => ({
      feedMode: "symbol",
      symbol,
      colorTheme: "dark",
      isTransparent: true,
      displayMode: "regular",
      width: "100%",
      height: "100%",
      locale: "es",
    }),
    [symbol],
  );

  return (
    <div className="live-widget-wrap">
      <TradingViewEmbed
        className="live-news-widget"
        scriptName="embed-widget-timeline.js"
        config={config}
        label={`Noticias dinamicas de ${ticker}`}
      />
      <div className="live-widget-foot">
        <span>Estas noticias no modifican el score hasta la siguiente ejecucion del analisis.</span>
        <a href={publicSymbolUrl(ticker)} target="_blank" rel="noreferrer">Ver activo ↗</a>
      </div>
    </div>
  );
}
