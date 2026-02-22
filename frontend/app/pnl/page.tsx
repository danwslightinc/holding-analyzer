"use client";

import { usePortfolio } from "@/lib/PortfolioContext";
import { useEffect, useState, useCallback } from "react";
import { API_BASE_URL } from "@/lib/api";
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, ReferenceLine, Cell
} from "recharts";
import { TrendingUp, TrendingDown, DollarSign, Activity, Archive, ChevronUp, ChevronDown } from "lucide-react";

interface RealizedRow {
    symbol: string;
    currency: string;
    pnl_amount: number;
    cost_basis_sold: number;
    pnl_pct: number | null;
    broker: string;
    account_type: string;
    source: string;
}

type SortDir = "asc" | "desc";
interface SortCfg { key: string; dir: SortDir }

const fmt = (n: number) =>
    `${n < 0 ? "-" : "+"}$${Math.abs(n).toLocaleString("en-CA", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;

/** Official bank brand colors extracted from live websites */
const BROKER_COLORS: Record<string, { bg: string; text: string; border: string }> = {
    TD: { bg: "rgba(0,138,0,0.15)", text: "#00b300", border: "rgba(0,138,0,0.40)" },  // td.com #008A00
    CIBC: { bg: "rgba(196,31,62,0.15)", text: "#e84464", border: "rgba(196,31,62,0.40)" }, // cibc.com #C41F3E
    RBC: { bg: "rgba(0,106,195,0.15)", text: "#3da5ff", border: "rgba(0,106,195,0.40)" }, // rbc.com #006AC3
    Manual: { bg: "rgba(255,255,255,0.08)", text: "#a1a1aa", border: "rgba(255,255,255,0.15)" },
};
const DEFAULT_BROKER_COLOR = { bg: "rgba(255,255,255,0.08)", text: "#a1a1aa", border: "rgba(255,255,255,0.15)" };

/** Account-type color scheme — each account type has its own look */
const ACCOUNT_COLORS: Record<string, { bg: string; text: string; border: string }> = {
    TFSA: { bg: "rgba(20,184,166,0.15)", text: "#2dd4bf", border: "rgba(20,184,166,0.40)" }, // teal  — tax-free growth
    RRSP: { bg: "rgba(139,92,246,0.15)", text: "#a78bfa", border: "rgba(139,92,246,0.40)" }, // purple — retirement
    Open: { bg: "rgba(249,115,22,0.15)", text: "#fb923c", border: "rgba(249,115,22,0.40)" }, // orange — taxable/open
    Manual: { bg: "rgba(255,255,255,0.08)", text: "#a1a1aa", border: "rgba(255,255,255,0.15)" },
};
const DEFAULT_ACCOUNT_COLOR = { bg: "rgba(255,255,255,0.08)", text: "#a1a1aa", border: "rgba(255,255,255,0.15)" };

/** Clickable sort header */
function SortTh({ label, sortKey, cfg, onSort, align = "right" }: {
    label: string; sortKey: string;
    cfg: SortCfg; onSort: (k: string) => void; align?: "left" | "right";
}) {
    const active = cfg.key === sortKey;
    return (
        <th
            className={`p-4 cursor-pointer select-none hover:bg-white/10 transition-colors group whitespace-nowrap ${align === "right" ? "text-right" : "text-left"}`}
            onClick={() => onSort(sortKey)}
        >
            <span className={`inline-flex items-center gap-1 ${align === "right" ? "justify-end" : "justify-start"}`}>
                {label}
                <span className="w-4">
                    {active
                        ? (cfg.dir === "asc" ? <ChevronUp size={13} /> : <ChevronDown size={13} />)
                        : <ChevronUp size={13} className="opacity-0 group-hover:opacity-40 transition-opacity" />}
                </span>
            </span>
        </th>
    );
}

/** Generic sort comparator */
function sortRows<T>(rows: T[], cfg: SortCfg, getValue: (row: T, key: string) => any): T[] {
    return [...rows].sort((a, b) => {
        const av = getValue(a, cfg.key);
        const bv = getValue(b, cfg.key);
        if (av == null) return 1;
        if (bv == null) return -1;
        const cmp = typeof av === "string" ? av.localeCompare(bv) : av - bv;
        return cfg.dir === "asc" ? cmp : -cmp;
    });
}

export default function PnLPage() {
    const { data, loading, symbolAccounts, error } = usePortfolio();
    const [realized, setRealized] = useState<RealizedRow[]>([]);
    const [realizedLoading, setRealizedLoading] = useState(true);
    const [selectedBroker, setSelectedBroker] = useState<string>('All');
    const [selectedAccountType, setSelectedAccountType] = useState<string>('All');

    // Sort state — unrealized table
    const [uSort, setUSort] = useState<SortCfg>({ key: "pnl", dir: "desc" });
    // Sort state — realized table
    const [rSort, setRSort] = useState<SortCfg>({ key: "pnl_amount", dir: "desc" });

    const handleUSort = useCallback((k: string) => setUSort(prev =>
        prev.key === k ? { key: k, dir: prev.dir === "desc" ? "asc" : "desc" } : { key: k, dir: "desc" }
    ), []);
    const handleRSort = useCallback((k: string) => setRSort(prev =>
        prev.key === k ? { key: k, dir: prev.dir === "desc" ? "asc" : "desc" } : { key: k, dir: "desc" }
    ), []);

    useEffect(() => {
        setRealizedLoading(true);
        fetch(`${API_BASE_URL}/api/realized-pnl`)
            .then(r => r.json())
            .then(d => setRealized(d))
            .catch(() => { })
            .finally(() => setRealizedLoading(false));
    }, []);

    if (loading) return (
        <div className="p-10 text-center animate-pulse text-zinc-400 text-lg">Loading P&L data...</div>
    );
    if (error || !data) return (
        <div className="p-10 text-center text-rose-400">Failed to load data. Ensure backend is running.</div>
    );

    const usdCad = data.summary?.usd_cad_rate ?? 1.36;
    const brokers = ['All', ...Array.from(new Set((data.holdings as any[]).map(h => h.Broker).filter(Boolean)))];
    const accountTypes = ['All', ...Array.from(new Set((data.holdings as any[]).map(h => h.Account_Type).filter(Boolean)))];

    const filteredHoldings = (data.holdings as any[]).filter((h: any) => {
        const bMatch = selectedBroker === 'All' || h.Broker === selectedBroker;
        const aMatch = selectedAccountType === 'All' || h.Account_Type === selectedAccountType;
        return bMatch && aMatch;
    });

    const groupedMap: Record<string, any> = {};
    filteredHoldings.forEach((h: any) => {
        const sym = h.Symbol;
        if (!groupedMap[sym]) {
            groupedMap[sym] = { ...h };
        } else {
            const prev = groupedMap[sym];
            const prevCost = (prev.Market_Value - prev.PnL);
            const currCost = (h.Market_Value - h.PnL);
            prev.Quantity += h.Quantity;
            prev.Market_Value += h.Market_Value;
            prev.PnL += h.PnL;
            prev['Purchase Price'] = (prevCost + currCost) / prev.Quantity;
        }
    });

    // ---- Build unrealized rows ----
    const rawRows = Object.values(groupedMap).map((h: any) => {
        const costBasis = h.Market_Value - h.PnL;
        const pnl = h.PnL;
        const pnlPct = costBasis > 0 ? (pnl / costBasis) * 100 : 0;
        const currency = h.Currency ?? "USD";
        return {
            symbol: h.Symbol,
            currency,
            currencyPrefix: currency === "USD" ? "US$" : "$",
            qty: h.Quantity ?? 0,
            avgCost: h["Purchase Price"] ?? 0,
            currentPrice: h["Current Price"] ?? 0,
            marketValue: h.Market_Value ?? 0,
            costBasis,
            pnl,
            pnlPct,
        };
    });

    const rows = sortRows(rawRows, uSort, (r, k) => {
        const m: Record<string, any> = {
            symbol: r.symbol,
            qty: r.qty,
            avgCost: r.avgCost,
            currentPrice: r.currentPrice,
            costBasis: r.costBasis,
            marketValue: r.marketValue,
            pnl: r.pnl,
            pnlPct: r.pnlPct,
        };
        return m[k];
    });

    const winners = rawRows.filter(r => r.pnl >= 0);
    const losers = rawRows.filter(r => r.pnl < 0);
    const totalUnrealizedPnL = rawRows.reduce((s, r) => s + r.pnl, 0);
    const totalCostBasis = rawRows.reduce((s, r) => s + r.costBasis, 0);
    const totalPct = totalCostBasis > 0 ? (totalUnrealizedPnL / totalCostBasis) * 100 : 0;
    const chartData = [...rawRows].sort((a, b) => b.pnl - a.pnl).map(r => ({ name: r.symbol, pnl: parseFloat(r.pnl.toFixed(0)) }));

    // ---- Realized rows ----
    const filteredRealized = realized.filter((r: any) => {
        const bMatch = selectedBroker === 'All' || r.broker === selectedBroker;
        const aMatch = selectedAccountType === 'All' || r.account_type === selectedAccountType;
        return bMatch && aMatch;
    });

    const realizedSorted = sortRows(filteredRealized, rSort, (r, k) => {
        const inCad = r.currency === "USD" ? r.pnl_amount * usdCad : r.pnl_amount;
        const m: Record<string, any> = {
            symbol: r.symbol,
            broker: r.broker,
            account_type: r.account_type,
            cost_basis_sold: r.cost_basis_sold,
            pnl_amount: r.pnl_amount,
            pnl_pct: r.pnl_pct,
            pnl_cad: inCad,
        };
        return m[k];
    });

    const totalRealizedCAD = filteredRealized.reduce((sum, r) => {
        return sum + (r.currency === "USD" ? r.pnl_amount * usdCad : r.pnl_amount);
    }, 0);

    return (
        <div className="p-8 max-w-[1400px] mx-auto space-y-8">

            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-blue-500">
                    Profit & Loss
                </h1>
                <p className="text-zinc-400 mt-1">Unrealized and realized gains/losses across your portfolio</p>
            </div>

            {/* Filters */}
            <div className="flex flex-wrap items-center gap-6">
                <div className="flex flex-col gap-1.5">
                    <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider ml-1">Bank</label>
                    <select
                        value={selectedBroker}
                        onChange={(e) => setSelectedBroker(e.target.value)}
                        className="bg-white/5 border border-white/10 text-zinc-300 text-xs rounded-xl block w-full p-2.5 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all hover:bg-white/10"
                    >
                        {brokers.map((b: any) => (
                            <option key={b} value={b} className="bg-zinc-900">{b === 'All' ? 'All Banks' : b}</option>
                        ))}
                    </select>
                </div>

                <div className="flex flex-col gap-1.5">
                    <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider ml-1">Account Type</label>
                    <select
                        value={selectedAccountType}
                        onChange={(e) => setSelectedAccountType(e.target.value)}
                        className="bg-white/5 border border-white/10 text-zinc-300 text-xs rounded-xl block w-full p-2.5 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all hover:bg-white/10"
                    >
                        {accountTypes.map((at: any) => (
                            <option key={at} value={at} className="bg-zinc-900">{at === 'All' ? 'All Accounts' : at}</option>
                        ))}
                    </select>
                </div>

                <button
                    onClick={() => { setSelectedBroker('All'); setSelectedAccountType('All'); }}
                    className="self-end mb-1 px-4 py-2 text-xs font-medium text-zinc-500 hover:text-white transition-colors"
                >
                    Reset Filters
                </button>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                    { label: "Unrealized P&L", value: fmt(totalUnrealizedPnL), sub: `${totalPct >= 0 ? "+" : ""}${totalPct.toFixed(2)}% | CAD`, icon: Activity, color: totalUnrealizedPnL >= 0 ? "text-emerald-400" : "text-rose-400", bg: totalUnrealizedPnL >= 0 ? "from-emerald-500/10 to-emerald-500/5 border-emerald-500/20" : "from-rose-500/10 to-rose-500/5 border-rose-500/20" },
                    { label: "Realized P&L (Closed)", value: fmt(totalRealizedCAD), sub: "CAD equiv. from broker history", icon: Archive, color: totalRealizedCAD >= 0 ? "text-emerald-400" : "text-rose-400", bg: totalRealizedCAD >= 0 ? "from-emerald-500/10 to-emerald-500/5 border-emerald-500/20" : "from-rose-500/10 to-rose-500/5 border-rose-500/20" },
                    { label: "Open Winners", value: `${winners.length} positions`, sub: `+$${winners.reduce((s, r) => s + r.pnl, 0).toLocaleString("en-CA", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`, icon: TrendingUp, color: "text-emerald-400", bg: "from-emerald-500/10 to-emerald-500/5 border-emerald-500/20" },
                    { label: "Open Losers", value: `${losers.length} positions`, sub: `-$${Math.abs(losers.reduce((s, r) => s + r.pnl, 0)).toLocaleString("en-CA", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`, icon: TrendingDown, color: "text-rose-400", bg: "from-rose-500/10 to-rose-500/5 border-rose-500/20" },
                ].map((card, i) => (
                    <div key={i} className={`glass-panel rounded-2xl p-5 bg-gradient-to-br ${card.bg} border`}>
                        <div className="flex items-center justify-between mb-3">
                            <span className="text-xs text-zinc-400 font-medium uppercase tracking-wider">{card.label}</span>
                            <card.icon className={`w-4 h-4 ${card.color}`} />
                        </div>
                        <div className={`text-2xl font-bold ${card.color}`}>{card.value}</div>
                        <div className="text-xs text-zinc-500 mt-1">{card.sub}</div>
                    </div>
                ))}
            </div>

            {/* Bar Chart */}
            <div className="glass-panel rounded-2xl p-6">
                <h2 className="text-lg font-bold mb-1">Unrealized P&L by Open Position (CAD)</h2>
                <p className="text-xs text-zinc-500 mb-4">Sorted best to worst. Green = profit, red = loss</p>
                <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={chartData} margin={{ top: 8, right: 16, left: 16, bottom: 40 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                        <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#9ca3af" }} angle={-35} textAnchor="end" interval={0} />
                        <YAxis tick={{ fontSize: 11, fill: "#9ca3af" }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                        <Tooltip
                            formatter={(v: number | undefined) => [`$${(v ?? 0).toLocaleString("en-CA")} CAD`, "Unrealized PnL"]}
                            contentStyle={{ background: "#1a1a2e", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "12px", color: "#e2e8f0" }}
                        />
                        <ReferenceLine y={0} stroke="rgba(255,255,255,0.2)" strokeWidth={1} />
                        <Bar dataKey="pnl" radius={[4, 4, 0, 0]}>
                            {chartData.map((entry, idx) => (
                                <Cell key={idx} fill={entry.pnl >= 0 ? "#10b981" : "#f43f5e"} />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </div>

            {/* Unrealized Table */}
            <div className="glass-panel rounded-2xl overflow-hidden">
                <div className="p-6 border-b border-white/10">
                    <h2 className="text-lg font-bold">Open Positions — Unrealized P&L</h2>
                    <p className="text-xs text-zinc-500 mt-1">Click any column header to sort. Values in CAD.</p>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                        <thead className="bg-white/5 text-zinc-400 text-xs uppercase tracking-wider">
                            <tr>
                                <SortTh label="Symbol" sortKey="symbol" cfg={uSort} onSort={handleUSort} align="left" />
                                <th className="p-4 text-left text-zinc-400 text-xs uppercase tracking-wider whitespace-nowrap">Broker / Account</th>
                                <SortTh label="Qty" sortKey="qty" cfg={uSort} onSort={handleUSort} />
                                <SortTh label="Avg Cost" sortKey="avgCost" cfg={uSort} onSort={handleUSort} />
                                <SortTh label="Current Price" sortKey="currentPrice" cfg={uSort} onSort={handleUSort} />
                                <SortTh label="Cost Basis" sortKey="costBasis" cfg={uSort} onSort={handleUSort} />
                                <SortTh label="Market Value" sortKey="marketValue" cfg={uSort} onSort={handleUSort} />
                                <SortTh label="Unrealized P&L" sortKey="pnl" cfg={uSort} onSort={handleUSort} />
                                <SortTh label="Return %" sortKey="pnlPct" cfg={uSort} onSort={handleUSort} />
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {rows.map((r) => {
                                const isWin = r.pnl >= 0;
                                const accounts = symbolAccounts[r.symbol] ?? [];
                                return (
                                    <tr key={r.symbol} className="hover:bg-white/5 transition-colors">
                                        <td className="p-4">
                                            <div className="font-bold text-blue-400">{r.symbol}</div>
                                            <div className="text-xs text-zinc-500">{r.currency}</div>
                                        </td>
                                        {/* Broker / Account badges */}
                                        <td className="p-4">
                                            <div className="flex flex-wrap gap-1">
                                                {accounts.length > 0 ? accounts
                                                    .filter(a => (selectedBroker === 'All' || a.broker === selectedBroker) && (selectedAccountType === 'All' || a.account_type === selectedAccountType))
                                                    .map((a, ai) => {
                                                        const bc = BROKER_COLORS[a.broker] ?? DEFAULT_BROKER_COLOR;
                                                        const ac = ACCOUNT_COLORS[a.account_type] ?? DEFAULT_ACCOUNT_COLOR;
                                                        return (
                                                            <span key={ai} className="inline-flex gap-0.5">
                                                                <span style={{ background: bc.bg, color: bc.text, border: `1px solid ${bc.border}` }}
                                                                    className="px-1.5 py-0.5 rounded-l-md text-xs font-bold">
                                                                    {a.broker}
                                                                </span>
                                                                <span style={{ background: ac.bg, color: ac.text, border: `1px solid ${ac.border}` }}
                                                                    className="px-1.5 py-0.5 rounded-r-md text-xs font-semibold">
                                                                    {a.account_type}
                                                                </span>
                                                            </span>
                                                        );
                                                    }) : <span className="text-zinc-600 text-xs">—</span>}
                                            </div>
                                        </td>
                                        <td className="p-4 text-right text-zinc-400">{r.qty.toLocaleString()}</td>
                                        <td className="p-4 text-right text-zinc-400">{r.currencyPrefix}{r.avgCost.toFixed(2)}</td>
                                        <td className="p-4 text-right text-zinc-400">{r.currencyPrefix}{r.currentPrice.toFixed(2)}</td>
                                        <td className="p-4 text-right text-zinc-300">${r.costBasis.toLocaleString("en-CA", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</td>
                                        <td className="p-4 text-right text-zinc-300">${r.marketValue.toLocaleString("en-CA", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</td>
                                        <td className={`p-4 text-right font-semibold ${isWin ? "text-emerald-400" : "text-rose-400"}`}>{fmt(r.pnl)}</td>
                                        <td className={`p-4 text-right font-semibold ${isWin ? "text-emerald-400" : "text-rose-400"}`}>
                                            <span className="flex items-center justify-end gap-1">
                                                {isWin ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
                                                {r.pnlPct.toFixed(2)}%
                                            </span>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                        <tfoot className="bg-white/5 font-bold border-t border-white/10">
                            <tr>
                                <td className="p-4 text-zinc-300" colSpan={5}>Portfolio Total</td>
                                <td className="p-4 text-right text-zinc-300">${totalCostBasis.toLocaleString("en-CA", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</td>
                                <td className="p-4 text-right text-zinc-300">${(totalCostBasis + totalUnrealizedPnL).toLocaleString("en-CA", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</td>
                                <td className={`p-4 text-right ${totalUnrealizedPnL >= 0 ? "text-emerald-400" : "text-rose-400"}`}>{fmt(totalUnrealizedPnL)}</td>
                                <td className={`p-4 text-right ${totalUnrealizedPnL >= 0 ? "text-emerald-400" : "text-rose-400"}`}>{totalPct >= 0 ? "+" : ""}{totalPct.toFixed(2)}%</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>

            {/* Realized Table */}
            <div className="glass-panel rounded-2xl overflow-hidden">
                <div className="p-6 border-b border-white/10 flex items-center justify-between">
                    <div>
                        <h2 className="text-lg font-bold">Closed Trades — Realized P&L</h2>
                        <p className="text-xs text-zinc-500 mt-1">FIFO cost-basis from broker exports — click any column header to sort</p>
                    </div>
                    <span className={`text-xl font-bold ${totalRealizedCAD >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                        {fmt(totalRealizedCAD)} CAD
                    </span>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                        <thead className="bg-white/5 text-zinc-400 text-xs uppercase tracking-wider">
                            <tr>
                                <SortTh label="Symbol" sortKey="symbol" cfg={rSort} onSort={handleRSort} align="left" />
                                <SortTh label="Broker" sortKey="broker" cfg={rSort} onSort={handleRSort} align="left" />
                                <SortTh label="Account" sortKey="account_type" cfg={rSort} onSort={handleRSort} align="left" />
                                <SortTh label="Cost Basis" sortKey="cost_basis_sold" cfg={rSort} onSort={handleRSort} />
                                <SortTh label="P&L (Native)" sortKey="pnl_amount" cfg={rSort} onSort={handleRSort} />
                                <SortTh label="Return %" sortKey="pnl_pct" cfg={rSort} onSort={handleRSort} />
                                <SortTh label="P&L (CAD)" sortKey="pnl_cad" cfg={rSort} onSort={handleRSort} />
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {realizedLoading ? (
                                <tr><td className="p-6 text-zinc-500 animate-pulse" colSpan={7}>Loading realized data...</td></tr>
                            ) : realizedSorted.map((r, i) => {
                                const isWin = r.pnl_amount >= 0;
                                const inCad = r.currency === "USD" ? r.pnl_amount * usdCad : r.pnl_amount;
                                const cbDisplay = r.cost_basis_sold > 0
                                    ? `${r.currency === "USD" ? "US$" : "$"}${r.cost_basis_sold.toLocaleString("en-CA", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
                                    : "—";
                                return (
                                    <tr key={i} className="hover:bg-white/5 transition-colors">
                                        <td className="p-4 font-bold text-blue-400">{r.symbol}</td>
                                        <td className="p-4">
                                            {(() => {
                                                const c = BROKER_COLORS[r.broker] ?? DEFAULT_BROKER_COLOR;
                                                return (
                                                    <span style={{ background: c.bg, color: c.text, border: `1px solid ${c.border}` }}
                                                        className="px-2.5 py-0.5 rounded-lg text-xs font-bold tracking-wide">
                                                        {r.broker}
                                                    </span>
                                                );
                                            })()}
                                        </td>
                                        <td className="p-4">
                                            {(() => {
                                                const c = ACCOUNT_COLORS[r.account_type] ?? DEFAULT_ACCOUNT_COLOR;
                                                return (
                                                    <span style={{ background: c.bg, color: c.text, border: `1px solid ${c.border}` }}
                                                        className="px-2.5 py-0.5 rounded-lg text-xs font-semibold">
                                                        {r.account_type}
                                                    </span>
                                                );
                                            })()}
                                        </td>
                                        <td className="p-4 text-right text-zinc-400">{cbDisplay}</td>
                                        <td className={`p-4 text-right font-semibold ${isWin ? "text-emerald-400" : "text-rose-400"}`}>
                                            {r.currency === "USD" ? "US$" : "$"}{r.pnl_amount >= 0 ? "+" : ""}{r.pnl_amount.toFixed(2)}
                                        </td>
                                        <td className={`p-4 text-right font-semibold ${isWin ? "text-emerald-400" : "text-rose-400"}`}>
                                            {r.pnl_pct !== null
                                                ? <span className="flex items-center justify-end gap-1">
                                                    {isWin ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
                                                    {r.pnl_pct >= 0 ? "+" : ""}{r.pnl_pct.toFixed(2)}%
                                                </span>
                                                : "—"}
                                        </td>
                                        <td className={`p-4 text-right font-semibold ${isWin ? "text-emerald-400" : "text-rose-400"}`}>{fmt(inCad)}</td>
                                    </tr>
                                );
                            })}
                        </tbody>
                        <tfoot className="bg-white/5 font-bold border-t border-white/10">
                            <tr>
                                <td className="p-4 text-zinc-300" colSpan={6}>Total Realized (CAD equiv.)</td>
                                <td className={`p-4 text-right ${totalRealizedCAD >= 0 ? "text-emerald-400" : "text-rose-400"}`}>{fmt(totalRealizedCAD)}</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>
        </div>
    );
}
