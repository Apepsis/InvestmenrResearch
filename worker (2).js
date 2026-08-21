const DEFAULT_ALLOWED_SYMBOLS = [
  "UBER",
  "AAPL",
  "MSFT",
  "NVDA",
  "AMZN",
  "GOOGL",
  "META",
  "TSLA",
  "JPM",
  "BAC",
  "GS",
  "JNJ",
  "UNH",
  "LLY",
  "PFE",
  "XOM",
  "CVX",
  "WMT",
  "COST",
  "HD",
  "MCD",
  "NKE",
  "CAT",
  "GE",
  "UPS",
  "AMD",
  "INTC",
  "ORCL",
  "CRM",
  "ADBE",
  "DIS",
  "NFLX",
  "SPY",
];

const DEFAULT_ALLOWED_ORIGINS = [
  "https://apepsis.github.io",
  "http://localhost:5173",
];

let memoryCache = {
  key: "",
  expiresAt: 0,
  payload: null,
};

function listFromEnv(value, fallback) {
  const values = String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  return values.length ? values : fallback;
}

function getAllowedOrigin(request, env) {
  const origin = request.headers.get("Origin");
  if (!origin) return "*";
  const allowedOrigins = listFromEnv(env.ALLOWED_ORIGINS, DEFAULT_ALLOWED_ORIGINS)
    .map((value) => {
      try {
        return new URL(value).origin;
      } catch {
        return value.replace(/\/+$/, "");
      }
    });
  return allowedOrigins.includes(origin) ? origin : null;
}

function corsHeaders(origin) {
  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
    "Content-Type": "application/json; charset=utf-8",
    "X-Content-Type-Options": "nosniff",
    "X-Robots-Tag": "noindex, nofollow",
    Vary: "Origin",
  };
}

function json(payload, status, origin, extraHeaders = {}) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { ...corsHeaders(origin), ...extraHeaders },
  });
}

function requestedSymbols(url, env) {
  const allowedSymbols = new Set(
    [...DEFAULT_ALLOWED_SYMBOLS, ...listFromEnv(env.ALLOWED_SYMBOLS, [])].map((symbol) => symbol.toUpperCase()),
  );
  const requested = String(url.searchParams.get("symbols") || "")
    .split(",")
    .map((symbol) => symbol.trim().toUpperCase())
    .filter((symbol) => /^[A-Z.]{1,10}$/.test(symbol) && allowedSymbols.has(symbol));
  return [...new Set(requested)].slice(0, 50);
}

async function getLatestQuotes(symbols, env) {
  const cacheKey = symbols.slice().sort().join(",");
  const now = Date.now();
  if (memoryCache.key === cacheKey && memoryCache.expiresAt > now && memoryCache.payload) {
    return memoryCache.payload;
  }

  const upstreamUrl = new URL("https://data.alpaca.markets/v2/stocks/trades/latest");
  upstreamUrl.searchParams.set("symbols", symbols.join(","));
  upstreamUrl.searchParams.set("feed", "iex");

  const response = await fetch(upstreamUrl, {
    headers: {
      "APCA-API-KEY-ID": env.ALPACA_API_KEY_ID,
      "APCA-API-SECRET-KEY": env.ALPACA_API_SECRET_KEY,
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Alpaca respondio con estado ${response.status}`);
  }

  const source = await response.json();
  const trades = source.trades || source;
  const quotes = {};

  for (const symbol of symbols) {
    const trade = trades[symbol];
    const price = Number(trade?.p);
    if (!Number.isFinite(price) || price <= 0) continue;
    quotes[symbol] = {
      ticker: symbol,
      price,
      asOf: trade?.t || new Date().toISOString(),
      source: "Alpaca IEX",
    };
  }

  const payload = {
    generatedAt: new Date().toISOString(),
    feed: "iex",
    quotes,
  };

  memoryCache = {
    key: cacheKey,
    expiresAt: now + 45_000,
    payload,
  };
  return payload;
}

export default {
  async fetch(request, env) {
    const origin = getAllowedOrigin(request, env);
    if (!origin) {
      return json({ error: "Origen no autorizado" }, 403, "null");
    }

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(origin) });
    }

    if (request.method !== "GET") {
      return json({ error: "Metodo no permitido" }, 405, origin);
    }

    const url = new URL(request.url);
    if (url.pathname === "/health") {
      return json(
        {
          ok: true,
          service: "investment-market-api",
          status: "healthy",
          alpacaConfigured: Boolean(env.ALPACA_API_KEY_ID && env.ALPACA_API_SECRET_KEY),
          allowedSymbolCount: new Set([...DEFAULT_ALLOWED_SYMBOLS, ...listFromEnv(env.ALLOWED_SYMBOLS, [])]).size,
          generatedAt: new Date().toISOString(),
        },
        200,
        origin,
        { "Cache-Control": "no-store" },
      );
    }

    if (url.pathname !== "/quotes") {
      return json({ error: "Ruta no encontrada" }, 404, origin);
    }

    if (!env.ALPACA_API_KEY_ID || !env.ALPACA_API_SECRET_KEY) {
      return json({ error: "El Worker todavia no tiene configuradas las claves de Alpaca" }, 503, origin);
    }

    const symbols = requestedSymbols(url, env);
    if (!symbols.length) {
      return json({ error: "No se recibieron simbolos permitidos" }, 400, origin);
    }

    try {
      const payload = await getLatestQuotes(symbols, env);
      return json(payload, 200, origin, { "Cache-Control": "public, max-age=45" });
    } catch (error) {
      console.error("No se pudieron obtener las cotizaciones", error);
      return json({ error: "No se pudieron obtener las cotizaciones en este momento" }, 502, origin, {
        "Cache-Control": "no-store",
      });
    }
  },
};
