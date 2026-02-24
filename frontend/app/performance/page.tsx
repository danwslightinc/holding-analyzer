"use client";

import { useEffect, useState, useMemo } from "react";
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, Treemap, Cell
} from "recharts";
import { TrendingUp, Filter, Layers } from "lucide-react";
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

const getHeatmapStyle = (perf: number | undefined) => {
    // 0 or N/A is dark gray
    if (perf === undefined || isNaN(perf) || perf === 0) return { bg: '#3f3f46', text: '#ffffff' };

    // Up stocks (Finviz style greens)
    if (perf >= 2) return { bg: '#15803d', text: '#ffffff' }; // green-700
    if (perf >= 1) return { bg: '#22c55e', text: '#ffffff' }; // green-500
    if (perf > 0) return { bg: '#4ade80', text: '#022c22' };  // green-400

    // Down stocks (Finviz style reds)
    if (perf <= -2) return { bg: '#b91c1c', text: '#ffffff' }; // red-700
    if (perf <= -1) return { bg: '#ef4444', text: '#ffffff' }; // red-500
    if (perf < 0) return { bg: '#f87171', text: '#450a0a' };   // red-400

    return { bg: '#3f3f46', text: '#ffffff' };
};

const CustomizedTreemapContent = (props: any) => {
    const { root, depth, x, y, width, height, index, name, value, dayChange } = props;

    // Only render inner nodes
    if (depth < 1) return null;

    const style = getHeatmapStyle(dayChange);

    return (
        <g>
            <foreignObject x={x} y={y} width={width} height={height}>
                <div
                    className="group cursor-pointer border-[1px] border-white dark:border-[#121212]"
                    style={{
                        width: '100%',
                        height: '100%',
                        backgroundColor: style.bg,
                        boxSizing: 'border-box',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'center',
                        alignItems: 'center',
                        overflow: 'hidden',
                        position: 'relative',
                        color: style.text
                    }}
                >
                    {/* Overlay for hover effect */}
                    <div className="absolute inset-0 bg-white/0 group-hover:bg-white/10 transition-colors duration-200 pointer-events-none" />

                    <div className="relative z-10 flex flex-col items-center justify-center p-1 pointer-events-none">
                        {width > 45 && height > 35 && (
                            <>
                                <span className={`font-bold ${width > 80 ? 'text-lg' : 'text-sm'} whitespace-nowrap overflow-hidden text-ellipsis max-w-[90%] drop-shadow-sm`}>
                                    {name}
                                </span>
                                {height > 55 && (
                                    <span className={`font-medium ${width > 80 ? 'text-sm' : 'text-xs'} opacity-90 tracking-wide drop-shadow-sm mt-0.5`}>
                                        {dayChange !== undefined && !isNaN(dayChange) ? `${dayChange > 0 ? '+' : ''}${dayChange.toFixed(2)}%` : 'N/A'}
                                    </span>
                                )}
                            </>
                        )}
                    </div>
                </div>
            </foreignObject>
        </g>
    );
};

const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
        const data = payload[0].payload;
        if (!data || !data.name) return null;
        return (
            <div className="bg-white/95 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 p-4 rounded-xl shadow-2xl backdrop-blur-md">
                <p className="font-bold text-gray-900 dark:text-white text-lg mb-2">{data.name}</p>
                <div className="flex flex-col gap-2">
                    <div className="flex justify-between gap-4">
                        <span className="text-sm text-gray-500 dark:text-zinc-400">Market Value</span>
                        <span className="text-sm font-mono text-gray-900 dark:text-zinc-200">
                            ${data.value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </span>
                    </div>
                    <div className="flex justify-between gap-4">
                        <span className="text-sm text-gray-500 dark:text-zinc-400">Day Change</span>
                        <span className={`text-sm font-bold ${data.dayChange > 0 ? 'text-emerald-500 dark:text-emerald-400' : data.dayChange < 0 ? 'text-rose-500 dark:text-rose-400' : 'text-gray-500 dark:text-zinc-400'}`}>
                            {data.dayChange !== undefined && !isNaN(data.dayChange) ? `${data.dayChange > 0 ? '+' : ''}${data.dayChange.toFixed(2)}%` : 'N/A'}
                        </span>
                    </div>
                </div>
            </div>
        );
    }
    return null;
};

export default function PerformancePage() {
    const { history: rawHistory, data, loading, error } = usePortfolio();
    const [range, setRange] = useState("1M");
    const [visibleBenchmarks, setVisibleBenchmarks] = useState<Record<string, boolean>>({
        '^GSPC': true,
        '^IXIC': false,
        '^GSPTSE': false
    });

    const treemapData = useMemo(() => {
        if (!data || !data.holdings) return [];

        const aggregated = data.holdings.reduce((acc: any, h: any) => {
            if (!acc[h.Symbol]) {
                acc[h.Symbol] = {
                    name: h.Symbol,
                    value: 0,
                    dayChange: h["Day Change"],
                };
            }
            acc[h.Symbol].value += h.Market_Value;
            return acc;
        }, {});

        return [
            {
                name: 'Portfolio',
                children: Object.values(aggregated) as any[]
            }
        ];
    }, [data]);

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
            BENCHMARKS.forEach((b: any) => {
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
        setVisibleBenchmarks((prev: Record<string, boolean>) => ({ ...prev, [key]: !prev[key] }));
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
                    {RANGES.map((r: string) => (
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
                    {BENCHMARKS.map((b: any) => (
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
                                tickFormatter={(val: string) => {
                                    const d = new Date(val);
                                    return range === '1M' || range === '1W'
                                        ? d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
                                        : d.toLocaleDateString(undefined, { month: 'short', year: '2-digit' });
                                }}
                                minTickGap={50}
                            />
                            <YAxis
                                stroke="#666"
                                tickFormatter={(val: number) => `${val.toFixed(0)}%`}
                                domain={['auto', 'auto']}
                            />
                            <Tooltip
                                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}
                                formatter={(val: any, name: any) => {
                                    const benchmarkName = BENCHMARKS.find((b: any) => b.key === name)?.name || name;
                                    return [`${val.toFixed(2)}%`, benchmarkName];
                                }}
                                labelFormatter={(label: string) => new Date(label).toISOString().split('T')[0].replace(/-/g, '/')}
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
                            {BENCHMARKS.map((b: any) => (
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

                            const start = new Date(chartData[0].date);
                            const end = new Date(chartData[chartData.length - 1].date);
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

            {/* Daily Performance Heatmap */}
            <div className="glass-panel p-6 rounded-3xl h-[600px] flex flex-col mt-8 shadow-xl border border-zinc-200/50 dark:border-white/10 dark:bg-[#1a1a1a]">
                <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-6 flex items-center gap-3">
                    <div className="p-2 bg-gradient-to-br from-purple-500/20 to-blue-500/20 rounded-lg">
                        <Layers className="w-5 h-5 text-purple-500 dark:text-purple-400" />
                    </div>
                    Daily Performance
                </h3>
                <div className="flex-1 min-h-0 relative -mx-2">
                    <div className="absolute inset-0">
                        {treemapData && treemapData.length > 0 && treemapData[0].children && treemapData[0].children.length > 0 ? (
                            <ResponsiveContainer width="100%" height="100%">
                                <Treemap
                                    data={treemapData}
                                    dataKey="value"
                                    aspectRatio={4 / 3}
                                    stroke="none"
                                    isAnimationActive={true}
                                    animationDuration={800}
                                    content={<CustomizedTreemapContent />}
                                >
                                    <Tooltip content={<CustomTooltip />} wrapperStyle={{ zIndex: 1000 }} cursor={false} />
                                </Treemap>
                            </ResponsiveContainer>
                        ) : (
                            <div className="flex flex-col items-center justify-center h-full text-zinc-500 dark:text-zinc-600 space-y-4">
                                <div className="animate-pulse w-12 h-12 rounded-full bg-zinc-200 dark:bg-zinc-800" />
                                <p className="font-medium tracking-wide">Waiting for daily market data...</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
