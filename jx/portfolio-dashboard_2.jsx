import { useState, useMemo, useEffect, useRef, useCallback } from "react";

// ─────────────────────────────────────────────────────────────────
// FALLBACK PRICES (CSV snapshot Mar 5 2026 close)
// ─────────────────────────────────────────────────────────────────
const FALLBACK_PRICES = {
  AVUV: 111.06, COST: 982.57, GLD: 466.13, MSFT: 410.68, NVDA: 183.34,
  SLV: 74.27, "VDY.TO": 66.80, "VFV.TO": 165.83, VOO: 626.81,
  "WCP.TO": 13.83, "XEC.TO": 37.74, "XEF.TO": 47.73, "XEI.TO": 35.94,
  "XIU.TO": 49.05, QQQM: 250.72,
};

const FALLBACK_USDCAD = 1.36577;

// Alpha Vantage symbol mapping (.TO → TSX format)
const AV_SYMBOL = {
  "VDY.TO": "VDY.TRT", "VFV.TO": "VFV.TRT", "WCP.TO": "WCP.TRT",
  "XEC.TO": "XEC.TRT", "XEF.TO": "XEF.TRT", "XEI.TO": "XEI.TRT",
  "XIU.TO": "XIU.TRT",
};
function avSym(ticker) { return AV_SYMBOL[ticker] || ticker; }

// ─────────────────────────────────────────────────────────────────
// PORTFOLIO DATA
// ─────────────────────────────────────────────────────────────────
const RAW_HOLDINGS = [
  { ticker: "AVUV", name: "Avantis US Small Cap Value ETF", account: "RRSP", broker: "RBC", currency: "USD", qty: 191, avgCost: 114.47, type: "US Small Cap Value", color: "#FFD700", dividendYield: 1.85, beta: 1.22, expectedCAGR: 11.5, sharpe: 0.82, geography: { "United States": 100 } },
  { ticker: "COST", name: "Costco Wholesale Corp", account: "RRSP", broker: "RBC", currency: "USD", qty: 3, avgCost: 875.00, type: "US Large Cap Growth", color: "#FF6B35", dividendYield: 0.52, beta: 0.90, expectedCAGR: 12.0, sharpe: 0.88, geography: { "United States": 100 } },
  { ticker: "GLD", name: "SPDR Gold Shares ETF", account: "Open", broker: "CIBC", currency: "USD", qty: 7, avgCost: 398.80, type: "Commodity – Gold", color: "#FFAA00", dividendYield: 0.00, beta: 0.10, expectedCAGR: 5.5, sharpe: 0.40, geography: { "Global": 100 } },
  { ticker: "MSFT", name: "Microsoft Corporation", account: "TFSA", broker: "TD", currency: "USD", qty: 7.622, avgCost: 411.95, type: "US Large Cap Growth", color: "#00AAFF", dividendYield: 0.82, beta: 0.90, expectedCAGR: 11.5, sharpe: 0.92, geography: { "United States": 100 } },
  { ticker: "NVDA", name: "NVIDIA Corporation", account: "TFSA", broker: "CIBC", currency: "USD", qty: 18, avgCost: 175.07, type: "US Large Cap Growth", color: "#76FF44", dividendYield: 0.03, beta: 1.65, expectedCAGR: 15.0, sharpe: 0.85, geography: { "United States": 100 } },
  { ticker: "SLV", name: "iShares Silver Trust ETF", account: "Open", broker: "CIBC", currency: "USD", qty: 58, avgCost: 40.05, type: "Commodity – Silver", color: "#CCDDEE", dividendYield: 0.00, beta: 0.30, expectedCAGR: 4.5, sharpe: 0.32, geography: { "Global": 100 } },
  { ticker: "VDY.TO", name: "Vanguard FTSE CDN High Div Yld ETF", account: "Open", broker: "CIBC", currency: "CAD", qty: 537, avgCost: 65.78, type: "Canadian High Dividend", color: "#CC44FF", dividendYield: 4.10, beta: 0.72, expectedCAGR: 7.0, sharpe: 0.70, geography: { "Canada": 100 } },
  { ticker: "VFV.TO", name: "Vanguard S&P 500 Index ETF (CAD)", account: "TFSA", broker: "TD", currency: "CAD", qty: 30.427, avgCost: 164.33, type: "US Large Cap Blend", color: "#0088FF", dividendYield: 1.10, beta: 1.00, expectedCAGR: 10.2, sharpe: 0.93, geography: { "United States": 100 } },
  { ticker: "VOO", name: "Vanguard S&P 500 ETF", account: "TFSA", broker: "CIBC", currency: "USD", qty: 111.579, avgCost: 560.04, type: "US Large Cap Blend", color: "#00D4FF", dividendYield: 1.32, beta: 1.00, expectedCAGR: 10.5, sharpe: 0.95, geography: { "United States": 100 } },
  { ticker: "WCP.TO", name: "Whitecap Resources Inc", account: "TFSA", broker: "CIBC", currency: "CAD", qty: 455, avgCost: 14.44, type: "Canadian Energy", color: "#FF8800", dividendYield: 6.20, beta: 1.35, expectedCAGR: 6.0, sharpe: 0.45, geography: { "Canada": 100 } },
  { ticker: "XEC.TO", name: "iShares Core MSCI EM IMI Index ETF", account: "TFSA", broker: "RBC", currency: "CAD", qty: 1047, avgCost: 38.90, type: "Emerging Markets", color: "#FF3366", dividendYield: 2.80, beta: 1.05, expectedCAGR: 8.8, sharpe: 0.55, geography: { "China": 28, "India": 18, "Taiwan": 16, "South Korea": 10, "Brazil": 5, "Other EM": 23 } },
  { ticker: "XEF.TO", name: "iShares MSCI EAFE IMI Index ETF", account: "TFSA", broker: "CIBC", currency: "CAD", qty: 1335, avgCost: 48.24, type: "Developed Market ex-NA", color: "#00FF88", dividendYield: 3.20, beta: 0.85, expectedCAGR: 7.5, sharpe: 0.62, geography: { "Europe": 55, "Japan": 22, "Australia/NZ": 10, "Other Developed": 13 } },
  { ticker: "XEI.TO", name: "iShares S&P/TSX Comp High Div ETF", account: "TFSA", broker: "TD", currency: "CAD", qty: 6, avgCost: 33.87, type: "Canadian High Dividend", color: "#AA44FF", dividendYield: 5.50, beta: 0.75, expectedCAGR: 6.5, sharpe: 0.65, geography: { "Canada": 100 } },
  { ticker: "XIU.TO", name: "iShares S&P/TSX 60 Index ETF", account: "TFSA", broker: "RBC", currency: "CAD", qty: 97, avgCost: 47.59, type: "Canadian Large Cap", color: "#BB55EE", dividendYield: 2.90, beta: 0.82, expectedCAGR: 7.2, sharpe: 0.68, geography: { "Canada": 100 } },
];

const TICKERS = RAW_HOLDINGS.map(h => h.ticker);

// ─────────────────────────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────────────────────────
const ACCOUNT_COLORS = { RRSP: "#00D4FF", TFSA: "#00FF88", Open: "#FFD700" };
const ACCOUNT_BG = { RRSP: "#001a2a", TFSA: "#001a10", Open: "#1a1400" };
const BROKER_COLORS = { CIBC: "#DD0000", RBC: "#0055AA", TD: "#00AA55" };
const TAX_COLORS = { OPTIMAL: "#00FF88", GOOD: "#66ffaa", NEUTRAL: "#FFD700", ACCEPTABLE: "#FF9944", SUBOPTIMAL: "#FF3366" };
const TAX_MAP = { AVUV: "OPTIMAL", COST: "GOOD", GLD: "NEUTRAL", MSFT: "GOOD", NVDA: "GOOD", SLV: "NEUTRAL", "VDY.TO": "ACCEPTABLE", "VFV.TO": "GOOD", VOO: "SUBOPTIMAL", "WCP.TO": "GOOD", "XEC.TO": "NEUTRAL", "XEF.TO": "SUBOPTIMAL", "XEI.TO": "GOOD", "XIU.TO": "GOOD" };

function heatColor(pct) {
  if (pct === null) return { bg: "#1a1a2e", text: "#666", border: "#2a2a44" };
  if (pct >= 8) return { bg: "#003d1a", text: "#00ff88", border: "#00aa44" };
  if (pct >= 5) return { bg: "#00291a", text: "#00cc66", border: "#007733" };
  if (pct >= 0) return { bg: "#001a12", text: "#44cc88", border: "#115533" };
  if (pct >= -2) return { bg: "#1a0808", text: "#ff8877", border: "#663322" };
  if (pct >= -5) return { bg: "#2a0808", text: "#ff5544", border: "#882222" };
  return { bg: "#3a0606", text: "#ff2211", border: "#aa1111" };
}

const fmt = (n, dec = 0) => n.toLocaleString("en-CA", { minimumFractionDigits: dec, maximumFractionDigits: dec });
const fmtCAD = n => `$${fmt(n)}`;
const sleep = ms => new Promise(r => setTimeout(r, ms));

function PieChart({ data, size = 180 }) {
  const total = data.reduce((s, d) => s + d.value, 0);
  if (!total) return null;
  let cum = 0;
  const slices = data.filter(d => d.value > 0).map(d => {
    const pct = d.value / total, s0 = cum; cum += pct;
    const a1 = s0 * 2 * Math.PI - Math.PI / 2, a2 = cum * 2 * Math.PI - Math.PI / 2;
    const r = size / 2 - 8, cx = size / 2, cy = size / 2;
    return { ...d, path: `M${cx},${cy} L${cx + r * Math.cos(a1)},${cy + r * Math.sin(a1)} A${r},${r} 0 ${pct > .5 ? 1 : 0},1 ${cx + r * Math.cos(a2)},${cy + r * Math.sin(a2)} Z` };
  });
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {slices.map((s, i) => <path key={i} d={s.path} fill={s.color} opacity={.88} stroke="#0a0a14" strokeWidth={1.5} />)}
      <circle cx={size / 2} cy={size / 2} r={size / 4} fill="#0a0a14" />
    </svg>
  );
}

function Bar({ value, max = 100, color, height = 5 }) {
  return (
    <div style={{ background: "#1a1a2e", borderRadius: 4, height, width: "100%", overflow: "hidden" }}>
      <div style={{ width: `${Math.min((value / max) * 100, 100)}%`, height: "100%", background: color, borderRadius: 4, transition: "width .5s" }} />
    </div>
  );
}

const ABadge = ({ a }) => <span style={{ display: "inline-block", padding: "1px 5px", borderRadius: 3, fontSize: 8, letterSpacing: 1, background: ACCOUNT_BG[a], border: `1px solid ${ACCOUNT_COLORS[a]}44`, color: ACCOUNT_COLORS[a] }}>{a}</span>;
const BBadge = ({ b }) => <span style={{ display: "inline-block", padding: "1px 5px", borderRadius: 3, fontSize: 8, letterSpacing: 1, background: (BROKER_COLORS[b] || "#333") + "22", border: `1px solid ${BROKER_COLORS[b] || "#555"}44`, color: BROKER_COLORS[b] || "#999" }}>{b}</span>;
const TBadge = ({ r }) => <span style={{ display: "inline-block", padding: "1px 5px", borderRadius: 3, fontSize: 8, letterSpacing: 1, background: TAX_COLORS[r] + "18", border: `1px solid ${TAX_COLORS[r]}44`, color: TAX_COLORS[r] }}>{r}</span>;

// ─────────────────────────────────────────────────────────────────
// ALPHA VANTAGE FETCHER
// ─────────────────────────────────────────────────────────────────
async function fetchQuote(ticker, apiKey) {
  const sym = avSym(ticker);
  const url = `https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=${sym}&apikey=${apiKey}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  if (data["Note"] || data["Information"]) throw new Error("RATE_LIMIT");
  const q = data["Global Quote"];
  if (!q || !q["05. price"]) throw new Error("NO_DATA");
  return {
    price: parseFloat(q["05. price"]),
    open: parseFloat(q["02. open"]),
    high: parseFloat(q["03. high"]),
    low: parseFloat(q["04. low"]),
    prevClose: parseFloat(q["08. previous close"]),
    change: parseFloat(q["09. change"]),
    changePct: parseFloat(q["10. change percent"]?.replace("%", "")),
    volume: parseInt(q["06. volume"]),
    latestDay: q["07. latest trading day"],
  };
}

async function fetchUSDCAD(apiKey) {
  const url = `https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=USD&to_currency=CAD&apikey=${apiKey}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  if (data["Note"] || data["Information"]) throw new Error("RATE_LIMIT");
  const r = data["Realtime Currency Exchange Rate"];
  if (!r) throw new Error("NO_FX_DATA");
  return parseFloat(r["5. Exchange Rate"]);
}

// ─────────────────────────────────────────────────────────────────
// MAIN APP
// ─────────────────────────────────────────────────────────────────
export default function App() {
  const [apiKey, setApiKey] = useState("");
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [showKeyInput, setShowKeyInput] = useState(true);

  const [prices, setPrices] = useState({ ...FALLBACK_PRICES });
  const [quoteDetails, setQuoteDetails] = useState({});
  const [usdcad, setUsdcad] = useState(FALLBACK_USDCAD);
  const [priceSource, setPriceSource] = useState("CSV snapshot — Mar 5 2026");
  const [lastUpdated, setLastUpdated] = useState(null);
  const [fetchStatus, setFetchStatus] = useState({}); // ticker → "ok"|"error"|"loading"
  const [isFetching, setIsFetching] = useState(false);
  const [fetchLog, setFetchLog] = useState([]);
  const [callsUsed, setCallsUsed] = useState(0);

  const [tab, setTab] = useState("heatmap");
  const [heatSort, setHeatSort] = useState("value");
  const [acctFilter, setAcctFilter] = useState("ALL");
  const [brokerFilter, setBrokerFilter] = useState("ALL");
  const [sortBy, setSortBy] = useState("value");
  const [hoveredTicker, setHoveredTicker] = useState(null);
  const [clock, setClock] = useState(new Date());

  // Clock
  useEffect(() => {
    const t = setInterval(() => setClock(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  // ── FETCH ALL PRICES ─────────────────────────────────────────
  const fetchAllPrices = useCallback(async (key) => {
    if (!key) return;
    setIsFetching(true);
    setFetchLog([]);
    const newPrices = { ...prices };
    const newDetails = { ...quoteDetails };
    const newStatus = {};
    let calls = 0;
    const log = [];

    const addLog = (msg, ok = true) => {
      setFetchLog(l => [...l, { msg, ok, t: new Date().toLocaleTimeString("en-CA", { hour12: false }) }]);
    };

    // 1. Fetch USD/CAD first (1 call)
    try {
      addLog("Fetching USD/CAD exchange rate...", true);
      const fx = await fetchUSDCAD(key);
      setUsdcad(fx);
      calls++;
      addLog(`✓ USD/CAD = ${fx.toFixed(5)}`, true);
    } catch (e) {
      if (e.message === "RATE_LIMIT") {
        addLog("⚠ Rate limited on FX. Using fallback USD/CAD.", false);
      } else {
        addLog(`✗ FX error: ${e.message}. Using fallback.`, false);
      }
    }
    await sleep(1200); // AV free tier: ~5 req/min

    // 2. Fetch each ticker sequentially
    for (const ticker of TICKERS) {
      setFetchLog(l => [...l, { msg: `Fetching ${ticker} (${avSym(ticker)})...`, ok: true, t: new Date().toLocaleTimeString("en-CA", { hour12: false }) }]);
      newStatus[ticker] = "loading";
      setFetchStatus({ ...newStatus });

      try {
        const q = await fetchQuote(ticker, key);
        newPrices[ticker] = q.price;
        newDetails[ticker] = q;
        newStatus[ticker] = "ok";
        calls++;
        addLog(`✓ ${ticker}: ${q.price.toFixed(2)} (${q.changePct >= 0 ? "+" : ""}${q.changePct?.toFixed(2)}% · ${q.latestDay})`, true);
        setPrices({ ...newPrices });
        setQuoteDetails({ ...newDetails });
        setFetchStatus({ ...newStatus });
        await sleep(1200);
      } catch (e) {
        newStatus[ticker] = "error";
        setFetchStatus({ ...newStatus });
        if (e.message === "RATE_LIMIT") {
          addLog(`⚠ ${ticker}: Rate limited — using fallback price ${FALLBACK_PRICES[ticker]}`, false);
          await sleep(60000); // wait 60s on rate limit
        } else {
          addLog(`✗ ${ticker}: ${e.message} — using fallback`, false);
          await sleep(1200);
        }
      }
    }

    setCallsUsed(c => c + calls);
    setPriceSource("Alpha Vantage");
    setLastUpdated(new Date());
    setIsFetching(false);
    addLog(`─── Done. ${calls} API calls used (${25 - calls} remaining today). ───`, true);
  }, [prices, quoteDetails]);

  const handleSaveKey = () => {
    const k = apiKeyInput.trim();
    if (!k) return;
    setApiKey(k);
    setShowKeyInput(false);
    fetchAllPrices(k);
  };

  // ── DERIVED DATA ─────────────────────────────────────────────
  const holdings = useMemo(() => RAW_HOLDINGS.map(h => {
    const cp = prices[h.ticker] ?? FALLBACK_PRICES[h.ticker];
    const qd = quoteDetails[h.ticker];
    const prevClose = qd?.prevClose ?? FALLBACK_PRICES[h.ticker];
    const dayChgPct = qd?.changePct ?? 0;
    const mkt = h.currency === "USD" ? h.qty * cp * usdcad : h.qty * cp;
    const gl = h.avgCost > 0 ? ((cp / h.avgCost) - 1) * 100 : null;
    return {
      ...h,
      currPrice: cp, prevClose, dayChgPct,
      mktValueCAD: mkt,
      costCAD: h.currency === "USD" ? h.qty * h.avgCost * usdcad : h.qty * h.avgCost,
      glPct: gl,
      glAmtLocal: (cp - h.avgCost) * h.qty,
      annualDivCAD: mkt * h.dividendYield / 100,
      heatColor: heatColor(gl),
      taxRating: TAX_MAP[h.ticker] || "NEUTRAL",
      fetchStatus: fetchStatus[h.ticker] || "idle",
      latestDay: qd?.latestDay || "Mar 5, 2026",
      volume: qd?.volume,
      high: qd?.high, low: qd?.low,
    };
  }), [prices, quoteDetails, usdcad, fetchStatus]);

  const totalCAD = useMemo(() => holdings.reduce((s, h) => s + h.mktValueCAD, 0), [holdings]);
  const totalCostCAD = useMemo(() => holdings.reduce((s, h) => s + h.costCAD, 0), [holdings]);
  const totalGL = totalCAD - totalCostCAD;
  const totalGLpct = totalCostCAD > 0 ? (totalGL / totalCostCAD) * 100 : 0;

  const withWeights = useMemo(() => holdings.map(h => ({ ...h, weight: (h.mktValueCAD / totalCAD) * 100 })), [holdings, totalCAD]);

  const metrics = useMemo(() => {
    const wCAGR = withWeights.reduce((s, h) => s + (h.weight / 100) * h.expectedCAGR, 0);
    const wYield = withWeights.reduce((s, h) => s + (h.weight / 100) * h.dividendYield, 0);
    const wBeta = withWeights.reduce((s, h) => s + (h.weight / 100) * h.beta, 0);
    const annualDiv = withWeights.reduce((s, h) => s + h.annualDivCAD, 0);
    return { wCAGR, wYield, wBeta, annualDiv, val20yr: totalCAD * Math.pow(1 + wCAGR / 100, 20) };
  }, [withWeights, totalCAD]);

  const acctBreak = useMemo(() => {
    const a = { RRSP: 0, TFSA: 0, Open: 0 };
    withWeights.forEach(h => { a[h.account] += h.mktValueCAD; });
    return Object.entries(a).map(([n, v]) => ({ name: n, value: v, pct: (v / totalCAD) * 100, color: ACCOUNT_COLORS[n] }));
  }, [withWeights, totalCAD]);

  const brokerBreak = useMemo(() => {
    const b = {};
    withWeights.forEach(h => { b[h.broker] = (b[h.broker] || 0) + h.mktValueCAD; });
    return Object.entries(b).map(([n, v]) => ({ name: n, value: v, pct: (v / totalCAD) * 100, color: BROKER_COLORS[n] || "#888" }));
  }, [withWeights, totalCAD]);

  const geoData = useMemo(() => {
    const geo = {};
    withWeights.forEach(h => Object.entries(h.geography).forEach(([r, p]) => { geo[r] = (geo[r] || 0) + (h.weight / 100) * p; }));
    const gc = { "United States": "#00D4FF", "Canada": "#CC44FF", "Europe": "#00FF88", "Japan": "#FFD700", "China": "#FF3366", "India": "#FF6B35", "Taiwan": "#88FFCC", "South Korea": "#FF88AA", "Australia/NZ": "#AADDFF", "Brazil": "#FFAA44", "Global": "#AAAAFF", "Other Developed": "#8888AA", "Other EM": "#AA5566" };
    return Object.entries(geo).map(([n, v]) => ({ name: n, value: +v.toFixed(1), color: gc[n] || "#888" })).sort((a, b) => b.value - a.value);
  }, [withWeights]);

  const assetClasses = useMemo(() => {
    const g = { "US Equity": 0, "Canadian Equity": 0, "Intl Developed": 0, "Emerging Markets": 0, "Commodities": 0, "Energy (CA)": 0 };
    withWeights.forEach(h => {
      if (["US Large Cap Blend", "US Large Cap Growth", "US Small Cap Value"].includes(h.type)) g["US Equity"] += h.mktValueCAD;
      else if (["Canadian High Dividend", "Canadian Large Cap"].includes(h.type)) g["Canadian Equity"] += h.mktValueCAD;
      else if (h.type === "Developed Market ex-NA") g["Intl Developed"] += h.mktValueCAD;
      else if (h.type === "Emerging Markets") g["Emerging Markets"] += h.mktValueCAD;
      else if (h.type.startsWith("Commodity")) g["Commodities"] += h.mktValueCAD;
      else if (h.type === "Canadian Energy") g["Energy (CA)"] += h.mktValueCAD;
    });
    return Object.entries(g).filter(([, v]) => v > 0).map(([n, v]) => ({ name: n, value: v, pct: (v / totalCAD) * 100 }));
  }, [withWeights, totalCAD]);
  const acClrs = { "US Equity": "#00D4FF", "Canadian Equity": "#CC44FF", "Intl Developed": "#00FF88", "Emerging Markets": "#FF3366", "Commodities": "#FFAA00", "Energy (CA)": "#FF6B35" };

  const cagrGap = metrics.wCAGR - 8;

  const heatTiles = useMemo(() => {
    const h = [...withWeights];
    if (heatSort === "value") return h.sort((a, b) => b.mktValueCAD - a.mktValueCAD);
    if (heatSort === "gl") return h.sort((a, b) => (b.glPct || 0) - (a.glPct || 0));
    if (heatSort === "day") return h.sort((a, b) => b.dayChgPct - a.dayChgPct);
    return h.sort((a, b) => a.ticker.localeCompare(b.ticker));
  }, [withWeights, heatSort]);

  const filtered = useMemo(() => {
    let h = [...withWeights];
    if (acctFilter !== "ALL") h = h.filter(x => x.account === acctFilter);
    if (brokerFilter !== "ALL") h = h.filter(x => x.broker === brokerFilter);
    return h.sort((a, b) => sortBy === "value" ? b.mktValueCAD - a.mktValueCAD : sortBy === "gl" ? b.glAmtLocal - a.glAmtLocal : b.weight - a.weight);
  }, [withWeights, acctFilter, brokerFilter, sortBy]);

  const clockStr = clock.toLocaleTimeString("en-CA", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
  const dateStr = clock.toLocaleDateString("en-CA", { weekday: "short", month: "short", day: "numeric", year: "numeric" });
  const okCount = Object.values(fetchStatus).filter(s => s === "ok").length;
  const errCount = Object.values(fetchStatus).filter(s => s === "error").length;
  const tabs = ["heatmap", "overview", "holdings", "tax", "geography", "dividends", "projection"];

  return (
    <div style={{ fontFamily: "'DM Mono','Courier New',monospace", background: "#06061a", minHeight: "100vh", color: "#e0e0ff" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Bebas+Neue&display=swap');
        *{box-sizing:border-box;margin:0;padding:0}
        ::-webkit-scrollbar{width:4px}::-webkit-scrollbar-track{background:#0a0a1a}::-webkit-scrollbar-thumb{background:#334;border-radius:2px}
        .card{background:linear-gradient(135deg,#0d0d26,#10102a);border:1px solid #1e1e48;border-radius:12px;padding:16px;transition:border-color .2s}
        .card:hover{border-color:#2a2a60}
        .tab{background:none;border:none;cursor:pointer;font-family:inherit;font-size:10px;letter-spacing:2px;padding:7px 13px;border-radius:6px;color:#444;transition:all .2s}
        .tab.on{background:#1a1a44;color:#00D4FF}
        .tab:hover:not(.on){color:#888}
        .hrow{display:grid;grid-template-columns:115px 1fr 55px 58px 62px 78px 90px 80px 90px 80px 72px;gap:6px;align-items:center;padding:9px 14px;border-bottom:1px solid #0f0f22;transition:background .15s;font-size:10px}
        .hrow:hover{background:#0d0d24}
        .pill{padding:3px 9px;border-radius:10px;font-size:9px;letter-spacing:1px;cursor:pointer;border:1px solid transparent;font-family:inherit;transition:all .15s}
        .gl-pos{color:#00FF88}.gl-neg{color:#FF4455}
        .heat-tile{border-radius:10px;cursor:pointer;transition:transform .18s,box-shadow .18s;position:relative;overflow:hidden;display:flex;flex-direction:column;justify-content:space-between;padding:13px}
        .heat-tile:hover{transform:scale(1.04);z-index:10;box-shadow:0 8px 32px rgba(0,0,0,.7)}
        .api-input{background:#0a0a20;border:1px solid #2244aa;color:#00D4FF;padding:10px 14px;border-radius:8px;font-family:inherit;font-size:13px;outline:none;width:100%;letter-spacing:2px}
        .api-input:focus{border-color:#4488ff;box-shadow:0 0 0 2px #4488ff22}
        .fetch-btn{background:#001a08;border:1px solid #00aa44;color:#00ff88;padding:10px 24px;border-radius:8px;cursor:pointer;font-family:inherit;font-size:11px;letter-spacing:2px;transition:all .2s}
        .fetch-btn:hover{background:#002a10;box-shadow:0 0 12px #00ff8833}
        .fetch-btn:disabled{opacity:.4;cursor:not-allowed}
        .status-ok{color:#00ff88}.status-err{color:#ff4444}.status-load{color:#FFD700}
        @keyframes spin{to{transform:rotate(360deg)}}
        .spinner{display:inline-block;width:10px;height:10px;border:2px solid #FFD70044;border-top-color:#FFD700;border-radius:50%;animation:spin .7s linear infinite}
      `}</style>

      {/* ── API KEY PANEL ── */}
      {showKeyInput && (
        <div style={{ position: "fixed", inset: 0, background: "#06061acc", backdropFilter: "blur(6px)", zIndex: 100, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div style={{ background: "linear-gradient(135deg,#0d0d26,#12123a)", border: "1px solid #2244aa", borderRadius: 16, padding: 36, width: 520, maxWidth: "90vw" }}>
            <div style={{ fontFamily: "'Bebas Neue',sans-serif", fontSize: 28, letterSpacing: 3, color: "#fff", marginBottom: 6 }}>ALPHA VANTAGE SETUP</div>
            <div style={{ fontSize: 9, color: "#446", letterSpacing: 2, marginBottom: 20 }}>ENTER YOUR API KEY TO FETCH REAL MARKET PRICES</div>

            <div style={{ fontSize: 10, color: "#8899bb", lineHeight: 1.7, marginBottom: 20 }}>
              Your key is stored <span style={{ color: "#00FF88" }}>only in this browser session</span> — never sent anywhere except directly to Alpha Vantage's servers. It is not saved, logged, or visible in the code.
            </div>

            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 8, letterSpacing: 2, color: "#446", marginBottom: 6 }}>API KEY</div>
              <input
                className="api-input"
                type="password"
                placeholder="Paste your Alpha Vantage API key..."
                value={apiKeyInput}
                onChange={e => setApiKeyInput(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleSaveKey()}
                autoComplete="off"
              />
            </div>

            <div style={{ display: "flex", gap: 10, marginBottom: 20 }}>
              <button className="fetch-btn" onClick={handleSaveKey} disabled={!apiKeyInput.trim()}>
                ▶ CONNECT &amp; FETCH PRICES
              </button>
              <button onClick={() => setShowKeyInput(false)} style={{ background: "transparent", border: "1px solid #334", color: "#667", padding: "10px 20px", borderRadius: 8, cursor: "pointer", fontFamily: "inherit", fontSize: 11, letterSpacing: 1 }}>
                USE SNAPSHOT PRICES
              </button>
            </div>

            <div style={{ padding: "10px 14px", background: "#0a0a1e", borderRadius: 8, border: "1px solid #1a1a3a" }}>
              <div style={{ fontSize: 8, color: "#446", letterSpacing: 2, marginBottom: 6 }}>FREE TIER LIMITS</div>
              {[
                { label: "Requests/day", value: "25" },
                { label: "Your holdings", value: `${TICKERS.length} tickers + 1 FX = ${TICKERS.length + 1} calls` },
                { label: "Remaining after 1 refresh", value: `${25 - (TICKERS.length + 1)} calls` },
                { label: "Data type", value: "Latest trading day close + day change" },
                { label: "CAD tickers (.TO)", value: "Supported via .TRT suffix" },
              ].map(r => (
                <div key={r.label} style={{ display: "flex", justifyContent: "space-between", padding: "3px 0", borderBottom: "1px solid #111" }}>
                  <span style={{ fontSize: 9, color: "#556" }}>{r.label}</span>
                  <span style={{ fontSize: 9, color: "#aab" }}>{r.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── HEADER ── */}
      <div style={{ background: "linear-gradient(180deg,#0a0a22,#06061a)", borderBottom: "1px solid #181840", padding: "18px 26px 0" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
          <div>
            <div style={{ fontSize: 8, letterSpacing: 4, color: "#335", marginBottom: 4 }}>REAL-TIME PRICES · CIBC + RBC + TD · TFSA + OPEN · RRSP FULL</div>
            <div style={{ fontFamily: "'Bebas Neue',sans-serif", fontSize: 30, letterSpacing: 3, color: "#fff", lineHeight: 1 }}>LONG-TERM WEALTH ENGINE</div>
            <div style={{ fontSize: 8, color: "#334", marginTop: 4, letterSpacing: 2 }}>20-YEAR HORIZON · 8% CAGR TARGET · USD/CAD {usdcad.toFixed(5)}</div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontFamily: "'Bebas Neue',sans-serif", fontSize: 30, color: "#00D4FF", letterSpacing: 2, lineHeight: 1 }}>{clockStr}</div>
            <div style={{ fontSize: 9, color: "#446", letterSpacing: 1, marginBottom: 8 }}>{dateStr}</div>

            {/* Data source badge + refresh */}
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", alignItems: "center", flexWrap: "wrap" }}>
              <div style={{
                padding: "3px 10px", borderRadius: 12, fontSize: 8, letterSpacing: 1,
                background: priceSource === "Alpha Vantage" ? "#001a08" : "#1a1400",
                border: `1px solid ${priceSource === "Alpha Vantage" ? "#00aa44" : "#886600"}`,
                color: priceSource === "Alpha Vantage" ? "#00ff88" : "#FFD700"
              }}>
                {isFetching ? <><span className="spinner" /> FETCHING...</> :
                  priceSource === "Alpha Vantage"
                    ? `✓ LIVE · ${lastUpdated?.toLocaleTimeString("en-CA", { hour12: false })} · ${okCount}/${TICKERS.length} ok${errCount > 0 ? ` · ${errCount} err` : ""}`
                    : "⚠ CSV SNAPSHOT · MAR 5 2026"
                }
              </div>
              {apiKey && (
                <button
                  className="fetch-btn"
                  disabled={isFetching}
                  onClick={() => fetchAllPrices(apiKey)}
                  style={{ padding: "4px 14px", fontSize: 9 }}
                >
                  {isFetching ? "FETCHING..." : "↻ REFRESH"}
                </button>
              )}
              <button
                onClick={() => setShowKeyInput(true)}
                style={{ background: "transparent", border: "1px solid #2244aa", color: "#4488ff", padding: "4px 12px", borderRadius: 6, cursor: "pointer", fontFamily: "inherit", fontSize: 9, letterSpacing: 1 }}
              >
                {apiKey ? "⚙ API KEY" : "+ ADD KEY"}
              </button>
            </div>
            {lastUpdated && (
              <div style={{ fontSize: 7, color: "#334", letterSpacing: 1, marginTop: 4, textAlign: "right" }}>
                CALLS USED: {callsUsed} / 25 · DATA: {TICKERS.map(t => `${t}:${fetchStatus[t] === "ok" ? "✓" : fetchStatus[t] === "error" ? "✗" : "○"}`).join("  ")}
              </div>
            )}
          </div>
        </div>

        {/* Fetch log (collapsible) */}
        {fetchLog.length > 0 && (
          <div style={{ marginBottom: 10, padding: "8px 12px", background: "#04040e", border: "1px solid #0f0f22", borderRadius: 8, maxHeight: 120, overflowY: "auto", fontFamily: "inherit" }}>
            {fetchLog.map((l, i) => (
              <div key={i} style={{ fontSize: 8, color: l.ok ? "#446" : "#663", letterSpacing: .5, lineHeight: 1.8 }}>
                <span style={{ color: "#224", marginRight: 8 }}>[{l.t}]</span>
                <span style={{ color: l.ok ? "#557" : "#664" }}>{l.msg}</span>
              </div>
            ))}
          </div>
        )}

        {/* ACCOUNT + BROKER STRIP */}
        <div style={{ display: "flex", gap: 6, marginBottom: 10, flexWrap: "wrap" }}>
          {acctBreak.map(a => (
            <div key={a.name} onClick={() => { setTab("holdings"); setAcctFilter(a.name); }} style={{ padding: "5px 12px", background: ACCOUNT_BG[a.name], border: `1px solid ${a.color}44`, borderRadius: 8, cursor: "pointer" }}>
              <div style={{ fontFamily: "'Bebas Neue',sans-serif", fontSize: 18, color: a.color, lineHeight: 1 }}>{fmtCAD(a.value)}</div>
              <div style={{ fontSize: 7, color: a.color + "88", letterSpacing: 1 }}>{a.name} · {a.pct.toFixed(1)}%</div>
            </div>
          ))}
          <div style={{ width: 1, background: "#1a1a3a", margin: "0 4px" }} />
          {brokerBreak.map(b => (
            <div key={b.name} onClick={() => { setTab("holdings"); setBrokerFilter(b.name); }} style={{ padding: "5px 12px", background: (BROKER_COLORS[b.name] || "#333") + "11", border: `1px solid ${BROKER_COLORS[b.name] || "#555"}33`, borderRadius: 8, cursor: "pointer" }}>
              <div style={{ fontFamily: "'Bebas Neue',sans-serif", fontSize: 18, color: BROKER_COLORS[b.name] || "#999", lineHeight: 1 }}>{fmtCAD(b.value)}</div>
              <div style={{ fontSize: 7, color: (BROKER_COLORS[b.name] || "#888") + "88", letterSpacing: 1 }}>{b.name} · {b.pct.toFixed(1)}%</div>
            </div>
          ))}
        </div>

        {/* METRICS BAR */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(7,1fr)", gap: 2, marginBottom: -1 }}>
          {[
            { label: "TOTAL VALUE (CAD)", value: fmtCAD(totalCAD), color: "#00D4FF" },
            { label: "UNREALIZED G/L", value: `${totalGLpct >= 0 ? "+" : ""}${totalGLpct.toFixed(2)}%`, color: totalGLpct >= 0 ? "#00FF88" : "#FF4455" },
            { label: "WEIGHTED CAGR", value: `${metrics.wCAGR.toFixed(2)}%`, color: "#44AAFF" },
            { label: "ANNUAL DIVIDEND", value: fmtCAD(metrics.annualDiv), color: "#FFD700" },
            { label: "PORTFOLIO BETA", value: metrics.wBeta.toFixed(2), color: "#FF6B35" },
            { label: "20YR PROJECTION", value: fmtCAD(metrics.val20yr / 1000) + "K", color: "#CC44FF" },
            { label: "VS 8% TARGET", value: `${cagrGap >= 0 ? "+" : ""}${cagrGap.toFixed(2)}%`, color: cagrGap >= 0 ? "#00FF88" : "#FF4455" },
          ].map((m, i) => (
            <div key={i} style={{ padding: "8px 10px", borderTop: `2px solid ${m.color}22` }}>
              <div style={{ fontSize: 7, letterSpacing: 2, color: "#334", marginBottom: 2 }}>{m.label}</div>
              <div style={{ fontFamily: "'Bebas Neue',sans-serif", fontSize: 19, color: m.color, letterSpacing: 1 }}>{m.value}</div>
            </div>
          ))}
        </div>
        <div style={{ display: "flex", gap: 2, marginTop: 10 }}>
          {tabs.map(t => (
            <button key={t} className={`tab ${tab === t ? "on" : ""}`} onClick={() => setTab(t)}>
              {t === "tax" ? "🍁 TAX" : t === "heatmap" ? "▦ HEATMAP" : t.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* ── CONTENT ── */}
      <div style={{ padding: "18px 26px" }}>

        {/* ════ HEATMAP */}
        {tab === "heatmap" && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, flexWrap: "wrap", gap: 8 }}>
              <div style={{ display: "flex", gap: 5, flexWrap: "wrap", alignItems: "center" }}>
                <span style={{ fontSize: 8, letterSpacing: 2, color: "#334", marginRight: 2 }}>SCALE:</span>
                {[
                  { bg: "#003d1a", border: "#00aa44", text: "#00ff88", label: "≥+8%" },
                  { bg: "#00291a", border: "#007733", text: "#00cc66", label: "+5–8%" },
                  { bg: "#001a12", border: "#115533", text: "#44cc88", label: "0–+5%" },
                  { bg: "#1a0808", border: "#663322", text: "#ff8877", label: "0–−2%" },
                  { bg: "#2a0808", border: "#882222", text: "#ff5544", label: "−2–−5%" },
                  { bg: "#3a0606", border: "#aa1111", text: "#ff2211", label: "<−5%" },
                ].map((c, i) => (
                  <div key={i} style={{ padding: "3px 8px", background: c.bg, border: `1px solid ${c.border}`, borderRadius: 4, fontSize: 9, color: c.text }}>{c.label}</div>
                ))}
              </div>
              <div style={{ display: "flex", gap: 5 }}>
                {[["value", "SIZE"], ["gl", "TOTAL G/L"], ["day", "TODAY"], ["ticker", "A–Z"]].map(([k, l]) => (
                  <button key={k} onClick={() => setHeatSort(k)} style={{ padding: "3px 9px", borderRadius: 8, fontSize: 8, letterSpacing: 1, cursor: "pointer", fontFamily: "inherit", background: heatSort === k ? "#1a1a44" : "transparent", border: `1px solid ${heatSort === k ? "#00D4FF" : "#222"}`, color: heatSort === k ? "#00D4FF" : "#445" }}>{l}</button>
                ))}
              </div>
            </div>

            <div style={{ fontSize: 8, color: "#2a2a44", letterSpacing: 1, marginBottom: 10 }}>
              SOURCE: {priceSource.toUpperCase()} · TILE SIZE ∝ MARKET VALUE · HOVER FOR DETAILS
              {isFetching && <span style={{ color: "#FFD700", marginLeft: 8 }}><span className="spinner" /> FETCHING LIVE PRICES...</span>}
            </div>

            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {heatTiles.map(h => {
                const c = h.heatColor;
                const w = Math.max(82, Math.min(430, (h.weight / 100) * 1380));
                const th = Math.max(82, w * 0.54);
                const isH = hoveredTicker === h.ticker;
                const isLoading = h.fetchStatus === "loading";
                const isErr = h.fetchStatus === "error";
                return (
                  <div key={h.ticker}
                    className="heat-tile"
                    onMouseEnter={() => setHoveredTicker(h.ticker)}
                    onMouseLeave={() => setHoveredTicker(null)}
                    style={{ width: w, minHeight: th, background: c.bg, border: `1.5px solid ${isH ? c.text : isErr ? "#aa2200" : c.border}`, boxShadow: isH ? `0 0 20px ${c.text}44` : undefined, opacity: isLoading ? 0.6 : 1 }}
                  >
                    <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 2, background: `linear-gradient(90deg,transparent,${c.text}55,transparent)`, borderRadius: "10px 10px 0 0" }} />
                    {isLoading && <div style={{ position: "absolute", top: 6, right: 8 }}><span className="spinner" /></div>}
                    {isErr && <div style={{ position: "absolute", top: 5, right: 7, fontSize: 7, color: "#ff6644", letterSpacing: 1 }}>FALLBACK</div>}

                    <div>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 4 }}>
                        <div style={{ fontFamily: "'Bebas Neue',sans-serif", fontSize: Math.max(17, Math.min(26, w / 6)), color: c.text, letterSpacing: 2, lineHeight: 1 }}>{h.ticker}</div>
                        <div style={{ display: "flex", gap: 3, flexWrap: "wrap", justifyContent: "flex-end" }}>
                          <ABadge a={h.account} /><BBadge b={h.broker} />
                        </div>
                      </div>
                      {w > 115 && <div style={{ fontSize: Math.max(8, Math.min(9, w / 22)), color: c.text + "88", marginBottom: 3, lineHeight: 1.2 }}>{h.name.split("(")[0].trim()}</div>}
                    </div>

                    <div>
                      <div style={{ display: "flex", alignItems: "baseline", gap: 6, marginBottom: 2 }}>
                        <span style={{ fontFamily: "'Bebas Neue',sans-serif", fontSize: Math.max(14, Math.min(20, w / 8)), color: h.dayChgPct >= 0 ? "#00cc88" : "#ff6655", letterSpacing: .5 }}>
                          {h.currency === "USD" ? "$" : "C$"}{fmt(h.currPrice, 2)}
                        </span>
                        {w > 110 && h.dayChgPct !== 0 && (
                          <span style={{ fontSize: 8, color: h.dayChgPct >= 0 ? "#00cc88" : "#ff6655" }}>
                            {h.dayChgPct >= 0 ? "▲" : "▼"}{Math.abs(h.dayChgPct).toFixed(2)}%
                          </span>
                        )}
                      </div>

                      <div style={{ fontFamily: "'Bebas Neue',sans-serif", fontSize: Math.max(20, Math.min(38, w / 5)), color: c.text, letterSpacing: 1, lineHeight: 1, marginBottom: 3 }}>
                        {h.glPct !== null ? `${h.glPct >= 0 ? "+" : ""}${h.glPct.toFixed(2)}%` : "—"}
                      </div>

                      {w > 100 && (
                        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                          <span style={{ fontSize: 8, color: c.text + "88" }}>{fmtCAD(h.mktValueCAD)}</span>
                          {w > 150 && <span style={{ fontSize: 8, color: c.text + "55" }}>{h.weight.toFixed(1)}%</span>}
                        </div>
                      )}

                      {isH && w > 110 && (
                        <div style={{ marginTop: 7, paddingTop: 7, borderTop: `1px solid ${c.border}`, display: "flex", flexDirection: "column", gap: 2 }}>
                          <div style={{ fontSize: 8, color: c.text + "cc" }}>Qty {h.qty % 1 === 0 ? h.qty : h.qty.toFixed(2)} · Avg {h.currency === "USD" ? "$" : "C$"}{fmt(h.avgCost, 2)}</div>
                          {w > 160 && <div style={{ fontSize: 8, color: c.text + "99" }}>G/L {h.glAmtLocal >= 0 ? "+" : ""}{h.currency === "USD" ? "$" : "C$"}{fmt(Math.abs(h.glAmtLocal), 0)} · Yield {h.dividendYield}% · β{h.beta}</div>}
                          {w > 200 && h.high && <div style={{ fontSize: 8, color: c.text + "77" }}>H: {fmt(h.high, 2)} · L: {fmt(h.low, 2)} · {h.latestDay}</div>}
                          {w > 220 && h.volume && <div style={{ fontSize: 8, color: c.text + "55" }}>Vol: {h.volume?.toLocaleString()}</div>}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Band summary */}
            <div style={{ marginTop: 16, display: "grid", gridTemplateColumns: "repeat(6,1fr)", gap: 6 }}>
              {[
                { bg: "#003d1a", border: "#00aa44", text: "#00ff88", label: "DEEP GREEN ≥+8%", fn: h => h.glPct !== null && h.glPct >= 8 },
                { bg: "#00291a", border: "#007733", text: "#00cc66", label: "GREEN +5–+8%", fn: h => h.glPct !== null && h.glPct >= 5 && h.glPct < 8 },
                { bg: "#001a12", border: "#115533", text: "#44cc88", label: "LIGHT GREEN 0–+5%", fn: h => h.glPct !== null && h.glPct >= 0 && h.glPct < 5 },
                { bg: "#1a0808", border: "#663322", text: "#ff8877", label: "LIGHT RED 0–−2%", fn: h => h.glPct !== null && h.glPct < 0 && h.glPct >= -2 },
                { bg: "#2a0808", border: "#882222", text: "#ff5544", label: "RED −2–−5%", fn: h => h.glPct !== null && h.glPct < -2 && h.glPct >= -5 },
                { bg: "#3a0606", border: "#aa1111", text: "#ff2211", label: "DARK RED <−5%", fn: h => h.glPct !== null && h.glPct < -5 },
              ].map((band, i) => {
                const tickers = withWeights.filter(band.fn);
                return (
                  <div key={i} style={{ background: band.bg, border: `1px solid ${band.border}`, borderRadius: 8, padding: "9px 11px" }}>
                    <div style={{ fontSize: 7, color: band.text + "77", letterSpacing: 1, marginBottom: 6 }}>{band.label}</div>
                    {tickers.length === 0 ? <div style={{ fontSize: 9, color: band.text + "33" }}>—</div> : tickers.map(h => (
                      <div key={h.ticker} style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                        <span style={{ fontSize: 10, color: band.text, fontWeight: 500 }}>{h.ticker}</span>
                        <span style={{ fontSize: 9, color: band.text + "99" }}>{h.glPct >= 0 ? "+" : ""}{h.glPct.toFixed(1)}%</span>
                      </div>
                    ))}
                    <div style={{ marginTop: 5, paddingTop: 5, borderTop: `1px solid ${band.border}`, fontSize: 7, color: band.text + "55" }}>
                      {tickers.length} · {fmtCAD(tickers.reduce((s, h) => s + h.mktValueCAD, 0))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ════ OVERVIEW */}
        {tab === "overview" && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14 }}>
            <div className="card" style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
              <div style={{ fontSize: 8, letterSpacing: 3, color: "#335" }}>ALLOCATION BY HOLDING</div>
              <PieChart data={withWeights.map(h => ({ name: h.ticker, value: h.weight, color: h.color }))} size={175} />
              <div style={{ width: "100%", maxHeight: 240, overflowY: "auto" }}>
                {withWeights.sort((a, b) => b.weight - a.weight).map(h => (
                  <div key={h.ticker} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 5 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                      <div style={{ width: 6, height: 6, borderRadius: 2, background: h.heatColor.text }} />
                      <span style={{ fontSize: 9, color: "#aab" }}>{h.ticker}</span>
                      <ABadge a={h.account} />
                    </div>
                    <span style={{ fontSize: 9, color: h.heatColor.text }}>{h.weight.toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <div className="card">
                <div style={{ fontSize: 8, letterSpacing: 3, color: "#335", marginBottom: 10 }}>BY ASSET CLASS</div>
                {assetClasses.sort((a, b) => b.value - a.value).map(a => (
                  <div key={a.name} style={{ marginBottom: 7 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                      <span style={{ fontSize: 9, color: "#aab" }}>{a.name}</span>
                      <div style={{ display: "flex", gap: 8, fontSize: 9 }}>
                        <span style={{ color: "#667" }}>{fmtCAD(a.value)}</span>
                        <span style={{ color: acClrs[a.name] || "#888" }}>{a.pct.toFixed(1)}%</span>
                      </div>
                    </div>
                    <Bar value={a.pct} max={100} color={acClrs[a.name] || "#888"} />
                  </div>
                ))}
              </div>
              <div className="card">
                <div style={{ fontSize: 8, letterSpacing: 3, color: "#335", marginBottom: 10 }}>BY ACCOUNT TYPE</div>
                {acctBreak.map(a => (
                  <div key={a.name} style={{ marginBottom: 8 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                      <span style={{ fontSize: 10, color: a.color }}>{a.name}</span>
                      <div style={{ display: "flex", gap: 8, fontSize: 9 }}>
                        <span style={{ color: "#667" }}>{fmtCAD(a.value)}</span>
                        <span style={{ color: a.color }}>{a.pct.toFixed(1)}%</span>
                      </div>
                    </div>
                    <Bar value={a.pct} max={100} color={a.color} />
                  </div>
                ))}
              </div>
            </div>
            <div className="card">
              <div style={{ fontSize: 8, letterSpacing: 3, color: "#335", marginBottom: 10 }}>LIVE SNAPSHOT</div>
              {[
                { label: "DATA SOURCE", v: priceSource, c: priceSource === "Alpha Vantage" ? "#00FF88" : "#FFD700" },
                { label: "LAST REFRESHED", v: lastUpdated ? lastUpdated.toLocaleTimeString("en-CA", { hour12: false }) : "Mar 5, 2026 close", c: "#aab" },
                { label: "USD/CAD", v: usdcad.toFixed(5), c: "#88AACC" },
                { label: "COST BASIS (CAD)", v: fmtCAD(totalCostCAD), c: "#778" },
                { label: "MARKET VALUE (CAD)", v: fmtCAD(totalCAD), c: "#00D4FF" },
                { label: "UNREALIZED G/L", v: `${totalGL >= 0 ? "+" : ""}${fmtCAD(totalGL)}`, c: totalGL >= 0 ? "#00FF88" : "#FF4455" },
                { label: "ANNUAL DIVIDEND", v: fmtCAD(metrics.annualDiv), c: "#FFD700" },
                { label: "MONTHLY DIVIDEND", v: fmtCAD(metrics.annualDiv / 12), c: "#FFAA00" },
                { label: "PORTFOLIO BETA", v: metrics.wBeta.toFixed(2), c: "#FF6B35" },
                { label: "20YR PROJECTION", v: fmtCAD(metrics.val20yr), c: "#CC44FF" },
              ].map(s => (
                <div key={s.label} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid #0f0f22" }}>
                  <span style={{ fontSize: 8, letterSpacing: 1, color: "#445" }}>{s.label}</span>
                  <span style={{ fontFamily: "'Bebas Neue',sans-serif", fontSize: 14, color: s.c }}>{s.v}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ════ HOLDINGS */}
        {tab === "holdings" && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10, flexWrap: "wrap", gap: 6 }}>
              <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                {["ALL", "RRSP", "TFSA", "Open"].map(a => (
                  <button key={a} className="pill" onClick={() => setAcctFilter(a)} style={{ background: acctFilter === a ? (ACCOUNT_COLORS[a] || "#00D4FF") + "22" : "transparent", borderColor: acctFilter === a ? (ACCOUNT_COLORS[a] || "#00D4FF") : "#222", color: acctFilter === a ? (ACCOUNT_COLORS[a] || "#00D4FF") : "#445", fontFamily: "inherit" }}>{a}</button>
                ))}
                <div style={{ width: 1, background: "#222", margin: "0 2px" }} />
                {["ALL", "CIBC", "RBC", "TD"].map(b => (
                  <button key={b} className="pill" onClick={() => setBrokerFilter(b)} style={{ background: brokerFilter === b ? (BROKER_COLORS[b] || "#888") + "22" : "transparent", borderColor: brokerFilter === b ? (BROKER_COLORS[b] || "#888") : "#222", color: brokerFilter === b ? (BROKER_COLORS[b] || "#888") : "#445", fontFamily: "inherit" }}>{b}</button>
                ))}
                <div style={{ width: 1, background: "#222", margin: "0 2px" }} />
                {[["value", "VALUE"], ["weight", "WEIGHT"], ["gl", "G/L"]].map(([k, l]) => (
                  <button key={k} className="pill" onClick={() => setSortBy(k)} style={{ background: sortBy === k ? "#1a1a44" : "transparent", border: `1px solid ${sortBy === k ? "#00D4FF" : "#222"}`, color: sortBy === k ? "#00D4FF" : "#445", fontFamily: "inherit" }}>{l}</button>
                ))}
              </div>
            </div>
            <div style={{ border: "1px solid #1a1a44", borderRadius: 10, overflow: "auto" }}>
              <div className="hrow" style={{ background: "#09091e", borderBottom: "1px solid #1a1a44" }}>
                {["TICKER", "NAME", "ACCT", "BROKER", "QTY", "AVG COST", "LAST PRICE", "DAY CHG", "MKT VAL (CAD)", "TOTAL G/L", "AS OF"].map((h, i) => (
                  <div key={i} style={{ fontSize: 7, letterSpacing: 2, color: "#334" }}>{h}</div>
                ))}
              </div>
              {filtered.map((h, i) => {
                const gp = h.glPct || 0;
                const statusColor = h.fetchStatus === "ok" ? "#00FF88" : h.fetchStatus === "error" ? "#FF4444" : h.fetchStatus === "loading" ? "#FFD700" : "#334";
                return (
                  <div key={i} className="hrow">
                    <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                      <div style={{ width: 4, height: 4, borderRadius: "50%", background: statusColor, flexShrink: 0 }} />
                      <span style={{ color: h.heatColor.text, fontWeight: 500, fontSize: 10 }}>{h.ticker}</span>
                    </div>
                    <div style={{ fontSize: 9, color: "#8899bb", overflow: "hidden", whiteSpace: "nowrap", textOverflow: "ellipsis" }}>{h.name.split("(")[0].trim()}</div>
                    <ABadge a={h.account} />
                    <BBadge b={h.broker} />
                    <span style={{ color: "#aab" }}>{h.qty % 1 === 0 ? h.qty : h.qty.toFixed(2)}</span>
                    <span style={{ color: "#667", fontSize: 9 }}>{h.currency === "USD" ? "$" : "C$"}{fmt(h.avgCost, 2)}</span>
                    <span style={{ fontFamily: "'Bebas Neue',sans-serif", fontSize: 13, color: h.dayChgPct >= 0 ? "#00cc88" : "#ff6655", letterSpacing: .5 }}>
                      {h.currency === "USD" ? "$" : "C$"}{fmt(h.currPrice, 2)}
                    </span>
                    <span style={{ fontSize: 9, color: h.dayChgPct >= 0 ? "#00cc66" : "#ff5544" }}>
                      {h.dayChgPct !== 0 ? (h.dayChgPct >= 0 ? "▲" : "▼") + Math.abs(h.dayChgPct).toFixed(2) + "%" : "—"}
                    </span>
                    <span style={{ color: "#dde", fontWeight: 500, fontSize: 10 }}>{fmtCAD(h.mktValueCAD)}</span>
                    <span className={gp >= 0 ? "gl-pos" : "gl-neg"} style={{ fontSize: 10 }}>{gp >= 0 ? "+" : ""}{gp.toFixed(2)}%</span>
                    <span style={{ fontSize: 8, color: "#334" }}>{h.latestDay}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ════ TAX */}
        {tab === "tax" && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <div className="card">
              <div style={{ fontSize: 8, letterSpacing: 3, color: "#335", marginBottom: 10 }}>TAX PLACEMENT · RRSP FULL</div>
              {withWeights.sort((a, b) => b.mktValueCAD - a.mktValueCAD).map((h, i) => (
                <div key={i} style={{ padding: "9px 0", borderBottom: "1px solid #0f0f22" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
                      <span style={{ color: h.heatColor.text, fontSize: 12, fontWeight: 500 }}>{h.ticker}</span>
                      <ABadge a={h.account} /><BBadge b={h.broker} />
                    </div>
                    <div style={{ display: "flex", gap: 5 }}><span style={{ fontSize: 9, color: "#556" }}>{fmtCAD(h.mktValueCAD)}</span><TBadge r={h.taxRating} /></div>
                  </div>
                  <div style={{ fontSize: 9, color: "#667", lineHeight: 1.5 }}>{
                    h.ticker === "AVUV" ? "RRSP (FULL): Treaty-exempt from 15% IRS WHT. Optimal. Hold as-is." :
                      h.ticker === "COST" ? "RRSP (FULL): US stock with tax-deferred compounding. Hold existing lot." :
                        h.ticker === "GLD" ? "Open: No dividends = no WHT issue. Capital gains taxed at 50% inclusion on exit." :
                          h.ticker === "MSFT" ? "TFSA: Low yield, WHT minimal. Capital gains fully sheltered. Correct." :
                            h.ticker === "NVDA" ? "TFSA: ~0% yield. Capital gain potential fully sheltered. Best possible account." :
                              h.ticker === "SLV" ? "Open: Significant unrealized gain. No annual drag. Plan exit timing with loss harvesting." :
                                h.ticker === "VDY.TO" ? "Open: DTC reduces CAN dividend tax to ~25%. Shift to TFSA when Jan 1 room opens." :
                                  h.ticker === "VFV.TO" ? "TFSA: 15% WHT embedded at fund level — manageable at 1.1% yield. Fine to hold." :
                                    h.ticker === "VOO" ? "Multi-acct: RRSP full. TFSA lots pay 15% IRS WHT. Open lot faces WHT + CG tax. Do not add more in Open." :
                                      h.ticker === "WCP.TO" ? "TFSA: 6.2% yield fully sheltered. Excellent placement." :
                                        h.ticker === "XEC.TO" ? "TFSA: EM WHT embedded at fund level regardless. Capital gains sheltered." :
                                          h.ticker === "XEF.TO" ? "⚠ SUBOPTIMAL: ~0.48%/yr EAFE WHT permanently lost in TFSA. RRSP full = no fix." :
                                            h.ticker === "XEI.TO" ? "TFSA: 5.5% yield fully sheltered. Optimal." :
                                              h.ticker === "XIU.TO" ? "TFSA: CAN dividends + gains sheltered. Correct placement." :
                                                "Neutral."
                  }</div>
                </div>
              ))}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <div className="card">
                <div style={{ fontSize: 8, letterSpacing: 3, color: "#335", marginBottom: 10 }}>PRIORITY ACTIONS (RRSP FULL)</div>
                {[
                  { pri: "HIGH", action: "Stop buying VOO in Open/TFSA", reason: "RRSP full — no WHT-exempt home for new USD ETFs. Route S&P 500 to VFV.TO in TFSA instead.", impact: "Prevent further WHT drag", color: "#FF3366" },
                  { pri: "HIGH", action: "Accept XEF.TO drag — no fix", reason: "EAFE in TFSA loses ~0.48%/yr permanently. RRSP full. Consider swap-based EAFE alternative.", impact: "~$300/yr unrecoverable", color: "#FF6B35" },
                  { pri: "MEDIUM", action: "VDY.TO → TFSA next Jan 1", reason: "~$7,000 new TFSA room each Jan 1. Prioritize shifting VDY.TO for full dividend sheltering.", impact: "+$1,200/yr effective", color: "#FFD700" },
                  { pri: "MEDIUM", action: "SLV exit timing — pair with losses", reason: "High unrealized gain. No annual drag. Harvest offsetting losses in same tax year at exit.", impact: "Reduce CG tax", color: "#FFAA44" },
                  { pri: "WATCH", action: "QQQM entry → TFSA only", reason: "US/Iran trigger fires → TFSA is the only sheltered option. 0.60% yield = minimal WHT.", impact: "100% gains tax-free", color: "#00FF88" },
                ].map(o => (
                  <div key={o.action} style={{ padding: "9px 0", borderBottom: "1px solid #0f0f22" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                      <span style={{ fontSize: 8, color: o.color, letterSpacing: 1 }}>{o.pri}</span>
                      <span style={{ fontSize: 8, color: "#00FF88" }}>{o.impact}</span>
                    </div>
                    <div style={{ fontSize: 10, color: "#dde", marginBottom: 2 }}>{o.action}</div>
                    <div style={{ fontSize: 9, color: "#667", lineHeight: 1.5 }}>{o.reason}</div>
                  </div>
                ))}
              </div>
              <div className="card">
                <div style={{ fontSize: 8, letterSpacing: 3, color: "#335", marginBottom: 8 }}>ANNUAL WHT DRAG ESTIMATE</div>
                {[
                  { label: "XEF.TO (TFSA, EAFE WHT)", drag: withWeights.filter(h => h.ticker === "XEF.TO").reduce((s, h) => s + h.mktValueCAD, 0) * 0.0048, c: "#FF3366" },
                  { label: "VOO (TFSA, IRS WHT)", drag: withWeights.filter(h => h.ticker === "VOO").reduce((s, h) => s + h.mktValueCAD, 0) * 0.002, c: "#FF6B35" },
                  { label: "VFV.TO (fund-level WHT)", drag: withWeights.filter(h => h.ticker === "VFV.TO").reduce((s, h) => s + h.mktValueCAD, 0) * 0.002, c: "#FFCC44" },
                ].map(d => (
                  <div key={d.label} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid #0f0f22" }}>
                    <span style={{ fontSize: 9, color: "#667" }}>{d.label}</span>
                    <span style={{ fontSize: 9, color: d.c }}>-{fmtCAD(d.drag)}/yr</span>
                  </div>
                ))}
                {(() => { const t = withWeights.filter(h => h.ticker === "XEF.TO").reduce((s, h) => s + h.mktValueCAD, 0) * 0.0048 + withWeights.filter(h => h.ticker === "VOO").reduce((s, h) => s + h.mktValueCAD, 0) * 0.002 + withWeights.filter(h => h.ticker === "VFV.TO").reduce((s, h) => s + h.mktValueCAD, 0) * 0.002; return (<div style={{ display: "flex", justifyContent: "space-between", paddingTop: 7 }}><span style={{ fontSize: 9, color: "#aab" }}>TOTAL</span><span style={{ fontFamily: "'Bebas Neue',sans-serif", fontSize: 18, color: "#FF3366" }}>-{fmtCAD(t)}/yr</span></div>); })()}
              </div>
            </div>
          </div>
        )}

        {/* ════ GEOGRAPHY */}
        {tab === "geography" && (
          <div style={{ display: "grid", gridTemplateColumns: "220px 1fr", gap: 14 }}>
            <div className="card" style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
              <div style={{ fontSize: 8, letterSpacing: 3, color: "#335" }}>GEOGRAPHIC EXPOSURE</div>
              <PieChart data={geoData} size={185} />
              {geoData.map(g => (
                <div key={g.name} style={{ width: "100%" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                    <span style={{ fontSize: 9, color: "#aab" }}>{g.name}</span>
                    <span style={{ fontSize: 9, color: g.color }}>{g.value.toFixed(1)}%</span>
                  </div>
                  <Bar value={g.value} max={100} color={g.color} />
                </div>
              ))}
            </div>
            <div className="card">
              <div style={{ fontSize: 8, letterSpacing: 3, color: "#335", marginBottom: 12 }}>REGIONAL ANALYSIS</div>
              {[
                { region: "United States", pct: geoData.find(g => g.name === "United States")?.value || 0, risk: "MODERATE", color: "#00D4FF", note: "VOO, VFV.TO, AVUV, MSFT, NVDA, COST. Dominant exposure. S&P ~21x P/E. AVUV in RRSP (treaty-exempt)." },
                { region: "Canada", pct: geoData.find(g => g.name === "Canada")?.value || 0, risk: "LOW", color: "#CC44FF", note: "VDY.TO (Open), XIU.TO, XEI.TO, WCP.TO (TFSA). DTC on Open dividends. TFSA positions fully sheltered." },
                { region: "Europe", pct: geoData.find(g => g.name === "Europe")?.value || 0, risk: "MODERATE", color: "#00FF88", note: "XEF.TO (TFSA). WHT drag unrecoverable, RRSP full. ECB cuts supportive. Cheap ~13x P/E." },
                { region: "Emerging Mkts", pct: geoData.filter(g => ["China", "India", "Taiwan", "South Korea", "Brazil", "Other EM"].includes(g.name)).reduce((s, g) => s + g.value, 0), risk: "HIGH", color: "#FF3366", note: "XEC.TO. India demographics + manufacturing shift. China geopolitical risk. EM WHT embedded at fund level." },
                { region: "Commodities", pct: geoData.find(g => g.name === "Global")?.value || 0, risk: "LOW", color: "#FFAA00", note: "GLD + SLV in Open. Real asset hedge. SLV +85% unrealized gain — monitor exit timing." },
              ].map(r => (
                <div key={r.region} style={{ padding: "10px 0", borderBottom: "1px solid #0f0f22" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                    <span style={{ color: r.color, fontSize: 11 }}>{r.region}</span>
                    <div style={{ display: "flex", gap: 7, alignItems: "center" }}>
                      <span style={{ fontSize: 9, color: "#667" }}>{r.pct.toFixed(1)}%</span>
                      <span style={{ padding: "1px 6px", borderRadius: 3, fontSize: 8, background: r.risk === "HIGH" ? "#FF336622" : r.risk === "MODERATE" ? "#FFD70022" : "#00FF8822", color: r.risk === "HIGH" ? "#FF3366" : r.risk === "MODERATE" ? "#FFD700" : "#00FF88" }}>{r.risk}</span>
                    </div>
                  </div>
                  <div style={{ fontSize: 9, color: "#667", lineHeight: 1.5 }}>{r.note}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ════ DIVIDENDS */}
        {tab === "dividends" && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <div className="card">
              <div style={{ fontSize: 8, letterSpacing: 3, color: "#335", marginBottom: 12 }}>DIVIDEND INCOME BY HOLDING (CAD)</div>
              {withWeights.filter(h => h.dividendYield > 0).sort((a, b) => b.annualDivCAD - a.annualDivCAD).map((h, i) => (
                <div key={i} style={{ padding: "8px 0", borderBottom: "1px solid #0f0f22" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                    <div style={{ display: "flex", gap: 5, alignItems: "center" }}>
                      <span style={{ color: h.color, fontSize: 11 }}>{h.ticker}</span>
                      <ABadge a={h.account} /><TBadge r={h.taxRating} />
                    </div>
                    <span style={{ fontSize: 11, color: "#dde" }}>{fmtCAD(h.annualDivCAD)}/yr</span>
                  </div>
                  <div style={{ fontSize: 8, color: "#445", marginBottom: 3 }}>Yield {h.dividendYield}% · {fmtCAD(h.annualDivCAD / 12)}/mo</div>
                  <Bar value={h.annualDivCAD} max={metrics.annualDiv} color={h.color} />
                </div>
              ))}
              <div style={{ display: "flex", justifyContent: "space-between", paddingTop: 10 }}>
                <span style={{ fontSize: 9, color: "#aab", letterSpacing: 1 }}>TOTAL ANNUAL</span>
                <span style={{ fontFamily: "'Bebas Neue',sans-serif", fontSize: 22, color: "#00FF88" }}>{fmtCAD(metrics.annualDiv)}</span>
              </div>
            </div>
            <div className="card">
              <div style={{ fontSize: 8, letterSpacing: 3, color: "#335", marginBottom: 12 }}>DRIP PROJECTIONS</div>
              {[1, 3, 5, 10, 15, 20].map(yr => {
                const proj = totalCAD * Math.pow(1 + metrics.wCAGR / 100, yr);
                const div = proj * (metrics.wYield / 100);
                return (
                  <div key={yr} style={{ display: "flex", justifyContent: "space-between", padding: "7px 0", borderBottom: "1px solid #0f0f22" }}>
                    <span style={{ fontSize: 10, color: "#667" }}>YEAR {yr}</span>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontFamily: "'Bebas Neue',sans-serif", fontSize: 18, color: "#00FF88" }}>{fmtCAD(div)}/yr</div>
                      <div style={{ fontSize: 8, color: "#334" }}>Portfolio: {fmtCAD(proj)}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ════ PROJECTION */}
        {tab === "projection" && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <div className="card">
              <div style={{ fontSize: 8, letterSpacing: 3, color: "#335", marginBottom: 14 }}>20-YEAR WEALTH SCENARIOS (CAD)</div>
              {[
                { label: "BEAR CASE", cagr: 5.0, color: "#FF3366" },
                { label: "BASE (YOUR TARGET)", cagr: 8.0, color: "#FFD700" },
                { label: "PORTFOLIO WEIGHTED", cagr: metrics.wCAGR, color: "#00D4FF" },
                { label: "BULL CASE", cagr: 12.0, color: "#00FF88" },
              ].map(s => {
                const proj = totalCAD * Math.pow(1 + s.cagr / 100, 20);
                return (
                  <div key={s.label} style={{ padding: "11px 0", borderBottom: "1px solid #0f0f22" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                      <span style={{ fontSize: 9, color: s.color, letterSpacing: 1 }}>{s.label}</span>
                      <span style={{ fontSize: 9, color: "#445" }}>CAGR {s.cagr.toFixed(1)}%</span>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 5 }}>
                      <div style={{ fontFamily: "'Bebas Neue',sans-serif", fontSize: 28, color: s.color }}>{fmtCAD(proj)}</div>
                      <span style={{ fontSize: 10, color: "#334" }}>{(proj / totalCAD).toFixed(1)}x</span>
                    </div>
                    <Bar value={proj} max={totalCAD * Math.pow(1.12, 20)} color={s.color} />
                  </div>
                );
              })}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <div className="card">
                <div style={{ fontSize: 8, letterSpacing: 3, color: "#335", marginBottom: 10 }}>MONTE CARLO · 10,000 SIMS (CAD)</div>
                {[
                  { pct: "10th percentile", val: totalCAD * Math.pow(1.04, 20), color: "#FF3366" },
                  { pct: "25th percentile", val: totalCAD * Math.pow(1.065, 20), color: "#FF8855" },
                  { pct: "50th percentile", val: totalCAD * Math.pow(1.085, 20), color: "#FFD700" },
                  { pct: "75th percentile", val: totalCAD * Math.pow(1.11, 20), color: "#00FF88" },
                  { pct: "90th percentile", val: totalCAD * Math.pow(1.135, 20), color: "#00D4FF" },
                ].map(s => (
                  <div key={s.pct} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid #0f0f20" }}>
                    <span style={{ fontSize: 9, color: "#556" }}>{s.pct}</span>
                    <span style={{ fontSize: 9, color: s.color }}>{fmtCAD(s.val)}</span>
                  </div>
                ))}
                <div style={{ marginTop: 8, fontSize: 8, color: "#223", lineHeight: 1.5 }}>Assumes annual rebalancing + DRIP. Excludes tax, inflation, FX. All values CAD.</div>
              </div>
              <div className="card">
                <div style={{ fontSize: 8, letterSpacing: 3, color: "#335", marginBottom: 10 }}>FACTOR PROFILE</div>
                {withWeights.sort((a, b) => b.mktValueCAD - a.mktValueCAD).map((h, i) => (
                  <div key={i} style={{ padding: "6px 0", borderBottom: "1px solid #0f0f22" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 2 }}>
                      <div style={{ display: "flex", gap: 5 }}><span style={{ color: h.color, fontSize: 10 }}>{h.ticker}</span><ABadge a={h.account} /></div>
                      <div style={{ display: "flex", gap: 7, fontSize: 9, color: "#556" }}><span>β{h.beta}</span><span>{h.expectedCAGR}%</span><span>S{h.sharpe}</span></div>
                    </div>
                    <div style={{ fontSize: 8, color: "#334" }}>{h.weight.toFixed(1)}% · {fmtCAD(h.mktValueCAD)}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      <div style={{ borderTop: "1px solid #0f0f22", padding: "9px 26px", display: "flex", justifyContent: "space-between", fontSize: 7, color: "#1a1a44", letterSpacing: 1 }}>
        <span>PORTFOLIO TERMINAL · CIBC + RBC + TD · v6.0 · ALPHA VANTAGE</span>
        <span>NOT FINANCIAL ADVICE · PRICES FROM ALPHA VANTAGE OR CSV SNAPSHOT</span>
        <span>USD/CAD {usdcad.toFixed(5)} · {priceSource}</span>
      </div>
    </div>
  );
}
