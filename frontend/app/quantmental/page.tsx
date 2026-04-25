"use client";

import { useEffect, useState, useMemo } from "react";
import { ExternalLink, TrendingUp, TrendingDown, Minus, Edit2, Save, X, Sparkles, BrainCircuit, RefreshCw, Search, Wand2 } from "lucide-react";
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

export default function QuantmentalPage({ portfolioFilter = "ALL" }: { portfolioFilter?: string }) {
    const { data: portData, loading, error, refresh } = usePortfolio();
    const [sortField, setSortField] = useState<string>("");
    const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

    const [editingSymbol, setEditingSymbol] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);
    const [analyzing, setAnalyzing] = useState(false);
    const [aiAnalysis, setAiAnalysis] = useState<string | null>(null);
    const [aiModel, setAiModel] = useState<string | null>(null);

    const [researchingSymbol, setResearchingSymbol] = useState<string | null>(null);
    const [researchData, setResearchData] = useState<string | null>(null);
    const [isResearchLoading, setIsResearchLoading] = useState(false);

    const runAiAnalysis = async () => {
        setAnalyzing(true);
        try {
            const res = await fetch(`${API_BASE_URL}/api/ai/analyze`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ 
                    query: "Summarize the composition and trends in this portfolio data.",
                    category: portfolioFilter
                })
            });
            const data = await res.json();
            setAiAnalysis(data.analysis);
            setAiModel(data.model || "Local Engine");
        } catch (err) {
            console.error("AI analysis failed", err);
            setAiAnalysis("Failed to connect to AI engine. Ensure Ollama is running or GOOGLE_API_KEY is set in .env");
            setAiModel("Error");
        } finally {
            setAnalyzing(false);
        }
    };

    const handleResearch = async (symbol: string) => {
        setResearchingSymbol(symbol);
        setIsResearchLoading(true);
        setResearchData(null);
        try {
            const res = await fetch(`${API_BASE_URL}/api/ai/research-holding`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ symbol })
            });
            const data = await res.json();
            setResearchData(data.analysis);
        } catch (err) {
            console.error("Research failed", err);
            setResearchData("Failed to load AI research. Check API connection and GOOGLE_API_KEY.");
        } finally {
            setIsResearchLoading(false);
        }
    };

    const handleDraft = async (field: 'Thesis' | 'Kill Switch') => {
        if (!editingSymbol) return;
        try {
            const res = await fetch(`${API_BASE_URL}/api/ai/draft-thesis`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ symbol: editingSymbol, field })
            });
            const data = await res.json();
            if (data.draft) {
                setEditForm(prev => ({ ...prev, [field]: data.draft }));
            }
        } catch (err) {
            console.error("Drafting failed", err);
        }
    };
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
        if (!portData || !portData.holdings) {
            console.log("DEBUG: portData or holdings missing", portData);
            return [];
        }

        const filtered = portData.holdings.filter((h: any) => 
            portfolioFilter === "ALL" || h.Portfolio_Category === portfolioFilter
        );

        console.log(`DEBUG: Processing ${filtered.length} holdings for Quant-mental`);

        // Group by Symbol to avoid duplicates
        const grouped = filtered.reduce((acc: any, h: any) => {
            const sym = h.Symbol;
            if (!acc[sym]) {
                acc[sym] = { ...h };
            } else {
                // Sum quantities for aggregated symbol view
                acc[sym].Quantity = (acc[sym].Quantity || 0) + (h.Quantity || 0);
            }
            return acc;
        }, {});

        const result = Object.values(grouped).map((h: any) => ({
            Symbol: h.Symbol,
            Thesis: h.Thesis || "",
            Catalyst: h.Catalyst || "",
            CatalystLink: h.CatalystLink || "",
            "Kill Switch": h["Kill Switch"] || "",
            Conviction: h.Conviction || "",
            RSI: typeof h.RSI === 'number' ? Math.round(h.RSI) : (h.RSI || 0),
            "Tech Scorecard": h["Tech Scorecard"] || "--",
            "Next Earnings": h["Next Earnings"] || "--",
            "Ex-Div": h["Ex-Div"] || "--",
            Yield: h.Yield || "0.00%",
            Timeframe: h.Timeframe || "",
            "PEG Ratio": h["PEG Ratio"] || "--",
            Growth: h.Growth || "--",
            Rec: h.Rec || "--"
        }));
        
        console.log(`DEBUG: Found ${result.length} unique symbols for Quant-mental`);
        return result;
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

    const getRecommendationBadge = (rec: string) => {
        if (rec === 'Strong Buy') return 'bg-emerald-500/20 text-emerald-400 border-emerald-500';
        if (rec === 'Buy') return 'bg-green-500/20 text-green-400 border-green-500';
        if (rec === 'Hold') return 'bg-amber-500/20 text-amber-400 border-amber-500';
        if (rec === 'Sell') return 'bg-rose-500/20 text-rose-400 border-rose-500';
        if (rec === 'Underperform') return 'bg-orange-500/20 text-orange-400 border-orange-500';
        return 'bg-gray-500/20 text-gray-400 border-gray-500';
    };

    const getRSIColor = (rsi: number | string) => {
        if (typeof rsi !== 'number' || isNaN(Number(rsi))) return { color: '#666' };
        const val = Number(rsi);
        if (val > 70) return { color: '#e11d48', fontWeight: 'bold' }; // rose-600
        if (val < 30) return { color: '#059669', fontWeight: 'bold' }; // emerald-600
        return { fontWeight: 'bold' };
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
                <div className="glass-panel p-12 rounded-3xl max-w-2xl mx-auto border border-blue-500/20 bg-blue-500/5">
                    <BrainCircuit className="w-16 h-16 text-blue-400 mx-auto mb-6 opacity-50" />
                    <h2 className="text-2xl font-bold mb-4 text-foreground">No Holdings Detected</h2>
                    <p className="text-gray-400 mb-8 leading-relaxed">
                        The Quant-mental dashboard requires active positions to analyze. 
                        Record some trades in the <strong>Transactions</strong> tab to see technical scores, investment theses, and fundamental metrics here.
                    </p>
                    <button 
                        onClick={() => refresh(true)}
                        className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-bold transition-all shadow-lg shadow-blue-500/20"
                    >
                        Force Data Refresh
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="p-4 md:p-8 max-w-[1800px] mx-auto space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">
                        Quant-mental Analysis
                    </h1>
                    <p className="text-gray-400 mt-2">Combining quantitative metrics with investment thesis</p>
                </div>
                
                <button
                    onClick={runAiAnalysis}
                    disabled={analyzing}
                    className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-xl font-bold text-sm transition-all shadow-lg shadow-purple-500/20 disabled:opacity-50"
                >
                    {analyzing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                    {analyzing ? "AI is Thinking..." : "Generate AI Insights"}
                </button>
            </div>

            {/* AI Insights Panel */}
            {aiAnalysis && (
                <div className="glass-panel p-6 rounded-2xl border border-purple-500/30 bg-purple-500/5 animate-in fade-in slide-in-from-top-4 duration-500">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-2 text-purple-400 font-bold uppercase tracking-widest text-xs">
                            <BrainCircuit className="w-4 h-4" />
                            Intelligence Report
                        </div>
                        {aiModel && (
                            <span className="text-[10px] bg-purple-500/20 text-purple-300 px-2 py-0.5 rounded-full border border-purple-500/30 font-mono">
                                ENGINE: {aiModel.toUpperCase()}
                            </span>
                        )}
                    </div>
                    <div className="text-gray-900 dark:text-gray-200 prose prose-invert max-w-none whitespace-pre-wrap leading-relaxed text-sm">
                        {aiAnalysis}
                    </div>
                </div>
            )}

            {/* Main Table */}
            <div className="glass-panel rounded-2xl overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-white/5 sticky top-0">
                            <tr>
                                {['Symbol', 'Thesis', 'Catalyst', 'Kill Switch', 'Conviction', 'RSI', 'Tech Scorecard', 'Next Earnings', 'Ex-Div', 'Yield', 'Timeframe', 'PEG Ratio', 'Growth', 'Rec', 'Actions'].map((header: string) => (
                                    <th
                                        key={header}
                                        onClick={() => header !== 'Actions' && handleSort(header)}
                                        className={`p-4 font-semibold select-none ${header === 'Actions' ? 'text-center cursor-default text-gray-400' : 'text-left cursor-pointer hover:bg-white/10 transition-colors'}`}
                                    >
                                        <div className={`flex items-center gap-2 ${header === 'Actions' ? 'justify-center' : ''}`}>
                                            {header}
                                            {header !== 'Actions' && <span className="text-gray-500 text-xs">↕</span>}
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
                                                <div className="relative group">
                                                    <textarea
                                                        className="w-full bg-white/5 border border-white/20 rounded p-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-blue-500 min-h-[60px] pr-8"
                                                        value={editForm.Thesis}
                                                        onChange={e => setEditForm({ ...editForm, Thesis: e.target.value })}
                                                    />
                                                    <button 
                                                        onClick={() => handleDraft('Thesis')}
                                                        className="absolute top-2 right-2 text-purple-400 hover:text-purple-300 p-1 rounded-md hover:bg-white/10 transition-all opacity-0 group-hover:opacity-100"
                                                        title="AI Draft Thesis"
                                                    >
                                                        <Wand2 className="w-3 h-3" />
                                                    </button>
                                                </div>
                                            ) : (
                                                <div
                                                    className="text-sm font-bold leading-relaxed line-clamp-2 text-gray-900 dark:text-white/90"
                                                    title={row.Thesis}
                                                >
                                                    {row.Thesis || <span className="text-gray-400 dark:text-gray-500 italic font-normal">--</span>}
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
                                                <div className="relative group">
                                                    <input
                                                        className="w-full bg-white/5 border border-white/20 rounded p-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-blue-500 pr-8"
                                                        value={editForm["Kill Switch"]}
                                                        onChange={e => setEditForm({ ...editForm, "Kill Switch": e.target.value })}
                                                    />
                                                    <button 
                                                        onClick={() => handleDraft('Kill Switch')}
                                                        className="absolute top-1/2 -translate-y-1/2 right-2 text-purple-400 hover:text-purple-300 p-1 rounded-md hover:bg-white/10 transition-all opacity-0 group-hover:opacity-100"
                                                        title="AI Draft Kill Switch"
                                                    >
                                                        <Wand2 className="w-3 h-3" />
                                                    </button>
                                                </div>
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
                                            <span
                                                className="text-gray-900 dark:text-white"
                                                style={getRSIColor(row.RSI)}
                                            >
                                                {row.RSI}
                                            </span>
                                        </td>
                                        <td
                                            className="p-4 text-sm font-bold text-gray-900 dark:text-white"
                                        >
                                            {row["Tech Scorecard"]}
                                        </td>
                                        <td className="p-4 text-sm font-medium text-gray-700 dark:text-white/70">{row["Next Earnings"]}</td>
                                        <td className="p-4 text-sm font-medium text-gray-700 dark:text-white/70">{row["Ex-Div"]}</td>
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
                                                <span
                                                    className="text-gray-900 dark:text-white"
                                                    style={{ color: row["PEG Ratio"] < 1 ? '#059669' : row["PEG Ratio"] > 2 ? '#e11d48' : undefined }}
                                                >
                                                    {row["PEG Ratio"].toFixed(2)}
                                                </span>
                                            )}
                                            {row["PEG Ratio"] === 'N/A' && <span style={{ color: '#999' }}>--</span>}
                                        </td>
                                        <td className="p-4 text-sm font-bold text-gray-900 dark:text-white">{row.Growth}</td>
                                        <td className="p-4">
                                            <span className={`px-2 py-1 rounded-md text-[10px] font-bold border uppercase tracking-wider ${getRecommendationBadge(row.Rec)}`}>
                                                {row.Rec}
                                            </span>
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
                                                <div className="flex items-center justify-center gap-1">
                                                    <button
                                                        onClick={() => handleResearch(row.Symbol)}
                                                        className="p-1.5 text-purple-400 hover:text-purple-300 hover:bg-white/5 rounded transition-colors"
                                                        title="AI Research Deep Dive"
                                                    >
                                                        <Search className="w-4 h-4" />
                                                    </button>
                                                    <button
                                                        onClick={() => handleEdit(row)}
                                                        className="p-1.5 text-gray-400 hover:text-blue-500 hover:bg-white/5 rounded transition-colors"
                                                        title="Edit Thesis Data"
                                                    >
                                                        <Edit2 className="w-4 h-4" />
                                                    </button>
                                                </div>
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

            {/* AI Research Modal */}
            {researchingSymbol && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
                    <div className="glass-panel w-full max-w-4xl max-h-[90vh] overflow-hidden rounded-3xl border border-purple-500/30 flex flex-col shadow-2xl">
                        {/* Modal Header */}
                        <div className="p-6 border-b border-white/10 flex items-center justify-between bg-gradient-to-r from-purple-900/20 to-indigo-900/20">
                            <div className="flex items-center gap-4">
                                <div className="w-12 h-12 rounded-2xl bg-purple-500/20 flex items-center justify-center border border-purple-500/40">
                                    <BrainCircuit className="w-6 h-6 text-purple-400" />
                                </div>
                                <div>
                                    <h2 className="text-xl font-bold text-foreground">AI Research Deep Dive</h2>
                                    <p className="text-purple-400 font-mono text-sm tracking-widest">{researchingSymbol}</p>
                                </div>
                            </div>
                            <button 
                                onClick={() => setResearchingSymbol(null)}
                                className="p-2 hover:bg-white/10 rounded-full transition-colors text-gray-400 hover:text-white"
                            >
                                <X className="w-6 h-6" />
                            </button>
                        </div>

                        {/* Modal Content */}
                        <div className="p-8 overflow-y-auto custom-scrollbar flex-1 bg-black/20">
                            {isResearchLoading ? (
                                <div className="flex flex-col items-center justify-center py-20 space-y-6">
                                    <div className="relative">
                                        <div className="w-16 h-16 border-4 border-purple-500/20 border-t-purple-500 rounded-full animate-spin"></div>
                                        <Sparkles className="w-6 h-6 text-purple-400 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 animate-pulse" />
                                    </div>
                                    <div className="text-center">
                                        <h3 className="text-lg font-medium text-purple-300">Consulting Gemini Flash...</h3>
                                        <p className="text-gray-500 text-sm mt-1">Analyzing fundamentals, technicals, and latest news</p>
                                    </div>
                                </div>
                            ) : (
                                <div className="prose prose-invert max-w-none prose-headings:text-purple-400 prose-strong:text-white prose-p:text-gray-300 leading-relaxed">
                                    {researchData ? (
                                        <div className="whitespace-pre-wrap">
                                            {researchData}
                                        </div>
                                    ) : (
                                        <div className="text-center py-10 text-gray-500">
                                            No data returned from AI engine.
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>

                        {/* Modal Footer */}
                        <div className="p-4 border-t border-white/10 bg-white/5 flex justify-end">
                            <button
                                onClick={() => setResearchingSymbol(null)}
                                className="px-6 py-2 bg-white/10 hover:bg-white/20 text-white rounded-xl font-bold transition-all"
                            >
                                Close Research
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
