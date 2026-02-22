"use client";

import { usePortfolio } from "@/lib/PortfolioContext";
import { useEffect, useState } from "react";
import { API_BASE_URL } from "@/lib/api";
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, ReferenceLine, Cell
} from "recharts";
import { TrendingUp, TrendingDown, DollarSign, Activity, Archive } from "lucide-react";

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

const fmt = (n: number) =>
    `${n < 0 ? "-" : "+"}$${Math.abs(n).toLocaleString("en-CA", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;

export default function PnLPage() {
    const { data, loading, error } = usePortfolio();
    const [realized, setRealized] = useState<RealizedRow[]>([]);
    const [realizedLoading, setRealizedLoading] = useState(true);

    useEffect(() => {
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

    const holdings = data.holdings as any[];
    const usdCad = data.summary?.usd_cad_rate ?? 1.36;

    // ---- Unrealized rows ----
    const rows = holdings.map((h: any) => {
        const costBasis = h["Cost Basis"] ?? 0;
        const pnl = h["PnL"] ?? 0;
        const pnlPct = costBasis > 0 ? (pnl / costBasis) * 100 : 0;
        const currency = h["Currency"] ?? "USD";
        return {
            symbol: h.Symbol,
            currency,
            currencyPrefix: currency === "USD" ? "US$" : "$",
            qty: h["Quantity"] ?? 0,
            avgCost: h["Purchase Price"] ?? 0,
            currentPrice: h["Current Price"] ?? 0,
            marketValue: h["Market_Value"] ?? 0,
            costBasis,
            pnl,
            pnlPct,
        };
    }).sort((a, b) => b.pnl - a.pnl);

    const winners = rows.filter(r => r.pnl >= 0);
    const losers = rows.filter(r => r.pnl < 0);
    const totalUnrealizedPnL = rows.reduce((s, r) => s + r.pnl, 0);
    const totalCostBasis = rows.reduce((s, r) => s + r.costBasis, 0);
    const totalPct = totalCostBasis > 0 ? (totalUnrealizedPnL / totalCostBasis) * 100 : 0;
    const chartData = rows.map(r => ({ name: r.symbol, pnl: parseFloat(r.pnl.toFixed(0)) }));

    // ---- Realized rows (converted to CAD for summary) ----
    const realizedSorted = [...realized].sort((a, b) => b.pnl_amount - a.pnl_amount);
    const totalRealizedCAD = realized.reduce((s, r) => {
        const inCad = r.currency === "USD" ? r.pnl_amount * usdCad : r.pnl_amount;
        return s + inCad;
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

            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                    {
                        label: "Unrealized P&L",
                        value: fmt(totalUnrealizedPnL),
                        sub: `${totalPct >= 0 ? "+" : ""}${totalPct.toFixed(2)}% | CAD`,
                        icon: Activity,
                        color: totalUnrealizedPnL >= 0 ? "text-emerald-400" : "text-rose-400",
                        bg: totalUnrealizedPnL >= 0 ? "from-emerald-500/10 to-emerald-500/5 border-emerald-500/20" : "from-rose-500/10 to-rose-500/5 border-rose-500/20",
                    },
                    {
                        label: "Realized P&L (Closed Trades)",
                        value: fmt(totalRealizedCAD),
                        sub: "CAD equivalent (from broker history)",
                        icon: Archive,
                        color: totalRealizedCAD >= 0 ? "text-emerald-400" : "text-rose-400",
                        bg: totalRealizedCAD >= 0 ? "from-emerald-500/10 to-emerald-500/5 border-emerald-500/20" : "from-rose-500/10 to-rose-500/5 border-rose-500/20",
                    },
                    {
                        label: "Open Winners",
                        value: `${winners.length} positions`,
                        sub: `+$${winners.reduce((s, r) => s + r.pnl, 0).toLocaleString("en-CA", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`,
                        icon: TrendingUp,
                        color: "text-emerald-400",
                        bg: "from-emerald-500/10 to-emerald-500/5 border-emerald-500/20",
                    },
                    {
                        label: "Open Losers",
                        value: `${losers.length} positions`,
                        sub: `-$${Math.abs(losers.reduce((s, r) => s + r.pnl, 0)).toLocaleString("en-CA", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`,
                        icon: TrendingDown,
                        color: "text-rose-400",
                        bg: "from-rose-500/10 to-rose-500/5 border-rose-500/20",
                    },
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

            {/* Unrealized Bar Chart */}
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

            {/* Unrealized Positions Table */}
            <div className="glass-panel rounded-2xl overflow-hidden">
                <div className="p-6 border-b border-white/10">
                    <h2 className="text-lg font-bold">Open Positions — Unrealized P&L</h2>
                    <p className="text-xs text-zinc-500 mt-1">Current holdings vs average cost basis. Values in CAD.</p>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                        <thead className="bg-white/5 text-zinc-400 text-xs uppercase tracking-wider">
                            <tr>
                                <th className="p-4">Symbol</th>
                                <th className="p-4 text-right">Qty</th>
                                <th className="p-4 text-right">Avg Cost</th>
                                <th className="p-4 text-right">Current Price</th>
                                <th className="p-4 text-right">Cost Basis (CAD)</th>
                                <th className="p-4 text-right">Market Value (CAD)</th>
                                <th className="p-4 text-right">Unrealized P&L</th>
                                <th className="p-4 text-right">Return %</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {rows.map((r) => {
                                const isWin = r.pnl >= 0;
                                return (
                                    <tr key={r.symbol} className="hover:bg-white/5 transition-colors">
                                        <td className="p-4">
                                            <div className="font-bold text-blue-400">{r.symbol}</div>
                                            <div className="text-xs text-zinc-500">{r.currency}</div>
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
                                <td className="p-4 text-zinc-300" colSpan={4}>Portfolio Total</td>
                                <td className="p-4 text-right text-zinc-300">${totalCostBasis.toLocaleString("en-CA", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</td>
                                <td className="p-4 text-right text-zinc-300">${(totalCostBasis + totalUnrealizedPnL).toLocaleString("en-CA", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</td>
                                <td className={`p-4 text-right ${totalUnrealizedPnL >= 0 ? "text-emerald-400" : "text-rose-400"}`}>{fmt(totalUnrealizedPnL)}</td>
                                <td className={`p-4 text-right ${totalUnrealizedPnL >= 0 ? "text-emerald-400" : "text-rose-400"}`}>{totalPct >= 0 ? "+" : ""}{totalPct.toFixed(2)}%</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>

            {/* Realized PnL Table */}
            <div className="glass-panel rounded-2xl overflow-hidden">
                <div className="p-6 border-b border-white/10 flex items-center justify-between">
                    <div>
                        <h2 className="text-lg font-bold">Closed Trades — Realized P&L</h2>
                        <p className="text-xs text-zinc-500 mt-1">FIFO cost-basis from broker exports (RBC, CIBC, TD) — grouped by broker & account</p>
                    </div>
                    <span className={`text-xl font-bold ${totalRealizedCAD >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                        {fmt(totalRealizedCAD)} CAD
                    </span>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                        <thead className="bg-white/5 text-zinc-400 text-xs uppercase tracking-wider">
                            <tr>
                                <th className="p-4">Symbol</th>
                                <th className="p-4">Broker / Account</th>
                                <th className="p-4 text-right">Cost Basis</th>
                                <th className="p-4 text-right">Realized P&L (Native)</th>
                                <th className="p-4 text-right">Return %</th>
                                <th className="p-4 text-right">Realized P&L (CAD)</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {realizedLoading ? (
                                <tr><td className="p-6 text-zinc-500 animate-pulse" colSpan={6}>Loading realized data...</td></tr>
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
                                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-white/10 text-xs font-medium text-zinc-300">
                                                {r.broker}
                                            </span>
                                            <span className="ml-1 inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-blue-500/15 text-xs font-medium text-blue-400">
                                                {r.account_type}
                                            </span>
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
                                        <td className={`p-4 text-right font-semibold ${isWin ? "text-emerald-400" : "text-rose-400"}`}>
                                            {fmt(inCad)}
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                        <tfoot className="bg-white/5 font-bold border-t border-white/10">
                            <tr>
                                <td className="p-4 text-zinc-300" colSpan={5}>Total Realized (CAD equiv.)</td>
                                <td className={`p-4 text-right ${totalRealizedCAD >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                                    {fmt(totalRealizedCAD)}
                                </td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>
        </div>
    );
}
