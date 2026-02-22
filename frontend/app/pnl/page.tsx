"use client";

import { usePortfolio } from "@/lib/PortfolioContext";
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, ReferenceLine, Cell
} from "recharts";
import { TrendingUp, TrendingDown, DollarSign, Activity } from "lucide-react";

export default function PnLPage() {
    const { data, loading, error } = usePortfolio();

    if (loading) return (
        <div className="p-10 text-center animate-pulse text-zinc-400 text-lg">Loading P&L data...</div>
    );
    if (error || !data) return (
        <div className="p-10 text-center text-rose-400">Failed to load data. Ensure backend is running.</div>
    );

    const holdings = data.holdings as any[];
    const usdCad = data.summary?.usd_cad_rate ?? 1.36;

    // Build per-holding PnL rows
    const rows = holdings.map((h: any) => {
        const costBasis = h["Cost Basis"] ?? 0;
        const pnl = h["PnL"] ?? 0;
        const pnlPct = costBasis > 0 ? (pnl / costBasis) * 100 : 0;
        const currentPrice = h["Current Price"] ?? 0;
        const avgCost = h["Purchase Price"] ?? 0;
        const qty = h["Quantity"] ?? 0;
        const currency = h["Currency"] ?? "USD";
        const currencyPrefix = currency === "USD" ? "US$" : "$";

        return {
            symbol: h.Symbol,
            currency,
            currencyPrefix,
            qty,
            avgCost,
            currentPrice,
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

    const chartData = rows.map(r => ({
        name: r.symbol,
        pnl: parseFloat(r.pnl.toFixed(0)),
    }));

    const fmt = (n: number) =>
        `${n < 0 ? "-" : "+"}$${Math.abs(n).toLocaleString("en-CA", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;

    return (
        <div className="p-8 max-w-[1400px] mx-auto space-y-8">

            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-blue-500">
                    Profit & Loss
                </h1>
                <p className="text-zinc-400 mt-1">Unrealized gains and losses across your portfolio (CAD)</p>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                    {
                        label: "Total Unrealized P&L",
                        value: fmt(totalUnrealizedPnL),
                        sub: `${totalPct >= 0 ? "+" : ""}${totalPct.toFixed(2)}%`,
                        icon: Activity,
                        color: totalUnrealizedPnL >= 0 ? "text-emerald-400" : "text-rose-400",
                        bg: totalUnrealizedPnL >= 0 ? "from-emerald-500/10 to-emerald-500/5 border-emerald-500/20" : "from-rose-500/10 to-rose-500/5 border-rose-500/20",
                    },
                    {
                        label: "Total Cost Basis",
                        value: `$${totalCostBasis.toLocaleString("en-CA", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`,
                        sub: "CAD",
                        icon: DollarSign,
                        color: "text-blue-400",
                        bg: "from-blue-500/10 to-blue-500/5 border-blue-500/20",
                    },
                    {
                        label: "Winners",
                        value: `${winners.length} positions`,
                        sub: `+$${winners.reduce((s, r) => s + r.pnl, 0).toLocaleString("en-CA", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`,
                        icon: TrendingUp,
                        color: "text-emerald-400",
                        bg: "from-emerald-500/10 to-emerald-500/5 border-emerald-500/20",
                    },
                    {
                        label: "Losers",
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

            {/* Bar Chart */}
            <div className="glass-panel rounded-2xl p-6">
                <h2 className="text-lg font-bold mb-1">Unrealized P&L by Position (CAD)</h2>
                <p className="text-xs text-zinc-500 mb-4">Sorted from best to worst performer</p>
                <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={chartData} margin={{ top: 8, right: 16, left: 16, bottom: 40 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                        <XAxis
                            dataKey="name"
                            tick={{ fontSize: 11, fill: "#9ca3af" }}
                            angle={-35}
                            textAnchor="end"
                            interval={0}
                        />
                        <YAxis
                            tick={{ fontSize: 11, fill: "#9ca3af" }}
                            tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                        />
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

            {/* Detailed Table */}
            <div className="glass-panel rounded-2xl overflow-hidden">
                <div className="p-6 border-b border-white/10">
                    <h2 className="text-lg font-bold">Position Breakdown</h2>
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
                                        <td className="p-4 text-right text-zinc-400">
                                            {r.currencyPrefix}{r.avgCost.toFixed(2)}
                                        </td>
                                        <td className="p-4 text-right text-zinc-400">
                                            {r.currencyPrefix}{r.currentPrice.toFixed(2)}
                                        </td>
                                        <td className="p-4 text-right text-zinc-300">
                                            ${r.costBasis.toLocaleString("en-CA", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                                        </td>
                                        <td className="p-4 text-right text-zinc-300">
                                            ${r.marketValue.toLocaleString("en-CA", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                                        </td>
                                        <td className={`p-4 text-right font-semibold ${isWin ? "text-emerald-400" : "text-rose-400"}`}>
                                            {fmt(r.pnl)}
                                        </td>
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
                        {/* Totals row */}
                        <tfoot className="bg-white/5 font-bold border-t border-white/10">
                            <tr>
                                <td className="p-4 text-zinc-300" colSpan={4}>Portfolio Total</td>
                                <td className="p-4 text-right text-zinc-300">
                                    ${totalCostBasis.toLocaleString("en-CA", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                                </td>
                                <td className="p-4 text-right text-zinc-300">
                                    ${(totalCostBasis + totalUnrealizedPnL).toLocaleString("en-CA", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                                </td>
                                <td className={`p-4 text-right ${totalUnrealizedPnL >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                                    {fmt(totalUnrealizedPnL)}
                                </td>
                                <td className={`p-4 text-right ${totalUnrealizedPnL >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                                    {totalPct >= 0 ? "+" : ""}{totalPct.toFixed(2)}%
                                </td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>
        </div>
    );
}
