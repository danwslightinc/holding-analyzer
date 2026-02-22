
"use client";

import { useEffect, useState } from "react";
import {
    PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend
} from "recharts";
import { TrendingUp, DollarSign, Activity, Calendar, ArrowUpRight, ArrowDownRight, ChevronUp, ChevronDown } from "lucide-react";
import { motion } from "framer-motion";
import { API_BASE_URL } from "@/lib/api";
import { usePortfolio } from "@/lib/PortfolioContext";

// --- Types ---
interface Holding {
    Symbol: string;
    Current_Price: number;
    Quantity: number;
    Market_Value: number;
    PnL: number;
    CAGR: number;
    Status: string;
    Currency: string;
    [key: string]: any;
}

interface PortfolioSummary {
    total_value: number;
    total_cost: number;
    total_pnl: number;
    usd_cad_rate: number;
}

interface PortfolioData {
    summary: PortfolioSummary;
    holdings: Holding[];
}

interface DividendData {
    Symbol: string;
    Frequency: string;
    Rate: number;
    Months: number[];
    Last_Ex: string;
}

// --- Colors ---
const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#AF19FF', '#FF1919'];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export default function Dashboard() {
    const { data: portData, dividends: divRaw, tickerPerf, loading: portLoading, error: portError } = usePortfolio();
    const [divs, setDivs] = useState<any>(null);
    const [isMounted, setIsMounted] = useState(false);
    const [selectedMetric, setSelectedMetric] = useState<string>('Gain (Value)');
    const [selectedTimeframe, setSelectedTimeframe] = useState<string>('All');
    const [sortConfig, setSortConfig] = useState<{ key: string, direction: 'asc' | 'desc' }>({ key: 'Market_Value', direction: 'desc' });

    // Move processDividends before useEffect so it is hoisted/accessible
    const processDividends = (divRaw: any, portData: PortfolioData) => {
        const chartData = MONTHS.map((m: string) => ({ name: m }) as any);
        const symbols = Object.keys(divRaw);
        const shareMap: Record<string, number> = {};
        portData.holdings.forEach((h: Holding) => shareMap[h.Symbol] = h.Quantity);

        symbols.forEach((sym: string) => {
            const d = divRaw[sym];
            if (d && d.Months) {
                const shares = shareMap[sym] || 0;
                const amt = shares * d.Rate;
                d.Months.forEach((m: number) => {
                    if (m >= 1 && m <= 12) {
                        chartData[m - 1][sym] = amt;
                    }
                });
            }
        });
        setDivs({ chartData, symbols });
    };

    useEffect(() => {
        setIsMounted(true);
        if (portData && divRaw) {
            processDividends(divRaw, portData);
        }
    }, [portData, divRaw]);

    if (portLoading && !portData) return <div className="p-10 text-center animate-pulse">Loading Dashboard...</div>;
    if (portError) return <div className="p-10 text-center text-red-500">Failed to load data. Ensure Backend is running.</div>;
    if (!portData) return null;

    const data = portData;

    // Derived Metrics
    const totalValue = data.summary.total_value;
    const totalPnL = data.summary.total_pnl;
    const totalCost = data.summary.total_cost;
    const pnlPercent = totalCost > 0 ? (totalPnL / totalCost) * 100 : 0;

    // Process holdings for the chart based on selected metric and timeframe

    const handleSort = (key: string) => {
        let direction: 'asc' | 'desc' = 'asc';
        if (sortConfig.key === key && sortConfig.direction === 'asc') {
            direction = 'desc';
        }
        setSortConfig({ key, direction });
    };

    const sortedHoldings = [...data.holdings].sort((a: Holding, b: Holding) => {
        let aValue: any;
        let bValue: any;

        switch (sortConfig.key) {
            case 'Symbol':
                aValue = a.Symbol;
                bValue = b.Symbol;
                break;
            case 'Allocation':
            case 'Market_Value':
                aValue = a.Market_Value;
                bValue = b.Market_Value;
                break;
            case 'Price':
                aValue = a['Current Price'] || 0;
                bValue = b['Current Price'] || 0;
                break;
            case 'AvgCost':
                aValue = (a.Market_Value - a.PnL) / a.Quantity;
                bValue = (b.Market_Value - b.PnL) / b.Quantity;
                break;
            case 'PnL':
                aValue = a.PnL;
                bValue = b.PnL;
                break;
            case 'PnLPercent':
                aValue = a.Market_Value > 0 ? (a.PnL / (a.Market_Value - a.PnL)) : 0;
                bValue = b.Market_Value > 0 ? (b.PnL / (b.Market_Value - b.PnL)) : 0;
                break;
            default:
                aValue = (a as any)[sortConfig.key];
                bValue = (b as any)[sortConfig.key];
        }

        if (aValue < bValue) return sortConfig.direction === 'asc' ? -1 : 1;
        if (aValue > bValue) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
    });

    const getChartData = () => {
        // Debug logging
        console.log('Selected Timeframe:', selectedTimeframe);
        console.log('Selected Metric:', selectedMetric);
        console.log('Ticker Perf Available:', !!tickerPerf);
        if (tickerPerf && data.holdings.length > 0) {
            const firstSymbol = data.holdings[0].Symbol;
            console.log(`Sample ${firstSymbol} data:`, tickerPerf[firstSymbol]);
        }

        // Helper to get timeframe-specific performance
        const getTimeframeValue = (symbol: string, metric: 'value' | 'percent') => {
            if (!tickerPerf || !tickerPerf[symbol]) return 0;

            const perfData = tickerPerf[symbol][selectedTimeframe];
            if (!perfData) return 0;

            return metric === 'percent' ? perfData.change_pct : perfData.change_value;
        };

        switch (selectedMetric) {
            case 'Gain (%)':
                return data.holdings.map((h: Holding) => {
                    // Use timeframe-specific % change if available, otherwise use total P&L %
                    let pnlPercent;
                    if (selectedTimeframe !== 'All' && tickerPerf && tickerPerf[h.Symbol]?.[selectedTimeframe]) {
                        pnlPercent = tickerPerf[h.Symbol][selectedTimeframe].change_pct;
                    } else {
                        pnlPercent = h.Market_Value > 0 ? (h.PnL / (h.Market_Value - h.PnL)) * 100 : 0;
                    }

                    return {
                        name: h.Symbol,
                        value: pnlPercent,
                        fill: pnlPercent >= 0 ? '#10B981' : '#EF4444'
                    };
                }).sort((a: any, b: any) => b.value - a.value);

            case 'Weight':
                const filteredTotal = data.holdings.reduce((sum: number, h: Holding) => sum + h.Market_Value, 0);
                return data.holdings.map((h: Holding) => ({
                    name: h.Symbol,
                    value: filteredTotal > 0 ? (h.Market_Value / filteredTotal) * 100 : 0,
                    fill: '#3b82f6' // Blue for weight
                })).sort((a: any, b: any) => b.value - a.value);

            case 'Gain (Value)':
            default:
                return data.holdings.map((h: Holding) => {
                    // Use timeframe-specific $ change if available, otherwise use total P&L
                    let pnlValue;
                    if (selectedTimeframe !== 'All' && tickerPerf && tickerPerf[h.Symbol]?.[selectedTimeframe]) {
                        // Calculate position-level change: change_per_share * quantity
                        const changePerShare = tickerPerf[h.Symbol][selectedTimeframe].change_value;
                        pnlValue = changePerShare * h.Quantity;
                    } else {
                        pnlValue = h.PnL;
                    }

                    return {
                        name: h.Symbol,
                        value: pnlValue,
                        fill: pnlValue >= 0 ? '#10B981' : '#EF4444'
                    };
                }).sort((a: any, b: any) => b.value - a.value);
        }
    };

    const chartData = getChartData();

    return (
        <div className="p-8 max-w-[1600px] mx-auto space-y-8 font-sans">
            {/* Header Section */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Left: Main Balance */}
                <div className="lg:col-span-2 space-y-1">
                    <h2 className="text-gray-400 font-medium">Net Worth</h2>
                    <div className="flex items-baseline gap-4">
                        <h1 className="text-5xl font-bold text-foreground tracking-tight">
                            ${totalValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                        </h1>
                    </div>

                    <div className="flex items-center gap-2 mt-2">
                        <span className={`text-lg font-medium ${totalPnL >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {totalPnL >= 0 ? '+' : ''}${totalPnL.toLocaleString()}
                        </span>
                        <span className={`text-sm px-2 py-0.5 rounded ${totalPnL >= 0 ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>
                            {totalPnL >= 0 ? '+' : ''}{pnlPercent.toFixed(2)}%
                        </span>
                        <span className="text-gray-500 text-sm ml-2">All Time (Unrealized)</span>
                    </div>
                </div>

                {/* Right: Key Stats */}
                <div className="glass-panel p-6 rounded-2xl flex flex-col justify-center space-y-3">
                    <div className="flex justify-between items-center text-sm">
                        <span className="text-gray-400">Unrealized Gains:</span>
                        <span className={`font-medium ${totalPnL >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {totalPnL >= 0 ? '+' : ''}${totalPnL.toLocaleString()}
                        </span>
                    </div>
                    <div className="flex justify-between items-center text-sm">
                        <span className="text-gray-400">Portfolio Cost:</span>
                        <span className="text-foreground">${totalCost.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between items-center text-sm">
                        <span className="text-gray-400">Holdings Count:</span>
                        <span className="text-foreground">{data.holdings.length}</span>
                    </div>
                    {/* Placeholders for fields we don't have yet */}
                    <div className="flex justify-between items-center text-sm">
                        <span className="text-gray-400">Dividends (YTD):</span>
                        <span className="text-gray-400">--</span>
                    </div>
                </div>
            </div>

            {/* Benchmarks Row (Mocked/Static for now) */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                    { name: 'S&P 500', val: '4,783.45', change: '+0.56%' },
                    { name: 'NASDAQ', val: '15,055.65', change: '+0.12%' },
                    { name: 'TSX', val: '20,958.40', change: '-0.23%' },
                    { name: 'BTC-USD', val: '46,230.00', change: '+2.41%' }
                ].map((bench: any) => (
                    <div key={bench.name} className="glass-panel p-4 rounded-xl">
                        <div className="text-gray-400 text-xs font-semibold uppercase">{bench.name}</div>
                        <div className="flex items-end justify-between mt-1">
                            <span className="text-lg font-bold">{bench.val}</span>
                            <span className={`text-xs font-medium ${bench.change.startsWith('+') ? 'text-emerald-400' : 'text-rose-400'}`}>
                                {bench.change}
                            </span>
                        </div>
                    </div>
                ))}
            </div>

            {/* My Holdings - Visual Section */}
            <div className="space-y-4">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <h3 className="text-xl font-bold">Performance Map</h3>

                    {/* Controls Container */}
                    <div className="flex flex-col xl:flex-row gap-4">
                        {/* Metric Selector */}
                        <div className="flex gap-1 text-sm bg-white/5 p-1 rounded-lg">
                            {['Gain (Value)', 'Gain (%)', 'Weight'].map((m: string) => (
                                <button
                                    key={m}
                                    onClick={() => setSelectedMetric(m)}
                                    className={`px-3 py-1 rounded-md transition-all ${m === selectedMetric ? 'bg-black/10 dark:bg-white/10 text-foreground shadow-sm' : 'text-gray-400 hover:text-foreground'}`}
                                >
                                    {m}
                                </button>
                            ))}
                        </div>

                        {/* Time Range Selector - Currently shows total P&L (all holdings) */}
                        <div className="flex gap-1 text-sm bg-white/5 p-1 rounded-lg overflow-x-auto scrollbar-hide">
                            {['1d', '1w', '1m', '3m', '6m', 'YTD', '1y', 'All'].map((t: string) => (
                                <button
                                    key={t}
                                    onClick={() => setSelectedTimeframe(t)}
                                    className={`px-3 py-1 rounded-md transition-all whitespace-nowrap ${t === selectedTimeframe ? 'bg-black/10 dark:bg-white/10 text-foreground shadow-sm' : 'text-gray-400 hover:text-foreground'}`}
                                >
                                    {t}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="glass-panel p-6 rounded-2xl h-[350px] relative">
                    <div className="absolute inset-0 top-6 bottom-2 left-4 right-4">
                        <ResponsiveContainer width="100%" height="100%" minWidth={10} minHeight={10} debounce={300}>
                            <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                                <XAxis dataKey="name" stroke="#666" fontSize={10} tickLine={false} axisLine={false} />
                                <YAxis
                                    stroke="#666"
                                    fontSize={10}
                                    tickFormatter={(val: number) =>
                                        selectedMetric === 'Gain (%)' || selectedMetric === 'Weight'
                                            ? `${val.toFixed(0)}%`
                                            : `$${(val / 1000).toFixed(0)}k`
                                    }
                                    tickLine={false}
                                    axisLine={false}
                                />
                                <Tooltip
                                    cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}
                                    formatter={(val: any) =>
                                        selectedMetric === 'Gain (%)' || selectedMetric === 'Weight'
                                            ? [`${val.toFixed(2)}%`, selectedMetric]
                                            : [`$${val.toLocaleString()}`, selectedMetric]
                                    }
                                />
                                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                                    {chartData.map((entry: any, index: number) => (
                                        <Cell key={`cell-${index}`} fill={entry.fill} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            {/* Holdings Table */}
            <div className="glass-panel rounded-2xl overflow-hidden">
                <div className="p-6 border-b border-white/10 flex justify-between items-center">
                    <h3 className="text-lg font-bold">Holdings & Assets</h3>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                        <thead className="text-gray-400 bg-white/5 uppercase text-xs font-semibold tracking-wider">
                            <tr>
                                {[
                                    { label: 'Ticker', key: 'Symbol', align: 'left' },
                                    { label: 'Allocation', key: 'Market_Value', align: 'right' },
                                    { label: 'Price', key: 'Price', align: 'right' },
                                    { label: 'Avg Cost', key: 'AvgCost', align: 'right' },
                                    { label: 'Unr. Gain', key: 'PnL', align: 'right' },
                                    { label: 'Unr. %', key: 'PnLPercent', align: 'right' },
                                    { label: 'Market Value', key: 'Market_Value', align: 'right' },
                                ].map((col: any, idx: number) => {
                                    const isActive = sortConfig.key === col.key;
                                    return (
                                        <th
                                            key={col.key + idx}
                                            onClick={() => handleSort(col.key)}
                                            className={`p-4 cursor-pointer hover:bg-white/10 transition-colors group ${col.align === 'right' ? 'text-right' : 'text-left'} ${idx === 0 ? 'rounded-tl-lg' : ''} ${idx === 6 ? 'rounded-tr-lg' : ''}`}
                                        >
                                            <div className={`flex items-center gap-1 ${col.align === 'right' ? 'justify-end' : 'justify-start'}`}>
                                                {col.label}
                                                <div className="w-4 h-4 flex items-center justify-center">
                                                    {isActive ? (
                                                        sortConfig.direction === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />
                                                    ) : (
                                                        <ChevronUp size={14} className="opacity-0 group-hover:opacity-40 transition-opacity" />
                                                    )}
                                                </div>
                                            </div>
                                        </th>
                                    );
                                })}
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {sortedHoldings.map((h: Holding) => {
                                const avgCost = (h.Market_Value - h.PnL) / h.Quantity;
                                const allocation = (h.Market_Value / totalValue) * 100;
                                const isProfit = h.PnL >= 0;

                                return (
                                    <tr key={h.Symbol} className="hover:bg-white/5 transition-colors group">
                                        <td className="p-4">
                                            <div className="font-bold text-foreground">{h.Symbol}</div>
                                            <div className="text-xs text-gray-500">{h.Quantity} shares</div>
                                        </td>
                                        <td className="p-4 text-right text-gray-400">
                                            {allocation.toFixed(1)}%
                                        </td>
                                        <td className="p-4 text-right text-gray-400">${(h['Current Price'] || 0).toFixed(2)}</td>
                                        <td className="p-4 text-right text-gray-400">${avgCost.toFixed(2)}</td>
                                        <td className={`p-4 text-right font-medium ${isProfit ? 'text-emerald-400' : 'text-rose-400'}`}>
                                            ${h.PnL.toLocaleString()}
                                        </td>
                                        <td className={`p-4 text-right font-medium ${isProfit ? 'text-emerald-400' : 'text-rose-400'}`}>
                                            <div className="flex items-center justify-end gap-1">
                                                {isProfit ? <TrendingUp size={14} /> : <div className="p-1" />}
                                                {((h.PnL / (h.Market_Value - h.PnL)) * 100).toFixed(2)}%
                                            </div>
                                        </td>
                                        <td className="p-4 text-right font-bold text-foreground tracking-wide">
                                            ${h.Market_Value.toLocaleString()}
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Disclaimer Footer */}
            <div className="text-center text-gray-600 text-xs py-4">
                Market data is delayed. All figures in CAD. Last updated {new Date().toISOString().split('T')[0].replace(/-/g, '/')} {new Date().toLocaleTimeString()}.
            </div>
        </div>
    );
}
