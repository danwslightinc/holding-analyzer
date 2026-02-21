"use client";

import { useEffect, useState, useMemo } from "react";
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from "recharts";
import { TrendingUp, Filter } from "lucide-react";
import { API_BASE_URL } from "@/lib/api";
import { usePortfolio } from "@/lib/PortfolioContext";

interface PerformancePoint {
    date: string;
    Portfolio: number;
    "^GSPC": number;
    "^IXIC": number;
    "^GSPTSE": number;
    [key: string]: any; // For flexible access
}

const RANGES = ['1M', '3M', '6M', 'YTD', '1Y', '2Y', '5Y', '10Y', 'ALL'];
const BENCHMARKS = [
    { key: '^GSPC', name: 'S&P 500', color: '#EF4444' },
    { key: '^IXIC', name: 'NASDAQ', color: '#fbbf24' },
    { key: '^GSPTSE', name: 'TSX', color: '#A855F7' }
];

export default function PerformancePage() {
    const { history: rawHistory, loading, error } = usePortfolio();
    const [range, setRange] = useState("1M");
    const [visibleBenchmarks, setVisibleBenchmarks] = useState<Record<string, boolean>>({
        '^GSPC': true,
        '^IXIC': false,
        '^GSPTSE': false
    });

    const chartData = useMemo(() => {
        if (!rawHistory || rawHistory.length === 0) return [];

        // 1. Filter by Range
        const now = new Date();
        let startDate = new Date();

        // "ALL" uses earliest date
        if (range === 'ALL') {
            startDate = new Date(rawHistory[0].date);
        } else {
            switch (range) {
                case '1M': startDate.setMonth(now.getMonth() - 1); break;
                case '3M': startDate.setMonth(now.getMonth() - 3); break;
                case '6M': startDate.setMonth(now.getMonth() - 6); break;
                case 'YTD': startDate = new Date(now.getFullYear(), 0, 1); break;
                case '1Y': startDate.setFullYear(now.getFullYear() - 1); break;
                case '2Y': startDate.setFullYear(now.getFullYear() - 2); break;
                case '5Y': startDate.setFullYear(now.getFullYear() - 5); break;
                case '10Y': startDate.setFullYear(now.getFullYear() - 10); break;
            }
        }

        const filtered = (rawHistory as PerformancePoint[]).filter((d: PerformancePoint) => new Date(d.date) >= startDate);
        if (filtered.length === 0) return [];

        // 2. Normalize to Percentage (Start = 0%)
        const base = filtered[0];

        return filtered.map((d: PerformancePoint) => {
            const point: any = { date: d.date };

            // Portfolio %
            if (base.Portfolio) {
                point.Portfolio = ((d.Portfolio - base.Portfolio) / base.Portfolio) * 100;
            }

            // Benchmarks %
            BENCHMARKS.forEach(b => {
                if (d[b.key] && base[b.key]) {
                    point[b.key] = ((d[b.key] - base[b.key]) / base[b.key]) * 100;
                }
            });

            return point;
        });

    }, [rawHistory, range]);

    // Calculate Summary Stats for selected Range
    const currentReturn = chartData.length > 0 ? chartData[chartData.length - 1].Portfolio : 0;
    const isPositive = currentReturn >= 0;

    const toggleBenchmark = (key: string) => {
        setVisibleBenchmarks(prev => ({ ...prev, [key]: !prev[key] }));
    };

    if (loading && !rawHistory) return <div className="p-10 text-center animate-pulse">Loading History (10Y Backtest)...</div>;
    if (error) return <div className="p-10 text-center text-red-500">Failed to load performance data.</div>;
    if (!rawHistory || (rawHistory as PerformancePoint[]).length === 0) return <div className="p-10 text-center text-red-500">No historical data available.</div>;

    return (
        <div className="p-8 max-w-[1600px] mx-auto space-y-8 font-sans">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                <div>
                    <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">
                        Performance
                    </h1>
                    <div className="flex items-baseline gap-4 mt-2">
                        <span className={`text-4xl font-bold ${isPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {isPositive ? '+' : ''}{currentReturn.toFixed(2)}%
                        </span>
                        <span className="text-gray-400 text-sm uppercase tracking-wider">{range} Return</span>
                    </div>
                </div>

                {/* Range Selector */}
                <div className="glass-panel p-1 rounded-xl flex overflow-x-auto">
                    {RANGES.map(r => (
                        <button
                            key={r}
                            onClick={() => setRange(r)}
                            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${range === r
                                ? 'bg-primary/20 text-blue-400 bg-white/10 shadow-sm'
                                : 'text-gray-400 hover:text-foreground hover:bg-black/5 dark:hover:bg-white/5'
                                }`}
                        >
                            {r}
                        </button>
                    ))}
                </div>
            </div>

            {/* Main Chart */}
            <div className="glass-panel p-6 rounded-2xl h-[500px] relative">
                {/* Legend / Toggles */}
                <div className="absolute top-6 left-6 right-6 flex flex-wrap gap-4 z-10 pointer-events-none">
                    {/* Portfolio Legend */}
                    <div className="flex items-center gap-2 pointer-events-auto">
                        <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                        <span className="text-sm font-medium text-foreground">Portfolio</span>
                    </div>

                    {/* Benchmark Toggles */}
                    {BENCHMARKS.map(b => (
                        <button
                            key={b.key}
                            onClick={() => toggleBenchmark(b.key)}
                            className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium border transition-all pointer-events-auto ${visibleBenchmarks[b.key]
                                ? `bg-[${b.color}]/10 border-[${b.color}]/30 text-foreground`
                                : 'bg-transparent border-white/10 text-gray-500 hover:border-white/30'
                                }`}
                            style={{
                                color: visibleBenchmarks[b.key] ? b.color : undefined,
                                borderColor: visibleBenchmarks[b.key] ? b.color : undefined
                            }}
                        >
                            <div className={`w-2 h-2 rounded-full ${visibleBenchmarks[b.key] ? '' : 'bg-gray-600'}`} style={{ backgroundColor: visibleBenchmarks[b.key] ? b.color : undefined }}></div>
                            {b.name}
                        </button>
                    ))}
                </div>

                <div className="flex-1 min-h-0 relative h-full pt-10">
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={chartData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                            <XAxis
                                dataKey="date"
                                stroke="#666"
                                fontSize={12}
                                tickFormatter={(val) => {
                                    const d = new Date(val);
                                    return range === '1M' || range === '1W'
                                        ? d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
                                        : d.toLocaleDateString(undefined, { month: 'short', year: '2-digit' });
                                }}
                                minTickGap={50}
                            />
                            <YAxis
                                stroke="#666"
                                tickFormatter={(val) => `${val.toFixed(0)}%`}
                                domain={['auto', 'auto']}
                            />
                            <Tooltip
                                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}
                                formatter={(val: any, name: any) => {
                                    const benchmarkName = BENCHMARKS.find(b => b.key === name)?.name || name;
                                    return [`${val.toFixed(2)}%`, benchmarkName];
                                }}
                                labelFormatter={(label) => new Date(label).toISOString().split('T')[0].replace(/-/g, '/')}
                            />

                            {/* Portfolio Line */}
                            <Line
                                type="monotone"
                                dataKey="Portfolio"
                                stroke="#3b82f6"
                                strokeWidth={3}
                                dot={false}
                                activeDot={{ r: 6 }}
                            />

                            {/* Benchmark Lines */}
                            {BENCHMARKS.map(b => (
                                visibleBenchmarks[b.key] && (
                                    <Line
                                        key={b.key}
                                        type="monotone"
                                        dataKey={b.key}
                                        stroke={b.color}
                                        strokeWidth={2}
                                        dot={false}
                                        strokeDasharray="5 5"
                                    />
                                )
                            ))}
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="glass-panel p-6 rounded-2xl">
                    <h3 className="text-gray-400 mb-2 font-medium">Annualized Return {range !== 'ALL' && !range.includes('Y') && '(Extrapolated)'}</h3>
                    <div className="text-2xl font-bold text-foreground">
                        {(() => {
                            if (chartData.length < 2) return <span className="text-gray-500 text-lg">--</span>;

                            const start = new Date(chartData[0].Date);
                            const end = new Date(chartData[chartData.length - 1].Date);
                            const diffTime = end.getTime() - start.getTime();
                            const years = diffTime / (1000 * 60 * 60 * 24 * 365.25);

                            if (years < 0.08) return <span className="text-gray-500 text-lg">--</span>; // < 1 month

                            const cagr = (Math.pow((currentReturn / 100) + 1, 1 / years) - 1) * 100;
                            return <span>{cagr.toFixed(2)}%</span>;
                        })()}
                    </div>
                </div>
                <div className="glass-panel p-6 rounded-2xl">
                    <h3 className="text-gray-400 mb-2 font-medium">Best Day</h3>
                    <div className="text-2xl font-bold text-emerald-400">
                        {/* Calculate max daily change from chartData */}
                        {(() => {
                            if (chartData.length < 2) return "--";
                            let maxChange = -Infinity;
                            for (let i = 1; i < chartData.length; i++) {
                                const change = chartData[i].Portfolio - chartData[i - 1].Portfolio;
                                if (change > maxChange) maxChange = change;
                            }
                            return `+${maxChange.toFixed(2)}%`;
                        })()}
                    </div>
                </div>
                <div className="glass-panel p-6 rounded-2xl">
                    <h3 className="text-gray-400 mb-2 font-medium">Worst Day</h3>
                    <div className="text-2xl font-bold text-rose-400">
                        {(() => {
                            if (chartData.length < 2) return "--";
                            let minChange = Infinity;
                            for (let i = 1; i < chartData.length; i++) {
                                const change = chartData[i].Portfolio - chartData[i - 1].Portfolio;
                                if (change < minChange) minChange = change;
                            }
                            return `${minChange.toFixed(2)}%`;
                        })()}
                    </div>
                </div>
            </div>
        </div>
    );
}
