"use client";

import { useEffect, useState, useMemo } from "react";
import { ExternalLink, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { API_BASE_URL } from "@/lib/api";
import { usePortfolio } from "@/lib/PortfolioContext";

interface QuantmentalData {
    Symbol: string;
    Thesis: string;
    Catalyst: string;
    CatalystLink: string;
    "Kill Switch": string;
    Conviction: string;
    RSI: number | string;
    "Tech Scorecard": string;
    "Next Earnings": string;
    "Ex-Div": string;
    Yield: string;
    Timeframe: string;
    "PEG Ratio": number | string;
    Growth: string;
    Rec: string;
}

export default function QuantmentalPage() {
    const { data: portData, loading, error } = usePortfolio();
    const [sortField, setSortField] = useState<string>("");
    const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

    const data = useMemo(() => {
        if (!portData) return [];

        return portData.holdings.map((h: any) => ({
            Symbol: h.Symbol,
            Thesis: h.Thesis || "",
            Catalyst: h.Catalyst || "",
            CatalystLink: h.CatalystLink || "",
            "Kill Switch": h["Kill Switch"] || "",
            Conviction: h.Conviction || "",
            RSI: typeof h.RSI === 'number' ? Math.round(h.RSI) : (h.RSI || 0),
            "Tech Scorecard": h["Tech Scorecard"] || "N/A",
            "Next Earnings": h["Next Earnings"] || "N/A",
            "Ex-Div": h["Ex-Div"] || "N/A",
            Yield: h.Yield || "0.00%",
            Timeframe: h.Timeframe || "",
            "PEG Ratio": h["PEG Ratio"] || "N/A",
            Growth: h.Growth || "N/A",
            Rec: h.Rec || "N/A"
        }));
    }, [portData]);

    const sortedData = useMemo(() => {
        if (!sortField) return data;

        return [...data].sort((a: QuantmentalData, b: QuantmentalData) => {
            const aVal = (a as any)[sortField];
            const bVal = (b as any)[sortField];

            if (aVal === bVal) return 0;
            if (aVal === 'N/A' || aVal === '') return 1;
            if (bVal === 'N/A' || bVal === '') return -1;

            const cleanA = typeof aVal === 'string' ? aVal.replace(/[$,%]/g, '') : aVal;
            const cleanB = typeof bVal === 'string' ? bVal.replace(/[$,%]/g, '') : bVal;

            if (!isNaN(cleanA) && !isNaN(cleanB)) {
                return sortDirection === 'asc' ? cleanA - cleanB : cleanB - cleanA;
            }

            return sortDirection === 'asc' ? String(aVal).localeCompare(String(bVal)) : String(bVal).localeCompare(String(aVal));
        });
    }, [data, sortField, sortDirection]);

    const handleSort = (field: string) => {
        const direction = sortField === field && sortDirection === 'asc' ? 'desc' : 'asc';
        setSortField(field);
        setSortDirection(direction);
    };

    const getRecommendationColor = (rec: string) => {
        if (rec === 'Strong Buy') return 'text-emerald-700 font-bold';
        if (rec === 'Buy') return 'text-green-700 font-bold';
        if (rec === 'Hold') return 'text-amber-700 font-bold';
        if (rec === 'Sell') return 'text-rose-700 font-bold';
        return ''; // Handled by inline style
    };

    const getRSIColor = (rsi: number | string) => {
        if (typeof rsi !== 'number' || isNaN(Number(rsi))) return { color: '#666' };
        const val = Number(rsi);
        if (val > 70) return { color: '#e11d48', fontWeight: 'bold' }; // rose-600
        if (val < 30) return { color: '#059669', fontWeight: 'bold' }; // emerald-600
        return { color: '#000', fontWeight: 'bold' };
    };

    const getConvictionBadge = (conviction: string) => {
        const colors = {
            'High': 'bg-emerald-500/20 text-emerald-400 border-emerald-500',
            'Medium': 'bg-blue-500/20 text-blue-400 border-blue-500',
            'Low': 'bg-gray-500/20 text-gray-400 border-gray-500',
            'Whatever': 'bg-purple-500/20 text-purple-400 border-purple-500'
        };
        return colors[conviction as keyof typeof colors] || colors.Low;
    };

    if (loading) return <div className="p-10 text-center animate-pulse">Loading Quant-mental Analysis...</div>;

    if (data.length === 0) {
        return (
            <div className="p-10 text-center">
                <div className="glass-panel p-8 rounded-2xl max-w-2xl mx-auto">
                    <h2 className="text-2xl font-bold mb-4">Quant-mental Analysis</h2>
                    <p className="text-gray-400 mb-4">
                        The Quant-mental feature combines quantitative metrics with your investment thesis for each holding.
                    </p>
                    <p className="text-sm text-gray-500">
                        Backend API needs to be updated to include thesis, catalyst, and fundamental data from thesis.json.
                        Reference: portfolio_dashboard.html shows the expected format.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="p-8 max-w-[1800px] mx-auto space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">
                        Quant-mental Analysis
                    </h1>
                    <p className="text-gray-400 mt-2">Combining quantitative metrics with investment thesis</p>
                </div>
            </div>

            {/* Main Table */}
            <div className="glass-panel rounded-2xl overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-white/5 sticky top-0">
                            <tr>
                                {['Symbol', 'Thesis', 'Catalyst', 'Kill Switch', 'Conviction', 'RSI', 'Tech Scorecard', 'Next Earnings', 'Ex-Div', 'Yield', 'Timeframe', 'PEG Ratio', 'Growth', 'Rec'].map((header: string) => (
                                    <th
                                        key={header}
                                        onClick={() => handleSort(header)}
                                        className="p-4 text-left font-semibold cursor-pointer hover:bg-white/10 transition-colors select-none"
                                    >
                                        <div className="flex items-center gap-2">
                                            {header}
                                            <span className="text-gray-500 text-xs">↕</span>
                                        </div>
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {sortedData.map((row: QuantmentalData, idx: number) => (
                                <tr key={`${row.Symbol}-${idx}`} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                                    <td className="p-4 font-bold text-blue-600">{row.Symbol}</td>
                                    <td className="p-4 max-w-md">
                                        <div
                                            className="text-sm font-bold leading-relaxed line-clamp-2"
                                            style={{ color: '#000' }}
                                            title={row.Thesis}
                                        >
                                            {row.Thesis || <span style={{ color: '#999', fontStyle: 'italic', fontWeight: 'normal' }}>--</span>}
                                        </div>
                                    </td>
                                    <td className="p-4 max-w-sm">
                                        {row.Catalyst ? (
                                            <a
                                                href={row.CatalystLink}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="text-sm text-gray-700 dark:text-gray-400 line-clamp-2 flex items-center gap-2 hover:text-blue-500 transition-colors"
                                            >
                                                {row.Catalyst}
                                                <ExternalLink className="w-3 h-3 flex-shrink-0" />
                                            </a>
                                        ) : <span className="text-gray-400 italic">--</span>}
                                    </td>
                                    <td className="p-4 text-sm text-gray-700 dark:text-gray-400 font-medium">{row["Kill Switch"] || <span className="text-gray-400">--</span>}</td>
                                    <td className="p-4">
                                        {row.Conviction ? (
                                            <span className={`px-2 py-1 rounded-md text-xs font-bold border ${getConvictionBadge(row.Conviction)}`}>
                                                {row.Conviction}
                                            </span>
                                        ) : <span className="text-gray-400">--</span>}
                                    </td>
                                    <td className="p-4 text-sm">
                                        <span style={getRSIColor(row.RSI)}>
                                            {row.RSI}
                                        </span>
                                    </td>
                                    <td
                                        className="p-4 text-sm font-bold"
                                        style={{ color: '#000' }}
                                    >
                                        {row["Tech Scorecard"]}
                                    </td>
                                    <td className="p-4 text-sm font-medium" style={{ color: '#333' }}>{row["Next Earnings"]}</td>
                                    <td className="p-4 text-sm font-medium" style={{ color: '#333' }}>{row["Ex-Div"]}</td>
                                    <td className="p-4 text-sm font-bold" style={{ color: '#059669' }}>{row.Yield}</td>
                                    <td className="p-4 text-sm font-medium" style={{ color: '#666' }}>{row.Timeframe || '--'}</td>
                                    <td className="p-4 text-sm font-bold">
                                        {typeof row["PEG Ratio"] === 'number' && (
                                            <span style={{ color: row["PEG Ratio"] < 1 ? '#059669' : row["PEG Ratio"] > 2 ? '#e11d48' : '#000' }}>
                                                {row["PEG Ratio"].toFixed(2)}
                                            </span>
                                        )}
                                        {row["PEG Ratio"] === 'N/A' && <span style={{ color: '#999' }}>--</span>}
                                    </td>
                                    <td className="p-4 text-sm font-bold" style={{ color: '#000' }}>{row.Growth}</td>
                                    <td className={`p-4 text-sm font-bold ${getRecommendationColor(row.Rec)}`} style={!getRecommendationColor(row.Rec) ? { color: '#000' } : {}}>
                                        {row.Rec}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Legend */}
            <div className="glass-panel p-6 rounded-xl space-y-4 text-sm text-gray-400">
                <div>
                    <strong className="text-foreground">* PEG Ratio:</strong> &lt; 1.0 (Undervalued); 1.0-2.0 (Fair); &gt; 2.0 (Overvalued/High Expectations).
                </div>
                <div>
                    <strong className="text-foreground">* Tech Scorecard:</strong> Combined signals from 3 indicators:
                    <ul className="ml-6 mt-2 space-y-1">
                        <li><strong>MACD:</strong> Momentum shift (🚀 Buy / 🔻 Sell).</li>
                        <li><strong>Bollinger:</strong> Volatility extremes (Breakout) or potential explosions (<strong>Squeeze</strong>: "Calm before the storm").</li>
                        <li><strong>Candles:</strong> Reversal patterns (🔨 Hammer = Bullish, 🌠 Star = Bearish, <strong>Doji</strong> = Indecision).</li>
                    </ul>
                </div>
            </div>
        </div>
    );
}
