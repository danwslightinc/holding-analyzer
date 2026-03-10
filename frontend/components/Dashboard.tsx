// @ts-nocheck
import { useState, useMemo, useEffect, useRef, useCallback } from "react";
import dynamic from "next/dynamic";
import { usePortfolio } from "@/lib/PortfolioContext";
import { signOut, useSession } from "next-auth/react";

const PnLPage = dynamic(() => import("@/app/pnl/page"), { ssr: false, loading: () => <div style={{ color: '#00D4FF', padding: 40, textAlign: 'center', letterSpacing: 4, fontFamily: "'Bebas Neue',sans-serif", fontSize: 18 }}>LOADING P&L...</div> });
const TradeAnalysisPage = dynamic(() => import("@/app/trade-analysis/page"), { ssr: false, loading: () => <div style={{ color: '#00D4FF', padding: 40, textAlign: 'center', letterSpacing: 4, fontFamily: "'Bebas Neue',sans-serif", fontSize: 18 }}>LOADING TRADE ANALYSIS...</div> });
const QuantmentalPage = dynamic(() => import("@/app/quantmental/page"), { ssr: false, loading: () => <div style={{ color: '#00D4FF', padding: 40, textAlign: 'center', letterSpacing: 4, fontFamily: "'Bebas Neue',sans-serif", fontSize: 18 }}>LOADING QUANT-MENTAL...</div> });
const TransactionsPage = dynamic(() => import("@/app/transactions/page"), { ssr: false, loading: () => <div style={{ color: '#00D4FF', padding: 40, textAlign: 'center', letterSpacing: 4, fontFamily: "'Bebas Neue',sans-serif", fontSize: 18 }}>LOADING TRANSACTIONS...</div> });

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
  const slices = [];
  data.filter(d => d.value > 0).reduce((cum, d) => {
    const pct = d.value / total, s0 = cum;
    const newCum = cum + pct;
    const a1 = s0 * 2 * Math.PI - Math.PI / 2, a2 = newCum * 2 * Math.PI - Math.PI / 2;
    const r = size / 2 - 8, cx = size / 2, cy = size / 2;
    slices.push({ ...d, path: `M${cx},${cy} L${cx + r * Math.cos(a1)},${cy + r * Math.sin(a1)} A${r},${r} 0 ${pct > .5 ? 1 : 0},1 ${cx + r * Math.cos(a2)},${cy + r * Math.sin(a2)} Z` });
    return newCum;
  }, 0);
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {slices.map((s, i) => <path key={i} d={s.path} fill={s.color} opacity={.88} stroke="var(--bg)" strokeWidth={1.5} />)}
      <circle cx={size / 2} cy={size / 2} r={size / 4} fill="var(--bg)" />
    </svg>
  );
}

function Bar({ value, max = 100, color, height = 5 }) {
  return (
    <div style={{ background: "var(--bg2)", borderRadius: 4, height, width: "100%", overflow: "hidden" }}>
      <div style={{ width: `${Math.min((value / max) * 100, 100)}%`, height: "100%", background: color, borderRadius: 4, transition: "width .5s" }} />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────

// ─────────────────────────────────────────────────────────────────


// ─────────────────────────────────────────────────────────────────
// MAIN APP
// ─────────────────────────────────────────────────────────────────
const META_MAP = {
  AVUV: { type: "US Small Cap Value", color: "#FFD700", expectedCAGR: 11.5, beta: 1.22, geography: { "United States": 100 }, div: 1.85 },
  COST: { type: "US Large Cap Growth", color: "#FF6B35", expectedCAGR: 12.0, beta: 0.90, geography: { "United States": 100 }, div: 0.52 },
  GLD: { type: "Commodity – Gold", color: "#FFAA00", expectedCAGR: 5.5, beta: 0.10, geography: { "Global": 100 }, div: 0.00 },
  MSFT: { type: "US Large Cap Growth", color: "#00AAFF", expectedCAGR: 11.5, beta: 0.90, geography: { "United States": 100 }, div: 0.82 },
  NVDA: { type: "US Large Cap Growth", color: "#76FF44", expectedCAGR: 15.0, beta: 1.65, geography: { "United States": 100 }, div: 0.03 },
  SLV: { type: "Commodity – Silver", color: "#CCDDEE", expectedCAGR: 4.5, beta: 0.30, geography: { "Global": 100 }, div: 0.00 },
  "VDY.TO": { type: "Canadian High Dividend", color: "#CC44FF", expectedCAGR: 7.0, beta: 0.72, geography: { "Canada": 100 }, div: 4.10 },
  "VFV.TO": { type: "US Large Cap Blend", color: "#0088FF", expectedCAGR: 10.2, beta: 1.00, geography: { "United States": 100 }, div: 1.10 },
  VOO: { type: "US Large Cap Blend", color: "#00D4FF", expectedCAGR: 10.5, beta: 1.00, geography: { "United States": 100 }, div: 1.32 },
  "WCP.TO": { type: "Canadian Energy", color: "#FF8800", expectedCAGR: 6.0, beta: 1.35, geography: { "Canada": 100 }, div: 6.20 },
  "XEC.TO": { type: "Emerging Markets", color: "#FF3366", expectedCAGR: 8.8, beta: 1.05, geography: { "China": 28, "India": 18, "Taiwan": 16, "South Korea": 10, "Brazil": 5, "Other EM": 23 }, div: 2.80 },
  "XEF.TO": { type: "Developed Market ex-NA", color: "#00FF88", expectedCAGR: 7.5, beta: 0.85, geography: { "Europe": 55, "Japan": 22, "Australia/NZ": 10, "Other Developed": 13 }, div: 3.20 },
  "XEI.TO": { type: "Canadian High Dividend", color: "#AA44FF", expectedCAGR: 6.5, beta: 0.75, geography: { "Canada": 100 }, div: 5.50 },
  "XIU.TO": { type: "Canadian Large Cap", color: "#BB55EE", expectedCAGR: 7.2, beta: 0.82, geography: { "Canada": 100 }, div: 2.90 },
};

export default function Dashboard() {
  const { data: portData, dividends: divRaw, tickerPerf, loading, error, refresh } = usePortfolio();

  const [tab, setTab] = useState("overview");
  const [heatSort, setHeatSort] = useState("value");
  const [acctFilter, setAcctFilter] = useState("ALL");
  const [brokerFilter, setBrokerFilter] = useState("ALL");
  const [sortBy, setSortBy] = useState("value");
  const [hoveredTicker, setHoveredTicker] = useState(null);
  const [clock, setClock] = useState(new Date());
  const [theme, setTheme] = useState("dark");
  const isLight = theme === "light";
  const { data: session } = useSession();

  const ABadge = ({ a }) => {
    const baseBg = ACCOUNT_COLORS[a] || "#00D4FF";
    return <span style={{ display: "inline-block", padding: "1px 5px", borderRadius: 3, fontSize: 11, letterSpacing: 1, background: isLight ? baseBg + "22" : (ACCOUNT_BG[a] || "#001a2a"), border: `1px solid ${baseBg}44`, color: baseBg }}>{a}</span>;
  };
  const BBadge = ({ b }) => {
    const baseClr = BROKER_COLORS[b] || "#888";
    return <span style={{ display: "inline-block", padding: "1px 5px", borderRadius: 3, fontSize: 11, letterSpacing: 1, background: isLight ? baseClr + "11" : baseClr + "22", border: `1px solid ${baseClr}44`, color: isLight ? baseClr : (BROKER_COLORS[b] || "#999") }}>{b}</span>;
  };
  const TBadge = ({ r }) => <span style={{ display: "inline-block", padding: "1px 5px", borderRadius: 3, fontSize: 11, letterSpacing: 1, background: TAX_COLORS[r] + (isLight ? "22" : "18"), border: `1px solid ${TAX_COLORS[r]}44`, color: TAX_COLORS[r] }}>{r}</span>;

  // Clock
  useEffect(() => {
    const t = setInterval(() => setClock(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const [apiKey, setApiKey] = useState("");
  const [showKeyInput, setShowKeyInput] = useState(false);

  useEffect(() => {
    fetch("http://127.0.0.1:8000/api/settings/ALPHA_VANTAGE_API_KEY")
      .then(r => r.json())
      .then(d => { if (d.value) setApiKey(d.value); })
      .catch(e => console.error(e));
  }, []);

  const saveApiKey = async () => {
    try {
      await fetch("http://127.0.0.1:8000/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key: "ALPHA_VANTAGE_API_KEY", value: apiKey })
      });
      setShowKeyInput(false);
      refresh(true);
    } catch (e) {
      console.error(e);
    }
  };

  const isFetching = loading;
  const priceSource = "Alpha Vantage (Native)";
  const lastUpdated = new Date();
  const usdcad = portData?.summary?.usd_cad_rate || FALLBACK_USDCAD;
  const callsUsed = 0;
  const fetchStatus = {}; // Mock

  // ── DERIVED DATA ─────────────────────────────────────────────

  const holdings = useMemo(() => {
    if (!portData || !portData.holdings) return [];

    // Create lookup for performance data
    const perfLookup = {};
    if (tickerPerf) {
      Object.keys(tickerPerf).forEach(sym => {
        perfLookup[sym] = tickerPerf[sym]['1d']?.change_pct || 0;
      });
    }

    // Lookup for dividends
    const divLookup = {};
    if (divRaw && divRaw.holdings) {
      divRaw.holdings.forEach(d => {
        divLookup[d.symbol] = d.dividend_yield * 100;
      });
    }

    return portData.holdings.map(h => {
      const meta = META_MAP[h.Symbol] || { type: "Unknown", color: "#888", expectedCAGR: 8.0, beta: 1.0, geography: { "Global": 100 }, div: 0 };
      const cp = h['Current Price'] || 0;
      const prevClose = cp; // Backend doesn't give prev cost easily unless using perf
      const dayChgPct = perfLookup[h.Symbol] || 0;

      let mkt = h.Market_Value_CAD || h.Market_Value;
      // Fallback calculation if backend market value is missing but we have price/qty
      if (!mkt && h.Quantity && cp) {
        mkt = h.Quantity * cp * (h.Currency === 'USD' ? usdcad : 1.0);
      }
      const gl = h['Purchase Price'] > 0 ? ((cp / h['Purchase Price']) - 1) * 100 : null;

      const yieldPct = divLookup[h.Symbol] || meta.div;

      return {
        ...h,
        ticker: h.Symbol,
        name: h.Symbol, // Alternatively, fetch name from a map if needed
        account: h.Account_Type || "Open",
        broker: h.Broker || "CIBC",
        currency: h.Currency || "CAD",
        qty: h.Quantity,
        avgCost: h['Purchase Price'] || 0,
        type: meta.type,
        color: meta.color,
        dividendYield: yieldPct,
        beta: meta.beta,
        expectedCAGR: meta.expectedCAGR,
        geography: meta.geography,

        currPrice: cp, prevClose, dayChgPct,
        mktValueCAD: mkt,
        costCAD: mkt - (h.PnL_CAD || h.PnL || 0),
        glPct: gl,
        glAmtLocal: (cp - (h['Purchase Price'] || 0)) * h.Quantity,
        annualDivCAD: mkt * (yieldPct / 100),
        heatColor: heatColor(gl),
        taxRating: TAX_MAP[h.Symbol] || "NEUTRAL",
        fetchStatus: "ok",
        latestDay: new Date().toLocaleDateString("en-CA"),
        volume: null,
        high: null, low: null,
      };
    });
  }, [portData, tickerPerf, divRaw]);


  const totalCAD = useMemo(() => holdings.reduce((s, h) => s + h.mktValueCAD, 0), [holdings]);
  const totalCostCAD = useMemo(() => holdings.reduce((s, h) => s + h.costCAD, 0), [holdings]);
  const totalGL = totalCAD - totalCostCAD;
  const totalGLpct = totalCostCAD > 0 ? (totalGL / totalCostCAD) * 100 : 0;

  const withWeights = useMemo(() => holdings.map(h => ({ ...h, weight: (h.mktValueCAD / totalCAD) * 100 })), [holdings, totalCAD]);

  const combinedWeights = useMemo(() => {
    const combined: Record<string, any> = {};
    withWeights.forEach(h => {
      if (!combined[h.ticker]) {
        combined[h.ticker] = { ...h, weight: 0 };
      }
      combined[h.ticker].weight += h.weight;
    });
    return Object.values(combined).sort((a, b) => b.weight - a.weight);
  }, [withWeights]);

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
  const okCount = holdings.length;
  const errCount = 0;
  const tabs = ["overview", "heatmap", "holdings", "tax", "geography", "dividends", "projection", "pnl", "trades", "quantmental", "transactions"];

  // Handle loading state before rendering main app view
  if (loading && !portData) {
    return <div style={{ background: "#06061a", minHeight: "100vh", color: "#00D4FF", display: "flex", justifyContent: "center", alignItems: "center", fontFamily: "'Bebas Neue',sans-serif", fontSize: 24, letterSpacing: 4 }}>LOADING PORTFOLIO DATA...</div>;
  }
  if (error) {
    return <div style={{ background: "#06061a", minHeight: "100vh", color: "#FF4455", display: "flex", justifyContent: "center", alignItems: "center", fontFamily: "'Bebas Neue',sans-serif", fontSize: 24 }}>ERROR LOADING DATA</div>;
  }

  return (
    <div className={theme === "light" ? "terminal light" : "terminal"} style={{ fontFamily: "'DM Mono','Courier New',monospace", minHeight: "100vh" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Bebas+Neue&display=swap');
        *{box-sizing:border-box;margin:0;padding:0}

        /* ── THEME VARIABLES ── */
        .terminal{--bg:#06061a;--bg2:#0a0a22;--card:linear-gradient(135deg,#0d0d26,#10102a);--card-border:#1e1e48;--card-hover:#2a2a60;--text:#e0e0ff;--muted:#556;--muted2:#334;--row-border:#0f0f22;--row-hover:#0d0d24;--accent:#00D4FF;--green:#00FF88;--red:#FF4455;--gold:#FFD700;--tab-bg:#1a1a44;--header-bg:linear-gradient(180deg,#0a0a22,#06061a);--header-border:#181840;--scroll-track:#0a0a1a;--scroll-thumb:#334;--input-bg:#0a0a20;--input-border:#2244aa;color:var(--text);background:var(--bg)}
        .terminal.light{--bg:#f0f0f4;--bg2:#e8e8f0;--card:linear-gradient(135deg,#ffffff,#f5f5fa);--card-border:#d0d0e0;--card-hover:#b0b0cc;--text:#1a1a2e;--muted:#777;--muted2:#999;--row-border:#e0e0ea;--row-hover:#eaeaf2;--accent:#0066cc;--green:#008844;--red:#cc2233;--gold:#aa7700;--tab-bg:#dde;--header-bg:linear-gradient(180deg,#e8e8f0,#f0f0f4);--header-border:#d0d0e0;--scroll-track:#eee;--scroll-thumb:#bbb;--input-bg:#fff;--input-border:#aac}

        ::-webkit-scrollbar{width:4px}::-webkit-scrollbar-track{background:var(--scroll-track)}::-webkit-scrollbar-thumb{background:var(--scroll-thumb);border-radius:2px}
        .card{background:var(--card);border:1px solid var(--card-border);border-radius:12px;padding:16px;transition:border-color .2s}
        .card:hover{border-color:var(--card-hover)}
        .tab{background:none;border:none;cursor:pointer;font-family:inherit;font-size:13px;letter-spacing:2px;padding:8px 15px;border-radius:6px;color:var(--muted);transition:all .2s}
        .tab.on{background:var(--tab-bg);color:var(--accent)}
        .tab:hover:not(.on){color:var(--text)}
        .hrow{display:grid;grid-template-columns:130px 1fr 65px 68px 72px 88px 100px 90px 100px 90px 82px;gap:6px;align-items:center;padding:10px 14px;border-bottom:1px solid var(--row-border);transition:background .15s;font-size:13px}
        
        /* ── MEDIA QUERIES FOR RESPONSIVENESS ── */
        @media (max-width: 1200px) {
          .hrow { grid-template-columns: 100px 1fr 60px 60px 80px 80px 80px 80px; }
          .hrow > *:nth-child(n+9) { display: none; }
        }
        @media (max-width: 1024px) {
          .stat-grid { grid-template-columns: repeat(3, 1fr) !important; }
        }
        @media (max-width: 768px) {
          .dash-header { display: none !important; } /* Hide the internal dashboard header as TopNav covers it */
          .tabs-container { padding: 10px 20px !important; border-bottom: 1px solid var(--header-border); background: var(--header-bg); position: sticky; top: 48px; z-index: 40; }
          .stat-grid { grid-template-columns: repeat(2, 1fr) !important; padding: 0 16px !important; }
          .hrow { grid-template-columns: 80px 1fr 65px 65px !important; }
          .hrow > *:nth-child(n+5) { display: none; }
          .heat-tile { width: 100% !important; min-height: 140px !important; }
          .card-split { grid-template-columns: 1fr !important; }
          .content-container { padding: 10px 16px !important; }
        }
        @media (max-width: 480px) {
          .stat-grid { grid-template-columns: 1fr !important; }
          .heat-tile { width: 100% !important; }
          .hrow { grid-template-columns: 60px 1fr 55px !important; font-size: 11px; }
          .hrow > *:nth-child(4) { display: none; }
        }

        .hrow:hover{background:var(--row-hover)}
        .pill{padding:4px 10px;border-radius:10px;font-size:12px;letter-spacing:1px;cursor:pointer;border:1px solid transparent;font-family:inherit;transition:all .15s}
        .gl-pos{color:var(--green)}.gl-neg{color:var(--red)}
        .heat-tile{border-radius:10px;cursor:pointer;transition:transform .18s,box-shadow .18s;position:relative;overflow:hidden;display:flex;flex-direction:column;justify-content:space-between;padding:14px}
        .heat-tile:hover{transform:scale(1.04);z-index:10;box-shadow:0 8px 32px rgba(0,0,0,.4)}
        .api-input{background:var(--input-bg);border:1px solid var(--input-border);color:var(--accent);padding:10px 14px;border-radius:8px;font-family:inherit;font-size:15px;outline:none;width:100%;letter-spacing:2px}
        .api-input:focus{border-color:#4488ff;box-shadow:0 0 0 2px #4488ff22}
        .fetch-btn{background:#001a08;border:1px solid #00aa44;color:#00ff88;padding:10px 24px;border-radius:8px;cursor:pointer;font-family:inherit;font-size:14px;letter-spacing:2px;transition:all .2s}
        .fetch-btn:hover{background:#002a10;box-shadow:0 0 12px #00ff8833}
        .fetch-btn:disabled{opacity:.4;cursor:not-allowed}
        .terminal.light .fetch-btn{background:#e8f5e9;border-color:#4caf50;color:#2e7d32}
        .status-ok{color:var(--green)}.status-err{color:var(--red)}.status-load{color:var(--gold)}
        @keyframes spin{to{transform:rotate(360deg)}}
        .spinner{display:inline-block;width:12px;height:12px;border:2px solid #FFD70044;border-top-color:#FFD700;border-radius:50%;animation:spin .7s linear infinite}

        /* ── EMBEDDED PAGE OVERRIDES (.dash-embed) ── */
        .dash-embed{font-family:'DM Mono','Courier New',monospace !important;color:var(--text) !important;padding:0 !important}
        .dash-embed *{font-family:'DM Mono','Courier New',monospace !important}
        .dash-embed > div{padding:18px 0 !important;max-width:100% !important;margin:0 !important}
        .dash-embed .glass-panel{background:var(--card) !important;border:1px solid var(--card-border) !important;border-radius:12px !important;backdrop-filter:none !important;box-shadow:none !important}
        .dash-embed .glass-panel:hover{border-color:var(--card-hover) !important}
        .dash-embed h1{background:none !important;-webkit-background-clip:unset !important;background-clip:unset !important;-webkit-text-fill-color:unset !important;color:var(--accent) !important;font-family:'Bebas Neue',sans-serif !important;font-size:28px !important;letter-spacing:3px !important;text-transform:uppercase !important}
        .dash-embed h2,.dash-embed h3{color:var(--text) !important;font-size:15px !important;letter-spacing:2px !important;text-transform:uppercase !important}
        .dash-embed p{color:var(--muted) !important;font-size:12px !important;letter-spacing:1px !important}
        .dash-embed .text-gray-400,.dash-embed .text-gray-500,.dash-embed .text-zinc-400,.dash-embed .text-zinc-500,.dash-embed .text-zinc-600{color:var(--muted) !important}
        .dash-embed .text-foreground,.dash-embed .text-white,.dash-embed .text-gray-900{color:var(--text) !important}
        .dash-embed .text-emerald-400,.dash-embed .text-emerald-500,.dash-embed .text-green-700{color:var(--green) !important}
        .dash-embed .text-rose-400,.dash-embed .text-rose-500,.dash-embed .text-red-400{color:var(--red) !important}
        .dash-embed .text-blue-400,.dash-embed .text-blue-500,.dash-embed .text-blue-600{color:var(--accent) !important}
        .dash-embed .text-purple-400,.dash-embed .text-purple-500{color:#CC44FF !important}
        .dash-embed .text-amber-400,.dash-embed .text-amber-700{color:var(--gold) !important}
        .dash-embed table{color:var(--text) !important;font-size:13px !important}
        .dash-embed thead,.dash-embed .glass-table-header,.dash-embed [class*="bg-white/5"]{background:rgba(255,255,255,0.03) !important}
        .dash-embed tbody tr{border-bottom:1px solid var(--row-border) !important}
        .dash-embed tbody tr:hover{background:var(--row-hover) !important}
        .dash-embed th{color:var(--muted) !important;font-size:11px !important;letter-spacing:2px !important;text-transform:uppercase !important}
        .dash-embed td{color:var(--text) !important;font-size:13px !important}
        .dash-embed tfoot{background:rgba(255,255,255,0.02) !important;border-top:1px solid var(--card-border) !important}
        .dash-embed .divide-y > * + *{border-color:var(--row-border) !important}
        .dash-embed select,.dash-embed input[type="text"],.dash-embed input[type="number"],.dash-embed input[type="date"],.dash-embed textarea{background:var(--input-bg) !important;border:1px solid var(--card-border) !important;color:var(--text) !important;border-radius:8px !important;font-size:13px !important}
        .dash-embed button{font-family:'DM Mono','Courier New',monospace !important;letter-spacing:1px !important}
        .dash-embed [class*="border-white"]{border-color:var(--card-border) !important}
        .dash-embed .bg-clip-text{-webkit-text-fill-color:unset !important;background:none !important;color:var(--accent) !important}
        .dash-embed .recharts-cartesian-grid line{stroke:var(--card-border) !important}
        .dash-embed .recharts-text{fill:var(--muted) !important;font-family:'DM Mono',monospace !important;font-size:12px !important}
        .dash-embed .recharts-tooltip-wrapper .bg-white\/95,.dash-embed .recharts-tooltip-wrapper .dark\:bg-zinc-900,.dash-embed .recharts-tooltip-wrapper > div > div{background:var(--card) !important;border:1px solid var(--card-border) !important;color:var(--text) !important}
        .dash-embed .recharts-tooltip-wrapper span,.dash-embed .recharts-tooltip-wrapper p{color:var(--text) !important}
        .dash-embed [class*="from-"][class*="to-"]{background:var(--card) !important}
        .dash-embed .bg-blue-600,.dash-embed .bg-emerald-600,.dash-embed .bg-rose-600,.dash-embed .bg-emerald-500,.dash-embed .bg-rose-500{opacity:0.85}
        .dash-embed [class*="shadow-"]{box-shadow:none !important}
        .dash-embed [class*="rounded-2xl"]{border-radius:12px !important}
        .dash-embed [class*="rounded-xl"]{border-radius:10px !important}
        .dash-embed .animate-pulse{color:var(--accent) !important}
        
        @media (max-width: 1024px) {
          .stat-grid { grid-template-columns: repeat(3, 1fr) !important; }
        }
        @media (max-width: 768px) {
          .dash-header { flex-direction: column !important; gap: 12px !important; align-items: stretch !important; padding: 12px 16px !important; }
          .dash-header > div:nth-child(2) { text-align: left !important; display: flex; flex-direction: column; align-items: flex-start !important; }
          .clock-area { align-items: flex-start !important; }
          .stat-grid { grid-template-columns: repeat(2, 1fr) !important; padding: 0 16px !important; }
          .tabs-container { overflow-x: auto; white-space: nowrap; -webkit-overflow-scrolling: touch; padding: 8px 16px !important; gap: 8px !important; background: var(--header-bg); border-bottom: 1px solid var(--header-border); position: sticky; top: 0; z-index: 50; }
          .tab { font-size: 11px !important; padding: 6px 12px !important; border-radius: 4px !important; border: 1px solid var(--muted2) !important; }
          .tab.on { border-color: var(--accent) !important; }
          .hrow { grid-template-columns: 80px 1fr 60px 60px !important; font-size: 11px !important; }
          .hrow > *:nth-child(n+5) { display: none !important; }
          .heat-tile { width: 100% !important; min-height: 120px !important; }
          .card-split { grid-template-columns: 1fr !important; }
          .content-container { padding: 12px 16px !important; }
        }
        @media (max-width: 480px) {
          .stat-grid { grid-template-columns: 1fr !important; }
        }
      `}</style>

      {/* ── HEADER ── */}
      <div style={{ background: "var(--header-bg)", borderBottom: "1px solid var(--header-border)", padding: "18px 26px 0" }} className="dash-header-wrap">
        <div className="dash-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
          <div>
            <div style={{ fontSize: 11, letterSpacing: 4, color: "var(--muted2)", marginBottom: 4 }}>REAL-TIME PRICES · CIBC + RBC + TD · TFSA + OPEN · RRSP FULL</div>
            <div style={{ fontFamily: "'Bebas Neue',sans-serif", fontSize: 38, letterSpacing: 3, color: "var(--text)", lineHeight: 1 }}>LONG-TERM WEALTH ENGINE</div>
            <div style={{ fontSize: 11, color: "var(--muted2)", marginTop: 4, letterSpacing: 2 }}>20-YEAR HORIZON · 8% CAGR TARGET · USD/CAD {usdcad.toFixed(5)}</div>
          </div>
          <div className="clock-area" style={{ display: "flex", flexDirection: "column", alignItems: "flex-end" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ fontFamily: "'Bebas Neue',sans-serif", fontSize: 38, color: "var(--accent)", letterSpacing: 2, lineHeight: 1 }}>{clockStr}</div>
              <button
                onClick={() => setTheme(t => t === "dark" ? "light" : "dark")}
                style={{ padding: "6px 12px", borderRadius: 6, fontSize: 12, letterSpacing: 1, background: isLight ? "#dde" : "#1a1a44", border: `1px solid ${isLight ? "#bbc" : "#2a2a60"}`, color: isLight ? "#555" : "#aab", cursor: "pointer", fontFamily: "inherit" }}
              >
                {isLight ? "☾ DARK" : "☀ LIGHT"}
              </button>
              {session && (
                <button
                  onClick={() => signOut({ callbackUrl: "/login" })}
                  style={{ padding: "6px 12px", borderRadius: 6, fontSize: 12, letterSpacing: 1, background: "rgba(255, 68, 85, 0.1)", border: "1px solid rgba(255, 68, 85, 0.3)", color: "#FF4455", cursor: "pointer", fontFamily: "inherit" }}
                >
                  ⏻ LOGOUT
                </button>
              )}
            </div>
            <div style={{ fontSize: 12, color: "var(--muted)", letterSpacing: 1, marginBottom: 8 }}>{dateStr}</div>

            {/* Data source badge + refresh */}
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", alignItems: "center", flexWrap: "wrap" }}>
              <div style={{
                padding: "4px 12px", borderRadius: 12, fontSize: 11, letterSpacing: 1,
                background: isLight ? "#e8f5e9" : "#001a08",
                border: `1px solid ${isLight ? "#4caf50" : "#00aa44"}`,
                color: isLight ? "#2e7d32" : "#00ff88"
              }}>
                {isFetching ? <><span className="spinner" /> FETCHING...</> :
                  true
                    ? `✓ LIVE · ${lastUpdated?.toLocaleTimeString("en-CA", { hour12: false })} · ${okCount}/${TICKERS.length} ok${errCount > 0 ? ` · ${errCount} err` : ""}`
                    : "⚠ CSV SNAPSHOT · MAR 5 2026"
                }
              </div>
              <button
                className="fetch-btn"
                disabled={isFetching}
                onClick={() => refresh(true)}
                style={{ padding: "6px 16px", fontSize: 12 }}
              >
                {isFetching ? "FETCHING..." : "↻ FORCE REFRESH"}
              </button>
              <button
                onClick={() => setShowKeyInput(!showKeyInput)}
                style={{ padding: "6px 12px", borderRadius: 6, fontSize: 12, letterSpacing: 1, background: "rgba(0, 212, 255, 0.1)", border: "1px solid rgba(0, 212, 255, 0.3)", color: "#00D4FF", cursor: "pointer", fontFamily: "inherit" }}
              >
                ⚿ API KEY
              </button>
            </div>

            {showKeyInput && (
              <div style={{ marginTop: 8, display: "flex", gap: 6, width: "100%", justifyContent: "flex-end" }}>
                <input
                  type="text"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="Alpha Vantage key..."
                  className="api-input"
                  style={{ width: "220px", padding: "6px 10px", fontSize: 12 }}
                />
                <button
                  onClick={saveApiKey}
                  className="fetch-btn"
                  style={{ padding: "6px 12px", fontSize: 12 }}
                >
                  SAVE
                </button>
              </div>
            )}
            {lastUpdated && (
              <div style={{ fontSize: 13, color: "var(--muted2)", letterSpacing: 1, marginTop: 4, textAlign: "right" }}>
                CAD: {fmtCAD(1)} = USD: {(1 / usdcad).toFixed(4)}
              </div>
            )}
          </div>
        </div>




        {/* ACCOUNT + BROKER STRIP */}
        <div style={{ display: "flex", gap: 6, marginBottom: 10, flexWrap: "wrap" }}>
          {acctBreak.map(a => (
            <div key={a.name} onClick={() => { setTab("holdings"); setAcctFilter(a.name); }} style={{ padding: "6px 14px", background: ACCOUNT_BG[a.name], border: `1px solid ${a.color}44`, borderRadius: 8, cursor: "pointer" }}>
              <div style={{ fontFamily: "'Bebas Neue',sans-serif", fontSize: 24, color: a.color, lineHeight: 1 }}>{fmtCAD(a.value)}</div>
              <div style={{ fontSize: 13, color: a.color + "88", letterSpacing: 1 }}>{a.name} · {a.pct.toFixed(1)}%</div>
            </div>
          ))}
          <div style={{ width: 1, background: "var(--card-border)", margin: "0 4px" }} />
          {brokerBreak.map(b => (
            <div key={b.name} onClick={() => { setTab("holdings"); setBrokerFilter(b.name); }} style={{ padding: "6px 14px", background: (BROKER_COLORS[b.name] || "#333") + "11", border: `1px solid ${BROKER_COLORS[b.name] || "#555"}33`, borderRadius: 8, cursor: "pointer" }}>
              <div style={{ fontFamily: "'Bebas Neue',sans-serif", fontSize: 24, color: BROKER_COLORS[b.name] || "#999", lineHeight: 1 }}>{fmtCAD(b.value)}</div>
              <div style={{ fontSize: 13, color: (BROKER_COLORS[b.name] || "#888") + "88", letterSpacing: 1 }}>{b.name} · {b.pct.toFixed(1)}%</div>
            </div>
          ))}
        </div>

        {/* METRICS BAR */}
        <div className="stat-grid" style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 14, marginBottom: 20 }}>
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
              <div style={{ fontSize: 13, letterSpacing: 2, color: "var(--muted2)", marginBottom: 2 }}>{m.label}</div>
              <div style={{ fontFamily: "'Bebas Neue',sans-serif", fontSize: 26, color: m.color, letterSpacing: 1 }}>{m.value}</div>
            </div>
          ))}
        </div>
        <div className="tabs-container" style={{ display: "flex", gap: 2, marginTop: 10, flexWrap: "wrap" }}>
          {tabs.map(t => {
            const labels = {
              heatmap: "▦ HEATMAP", overview: "OVERVIEW", holdings: "HOLDINGS",
              tax: "🍁 TAX", geography: "GEOGRAPHY", dividends: "DIVIDENDS", projection: "PROJECTION",
              pnl: "₿ P&L", trades: "⟡ TRADES",
              quantmental: "⊕ QUANT-MENTAL", transactions: "☰ TRANSACTIONS"
            };
            return (
              <button key={t} className={`tab ${tab === t ? "on" : ""}`} onClick={() => setTab(t)}>
                {labels[t] || t.toUpperCase()}
              </button>
            );
          })}
        </div>
      </div>

      {/* ── CONTENT ── */}
      <div className="content-container" style={{ padding: "18px 26px" }}>

        {/* ════ HEATMAP */}
        {tab === "heatmap" && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, flexWrap: "wrap", gap: 8 }}>
              <div style={{ display: "flex", gap: 5, flexWrap: "wrap", alignItems: "center" }}>
                <span style={{ fontSize: 11, letterSpacing: 2, color: "#334", marginRight: 2 }}>SCALE:</span>
                {[
                  { bg: "#003d1a", border: "#00aa44", text: "#00ff88", label: "≥+8%" },
                  { bg: "#00291a", border: "#007733", text: "#00cc66", label: "+5–8%" },
                  { bg: "#001a12", border: "#115533", text: "#44cc88", label: "0–+5%" },
                  { bg: "#1a0808", border: "#663322", text: "#ff8877", label: "0–−2%" },
                  { bg: "#2a0808", border: "#882222", text: "#ff5544", label: "−2–−5%" },
                  { bg: "#3a0606", border: "#aa1111", text: "#ff2211", label: "<−5%" },
                ].map((c, i) => (
                  <div key={i} style={{ padding: "3px 8px", background: c.bg, border: `1px solid ${c.border}`, borderRadius: 4, fontSize: 12, color: c.text }}>{c.label}</div>
                ))}
              </div>
              <div style={{ display: "flex", gap: 5 }}>
                {[["value", "SIZE"], ["gl", "TOTAL G/L"], ["day", "TODAY"], ["ticker", "A–Z"]].map(([k, l]) => (
                  <button key={k} onClick={() => setHeatSort(k)} style={{ padding: "3px 9px", borderRadius: 8, fontSize: 11, letterSpacing: 1, cursor: "pointer", fontFamily: "inherit", background: heatSort === k ? "#1a1a44" : "transparent", border: `1px solid ${heatSort === k ? "#00D4FF" : "#222"}`, color: heatSort === k ? "#00D4FF" : "#445" }}>{l}</button>
                ))}
              </div>
            </div>

            <div style={{ fontSize: 11, color: "#2a2a44", letterSpacing: 1, marginBottom: 10 }}>
              SOURCE: {priceSource.toUpperCase()} · TILE SIZE ∝ MARKET VALUE · HOVER FOR DETAILS
              {isFetching && <span style={{ color: "#FFD700", marginLeft: 8 }}><span className="spinner" /> FETCHING LIVE PRICES...</span>}
            </div>

            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {heatTiles.map((h, idx) => {
                const c = h.heatColor;
                const w = Math.max(82, Math.min(430, (h.weight / 100) * 1380));
                const th = Math.max(82, w * 0.54);
                const isH = hoveredTicker === h.ticker;
                const isLoading = h.fetchStatus === "loading";
                const isErr = h.fetchStatus === "error";
                return (
                  <div key={`tile-${idx}-${h.ticker}-${h.account}-${h.broker}`}
                    className="heat-tile"
                    onMouseEnter={() => setHoveredTicker(h.ticker)}
                    onMouseLeave={() => setHoveredTicker(null)}
                    style={{ width: w, minHeight: th, background: c.bg, border: `1.5px solid ${isH ? c.text : isErr ? "#aa2200" : c.border}`, boxShadow: isH ? `0 0 20px ${c.text}44` : undefined, opacity: isLoading ? 0.6 : 1 }}
                  >
                    <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 2, background: `linear-gradient(90deg,transparent,${c.text}55,transparent)`, borderRadius: "10px 10px 0 0" }} />
                    {isLoading && <div style={{ position: "absolute", top: 6, right: 8 }}><span className="spinner" /></div>}
                    {isErr && <div style={{ position: "absolute", top: 5, right: 7, fontSize: 13, color: "#ff6644", letterSpacing: 1 }}>FALLBACK</div>}

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
                          <span style={{ fontSize: 11, color: h.dayChgPct >= 0 ? "#00cc88" : "#ff6655" }}>
                            {h.dayChgPct >= 0 ? "▲" : "▼"}{Math.abs(h.dayChgPct).toFixed(2)}%
                          </span>
                        )}
                      </div>

                      <div style={{ fontFamily: "'Bebas Neue',sans-serif", fontSize: Math.max(20, Math.min(38, w / 5)), color: c.text, letterSpacing: 1, lineHeight: 1, marginBottom: 3 }}>
                        {h.glPct !== null ? `${h.glPct >= 0 ? "+" : ""}${h.glPct.toFixed(2)}%` : "—"}
                      </div>

                      {w > 100 && (
                        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                          <span style={{ fontSize: 11, color: c.text + "88" }}>{fmtCAD(h.mktValueCAD)}</span>
                          {w > 150 && <span style={{ fontSize: 11, color: c.text + "55" }}>{h.weight.toFixed(1)}%</span>}
                        </div>
                      )}

                      {isH && w > 110 && (
                        <div style={{ marginTop: 7, paddingTop: 7, borderTop: `1px solid ${c.border}`, display: "flex", flexDirection: "column", gap: 2 }}>
                          <div style={{ fontSize: 11, color: c.text + "cc" }}>Qty {h.qty % 1 === 0 ? h.qty : h.qty.toFixed(2)} · Avg {h.currency === "USD" ? "$" : "C$"}{fmt(h.avgCost, 2)}</div>
                          {w > 160 && <div style={{ fontSize: 11, color: c.text + "99" }}>G/L {h.glAmtLocal >= 0 ? "+" : ""}{h.currency === "USD" ? "$" : "C$"}{fmt(Math.abs(h.glAmtLocal), 0)} · Yield {h.dividendYield}% · β{h.beta}</div>}
                          {w > 200 && h.high && <div style={{ fontSize: 11, color: c.text + "77" }}>H: {fmt(h.high, 2)} · L: {fmt(h.low, 2)} · {h.latestDay}</div>}
                          {w > 220 && h.volume && <div style={{ fontSize: 11, color: c.text + "55" }}>Vol: {h.volume?.toLocaleString()}</div>}
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
                    <div style={{ fontSize: 13, color: band.text + "77", letterSpacing: 1, marginBottom: 6 }}>{band.label}</div>
                    {tickers.length === 0 ? <div style={{ fontSize: 12, color: band.text + "33" }}>—</div> : tickers.map((h, j) => (
                      <div key={`band-${i}-${j}-${h.ticker}-${h.account}-${h.broker}`} style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                        <span style={{ fontSize: 13, color: band.text, fontWeight: 500 }}>{h.ticker}</span>
                        <span style={{ fontSize: 12, color: band.text + "99" }}>{h.glPct >= 0 ? "+" : ""}{h.glPct.toFixed(1)}%</span>
                      </div>
                    ))}
                    <div style={{ marginTop: 5, paddingTop: 5, borderTop: `1px solid ${band.border}`, fontSize: 13, color: band.text + "55" }}>
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
              <div style={{ fontSize: 11, letterSpacing: 3, color: "#335" }}>ALLOCATION BY HOLDING</div>
              <PieChart data={combinedWeights.map((h: any) => ({ name: h.ticker, value: h.weight, color: h.color }))} size={175} />
              <div style={{ width: "100%", maxHeight: 240, overflowY: "auto" }}>
                {combinedWeights.map((h: any, idx) => (
                  <div key={`ov-comb-${idx}-${h.ticker}`} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 5 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                      <div style={{ width: 6, height: 6, borderRadius: 2, background: h.heatColor.text }} />
                      <span style={{ fontSize: 12, color: "#aab" }}>{h.ticker}</span>
                    </div>
                    <span style={{ fontSize: 12, color: h.heatColor.text }}>{h.weight.toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <div className="card">
                <div style={{ fontSize: 11, letterSpacing: 3, color: "#335", marginBottom: 10 }}>BY ASSET CLASS</div>
                {assetClasses.sort((a, b) => b.value - a.value).map(a => (
                  <div key={a.name} style={{ marginBottom: 7 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                      <span style={{ fontSize: 12, color: "#aab" }}>{a.name}</span>
                      <div style={{ display: "flex", gap: 8, fontSize: 12 }}>
                        <span style={{ color: "#667" }}>{fmtCAD(a.value)}</span>
                        <span style={{ color: acClrs[a.name] || "#888" }}>{a.pct.toFixed(1)}%</span>
                      </div>
                    </div>
                    <Bar value={a.pct} max={100} color={acClrs[a.name] || "#888"} />
                  </div>
                ))}
              </div>
              <div className="card">
                <div style={{ fontSize: 11, letterSpacing: 3, color: "#335", marginBottom: 10 }}>BY ACCOUNT TYPE</div>
                {acctBreak.map(a => (
                  <div key={a.name} style={{ marginBottom: 8 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                      <span style={{ fontSize: 13, color: a.color }}>{a.name}</span>
                      <div style={{ display: "flex", gap: 8, fontSize: 12 }}>
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
              <div style={{ fontSize: 11, letterSpacing: 3, color: "#335", marginBottom: 10 }}>LIVE SNAPSHOT</div>
              {[
                { label: "DATA SOURCE", v: priceSource, c: true ? "#00FF88" : "#FFD700" },
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
                  <span style={{ fontSize: 11, letterSpacing: 1, color: "#445" }}>{s.label}</span>
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
            <div style={{ border: "1px solid var(--card-border)", borderRadius: 10, overflow: "auto" }}>
              <div className="hrow" style={{ background: "var(--bg2)", borderBottom: "1px solid var(--row-border)" }}>
                {["TICKER", "NAME", "ACCT", "BROKER", "QTY", "AVG COST", "LAST PRICE", "DAY CHG", "MKT VAL (CAD)", "TOTAL G/L", "AS OF"].map((h, i) => (
                  <div key={i} style={{ fontSize: 13, letterSpacing: 2, color: "var(--muted2)" }}>{h}</div>
                ))}
              </div>
              {filtered.map((h, i) => {
                const gp = h.glPct || 0;
                const statusColor = h.fetchStatus === "ok" ? "#00FF88" : h.fetchStatus === "error" ? "#FF4444" : h.fetchStatus === "loading" ? "#FFD700" : "#334";
                return (
                  <div key={`hold-${i}-${h.ticker}-${h.account}-${h.broker}`} className="hrow">
                    <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                      <div style={{ width: 4, height: 4, borderRadius: "50%", background: statusColor, flexShrink: 0 }} />
                      <span style={{ color: h.heatColor.text, fontWeight: 500, fontSize: 13 }}>{h.ticker}</span>
                    </div>
                    <div style={{ fontSize: 12, color: "var(--muted)", overflow: "hidden", whiteSpace: "nowrap", textOverflow: "ellipsis" }}>{h.name.split("(")[0].trim()}</div>
                    <ABadge a={h.account} />
                    <BBadge b={h.broker} />
                    <span style={{ color: "var(--muted)" }}>{h.qty % 1 === 0 ? h.qty : h.qty.toFixed(2)}</span>
                    <span style={{ color: "var(--muted2)", fontSize: 12 }}>{h.currency === "USD" ? "$" : "C$"}{fmt(h.avgCost, 2)}</span>
                    <span style={{ fontFamily: "'Bebas Neue',sans-serif", fontSize: 13, color: h.dayChgPct >= 0 ? "#00cc88" : "#ff6655", letterSpacing: .5 }}>
                      {h.currency === "USD" ? "$" : "C$"}{fmt(h.currPrice, 2)}
                    </span>
                    <span style={{ fontSize: 12, color: h.dayChgPct >= 0 ? "#00cc66" : "#ff5544" }}>
                      {h.dayChgPct !== 0 ? (h.dayChgPct >= 0 ? "▲" : "▼") + Math.abs(h.dayChgPct).toFixed(2) + "%" : "—"}
                    </span>
                    <span style={{ color: "var(--text)", fontWeight: 500, fontSize: 13 }}>{fmtCAD(h.mktValueCAD)}</span>
                    <span className={gp >= 0 ? "gl-pos" : "gl-neg"} style={{ fontSize: 13 }}>{gp >= 0 ? "+" : ""}{gp.toFixed(2)}%</span>
                    <span style={{ fontSize: 11, color: "var(--muted2)" }}>{h.latestDay}</span>
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
              <div style={{ fontSize: 11, letterSpacing: 3, color: "var(--muted2)", marginBottom: 10 }}>TAX PLACEMENT · RRSP FULL</div>
              {withWeights.sort((a, b) => b.mktValueCAD - a.mktValueCAD).map((h, i) => (
                <div key={`tax-${i}-${h.ticker}-${h.account}-${h.broker}`} style={{ padding: "9px 0", borderBottom: "1px solid var(--row-border)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
                      <span style={{ color: h.heatColor.text, fontSize: 12, fontWeight: 500 }}>{h.ticker}</span>
                      <ABadge a={h.account} /><BBadge b={h.broker} />
                    </div>
                    <div style={{ display: "flex", gap: 5 }}><span style={{ fontSize: 12, color: "var(--muted)" }}>{fmtCAD(h.mktValueCAD)}</span><TBadge r={h.taxRating} /></div>
                  </div>
                  <div style={{ fontSize: 12, color: "var(--muted)", lineHeight: 1.5 }}>{
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
                <div style={{ fontSize: 11, letterSpacing: 3, color: "var(--muted2)", marginBottom: 10 }}>PRIORITY ACTIONS (RRSP FULL)</div>
                {[
                  { pri: "HIGH", action: "Stop buying VOO in Open/TFSA", reason: "RRSP full — no WHT-exempt home for new USD ETFs. Route S&P 500 to VFV.TO in TFSA instead.", impact: "Prevent further WHT drag", color: "#FF3366" },
                  { pri: "HIGH", action: "Accept XEF.TO drag — no fix", reason: "EAFE in TFSA loses ~0.48%/yr permanently. RRSP full. Consider swap-based EAFE alternative.", impact: "~$300/yr unrecoverable", color: "#FF6B35" },
                  { pri: "MEDIUM", action: "VDY.TO → TFSA next Jan 1", reason: "~$7,000 new TFSA room each Jan 1. Prioritize shifting VDY.TO for full dividend sheltering.", impact: "+$1,200/yr effective", color: "#FFD700" },
                  { pri: "MEDIUM", action: "SLV exit timing — pair with losses", reason: "High unrealized gain. No annual drag. Harvest offsetting losses in same tax year at exit.", impact: "Reduce CG tax", color: "#FFAA44" },
                  { pri: "WATCH", action: "QQQM entry → TFSA only", reason: "US/Iran trigger fires → TFSA is the only sheltered option. 0.60% yield = minimal WHT.", impact: "100% gains tax-free", color: "#00FF88" },
                ].map(o => (
                  <div key={o.action} style={{ padding: "9px 0", borderBottom: "1px solid var(--row-border)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                      <span style={{ fontSize: 11, color: o.color, letterSpacing: 1 }}>{o.pri}</span>
                      <span style={{ fontSize: 11, color: "var(--green)" }}>{o.impact}</span>
                    </div>
                    <div style={{ fontSize: 13, color: "var(--text)", marginBottom: 2 }}>{o.action}</div>
                    <div style={{ fontSize: 12, color: "var(--muted)", lineHeight: 1.5 }}>{o.reason}</div>
                  </div>
                ))}
              </div>
              <div className="card">
                <div style={{ fontSize: 11, letterSpacing: 3, color: "var(--muted2)", marginBottom: 8 }}>ANNUAL WHT DRAG ESTIMATE</div>
                {[
                  { label: "XEF.TO (TFSA, EAFE WHT)", drag: withWeights.filter(h => h.ticker === "XEF.TO").reduce((s, h) => s + h.mktValueCAD, 0) * 0.0048, c: "var(--red)" },
                  { label: "VOO (TFSA, IRS WHT)", drag: withWeights.filter(h => h.ticker === "VOO").reduce((s, h) => s + h.mktValueCAD, 0) * 0.002, c: "var(--red)" },
                  { label: "VFV.TO (fund-level WHT)", drag: withWeights.filter(h => h.ticker === "VFV.TO").reduce((s, h) => s + h.mktValueCAD, 0) * 0.002, c: "var(--gold)" },
                ].map(d => (
                  <div key={d.label} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid var(--row-border)" }}>
                    <span style={{ fontSize: 12, color: "var(--muted)" }}>{d.label}</span>
                    <span style={{ fontSize: 12, color: d.c }}>-{fmtCAD(d.drag)}/yr</span>
                  </div>
                ))}
                {(() => { const t = withWeights.filter(h => h.ticker === "XEF.TO").reduce((s, h) => s + h.mktValueCAD, 0) * 0.0048 + withWeights.filter(h => h.ticker === "VOO").reduce((s, h) => s + h.mktValueCAD, 0) * 0.002 + withWeights.filter(h => h.ticker === "VFV.TO").reduce((s, h) => s + h.mktValueCAD, 0) * 0.002; return (<div style={{ display: "flex", justifyContent: "space-between", paddingTop: 7 }}><span style={{ fontSize: 12, color: "#aab" }}>TOTAL</span><span style={{ fontFamily: "'Bebas Neue',sans-serif", fontSize: 18, color: "#FF3366" }}>-{fmtCAD(t)}/yr</span></div>); })()}
              </div>
            </div>
          </div>
        )}

        {/* ════ GEOGRAPHY */}
        {tab === "geography" && (
          <div style={{ display: "grid", gridTemplateColumns: "220px 1fr", gap: 14 }}>
            <div className="card" style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
              <div style={{ fontSize: 11, letterSpacing: 3, color: "#335" }}>GEOGRAPHIC EXPOSURE</div>
              <PieChart data={geoData} size={185} />
              {geoData.map(g => (
                <div key={g.name} style={{ width: "100%" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                    <span style={{ fontSize: 12, color: "#aab" }}>{g.name}</span>
                    <span style={{ fontSize: 12, color: g.color }}>{g.value.toFixed(1)}%</span>
                  </div>
                  <Bar value={g.value} max={100} color={g.color} />
                </div>
              ))}
            </div>
            <div className="card">
              <div style={{ fontSize: 11, letterSpacing: 3, color: "#335", marginBottom: 12 }}>REGIONAL ANALYSIS</div>
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
                      <span style={{ fontSize: 12, color: "#667" }}>{r.pct.toFixed(1)}%</span>
                      <span style={{ padding: "1px 6px", borderRadius: 3, fontSize: 11, background: r.risk === "HIGH" ? "#FF336622" : r.risk === "MODERATE" ? "#FFD70022" : "#00FF8822", color: r.risk === "HIGH" ? "#FF3366" : r.risk === "MODERATE" ? "#FFD700" : "#00FF88" }}>{r.risk}</span>
                    </div>
                  </div>
                  <div style={{ fontSize: 12, color: "#667", lineHeight: 1.5 }}>{r.note}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ════ DIVIDENDS */}
        {tab === "dividends" && (
          <div className="card-split" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <div className="card">
              <div style={{ fontSize: 11, letterSpacing: 3, color: "var(--muted2)", marginBottom: 12 }}>DIVIDEND INCOME BY HOLDING (CAD)</div>
              {withWeights.filter(h => h.dividendYield > 0).sort((a, b) => b.annualDivCAD - a.annualDivCAD).map((h, i) => (
                <div key={i} style={{ padding: "8px 0", borderBottom: "1px solid var(--row-border)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                    <div style={{ display: "flex", gap: 5, alignItems: "center" }}>
                      <span style={{ color: h.color, fontSize: 11 }}>{h.ticker}</span>
                      <ABadge a={h.account} /><TBadge r={h.taxRating} />
                    </div>
                    <span style={{ fontSize: 11, color: "var(--text)" }}>{fmtCAD(h.annualDivCAD)}/yr</span>
                  </div>
                  <div style={{ fontSize: 11, color: "var(--muted)", marginBottom: 3 }}>Yield {h.dividendYield}% · {fmtCAD(h.annualDivCAD / 12)}/mo</div>
                  <Bar value={h.annualDivCAD} max={metrics.annualDiv} color={h.color} />
                </div>
              ))}
              <div style={{ display: "flex", justifyContent: "space-between", paddingTop: 10 }}>
                <span style={{ fontSize: 12, color: "var(--muted)", letterSpacing: 1 }}>TOTAL ANNUAL</span>
                <span style={{ fontFamily: "'Bebas Neue',sans-serif", fontSize: 22, color: "#00FF88" }}>{fmtCAD(metrics.annualDiv)}</span>
              </div>
            </div>
            <div className="card">
              <div style={{ fontSize: 11, letterSpacing: 3, color: "var(--muted2)", marginBottom: 12 }}>DRIP PROJECTIONS</div>
              {[1, 3, 5, 10, 15, 20].map((yr, index) => {
                const proj = totalCAD * Math.pow(1 + metrics.wCAGR / 100, yr);
                const div = proj * (metrics.wYield / 100);
                return (
                  <div key={`div-${index}-${yr}`} style={{ display: "flex", justifyContent: "space-between", padding: "7px 0", borderBottom: "1px solid var(--row-border)" }}>
                    <span style={{ fontSize: 13, color: "var(--muted)" }}>YEAR {yr}</span>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontFamily: "'Bebas Neue',sans-serif", fontSize: 18, color: "var(--green)" }}>{fmtCAD(div)}/yr</div>
                      <div style={{ fontSize: 11, color: "var(--muted2)" }}>Portfolio: {fmtCAD(proj)}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ════ PROJECTION */}
        {tab === "projection" && (
          <div className="card-split" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <div className="card">
              <div style={{ fontSize: 11, letterSpacing: 3, color: "var(--muted2)", marginBottom: 14 }}>20-YEAR WEALTH SCENARIOS (CAD)</div>
              {[
                { label: "BEAR CASE", cagr: 5.0, color: "#FF3366" },
                { label: "BASE (YOUR TARGET)", cagr: 8.0, color: "#FFD700" },
                { label: "PORTFOLIO WEIGHTED", cagr: metrics.wCAGR, color: "#00D4FF" },
                { label: "BULL CASE", cagr: 12.0, color: "#00FF88" },
              ].map(s => {
                const proj = totalCAD * Math.pow(1 + s.cagr / 100, 20);
                return (
                  <div key={s.label} style={{ padding: "11px 0", borderBottom: "1px solid var(--row-border)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                      <span style={{ fontSize: 12, color: s.color, letterSpacing: 1 }}>{s.label}</span>
                      <span style={{ fontSize: 12, color: "var(--muted)" }}>CAGR {s.cagr.toFixed(1)}%</span>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 5 }}>
                      <div style={{ fontFamily: "'Bebas Neue',sans-serif", fontSize: 28, color: s.color }}>{fmtCAD(proj)}</div>
                      <span style={{ fontSize: 13, color: "var(--muted2)" }}>{(proj / totalCAD).toFixed(1)}x</span>
                    </div>
                    <Bar value={proj} max={totalCAD * Math.pow(1.12, 20)} color={s.color} />
                  </div>
                );
              })}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <div className="card">
                <div style={{ fontSize: 11, letterSpacing: 3, color: "#335", marginBottom: 10 }}>MONTE CARLO · 10,000 SIMS (CAD)</div>
                {[
                  { pct: "10th percentile", val: totalCAD * Math.pow(1.04, 20), color: "#FF3366" },
                  { pct: "25th percentile", val: totalCAD * Math.pow(1.065, 20), color: "#FF8855" },
                  { pct: "50th percentile", val: totalCAD * Math.pow(1.085, 20), color: "#FFD700" },
                  { pct: "75th percentile", val: totalCAD * Math.pow(1.11, 20), color: "#00FF88" },
                  { pct: "90th percentile", val: totalCAD * Math.pow(1.135, 20), color: "#00D4FF" },
                ].map(s => (
                  <div key={s.pct} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid #0f0f20" }}>
                    <span style={{ fontSize: 12, color: "#556" }}>{s.pct}</span>
                    <span style={{ fontSize: 12, color: s.color }}>{fmtCAD(s.val)}</span>
                  </div>
                ))}
                <div style={{ marginTop: 8, fontSize: 11, color: "#223", lineHeight: 1.5 }}>Assumes annual rebalancing + DRIP. Excludes tax, inflation, FX. All values CAD.</div>
              </div>
              <div className="card">
                <div style={{ fontSize: 11, letterSpacing: 3, color: "#335", marginBottom: 10 }}>FACTOR PROFILE</div>
                {withWeights.sort((a, b) => b.mktValueCAD - a.mktValueCAD).map((h, i) => (
                  <div key={`fact-${i}-${h.ticker}-${h.account}-${h.broker}`} style={{ padding: "6px 0", borderBottom: "1px solid #0f0f22" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 2 }}>
                      <div style={{ display: "flex", gap: 5 }}><span style={{ color: h.color, fontSize: 13 }}>{h.ticker}</span><ABadge a={h.account} /></div>
                      <div style={{ display: "flex", gap: 7, fontSize: 12, color: "#556" }}><span>β{h.beta}</span><span>{h.expectedCAGR}%</span><span>S{h.sharpe}</span></div>
                    </div>
                    <div style={{ fontSize: 11, color: "#334" }}>{h.weight.toFixed(1)}% · {fmtCAD(h.mktValueCAD)}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ════ PAGE TABS (embedded from routes) */}
        {tab === "pnl" && <div className="dash-embed"><PnLPage /></div>}
        {tab === "trades" && <div className="dash-embed"><TradeAnalysisPage /></div>}
        {tab === "quantmental" && <div className="dash-embed"><QuantmentalPage /></div>}
        {tab === "transactions" && <div className="dash-embed"><TransactionsPage /></div>}
      </div>

      <div style={{ borderTop: "1px solid var(--row-border)", padding: "10px 26px", display: "flex", justifyContent: "space-between", fontSize: 13, color: "var(--muted2)", letterSpacing: 1 }}>
        <span>PORTFOLIO TERMINAL · CIBC + RBC + TD · v6.0 · ALPHA VANTAGE</span>
        <span>NOT FINANCIAL ADVICE · PRICES FROM ALPHA VANTAGE OR CSV SNAPSHOT</span>
        <span>USD/CAD {usdcad.toFixed(5)} · {priceSource}</span>
      </div>
    </div>
  );
}
