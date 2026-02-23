"use client";

import { useEffect, useState, useMemo } from "react";
import { API_BASE_URL } from "@/lib/api";
import { Activity, Target, Timer, TrendingUp, TrendingDown, Percent, Calendar, ShieldCheck, BarChart3 } from "lucide-react";
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, ZAxis, ReferenceLine, Cell } from "recharts";
import { usePortfolio } from "@/lib/PortfolioContext";

interface Transaction {
    id: number;
    Symbol: string;
    "Purchase Price": number;
    Quantity: number;
    Commission: number;
    "Trade Date": string;
    "Transaction Type": string;
    Broker: string;
    "Account Type": string;
    Comment: string;
}

interface ClosedTrade {
    symbol: string;
    buyDate: string;
    sellDate: string;
    quantity: number;
    costBasis: number;
    proceeds: number;
    pnl: number;
    returnPct: number;
    holdingDays: number;
    annualizedReturn: number;
    isWin: boolean;
}

export default function TradeAnalysisPage() {
    const { data: portData } = usePortfolio();
    const [closedTrades, setClosedTrades] = useState<ClosedTrade[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch(`${API_BASE_URL}/api/closed-trades`)
            .then(res => res.json())
            .then(data => {
                setClosedTrades(data || []);
            })
            .catch(console.error)
            .finally(() => setLoading(false));
    }, []);

    if (loading) {
        return <div className="p-10 text-center animate-pulse text-zinc-400">Loading Trade History...</div>;
    }

    const totalTrades = closedTrades.length;
    const wins = closedTrades.filter(t => t.isWin);
    const losses = closedTrades.filter(t => !t.isWin);
    const winRate = totalTrades > 0 ? (wins.length / totalTrades) * 100 : 0;

    // Average holding days calculation
    const avgHoldingDays = totalTrades > 0 ? closedTrades.reduce((acc, t) => acc + t.holdingDays, 0) / totalTrades : 0;

    // Average Annualized Return
    // Portseido simply averages the annualized returns of all closed trades usually, 
    // or does an aggregate portfolio CAGR. We'll do the average of the trade CAGRs.
    const validAnnRets = closedTrades.filter(t => isFinite(t.annualizedReturn));
    const avgAnnRet = validAnnRets.length > 0 ? validAnnRets.reduce((acc, t) => acc + t.annualizedReturn, 0) / validAnnRets.length : 0;

    // SP500 Historical average win rate on random trades is roughly ~54%
    const baselineSP500WinRate = 54.0;
    const beatSP500 = winRate > baselineSP500WinRate;

    const scatterData = closedTrades.map((t, idx) => ({
        id: `${t.symbol}-${idx}`,
        name: t.symbol,
        x: t.holdingDays,
        y: t.returnPct,
        z: Math.abs(t.proceeds) + Math.abs(t.costBasis), // Bubble size proportional to trade value
        fill: t.isWin ? "#10b981" : "#f43f5e"
    }));

    return (
        <div className="p-8 max-w-[1400px] mx-auto space-y-8">
            {/* Portseido-style Top Header */}
            <div>
                <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-indigo-500">
                    Trade Analysis
                </h1>
                <p className="text-zinc-400 mt-2 text-sm">Review individual closed trades, holding periods, and annualized performance.</p>
            </div>

            {/* Portseido Metrics Row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="glass-panel p-6 rounded-2xl flex flex-col justify-center border-l-4 border-l-blue-500">
                    <span className="text-xs text-zinc-400 font-bold uppercase tracking-wider flex items-center gap-2 mb-2"><Activity size={14} /> Total Trades</span>
                    <span className="text-3xl font-bold text-foreground">{totalTrades}</span>
                    <span className="text-xs text-zinc-500 mt-1">{wins.length} Winners / {losses.length} Losers</span>
                </div>

                <div className={`glass-panel p-6 rounded-2xl flex flex-col justify-center border-l-4 ${winRate >= 50 ? 'border-l-emerald-500' : 'border-l-rose-500'}`}>
                    <span className="text-xs text-zinc-400 font-bold uppercase tracking-wider flex items-center gap-2 mb-2"><Target size={14} /> Win Rate</span>
                    <span className="text-3xl font-bold text-foreground">{winRate.toFixed(2)}%</span>
                    <span className="text-xs text-zinc-500 mt-1 flex items-center gap-1">
                        {beatSP500 ? <TrendingUp size={12} className="text-emerald-500" /> : <TrendingDown size={12} className="text-rose-500" />}
                        vs S&P 500 (~{baselineSP500WinRate}%)
                    </span>
                </div>

                <div className="glass-panel p-6 rounded-2xl flex flex-col justify-center border-l-4 border-l-purple-500">
                    <span className="text-xs text-zinc-400 font-bold uppercase tracking-wider flex items-center gap-2 mb-2"><Percent size={14} /> Avg Annualized</span>
                    <span className={`text-3xl font-bold ${avgAnnRet >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {avgAnnRet >= 0 ? '+' : ''}{avgAnnRet.toFixed(2)}%
                    </span>
                    <span className="text-xs text-zinc-500 mt-1">Mean of Individual Trade CAGRs</span>
                </div>

                <div className="glass-panel p-6 rounded-2xl flex flex-col justify-center border-l-4 border-l-amber-500">
                    <span className="text-xs text-zinc-400 font-bold uppercase tracking-wider flex items-center gap-2 mb-2"><Timer size={14} /> Avg Holding Days</span>
                    <span className="text-3xl font-bold text-foreground">{avgHoldingDays.toFixed(0)}</span>
                    <span className="text-xs text-zinc-500 mt-1">Days per closed trade</span>
                </div>
            </div>

            {/* Trade Analysis Chart */}
            <div className="glass-panel rounded-2xl p-6 mt-8">
                <h2 className="text-lg font-bold flex items-center gap-2 mb-1"><BarChart3 size={18} className="text-purple-400" /> Return % vs Holding Period</h2>
                <p className="text-xs text-zinc-500 mb-6">Scatter plot mirroring Portseido's Trade Analysis visual. Bubble size represents relative trade sizing.</p>
                <ResponsiveContainer width="100%" height={350}>
                    <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 10 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={true} vertical={false} />
                        <XAxis type="number" dataKey="x" name="Holding Days" tick={{ fill: "#9ca3af", fontSize: 11 }} label={{ value: 'Holding Time (Days)', position: 'bottom', offset: 0, fill: '#9ca3af', fontSize: 11 }} />
                        <YAxis type="number" dataKey="y" name="Return %" tick={{ fill: "#9ca3af", fontSize: 11 }} tickFormatter={(v) => `${v}%`} label={{ value: 'Return (%)', angle: -90, position: 'insideLeft', fill: '#9ca3af', fontSize: 11 }} />
                        <ZAxis type="number" dataKey="z" range={[60, 600]} name="Trade Size" />
                        <RechartsTooltip
                            cursor={{ strokeDasharray: '3 3', stroke: 'rgba(255,255,255,0.2)' }}
                            content={({ active, payload }) => {
                                if (active && payload && payload.length) {
                                    const data = payload[0].payload;
                                    return (
                                        <div className="bg-[#1a1a2e] border border-white/10 rounded-xl p-3 shadow-xl">
                                            <p className="font-bold text-white mb-2">{data.name}</p>
                                            <div className="flex justify-between gap-4 text-sm mt-1">
                                                <span className="text-zinc-400">Return:</span>
                                                <span className={data.y >= 0 ? "text-emerald-400 font-medium" : "text-rose-400 font-medium"}>{data.y > 0 ? '+' : ''}{data.y.toFixed(2)}%</span>
                                            </div>
                                            <div className="flex justify-between gap-4 text-sm mt-1">
                                                <span className="text-zinc-400">Holding Days:</span>
                                                <span className="text-zinc-200 font-medium">{data.x}</span>
                                            </div>
                                        </div>
                                    );
                                }
                                return null;
                            }}
                        />
                        <ReferenceLine y={0} stroke="rgba(255,255,255,0.2)" strokeWidth={1} />
                        <Scatter data={scatterData} opacity={0.8} stroke="rgba(0,0,0,0.3)" strokeWidth={1}>
                            {scatterData.map((entry) => (
                                <Cell key={entry.id} fill={entry.fill} />
                            ))}
                        </Scatter>
                    </ScatterChart>
                </ResponsiveContainer>
            </div>

            {/* Individual Closed Trades Table */}
            <div className="glass-panel rounded-2xl overflow-hidden mt-8">
                <div className="p-6 border-b border-white/10">
                    <h2 className="text-lg font-bold flex items-center gap-2"><ShieldCheck size={18} className="text-blue-500" /> Individual Trade Log</h2>
                    <p className="text-xs text-zinc-500 mt-1">Calculated automatically via FIFO logic matching buys and sells.</p>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                        <thead className="bg-white/5 text-zinc-400 text-xs uppercase tracking-wider">
                            <tr>
                                <th className="p-4 font-semibold">Symbol</th>
                                <th className="p-4 font-semibold text-right">Hold Days</th>
                                <th className="p-4 font-semibold text-right">Ann. Return</th>
                                <th className="p-4 font-semibold text-right">Return %</th>
                                <th className="p-4 font-semibold text-right">Gain / Loss</th>
                                <th className="p-4 font-semibold text-right">Buy Date</th>
                                <th className="p-4 font-semibold text-right">Sell Date</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {closedTrades.length === 0 ? (
                                <tr>
                                    <td colSpan={7} className="p-8 text-center text-zinc-500">No closed trades found matching buys and sells in your history.</td>
                                </tr>
                            ) : closedTrades.map((t, idx) => (
                                <tr key={idx} className="hover:bg-white/5 transition-colors">
                                    <td className="p-4 font-bold text-blue-400">{t.symbol}</td>
                                    <td className="p-4 text-right font-medium text-zinc-300">{t.holdingDays}</td>
                                    <td className={`p-4 text-right font-bold ${t.annualizedReturn >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                                        {isFinite(t.annualizedReturn) ? `${t.annualizedReturn >= 0 ? '+' : ''}${t.annualizedReturn.toFixed(2)}%` : 'N/A'}
                                    </td>
                                    <td className={`p-4 text-right font-semibold ${t.isWin ? "text-emerald-400" : "text-rose-400"}`}>
                                        {t.returnPct >= 0 ? '+' : ''}{t.returnPct.toFixed(2)}%
                                    </td>
                                    <td className={`p-4 text-right font-semibold ${t.isWin ? "text-emerald-400" : "text-rose-400"}`}>
                                        {t.pnl >= 0 ? '+' : ''}${Math.abs(t.pnl).toLocaleString("en-CA", { maximumFractionDigits: 2 })}
                                    </td>
                                    <td className="p-4 text-right text-zinc-400 text-xs">{t.buyDate}</td>
                                    <td className="p-4 text-right text-zinc-400 text-xs">{t.sellDate}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
