import { useMemo } from "react";
import type { Position, RiskDataset } from "@/lib/types";

type Props = {
  positions: Position[];
  prices: Record<string, number>;
  risk: RiskDataset;
};

const percent = (value: number, digits = 1) => `${value >= 0 ? "+" : ""}${(value * 100).toFixed(digits)}%`;

function percentile(values: number[], p: number) {
  if (!values.length) return 0;
  const ordered = [...values].sort((a, b) => a - b);
  const index = Math.min(ordered.length - 1, Math.max(0, Math.floor((ordered.length - 1) * p)));
  return ordered[index];
}

function maxDrawdown(returns: number[]) {
  let equity = 1;
  let peak = 1;
  let worst = 0;
  for (const value of returns) {
    equity *= 1 + value;
    peak = Math.max(peak, equity);
    worst = Math.min(worst, equity / peak - 1);
  }
  return worst;
}

function standardDeviation(values: number[]) {
  if (values.length < 2) return 0;
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
  return Math.sqrt(values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / (values.length - 1));
}

export default function PortfolioRiskLab({ positions, prices, risk }: Props) {
  const analysis = useMemo(() => {
    const grouped = new Map<string, number>();
    positions.forEach((position) => grouped.set(position.ticker, (grouped.get(position.ticker) ?? 0) + position.shares * (prices[position.ticker] ?? position.averageCost)));
    const available = [...grouped.entries()].filter(([ticker]) => risk.dailyReturns[ticker]?.length);
    const total = available.reduce((sum, [, value]) => sum + value, 0);
    if (!total || !available.length) return null;
    const weights = Object.fromEntries(available.map(([ticker, value]) => [ticker, value / total]));
    const length = Math.min(...available.map(([ticker]) => risk.dailyReturns[ticker].length));
    const returns = Array.from({ length }, (_, index) => available.reduce((sum, [ticker]) => {
      const series = risk.dailyReturns[ticker];
      return sum + series[series.length - length + index] * weights[ticker];
    }, 0));
    const var95 = percentile(returns, 0.05);
    const tail = returns.filter((value) => value <= var95);
    const cvar95 = tail.length ? tail.reduce((sum, value) => sum + value, 0) / tail.length : var95;
    const beta = available.reduce((sum, [ticker]) => sum + (risk.beta[ticker] ?? 1) * weights[ticker], 0);
    const volatility = standardDeviation(returns) * Math.sqrt(252);
    const drawdown = maxDrawdown(returns);
    const concentration = Math.max(...Object.values(weights));
    const largest = Object.entries(weights).sort((a, b) => b[1] - a[1])[0];
    const scenarios = risk.stressScenarios.map((scenario) => {
      const loss = scenario.id === "single-30" ? -0.30 * largest[1] : available.reduce((sum, [ticker]) => sum + (scenario.shocks[ticker] ?? 0) * weights[ticker], 0);
      return { ...scenario, loss };
    });
    return { weights, returns, var95, cvar95, beta, volatility, drawdown, concentration, largest, scenarios };
  }, [positions, prices, risk]);

  if (!analysis) return <section className="research-panel portfolio-risk-empty"><p className="eyebrow">Riesgo cuantitativo</p><h2>Agrega posiciones para calcular el riesgo conjunto</h2><p>El análisis utiliza retornos históricos publicados por el pipeline. No envía tus posiciones privadas fuera del navegador.</p></section>;

  const tickers = Object.keys(analysis.weights);
  return (
    <div className="portfolio-risk-lab">
      <section className="research-panel">
        <div className="research-heading"><div><p className="eyebrow">Riesgo cuantitativo</p><h2>Diagnóstico conjunto de la cartera</h2></div><span className={`research-status ${risk.mode === "live" ? "is-live" : "is-sample"}`}>{risk.mode === "live" ? `${risk.windowSessions} sesiones` : "Muestra estructural"}</span></div>
        <div className="risk-kpis">
          <article><span>VaR histórico 95%</span><strong className="down">{percent(analysis.var95)}</strong><small>Pérdida diaria superada aproximadamente 5% de las sesiones.</small></article>
          <article><span>CVaR 95%</span><strong className="down">{percent(analysis.cvar95)}</strong><small>Pérdida promedio dentro de la cola más adversa.</small></article>
          <article><span>Volatilidad anual</span><strong>{percent(analysis.volatility)}</strong><small>Desviación estándar anualizada de retornos diarios.</small></article>
          <article><span>Beta vs. SPY</span><strong>{analysis.beta.toFixed(2)}</strong><small>Sensibilidad histórica aproximada al mercado.</small></article>
          <article><span>Drawdown observado</span><strong className="down">{percent(analysis.drawdown)}</strong><small>Mayor caída pico–valle dentro de la ventana.</small></article>
          <article><span>Mayor concentración</span><strong>{percent(analysis.concentration)}</strong><small>{analysis.largest[0]} es la posición con mayor peso.</small></article>
        </div>
      </section>

      <div className="research-two-column">
        <section className="research-panel">
          <p className="eyebrow">Concentración</p><h2>Peso y contribución aproximada</h2>
          <div className="weight-risk-list">{Object.entries(analysis.weights).sort((a, b) => b[1] - a[1]).map(([ticker, weight]) => <article key={ticker}><strong>{ticker}</strong><div><i style={{ width: `${weight * 100}%` }} /></div><span>{percent(weight)}</span><small>β {(risk.beta[ticker] ?? 1).toFixed(2)}</small></article>)}</div>
        </section>
        <section className="research-panel">
          <p className="eyebrow">Pruebas de estrés</p><h2>Sensibilidad, no predicción</h2>
          <div className="stress-list">{analysis.scenarios.map((scenario) => <article key={scenario.id}><div><strong>{scenario.label}</strong><small>{scenario.description}</small></div><b className={scenario.loss < 0 ? "down" : "up"}>{percent(scenario.loss)}</b></article>)}</div>
        </section>
      </div>

      <section className="research-panel correlation-panel">
        <p className="eyebrow">Dependencia entre posiciones</p><h2>Matriz de correlaciones</h2>
        <div className="correlation-table" style={{ "--risk-columns": tickers.length } as React.CSSProperties}>
          <span />{tickers.map((ticker) => <strong key={`head-${ticker}`}>{ticker}</strong>)}
          {tickers.flatMap((row) => [<strong key={`row-${row}`}>{row}</strong>, ...tickers.map((column) => {
            const value = risk.correlation[row]?.[column] ?? (row === column ? 1 : 0);
            return <span key={`${row}-${column}`} style={{ background: `rgba(${value >= 0 ? "112,230,177" : "243,130,130"},${0.06 + Math.abs(value) * 0.32})` }}>{value.toFixed(2)}</span>;
          })])}
        </div>
      </section>
      <p className="research-note">VaR, CVaR y estrés describen el historial o un escenario definido. No establecen la pérdida máxima posible ni garantizan el comportamiento futuro.</p>
    </div>
  );
}
