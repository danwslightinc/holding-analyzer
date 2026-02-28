"use client";

import { useEffect, useState, useMemo } from "react";
import { ExternalLink, TrendingUp, TrendingDown, Minus, Edit2, Save, X } from "lucide-react";
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
    const { data: portData, loading, error, refresh } = usePortfolio();
    const [sortField, setSortField] = useState<string>("");
    const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

    const [editingSymbol, setEditingSymbol] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);
    const [editForm, setEditForm] = useState({
        Thesis: "",
        "Kill Switch": "",
        Conviction: "Medium",
        Timeframe: "Long-term"
    });

    const handleEdit = (row: QuantmentalData) => {
        setEditingSymbol(row.Symbol);
        setEditForm({
            Thesis: row.Thesis || "",
            "Kill Switch": row["Kill Switch"] || "",
            Conviction: row.Conviction || "Medium",
            Timeframe: row.Timeframe || "Long-term"
        });
    };

    const handleSave = async (symbol: string) => {
        setSaving(true);
        try {
            const response = await fetch(`${API_BASE_URL}/api/holdings/${symbol}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(editForm)
            });
            if (response.ok) {
                setEditingSymbol(null);
                await refresh(true);
            }
        } catch (error) {
            console.error("Failed to update", error);
        } finally {
            setSaving(false);
        }
    };

    const data = useMemo(() => {
        if (!portData) return [];

        // Group by Symbol to avoid duplicates
        const grouped = portData.holdings.reduce((acc: any, h: any) => {
            const sym = h.Symbol;
            if (!acc[sym]) {
                acc[sym] = { ...h };
            } else {
                // If needed, we could sum quantities here, but for Quant-mental
                // we mostly care about symbol-level metrics and the thesis.
                acc[sym].Quantity = (acc[sym].Quantity || 0) + (h.Quantity || 0);
            }
            return acc;
        }, {});

        return Object.values(grouped).map((h: any) => ({
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
                                {['Symbol', 'Thesis', 'Catalyst', 'Kill Switch', 'Conviction', 'RSI', 'Tech Scorecard', 'Next Earnings', 'Ex-Div', 'Yield', 'Timeframe', 'PEG Ratio', 'Growth', 'Rec', 'Action'].map((header: string) => (
                                    <th
                                        key={header}
                                        onClick={() => header !== 'Action' && handleSort(header)}
                                        className={`p-4 font-semibold select-none ${header === 'Action' ? 'text-center cursor-default text-gray-400' : 'text-left cursor-pointer hover:bg-white/10 transition-colors'}`}
                                    >
                                        <div className={`flex items-center gap-2 ${header === 'Action' ? 'justify-center' : ''}`}>
                                            {header}
                                            {header !== 'Action' && <span className="text-gray-500 text-xs">↕</span>}
                                        </div>
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {sortedData.map((row: QuantmentalData, idx: number) => {
                                const isEditing = editingSymbol === row.Symbol;

                                return (
                                    <tr key={`${row.Symbol}-${idx}`} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                                        <td className="p-4 font-bold text-blue-600">{row.Symbol}</td>

                                        <td className="p-4 max-w-md">
                                            {isEditing ? (
                                                <textarea
                                                    className="w-full bg-white/5 border border-white/20 rounded p-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-blue-500 min-h-[60px]"
                                                    value={editForm.Thesis}
                                                    onChange={e => setEditForm({ ...editForm, Thesis: e.target.value })}
                                                />
                                            ) : (
                                                <div
                                                    className="text-sm font-bold leading-relaxed line-clamp-2"
                                                    style={{ color: '#000' }}
                                                    title={row.Thesis}
                                                >
                                                    {row.Thesis || <span style={{ color: '#999', fontStyle: 'italic', fontWeight: 'normal' }}>--</span>}
                                                </div>
                                            )}
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

                                        <td className="p-4 max-w-xs">
                                            {isEditing ? (
                                                <input
                                                    className="w-full bg-white/5 border border-white/20 rounded p-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-blue-500"
                                                    value={editForm["Kill Switch"]}
                                                    onChange={e => setEditForm({ ...editForm, "Kill Switch": e.target.value })}
                                                />
                                            ) : (
                                                <div className="text-sm text-gray-700 dark:text-gray-400 font-medium line-clamp-2" title={row["Kill Switch"]}>{row["Kill Switch"] || <span className="text-gray-400">--</span>}</div>
                                            )}
                                        </td>

                                        <td className="p-4">
                                            {isEditing ? (
                                                <select
                                                    className="bg-white/5 border border-white/20 rounded p-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-blue-500"
                                                    value={editForm.Conviction}
                                                    onChange={e => setEditForm({ ...editForm, Conviction: e.target.value })}
                                                >
                                                    <option value="High" className="text-black">High</option>
                                                    <option value="Medium" className="text-black">Medium</option>
                                                    <option value="Low" className="text-black">Low</option>
                                                </select>
                                            ) : row.Conviction ? (
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

                                        <td className="p-4">
                                            {isEditing ? (
                                                <input
                                                    className="w-24 bg-white/5 border border-white/20 rounded p-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-blue-500"
                                                    value={editForm.Timeframe}
                                                    onChange={e => setEditForm({ ...editForm, Timeframe: e.target.value })}
                                                    placeholder="e.g. Long-term"
                                                />
                                            ) : (
                                                <span className="text-sm font-medium" style={{ color: '#666' }}>{row.Timeframe || '--'}</span>
                                            )}
                                        </td>

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

                                        <td className="p-4 text-center">
                                            {isEditing ? (
                                                <div className="flex items-center justify-center gap-2">
                                                    <button
                                                        onClick={() => handleSave(row.Symbol)}
                                                        disabled={saving}
                                                        className="p-1.5 bg-emerald-500 hover:bg-emerald-600 text-white rounded transition-colors disabled:opacity-50"
                                                        title="Save"
                                                    >
                                                        <Save className="w-4 h-4" />
                                                    </button>
                                                    <button
                                                        onClick={() => setEditingSymbol(null)}
                                                        disabled={saving}
                                                        className="p-1.5 bg-gray-500 hover:bg-gray-600 text-white rounded transition-colors disabled:opacity-50"
                                                        title="Cancel"
                                                    >
                                                        <X className="w-4 h-4" />
                                                    </button>
                                                </div>
                                            ) : (
                                                <button
                                                    onClick={() => handleEdit(row)}
                                                    className="p-1.5 text-gray-400 hover:text-blue-500 hover:bg-white/5 rounded transition-colors"
                                                    title="Edit Thesis Data"
                                                >
                                                    <Edit2 className="w-4 h-4" />
                                                </button>
                                            )}
                                        </td>
                                    </tr>
                                )
                            })}
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
