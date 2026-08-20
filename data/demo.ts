import type { MarketDataset, StockAnalysis } from "@/lib/types";

const base = (
  ticker: string,
  name: string,
  sector: string,
  price: number,
  changePct: number,
  score: number,
  scores: StockAnalysis["scores"],
  history: number[],
): StockAnalysis => ({
  ticker,
  name,
  sector,
  currency: "USD",
  price,
  changePct,
  asOf: "Muestra ilustrativa; no es una cotización actual",
  score,
  verdict: score >= 80 ? "Oportunidad interesante" : score >= 60 ? "Analizar entrada" : score >= 40 ? "Mantener vigilancia" : "Evitar",
  source: "sample",
  confidence: 68,
  scores,
  history,
  technical: [
    { label: "Tendencia", value: "Sobre SMA 200", interpretation: "La estructura de largo plazo conserva sesgo alcista.", tone: "positive" },
    { label: "RSI 14", value: "57.4", interpretation: "Momentum positivo sin sobrecompra extrema.", tone: "positive" },
    { label: "MACD", value: "Neutral", interpretation: "La aceleracion reciente aun no confirma una nueva etapa.", tone: "neutral" },
    { label: "Drawdown", value: "-18.6%", interpretation: "La caida historica exige dimensionar la posicion.", tone: "negative" },
  ],
  fundamental: [
    { label: "Ingresos", value: "+14.1%", interpretation: "Crecimiento interanual positivo.", tone: "positive" },
    { label: "Margen operativo", value: "11.8%", interpretation: "La rentabilidad operativa mejora, pero debe sostenerse.", tone: "positive" },
    { label: "Flujo de caja libre", value: "Positivo", interpretation: "La operacion genera caja despues de inversiones.", tone: "positive" },
    { label: "Valoracion", value: "Exigente", interpretation: "Parte del crecimiento esperado ya parece incorporado.", tone: "neutral" },
  ],
  thesis: [
    "La empresa mantiene crecimiento operativo y mejora la generacion de caja.",
    "La tendencia de largo plazo es favorable, aunque la entrada debe considerar volatilidad.",
    "El score combina cinco bloques independientes; ninguna señal aislada decide la tesis.",
  ],
  risks: [
    "Una desaceleracion economica podria reducir demanda y comprimir margenes.",
    "La valoracion deja menos margen de seguridad si las expectativas no se cumplen.",
    "Riesgo regulatorio y competencia pueden alterar el escenario base.",
  ],
  invalidation: [
    "Dos trimestres consecutivos con deterioro material de ingresos y margen.",
    "Ruptura sostenida de la tendencia de largo plazo con volumen elevado.",
    "Cambio regulatorio estructural que afecte la economia de la unidad.",
  ],
  committee: [
    { agent: "Calidad", focus: "Regla fundamental", view: "Negocio mejorando; vigilar ventaja competitiva.", tone: "positive" },
    { agent: "Valoración", focus: "Múltiplos", view: "Precio sin amplio margen de seguridad.", tone: "neutral" },
    { agent: "Crecimiento", focus: "Ingresos y caja", view: "Crecimiento entendible y aún verificable.", tone: "positive" },
    { agent: "Mercado", focus: "Modelo estadístico", view: "Momentum favorable, confirmación incompleta.", tone: "neutral" },
    { agent: "Riesgo", focus: "Volatilidad", view: "Entrada gradual; limitar concentración sectorial.", tone: "negative" },
  ],
  news: [
    { title: "Ejemplo: el pipeline reemplazara esta noticia por una fuente real", source: "Modo demostracion", url: "#", publishedAt: "Sin fecha real", sentiment: "neutral", eventType: "demostracion", duration: "temporary", confidence: 0 },
  ],
  trace: {
    prices: "Muestra local claramente identificada",
    fundamentals: "Muestra local claramente identificada",
    news: "Muestra local claramente identificada",
    macro: "Sin datos macro inventados",
    method: "Deterministic weighted score v2",
  },
});

export const demoMarket: MarketDataset = {
  generatedAt: "Modo demostracion",
  mode: "sample",
  macro: {
    fedRate: { label: "Tasa FED", value: null, unit: "%", asOf: "Sin dato real en modo demostración", source: "FRED:FEDFUNDS" },
    inflation: { label: "Inflación EE. UU.", value: null, unit: "%", asOf: "Sin dato real en modo demostración", source: "FRED:CPIAUCSL" },
    unemployment: { label: "Desempleo EE. UU.", value: null, unit: "%", asOf: "Sin dato real en modo demostración", source: "FRED:UNRATE" },
    dollar: { label: "Índice dólar", value: null, unit: "índice", asOf: "Sin dato real en modo demostración", source: "FRED:DTWEXBGS" },
    oil: { label: "Petróleo WTI", value: null, unit: "USD", asOf: "Sin dato real en modo demostración", source: "FRED:DCOILWTICO" },
  },
  stocks: {
    UBER: base("UBER", "Uber Technologies", "Movilidad", 91.84, 1.26, 72, { technical: 76, fundamental: 74, news: 67, macro: 61, risk: 63 }, [58,61,60,64,67,66,71,73,70,74,78,80,77,82,85,84,88,91]),
    AAPL: base("AAPL", "Apple", "Tecnologia", 228.51, -0.42, 66, { technical: 63, fundamental: 78, news: 61, macro: 58, risk: 65 }, [73,75,78,76,80,83,81,85,84,88,90,87,91,89,92,94,93,95]),
    MSFT: base("MSFT", "Microsoft", "Tecnologia", 516.32, 0.64, 79, { technical: 81, fundamental: 88, news: 74, macro: 62, risk: 66 }, [62,65,67,69,68,72,76,75,79,82,80,84,86,89,88,92,95,97]),
    NVDA: base("NVDA", "NVIDIA", "Semiconductores", 181.11, 2.14, 75, { technical: 84, fundamental: 82, news: 76, macro: 64, risk: 49 }, [42,47,45,54,59,57,66,71,68,76,83,80,88,92,87,94,90,98]),
    AMZN: base("AMZN", "Amazon", "Consumo / Cloud", 229.02, 0.31, 70, { technical: 71, fundamental: 79, news: 69, macro: 60, risk: 61 }, [60,62,64,63,67,70,69,73,76,74,78,81,80,84,83,87,89,91]),
  },
};
